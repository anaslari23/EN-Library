import os
import tempfile
from pathlib import Path

from .errors import CodeInEnglishError
from .contract import ENSourceError, read_contract
from .parser import parse_program
from .provenance import add_provenance
from .python_generator import generate_python


def translate(source: str, filename: str = "<string>") -> str:
    """Translate a supported English program into Python source."""
    contract = read_contract(source, filename)
    if not contract.ok:
        raise ENSourceError(tuple(item for item in contract.diagnostics if item.severity == "error"))
    from .interpreter import interpret_source
    from .problem_recognizer import ProblemSpec
    from .problem_solver import render_problem_python

    if contract.target != "python":
        raise CodeInEnglishError(filename, 1, "translate() generates Python; use generate_file() for a different target")
    interpreted = interpret_source(source, filename)
    return render_problem_python(interpreted) if isinstance(interpreted, ProblemSpec) else generate_python(interpreted)


def translate_file(source_path: str | Path, output_path: str | Path | None = None) -> Path:
    """Translate an English source file and atomically write its Python output."""
    source = Path(source_path)
    destination = Path(output_path) if output_path is not None else source.with_suffix(".py")
    if source.resolve() == destination.resolve():
        raise CodeInEnglishError(str(source), 1, "input and output paths must be different")

    english_source = source.read_text(encoding="utf-8")
    python_source = translate(english_source, str(source))
    contract = read_contract(english_source, str(source))
    version_label = f"{contract.version[0]}.{contract.version[1]}" if contract.version else None
    python_source = add_provenance(python_source, source, version_label, "python")

    _write_python(python_source, destination)
    return destination


def _write_python(python_source: str, destination: Path) -> None:
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(python_source)
            temporary.write("\n")
        os.replace(temporary_path, destination)
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
