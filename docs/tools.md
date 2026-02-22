# Tool Reference

Axom provides five core MCP tools to empower AI agents with persistent memory and system interaction capabilities.

## `axom_mcp_memory`

Manage persistent memories in the Axom SQLite database.

| Parameter         | Type    | Required | Description                                                |
| :---------------- | :------ | :------- | :--------------------------------------------------------- |
| `action`          | string  | Yes      | `read`, `write`, `list`, `delete`, `search`                |
| `name`            | string  | No       | Memory identifier (required for `read`, `write`, `delete`) |
| `content`         | string  | No       | Text content to store (required for `write`)               |
| `query`           | string  | No       | Search term for `search` action                            |
| `memory_type`     | string  | No       | `short_term`, `long_term`, `reflex`, `dreams`              |
| `importance`      | string  | No       | `critical`, `important`, `normal`, `low`                   |
| `tags`            | array   | No       | List of strings for categorization                         |
| `limit`           | integer | No       | Maximum results to return (default: 50)                    |
| `expires_in_days` | integer | No       | Override default expiration                                |

---

## `axom_mcp_exec`

Execute file operations and shell commands with chain-reaction support.

| Parameter   | Type   | Required | Description                              |
| :---------- | :----- | :------- | :--------------------------------------- |
| `operation` | string | Yes      | `read`, `write`, `shell`                 |
| `target`    | string | Yes      | File path or shell command               |
| `data`      | string | No       | Content to write (for `write` operation) |
| `chain`     | array  | No       | List of subsequent tool calls            |

---

## `axom_mcp_analyze`

Perform structured analysis on code or text.

| Parameter       | Type   | Required | Description                                     |
| :-------------- | :----- | :------- | :---------------------------------------------- |
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
| :---------- | :------ | :------- | :------------------------------------------------ |
| `domain`    | string  | Yes      | `files`, `tools`, `memory`, `capabilities`, `all` |
| `filter`    | object  | No       | Criteria (e.g., `{"pattern": "*.py"}`)            |
| `recursive` | boolean | No       | Search subdirectories (for `files` domain)        |
| `limit`     | integer | No       | Maximum results to return                         |
| `chain`     | array   | No       | List of subsequent tool calls                     |

---

## `axom_mcp_transform`

Transform data between formats and structures.

| Parameter       | Type   | Required | Description                                      |
| :-------------- | :----- | :------- | :----------------------------------------------- |
| `input`         | any    | Yes      | Data to transform                                |
| `output_format` | string | Yes      | `json`, `yaml`, `csv`, `markdown`, `code`        |
| `input_format`  | string | No       | Hint for input format (auto-detected if omitted) |
| `template`      | string | No       | Jinja2 template for custom formatting            |
| `rules`         | array  | No       | Specific transformation rules                    |
| `chain`         | array  | No       | List of subsequent tool calls                    |
