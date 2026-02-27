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

### Make Command Menu - Overview

```bash
make help              # Project command menu
make install-help      # Install options (e.g. DRY_RUN, etc.)
make clean-help        # Cleanup options (incl. CLEAN_ALL=1 for full reset)
make agents-help       # Agent commands
make db-help           # Database commands
make test-help         # Test commands
```

### Ruff Dev Tool Commands

```bash
make lint-help         # Lint commands (ruff dev tool)
make format-help       # Format commands (ruff dev tool)
```

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
      "command": "axom-mcp"
    }
  }
}
```

For Codex, `~/.codex/config.toml` should contain:

```toml
[mcp_servers.axom]
command = "axom-mcp"
```

---

## Tools

Axom provides five core MCP tools:

- `**axom_mcp_memory**`: Store and retrieve persistent context.
- `**axom_mcp_exec**`: File operations and shell commands with pre-meditated chaining.
- `**axom_mcp_analyze**`: Code analysis and debugging.
- `**axom_mcp_discover**`: Map environment and capabilities.
- `**axom_mcp_transform**`: Convert data between formats.

---

## Documentation

- [Architecture](docs/architecture.md) - System design and data flow.
- [Tool Reference](docs/tools.md) - Detailed tool parameters.
- [Agent Guide](docs/agents/INDEX.md) - How to use Axom with AI agents.
- [Troubleshooting](docs/agents/TROUBLESHOOTING.md) - Common issues and fixes.
