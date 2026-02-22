# Changelog

## 2026-02-23 - Cleanup Pass

- **Scope**: Repository-wide cleanup, linting remediation, and workflow integration.
- **Quality**: Reformatted 11 files with Black/Isort; resolved 20+ Mypy type errors (dataclass mutable defaults, optional connection handling, type casting).
- **Validation**: All 182 tests passed (drift, handlers, schemas, server).
- **Docs**: Created `docs/changelog.md`, updated `.gitignore` for `docs/cleanup.md`, and fixed Makefile logging helpers.
- **Workflow**: Initialized and installed the `cleanup` skill globally for Gemini CLI.
