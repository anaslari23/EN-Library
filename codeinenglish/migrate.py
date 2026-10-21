"""Conservative, body-verified migration for versioned EN source files."""

import difflib
from pathlib import Path
import re
import tempfile

from .contract import MIGRATION_PATHS, SUPPORTED_VERSIONS, read_contract
from .interpreter import generate_file
from .provenance import split_provenance
from .translator import _write_python


def migrate_source(source: str, filename: str = "source.en", target: str | None = None) -> tuple[str, list[str]]:
    newline = "\r\n" if "\r\n" in source else "\n"
    normalized = source.replace("\r\n", "\n").replace("\r", "\n")
    has_final_newline = normalized.endswith("\n")
    lines = normalized.splitlines()
    version = _read_version(lines)
    destination = target or _version_label(max(SUPPORTED_VERSIONS))
    target_version = _parse_version(destination)
    if target_version not in SUPPORTED_VERSIONS:
        raise ValueError(f"Target en {destination} is not supported by this install.")
    if version == target_version:
        return source, []

    reasons: list[str] = []
    current = version
    while current != target_version:
        next_version = MIGRATION_PATHS.get(current)
        if next_version is None or next_version > target_version:
            raise ValueError(f"No migration path from {_version_label(current) if current else 'legacy'} to {destination}.")
        if current is None and next_version == (0, 1):
            lines = _legacy_to_01(lines)
            reasons.append("Added version header en 0.1 without changing instruction or comment text.")
        elif current == (0, 1) and next_version == (0, 2):
            lines, changes = _migrate_01_to_02(lines, filename)
            reasons.extend(changes)
        else:
            raise ValueError(f"No migration step from {_version_label(current)} to {_version_label(next_version)}.")
        current = next_version

    migrated = "\n".join(lines)
    if has_final_newline:
        migrated += "\n"
    if newline != "\n":
        migrated = migrated.replace("\n", newline)
    return migrated, reasons


def migrate_file(path: str | Path, target: str | None = None, *, write: bool = False) -> tuple[bool, str]:
    source_path = Path(path)
    original = source_path.read_text(encoding="utf-8")
    migrated, reasons = migrate_source(original, str(source_path), target)
    if migrated == original:
        return False, ""

    before = _generated_body(original, source_path.name)
    after = _generated_body(migrated, source_path.name)
    if before != after:
        raise ValueError("Migration would change the generated Python code. The source was left untouched; review the diff and update the request manually.")

    diff = "".join(difflib.unified_diff(
        original.splitlines(keepends=True), migrated.splitlines(keepends=True),
        fromfile=str(source_path), tofile=str(source_path) + " (migrated)",
    ))
    if reasons:
        diff += "\nMigration notes:\n" + "\n".join(f"- {reason}" for reason in reasons) + "\n"
    if write:
        _write_python(migrated, source_path)
    return True, diff


def _generated_body(source_text: str, filename: str) -> str:
    with tempfile.TemporaryDirectory(prefix="codeinenglish-migrate-") as temp:
        source_path = Path(temp) / filename
        source_path.write_text(source_text, encoding="utf-8")
        generated_path = generate_file(source_path)
        _, body = split_provenance(generated_path.read_text(encoding="utf-8"))
        return body


def _read_version(lines: list[str]) -> tuple[int, int] | None:
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = re.fullmatch(r"en (\d+)\.(\d+)", stripped)
        if match:
            return int(match.group(1)), int(match.group(2))
        if stripped.startswith("en"):
            raise ValueError(f'Invalid EN version line "{stripped}". Use "en 0.2".')
        return None
    return None


def _legacy_to_01(lines: list[str]) -> list[str]:
    index = next((i for i, line in enumerate(lines) if line.strip() and not line.lstrip().startswith("#")), None)
    if index is None:
        return ["en 0.1", *lines]
    return [*lines[:index], "en 0.1", *lines[index:]]


def _migrate_01_to_02(lines: list[str], filename: str) -> tuple[list[str], list[str]]:
    source = "\n".join(lines)
    contract = read_contract(source, filename)
    if not contract.ok:
        messages = "; ".join(item.message for item in contract.diagnostics if item.severity == "error")
        raise ValueError(f"Cannot migrate invalid en 0.1 source: {messages}")
    is_problem = contract.form == "problem"
    updated = list(lines)
    notes: list[str] = []
    comment_indices = [i for i, line in enumerate(lines) if line.lstrip().startswith("#")]
    if is_problem:
        for previous, current in zip(comment_indices, comment_indices[1:]):
            if any(not lines[index].strip() for index in range(previous + 1, current)):
                raise ValueError(f"Cannot safely migrate separated problem comment blocks near line {current + 1}; move them together or review manually.")

    for index, original in enumerate(lines):
        stripped = original.strip()
        if not stripped:
            continue
        folded = stripped.casefold()
        if folded == "import codeinpython library":
            indent = original[:len(original) - len(original.lstrip())]
            updated[index] = indent + "target python"
            notes.append(f"Replaced the legacy Python alias on line {index + 1} with target python.")
            continue
        if folded.startswith("target "):
            words = stripped.split()
            if len(words) == 2:
                indent = original[:len(original) - len(original.lstrip())]
                updated[index] = indent + f"target {words[1].casefold()}"
            continue
        if not stripped.startswith("#"):
            continue
        indent = original[:len(original) - len(original.lstrip())]
        if is_problem:
            legacy_text = stripped[1:]
            if legacy_text.startswith(" "):
                legacy_text = legacy_text[1:]
            legacy_text = legacy_text.rstrip()
            updated[index] = indent + "#?" + (" " + legacy_text if legacy_text else "")
            notes.append(f"Marked problem text on line {index + 1} with #?.")
        elif stripped.startswith("#?"):
            updated[index] = indent + "# " + stripped[1:]
            notes.append(f"Escaped documentation marker on line {index + 1} so it stays a comment.")

    for index, line in enumerate(updated):
        if line.strip() == "en 0.1":
            updated[index] = "en 0.2"
            break
    return updated, notes


def _parse_version(value: str) -> tuple[int, int]:
    match = re.fullmatch(r"(\d+)\.(\d+)", value)
    if not match:
        raise ValueError("Target version must be MAJOR.MINOR, such as 0.2.")
    return int(match.group(1)), int(match.group(2))


def _version_label(version: tuple[int, int] | None) -> str:
    return "legacy" if version is None else f"{version[0]}.{version[1]}"
