# Axom Reflex Shortcut

**When search returns reflex memories:** Implement from experience, verify, and update the reflex if verification fails.

## Reflex Path (with Verification Feedback Loop)

1. **Search** → reflex hit (`has_reflex: true` in search response)
2. **Implement** from reflex (TRIGGER|DIAGNOSIS|SOLUTION)
3. **Verify** – run the verification command (e.g. `make test`, `pytest path/to/test.py`). Evidence before claims.
4. **If verify passes** → store outcome with REFLECTION
5. **If verify fails** → edit the reflex OR associate a gotcha memory. Never leave reflex unchanged—next agent would repeat the same mistake. Then escalate to full workflow.

## Critical: Update Reflex on Failure

When verification fails:

```
axom_mcp_memory(
  action="write",
  name="gotcha_[reflex_name]_[YYYYMMDD]",
  content="TRIGGER|WHAT_FAILED|WHY|REFLECTION: ...",
  memory_type="short_term",
  importance="high"
)
axom_mcp_memory(
  action="associate",
  name="[reflex_name]",
  target_memory_name="gotcha_[reflex_name]_[YYYYMMDD]"
)
```

Then escalate: discover + analyze (medium path) or full creative flow if still stuck.

## Medium Escalation Path

When reflex verify fails but the reflex was close:

1. **Discover** – `axom_mcp_discover(domain="files")` for relevant files
2. **Analyze** – `axom_mcp_analyze(type="debug", target="...")` for root cause
3. If root cause found → fix, update reflex, store
4. Else → full creative flow (dreams, web, subagent)

## Verification Command Specificity

Always run a concrete command. Examples:

- `make test`
- `pytest path/to/test.py`
- `npm test`
- `cargo test`

Avoid vague "I verified." Evidence before claims.

## Reference

- [axom-memory](../axom-memory/SKILL.md) – search, write, associate
- [axom-rule](../../rules/axom-rule.md) – required behavior
