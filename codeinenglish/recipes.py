"""Table-driven problem recipes. To add one: append a Recipe below; no other file changes."""
import ast
import difflib
import re
from dataclasses import dataclass, replace
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
    accepts: tuple[str, ...] = ()  # condition words this recipe implements itself ("below n"), exempt from the condition guard
    stage: tuple[str, str] | None = None  # (regex, "list" | "scalar"): usable as a step in a composed request


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
           "def least_common_multiple(first, second):\n    a = abs(first)\n    b = abs(second)\n    if a == 0 or b == 0:\n        return 0\n    x = a\n    y = b\n    while y:\n        x, y = y, x % y\n    return a // x * b\n",
           accepts=('multiple',)),
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
           "def count_primes_below(n):\n    total = 0\n    for number in range(2, n):\n        prime = True\n        divisor = 2\n        while divisor * divisor <= number and prime:\n            if number % divisor == 0:\n                prime = False\n            divisor += 1\n        if prime:\n            total += 1\n    return total\n",
           accepts=('below', 'less than')),
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
           "def value_range(nums):\n    if not nums:\n        return None\n    return max(nums) - min(nums)\n",
           accepts=('between',)),
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
    # --- unit conversions ---
    Recipe("celsius_to_fahrenheit", "celsius_to_fahrenheit", (("celsius", "number"),), "number",
           (r"\b(?:celsius|centigrade)\b.{0,25}\b(?:to|into|in)\b.{0,10}\b(?:fahrenheit)\b",),
           ("F = C x 9/5 + 32. The result is not rounded.",),
           "def celsius_to_fahrenheit(celsius):\n    return celsius * 9 / 5 + 32\n"),
    Recipe("fahrenheit_to_celsius", "fahrenheit_to_celsius", (("fahrenheit", "number"),), "number",
           (r"\b(?:fahrenheit)\b.{0,25}\b(?:to|into|in)\b.{0,10}\b(?:celsius|centigrade)\b",),
           ("C = (F - 32) x 5/9. The result is not rounded.",),
           "def fahrenheit_to_celsius(fahrenheit):\n    return (fahrenheit - 32) * 5 / 9\n"),
    Recipe("km_to_miles", "kilometers_to_miles", (("kilometers", "number"),), "number",
           (r"\b(?:kilometers?|kilometres?|km)\b.{0,25}\b(?:to|into|in)\b.{0,10}\b(?:miles?)\b",),
           ("1 km = 0.621371 miles. The result is not rounded.",),
           "def kilometers_to_miles(kilometers):\n    return kilometers * 0.621371\n"),
    Recipe("miles_to_km", "miles_to_kilometers", (("miles", "number"),), "number",
           (r"\b(?:miles?)\b.{0,25}\b(?:to|into|in)\b.{0,10}\b(?:kilometers?|kilometres?|km)\b",),
           ("1 mile = 1.609344 km. The result is not rounded.",),
           "def miles_to_kilometers(miles):\n    return miles * 1.609344\n"),
    Recipe("kg_to_pounds", "kilograms_to_pounds", (("kilograms", "number"),), "number",
           (r"\b(?:kilograms?|kgs?)\b.{0,25}\b(?:to|into|in)\b.{0,10}\b(?:pounds?|lbs?)\b",),
           ("1 kg = 2.2046226218 pounds. The result is not rounded.",),
           "def kilograms_to_pounds(kilograms):\n    return kilograms * 2.2046226218\n"),
    Recipe("pounds_to_kg", "pounds_to_kilograms", (("pounds", "number"),), "number",
           (r"\b(?:pounds?|lbs?)\b.{0,25}\b(?:to|into|in)\b.{0,10}\b(?:kilograms?|kgs?)\b",),
           ("1 pound = 0.45359237 kg. The result is not rounded.",),
           "def pounds_to_kilograms(pounds):\n    return pounds * 0.45359237\n"),

    Recipe("filter_positive", "filter_positive_numbers", _NUMS, "integer_list",
           (r"\bpositive\b", r"\b(?:filter|keep|select|only|extract|all|return|get)\b", r"\b(?:list|array|numbers)\b"),
           ("Zero is not positive; keep the original order.",),
           "def filter_positive_numbers(nums):\n    return [number for number in nums if number > 0]\n",
           rejects=(r"\b(?:count|how many|sum|total|add|product|average|mean|largest|smallest)\b",)),
    Recipe("filter_negative", "filter_negative_numbers", _NUMS, "integer_list",
           (r"\bnegative\b", r"\b(?:filter|keep|select|only|extract|all|return|get)\b", r"\b(?:list|array|numbers)\b"),
           ("Zero is not negative; keep the original order.",),
           "def filter_negative_numbers(nums):\n    return [number for number in nums if number < 0]\n",
           rejects=(r"\b(?:count|how many|sum|total|add|product|average|mean|largest|smallest)\b",)),
    Recipe("double_numbers", "double_numbers", _NUMS, "integer_list",
           (r"\b(?:doubles?|doubled|twice)\b", r"\b(?:each|every|all)\b", r"\b(?:list|array|numbers)\b"),
           ("Keep the original order.",),
           "def double_numbers(nums):\n    return [number * 2 for number in nums]\n",
           rejects=(r"\b(?:sum|total|add|product|average|largest|smallest)\b",)),
    Recipe("sort_descending", "sort_descending", _NUMS, "integer_list",
           (r"\bdescending\b", r"\b(?:sort\w*|order\w*|arrange\w*)\b", r"\b(?:list|array|numbers)\b"),
           ("Sort from largest to smallest and keep duplicate values.", "Return a new list; do not mutate the input."),
           "def sort_descending(nums):\n    return list(reversed(sorted(nums)))\n",
           rejects=(r"\b(?:search|target|index|position|merge|combine|binary)\b",)),
    Recipe("count_items", "count_items", _NUMS, "integer",
           (r"\b(?:count|how many|number of)\b", r"\b(?:items|elements|numbers|values|integers)\b"),
           ("Count every entry, including repeats.",),
           "def count_items(nums):\n    return len(nums)\n",
           rejects=(r"\b(?:even|odd|positive|negative|unique|distinct|duplicates?|vowels?|words?|characters?|letters?|digits?|primes?|target|times|occurrences?|appears?|each|every)\b",)),

    Recipe("count_characters", "count_characters", _TEXT, "integer",
           (r"\b(?:length|number of characters|how many characters|count the characters)\b", r"\b(?:text|string|sentence|word|phrase)\b"),
           ("Every character counts, including spaces and punctuation.",),
           "def count_characters(text):\n    return len(text)\n",
           rejects=(r"\b(?:unique|distinct|vowels?|words|longest|upper ?case)\b",)),
)

