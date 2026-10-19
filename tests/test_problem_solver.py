import ast
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from codeinenglish import solve, solve_file
from codeinenglish.errors import CodeInEnglishError
from codeinenglish.problem_prompt import extract_problem_prompt


class ProblemSolverTests(unittest.TestCase):
    def test_generated_program_reads_json_and_writes_json(self):
        source = solve("# Find two numbers that add up to target and return their indices. Exactly one solution exists.")
        with tempfile.TemporaryDirectory() as directory:
            program = Path(directory) / "solution.py"
            program.write_text(source, encoding="utf-8")
            result = subprocess.run([sys.executable, str(program)], input='{"nums":[2,7,11],"target":9}', text=True, capture_output=True, check=True)
        self.assertEqual(result.stdout.strip(), "[0, 1]")

    def test_generated_program_reports_missing_and_extra_json_keys(self):
        source = solve("# Return the largest number in the list.")
        with tempfile.TemporaryDirectory() as directory:
            program = Path(directory) / "solution.py"
            program.write_text(source, encoding="utf-8")
            missing = subprocess.run([sys.executable, str(program)], input='{}', text=True, capture_output=True)
            extra = subprocess.run([sys.executable, str(program)], input='{"nums":[1],"other":2}', text=True, capture_output=True)
        self.assertNotEqual(missing.returncode, 0)
        self.assertIn("nums", missing.stderr)
        self.assertNotEqual(extra.returncode, 0)
        self.assertIn("exactly", extra.stderr)

    def test_generated_example_checker_passes_and_fails(self):
        source = solve(
            "# Return the largest number in the list.\n"
            "# Example input: {\"nums\":[1,5,2]}\n"
            "# Example output: 5")
        with tempfile.TemporaryDirectory() as directory:
            program = Path(directory) / "solution.py"
            program.write_text(source, encoding="utf-8")
            passed = subprocess.run([sys.executable, str(program), "--check-examples"], text=True, capture_output=True)
            wrong_source = solve(
                "# Return the largest number in the list.\n"
                "# Example input: {\"nums\":[1,5,2]}\n"
                "# Example output: 4")
            program.write_text(wrong_source, encoding="utf-8")
            failed = subprocess.run([sys.executable, str(program), "--check-examples"], text=True, capture_output=True)
        self.assertEqual(passed.returncode, 0, passed.stderr)
        self.assertIn("passed", passed.stdout)
        self.assertNotEqual(failed.returncode, 0)
        self.assertIn("example failed: 1", failed.stderr.lower())

    def test_example_checker_refuses_to_claim_success_without_examples(self):
        generated = solve("# Return the largest number in the list.")
        with tempfile.TemporaryDirectory() as directory:
            program = Path(directory) / "solution.py"
            program.write_text(generated, encoding="utf-8")
            result = subprocess.run([sys.executable, str(program), "--check-examples"], text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("no examples", result.stderr.lower())

    def test_generated_source_discloses_interpretation_and_assumptions(self):
        generated = solve("# Find two numbers that add up to target and return their indices.")
        self.assertIn("# Interpreted request:", generated)
        self.assertIn("# Defaulted assumption: There may be no matching pair.", generated)
        self.assertIn("# Defaulted assumption: Return null when no pair exists.", generated)
        self.assertIn("# Defaulted assumption: Return the first matching pair in left-to-right order.", generated)

    def test_every_problem_example_generates_and_passes_its_embedded_check(self):
        examples = Path(__file__).parent / "fixtures"
        for source in sorted(examples.glob("*_problem.en")):
            with self.subTest(example=source.name):
                generated = solve(source.read_text(encoding="utf-8"), str(source))
                ast.parse(generated)
                with tempfile.TemporaryDirectory() as directory:
                    program = Path(directory) / "solution.py"
                    program.write_text(generated, encoding="utf-8")
                    result = subprocess.run([sys.executable, str(program), "--check-examples"], text=True, capture_output=True)
                    sample = extract_problem_prompt(source.read_text(encoding="utf-8"), str(source)).examples[0]
                    run_result = subprocess.run([sys.executable, str(program)], input=json.dumps(sample.input), text=True, capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(run_result.returncode, 0, run_result.stderr)
                self.assertEqual(json.loads(run_result.stdout), sample.expected)

    def test_generated_runner_checks_field_types_and_sorted_lists(self):
        generated = solve("# Find target in a sorted list and return its index or -1 if absent.")
        with tempfile.TemporaryDirectory() as directory:
            program = Path(directory) / "solution.py"
            program.write_text(generated, encoding="utf-8")
            wrong_type = subprocess.run([sys.executable, str(program)], input='{"nums":"1,2","target":1}', text=True, capture_output=True)
            unsorted = subprocess.run([sys.executable, str(program)], input='{"nums":[2,1],"target":1}', text=True, capture_output=True)
        self.assertNotEqual(wrong_type.returncode, 0)
        self.assertIn("sorted_integer_list", wrong_type.stderr)
        self.assertNotEqual(unsorted.returncode, 0)
        self.assertIn("sorted in ascending", unsorted.stderr)
    def test_two_sum_example_end_to_end(self):
        example = Path(__file__).parent / "fixtures" / "two_sum_problem.en"
        generated = solve(example.read_text(encoding="utf-8"), str(example))
        ast.parse(generated)
        namespace = {}
        exec(generated, namespace)
        self.assertEqual(namespace["two_sum"]([2, 7, 11, 15], 9), (0, 1))

    def test_generates_python_and_omits_library_directive(self):
        generated = solve("import codeinpython library\n# Find two numbers that add up to target and return their indices. Exactly one solution exists.")
        ast.parse(generated)
        self.assertIn("def two_sum(nums, target):", generated)
        self.assertNotIn("codeinpython", generated)

    def test_file_output_defaults_and_explicit_path(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "task.en"
            source.write_text("# Return the largest number in the list.", encoding="utf-8")
            self.assertEqual(solve_file(source), source.with_suffix(".py"))
            output = Path(directory) / "result.py"
            self.assertEqual(solve_file(source, output), output)
            ast.parse(output.read_text(encoding="utf-8"))

    def test_failure_preserves_existing_output(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "task.en"
            output = Path(directory) / "task.py"
            source.write_text("# Invent a new algorithm.", encoding="utf-8")
            output.write_text("keep me", encoding="utf-8")
            with self.assertRaises(CodeInEnglishError):
                solve_file(source, output)
            self.assertEqual(output.read_text(encoding="utf-8"), "keep me")


if __name__ == "__main__":
    unittest.main()
