import operator

from .errors import CodeInEnglishError
from .ir import (
    Append, Assign, Attribute, Binary, ClassDef, Compare, Contains, CreateDictionary, CreateInstance,
    CreateList, Display, ForEach, If, Index, Literal, MethodCall, Name, Program, ReadInput, Return,
    SetAttribute, SetItem,
)

_BINARY = {"+": operator.add, "-": operator.sub, "*": operator.mul, "/": operator.truediv}
_COMPARE = {"==": operator.eq, "!=": operator.ne, ">": operator.gt, "<": operator.lt}


class _Return(Exception):
    def __init__(self, value):
        self.value = value


class _Instance:
    def __init__(self, cls):
        self._cls = cls


def run(program: Program, read=input, write=print, filename: str = "<string>") -> None:
    """Execute a program IR directly; the reference semantics shared with the generators."""

    def fail(message):
        raise CodeInEnglishError(filename, 1, message, kind="runtime")

    def expr(node, scope):
        if isinstance(node, Literal):
            return node.value
        if isinstance(node, Name):
            if node.identifier not in scope:
                fail(f"'{node.identifier}' is not defined")
            return scope[node.identifier]
        if isinstance(node, Binary):
            return guard(lambda: _BINARY[node.operator](expr(node.left, scope), expr(node.right, scope)))
        if isinstance(node, Compare):
            return guard(lambda: _COMPARE[node.operator](expr(node.left, scope), expr(node.right, scope)))
        if isinstance(node, Index):
            return guard(lambda: expr(node.collection, scope)[expr(node.index, scope)])
        if isinstance(node, Contains):
            return guard(lambda: expr(node.item, scope) in expr(node.collection, scope))
        if isinstance(node, Attribute):
            target = expr(node.value, scope)
            if not isinstance(target, _Instance) or node.name not in vars(target):
                fail(f"no field '{node.name}'")
            return vars(target)[node.name]
        if isinstance(node, MethodCall):
            target = expr(node.value, scope)
            args = [expr(argument, scope) for argument in node.arguments]
            if isinstance(target, _Instance):
                method = target._cls.get(node.name)
                if method is None:
                    fail(f"no method '{node.name}'")
                frame = dict(zip(method.parameters, args), self=target)
                try:
                    block(method.body, frame)
                except _Return as result:
                    return result.value
                return None
            return guard(lambda: getattr(target, node.name)(*args))
        fail(f"unsupported expression {type(node).__name__}")

    def guard(operation):
        try:
            return operation()
        except (ArithmeticError, LookupError, TypeError, AttributeError) as error:
            fail(str(error))

    def block(statements, scope):
        for node in statements:
            if isinstance(node, Assign):
                scope[node.name] = expr(node.value, scope)
            elif isinstance(node, ReadInput):
                scope[node.name] = read(f"Your {node.prompt}: ")
            elif isinstance(node, Display):
                values = [expr(value, scope) for value in node.values]
                write(values[0] if len(values) == 1 else "".join(str(value) for value in values))
            elif isinstance(node, If):
                branch = node.body if expr(node.condition, scope) else node.otherwise or []
                block(branch, scope)
            elif isinstance(node, CreateList):
                scope[node.name] = []
            elif isinstance(node, CreateDictionary):
                scope[node.name] = {}
            elif isinstance(node, Append):
                scope[node.collection].append(expr(node.value, scope))
            elif isinstance(node, SetItem):
                collection, index, value = scope[node.collection], expr(node.index, scope), expr(node.value, scope)
                guard(lambda: collection.__setitem__(index, value))
            elif isinstance(node, ForEach):
                for item in guard(lambda: list(expr(node.collection, scope))):
                    scope[node.name] = item
                    block(node.body, scope)
            elif isinstance(node, ClassDef):
                scope[node.name] = {method.name: method for method in node.methods}
            elif isinstance(node, CreateInstance):
                scope[node.name] = _Instance(scope[node.class_name])
            elif isinstance(node, SetAttribute):
                setattr(expr(node.value, scope), node.name, expr(node.expression, scope))
            elif isinstance(node, Return):
                raise _Return(expr(node.value, scope))
            elif isinstance(node, MethodCall):
                expr(node, scope)
            else:
                fail(f"unsupported statement {type(node).__name__}")

    block(program.statements, {})
