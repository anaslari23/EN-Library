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

    # --- math ---
    Recipe("is_even", "is_even", _NUM, "boolean", (r"\b(?:even|odd)\b", r"\b(?:check|whether|determine|is|test)\b"),
           ("Zero is even; negative numbers follow the same rule.",),
           "def is_even(n):\n    return n % 2 == 0\n",
           rejects=(r"\b(?:list|array|numbers|filter|sum|count|sort|divisible)\b",)),
    Recipe("power_of_two", "is_power_of_two", _NUM, "boolean", (r"\bpower of (?:two|2)\b",),
           ("1 is a power of two; zero and negative numbers are not.",),
           "def is_power_of_two(n):\n    if n < 1:\n        return False\n    while n % 2 == 0:\n        n = n // 2\n    return n == 1\n"),
    Recipe("sum_of_digits", "sum_of_digits", _NUM, "integer", (r"\bdigits?\b", r"\b(?:sum|total|add)\b"),
           ("Use the absolute value; the sum of the digits of 0 is 0.",),
           "def sum_of_digits(n):\n    n = abs(n)\n    total = 0\n    while n > 0:\n        total += n % 10\n        n = n // 10\n    return total\n",
           rejects=(r"\b(?:list|array)\b",)),
    Recipe("perfect_square", "is_perfect_square", _NUM, "boolean", (r"\bperfect squares?\b",),
           ("Negative numbers are not perfect squares.",),
           "def is_perfect_square(n):\n    if n < 0:\n        return False\n    root = 0\n    while root * root < n:\n        root += 1\n    return root * root == n\n"),
    Recipe("leap_year", "is_leap_year", (("year", "integer"),), "boolean", (r"\bleap years?\b",),
           ("Gregorian rule: divisible by 4, except centuries not divisible by 400.",),
           "def is_leap_year(year):\n    return (year % 4 == 0 and year % 100 != 0) or year % 400 == 0\n"),
    Recipe("fizzbuzz", "fizzbuzz", _NUM, "string_list", (r"\bfizz ?buzz\b",),
           ("Count from 1 to n; multiples of 3 give Fizz, of 5 Buzz, of both FizzBuzz; other numbers appear as text.",),
           "def fizzbuzz(n):\n    result = []\n    for number in range(1, n + 1):\n        if number % 15 == 0:\n            result.append('FizzBuzz')\n        elif number % 3 == 0:\n            result.append('Fizz')\n        elif number % 5 == 0:\n            result.append('Buzz')\n        else:\n            result.append(str(number))\n    return result\n"),
    # --- text ---
    Recipe("count_words", "count_words", _TEXT, "integer", (r"\bwords\b", r"\b(?:count|how many|number of)\b"),
           ("Words are separated by any whitespace.",),
           "def count_words(text):\n    return len(text.split())\n",
           rejects=(r"\b(?:vowels?|longest|shortest)\b",)),
    Recipe("longest_word", "longest_word", _TEXT, "string", (r"\blongest\b", r"\bwords?\b"),
           ("Words are separated by whitespace; the first of equally long words wins; empty text gives an empty string.",),
           "def longest_word(text):\n    best = ''\n    for word in text.split():\n        if len(word) > len(best):\n            best = word\n    return best\n"),
    Recipe("remove_spaces", "remove_spaces", _TEXT, "string",
           (r"\b(?:remove|delete|strip|eliminate)\b", r"\b(?:spaces?|whitespace)\b", r"\b(?:text|string|sentence|word)\b"),
           ("All whitespace is removed, not just spaces.",),
           "def remove_spaces(text):\n    return ''.join(text.split())\n"),
    Recipe("remove_vowels", "remove_vowels", _TEXT, "string", (r"\b(?:remove|delete|strip|eliminate|drop)\b", r"\bvowels?\b"),
           ("Vowels are a, e, i, o, u in either case.",),
           "def remove_vowels(text):\n    return ''.join(character for character in text if character.lower() not in 'aeiou')\n"),
    Recipe("count_character", "count_character", (("text", "string"), ("character", "string")), "integer",
           (r"\b(?:count|how many times|number of times|occurrences?)\b", r"\b(?:character|letter|char)\b"),
           ("The comparison is case-sensitive.",),
           "def count_character(text, character):\n    total = 0\n    for item in text:\n        if item == character:\n            total += 1\n    return total\n",
           rejects=(r"\b(?:each|every|all|vowels?|unique|first)\b",)),
    # --- lists ---
    Recipe("average", "calculate_average", _NUMS, "number_or_null", (r"\b(?:average|mean)\b", r"\b(?:list|array|numbers?|values?)\b"),
           ("Return null for an empty list.",),
           "def calculate_average(nums):\n    if not nums:\n        return None\n    return sum(nums) / len(nums)\n",
           rejects=(r"\b(?:median|mode|weighted|moving|running)\b",)),
    Recipe("filter_even", "filter_even_numbers", _NUMS, "integer_list",
           (r"\beven\b", r"\b(?:filter|keep|select|only|extract|all)\b", r"\b(?:list|array|numbers)\b"),
           ("Keep the original order.",),
           "def filter_even_numbers(nums):\n    return [number for number in nums if number % 2 == 0]\n", rejects=(r"\bodd\b", r"\b(?:sum|total|add|count|how many|product|average)\b")),
    Recipe("filter_odd", "filter_odd_numbers", _NUMS, "integer_list",
           (r"\bodd\b", r"\b(?:filter|keep|select|only|extract|all)\b", r"\b(?:list|array|numbers)\b"),
           ("Keep the original order.",),
           "def filter_odd_numbers(nums):\n    return [number for number in nums if number % 2 == 1]\n", rejects=(r"\beven\b", r"\b(?:sum|total|add|count|how many|product|average)\b")),
    Recipe("product", "product_of_list", _NUMS, "integer", (r"\b(?:product|multiply)\b", r"\b(?:list|array|numbers)\b"),
           ("The product of an empty list is 1.",),
           "def product_of_list(nums):\n    result = 1\n    for number in nums:\n        result *= number\n    return result\n",
           rejects=(r"\b(?:dot|cross|matrix)\b",)),
    Recipe("contains_value", "contains_value", (("nums", "integer_list"), ("target", "integer")), "boolean",
           (r"\b(?:contains?|includes?|is present|is in)\b", r"\btarget\b"),
           ("Return true when the target appears at least once.",),
           "def contains_value(nums, target):\n    return target in nums\n",
           rejects=(r"\b(?:duplicates?|index|position|sorted|sum|pair|count|times)\b",)),
    Recipe("count_occurrences", "count_occurrences", (("nums", "integer_list"), ("target", "integer")), "integer",
           (r"\b(?:count|how many times|number of times|occurrences?)\b", r"\b(?:appears?|occurs?|occurrences?)\b", r"\btarget\b"),
           ("Count every position where the value equals the target.",),
           "def count_occurrences(nums, target):\n    total = 0\n    for number in nums:\n        if number == target:\n            total += 1\n    return total\n",
           rejects=(r"\b(?:each|every|all|character|letter|word)\b",)),
    Recipe("reverse_list", "reverse_list", _NUMS, "integer_list", (r"\brevers\w*\b", r"\b(?:list|array)\b"),
           ("Return a new list; do not mutate the input.",),
           "def reverse_list(nums):\n    return list(reversed(nums))\n",
           rejects=(r"\b(?:text|string|word|phrase|characters?|sort\w*)\b",)),
    Recipe("running_total", "running_total", _NUMS, "integer_list", (r"\b(?:running|cumulative|prefix)\b", r"\b(?:sum|total)\b"),
           ("Each entry is the sum of all values up to and including that position.",),
           "def running_total(nums):\n    total = 0\n    result = []\n    for number in nums:\n        total += number\n        result.append(total)\n    return result\n"),

    # --- math (batch 2) ---
    Recipe("power", "power", (("base", "integer"), ("exponent", "integer")), "integer",
           (r"\b(?:to the power|raised to|raise|exponent|exponentiation)\b",),
           ("Return null for a negative exponent.",),
           "def power(base, exponent):\n    if exponent < 0:\n        return None\n    result = 1\n    for _ in range(exponent):\n        result *= base\n    return result\n",
           rejects=(r"\bpower of (?:two|2)\b",)),
    Recipe("lcm", "least_common_multiple", (("first", "integer"), ("second", "integer")), "integer",
           (r"\b(?:least common multiple|lowest common multiple|lcm)\b",),
           ("The result is never negative; it is 0 if either number is 0.",),
           "def least_common_multiple(first, second):\n    a = abs(first)\n    b = abs(second)\n    if a == 0 or b == 0:\n        return 0\n    x = a\n    y = b\n    while y:\n        x, y = y, x % y\n    return a // x * b\n"),
    Recipe("palindrome_number", "is_palindrome_number", _NUM, "boolean", (r"\bpalindrome\b", r"\b(?:number|integer)\b"),
           ("Negative numbers are not palindromes.",),
           "def is_palindrome_number(n):\n    if n < 0:\n        return False\n    remaining = n\n    reversed_number = 0\n    while remaining > 0:\n        reversed_number = reversed_number * 10 + remaining % 10\n        remaining = remaining // 10\n    return reversed_number == n\n",
           rejects=(r"\b(?:text|string|word|phrase|sentence|characters?|letters?)\b",)),
    Recipe("count_digits", "count_digits", _NUM, "integer", (r"\b(?:count|how many|number of)\b", r"\bdigits?\b"),
           ("Use the absolute value; 0 has one digit.",),
           "def count_digits(n):\n    n = abs(n)\n    if n == 0:\n        return 1\n    total = 0\n    while n > 0:\n        total += 1\n        n = n // 10\n    return total\n",
           rejects=(r"\b(?:sum|total|add|list|array)\b",)),
    Recipe("reverse_number", "reverse_number", _NUM, "integer", (r"\brevers\w*\b", r"\b(?:number|integer|digits)\b"),
           ("A negative number keeps its sign; trailing zeros disappear.",),
           "def reverse_number(n):\n    sign = -1 if n < 0 else 1\n    n = abs(n)\n    result = 0\n    while n > 0:\n        result = result * 10 + n % 10\n        n = n // 10\n    return sign * result\n",
           rejects=(r"\b(?:text|string|word|phrase|list|array|characters?|sort\w*|palindrome)\b",)),
    Recipe("collatz", "collatz_steps", _NUM, "integer", (r"\bcollatz\b",),
           ("Count the steps to reach 1; return null for numbers below 1.",),
           "def collatz_steps(n):\n    if n < 1:\n        return None\n    steps = 0\n    while n != 1:\n        if n % 2 == 0:\n            n = n // 2\n        else:\n            n = 3 * n + 1\n        steps += 1\n    return steps\n"),
    Recipe("sum_to_n", "sum_to_n", _NUM, "integer",
           (r"\b(?:sum|total|add)\b", r"\b(?:natural numbers?|first n|(?:1|one) to n)\b"),
           ("Return 0 when n is below 1.",),
           "def sum_to_n(n):\n    if n < 1:\n        return 0\n    return n * (n + 1) // 2\n"),
    Recipe("count_primes", "count_primes_below", _NUM, "integer", (r"\bprimes\b", r"\b(?:count|how many|number of)\b"),
           ("Count primes strictly less than n.",),
           "def count_primes_below(n):\n    total = 0\n    for number in range(2, n):\n        prime = True\n        divisor = 2\n        while divisor * divisor <= number and prime:\n            if number % divisor == 0:\n                prime = False\n            divisor += 1\n        if prime:\n            total += 1\n    return total\n"),
    Recipe("binary_representation", "to_binary", _NUM, "string", (r"\bbinary\b", r"\b(?:convert|representation|to binary|as binary|in binary)\b"),
           ("Return null for a negative number; 0 is '0'.",),
           "def to_binary(n):\n    if n < 0:\n        return None\n    if n == 0:\n        return '0'\n    result = ''\n    while n > 0:\n        result = str(n % 2) + result\n        n = n // 2\n    return result\n",
           rejects=(r"\bsearch\b",)),
    # --- text (batch 2) ---
    Recipe("count_uppercase", "count_uppercase", _TEXT, "integer", (r"\b(?:upper ?case|capital)\b", r"\b(?:count|how many|number of)\b"),
           ("Count uppercase letters only.",),
           "def count_uppercase(text):\n    return sum(1 for character in text if character.isupper())\n"),
    Recipe("swap_case", "swap_case", _TEXT, "string", (r"\b(?:swap|invert|toggle|flip)\b", r"\bcase\b"),
           ("Characters without case are unchanged.",),
           "def swap_case(text):\n    return ''.join(character.lower() if character.isupper() else character.upper() for character in text)\n"),
    Recipe("to_uppercase", "to_uppercase", _TEXT, "string",
           (r"\b(?:upper ?case|capital letters|all caps)\b", r"\b(?:convert|change|make|turn|transform|to)\b"),
           ("Return a new string.",),
           "def to_uppercase(text):\n    return text.upper()\n",
           rejects=(r"\b(?:count|how many|number of|swap|check|whether|first|each word)\b",)),
    Recipe("to_lowercase", "to_lowercase", _TEXT, "string",
           (r"\b(?:lower ?case|small letters)\b", r"\b(?:convert|change|make|turn|transform|to)\b"),
           ("Return a new string.",),
           "def to_lowercase(text):\n    return text.lower()\n",
           rejects=(r"\b(?:count|how many|number of|swap|check|whether|first|each word)\b",)),
    Recipe("pangram", "is_pangram", _TEXT, "boolean", (r"\bpangram\b",),
           ("Letters a-z are compared case-insensitively; other characters are ignored.",),
           "def is_pangram(text):\n    lowered = text.lower()\n    for letter in 'abcdefghijklmnopqrstuvwxyz':\n        if letter not in lowered:\n            return False\n    return True\n"),
    Recipe("repeat_text", "repeat_text", (("text", "string"), ("times", "integer")), "string",
           (r"\brepeat\w*\b", r"\b(?:text|string|word|phrase)\b", r"\btimes\b"),
           ("A count below 1 gives an empty string.",),
           "def repeat_text(text, times):\n    result = ''\n    for _ in range(times):\n        result += text\n    return result\n"),
    Recipe("count_unique_characters", "count_unique_characters", _TEXT, "integer",
           (r"\b(?:unique|distinct)\b", r"\b(?:characters?|letters?)\b", r"\b(?:count|how many|number of)\b"),
           ("Case-sensitive; spaces and punctuation count as characters.",),
           "def count_unique_characters(text):\n    return len(set(text))\n",
           rejects=(r"\b(?:first|vowels?)\b",)),
    # --- lists (batch 2) ---
    Recipe("median", "find_median", _NUMS, "number_or_null", (r"\bmedian\b",),
           ("Return null for an empty list; an even-length list averages the two middle values.",),
           "def find_median(nums):\n    if not nums:\n        return None\n    ordered = sorted(nums)\n    middle = len(ordered) // 2\n    if len(ordered) % 2 == 1:\n        return ordered[middle]\n    return (ordered[middle - 1] + ordered[middle]) / 2\n"),
    Recipe("mode", "find_mode", _NUMS, "integer_or_null", (r"\b(?:mode|most frequent|most common|most often)\b", r"\b(?:list|array|numbers?|values?)\b"),
           ("Ties go to the smallest value; return null for an empty list.",),
           "def find_mode(nums):\n    best = None\n    best_count = 0\n    for number in nums:\n        count = 0\n        for other in nums:\n            if other == number:\n                count += 1\n        if count > best_count or (count == best_count and number < best):\n            best = number\n            best_count = count\n    return best\n",
           rejects=(r"\b(?:character|letter|word)\b",)),
    Recipe("value_range", "value_range", _NUMS, "integer_or_null",
           (r"\b(?:difference between the (?:largest|maximum|biggest|greatest) and (?:the )?(?:smallest|minimum|least)|range of)\b",),
           ("Largest minus smallest; return null for an empty list.",),
           "def value_range(nums):\n    if not nums:\n        return None\n    return max(nums) - min(nums)\n"),
    Recipe("count_positive", "count_positive_numbers", _NUMS, "integer",
           (r"\bpositive\b", r"\b(?:count|how many|number of)\b", r"\b(?:list|array|numbers)\b"),
           ("Zero is not positive.",),
           "def count_positive_numbers(nums):\n    total = 0\n    for number in nums:\n        if number > 0:\n            total += 1\n    return total\n"),
    Recipe("count_even", "count_even_numbers", _NUMS, "integer",
           (r"\beven\b", r"\b(?:count|how many|number of)\b", r"\b(?:list|array|numbers)\b"),
           ("Zero is even.",),
           "def count_even_numbers(nums):\n    total = 0\n    for number in nums:\n        if number % 2 == 0:\n            total += 1\n    return total\n",
           rejects=(r"\b(?:odd|sum|add|product|average)\b",)),
    Recipe("sum_of_evens", "sum_of_even_numbers", _NUMS, "integer",
           (r"\b(?:sum|total|add)\b", r"\beven\b", r"\b(?:list|array|numbers)\b"),
           ("The sum of no even numbers is 0.",),
           "def sum_of_even_numbers(nums):\n    total = 0\n    for number in nums:\n        if number % 2 == 0:\n            total += number\n    return total\n",
           rejects=(r"\b(?:odd|count|how many|product|average)\b",)),
    Recipe("sum_of_odds", "sum_of_odd_numbers", _NUMS, "integer",
           (r"\b(?:sum|total|add)\b", r"\bodd\b", r"\b(?:list|array|numbers)\b"),
           ("The sum of no odd numbers is 0.",),
           "def sum_of_odd_numbers(nums):\n    total = 0\n    for number in nums:\n        if number % 2 == 1:\n            total += number\n    return total\n",
           rejects=(r"\b(?:even|count|how many|product|average)\b",)),
    Recipe("second_smallest", "second_smallest", _NUMS, "integer_or_null", (r"\bsecond (?:smallest|lowest|least)\b",),
           ("Duplicates count once; return null when fewer than two distinct values exist.",),
           "def second_smallest(nums):\n    distinct = sorted(set(nums))\n    return distinct[1] if len(distinct) >= 2 else None\n"),
    Recipe("square_numbers", "square_numbers", _NUMS, "integer_list", (r"\bsquares?\b", r"\b(?:each|every|all)\b", r"\b(?:list|array|numbers)\b"),
           ("Keep the original order.",),
           "def square_numbers(nums):\n    return [number * number for number in nums]\n",
           rejects=(r"\b(?:perfect|root|sum|average|area|count)\b",)),
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


def suggest(text: str, limit: int = 2) -> list[str]:
    """Names of the recipes whose name and key words best overlap the (normalized) request, tolerating typos."""
    tokens = {word for word in text.split() if len(word) > 3}
    scored = []
    for recipe in RECIPES:
        name_words = set(recipe.key.split("_"))
        other_words = set(re.findall(r"[a-z]{4,}", recipe.patterns[0])) - name_words  # the first pattern names the task
        score = sum(3 * bool(difflib.get_close_matches(word, name_words, n=1, cutoff=0.8))
                    + bool(difflib.get_close_matches(word, other_words, n=1, cutoff=0.8)) for word in tokens)
        if score:
            scored.append((-score, recipe.key))
    scored.sort()
    return [key.replace("_", " ") for score, key in scored[:limit] if -score * 2 >= -scored[0][0]]
