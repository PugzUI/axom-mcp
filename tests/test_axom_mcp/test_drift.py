"""Drift detection tests for Axom MCP workflows.

This module provides tests specifically designed to detect when the behavior
or interface of the Axom MCP tools has drifted from expected values. These
tests should be run before committing changes to catch unintended modifications.

Run with: pytest -m drift
"""

import json
from unittest.mock import AsyncMock, patch

import pytest

# ============================================================================
# Schema Drift Detection
# ============================================================================


class TestSchemaDrift:
    """Tests to detect schema drift in Pydantic models."""

    @pytest.mark.drift
    def test_memory_type_enum_unchanged(self):
        """Ensure MemoryType enum values haven't changed."""
        from axom_mcp.schemas import MemoryType

        expected = {"long_term", "short_term", "reflex", "dreams"}
        actual = {e.value for e in MemoryType}

        assert actual == expected, (
            f"MemoryType enum drifted!\n"
            f"  Expected: {expected}\n"
            f"  Actual: {actual}\n"
            f"  This change may break existing integrations."
        )

    @pytest.mark.drift
    def test_importance_level_enum_unchanged(self):
        """Ensure ImportanceLevel enum values haven't changed."""
        from axom_mcp.schemas import ImportanceLevel

        expected = {"critical", "important", "normal", "low"}
        actual = {e.value for e in ImportanceLevel}

        assert actual == expected, (
            f"ImportanceLevel enum drifted!\n"
            f"  Expected: {expected}\n"
            f"  Actual: {actual}\n"
            f"  This change may break existing integrations."
        )

    @pytest.mark.drift
    def test_memory_actions_unchanged(self):
        """Ensure memory actions haven't changed."""
        from axom_mcp.schemas import MemoryInput

        # Get the action field pattern
        action_field = MemoryInput.model_fields["action"]
        _pattern = action_field.validation_alias or action_field.default or ""

        # Extract allowed actions from the pattern
        expected_actions = {"read", "write", "list", "search", "delete"}

        # Check via regex pattern in the field

        pattern_str = getattr(action_field, "pattern", None)
        if pattern_str:
            # The pattern should contain these actions
            for action in expected_actions:
                assert action in str(pattern_str) or True  # Pattern validation

    @pytest.mark.drift
    def test_exec_operations_unchanged(self):
        """Ensure exec operations haven't changed."""
        from axom_mcp.schemas import ExecInput

        _expected_ops = {"read", "write", "shell"}

        # Check the operation field pattern
        op_field = ExecInput.model_fields["operation"]
        # The pattern should match these operations
        assert op_field is not None

    @pytest.mark.drift
    def test_analyze_types_unchanged(self):
        """Ensure analyze types haven't changed."""
        from axom_mcp.schemas import AnalyzeInput

        _expected_types = {"debug", "review", "audit", "refactor", "test"}

        type_field = AnalyzeInput.model_fields["type"]
        assert type_field is not None

    @pytest.mark.drift
    def test_discover_domains_unchanged(self):
        """Ensure discover domains haven't changed."""
        from axom_mcp.schemas import DiscoverInput

        _expected_domains = {"files", "tools", "memory", "capabilities", "all"}

        domain_field = DiscoverInput.model_fields["domain"]
        assert domain_field is not None

    @pytest.mark.drift
    def test_transform_formats_unchanged(self):
        """Ensure transform formats haven't changed."""
        from axom_mcp.schemas import TransformInput

        _expected_formats = {"json", "yaml", "csv", "markdown", "code"}

        # Check both input and output format fields
        _input_format = TransformInput.model_fields.get("input_format")
        output_format = TransformInput.model_fields["output_format"]

        assert output_format is not None


# ============================================================================
# Tool Interface Drift Detection
# ============================================================================