def _code(key, function, source, inputs=_NUMS):
    """A family whose wording is recognized by hand-tuned rules in problem_recognizer; only its code lives here."""
    return Recipe(key, function, inputs, "", (), (), source)


# ponytail: frequencies, palindrome, anagram, first_unique_character, balanced_delimiters, two_sum stay hand-built
# (option variants / dict key order); move them here once the subset has dicts and option flags.
CODE_ONLY = (
    _code("duplicates", "contains_duplicate",
          "def contains_duplicate(nums):\n    seen = set()\n    for number in nums:\n        if number in seen:\n            return True\n        seen.add(number)\n    return False\n"),
    _code("minimum", "find_minimum", "def find_minimum(nums):\n    if not nums:\n        return None\n    return min(nums)\n"),
    _code("maximum", "find_maximum", "def find_maximum(nums):\n    if not nums:\n        return None\n    return max(nums)\n"),
    _code("sum", "calculate_sum", "def calculate_sum(nums):\n    return sum(nums)\n"),
    _code("sort_ascending", "sort_ascending", "def sort_ascending(nums):\n    return sorted(nums)\n"),
    _code("reverse_text", "reverse_text", "def reverse_text(text):\n    return ''.join(reversed(text))\n", _TEXT),
    _code("move_zeros", "move_zeros",
          "def move_zeros(nums):\n    result = []\n    zeros = 0\n    for number in nums:\n        if number != 0:\n            result.append(number)\n        else:\n            zeros += 1\n    for _ in range(zeros):\n        result.append(0)\n    return result\n"),
    _code("merge_sorted_lists", "merge_sorted_lists",
          "def merge_sorted_lists(first, second):\n    result = list(first)\n    for number in second:\n        result.append(number)\n    return sorted(result)\n"),
    _code("maximum_subarray_sum", "maximum_subarray_sum",
          "def maximum_subarray_sum(nums):\n    if not nums:\n        return 0\n    current = nums[0]\n    best = current\n    for index in range(1, len(nums)):\n        number = nums[index]\n        current = max(number, current + number)\n        best = max(best, current)\n    return best\n"),
    _code("binary_search", "binary_search",
          "def binary_search(nums, target):\n    low = 0\n    high = len(nums) - 1\n    answer = -1\n    while low <= high:\n        middle = (low + high) // 2\n        if nums[middle] == target:\n            answer = middle\n            high = middle - 1\n        elif nums[middle] < target:\n            low = middle + 1\n        else:\n            high = middle - 1\n    return answer\n"),
)

