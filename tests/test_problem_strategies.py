import ast
import itertools
import unittest

from codeinenglish.problem_prompt import ProblemPrompt
from codeinenglish.problem_recognizer import recognize_problem
from codeinenglish.problem_strategies import generate_problem_ast
from codeinenglish.python_generator import generate_python_ast


class ProblemStrategyTests(unittest.TestCase):
    def function(self, prompt, function_name, *args):
        spec = recognize_problem(ProblemPrompt(prompt, (1,)))
        source = generate_python_ast(generate_problem_ast(spec))
        ast.parse(source)
        namespace = {}
        exec(source, namespace)
        return namespace[function_name](*args)

    def test_pair_sum(self):
        self.assertEqual(self.function("Find two numbers that add up to target and return their indices. Exactly one solution exists.", "two_sum", [2, 7, 11], 9), (0, 1))

    def test_duplicates_and_frequency(self):
        self.assertTrue(self.function("Check whether a list contains a duplicate value.", "contains_duplicate", [1, 2, 1]))
        self.assertFalse(self.function("Check whether a list contains a duplicate value.", "contains_duplicate", []))
        self.assertEqual(self.function("Return the frequency of each number.", "count_frequencies", [1, 2, 1]), {1: 2, 2: 1})

    def test_aggregates(self):
        self.assertEqual(self.function("Return the largest number in the list.", "find_maximum", [1, 9, 4]), 9)
        self.assertIsNone(self.function("Return the smallest number in the list.", "find_minimum", []))
        self.assertEqual(self.function("Calculate the sum of all numbers in the list.", "calculate_sum", []), 0)

    def test_palindrome_and_anagram(self):
        self.assertTrue(self.function("Check if the text is a palindrome.", "is_palindrome", "abba"))
        self.assertFalse(self.function("Check if the text is a palindrome.", "is_palindrome", "Abba"))
        self.assertFalse(self.function("Check if the text is a palindrome ignoring case and punctuation.", "is_palindrome", "A man, a plan, a canal: Panama"))
        self.assertFalse(self.function("Check if the text is a palindrome ignoring punctuation.", "is_palindrome", "$a,bba"))
        self.assertTrue(self.function("Check if the text is a palindrome ignoring case, punctuation, and whitespace.", "is_palindrome", "A man, a plan, a canal: Panama"))
        self.assertFalse(self.function("Check if the text is a palindrome ignoring whitespace.", "is_palindrome", "a, b"))
        self.assertTrue(self.function("Check whether two strings are anagrams.", "are_anagrams", "listen", "silent"))
        self.assertTrue(self.function("Check whether two strings are anagrams ignoring case.", "are_anagrams", "Listen", "Silent"))
        self.assertTrue(self.function("Check whether two strings are anagrams ignoring whitespace.", "are_anagrams", "a b", "ba"))
        self.assertFalse(self.function("Check whether two strings are anagrams.", "are_anagrams", "a", "ab"))

    def test_binary_search_boundaries(self):
        prompt = "Find target in a sorted list and return its index or -1 if absent."
        self.assertEqual(self.function(prompt, "binary_search", [1, 4, 8, 12], 1), 0)
        self.assertEqual(self.function(prompt, "binary_search", [1, 4, 8, 12], 12), 3)
        self.assertEqual(self.function(prompt, "binary_search", [1, 4, 8, 12], 7), -1)
        self.assertEqual(self.function(prompt, "binary_search", [], 7), -1)
        self.assertEqual(self.function(prompt, "binary_search", [1, 2, 2, 2, 3], 2), 1)

    def test_current_strategies_match_simple_reference_implementations(self):
        duplicate_prompt = "Check whether a list contains a duplicate value."
        frequency_prompt = "Return the frequency of each number."
        pair_prompt = "Find two numbers that add up to target and return their indices."
        search_prompt = "Find target in a sorted list and return its first index or -1 if absent."
        for nums in itertools.product((-1, 0, 1), repeat=3):
            values = list(nums)
            self.assertEqual(self.function(duplicate_prompt, "contains_duplicate", values), len(values) != len(set(values)))
            self.assertEqual(self.function(frequency_prompt, "count_frequencies", values), {value: values.count(value) for value in set(values)})
            for target in (-2, 0, 2):
                expected = next(((i, j) for j in range(len(values)) for i in range(j) if values[i] + values[j] == target), None)
                self.assertEqual(self.function(pair_prompt, "two_sum", values, target), expected)
        sorted_prompt = search_prompt
        for size in range(5):
            for values in itertools.combinations_with_replacement(range(3), size):
                for target in range(-1, 4):
                    expected = list(values).index(target) if target in values else -1
                    self.assertEqual(self.function(sorted_prompt, "binary_search", list(values), target), expected)
        for length in range(5):
            for chars in itertools.product("ab", repeat=length):
                text = "".join(chars)
                self.assertEqual(self.function("Check if text is a palindrome.", "is_palindrome", text), text == text[::-1])
                for other_chars in itertools.product("ab", repeat=length):
                    other = "".join(other_chars)
                    self.assertEqual(self.function("Check whether two strings are anagrams.", "are_anagrams", text, other), sorted(text) == sorted(other))
        for length in range(4):
            for values in itertools.product((-1, 0, 1), repeat=length):
                nums = list(values)
                self.assertEqual(self.function("Return the largest integer in the list.", "find_maximum", nums), max(nums) if nums else None)
                self.assertEqual(self.function("Find the smallest value in the array.", "find_minimum", nums), min(nums) if nums else None)
                self.assertEqual(self.function("Calculate the total of all numbers in the list.", "calculate_sum", nums), sum(nums))

    def test_six_new_strategies_cover_their_contract_boundaries(self):
        self.assertEqual(self.function("Find the first non-repeating character in a string.", "first_unique_character", "swiss"), "w")
        self.assertIsNone(self.function("Find the first non-repeating character in a string.", "first_unique_character", "aabb"))
        self.assertEqual(self.function("Find the first unique character ignoring case.", "first_unique_character", "aAq"), "q")
        self.assertEqual(self.function("Reverse the given word.", "reverse_text", ""), "")
        self.assertEqual(self.function("Reverse the given word.", "reverse_text", "café"), "éfac")
        self.assertEqual(self.function("Move all zero values to the end of the array and preserve order.", "move_zeros", [0, 2, 0, 1, 3]), [2, 1, 3, 0, 0])
        self.assertEqual(self.function("Merge two sorted integer lists into one sorted list.", "merge_sorted_lists", [1, 2, 2], [2, 4]), [1, 2, 2, 2, 4])
        self.assertEqual(self.function("Find the largest sum of a contiguous part of the list.", "maximum_subarray_sum", [-2, 1, -3, 4, -1, 2, 1, -5, 4]), 6)
        self.assertEqual(self.function("Find the largest sum of a contiguous part of the list.", "maximum_subarray_sum", [-4, -1, -8]), -1)
        self.assertEqual(self.function("Find the largest sum of a contiguous part of the list.", "maximum_subarray_sum", []), 0)
        prompt = "Check whether the parentheses are balanced."
        self.assertTrue(self.function(prompt, "has_balanced_delimiters", "(()())"))
        self.assertFalse(self.function(prompt, "has_balanced_delimiters", "())("))
        self.assertTrue(self.function(prompt, "has_balanced_delimiters", "a(b)c"))
        all_delimiters = "Determine if all brackets and braces are properly matched."
        self.assertTrue(self.function(all_delimiters, "has_balanced_delimiters", "{[()]}"))
        self.assertFalse(self.function(all_delimiters, "has_balanced_delimiters", "([)]"))

    def test_new_strategies_match_simple_reference_domains(self):
        for length in range(5):
            for chars in itertools.product("abc", repeat=length):
                text = "".join(chars)
                expected = next((char for char in text if text.count(char) == 1), None)
                self.assertEqual(self.function("Find the first non-repeating character in a string.", "first_unique_character", text), expected)
                self.assertEqual(self.function("Reverse the given word.", "reverse_text", text), text[::-1])
                for candidate in ("", "a", "ab"):
                    brackets = "()" + candidate
                    self.assertEqual(self.function("Determine if all brackets and braces are properly matched.", "has_balanced_delimiters", brackets), _balanced_reference(brackets))
        for length in range(5):
            for values in itertools.product((0, 1, 2), repeat=length):
                nums = list(values)
                expected = [n for n in nums if n != 0] + [n for n in nums if n == 0]
                self.assertEqual(self.function("Move every zero to the end of the list while keeping the other numbers in order.", "move_zeros", nums), expected)
                expected_sum = max((sum(nums[i:j]) for i in range(len(nums)) for j in range(i + 1, len(nums) + 1)), default=0)
                self.assertEqual(self.function("Find the largest sum of a contiguous part of the list.", "maximum_subarray_sum", nums), expected_sum)


def _balanced_reference(text):
    pairs = {")": "(", "]": "[", "}": "{"}
    stack = []
    for char in text:
        if char in "([{":
            stack.append(char)
        elif char in pairs:
            if not stack or stack.pop() != pairs[char]:
                return False
    return not stack


if __name__ == "__main__":
    unittest.main()
