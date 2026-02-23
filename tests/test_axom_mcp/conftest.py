"""Shared pytest fixtures for Axom MCP tests.

This module provides fixtures for testing the Axom MCP server components.
"""

import asyncio
import json
import os
import tempfile
from datetime import datetime, timedelta
from typing import Any, Dict, List
from unittest.mock import AsyncMock

import aiosqlite
import pytest

# ============================================================================
# Event Loop Fixture
# ============================================================================


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Database Fixtures
# ============================================================================


@pytest.fixture
def mock_connection():
    """Create a mock aiosqlite database connection."""
    from contextlib import asynccontextmanager

    conn = AsyncMock()

    # Create a mock cursor for async context manager
    mock_cursor = AsyncMock()
    mock_cursor.fetchone = AsyncMock(return_value=None)
    mock_cursor.fetchall = AsyncMock(return_value=[])
    mock_cursor.rowcount = 0

    # Mock the execute method to return an async context manager
    @asynccontextmanager
    async def mock_execute(query, params=None):
        """Mock execute that returns an async context manager."""
        yield mock_cursor

    conn.execute = mock_execute
    conn.commit = AsyncMock(return_value=None)
    conn.rollback = AsyncMock(return_value=None)
    conn.close = AsyncMock(return_value=None)
    conn.row_factory = None

    return conn


@pytest.fixture
def mock_db_manager(mock_connection):
    """Create a mock DatabaseManager instance."""
    from axom_mcp.database import DatabaseManager

    manager = DatabaseManager(":memory:")
    manager.conn = mock_connection

    return manager


@pytest.fixture
async def sqlite_db():
    """Create an in-memory SQLite database for fast tests."""

    db = await aiosqlite.connect(":memory:")
    db.row_factory = aiosqlite.Row

    # Create tables
    await db.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id TEXT PRIMARY KEY,
            memory_type TEXT NOT NULL CHECK(memory_type IN ('short_term', 'long_term', 'reflex', 'dreams')),
            importance TEXT NOT NULL DEFAULT 'high' CHECK(importance IN ('critical', 'high', 'low')),
            name TEXT,
            content TEXT NOT NULL,
            summary TEXT,
            tags TEXT,
            source_agent TEXT,
            source_context TEXT,
            source_tool TEXT,
            parent_memory_id TEXT,
            associated_memories TEXT,
            created_at TEXT,
            updated_at TEXT,
            accessed_at TEXT,
            expires_at TEXT,
            access_count INTEGER DEFAULT 0,
            last_accessed_at TEXT,
            metadata TEXT DEFAULT '{}'
        )
    """)

    await db.execute("""
        CREATE TABLE IF NOT EXISTS memory_access_log (
            id TEXT PRIMARY KEY,
            memory_id TEXT NOT NULL,
            accessed_by TEXT,
            access_type TEXT,
            context TEXT,
            created_at TEXT
        )
    """)

    await db.commit()
    yield db
    await db.close()


@pytest.fixture
def sample_memory_data() -> Dict[str, Any]:
    """Sample memory data for testing."""
    return {
        "id": "12345678-1234-1234-1234-123456789abc",
        "name": "pattern_test_20260215",
        "memory_type": "long_term",
        "importance": "high",
        "content": "TASK|Test task|APPROACH|Test approach|OUTCOME|Success|GOTCHAS|None|RELATED|test",
        "summary": "Test memory summary",
        "tags": ["test", "example", "pytest"],
        "source_agent": "test-agent",
        "source_context": "pytest",
        "source_tool": "axom_mcp_memory",
        "metadata": {"key": "value"},
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "accessed_at": datetime.utcnow(),
        "expires_at": datetime.utcnow() + timedelta(days=30),
        "access_count": 0,
    }


@pytest.fixture
def sample_memory_record(sample_memory_data) -> Dict[str, Any]:
    """Sample memory record as returned from database."""
    record = sample_memory_data.copy()
    # Convert datetime to string format as returned by aiosqlite
    record["created_at"] = record["created_at"].isoformat()
    record["updated_at"] = record["updated_at"].isoformat()
    record["accessed_at"] = record["accessed_at"].isoformat()
    record["expires_at"] = record["expires_at"].isoformat()
    # Add JSON-serialized fields for SQLite
    record["tags"] = json.dumps(record["tags"])
    record["metadata"] = json.dumps(record["metadata"])
    return record


@pytest.fixture
def sample_memories_list() -> List[Dict[str, Any]]:
    """List of sample memories for list/search tests."""
    return [
        {
            "id": "uuid-1",
            "name": "pattern_api_20260201",
            "memory_type": "long_term",
            "importance": "high",
            "content": "API pattern for REST endpoints",
            "tags": ["api", "rest"],
            "created_at": "2026-02-01T10:00:00",
        },
        {
            "id": "uuid-2",
            "name": "bugfix_auth_20260210",
            "memory_type": "short_term",
            "importance": "low",
            "content": "Fixed authentication timeout issue",
            "tags": ["bugfix", "auth"],
            "created_at": "2026-02-10T15:30:00",
        },
        {
            "id": "uuid-3",
            "name": "refactor_db_20260215",
            "memory_type": "long_term",
            "importance": "critical",
            "content": "Database refactoring for performance",
            "tags": ["refactor", "database", "performance"],
            "created_at": "2026-02-15T09:00:00",
        },
    ]


# ============================================================================
# File System Fixtures
# ============================================================================


@pytest.fixture
def temp_directory():
    """Create a temporary directory for file operations tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def temp_file(temp_directory):
    """Create a temporary file with test content."""
    file_path = os.path.join(temp_directory, "test_file.txt")
    with open(file_path, "w") as f:
        f.write("Test file content\nLine 2\nLine 3")
    yield file_path


