"""Inductive program synthesis: discovering algorithms from example inputs and outputs.

When English wording does not match the curated catalog or exact regexes,
the inductive synthesizer searches the typed combinator graph to find the
pipeline that reproduces the user's examples.
"""

from __future__ import annotations
import re
from typing import Any

from .synth import (
    COERCE,
    OPS,
    PROBES,
    Program,
    _describe,
    _matches,
    _name_of,
    _run,
)

_NUM_PATTERN = re.compile(r"\b(-?\d+)\b")


def infer_type(value: Any) -> str | None:
    """Infer the synth type string ('ilist', 'text', 'tlist', 'int', 'bool', 'num') from a Python value."""
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "num"
    if isinstance(value, str):
        return "text"
    if isinstance(value, list):
        if not value:
            return "ilist"  # default empty list
        if all(isinstance(x, bool) for x in value):
            return None
        if all(isinstance(x, int) and not isinstance(x, bool) for x in value):
            return "ilist"
        if all(isinstance(x, str) for x in value):
            return "tlist"
    return None


def _numbers_in_prompt(text: str) -> list[int]:
    """Find integers mentioned in the prompt text."""
    numbers = []
    for match in _NUM_PATTERN.finditer(text):
        try:
            numbers.append(int(match.group(1)))
        except ValueError:
            pass
    return list(dict.fromkeys(numbers)) or [2, 3, 5, 10]


def inductive_synthesize(examples: tuple[Any, ...], prompt_text: str = "") -> Program | None:
    """Synthesize a Program from examples by searching the combinator graph."""
    if not examples:
        return None

    # Verify each example has exactly one input value
    first_example = examples[0]
    input_values = list(first_example.input.values())
    if len(input_values) != 1:
        return None

    first_in = input_values[0]
    first_out = first_example.expected

    input_type = infer_type(first_in)
    expected_type = infer_type(first_out)
    if input_type is None:
        return None

    numbers_to_try = _numbers_in_prompt(prompt_text)

    candidates: list[tuple[int, list]] = []  # (score, chain)
    words_in_prompt = set(re.findall(r"[a-z0-9]+", prompt_text.lower()))

    def score_chain(chain: list) -> int:
        score = 0
        for item in chain:
            op = item[0]
            if op is not None:
                op_words = set(re.findall(r"[a-z0-9]+", (op.name + " " + op.says).lower()))
                score += len(words_in_prompt & op_words) * 10
        # Penalize longer chains slightly to prefer simpler solutions
        score -= len(chain) * 2
        return score

    # 1. Depth 1: Single operations
    for op in OPS:
        if op.src != input_type:
            continue
        param_values = numbers_to_try if op.parametric else [None]
        for n in param_values:
            chain = [(op, n, op.expr, op.says)]
            if all(_matches(chain, ex) for ex in examples):
                # Verify on probe inputs that it doesn't always fail
                probes = PROBES.get(input_type, [])
                if probes and any(not str(_run(chain, p)).startswith("ERR:") for p in probes):
                    candidates.append((score_chain(chain), chain))

    # 2. Depth 2: Two-operation chains (only searched if no single op explains the examples)
    if not candidates:
        for op1 in OPS:
            if op1.src != input_type:
                continue
            param1_values = numbers_to_try if op1.parametric else [None]
            for n1 in param1_values:
                step1 = (op1, n1, op1.expr, op1.says)
                mid_type = op1.dst

                # Direct connection
                for op2 in OPS:
                    if op2.src != mid_type:
                        continue
                    param2_values = numbers_to_try if op2.parametric else [None]
                    for n2 in param2_values:
                        step2 = (op2, n2, op2.expr, op2.says)
                        chain = [step1, step2]
                        if all(_matches(chain, ex) for ex in examples):
                            probes = PROBES.get(input_type, [])
                            if probes and any(not str(_run(chain, p)).startswith("ERR:") for p in probes):
                                candidates.append((score_chain(chain), chain))

                # With coercion bridge between text and tlist
                if (mid_type, "text") in COERCE:
                    bridge_label, bridge_expr = COERCE[(mid_type, "text")]
                    bridge_step = (None, None, bridge_expr, bridge_label)
                    for op2 in OPS:
                        if op2.src != "text":
                            continue
                        param2_values = numbers_to_try if op2.parametric else [None]
                        for n2 in param2_values:
                            step2 = (op2, n2, op2.expr, op2.says)
                            chain = [step1, bridge_step, step2]
                            if all(_matches(chain, ex) for ex in examples):
                                candidates.append((score_chain(chain), chain))

                elif (mid_type, "tlist") in COERCE:
                    bridge_label, bridge_expr = COERCE[(mid_type, "tlist")]
                    bridge_step = (None, None, bridge_expr, bridge_label)
                    for op2 in OPS:
                        if op2.src != "tlist":
                            continue
                        param2_values = numbers_to_try if op2.parametric else [None]
                        for n2 in param2_values:
                            step2 = (op2, n2, op2.expr, op2.says)
                            chain = [step1, bridge_step, step2]
                            if all(_matches(chain, ex) for ex in examples):
                                candidates.append((score_chain(chain), chain))

    if not candidates:
        return None

    # Pick candidate with highest score (keyword matching + simplicity)
    candidates.sort(key=lambda item: item[0], reverse=True)
    best_chain = candidates[0][1]

    paraphrase = _describe(best_chain)
    function_name = _name_of(best_chain)
    return Program(
        input_type=input_type,
        chain=tuple(best_chain),
        paraphrase=paraphrase,
        function_name=function_name,
        examples_checked=len(examples),
    )
