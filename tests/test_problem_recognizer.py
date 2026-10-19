import unittest

from codeinenglish.errors import CodeInEnglishError
from codeinenglish.problem_prompt import ProblemPrompt
from codeinenglish.problem_recognizer import ProblemAssumption, ProblemFamily, recognize_problem


class RecognizeProblemTests(unittest.TestCase):
    def recognize(self, text):
        return recognize_problem(ProblemPrompt(text, (1,)))

    def test_recognizes_two_sum_indices_from_two_phrasings(self):
        prompts = (
            "Given an array of integers nums and a target, return the indices of two numbers that add up to target. Exactly one solution exists and do not reuse an element.",
            "Find the positions of two different values in a list whose total equals the target number. Exactly one pair exists.",
        )
        for prompt in prompts:
            with self.subTest(prompt=prompt):
                spec = self.recognize(prompt)
                self.assertEqual(spec.family, ProblemFamily.TWO_SUM)
                self.assertEqual([item.name for item in spec.inputs], ["nums", "target"])
                self.assertEqual(spec.result, "indices")

    def test_recognizes_duplicate_and_frequency_requests(self):
        cases = (
            ("Determine whether any value appears more than once in the list.", ProblemFamily.DUPLICATES),
            ("Return the number of occurrences of each number in this array.", ProblemFamily.FREQUENCIES),
            ("Check if the collection contains a repeated value.", ProblemFamily.DUPLICATES),
            ("Count how often every distinct integer occurs.", ProblemFamily.FREQUENCIES),
            ("Tell me whether any number is repeated.", ProblemFamily.DUPLICATES),
            ("Give the count for every distinct value in the collection.", ProblemFamily.FREQUENCIES),
        )
        for prompt, expected in cases:
            with self.subTest(prompt=prompt):
                self.assertEqual(self.recognize(prompt).family, expected)

    def test_recognizes_palindrome_and_anagram_requests(self):
        cases = (
            ("Check whether a word reads the same forward and backward.", ProblemFamily.PALINDROME),
            ("Determine if this text is a palindrome.", ProblemFamily.PALINDROME),
            ("Check whether two strings are anagrams.", ProblemFamily.ANAGRAM),
            ("Determine if one word can be rearranged to make the other.", ProblemFamily.ANAGRAM),
            ("Check if this phrase reads the same forward and backward.", ProblemFamily.PALINDROME),
            ("Determine whether two words contain the same letters in a different order.", ProblemFamily.ANAGRAM),
        )
        for prompt, expected in cases:
            with self.subTest(prompt=prompt):
                self.assertEqual(self.recognize(prompt).family, expected)

    def test_recognizes_sorted_search_and_aggregates(self):
        cases = (
            ("Find target in a sorted array and return its index or -1 if absent.", ProblemFamily.BINARY_SEARCH),
            ("Search an ordered list for the target value and give its position.", ProblemFamily.BINARY_SEARCH),
            ("Return the largest integer in the list.", ProblemFamily.MAXIMUM),
            ("Find the smallest value in the array.", ProblemFamily.MINIMUM),
            ("Calculate the total of all numbers in the list.", ProblemFamily.SUM),
            ("Locate the target in an ascending sequence and return its position.", ProblemFamily.BINARY_SEARCH),
            ("Give me the biggest value in this array.", ProblemFamily.MAXIMUM),
            ("Find the least value in these numbers.", ProblemFamily.MINIMUM),
            ("Add up every number in the sequence.", ProblemFamily.SUM),
        )
        for prompt, expected in cases:
            with self.subTest(prompt=prompt):
                self.assertEqual(self.recognize(prompt).family, expected)

    def test_rejects_negated_or_ambiguous_intent_instead_of_guessing(self):
        cases = (
            "Find two numbers that do not add up to the target and return their positions.",
            "Search for target in this list.",
            "Find the maximum and minimum values and return their difference.",
            "Do not check whether this word is a palindrome.",
        )
        for prompt in cases:
            with self.subTest(prompt=prompt), self.assertRaises(CodeInEnglishError):
                self.recognize(prompt)

    def test_records_stated_and_defaulted_pair_sum_behavior(self):
        stated = self.recognize("Find two numbers that add to target and return their indices. Exactly one solution exists; do not reuse an element.")
        defaults = self.recognize("Find two numbers that add to target and return their indices.")
        self.assertIn(ProblemAssumption("Exactly one matching pair is guaranteed.", "stated"), stated.assumptions)
        self.assertIn(ProblemAssumption("Return the first matching pair in left-to-right order.", "defaulted"), defaults.assumptions)
        self.assertIn(ProblemAssumption("There may be no matching pair.", "defaulted"), defaults.assumptions)
        self.assertIn(ProblemAssumption("Return null when no pair exists.", "defaulted"), defaults.assumptions)

    def test_reports_search_and_text_defaults(self):
        search = self.recognize("Find target in a sorted list and return its index or -1 if absent.")
        self.assertIn(ProblemAssumption("Input is sorted in ascending order.", "defaulted"), search.assumptions)
        self.assertIn(ProblemAssumption("Return the first matching index.", "defaulted"), search.assumptions)
        self.assertIn(ProblemAssumption("Return -1 when the value is absent.", "stated"), search.assumptions)
        palindrome = self.recognize("Check if the text is a palindrome.")
        self.assertIn(ProblemAssumption("Compare case-sensitively.", "defaulted"), palindrome.assumptions)
        self.assertIn(ProblemAssumption("Punctuation is significant.", "defaulted"), palindrome.assumptions)
        self.assertIn(ProblemAssumption("Whitespace is significant.", "defaulted"), palindrome.assumptions)
        case_rule = self.recognize("Check if a word is a palindrome; ignore case.")
        self.assertIn("case_insensitive", case_rule.constraints)

    def test_rejects_unsupported_anagram_punctuation_qualifier(self):
        with self.assertRaises(CodeInEnglishError):
            self.recognize("Check whether two strings are anagrams ignoring punctuation.")

    def test_rejects_conflicting_text_policies_and_descending_binary_search(self):
        cases = (
            "Check if text is a palindrome, case-sensitive and ignoring case.",
            "Check if text is a palindrome ignoring whitespace while whitespace matters.",
            "Search for target in a descending sorted list and return its index.",
        )
        for prompt in cases:
            with self.subTest(prompt=prompt), self.assertRaises(CodeInEnglishError):
                self.recognize(prompt)

    def test_rejects_conflicting_anagram_policies(self):
        for prompt in (
            "Check whether two strings are anagrams, case-sensitive and ignoring case.",
            "Check whether two strings are anagrams ignoring whitespace while whitespace matters.",
        ):
            with self.subTest(prompt=prompt), self.assertRaises(CodeInEnglishError):
                self.recognize(prompt)

    def test_rejects_conflicting_or_unsupported_pair_result_requirements(self):
        for prompt in (
            "Find two numbers adding to target and return every matching pair of indices.",
            "Find two numbers adding to target and return an empty list if none exist.",
        ):
            with self.subTest(prompt=prompt), self.assertRaises(CodeInEnglishError):
                self.recognize(prompt)

    def test_recognizes_six_additional_problem_families(self):
        cases = (
            ("Find the first non-repeating character in a string.", "first_unique_character"),
            ("Return the first character that occurs once in the text.", "first_unique_character"),
            ("Find the first unique character ignoring case.", "first_unique_character"),
            ("Reverse the given word.", "reverse_text"),
            ("Return this string in reverse order.", "reverse_text"),
            ("Move every zero to the end of the list while keeping the other numbers in order.", "move_zeros"),
            ("Shift all zero values to the end of the array and preserve order.", "move_zeros"),
            ("Merge two sorted integer lists into one sorted list.", "merge_sorted_lists"),
            ("Combine these two ascending arrays into sorted order.", "merge_sorted_lists"),
            ("Find the largest sum of a contiguous part of the list.", "maximum_subarray_sum"),
            ("Return the maximum contiguous subarray total.", "maximum_subarray_sum"),
            ("Check whether the parentheses are balanced.", "has_balanced_delimiters"),
            ("Determine if all brackets and braces are properly matched.", "has_balanced_delimiters"),
        )
        for prompt, expected in cases:
            with self.subTest(prompt=prompt):
                self.assertEqual(self.recognize(prompt).function_name, expected)

    def test_rejects_missing_sorted_and_conflicting_new_family_contracts(self):
        cases = (
            "Merge these two lists into sorted order.",
            "Find the first non-repeating character and return its index.",
            "Find the largest sum of a contiguous part but include non-contiguous values too.",
            "Do not reverse the text.",
        )
        for prompt in cases:
            with self.subTest(prompt=prompt), self.assertRaises(CodeInEnglishError):
                self.recognize(prompt)


if __name__ == "__main__":
    unittest.main()
