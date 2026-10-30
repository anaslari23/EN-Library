import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from codeinenglish import generate_file
from codeinenglish.__main__ import main
from codeinenglish.contract import ENSourceError
from codeinenglish.interpreter import run_source

EXAMPLES = Path(__file__).resolve().parents[2] / "examples"


def interpreted(source, stdin=()):
    out, answers = [], iter(stdin)
    run_source(source, "t.en", read=lambda prompt: next(answers), write=out.append)
    return out


def generated(path, stdin=""):
    with tempfile.TemporaryDirectory() as directory:
        target = generate_file(path, Path(directory) / "out.py")
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            import builtins
            lines = iter(stdin.splitlines())
            original, builtins.input = builtins.input, lambda prompt="": next(lines)
            try:
                exec(compile(target.read_text(), str(target), "exec"), {"__name__": "__main__"})
            finally:
                builtins.input = original
        return out.getvalue()


@unittest.skipUnless(EXAMPLES.is_dir(), "needs the en-language examples folder next to this checkout")
class EvaluatorTests(unittest.TestCase):
    def test_classes_fields_and_methods(self):
        self.assertEqual(interpreted((EXAMPLES / "greeter.en").read_text()), ["Hello Ada"])

    def test_runtime_error_is_a_diagnostic(self):
        with self.assertRaises(Exception) as caught:
            interpreted("set x to 1 divided by 0\n")
        self.assertNotIsInstance(caught.exception, ZeroDivisionError)

    def test_problem_file_is_rejected(self):
        with self.assertRaises(Exception):
            interpreted("target python\n# Find two numbers that add up to the target.\n")

    def test_matches_generated_python_on_instruction_examples(self):
        for path in sorted(EXAMPLES.glob("*.en")):
            if "problem" in path.name or "javascript" in path.name or path.name.startswith("two_sum"):
                continue
            with self.subTest(path.name):
                expected = generated(path, "Ada\nAda\nAda").splitlines()
                self.assertEqual([str(line) for line in interpreted(path.read_text(), ["Ada"] * 3)], expected)

    def test_cli_run(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(main(["run", str(EXAMPLES / "greeter.en")]), 0)
        self.assertEqual(out.getvalue(), "Hello Ada\n")


if __name__ == "__main__":
    unittest.main()