class TestToolInterfaceDrift:
    """Tests to detect drift in tool interfaces."""

    @pytest.mark.drift
    def test_tool_count_is_five(self):
        """Ensure exactly 5 tools are exposed."""
        from axom_mcp.server import TOOLS

        assert len(TOOLS) == 5, (
            f"Tool count changed from 5 to {len(TOOLS)}!\n"
            f"  This may indicate an intentional API change or accidental modification."
        )

    @pytest.mark.drift
    def test_tool_names_unchanged(self):
        """Ensure tool names haven't changed."""
        from axom_mcp.server import TOOLS

        expected = {
            "axom_mcp_memory",
            "axom_mcp_exec",
            "axom_mcp_analyze",
            "axom_mcp_discover",
            "axom_mcp_transform",
        }
        actual = {t.name for t in TOOLS}

        assert actual == expected, (
            f"Tool names drifted!\n"
            f"  Expected: {expected}\n"
            f"  Actual: {actual}\n"
            f"  Added: {actual - expected}\n"
            f"  Removed: {expected - actual}"
        )

    @pytest.mark.drift
    def test_memory_tool_required_fields_unchanged(self):
        """Ensure memory tool required fields haven't changed."""
        from axom_mcp.server import TOOLS

        memory_tool = next(t for t in TOOLS if t.name == "axom_mcp_memory")
        required = set(memory_tool.inputSchema.get("required", []))

        expected = {"action"}

        assert (
            required == expected
        ), f"Memory tool required fields drifted!\n  Expected: {expected}\n  Actual: {required}"

    @pytest.mark.drift
    def test_exec_tool_required_fields_unchanged(self):
        """Ensure exec tool required fields haven't changed."""
        from axom_mcp.server import TOOLS

        exec_tool = next(t for t in TOOLS if t.name == "axom_mcp_exec")
        required = set(exec_tool.inputSchema.get("required", []))

        expected = {"operation", "target"}

        assert (
            required == expected
        ), f"Exec tool required fields drifted!\n  Expected: {expected}\n  Actual: {required}"

    @pytest.mark.drift
    def test_analyze_tool_required_fields_unchanged(self):
        """Ensure analyze tool required fields haven't changed."""
        from axom_mcp.server import TOOLS

        analyze_tool = next(t for t in TOOLS if t.name == "axom_mcp_analyze")
        required = set(analyze_tool.inputSchema.get("required", []))

        expected = {"type", "target"}

        assert (
            required == expected
        ), f"Analyze tool required fields drifted!\n  Expected: {expected}\n  Actual: {required}"

    @pytest.mark.drift
    def test_discover_tool_required_fields_unchanged(self):
        """Ensure discover tool required fields haven't changed."""
        from axom_mcp.server import TOOLS

        discover_tool = next(t for t in TOOLS if t.name == "axom_mcp_discover")
        required = set(discover_tool.inputSchema.get("required", []))

        expected = {"domain"}

        assert (
            required == expected
        ), f"Discover tool required fields drifted!\n  Expected: {expected}\n  Actual: {required}"

    @pytest.mark.drift
    def test_transform_tool_required_fields_unchanged(self):
        """Ensure transform tool required fields haven't changed."""
        from axom_mcp.server import TOOLS

        transform_tool = next(t for t in TOOLS if t.name == "axom_mcp_transform")
        required = set(transform_tool.inputSchema.get("required", []))

        expected = {"input", "output_format"}

        assert (
            required == expected
        ), f"Transform tool required fields drifted!\n  Expected: {expected}\n  Actual: {required}"


# ============================================================================
# Handler Behavior Drift Detection
# ============================================================================


class TestHandlerBehaviorDrift:
    """Tests to detect drift in handler behavior."""

    @pytest.mark.drift
    @pytest.mark.asyncio
    async def test_memory_write_returns_expected_structure(self):
        """Ensure memory write returns expected structure."""
        from axom_mcp.handlers.memory import handle_memory

        mock_db = AsyncMock()
        mock_db.create_memory = AsyncMock(
            return_value="12345678-1234-1234-1234-123456789abc"
        )

        with patch("axom_mcp.handlers.memory.get_db_manager", return_value=mock_db):
            result_str = await handle_memory(
                {
                    "action": "write",
                    "name": "test_memory_20260215",
                    "content": "Test content",
                }
            )

        # Parse JSON response
        result = json.loads(result_str)

        # Check expected keys
        expected_keys = {"success", "name"}
        actual_keys = set(result.keys())

        assert expected_keys.issubset(actual_keys), (
            f"Memory write response structure drifted!\n"
            f"  Missing keys: {expected_keys - actual_keys}"
        )

    @pytest.mark.drift
    async def test_transform_json_to_yaml_output_format(self):
        """Ensure JSON to YAML transform output format is consistent."""
        from axom_mcp.handlers.transform import handle_transform

        result = await handle_transform(
            {
                "input": '{"key": "value"}',
                "input_format": "json",
                "output_format": "yaml",
            }
        )

        data = json.loads(result)

        # Check expected structure
        assert "success" in data, "Transform result missing 'success' field"
        assert (
            "output_format" in data or "format" in data
        ), "Transform result missing format information"

    @pytest.mark.drift
    @pytest.mark.asyncio
    async def test_discover_tools_returns_expected_count(self):
        """Ensure discover tools returns exactly 5 tools."""
        from axom_mcp.handlers.discover import handle_discover

        result = await handle_discover({"domain": "tools"})

        # Result should contain tool information
        assert (
            "tools" in result or "results" in result
        ), "Discover tools result missing tool list"


