"""Opt-in local log of requests that could not be turned into code, to learn which wordings to support."""

from __future__ import annotations

import json
import os
from collections import Counter
from pathlib import Path

ENV_VAR = "CODEINENGLISH_MISSES"


def record(request: str, message: str, kind: str) -> None:
    """Append one line to the file named by CODEINENGLISH_MISSES; does nothing when it is unset."""
    path = os.environ.get(ENV_VAR)
    if not path:
        return
    try:
        with open(path, "a", encoding="utf-8") as log:
            log.write(json.dumps({"request": request, "kind": kind, "message": message}, ensure_ascii=False) + "\n")
    except OSError:
        pass  # logging must never break generation


def summarize(path: str | Path | None = None) -> list[tuple[int, str, str]]:
    """(count, request, kind) for each distinct logged request, most frequent first."""
    log_path = path or os.environ.get(ENV_VAR)
    if not log_path or not Path(log_path).exists():
        return []
    counts = Counter()
    for line in Path(log_path).read_text(encoding="utf-8").splitlines():
        entry = json.loads(line)
        counts[(entry["request"], entry["kind"])] += 1
    return [(count, request, kind) for (request, kind), count in counts.most_common()]
