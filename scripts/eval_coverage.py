"""Held-out coverage eval: for each wording, is the generated code correct, wrong, or refused?

Usage: python3 scripts/eval_coverage.py [-v]
A case with expected=None must be refused; generating any code for it counts as wrong.
"""
import json
import sys

from codeinenglish.interpreter import interpret_source
from codeinenglish.problem_solver import render_problem_python

N, T = "nums", "text"
CASES = [
    # single tasks, reworded
    ("Return the sum of all numbers in the list.", {N: [1, 2, 3]}, 6),
    ("What is the biggest value in an array of integers?", {N: [3, 9, 2]}, 9),
    ("Given a list, tell me whether any value appears twice.", {N: [1, 2, 1]}, True),
    ("Reverse the order of a list of numbers.", {N: [1, 2, 3]}, [3, 2, 1]),
    ("Compute the average of the numbers.", {N: [1, 2, 3, 4]}, 2.5),
    ("How many words are in a sentence?", {T: "a b c"}, 3),
    ("Make this text all caps.", {T: "hi"}, "HI"),
    ("Is the given number prime?", {"n": 7}, True),
    ("Return the factorial of n.", {"n": 5}, 120),
    ("Find the median of a list of integers.", {N: [5, 1, 3]}, 3),
    ("Count the vowels in the string.", {T: "audio"}, 4),
    ("Remove all duplicate values from a list.", {N: [1, 1, 2]}, [1, 2]),
    ("Check if a word reads the same forwards and backwards.", {T: "level"}, True),
    ("Find the smallest number in the list.", {N: [4, 2, 8]}, 2),
    ("Multiply all the numbers in the list together.", {N: [2, 3, 4]}, 24),
    ("Return the second largest value in the list.", {N: [1, 5, 3]}, 3),
    ("Convert a temperature in celsius to fahrenheit.", {"celsius": 0}, 32.0),
    ("Sort the numbers from smallest to largest.", {N: [3, 1, 2]}, [1, 2, 3]),
    ("Find the greatest common divisor of two numbers.", {"first": 12, "second": 18}, 6),
    ("Is a year a leap year?", {"year": 2000}, True),
    # compositions the catalog was never written for
    ("Find the sum of the squares of the even numbers in a list.", {N: [1, 2, 3, 4]}, 20),
    ("Count the odd numbers in the list.", {N: [1, 2, 3]}, 2),
    ("Sort the unique numbers in ascending order.", {N: [3, 1, 3]}, [1, 3]),
    ("Remove duplicates, then reverse the list.", {N: [1, 2, 1, 3]}, [3, 2, 1]),
    ("Double each number and then add them all up.", {N: [1, 2, 3]}, 12),
    ("Find the average of the positive numbers.", {N: [-1, 2, 4]}, 3.0),
    ("What is the maximum of the squared values?", {N: [-3, 2]}, 9),
    ("Sort the numbers in descending order.", {N: [1, 3, 2]}, [3, 2, 1]),
    ("How many positive numbers are in the list?", {N: [1, -1, 2]}, 2),
    ("Return the product of the even numbers.", {N: [1, 2, 3, 4]}, 8),
    ("Take the even numbers and sum them.", {N: [1, 2, 3, 4]}, 6),
    ("Find the smallest of the odd numbers in the list.", {N: [4, 3, 5, 1]}, 1),
    ("Sum the squares of the numbers in the list.", {N: [1, 2, 3]}, 14),
    ("Give me the running total of the even numbers.", {N: [1, 2, 3, 4]}, [2, 6]),
    # must be refused, never answered with the wrong program
    ("Send an email to my boss.", None, None),
    ("Compose a symphony.", None, None),
    ("Find the sum of the numbers greater than 10 in the list.", None, None),
    ("Count the vowels in the string and print them in red.", None, None),
    ("Sort the list by the length of each item.", None, None),
]


# Adversarial set, written after the matcher was built and not used to tune it.
TRAPS = [
    # a condition the tool cannot apply: running the plain task would be a silent wrong answer
    ("Sum the numbers greater than 5 in the list.", None, None),
    ("Sum the first three numbers of the list.", None, None),
    ("Count the vowels and the consonants in the string.", None, None),
    ("Find the largest number below 100 in the list.", None, None),
    ("Return the even numbers sorted by their square.", None, None),
    ("Find the sum of the list but skip negative numbers.", None, None),
    ("Is the number divisible by 3?", None, None),
    ("Translate the text to French.", None, None),
    ("Count the words in the text that start with a capital letter.", None, None),
    ("Find the average of the list excluding the maximum.", None, None),
    ("Remove duplicates from the list and sum what is left.", None, None),
    ("Merge two sorted lists and remove the duplicates.", None, None),
    ("Check if the text is a palindrome and count its vowels.", None, None),
    # unseen wordings that should work
    ("Add up every value in the array.", {N: [1, 2, 3]}, 6),
    ("Give me the total of the positive values.", {N: [1, -2, 3]}, 4),
    ("Reverse the list and then sort it in descending order.", {N: [2, 1, 3]}, [3, 2, 1]),
    ("Find the minimum of the doubled numbers.", {N: [3, 1, 2]}, 2),
    ("What is the mean of the even integers?", {N: [2, 3, 4]}, 3.0),
    ("Count how many items there are in the list.", {N: [4, 5]}, 2),
    ("Tell me the biggest of the squares of the numbers.", {N: [-3, 2]}, 9),
    ("Return the even numbers that are also positive.", {N: [-2, 1, 4]}, [4]),
    ("Sort the list, then remove the duplicates.", {N: [3, 1, 3]}, [1, 3]),
    ("What is the product of the odd numbers?", {N: [1, 2, 3, 5]}, 15),
]


def run(prompt, given):
    spec = interpret_source("target python\n# " + prompt + "\n")
    scope = {"__name__": "generated"}
    exec(compile(render_problem_python(spec), "<generated>", "exec"), scope)
    return json.loads(json.dumps(scope[spec.function_name](**given)))


def classify(prompt, given, expected):
    """('correct' | 'wrong' | 'refused', detail). A must-refuse prompt is correct only if no code is generated."""
    if given is None:
        try:
            spec = interpret_source("target python\n# " + prompt + "\n")
        except Exception as error:
            return "correct", type(error).__name__
        return "wrong", f"generated {spec.function_name}()"
    try:
        got = run(prompt, given)
    except Exception as error:
        return "refused", type(error).__name__
    return ("correct" if got == expected else "wrong"), repr(got)


def main(verbose=False, cases=None):
    cases = cases or CASES
    counts = {"correct": 0, "wrong": 0, "refused": 0}
    for prompt, given, expected in cases:
        outcome, detail = classify(prompt, given, expected)
        counts[outcome] += 1
        if verbose and outcome != "correct":
            print(f"{outcome.upper():8} {prompt!r} -> {detail} (expected {expected!r})")
    print(f"cases={len(cases)} correct={counts['correct']} wrong={counts['wrong']} refused={counts['refused']}")
    return counts


if __name__ == "__main__":
    main("-v" in sys.argv, TRAPS if "--traps" in sys.argv else None)
