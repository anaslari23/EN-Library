import ast

from .errors import CodeInEnglishError
from .ir import (
    Append,
    Attribute,
    Assign,
    Binary,
    Compare,
    Contains,
    ClassDef as ClassDefinition,
    CreateDictionary,
    CreateInstance,
    CreateList,
    Display,
    Expr,
    ForEach,
    If,
    Index,
    Literal,
    MethodCall,
    MethodDef,
    Name,
    Program,
    ReadInput,
    Return,
    SetAttribute,
    SetItem,
    Statement,
)


_BINARY_OPERATORS = {
    "+": ast.Add,
    "-": ast.Sub,
    "*": ast.Mult,
    "/": ast.Div,
}
_COMPARISON_OPERATORS = {
    "==": ast.Eq,
    "!=": ast.NotEq,
    ">": ast.Gt,
    "<": ast.Lt,
}


def _expression(node: Expr) -> ast.expr:
    if isinstance(node, Literal):
        return ast.Constant(value=node.value)
    if isinstance(node, Name):
        return ast.Name(id=node.identifier, ctx=ast.Load())
    if isinstance(node, Binary):
        return ast.BinOp(
            left=_expression(node.left),
            op=_BINARY_OPERATORS[node.operator](),
            right=_expression(node.right),
        )
    if isinstance(node, Compare):
        return ast.Compare(
            left=_expression(node.left),
            ops=[_COMPARISON_OPERATORS[node.operator]()],
            comparators=[_expression(node.right)],
        )
    if isinstance(node, Index):
        return ast.Subscript(
            value=_expression(node.collection),
            slice=_expression(node.index),
            ctx=ast.Load(),
        )
    if isinstance(node, Contains):
        return ast.Compare(
            left=_expression(node.item),
            ops=[ast.In()],
            comparators=[_expression(node.collection)],
        )
    if isinstance(node, Attribute):
        return ast.Attribute(value=_expression(node.value), attr=node.name, ctx=ast.Load())
    if isinstance(node, MethodCall):
        return ast.Call(
            func=ast.Attribute(value=_expression(node.value), attr=node.name, ctx=ast.Load()),
            args=[_expression(argument) for argument in node.arguments],
            keywords=[],
        )
    raise TypeError(f"unsupported expression IR node: {type(node).__name__}")


def _call(name: str, arguments: list[ast.expr]) -> ast.Call:
    return ast.Call(func=ast.Name(id=name, ctx=ast.Load()), args=arguments, keywords=[])


def _statements(nodes: list[Statement]) -> list[ast.stmt]:
    result: list[ast.stmt] = []
    for node in nodes:
        if isinstance(node, Assign):
            result.append(
                ast.Assign(
                    targets=[ast.Name(id=node.name, ctx=ast.Store())],
                    value=_expression(node.value),
                )
            )
        elif isinstance(node, ReadInput):
            prompt = ast.Constant(value=f"Your {node.prompt}: ")
            result.append(
                ast.Assign(
                    targets=[ast.Name(id=node.name, ctx=ast.Store())],
                    value=_call("input", [prompt]),
                )
            )
        elif isinstance(node, Display):
            if len(node.values) == 1:
                value = _expression(node.values[0])
            else:
                value = ast.BinOp(
                    left=_call("str", [_expression(node.values[0])]),
                    op=ast.Add(),
                    right=_call("str", [_expression(node.values[1])]),
                )
                for part in node.values[2:]:
                    value = ast.BinOp(left=value, op=ast.Add(), right=_call("str", [_expression(part)]))
            result.append(ast.Expr(value=_call("print", [value])))
        elif isinstance(node, If):
            otherwise = _statements(node.otherwise) if node.otherwise is not None else []
            result.append(
                ast.If(
                    test=_expression(node.condition),
                    body=_statements(node.body) or [ast.Pass()],
                    orelse=otherwise or ([ast.Pass()] if node.otherwise is not None else []),
                )
            )
        elif isinstance(node, CreateList):
            result.append(
                ast.Assign(
                    targets=[ast.Name(id=node.name, ctx=ast.Store())],
                    value=ast.List(elts=[], ctx=ast.Load()),
                )
            )
        elif isinstance(node, CreateDictionary):
            result.append(
                ast.Assign(
                    targets=[ast.Name(id=node.name, ctx=ast.Store())],
                    value=ast.Dict(keys=[], values=[]),
                )
            )
        elif isinstance(node, Append):
            result.append(
                ast.Expr(
                    value=ast.Call(
                        func=ast.Attribute(
                            value=ast.Name(id=node.collection, ctx=ast.Load()),
                            attr="append",
                            ctx=ast.Load(),
                        ),
                        args=[_expression(node.value)],
                        keywords=[],
                    )
                )
            )
        elif isinstance(node, SetItem):
            result.append(
                ast.Assign(
                    targets=[
                        ast.Subscript(
                            value=ast.Name(id=node.collection, ctx=ast.Load()),
                            slice=_expression(node.index),
                            ctx=ast.Store(),
                        )
                    ],
                    value=_expression(node.value),
                )
            )
        elif isinstance(node, ForEach):
            result.append(
                ast.For(
                    target=ast.Name(id=node.name, ctx=ast.Store()),
                    iter=_expression(node.collection),
                    body=_statements(node.body) or [ast.Pass()],
                    orelse=[],
                    type_comment=None,
                )
            )
        elif isinstance(node, ClassDefinition):
            methods = []
            for method in node.methods:
                methods.append(ast.FunctionDef(
                    name=method.name,
                    args=ast.arguments(
                        posonlyargs=[],
                        args=[ast.arg(arg="self")] + [ast.arg(arg=parameter) for parameter in method.parameters],
                        kwonlyargs=[], kw_defaults=[], defaults=[],
                    ),
                    body=_statements(method.body) or [ast.Pass()],
                    decorator_list=[],
                ))
            result.append(ast.ClassDef(name=node.name, bases=[], keywords=[], body=methods or [ast.Pass()], decorator_list=[]))
        elif isinstance(node, CreateInstance):
            result.append(ast.Assign(
                targets=[ast.Name(id=node.name, ctx=ast.Store())],
                value=_call(node.class_name, []),
            ))
        elif isinstance(node, SetAttribute):
            result.append(ast.Assign(
                targets=[ast.Attribute(value=_expression(node.value), attr=node.name, ctx=ast.Store())],
                value=_expression(node.expression),
            ))
        elif isinstance(node, Return):
            result.append(ast.Return(value=_expression(node.value)))
        elif isinstance(node, MethodCall):
            result.append(ast.Expr(value=_expression(node)))
        else:
            raise TypeError(f"unsupported statement IR node: {type(node).__name__}")
    return result


def generate_python(program: Program) -> str:
    """Generate and syntax-check Python source from a program IR."""
    module = ast.fix_missing_locations(ast.Module(body=_statements(program.statements), type_ignores=[]))
    return generate_python_ast(module)


def generate_python_ast(module: ast.Module, comments: list[str] | None = None) -> str:
    """Render and syntax-check a Python AST module."""
    module = ast.fix_missing_locations(module)
    source = ast.unparse(module)
    if comments:
        source = "\n".join(f"# {line}" if line else "#" for line in comments) + "\n\n" + source
    try:
        ast.parse(source)
    except SyntaxError as error:
        raise CodeInEnglishError("<generated>", error.lineno or 1, "generated Python is invalid") from error
    return source
