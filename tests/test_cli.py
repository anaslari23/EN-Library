import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from codeinenglish.__main__ import main
from codeinenglish.contract import read_contract
from codeinenglish.provenance import split_provenance


class CliTests(unittest.TestCase):
    def test_check_json_reports_contract_and_exact_run_plan_without_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "pair.en"
            source.write_text(
                'en 0.2\ntarget python\n#? Find two numbers that add up to the target and return their indices.\n'
                '#? Example input: {"nums":[2,7],"target":9}\n#? Example output: [0,1]\n', encoding="utf-8")
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                result = main(["check", str(source), "--json"])
            payload = json.loads(stdout.getvalue())
            self.assertEqual(result, 0)
            self.assertEqual(payload["version"], "0.2")
            self.assertEqual(payload["form"], "problem")
            self.assertEqual(payload["examples"], {"present": True, "count": 1})
            self.assertEqual(payload["plan"]["runtime"], "python")
            self.assertEqual(payload["plan"]["run_args"], [str(source.with_suffix(".py").resolve()), "--check-examples"])
            self.assertFalse(payload["written"])
            self.assertFalse(source.with_suffix(".py").exists())

    def test_check_json_matches_python_source_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "contract.en"
            source_text = "en 0.2\ntarget python\n#? Find the maximum number.\n"
            source.write_text(source_text, encoding="utf-8")
            contract = read_contract(source_text, str(source))
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                result = main(["check", str(source), "--json"])
            payload = json.loads(stdout.getvalue())
            self.assertEqual(result, 0)
            self.assertEqual(payload["version"], f"{contract.version[0]}.{contract.version[1]}")
            self.assertEqual(payload["target"], contract.target)
            self.assertEqual(payload["form"], contract.form)
            self.assertEqual(payload["diagnostics"], [
                {
                    "code": item.code, "severity": item.severity, "message": item.message,
                    "file": item.file, "line": item.line, "column": item.column,
                    "end_line": item.end_line, "end_column": item.end_column,
                    "hint": item.hint, "related": [list(pair) for pair in item.related],
                }
                for item in contract.diagnostics
            ])

    def test_generate_json_writes_and_reports_diagnostics_and_run_plan(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "hello.en"
            source.write_text('en 0.2\nshow "hello"\n', encoding="utf-8")
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                result = main(["generate", str(source), "--json"])
            payload = json.loads(stdout.getvalue())
            self.assertEqual(result, 0)
            self.assertTrue(payload["written"])
            self.assertEqual(payload["plan"]["run_args"], [str(source.with_suffix(".py").resolve())])
            self.assertTrue(source.with_suffix(".py").exists())

    def test_generate_json_source_error_keeps_existing_output(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "bad.en"
            output = source.with_suffix(".py")
            source.write_text("en 0.2\n# ordinary docs\n", encoding="utf-8")
            output.write_text("previous bytes", encoding="utf-8")
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                result = main(["generate", str(source), "--json"])
            payload = json.loads(stdout.getvalue())
            self.assertEqual(result, 1)
            self.assertFalse(payload["written"])
            self.assertIsNone(payload["plan"])
            self.assertIn("EN-E305", [item["code"] for item in payload["diagnostics"]])
            self.assertEqual(output.read_text(encoding="utf-8"), "previous bytes")

    def test_usage_error_returns_two(self):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            result = main([])
        self.assertEqual(result, 2)
        self.assertIn("usage:", stderr.getvalue())

    def test_default_output_and_success_path(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "greeting.en"
            source.write_text('show "Hello"', encoding="utf-8")
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                result = main(["translate", str(source)])
            self.assertEqual(result, 0)
            self.assertEqual(split_provenance(source.with_suffix(".py").read_text(encoding="utf-8"))[1], "print('Hello')\n")
            self.assertIn(str(source.with_suffix(".py")), stdout.getvalue())

    def test_explicit_output_is_used(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "greeting.en"
            output = Path(directory) / "custom.py"
            source.write_text('show "Hello"', encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()):
                result = main(["translate", str(source), "--output", str(output)])
            self.assertEqual(result, 0)
            self.assertTrue(output.exists())
            self.assertFalse(source.with_suffix(".py").exists())

    def test_generated_python_is_written_but_not_executed(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "program.en"
            output = Path(directory) / "program.py"
            source.write_text("show 1", encoding="utf-8")
            output.write_text("raise RuntimeError('generated code was executed')", encoding="utf-8")
            with patch("codeinenglish.__main__.translate_file", return_value=output) as translate_file:
                with contextlib.redirect_stdout(io.StringIO()):
                    result = main(["translate", str(source)])
            self.assertEqual(result, 0)
            translate_file.assert_called_once_with(str(source), None)
            self.assertEqual(output.read_text(encoding="utf-8"), "raise RuntimeError('generated code was executed')")

    def test_translation_error_returns_one(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "bad.en"
            source.write_text("unsupported wording", encoding="utf-8")
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                result = main(["translate", str(source)])
            self.assertEqual(result, 1)
            self.assertIn("bad.en:1", stderr.getvalue())

    def test_solve_command_generates_sibling_python_file(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "task.en"
            source.write_text("# Calculate the sum of all numbers in the list.", encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()):
                result = main(["solve", str(source)])
            self.assertEqual(result, 0)
            self.assertIn("def calculate_sum", source.with_suffix(".py").read_text(encoding="utf-8"))

    def test_generate_command_dispatches_instruction_program(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "greeting.en"
            source.write_text('show "Hello"', encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()):
                result = main(["generate", str(source)])
            self.assertEqual(result, 0)
            self.assertEqual(split_provenance(source.with_suffix(".py").read_text(encoding="utf-8"))[1], "print('Hello')\n")

    def test_generate_command_dispatches_problem_directive(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "pair.en"
            source.write_text(
                "import codeinpython library\n"
                "# Find two numbers that add up to the target and return their indices.\n"
                "# Exactly one solution exists; do not reuse an element.\n",
                encoding="utf-8",
            )
            with contextlib.redirect_stdout(io.StringIO()):
                result = main(["generate", str(source)])
            self.assertEqual(result, 0)
            self.assertIn("def two_sum(nums, target):", source.with_suffix(".py").read_text(encoding="utf-8"))

    def test_generate_command_accepts_python_target_directive(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "greeting.en"
            source.write_text('target python\nshow "Hello"', encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()):
                result = main(["generate", str(source)])
            self.assertEqual(result, 0)
            self.assertEqual(split_provenance(source.with_suffix(".py").read_text(encoding="utf-8"))[1], "print('Hello')\n")

    def test_generate_command_uses_explicit_output_path(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "greeting.en"
            output = Path(directory) / "result.py"
            source.write_text('show "Hello"', encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()):
                result = main(["generate", str(source), "--output", str(output)])
            self.assertEqual(result, 0)
            self.assertTrue(output.exists())
            self.assertFalse(source.with_suffix(".py").exists())


if __name__ == "__main__":
    unittest.main()
