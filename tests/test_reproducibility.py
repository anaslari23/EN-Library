import tempfile
import unittest
from pathlib import Path

from codeinenglish import generate_file


class ReproducibilityTests(unittest.TestCase):
    def test_same_source_generates_identical_instruction_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "hello.en"
            source.write_text('target python\nshow "Hello"\n', encoding="utf-8")
            first = generate_file(source, root / "first.py")
            second = generate_file(source, root / "second.py")
            self.assertEqual(first.read_bytes(), second.read_bytes())

    def test_same_source_generates_identical_problem_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "sort.en"
            source.write_text(
                "target python\n"
                "# Sort the list of integers in ascending order.\n"
                '# Example input: {"nums":[3,1,3,-2]}\n'
                "# Example output: [-2,1,3,3]\n",
                encoding="utf-8",
            )
            first = generate_file(source, root / "first.py")
            second = generate_file(source, root / "second.py")
            self.assertEqual(first.read_bytes(), second.read_bytes())


if __name__ == "__main__":
    unittest.main()
