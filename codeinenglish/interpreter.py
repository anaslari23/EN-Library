from pathlib import Path

from .errors import CodeInEnglishError
from .contract import Diagnostic, ENSourceError, read_contract
from .ir import Program
from .javascript_generator import generate_javascript
from .parser import parse_program
from .problem_prompt import LIBRARY_DIRECTIVE
from .problem_recognizer import ProblemSpec
from .problem_solver import recognize_lines, recognize_source, render_problem_python
from .python_generator import generate_python
from .provenance import add_provenance
from .translator import _write_python


def generate_file(source_path: str | Path, output_path: str | Path | None = None) -> Path:
    """Generate target-language source from a supported EN file."""
    source = Path(source_path)
    english_source = source.read_text(encoding="utf-8")
    contract = read_contract(english_source, str(source))
    if not contract.ok:
        raise ENSourceError(tuple(item for item in contract.diagnostics if item.severity == "error"))
    target = contract.target
    destination = Path(output_path) if output_path is not None else source.with_suffix(".js" if target == "javascript" else ".py")
    if source.resolve() == destination.resolve():
        raise CodeInEnglishError(str(source), 1, "input and output paths must be different")

    interpreted = _interpret_contract(contract, str(source))
    generated = (generate_javascript(interpreted, str(source)) if target == "javascript" else
                 render_problem_python(interpreted) if isinstance(interpreted, ProblemSpec) else generate_python(interpreted))
    version_label = f"{contract.version[0]}.{contract.version[1]}" if contract.version else None
    generated = add_provenance(generated, source, version_label, target)

    _write_python(generated, destination)
    return destination


def interpret_source(source: str, filename: str = "<string>") -> Program | ProblemSpec:
    """Interpret an EN file without generating target-language source."""
    contract = read_contract(source, filename)
    if not contract.ok:
        raise ENSourceError(tuple(item for item in contract.diagnostics if item.severity == "error"))
    return _interpret_contract(contract, filename)


def _interpret_contract(contract, filename: str) -> Program | ProblemSpec:
    try:
        if contract.form == "problem":
            return recognize_lines(contract.lines, filename)
        if contract.form != "instructions":
            raise CodeInEnglishError(filename, 1, "nothing to generate")
        source_lines = [""] * max((item.line for item in contract.lines), default=0)
        for item in contract.lines:
            source_lines[item.line - 1] = item.text
        return parse_program("\n".join(source_lines), filename)
    except CodeInEnglishError as error:
        if isinstance(error, ENSourceError):
            raise
        line = getattr(error, "line", 1)
        source_line = next((item for item in contract.lines if item.line == line), None)
        column = (source_line.col_offset + getattr(error, "column", 1)) if source_line else getattr(error, "column", 1)
        diagnostic = Diagnostic("EN-E400", "error", error.message, filename, line, column, line, column + 1)
        raise ENSourceError((diagnostic,)) from error


def _interpret_prepared(prepared: str, mode: str, filename: str) -> Program | ProblemSpec:
    return recognize_source(prepared, filename) if mode == "problem" else parse_program(prepared, filename)


def _prepare_source(source: str, filename: str) -> tuple[str, str, str]:
    """Read a standalone target directive without changing later source line numbers."""
    lines = source.splitlines(keepends=True)
    directive = None
    target = "python"
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
                raise CodeInEnglishError(filename, line_number, "use 'target python' or 'target javascript' on its own line")
            if words[1] not in ("python", "javascript"):
                raise CodeInEnglishError(filename, line_number, f"target '{words[1]}' is not supported; use python or javascript", kind="unsupported")
            directive = "target"
            target = words[1]
            lines[line_number - 1] = "\n" if original.endswith("\n") else ""
            continue
        if stripped.casefold().startswith("import codein") and stripped.casefold().endswith(" library"):
            raise CodeInEnglishError(filename, line_number, "unsupported library directive; use 'target python'", kind="unsupported")

    prepared = "".join(lines)
    if directive == "legacy":
        return prepared, "problem", "python"
    if directive == "target":
        has_instructions = any(
            line.strip() and not line.lstrip().startswith("#") for line in prepared.splitlines()
        )
        return prepared, "instructions" if has_instructions else "problem", target
    return prepared, "instructions", "python"
