"""JavaScript backend entry point: whole programs (js_program.py) and problem recipes (transpile_js.py)."""

from __future__ import annotations


from .errors import CodeInEnglishError
from .ir import Program
from .problem_recognizer import ProblemSpec
from .recipes import BY_KEY
from .java_program import program_java
from .js_program import program_javascript
from .transpile_js import recipe_javascript


def generate_javascript(program: Program | ProblemSpec, filename: str) -> str:
    if isinstance(program, ProblemSpec):
        return _problem_javascript(program, filename)
    return program_javascript(program, filename)


def _problem_javascript(spec: ProblemSpec, filename: str) -> str:
    if spec.family.value in BY_KEY or spec.stages:
        return recipe_javascript(spec, filename)
    raise CodeInEnglishError(filename, 1, f"JavaScript does not yet support {spec.family.value} problems", kind="unsupported")


def generate_java(program: Program | ProblemSpec, filename: str) -> str:
    if isinstance(program, ProblemSpec):
        raise CodeInEnglishError(filename, 1, "Java output supports instruction programs for now; use target python or javascript for problem requests", kind="unsupported")
    return program_java(program, filename)
