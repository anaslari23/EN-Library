import argparse
import sys

from .errors import CodeInEnglishError
from .translator import translate_file
from .problem_solver import solve_file
from .interpreter import generate_file


def _argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="codeinenglish")
    commands = parser.add_subparsers(dest="command", required=True)
    translate = commands.add_parser("translate", help="translate an .en file into Python")
    translate.add_argument("source", help="English program source file")
    translate.add_argument("--output", help="Python output path (defaults to the same name with .py)")
    solve = commands.add_parser("solve", help="generate Python from an .en problem statement")
    solve.add_argument("source", help="comment-based problem source file")
    solve.add_argument("--output", help="Python output path (defaults to the same name with .py)")
    generate = commands.add_parser("generate", help="generate Python from any supported .en file")
    generate.add_argument("source", help="Code in English source file")
    generate.add_argument("--output", help="Python output path (defaults to the same name with .py)")
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        arguments = _argument_parser().parse_args(sys.argv[1:] if argv is None else argv)
    except SystemExit as error:
        return int(error.code)

    try:
        command = {
            "translate": translate_file,
            "solve": solve_file,
            "generate": generate_file,
        }[arguments.command]
        output_path = command(arguments.source, arguments.output)
    except (OSError, UnicodeError, CodeInEnglishError) as error:
        print(error, file=sys.stderr)
        return 1
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
