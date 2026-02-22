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
- **uv** (optional, for faster installation and `uvx` support)

### Installation

#### Linux / macOS / WSL / Windows (Native)

Requires **Git Bash**, **PowerShell**, or a `make` provider.

```bash
git clone https://github.com/PugzUI/axom-mcp.git
cd axom-mcp
make install
```

**What `make install` does:**
1. Installs Python dependencies.
2. Creates `.env` from `.env.example`.
3. Configures all detected agents (Cursor, Trae, etc.).
4. Installs Axom rules and skills for each agent.

### Verification

```bash
make test      # Run tests
```

---

## Client Configuration

`make install` automatically configures MCP for detected agents. The installer uses the best available command:
1. **`uvx axom-mcp`** (if `uv` is installed)
2. **`axom`** (if in PATH)
3. **`python -m axom_mcp`** (fallback)

See [docs/agents/INDEX.md](docs/agents/INDEX.md) for detailed agent configuration.

---

## Tools

Axom provides five core MCP tools:

- **`axom_mcp_memory`**: Store and retrieve persistent context.
- **`axom_mcp_exec`**: File operations and shell commands with chaining.
- **`axom_mcp_analyze`**: Code analysis and debugging.
- **`axom_mcp_discover`**: Map environment and capabilities.
- **`axom_mcp_transform`**: Convert data between formats.

---

## Documentation

- [Architecture](docs/architecture.md) - System design and data flow.
- [Tool Reference](docs/tools.md) - Detailed tool parameters.
- [Agent Guide](docs/agents/INDEX.md) - How to use Axom with AI agents.
- [Troubleshooting](docs/agents/TROUBLESHOOTING.md) - Common issues and fixes.
