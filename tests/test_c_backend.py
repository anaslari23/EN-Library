import random
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from codeinenglish import CodeInEnglishError, generate_file

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "seed"))
import fuzz  # noqa: E402

CC = shutil.which("cc")


def build_and_run(source):
    with tempfile.TemporaryDirectory() as directory:
        en = Path(directory) / "p.en"
        en.write_text("target c\n" + source, encoding="utf-8")
        c_file = generate_file(en)
        built = subprocess.run([CC, "-Wall", "-Werror", "-o", str(Path(directory) / "p"), str(c_file)], capture_output=True, text=True)
        assert built.returncode == 0, built.stderr
        return subprocess.run([str(Path(directory) / "p")], capture_output=True, text=True)


@unittest.skipUnless(CC, "needs a C compiler (cc)")
class CBackendTests(unittest.TestCase):
    def test_random_programs_print_what_the_interpreter_prints(self):
        for number in range(40):
            source = fuzz.program(random.Random(1000 + number))
            if not source.strip():
                continue  # an empty program is not a program
            with self.subTest(seed=1000 + number):
                self.assertEqual(build_and_run(source).stdout, fuzz.full(source), source)

    def test_big_numbers_and_nested_loops(self):
        source = ("set big to 100000 times 100000\nshow big\nmake an empty list called xs\nadd 1 to xs\nadd 2 to xs\n"
                  "for each a in xs\nfor each b in xs\nshow a times 10 plus b\nend for\nend for\n")
        self.assertEqual(build_and_run(source).stdout, "10000000000\n11\n12\n21\n22\n")

    def test_unsupported_things_are_refused_not_mistranslated(self):
        for label, source in {
            "division": "set x to 10 divided by 4\n",
            "text plus": 'set x to "a" plus "b"\n',
            "classes": "define a class called A\nend class\n",
            "dictionary": "make an empty dictionary called d\n",
            "input": "ask for your name and call it name\n",
            "text in list": 'make an empty list called xs\nadd "a" to xs\n',
        }.items():
            with self.subTest(label), tempfile.TemporaryDirectory() as directory:
                en = Path(directory) / "p.en"
                en.write_text("target c\n" + source, encoding="utf-8")
                with self.assertRaises(CodeInEnglishError) as caught:
                    generate_file(en)
                self.assertEqual(caught.exception.kind, "unsupported")


if __name__ == "__main__":
    unittest.main()
