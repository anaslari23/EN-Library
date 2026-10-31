"""Typed-combinator synthesis: programs the recipe catalog never listed, built from a small vocabulary.

A request is read as a bag of typed operations ("keep the even numbers", "square each", "add them up").
Every ordering that type-checks is a candidate reading. Candidates are run on a fixed set of probe inputs;
readings that behave identically are the same program, so only real differences are ever ambiguous.
Embedded examples act as proof, and sentence cues ("of", "then", "and") break the remaining ties.
Anything left unexplained, or still ambiguous, is refused. Fully deterministic and offline.
"""

from __future__ import annotations

import ast
import itertools
import re
from dataclasses import dataclass

NUM = r"((?:minus )?(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten))"
_NUMBER_WORDS = {w: i for i, w in enumerate("zero one two three four five six seven eight nine ten".split())}


class SynthRefusal(Exception):
    def __init__(self, message: str, kind: str = "ambiguous"):
        super().__init__(message)
        self.message, self.kind = message, kind


@dataclass(frozen=True)
class Op:
    name: str
    src: str
    dst: str
    regex: "re.Pattern[str]"
    expr: str  # Python expression over {x} (the current value) and {n} (a number from the sentence)
    says: str
    note: str = ""
    helpers: tuple = ()

    @property
    def parametric(self) -> bool:
        return "{n}" in self.expr


HELPERS = {
    "_is_prime": "def _is_prime(n):\n    if n > 10 ** 12:\n        raise ValueError('number too large for this operation')\n    if n < 2:\n        return False\n    divisor = 2\n    while divisor * divisor <= n:\n        if n % divisor == 0:\n            return False\n        divisor += 1\n    return True\n",
    "_product": "def _product(values):\n    result = 1\n    for value in values:\n        result *= value\n    return result\n",
    "_median": "def _median(values):\n    if not values:\n        return None\n    ordered = sorted(values)\n    middle = len(ordered) // 2\n    if len(ordered) % 2:\n        return ordered[middle]\n    return (ordered[middle - 1] + ordered[middle]) / 2\n",
    "_mode": "def _mode(values):\n    if not values:\n        return None\n    counts = {}\n    for value in values:\n        counts[value] = counts.get(value, 0) + 1\n    best = max(counts.values())\n    return min(value for value, count in counts.items() if count == best)\n",
    "_running_total": "def _running_total(values):\n    total = 0\n    result = []\n    for value in values:\n        total += value\n        result.append(total)\n    return result\n",
    "_divisors": "def _divisors(n):\n    if abs(n) > 10 ** 5:\n        raise ValueError('number too large for this operation')\n    return [d for d in range(1, abs(n) + 1) if n % d == 0] if n != 0 else []\n",
    "_factorial": "def _factorial(n):\n    if n > 5000:\n        raise ValueError('number too large for this operation')\n    if n < 0:\n        return None\n    result = 1\n    for value in range(2, n + 1):\n        result *= value\n    return result\n",
    "_fibonacci": "def _fibonacci(n):\n    if n > 100000:\n        raise ValueError('number too large for this operation')\n    if n < 0:\n        return None\n    previous, current = 0, 1\n    for _ in range(n):\n        previous, current = current, previous + current\n    return previous\n",
    "_fib_list": "def _fib_list(n):\n    if n > 100000:\n        raise ValueError('number too large for this operation')\n    result = []\n    previous, current = 0, 1\n    for _ in range(max(n, 0)):\n        result.append(previous)\n        previous, current = current, previous + current\n    return result\n",
    "_collatz_steps": "def _collatz_steps(n):\n    if n > 10 ** 18:\n        raise ValueError('number too large for this operation')\n    if n < 1:\n        return None\n    steps = 0\n    while n != 1:\n        n = n // 2 if n % 2 == 0 else 3 * n + 1\n        steps += 1\n    return steps\n",
    "_is_square": "def _is_square(n):\n    if n < 0:\n        return False\n    root = int(n ** 0.5)\n    while root * root > n:\n        root -= 1\n    while (root + 1) * (root + 1) <= n:\n        root += 1\n    return root * root == n\n",
    "_is_leap": "def _is_leap(year):\n    return (year % 4 == 0 and year % 100 != 0) or year % 400 == 0\n",
    "_is_armstrong": "def _is_armstrong(n):\n    if n < 0:\n        return False\n    digits = str(n)\n    return sum(int(d) ** len(digits) for d in digits) == n\n",
    "_is_perfect": "def _is_perfect(n):\n    if n > 10 ** 5:\n        raise ValueError('number too large for this operation')\n    return n > 1 and sum(d for d in range(1, n) if n % d == 0) == n\n",
    "_is_palindrome": "def _is_palindrome(text):\n    cleaned = [c.lower() for c in text if c.isalnum()]\n    return cleaned == cleaned[::-1]\n",
    "_is_pangram": "def _is_pangram(text):\n    return set('abcdefghijklmnopqrstuvwxyz') <= set(text.lower())\n",
    "_consonants": "def _consonants(text):\n    return sum(1 for c in text.lower() if c.isalpha() and c not in 'aeiou')\n",
    "_primes_up_to": "def _primes_up_to(n):\n    if n > 10 ** 5:\n        raise ValueError('number too large for this operation')\n    if n < 2:\n        return []\n    flags = [True] * (n + 1)\n    flags[0] = flags[1] = False\n    for p in range(2, int(n ** 0.5) + 1):\n        if flags[p]:\n            for m in range(p * p, n + 1, p):\n                flags[m] = False\n    return [i for i, f in enumerate(flags) if f]\n",
    "_cap": "def _cap(n):\n    if abs(n) > 10 ** 5:\n        raise ValueError('number too large for this operation')\n    return n\n",
    "_binary": "def _binary(n):\n    return bin(n)[2:] if n >= 0 else '-' + bin(-n)[3:]\n",
}

