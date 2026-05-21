"""Unit tests for Axom MCP Pydantic schemas."""

import pytest
from pydantic import ValidationError

from axom_mcp.schemas import (
    AnalyzeInput,
    DiscoverInput,
    ExecInput,
    ImportanceLevel,
    MemoryDeleteInput,
    MemoryInput,
    MemoryListInput,
    MemoryReadInput,
    MemorySearchInput,
    MemoryType,
    MemoryWriteInput,
    TransformInput,
)


class TestMemoryEnums:
    """Tests for enum types."""

    def test_memory_type_values(self):
        """Test MemoryType enum values."""
        assert MemoryType.LONG_TERM == "long_term"
        assert MemoryType.SHORT_TERM == "short_term"
        assert MemoryType.REFLEX == "reflex"
        assert MemoryType.DREAMS == "dreams"

    def test_importance_level_values(self):
        """Test ImportanceLevel enum values."""
        assert ImportanceLevel.CRITICAL == "critical"
        assert ImportanceLevel.HIGH == "high"
        assert ImportanceLevel.LOW == "low"


class TestMemoryWriteInput:
    """Tests for MemoryWriteInput schema."""

    def test_valid_write_input(self):
        """Test valid memory write input."""
        data = {
            "action": "write",
            "name": "pattern_test_20260214",
            "content": "Test content",
            "memory_type": "long_term",
            "importance": "high",
            "tags": ["test", "example"],
        }
        result = MemoryWriteInput(**data)
        assert result.action == "write"
        assert result.name == "pattern_test_20260214"
        assert result.content == "Test content"
        assert result.memory_type == MemoryType.LONG_TERM
        assert result.importance == ImportanceLevel.HIGH
        assert result.tags == ["test", "example"]

    def test_minimal_write_input(self):
        """Test minimal memory write input with defaults."""
        data = {
            "name": "test_memory",
            "content": "Test content",
        }
        result = MemoryWriteInput(**data)
        assert result.action == "write"
        assert result.memory_type == MemoryType.LONG_TERM
        assert result.importance == ImportanceLevel.HIGH
        assert result.tags is None

    def test_extra_fields_forbidden(self):
        """Test that extra fields are forbidden."""
        data = {
            "name": "test_memory",
            "content": "Test content",
            "unknown_field": "value",
        }
        with pytest.raises(ValidationError) as exc_info:
            MemoryWriteInput(**data)
        assert "extra" in str(exc_info.value).lower()

    def test_name_too_long(self):
        """Test that name exceeding max length is rejected."""
        data = {
            "name": "a" * 256,
            "content": "Test content",
        }
        with pytest.raises(ValidationError):
            MemoryWriteInput(**data)

    def test_content_too_long(self):
        """Test that content exceeding max length is rejected."""
        data = {
            "name": "test_memory",
            "content": "a" * 1_000_001,
        }
        with pytest.raises(ValidationError):
            MemoryWriteInput(**data)

    def test_too_many_tags(self):
        """Test that too many tags are rejected."""
        data = {
            "name": "test_memory",
            "content": "Test content",
            "tags": [f"tag_{i}" for i in range(21)],
        }
        with pytest.raises(ValidationError):
            MemoryWriteInput(**data)


class TestMemorySearchInput:
    """Tests for MemorySearchInput schema."""

    def test_valid_search_input(self):
        """Test valid memory search input."""
        data = {
            "action": "search",
            "query": "test query",
            "memory_type": "long_term",
            "limit": 20,
        }
        result = MemorySearchInput(**data)
        assert result.action == "search"
        assert result.query == "test query"
        assert result.memory_type == MemoryType.LONG_TERM
        assert result.limit == 20

    def test_default_limit(self):
        """Test default limit value."""
        data = {"query": "test query"}
        result = MemorySearchInput(**data)
        assert result.limit == 10

    def test_limit_bounds(self):
        """Test limit bounds validation."""
        # Too low
        with pytest.raises(ValidationError):
            MemorySearchInput(query="test", limit=0)
        # Too high
        with pytest.raises(ValidationError):
            MemorySearchInput(query="test", limit=101)


class TestMemoryReadInput:
    """Tests for MemoryReadInput schema."""

    def test_valid_read_input(self):
        """Test valid memory read input."""
        data = {
            "action": "read",
            "name": "test_memory",
        }
        result = MemoryReadInput(**data)
        assert result.action == "read"
        assert result.name == "test_memory"


class TestMemoryListInput:
    """Tests for MemoryListInput schema."""

    def test_valid_list_input(self):
        """Test valid memory list input."""
        data = {
            "action": "list",
            "memory_type": "short_term",
            "limit": 100,
        }
        result = MemoryListInput(**data)
        assert result.action == "list"
        assert result.memory_type == MemoryType.SHORT_TERM
        assert result.limit == 100

    def test_default_limit(self):
        """Test default limit value."""
        data = {}
        result = MemoryListInput(**data)
        assert result.limit == 50


class TestMemoryDeleteInput:
    """Tests for MemoryDeleteInput schema."""

    def test_valid_delete_input(self):
        """Test valid memory delete input."""
        data = {
            "action": "delete",
            "name": "test_memory",
        }
        result = MemoryDeleteInput(**data)
        assert result.action == "delete"
        assert result.name == "test_memory"


