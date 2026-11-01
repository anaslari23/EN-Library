import io
import unittest

from codeinenglish.repl import start_repl


class ReplTests(unittest.TestCase):
    def test_repl_exit(self):
        inp = io.StringIO("exit\n")
        out = io.StringIO()
        start_repl(input_stream=inp, output_stream=out)
        self.assertIn("EN Language 0.2 Interactive Shell", out.getvalue())
        self.assertIn("Goodbye!", out.getvalue())

    def test_repl_variable_assignment_and_expression(self):
        inp = io.StringIO("set score to 10\nincrease score by 5\nscore\nexit\n")
        out = io.StringIO()
        start_repl(input_stream=inp, output_stream=out)
        output = out.getvalue()
        self.assertIn("15", output)

    def test_repl_multiline_while_loop(self):
        script = (
            "set count to 1\n"
            "set total to 0\n"
            "while count is less than 4:\n"
            "    set total to total plus count\n"
            "    set count to count plus 1\n"
            "end while\n"
            "show total\n"
            "exit\n"
        )
        inp = io.StringIO(script)
        out = io.StringIO()
        start_repl(input_stream=inp, output_stream=out)
        output = out.getvalue()
        self.assertIn("6", output)

    def test_repl_help_and_vars_commands(self):
        script = "set hero to \"Aria\"\nvars\nhelp\nexit\n"
        inp = io.StringIO(script)
        out = io.StringIO()
        start_repl(input_stream=inp, output_stream=out)
        output = out.getvalue()
        self.assertIn("hero = 'Aria'", output)
        self.assertIn("EN Language Quick Reference:", output)

    def test_repl_error_recovery(self):
        script = "set valid to 42\nmalformed instruction here\nshow valid\nexit\n"
        inp = io.StringIO(script)
        out = io.StringIO()
        start_repl(input_stream=inp, output_stream=out)
        output = out.getvalue()
        self.assertIn("Error:", output)
        self.assertIn("42", output)


if __name__ == "__main__":
    unittest.main()

