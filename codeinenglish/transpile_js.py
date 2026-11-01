"""Transpile the small Python subset used by recipes into JavaScript."""

from __future__ import annotations

import ast
import json

from .errors import CodeInEnglishError
from .recipes import BY_KEY

_PRELUDE = """\
function enIn(item, container) { return container instanceof Set ? container.has(item) : container.includes(item); }
function enLen(value) { return value instanceof Set ? value.size : value.length; }
function enAt(value, index) { return value[index < 0 ? value.length + index : index]; }
function enMod(a, b) { return ((a % b) + b) % b; }
function enSorted(value) { return [...value].sort((a, b) => (a < b ? -1 : a > b ? 1 : 0)); }
function enMax(values) { return values.reduce((a, b) => (b > a ? b : a)); }
function enMin(values) { return values.reduce((a, b) => (b < a ? b : a)); }
function enReversed(value) { return Array.from(value).reverse(); }
function enSum(values) { let total = 0; for (const value of values) total += value; return total; }
"""
_COMPARE = {ast.Eq: "===", ast.NotEq: "!==", ast.Lt: "<", ast.LtE: "<=", ast.Gt: ">", ast.GtE: ">="}
_BINARY = {ast.Add: "+", ast.Sub: "-", ast.Mult: "*", ast.Div: "/"}
_TESTS = {"isupper": r"/^\p{Lu}+$/u", "islower": r"/^\p{Ll}+$/u", "isdigit": r"/^[0-9]+$/", "isalpha": r"/^\p{L}+$/u", "isspace": r"/^\s+$/"}
_METHODS = {"lower": "toLowerCase", "upper": "toUpperCase", "append": "push", "add": "add"}
_CHECKS = {
    "integer": "Number.isSafeInteger({0})",
    "number": "typeof {0} === 'number' && Number.isFinite({0})",
    "string": "typeof {0} === 'string'",
    "integer_list": "Array.isArray({0}) && {0}.every(Number.isSafeInteger)",
    "sorted_integer_list": "Array.isArray({0}) && {0}.every(Number.isSafeInteger) && {0}.every((v, i) => i === 0 || {0}[i - 1] <= v)",
}


def _fail(node, message):
    raise CodeInEnglishError("<recipe>", getattr(node, "lineno", 1), f"JavaScript: {message}", kind="unsupported")


def _name(identifier):
    return f"en_{identifier}"


