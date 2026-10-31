import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from codeinenglish import CodeInEnglishError, generate_file
from codeinenglish.__main__ import main
from codeinenglish.interpreter import run_source

EXAMPLES = Path(__file__).resolve().parents[2] / "examples"


def find_java():
    for candidate in (shutil.which("java"), "/opt/homebrew/opt/openjdk@17/bin/java", "/opt/homebrew/opt/openjdk/bin/java"):
        if candidate and Path(candidate).exists() and subprocess.run([candidate, "-version"], capture_output=True).returncode == 0:
            return candidate
    return None


JAVA = find_java()


def java_run(source, stdin=""):
    with tempfile.TemporaryDirectory() as directory:
        en = Path(directory) / "p.en"
        en.write_text("target java\n" + source, encoding="utf-8")
        return subprocess.run([JAVA, str(generate_file(en))], input=stdin, capture_output=True, text=True)


def interpreted(source, answers=()):
    out, lines = [], iter(answers)
    run_source(source, "t.en", read=lambda prompt: next(lines), write=out.append)
    return "".join(f"{line}\n" for line in out)


@unittest.skipUnless(JAVA, "needs a working JDK (java and javac)")
class JavaBackendTests(unittest.TestCase):
    def test_java_output_matches_the_interpreter_on_instruction_examples(self):
        for path in sorted(EXAMPLES.glob("*.en")) if EXAMPLES.is_dir() else []:
            if "problem" in path.name or "javascript" in path.name or path.name.startswith("two_sum"):
                continue
            with self.subTest(path.name):
                source = path.read_text().replace("target python", "")
                result = java_run(source, "Ada\nAda\nAda\n")
                expected = interpreted(path.read_text(), ["Ada"] * 3)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout.replace("Your name: ", ""), expected.replace("Your name: ", ""))

    def test_runtime_errors_exit_nonzero_with_a_message_like_the_interpreter(self):
        class_base = "define a class called A\ndefine a constructor with parameter x\nset self.x to x\nend constructor\nend class\n"
        for label, source in {
            "division by zero": "set x to 1 divided by 0\n",
            "text plus number": 'set x to "a" plus 1\n',
            "constructor arity": class_base + "make an A called a\n",
            "missing field": class_base + "make an A called a with 1\nshow a.y\n",
            "list index": "make an empty list called xs\nshow xs at 3\n",
        }.items():
            with self.subTest(label):
                result = java_run(source)
                self.assertNotEqual(result.returncode, 0)
                self.assertTrue(result.stderr.strip(), "an error message is expected")
                with self.assertRaises(Exception):
                    interpreted(source)

    def test_input_prompt_and_python_style_printing(self):
        source = ('ask for your name and call it name\nshow "Hello " and name\n'
                  'make an empty list called xs\nadd 1 to xs\nadd "a" to xs\nshow xs\nset ratio to 10 divided by 4\nshow ratio\n'
                  'set whole to 10 divided by 5\nshow whole\nshow true\nshow none\n')
        result = java_run(source, "Ada\n")
        self.assertEqual(result.stdout, "Your name: Hello Ada\n[1, 'a']\n2.5\n2.0\nTrue\nNone\n", result.stderr)

    def test_problem_requests_are_not_supported_for_java_yet(self):
        with tempfile.TemporaryDirectory() as directory:
            en = Path(directory) / "p.en"
            en.write_text("target java\n# Sort the list of integers in ascending order.\n", encoding="utf-8")
            with self.assertRaises(CodeInEnglishError) as caught:
                generate_file(en)
            self.assertEqual(caught.exception.kind, "unsupported")


class JavaTargetPlanTests(unittest.TestCase):
    def test_check_reports_a_java_run_plan(self):
        import contextlib
        import io
        with tempfile.TemporaryDirectory() as directory:
            en = Path(directory) / "p.en"
            en.write_text("en 0.2\ntarget java\nset x to 1\nshow x\n", encoding="utf-8")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(main(["check", str(en), "--json"]), 0)
            payload = json.loads(out.getvalue())
            self.assertEqual((payload["target"], payload["plan"]["runtime"]), ("java", "java"))
            self.assertTrue(payload["plan"]["output_path"].endswith("p.java"))


if __name__ == "__main__":
    unittest.main()
