import ast

from .problem_recognizer import ProblemFamily, ProblemSpec


def _name(value, ctx=ast.Load):
    return ast.Name(id=value, ctx=ctx())


def _const(value):
    return ast.Constant(value=value)


def _call(function, *args, keywords=None):
    return ast.Call(func=function if isinstance(function, ast.expr) else _name(function), args=list(args), keywords=keywords or [])


def _attr(value, name):
    return ast.Attribute(value=value, attr=name, ctx=ast.Load())


def _assign(name, value):
    return ast.Assign(targets=[_name(name, ast.Store)], value=value)


def _return(value):
    return ast.Return(value=value)


def _function(name, parameters, body):
    return ast.FunctionDef(name=name, args=ast.arguments(posonlyargs=[], args=[ast.arg(arg=p) for p in parameters], kwonlyargs=[], kw_defaults=[], defaults=[]), body=body, decorator_list=[])


def _value(value):
    if isinstance(value, dict):
        return ast.Dict(keys=[_value(key) for key in value], values=[_value(item) for item in value.values()])
    if isinstance(value, (list, tuple)):
        return ast.List(elts=[_value(item) for item in value], ctx=ast.Load())
    return ast.Constant(value=value)


def _print_error(message):
    return ast.Expr(value=_call("print", _const(message), keywords=[ast.keyword(arg="file", value=_attr(_name("sys"), "stderr"))]))


def _two_sum(spec):
    nums, target = _name("nums"), _name("target")
    complement = ast.BinOp(left=target, op=ast.Sub(), right=_name("number"))
    body = [
        _assign("seen", ast.Dict(keys=[], values=[])),
        ast.For(target=_name("index", ast.Store), iter=_call("enumerate", nums), body=[
            _assign("number", _name("pair")),
        ], orelse=[]),
    ]
    # enumerate tuple unpack is represented by a tuple target.
    body[1].target = ast.Tuple(elts=[_name("index", ast.Store), _name("number", ast.Store)], ctx=ast.Store())
    body[1].body = [
        ast.If(test=ast.Compare(left=complement, ops=[ast.In()], comparators=[_name("seen")]), body=[
            _return(ast.Tuple(elts=[_Subscript(_name("seen"), complement), _name("index")], ctx=ast.Load()))
        ], orelse=[]),
        ast.If(test=ast.Compare(left=_name("number"), ops=[ast.NotIn()], comparators=[_name("seen")]), body=[
            ast.Assign(targets=[_Subscript(_name("seen"), _name("number"), ast.Store)], value=_name("index")),
        ], orelse=[]),
    ]
    body[2:] = [_return(_const(None))]
    if "one_solution_guaranteed" in spec.constraints:
        body[2:] = []
    return _function("two_sum", ["nums", "target"], body)


def _Subscript(value, index, ctx=ast.Load):
    return ast.Subscript(value=value, slice=index, ctx=ctx())


