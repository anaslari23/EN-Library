"""Small, explicit JavaScript backend for the shared EN semantic forms."""

import json

from .errors import CodeInEnglishError
from .ir import Assign, Display, Literal, Name, Program
from .problem_recognizer import ProblemSpec
from .recipes import BY_KEY
from .transpile_js import recipe_javascript


def _expression(node, filename: str) -> str:
    if isinstance(node, Literal):
        if isinstance(node.value, float) or (type(node.value) is int and abs(node.value) > 2**53 - 1):
            raise CodeInEnglishError(filename, 1, "JavaScript currently supports only exact integer, text, boolean, and null literals", kind="unsupported")
        return json.dumps(node.value, ensure_ascii=False)
    if isinstance(node, Name):
        return f"en_{node.identifier}"
    raise CodeInEnglishError(filename, 1, f"JavaScript does not yet support {type(node).__name__} expressions", kind="unsupported")


def generate_javascript(program: Program | ProblemSpec, filename: str) -> str:
    if isinstance(program, ProblemSpec):
        return _problem_javascript(program, filename)
    lines = ['"use strict";',
             "function enString(value) {",
             "  return value === null ? 'None' : value === true ? 'True' : value === false ? 'False' : String(value);",
             "}"]
    declared = set()
    for statement in program.statements:
        if isinstance(statement, Assign):
            prefix = "" if statement.name in declared else "let "
            lines.append(f"{prefix}en_{statement.name} = {_expression(statement.value, filename)};")
            declared.add(statement.name)
        elif isinstance(statement, Display):
            values = [_expression(value, filename) for value in statement.values]
            if not values:
                raise CodeInEnglishError(filename, 1, "JavaScript display needs a value", kind="unsupported")
            lines.append(f"console.log({' + '.join(f'enString({value})' for value in values)});")
        else:
            raise CodeInEnglishError(filename, 1, f"JavaScript does not yet support {type(statement).__name__} instructions", kind="unsupported")
    return "\n".join(lines) + "\n"


def _problem_javascript(spec: ProblemSpec, filename: str) -> str:
    if spec.family.value in BY_KEY or spec.stages:
        return recipe_javascript(spec, filename)
    raise CodeInEnglishError(filename, 1, f"JavaScript does not yet support {spec.family.value} problems", kind="unsupported")
