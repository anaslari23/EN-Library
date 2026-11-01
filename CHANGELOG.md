# Changelog

## Unreleased

- Added Inductive Program Synthesis (Programming-by-Example / PBE via `inductive_synth.py`): discovers typed algorithms and pipelines from `#? Example input/output` when the English wording uses uncataloged, novel phrasing.
- Added Autonomous Recipe Multiplier (`scripts/multiply_recipes.py`): discovers, type-checks, probe-verifies, and exports thousands of composable algorithmic pipelines ($A \to B \to C$) automatically from the combinator graph without manual recipe authoring.
- Added standalone conversational functions (`define a function named ... taking ...`, `to <name> taking ...:`, `end function`) with scoped parameter frames, return value support, and calling syntax (`call <func> with <args>`) in expressions and as standalone statements across all backends.
- Added conversational `while` loops (`while <condition>`, `repeat while <condition>`, `as long as <condition>`, `end while`) across parser, IR, evaluator, and all backends (Python, C, Java, JavaScript).
- Added conversational loop controls: `stop the loop` / `break out of the loop` (`Break`) and `skip to next` / `continue` (`Continue`), with strict loop-depth validation.
- Added conversational increment/decrement statements: `increase <name> by <amount>` and `decrease <name> by <amount>`.
- Added interactive terminal REPL (`python3 -m codeinenglish repl`) with live state persistence, multi-line block entry, expression evaluation, and built-in `help` and `vars` commands.
- Removed external `vscode-extension` dependency in favor of standalone zero-dependency stdio LSP (`python3 -m codeinenglish lsp`).
- Added first-class `import codein<lang>;` target directives (`import codeinpython;`, `import codeinc;`, `import codeinjavascript;`, `import codeinjava;`) across `.en` source contracts.
- Added polyglot problem code generation and `--check-examples` verification runner for C and Java (`c_problem.py`, `java_problem.py`).
- Added zero-dependency Language Server Protocol (LSP) server (`codeinenglish lsp`) over stdio JSON-RPC for universal IDE support (VS Code, JetBrains, Neovim, Sublime, Cursor).
- Added conversational plain-English OOP phrasing (`create a class named ...`, `create a constructor taking ...`, `create a method named ...`, `tell X to speak`) with offline interpreter and generator parity.
- Added typed synthesis (`synth.py`): about 90 composable operations, type-checked orderings, behaviour-based ambiguity detection, example verification, and cross-checking against the catalog.
- Synthesized programs now generate JavaScript (`target javascript`), checked against Python by a differential test over every operation and random chains.
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
