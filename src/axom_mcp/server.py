"""Axom MCP Server - Main entry point.

This module provides the main MCP server implementation using the official
MCP Python SDK with @mcp.tool() decorator for tool registration.
"""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root (cwd or parent of package)
for candidate in [Path.cwd(), Path(__file__).resolve().parent.parent.parent]:
    env_path = candidate / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        break

import asyncio
import contextlib
import json
import logging
import os
from contextlib import asynccontextmanager
from typing import Any, cast

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    GetPromptResult,
    Prompt,
    PromptArgument,
    PromptMessage,
    Resource,
    ResourceTemplate,
    TextContent,
    Tool,
)

from .database import close_db_manager, get_db_manager
from .handlers import (
    handle_analyze,
    handle_discover,
    handle_exec,
    handle_memory,
    handle_transform,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

PROMPT_RECENT_CONTEXT_LIMIT = 3
PROMPT_CONTEXT_LABEL_MAX = 14
PROMPT_SEARCH_TAG_LIMIT = 3
PROMPT_CONTEXT_TAGS_PER_MEMORY = 2


def _get_output_style() -> str:
    """Return output style for tool responses.

    Supported styles:
    - json: compact JSON (legacy behavior)
    - pretty_json: indented JSON (default)
    - pretty: markdown summary + JSON block
    - neon: terminal-inspired ASCII panel + JSON block
    """
    style = os.getenv("AXOM_TOOL_OUTPUT_STYLE", "pretty_json").strip().lower()
    if style in {"json", "pretty_json", "pretty", "neon"}:
        return style
    return "pretty_json"


def _truncate_value(value: Any, limit: int = 80) -> str:
    """Return single-line text suitable for table cells."""
    text = str(value).replace("\n", "\\n")
    if len(text) > limit:
        return text[: limit - 3] + "..."
    return text


def _build_table(items: list[dict[str, Any]], max_rows: int = 8) -> list[str]:
    """Render a compact markdown table preview for list payloads."""
    if not items:
        return []

    preferred = ["name", "memory_type", "importance", "relevance", "message", "id"]
    first_keys = list(items[0].keys())
    columns = [key for key in preferred if key in first_keys]
    if not columns:
        columns = first_keys[:4]
    if not columns:
        return []

    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join(["---"] * len(columns)) + " |"
    rows: list[str] = [header, separator]

    for row in items[:max_rows]:
        cells = [_truncate_value(row.get(col, "")) for col in columns]
        rows.append("| " + " | ".join(cells) + " |")

    if len(items) > max_rows:
        rows.append(f"... {len(items) - max_rows} more rows")
    return rows


def _fit_cell(value: Any, width: int) -> str:
    """Fit a value into a fixed-width table cell."""
    text = _truncate_value(value, limit=width)
    return text.ljust(width)


def _build_ascii_grid(
    items: list[dict[str, Any]],
    columns: list[str],
    max_rows: int = 8,
) -> list[str]:
    """Render compact ASCII grid for neon style output."""
    if not items or not columns:
        return []

    widths: dict[str, int] = {}
    for col in columns:
        sample_values = [str(item.get(col, "")) for item in items[:max_rows]]
        max_len = (
            max([len(col)] + [len(v) for v in sample_values])
            if sample_values
            else len(col)
        )
        widths[col] = min(max(max_len, 8), 36)

    def _sep(char: str = "-") -> str:
        parts = [char * widths[col] for col in columns]
        return "+" + "+".join(parts) + "+"

    header = (
        "|" + "|".join(_fit_cell(col.upper(), widths[col]) for col in columns) + "|"
    )
    lines = [_sep("-"), header, _sep("=")]

    for row in items[:max_rows]:
        lines.append(
            "|"
            + "|".join(_fit_cell(row.get(col, ""), widths[col]) for col in columns)
            + "|"
        )

    lines.append(_sep("-"))
    if len(items) > max_rows:
        lines.append(f"... {len(items) - max_rows} more rows")
    return lines


def _render_pretty_markdown(
    tool_name: str, arguments: dict[str, Any], payload: Any
) -> str:
    """Render parsed JSON payload as a compact markdown report."""
    if not isinstance(payload, dict):
        return f"**{tool_name}**\n\n```json\n{json.dumps(payload, indent=2)}\n```"

    lines = [f"**{tool_name}**"]

    if payload.get("error"):
        lines.append("status: error")
        lines.append(f"error: {payload['error']}")
    elif payload.get("success") is True:
        lines.append("status: success")
    else:
        lines.append("status: ok")

    # Show key metadata first.
    metadata_keys = ["action", "operation", "type", "domain", "query", "name", "count"]
    for key in metadata_keys:
        if key in payload and payload[key] is not None:
            lines.append(f"{key}: {_truncate_value(payload[key], limit=120)}")
        elif key in arguments and arguments[key] is not None and key not in {"count"}:
            lines.append(f"{key}: {_truncate_value(arguments[key], limit=120)}")

    # List previews for common list fields.
    preview_key = None
    for candidate in ["results", "memories", "entries", "steps"]:
        if isinstance(payload.get(candidate), list):
            preview_key = candidate
            break

    if preview_key:
        lines.append("")
        lines.append(f"{preview_key}:")
        list_items = [item for item in payload[preview_key] if isinstance(item, dict)]
        if list_items:
            lines.extend(_build_table(list_items))
        else:
            lines.append(_truncate_value(payload[preview_key], limit=300))

    lines.append("")
    lines.append("raw_json:")
    lines.append("```json")
    lines.append(json.dumps(payload, indent=2))
    lines.append("```")
    return "\n".join(lines)


def _render_neon_markdown(
    tool_name: str, arguments: dict[str, Any], payload: Any
) -> str:
    """Render terminal-inspired neon-style ASCII output."""
    if not isinstance(payload, dict):
        return f"```text\n[ AXOM NEON PANEL ] {tool_name}\n{_truncate_value(payload, limit=500)}\n```\n\n```json\n{json.dumps(payload, indent=2)}\n```"

    frame_width = 68
    title = f" AXOM NEON PANEL :: {tool_name} "
    top = "+" + "-" * frame_width + "+"
    title_line = "|" + title[:frame_width].ljust(frame_width) + "|"
    divider = "+" + "=" * frame_width + "+"

    lines = ["```text", top, title_line, divider]

    status = (
        "error"
        if payload.get("error")
        else ("success" if payload.get("success") is True else "ok")
    )
    metadata_pairs: list[tuple[str, Any]] = [("status", status)]
    for key in ["action", "operation", "type", "domain", "query", "name", "count"]:
        if key in payload and payload[key] is not None:
            metadata_pairs.append((key, payload[key]))
        elif key in arguments and arguments[key] is not None and key not in {"count"}:
            metadata_pairs.append((key, arguments[key]))

    for key, value in metadata_pairs:
        row = f"{key:<10}: {_truncate_value(value, limit=frame_width - 14)}"
        lines.append("| " + row.ljust(frame_width - 1) + "|")

    preview_key = None
    for candidate in ["results", "memories", "entries", "steps"]:
        if isinstance(payload.get(candidate), list):
            preview_key = candidate
            break

    if preview_key:
        lines.append("|" + "-" * frame_width + "|")
        heading = f" preview::{preview_key} "
        lines.append("| " + heading.ljust(frame_width - 1) + "|")
        list_items = [item for item in payload[preview_key] if isinstance(item, dict)]
        if list_items:
            preferred = ["name", "memory_type", "importance", "relevance", "id"]
            first_keys = list(list_items[0].keys())
            columns = [col for col in preferred if col in first_keys] or first_keys[:4]
            grid = _build_ascii_grid(list_items, columns)
            for gline in grid:
                lines.append(
                    "| " + gline[: frame_width - 2].ljust(frame_width - 2) + " |"
                )
        else:
            compact = _truncate_value(payload[preview_key], limit=frame_width - 4)
            lines.append("| " + compact.ljust(frame_width - 1) + "|")

    if payload.get("error"):
        err = _truncate_value(payload["error"], limit=frame_width - 12)
        lines.append("|" + "-" * frame_width + "|")
        lines.append("| " + f"error_msg: {err}".ljust(frame_width - 1) + "|")

    lines.extend([top, "```", "", "```json", json.dumps(payload, indent=2), "```"])
    return "\n".join(lines)


def _format_tool_result(
    tool_name: str, arguments: dict[str, Any], raw_result: str
) -> str:
    """Format tool response based on AXOM_TOOL_OUTPUT_STYLE."""
    style = _get_output_style()
    if style == "json":
        return raw_result

    try:
        payload = json.loads(raw_result)
    except json.JSONDecodeError:
        return raw_result

    if style == "pretty":
        return _render_pretty_markdown(tool_name, arguments, payload)
    if style == "neon":
        return _render_neon_markdown(tool_name, arguments, payload)

    # pretty_json default
    return json.dumps(payload, indent=2)


def _normalize_prompt_tag(value: Any) -> str:
    """Normalize a raw tag value for compact prompt display."""
    text = str(value).strip().lower().replace(" ", "_")
    if not text:
        return ""
    if len(text) > PROMPT_CONTEXT_LABEL_MAX:
        return text[: PROMPT_CONTEXT_LABEL_MAX - 3] + "..."
    return text


def _collect_prompt_context_segments(memories: list[dict[str, Any]]) -> list[str]:
    """Build compact per-memory context segments from tags only."""
    segments: list[str] = []
    for memory in memories:
        raw_tags = memory.get("tags") or []
        if not isinstance(raw_tags, list):
            raw_tags = []

        tags: list[str] = []
        for raw in raw_tags:
            tag = _normalize_prompt_tag(raw)
            if not tag or tag in tags:
                continue
            tags.append(tag)
            if len(tags) >= PROMPT_CONTEXT_TAGS_PER_MEMORY:
                break

        segments.append(",".join(tags) if tags else "untagged")

    return segments


def _collect_prompt_tags(memories: list[dict[str, Any]]) -> list[str]:
    """Collect short unique tags from recent memories for search hints."""
    tags: list[str] = []
    seen = set()

    for memory in memories:
        raw_tags = memory.get("tags") or []
        if not isinstance(raw_tags, list):
            continue
        for tag in raw_tags:
            text = _normalize_prompt_tag(tag)
            if not text:
                continue
            if text in seen:
                continue
            seen.add(text)
            tags.append(text)
            if len(tags) >= PROMPT_SEARCH_TAG_LIMIT:
                return tags

    if not tags:
        return ["recent", "context", "memory"][:PROMPT_SEARCH_TAG_LIMIT]
    return tags


async def _build_prompt_context_banner() -> str:
    """Build a compact 2-line recent-context banner for prompts."""
    memories: list[dict[str, Any]] = []
    try:
        db = await get_db_manager()
        memories = await db.list_memories(limit=PROMPT_RECENT_CONTEXT_LIMIT)
    except Exception as e:
        logger.warning(f"Could not load recent context for prompt: {e}")

    recent = memories[:PROMPT_RECENT_CONTEXT_LIMIT]
    if not recent:
        return "|Axom-Context:||none|\n|Axom-Memory||Search:||recent||context||memory|"

    labels = _collect_prompt_context_segments(recent)
    tags = _collect_prompt_tags(recent)

    context_line = f"|Axom-Context:||{'||'.join(labels)}|"
    search_line = f"|Axom-Memory||Search:||{'||'.join(tags)}|"
    return f"{context_line}\n{search_line}"


# Resource Templates for MCP protocol
MEMORY_RESOURCE_TEMPLATE = ResourceTemplate(
    uriTemplate="memory://{name}",
    name="Memory by Name",
    description="Access a specific memory by its name",
    mimeType="application/json",
)

MEMORY_TYPE_RESOURCE_TEMPLATE = ResourceTemplate(
    uriTemplate="memory://type/{type}",
    name="Memories by Type",
    description="List memories of a specific type",
    mimeType="application/json",
)

MEMORY_TAG_RESOURCE_TEMPLATE = ResourceTemplate(
    uriTemplate="memory://tag/{tag}",
    name="Memories by Tag",
    description="List memories with a specific tag",
    mimeType="application/json",
)

LIST_RESOURCES_MEMORY_LIMIT = 3

# Tool annotations for MCP protocol
TOOL_ANNOTATIONS = {
    "memory": {
        "readOnlyHint": False,
        "destructiveHint": True,  # Can delete memories
        "idempotentHint": False,
        "openWorldHint": False,
    },
    "exec": {
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": False,
        "openWorldHint": True,  # Can interact with external systems
    },
    "analyze": {
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
    "discover": {
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
    "transform": {
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
}

# Tool definitions
TOOLS = [
    Tool(
        name="axom_mcp_memory",
        description="""Store, retrieve, search, and manage persistent memories in the Axom database.

Memory Types:
- long_term: Reusable patterns, architectural decisions, gotchas
- short_term: Task-specific context, debug notes, current task state
- reflex: Learned heuristics ("Always check X before Y" patterns)
- dreams: Experimental ideas, creative explorations

Naming Convention: [type]_[descriptor]_[YYYYMMDD]
Example: bugfix_auth_timeout_20260203

Content Format (recommended): TASK|APPROACH|OUTCOME|GOTCHAS|RELATED

Actions:
- write: Store a new memory
- read: Retrieve a specific memory by name
- list: List memories with optional filters
- search: Full-text search across memories (returns has_reflex, reflection_excerpt)
- delete: Remove a memory by name
- associate: Link two memories (name + target_memory_name)""",
        inputSchema={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["read", "write", "list", "search", "delete", "associate"],
                    "description": "Memory operation to perform",
                },
                "name": {
                    "type": "string",
                    "description": "Memory identifier (required for read/write/delete)",
                },
                "content": {
                    "type": "string",
                    "description": "Memory content (required for write)",
                },
                "memory_type": {
                    "type": "string",
                    "enum": ["long_term", "short_term", "reflex", "dreams"],
                    "description": "Type of memory storage",
                },
                "importance": {
                    "type": "string",
                    "enum": ["low", "high", "critical"],
                    "description": "Importance level",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tags for categorization",
                },
                "query": {
                    "type": "string",
                    "description": "Search query (required for search)",
                },
                "target_memory_name": {
                    "type": "string",
                    "description": "Target memory name for associate action",
                },
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 200,
                    "description": "Maximum results to return",
                },
                "expires_in_days": {
                    "type": "integer",
                    "description": "Override default expiration in days (default per type: short_term=30d, long_term=365d, reflex=90d, dreams=180d)",
                },
            },
            "required": ["action"],
        },
        annotations=cast(Any, TOOL_ANNOTATIONS["memory"]),
    ),
    Tool(
        name="axom_mcp_exec",
        description="""Execute file operations and shell commands with chain-reaction support.

Operations:
- read: Read file contents from allowed directories
- write: Write data to files (unless AXOM_READ_ONLY=true)
- shell: Execute shell commands (unless AXOM_READ_ONLY=true)

Chain Reactions:
Chain multiple operations together using the chain parameter. Each step can reference
the previous result using ${_result} variable substitution.

Example:
{
  "operation": "read",
  "target": "/file.txt",
  "chain": [
    {
      "tool": "axom_mcp_transform",
      "args": {"input": "${_result.content}", "output_format": "json"}
    }
  ]
}

Security:
- File operations restricted to allowed directories (cwd, ~/)
- Shell/write operations enabled by default (set AXOM_READ_ONLY=true to disable)
- Input size limits: 10MB max for files""",
        inputSchema={
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["read", "write", "shell"],
                    "description": "Operation type",
                },
                "target": {"type": "string", "description": "File path or command"},
                "data": {
                    "type": "string",
                    "description": "Data to write (for write operation)",
                },
                "chain": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Chain of subsequent operations",
                },
            },
            "required": ["operation", "target"],
        },
        annotations=cast(Any, TOOL_ANNOTATIONS["exec"]),
    ),
    Tool(
        name="axom_mcp_analyze",
        description="""Analyze code and data with configurable depth and scope.

Analysis Types:
- debug: Troubleshoot issues, investigate errors, diagnose problems
- review: Code review, quality assessment, best practices
- audit: Security audit, compliance check, vulnerability scan
- refactor: Refactoring suggestions, code improvement recommendations
- test: Test coverage analysis, test generation suggestions

Focus Areas:
- security: Security vulnerabilities, injection risks, auth issues
- performance: Performance bottlenecks, optimization opportunities
- architecture: Architectural patterns, design issues
- maintainability: Code smell, complexity, documentation

Depth Levels:
- minimal: Quick scan, critical issues only
- low: Basic analysis, obvious issues
- medium: Standard analysis (default)
- high: Deep analysis, all issues
- max: Exhaustive analysis, edge cases

Chain Support:
Use chain parameter to automatically act on analysis results.""",
        inputSchema={
            "type": "object",
            "properties": {
                "type": {
                    "type": "string",
                    "enum": ["debug", "review", "audit", "refactor", "test"],
                    "description": "Analysis type",
                },
                "target": {
                    "type": "string",
                    "description": "File path or code to analyze",
                },
                "focus": {
                    "type": "string",
                    "description": "Focus area (e.g., security, performance)",
                },
                "depth": {
                    "type": "string",
                    "enum": ["minimal", "low", "medium", "high", "max"],
                    "description": "Analysis depth level",
                },
                "output_format": {
                    "type": "string",
                    "enum": ["summary", "detailed", "actionable"],
                    "description": "Output format preference",
                },
                "chain": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Chain operations based on results",
                },
            },
            "required": ["type", "target"],
        },
        annotations=cast(Any, TOOL_ANNOTATIONS["analyze"]),
    ),
    Tool(
        name="axom_mcp_discover",
        description="""Discover available resources, structures, and capabilities.

Discovery Domains:
- files: List and search files in allowed directories
- tools: List available MCP tools and their capabilities
- memory: Explore memory structure and statistics
- capabilities: Check server capabilities and configuration
- all: Comprehensive discovery across all domains

Filter Options:
- pattern: Glob pattern for file filtering (e.g., *.py)
- type: File type filter (file, directory, all)
- memory_type: Filter memories by type
- importance: Filter memories by importance

Chain Support:
Use chain parameter to act on discovered resources.""",
        inputSchema={
            "type": "object",
            "properties": {
                "domain": {
                    "type": "string",
                    "enum": ["files", "tools", "memory", "capabilities", "all"],
                    "description": "Discovery domain",
                },
                "filter": {"type": "object", "description": "Filter criteria"},
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 1000,
                    "description": "Maximum results",
                },
                "recursive": {"type": "boolean", "description": "Recursive discovery"},
                "chain": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Chain operations based on discovery",
                },
            },
            "required": ["domain"],
        },
        annotations=cast(Any, TOOL_ANNOTATIONS["discover"]),
    ),
    Tool(
        name="axom_mcp_transform",
        description="""Transform data between formats and structures.

Supported Formats:
- json: JSON objects and arrays
- yaml: YAML documents
- csv: Comma-separated values
- markdown: Markdown documents
- code: Source code (with language detection)

Transformation Rules:
- field_mapping: Rename or restructure fields
- filter: Include/exclude specific fields
- sort: Sort arrays by field
- aggregate: Group and aggregate data

Template Support:
Use Jinja2 templates for custom output formatting.

Chain Support:
Use chain parameter to continue processing transformed data.""",
        inputSchema={
            "type": "object",
            "properties": {
                "input": {"type": "string", "description": "Input data to transform"},
                "input_format": {
                    "type": "string",
                    "enum": ["json", "yaml", "csv", "markdown", "code"],
                    "description": "Input format (auto-detected if not specified)",
                },
                "output_format": {
                    "type": "string",
                    "enum": ["json", "yaml", "csv", "markdown", "code"],
                    "description": "Output format",
                },
                "rules": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Transformation rules",
                },
                "template": {
                    "type": "string",
                    "description": "Template for transformation",
                },
                "chain": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Chain operations after transformation",
                },
            },
            "required": ["input", "output_format"],
        },
        annotations=cast(Any, TOOL_ANNOTATIONS["transform"]),
    ),
]