OPS: list = []


def _op(name, src, dst, pattern, expr, says, note="", helpers=()):
    OPS.append(Op(name, src, dst, re.compile(pattern.replace("{N}", NUM)), expr, says, note, tuple(helpers)))


_LN = r"(?:list|array|numbers|integers|values|elements|items)"
_GT, _LT = r"(?:greater than|more than|larger than|bigger than|above|over|exceeding)", r"(?:less than|smaller than|fewer than|below|under)"
_COUNT = r"(?:count|how many|number of)"

# ---- list of integers -> list of integers
_op("keep_even", "ilist", "ilist", r"\bevens?\b", "[v for v in {x} if v % 2 == 0]", "keep the even numbers")
_op("keep_odd", "ilist", "ilist", r"\bodds?\b", "[v for v in {x} if v % 2 != 0]", "keep the odd numbers")
_op("keep_positive", "ilist", "ilist", r"\bpositives?\b", "[v for v in {x} if v > 0]", "keep the positive numbers")
_op("keep_negative", "ilist", "ilist", r"\bnegatives?\b", "[v for v in {x} if v < 0]", "keep the negative numbers")
_op("keep_nonzero", "ilist", "ilist", r"\bnon ?zero\b", "[v for v in {x} if v != 0]", "keep the non-zero numbers")
_op("keep_prime", "ilist", "ilist", r"\bprimes?\b", "[v for v in {x} if _is_prime(v)]", "keep the prime numbers", helpers=["_is_prime"])
_op("keep_greater", "ilist", "ilist", rf"\b{_GT} {{N}}\b", "[v for v in {x} if v > {n}]", "keep numbers greater than N")
_op("keep_less", "ilist", "ilist", rf"\b{_LT} {{N}}\b", "[v for v in {x} if v < {n}]", "keep numbers less than N")
_op("keep_at_least", "ilist", "ilist", r"\b(?:at least {N}|{N} or more)\b", "[v for v in {x} if v >= {n}]", "keep numbers at least N")
_op("keep_at_most", "ilist", "ilist", r"\b(?:at most {N}|{N} or less)\b", "[v for v in {x} if v <= {n}]", "keep numbers at most N")
_op("keep_divisible", "ilist", "ilist", r"\b(?:divisible by|multiples? of) {N}\b", "[v for v in {x} if v % {n} == 0]", "keep numbers divisible by N")
_op("square_each", "ilist", "ilist", r"\b(?:squares?|squared)\b", "[v * v for v in {x}]", "square each number")
_op("cube_each", "ilist", "ilist", r"\b(?:cubes?|cubed)\b", "[v * v * v for v in {x}]", "cube each number")
_op("double_each", "ilist", "ilist", r"\b(?:doubles?|doubled|twice)\b", "[v * 2 for v in {x}]", "double each number")
_op("negate_each", "ilist", "ilist", r"\b(?:negat(?:e|ed|ing)|opposites?)\b", "[-v for v in {x}]", "negate each number")
_op("absolute_each", "ilist", "ilist", r"\babsolute values?\b", "[abs(v) for v in {x}]", "take the absolute value of each number")
_op("sort_ascending", "ilist", "ilist", rf"\b(?:sort(?:ed|ing)?|arrange[d]?)\b(?: the)?(?: {_LN})?(?: (?:in|into|from))?(?: (?:an |the |a )?(?:ascending|increasing)(?: order)?)|\b(?:ascending|increasing) order\b|\bsmallest to (?:largest|biggest|greatest)\b", "sorted({x})", "sort ascending")  # a direction must be stated
_op("sort_descending", "ilist", "ilist", rf"\b(?:sort(?:ed|ing)?|arrange[d]?)\b(?: the)?(?: {_LN})?(?: (?:in|into|from))?(?: (?:an |the |a )?(?:descending|decreasing)(?: order)?)|\b(?:descending|decreasing)(?: order)?\b|\b(?:largest|biggest|greatest|highest) to (?:smallest|lowest|least)\b", "sorted({x}, reverse=True)", "sort descending")
_op("reverse_list", "ilist", "ilist", r"\b(?:revers(?:e|ed|ing)|backwards?)\b", "{x}[::-1]", "reverse the order")
_op("remove_duplicates", "ilist", "ilist", r"\b(?:remov\w*|delet\w*|eliminat\w*|drop\w*|discard\w*) (?:all |any |the )*duplicates?\b|\bwithout (?:any )?duplicates\b|\b(?:unique|distinct)\b|\bduplicates? (?:removed|eliminated|dropped)\b", "list(dict.fromkeys({x}))", "remove duplicates, keeping first occurrences")
_op("running_total", "ilist", "ilist", r"\b(?:running totals?|cumulative sums?|prefix sums?)\b", "_running_total({x})", "take running totals", helpers=["_running_total"])
_op("first_n", "ilist", "ilist", r"\bfirst {N}\b", "{x}[:{n}]", "keep the first N")
_op("last_n", "ilist", "ilist", r"\blast {N}\b", "{x}[max(len({x}) - {n}, 0):]", "keep the last N")
_op("differences", "ilist", "ilist", r"\b(?:consecutive|adjacent) differences\b|\bdifferences between (?:consecutive|adjacent|neighbou?ring) (?:numbers|values|elements|items)\b", "[b - a for a, b in zip({x}, {x}[1:])]", "take differences between neighbours")
# ---- list of integers -> a value
_op("total", "ilist", "int", r"\b(?:sum|total|add(?: them| these)?(?: all)? up|add up)\b", "sum({x})", "add them up")
_op("product", "ilist", "int", r"\b(?:product|multiply)\b", "_product({x})", "multiply them", "The product of an empty list is 1.", ["_product"])
_op("count_items", "ilist", "int", rf"\b(?:{_COUNT}|length|size)\b", "len({x})", "count them")
_op("maximum", "ilist", "int", r"\b(?:maximum|largest|biggest|greatest|highest|max)\b", "max({x}) if {x} else None", "take the largest", "Return null for an empty list.")
_op("minimum", "ilist", "int", r"\b(?:minimum|smallest|lowest|least|min)\b", "min({x}) if {x} else None", "take the smallest", "Return null for an empty list.")
_op("average", "ilist", "num", r"\b(?:average|mean)\b", "sum({x}) / len({x}) if {x} else None", "take the average", "Return null for an empty list.")
_op("median", "ilist", "num", r"\bmedian\b", "_median({x})", "take the median", "Return null for an empty list.", ["_median"])
_op("mode", "ilist", "int", r"\b(?:mode|most common|most frequent)\b", "_mode({x})", "take the most frequent value", "Ties go to the smallest value; null for an empty list.", ["_mode"])
_op("spread", "ilist", "int", r"\b(?:range|spread)\b", "max({x}) - min({x}) if {x} else None", "take largest minus smallest", "Return null for an empty list.")
_op("second_largest", "ilist", "int", r"\bsecond (?:largest|biggest|highest|greatest)\b", "sorted(set({x}))[-2] if len(set({x})) >= 2 else None", "take the second largest distinct value", "Return null when fewer than two distinct values exist.")
_op("second_smallest", "ilist", "int", r"\bsecond (?:smallest|lowest)\b", "sorted(set({x}))[1] if len(set({x})) >= 2 else None", "take the second smallest distinct value", "Return null when fewer than two distinct values exist.")
_op("has_duplicates", "ilist", "bool", r"\b(?:contains?|has|have|any) (?:any )?duplicates?\b", "len(set({x})) != len({x})", "check for duplicates")
_op("join_commas", "ilist", "text", r"\bcomma separated\b|\bjoin\b.{0,20}\bcommas?\b", "', '.join(str(v) for v in {x})", "join with commas")
# ---- text -> text
_op("to_uppercase", "text", "text", r"\b(?:upper ?case|capital letters|all caps)\b", "{x}.upper()", "make it uppercase")
_op("to_lowercase", "text", "text", r"\b(?:lower ?case|small letters)\b", "{x}.lower()", "make it lowercase")
_op("swap_case", "text", "text", r"\b(?:swap(?:ping)?|invert(?:ing)?|toggl(?:e|ing)|flip(?:ping)?) (?:the )?case\b", "{x}.swapcase()", "swap the case")
_op("title_case", "text", "text", r"\b(?:capitali[sz]e|title ?case)\b", "{x}.title()", "capitalize each word")
_op("remove_spaces", "text", "text", r"\b(?:remov\w*|delet\w*|strip\w*|eliminat\w*) (?:all |the )?(?:spaces|whitespace)\b", "''.join({x}.split())", "remove all whitespace")
_op("remove_vowels", "text", "text", r"\b(?:remov\w*|delet\w*|strip\w*|eliminat\w*|drop\w*) (?:all |the )?vowels\b", "''.join(c for c in {x} if c.lower() not in 'aeiou')", "remove the vowels")
_op("remove_digits", "text", "text", r"\b(?:remov\w*|delet\w*|strip\w*|eliminat\w*|drop\w*) (?:all |the )?digits\b", "''.join(c for c in {x} if not c.isdigit())", "remove the digits")
_op("remove_punctuation", "text", "text", r"\b(?:remov\w*|delet\w*|strip\w*|eliminat\w*) (?:all |the )?punctuation\b", "''.join(c for c in {x} if c.isalnum() or c.isspace())", "remove punctuation")
_op("reverse_text", "text", "text", r"\b(?:revers(?:e|ed|ing)|backwards?)\b", "{x}[::-1]", "reverse the characters")
_op("reverse_word_order", "text", "text", r"\brevers(?:e|ed|ing) (?:the )?(?:order of )?(?:the )?words\b", "' '.join(reversed({x}.split()))", "reverse the order of the words")
_op("sort_letters", "text", "text", r"\bsort(?:ed|ing)?(?: the)? (?:letters|characters)\b", "''.join(sorted({x}))", "sort the characters")
_op("remove_repeated_characters", "text", "text", r"\bremov\w* (?:all |the )?(?:duplicate|repeated) (?:characters|letters)\b", "''.join(dict.fromkeys({x}))", "remove repeated characters, keeping first occurrences")
_op("to_binary", "int", "text", r"\bbinary\b", "_binary({x})", "write it in binary", helpers=["_binary"])
# ---- text -> value
_op("length", "text", "int", rf"\b(?:length|number of (?:characters|letters)|how many (?:characters|letters)|{_COUNT} (?:the )?(?:characters|letters))\b", "len({x})", "count the characters")
_op("count_vowels", "text", "int", rf"\b{_COUNT}\b.{{0,25}}?\bvowels?\b", "sum(1 for c in {x} if c.lower() in 'aeiou')", "count the vowels", "Vowels are a, e, i, o, u in either case.")
_op("count_consonants", "text", "int", rf"\b{_COUNT}\b.{{0,25}}?\bconsonants?\b", "_consonants({x})", "count the consonants", helpers=["_consonants"])
_op("count_words", "text", "int", rf"\b{_COUNT}\b.{{0,25}}?\bwords\b", "len({x}.split())", "count the words")
_op("count_uppercase", "text", "int", rf"\b{_COUNT}\b.{{0,25}}?\b(?:upper ?case|capital)\b", "sum(1 for c in {x} if c.isupper())", "count the uppercase letters")
_op("count_lowercase", "text", "int", rf"\b{_COUNT}\b.{{0,25}}?\blower ?case\b", "sum(1 for c in {x} if c.islower())", "count the lowercase letters")
_op("count_digit_characters", "text", "int", rf"\b{_COUNT}\b.{{0,25}}?\bdigits\b", "sum(1 for c in {x} if c.isdigit())", "count the digits")
_op("count_unique_characters", "text", "int", rf"\b{_COUNT}\b.{{0,25}}?\b(?:unique|distinct)\b.{{0,15}}?\b(?:characters|letters)\b", "len(set({x}))", "count the distinct characters")
_op("is_palindrome_text", "text", "bool", r"\bpalindrom\w*\b", "_is_palindrome({x})", "check for a palindrome", "Case and non-alphanumeric characters are ignored.", ["_is_palindrome"])
_op("is_pangram", "text", "bool", r"\bpangram\b", "_is_pangram({x})", "check for a pangram", helpers=["_is_pangram"])
# ---- text <-> list of words
_op("split_words", "text", "tlist", r"\b(?:split|break)\b.{0,20}\bwords\b", "{x}.split()", "split into words")
_op("split_characters", "text", "tlist", r"\b(?:split|break)\b.{0,20}\b(?:characters|letters)\b", "list({x})", "split into characters")
_op("keep_longer", "tlist", "tlist", r"\b(?:words |ones )?(?:longer|more) than {N}(?: characters| letters)?\b", "[w for w in {x} if len(w) > {n}]", "keep words longer than N")
_op("keep_shorter", "tlist", "tlist", r"\b(?:words |ones )?(?:shorter|fewer) than {N}(?: characters| letters)?\b", "[w for w in {x} if len(w) < {n}]", "keep words shorter than N")
_op("sort_alphabetically", "tlist", "tlist", r"\b(?:sort\w*|arrange\w*)\b.{0,15}\balphabetical\w*|\balphabetical(?:ly| order)\b", "sorted({x})", "sort alphabetically")
_op("unique_words", "tlist", "tlist", r"\b(?:unique|distinct) words\b|\bremov\w* (?:the )?duplicate words\b", "list(dict.fromkeys({x}))", "remove duplicate words")
_op("count_entries", "tlist", "int", rf"\b(?:{_COUNT}|length|size)\b", "len({x})", "count them")
_op("longest_entry", "tlist", "text", r"\blongest(?: word)?\b", "max({x}, key=len) if {x} else ''", "take the longest word", "The first of equally long words wins; empty text gives an empty string.")
_op("shortest_entry", "tlist", "text", r"\bshortest(?: word)?\b", "min({x}, key=len) if {x} else ''", "take the shortest word", "The first of equally short words wins; empty text gives an empty string.")
# ---- single number
_op("is_prime_number", "int", "bool", r"\bprime\b", "_is_prime({x})", "check for a prime", "Numbers below 2 are not prime.", ["_is_prime"])
_op("is_even_number", "int", "bool", r"\beven\b", "{x} % 2 == 0", "check for even")
_op("is_odd_number", "int", "bool", r"\bodd\b", "{x} % 2 != 0", "check for odd")
_op("is_perfect_square", "int", "bool", r"\bperfect squares?\b", "_is_square({x})", "check for a perfect square", helpers=["_is_square"])
_op("is_power_of_two", "int", "bool", r"\bpower of (?:two|2)\b", "{x} > 0 and {x} & ({x} - 1) == 0", "check for a power of two")
_op("is_leap_year", "int", "bool", r"\bleap years?\b", "_is_leap({x})", "check for a leap year", helpers=["_is_leap"])
_op("is_armstrong", "int", "bool", r"\barmstrong\b", "_is_armstrong({x})", "check for an Armstrong number", helpers=["_is_armstrong"])
_op("is_perfect_number", "int", "bool", r"\bperfect (?:number|numbers)\b", "_is_perfect({x})", "check for a perfect number", helpers=["_is_perfect"])
_op("is_palindrome_number", "int", "bool", r"\bpalindrom\w*\b", "str({x}) == str({x})[::-1]", "check for a palindromic number", "Negative numbers are not palindromes.")
_op("factorial", "int", "int", r"\bfactorial\b", "_factorial({x})", "take the factorial", "Return null for a negative number.", ["_factorial"])
_op("fibonacci_term", "int", "int", r"\bfibonacci\b", "_fibonacci({x})", "take the Fibonacci term", "F(0) = 0 and F(1) = 1; null for a negative number.", ["_fibonacci"])
_op("collatz_steps", "int", "int", r"\bcollatz\b", "_collatz_steps({x})", "count the Collatz steps", "Return null below 1.", ["_collatz_steps"])
_op("square_number", "int", "int", r"\b(?:square|squared)\b", "{x} * {x}", "square it")
_op("absolute_number", "int", "int", r"\babsolute value\b", "abs({x})", "take the absolute value")
_op("reverse_digits", "int", "int", r"\brevers\w* (?:the )?(?:digits of )?(?:a |the |its )?(?:number|digits)\b|\breversed number\b", "(-1 if {x} < 0 else 1) * int(str(abs({x}))[::-1])", "reverse its digits")
_op("digits", "int", "ilist", r"\bdigits?\b", "[int(c) for c in str(abs({x}))]", "list its digits", "The sign is ignored.")
_op("divisors", "int", "ilist", r"\b(?:divisors?|factors)\b", "_divisors({x})", "list its divisors", "Divisors of 0 are an empty list.", ["_divisors"])
_op("primes_up_to", "int", "ilist", r"\bprimes? (?:up to|upto|till|not exceeding)\b", "_primes_up_to({x})", "list the primes up to it (including it)", "Numbers above 100,000 are refused.", ["_primes_up_to"])
_op("primes_below", "int", "ilist", r"\bprimes? (?:below|under|less than|smaller than)\b", "_primes_up_to({x} - 1)", "list the primes below it", "Numbers above 100,000 are refused.", ["_primes_up_to"])
_op("natural_numbers", "int", "ilist", r"\b(?:natural numbers|numbers from 1 to|integers from 1 to|numbers up to|numbers till)\b", "list(range(1, _cap({x}) + 1))", "list 1 up to it", "Numbers above 100,000 are refused.", ["_cap"])
_op("fibonacci_list", "int", "ilist", r"\bfibonacci (?:numbers|sequence|series|terms)\b", "_fib_list({x})", "list that many Fibonacci numbers", helpers=["_fib_list"])

