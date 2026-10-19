import ast
import tempfile
import unittest
from pathlib import Path

from codeinenglish import CodeInEnglishError, translate, translate_file


class TranslateTests(unittest.TestCase):
    def test_translates_source_to_python(self):
        self.assertEqual(translate("set answer to 42"), "answer = 42")

    def test_source_filename_is_used_in_diagnostics(self):
        with self.assertRaises(CodeInEnglishError) as caught:
            translate("show missing", filename="problem.en")
        self.assertEqual(caught.exception.filename, "problem.en")
        self.assertEqual(caught.exception.line, 1)

    def test_assignment_phrase_aliases_generate_equivalent_python(self):
        set_form = ast.dump(ast.parse(translate("set answer to 40 plus 2")))
        let_form = ast.dump(ast.parse(translate("let answer be 40 plus 2")))
        self.assertEqual(set_form, let_form)

    def test_object_oriented_program_creates_instance_and_calls_method(self):
        example = Path(__file__).parent / "fixtures" / "greeter.en"
        english = example.read_text(encoding="utf-8")
        displayed = []
        exec(translate(english), {"print": displayed.append})
        self.assertEqual(displayed, ["Hello Ada"])


class CollectionProgramTests(unittest.TestCase):
    _algorithm = """set answer to none
make an empty dictionary called seen
set index to 0
for each number in nums
if answer is none then
set complement to target minus number
if complement is in seen then
make an empty list called answer
add seen at complement to answer
add index to answer
otherwise
set seen at number to index
end if
set index to index plus 1
end if
end for
if answer is none then
show \"No pair found\"
otherwise
show answer
end if"""

    @classmethod
    def source_for(cls, numbers, target):
        lines = ["make an empty list called nums"]
        lines.extend(f"add {number} to nums" for number in numbers)
        lines.extend([f"set target to {target}", cls._algorithm])
        return "\n".join(lines)

    def run_program(self, numbers, target):
        english = self.source_for(numbers, target)
        try:
            python_source = translate(english, filename="two_sum.en")
        except CodeInEnglishError as error:
            self.fail(f"Two Sum grammar did not translate: {error}")
        ast.parse(python_source)
        displayed = []
        exec(python_source, {"__builtins__": {}, "print": displayed.append})
        return displayed

    def test_finds_pair_at_zero_and_one(self):
        self.assertEqual(self.run_program([2, 7, 11, 15], 9), [[0, 1]])

    def test_finds_pair_with_duplicate_values(self):
        self.assertEqual(self.run_program([3, 3], 6), [[0, 1]])

    def test_finds_pair_after_first_item(self):
        self.assertEqual(self.run_program([3, 2, 4], 6), [[1, 2]])

    def test_reports_when_no_pair_exists(self):
        self.assertEqual(self.run_program([1, 2, 3], 7), ["No pair found"])

    def test_empty_list_reports_when_no_pair_exists(self):
        self.assertEqual(self.run_program([], 7), ["No pair found"])

    def test_two_sum_example_translates_and_displays_its_pair(self):
        example = Path(__file__).parent / "fixtures" / "two_sum.en"
        python_source = translate(example.read_text(encoding="utf-8"), filename=str(example))
        displayed = []
        exec(python_source, {"__builtins__": {}, "print": displayed.append})
        self.assertEqual(displayed, [[0, 1]])


class TranslateFileTests(unittest.TestCase):
    def test_default_and_explicit_output_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "program.en"
            source.write_text("set answer to 42", encoding="utf-8")
            self.assertEqual(translate_file(source), source.with_suffix(".py"))
            self.assertEqual(source.with_suffix(".py").read_text(encoding="utf-8"), "answer = 42\n")
            explicit = Path(directory) / "other.py"
            self.assertEqual(translate_file(source, explicit), explicit)
            self.assertEqual(explicit.read_text(encoding="utf-8"), "answer = 42\n")

    def test_preserves_source_and_existing_output_on_translation_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "program.en"
            output = Path(directory) / "program.py"
            source.write_text("show missing", encoding="utf-8")
            output.write_text("old code", encoding="utf-8")
            with self.assertRaises(CodeInEnglishError):
                translate_file(source)
            self.assertEqual(source.read_text(encoding="utf-8"), "show missing")
            self.assertEqual(output.read_text(encoding="utf-8"), "old code")

    def test_rejects_same_input_and_output_path(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "program.en"
            source.write_text("set answer to 42", encoding="utf-8")
            with self.assertRaises(CodeInEnglishError):
                translate_file(source, source)
            self.assertEqual(source.read_text(encoding="utf-8"), "set answer to 42")

    def test_missing_source_does_not_replace_existing_output(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "missing.en"
            output = Path(directory) / "program.py"
            output.write_text("old code", encoding="utf-8")
            with self.assertRaises(FileNotFoundError):
                translate_file(source, output)
            self.assertEqual(output.read_text(encoding="utf-8"), "old code")

    def test_generated_source_parses(self):
        source = translate('set value to 1 plus 2\nshow value')
        ast.parse(source)


if __name__ == "__main__":
    unittest.main()
