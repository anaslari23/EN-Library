from pathlib import Path

from .errors import CodeInEnglishError
from .ir import Program
from .parser import parse_program
from .problem_prompt import LIBRARY_DIRECTIVE
from .problem_recognizer import ProblemSpec
from .problem_solver import recognize_source, render_problem_python
from .python_generator import generate_python
from .translator import _write_python


def generate_file(source_path: str | Path, output_path: str | Path | None = None) -> Path:
    """Generate Python from an instruction program or directive-based problem file."""
    source = Path(source_path)
    destination = Path(output_path) if output_path is not None else source.with_suffix(".py")
    if source.resolve() == destination.resolve():
        raise CodeInEnglishError(str(source), 1, "input and output paths must be different")

    english_source = source.read_text(encoding="utf-8")
    interpreted = interpret_source(english_source, str(source))
    python_source = (
        render_problem_python(interpreted)
        if isinstance(interpreted, ProblemSpec)
        else generate_python(interpreted)
    )

    _write_python(python_source, destination)
    return destination


def interpret_source(source: str, filename: str = "<string>") -> Program | ProblemSpec:
    """Interpret an EN file without generating target-language source."""
    prepared, mode = _prepare_source(source, filename)
    return recognize_source(prepared, filename) if mode == "problem" else parse_program(prepared, filename)


def _prepare_source(source: str, filename: str) -> tuple[str, str]:
    """Read a standalone target directive without changing later source line numbers."""
    lines = source.splitlines(keepends=True)
    directive = None
    for line_number, original in enumerate(lines, start=1):
        stripped = original.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped == LIBRARY_DIRECTIVE:
            if directive is not None:
                raise CodeInEnglishError(filename, line_number, "target directive may appear only once")
            directive = "legacy"
            continue
        if stripped.casefold() == "target" or stripped.casefold().startswith("target "):
            if directive is not None:
                raise CodeInEnglishError(filename, line_number, "target directive may appear only once")
            words = stripped.casefold().split()
            if len(words) != 2:
                raise CodeInEnglishError(filename, line_number, "use 'target python' on its own line")
            if words[1] != "python":
                raise CodeInEnglishError(filename, line_number, f"target '{words[1]}' is not supported; use python", kind="unsupported")
            directive = "target"
            lines[line_number - 1] = "\n" if original.endswith("\n") else ""
            continue
        if stripped.casefold().startswith("import codein") and stripped.casefold().endswith(" library"):
            raise CodeInEnglishError(filename, line_number, "unsupported library directive; use 'target python'", kind="unsupported")

    prepared = "".join(lines)
    if directive == "legacy":
        return prepared, "problem"
    if directive == "target":
        has_instructions = any(
            line.strip() and not line.lstrip().startswith("#") for line in prepared.splitlines()
        )
        return prepared, "instructions" if has_instructions else "problem"
    return prepared, "instructions"
