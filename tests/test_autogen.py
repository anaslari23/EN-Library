import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ("import codeinenglish\n\n# write a program to find two numbers that add up to the target\n"
          "# and return their indices. Exactly one solution exists.\n\nprint(two_sum([2, 7, 11, 15], 9))\n")


def run_script(text):
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "script.py"
        path.write_text(text, encoding="utf-8")
        return subprocess.run([sys.executable, str(path)], capture_output=True, text=True,
                              env={"PYTHONPATH": str(ROOT), "PATH": ""}, cwd=directory)


class ImportGenerationTests(unittest.TestCase):
    def test_import_generates_function_from_comment(self):
        result = run_script(SCRIPT)
        self.assertEqual((result.returncode, result.stdout.strip()), (0, "(0, 1)"), result.stderr)

    def test_import_generation_works_from_a_zip_file_with_no_install(self):
        import subprocess as sp
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "en.pyz"
            sp.run([sys.executable, str(ROOT / "scripts" / "build_zipapp.py")], check=True, capture_output=True)
            archive.write_bytes((ROOT / "dist" / "en.pyz").read_bytes())
            script = Path(directory) / "s.py"
            script.write_text("import codeinenglish\n# write a program to find the median of a list of numbers\nprint(find_median([4, 1, 3, 2]))\n")
            result = sp.run([sys.executable, str(script)], capture_output=True, text=True, env={"PYTHONPATH": str(archive), "PATH": ""}, cwd=directory)
            self.assertEqual((result.returncode, result.stdout.strip()), (0, "2.5"), result.stderr)

    def test_import_without_trigger_comment_does_nothing(self):
        result = run_script("import codeinenglish\nprint('plain')\n")
        self.assertEqual((result.returncode, result.stdout.strip()), (0, "plain"), result.stderr)

    def test_unsupported_request_fails_loudly_on_import(self):
        result = run_script("import codeinenglish\n# write a program to compose a symphony\n")
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
