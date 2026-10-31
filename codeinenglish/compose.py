"""Compose list stages mentioned in one request: "sum of the squares of the even numbers in a list".

Each recipe with a `stage` is a building block. The request is scanned for blocks, ordered from its
structure, type-checked (only the last block may produce a single value), and refused if any meaningful
word is left unexplained, so it never quietly drops part of what was asked.
"""
import re

from .recipes import BY_KEY, PARAM_STEPS, parameter, parametric_step

_PLURAL_LIST_NOUN = re.compile(r"\b(?:list|array|numbers|integers|values|elements|items|sequence)\b")
_TEXT_NOUN = re.compile(r"\b(?:text|string|strings|sentence|words?|characters?|letters?|phrase)\b")
_LIST_NOUN = re.compile(r"\b(?:list|array|numbers?|integers?|values?|elements?|items?|sequence)\b")
_CONJUNCTION = re.compile(r"\b(?:and|then|afterwards|followed by|after that)\b")
_PHRASES = (  # fixed phrasings rewritten before scanning, so their words are not read as separate stages
    (re.compile(r"\b(?:from )?(?:smallest|lowest|least) to (?:largest|highest|greatest|biggest)\b"), "ascending"),
    (re.compile(r"\b(?:from )?(?:largest|highest|greatest|biggest) to (?:smallest|lowest|least)\b"), "descending"),
)
_STOP = set("""list array numbers integers values elements items given each every find calculate compute return write
program that from then after those them with into what which whole please also just give take make tell show result
output sequence collection this these there where have does here afterwards followed number only keep retain select filter pick extract convert converting change changing turning transform version applying apply using string text sentence phrase left remaining once still""".split())
_MEANINGFUL_SMALL = re.compile(r"\b(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten)\b")


STAGE_KEYS = {key for key, recipe in BY_KEY.items() if recipe.stage and recipe.stage[0]}


def strip_parameters(text: str) -> str:
    """The request with every "greater than 5"-style phrase removed (those are handled as steps)."""
    for _, regex, *_ in PARAM_STEPS:
        text = re.sub(regex, " ", text)
    return text


def _stages(domain: str):
    """Steps for one kind of input: a list of integers or a text."""
    wanted = "string" if domain == "text" else "integer_list"
    return [(key, re.compile(recipe.stage[0]), recipe.stage[1]) for key, recipe in BY_KEY.items()
            if recipe.stage and recipe.stage[0] and len(recipe.inputs) == 1 and recipe.inputs[0][1] == wanted]


def analyze(text: str) -> tuple[list[str] | None, int]:
    """(recipe keys in application order or None, number of distinct steps found).

    A step count of 2+ with no order means the request names several steps that could not be combined."""
    in_list, in_text = bool(_LIST_NOUN.search(text)), bool(_TEXT_NOUN.search(text))
    if in_list == in_text:  # neither (nothing to compose) or both (which input is meant?)
        return None, 0
    domain = "list" if in_list else "text"
    for pattern, replacement in _PHRASES:
        text = pattern.sub(replacement, text)
    found = []
    for key, pattern, out in _stages(domain):
        found += [(match.start(), match.end(), key, out) for match in pattern.finditer(text)]
    for base, regex, *_ in PARAM_STEPS if domain == "list" else ():
        found += [(match.start(), match.end(), parametric_step(base, parameter(match)), "list") for match in re.finditer(regex, text)]
    found.sort(key=lambda item: (item[0], -(item[1] - item[0])))
    mentions, end = [], -1
    for item in found:  # longest-first, no overlaps
        if item[0] >= end:
            mentions.append(item)
            end = item[1]
    if {"sort_descending", "sort_ascending"} <= {item[2] for item in mentions}:
        mentions = [item for item in mentions if item[2] != "sort_ascending"]
    rest = text
    for start, stop, _, _ in reversed(mentions):
        rest = rest[:start] + " " + rest[stop:]
    seen, unique = set(), []
    for item in mentions:  # "sort ... in ascending order" names one step twice; keep the first
        if item[2] not in seen:
            seen.add(item[2])
            unique.append(item)
    mentions = unique
    count = len(mentions)
    has_parameter = any(item[2] not in STAGE_KEYS for item in mentions)
    if count < 2 and not (has_parameter and _PLURAL_LIST_NOUN.search(text)):  # one step alone needs a clear list
        return None, count
    if {"sort_ascending", "reverse_list"} <= {item[2] for item in mentions}:
        return None, count  # "sort and reverse" is ambiguous (descending order?); let the older rules ask
    if _MEANINGFUL_SMALL.search(rest) or any(len(word) >= 4 and word not in _STOP for word in re.findall(r"[a-z]+", rest)):
        return None, count
    # a conjunction between two mentions means "in the order said"; otherwise the later one is applied first
    after = {index: set() for index in range(len(mentions))}
    for index in range(len(mentions) - 1):
        gap = text[mentions[index][1]:mentions[index + 1][0]]
        first, second = (index, index + 1) if _CONJUNCTION.search(gap) else (index + 1, index)
        after[first].add(second)
    for index, item in enumerate(mentions):
        if item[3] == "scalar":
            for other in range(len(mentions)):
                if other != index:
                    after[other].add(index)
    waiting = {index: sum(index in later for later in after.values()) for index in after}
    order = []
    while waiting:
        ready = [index for index, count in waiting.items() if count == 0]
        if len(ready) != 1:
            return None, count  # cyclic or ambiguous
        order.append(ready[0])
        del waiting[ready[0]]
        for later in after[ready[0]]:
            waiting[later] -= 1
    outs = [mentions[index][3] for index in order]
    if any(out == "scalar" for out in outs[:-1]):
        return None, count  # a single value cannot be fed into another step
    return [mentions[index][2] for index in order], count


def plan(text: str) -> list[str] | None:
    return analyze(text)[0]
