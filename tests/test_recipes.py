import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from codeinenglish import generate_file, solve
from codeinenglish.recipes import RECIPES

MIGRATED = {  # original families whose code now lives in recipes.py: (request, input, output)
    "duplicates": ("Check whether a list of numbers contains a duplicate.", {"nums": [1, 2, 1]}, True),
    "minimum": ("Find the smallest number in the list.", {"nums": [4, 2, 9]}, 2),
    "maximum": ("Find the largest number in the list.", {"nums": [4, 2, 9]}, 9),
    "sum": ("Calculate the sum of the list of numbers.", {"nums": [4, 2, 9]}, 15),
    "sort_ascending": ("Sort the list of integers in ascending order.", {"nums": [3, 1, 3, -2]}, [-2, 1, 3, 3]),
    "reverse_text": ("Reverse the given word.", {"text": "stressed"}, "desserts"),
    "move_zeros": ("Move all zeros to the end of the list, preserving order.", {"nums": [0, 1, 0, 3]}, [1, 3, 0, 0]),
    "merge_sorted_lists": ("Merge two sorted lists.", {"first": [1, 4], "second": [2, 3]}, [1, 2, 3, 4]),
    "maximum_subarray_sum": ("Find the maximum contiguous subarray sum.", {"nums": [-2, 1, -3, 4, -1, 2, 1]}, 6),
    "binary_search": ("Search the sorted list for the target and return its index.", {"nums": [1, 3, 5, 7], "target": 5}, 2),
}

CASES = {
    "factorial": ("Write a program to compute the factorial of a number.", {"n": 5}, 120),
    "fibonacci": ("Return the n-th Fibonacci number.", {"n": 10}, 55),
    "is_prime": ("Check whether a number is prime.", {"n": 17}, True),
    "gcd": ("Find the greatest common divisor of two numbers.", {"first": 12, "second": 18}, 6),
    "count_vowels": ("Count the vowels in a text.", {"text": "Education"}, 5),
    "remove_duplicates": ("Remove duplicates from a list of numbers.", {"nums": [3, 1, 3, 2, 1]}, [3, 1, 2]),
    "second_largest": ("Find the second largest number in a list.", {"nums": [4, 9, 9, 7]}, 7),
    "is_even": ("Check whether a number is even.", {"n": 10}, True),
    "power_of_two": ("Check whether a number is a power of two.", {"n": 64}, True),
    "sum_of_digits": ("Calculate the sum of the digits of a number.", {"n": 1234}, 10),
    "perfect_square": ("Check whether a number is a perfect square.", {"n": 49}, True),
    "leap_year": ("Check whether a year is a leap year.", {"year": 1900}, False),
    "fizzbuzz": ("Write FizzBuzz up to n.", {"n": 5}, ["1", "2", "Fizz", "4", "Buzz"]),
    "count_words": ("Count the words in a text.", {"text": "  offline code  generation "}, 3),
    "longest_word": ("Find the longest word in a text.", {"text": "a quick brown fox"}, "quick"),
    "remove_spaces": ("Remove the spaces from a string.", {"text": "a b  c"}, "abc"),
    "remove_vowels": ("Remove the vowels from a string.", {"text": "Education"}, "dctn"),
    "count_character": ("Count how many times a character appears in a text.", {"text": "banana", "character": "a"}, 3),
    "average": ("Calculate the average of a list of numbers.", {"nums": [1, 2, 3, 4]}, 2.5),
    "filter_even": ("Keep only the even numbers from a list.", {"nums": [1, 2, 3, 4]}, [2, 4]),
    "filter_odd": ("Keep only the odd numbers from a list.", {"nums": [1, 2, 3, 4, -3]}, [1, 3, -3]),
    "product": ("Calculate the product of a list of numbers.", {"nums": [2, 3, 4]}, 24),
    "contains_value": ("Check whether a list contains the target.", {"nums": [1, 2, 3], "target": 2}, True),
    "count_occurrences": ("Count how many times the target appears in the list.", {"nums": [1, 2, 1, 1], "target": 1}, 3),
    "reverse_list": ("Reverse a list of numbers.", {"nums": [1, 2, 3]}, [3, 2, 1]),
    "power": ("Raise a base to the power of an exponent.", {"base": 2, "exponent": 10}, 1024),
    "lcm": ("Find the least common multiple of two numbers.", {"first": 4, "second": 6}, 12),
    "palindrome_number": ("Check whether a number is a palindrome.", {"n": 12321}, True),
    "count_digits": ("Count the digits of a number.", {"n": 90210}, 5),
    "reverse_number": ("Reverse the digits of a number.", {"n": -120}, -21),
    "collatz": ("Count the Collatz steps for a number.", {"n": 6}, 8),
    "sum_to_n": ("Calculate the sum of the first n natural numbers.", {"n": 100}, 5050),
    "count_primes": ("Count the primes below n.", {"n": 10}, 4),
    "binary_representation": ("Convert a number to binary.", {"n": 10}, "1010"),
    "count_uppercase": ("Count the uppercase letters in a text.", {"text": "Hello World"}, 2),
    "swap_case": ("Swap the case of a text.", {"text": "Hello"}, "hELLO"),
    "to_uppercase": ("Convert a text to uppercase.", {"text": "offline"}, "OFFLINE"),
    "to_lowercase": ("Convert a text to lowercase.", {"text": "OFFLINE"}, "offline"),
    "pangram": ("Check whether a text is a pangram.", {"text": "The quick brown fox jumps over the lazy dog"}, True),
    "repeat_text": ("Repeat a text a number of times.", {"text": "ab", "times": 3}, "ababab"),
    "count_unique_characters": ("Count the unique characters in a text.", {"text": "banana"}, 3),
    "median": ("Find the median of a list of numbers.", {"nums": [4, 1, 3, 2]}, 2.5),
    "mode": ("Find the most frequent number in a list.", {"nums": [1, 2, 2, 3, 3]}, 2),
    "value_range": ("Find the difference between the largest and smallest number in a list.", {"nums": [4, 9, 1]}, 8),
    "count_positive": ("Count the positive numbers in a list.", {"nums": [3, -1, 0, 5]}, 2),
    "count_even": ("Count the even numbers in a list.", {"nums": [1, 2, 4, 5]}, 2),
    "sum_of_evens": ("Calculate the sum of the even numbers in a list.", {"nums": [1, 2, 4, 5]}, 6),
    "sum_of_odds": ("Calculate the sum of the odd numbers in a list.", {"nums": [1, 2, 4, 5]}, 6),
    "second_smallest": ("Find the second smallest number in a list.", {"nums": [4, 1, 1, 3]}, 3),
    "square_numbers": ("Square each number in a list.", {"nums": [1, 2, 3]}, [1, 4, 9]),
    "running_total": ("Calculate the running total of a list of numbers.", {"nums": [1, 2, 3]}, [1, 3, 6]),
}