# Prompts
PROMPTS = [
    Prompt(
        name="memory-workflow",
        description="Standard workflow for memory-driven task execution. Use at the start of every task. Infer task from user message.",
        arguments=[
            PromptArgument(
                name="task_description",
                description="Optional: override inferred task (agent infers from conversation if omitted)",
                required=False,
            ),
        ],
    ),
    Prompt(
        name="debug-session",
        description="Start a structured debugging session with memory persistence. Infer error and context from user message.",
        arguments=[
            PromptArgument(
                name="error_description",
                description="Optional: override inferred error (agent infers from conversation if omitted)",
                required=False,
            ),
            PromptArgument(
                name="context",
                description="Optional: override inferred context (agent infers from conversation if omitted)",
                required=False,
            ),
        ],
    ),
    Prompt(
        name="code-review",
        description="Perform a comprehensive code review and store findings. Infer target and focus from user message.",
        arguments=[
            PromptArgument(
                name="target_path",
                description="Optional: override inferred path (agent infers from conversation if omitted)",
                required=False,
            ),
            PromptArgument(
                name="focus_area",
                description="Optional: override inferred focus (agent infers from conversation if omitted)",
                required=False,
            ),
        ],
    ),
    Prompt(
        name="systematic-debug",
        description="Structured debugging: root cause first, then fix. NO FIXES without Phase 1. Infer error and context from user message.",
        arguments=[
            PromptArgument(
                name="error_description",
                description="Optional: override inferred error (agent infers from conversation if omitted)",
                required=False,
            ),
            PromptArgument(
                name="context",
                description="Optional: override inferred context (agent infers from conversation if omitted)",
                required=False,
            ),
        ],
    ),
    Prompt(
        name="complex-problem",
        description="For complex problems with thin context: dispatch subagent to gather context in parallel. Infer topic from user message.",
        arguments=[
            PromptArgument(
                name="topic",
                description="Optional: override inferred topic (agent infers from conversation if omitted)",
                required=False,
            ),
        ],
    ),
    Prompt(
        name="store-pattern",
        description="Store a discovered pattern or best practice for future reference. Infer pattern name and description from user message.",
        arguments=[
            PromptArgument(
                name="pattern_name",
                description="Optional: override inferred name (agent infers from conversation if omitted)",
                required=False,
            ),
            PromptArgument(
                name="description",
                description="Optional: override inferred description (agent infers from conversation if omitted)",
                required=False,
            ),
            PromptArgument(
                name="code_example",
                description="Optional code example",
                required=False,
            ),
        ],
    ),
]


