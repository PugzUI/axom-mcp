# Axom skills

Skill guides for Axom MCP agents. Each skill is a short guide that tells the agent when and how to use tools and workflows.

## Index

The main index is **[docs/agents/INDEX.md](../INDEX.md)**. It contains:

- Tool selection decision tree
- Standard workflow (Remember → Discover → Analyze → Execute → Remember)
- Quick reference for each tool and links to detailed skill docs

## Skills in this directory

| Skill                                     | Purpose                                                                |
| :---------------------------------------- | :--------------------------------------------------------------------- |
| [axom-memory](axom-memory/SKILL.md)       | Memory workflow: search, write with reflection, associate (start here) |
| [axom-reflex](axom-reflex/SKILL.md)       | Reflex shortcut: implement → verify → update on failure                |
| [axom-dispatch](axom-dispatch/SKILL.md)   | Sub-agent dispatch for context gathering and parallel work             |
| [axom-discover](axom-discover/SKILL.md)   | Map files, tools, memory, capabilities before acting                   |
| [axom-exec](axom-exec/SKILL.md)           | Atomic chains, read/write/shell, tool abstraction                      |
| [axom-analyze](axom-analyze/SKILL.md)     | Debug, review, audit, refactor with actionable output                  |
| [axom-transform](axom-transform/SKILL.md) | Convert formats (JSON, YAML, CSV, markdown, code)                      |

## Discovery

- **Tools**: Call `axom_mcp_discover` with `domain: "tools"` to list MCP tools and parameters.
- **This repo**: Run `make agents` to install these skills into your agent (Cursor, Codex, etc.). See [AGENTS.md](../../../AGENTS.md) for the discovery stanza to add to agent context.

For a short “how to discover and use skills” guide, see [axom-skills/SKILL.md](axom-skills/SKILL.md).
