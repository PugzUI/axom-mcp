# Axom Subagent Dispatch

**When the problem is complex and context is thin:** Dispatch a subagent to gather context in parallel while you solve.

## When to Dispatch

- Initial memory search returned thin results
- Creative flow needs dreams + long_term + web combined
- You need distilled context before the combine step

## Dispatch Flow

1. **Dispatch subagent first** (runs in parallel).
   - **Cursor:** Use `/axom-agent Gather context for [topic]. Return context envelope.` (installed to `~/.cursor/agents/` via `make agents`)
   - **Generic:** Pass [axom-agent.md](../../subagent/axom-agent.md) as context. Use `mcp_task` with attachments: `[docs/agents/subagent/axom-agent.md]`

2. **Main agent:** discover, read, analyze while subagent runs

3. **At combine step:** Wait for subagent result (with timeout ~60–120s)

4. **If timeout:** Proceed with partial context. Store: "Subagent timed out; proceeded with [what we had]."

## Context Envelope (from Subagent)

```json
{
  "memory_hits": [...],
  "dreams": [...],
  "web_snippets": [...],
  "discover_summary": "...",
  "distilled_summary": "2–4 sentences: key patterns, wild ideas, relevant facts."
}
```

## Early Dispatch = Parallel Work

Dispatch at the start of your chain so the subagent runs while you:
- Run `axom_mcp_discover`
- Read relevant files
- Run `axom_mcp_analyze`

By the combine step, subagent result may already be ready.

## Timeout Guidance

- Default: 60–120 seconds
- On timeout: proceed with partial context
- Store in memory: "Subagent timed out; proceeded with [summary of what you had]"

## Chain Failure Recovery

If a chain fails mid-way, store partial result + error in memory so the next agent knows where it stopped:

```
axom_mcp_memory(
  action="write",
  name="partial_[task]_[YYYYMMDD]",
  content="TASK|STEPS_COMPLETED|ERROR|REFLECTION: ...",
  memory_type="short_term"
)
```

## Reference

- **Cursor subagent:** `~/.cursor/agents/axom-agent.md` — invoke via `/axom-agent` (installed by `make agents`)
- [Subagent: Axom Context Gatherer](../../subagent/axom-agent.md) — generic spec for mcp_task
- [axom-memory](../axom-memory/SKILL.md)
- [axom-reflex](../axom-reflex/SKILL.md)
