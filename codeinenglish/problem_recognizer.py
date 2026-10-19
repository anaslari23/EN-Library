import re
from dataclasses import dataclass
from enum import Enum
from typing import Literal

from .errors import CodeInEnglishError
from .problem_prompt import ProblemExample, ProblemPrompt


class ProblemFamily(str, Enum):
    TWO_SUM = "two_sum"
    DUPLICATES = "duplicates"
    FREQUENCIES = "frequencies"
    PALINDROME = "palindrome"
    ANAGRAM = "anagram"
    BINARY_SEARCH = "binary_search"
    MINIMUM = "minimum"
    MAXIMUM = "maximum"
    SUM = "sum"
    FIRST_UNIQUE_CHARACTER = "first_unique_character"
    REVERSE_TEXT = "reverse_text"
    MOVE_ZEROS = "move_zeros"
    MERGE_SORTED_LISTS = "merge_sorted_lists"
    MAXIMUM_SUBARRAY_SUM = "maximum_subarray_sum"
    BALANCED_DELIMITERS = "balanced_delimiters"


@dataclass(frozen=True)
class ProblemInput:
    name: str
    kind: str


@dataclass(frozen=True)
class ProblemAssumption:
    text: str
    status: Literal["stated", "defaulted"]


@dataclass(frozen=True)
class ProblemSpec:
    family: ProblemFamily
    inputs: tuple[ProblemInput, ...]
    result: str
    constraints: frozenset[str]
    evidence: tuple[str, ...]
    assumptions: tuple[ProblemAssumption, ...] = ()
    examples: tuple[ProblemExample, ...] = ()

    @property
    def function_name(self) -> str:
        return {
            ProblemFamily.TWO_SUM: "two_sum",
            ProblemFamily.DUPLICATES: "contains_duplicate",
            ProblemFamily.FREQUENCIES: "count_frequencies",
            ProblemFamily.PALINDROME: "is_palindrome",
            ProblemFamily.ANAGRAM: "are_anagrams",
            ProblemFamily.BINARY_SEARCH: "binary_search",
            ProblemFamily.MINIMUM: "find_minimum",
            ProblemFamily.MAXIMUM: "find_maximum",
            ProblemFamily.SUM: "calculate_sum",
            ProblemFamily.FIRST_UNIQUE_CHARACTER: "first_unique_character",
            ProblemFamily.REVERSE_TEXT: "reverse_text",
            ProblemFamily.MOVE_ZEROS: "move_zeros",
            ProblemFamily.MERGE_SORTED_LISTS: "merge_sorted_lists",
            ProblemFamily.MAXIMUM_SUBARRAY_SUM: "maximum_subarray_sum",
            ProblemFamily.BALANCED_DELIMITERS: "has_balanced_delimiters",
        }[self.family]


_WORD = re.compile(r"[^a-z0-9_]+")
_DATA = r"\b(array|list|collection|sequence|numbers?|integers?|values?)\b"
_TARGET = r"\b(target|goal|desired value)\b"


def _normalize(text: str) -> str:
    return " ".join(_WORD.sub(" ", text.lower()).split())


def _has(text: str, *patterns: str) -> bool:
    return any(re.search(pattern, text) for pattern in patterns)


def _error(prompt: ProblemPrompt, filename: str, message: str, kind: str = "unsupported") -> None:
    line = prompt.source_lines[0] if prompt.source_lines else 1
    raise CodeInEnglishError(filename, line, message, kind=kind)


def _inputs(family: ProblemFamily) -> tuple[ProblemInput, ...]:
    if family == ProblemFamily.TWO_SUM:
        return (ProblemInput("nums", "integer_list"), ProblemInput("target", "integer"))
    if family in (ProblemFamily.DUPLICATES, ProblemFamily.FREQUENCIES,
                  ProblemFamily.MINIMUM, ProblemFamily.MAXIMUM, ProblemFamily.SUM):
        return (ProblemInput("nums", "integer_list"),)
    if family == ProblemFamily.PALINDROME:
        return (ProblemInput("text", "string"),)
    if family == ProblemFamily.ANAGRAM:
        return (ProblemInput("first", "string"), ProblemInput("second", "string"))
    if family in (ProblemFamily.FIRST_UNIQUE_CHARACTER, ProblemFamily.REVERSE_TEXT, ProblemFamily.BALANCED_DELIMITERS):
        return (ProblemInput("text", "string"),)
    if family == ProblemFamily.MOVE_ZEROS:
        return (ProblemInput("nums", "integer_list"),)
    if family == ProblemFamily.MERGE_SORTED_LISTS:
        return (ProblemInput("first", "sorted_integer_list"), ProblemInput("second", "sorted_integer_list"))
    if family == ProblemFamily.MAXIMUM_SUBARRAY_SUM:
        return (ProblemInput("nums", "integer_list"),)
    return (ProblemInput("nums", "sorted_integer_list"), ProblemInput("target", "integer"))


