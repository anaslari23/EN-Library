from __future__ import annotations
import operator

from .errors import CodeInEnglishError
from .ir import (
    Append, Assign, Attribute, Binary, Break, ClassDef, Compare, Contains, Continue,
    CreateDictionary, CreateInstance, CreateList, Display, ForEach, FunctionCall, FunctionDef, If, Index,
    Literal, MethodCall, Name, Program, ReadInput, Return, SetAttribute, SetItem, While,
)

_BINARY = {"+": operator.add, "-": operator.sub, "*": operator.mul, "/": operator.truediv}
_COMPARE = {"==": operator.eq, "!=": operator.ne, ">": operator.gt, "<": operator.lt}


class _Return(Exception):
    def __init__(self, value):
        self.value = value


class _Break(Exception):
    pass


class _Continue(Exception):
    pass


class _Function:
    def __init__(self, name, parameters, body):
        self.name, self.parameters, self.body = name, parameters, body

    def call(self, args, scope, invoke_block, fail_fn):
        if len(args) != len(self.parameters):
            fail_fn(f"function '{self.name}' takes {len(self.parameters)} value(s) but got {len(args)}")
        frame = dict(scope)
        frame.update(dict(zip(self.parameters, args)))
        try:
            invoke_block(self.body, frame)
        except _Return as result:
            return result.value
        return None


class _Class:
    def __init__(self, name, methods, parent):
        self.name, self.methods, self.parent = name, methods, parent

    def find(self, name):
        """The (defining class, method) pair, searching this class then its parents."""
        cls = self
        while cls:
            if name in cls.methods:
                return cls, cls.methods[name]
            cls = cls.parent
        return None, None


class _Instance:
    def __init__(self, cls):
        self._cls = cls


class _Super:
    """What `super` means inside a method: the instance, looked up from the parent class."""
    def __init__(self, instance, parent):
        self.instance, self.parent = instance, parent


def run(program: Program, read=input, write=print, filename: str = "<string>", scope: dict | None = None) -> dict:
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
            if isinstance(target, (_Instance, _Super)):
                return invoke(target, node.name, args)
            return guard(lambda: getattr(target, node.name)(*args))
        if isinstance(node, FunctionCall):
            target = scope.get(node.name)
            if not isinstance(target, _Function):
                fail(f"'{node.name}' is not a function")
            args = [expr(argument, scope) for argument in node.arguments]
            return target.call(args, scope, block, fail)
        fail(f"unsupported expression {type(node).__name__}")

    def invoke(target, name, args):
        instance, start = (target.instance, target.parent) if isinstance(target, _Super) else (target, target._cls)
        if isinstance(target, _Super) and name == "init":
            name = "__init__"
        owner, method = start.find(name) if start else (None, None)
        if method is None:
            fail(f"no method '{name}'")
        if len(args) != len(method.parameters):
            fail(f"{'the constructor' if name == '__init__' else repr(name)} takes {len(method.parameters)} value(s) but got {len(args)}")
        frame = dict(zip(method.parameters, args), self=instance)
        if owner.parent:
            frame["super"] = _Super(instance, owner.parent)
        try:
            block(method.body, frame)
        except _Return as result:
            return result.value
        return None

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
                    try:
                        block(node.body, scope)
                    except _Continue:
                        continue
                    except _Break:
                        break
            elif isinstance(node, While):
                while expr(node.condition, scope):
                    try:
                        block(node.body, scope)
                    except _Continue:
                        continue
                    except _Break:
                        break
            elif isinstance(node, Break):
                raise _Break()
            elif isinstance(node, Continue):
                raise _Continue()
            elif isinstance(node, ClassDef):
                scope[node.name] = _Class(node.name, {method.name: method for method in node.methods}, scope.get(node.parent))
            elif isinstance(node, CreateInstance):
                instance = _Instance(scope[node.class_name])
                arguments = [expr(argument, scope) for argument in node.arguments]
                if instance._cls.find("__init__")[1] is not None:
                    invoke(instance, "__init__", arguments)
                elif arguments:
                    fail(f"'{node.class_name}' has no constructor, so it takes no values")
                scope[node.name] = instance
            elif isinstance(node, SetAttribute):
                setattr(expr(node.value, scope), node.name, expr(node.expression, scope))
            elif isinstance(node, Return):
                raise _Return(expr(node.value, scope))
            elif isinstance(node, FunctionDef):
                scope[node.name] = _Function(node.name, node.parameters, node.body)
            elif isinstance(node, (MethodCall, FunctionCall)):
                expr(node, scope)
            else:
                fail(f"unsupported statement {type(node).__name__}")

    if scope is None:
        scope = {}
    block(program.statements, scope)
    return scope
