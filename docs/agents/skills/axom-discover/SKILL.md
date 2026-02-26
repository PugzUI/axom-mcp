# Axom Discover Skill

**Map the unknown before you act.** Violently effective recon.
No blind discovery. Filter aggressively. Chain to memory.

## ⚠️ Core Mandate

**Don't fly blind.** Discovery is the foundation of every
precise action. Check memory before deep file dive.
Build a mental map of files, tools, memory, capabilities.

## Domains: Use with Intent

| Domain         | Returns                 | When                       |
| :------------- | :---------------------- | :------------------------- |
| `files`        | File tree, filtered     | Code, configs, tests, docs |
| `tools`        | Available MCP tools     | Before chaining            |
| `memory`       | Memory stats, structure | What is already known      |
| `capabilities` | Server config, limits   | Constraints                |
| `all`          | Combined discovery      | Full recon in one call     |

## Reconnaissance Patterns

### 1. Cold Start: New Repo

```
1. domain="files", recursive=false                        → Top-level structure
2. domain="files", filter={"pattern": "README*|*.md"}     → Docs
3. domain="files", filter={"pattern": "test_*|*_test*"}   → Tests
4. domain="tools"                                         → What can be chained
5. domain="memory"                                        → Prior knowledge
```

### 2. Targeted Strike: You Know What You Need

| Need                | Parameters                           |
| :------------------ | :----------------------------------- | ------------- | --------- |
| Configs             | `domain="files"`, `filter="\*.conf   | \*.json       | \*.yaml"` |
| Python entry points | `domain="files"`, `filter="main\*.py | **main**.py"` |
| Handlers / routes   | `domain="files"`, `filter="_handler_ | _route_"`     |
| Schemas             | `domain="files"`, `filter="_schema_  | _model_"`     |

### 3. Chain Discovery: Multi-Domain Recon

Feed discovery results into the next step:

```json
{
  "domain": "files",
  "filter": { "pattern": "*.py" },
  "limit": 20,
  "chain": [
    {
      "tool": "axom_mcp_memory",
      "args": {
        "action": "write",
        "name": "recon_file_map_20260222",
        "content": "Discovered Python files: ${_result}",
        "memory_type": "short_term"
      }
    }
  ]
}
```

## Filter Patterns: Be Brutal

| Pattern             | Use            |
| :------------------ | :------------- | ---------------------- |
| `*.py`              | Python only    |
| `test\_\*           | _\_test_`      | Test files (pipe = OR) |
| `*.{json,yaml,yml}` | Config formats |
| `**/handlers/*`     | Nested paths   |

## Best Practices

1. **Always filter.** Unfiltered discovery returns noise.
2. **Limit ruthlessly.** 20 for focused recon; 100 for large trees.
3. **Check memory first.** `domain="memory"` before deep file dive.
4. **Chain to memory.** Store results for the next agent or session.

---

_Axom Discover: Map the unknown. Strike with precision._
