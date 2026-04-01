# Axom Agent Registry Helper

This document tracks the installation status and compatibility of various AI agents with the Axom MCP server.

## 1. Agent Variant Matrix

| Agent           | IDE | CLI | EXT | Status          |
| :-------------- | :-- | :-- | :-- | :-------------- |
| **Cursor**      | ✅  | ✅  | ❌  | Fully Supported |
| **Kiro**        | ✅  | ➖  | ❌  | IDE Only        |
| **Zed**         | ➖  | ❌  | ❌  | Registry Only   |
| **Windsurf**    | ➖  | ❌  | ❌  | Registry Only   |
| **Trae**        | ✅  | ❌  | ❌  | IDE Only        |
| **Antigravity** | ✅  | ❌  | ❌  | IDE Only        |
| **Codex**       | ❌  | ✅  | ➖  | CLI Only        |
| **Gemini CLI**  | ❌  | ✅  | ➖  | CLI Only        |
| **Qwen Code**   | ❌  | ✅  | ➖  | CLI Only        |
| **OpenCode**    | ❌  | ✅  | ❌  | CLI Only        |
| **Junie**       | ❌  | ✅  | ❌  | CLI Only        |
| **Vibe**        | ❌  | ➖  | ❌  | Registry Only   |
| **Claude Code** | ➖  | ➖  | ➖  | Registry Only   |
| **Kilo Code**   | ❌  | ✅  | ✅  | Extension + CLI |
| **Cline**       | ❌  | ➖  | ➖  | Registry Only   |
| **Roo Code**    | ❌  | ➖  | ➖  | Registry Only   |

**Legend:**

- ✅: Installed and verified on this system
- ➖: Defined in registry but not installed
- ❌: Not yet supported or registry entry missing

## 2. IDE Extension Compatibility

| IDE \ Extension | Kilo Code | Cline | Roo Code | Continue |
| :-------------- | :-------- | :---- | :------- | :------- |
| **Cursor**      | ✅        | ➖    | ➖       | ➖       |
| **VS Code**     | ➖        | ➖    | ➖       | ➖       |
| **Zed**         | ➖        | ➖    | ➖       | ➖       |

## 3. Registry Configuration

The registry (`agent-registry.json`) defines how Axom interacts with each agent:

- **Detection**: Executables and path patterns to find the agent.
- **MCP**: Path to the agent's MCP configuration file.
- **Rules**: Path to the agent's instructions/rules file (e.g., `.cursor/rules`).
- **Skills**: Path to the agent's skill/documentation directory.