COERCE = {("text", "tlist"): ("split into words", "{x}.split()"), ("tlist", "text"): ("join with spaces", "' '.join({x})")}
STOP = set("""a an the of in on to from and then after that those them it its this these is are be each every all any given please write program
function find compute calculate return get give me what which whole list array numbers integers values elements items sequence collection
text string strings sentence phrase word words character characters letters number integer n for by with into as only also just can you i
want need would like should create make using use result output new there where have does here afterwards followed form representation version keep take check whether determine verify decide test will would could shall may might do did me us we our my your their""".split())
_NOUNS = {
    "ilist": re.compile(r"\b(?:list|array|numbers|integers|values|elements|items|sequence|collection)\b"),
    "text": re.compile(r"\b(?:text|string|strings|sentence|phrase|word|words|characters|letters)\b"),
    "int": re.compile(r"\b(?:number|integer|digit|digits|n)\b"),
}
_QUESTION = re.compile(r"^(?:is|are|does|do|can|has|have)\b|\b(?:check|whether|determine|test|verify|decide)\b")
_CONJUNCTION = re.compile(r"\b(?:and|then|afterwards|after that|followed by)\b")
_INPUT = {"ilist": ("nums", "integer_list"), "text": ("text", "string"), "int": ("n", "integer")}
_KIND = {"int": "integer", "num": "number", "bool": "boolean", "ilist": "integer_list", "text": "string", "tlist": "string_list"}
PROBES = {
    "ilist": [[], [0], [7], [-3], [2, 2], [1, 2, 3, 4, 5, 6], [6, 5, 4, 3, 2, 1], [3, -1, 3, 0, -5, 8, 8, 2], [10, 9, 1, 1, 4], [-2, -4, -6],
              [11, 13, 17, 4, 9, 25], [5, 3, 5, 3, 5], [100, -100, 50, -50, 25], [12, 18, 24, 36, 7, 7, 1]],
    "text": ["", "a", "Hello World", "  spaces  here ", "Level", "racecar", "The quick brown fox jumps over the lazy dog", "AbC aBc 123",
             "banana bandana", "x y x y z", "Madam, I'm Adam", "aeiou AEIOU", "to be or not to be"],
    "int": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 15, 16, 17, 24, 28, 100, 121, 153, 371, 400, -5, -12, 97],
}
_NAMESPACE: dict = {}
for _source in HELPERS.values():
    exec(_source, _NAMESPACE)
