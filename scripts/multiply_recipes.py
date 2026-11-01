#!/usr/bin/env python3
"""Autonomous Recipe Multiplier for Code in English.

Explores the combinatorial graph of typed operations to automatically generate,
verify, and emit new problem recipes without manual human authoring.
"""

from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

# Add parent directory to path to import codeinenglish
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from codeinenglish.synth import (
    COERCE,
    OPS,
    PROBES,
    Program,
    _describe,
    _name_of,
    _run,
    _INPUT,
)


def generate_chains(max_depth: int = 2) -> list[tuple[str, list]]:
    """Generate all type-safe operation chains up to max_depth."""
    chains: list[tuple[str, list]] = []

    # Depth 1: Single operations
    for op in OPS:
        if not op.parametric:
            chain = [(op, None, op.expr, op.says)]
            chains.append((op.src, chain))
        else:
            for n in (2, 3, 5):
                chain = [(op, n, op.expr, op.says)]
                chains.append((op.src, chain))

    if max_depth < 2:
        return chains

    # Depth 2: Two operations
    for op1 in OPS:
        n1_values = [2, 3, 5] if op1.parametric else [None]
        for n1 in n1_values:
            step1 = (op1, n1, op1.expr, op1.says)
            mid = op1.dst

            # Direct connection
            for op2 in OPS:
                if op2.src != mid:
                    continue
                n2_values = [2, 3, 5] if op2.parametric else [None]
                for n2 in n2_values:
                    step2 = (op2, n2, op2.expr, op2.says)
                    chains.append((op1.src, [step1, step2]))

            # Coercion between text and tlist
            for bridge_type in ("text", "tlist"):
                if (mid, bridge_type) in COERCE:
                    bridge_label, bridge_expr = COERCE[(mid, bridge_type)]
                    bridge_step = (None, None, bridge_expr, bridge_label)
                    for op2 in OPS:
                        if op2.src != bridge_type:
                            continue
                        n2_values = [2, 3, 5] if op2.parametric else [None]
                        for n2 in n2_values:
                            step2 = (op2, n2, op2.expr, op2.says)
                            chains.append((op1.src, [step1, bridge_step, step2]))

    return chains


def verify_and_sample(chains: list[tuple[str, list]], limit: int | None = None) -> list[dict]:
    """Test chains on probe inputs to verify they produce valid, error-free results."""
    verified = []
    seen_names = set()

    for input_type, chain in chains:
        name = _name_of(chain)
        if name in seen_names:
            continue
        seen_names.add(name)

        probes = PROBES.get(input_type, [])
        valid_sample = None
        # Prefer a non-empty illustrative probe when available
        for probe in probes:
            result = _run(chain, probe)
            if not str(result).startswith("ERR:") and result is not None:
                if probe and result:
                    valid_sample = (probe, result)
                    break
                if valid_sample is None:
                    valid_sample = (probe, result)

        if valid_sample is None:
            continue

        param_name = _INPUT[input_type][0]
        sample_in, sample_out = valid_sample

        verified.append({
            "name": name,
            "description": _describe(chain),
            "input_type": input_type,
            "param_name": param_name,
            "example_input": {param_name: sample_in},
            "example_output": sample_out,
            "steps": len(chain),
        })

        if limit and len(verified) >= limit:
            break

    return verified


def main() -> int:
    parser = argparse.ArgumentParser(description="Multiply recipes autonomously through combinator exploration")
    parser.add_argument("--count", action="store_true", help="count total valid algorithms available")
    parser.add_argument("--depth", type=int, default=2, choices=(1, 2), help="maximum chain depth (1 or 2)")
    parser.add_argument("--sample", type=int, default=5, help="number of sample problem recipes to display")
    parser.add_argument("--export-dir", type=str, help="directory to write generated .en problem files into")
    args = parser.parse_args()

    print(f"Exploring combinator graph (depth <= {args.depth})...", file=sys.stderr)
    all_chains = generate_chains(max_depth=args.depth)
    print(f"Generated {len(all_chains)} candidate pipelines.", file=sys.stderr)

    if args.count:
        print(f"Total verifiable candidate pipelines: {len(all_chains)}")
        return 0

    samples = verify_and_sample(all_chains, limit=args.sample)
    print(f"\nSuccessfully verified {len(samples)} distinct problem algorithms:\n")

    for i, s in enumerate(samples, 1):
        print(f"--- Recipe {i}: {s['name']} ---")
        print(f"Description: {s['description']}")
        print(f"Example input:  {json.dumps(s['example_input'])}")
        print(f"Example output: {json.dumps(s['example_output'])}\n")

    if args.export_dir:
        out_dir = Path(args.export_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        for s in samples:
            file_path = out_dir / f"{s['name']}.en"
            content = (
                "target python\n"
                f"#? {s['description'].capitalize()}.\n"
                f"#? Example input: {json.dumps(s['example_input'])}\n"
                f"#? Example output: {json.dumps(s['example_output'])}\n"
            )
            file_path.write_text(content, encoding="utf-8")
        print(f"Exported {len(samples)} .en files to {out_dir}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