def _assumptions(family: ProblemFamily) -> tuple[ProblemAssumption, ...]:
    if family == ProblemFamily.DUPLICATES:
        return (ProblemAssumption("Return true if any value occurs more than once; otherwise false.", "stated"),)
    if family == ProblemFamily.FREQUENCIES:
        return (ProblemAssumption("Return a JSON object mapping each value to its count.", "defaulted"),)
    if family == ProblemFamily.ANAGRAM:
        return (ProblemAssumption("Compare case-sensitively and treat whitespace as significant unless stated otherwise.", "defaulted"),)
    if family == ProblemFamily.MINIMUM:
        return (ProblemAssumption("Return null for an empty list.", "defaulted"),)
    if family == ProblemFamily.MAXIMUM:
        return (ProblemAssumption("Return null for an empty list.", "defaulted"),)
    if family == ProblemFamily.SUM:
        return (ProblemAssumption("The sum of an empty list is zero.", "defaulted"),)
    if family == ProblemFamily.FIRST_UNIQUE_CHARACTER:
        return (ProblemAssumption("Return the first character occurring once, or null if none exists.", "defaulted"), ProblemAssumption("Character comparison is case-sensitive.", "defaulted"))
    if family == ProblemFamily.REVERSE_TEXT:
        return (ProblemAssumption("Reverse the sequence of Unicode code points without normalization.", "defaulted"),)
    if family == ProblemFamily.MOVE_ZEROS:
        return (ProblemAssumption("Preserve the relative order of nonzero values.", "defaulted"), ProblemAssumption("Return a new list; do not mutate the input.", "defaulted"))
    if family == ProblemFamily.MERGE_SORTED_LISTS:
        return (ProblemAssumption("Both inputs are sorted in ascending order.", "stated"), ProblemAssumption("Keep duplicate values and return a new list.", "defaulted"))
    if family == ProblemFamily.MAXIMUM_SUBARRAY_SUM:
        return (ProblemAssumption("The selected elements must be contiguous.", "stated"), ProblemAssumption("Return zero for an empty input list.", "defaulted"))
    if family == ProblemFamily.BALANCED_DELIMITERS:
        return (ProblemAssumption("Check (), [], and {}; ignore other characters.", "defaulted"),)
    return ()


