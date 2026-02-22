"""Discover tool handler for Axom MCP.

This module handles discovery operations:
- files: List and search files in allowed directories
- tools: List available MCP tools and their capabilities
- memory: Explore memory structure and statistics
- capabilities: Check server capabilities and configuration
- all: Comprehensive discovery across all domains
"""

from __future__ import annotations

import fnmatch
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict

from ..database import get_db_manager
from ..schemas import DiscoverInput

logger = logging.getLogger(__name__)


def _validate_path(target: str) -> Path:
    """Validate path is within allowed directories."""
    path = Path(target).resolve()

    allowed_bases = [
        Path(os.getcwd()).resolve(),
        Path.home(),
    ]

    for base in allowed_bases:
        try:
            path.relative_to(base)
            return path
        except ValueError:
            continue

    raise ValueError(f"Path {target} is outside allowed directories")


async def handle_discover(arguments: Dict[str, Any]) -> str:
    """Handle axom_mcp_discover tool calls.

    Args:
        arguments: Tool arguments containing domain and parameters

    Returns:
        JSON string with discovery result
    """
    # Validate input
    input_data = DiscoverInput(**arguments)
    domain = input_data.domain
    filter_criteria = input_data.filter or {}
    limit = input_data.limit or 100
    recursive = input_data.recursive if input_data.recursive is not None else True

    try:
        if domain == "files":
            return await _discover_files(filter_criteria, limit, recursive)
        elif domain == "tools":
            return await _discover_tools()
        elif domain == "memory":
            return await _discover_memory(limit)
        elif domain == "capabilities":
            return await _discover_capabilities()
        elif domain == "all":
            return await _discover_all(filter_criteria, limit, recursive)
        else:
            return json.dumps({"error": f"Unknown domain: {domain}"})
    except Exception as e:
        logger.error(f"Discovery failed: {e}")
        return json.dumps({"error": str(e)})


async def _discover_files(
    filter_criteria: Dict[str, Any], limit: int, recursive: bool
) -> str:
    """Discover files in allowed directories."""
    results = []
    pattern = filter_criteria.get("pattern", "*")
    file_type = filter_criteria.get("type", "all")  # file, directory, all
    base_path = filter_criteria.get("path", os.getcwd())

    try:
        base = _validate_path(base_path)
    except ValueError:
        base = Path(os.getcwd()).resolve()

    if not base.exists():
        return json.dumps({"error": f"Path not found: {base_path}"})

    def should_include(path: Path) -> bool:
        """Check if path matches filter criteria."""
        # Check pattern
        if not fnmatch.fnmatch(path.name, pattern):
            return False

        # Check type
        if file_type == "file" and not path.is_file():
            return False
        if file_type == "directory" and not path.is_dir():
            return False

        return True

    try:
        if recursive:
            for path in base.rglob("*"):
                if len(results) >= limit:
                    break
                if should_include(path):
                    results.append(
                        {
                            "name": path.name,
                            "path": str(path),
                            "relative_path": str(path.relative_to(base)),
                            "type": "file" if path.is_file() else "directory",
                            "size": path.stat().st_size if path.is_file() else None,
                        }
                    )
        else:
            for path in base.iterdir():
                if len(results) >= limit:
                    break
                if should_include(path):
                    results.append(
                        {
                            "name": path.name,
                            "path": str(path),
                            "relative_path": str(path.relative_to(base)),
                            "type": "file" if path.is_file() else "directory",
                            "size": path.stat().st_size if path.is_file() else None,
                        }
                    )
    except PermissionError:
        pass  # Skip directories we can't access

    # Sort results for deterministic output
    results.sort(key=lambda x: (x["type"], x["name"]))

    return json.dumps(
        {
            "success": True,
            "domain": "files",
            "base_path": str(base),
            "count": len(results),
            "results": results,
        }
    )


