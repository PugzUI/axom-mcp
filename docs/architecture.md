# Architecture

Axom is a Model Context Protocol (MCP) server that provides AI agents with persistent memory, tool abstraction, and chain-reaction capabilities.

## Technical Stack

- **Language**: Python 3.11+
- **Database**: SQLite (embedded, zero-config, file-based)
- **Protocol**: MCP (Model Context Protocol) via stdio
- **Driver**: `aiosqlite` (async SQLite driver)

## Core Components

### 1. Axom MCP Server

The main entry point (`src/axom_mcp/server.py`) that implements the MCP protocol and handles client requests.

### 2. Axom Database

The persistence layer (`src/axom_mcp/database.py`) that manages the SQLite database where memories are stored.

### 3. Handlers

Specialized modules (`src/axom_mcp/handlers/`) that implement the logic for each MCP tool:

- `memory.py`: Persistent context management
- `exec.py`: File I/O and shell command execution
- `analyze.py`: Code and data analysis
- `discover.py`: Environment and capability mapping
- `transform.py`: Data format conversion

### 4. Chain Engine

Orchestrates multi-step tool calls with variable substitution, allowing tools to feed their output into subsequent steps.

## Data Flow

1.  **Request**: Client sends a JSON-RPC request to the server via stdio.
2.  **Dispatch**: The server identifies the requested tool and routes it to the appropriate handler.
3.  **Action**: The handler performs its operation, interacting with the database or the system as needed.
4.  **Chaining**: If a `chain` is provided, the Chain Engine executes subsequent steps using the results of previous ones.
5.  **Response**: The final result is formatted as an MCP-compliant JSON response and sent back to the client.
