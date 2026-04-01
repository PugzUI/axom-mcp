# Axom Agent Documentation Index

**Quick Navigation for Axom MCP Tools**

---

## Tool Selection Decision Tree

```mermaid
graph TD
    START[START HERE: What do you need?]

    FIND[Need to FIND something?]
    RUN[Need to RUN something?]
    ANALYZE[Need to ANALYZE something?]
    CONVERT[Need to CONVERT data?]
    REMEMBER[Need to REMEMBER something?]

    START --> FIND
    START --> RUN
    START --> ANALYZE
    START --> CONVERT
    START --> REMEMBER

    FIND --> DISCOVER[axom_mcp_discover]
    DISCOVER --> D1[domain: files]
    DISCOVER --> D2[domain: tools]
    DISCOVER --> D3[domain: capabilities]

    RUN --> EXEC[axom_mcp_exec]
    EXEC --> E1[operation: read]
    EXEC --> E2[operation: write]
    EXEC --> E3[operation: shell]
    EXEC --> E4[chain: multiple steps]

    ANALYZE --> ANALYZE_T[axom_mcp_analyze]
    ANALYZE_T --> A1[type: debug]
    ANALYZE_T --> A2[type: review]
    ANALYZE_T --> A3[type: audit]
    ANALYZE_T --> A4[type: refactor]

    CONVERT --> TRANS[axom_mcp_transform]
    TRANS --> T1[output_format: json|yaml|csv|...]

    REMEMBER --> MEM[axom_mcp_memory]
    MEM --> M1[action: write]
    MEM --> M2[action: search]
    MEM --> M3[action: list]
    MEM --> M4[action: associate]
    MEM --> REFLEX{has_reflex?}
    M2 --> REFLEX
    REFLEX -->|Yes| SHORTCUT[Reflex shortcut]
    REFLEX -->|No| DISCOVER_ACT[Discover then act]

    style START fill:#f9f,stroke:#333,stroke-width:2px
    style FIND fill:#bbf,stroke:#333,stroke-width:1px
    style RUN fill:#bbf,stroke:#333,stroke-width:1px
    style ANALYZE fill:#bbf,stroke:#333,stroke-width:1px
    style CONVERT fill:#bbf,stroke:#333,stroke-width:1px
    style REMEMBER fill:#bbf,stroke:#333,stroke-width:1px
```

---

## Standard Workflow

| Step        | Action                                           |
| :---------- | :----------------------------------------------- |
| 1. Remember | Search prior context (required). Refine if thin. |
| 2. Discover | Map files, tools, memory before acting.          |
| 3. Analyze  | Debug, review, audit; chain to memory.           |
| 4. Execute  | Chains: read→transform→write, etc.               |
| 5. Remember | Store with REFLECTION (critical).                |

---

## Quick Reference Cards

### Discover (Find)

→ [axom-discover.md](skills/axom-discover/SKILL.md)

| Need         | Parameter          | Example                                              |
| :----------- | :----------------- | :--------------------------------------------------- |
| Find files   | `domain: "files"`  | `{"domain": "files", "filter": {"pattern": "*.py"}}` |
| List tools   | `domain: "tools"`  | `{"domain": "tools"}`                                |
| Check memory | `domain: "memory"` | `{"domain": "memory"}`                               |
| All of above | `domain: "all"`    | `{"domain": "all"}`                                  |

### Exec (Run)

→ [axom-exec.md](skills/axom-exec/SKILL.md)

| Need       | Parameter            | Example                                                         |
| :--------- | :------------------- | :-------------------------------------------------------------- |
| Read file  | `operation: "read"`  | `{"operation": "read", "target": "/path/file"}`                 |
| Write file | `operation: "write"` | `{"operation": "write", "target": "/path/file", "data": "..."}` |
| Shell cmd  | `operation: "shell"` | `{"operation": "shell", "target": "ls -la"}`                    |
| Chain      | `chain: [...]`       | Auto-execute multiple steps                                     |

### Analyze (Debug)

→ [axom-analyze.md](skills/axom-analyze/SKILL.md)

| Need           | Parameter          | Example                                         |
| :------------- | :----------------- | :---------------------------------------------- |
| Find bugs      | `type: "debug"`    | `{"type": "debug", "target": "/path/file.py"}`  |
| Review code    | `type: "review"`   | `{"type": "review", "target": "/path/file.py"}` |
| Security audit | `type: "audit"`    | `{"type": "audit", "focus": "security"}`        |
| Refactor       | `type: "refactor"` | `{"type": "refactor", "focus": "performance"}`  |

