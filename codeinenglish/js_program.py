"""JavaScript backend for whole instruction programs: classes, lists, loops, conditions, input and output."""

from __future__ import annotations

import json

from .errors import CodeInEnglishError
from .ir import (
    Append, Assign, Attribute, Binary, Break, ClassDef, Compare, Contains, Continue,
    CreateDictionary, CreateInstance, CreateList, Display, ForEach, FunctionCall, FunctionDef, If, Index,
    Literal, MethodCall, Name, Program, ReadInput, Return, SetAttribute, SetItem, While,
)

# Helpers keep Python's behaviour where plain JavaScript differs: strict types, errors for bad index/key/field,
# Python-style printing, and list/dictionary membership.
_PRELUDE = r"""'use strict';
const fs = require('node:fs');
let enInputLines = null;
function enInput(prompt) {
  process.stdout.write(prompt);
  if (enInputLines === null) enInputLines = fs.readFileSync(0, 'utf8').split('\n');
  if (!enInputLines.length || (enInputLines.length === 1 && enInputLines[0] === '')) throw new Error('EOF when reading a line');
  return enInputLines.shift();
}
function enRepr(v) { return typeof v === 'string' ? "'" + v.replace(/\\/g, '\\\\').replace(/'/g, "\\'") + "'" : enStr(v, true); }
function enStr(v, nested) {
  if (v === null || v === undefined) return 'None';
  if (v === true) return 'True';
  if (v === false) return 'False';
  if (Array.isArray(v)) return '[' + v.map(enRepr).join(', ') + ']';
  if (v instanceof Map) return '{' + [...v].map(([k, x]) => enRepr(k) + ': ' + enRepr(x)).join(', ') + '}';
  if (typeof v === 'object') return '<' + v.constructor.name.replace(/^en_/, '') + ' object>';
  return String(v);
}
function enNumbers(a, b, op) { if (typeof a !== 'number' || typeof b !== 'number') throw new TypeError(`unsupported operand types for ${op}`); }
function enAdd(a, b) {
  if (typeof a === 'number' && typeof b === 'number') return a + b;
  if (typeof a === 'string' && typeof b === 'string') return a + b;
  if (Array.isArray(a) && Array.isArray(b)) return a.concat(b);
  throw new TypeError('unsupported operand types for +');
}
function enSub(a, b) { enNumbers(a, b, '-'); return a - b; }
function enMul(a, b) {
  if (typeof a === 'number' && typeof b === 'number') return a * b;
  if ((typeof a === 'string' || Array.isArray(a)) && typeof b === 'number') return a.length * Math.max(b, 0) === 0 ? (typeof a === 'string' ? '' : []) : (typeof a === 'string' ? a.repeat(b) : Array.from({length: b}, () => a).flat());
  throw new TypeError('unsupported operand types for *');
}
function enDiv(a, b) { enNumbers(a, b, '/'); if (b === 0) throw new Error('division by zero'); return a / b; }
function enCompare(a, b, op) {
  if (typeof a !== typeof b) throw new TypeError(`'${op}' not supported between these types`);
  return op === '>' ? a > b : a < b;
}
function enGet(c, i) {
  if (c instanceof Map) { if (!c.has(i)) throw new Error('key not found: ' + enRepr(i)); return c.get(i); }
  if (typeof c === 'string' || Array.isArray(c)) {
    const at = i < 0 ? c.length + i : i;
    if (!Number.isInteger(at) || at < 0 || at >= c.length) throw new Error('index out of range');
    return c[at];
  }
  throw new TypeError('value is not indexable');
}
function enSet(c, i, v) {
  if (c instanceof Map) { c.set(i, v); return; }
  enGet(c, i);
  c[i < 0 ? c.length + i : i] = v;
}
function enIn(item, c) { return c instanceof Map ? c.has(item) : c.includes(item); }
function enField(o, name) { if (!(name in o)) throw new Error('no field ' + name); return o[name]; }
function enNew(cls, args) {
  const o = new cls();
  if (typeof o.__init__ === 'function') {
    if (o.__init__.length !== args.length) throw new Error(`the constructor takes ${o.__init__.length} value(s) but got ${args.length}`);
    o.__init__(...args);
  } else if (args.length) throw new Error(`'${cls.name.replace(/^en_/, '')}' has no constructor, so it takes no values`);
  return o;
}
"""