_COMPILED: dict = {}


def _number(token: str) -> int:
    if token.startswith("minus "):
        return -_number(token[6:])
    return int(token) if token.isdigit() else _NUMBER_WORDS[token]


def _function_of(op_expr: str, n):
    key = (op_expr, n)
    if key not in _COMPILED:
        body = op_expr.replace("{x}", "x").replace("{n}", str(n))
        _COMPILED[key] = eval("lambda x: " + body, _NAMESPACE)
    return _COMPILED[key]


def _steps_of(chain):
    return [(item[0].expr, item[1]) if item[0] is not None else (item[2], None) for item in chain]


def _run(chain, value):
    try:
        for expr, n in _steps_of(chain):
            value = _function_of(expr, n)(value)
        return value
    except Exception as error:  # a runtime failure is part of the behaviour being compared
        return "ERR:" + type(error).__name__


def _fingerprint(value):
    """A comparable, always-printable stand-in for a result (huge integers are summarised, not printed)."""
    if isinstance(value, bool) or value is None or isinstance(value, (str, float)):
        return value
    if isinstance(value, int):
        return value if abs(value) < 10 ** 40 else ("big", value.bit_length(), value % 1000003)
    if isinstance(value, list):
        return [_fingerprint(item) for item in value]
    return str(value)


