# Axom Agent Troubleshooting Guide

Common issues and solutions for Axom MCP.

## Agent Limitations

### Zed

**Zed does not support global rules or skills.** Zed only supports:
- Project-level rules: `.rules`, `AGENTS.md`, `.cursorrules`, etc. in project root
- Rules Library: Internal database (no CLI/API to inject rules)

For Zed, only MCP configuration is installed. To use Axom rules:
1. Copy `AGENTS.md` to your project root, OR
2. Manually add rules via Zed's Rules Library (`cmd-alt-l`)

---

## Quick Diagnostics

### Tool Not Found

**Error:** `Tool axom_mcp_* not found`

**Solutions:**

1. Check prefixed variants: `axom-mcp-server_axom_mcp_*`.
2. Verify Axom MCP is configured in your client.
3. Check server logs for startup errors.

### Context Server Timeout

**Error:** `axom context server failed to start: Context server request timeout`

**Common causes:**

- Client MCP config still points to a stale command (for example old `uvx` entries).
- `axom-mcp` not installed in the current Python environment.

**Checks:**

1. Re-run install from the repo root: `make install`.
2. Confirm command exists: `command -v axom-mcp`.
3. For Cursor, verify `~/.cursor/mcp.json` uses:
   - `mcpServers.axom.command = "axom-mcp"` (args optional, omit if empty)
4. Restart the IDE/client after config changes.

### Chain Execution Failed

**Error:** Chain stops unexpectedly or variables not resolved.

**Common causes:**

- Using `${content}` instead of `${_result}`.
- Missing condition in chain step.
- Tool name typo.
- Invalid JSON syntax.

### Memory Not Stored

**Error:** Write succeeds but memory not found.

**Checklist:**

- [ ] `action` is `"write"`.
- [ ] `name` follows `[type]_[descriptor]_[YYYYMMDD]`.
- [ ] `importance` and `memory_type` are valid.
- [ ] Database connection is active.

### Permission Denied

**Error:** Cannot read/write files or execute commands.

**Solutions:**

1. **File ops:** Use absolute paths.
2. **Shell:** Ensure non-interactive.
3. **Location:** Use `axom_mcp_exec` with `operation: "list"` to verify.

## Error Patterns by Tool

| Tool                 | Error                  | Solution                                     |
| :------------------- | :--------------------- | :------------------------------------------- |
| `axom_mcp_memory`    | `Invalid action`       | Use: search, write, read, list, delete       |
| `axom_mcp_exec`      | `File not found`       | Use absolute path                            |
| `axom_mcp_analyze`   | `Target not found`     | Verify absolute path                         |
| `axom_mcp_discover`  | `Invalid domain`       | Use: files, tools, memory, capabilities, all |
| `axom_mcp_transform` | `Invalid input format` | Verify input is valid JSON/YAML/etc          |

## Still Stuck?

1. **Review examples:** See skill guides.
2. **Read skill guides:** [INDEX.md](INDEX.md).
3. **Verify environment:** Ensure Axom MCP server is running.

---

_Last updated: 2026-02-22_
