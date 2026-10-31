from __future__ import annotations
import os
import re
import sys
from pathlib import Path

_TRIGGER = re.compile(r"^\s*#\s*write a program(?: called (\w+))? to\b", re.IGNORECASE)


def comment_requests(source: str) -> list[tuple[str | None, str]]:
    """(name or None, request) for each `# write a program [called NAME] to ...` comment block."""
    blocks, current = [], None
    for line in source.splitlines():
        stripped = line.strip()
        trigger = _TRIGGER.match(line)
        if trigger:
            current = [re.sub(r"\bcalled \w+ ", "", stripped.lstrip("#").strip(), count=1, flags=re.IGNORECASE)]
            blocks.append((trigger.group(1), current))
        elif current is not None and stripped.startswith("#"):
            current.append(stripped.lstrip("#").strip())
        else:
            current = None
    return [(name, "target python\n" + "".join(f"# {text}\n" for text in block)) for name, block in blocks]


def generate_from_comments(source: str, namespace: dict, filename: str = "<string>", announce: bool = False) -> list[str]:
    """Generate each commented request and bind its function in `namespace`; return the names bound.

    A comment may name its function (`# write a program called vowel_count to ...`); the generated name is always bound too.
    """
    from .interpreter import interpret_source
    from .problem_solver import render_problem_python

    names = []
    for alias, request in comment_requests(source):
        spec = interpret_source(request, filename)
        scope = {"__name__": "codeinenglish_generated"}  # keeps the generated `__main__` guard from running
        exec(compile(render_problem_python(spec), filename, "exec"), scope)
        function = scope[spec.function_name]
        for name in dict.fromkeys(filter(None, (alias, spec.function_name))):
            namespace[name] = function
            names.append(name)
        if announce and not os.environ.get("CODEINENGLISH_QUIET"):
            shown = " (also " + spec.function_name + ")" if alias else ""
            print(f"codeinenglish: defined {alias or spec.function_name}({', '.join(item.name for item in spec.inputs)}){shown}", file=sys.stderr)
    return names


def _on_import() -> None:
    """Act on `# write a program to ...` comments in the file that first imports codeinenglish."""
    frame = sys._getframe(1)
    while frame and (frame.f_code.co_filename.startswith("<frozen")
                     or frame.f_globals.get("__name__", "").split(".")[0] == __package__):  # by name: paths can differ (symlinks, zips)
        frame = frame.f_back
    path = frame.f_globals.get("__file__") if frame else None
    if not isinstance(path, str) or not path.endswith(".py"):
        return
    try:
        source = Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return
    generate_from_comments(source, frame.f_globals, path, announce=True)
