import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from codeinenglish import CodeInEnglishError, generate_file


NODE = shutil.which("node")


class JavaScriptBackendTests(unittest.TestCase):
    @unittest.skipUnless(NODE, "Node.js is required for JavaScript behavior checks")
    def test_instruction_program_matches_python(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            en = root / "hello.en"
            en.write_text('target javascript\nset answer to 42\nshow answer\nshow true\n', encoding="utf-8")
            js = generate_file(en)
            self.assertEqual(js.suffix, ".js")
            subprocess.run([NODE, "--check", str(js)], capture_output=True, text=True, check=True)
            js_run = subprocess.run([NODE, str(js)], capture_output=True, text=True, check=True)
            en.write_text('target python\nset answer to 42\nshow answer\nshow true\n', encoding="utf-8")
            py = generate_file(en)
            py_run = subprocess.run(["python3", str(py)], capture_output=True, text=True, check=True)
            self.assertEqual(js_run.stdout, py_run.stdout)

    @unittest.skipUnless(NODE, "Node.js is required for JavaScript behavior checks")
    def test_sort_problem_matches_python_and_examples(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            en = root / "sort.en"
            body = ('# Sort the list of integers in ascending order.\n'
                    '# Example input: {"nums":[3,1,3,-2]}\n'
                    '# Example output: [-2,1,3,3]\n')
            en.write_text("target javascript\n" + body, encoding="utf-8")
            js = generate_file(en)
            self.assertEqual(js.suffix, ".js")
            subprocess.run([NODE, "--check", str(js)], capture_output=True, text=True, check=True)
            checked = subprocess.run([NODE, str(js), "--check-examples"], capture_output=True, text=True, check=True)
            self.assertIn("All 1 examples passed.", checked.stdout)
            sample = json.dumps({"nums": [3, 1, 3, -2]})
            js_run = subprocess.run([NODE, str(js)], input=sample, capture_output=True, text=True, check=True)
            en.write_text("target python\n" + body, encoding="utf-8")
            py = generate_file(en)
            py_run = subprocess.run(["python3", str(py)], input=sample, capture_output=True, text=True, check=True)
            self.assertEqual(json.loads(js_run.stdout), json.loads(py_run.stdout))

    def test_unsupported_javascript_program_preserves_existing_output(self):
        with tempfile.TemporaryDirectory() as directory:
            en = Path(directory) / "program.en"
            en.write_text('target javascript\nmake an empty list called numbers\n', encoding="utf-8")
            output = en.with_suffix(".js")
            output.write_text("old source", encoding="utf-8")
            with self.assertRaises(CodeInEnglishError) as caught:
                generate_file(en)
            self.assertEqual(caught.exception.kind, "unsupported")
            self.assertEqual(output.read_text(encoding="utf-8"), "old source")

    def test_unsupported_javascript_problem_preserves_existing_output(self):
        with tempfile.TemporaryDirectory() as directory:
            en = Path(directory) / "program.en"
            en.write_text('target javascript\n# Find the largest number in the list.\n', encoding="utf-8")
            output = en.with_suffix(".js")
            output.write_text("old source", encoding="utf-8")
            with self.assertRaises(CodeInEnglishError) as caught:
                generate_file(en)
            self.assertEqual(caught.exception.kind, "unsupported")
            self.assertEqual(output.read_text(encoding="utf-8"), "old source")