class TestMemoryInput:
    """Tests for unified MemoryInput schema."""

    def test_write_action(self):
        """Test write action."""
        data = {
            "action": "write",
            "name": "test_memory",
            "content": "Test content",
        }
        result = MemoryInput(**data)
        assert result.action == "write"
        assert result.name == "test_memory"
        assert result.content == "Test content"

    def test_search_action(self):
        """Test search action."""
        data = {
            "action": "search",
            "query": "test query",
        }
        result = MemoryInput(**data)
        assert result.action == "search"
        assert result.query == "test query"

    def test_invalid_action(self):
        """Test invalid action."""
        data = {"action": "invalid"}
        with pytest.raises(ValidationError):
            MemoryInput(**data)


class TestExecInput:
    """Tests for ExecInput schema."""

    def test_read_operation(self):
        """Test read operation."""
        data = {
            "operation": "read",
            "target": "/path/to/file.txt",
        }
        result = ExecInput(**data)
        assert result.operation == "read"
        assert result.target == "/path/to/file.txt"

    def test_write_operation(self):
        """Test write operation."""
        data = {
            "operation": "write",
            "target": "/path/to/file.txt",
            "data": "Content to write",
        }
        result = ExecInput(**data)
        assert result.operation == "write"
        assert result.data == "Content to write"

    def test_shell_operation(self):
        """Test shell operation."""
        data = {
            "operation": "shell",
            "target": "ls -la",
        }
        result = ExecInput(**data)
        assert result.operation == "shell"
        assert result.target == "ls -la"

    def test_invalid_operation(self):
        """Test invalid operation."""
        data = {
            "operation": "invalid",
            "target": "test",
        }
        with pytest.raises(ValidationError):
            ExecInput(**data)

    def test_chain_parameter(self):
        """Test chain parameter."""
        data = {
            "operation": "read",
            "target": "/file.txt",
            "chain": [
                {"tool": "axom_mcp_transform", "args": {"output_format": "json"}}
            ],
        }
        result = ExecInput(**data)
        assert result.chain is not None
        assert len(result.chain) == 1


class TestAnalyzeInput:
    """Tests for AnalyzeInput schema."""

    def test_valid_analyze_input(self):
        """Test valid analyze input."""
        data = {
            "type": "debug",
            "target": "/path/to/file.py",
            "focus": "security",
            "depth": "high",
        }
        result = AnalyzeInput(**data)
        assert result.type == "debug"
        assert result.target == "/path/to/file.py"
        assert result.focus == "security"
        assert result.depth == "high"

    def test_default_values(self):
        """Test default values."""
        data = {
            "type": "review",
            "target": "/file.py",
        }
        result = AnalyzeInput(**data)
        assert result.depth == "medium"
        assert result.output_format == "summary"

    def test_invalid_type(self):
        """Test invalid analysis type."""
        data = {
            "type": "invalid",
            "target": "/file.py",
        }
        with pytest.raises(ValidationError):
            AnalyzeInput(**data)

    def test_invalid_depth(self):
        """Test invalid depth."""
        data = {
            "type": "debug",
            "target": "/file.py",
            "depth": "invalid",
        }
        with pytest.raises(ValidationError):
            AnalyzeInput(**data)


class TestDiscoverInput:
    """Tests for DiscoverInput schema."""

    def test_valid_discover_input(self):
        """Test valid discover input."""
        data = {
            "domain": "files",
            "filter": {"pattern": "*.py"},
            "recursive": True,
        }
        result = DiscoverInput(**data)
        assert result.domain == "files"
        assert result.filter == {"pattern": "*.py"}
        assert result.recursive is True

    def test_tools_domain(self):
        """Test tools domain."""
        data = {"domain": "tools"}
        result = DiscoverInput(**data)
        assert result.domain == "tools"

    def test_invalid_domain(self):
        """Test invalid domain."""
        data = {"domain": "invalid"}
        with pytest.raises(ValidationError):
            DiscoverInput(**data)

    def test_limit_bounds(self):
        """Test limit bounds."""
        with pytest.raises(ValidationError):
            DiscoverInput(domain="files", limit=0)
        with pytest.raises(ValidationError):
            DiscoverInput(domain="files", limit=1001)


class TestTransformInput:
    """Tests for TransformInput schema."""

    def test_valid_transform_input(self):
        """Test valid transform input."""
        data = {
            "input": '{"key": "value"}',
            "input_format": "json",
            "output_format": "yaml",
        }
        result = TransformInput(**data)
        assert result.input == '{"key": "value"}'
        assert result.input_format == "json"
        assert result.output_format == "yaml"

    def test_required_output_format(self):
        """Test that output_format is required."""
        data = {"input": "test data"}
        with pytest.raises(ValidationError):
            TransformInput(**data)

    def test_invalid_input_format(self):
        """Test invalid input format."""
        data = {
            "input": "test",
            "input_format": "invalid",
            "output_format": "json",
        }
        with pytest.raises(ValidationError):
            TransformInput(**data)

    def test_invalid_output_format(self):
        """Test invalid output format."""
        data = {
            "input": "test",
            "output_format": "invalid",
        }
        with pytest.raises(ValidationError):
            TransformInput(**data)

    def test_transformation_rules(self):
        """Test transformation rules parameter."""
        data = {
            "input": '{"a": 1, "b": 2}',
            "output_format": "json",
            "rules": [{"type": "filter", "fields": ["a"]}],
        }
        result = TransformInput(**data)
        assert result.rules is not None
        assert len(result.rules) == 1
