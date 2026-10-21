# Changelog

## 0.2.0 — 2026-10-21

- Added versioned `.en` source contracts for legacy, `en 0.1`, and `en 0.2` files.
- Added explicit `#?` problem requests, structured source diagnostics, JSON check/generate responses, and the run-plan schema.
- Added dry-run-by-default, code-body-verified source migration.
- Added deterministic generated-file provenance and the VS Code extension's CLI-owned run plan.
- Headerless files now emit EN-W401. They remain supported through package minor releases 0.2.x and 0.3.x; removal is scheduled for 0.4.0.
