"""Axom MCP - Persistent Memory for AI Agents.

Axom is a Model Context Protocol (MCP) server that provides AI agents with:
- Persistent memory via the Axom database
- Tool abstraction for file operations and shell commands
- Chain-reaction capabilities for complex workflows

Usage:
    # Run the MCP server
    axom-mcp

    # Or programmatically
    from axom_mcp import create_server
    server = create_server()
"""

__version__ = "2.0.0"
__author__ = "CNS Team"

from .server import create_server, main, run_server

__all__ = ["create_server", "main", "run_server", "__version__"]