def _strategy(spec):
    family = spec.family
    if family == ProblemFamily.TWO_SUM:
        return _two_sum(spec)
    nums = _name("nums")
    if family == ProblemFamily.DUPLICATES:
        loop = ast.For(target=_name("number", ast.Store), iter=nums, body=[
            ast.If(test=ast.Compare(left=_name("number"), ops=[ast.In()], comparators=[_name("seen")]), body=[_return(_const(True))], orelse=[]),
            ast.Expr(value=_call(_attr(_name("seen"), "add"), _name("number"))),
        ], orelse=[])
        return _function("contains_duplicate", ["nums"], [_assign("seen", _call("set")), loop, _return(_const(False))])
    if family == ProblemFamily.FREQUENCIES:
        loop = ast.For(target=_name("number", ast.Store), iter=nums, body=[
                ast.If(test=ast.Compare(left=_name("number"), ops=[ast.In()], comparators=[_name("counts")]), body=[
                ast.AugAssign(target=_Subscript(_name("counts"), _name("number")), op=ast.Add(), value=_const(1))
            ], orelse=[ast.Assign(targets=[_Subscript(_name("counts"), _name("number"), ast.Store)], value=_const(1))]),
        ], orelse=[])
        return _function("count_frequencies", ["nums"], [_assign("counts", ast.Dict(keys=[], values=[])), loop, _return(_name("counts"))])
    if family in (ProblemFamily.MINIMUM, ProblemFamily.MAXIMUM):
        choose = "min" if family == ProblemFamily.MINIMUM else "max"
        return _function(spec.function_name, ["nums"], [ast.If(test=ast.UnaryOp(op=ast.Not(), operand=nums), body=[_return(_const(None))], orelse=[]), _return(_call(choose, nums))])
    if family == ProblemFamily.SUM:
        return _function("calculate_sum", ["nums"], [_return(_call("sum", nums))])
    if family == ProblemFamily.SORT_ASCENDING:
        return _function("sort_ascending", ["nums"], [_return(_call("sorted", nums))])
    if family == ProblemFamily.PALINDROME:
        text = _name("text")
        normalized = _call(_attr(text, "lower")) if "case_insensitive" in spec.constraints else text
        if "ignore_punctuation" in spec.constraints or "ignore_whitespace" in spec.constraints:
            conditions = []
            if "ignore_punctuation" in spec.constraints:
                category = _Subscript(_call(_attr(_name("unicodedata"), "category"), _name("character")), _const(0))
                conditions.append(ast.Compare(left=category, ops=[ast.NotEq()], comparators=[_const("P")]))
            if "ignore_whitespace" in spec.constraints:
                conditions.append(ast.UnaryOp(op=ast.Not(), operand=_call(_attr(_name("character"), "isspace"))))
            keep_character = conditions[0] if len(conditions) == 1 else ast.BoolOp(op=ast.And(), values=conditions)
            normalized = ast.ListComp(elt=_name("character"), generators=[ast.comprehension(
                target=_name("character", ast.Store), iter=normalized, ifs=[keep_character], is_async=0
            )])
        reversed_value = _Subscript(normalized, ast.Slice(lower=None, upper=None, step=ast.UnaryOp(op=ast.USub(), operand=_const(1))))
        return _function("is_palindrome", ["text"], [_return(ast.Compare(left=normalized, ops=[ast.Eq()], comparators=[reversed_value]))])
    if family == ProblemFamily.FIRST_UNIQUE_CHARACTER:
        count_key = _call(_attr(_name("character"), "lower")) if "case_insensitive" in spec.constraints else _name("character")
        result_key = _call(_attr(_name("character"), "lower")) if "case_insensitive" in spec.constraints else _name("character")
        count_loop = ast.For(target=_name("character", ast.Store), iter=_name("text"), body=[
            ast.If(test=ast.Compare(left=count_key, ops=[ast.In()], comparators=[_name("counts")]), body=[
                ast.AugAssign(target=_Subscript(_name("counts"), count_key, ast.Store), op=ast.Add(), value=_const(1))
            ], orelse=[ast.Assign(targets=[_Subscript(_name("counts"), count_key, ast.Store)], value=_const(1))]),
        ], orelse=[])
        unique_loop = ast.For(target=_name("character", ast.Store), iter=_name("text"), body=[
            ast.If(test=ast.Compare(left=_Subscript(_name("counts"), result_key), ops=[ast.Eq()], comparators=[_const(1)]), body=[_return(_name("character"))], orelse=[]),
        ], orelse=[])
        return _function("first_unique_character", ["text"], [_assign("counts", ast.Dict(keys=[], values=[])), count_loop, unique_loop, _return(_const(None))])
    if family == ProblemFamily.REVERSE_TEXT:
        reversed_text = _Subscript(_name("text"), ast.Slice(lower=None, upper=None, step=ast.UnaryOp(op=ast.USub(), operand=_const(1))))
        return _function("reverse_text", ["text"], [_return(reversed_text)])
    if family == ProblemFamily.MOVE_ZEROS:
        kept = ast.ListComp(elt=_name("number"), generators=[ast.comprehension(target=_name("number", ast.Store), iter=_name("nums"), ifs=[ast.Compare(left=_name("number"), ops=[ast.NotEq()], comparators=[_const(0)])], is_async=0)])
        zeroes = ast.ListComp(elt=_const(0), generators=[ast.comprehension(target=_name("number", ast.Store), iter=_name("nums"), ifs=[ast.Compare(left=_name("number"), ops=[ast.Eq()], comparators=[_const(0)])], is_async=0)])
        return _function("move_zeros", ["nums"], [_return(ast.BinOp(left=kept, op=ast.Add(), right=zeroes))])
    if family == ProblemFamily.MERGE_SORTED_LISTS:
        joined = ast.BinOp(left=_name("first"), op=ast.Add(), right=_name("second"))
        return _function("merge_sorted_lists", ["first", "second"], [_return(_call("sorted", joined))])
    if family == ProblemFamily.MAXIMUM_SUBARRAY_SUM:
        nums_value = _name("nums")
        body = [ast.If(test=ast.UnaryOp(op=ast.Not(), operand=nums_value), body=[_return(_const(0))], orelse=[]),
                _assign("current", _Subscript(_name("nums"), _const(0))), _assign("best", _name("current")),
                ast.For(target=_name("number", ast.Store), iter=_Subscript(_name("nums"), ast.Slice(lower=_const(1), upper=None, step=None)), body=[
                    _assign("current", _call("max", _name("number"), ast.BinOp(left=_name("current"), op=ast.Add(), right=_name("number")))),
                    _assign("best", _call("max", _name("best"), _name("current"))),
                ], orelse=[]), _return(_name("best"))]
        return _function("maximum_subarray_sum", ["nums"], body)
    if family == ProblemFamily.BALANCED_DELIMITERS:
        if "parentheses_only" in spec.constraints:
            opening, closing, pairs = "(", ")", {")": "("}
        elif "square_brackets_only" in spec.constraints:
            opening, closing, pairs = "[", "]", {"]": "["}
        else:
            opening, closing, pairs = "([{", ")]}", {")": "(", "]": "[", "}": "{"}
        loop_body = [
            ast.If(test=ast.Compare(left=_name("character"), ops=[ast.In()], comparators=[_const(opening)]), body=[ast.Expr(value=_call(_attr(_name("stack"), "append"), _name("character")))], orelse=[
                ast.If(test=ast.Compare(left=_name("character"), ops=[ast.In()], comparators=[_const(closing)]), body=[
                    ast.If(test=ast.BoolOp(op=ast.Or(), values=[ast.UnaryOp(op=ast.Not(), operand=_name("stack")), ast.Compare(left=_call(_attr(_name("stack"), "pop")), ops=[ast.NotEq()], comparators=[_Subscript(_name("pairs"), _name("character"))])]), body=[_return(_const(False))], orelse=[])
                ], orelse=[])
            ]),
        ]
        return _function("has_balanced_delimiters", ["text"], [_assign("stack", ast.List(elts=[], ctx=ast.Load())), _assign("pairs", _value(pairs)), ast.For(target=_name("character", ast.Store), iter=_name("text"), body=loop_body, orelse=[]), _return(ast.UnaryOp(op=ast.Not(), operand=_name("stack")))])
    if family == ProblemFamily.ANAGRAM:
        first, second = _name("first"), _name("second")
        if "case_insensitive" in spec.constraints:
            first, second = _call(_attr(first, "lower")), _call(_attr(second, "lower"))
        if "ignore_whitespace" in spec.constraints:
            first, second = _call(_attr(_const(""), "join"), _call(_attr(first, "split"))), _call(_attr(_const(""), "join"), _call(_attr(second, "split")))
        return _function("are_anagrams", ["first", "second"], [_return(ast.Compare(left=_call("sorted", first), ops=[ast.Eq()], comparators=[_call("sorted", second)]))])
    if family == ProblemFamily.BINARY_SEARCH:
        low, high = _name("low"), _name("high")
        middle = ast.BinOp(left=ast.BinOp(left=low, op=ast.Add(), right=high), op=ast.FloorDiv(), right=_const(2))
        cond = ast.Compare(left=low, ops=[ast.LtE()], comparators=[high])
        while_body = [
            _assign("middle", middle),
            ast.If(test=ast.Compare(left=_Subscript(nums, _name("middle")), ops=[ast.Eq()], comparators=[_name("target")]), body=[
                _assign("answer", _name("middle")),
                _assign("high", ast.BinOp(left=_name("middle"), op=ast.Sub(), right=_const(1))),
            ], orelse=[
                ast.If(test=ast.Compare(left=_Subscript(nums, _name("middle")), ops=[ast.Lt()], comparators=[_name("target")]), body=[_assign("low", ast.BinOp(left=_name("middle"), op=ast.Add(), right=_const(1)))], orelse=[_assign("high", ast.BinOp(left=_name("middle"), op=ast.Sub(), right=_const(1)))]),
            ]),
        ]
        return _function("binary_search", ["nums", "target"], [_assign("low", _const(0)), _assign("high", ast.BinOp(left=_call("len", nums), op=ast.Sub(), right=_const(1))), _assign("answer", _const(-1)), ast.While(test=cond, body=while_body, orelse=[]), _return(_name("answer"))])
    raise ValueError(f"no problem strategy for {family}")


