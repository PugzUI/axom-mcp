# Axom Memory Skill

**Memory tool that challenges itself, other agents, and users.**
Re-think. Seek optimal solutions. Improves creativity and focus.
Use for self-reflection, knowledge exploration, deepthink, dreams.

## ⚠️ Core Mandate

**Axom memory is not a key-value store.** It challenges itself,
other agents, and users to re-think and seek optimal solutions.
Via self-reflection, knowledge exploration, and dreams.

### What Axom Memory Does Uniquely

| Capability       | How                                                   |
| :--------------- | :---------------------------------------------------- |
| Search & refine  | **Search → Reflect → Search again**                   |
| Knowledge graphs | **Associate** memories                                |
| Creative ideas   | **Dreams** for experiments; **reflex** for heuristics |
| Self-reflection  | What did you learn about your own reasoning?          |

## Workflow: Search → Act → Reflect → Store

### 1. TASK START: Search with Imagination

**Never act blind.** Search first. If results feel thin,
search again with different terms. Combinatorial exploration:

```
axom_mcp_memory(action="search", query="[domain] [terms]", limit=5)
→ has_reflex: true? Use reflex shortcut (see axom-reflex)
→ No hits? Refine: synonyms, broader terms, related concepts
→ Some hits? Search associated memories; use tags from results
→ Still stuck? Search dreams: memory_type="dreams"
→ Still thin? Web fallback runs automatically
```

**Search response:** Includes `has_reflex` (branch without parsing) and `reflection_excerpt` per result (re-think from prior agent).

**Parameters:**

| Param         | Use                                              |
| :------------ | :----------------------------------------------- |
| `query`       | Be specific. Then creative. Multiple angles.     |
| `limit`       | 5 focused; 10+ when exploring                    |
| `memory_type` | `dreams` for wild ideas; `reflex` for heuristics |
| `tags`        | Narrow by prior categorization                   |

### 2. TASK END: Reflect & Store with Depth

**Shallow storage loses institutional knowledge.**
Store what you learned, not just what you did.

| Param         | Value                                               |
| :------------ | :-------------------------------------------------- |
| `action`      | `"write"`                                           |
| `name`        | `[type]_[descriptor]_[YYYYMMDD]`                    |
| `content`     | Reflective structure below                          |
| `importance`  | `low` \| `high` \| `critical`                        |
| `memory_type` | `long_term` \| `short_term` \| `reflex` \| `dreams` |
| `tags`        | 2–5 strings for future search                       |

### 3. Associate: Build Knowledge Graphs

Link related memories. Use when one explains another,
or both inform a third:

```
axom_mcp_memory(action="associate",
  name="pattern_retry_20260222",
  target_memory_name="gotcha_async_locks_20260222")
```

## Reflective Content Structure

**REFLECTION field is mandatory.** Axom challenges itself,
other agents, and users to re-think. Improves creativity
and focus. Seek optimal solutions.

```text
TASK: [1 line: what needed doing]
APPROACH: [2–3 lines: steps, decisions, pivots]
OUTCOME: [result + metrics if applicable]
GOTCHAS: [pitfalls, surprises, edge cases]
REFLECTION: [What did you learn about your reasoning?
  What would you do differently? What assumption was wrong?]
RELATED: [memory names, paths, or "associate with X"]
```

## Memory Types: Choose with Intent

| Type           | Purpose                                   | When                  |
| :------------- | :---------------------------------------- | :-------------------- |
| **long_term**  | Patterns, decisions, architecture         | Reusable across tasks |
| **short_term** | Task-specific context                     | One-off; will expire  |
| **reflex**     | Heuristics; "always check X before Y"     | Learned behavior      |
| **dreams**     | Experimental ideas, creative explorations | Imagination fuel      |

## Naming Convention

Format: `[type]_[descriptor]_[YYYYMMDD]`

| Type       | Example                              |
| :--------- | :----------------------------------- |
| `bugfix`   | `bugfix_auth_timeout_20260222`       |
| `feature`  | `feature_oauth_flow_20260222`        |
| `pattern`  | `pattern_retry_logic_20260222`       |
| `decision` | `decision_sqlite_storage_20260222`   |
| `gotcha`   | `gotcha_async_locks_20260222`        |
| `insight`  | `insight_why_users_abandon_20260222` |

## Advanced: Multi-Pass Reflection

When the problem is hard:

1. **Search** with initial query
2. **Act** on what you find
3. **Search again** with terms from your attempt
4. **Reflect** in content: "First search missed X because..."
5. **Store** with rich REFLECTION so the next agent (or you)
   does not repeat the blind spot

---

_Axom Memory: Challenges itself, other agents, and users to re-think.
Improves creativity and focus. Seek optimal solutions._
