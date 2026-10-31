"""How many programs can EN express? Counts type-valid operation chains and how many behave differently."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from codeinenglish import synth  # noqa: E402

DEPTH = int(sys.argv[1]) if len(sys.argv) > 1 else 2
ARG = {"ilist": 3, "text": 3, "int": 3}  # one representative number for parametric steps


def successors(kind):
    return [(op, 3 if op.parametric else None) for op in synth.OPS if op.src == kind] + \
           [(None, None, bridge, dst) for (src, dst), bridge in synth.COERCE.items() if src == kind]


def sequences(kind, depth):
    if depth == 0:
        yield []
        return
    for step in successors(kind):
        if step[0] is None:
            nxt, item = step[3], (None, None, step[2][1], step[2][0])
        else:
            nxt, item = step[0].dst, (step[0], step[1], None, None)
        for rest in sequences(nxt, depth - 1):
            yield [item, *rest]


def dp_counts(kind, depth):
    table = {t: 1 for t in ("ilist", "text", "int", "bool", "num", "tlist")}
    for _ in range(depth):
        new = {}
        for t in table:
            new[t] = sum(table[o.dst] for o in synth.OPS if o.src == t) + sum(table[d] for (s, d) in synth.COERCE if s == t)
        table = new
    return table[kind]


print(f"{len(synth.OPS)} operations, {len(synth.COERCE)} implicit conversions")
total_distinct = 0
for kind in ("ilist", "text", "int"):
    raw = [dp_counts(kind, d) for d in range(1, 6)]
    print(f"input {kind}: type-valid chains of length 1..5 = {raw}")
    seen = set()
    for depth in range(1, DEPTH + 1):
        for seq in sequences(kind, depth):
            if all(item[0] is None for item in seq):
                continue
            seen.add(synth.signature(seq, kind))
        print(f"   distinct behaviours at depth<={depth}: {len(seen)}")
    total_distinct += len(seen)
print("distinct programs reachable at depth<=DEPTH (parameters fixed at 3):", total_distinct)
