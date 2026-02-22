"""Axom MCP Server - Main entry point.

This module provides the main MCP server implementation using the official
MCP Python SDK with @mcp.tool() decorator for tool registration.
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any, Dict, List

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
    Resource,
    ResourceTemplate,
    Prompt,
    PromptArgument,
    PromptMessage,
)

from .database import get_db_manager, close_db_manager
from .handlers import (
    handle_memory,
    handle_exec,
    handle_analyze,
    handle_discover,
    handle_transform,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

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
- search: Full-text search across memories
- delete: Remove a memory by name""",
        inputSchema={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["read", "write", "list", "search", "delete"],
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
                    "enum": ["critical", "important", "normal", "low"],
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
        annotations=TOOL_ANNOTATIONS["memory"],
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
        annotations=TOOL_ANNOTATIONS["exec"],
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
        annotations=TOOL_ANNOTATIONS["analyze"],
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
        annotations=TOOL_ANNOTATIONS["discover"],
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
        annotations=TOOL_ANNOTATIONS["transform"],
    ),
]

# Prompts
PROMPTS = [
    Prompt(
        name="memory-workflow",
        description="Standard workflow for memory-driven task execution. Use at the start of every task.",
        arguments=[
            PromptArgument(
                name="task_description",
                description="Description of the task to perform",
                required=True,
            ),
        ],
    ),
    Prompt(
        name="debug-session",
        description="Start a structured debugging session with memory persistence.",
        arguments=[
            PromptArgument(
                name="error_description",
                description="Description of the error or issue",
                required=True,
            ),
            PromptArgument(
                name="context",
                description="Additional context (file paths, logs, etc.)",
                required=False,
            ),
        ],
    ),
    Prompt(
        name="code-review",
        description="Perform a comprehensive code review and store findings.",
        arguments=[
            PromptArgument(
                name="target_path",
                description="Path to the file or directory to review",
                required=True,
            ),
            PromptArgument(
                name="focus_area",
                description="Specific focus area (security, performance, etc.)",
                required=False,
            ),
        ],
    ),
    Prompt(
        name="store-pattern",
        description="Store a discovered pattern or best practice for future reference.",
        arguments=[
            PromptArgument(
                name="pattern_name",
                description="Name for the pattern",
                required=True,
            ),
            PromptArgument(
                name="description",
                description="Description of the pattern",
                required=True,
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
async def server_lifespan(server: Server):
    """Manage server startup and shutdown."""
    # Startup: Initialize database connection
    try:
        await get_db_manager()
        logger.info("Database connection established")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        logger.error("Axom MCP requires PostgreSQL. Configure .env with database settings.")
        raise

    yield

    # Shutdown: Close database connection
    await close_db_manager()
    logger.info("Database connection closed")


def create_server() -> Server:
    """Create and configure the MCP server."""
    server = Server(
        name="axom",
        version="2.0.0",
    )

    @server.list_tools()
    async def list_tools() -> List[Tool]:
        """Return list of available tools."""
        return TOOLS

    @server.call_tool()
    async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
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

            return [TextContent(type="text", text=result)]
        except Exception as e:
            logger.error(f"Tool call failed: {name} - {e}")
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    @server.list_resources()
    async def list_resources() -> List[Resource]:
        """List all available memory resources."""
        try:
            db = await get_db_manager()
            memories = await db.list_memories(limit=100)

            return [
                Resource(
                    uri=f"memory://{m['name']}",
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
    async def list_resource_templates() -> List[ResourceTemplate]:
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

        # Parse URI
        if uri.startswith("memory://"):
            path = uri[9:]  # Remove "memory://" prefix

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
                memories = await db.search_memories(tags=[tag], limit=50)
                return json.dumps({"tag": tag, "count": len(memories), "memories": memories})

            # Handle specific memory
            memory = await db.get_memory_by_name(path)
            if memory is None:
                raise ValueError(f"Memory not found: {path}")

            return json.dumps(memory, default=str)

        raise ValueError(f"Unknown resource URI: {uri}")

    @server.list_prompts()
    async def list_prompts() -> List[Prompt]:
        """Return list of available prompts."""
        return PROMPTS

    @server.get_prompt()
    async def get_prompt(name: str, arguments: Dict[str, Any]) -> List[PromptMessage]:
        """Return prompt messages for a specific prompt."""
        if name == "memory-workflow":
            task = arguments.get("task_description", "the task")
            return [
                PromptMessage(
                    role="user",
                    content=TextContent(
                        type="text",
                        text=f"""Follow this workflow for: {task}

1. **SEARCH**: Before starting, search for prior context:
   ```
   axom_mcp_memory(action="search", query="relevant keywords")
   ```

2. **EXECUTE**: Perform the task using available tools.

3. **STORE**: After completion, store key insights:
   ```
   axom_mcp_memory(
       action="write",
       name="[type]_[descriptor]_[YYYYMMDD]",
       content="TASK|APPROACH|OUTCOME|GOTCHAS|RELATED",
       memory_type="long_term",
       importance="important",
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
            ]

        elif name == "debug-session":
            error = arguments.get("error_description", "unknown error")
            context = arguments.get("context", "no additional context")
            return [
                PromptMessage(
                    role="user",
                    content=TextContent(
                        type="text",
                        text=f"""Start a structured debugging session for:

**Error:** {error}
**Context:** {context}

Follow these steps:

1. **Search for similar issues:**
   ```
   axom_mcp_memory(action="search", query="error {error}")
   ```

2. **Analyze the code:**
   ```
   axom_mcp_analyze(type="debug", target="relevant_file.py", focus="error")
   ```

3. **Document findings:**
   ```
   axom_mcp_memory(
       action="write",
       name="debug_[issue]_[YYYYMMDD]",
       content="ERROR|INVESTIGATION|ROOT_CAUSE|FIX|PREVENTION",
       memory_type="short_term",
       tags=["debug", "error"]
   )
   ```

4. **If resolved, promote to reflex:**
   ```
   axom_mcp_memory(
       action="write",
       name="reflex_[pattern]_[YYYYMMDD]",
       content="TRIGGER|DIAGNOSIS|SOLUTION",
       memory_type="reflex",
       importance="important"
   )
   ```""",
                    ),
                ),
            ]

        elif name == "code-review":
            target = arguments.get("target_path", "the code")
            focus = arguments.get("focus_area", "general quality")
            return [
                PromptMessage(
                    role="user",
                    content=TextContent(
                        type="text",
                        text=f"""Perform a code review of: {target}

Focus area: {focus}

Steps:

1. **Discover the codebase:**
   ```
   axom_mcp_discover(domain="files", filter={{"pattern": "*.py"}}, recursive=true)
   ```

2. **Analyze the code:**
   ```
   axom_mcp_analyze(
       type="review",
       target="{target}",
       focus="{focus}",
       depth="high",
       output_format="detailed"
   )
   ```

3. **Store review findings:**
   ```
   axom_mcp_memory(
       action="write",
       name="review_[component]_[YYYYMMDD]",
       content="COMPONENT|ISSUES|RECOMMENDATIONS|PRIORITY",
       memory_type="short_term",
       tags=["review", "{focus}"]
   )
   ```

4. **If critical issues found, create reflex:**
   ```
   axom_mcp_memory(
       action="write",
       name="reflex_avoid_[pattern]_[YYYYMMDD]",
       content="ANTI_PATTERN|WHY_BAD|ALTERNATIVE",
       memory_type="reflex",
       importance="important"
   )
   ```""",
                    ),
                ),
            ]

        elif name == "store-pattern":
            pattern_name = arguments.get("pattern_name", "unnamed")
            description = arguments.get("description", "")
            code_example = arguments.get("code_example", "")
            return [
                PromptMessage(
                    role="user",
                    content=TextContent(
                        type="text",
                        text=f"""Store this pattern for future reference:

**Name:** {pattern_name}
**Description:** {description}
**Code Example:** {code_example if code_example else "N/A"}

Store as a long-term memory:
```
axom_mcp_memory(
    action="write",
    name="pattern_{pattern_name.replace(" ", "_")}_[YYYYMMDD]",
    content="NAME|PROBLEM|SOLUTION|WHEN_TO_USE|WHEN_NOT_TO_USE|EXAMPLE",
    memory_type="long_term",
    importance="important",
    tags=["pattern", "best-practice"]
)
```

This pattern will be discoverable by future agents working on similar problems.""",
                    ),
                ),
            ]

        raise ValueError(f"Unknown prompt: {name}")

    return server


async def run_server():
    """Run the MCP server with stdio transport."""
    server = create_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main():
    """CLI entry point."""
    asyncio.run(run_server())


if __name__ == "__main__":
    main()