### Transform (Convert)

→ [axom-transform.md](skills/axom-transform/SKILL.md)

| From | To       | Parameters                                                                |
| :--- | :------- | :------------------------------------------------------------------------ |
| JSON | YAML     | `{"input": {...}, "output_format": "yaml"}`                               |
| CSV  | JSON     | `{"input": "a,b\n1,2", "output_format": "json"}`                          |
| Any  | Markdown | `{"input": {...}, "output_format": "markdown", "template": "# ${data}"}`  |
| Any  | Code     | `{"input": {...}, "output_format": "code", "template": "data = ${data}"}` |

### Remember (Memory)

Challenges itself, other agents, and users to re-think.
→ [axom-memory.md](skills/axom-memory/SKILL.md)

| Need               | Action                | Example                                                                  |
| :----------------- | :-------------------- | :----------------------------------------------------------------------- |
| Search & reflect   | `action: "search"`    | `{"action": "search", "query": "auth bug", "limit": 5}`                  |
| Store with depth   | `action: "write"`     | Include REFLECTION in content                                            |
| Associate memories | `action: "associate"` | `{"action": "associate", "name": "ref", "target_memory_name": "gotcha"}` |
| Read specific      | `action: "read"`      | `{"action": "read", "name": "bugfix_xyz_20260203"}`                      |
| List all           | `action: "list"`      | `{"action": "list", "limit": 10}`                                        |
| Delete specific    | `action: "delete"`    | `{"action": "delete", "name": "bugfix_xyz_20260203"}`                    |

---

## Available Skills

| Skill                                            | Purpose                                                                          |
| :----------------------------------------------- | :------------------------------------------------------------------------------- |
| [axom-memory](skills/axom-memory/SKILL.md)       | Challenges itself, other agents, and users. Re-think, seek optimal. (START HERE) |
| [axom-reflex](skills/axom-reflex/SKILL.md)       | Reflex shortcut: implement → verify → update on failure.                         |
| [axom-dispatch](skills/axom-dispatch/SKILL.md)   | Sub-agent dispatch for context gathering. Parallel work.                         |
| [axom-discover](skills/axom-discover/SKILL.md)   | Map the unknown before you act. Violently effective recon.                       |
| [axom-exec](skills/axom-exec/SKILL.md)           | Atomic chains. Tool abstraction. Zero wasted steps.                              |
| [axom-analyze](skills/axom-analyze/SKILL.md)     | Deep analysis. Actionable output. Memory integration.                            |
| [axom-transform](skills/axom-transform/SKILL.md) | Format mastery. Pipeline glue. Data flow.                                        |

## URI Resources (Default Context)

| URI              | Description                                                  |
| :--------------- | :----------------------------------------------------------- |
| **axom_toolkit** | Tools index (id, name, description, enabled)                 |
| **axom_agents**  | Subagents registry (axom_exec, axom_reader, axom_researcher) |
| **axom_context** | Three most recent memories                                   |

Load via MCP `ReadResource` with URIs `axom://axom_toolkit`, `axom://axom_agents`, `axom://axom_context`.

---

## Related Documentation

| Doc                                                                                                    | Purpose                                 |
| :----------------------------------------------------------------------------------------------------- | :-------------------------------------- |
| [Rules Reference](rules/axom-core.md)                                                                  | Mandatory agent behavior                |
| Prompts: memory-workflow, debug-session, systematic-debug, complex-problem, code-review, store-pattern | Structured workflows                    |
| [Subagents](subagents/)                                                                                | axom_exec, axom_reader, axom_researcher |
| [Subagent: Axom Reader](subagents/axom-reader.md)                                                      | Context, docs, DB specialist            |
| [Subagent: Axom Exec](subagents/axom-exec.md)                                                          | API/MCP/shell execution                 |
| [Subagent: Axom Researcher](subagents/axom-researcher.md)                                              | Search, filter slop                     |
| [Architecture Overview](../../architecture.md)                                                         | System design                           |
| [Troubleshooting Guide](TROUBLESHOOTING.md)                                                            | Common issues and fixes                 |

---

_Last updated: 2026-02-27_
