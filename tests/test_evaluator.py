import contextlib
import io
import subprocess
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

    def test_constructor_inheritance_and_super(self):
        source = (EXAMPLES / "animals.en").read_text()
        self.assertEqual(interpreted(source), ["Rex makes a sound and barks", 3])

    def test_objects_in_a_list_can_be_looped_over(self):
        source = (EXAMPLES / "bank_account.en").read_text().split("make an Account")[0] + (
            'make an empty list called accounts\nmake an Account called a with "A" and 1\nmake an Account called b with "B" and 2\n'
            "add a to accounts\nadd b to accounts\nfor each item in accounts\ncall item.deposit with 10\nend for\n"
            "set x to call a.current\nset y to call b.current\nshow x and \" \" and y\n")
        self.assertEqual(interpreted(source), ["11 12"])

    def test_class_errors_are_diagnostics(self):
        base = "define a class called A\ndefine a constructor with parameter x\nset self.x to x\nend constructor\nend class\n"
        for source, message in ((base + "make an A called a\n", "constructor takes 1"),
                                ("define a class called B\nend class\nmake a B called b with 1\n", "no constructor"),
                                ("define a class called C that extends Nope\nend class\n", "unknown parent"),
                                ("define a class called D\ndefine a method called m\ncall super.m\nend method\nend class\n", "super"),
                                (base.replace("end class", "define a constructor\nend constructor\nend class"), "only one constructor")):
            with self.subTest(message), self.assertRaisesRegex(Exception, message):
                interpreted(source)

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


@unittest.skipUnless(EXAMPLES.is_dir() and __import__("shutil").which("node"), "needs the examples folder and Node.js")
class JavaScriptDifferentialTests(unittest.TestCase):
    def test_javascript_output_matches_the_interpreter_on_instruction_examples(self):
        import shutil
        for path in sorted(EXAMPLES.glob("*.en")):
            if "problem" in path.name or "javascript" in path.name or path.name.startswith("two_sum"):
                continue
            with self.subTest(path.name), tempfile.TemporaryDirectory() as directory:
                source = path.read_text()
                if "target python" in source:
                    source = source.replace("target python", "target javascript")
                else:
                    source = "target javascript\n" + source
                en = Path(directory) / "p.en"
                en.write_text(source, encoding="utf-8")
                result = subprocess.run([shutil.which("node"), str(generate_file(en))], input="Ada\nAda\nAda\n", capture_output=True, text=True)
                expected = "".join(f"{line}\n" for line in interpreted(path.read_text(), ["Ada"] * 3))
                self.assertEqual((result.returncode, result.stdout.replace("Your name: ", "")), (0, expected.replace("Your name: ", "")), result.stderr)