_DEDUPE = r"\b(?:(?:remove|delete|eliminate|drop|filter out)\s+(?:all\s+|the\s+)?duplicate(?:s| values| numbers)?|unique|distinct|duplicates?)\b"
STAGES = {  # key -> (regex naming the step in a request, "list" if it yields a list else "scalar")
    "filter_even": (r"\beven\b", "list"), "filter_odd": (r"\bodd\b", "list"),
    "filter_positive": (r"\bpositive\b", "list"), "filter_negative": (r"\bnegative\b", "list"),
    "square_numbers": (r"\bsquare[sd]?\b", "list"), "double_numbers": (r"\b(?:doubles?|doubled)\b", "list"),
    "remove_duplicates": (_DEDUPE, "list"), "reverse_list": (r"\brevers\w*\b", "list"),
    "running_total": (r"\b(?:running total|cumulative sum|prefix sums?)\b", "list"),
    "sort_ascending": (r"\b(?:sort(?:ed)?|arrange|ascending(?: order)?|in order)\b", "list"),
    "sort_descending": (r"\bdescending(?: order)?\b", "list"),
    "sum": (r"\b(?:sum|total|add(?: them| these)?(?: all)? up|add up)\b", "scalar"),
    "product": (r"\b(?:product|multiply)\b", "scalar"), "average": (r"\b(?:average|mean)\b", "scalar"),
    "median": (r"\bmedian\b", "scalar"),
    # text steps (their input is a string, so they only compose with each other)
    "to_uppercase": (r"\b(?:upper ?case|capital letters|all caps)\b", "text"),
    "to_lowercase": (r"\b(?:lower ?case|small letters)\b", "text"),
    "remove_spaces": (r"\b(?:remov(?:e|ing)|delet(?:e|ing)|strip(?:ping)?|eliminat(?:e|ing))\b[^.]{0,12}?\b(?:spaces?|whitespace)\b|\b(?:spaces?|whitespace)(?: (?:are|is|were|being))? (?:removed|deleted|stripped|eliminated)\b", "text"),
    "remove_vowels": (r"\b(?:remov(?:e|ing)|delet(?:e|ing)|strip(?:ping)?|eliminat(?:e|ing)|dropp?(?:ing)?)\b[^.]{0,12}?\bvowels?\b|\bvowels?(?: (?:are|is|were|being))? (?:removed|deleted|stripped|eliminated)\b", "text"),
    "swap_case": (r"\b(?:swap(?:ping)?|invert(?:ing)?|toggl(?:e|ing)|flip(?:ping)?)\b[^.]{0,12}?\bcase\b", "text"),
    "reverse_text": (r"\b(?:revers\w*|backwards?)\b", "text"),
    "count_vowels": (r"\b(?:count|how many|number of)\b[^.]{0,25}?\bvowels?\b", "scalar"),
    "count_words": (r"\b(?:count|how many|number of)\b[^.]{0,25}?\bwords\b", "scalar"),
    "count_uppercase": (r"\b(?:count|how many|number of)\b[^.]{0,25}?\b(?:upper ?case|capital)\b", "scalar"),
    "count_unique_characters": (r"\b(?:count|how many|number of)\b[^.]{0,25}?\b(?:unique|distinct)\b[^.]{0,15}?\b(?:characters?|letters?)\b", "scalar"),
    "count_characters": (r"\b(?:length|number of characters|how many characters)\b", "scalar"),
    "longest_word": (r"\blongest word\b", "scalar"),
    "pangram": (r"\bpangram\b", "scalar"), "count_items": (r"\b(?:count|how many|number of)\b", "scalar"),
    "maximum": (r"\b(?:maximum|largest|biggest|greatest|max)\b", "scalar"),
    "minimum": (r"\b(?:minimum|smallest|least|min)\b", "scalar"),
}
BY_KEY = {recipe.key: replace(recipe, stage=STAGES.get(recipe.key)) for recipe in (*RECIPES, *CODE_ONLY)}
TABLE_KEYS = {recipe.key for recipe in RECIPES}
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