def _expr(node):
    if isinstance(node, ast.Constant):
        if type(node.value) is int and abs(node.value) > 2**53 - 1:
            _fail(node, "integer literal outside the exact Number range")
        return json.dumps(node.value, ensure_ascii=False)
    if isinstance(node, ast.Name):
        return _name(node.id)
    if isinstance(node, ast.BinOp):
        left, right = _expr(node.left), _expr(node.right)
        if isinstance(node.op, ast.Mod):
            return f"enMod({left}, {right})"
        if isinstance(node.op, ast.FloorDiv):
            return f"Math.floor({left} / {right})"
        if type(node.op) in _BINARY:
            return f"({left} {_BINARY[type(node.op)]} {right})"
        _fail(node, f"operator {type(node.op).__name__}")
    if isinstance(node, ast.UnaryOp):
        symbol = {ast.Not: "!", ast.USub: "-"}.get(type(node.op))
        return f"({symbol}{_expr(node.operand)})" if symbol else _fail(node, "unary operator")
    if isinstance(node, ast.BoolOp):
        return "(" + (" && " if isinstance(node.op, ast.And) else " || ").join(_expr(v) for v in node.values) + ")"
    if isinstance(node, ast.IfExp):
        return f"({_expr(node.test)} ? {_expr(node.body)} : {_expr(node.orelse)})"
    if isinstance(node, ast.Compare):
        parts, left = [], node.left
        for op, right in zip(node.ops, node.comparators):
            if isinstance(op, (ast.In, ast.NotIn)):
                test = f"enIn({_expr(left)}, {_expr(right)})"
                parts.append(test if isinstance(op, ast.In) else f"!{test}")
            elif type(op) in _COMPARE:
                parts.append(f"{_expr(left)} {_COMPARE[type(op)]} {_expr(right)}")
            else:
                _fail(node, "comparison")
            left = right
        return "(" + " && ".join(parts) + ")"
    if isinstance(node, ast.List):
        return "[" + ", ".join(_expr(item) for item in node.elts) + "]"
    if isinstance(node, ast.Subscript):
        if isinstance(node.slice, ast.Slice):
            _fail(node, "slices")
        return f"enAt({_expr(node.value)}, {_expr(node.slice)})"
    if isinstance(node, (ast.ListComp, ast.GeneratorExp)):
        if len(node.generators) != 1 or not isinstance(node.generators[0].target, ast.Name):
            _fail(node, "nested comprehensions")
        generator, variable = node.generators[0], _name(node.generators[0].target.id)
        result = f"Array.from({_expr(generator.iter)})"
        for condition in generator.ifs:
            result += f".filter(({variable}) => {_expr(condition)})"
        return f"{result}.map(({variable}) => {_expr(node.elt)})"
    if isinstance(node, ast.Call) and not node.keywords:
        arguments = [_expr(argument) for argument in node.args]
        if isinstance(node.func, ast.Attribute) and node.func.attr == "join" and isinstance(node.func.value, ast.Constant):
            return f"{arguments[0]}.join({_expr(node.func.value)})"
        if isinstance(node.func, ast.Attribute) and node.func.attr == "split" and not arguments:
            return f'{_expr(node.func.value)}.split(/\\s+/).filter((word) => word !== "")'
        if isinstance(node.func, ast.Attribute) and node.func.attr in _TESTS and not arguments:
            return f"{_TESTS[node.func.attr]}.test({_expr(node.func.value)})"
        if isinstance(node.func, ast.Attribute):
            method = _METHODS.get(node.func.attr)
            if method is None:
                _fail(node, f"method .{node.func.attr}()")
            return f"{_expr(node.func.value)}.{method}({', '.join(arguments)})"
        name = getattr(node.func, "id", "")
        if name == "str" and len(arguments) == 1:
            return f"String({arguments[0]})"
        function = {"len": "enLen", "abs": "Math.abs", "sum": "enSum", "sorted": "enSorted", "reversed": "enReversed",
                    "max": "Math.max" if len(arguments) > 1 else "enMax",
                    "min": "Math.min" if len(arguments) > 1 else "enMin"}.get(name)
        if getattr(node.func, "id", "") in ("set", "list"):
            return f"new Set({', '.join(arguments)})" if node.func.id == "set" else f"Array.from({', '.join(arguments)})"
        if function is None:
            _fail(node, f"call to {ast.unparse(node.func)}")
        return f"{function}({', '.join(arguments)})"
    _fail(node, f"expression {type(node).__name__}")


def _block(statements, indent):
    pad, lines = "  " * indent, []
    for node in statements:
        if isinstance(node, ast.Return):
            lines.append(f"{pad}return {_expr(node.value) if node.value else 'null'};")
        elif isinstance(node, ast.Assign):
            if isinstance(node.targets[0], ast.Tuple):
                names = ", ".join(_name(t.id) for t in node.targets[0].elts)
                lines.append(f"{pad}[{names}] = [{', '.join(_expr(v) for v in node.value.elts)}];")
            else:
                lines.append(f"{pad}{_expr(node.targets[0])} = {_expr(node.value)};")
        elif isinstance(node, ast.AugAssign):
            operator = _BINARY.get(type(node.op)) or _fail(node, "augmented operator")
            lines.append(f"{pad}{_expr(node.target)} {operator}= {_expr(node.value)};")
        elif isinstance(node, ast.Expr):
            lines.append(f"{pad}{_expr(node.value)};")
        elif isinstance(node, ast.If):
            lines.append(f"{pad}if ({_expr(node.test)}) {{")
            lines += _block(node.body, indent + 1)
            orelse = node.orelse
            while len(orelse) == 1 and isinstance(orelse[0], ast.If):
                lines.append(f"{pad}}} else if ({_expr(orelse[0].test)}) {{")
                lines += _block(orelse[0].body, indent + 1)
                orelse = orelse[0].orelse
            if orelse:
                lines.append(f"{pad}}} else {{")
                lines += _block(orelse, indent + 1)
            lines.append(f"{pad}}}")
        elif isinstance(node, ast.While):
            lines.append(f"{pad}while ({_expr(node.test)}) {{")
            lines += _block(node.body, indent + 1) + [f"{pad}}}"]
        elif isinstance(node, ast.For):
            variable = _name(node.target.id)
            iterable = node.iter
            if isinstance(iterable, ast.Call) and getattr(iterable.func, "id", "") == "range":
                low, high = (("0", _expr(iterable.args[0])) if len(iterable.args) == 1
                             else (_expr(iterable.args[0]), _expr(iterable.args[1])))
                lines.append(f"{pad}for (let {variable} = {low}; {variable} < {high}; {variable}++) {{")
            else:
                lines.append(f"{pad}for (const {variable} of {_expr(iterable)}) {{")
            lines += _block(node.body, indent + 1) + [f"{pad}}}"]
        elif isinstance(node, ast.Pass):
            continue
        else:
            _fail(node, f"statement {type(node).__name__}")
    return lines