def signature(chain, input_type) -> str:
    return repr([_fingerprint(_run(chain, probe)) for probe in PROBES[input_type]])


def _mentions(text: str):
    found = []
    for op in OPS:
        for match in op.regex.finditer(text):
            found.append((match.start(), match.end(), op, _number(match.group(1)) if op.parametric else None))
    found.sort(key=lambda item: (-(item[1] - item[0]), item[0]))
    spans, kept = [], []
    for item in found:
        span = (item[0], item[1])
        if span in spans:
            kept.append(item)
        elif not any(item[0] < end and start < item[1] for start, end in spans):
            spans.append(span)
            kept.append(item)
    groups = {}
    for start, end, op, n in kept:
        groups.setdefault((start, end), []).append((op, n))
    return [(span, groups[span]) for span in sorted(groups)]


def _typed(sequence, input_type):
    """The chain with implicit text<->word-list conversions inserted, or None if it does not type-check."""
    chain, current = [], input_type
    for op, n in sequence:
        if current != op.src:
            bridge = COERCE.get((current, op.src))
            if bridge is None:
                return None
            chain.append((None, None, bridge[1], bridge[0]))
            current = op.src
        chain.append((op, n, None, None))
        current = op.dst
    return chain


def _describe(chain) -> str:
    parts = []
    for op, n, _, says in chain:
        parts.append(says if op is None else op.says.replace("N", str(n)) if n is not None else op.says)
    return ", then ".join(parts)


