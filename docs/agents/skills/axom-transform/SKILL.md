# Axom Transform Skill

**Format mastery. Pipeline glue. Data flow.**
Connective tissue of chains. Read → Transform → Write.

## ⚠️ Core Mandate

**Transformation is the connective tissue of chains.**
Read → Transform → Write. Analyze → Transform → Store.
Transform turns raw data into the shape the next step expects.
Use it aggressively in pipelines.

## Core Capabilities

### 1. Format Conversion

| From | To       | Parameters                                            |
| :--- | :------- | :---------------------------------------------------- |
| JSON | YAML     | `input: {...}`, `output_format: "yaml"`               |
| YAML | JSON     | `input: "key: value"`, `output_format: "json"`        |
| CSV  | JSON     | `input: "a,b\n1,2"`, `output_format: "json"`          |
| Any  | Markdown | `output_format: "markdown"`, optional `template`      |
| Any  | Code     | `output_format: "code"`, `template: "data = ${data}"` |

### 2. Templating (Jinja2)

```json
{
  "input": { "name": "World", "items": [1, 2, 3] },
  "output_format": "markdown",
  "template": "# Hello {{ name }}\n\nItems:\n{% for i in items %}- {{ i }}\n{% endfor %}"
}
```

### 3. Rule-Based Transformation

```json
{
  "input": { "old_name": "value" },
  "output_format": "json",
  "rules": [{ "action": "rename", "field": "old_name", "new": "new_name" }]
}
```

## Pipeline Patterns

### Config Conversion (Exec → Transform → Exec)

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

### Analysis Report → Memory (Analyze → Transform → Memory)

```json
{
  "type": "review",
  "target": "src/",
  "chain": [
    {
      "tool": "axom_mcp_transform",
      "args": {
        "input": "${_result}",
        "output_format": "markdown",
        "template": "# Review Summary\n\n{{ content }}"
      }
    },
    {
      "tool": "axom_mcp_memory",
      "args": {
        "action": "write",
        "name": "review_report_20260222",
        "content": "${_result}",
        "importance": "low"
      }
    }
  ]
}
```

## Data Integrity

- **Verify inputs.** Use `input_format` when ambiguous.
- **Watch for lossy conversion.** CSV ↔ JSON can lose structure.
- **Template escaping.** Jinja2 can execute logic; trust inputs.

## Integration Points

| Upstream  | Transform Role         | Downstream         |
| :-------- | :--------------------- | :----------------- |
| exec read | Parse, convert format  | exec write, memory |
| analyze   | Format for readability | memory             |
| discover  | Structure raw results  | memory             |

---

_Axom Transform: Reshape. Connect. Flow._
