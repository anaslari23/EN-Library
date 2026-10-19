import ast
import unittest

from codeinenglish.ir import (
    Append,
    Attribute,
    Assign,
    Binary,
    Compare,
    Contains,
    CreateDictionary,
    CreateList,
    ClassDef,
    CreateInstance,
    Display,
    ForEach,
    If,
    Index,
    Literal,
    MethodCall,
    MethodDef,
    Name,
    Program,
    ReadInput,
    Return,
    SetAttribute,
    SetItem,
)
from codeinenglish.python_generator import generate_python


class GeneratePythonTests(unittest.TestCase):
    def assert_python_equal(self, actual, expected):
        self.assertEqual(ast.dump(ast.parse(actual)), ast.dump(ast.parse(expected)))

    def assert_program_equal(self, program, expected):
        try:
            source = generate_python(program)
        except TypeError as error:
            self.fail(f"generator does not support the collection IR: {error}")
        self.assert_python_equal(source, expected)

    def test_generates_assignments_and_input(self):
        program = Program([Assign("age", Literal(18)), ReadInput("name", "name")])
        self.assert_python_equal(generate_python(program), "age = 18\nname = input('Your name: ')")

    def test_generates_display_and_arithmetic(self):
        program = Program([
            Assign("total", Binary(Literal(2), "+", Binary(Literal(3), "*", Literal(4)))),
            Display([Literal("total: "), Name("total")]),
        ])
        self.assert_python_equal(
            generate_python(program),
            "total = 2 + 3 * 4\nprint(str('total: ') + str(total))",
        )

    def test_generates_comparison_and_conditional(self):
        program = Program([
            If(Compare(Name("age"), ">", Literal(18)), [Display([Literal("adult")])], [Display([Literal("child")])])
        ])
        self.assert_python_equal(
            generate_python(program),
            "if age > 18:\n    print('adult')\nelse:\n    print('child')",
        )

    def test_empty_conditional_branches_emit_pass(self):
        program = Program([If(Compare(Name("age"), "==", Literal(18)), [], [])])
        self.assert_python_equal(generate_python(program), "if age == 18:\n    pass\nelse:\n    pass")

    def test_omits_else_when_there_is_no_otherwise_marker(self):
        program = Program([If(Compare(Name("age"), ">", Literal(18)), [Display([Literal("adult")])], None)])
        self.assert_python_equal(generate_python(program), "if age > 18:\n    print('adult')")

    def test_generated_source_is_valid_python(self):
        source = generate_python(Program([Assign("answer", Literal(42))]))
        ast.parse(source)

    def test_generates_collection_creation_append_and_item_update(self):
        program = Program([
            CreateList("nums"),
            Append("nums", Literal(7)),
            CreateDictionary("seen"),
            SetItem("seen", Name("nums"), Literal(0)),
        ])
        self.assert_program_equal(
            program,
            "nums = []\nnums.append(7)\nseen = {}\nseen[nums] = 0",
        )

    def test_generates_membership_indexing_and_nested_loop(self):
        program = Program([
            CreateList("nums"),
            CreateDictionary("seen"),
            ForEach(
                "number",
                Name("nums"),
                [If(Contains(Name("number"), Name("seen")), [Display([Index(Name("seen"), Name("number"))])], None)],
            ),
        ])
        self.assert_program_equal(
            program,
            "nums = []\nseen = {}\nfor number in nums:\n    if number in seen:\n        print(seen[number])",
        )

    def test_empty_loop_body_emits_pass(self):
        program = Program([CreateList("nums"), ForEach("item", Name("nums"), [])])
        try:
            source = generate_python(program)
        except TypeError as error:
            self.fail(f"generator does not support the collection IR: {error}")
        self.assert_python_equal(source, "nums = []\nfor item in nums:\n    pass")

    def test_generates_class_with_method_instance_field_and_return(self):
        program = Program([
            ClassDef("Greeter", [MethodDef("greet", ["name"], [Return(Name("name"))])]),
            CreateInstance("Greeter", "greeter"),
            SetAttribute(Name("greeter"), "name", Literal("Ada")),
            Assign("greeting", MethodCall(Name("greeter"), "greet", [Attribute(Name("greeter"), "name")])),
        ])
        self.assert_program_equal(
            program,
            "class Greeter:\n    def greet(self, name):\n        return name\ngreeter = Greeter()\ngreeter.name = 'Ada'\ngreeting = greeter.greet(greeter.name)",
        )


if __name__ == "__main__":
    unittest.main()
