from __future__ import annotations
import sys
from typing import TextIO

from .errors import CodeInEnglishError
from .evaluator import _Instance, run
from .expressions import parse_expression
from .ir import Display, Program
from .parser import parse

_HELP_TEXT = """
EN Language Quick Reference:
  set <name> to <value>                -- Define or assign a variable
  increase <name> by <amount>          -- Increment
  decrease <name> by <amount>          -- Decrement
  show <expression>                    -- Display output
  if <condition> then ... end if       -- Conditional branch
  while <condition> ... end while      -- While loop
  stop the loop                        -- Break out of loop
  skip to next                         -- Continue loop
  for each <item> in <list> ... end for-- For-each loop
  create a class named <Name>          -- Define OOP class
  make a <Class> called <instance>     -- Instantiate class
  tell <instance> to <method>          -- Call method
  vars                                 -- List active variables and classes
  clear                                -- Reset session variables
  exit / quit                          -- Exit the shell
"""


def start_repl(
    input_stream: TextIO | None = None,
    output_stream: TextIO | None = None,
) -> None:
    """Run an interactive offline read-eval-print loop."""
    if input_stream is None:
        try:
            import readline  # Enable arrow keys, history in standard terminals
        except ImportError:
            pass
        input_fn = input
    else:
        def input_fn(prompt: str = "") -> str:
            if prompt and output_stream:
                output_stream.write(prompt)
                output_stream.flush()
            line = input_stream.readline()
            if not line:
                raise EOFError()
            return line.rstrip("\r\n")

    out = output_stream or sys.stdout

    def emit(text: str = "") -> None:
        out.write(f"{text}\n")
        out.flush()

    emit("EN Language 0.2 Interactive Shell (offline)")
    emit("Type English statements, 'help' for instructions, or 'exit' to quit.\n")

    scope: dict = {}
    buffer: list[str] = []

    while True:
        prompt = ".. " if buffer else ">> "
        try:
            raw_line = input_fn(prompt)
        except (EOFError, KeyboardInterrupt):
            emit("\nGoodbye!")
            break

        line = raw_line.strip()
        if not line:
            continue

        # Handle top-level shell commands when not in a multiline block
        if not buffer:
            if line.lower() in ("exit", "quit", ":q"):
                emit("Goodbye!")
                break
            if line.lower() == "help":
                emit(_HELP_TEXT)
                continue
            if line.lower() == "clear":
                scope.clear()
                emit("Session cleared.")
                continue
            if line.lower() == "vars":
                if not scope:
                    emit("(no variables defined)")
                else:
                    for k, v in scope.items():
                        if isinstance(v, _Instance):
                            emit(f"  {k} = <instance of {v._cls.name}>")
                        elif hasattr(v, "methods"):
                            emit(f"  {k} = <class {v.name}>")
                        else:
                            emit(f"  {k} = {v!r}")
                continue

        buffer.append(line)
        source = "\n".join(buffer)

        try:
            known_names = set(scope.keys())
            known_classes = {k for k, v in scope.items() if hasattr(v, "methods")}
            program = parse(source, known_names=known_names, known_classes=known_classes)
            buffer.clear()
            run(program, write=emit, scope=scope)
        except CodeInEnglishError as error:
            # Check if this error is due to an unclosed block
            msg = str(error)
            if "needs 'end " in msg or "unexpected indentation" in msg:
                # Still waiting for block closing marker
                continue
            # Check if standalone line is an expression (e.g. `score plus 5`, `buddy.name`)
            if len(buffer) == 1:
                try:
                    expr = parse_expression(buffer[0], filename="<repl>", line=1)
                    eval_program = Program([Display([expr])])
                    buffer.clear()
                    run(eval_program, write=emit, scope=scope)
                    continue
                except Exception:
                    pass

            emit(f"Error: {error}")
            buffer.clear()
        except Exception as error:
            emit(f"Runtime error: {error}")
            buffer.clear()
