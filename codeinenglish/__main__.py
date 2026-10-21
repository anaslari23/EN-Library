import argparse
from dataclasses import asdict
import json
import sys
from pathlib import Path

from .errors import CodeInEnglishError
from .contract import Diagnostic, ENSourceError, read_contract, SUPPORTED_VERSIONS
from .problem_recognizer import ProblemSpec
from .translator import translate_file
from .problem_solver import solve_file
from .interpreter import generate_file, interpret_source
from .migrate import migrate_file


def _argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="codeinenglish")
    commands = parser.add_subparsers(dest="command", required=True)
    translate = commands.add_parser("translate", help="translate an .en file into Python")
    translate.add_argument("source", help="English program source file")
    translate.add_argument("--output", help="Python output path (defaults to the same name with .py)")
    solve = commands.add_parser("solve", help="generate Python from an .en problem statement")
    solve.add_argument("source", help="comment-based problem source file")
    solve.add_argument("--output", help="Python output path (defaults to the same name with .py)")
    generate = commands.add_parser("generate", help="generate target-language source from a supported .en file")
    generate.add_argument("source", help="Code in English source file")
    generate.add_argument("--output", help="output path (defaults to .py or .js based on target)")
    generate.add_argument("--json", action="store_true", help="print the versioned run-plan response as JSON")
    check = commands.add_parser("check", help="validate an .en file and report its run plan")
    check.add_argument("source", help="Code in English source file")
    check.add_argument("--output", help="output path to report (defaults to .py or .js based on target)")
    check.add_argument("--json", action="store_true", required=True, help="print the contract and run plan as JSON")
    migrate = commands.add_parser("migrate", help="safely update an .en source version")
    migrate.add_argument("source", help="source file to migrate")
    migrate.add_argument("--to", choices=("0.1", "0.2"), help="target EN version (defaults to the newest supported version)")
    migrate.add_argument("--write", action="store_true", help="write the migration atomically; default is a preview")
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        arguments = _argument_parser().parse_args(sys.argv[1:] if argv is None else argv)
    except SystemExit as error:
        return int(error.code)

    try:
        if arguments.command in ("check",) or (arguments.command == "generate" and arguments.json):
            return _json_command(arguments)
        if arguments.command == "migrate":
            changed, diff = migrate_file(arguments.source, arguments.to, write=arguments.write)
            if diff:
                print(diff, end="" if diff.endswith("\n") else "\n")
            elif not changed:
                print("This file already uses the requested version.")
            return 0
        if arguments.command == "generate":
            source_text = Path(arguments.source).read_text(encoding="utf-8")
            contract = read_contract(source_text, arguments.source)
            for warning in (item for item in contract.diagnostics if item.severity == "warning"):
                print(f"{warning.file}:{warning.line}:{warning.column}: {warning.code}: {warning.message}", file=sys.stderr)
        command = {
            "translate": translate_file,
            "solve": solve_file,
            "generate": generate_file,
        }[arguments.command]
        output_path = command(arguments.source, arguments.output)
    except (OSError, UnicodeError, CodeInEnglishError, ValueError) as error:
        print(error, file=sys.stderr)
        return 1
    print(output_path)
    return 0


def _json_command(arguments) -> int:
    source_path = Path(arguments.source)
    output_argument = getattr(arguments, "output", None)
    try:
        source_text = source_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        print(json.dumps({"schema_version": 1, "file": str(source_path), "version": None,
                          "supported_versions": _version_labels(), "target": "python", "form": None,
                          "examples": {"present": False, "count": 0}, "plan": None,
                          "written": False, "diagnostics": [_io_diagnostic(source_path, str(error))]},
                         separators=(",", ":")))
        return 2

    contract = read_contract(source_text, str(source_path))
    for warning in (item for item in contract.diagnostics if item.severity == "warning"):
        print(f"{warning.file}:{warning.line}:{warning.column}: {warning.code}: {warning.message}", file=sys.stderr)
    output_path = Path(output_argument) if output_argument else source_path.with_suffix(".js" if contract.target == "javascript" else ".py")
    diagnostics = list(contract.diagnostics)
    interpreted = None
    if contract.ok:
        try:
            interpreted = interpret_source(source_text, str(source_path))
        except ENSourceError as error:
            diagnostics.extend(error.diagnostics)
        except CodeInEnglishError as error:
            line = getattr(error, "line", 1)
            diagnostics.append(Diagnostic("EN-E400", "error", error.message, str(source_path), line, 1, line, 2))

    has_errors = any(item.severity == "error" for item in diagnostics)
    examples = tuple(interpreted.examples) if isinstance(interpreted, ProblemSpec) else ()
    absolute_output = str(output_path.resolve())
    run_args = [absolute_output]
    if examples:
        run_args.append("--check-examples")
    plan = None if has_errors else {
        "output_path": absolute_output,
        "runtime": "node" if contract.target == "javascript" else "python",
        "run_examples": bool(examples),
        "run_args": run_args,
    }
    if source_path.resolve() == output_path.resolve() and not has_errors:
        diagnostics.append(Diagnostic("EN-E400", "error", "input and output paths must be different", str(source_path), 1, 1, 1, 2))
        plan = None
        has_errors = True
    written = False
    if arguments.command == "generate" and not has_errors:
        try:
            written_path = generate_file(source_path, output_argument)
            plan["output_path"] = str(written_path.resolve())
            plan["run_args"][0] = plan["output_path"]
            written = True
        except (OSError, UnicodeError) as error:
            diagnostics.append(_io_diagnostic(source_path, str(error)))
            plan = None
        except ENSourceError as error:
            diagnostics.extend(error.diagnostics)
            plan = None
        except CodeInEnglishError as error:
            line = getattr(error, "line", 1)
            diagnostics.append(Diagnostic("EN-E400", "error", error.message, str(source_path), line, 1, line, 2))
            plan = None
    payload = {
        "schema_version": 1,
        "file": str(source_path),
        "version": f"{contract.version[0]}.{contract.version[1]}" if contract.version else None,
        "supported_versions": _version_labels(),
        "target": contract.target,
        "form": contract.form,
        "examples": {"present": bool(examples), "count": len(examples)},
        "plan": plan,
        "written": written,
        "diagnostics": [asdict(item) for item in diagnostics],
    }
    print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    return 1 if any(item.severity == "error" for item in diagnostics) else 0


def _version_labels() -> list[str]:
    return [f"{major}.{minor}" for major, minor in sorted(SUPPORTED_VERSIONS)]


def _io_diagnostic(filename: Path, message: str) -> Diagnostic:
    return Diagnostic("EN-E500", "error", message, str(filename), 1, 1, 1, 2)


if __name__ == "__main__":
    raise SystemExit(main())