def _name_of(chain) -> str:
    names = [item[0].name if item[0] is not None else "split_words" if item[2].endswith("split()") else "join_words" for item in chain]
    return "_then_".join(names)[:70].rstrip("_")


@dataclass(frozen=True)
class Program:
    input_type: str
    chain: tuple
    paraphrase: str
    function_name: str
    examples_checked: int = 0

    @property
    def result_type(self) -> str:
        last = [item for item in self.chain if item[0] is not None][-1][0]
        return _KIND[last.dst]

    @property
    def parameter(self):
        return _INPUT[self.input_type]

    def assumptions(self):
        notes = [f"Interpreted as: {self.paraphrase}."]
        notes += [item[0].note for item in self.chain if item[0] is not None and item[0].note]
        return list(dict.fromkeys(notes))

    def helper_names(self):
        names = []
        for item in self.chain:
            for name in (item[0].helpers if item[0] is not None else ()):
                if name not in names:
                    names.append(name)
        return names

    def source(self) -> str:
        parameter = self.parameter[0]
        lines = [f"def {self.function_name}({parameter}):", f"    value = {parameter}"]
        for op, n, expr, says in self.chain:
            body = (op.expr if op is not None else expr).replace("{x}", "value").replace("{n}", str(n))
            label = says if op is None else (op.says.replace("N", str(n)) if n is not None else op.says)
            lines.append(f"    value = {body}  # {label}")
        lines.append("    return value")
        return "\n".join(lines) + "\n"

    def helper_asts(self):
        return [ast.parse(HELPERS[name]).body[0] for name in self.helper_names()]

    def function_ast(self):
        return ast.parse(self.source()).body[0]


