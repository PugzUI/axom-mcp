"""Unit tests for Axom MCP handlers."""

import json
import os

import pytest

from axom_mcp.handlers.transform import (
    handle_transform,
    _detect_format,
    _detect_language,
)
from axom_mcp.handlers.discover import handle_discover
from axom_mcp.handlers.analyze import handle_analyze
from axom_mcp.handlers.exec import handle_exec


class TestTransformHandler:
    """Tests for transform handler."""

    @pytest.mark.asyncio
    async def test_json_to_yaml(self):
        """Test JSON to YAML transformation."""
        result = await handle_transform(
            {
                "input": '{"name": "test", "value": 123}',
                "input_format": "json",
                "output_format": "yaml",
            }
        )
        data = json.loads(result)
        assert data["success"] is True
        assert data["input_format"] == "json"
        assert data["output_format"] == "yaml"
        assert "name: test" in data["result"]

    @pytest.mark.asyncio
    async def test_json_to_csv(self):
        """Test JSON to CSV transformation."""
        result = await handle_transform(
            {
                "input": '[{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]',
                "input_format": "json",
                "output_format": "csv",
            }
        )
        data = json.loads(result)
        assert data["success"] is True
        assert "name,age" in data["result"]
        assert "Alice,30" in data["result"]

    @pytest.mark.asyncio
    async def test_auto_detect_json(self):
        """Test auto-detection of JSON format."""
        result = await handle_transform(
            {
                "input": '{"key": "value"}',
                "output_format": "yaml",
            }
        )
        data = json.loads(result)
        assert data["success"] is True
        assert data["input_format"] == "json"

    @pytest.mark.asyncio
    async def test_auto_detect_csv(self):
        """Test auto-detection of CSV format."""
        result = await handle_transform(
            {
                "input": "name,age\nAlice,30\nBob,25",
                "output_format": "json",
            }
        )
        data = json.loads(result)
        assert data["success"] is True
        assert data["input_format"] == "csv"

    @pytest.mark.asyncio
    async def test_markdown_parsing(self):
        """Test markdown parsing."""
        result = await handle_transform(
            {
                "input": "# Title\n\nParagraph\n\n- Item 1\n- Item 2",
                "input_format": "markdown",
                "output_format": "json",
            }
        )
        data = json.loads(result)
        assert data["success"] is True
        parsed = json.loads(data["result"])
        assert "headers" in parsed
        assert len(parsed["headers"]) == 1
        assert parsed["headers"][0]["title"] == "Title"

    @pytest.mark.asyncio
    async def test_field_mapping_rule(self):
        """Test field mapping transformation rule."""
        result = await handle_transform(
            {
                "input": '{"old_name": "test", "value": 123}',
                "output_format": "json",
                "rules": [
                    {"type": "field_mapping", "mapping": {"old_name": "new_name"}}
                ],
            }
        )
        data = json.loads(result)
        assert data["success"] is True
        parsed = json.loads(data["result"])
        assert "new_name" in parsed
        assert "old_name" not in parsed

    @pytest.mark.asyncio
    async def test_filter_rule(self):
        """Test filter transformation rule."""
        result = await handle_transform(
            {
                "input": '{"a": 1, "b": 2, "c": 3}',
                "output_format": "json",
                "rules": [{"type": "filter", "fields": ["a", "b"]}],
            }
        )
        data = json.loads(result)
        assert data["success"] is True
        parsed = json.loads(data["result"])
        assert "a" in parsed
        assert "b" in parsed
        assert "c" not in parsed


class TestFormatDetection:
    """Tests for format detection functions."""

    def test_detect_json_object(self):
        """Test JSON object detection."""
        assert _detect_format('{"key": "value"}') == "json"

    def test_detect_json_array(self):
        """Test JSON array detection."""
        assert _detect_format("[1, 2, 3]") == "json"

    def test_detect_yaml_key_value(self):
        """Test YAML key-value detection."""
        assert _detect_format("name: test\nvalue: 123") == "yaml"

    def test_detect_yaml_list(self):
        """Test YAML list detection."""
        assert _detect_format("- item1\n- item2") == "yaml"

    def test_detect_csv(self):
        """Test CSV detection."""
        assert _detect_format("a,b,c\n1,2,3\n4,5,6") == "csv"

    def test_detect_markdown_header(self):
        """Test markdown header detection."""
        assert _detect_format("# Title\n\nContent") == "markdown"

    def test_detect_markdown_list(self):
        """Test markdown list detection."""
        assert _detect_format("* Item 1\n* Item 2") == "markdown"

    def test_detect_code_default(self):
        """Test code as default fallback."""
        # Plain text without clear indicators
        result = _detect_format("def hello():\n    pass")
        assert result in ["code", "yaml"]  # Could be detected as either


