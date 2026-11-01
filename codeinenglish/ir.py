from __future__ import annotations
from dataclasses import dataclass, field
from typing import Union


@dataclass(frozen=True)
class Literal:
    value: str | int | float | bool | None


@dataclass(frozen=True)
class Name:
    identifier: str


@dataclass(frozen=True)
class Binary:
    left: "Expr"
    operator: str
    right: "Expr"


@dataclass(frozen=True)
class Compare:
    left: "Expr"
    operator: str
    right: "Expr"


@dataclass(frozen=True)
class Index:
    collection: "Expr"
    index: "Expr"


@dataclass(frozen=True)
class Contains:
    item: "Expr"
    collection: "Expr"


@dataclass(frozen=True)
class Attribute:
    value: "Expr"
    name: str


@dataclass(frozen=True)
class MethodCall:
    value: "Expr"
    name: str
    arguments: list["Expr"]


Expr = Union[Literal, Name, Binary, Compare, Index, Contains, Attribute, MethodCall]


@dataclass(frozen=True)
class Assign:
    name: str
    value: Expr


@dataclass(frozen=True)
class ReadInput:
    name: str
    prompt: str


@dataclass(frozen=True)
class Display:
    values: list[Expr]


@dataclass(frozen=True)
class If:
    condition: Expr
    body: list["Statement"]
    otherwise: list["Statement"] | None


@dataclass(frozen=True)
class CreateList:
    name: str


@dataclass(frozen=True)
class CreateDictionary:
    name: str


@dataclass(frozen=True)
class Append:
    collection: str
    value: Expr


@dataclass(frozen=True)
class SetItem:
    collection: str
    index: Expr
    value: Expr


@dataclass(frozen=True)
class ForEach:
    name: str
    collection: Expr
    body: list["Statement"]


@dataclass(frozen=True)
class While:
    condition: Expr
    body: list["Statement"]


@dataclass(frozen=True)
class Break:
    pass


@dataclass(frozen=True)
class Continue:
    pass


@dataclass(frozen=True)
class MethodDef:
    name: str
    parameters: list[str]
    body: list["Statement"]


@dataclass(frozen=True)
class ClassDef:
    name: str
    methods: list[MethodDef]
    parent: str | None = None


@dataclass(frozen=True)
class CreateInstance:
    class_name: str
    name: str
    arguments: list["Expr"] = field(default_factory=list)


@dataclass(frozen=True)
class SetAttribute:
    value: Expr
    name: str
    expression: Expr


@dataclass(frozen=True)
class Return:
    value: Expr


Statement = Union[
    Assign, ReadInput, Display, If, CreateList, CreateDictionary, Append,
    SetItem, ForEach, While, Break, Continue, ClassDef, MethodDef,
    CreateInstance, SetAttribute, Return, MethodCall
]


@dataclass(frozen=True)
class Program:
    statements: list[Statement]