def _fail(filename, message):
    raise CodeInEnglishError(filename, 1, message, kind="unsupported")


class _Generator:
    def __init__(self, filename):
        self.filename = filename

    def expr(self, node):
        if isinstance(node, Literal):
            if isinstance(node.value, float) or (type(node.value) is int and abs(node.value) > 2**53 - 1):
                _fail(self.filename, "JavaScript currently supports only exact integer, text, boolean, and null literals")
            return json.dumps(node.value, ensure_ascii=False)
        if isinstance(node, Name):
            return "this" if node.identifier == "self" else f"en_{node.identifier}"
        if isinstance(node, Binary):
            left, right = self.expr(node.left), self.expr(node.right)
            helper = {"+": "enAdd", "-": "enSub", "*": "enMul", "/": "enDiv"}[node.operator]
            return f"{helper}({left}, {right})"
        if isinstance(node, Compare):
            left, right = self.expr(node.left), self.expr(node.right)
            if node.operator in ("==", "!="):
                return f"({left} {'===' if node.operator == '==' else '!=='} {right})"
            return f"enCompare({left}, {right}, '{node.operator}')"
        if isinstance(node, Index):
            return f"enGet({self.expr(node.collection)}, {self.expr(node.index)})"
        if isinstance(node, Contains):
            return f"enIn({self.expr(node.item)}, {self.expr(node.collection)})"
        if isinstance(node, Attribute):
            return f"enField({self.expr(node.value)}, {json.dumps(node.name)})"
        if isinstance(node, MethodCall):
            arguments = ", ".join(self.expr(argument) for argument in node.arguments)
            if node.value == Name("super"):
                return f"super.{'__init__' if node.name == 'init' else node.name}({arguments})"
            return f"{self.expr(node.value)}.{node.name}({arguments})"
        if isinstance(node, FunctionCall):
            arguments = ", ".join(self.expr(argument) for argument in node.arguments)
            return f"en_{node.name}({arguments})"
        _fail(self.filename, f"JavaScript does not yet support {type(node).__name__} expressions")

    def declared(self, statements):
        """Names assigned anywhere in this scope; declared up front because Python scopes are function-wide."""
        names = set()
        for node in statements:
            if isinstance(node, (Assign, ReadInput, CreateList, CreateDictionary, CreateInstance)):
                names.add(node.name)
            elif isinstance(node, ForEach):
                names.add(node.name)
                names |= self.declared(node.body)
            elif isinstance(node, While):
                names |= self.declared(node.body)
            elif isinstance(node, If):
                names |= self.declared(node.body) | self.declared(node.otherwise or [])
        return names

    def block(self, statements, indent):
        pad, lines = "  " * indent, []
        for node in statements:
            if isinstance(node, Assign):
                lines.append(f"{pad}en_{node.name} = {self.expr(node.value)};")
            elif isinstance(node, ReadInput):
                lines.append(f"{pad}en_{node.name} = enInput({json.dumps(f'Your {node.prompt}: ')});")
            elif isinstance(node, Display):
                if not node.values:
                    _fail(self.filename, "JavaScript display needs a value")
                lines.append(f"{pad}console.log({' + '.join(f'enStr({self.expr(value)})' for value in node.values)});")
            elif isinstance(node, If):
                lines.append(f"{pad}if ({self.expr(node.condition)}) {{")
                lines += self.block(node.body, indent + 1)
                if node.otherwise is not None:
                    lines.append(f"{pad}}} else {{")
                    lines += self.block(node.otherwise, indent + 1)
                lines.append(f"{pad}}}")
            elif isinstance(node, CreateList):
                lines.append(f"{pad}en_{node.name} = [];")
            elif isinstance(node, CreateDictionary):
                lines.append(f"{pad}en_{node.name} = new Map();")
            elif isinstance(node, Append):
                lines.append(f"{pad}en_{node.collection}.push({self.expr(node.value)});")
            elif isinstance(node, SetItem):
                lines.append(f"{pad}enSet(en_{node.collection}, {self.expr(node.index)}, {self.expr(node.value)});")
            elif isinstance(node, ForEach):
                lines.append(f"{pad}for (const en__item of {self.expr(node.collection)}) {{")
                lines.append(f"{pad}  en_{node.name} = en__item;")
                lines += self.block(node.body, indent + 1)
                lines.append(f"{pad}}}")
            elif isinstance(node, While):
                lines.append(f"{pad}while ({self.expr(node.condition)}) {{")
                lines += self.block(node.body, indent + 1)
                lines.append(f"{pad}}}")
            elif isinstance(node, Break):
                lines.append(f"{pad}break;")
            elif isinstance(node, Continue):
                lines.append(f"{pad}continue;")
            elif isinstance(node, ClassDef):
                lines += self.class_def(node, indent)
            elif isinstance(node, CreateInstance):
                arguments = ", ".join(self.expr(argument) for argument in node.arguments)
                lines.append(f"{pad}en_{node.name} = enNew(en_{node.class_name}, [{arguments}]);")
            elif isinstance(node, SetAttribute):
                lines.append(f"{pad}{self.expr(node.value)}.{node.name} = {self.expr(node.expression)};")
            elif isinstance(node, Return):
                lines.append(f"{pad}return {self.expr(node.value)};")
            elif isinstance(node, FunctionDef):
                parameters = ", ".join(f"en_{param}" for param in node.parameters)
                lines.append(f"{pad}function en_{node.name}({parameters}) {{")
                local = sorted(self.declared(node.body) - set(node.parameters))
                if local:
                    lines.append(f"{pad}  let {', '.join(f'en_{name}' for name in local)};")
                lines += self.block(node.body, indent + 1)
                lines.append(f"{pad}  return null;")
                lines.append(f"{pad}}}")
            elif isinstance(node, (MethodCall, FunctionCall)):
                lines.append(f"{pad}{self.expr(node)};")
            else:
                _fail(self.filename, f"JavaScript does not yet support {type(node).__name__} instructions")
        return lines

    def class_def(self, node, indent):
        pad = "  " * indent
        parent = f" extends en_{node.parent}" if node.parent else ""
        lines = [f"{pad}class en_{node.name}{parent} {{"]
        for method in node.methods:
            if method.name == "constructor":
                _fail(self.filename, "a method cannot be named 'constructor' in JavaScript output")
            parameters = ", ".join(f"en_{parameter}" for parameter in method.parameters)
            lines.append(f"{pad}  {method.name}({parameters}) {{")
            local = sorted(self.declared(method.body) - set(method.parameters))
            if local:
                lines.append(f"{pad}    let {', '.join(f'en_{name}' for name in local)};")
            lines += self.block(method.body, indent + 2)
            lines.append(f"{pad}    return null;")
            lines.append(f"{pad}  }}")
        lines.append(f"{pad}}}")
        return lines


def program_javascript(program: Program, filename: str) -> str:
    generator = _Generator(filename)
    names = sorted(generator.declared(program.statements))
    body = generator.block(program.statements, 1)
    declarations = [f"  let {', '.join(f'en_{name}' for name in names)};"] if names else []
    return "\n".join([_PRELUDE + "try {", *declarations, *body,
                      "} catch (error) {", "  console.error(error.message);", "  process.exit(1);", "}", ""])


program_js = program_javascript
