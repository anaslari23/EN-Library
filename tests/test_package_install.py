import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]


class InstalledPackageTests(unittest.TestCase):
    def test_installed_package_imports_and_solves_outside_checkout(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "site"
            outside = root / "outside"
            target.mkdir()
            outside.mkdir()
            install = subprocess.run(
                [sys.executable, "-m", "pip", "install", "--no-deps", "--no-build-isolation", "--target", str(target), str(ROOT)],
                text=True,
                capture_output=True,
            )
            self.assertEqual(install.returncode, 0, install.stderr)
            environment = os.environ.copy()
            environment["PYTHONPATH"] = str(target)
            imported = subprocess.run(
                [sys.executable, "-c", "import codeinenglish; assert callable(codeinenglish.solve_file)"],
                cwd=outside,
                env=environment,
                text=True,
                capture_output=True,
            )
            self.assertEqual(imported.returncode, 0, imported.stderr)
            source = root / "task.en"
            source.write_text(
                "# Find two numbers that add up to target and return their indices. Exactly one solution exists.\n"
                "# Example input: {\"nums\":[2,7,11],\"target\":9}\n"
                "# Example output: [0,1]\n",
                encoding="utf-8",
            )
            solved = subprocess.run(
                [sys.executable, "-m", "codeinenglish", "solve", str(source), "--output", str(root / "solution.py")],
                cwd=outside,
                env=environment,
                text=True,
                capture_output=True,
            )
            self.assertEqual(solved.returncode, 0, solved.stderr)
            checked = subprocess.run(
                [sys.executable, str(root / "solution.py"), "--check-examples"],
                cwd=outside,
                text=True,
                capture_output=True,
            )
            self.assertEqual(checked.returncode, 0, checked.stderr)
            self.assertIn("passed", checked.stdout.lower())


if __name__ == "__main__":
    unittest.main()
