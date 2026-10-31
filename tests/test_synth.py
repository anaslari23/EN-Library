"""Held-out evaluation of typed-combinator synthesis: requests the recipe catalog never listed.

Expected answers come from independent one-line Python, not from the engine's own operations."""
import unittest
from math import isclose

from codeinenglish.errors import CodeInEnglishError
from dataclasses import replace

from codeinenglish.problem_prompt import extract_problem_prompt
from codeinenglish.problem_recognizer import recognize_problem
from codeinenglish.problem_solver import render_problem_python
from codeinenglish import synth


def build(prompt):
    source = "import codeinpython library\n" + "".join(f"# {line}\n" for line in prompt.splitlines())
    extracted = extract_problem_prompt(source, "<test>")
    spec = replace(recognize_problem(extracted, "<test>"), examples=extracted.examples)
    namespace = {"__name__": "generated"}
    exec(compile(render_problem_python(spec), "<generated>", "exec"), namespace)
    return spec, namespace[spec.function_name]


def primes_to(n):
    return [v for v in range(2, n + 1) if all(v % d for d in range(2, int(v ** 0.5) + 1))]


POSITIVE = (
    ("Count the primes up to a number.", 20, len(primes_to(20))),
    ("Return the product of the odd numbers in a list.", [1, 2, 3, 4, 5], 15),
    ("Find the largest of the positive numbers in a list.", [-3, 4, 9, 2], 9),
    ("Count the words longer than 3 characters in a text.", "the quick brown fox", 2),
    ("Find the average of the squares of the numbers in a list.", [1, 2, 3], 14 / 3),
    ("Return the sum of the divisors of a number.", 12, 28),
    ("Sort the numbers in descending order and keep the first 3.", [5, 1, 9, 3, 7], [9, 7, 5]),
    ("Remove duplicates and then sort the numbers in ascending order.", [3, 1, 3, 2], [1, 2, 3]),
    ("Count the distinct numbers in a list.", [1, 1, 2], 2),
    ("Find the median of the even numbers in a list.", [1, 2, 4, 6, 7], 4),
    ("Find the number of digits in a number.", 12345, 5),
    ("Return the running totals of the odd numbers in a list.", [1, 2, 3, 4, 5], [1, 4, 9]),
    ("Return the cubes of the positive numbers in a list.", [-1, 2, 3], [8, 27]),
    ("Reverse the text and then make it uppercase.", "abc d", "D CBA"),
    ("Remove the vowels from a text and then reverse it.", "hello", "llh"),
    ("Check whether the binary form of a number is a palindrome.", 9, True),
    ("Check whether the binary form of a number is a palindrome.", 6, False),
    ("Is a number a perfect number?", 28, True),
    ("List the factors of a number.", 12, [1, 2, 3, 4, 6, 12]),
    ("Find the second largest of the numbers greater than 5 in a list.", [3, 9, 7, 6, 2], 7),
    ("Count the odd numbers in a list that are greater than 10.", [11, 12, 13, 5], 2),
    ("Add up the squares of the digits of a number.", 123, 14),
    ("Take the smallest of the numbers divisible by 3 in a list.", [9, 4, 6, 12, 5], 6),
    ("Return the last 2 numbers of the sorted list in ascending order.", [4, 1, 3, 2], [3, 4]),
)

REFUSED = (
    "Sum the numbers in a list that are not divisible by 3.",
    "Sum the even numbers in a list and email the result.",
    "Sort the numbers.",
    "Find the sum of the even numbers in a list except the first.",
    "Is the list of numbers sorted in ascending order?",
    "Count the primes between 3 and 20.",
    "Return the squares of the numbers greater than the average.",
    "Add the even numbers in a list and count the vowels in a text.",
    "Sort and reverse the list of numbers.",
)


class SynthesisTests(unittest.TestCase):
    def test_novel_requests_are_understood_and_correct(self):
        for prompt, given, expected in POSITIVE:
            with self.subTest(prompt=prompt, given=given):
                spec, function = build(prompt)
                got = function(given)
                if isinstance(expected, float):
                    self.assertTrue(isclose(got, expected), got)
                else:
                    self.assertEqual(got, expected)

    def test_polite_wrapping_never_changes_the_program(self):
        for prompt, given, expected in POSITIVE[:12]:
            with self.subTest(prompt=prompt):
                wrapped = "Please write a program that will " + prompt[0].lower() + prompt[1:]
                self.assertEqual(build(wrapped)[1](given), build(prompt)[1](given))

    def test_added_clauses_and_conditions_are_refused(self):
        for prompt, _, _ in POSITIVE:
            with self.subTest(prompt=prompt), self.assertRaises(CodeInEnglishError):
                build(prompt.rstrip(".") + " and print them in red.")

    def test_unsafe_or_unclear_requests_are_refused(self):
        for prompt in REFUSED:
            with self.subTest(prompt=prompt), self.assertRaises(CodeInEnglishError):
                build(prompt)

    def test_examples_decide_between_readings(self):
        spec, function = build("Find the square of the sum of the numbers in a list.\nExample input: {\"nums\":[1,2,3]}\nExample output: 36")
        self.assertEqual(function([1, 2]), 9)

    def test_an_example_no_reading_can_reproduce_is_rejected(self):
        with self.assertRaises(CodeInEnglishError):
            build("Add up the primes up to a number.\nExample input: {\"n\":10}\nExample output: 99")

    def test_negative_numbers_in_the_request_are_read_correctly(self):
        spec, function = build("Count the numbers greater than -2 that are even.")
        self.assertEqual(function([-3, -2, -1, 0, 2, 4]), 3)

    def test_huge_intermediate_values_fail_loudly_instead_of_hanging(self):
        spec, function = build("Add up the primes up to a number.")
        self.assertEqual(spec.family.value, "synth")
        self.assertEqual(function(10), 17)
        with self.assertRaises(ValueError):
            function(10 ** 9)

    def test_behaviourally_identical_orderings_are_not_ambiguous(self):
        program = synth.synthesize("sum the even positive numbers in a list")
        self.assertEqual(program.input_type, "ilist")
        spec, function = build("Sum the even positive numbers in a list.")
        self.assertEqual(function([-2, 2, 3, 4]), 6)

    def test_catalog_that_drops_a_word_is_overruled(self):
        spec, function = build("Return the cubes of the positive numbers in a list.")
        self.assertEqual(function([-1, 2, 3]), [8, 27])
        spec, function = build("Return the sum of the divisors of a number.")
        self.assertEqual(function(12), 28)


if __name__ == "__main__":
    unittest.main()