@pytest.fixture
def temp_json_file(temp_directory):
    """Create a temporary JSON file."""
    import json

    file_path = os.path.join(temp_directory, "test.json")
    content = {"key": "value", "nested": {"item": 1, "list": [1, 2, 3]}}
    with open(file_path, "w") as f:
        json.dump(content, f)
    yield file_path, content


@pytest.fixture
def temp_yaml_file(temp_directory):
    """Create a temporary YAML file."""
    file_path = os.path.join(temp_directory, "test.yaml")
    content = "key: value\nnested:\n  item: 1\n  list:\n    - 1\n    - 2\n    - 3\n"
    with open(file_path, "w") as f:
        f.write(content)
    yield file_path, content


@pytest.fixture
def temp_csv_file(temp_directory):
    """Create a temporary CSV file."""
    file_path = os.path.join(temp_directory, "test.csv")
    content = "name,age,city\nAlice,30,NYC\nBob,25,LA\nCharlie,35,Chicago\n"
    with open(file_path, "w") as f:
        f.write(content)
    yield file_path, content


@pytest.fixture
def temp_python_file(temp_directory):
    """Create a temporary Python file for analysis tests."""
    file_path = os.path.join(temp_directory, "test_module.py")
    content = '''
"""Sample Python module for testing."""

import os
import sys

# Global variable
DEBUG = True

def hello(name: str) -> str:
    """Return a greeting."""
    return f"Hello, {name}!"

def broken_function():
    """This function has issues."""
    # TODO: Fix this
    x = undefined_var  # This will cause an error
    return x

class TestClass:
    """A test class."""

    def __init__(self, value):
        self.value = value

    def get_value(self):
        return self.value

# Main block
if __name__ == "__main__":
    print(hello("World"))
'''
    with open(file_path, "w") as f:
        f.write(content)
    yield file_path, content


# ============================================================================
# Handler Input Fixtures
# ============================================================================


@pytest.fixture
def memory_write_input() -> Dict[str, Any]:
    """Valid input for memory write action."""
    return {
        "action": "write",
        "name": "test_memory_20260215",
        "content": "Test memory content with TASK|APPROACH|OUTCOME format",
        "memory_type": "long_term",
        "importance": "high",
        "tags": ["test", "pytest"],
        "source_agent": "test-runner",
    }


@pytest.fixture
def memory_search_input() -> Dict[str, Any]:
    """Valid input for memory search action."""
    return {
        "action": "search",
        "query": "test query",
        "memory_type": "long_term",
        "limit": 10,
    }


@pytest.fixture
def memory_read_input() -> Dict[str, Any]:
    """Valid input for memory read action."""
    return {
        "action": "read",
        "name": "test_memory_20260215",
    }


@pytest.fixture
def memory_list_input() -> Dict[str, Any]:
    """Valid input for memory list action."""
    return {
        "action": "list",
        "memory_type": "long_term",
        "importance": "high",
        "limit": 50,
    }


@pytest.fixture
def memory_delete_input() -> Dict[str, Any]:
    """Valid input for memory delete action."""
    return {
        "action": "delete",
        "name": "test_memory_20260215",
    }


@pytest.fixture
def exec_read_input(temp_file) -> Dict[str, Any]:
    """Valid input for exec read operation."""
    return {
        "operation": "read",
        "target": temp_file,
    }


@pytest.fixture
def exec_write_input(temp_directory) -> Dict[str, Any]:
    """Valid input for exec write operation."""
    return {
        "operation": "write",
        "target": os.path.join(temp_directory, "output.txt"),
        "data": "Written content from test",
    }


