import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from codeinenglish.__main__ import main


class CliTests(unittest.TestCase):
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
            self.assertEqual(source.with_suffix(".py").read_text(encoding="utf-8"), "print('Hello')\n")
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


if __name__ == "__main__":
    unittest.main()
