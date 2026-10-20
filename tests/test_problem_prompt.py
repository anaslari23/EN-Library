import unittest
import json

from codeinenglish.errors import CodeInEnglishError
from codeinenglish.problem_prompt import ProblemPrompt, extract_problem_prompt, has_problem_directive


class ExtractProblemPromptTests(unittest.TestCase):
    def test_detects_exact_problem_library_directive(self):
        self.assertTrue(has_problem_directive("\nimport codeinpython library\n# Find a pair.\n"))
        self.assertFalse(has_problem_directive("# import codeinpython library\nshow 1"))
        self.assertFalse(has_problem_directive("import codeinpython\nlibrary"))

    def test_extracts_comment_text_and_maps_source_lines(self):
        prompt = extract_problem_prompt(
            "import codeinpython library\n\n# Find two values\n# that sum to a target.\n",
            "problem.en",
        )
        self.assertEqual(prompt, ProblemPrompt("Find two values\nthat sum to a target.", (3, 4)))

    def test_preserves_and_inside_quoted_prompt_text(self):
        prompt = extract_problem_prompt('# Return the phrase "bread and butter" unchanged')
        self.assertEqual(prompt.text, 'Return the phrase "bread and butter" unchanged')

    def test_accepts_problem_comments_without_library_directive(self):
        self.assertEqual(extract_problem_prompt("# Check if a word is a palindrome").text,
                         "Check if a word is a palindrome")

    def test_rejects_empty_or_code_mixed_prompts_with_location(self):
        for source, line in (("\n# \n", 2), ("# Find a pair\nprint('hi')", 2)):
            with self.subTest(source=source), self.assertRaises(CodeInEnglishError) as caught:
                extract_problem_prompt(source, "bad.en")
            self.assertEqual(caught.exception.filename, "bad.en")
            self.assertEqual(caught.exception.line, line)

    def test_extracts_multiple_json_example_pairs(self):
        prompt = extract_problem_prompt(
            '# Find the pair that sums to target.\n'
            '# Example input: {"nums": [2, 7], "target": 9}\n'
            '# Example output: [0, 1]\n'
            '# Example input: {"nums": [4, 6], "target": 10}\n'
            '# Example output: [0, 1]\n', "examples.en")
        self.assertEqual(prompt.text, "Find the pair that sums to target.")
        self.assertEqual(prompt.examples[0].input, {"nums": [2, 7], "target": 9})
        self.assertEqual(prompt.examples[0].expected, [0, 1])
        self.assertEqual(prompt.examples[0].source_line, 2)
        self.assertEqual(len(prompt.examples), 2)

    def test_examples_accept_json_scalar_array_and_null_outputs(self):
        for value in (None, True, 3, "text", [1, 2], {"x": 1}):
            with self.subTest(value=value):
                rendered = json.dumps(value)
                prompt = extract_problem_prompt(f'# Check something.\n# Example input: {{"text":"x"}}\n# Example output: {rendered}')
                self.assertEqual(prompt.examples[0].expected, value)

    def test_rejects_incomplete_or_malformed_example_pairs(self):
        cases = (
            ('# Do a thing.\n# Example input: {"x":1}', 2),
            ('# Do a thing.\n# Example output: 1', 2),
            ('# Do a thing.\n# Example input: {bad}\n# Example output: 1', 2),
            ('# Do a thing.\n# Example input: []\n# Example output: 1', 2),
        )
        for source, line in cases:
            with self.subTest(source=source):
                with self.assertRaises(CodeInEnglishError) as caught:
                    extract_problem_prompt(source, "bad_examples.en")
            self.assertEqual(caught.exception.line, line)


if __name__ == "__main__":
    unittest.main()
