import io
import unittest

from codeinenglish.errors import CodeInEnglishError
from codeinenglish.evaluator import run
from codeinenglish.parser import parse
from codeinenglish.python_generator import generate_python
from codeinenglish.js_program import program_javascript as program_js
from codeinenglish.java_program import program_java
from codeinenglish.c_program import program_c


class FunctionTests(unittest.TestCase):
    def test_basic_function_definition_and_call(self):
        source = (
            "define a function named add taking a and b\n"
            "return a plus b\n"
            "end function\n"
            "set result to call add with 12 and 8\n"
            "show result\n"
        )
        out = io.StringIO()
        program = parse(source)
        run(program, write=lambda v: out.write(str(v) + "\n"))
        self.assertEqual(out.getvalue().strip(), "20")

    def test_shorthand_to_function_definition(self):
        source = (
            "to multiply taking x and y:\n"
            "return x times y\n"
            "end function\n"
            "set product to call multiply with 6 and 7\n"
            "show product\n"
        )
        out = io.StringIO()
        program = parse(source)
        run(program, write=lambda v: out.write(str(v) + "\n"))
        self.assertEqual(out.getvalue().strip(), "42")

    def test_function_with_no_parameters(self):
        source = (
            "to get_answer:\n"
            "return 42\n"
            "end function\n"
            "set ans to call get_answer\n"
            "show ans\n"
        )
        out = io.StringIO()
        program = parse(source)
        run(program, write=lambda v: out.write(str(v) + "\n"))
        self.assertEqual(out.getvalue().strip(), "42")

    def test_function_local_scope(self):
        source = (
            "set total to 100\n"
            "define a function named calculate taking value\n"
            "set total to value times 2\n"
            "return total\n"
            "end function\n"
            "set res to call calculate with 5\n"
            "show total\n"
            "show res\n"
        )
        out = io.StringIO()
        program = parse(source)
        run(program, write=lambda v: out.write(str(v) + "\n"))
        lines = out.getvalue().strip().split("\n")
        self.assertEqual(lines, ["100", "10"])

    def test_function_polyglot_python(self):
        source = (
            "to square taking n:\n"
            "return n times n\n"
            "end function\n"
            "set sq to call square with 9\n"
        )
        program = parse(source)
        py_code = generate_python(program)
        self.assertIn("def square(n):", py_code)
        self.assertIn("sq = square(9)", py_code)

        env = {}
        exec(py_code, env)
        self.assertEqual(env["sq"], 81)

    def test_function_polyglot_js(self):
        source = (
            "to double taking n:\n"
            "return n plus n\n"
            "end function\n"
            "set d to call double with 5\n"
        )
        program = parse(source)
        js_code = program_js(program, "test.en")
        self.assertIn("function en_double(en_n) {", js_code)
        self.assertIn("en_d = en_double(5);", js_code)

    def test_function_polyglot_java(self):
        source = (
            "to double taking n:\n"
            "return n plus n\n"
            "end function\n"
            "set d to call double with 5\n"
        )
        program = parse(source)
        java_code = program_java(program, "test.en")
        self.assertIn("static Object en_double(Object en_n) {", java_code)
        self.assertIn("en_d = en_double(Long.valueOf(5L));", java_code)

    def test_function_polyglot_c(self):
        source = (
            "to double taking n:\n"
            "return n plus n\n"
            "end function\n"
            "set d to call double with 5\n"
        )
        program = parse(source)
        c_code = program_c(program, "test.en")
        self.assertIn("static long long e_double(long long e_n) {", c_code)
        self.assertIn("e_d = e_double(5LL);", c_code)


if __name__ == "__main__":
    unittest.main()