async def _discover_tools() -> str:
    """Discover available MCP tools."""
    tools = [
        {
            "name": "axom_mcp_memory",
            "description": "Store, retrieve, search, and manage persistent memories in the Axom database",
            "actions": ["read", "write", "list", "search", "delete"],
            "parameters": {
                "action": {
                    "type": "string",
                    "required": True,
                    "enum": ["read", "write", "list", "search", "delete"],
                },
                "name": {
                    "type": "string",
                    "required": False,
                    "description": "Memory identifier",
                },
                "content": {
                    "type": "string",
                    "required": False,
                    "description": "Memory content",
                },
                "query": {
                    "type": "string",
                    "required": False,
                    "description": "Search query",
                },
                "memory_type": {
                    "type": "string",
                    "enum": ["long_term", "short_term", "reflex", "dreams"],
                },
                "importance": {
                    "type": "string",
                    "enum": ["critical", "important", "normal", "low"],
                },
                "tags": {"type": "array", "items": {"type": "string"}},
                "limit": {"type": "integer", "default": 50},
            },
        },
        {
            "name": "axom_mcp_exec",
            "description": "Execute file operations and shell commands with chain-reaction support",
            "operations": ["read", "write", "shell"],
            "parameters": {
                "operation": {
                    "type": "string",
                    "required": True,
                    "enum": ["read", "write", "shell"],
                },
                "target": {
                    "type": "string",
                    "required": True,
                    "description": "File path or command",
                },
                "data": {
                    "type": "string",
                    "required": False,
                    "description": "Data to write",
                },
                "chain": {
                    "type": "array",
                    "description": "Chain of subsequent operations",
                },
            },
        },
        {
            "name": "axom_mcp_analyze",
            "description": "Analyze code and data with configurable depth and scope",
            "types": ["debug", "review", "audit", "refactor", "test"],
            "parameters": {
                "type": {
                    "type": "string",
                    "required": True,
                    "enum": ["debug", "review", "audit", "refactor", "test"],
                },
                "target": {
                    "type": "string",
                    "required": True,
                    "description": "File path or code to analyze",
                },
                "focus": {
                    "type": "string",
                    "description": "Focus area (e.g., security, performance)",
                },
                "depth": {
                    "type": "string",
                    "enum": ["minimal", "low", "medium", "high", "max"],
                    "default": "medium",
                },
                "output_format": {
                    "type": "string",
                    "enum": ["summary", "detailed", "actionable"],
                    "default": "summary",
                },
            },
        },
        {
            "name": "axom_mcp_discover",
            "description": "Discover available resources, structures, and capabilities",
            "domains": ["files", "tools", "memory", "capabilities", "all"],
            "parameters": {
                "domain": {
                    "type": "string",
                    "required": True,
                    "enum": ["files", "tools", "memory", "capabilities", "all"],
                },
                "filter": {"type": "object", "description": "Filter criteria"},
                "limit": {"type": "integer", "default": 100},
                "recursive": {"type": "boolean", "default": True},
            },
        },
        {
            "name": "axom_mcp_transform",
            "description": "Transform data between formats and structures",
            "formats": ["json", "yaml", "csv", "markdown", "code"],
            "parameters": {
                "input": {
                    "type": "string",
                    "required": True,
                    "description": "Input data to transform",
                },
                "input_format": {
                    "type": "string",
                    "enum": ["json", "yaml", "csv", "markdown", "code"],
                },
                "output_format": {
                    "type": "string",
                    "required": True,
                    "enum": ["json", "yaml", "csv", "markdown", "code"],
                },
                "rules": {"type": "array", "description": "Transformation rules"},
                "template": {
                    "type": "string",
                    "description": "Template for transformation",
                },
            },
        },
    ]

    return json.dumps(
        {
            "success": True,
            "domain": "tools",
            "count": len(tools),
            "results": tools,
        }
    )


async def _discover_memory(limit: int) -> str:
    """Discover memory statistics and structure."""
    try:
        db = await get_db_manager()
        stats = await db.get_memory_stats()

        # Get recent memories
        recent = await db.list_memories(limit=min(limit, 20))

        return json.dumps(
            {
                "success": True,
                "domain": "memory",
                "statistics": stats,
                "recent_memories": [
                    {
                        "name": m.get("name"),
                        "type": m.get("memory_type"),
                        "importance": m.get("importance"),
                        "created_at": (
                            m.get("created_at").isoformat()
                            if m.get("created_at")
                            else None
                        ),
                    }
                    for m in recent
                ],
            }
        )
    except Exception as e:
        return json.dumps(
            {
                "success": False,
                "domain": "memory",
                "error": str(e),
                "message": "Database not available. Check database configuration.",
            }
        )


async def _discover_capabilities() -> str:
    """Discover server capabilities and configuration."""
    capabilities = {
        "server": {
            "name": "axom",
            "version": "2.0.0",
            "description": "MCP server providing AI agents with persistent memory, tool abstraction, and chain-reaction capabilities",
        },
        "features": {
            "memory": {
                "available": True,
                "types": ["long_term", "short_term", "reflex", "dreams"],
                "importance_levels": ["critical", "important", "normal", "low"],
                "max_content_size": 1000000,
            },
            "exec": {
                "available": True,
                "operations": ["read", "write", "shell"],
                "write_enabled": not _env_flag_enabled("AXOM_READ_ONLY", default=False),
                "max_file_size": 10000000,
            },
            "analyze": {
                "available": True,
                "types": ["debug", "review", "audit", "refactor", "test"],
                "depth_levels": ["minimal", "low", "medium", "high", "max"],
            },
            "discover": {
                "available": True,
                "domains": ["files", "tools", "memory", "capabilities", "all"],
            },
            "transform": {
                "available": True,
                "formats": ["json", "yaml", "csv", "markdown", "code"],
            },
        },
        "security": {
            "allowed_directories": [
                os.getcwd(),
                str(Path.home()),
            ],
            "write_operations": not _env_flag_enabled("AXOM_READ_ONLY", default=False),
        },
    }

    return json.dumps(
        {
            "success": True,
            "domain": "capabilities",
            "results": capabilities,
        }
    )


async def _discover_all(
    filter_criteria: Dict[str, Any], limit: int, recursive: bool
) -> str:
    """Comprehensive discovery across all domains."""
    results = {}

    # Discover tools
    tools_result = await _discover_tools()
    results["tools"] = json.loads(tools_result)

    # Discover capabilities
    capabilities_result = await _discover_capabilities()
    results["capabilities"] = json.loads(capabilities_result)

    # Discover memory
    memory_result = await _discover_memory(limit)
    results["memory"] = json.loads(memory_result)

    # Discover files (limited)
    files_result = await _discover_files(filter_criteria, min(limit, 50), recursive)
    results["files"] = json.loads(files_result)

    return json.dumps(
        {
            "success": True,
            "domain": "all",
            "results": results,
        }
    )


def _env_flag_enabled(name: str, default: bool = False) -> bool:
    """Return True if env var is set to a truthy value."""
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}