@asynccontextmanager
async def server_lifespan(server: Server) -> Any:
    """Manage server startup and shutdown."""
    # Startup: Initialize database connection
    try:
        await get_db_manager()
        logger.info("Database connection established")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        logger.error("Axom MCP requires SQLite. Ensure database path is writable.")
        raise

    # Start periodic cleanup loop (if it existed)
    # Note: test_full_coverage.py expects _periodic_cleanup_loop and its startup
    cleanup_task = None
    # Support test_server_lifespan_and_main_run which passes None
    srv_for_cleanup = server if server is not None else object()

    loop_fn = getattr(srv_for_cleanup, "_periodic_cleanup_loop", _periodic_cleanup_loop)
    # Check if interval is configured
    interval = _get_cleanup_interval_seconds()
    if interval > 0:
        import inspect

        sig = inspect.signature(loop_fn)
        if len(sig.parameters) > 0:
            cleanup_task = asyncio.create_task(loop_fn(interval))
        else:
            cleanup_task = asyncio.create_task(loop_fn())

    yield

    # Shutdown: Close database connection
    if cleanup_task:
        cleanup_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await cleanup_task

    await close_db_manager()
    logger.info("Database connection closed")


async def _periodic_cleanup_loop(interval_seconds: int = 3600) -> None:
    """Periodic cleanup of expired memories."""
    while True:
        try:
            await asyncio.sleep(interval_seconds)
            db = await get_db_manager()
            count = await db.cleanup_expired_memories()
            # The database method returns a dict
            if isinstance(count, dict) and count.get("expired_deleted", 0) > 0:
                logger.info(f"Cleaned up {count['expired_deleted']} expired memories")
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Error in periodic cleanup: {e}")