def generate_problem_ast(spec: ProblemSpec) -> ast.Module:
    """Build a Python AST module for the recognized problem strategy."""
    function = _strategy(spec)
    expected_keys = [item.name for item in spec.inputs]
    example_values = [{"input": example.input, "expected": example.expected} for example in spec.examples]
    examples = _assign("EXAMPLES", _value(example_values))

    checker_loop = ast.For(
        target=_name("number", ast.Store),
        iter=_call("enumerate", _name("EXAMPLES"), keywords=[ast.keyword(arg="start", value=_const(1))]),
        body=[], orelse=[],
    )
    checker_loop.target = ast.Tuple(elts=[_name("number", ast.Store), _name("example", ast.Store)], ctx=ast.Store())
    actual = _call(function.name, keywords=[ast.keyword(arg=None, value=_Subscript(_name("example"), _const("input")))])
    checker_loop.body = [
        _assign("actual", actual),
        _assign("actual_json", _call(_attr(_name("json"), "loads"), _call(_attr(_name("json"), "dumps"), _name("actual")))),
        ast.If(test=ast.Compare(left=_name("actual_json"), ops=[ast.NotEq()], comparators=[_Subscript(_name("example"), _const("expected"))]), body=[
            ast.Expr(value=_call("print", _const("Example failed:"), _name("number"), _const("expected"), _Subscript(_name("example"), _const("expected")), _const("got"), _name("actual"), keywords=[ast.keyword(arg="file", value=_attr(_name("sys"), "stderr"))])),
            _return(_const(1)),
        ], orelse=[]),
    ]
    check_examples = _function("_check_examples", [], [
        ast.If(
            test=ast.UnaryOp(op=ast.Not(), operand=_name("EXAMPLES")),
            body=[_print_error("No examples were included; nothing was checked."), _return(_const(2))],
            orelse=[],
        ),
        checker_loop,
        ast.Expr(value=_call("print", _const(f"All {len(example_values)} examples passed."))),
        _return(_const(0)),
    ])

    # The parser needs a registered flag before parsing.
    parser_init = _assign("parser", _call(_attr(_name("argparse"), "ArgumentParser")))
    add_flag = ast.Expr(value=_call(_attr(_name("parser"), "add_argument"), _const("--check-examples"), keywords=[ast.keyword(arg="action", value=_const("store_true"))]))
    parse_args = _assign("arguments", _call(_attr(_name("parser"), "parse_args")))
    check_branch = ast.If(test=_attr(_name("arguments"), "check_examples"), body=[_return(_call("_check_examples"))], orelse=[])

    expected_key_list = _value(expected_keys)
    bad_object = ast.UnaryOp(op=ast.Not(), operand=_call("isinstance", _name("payload"), _name("dict")))
    bad_keys = ast.Compare(left=_call("set", _name("payload")), ops=[ast.NotEq()], comparators=[_call("set", expected_key_list)])
    body = [
        parser_init, add_flag, parse_args, check_branch,
        ast.Try(
            body=[_assign("payload", _call(_attr(_name("json"), "load"), _attr(_name("sys"), "stdin")))],
            handlers=[ast.ExceptHandler(type=_attr(_name("json"), "JSONDecodeError"), name=None, body=[_print_error("Input must be one valid JSON value."), _return(_const(2))])],
            orelse=[], finalbody=[],
        ),
        ast.If(test=bad_object, body=[_print_error("Input must be a JSON object."), _return(_const(2))], orelse=[]),
        ast.If(test=bad_keys, body=[_print_error("JSON input must contain exactly these keys: " + ", ".join(expected_keys)), _return(_const(2))], orelse=[]),
    ]
    for item in spec.inputs:
        value = _Subscript(_name("payload"), _const(item.name))
        if item.kind in ("integer_list", "sorted_integer_list"):
            valid = ast.BoolOp(op=ast.And(), values=[
                ast.Compare(left=_call("type", value), ops=[ast.Is()], comparators=[_name("list")]),
                _call("all", ast.GeneratorExp(elt=ast.Compare(left=_call("type", _name("item")), ops=[ast.Is()], comparators=[_name("int")]), generators=[ast.comprehension(target=_name("item", ast.Store), iter=value, ifs=[], is_async=0)])),
            ])
        elif item.kind == "integer":
            valid = ast.Compare(left=_call("type", value), ops=[ast.Is()], comparators=[_name("int")])
        elif item.kind == "string":
            valid = ast.Compare(left=_call("type", value), ops=[ast.Is()], comparators=[_name("str")])
        else:
            valid = _const(True)
        body.append(ast.If(test=ast.UnaryOp(op=ast.Not(), operand=valid), body=[_print_error(f"JSON field '{item.name}' has the wrong type; expected {item.kind}."), _return(_const(2))], orelse=[]))
        if item.kind == "sorted_integer_list":
            sorted_check = ast.Compare(left=value, ops=[ast.NotEq()], comparators=[_call("sorted", value)])
            body.append(ast.If(test=sorted_check, body=[_print_error(f"JSON field '{item.name}' must be sorted in ascending order."), _return(_const(2))], orelse=[]))

    invocation = _call(function.name, keywords=[ast.keyword(arg=None, value=_name("payload"))])
    body.extend([_assign("result", invocation), ast.Expr(value=_call("print", _call(_attr(_name("json"), "dumps"), _name("result"), keywords=[ast.keyword(arg="ensure_ascii", value=_const(False))]))), _return(_const(0))])
    main = _function("main", [], body)
    entry = ast.If(
        test=ast.Compare(left=_name("__name__"), ops=[ast.Eq()], comparators=[_const("__main__")]),
        body=[ast.Raise(exc=_call("SystemExit", _call("main")), cause=None)], orelse=[],
    )
    imports = ast.Import(names=[ast.alias(name=name) for name in ("argparse", "json", "sys", "unicodedata")])
    module = ast.Module(body=[imports, function, examples, check_examples, main, entry], type_ignores=[])
    return ast.fix_missing_locations(module)