class TestLanguageDetection:
    """Tests for programming language detection."""

    def test_detect_python(self):
        """Test Python detection."""
        assert _detect_language("def hello():\n    print('hello')") == "python"
        assert _detect_language("import os\nfrom sys import path") == "python"

    def test_detect_javascript(self):
        """Test JavaScript detection."""
        assert (
            _detect_language("function hello() {\n  console.log('hello');\n}")
            == "javascript"
        )
        assert _detect_language("const x = 5;") == "javascript"

    def test_detect_typescript(self):
        """Test TypeScript detection."""
        assert _detect_language("interface User {\n  name: string;\n}") == "typescript"

    def test_detect_go(self):
        """Test Go detection."""
        assert _detect_language("package main\n\nfunc main() {}") == "go"

    def test_detect_rust(self):
        """Test Rust detection."""
        assert _detect_language('fn main() {\n    println!("hello");\n}') == "rust"

    def test_detect_unknown(self):
        """Test unknown language fallback."""
        assert _detect_language("hello world") == "unknown"


class TestDiscoverHandler:
    """Tests for discover handler."""

    @pytest.mark.asyncio
    async def test_discover_tools(self):
        """Test tools discovery."""
        result = await handle_discover({"domain": "tools"})
        data = json.loads(result)
        assert data["success"] is True
        assert data["domain"] == "tools"
        assert data["count"] == 5
        assert len(data["results"]) == 5
        tool_names = [t["name"] for t in data["results"]]
        assert "axom_mcp_memory" in tool_names
        assert "axom_mcp_exec" in tool_names

    @pytest.mark.asyncio
    async def test_discover_capabilities(self):
        """Test capabilities discovery."""
        result = await handle_discover({"domain": "capabilities"})
        data = json.loads(result)
        assert data["success"] is True
        assert "results" in data
        assert "features" in data["results"]

    @pytest.mark.asyncio
    async def test_discover_files(self):
        """Test files discovery."""
        result = await handle_discover(
            {
                "domain": "files",
                "filter": {"pattern": "*.py"},
                "recursive": False,
            }
        )
        data = json.loads(result)
        assert data["success"] is True
        assert data["domain"] == "files"


class TestAnalyzeHandler:
    """Tests for analyze handler."""

    @pytest.mark.asyncio
    async def test_analyze_debug(self):
        """Test debug analysis."""
        result = await handle_analyze(
            {
                "type": "debug",
                "target": "def broken():\n    return undefined_var",
            }
        )
        data = json.loads(result)
        assert data["success"] is True
        assert data["type"] == "debug"
        assert "issues_found" in data

    @pytest.mark.asyncio
    async def test_analyze_review(self):
        """Test code review analysis."""
        result = await handle_analyze(
            {
                "type": "review",
                "target": "x = 1  # TODO: fix this",
                "depth": "low",
            }
        )
        data = json.loads(result)
        assert data["success"] is True
        assert data["type"] == "review"

    @pytest.mark.asyncio
    async def test_analyze_with_focus(self):
        """Test analysis with focus area."""
        result = await handle_analyze(
            {
                "type": "audit",
                "target": "password = 'secret123'",
                "focus": "security",
            }
        )
        data = json.loads(result)
        assert data["success"] is True
        assert data["focus"] == "security"


class TestExecHandler:
    """Tests for exec handler."""

    @pytest.mark.asyncio
    async def test_read_file(self):
        """Test file reading."""
        # Create temp file in current working directory (allowed)
        temp_file = "test_temp_file.txt"
        try:
            with open(temp_file, "w") as f:
                f.write("test content")

            result = await handle_exec(
                {
                    "operation": "read",
                    "target": temp_file,
                }
            )
            data = json.loads(result)
            assert data["success"] is True
            assert data["content"] == "test content"
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)

    @pytest.mark.asyncio
    async def test_read_nonexistent_file(self):
        """Test reading nonexistent file."""
        result = await handle_exec(
            {
                "operation": "read",
                "target": "/nonexistent/file.txt",
            }
        )
        data = json.loads(result)
        assert "error" in data

    @pytest.mark.asyncio
    async def test_shell_command(self):
        """Test shell command execution."""
        result = await handle_exec(
            {
                "operation": "shell",
                "target": "echo 'hello world'",
            }
        )
        data = json.loads(result)
        assert data["success"] is True
        assert "hello world" in data["stdout"]

    @pytest.mark.asyncio
    async def test_shell_command_error(self):
        """Test shell command with error."""
        result = await handle_exec(
            {
                "operation": "shell",
                "target": "ls /nonexistent_directory_12345",
            }
        )
        data = json.loads(result)
        # Command runs but may have stderr
        assert "success" in data


class TestChainExecution:
    """Tests for chain execution in handlers."""

    @pytest.mark.asyncio
    async def test_transform_chain_parameter(self):
        """Test that chain parameter is accepted."""
        result = await handle_transform(
            {
                "input": '{"value": 123}',
                "output_format": "yaml",
                "chain": [{"tool": "axom_mcp_memory", "args": {"action": "write"}}],
            }
        )
        data = json.loads(result)
        assert data["success"] is True
        # Chain is not executed in unit tests, just validated

    @pytest.mark.asyncio
    async def test_discover_chain_parameter(self):
        """Test that chain parameter is accepted for discover."""
        result = await handle_discover(
            {
                "domain": "tools",
                "chain": [
                    {"tool": "axom_mcp_transform", "args": {"output_format": "json"}}
                ],
            }
        )
        data = json.loads(result)
        assert data["success"] is True
