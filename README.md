# Axom MCP Server

Axom is a **Model Context Protocol (MCP)** server that provides persistent memory, tool abstraction, and chain-of-thought for AI agents.

## Core Features

- **Persistent Memory**: Store and retrieve context across sessions using the **Axom** (SQLite) database.
- **Tool Abstraction**: Unified interface for memory, execution, analysis, discovery, and transformation.
- **Chain Reactions**: Execute tool sequences where outputs feed into the next step.
- **AI-Powered Classification**: Automatically categorizes memories by type and importance.

---

## Quick Start

Axom runs as **stdio MCP** - your IDE spawns it automatically. No manual server startup needed.

### Prerequisites

- **Python 3.11+**
- **SQLite** (included with Python)
- **Git**

### Installation

#### Linux / macOS / WSL / Windows

Requires (**Git) Bash**, **PowerShell**, or a `make` provider.

```bash
git clone https://github.com/PugzUI/axom-mcp.git
cd axom-mcp
make install
```

**What `make install` does:**

1. Installs Python dependencies.
2. Installs Axom in editable mode (`pip install -e .`).
3. Creates `.env` from `.env.example`.
4. Configures all detected agents (Cursor, Trae, etc.).
5. Installs Axom rules and skills for each agent.

### Verification

```bash
make test      # Run tests
make lint      # Run ruff linter
make format    # Format and fix with ruff
```

### Make Help

Project menus (not GNU Make's built-in). Use `-h` or `-help` consistently:

- `**make make-h**` / `**make make-help**` / `**make h**` / `**make help**` — project command menu
- `**make install-h**` / `**make install-help**` — install options (DRY_RUN, etc.)
- `**make clean-h**` / `**make clean-help**` — cleanup options
- `**make agents-h**` / `**make agents-help**` — agent commands
- `**make db-h**` / `**make db-help**` — database commands
- `**make test-h**` / `**make test-help**` — test commands
- `**make lint-h**` / `**make lint-help**` — lint commands

> **Note:** `make -h` and `make install -h` show GNU Make's built-in options, not our menus. Use `make make-h`, `make make-help`, `make h`, or `make help` for the project menu.

### Post-Install Check

Verify the local command is available:

```bash
command -v axom-mcp
```

Verify MCP initialization against the installed server:

```bash
python3 - <<'PY'
import asyncio
from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters

async def main():
    params = StdioServerParameters(command="axom-mcp", args=[])
    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            tools = await session.list_tools()
            print("tool_count:", len(tools.tools))

asyncio.run(main())
PY
```

---

## Client Configuration

`make install` automatically configures MCP for detected agents. The installer uses the best available command:

1. `**axom-mcp**` (if in PATH)
2. `**axom**` (if in PATH)
3. `**python -m axom_mcp.server**` (fallback)

See [docs/agents/INDEX.md](docs/agents/INDEX.md) for detailed agent configuration.

For Cursor, `~/.cursor/mcp.json` should contain:

```json
{
  "mcpServers": {
    "axom": {
      "command": "axom-mcp",
      "args": []
    }
  }
}
```

For Codex, `~/.codex/config.toml` should contain:

```toml
[context_servers.axom]
command = "axom-mcp"
args = []
```

---

## Tools

Axom provides five core MCP tools:

- `**axom_mcp_memory**`: Store and retrieve persistent context.
- `**axom_mcp_exec**`: File operations and shell commands with chaining.
- `**axom_mcp_analyze**`: Code analysis and debugging.
- `**axom_mcp_discover**`: Map environment and capabilities.
- `**axom_mcp_transform**`: Convert data between formats.

---

## Documentation

- [Architecture](docs/architecture.md) - System design and data flow.
- [Tool Reference](docs/tools.md) - Detailed tool parameters.
- [Agent Guide](docs/agents/INDEX.md) - How to use Axom with AI agents.
- [Troubleshooting](docs/agents/TROUBLESHOOTING.md) - Common issues and fixes.