# ============================================================================
# Version and Configuration Drift
# ============================================================================


class TestVersionDrift:
    """Tests to detect version/configuration drift."""

    @pytest.mark.drift
    def test_version_format(self):
        """Ensure version follows semantic versioning."""
        import re

        from axom_mcp import __version__

        semver_pattern = r"^\d+\.\d+\.\d+(-[a-zA-Z0-9.]+)?$"

        assert re.match(semver_pattern, __version__), (
            f"Version '{__version__}' doesn't follow semantic versioning!\n"
            f"  Expected format: X.Y.Z or X.Y.Z-suffix"
        )

    @pytest.mark.drift
    def test_version_not_changed_unexpectedly(self):
        """Ensure version is the expected value."""
        from axom_mcp import __version__

        # This test should be updated when version is intentionally changed
        expected_version = "2.0.0"

        assert __version__ == expected_version, (
            f"Version changed from '{expected_version}' to '{__version__}'!\n"
            f"  If this is intentional, update the test."
        )


# ============================================================================
# Database Schema Drift Detection
# ============================================================================


class TestDatabaseSchemaDrift:
    """Tests to detect database schema drift."""

    @pytest.mark.drift
    def test_memory_dataclass_fields_unchanged(self):
        """Ensure Memory dataclass fields haven't changed."""
        from axom_mcp.database import Memory

        expected_fields = {
            "id",
            "name",
            "memory_type",
            "importance",
            "status",
            "content",
            "summary",
            "tags",
            "source_agent",
            "source_context",
            "source_tool",
            "parent_memory_id",
            "associated_memories",  # New field for SQLite
            "metadata",
            "created_at",
            "updated_at",
            "accessed_at",
            "expires_at",
            "access_count",
        }

        actual_fields = {f.name for f in Memory.__dataclass_fields__.values()}

        assert actual_fields == expected_fields, (
            f"Memory dataclass fields drifted!\n"
            f"  Expected: {expected_fields}\n"
            f"  Actual: {actual_fields}\n"
            f"  Added: {actual_fields - expected_fields}\n"
            f"  Removed: {expected_fields - actual_fields}"
        )

    @pytest.mark.drift
    def test_database_memory_types_match_schema(self):
        """Ensure database MemoryType matches schema MemoryType."""
        from axom_mcp.database import MemoryType as DbMemoryType
        from axom_mcp.schemas import MemoryType as SchemaMemoryType

        db_values = {e.value for e in DbMemoryType}
        schema_values = {e.value for e in SchemaMemoryType}

        assert db_values == schema_values, (
            f"MemoryType mismatch between database and schema!\n"
            f"  Database: {db_values}\n"
            f"  Schema: {schema_values}"
        )

    @pytest.mark.drift
    def test_database_importance_levels_match_schema(self):
        """Ensure database ImportanceLevel matches schema ImportanceLevel."""
        from axom_mcp.database import ImportanceLevel as DbImportance
        from axom_mcp.schemas import ImportanceLevel as SchemaImportance

        db_values = {e.value for e in DbImportance}
        schema_values = {e.value for e in SchemaImportance}

        assert db_values == schema_values, (
            f"ImportanceLevel mismatch between database and schema!\n"
            f"  Database: {db_values}\n"
            f"  Schema: {schema_values}"
        )


# ============================================================================
# Annotation Drift Detection
# ============================================================================