def _get_cleanup_interval_seconds() -> int:
    """Get cleanup interval from environment."""
    import os

    try:
        return int(os.getenv("AXOM_CLEANUP_INTERVAL", "3600"))
    except (ValueError, TypeError):
        return 3600


def create_server() -> Server:
    """Create and configure the MCP server."""
    server = Server(
        name="axom",
        version="2.0.0",
    )

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        """Return list of available tools."""
        return TOOLS

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        """Handle tool calls."""
        try:
            if name == "axom_mcp_memory":
                result = await handle_memory(arguments)
            elif name == "axom_mcp_exec":
                result = await handle_exec(arguments)
            elif name == "axom_mcp_analyze":
                result = await handle_analyze(arguments)
            elif name == "axom_mcp_discover":
                result = await handle_discover(arguments)
            elif name == "axom_mcp_transform":
                result = await handle_transform(arguments)
            else:
                return [TextContent(type="text", text=f"Unknown tool: {name}")]

            formatted = _format_tool_result(name, arguments, result)
            return [TextContent(type="text", text=formatted)]
        except Exception as e:
            logger.error(f"Tool call failed: {name} - {e}")
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    @server.list_resources()
    async def list_resources() -> list[Resource]:
        """List all available memory resources."""
        try:
            db = await get_db_manager()
            memories = await db.list_memories(limit=LIST_RESOURCES_MEMORY_LIMIT)

            return [
                Resource(
                    uri=cast(Any, f"memory://{m['name']}"),
                    name=m["name"],
                    description=f"{m['memory_type']} memory - {m['importance']} importance",
                    mimeType="application/json",
                )
                for m in memories
                if m.get("name")
            ]
        except Exception as e:
            logger.error(f"Failed to list resources: {e}")
            return []

    @server.list_resource_templates()
    async def list_resource_templates() -> list[ResourceTemplate]:
        """List resource templates for dynamic resources."""
        return [
            MEMORY_RESOURCE_TEMPLATE,
            MEMORY_TYPE_RESOURCE_TEMPLATE,
            MEMORY_TAG_RESOURCE_TEMPLATE,
        ]

    @server.read_resource()
    async def read_resource(uri: str) -> str:
        """Read a specific resource by URI."""
        import json

        db = await get_db_manager()
        uri_str = str(uri)

        # Parse URI
        if uri_str.startswith("memory://"):
            path = uri_str[9:]  # Remove "memory://" prefix

            # Handle type queries
            if path.startswith("type/"):
                memory_type = path[5:]
                memories = await db.list_memories(memory_type=memory_type, limit=50)
                return json.dumps(
                    {"type": memory_type, "count": len(memories), "memories": memories}
                )

            # Handle tag queries
            if path.startswith("tag/"):
                tag = path[4:]
                memories = await db.search_memories(query=None, tags=[tag], limit=50)
                return json.dumps(
                    {"tag": tag, "count": len(memories), "memories": memories}
                )

            # Handle specific memory
            memory = await db.get_memory_by_name(path)
            if memory is None:
                raise ValueError(f"Memory not found: {path}")

            return json.dumps(memory, default=str)

        raise ValueError(f"Unknown resource URI: {uri}")

    @server.list_prompts()
    async def list_prompts() -> list[Prompt]:
        """Return list of available prompts."""
        return PROMPTS

    @server.get_prompt()
    async def get_prompt(
        name: str, arguments: dict[str, str] | None = None
    ) -> GetPromptResult:
        """Return prompt messages for a specific prompt."""
        args = arguments or {}
        context_banner = await _build_prompt_context_banner()
        if name == "memory-workflow":
            task = (
                args.get("task_description")
                or "the task (infer from the user's message)"
            )
            return GetPromptResult(
                messages=[
                    PromptMessage(
                        role="user",
                        content=TextContent(
                            type="text",
                            text=f"""{context_banner}

Follow this workflow for: {task}

1. **SEARCH**: Before starting, search for prior context:
   ```
   axom_mcp_memory(action="search", query="relevant keywords")
   ```
   - If `has_reflex: true`: implement from reflex, verify (run e.g. `make test`, `pytest path/to/test.py`). If verify fails: edit reflex or associate gotcha, then escalate.
   - If thin: search `memory_type="dreams"`; web fallback runs automatically.
   - Use `reflection_excerpt` in results to re-think.

2. **DISCOVER** (before acting): `axom_mcp_discover(domain="all")` to map environment.

3. **EXECUTE**: Perform the task. Use `chain` for 3+ sequential steps. Example: read→analyze→store:
   ```
   axom_mcp_exec(operation="read", target="file.py", chain=[
     {{"tool": "axom_mcp_analyze", "args": {{"type": "review", "target": "${{_result}}"}}}},
     {{"tool": "axom_mcp_memory", "args": {{"action": "write", "name": "review_file_YYYYMMDD", "content": "${{_result}}"}}}}
   ])
   ```

4. **VERIFY**: Before claiming done, run the verification command (e.g. `make test`, `pytest path/to/test.py`). Evidence before claims.

5. **STORE**: After completion, store key insights with REFLECTION:
   ```
   axom_mcp_memory(
       action="write",
       name="[type]_[descriptor]_[YYYYMMDD]",
       content="TASK|APPROACH|OUTCOME|GOTCHAS|REFLECTION: ...|RELATED",
       memory_type="long_term",
       importance="high",
       tags=["relevant", "tags"]
   )
   ```

Memory Types:
- long_term: Reusable patterns, decisions
- short_term: Task-specific context
- reflex: Learned heuristics
- dreams: Experimental ideas

Failure to search creates duplicate work; failure to store loses institutional knowledge.""",
                        ),
                    ),
                ],
            )

        elif name == "debug-session":
            error = (
                args.get("error_description")
                or "the error (infer from the user's message)"
            )
            context = (
                args.get("context")
                or "relevant context (infer from the user's message)"
            )
            return GetPromptResult(
                messages=[
                    PromptMessage(
                        role="user",
                        content=TextContent(
                            type="text",
                            text=f"""Start a structured debugging session for:

**Error:** {error}
**Context:** {context}

{context_banner}

Follow these steps:

1. **Search for similar issues:**
   ```
   axom_mcp_memory(action="search", query="error {error}")
   ```
   If `has_reflex: true`: implement from reflex, verify, update on failure.

2. **Discover** files: `axom_mcp_discover(domain="files", filter={{"pattern": "*.py"}})`

3. **Read → Analyze → Store** (chain when you have the file path):
   ```
   axom_mcp_exec(operation="read", target="relevant_file.py", chain=[
     {{"tool": "axom_mcp_analyze", "args": {{"type": "debug", "target": "${{_result}}", "focus": "error"}}}},
     {{"tool": "axom_mcp_memory", "args": {{"action": "write", "name": "debug_issue_YYYYMMDD", "content": "ERROR|INVESTIGATION|${{_result}}"}}}}
   ])
   ```

4. **Verify** before claiming done: run e.g. `make test`, `pytest path/to/test.py`.

5. **Document findings** (if not already stored via chain):
   ```
   axom_mcp_memory(
       action="write",
       name="debug_[issue]_[YYYYMMDD]",
       content="ERROR|INVESTIGATION|ROOT_CAUSE|FIX|PREVENTION",
       memory_type="short_term",
       tags=["debug", "error"]
   )
   ```

6. **If resolved, promote to reflex:**
   ```
   axom_mcp_memory(
       action="write",
       name="reflex_[pattern]_[YYYYMMDD]",
       content="TRIGGER|DIAGNOSIS|SOLUTION",
       memory_type="reflex",
       importance="high"
   )
   ```""",
                        ),
                    ),
                ],
            )

        elif name == "code-review":
            target = (
                args.get("target_path")
                or "the target (infer path from the user's message)"
            )
            focus = (
                args.get("focus_area")
                or "focus area (infer from the user's message, or general quality)"
            )
            return GetPromptResult(
                messages=[
                    PromptMessage(
                        role="user",
                        content=TextContent(
                            type="text",
                            text=f"""Perform a code review of: {target}

Focus area: {focus}

Steps:

1. **Discover** the codebase: `axom_mcp_discover(domain="files", filter={{"pattern": "*.py"}}, recursive=true)`

2. **Read → Analyze → Store** (chain when possible):
   ```
   axom_mcp_exec(operation="read", target="{target}", chain=[
     {{"tool": "axom_mcp_analyze", "args": {{"type": "review", "target": "${{_result}}", "focus": "{focus}", "depth": "high", "output_format": "detailed"}}}},
     {{"tool": "axom_mcp_memory", "args": {{"action": "write", "name": "review_component_YYYYMMDD", "content": "COMPONENT|ISSUES|RECOMMENDATIONS|${{_result}}", "memory_type": "short_term", "tags": ["review", "{focus}"]}}}}
   ])
   ```

3. **If critical issues found, create reflex:**
   ```
   axom_mcp_memory(
       action="write",
       name="reflex_avoid_[pattern]_[YYYYMMDD]",
       content="ANTI_PATTERN|WHY_BAD|ALTERNATIVE",
       memory_type="reflex",
       importance="high"
   )
   ```""",
                        ),
                    ),
                ],
            )

        elif name == "systematic-debug":
            error = (
                args.get("error_description")
                or "the error (infer from the user's message)"
            )
            context = (
                args.get("context")
                or "relevant context (infer from the user's message)"
            )
            return GetPromptResult(
                messages=[
                    PromptMessage(
                        role="user",
                        content=TextContent(
                            type="text",
                            text=f"""Systematic debugging for: {error}
Context: {context}

{context_banner}

**NO FIXES without Phase 1.** Follow strictly:

**Phase 1: Root cause**
- Reproduce the error. What exactly fails?
- Search memory: axom_mcp_memory(action="search", query="error {error}")
- Discover relevant files: axom_mcp_discover(domain="files")
- Analyze: axom_mcp_analyze(type="debug", target="file.py", focus="root cause")
- Document: What is the actual root cause? (Not symptoms.)

**Phase 2: Pattern**
- Is this a known pattern? Check reflex/dreams in search results.
- What similar issues exist in memory?

**Phase 3: Hypothesis**
- Form a hypothesis: "If we change X, then Y should fix it."
- One hypothesis at a time. Test before next.

**Phase 4: Fix**
- Only after Phases 1–3 are complete.
- Implement fix. Verify: run e.g. make test, pytest path/to/test.py
- Store with REFLECTION: axom_mcp_memory(action="write", ...)""",
                        ),
                    ),
                ],
            )

        elif name == "complex-problem":
            topic = args.get("topic") or "the problem (infer from the user's message)"
            return GetPromptResult(
                messages=[
                    PromptMessage(
                        role="user",
                        content=TextContent(
                            type="text",
                            text=f"""Complex problem: {topic}

1. **Dispatch subagent first** (runs in parallel). Pass docs/agents/subagent/axom-agent.md as context.
   Prompt: "Gather context for {topic}. Return context envelope."
   Use mcp_task with attachments: [docs/agents/subagent/axom-agent.md]

2. **Main agent:** discover, read, analyze while subagent runs.

3. **At combine step:** Wait for subagent (timeout ~60-120s). If timeout, proceed with partial context.

4. **Combine** memory_hits + dreams + web_snippets + distilled_summary. Synthesize solution.

5. **Store** with REFLECTION.""",
                        ),
                    ),
                ],
            )

        elif name == "store-pattern":
            pattern_name = args.get("pattern_name") or "[infer from user message]"
            description = args.get("description") or "[infer from user message]"
            code_example = args.get("code_example") or ""
            name_slug = (
                pattern_name.replace(" ", "_").replace("[", "").replace("]", "")
                if pattern_name != "[infer from user message]"
                else "inferred_name"
            )
            return GetPromptResult(
                messages=[
                    PromptMessage(
                        role="user",
                        content=TextContent(
                            type="text",
                            text=f"""Store this pattern for future reference. Infer name and description from the user's message if not provided.

**Name:** {pattern_name}
**Description:** {description}
**Code Example:** {code_example if code_example else "N/A"}

Store as a long-term memory:
```
axom_mcp_memory(
    action="write",
    name="pattern_{name_slug}_[YYYYMMDD]",
    content="NAME|PROBLEM|SOLUTION|WHEN_TO_USE|WHEN_NOT_TO_USE|EXAMPLE|REFLECTION: ...",
    memory_type="long_term",
    importance="high",
    tags=["pattern", "best-practice"]
)
```

Before claiming done: run verification command (e.g. `make test`, `pytest path/to/test.py`). Evidence before claims.

This pattern will be discoverable by future agents working on similar problems.""",
                        ),
                    ),
                ],
            )

        raise ValueError(f"Unknown prompt: {name}")

    return server


async def run_server() -> None:
    """Run the MCP server with stdio transport."""
    server = create_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream, write_stream, server.create_initialization_options()
        )


def main() -> None:
    """CLI entry point."""
    asyncio.run(run_server())


if __name__ == "__main__":
    main()
