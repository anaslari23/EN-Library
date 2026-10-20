from pathlib import Path

from .errors import CodeInEnglishError
from .problem_prompt import has_problem_directive
from .python_generator import generate_python_ast
from .translator import _write_python, translate
from .problem_solver import solve


def generate_file(source_path: str | Path, output_path: str | Path | None = None) -> Path:
    """Generate Python from an instruction program or directive-based problem file."""
    source = Path(source_path)
    destination = Path(output_path) if output_path is not None else source.with_suffix(".py")
    if source.resolve() == destination.resolve():
        raise CodeInEnglishError(str(source), 1, "input and output paths must be different")

    english_source = source.read_text(encoding="utf-8")
    if has_problem_directive(english_source):
        python_source = solve(english_source, str(source))
    else:
        python_source = translate(english_source, str(source))

    _write_python(python_source, destination)
    return destination
