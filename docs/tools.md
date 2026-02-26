# Tool Reference

Axom provides five core MCP tools to empower AI agents with persistent memory and system interaction capabilities.

## Tool Output Style

Set `AXOM_TOOL_OUTPUT_STYLE` to control response rendering:

- `pretty_json` (default): indented JSON output
- `json`: compact JSON output (legacy)
- `pretty`: markdown summary with table previews plus raw JSON block
- `neon`: terminal-inspired ASCII panel preview + raw JSON block

## Prompt Context Banner

Prompt responses for `memory-workflow` and `debug-session` include a compact
2-line context banner derived from the **3 most recent memories**:

- `Axom-Context`: per-memory tag bundles (names hidden)
- `Axom-Memory Search`: short unique tag hints for follow-up search queries

## `axom_mcp_memory`

Manage persistent memories in the Axom SQLite database.


| Parameter         | Type    | Required | Description                                                |
| ----------------- | ------- | -------- | ---------------------------------------------------------- |
| `action`          | string  | Yes      | `read`, `write`, `list`, `delete`, `search`                |
| `name`            | string  | No       | Memory identifier (required for `read`, `write`, `delete`) |
| `content`         | string  | No       | Text content to store (required for `write`)               |
| `query`           | string  | No       | Search term for `search` (runs web search if none found)   |
| `memory_type`     | string  | No       | `short_term`, `long_term`, `reflex`, `dreams`              |
| `importance`      | string  | No       | `low`, `high`, `critical`                                  |
| `tags`            | array   | No       | List of strings for categorization                         |
| `limit`           | integer | No       | Maximum results to return (default: 50)                    |
| `expires_in_days` | integer | No       | Override default expiration                                |


**Search behavior:** When `action` is `search` and no memories match, Axom automatically chains into an internet search (via DDGS) and returns `web_results` with `title`, `href`, and `body` for each hit. Set `AXOM_WEB_SEARCH_FALLBACK=false` to disable; `AXOM_WEB_SEARCH_LIMIT` (default 5) controls max web results.

---

## `axom_mcp_exec`

Execute file operations and shell commands with chain-reaction support.


| Parameter   | Type   | Required | Description                              |
| ----------- | ------ | -------- | ---------------------------------------- |
| `operation` | string | Yes      | `read`, `write`, `shell`                 |
| `target`    | string | Yes      | File path or shell command               |
| `data`      | string | No       | Content to write (for `write` operation) |
| `chain`     | array  | No       | List of subsequent tool calls            |


---

## `axom_mcp_analyze`

Perform structured analysis on code or text.


| Parameter       | Type   | Required | Description                                     |
| --------------- | ------ | -------- | ----------------------------------------------- |
| `type`          | string | Yes      | `debug`, `review`, `audit`, `refactor`, `test`  |
| `target`        | string | Yes      | File path or code block to analyze              |
| `focus`         | string | No       | Area of focus (e.g., "security", "performance") |
| `depth`         | string | No       | `minimal`, `low`, `medium`, `high`, `max`       |
| `output_format` | string | No       | `summary`, `detailed`, `actionable`             |
| `chain`         | array  | No       | List of subsequent tool calls                   |


---

## `axom_mcp_discover`

Explore the environment, files, and server capabilities.


| Parameter   | Type    | Required | Description                                       |
| ----------- | ------- | -------- | ------------------------------------------------- |
| `domain`    | string  | Yes      | `files`, `tools`, `memory`, `capabilities`, `all` |
| `filter`    | object  | No       | Criteria (e.g., `{"pattern": "*.py"}`)            |
| `recursive` | boolean | No       | Search subdirectories (for `files` domain)        |
| `limit`     | integer | No       | Maximum results to return                         |
| `chain`     | array   | No       | List of subsequent tool calls                     |


---

## `axom_mcp_transform`

Transform data between formats and structures.


| Parameter       | Type   | Required | Description                                      |
| --------------- | ------ | -------- | ------------------------------------------------ |
| `input`         | any    | Yes      | Data to transform                                |
| `output_format` | string | Yes      | `json`, `yaml`, `csv`, `markdown`, `code`        |
| `input_format`  | string | No       | Hint for input format (auto-detected if omitted) |
| `template`      | string | No       | Jinja2 template for custom formatting            |
| `rules`         | array  | No       | Specific transformation rules                    |
| `chain`         | array  | No       | List of subsequent tool calls                    |


