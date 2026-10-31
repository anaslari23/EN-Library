"""C backend for the core language: whole numbers, text, lists of numbers, loops, conditions and `show`.

Numbers are 64-bit (`long long`); text is `char *`. Anything else (classes, dictionaries, input, division,
joining text) is refused with a clear message instead of producing C that behaves differently.
"""
from __future__ import annotations

import json

from .errors import CodeInEnglishError
from .ir import Append, Assign, Binary, Compare, CreateList, Display, ForEach, If, Literal, Name, Program

_LIMIT = 1000  # items per list


def _fail(filename, message):
    raise CodeInEnglishError(filename, 1, message, kind="unsupported")


class _Generator:
    def __init__(self, filename):
        self.filename = filename
        self.types = {}  # name -> "i" number, "s" text, "l" list of numbers
        self.loops = 0

    def kind(self, node):
        if isinstance(node, Literal):
            if isinstance(node.value, bool) or node.value is None or isinstance(node.value, float):
                _fail(self.filename, "C supports whole numbers and text; true, false, none and decimals are not available")
            return "i" if isinstance(node.value, int) else "s"
        if isinstance(node, Name):
            if self.types.get(node.identifier) in ("i", "s"):
                return self.types[node.identifier]
            _fail(self.filename, f"C cannot use {node.identifier!r} here (a list, or not set yet)")
        if isinstance(node, Binary):
            if node.operator == "/":
                _fail(self.filename, "C output does not support division yet")
            if self.kind(node.left) != "i" or self.kind(node.right) != "i":
                _fail(self.filename, "C output does not join or repeat text; use numbers with plus, minus and times")
            return "i"
        _fail(self.filename, f"C output supports the core language only (not {type(node).__name__})")

    def expr(self, node):
        if isinstance(node, Literal):
            return f"{node.value}LL" if isinstance(node.value, int) else json.dumps(node.value, ensure_ascii=True)
        if isinstance(node, Name):
            return f"e_{node.identifier}"
        return f"({self.expr(node.left)} {node.operator} {self.expr(node.right)})"

    def condition(self, node):
        if not isinstance(node, Compare):
            _fail(self.filename, "C output supports comparisons only in conditions")
        left, right = self.kind(node.left), self.kind(node.right)
        if left != right:
            _fail(self.filename, "C cannot compare a number with text")
        a, b = self.expr(node.left), self.expr(node.right)
        if left == "s":
            if node.operator not in ("==", "!="):
                _fail(self.filename, "C compares text with 'is' and 'is not' only")
            return f"strcmp({a}, {b}) {node.operator} 0"
        return f"{a} {node.operator} {b}"

    def scan(self, statements):
        """Learn each name's type in program order (C needs every variable declared first)."""
        for node in statements:
            if isinstance(node, Assign):
                self.types.setdefault(node.name, self.kind(node.value))
            elif isinstance(node, CreateList):
                self.types[node.name] = "l"
            elif isinstance(node, ForEach):
                self.types[node.name] = "i"
                self.scan(node.body)
            elif isinstance(node, If):
                self.scan(node.body)
                self.scan(node.otherwise or [])

    def block(self, statements, indent):
        pad, lines = "    " * indent, []
        for node in statements:
            if isinstance(node, Assign):
                if node.value != Name(node.name):  # `set x to x` changes nothing (and C warns about it)
                    lines.append(f"{pad}e_{node.name} = {self.expr(node.value)};")
            elif isinstance(node, CreateList):
                lines.append(f"{pad}n_e_{node.name} = 0;")
            elif isinstance(node, Append):
                if self.types.get(node.collection) != "l" or self.kind(node.value) != "i":
                    _fail(self.filename, "C lists hold whole numbers only")
                lines.append(f"{pad}PUSH(e_{node.collection}, n_e_{node.collection}, {self.expr(node.value)});")
            elif isinstance(node, Display):
                formats = "".join("%s" if self.kind(value) == "s" else "%lld" for value in node.values)
                lines.append(f'{pad}printf("{formats}\\n", {", ".join(self.expr(value) for value in node.values)});')
            elif isinstance(node, If):
                lines.append(f"{pad}if ({self.condition(node.condition)}) {{")
                lines += self.block(node.body, indent + 1)
                if node.otherwise is not None:
                    lines.append(f"{pad}}} else {{")
                    lines += self.block(node.otherwise, indent + 1)
                lines.append(f"{pad}}}")
            elif isinstance(node, ForEach):
                if not isinstance(node.collection, Name) or self.types.get(node.collection.identifier) != "l":
                    _fail(self.filename, "C loops go over lists of numbers")
                self.loops += 1
                counter, source = f"k{self.loops}", node.collection.identifier
                lines.append(f"{pad}for (int {counter} = 0; {counter} < n_e_{source}; {counter}++) {{")
                lines.append(f"{pad}    e_{node.name} = e_{source}[{counter}];")
                lines += self.block(node.body, indent + 1)
                lines.append(f"{pad}}}")
            else:
                _fail(self.filename, f"C output supports the core language only (not {type(node).__name__})")
        return lines


def program_c(program: Program, filename: str) -> str:
    generator = _Generator(filename)
    generator.scan(program.statements)
    body = generator.block(program.statements, 1)
    declarations = [f"    long long e_{name}[{_LIMIT}]; int n_e_{name};" if kind == "l"
                    else f"    {'char *' if kind == 's' else 'long long '}e_{name};" for name, kind in generator.types.items()]
    quiet = [f"    (void)e_{name};" + (f" (void)n_e_{name};" if kind == "l" else "") for name, kind in generator.types.items()]  # no warnings for names that are set but never shown
    header = ["#include <stdio.h>", "#include <stdlib.h>", "#include <string.h>",
              '#pragma GCC diagnostic ignored "-Wtautological-compare"  /* a program may compare a name with itself */',
              f'#define PUSH(a, n, v) do {{ if ((n) >= {_LIMIT}) {{ fputs("list too long\\n", stderr); exit(1); }} (a)[(n)++] = (v); }} while (0)',
              "int main(void) {"]
    return "\n".join([*header, *declarations, *quiet, *body, "    return 0;", "}", ""])
