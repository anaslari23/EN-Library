# Changelog

## Unreleased

- Added typed synthesis (`synth.py`): about 90 composable operations, type-checked orderings, behaviour-based ambiguity detection, example verification, and cross-checking against the catalog.
- Fixed catalog answers that silently dropped a word (`not`, `cubes`), mis-typed a number request as a list sum, or read `up to n` as exclusive.
- Named functions in comments (`# write a program called NAME to ...`) and an announcement on import.

## 0.3.0 — 2026-10-31

- Added `codeinenglish run` and `import codeinenglish` generation from `# write a program to ...` comments.
- Added unit-conversion recipes taking decimal input, table-driven recipes (57 tasks, plus the ten migrated original families), a Python-to-JavaScript transpiler for them, "X then Y" pipelines, and closest-task suggestions.
- Added an opt-in local miss log (`CODEINENGLISH_MISSES`) and the `misses` command.

## 0.2.0 — 2026-10-21

- Added versioned `.en` source contracts for legacy, `en 0.1`, and `en 0.2` files.
- Added explicit `#?` problem requests, structured source diagnostics, JSON check/generate responses, and the run-plan schema.
- Added dry-run-by-default, code-body-verified source migration.
- Added deterministic generated-file provenance and the VS Code extension's CLI-owned run plan.
- Headerless files now emit EN-W401. They remain supported through package minor releases 0.2.x and 0.3.x; removal is scheduled for 0.4.0.
