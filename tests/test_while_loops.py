import io
import unittest

from codeinenglish.errors import CodeInEnglishError
from codeinenglish.evaluator import run
from codeinenglish.parser import parse
from codeinenglish.python_generator import generate_python
from codeinenglish.js_program import program_javascript as program_js
from codeinenglish.java_program import program_java
from codeinenglish.c_program import program_c


class WhileLoopTests(unittest.TestCase):
    def test_basic_while_loop_execution(self):
        source = (
            "set count to 1\n"
            "set total to 0\n"
            "while count is less than 5:\n"
            "set total to total plus count\n"
            "set count to count plus 1\n"
            "end while\n"
            "show total\n"
        )
        out = io.StringIO()
        program = parse(source)
        run(program, write=lambda v: out.write(str(v) + "\n"))
        self.assertEqual(out.getvalue().strip(), "10")

    def test_repeat_while_and_as_long_as_syntax(self):
        source1 = (
            "set i to 3\n"
            "repeat while i is greater than 0:\n"
            "set i to i minus 1\n"
            "end while\n"
            "show i\n"
        )
        out1 = io.StringIO()
        run(parse(source1), write=lambda v: out1.write(str(v) + "\n"))
        self.assertEqual(out1.getvalue().strip(), "0")

        source2 = (
            "set x to 2\n"
            "as long as x is greater than 0:\n"
            "set x to x minus 1\n"
            "end repeat\n"
            "show x\n"
        )
        out2 = io.StringIO()
        run(parse(source2), write=lambda v: out2.write(str(v) + "\n"))
        self.assertEqual(out2.getvalue().strip(), "0")

    def test_break_out_of_loop(self):
        source = (
            "set count to 1\n"
            "while count is less than 10:\n"
            "if count is equal to 4 then\n"
            "stop the loop\n"
            "end if\n"
            "set count to count plus 1\n"
            "end while\n"
            "show count\n"
        )
        out = io.StringIO()
        run(parse(source), write=lambda v: out.write(str(v) + "\n"))
        self.assertEqual(out.getvalue().strip(), "4")

    def test_continue_loop_iteration(self):
        source = (
            "set count to 0\n"
            "set evens to 0\n"
            "while count is less than 6:\n"
            "set count to count plus 1\n"
            "if count is equal to 2 then\n"
            "skip to next\n"
            "end if\n"
            "if count is equal to 4 then\n"
            "continue\n"
            "end if\n"
            "set evens to evens plus 1\n"
            "end while\n"
            "show evens\n"
        )
        out = io.StringIO()
        run(parse(source), write=lambda v: out.write(str(v) + "\n"))
        self.assertEqual(out.getvalue().strip(), "4")

    def test_break_outside_loop_raises_diagnostic(self):
        source = (
            "set x to 10\n"
            "stop the loop\n"
        )
        with self.assertRaises(CodeInEnglishError) as cm:
            parse(source)
        self.assertIn("loop", str(cm.exception))

    def test_continue_outside_loop_raises_diagnostic(self):
        source = (
            "set x to 10\n"
            "skip to next\n"
        )
        with self.assertRaises(CodeInEnglishError) as cm:
            parse(source)
        self.assertIn("loop", str(cm.exception))

    def test_unclosed_while_loop_raises_diagnostic(self):
        source = (
            "set x to 1\n"
            "while x is less than 5:\n"
            "set x to x plus 1\n"
        )
        with self.assertRaises(CodeInEnglishError) as cm:
            parse(source)
        self.assertIn("while block needs 'end while'", str(cm.exception))

    def test_polyglot_codegen_python(self):
        source = (
            "set n to 5\n"
            "while n is greater than 0:\n"
            "set n to n minus 1\n"
            "if n is equal to 2 then\n"
            "break out of the loop\n"
            "end if\n"
            "end while\n"
            "show n\n"
        )
        program = parse(source)
        py_code = generate_python(program)
        self.assertIn("while n > 0:", py_code)
        self.assertIn("break", py_code)

        env = {}
        exec(py_code, env)
        self.assertEqual(env["n"], 2)

    def test_polyglot_codegen_js(self):
        source = (
            "set n to 3\n"
            "while n is greater than 0:\n"
            "set n to n minus 1\n"
            "end while\n"
        )
        program = parse(source)
        js_code = program_js(program, "test.en")
        self.assertIn("while (enCompare(en_n, 0, '>')) {", js_code)

    def test_polyglot_codegen_java(self):
        source = (
            "set n to 3\n"
            "while n is greater than 0:\n"
            "set n to n minus 1\n"
            "end while\n"
        )
        program = parse(source)
        java_code = program_java(program, "test.en")
        self.assertIn("while (En.gt(en_n, Long.valueOf(0L))) {", java_code)

    def test_polyglot_codegen_c(self):
        source = (
            "set n to 3\n"
            "while n is greater than 0:\n"
            "set n to n minus 1\n"
            "end while\n"
        )
        program = parse(source)
        c_code = program_c(program, "test.en")
        self.assertIn("while (e_n > 0LL) {", c_code)


if __name__ == "__main__":
    unittest.main()
