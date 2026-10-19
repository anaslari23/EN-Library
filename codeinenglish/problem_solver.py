from pathlib import Path
from dataclasses import replace

from .errors import CodeInEnglishError
from .problem_prompt import extract_problem_prompt
from .problem_recognizer import recognize_problem
from .problem_strategies import generate_problem_ast
from .python_generator import generate_python_ast
from .translator import _write_python


def solve(source: str, filename: str = "<string>") -> str:
    """Generate editable Python for a supported comment-written problem."""
    prompt = extract_problem_prompt(source, filename)
    spec = replace(recognize_problem(prompt, filename), examples=prompt.examples)
    _validate_examples(spec, filename)
    comments = [
        f"Interpreted request: {spec.function_name}({', '.join(item.name for item in spec.inputs)}) -> {spec.result}.",
        *[f"{assumption.status.title()} assumption: {assumption.text}" for assumption in spec.assumptions],
    ]
    return generate_python_ast(generate_problem_ast(spec), comments=comments)


def _matches_kind(value: object, kind: str) -> bool:
    if kind == "integer":
        return type(value) is int
    if kind == "string":
        return type(value) is str
    if kind in ("integer_list", "sorted_integer_list"):
        return type(value) is list and all(type(item) is int for item in value)
    return True


def _validate_examples(spec, filename: str) -> None:
    expected = {item.name: item.kind for item in spec.inputs}
    for example in spec.examples:
        if set(example.input) != set(expected):
            raise CodeInEnglishError(filename, example.source_line, f"example input keys must be exactly {', '.join(expected)}", kind="ambiguous")
        for name, kind in expected.items():
            value = example.input[name]
            if not _matches_kind(value, kind):
                raise CodeInEnglishError(filename, example.source_line, f"example field '{name}' must be {kind}", kind="syntax")
            if kind == "sorted_integer_list" and value != sorted(value):
                raise CodeInEnglishError(filename, example.source_line, f"example field '{name}' must be sorted in ascending order", kind="ambiguous")


def solve_file(source_path: str | Path, output_path: str | Path | None = None) -> Path:
    source = Path(source_path)
    destination = Path(output_path) if output_path is not None else source.with_suffix(".py")
    if source.resolve() == destination.resolve():
        from .errors import CodeInEnglishError
        raise CodeInEnglishError(str(source), 1, "input and output paths must be different")
    generated = solve(source.read_text(encoding="utf-8"), str(source))
    _write_python(generated, destination)
    return destination