def recognize_problem(prompt: ProblemPrompt, filename: str = "<string>") -> ProblemSpec:
    """Recognize a supported DSA intent from explicit deterministic phrase rules."""
    text = _normalize(prompt.text)
    if not text:
        _error(prompt, filename, "the problem statement is empty")

    pair = (
        _has(text, r"\btwo\s+(?:different\s+)?(numbers?|values?|elements?)\b", r"\bpair of\s+(?:different\s+)?(numbers?|values?|elements?)\b", r"\bpairs?\b")
        and _has(text, r"\b(add up|sum|total|equal)\b", r"\badds?\s+to\b")
        and _has(text, r"\b(indices|indexes|positions)\b")
        and _has(text, _TARGET)
    )
    if pair:
        if _has(text, r"\b(?:not|never)\s+(?:add|sum|equal|total)\b"):
            _error(prompt, filename, "I can find pairs that reach a target, but not pairs defined by a negative sum condition", "ambiguous")
        constraints = {"distinct_indices", "return_first_matching_pair_if_multiple", "return_none_if_no_pair"}
        if _has(text, r"\bexactly one solution\b", r"\bone solution\b", r"\bexactly one pair exists\b"):
            constraints.add("one_solution_guaranteed")
        if _has(text, r"\b(?:all|every)\s+(?:matching\s+)?pairs?\b"):
            _error(prompt, filename, "I can currently return one matching pair, not every possible pair", "unsupported")
        if _has(text, r"\breturn\s+(?:an?\s+)?empty list\b.{0,30}\b(?:no pair|no solution|none exists)\b"):
            _error(prompt, filename, "I return null when no pair exists; an empty-list result is not supported", "ambiguous")
        no_pair_stated = _has(text, r"\breturn\s+(?:null|none)\b.{0,30}\b(?:no pair|no solution|none exists)\b")
        first_stated = _has(text, r"\bfirst\s+(?:matching\s+)?pair\b")
        distinct_stated = _has(text, r"\b(?:do not|don't|never)\s+(?:reuse|use)\b.{0,20}\b(?:element|number|value|index)\b", r"\bdifferent\s+(?:elements|indices|positions)\b")
        assumptions = [
            ProblemAssumption("Exactly one matching pair is guaranteed.", "stated") if "one_solution_guaranteed" in constraints else ProblemAssumption("There may be no matching pair.", "defaulted"),
            ProblemAssumption("Use two distinct indices.", "stated" if distinct_stated else "defaulted"),
            ProblemAssumption("Return the first matching pair in left-to-right order.", "stated" if first_stated else "defaulted"),
        ]
        if "one_solution_guaranteed" not in constraints:
            assumptions.append(ProblemAssumption("Return null when no pair exists.", "stated" if no_pair_stated else "defaulted"))
        result = "indices" if "one_solution_guaranteed" in constraints else "indices_or_none"
        return ProblemSpec(ProblemFamily.TWO_SUM, _inputs(ProblemFamily.TWO_SUM), result, frozenset(constraints), ("pair", "sum", "indices", "target"), tuple(assumptions), prompt.examples)

    if _has(text, r"\b(?:first\s+)?(?:non repeating|non-repeating|unique)\s+character\b", r"\bfirst character\b.{0,30}\b(?:occurs once|appears once|not repeated)\b"):
        if _has(text, r"\b(?:index|position|location)\b"):
            _error(prompt, filename, "I return the first unique character itself, not its index", "unsupported")
        constraints = {"case_insensitive"} if _has(text, r"\b(?:case insensitive|ignore case|ignoring case)\b") else set()
        assumptions = (
            ProblemAssumption("Return the first unique character itself, or null if none exists.", "defaulted"),
            ProblemAssumption("Compare characters case-insensitively." if constraints else "Compare characters case-sensitively.", "stated" if constraints else "defaulted"),
        )
        return ProblemSpec(ProblemFamily.FIRST_UNIQUE_CHARACTER, _inputs(ProblemFamily.FIRST_UNIQUE_CHARACTER), "character_or_null", frozenset(constraints), ("first unique character",), assumptions, prompt.examples)

    if _has(text, r"\brevers\w*\b") and _has(text, r"\b(?:text|string|word|phrase)\b"):
        if _has(text, r"\b(?:do not|don't|never)\s+revers\w*\b"):
            _error(prompt, filename, "the text reversal request is negated; describe the intended operation", "ambiguous")
        if _has(text, r"\b(?:sort|alphabetical|letters?)\b"):
            _error(prompt, filename, "the request mixes reversing and sorting; describe one result", "ambiguous")
        return ProblemSpec(ProblemFamily.REVERSE_TEXT, _inputs(ProblemFamily.REVERSE_TEXT), "reversed_text", frozenset(), ("reverse text",), _assumptions(ProblemFamily.REVERSE_TEXT), prompt.examples)

    if _has(text, r"\b(?:move|shift)\b") and _has(text, r"\bzeros?\b") and _has(text, r"\b(?:end|back)\b") and _has(text, r"\b(?:list|array|numbers?)\b"):
        if _has(text, r"\b(?:reverse|descending)\b"):
            _error(prompt, filename, "I preserve the order of nonzero values; a different reordering was requested", "ambiguous")
        assumptions = _assumptions(ProblemFamily.MOVE_ZEROS)
        if _has(text, r"\bpreserv(?:e|ing)\s+(?:the\s+)?(?:relative\s+)?order\b"):
            assumptions = (ProblemAssumption("Preserve the relative order of nonzero values.", "stated"), assumptions[1])
        return ProblemSpec(ProblemFamily.MOVE_ZEROS, _inputs(ProblemFamily.MOVE_ZEROS), "integer_list", frozenset(), ("move zeros to end",), assumptions, prompt.examples)

    if _has(text, r"\b(?:merge|combine)\b") and _has(text, r"\b(?:two|2|both)\b") and _has(text, r"\b(?:list|lists|arrays?)\b"):
        if not _has(text, r"\bsorted\s+(?:integer\s+)?lists?\b", r"\bascending\s+arrays?\b", r"\bboth\s+lists?\s+(?:are|is)\s+sorted\b"):
            _error(prompt, filename, "Are both lists sorted in ascending order?", "ambiguous")
        return ProblemSpec(ProblemFamily.MERGE_SORTED_LISTS, _inputs(ProblemFamily.MERGE_SORTED_LISTS), "integer_list", frozenset({"sorted_inputs_ascending"}), ("merge two sorted lists",), _assumptions(ProblemFamily.MERGE_SORTED_LISTS), prompt.examples)

    if _has(text, r"\b(?:maximum|largest|greatest)\b") and _has(text, r"\b(?:contiguous|subarray)\b") and _has(text, r"\b(?:sum|total)\b"):
        if _has(text, r"\b(?:do not|don't|never)\s+(?:find|return|calculate)\b"):
            _error(prompt, filename, "the maximum contiguous sum request is negated; describe the intended result", "ambiguous")
        if _has(text, r"\bnon contiguous\b", r"\bnon-contiguous\b", r"\bsubsequence\b"):
            _error(prompt, filename, "the request conflicts about whether selected values must be contiguous", "ambiguous")
        return ProblemSpec(ProblemFamily.MAXIMUM_SUBARRAY_SUM, _inputs(ProblemFamily.MAXIMUM_SUBARRAY_SUM), "maximum_subarray_sum", frozenset({"contiguous_values"}), ("maximum contiguous sum",), _assumptions(ProblemFamily.MAXIMUM_SUBARRAY_SUM), prompt.examples)

    if _has(text, r"\b(?:contiguous|subarray)\b") and _has(text, r"\b(?:sum|total)\b"):
        _error(prompt, filename, "do you want the maximum sum of a contiguous section? State the requested result", "ambiguous")

    if _has(text, r"\b(?:balanced|well formed|properly matched|properly nested)\b") and _has(text, r"\b(?:parentheses|brackets|delimiters|braces)\b"):
        if _has(text, r"\bunbalanced\b", r"\bnot\s+balanced\b", r"\b(?:do not|don't|never)\s+(?:check|test|determine)\b"):
            _error(prompt, filename, "I recognize balanced-delimiter checks, but not a request to detect the opposite condition", "ambiguous")
        constraints = set()
        if "parentheses" in text and not _has(text, r"\b(?:brackets|braces|delimiters)\b"):
            constraints.add("parentheses_only")
        elif "brackets" in text or "braces" in text or "delimiters" in text:
            constraints.add("all_common_delimiters")
        assumptions = _assumptions(ProblemFamily.BALANCED_DELIMITERS)
        if "parentheses_only" in constraints:
            assumptions = (ProblemAssumption("Check only (); ignore other characters.", "stated"),)
        if _has(text, r"\b(?:only|just)\s+(?:the\s+)?(?:parentheses|brackets)\b"):
            constraints = {"parentheses_only" if "parentheses" in text else "square_brackets_only"}
            mark = "()" if "parentheses_only" in constraints else "[]"
            assumptions = (ProblemAssumption(f"Check only {mark}; ignore other characters.", "stated"),)
        return ProblemSpec(ProblemFamily.BALANCED_DELIMITERS, _inputs(ProblemFamily.BALANCED_DELIMITERS), "boolean", frozenset(constraints), ("balanced delimiters",), assumptions, prompt.examples)

    if _has(text, r"\b(?:maximum|minimum|largest|smallest|biggest|least)\b") and _has(text, r"\b(?:maximum|largest|biggest)\b", r"\b(?:minimum|smallest|least)\b"):
        if _has(text, r"\b(?:maximum|largest|biggest)\b") and _has(text, r"\b(?:minimum|smallest|least)\b"):
            _error(prompt, filename, "I can find a minimum or maximum, but need you to ask for one result at a time", "ambiguous")

    if _has(text, r"\b(?:how often|frequency|frequencies|number of occurrences|count of each|count for each|count for every|count how many times|how many times each)\b"):
        if _has(text, r"\b(?:not|never)\s+(?:count|frequency|occur)\b"):
            _error(prompt, filename, "the frequency request is negated; please say what result you want", "ambiguous")
        return ProblemSpec(ProblemFamily.FREQUENCIES, _inputs(ProblemFamily.FREQUENCIES), "frequency_map", frozenset(), ("frequency", "occurrences"), _assumptions(ProblemFamily.FREQUENCIES), prompt.examples)

    if _has(text, r"\b(?:duplicate|duplicates|repeated value|is repeated|are repeated|appears more than once|occurs more than once)\b"):
        if _has(text, r"\b(?:not|never|no)\b.{0,24}\b(?:duplicate|repeated|more than once)\b"):
            _error(prompt, filename, "I recognized a duplicate check, but the request is negated; please clarify the desired result", "ambiguous")
        return ProblemSpec(ProblemFamily.DUPLICATES, _inputs(ProblemFamily.DUPLICATES), "contains_duplicate", frozenset(), ("duplicate", "repeated"), _assumptions(ProblemFamily.DUPLICATES), prompt.examples)

    if _has(text, r"\bpalindrome\b", r"\breads? the same forward and backward\b", r"\bsame forwards? and backwards?\b"):
        if _has(text, r"\b(?:not|never|no)\b.{0,24}\bpalindrome\b", r"\b(?:do not|don't|never)\s+(?:check|test|determine)\b.{0,24}\bpalindrome\b"):
            _error(prompt, filename, "I recognized a palindrome check, but the request is negated; please clarify the desired result", "ambiguous")
        constraints = {"case_sensitive", "punctuation_significant", "whitespace_significant"}
        case_ignore = _has(text, r"\bcase insensitive\b", r"\bignoring case\b", r"\bignore case\b")
        case_sensitive = _has(text, r"\bcase sensitive\b")
        punctuation_ignore = _has(text, r"\b(?:ignore|ignoring|exclude|excluding)\b.{0,30}\bpunctuation\b", r"\bcase and punctuation\b")
        punctuation_keep = _has(text, r"\bpunctuation (?:matters|is significant)\b", r"\bkeep punctuation\b")
        whitespace_ignore = _has(text, r"\b(?:ignore|ignoring|exclude|excluding)\b.{0,30}\b(?:spaces?|whitespace)\b")
        whitespace_keep = _has(text, r"\b(?:whitespace|spaces?) (?:matters|are significant|is significant)\b", r"\bkeep (?:the )?(?:spaces?|whitespace)\b")
        if (case_ignore and case_sensitive) or (punctuation_ignore and punctuation_keep) or (whitespace_ignore and whitespace_keep):
            _error(prompt, filename, "the text comparison rules conflict; specify one case, punctuation, and whitespace policy", "ambiguous")
        if case_ignore:
            constraints.discard("case_sensitive")
            constraints.add("case_insensitive")
        if punctuation_ignore:
            constraints.discard("punctuation_significant")
            constraints.add("ignore_punctuation")
        if whitespace_ignore:
            constraints.discard("whitespace_significant")
            constraints.add("ignore_whitespace")
        assumptions = (
            ProblemAssumption("Compare case-insensitively." if "case_insensitive" in constraints else "Compare case-sensitively.", "stated" if "case_insensitive" in constraints else "defaulted"),
            ProblemAssumption("Ignore punctuation." if "ignore_punctuation" in constraints else "Punctuation is significant.", "stated" if "ignore_punctuation" in constraints else "defaulted"),
            ProblemAssumption("Ignore whitespace." if "ignore_whitespace" in constraints else "Whitespace is significant.", "stated" if "ignore_whitespace" in constraints else "defaulted"),
        )
        return ProblemSpec(ProblemFamily.PALINDROME, _inputs(ProblemFamily.PALINDROME), "is_palindrome", frozenset(constraints), ("palindrome",), assumptions, prompt.examples)

    if _has(text, r"\banagrams?\b", r"\brearrang\w*.{0,30}\b(?:same|other|another)\b", r"\bsame letters? in (?:a )?different order\b"):
        if _has(text, r"\b(?:not|never|no)\b.{0,24}\banagrams?\b"):
            _error(prompt, filename, "I recognized an anagram check, but the request is negated; please clarify the desired result", "ambiguous")
        constraints = {"case_sensitive", "whitespace_significant"}
        if _has(text, r"\b(?:ignore|ignoring|exclude|excluding)\b.{0,30}\bpunctuation\b"):
            _error(prompt, filename, "punctuation-insensitive anagram matching is not supported yet", "unsupported")
        case_ignore = _has(text, r"\bcase insensitive\b", r"\bignoring case\b", r"\bignore case\b")
        case_sensitive = _has(text, r"\bcase sensitive\b")
        whitespace_ignore = _has(text, r"\b(?:ignore|ignoring|exclude|excluding)\b.{0,30}\b(?:spaces?|whitespace)\b")
        whitespace_keep = _has(text, r"\b(?:whitespace|spaces?) (?:matters|are significant|is significant)\b", r"\bkeep (?:the )?(?:spaces?|whitespace)\b")
        if (case_ignore and case_sensitive) or (whitespace_ignore and whitespace_keep):
            _error(prompt, filename, "the anagram comparison rules conflict; specify one case and whitespace policy", "ambiguous")
        if case_ignore:
            constraints.discard("case_sensitive")
            constraints.add("case_insensitive")
        if whitespace_ignore:
            constraints.discard("whitespace_significant")
            constraints.add("ignore_whitespace")
        assumptions = (
            ProblemAssumption("Compare case-insensitively." if case_ignore else "Compare case-sensitively.", "stated" if case_ignore or case_sensitive else "defaulted"),
            ProblemAssumption("Punctuation is significant.", "defaulted"),
            ProblemAssumption("Ignore whitespace." if whitespace_ignore else "Whitespace is significant.", "stated" if whitespace_ignore or whitespace_keep else "defaulted"),
        )
        return ProblemSpec(ProblemFamily.ANAGRAM, _inputs(ProblemFamily.ANAGRAM), "are_anagrams", frozenset(constraints), ("anagram", "rearrange"), assumptions, prompt.examples)

    search = _has(text, r"\bsearch\b", r"\bfind\b.{0,20}\b(?:target|value|number)\b", r"\blocate\b.{0,20}\b(?:target|value|number)\b")
    sorted_input = _has(text, r"\bsorted\b", r"\bordered\b", r"\bascending\b")
    if search and _has(text, _TARGET) and _has(text, r"\b(?:index|position|location)\b"):
        if _has(text, r"\bdescending\b", r"\bdecreasing\b"):
            _error(prompt, filename, "this binary search strategy requires ascending input, not descending input", "unsupported")
        if not sorted_input:
            _error(prompt, filename, "Is the list sorted? I need to know before choosing a search method", "ambiguous")
        if _has(text, r"\b(?:not|never)\b.{0,20}\bsearch\b"):
            _error(prompt, filename, "the search request is negated; please clarify what should be found", "ambiguous")
        assumptions = (
            ProblemAssumption("Input is sorted in ascending order.", "stated" if _has(text, r"\b(?:ascending|increasing)\b") else "defaulted"),
            ProblemAssumption("Return the first matching index.", "stated" if _has(text, r"\bfirst\b") else "defaulted"),
            ProblemAssumption("Return -1 when the value is absent.", "stated" if _has(text, r"\bminus one\b", r"\bif absent\b", r"\bwhen absent\b") or "-1" in prompt.text else "defaulted"),
        )
        return ProblemSpec(ProblemFamily.BINARY_SEARCH, _inputs(ProblemFamily.BINARY_SEARCH), "index_or_minus_one", frozenset({"sorted_input", "return_minus_one_if_missing"}), ("search", "sorted", "index"), assumptions, prompt.examples)

    aggregate = None
    if _has(text, r"\b(?:maximum|largest|biggest)\b"):
        aggregate = ProblemFamily.MAXIMUM
    elif _has(text, r"\b(?:minimum|smallest|least)\b"):
        aggregate = ProblemFamily.MINIMUM
    elif _has(text, r"\b(?:sum|total|add up all|add up every)\b") and not pair:
        aggregate = ProblemFamily.SUM
    if aggregate:
        if _has(text, r"\b(?:not|never)\b.{0,20}\b(?:maximum|minimum|largest|smallest|sum|total)\b"):
            _error(prompt, filename, "the aggregate request is negated; please clarify the result you want", "ambiguous")
        result = aggregate.value
        return ProblemSpec(aggregate, _inputs(aggregate), result, frozenset({"return_none_if_empty"}) if aggregate != ProblemFamily.SUM else frozenset(), (result,), _assumptions(aggregate), prompt.examples)

    if search and _has(text, _TARGET) and not sorted_input:
        _error(prompt, filename, "Is the list sorted, and should I return the value or its position?", "ambiguous")
    if not _has(text, _DATA):
        _error(prompt, filename, "I couldn't identify the input data. Describe the list, text, or values the problem uses.", "ambiguous")
    _error(prompt, filename, "I don't recognize this problem type yet. Try describing its input and the result you want.")
