import random
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

SEED = Path(__file__).resolve().parents[1] / "seed"
sys.path.insert(0, str(SEED))

import en as seed_en  # noqa: E402
import classfuzz  # noqa: E402
import fuzz  # noqa: E402

HAS_NODE, HAS_CC = bool(shutil.which("node")), bool(shutil.which("cc"))


@unittest.skipUnless(HAS_NODE, "needs Node.js")
class SeedAgreesWithFullEnglishTests(unittest.TestCase):
    def test_random_programs_print_the_same_in_every_language(self):
        for number in range(25):
            source = fuzz.program(random.Random(number))
            with self.subTest(seed=number):
                expected = fuzz.full(source)
                for language, output in fuzz.seeds(source, with_c=HAS_CC).items():
                    self.assertEqual(output, expected, f"{language}\n{source}")

    def test_the_javascript_seed_matches_too(self):
        script = ("const en = require(%r); const out = []; const log = console.log; console.log = s => out.push(s);"
                  "en(require('fs').readFileSync(0, 'utf8')); console.log = log; process.stdout.write(out.map(s => s + '\\n').join(''));" % str(SEED / "en.js"))
        for number in range(25):
            source = fuzz.program(random.Random(number))
            with self.subTest(seed=number):
                result = subprocess.run(["node", "-e", script], input=source, capture_output=True, text=True)
                self.assertEqual(result.stdout, fuzz.full(source), result.stderr)

    def test_whole_numbers_beyond_32_bits_agree_in_every_language(self):
        source = "set big to 100000 times 100000\nshow big\nset more to big times 30\nshow \"more=\" and more\n"
        expected = fuzz.full(source)
        self.assertEqual(expected, "10000000000\nmore=300000000000\n")
        for language, output in fuzz.seeds(source, with_c=HAS_CC).items():
            self.assertEqual(output, expected, language)

    def test_an_empty_branch_is_valid_python(self):
        source = "set x to 1\nif x is 1 then\notherwise\nshow 2\nend if\nshow 3\n"
        for language, output in fuzz.seeds(source, with_c=HAS_CC).items():
            self.assertEqual(output, "3\n", language)

    def test_random_class_programs_match_in_python_and_javascript(self):
        script = ("const en = require(%r); const out = []; const log = console.log; console.log = s => out.push(s);"
                  "en(require('fs').readFileSync(0, 'utf8')); console.log = log; process.stdout.write(out.map(s => s + '\\n').join(''));" % str(SEED / "en.js"))
        for number in range(25):
            source = classfuzz.program(random.Random(number))
            with self.subTest(seed=number):
                expected = fuzz.full(source)
                for language, output in fuzz.seeds(source, with_c=False).items():
                    self.assertEqual(output, expected, f"{language}\n{source}")
                browser = subprocess.run(["node", "-e", script], input=source, capture_output=True, text=True)
                self.assertEqual(browser.stdout, expected, browser.stderr)

    def test_classes_are_not_pretended_in_c(self):
        with self.assertRaises(SystemExit):
            seed_en.compile("define a class called A\nend class", "c")

    def test_the_seed_stays_small_enough_to_retype(self):
        self.assertLess((SEED / "en.py").stat().st_size, 6500)
        self.assertLess((SEED / "en.js").stat().st_size, 3200)

    def test_unknown_lines_are_refused(self):
        with self.assertRaises(SystemExit):
            seed_en.compile("fly to the moon", "py")


if __name__ == "__main__":
    unittest.main()
