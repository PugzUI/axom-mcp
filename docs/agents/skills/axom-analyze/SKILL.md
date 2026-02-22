# Axom Analyze Skill

**Deep analysis. Actionable output. Memory integration.**
Analysis without storage is wasted. Chain findings to memory.
Use reflex for heuristics.

## ⚠️ Core Mandate

**Analysis without storage is wasted insight.** Use `chain`
to write findings to memory. The next agent (or you, later)
will search and find what you learned. Make analysis persist.

## Analysis Types

| Type       | Purpose                | Depth       | When                               |
| :--------- | :--------------------- | :---------- | :--------------------------------- |
| `debug`    | Isolate issues         | high–max    | Errors, symptoms, flaky behavior   |
| `review`   | Code quality, patterns | medium–high | Assessment, style, structure       |
| `audit`    | Security, compliance   | max         | Vulnerabilities, policy violations |
| `refactor` | Improve structure      | medium      | Performance, readability           |
| `test`     | Test coverage, gaps    | medium      | Missing tests, brittle tests       |

## Parameters

| Param           | Values                               | Use                         |
| :-------------- | :----------------------------------- | :-------------------------- |
| `type`          | debug, review, audit, refactor, test | Required                    |
| `target`        | File path or code block              | Required                    |
| `focus`         | e.g. "security", "performance"       | Narrow the analysis         |
| `depth`         | minimal, low, medium, high, max      | Deeper = more thorough      |
| `output_format` | summary, detailed, actionable        | actionable = concrete steps |

## Chained Remediation: Store What You Find

**Pattern:** Analyze → Store in memory

```json
{
  "type": "debug",
  "target": "broken_function.py",
  "depth": "high",
  "focus": "TypeError on line 42",
  "chain": [
    {
      "condition": "${_result.issues_found} == true",
      "tool": "axom_mcp_memory",
      "args": {
        "action": "write",
        "name": "bugfix_analysis_20260222",
        "content": "TASK: Debug TypeError\nAPPROACH: ${_result.summary}\nOUTCOME: Pending fix\nGOTCHAS: ${_result.details}",
        "importance": "important",
        "memory_type": "short_term"
      }
    }
  ]
}
```

**Pattern:** Review → Always store

```json
{
  "type": "review",
  "target": "src/api/handlers.py",
  "depth": "high",
  "output_format": "actionable",
  "chain": [
    {
      "tool": "axom_mcp_memory",
      "args": {
        "action": "write",
        "name": "review_api_handlers_20260222",
        "content": "${_result}",
        "importance": "normal",
        "tags": ["review", "api", "handlers"]
      }
    }
  ]
}
```

## Depth Strategy

| Depth   | Use                            |
| :------ | :----------------------------- |
| minimal | Quick sanity check             |
| low     | Surface-level pass             |
| medium  | Standard review                |
| high    | Deep dive, complex bugs        |
| max     | Security audit, critical paths |

## Integration with Memory

1. **Store bug analyses.** Future agents search "similar bug."
2. **Store review findings.** Build patterns and anti-patterns.
3. **Store audit results.** Track security posture over time.
4. **Use reflex memory.** "Always check X before Y" as `reflex`.

---

_Axom Analyze: Analyze deep. Store what you learn._