def _matches(chain, example) -> bool:
    values = list(example.input.values())
    return len(values) == 1 and _run(chain, values[0]) == example.expected


def synthesize(text: str, examples=()) -> Program | None:
    """The one program this request describes, None if it has no operations, or a SynthRefusal explaining why not."""
    mentions = _mentions(text)
    if not mentions or len(mentions) > 6:
        return None
    rest = text
    for (start, end), _ in reversed(mentions):
        rest = rest[:start] + " " + rest[end:]
    leftover = [word for word in re.findall(r"[a-z0-9]+", rest) if word not in STOP]
    if leftover:
        raise SynthRefusal(f"I can't account for: {', '.join(leftover)}", "unsupported")
    candidates = [kind for kind, noun in _NOUNS.items() if noun.search(text)]
    if not candidates:
        return None
    gaps = []
    for index in range(len(mentions) - 1):
        gaps.append(bool(_CONJUNCTION.search(text[mentions[index][0][1]:mentions[index + 1][0][0]])))
    found = {}
    for input_type in candidates:
        classes = {}
        for choice in itertools.product(*[alternatives for _, alternatives in mentions]):
            for order in itertools.permutations(range(len(choice))):
                chain = _typed([choice[i] for i in order], input_type)
                if chain is None:
                    continue
                signature_text = signature(chain, input_type)
                violations = sum((order.index(i) < order.index(i + 1)) != forward for i, forward in enumerate(gaps))
                classes.setdefault(signature_text, []).append((violations, len(chain), _name_of(chain), chain))
        if classes:
            found[input_type] = classes
    if not found:
        return None
    if len(found) > 1:
        raise SynthRefusal("this could be about " + " or ".join({"ilist": "a list of numbers", "text": "a text", "int": "a single number"}[k] for k in found) + "; say which input you mean")
    input_type, classes = next(iter(found.items()))
    checked = 0
    if examples:
        classes = {s: m for s, m in classes.items() if all(_matches(min(m, key=lambda item: item[:3])[3], e) for e in examples)}
        checked = len(examples)
        if not classes:
            raise SynthRefusal("no reading of this request reproduces your example", "ambiguous")
    if len(classes) > 1:
        best = min(item[0] for members in classes.values() for item in members)
        classes = {s: m for s, m in classes.items() if min(item[0] for item in m) == best}
        if len(classes) > 1 or best > 0:
            readings = sorted({_describe(min(m, key=lambda item: item[:3])[3]) for m in classes.values()})
            raise SynthRefusal("this has more than one reading: " + " OR ".join(readings) + ". Say the steps in order with 'then'.", "ambiguous")
    chain = min(next(iter(classes.values())), key=lambda item: item[:3])[3]
    if _QUESTION.search(text) and [item for item in chain if item[0] is not None][-1][0].dst != "bool":
        raise SynthRefusal("this asks a yes/no question, but I can only answer it when it names a check (even, prime, palindrome, ...)", "unsupported")
    used = {item[0].name for item in chain if item[0] is not None}
    if {"sort_ascending", "reverse_list"} <= used:
        raise SynthRefusal("'sort and reverse' could mean descending order; say 'sort descending' or 'sort, then reverse'", "ambiguous")
    for op, n, _, _ in chain:
        if op is not None and op.name == "keep_divisible" and n == 0:
            raise SynthRefusal("divisible by zero is undefined", "unsupported")
    return Program(input_type, tuple(chain), _describe(chain), _name_of(chain), checked)
