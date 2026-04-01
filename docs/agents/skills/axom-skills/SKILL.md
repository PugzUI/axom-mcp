# Axom skills – discovery and use

**When to use:** At session start or when you need to refresh knowledge of available tools and skill guides.

## Goal

Load the current set of Axom MCP tools and skill guides into working memory so you can choose the right tool and follow the right workflow.

## Steps

1. **List tools**
   Call `axom_mcp_discover` with `{"domain": "tools"}`. The response lists MCP tools (e.g. `axom_mcp_memory`, `axom_mcp_exec`, `axom_mcp_discover`, `axom_mcp_analyze`, `axom_mcp_transform`) and their parameters. Use this to decide which tool to call and with what arguments.

2. **Load the skill index**
   Read [docs/agents/INDEX.md](../../INDEX.md). It contains the tool decision tree, standard workflow, quick reference cards, and links to each skill’s SKILL.md. Integrate the workflow and skill list into working memory.

3. **Use skills when relevant**
   When a task matches a skill (e.g. “find something” → discover, “remember something” → memory), open that skill’s SKILL.md from [docs/agents/skills/](../README.md) and follow its instructions.

## One-line summary

Call `axom_mcp_discover` with `domain: "tools"`, read `docs/agents/INDEX.md`, and use the skill guides in `docs/agents/skills/` for contextual lookup and chaining.