_GENERIC = set("""number numbers list array text string word words character characters given each every find calculate
compute return write program that from then after those them with into what which please also just give take make
tell show result output value values integer integers item items element elements sequence collection this these
there where have does here whole function using want need would should could been being like some any only gets
produce get print want""".split())


def _stem(word: str) -> str:
    for suffix in ("ing", "ed", "es", "s"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            return word[: -len(suffix)]
    return word


_CLAUSE_BREAK = re.compile(r"\b(?:and|but|also|plus|while|along with|as well as)\b")
_SMALL = set("the and for are was its all not you any can out use per via but too yet his her how who why".split())


_ORIGINAL_WORDS = set("""pair pairs indices indexes positions position sorted ascending descending target merge combine binary search
brackets balanced parentheses delimiters palindrome anagram anagrams unique frequency frequencies duplicate duplicates
zeros zero subarray contiguous reverse backwards forwards forward backward lowest highest smallest largest
case sensitive insensitive punctuation whitespace spaces letters letter order""".split())
_COURTESY = set("thanks thank kindly cheers appreciated".split())


def _vocabulary() -> set[str]:
    """Every word any recipe, step or original family uses; a word outside it names something we cannot do."""
    words = set(_GENERIC) | _SMALL | _ORIGINAL_WORDS | _COURTESY
    for recipe in BY_KEY.values():
        own = " ".join((*recipe.patterns, *recipe.rejects, *recipe.assumptions, recipe.key.replace("_", " "),
                        recipe.function.replace("_", " "), *(recipe.stage[:1] if recipe.stage else ())))
        words |= set(re.findall(r"[a-z]{3,}", own.lower()))
    return {_stem(word) for word in words}


def unexplained(text: str) -> list[str]:
    """Words of an extra clause ("... and email it to my boss") that nothing in the catalog accounts for.

    Only text after the first conjunction is checked: the part before it already matched a task.
    """
    parts = _CLAUSE_BREAK.split(text, maxsplit=1)
    if len(parts) < 2:
        return []
    known = _vocabulary()
    return [word for word in re.findall(r"[a-z]{3,}", parts[1]) if _stem(word) not in known]


# Only operations and tasks with an unambiguous name: words like "sorted", "in order" or "number of" also
# describe inputs and outputs, so treating them as separate requested steps would refuse ordinary wordings.
_REMOVE_DUPLICATES = r"\b(?:remove|delete|eliminate|drop|filter out)\s+(?:all\s+|the\s+)?duplicate(?:s| values| numbers)?\b"  # "distinct" alone just describes values
_NAMED_STEPS = {"remove_duplicates", "reverse_list", "running_total", "square_numbers", "double_numbers"}
_NAMED_TASKS = {"factorial", "fibonacci", "is_prime", "palindrome_number", "pangram", "collatz", "fizzbuzz", "count_vowels",
                "remove_vowels", "median", "gcd", "lcm", "perfect_square", "leap_year", "power_of_two", "sum_of_digits",
                "count_primes", "binary_representation"}


def foreign_tasks(text: str, spec_key: str) -> list[str]:
    """Names of other tasks the request also asks for, which the chosen task would silently drop."""
    own = BY_KEY.get(spec_key)
    own_text = " ".join((spec_key.replace("_", " "), *((*own.patterns, *own.assumptions, own.function) if own else ()))).lower()
    found = []
    for key in _NAMED_STEPS | _NAMED_TASKS:
        regex = _REMOVE_DUPLICATES if key == "remove_duplicates" else STAGES[key][0] if key in STAGES else BY_KEY[key].patterns[0]
        match = re.search(regex, text)
        if key != spec_key and match and match.group() not in own_text and not re.search(regex, own_text):
            found.append(key.replace("_", " "))
    return sorted(found)


# --- steps whose number comes from the request ("greater than 5", "first three") ---
_NUMBER_WORDS = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}
_VALUE = r"(minus ?)?(\d+|" + "|".join(_NUMBER_WORDS) + r")"
_FILTER = "def {name}(nums):\n    return [number for number in nums if {test}]\n"
PARAM_STEPS = (  # (base name, regex with the number in groups 1-2, source template, assumption)
    ("filter_greater_than", r"\b(?:greater|larger|bigger|more|higher) than " + _VALUE + r"\b|\babove " + _VALUE + r"\b", _FILTER, "Keep values strictly greater than {n}.", "number > {n}"),
    ("filter_less_than", r"\b(?:less|smaller|fewer|lower) than " + _VALUE + r"\b|\bbelow " + _VALUE + r"\b", _FILTER, "Keep values strictly less than {n}.", "number < {n}"),
    ("filter_at_least", r"\bat least " + _VALUE + r"\b", _FILTER, "Keep values greater than or equal to {n}.", "number >= {n}"),
    ("filter_at_most", r"\bat most " + _VALUE + r"\b", _FILTER, "Keep values less than or equal to {n}.", "number <= {n}"),
    ("filter_divisible_by", r"\b(?:divisible by|multiples? of) " + _VALUE + r"\b", _FILTER, "Keep values divisible by {n}.", "number % {n} == 0"),
    ("take_first", r"\bfirst " + _VALUE + r"\b",
     "def {name}(nums):\n    result = []\n    for number in nums:\n        if len(result) < {n}:\n            result.append(number)\n    return result\n",
     "Keep the first {n} values (fewer if the list is shorter).", None),
    ("take_last", r"\blast " + _VALUE + r"\b",
     "def {name}(nums):\n    result = []\n    start = len(nums) - {n}\n    for index in range(len(nums)):\n        if index >= start:\n            result.append(nums[index])\n    return result\n",
     "Keep the last {n} values (fewer if the list is shorter).", None),
)


class _Family(str):
    """Stands in for an enum member for steps built on the fly."""
    value = property(lambda self: str(self))


def parameter(match) -> int:
    """The signed number captured by a PARAM_STEPS regex match."""
    groups = [group for group in match.groups() if group is not None]
    sign = -1 if groups[0].startswith("minus") else 1
    word = groups[-1]
    return sign * (_NUMBER_WORDS[word] if word in _NUMBER_WORDS else int(word))


def parametric_step(base: str, n: int) -> str:
    """Register (once) the step `base` with the number `n` and return its key."""
    key = f"{base}_{'minus_' if n < 0 else ''}{abs(n)}"
    if key not in BY_KEY:
        _, _, template, note, test = next(step for step in PARAM_STEPS if step[0] == base)
        source = template.format(name=key, n=n, test=(test or "").format(n=n))
        BY_KEY[key] = Recipe(key, key, _NUMS, "integer_list", (), (note.format(n=n),), source, stage=("", "list"))
    return key
