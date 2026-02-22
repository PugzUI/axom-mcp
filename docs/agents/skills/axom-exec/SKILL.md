# Axom Exec Skill

**Atomic chains. Tool abstraction. Zero wasted steps.**
Read → transform → write in one call. 3–7 steps ideal.

## ⚠️ Core Mandate

**Prefer chains over sequential calls.** One `axom_mcp_exec`
with a `chain` replaces three separate invocations.
Use variable substitution (`${_result}`) to pipe data.
Think pipelines, not scripts.

## Operations

| Operation | Target             | Use                       |
| :-------- | :----------------- | :------------------------ |
| `read`    | File path          | Load content for chaining |
| `write`   | File path + `data` | Store results             |
| `shell`   | Command string     | Non-interactive CLI       |

## Chain Reactions: The Power Move

Each step receives the previous step's output as `_result`.

### Pattern: Read → Transform → Write

```json
{
  "operation": "read",
  "target": "config.json",
  "chain": [
    {
      "tool": "axom_mcp_transform",
      "args": { "input": "${_result}", "output_format": "yaml" }
    },
    {
      "tool": "axom_mcp_exec",
      "args": {
        "operation": "write",
        "target": "config.yaml",
        "data": "${_result}"
      }
    }
  ]
}
```

### Pattern: Read → Analyze → Store in Memory

```json
{
  "operation": "read",
  "target": "src/main.py",
  "chain": [
    {
      "tool": "axom_mcp_analyze",
      "args": { "type": "review", "target": "${_result}", "depth": "high" }
    },
    {
      "tool": "axom_mcp_memory",
      "args": {
        "action": "write",
        "name": "review_main_20260222",
        "content": "${_result}",
        "importance": "normal"
      }
    }
  ]
}
```

## Variable Substitution

| Syntax            | Meaning                        |
| :---------------- | :----------------------------- |
| `${_result}`      | Full result from previous step |
| `${_result.prop}` | Nested property (JSON)         |
| `${_result[0]}`   | Array element                  |

Chain steps receive raw output. For JSON tools,
`_result` may be a string; parse if needed.

## Safety & Best Practices

1. **Verify targets.** Use absolute paths when possible.
2. **Consider irreversibility.** `write` overwrites. `shell` can destroy.
3. **Keep chains short.** 3–7 steps ideal. Longer = harder debugging.
4. **Shell: non-interactive only.** No `vim`, no `less`.

## Chaining to Other Axom Tools

| From      | To            | Flow                      |
| :-------- | :------------ | :------------------------ |
| exec read | transform     | Format conversion         |
| exec read | analyze       | Code review, debug        |
| exec read | memory write  | Store content or analysis |
| transform | exec write    | Store transformed data    |
| discover  | exec / memory | Act on discovery results  |

---

_Axom Exec: Chain. Pipe. Execute._
