# Changelog

## 2026-02-24 - Cleanup Pass

- Scope: Stabilized memory search reliability, improved tool output rendering (including neon mode), and added prompt-time recent-context banners with tag-only context.
- Quality: Applied formatting cleanup; validated canonical test workflow; recorded non-gating mypy backlog as existing debt.
- Validation: 215 tests pass (full suite). Database schema verification remains green.
- Docs: Expanded tool reference with output-style + prompt-banner behavior and synced docs to Obsidian.

## 2026-02-23 - Cleanup Pass

- Scope: Complete repository cleanup and restoration. Fixed critical server bugs, schema mismatches, and test failures.
- Quality: Reformatted codebase (Black/Isort); resolved 60+ Mypy errors (type annotations, union attributes, connection handling).
- Validation: 212 tests pass (Core + Integration + Full Coverage). Fixed Pydantic validation and SyntaxErrors in server.
- Docs: Updated server behavior, fixed prompt schemas, and synced docs to Obsidian.