@pytest.fixture
def exec_shell_input() -> Dict[str, Any]:
    """Valid input for exec shell operation."""
    return {
        "operation": "shell",
        "target": "echo 'Hello from test'",
    }


@pytest.fixture
def analyze_debug_input(temp_python_file) -> Dict[str, Any]:
    """Valid input for analyze debug action."""
    return {
        "type": "debug",
        "target": temp_python_file[0],
        "depth": "medium",
    }


@pytest.fixture
def analyze_review_input(temp_python_file) -> Dict[str, Any]:
    """Valid input for analyze review action."""
    return {
        "type": "review",
        "target": temp_python_file[0],
        "depth": "low",
        "output_format": "summary",
    }


@pytest.fixture
def discover_tools_input() -> Dict[str, Any]:
    """Valid input for discover tools domain."""
    return {
        "domain": "tools",
    }


@pytest.fixture
def discover_files_input(temp_directory) -> Dict[str, Any]:
    """Valid input for discover files domain."""
    return {
        "domain": "files",
        "filter": {"pattern": "*.py"},
        "recursive": True,
    }


@pytest.fixture
def transform_json_yaml_input() -> Dict[str, Any]:
    """Valid input for JSON to YAML transformation."""
    return {
        "input": '{"key": "value", "nested": {"item": 1}}',
        "input_format": "json",
        "output_format": "yaml",
    }


@pytest.fixture
def transform_yaml_json_input() -> Dict[str, Any]:
    """Valid input for YAML to JSON transformation."""
    return {
        "input": "key: value\nnested:\n  item: 1",
        "input_format": "yaml",
        "output_format": "json",
    }


# ============================================================================
# Chain Reaction Fixtures
# ============================================================================


@pytest.fixture
def chain_read_transform(temp_json_file) -> Dict[str, Any]:
    """Chain: read file -> transform to YAML."""
    return {
        "operation": "read",
        "target": temp_json_file[0],
        "chain": [
            {
                "tool": "axom_mcp_transform",
                "args": {
                    "input": "${_result.content}",
                    "output_format": "yaml",
                },
            }
        ],
    }


@pytest.fixture
def chain_analyze_memory(temp_python_file) -> Dict[str, Any]:
    """Chain: analyze code -> store result in memory."""
    return {
        "type": "debug",
        "target": temp_python_file[0],
        "chain": [
            {
                "tool": "axom_mcp_memory",
                "args": {
                    "action": "write",
                    "name": "analysis_result_20260215",
                    "content": "${_result.summary}",
                },
            }
        ],
    }


# ============================================================================
# MCP Server Fixtures
# ============================================================================


@pytest.fixture
def mcp_server():
    """Create an MCP server instance for testing."""
    from axom_mcp.server import create_server

    return create_server()


@pytest.fixture
def mock_stdio():
    """Mock stdio transport for MCP server testing."""

    class MockStdio:
        def __init__(self):
            self.input_queue = asyncio.Queue()
            self.output_queue = asyncio.Queue()

        async def send(self, message: str) -> None:
            await self.input_queue.put(message)

        async def receive(self) -> str:
            return await self.output_queue.get()

        async def write_response(self, response: str) -> None:
            await self.output_queue.put(response)

    return MockStdio()


# ============================================================================
# Environment Fixtures
# ============================================================================


@pytest.fixture
def clean_env():
    """Clean environment variables for testing."""
    env_vars = [
        "AXOM_DATABASE_URL",
        "AXOM_READ_ONLY",
        "ALLOWED_PATHS",
    ]
    original_values = {}

    # Store original values
    for var in env_vars:
        if var in os.environ:
            original_values[var] = os.environ[var]
            del os.environ[var]

    yield

    # Restore original values
    for var, value in original_values.items():
        os.environ[var] = value


@pytest.fixture
def test_env(clean_env):
    """Set up test environment variables."""
    os.environ["AXOM_DATABASE_URL"] = "postgresql://test:test@localhost:5432/test_axom"
    os.environ["AXOM_READ_ONLY"] = "false"
    os.environ["ALLOWED_PATHS"] = "/tmp,/home/user/projects"
    yield
    # clean_env handles cleanup


# ============================================================================
# Pytest Configuration
# ============================================================================


def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line(
        "markers", "unit: Unit tests (fast, no external dependencies)"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests (may require database)"
    )
    config.addinivalue_line("markers", "slow: Slow tests (skip with -m 'not slow')")
    config.addinivalue_line("markers", "database: Tests requiring database connection")
    config.addinivalue_line("markers", "filesystem: Tests requiring filesystem access")
    config.addinivalue_line(
        "markers", "drift: Drift detection tests for workflow validation"
    )