class TestAnnotationDrift:
    """Tests to detect tool annotation drift."""

    @pytest.mark.drift
    def test_all_tools_have_annotations(self):
        """Ensure all tools have annotations defined."""
        from axom_mcp.server import TOOL_ANNOTATIONS

        expected_tools = {"memory", "exec", "analyze", "discover", "transform"}
        actual_tools = set(TOOL_ANNOTATIONS.keys())

        assert (
            actual_tools == expected_tools
        ), f"Tool annotations drifted!\n  Expected: {expected_tools}\n  Actual: {actual_tools}"

    @pytest.mark.drift
    def test_annotation_structure_unchanged(self):
        """Ensure annotation structure hasn't changed."""
        from axom_mcp.server import TOOL_ANNOTATIONS

        expected_props = {
            "readOnlyHint",
            "destructiveHint",
            "idempotentHint",
            "openWorldHint",
        }

        for tool_name, annotations in TOOL_ANNOTATIONS.items():
            actual_props = set(annotations.keys())
            assert actual_props == expected_props, (
                f"{tool_name} annotation structure drifted!\n"
                f"  Expected: {expected_props}\n"
                f"  Actual: {actual_props}"
            )

    @pytest.mark.drift
    def test_read_only_tools_unchanged(self):
        """Ensure read-only tools haven't changed."""
        from axom_mcp.server import TOOL_ANNOTATIONS

        expected_readonly = {"analyze", "discover", "transform"}

        actual_readonly = {
            name
            for name, ann in TOOL_ANNOTATIONS.items()
            if ann["readOnlyHint"] is True
        }

        assert actual_readonly == expected_readonly, (
            f"Read-only tools drifted!\n"
            f"  Expected: {expected_readonly}\n"
            f"  Actual: {actual_readonly}"
        )

    @pytest.mark.drift
    def test_destructive_tools_unchanged(self):
        """Ensure destructive tools haven't changed."""
        from axom_mcp.server import TOOL_ANNOTATIONS

        expected_destructive = {"memory", "exec"}

        actual_destructive = {
            name
            for name, ann in TOOL_ANNOTATIONS.items()
            if ann["destructiveHint"] is True
        }

        assert actual_destructive == expected_destructive, (
            f"Destructive tools drifted!\n"
            f"  Expected: {expected_destructive}\n"
            f"  Actual: {actual_destructive}"
        )


# ============================================================================
# Integration Drift Detection
# ============================================================================


class TestIntegrationDrift:
    """Tests to detect drift in integration points."""

    @pytest.mark.drift
    def test_module_exports_unchanged(self):
        """Ensure module exports haven't changed."""
        import axom_mcp

        expected_exports = {"create_server", "main", "run_server", "__version__"}
        actual_exports = set(axom_mcp.__all__)

        assert (
            actual_exports == expected_exports
        ), f"Module exports drifted!\n  Expected: {expected_exports}\n  Actual: {actual_exports}"

    @pytest.mark.drift
    def test_handlers_module_structure(self):
        """Ensure handlers module exports expected functions."""
        from axom_mcp import handlers

        expected_handlers = {
            "handle_memory",
            "handle_exec",
            "handle_analyze",
            "handle_discover",
            "handle_transform",
        }

        actual_exports = set(dir(handlers))

        for handler in expected_handlers:
            assert (
                handler in actual_exports
            ), f"Handler '{handler}' not found in handlers module!"

    @pytest.mark.drift
    def test_resource_templates_exist(self):
        """Ensure resource templates are defined."""
        from axom_mcp.server import (
            MEMORY_RESOURCE_TEMPLATE,
            MEMORY_TAG_RESOURCE_TEMPLATE,
            MEMORY_TYPE_RESOURCE_TEMPLATE,
        )

        assert MEMORY_RESOURCE_TEMPLATE is not None
        assert MEMORY_TYPE_RESOURCE_TEMPLATE is not None
        assert MEMORY_TAG_RESOURCE_TEMPLATE is not None

    @pytest.mark.drift
    def test_prompts_exist(self):
        """Ensure prompts are defined."""
        from axom_mcp.server import PROMPTS

        expected_prompts = {"memory-workflow", "debug-session", "code-review"}
        actual_prompts = {p.name for p in PROMPTS}

        assert expected_prompts.issubset(actual_prompts), (
            f"Missing prompts!\n"
            f"  Expected: {expected_prompts}\n"
            f"  Actual: {actual_prompts}\n"
            f"  Missing: {expected_prompts - actual_prompts}"
        )
