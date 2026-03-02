---
name: cleanup
description: "Pristine Project Cleanup Workflow - Bring a repository to a pristine state without cutting quality"
---
# Pristine Project Cleanup Workflow

Use this runbook to execute a deep, repeatable cleanup in any repository.

## 1) Mission

Bring a repository to a pristine state without cutting quality:

1. Organize files and remove stale artifacts.
2. Resolve lint/diagnostic issues.
3. Ensure full test success.
4. Update docs and changelog.
5. Sync docs to `/home/user/data/db/obsidian/<PROJECT>` with preserved relative paths.
6. Commit and push cleanly.

## 2) Agent Operating Rules

1. Work in gates; do not skip or reorder gates.
2. Fail fast: stop and fix at first red gate.
3. Use bounded loops (max retries per gate).
4. Prefer deterministic commands and structured outputs from tools.
5. Require explicit confirmation before destructive operations outside repo scope.
6. **No Destructive Clean**: NEVER run `make clean` or `make clean-all`. These commands often remove critical configurations and local databases.

## 3) Command Discovery (Project-Agnostic)

Before execution, discover the project's native task runners and quality commands.

1. Detect runner files (`Makefile`, `justfile`, `package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod`, etc.).
2. Resolve canonical commands for:
   - format
   - lint/static analysis
   - tests (unit + integration/e2e if present)
   - docs build/check (if present)
3. **CRITICAL**: Do NOT use automated `clean` targets from task runners (e.g., `make clean`) as they are too destructive.
4. Record selected commands for this run.

If multiple runners exist, prefer the one documented as canonical in repo docs.

## 4) Gate Sequence

### Gate A: Baseline and Safety

1. Confirm branch and upstream state.
2. Pull latest changes.
3. Capture baseline:
   - `git status`
   - current failing diagnostics/tests (if any)

Exit criteria:

1. Branch is correct and up to date.
2. Baseline recorded.

### Gate B: Sort and Organize Files

1. Move misplaced files to canonical locations.
2. Normalize naming and structure conventions.
3. Remove duplicate files with a single source of truth.

Exit criteria:

1. Repository structure is coherent and intentional.

### Gate C: Cleanup Temp and Stale Files

1. Perform manual, surgical removal of temp/cache/build leftovers (e.g., `__pycache__`, `.pytest_cache`).
2. **NEVER** use `make clean` or `make clean-all`.
3. Remove stale generated artifacts that are reproducible.
4. Remove dead files not referenced by code/docs/config.

Exit criteria:

1. No known junk/stale artifacts remain.

### Gate D: Lint and Diagnostic Remediation

1. Run formatter first.
2. Run lint and static diagnostics.
3. Fix all errors and high-value warnings.
4. Re-run until green.

Exit criteria:

1. Lint/static checks pass.

### Gate E: Test Validation

1. Run full default test suite.
2. Run integration/e2e suites when available.
3. Fix failures and rerun.

Exit criteria:

1. All required test suites pass.

### Gate F: Documentation Update

1. Update docs for all behavior/config/API changes.
2. Reorder sections where needed for clarity:
   - overview
   - setup
   - usage
   - reference
   - troubleshooting
3. Remove stale instructions/examples.

Exit criteria:

1. Docs match current behavior.

### Gate G: Changelog Update (`docs/changelog.md`)

1. Add a new entry at the beginning.
2. Include date, scope, validation summary, docs impact.
3. Keep only the latest 7 top-level entries.
4. Remove older entries.

Template:

```md
## YYYY-MM-DD - Cleanup Pass

- Scope: what was cleaned and reorganized
- Quality: lint/diagnostics status
- Validation: tests status
- Docs: updates + sync status
```

Exit criteria:

1. Top-loaded changelog with max 7 latest entries.

### Gate H: Docs Sync to Obsidian

Target root: `/home/user/data/db/obsidian/<PROJECT>`

1. Sync only after docs/changelog are final.
2. Preserve repository-relative paths.

Required mapping examples:

1. `docs/tools.md` -> `/home/user/data/db/obsidian/<PROJECT>/<PROJECT>/docs/tools.md`
2. `docs/changelog.md` -> `/home/user/data/db/obsidian/<PROJECT>/<PROJECT>/docs/changelog.md`

Exit criteria:

1. Mirror reflects latest docs with correct relative paths.

### Gate I: Final Validation, Commit, Push

1. Run final lint/static checks.
2. Run final full tests.
3. Validate intended diff only.
4. Stage intentional changes.
5. Commit with clear cleanup scope.
6. Push and verify remote commit.

Exit criteria:

1. Local working tree clean after commit.
2. Remote branch reflects pushed commit.

## 5) Quality Gate Policy

A run is successful only if all are true:

1. Lint/static checks pass.
2. Full required tests pass.
3. Docs are updated and synced.
4. Changelog updated and capped to latest 7.
5. Commit pushed.

## 6) Failure Protocol

If any gate fails:

1. Stop progression.
2. Record root cause and affected gate.
3. Apply minimal fix.
4. Re-run failed gate.
5. Re-run downstream validation gates before release.