def _function(source):
    function = ast.parse(source).body[0]
    parameters = {argument.arg for argument in function.args.args}
    assigned = {t.id for n in ast.walk(function) if isinstance(n, ast.Assign) for target in n.targets
                for t in (target.elts if isinstance(target, ast.Tuple) else [target]) if isinstance(t, ast.Name)}
    declared = sorted(assigned - parameters)
    body = _block(function.body, 1)
    if declared:
        body.insert(0, f"  let {', '.join(_name(name) for name in declared)};")
    header = f"function {function.name}({', '.join(_name(p) for p in sorted(parameters, key=[a.arg for a in function.args.args].index))}) {{"
    return function.name, "\n".join([header, *body, "}"])


def recipe_javascript(spec, filename: str) -> str:
    stages = spec.stages or (spec,)
    if any(stage.family.value not in BY_KEY for stage in stages):
        raise CodeInEnglishError(filename, 1, "JavaScript pipelines support only recipe stages so far", kind="unsupported")
    try:
        functions = dict(_function(BY_KEY[stage.family.value].source) for stage in stages)
    except CodeInEnglishError as error:
        raise CodeInEnglishError(filename, 1, error.message, kind="unsupported") from error
    name, function = spec.function_name, "\n".join(functions.values())
    if len(spec.stages) > 1:
        chained = _name(spec.inputs[0].name)
        for stage in stages:
            chained = f"{stage.function_name}({chained})"
        function += f"\nfunction {name}({_name(spec.inputs[0].name)}) {{ return {chained}; }}"
    return runner_javascript(spec, function)


def runner_javascript(spec, function: str) -> str:
    """Wrap `function` (named spec.function_name) with input checks, example checking and JSON I/O."""
    name = spec.function_name
    names = [item.name for item in spec.inputs]
    checks = "\n".join(
        f"  if (!({_CHECKS[item.kind].format(f'input.{item.name}')})) throw new Error('input.{item.name} must be {item.kind}');"
        for item in spec.inputs)
    examples = json.dumps([{"input": e.input, "expected": e.expected} for e in spec.examples], ensure_ascii=False)
    call = f"{name}({', '.join(f'input.{n}' for n in names)})"
    return "\n".join((
        '"use strict";', "const fs = require('node:fs');", _PRELUDE + function,
        "function run(input) {", checks,
        f"  const result = {call};",
        "  // ponytail: exact-integer results only; BigInt if larger factorials/Fibonacci are needed",
        "  if (Number.isInteger(result) && !Number.isSafeInteger(result)) throw new Error('result exceeds the exact integer range');",
        "  return result;", "}",
        f"const examples = {examples};",
        "if (process.argv.includes('--check-examples')) {",
        "  for (const [index, example] of examples.entries()) {",
        "    const actual = run(example.input);",
        "    if (JSON.stringify(actual) !== JSON.stringify(example.expected)) {",
        "      console.error(`Example ${index + 1} failed: ${JSON.stringify(actual)}`);", "      process.exit(1);", "    }", "  }",
        "  console.log(`All ${examples.length} examples passed.`);",
        "} else {",
        "  console.log(JSON.stringify(run(JSON.parse(fs.readFileSync(0, 'utf8')))));", "}", ""))
