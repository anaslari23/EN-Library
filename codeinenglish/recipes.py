"""Table-driven problem recipes. To add one: append a Recipe below; no other file changes."""
import ast
import difflib
import re
from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True)
class Recipe:
    key: str
    function: str
    inputs: tuple[tuple[str, str], ...]  # (parameter name, kind)
    result: str
    patterns: tuple[str, ...]  # every regex must match the normalized request; empty = code only (recognized elsewhere)
    assumptions: tuple[str, ...]
    source: str  # the function, as plain Python
    rejects: tuple[str, ...] = ()  # any match means "not this recipe"


_NUM = (("n", "integer"),)
_NUMS = (("nums", "integer_list"),)
_TEXT = (("text", "string"),)

RECIPES = (
    Recipe("factorial", "factorial", _NUM, "integer", (r"\bfactorial\b",),
           ("Return null for a negative number.", "factorial of 0 is 1."),
           "def factorial(n):\n    if n < 0:\n        return None\n    result = 1\n    for value in range(2, n + 1):\n        result *= value\n    return result\n"),
    Recipe("fibonacci", "fibonacci", _NUM, "integer", (r"\bfibonacci\b",),
           ("Return the n-th Fibonacci number counting from F(0) = 0 and F(1) = 1.", "Return null for a negative n."),
           "def fibonacci(n):\n    if n < 0:\n        return None\n    previous, current = 0, 1\n    for _ in range(n):\n        previous, current = current, previous + current\n    return previous\n",
           rejects=(r"\b(?:series|sequence|list|first)\b.{0,20}\bnumbers\b",)),
    Recipe("is_prime", "is_prime", _NUM, "boolean", (r"\bprime\b",),
           ("Numbers below 2 are not prime.",),
           "def is_prime(n):\n    if n < 2:\n        return False\n    divisor = 2\n    while divisor * divisor <= n:\n        if n % divisor == 0:\n            return False\n        divisor += 1\n    return True\n",
           rejects=(r"\b(?:all|list|generate|sieve|every|factors?)\b",)),
    Recipe("gcd", "greatest_common_divisor", (("first", "integer"), ("second", "integer")), "integer",
           (r"\b(?:greatest common (?:divisor|factor)|gcd|highest common factor)\b",),
           ("The result is never negative; gcd(0, 0) is 0.",),
           "def greatest_common_divisor(first, second):\n    first, second = abs(first), abs(second)\n    while second:\n        first, second = second, first % second\n    return first\n"),
    Recipe("count_vowels", "count_vowels", _TEXT, "integer", (r"\bvowels?\b", r"\b(?:count|how many|number of)\b"),
           ("Vowels are a, e, i, o, u in either case.", "y is not a vowel."),
           "def count_vowels(text):\n    return sum(1 for character in text if character.lower() in 'aeiou')\n"),
    Recipe("remove_duplicates", "remove_duplicates", _NUMS, "integer_list",
           (r"\b(?:remove|delete|eliminate|drop)\b.{0,30}\bduplicates?\b", r"\b(?:list|array|numbers?)\b"),
           ("Keep the first occurrence and preserve the original order.", "Return a new list."),
           "def remove_duplicates(nums):\n    seen = set()\n    result = []\n    for number in nums:\n        if number not in seen:\n            seen.add(number)\n            result.append(number)\n    return result\n"),
    Recipe("second_largest", "second_largest", _NUMS, "integer_or_null",
           (r"\bsecond (?:largest|biggest|highest|greatest)\b",),
           ("Duplicates count once; return null when fewer than two distinct values exist.",),
           "def second_largest(nums):\n    distinct = sorted(set(nums))\n    return distinct[-2] if len(distinct) >= 2 else None\n"),
)

def _code(key, function, source):
    """A family whose wording is recognized by hand-tuned rules in problem_recognizer; only its code lives here."""
    return Recipe(key, function, (), "", (), (), source)


# ponytail: frequencies, palindrome, anagram, first_unique_character, balanced_delimiters, two_sum stay hand-built
# (option variants / dict key order); move them here once the subset has dicts and option flags.
CODE_ONLY = (
    _code("duplicates", "contains_duplicate",
          "def contains_duplicate(nums):\n    seen = set()\n    for number in nums:\n        if number in seen:\n            return True\n        seen.add(number)\n    return False\n"),
    _code("minimum", "find_minimum", "def find_minimum(nums):\n    if not nums:\n        return None\n    return min(nums)\n"),
    _code("maximum", "find_maximum", "def find_maximum(nums):\n    if not nums:\n        return None\n    return max(nums)\n"),
    _code("sum", "calculate_sum", "def calculate_sum(nums):\n    return sum(nums)\n"),
    _code("sort_ascending", "sort_ascending", "def sort_ascending(nums):\n    return sorted(nums)\n"),
    _code("reverse_text", "reverse_text", "def reverse_text(text):\n    return ''.join(reversed(text))\n"),
    _code("move_zeros", "move_zeros",
          "def move_zeros(nums):\n    result = []\n    zeros = 0\n    for number in nums:\n        if number != 0:\n            result.append(number)\n        else:\n            zeros += 1\n    for _ in range(zeros):\n        result.append(0)\n    return result\n"),
    _code("merge_sorted_lists", "merge_sorted_lists",
          "def merge_sorted_lists(first, second):\n    result = list(first)\n    for number in second:\n        result.append(number)\n    return sorted(result)\n"),
    _code("maximum_subarray_sum", "maximum_subarray_sum",
          "def maximum_subarray_sum(nums):\n    if not nums:\n        return 0\n    current = nums[0]\n    best = current\n    for index in range(1, len(nums)):\n        number = nums[index]\n        current = max(number, current + number)\n        best = max(best, current)\n    return best\n"),
    _code("binary_search", "binary_search",
          "def binary_search(nums, target):\n    low = 0\n    high = len(nums) - 1\n    answer = -1\n    while low <= high:\n        middle = (low + high) // 2\n        if nums[middle] == target:\n            answer = middle\n            high = middle - 1\n        elif nums[middle] < target:\n            low = middle + 1\n        else:\n            high = middle - 1\n    return answer\n"),
)

BY_KEY = {recipe.key: recipe for recipe in (*RECIPES, *CODE_ONLY)}
RecipeFamily = Enum("RecipeFamily", {recipe.key.upper(): recipe.key for recipe in RECIPES}, type=str)


def function_ast(recipe: Recipe) -> ast.FunctionDef:
    return ast.parse(recipe.source).body[0]


def _vocabulary(recipe: Recipe) -> set[str]:
    words = set(recipe.key.split("_"))
    return words | set(re.findall(r"[a-z]{4,}", recipe.patterns[0]))  # the first pattern names the task


def suggest(text: str, limit: int = 2) -> list[str]:
    """Names of the recipes whose vocabulary best overlaps the (normalized) request, tolerating typos."""
    tokens = set(text.split())
    scored = []
    for recipe in RECIPES:
        vocabulary = _vocabulary(recipe)
        score = sum(bool(difflib.get_close_matches(word, vocabulary, n=1, cutoff=0.8)) for word in tokens if len(word) > 3)
        if score:
            scored.append((-score, recipe.key))
    return [key.replace("_", " ") for _, key in sorted(scored)[:limit]]
