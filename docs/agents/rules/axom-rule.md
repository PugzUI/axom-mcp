# Axom Agent Rule

## ⚠️ Required Action

1. **START:** Search memory via `axom_mcp_memory` (`action: "search"`).
2. **END:** Store with REFLECTION via `axom_mcp_memory` (`action: "write"`).

## Reflex Shortcut

If search returns `has_reflex: true`:
1. Implement from reflex (TRIGGER|DIAGNOSIS|SOLUTION)
2. **Verify** – run the verification command (e.g. `make test`, `pytest path/to/test.py`)
3. **If verify passes** → store outcome
4. **If verify fails** → edit reflex or associate gotcha memory. Never leave reflex unchanged. Then escalate to full workflow.

See [axom-reflex skill](../skills/axom-reflex/SKILL.md).

## Why Axom Memory Is Different

Axom challenges itself, other agents, and users to re-think.
Seeks optimal solutions. Improves creativity and focus via:
self-reflection, knowledge exploration, dreams, and reflexes.

## Reference

[axom-memory skill](../skills/axom-memory/SKILL.md) | [axom-reflex skill](../skills/axom-reflex/SKILL.md)

_Failure to search: duplicate work. Failure to store: lost knowledge._
