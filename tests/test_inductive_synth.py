import unittest

from codeinenglish.problem_recognizer import ProblemExample, ProblemPrompt, recognize_problem
from codeinenglish.inductive_synth import inductive_synthesize
from codeinenglish.problem_solver import render_problem_python
from codeinenglish.javascript_generator import generate_javascript, generate_java, generate_c


class InductiveSynthesisTests(unittest.TestCase):
    def test_inductive_discovers_single_op_from_novel_wording(self):
        # Novel wording never in any recipe or dictionary:
        prompt_text = "Perform arbitrary non-catalog filter for even elements"
        examples = (
            ProblemExample({"nums": [1, 2, 3, 4, 5, 6]}, [2, 4, 6], 1),
        )
        program = inductive_synthesize(examples, prompt_text)
        self.assertIsNotNone(program)
        self.assertEqual(program.function_name, "keep_even")

    def test_inductive_discovers_two_step_pipeline(self):
        # Filter evens then square each:
        prompt_text = "Unknown mystery math transformation"
        examples = (
            ProblemExample({"nums": [1, 2, 3, 4]}, [4, 16], 1),
        )
        program = inductive_synthesize(examples, prompt_text)
        self.assertIsNotNone(program)
        self.assertIn("keep_even", program.function_name)
        self.assertIn("square_each", program.function_name)

    def test_inductive_text_pipeline(self):
        # Reverse text from completely unlisted words:
        prompt_text = "Flipping the order of glyphs completely"
        examples = (
            ProblemExample({"text": "algorithm"}, "mhtirogla", 1),
        )
        program = inductive_synthesize(examples, prompt_text)
        self.assertIsNotNone(program)
        self.assertEqual(program.function_name, "reverse_text")

    def test_end_to_end_recognize_problem_with_inductive_fallback(self):
        prompt = ProblemPrompt(
            "Apply blackbox reduction logic across the integer elements",
            (1,),
            examples=(ProblemExample({"nums": [3, 9, 2, 8]}, 9, 1),),
        )
        # Without inductive synthesis, this novel phrasing would fail with EN-E305
        spec = recognize_problem(prompt, filename="test.en")
        self.assertIsNotNone(spec)
        self.assertEqual(spec.family.value, "synth")

        # Verify Python and JS code generators output valid runnable code
        py_code = render_problem_python(spec)
        self.assertIn("def maximum(", py_code)

        js_code = generate_javascript(spec, "test.en")
        self.assertIn("function maximum(", js_code)

        # Execute the generated Python code against the example
        env = {}
        exec(py_code, env)
        self.assertEqual(env["maximum"]([3, 9, 2, 8]), 9)


if __name__ == "__main__":
    unittest.main()
