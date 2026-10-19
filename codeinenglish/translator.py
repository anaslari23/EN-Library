import os
import tempfile
from pathlib import Path

from .errors import CodeInEnglishError
from .parser import parse_program
from .python_generator import generate_python


def translate(source: str, filename: str = "<string>") -> str:
    """Translate a supported English program into Python source."""
    return generate_python(parse_program(source, filename))


def translate_file(source_path: str | Path, output_path: str | Path | None = None) -> Path:
    """Translate an English source file and atomically write its Python output."""
    source = Path(source_path)
    destination = Path(output_path) if output_path is not None else source.with_suffix(".py")
    if source.resolve() == destination.resolve():
        raise CodeInEnglishError(str(source), 1, "input and output paths must be different")

    english_source = source.read_text(encoding="utf-8")
    python_source = translate(english_source, str(source))

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