class RecipeTests(unittest.TestCase):
    def test_migrated_families_pass_their_examples_in_python_and_javascript(self):
        for key, (request, given, expected) in MIGRATED.items():
            for target, runner in (("python", sys.executable), ("javascript", "node")):
                if runner == "node" and not shutil.which("node"):
                    continue
                with self.subTest(key=key, target=target), tempfile.TemporaryDirectory() as directory:
                    source = Path(directory) / "p.en"
                    source.write_text(f"target {target}\n# {request}\n# Example input: {json.dumps(given)}\n# Example output: {json.dumps(expected)}\n", encoding="utf-8")
                    result = subprocess.run([runner, str(generate_file(source)), "--check-examples"], capture_output=True, text=True)
                    self.assertEqual(result.returncode, 0, result.stderr)

    def test_every_recipe_has_a_case(self):
        self.assertEqual(set(CASES), {recipe.key for recipe in RECIPES})

    def test_each_recipe_generates_code_that_passes_its_example(self):
        for key, (request, given, expected) in CASES.items():
            with self.subTest(key):
                source = "import codeinpython library\n# " + request + "\n# Example input: " + json.dumps(given) + "\n# Example output: " + json.dumps(expected) + "\n"
                with tempfile.TemporaryDirectory() as directory:
                    path = Path(directory) / "out.py"
                    path.write_text(solve(source), encoding="utf-8")
                    result = subprocess.run([sys.executable, str(path), "--check-examples"], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)

    @unittest.skipUnless(shutil.which("node"), "Node.js is not installed")
    def test_each_recipe_runs_in_javascript_and_passes_its_example(self):
        for key, (request, given, expected) in CASES.items():
            with self.subTest(key), tempfile.TemporaryDirectory() as directory:
                source = Path(directory) / "p.en"
                source.write_text("target javascript\n# " + request + "\n# Example input: " + json.dumps(given) + "\n# Example output: " + json.dumps(expected) + "\n", encoding="utf-8")
                script = generate_file(source)
                result = subprocess.run(["node", str(script), "--check-examples"], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_pipeline_runs_in_python_and_javascript(self):
        request = "Remove duplicates from a list of numbers and then find the second largest number."
        body = "# " + request + '\n# Example input: {"nums":[3,1,3,2,1]}\n# Example output: 2\n'
        for target, runner, suffix in (("python", sys.executable, ".py"), ("javascript", "node", ".js")):
            if runner == "node" and not shutil.which("node"):
                continue
            with self.subTest(target), tempfile.TemporaryDirectory() as directory:
                source = Path(directory) / "p.en"
                source.write_text(f"target {target}\n" + body, encoding="utf-8")
                script = generate_file(source)
                self.assertEqual(script.suffix, suffix)
                result = subprocess.run([runner, str(script), "--check-examples"], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_pipeline_with_an_unknown_step_is_reported_not_dropped(self):
        with self.assertRaisesRegex(Exception, "not the step after it"):
            solve("import codeinpython library\n# Count the vowels in a text then sort ascending\n")

    def test_unknown_request_suggests_closest_tasks(self):
        with self.assertRaisesRegex(Exception, "Closest supported tasks: factorial"):
            solve("import codeinpython library\n# Compute the factorail of a number list\n")

    def test_prime_list_request_is_not_taken_by_the_prime_check(self):
        with self.assertRaises(Exception):
            solve("import codeinpython library\n# Generate all prime numbers below a limit.\n")


if __name__ == "__main__":
    unittest.main()
