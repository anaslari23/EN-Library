import re
import sys
from pathlib import Path

_TRIGGER = re.compile(r"^\s*#\s*write a program to\b", re.IGNORECASE)
_PACKAGE_DIR = str(Path(__file__).resolve().parent)


def comment_requests(source: str) -> list[str]:
    """Return each `# write a program to ...` comment block, with its comment markers removed."""
    blocks, current = [], None
    for line in source.splitlines():
        stripped = line.strip()
        if _TRIGGER.match(line):
            current = [stripped.lstrip("#").strip()]
            blocks.append(current)
        elif current is not None and stripped.startswith("#"):
            current.append(stripped.lstrip("#").strip())
        else:
            current = None
    return ["target python\n" + "".join(f"# {text}\n" for text in block) for block in blocks]


def generate_from_comments(source: str, namespace: dict, filename: str = "<string>") -> list[str]:
    """Generate each commented request and bind its function in `namespace`; return the function names."""
    from .interpreter import interpret_source
    from .problem_solver import render_problem_python

    names = []
    for request in comment_requests(source):
        spec = interpret_source(request, filename)
        scope = {"__name__": "codeinenglish_generated"}  # keeps the generated `__main__` guard from running
        exec(compile(render_problem_python(spec), filename, "exec"), scope)
        namespace[spec.function_name] = scope[spec.function_name]
        names.append(spec.function_name)
    return names


def _on_import() -> None:
    """Act on `# write a program to ...` comments in the file that first imports codeinenglish."""
    frame = sys._getframe(1)
    while frame and (frame.f_code.co_filename.startswith("<frozen importlib")
                     or frame.f_code.co_filename.startswith(_PACKAGE_DIR)):
        frame = frame.f_back
    path = frame.f_globals.get("__file__") if frame else None
    if not isinstance(path, str) or not path.endswith(".py"):
        return
    try:
        source = Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return
    generate_from_comments(source, frame.f_globals, path)
