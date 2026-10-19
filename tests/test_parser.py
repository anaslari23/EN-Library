import unittest

from codeinenglish.errors import CodeInEnglishError
from codeinenglish.ir import Assign, Binary, Compare, Display, If, Literal, Name, Program, ReadInput
from codeinenglish.parser import parse_program


class ParseProgramTests(unittest.TestCase):
    def parse(self, source):
        return parse_program(source, "sample.en")

    def test_parses_assign_aliases_and_reads(self):
        program = self.parse('set age to 18\nlet total be age plus 2\nask for your name and call it name')
        self.assertEqual(
            program,
            Program([
                Assign("age", Literal(18)),
                Assign("total", Binary(Name("age"), "+", Literal(2))),
                ReadInput("name", "name"),
            ]),
        )

    def test_splits_display_and_outside_quoted_text(self):
        program = self.parse('set name to "Ada"\nshow "Hello and " and name')
        self.assertEqual(program.statements[-1], Display([Literal("Hello and "), Name("name")]))

    def test_parses_if_and_otherwise(self):
        program = self.parse('set age to 18\nif age is 18 then\nshow "yes"\notherwise\nshow "no"\nend if')
        self.assertEqual(
            program.statements[-1],
            If(Compare(Name("age"), "==", Literal(18)), [Display([Literal("yes")])], [Display([Literal("no")])]),
        )

    def test_allows_empty_if_branch(self):
        program = self.parse("set age to 1\nif age is 1 then\nend if")
        self.assertEqual(program.statements[-1], If(Compare(Name("age"), "==", Literal(1)), [], None))

    def test_preserves_an_explicit_empty_otherwise_branch(self):
        program = self.parse("set age to 1\nif age is 1 then\notherwise\nend if")
        self.assertEqual(program.statements[-1], If(Compare(Name("age"), "==", Literal(1)), [], []))

    def test_parses_nested_conditionals(self):
        program = self.parse(
            "set age to 1\nif age is 1 then\nif age is 1 then\nshow age\nend if\nend if"
        )
        outer = program.statements[-1]
        self.assertEqual(type(outer).__name__, "If")
        self.assertEqual(type(outer.body[0]).__name__, "If")

    def test_parses_collections_and_nested_blocks(self):
        source = (
            "make an empty list called nums\n"
            "add 7 to nums\n"
            "make an empty dictionary called seen\n"
            "for each number in nums\n"
            "if number is in seen then\n"
            "show number\n"
            "otherwise\n"
            "set seen at number to number\n"
            "end if\n"
            "end for"
        )
        program = self.parse(source)
        self.assertEqual(type(program.statements[0]).__name__, "CreateList")
        self.assertEqual(program.statements[0].name, "nums")
        self.assertEqual(type(program.statements[1]).__name__, "Append")
        self.assertEqual(program.statements[1].collection, "nums")
        self.assertEqual(program.statements[1].value, Literal(7))
        self.assertEqual(type(program.statements[2]).__name__, "CreateDictionary")
        loop = program.statements[3]
        self.assertEqual(type(loop).__name__, "ForEach")
        self.assertEqual(loop.name, "number")
        self.assertEqual(loop.collection, Name("nums"))
        self.assertEqual(type(loop.body[0]).__name__, "If")
        self.assertEqual(type(loop.body[0].condition).__name__, "Contains")
        self.assertEqual(type(loop.body[0].otherwise[0]).__name__, "SetItem")

    def test_parses_class_method_instance_fields_and_call(self):
        source = (
            "define a class called Greeter\n"
            "define a method called greet with parameter name\n"
            "return name\n"
            "end method\n"
            "end class\n"
            "make a Greeter called greeter\n"
            'set greeter.name to "Ada"\n'
            "set greeting to call greeter.greet with greeter.name\n"
            "show greeting"
        )
        program = self.parse(source)
        self.assertEqual(type(program.statements[0]).__name__, "ClassDef")
        self.assertEqual(program.statements[0].name, "Greeter")
        method = program.statements[0].methods[0]
        self.assertEqual((method.name, method.parameters), ("greet", ["name"]))
        self.assertEqual(type(program.statements[1]).__name__, "CreateInstance")
        self.assertEqual(type(program.statements[2]).__name__, "SetAttribute")
        self.assertEqual(type(program.statements[3].value).__name__, "MethodCall")

    def test_rejects_return_outside_method(self):
        with self.assertRaises(CodeInEnglishError) as caught:
            self.parse("return 1")
        self.assertEqual(caught.exception.kind, "unsupported")

    def test_loop_variable_is_local_to_loop_body(self):
        with self.assertRaises(CodeInEnglishError) as caught:
            self.parse("make an empty list called nums\nfor each item in nums\nshow item\nend for\nshow item")
        self.assertEqual(caught.exception.kind, "unknown_name")
        self.assertEqual(caught.exception.line, 5)

    def test_collection_addition_preserves_and_inside_quoted_text(self):
        program = self.parse('make an empty list called words\nadd "salt and pepper" to words')
        self.assertEqual(program.statements[1].value, Literal("salt and pepper"))

    def test_rejects_unknown_index_names_and_python_escape_syntax(self):
        cases = (
            ("make an empty dictionary called seen\nset seen at missing to 0", "unknown_name"),
            ("set value to object.attribute", "unknown_name"),
            ("import os", "unsupported"),
        )
        for source, kind in cases:
            with self.subTest(source=source), self.assertRaises(CodeInEnglishError) as caught:
                self.parse(source)
            self.assertEqual(caught.exception.kind, kind)

    def test_rejects_unknown_collection_values_and_python_calls(self):
        cases = (
            ("add 3 to missing", 1),
            ("make an empty list called nums\nfor each item in missing\nend for", 2),
            ("set value to __import__(\"os\")", 1),
        )
        for source, line in cases:
            with self.subTest(source=source), self.assertRaises(CodeInEnglishError) as caught:
                self.parse(source)
            self.assertEqual(caught.exception.line, line)

    def test_rejects_mismatched_and_unclosed_nested_blocks(self):
        cases = (
            ("end for", 1),
            ("make an empty list called nums\nfor each item in nums\nend if", 3),
            ("set age to 1\nif age is 1 then\nend for", 3),
            ("make an empty list called nums\nfor each item in nums", 2),
            ("set age to 1\nif age is 1 then\nmake an empty list called nums\nfor each item in nums", 4),
        )
        for source, line in cases:
            with self.subTest(source=source), self.assertRaises(CodeInEnglishError) as caught:
                self.parse(source)
            self.assertEqual(caught.exception.line, line)

    def test_reports_unknown_name(self):
        with self.assertRaises(CodeInEnglishError) as caught:
            self.parse("show missing")
        self.assertEqual(caught.exception.kind, "unknown_name")
        self.assertEqual((caught.exception.filename, caught.exception.line), ("sample.en", 1))

    def test_reports_ambiguous_unquoted_comparison_word(self):
        with self.assertRaises(CodeInEnglishError) as caught:
            self.parse("set status to 1\nif status is ready then\nend if")
        self.assertEqual(caught.exception.kind, "ambiguous")
        self.assertIn("quote", caught.exception.message)

    def test_rejects_unclosed_and_unmatched_blocks(self):
        for source, line in (("set age to 1\nif age is 1 then", 2), ("end if", 1), ("otherwise", 1)):
            with self.subTest(source=source), self.assertRaises(CodeInEnglishError) as caught:
                self.parse(source)
            self.assertEqual(caught.exception.line, line)

    def test_rejects_duplicate_otherwise(self):
        with self.assertRaises(CodeInEnglishError):
            self.parse("set age to 1\nif age is 1 then\notherwise\notherwise\nend if")

    def test_unknown_instruction_has_category_and_line(self):
        with self.assertRaises(CodeInEnglishError) as caught:
            self.parse("make a website")
        self.assertEqual(caught.exception.kind, "unsupported")
        self.assertEqual(caught.exception.line, 1)


if __name__ == "__main__":
    unittest.main()
