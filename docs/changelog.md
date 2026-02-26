# Changelog

Format: `## YYYY-MM-DD - <main update>`

## 2026-02-26 - Cleanup: sync from backup, fix Makefile, lint

- Synced changes from backup drive (/run/media/user/Local Disk/dev/src/user/axom-mcp/).
- Fixed Makefile cross-platform Python detection (wildcard → shell test).
- Fixed CRLF line endings in scripts.
- Refactored Makefile: unified OS detection, removed redundant NULL variable, added NO_COLOR support.
- Fixed lint issues: E402 (imports), SIM110, SIM102, F821.
- Validation: 226 tests pass.
- Docs: Makefile improvements, changelog updated.

## 2026-02-25 - Refactor: stabilize database, install workflow, tests, and docs

- Extracted schema.sql; refactored database and handlers for clearer connection handling and type safety.
- Fixed install workflow and MCP config defaults.
- Stabilized memory search.
- Improved tool output rendering (neon mode)
- Added prompt-time recent-context banners.
- Validated canonical test workflow.
- Validation: 215 tests pass (full suite). Database schema verification remains green.
- Docs: Added changelog; expanded troubleshooting and tool reference with output-style and prompt-banner behavior.
