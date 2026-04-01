---
name: axom-agent
description: Legacy context gatherer. For orchestrator workflow use axom-reader (context, documentation and database specialist).
model: inherit
readonly: true
is_background: false
---

# Axom Context Gatherer (Legacy)

**Superseded by [axom-reader](axom-reader.md)** for the orchestrator workflow. Axom Reader is the context, documentation and database specialist subagent.

---

## When You Are Invoked

Same as axom-reader: when the main agent needs context gathered (memory + discover + distill). Prefer dispatching **axom-reader** by name.

---

## Task

See [axom-reader](axom-reader.md) for the current task, constraints, and output format.

---

## Reference

- [axom-reader](axom-reader.md) – current subagent
- [Agent Index](../INDEX.md)
