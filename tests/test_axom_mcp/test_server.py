"""Comprehensive tests for Axom MCP server module.

This module tests the server components including:
- Tool definitions and schemas
- Server creation and configuration
- Resource templates
- Prompt templates
- Tool annotations
"""


import pytest



# ============================================================================
# Tool Definition Tests
# ============================================================================


class TestToolDefinitions:
    """Tests for MCP tool definitions."""

    def test_tools_count(self):
        """Test that exactly 5 tools are defined."""
        from axom_mcp.server import TOOLS

        assert len(TOOLS) == 5

    def test_tool_names(self):
        """Test that all expected tools are present."""
        from axom_mcp.server import TOOLS

        tool_names = [t.name for t in TOOLS]
        expected_names = [
            "axom_mcp_memory",
            "axom_mcp_exec",
            "axom_mcp_analyze",
            "axom_mcp_discover",
            "axom_mcp_transform",
        ]

        assert set(tool_names) == set(expected_names)

    def test_all_tools_have_descriptions(self):
        """Test that all tools have non-empty descriptions."""
        from axom_mcp.server import TOOLS

        for tool in TOOLS:
            assert tool.description is not None
            assert len(tool.description) > 0

    def test_all_tools_have_input_schemas(self):
        """Test that all tools have valid input schemas."""
        from axom_mcp.server import TOOLS

        for tool in TOOLS:
            assert tool.inputSchema is not None
            assert tool.inputSchema["type"] == "object"
            assert "properties" in tool.inputSchema


class TestMemoryToolSchema:
    """Tests for axom_mcp_memory tool schema."""

    @pytest.fixture
    def memory_tool(self):
        """Get the memory tool."""
        from axom_mcp.server import TOOLS

        return next(t for t in TOOLS if t.name == "axom_mcp_memory")

    def test_memory_tool_has_action_property(self, memory_tool):
        """Test memory tool has action property."""
        assert "action" in memory_tool.inputSchema["properties"]

    def test_memory_tool_action_enum(self, memory_tool):
        """Test memory tool action has correct enum values."""
        action_prop = memory_tool.inputSchema["properties"]["action"]
        assert action_prop["type"] == "string"
        expected_actions = ["read", "write", "list", "search", "delete"]
        assert set(action_prop["enum"]) == set(expected_actions)

    def test_memory_tool_action_required(self, memory_tool):
        """Test memory tool action is required."""
        assert "action" in memory_tool.inputSchema["required"]

    def test_memory_tool_has_name_property(self, memory_tool):
        """Test memory tool has name property."""
        assert "name" in memory_tool.inputSchema["properties"]

    def test_memory_tool_has_content_property(self, memory_tool):
        """Test memory tool has content property."""
        assert "content" in memory_tool.inputSchema["properties"]

    def test_memory_tool_has_memory_type_property(self, memory_tool):
        """Test memory tool has memory_type property."""
        assert "memory_type" in memory_tool.inputSchema["properties"]

    def test_memory_tool_memory_type_enum(self, memory_tool):
        """Test memory tool memory_type has correct enum values."""
        type_prop = memory_tool.inputSchema["properties"]["memory_type"]
        expected_types = ["long_term", "short_term", "reflex", "dreams"]
        assert set(type_prop["enum"]) == set(expected_types)

    def test_memory_tool_has_importance_property(self, memory_tool):
        """Test memory tool has importance property."""
        assert "importance" in memory_tool.inputSchema["properties"]

    def test_memory_tool_importance_enum(self, memory_tool):
        """Test memory tool importance has correct enum values."""
        imp_prop = memory_tool.inputSchema["properties"]["importance"]
        expected_levels = ["critical", "important", "normal", "low"]
        assert set(imp_prop["enum"]) == set(expected_levels)

    def test_memory_tool_has_tags_property(self, memory_tool):
        """Test memory tool has tags property."""
        assert "tags" in memory_tool.inputSchema["properties"]

    def test_memory_tool_has_query_property(self, memory_tool):
        """Test memory tool has query property."""
        assert "query" in memory_tool.inputSchema["properties"]

    def test_memory_tool_has_limit_property(self, memory_tool):
        """Test memory tool has limit property."""
        assert "limit" in memory_tool.inputSchema["properties"]
        limit_prop = memory_tool.inputSchema["properties"]["limit"]
        assert limit_prop["type"] == "integer"
        assert limit_prop["minimum"] == 1
        assert limit_prop["maximum"] == 200


class TestExecToolSchema:
    """Tests for axom_mcp_exec tool schema."""

    @pytest.fixture
    def exec_tool(self):
        """Get the exec tool."""
        from axom_mcp.server import TOOLS

        return next(t for t in TOOLS if t.name == "axom_mcp_exec")

    def test_exec_tool_has_operation_property(self, exec_tool):
        """Test exec tool has operation property."""
        assert "operation" in exec_tool.inputSchema["properties"]

    def test_exec_tool_operation_enum(self, exec_tool):
        """Test exec tool operation has correct enum values."""
        op_prop = exec_tool.inputSchema["properties"]["operation"]
        expected_ops = ["read", "write", "shell"]
        assert set(op_prop["enum"]) == set(expected_ops)

    def test_exec_tool_operation_required(self, exec_tool):
        """Test exec tool operation is required."""
        assert "operation" in exec_tool.inputSchema["required"]

    def test_exec_tool_has_target_property(self, exec_tool):
        """Test exec tool has target property."""
        assert "target" in exec_tool.inputSchema["properties"]

    def test_exec_tool_target_required(self, exec_tool):
        """Test exec tool target is required."""
        assert "target" in exec_tool.inputSchema["required"]

    def test_exec_tool_has_data_property(self, exec_tool):
        """Test exec tool has data property."""
        assert "data" in exec_tool.inputSchema["properties"]

    def test_exec_tool_has_chain_property(self, exec_tool):
        """Test exec tool has chain property."""
        assert "chain" in exec_tool.inputSchema["properties"]


class TestAnalyzeToolSchema:
    """Tests for axom_mcp_analyze tool schema."""

    @pytest.fixture
    def analyze_tool(self):
        """Get the analyze tool."""
        from axom_mcp.server import TOOLS

        return next(t for t in TOOLS if t.name == "axom_mcp_analyze")

    def test_analyze_tool_has_type_property(self, analyze_tool):
        """Test analyze tool has type property."""
        assert "type" in analyze_tool.inputSchema["properties"]

    def test_analyze_tool_type_enum(self, analyze_tool):
        """Test analyze tool type has correct enum values."""
        type_prop = analyze_tool.inputSchema["properties"]["type"]
        expected_types = ["debug", "review", "audit", "refactor", "test"]
        assert set(type_prop["enum"]) == set(expected_types)

    def test_analyze_tool_type_required(self, analyze_tool):
        """Test analyze tool type is required."""
        assert "type" in analyze_tool.inputSchema["required"]

    def test_analyze_tool_has_target_property(self, analyze_tool):
        """Test analyze tool has target property."""
        assert "target" in analyze_tool.inputSchema["properties"]

    def test_analyze_tool_target_required(self, analyze_tool):
        """Test analyze tool target is required."""
        assert "target" in analyze_tool.inputSchema["required"]

    def test_analyze_tool_has_focus_property(self, analyze_tool):
        """Test analyze tool has focus property."""
        assert "focus" in analyze_tool.inputSchema["properties"]

    def test_analyze_tool_has_depth_property(self, analyze_tool):
        """Test analyze tool has depth property."""
        assert "depth" in analyze_tool.inputSchema["properties"]

    def test_analyze_tool_depth_enum(self, analyze_tool):
        """Test analyze tool depth has correct enum values."""
        depth_prop = analyze_tool.inputSchema["properties"]["depth"]
        expected_depths = ["minimal", "low", "medium", "high", "max"]
        assert set(depth_prop["enum"]) == set(expected_depths)

    def test_analyze_tool_has_output_format_property(self, analyze_tool):
        """Test analyze tool has output_format property."""
        assert "output_format" in analyze_tool.inputSchema["properties"]

    def test_analyze_tool_output_format_enum(self, analyze_tool):
        """Test analyze tool output_format has correct enum values."""
        format_prop = analyze_tool.inputSchema["properties"]["output_format"]
        expected_formats = ["summary", "detailed", "actionable"]
        assert set(format_prop["enum"]) == set(expected_formats)


class TestDiscoverToolSchema:
    """Tests for axom_mcp_discover tool schema."""

    @pytest.fixture
    def discover_tool(self):
        """Get the discover tool."""
        from axom_mcp.server import TOOLS

        return next(t for t in TOOLS if t.name == "axom_mcp_discover")

    def test_discover_tool_has_domain_property(self, discover_tool):
        """Test discover tool has domain property."""
        assert "domain" in discover_tool.inputSchema["properties"]

    def test_discover_tool_domain_enum(self, discover_tool):
        """Test discover tool domain has correct enum values."""
        domain_prop = discover_tool.inputSchema["properties"]["domain"]
        expected_domains = ["files", "tools", "memory", "capabilities", "all"]
        assert set(domain_prop["enum"]) == set(expected_domains)

    def test_discover_tool_domain_required(self, discover_tool):
        """Test discover tool domain is required."""
        assert "domain" in discover_tool.inputSchema["required"]

    def test_discover_tool_has_filter_property(self, discover_tool):
        """Test discover tool has filter property."""
        assert "filter" in discover_tool.inputSchema["properties"]

    def test_discover_tool_has_limit_property(self, discover_tool):
        """Test discover tool has limit property."""
        assert "limit" in discover_tool.inputSchema["properties"]
        limit_prop = discover_tool.inputSchema["properties"]["limit"]
        assert limit_prop["minimum"] == 1
        assert limit_prop["maximum"] == 1000

    def test_discover_tool_has_recursive_property(self, discover_tool):
        """Test discover tool has recursive property."""
        assert "recursive" in discover_tool.inputSchema["properties"]


class TestTransformToolSchema:
    """Tests for axom_mcp_transform tool schema."""

    @pytest.fixture
    def transform_tool(self):
        """Get the transform tool."""
        from axom_mcp.server import TOOLS

        return next(t for t in TOOLS if t.name == "axom_mcp_transform")

    def test_transform_tool_has_input_property(self, transform_tool):
        """Test transform tool has input property."""
        assert "input" in transform_tool.inputSchema["properties"]

    def test_transform_tool_input_required(self, transform_tool):
        """Test transform tool input is required."""
        assert "input" in transform_tool.inputSchema["required"]

    def test_transform_tool_has_input_format_property(self, transform_tool):
        """Test transform tool has input_format property."""
        assert "input_format" in transform_tool.inputSchema["properties"]

    def test_transform_tool_input_format_enum(self, transform_tool):
        """Test transform tool input_format has correct enum values."""
        format_prop = transform_tool.inputSchema["properties"]["input_format"]
        expected_formats = ["json", "yaml", "csv", "markdown", "code"]
        assert set(format_prop["enum"]) == set(expected_formats)

    def test_transform_tool_has_output_format_property(self, transform_tool):
        """Test transform tool has output_format property."""
        assert "output_format" in transform_tool.inputSchema["properties"]

    def test_transform_tool_output_format_required(self, transform_tool):
        """Test transform tool output_format is required."""
        assert "output_format" in transform_tool.inputSchema["required"]

    def test_transform_tool_output_format_enum(self, transform_tool):
        """Test transform tool output_format has correct enum values."""
        format_prop = transform_tool.inputSchema["properties"]["output_format"]
        expected_formats = ["json", "yaml", "csv", "markdown", "code"]
        assert set(format_prop["enum"]) == set(expected_formats)

    def test_transform_tool_has_rules_property(self, transform_tool):
        """Test transform tool has rules property."""
        assert "rules" in transform_tool.inputSchema["properties"]

    def test_transform_tool_has_template_property(self, transform_tool):
        """Test transform tool has template property."""
        assert "template" in transform_tool.inputSchema["properties"]


# ============================================================================
# Tool Annotations Tests
# ============================================================================


class TestToolAnnotations:
    """Tests for tool annotations."""

    def test_tool_annotations_defined(self):
        """Test tool annotations are defined."""
        from axom_mcp.server import TOOL_ANNOTATIONS

        assert TOOL_ANNOTATIONS is not None
        assert len(TOOL_ANNOTATIONS) == 5

    def test_memory_tool_annotations(self):
        """Test memory tool annotations."""
        from axom_mcp.server import TOOL_ANNOTATIONS

        memory_ann = TOOL_ANNOTATIONS["memory"]
        assert memory_ann["readOnlyHint"] is False
        assert memory_ann["destructiveHint"] is True
        assert memory_ann["idempotentHint"] is False
        assert memory_ann["openWorldHint"] is False

    def test_exec_tool_annotations(self):
        """Test exec tool annotations."""
        from axom_mcp.server import TOOL_ANNOTATIONS

        exec_ann = TOOL_ANNOTATIONS["exec"]
        assert exec_ann["readOnlyHint"] is False
        assert exec_ann["destructiveHint"] is True
        assert exec_ann["idempotentHint"] is False
        assert exec_ann["openWorldHint"] is True

    def test_analyze_tool_annotations(self):
        """Test analyze tool annotations."""
        from axom_mcp.server import TOOL_ANNOTATIONS

        analyze_ann = TOOL_ANNOTATIONS["analyze"]
        assert analyze_ann["readOnlyHint"] is True
        assert analyze_ann["destructiveHint"] is False
        assert analyze_ann["idempotentHint"] is True
        assert analyze_ann["openWorldHint"] is False

    def test_discover_tool_annotations(self):
        """Test discover tool annotations."""
        from axom_mcp.server import TOOL_ANNOTATIONS

        discover_ann = TOOL_ANNOTATIONS["discover"]
        assert discover_ann["readOnlyHint"] is True
        assert discover_ann["destructiveHint"] is False
        assert discover_ann["idempotentHint"] is True
        assert discover_ann["openWorldHint"] is False

    def test_transform_tool_annotations(self):
        """Test transform tool annotations."""
        from axom_mcp.server import TOOL_ANNOTATIONS

        transform_ann = TOOL_ANNOTATIONS["transform"]
        assert transform_ann["readOnlyHint"] is True
        assert transform_ann["destructiveHint"] is False
        assert transform_ann["idempotentHint"] is True
        assert transform_ann["openWorldHint"] is False


# ============================================================================
# Server Creation Tests
# ============================================================================


class TestServerCreation:
    """Tests for server creation."""

    def test_create_server(self):
        """Test creating the MCP server."""
        from axom_mcp.server import create_server

        server = create_server()

        assert server is not None
        assert server.name == "axom"

    def test_create_server_returns_server_instance(self):
        """Test create_server returns a Server instance."""
        from axom_mcp.server import create_server
        from mcp.server import Server

        server = create_server()

        assert isinstance(server, Server)


# ============================================================================
# Resource Template Tests
# ============================================================================


class TestResourceTemplates:
    """Tests for MCP resource templates."""

    def test_memory_resource_template_defined(self):
        """Test memory resource template is defined."""
        from axom_mcp.server import MEMORY_RESOURCE_TEMPLATE

        assert MEMORY_RESOURCE_TEMPLATE is not None

    def test_memory_resource_template_uri(self):
        """Test memory resource template URI."""
        from axom_mcp.server import MEMORY_RESOURCE_TEMPLATE

        assert "memory://{name}" in str(MEMORY_RESOURCE_TEMPLATE.uriTemplate)

    def test_memory_type_resource_template_defined(self):
        """Test memory type resource template is defined."""
        from axom_mcp.server import MEMORY_TYPE_RESOURCE_TEMPLATE

        assert MEMORY_TYPE_RESOURCE_TEMPLATE is not None

    def test_memory_type_resource_template_uri(self):
        """Test memory type resource template URI."""
        from axom_mcp.server import MEMORY_TYPE_RESOURCE_TEMPLATE

        assert "memory://type/{type}" in str(MEMORY_TYPE_RESOURCE_TEMPLATE.uriTemplate)

    def test_memory_tag_resource_template_defined(self):
        """Test memory tag resource template is defined."""
        from axom_mcp.server import MEMORY_TAG_RESOURCE_TEMPLATE

        assert MEMORY_TAG_RESOURCE_TEMPLATE is not None

    def test_memory_tag_resource_template_uri(self):
        """Test memory tag resource template URI."""
        from axom_mcp.server import MEMORY_TAG_RESOURCE_TEMPLATE

        assert "memory://tag/{tag}" in str(MEMORY_TAG_RESOURCE_TEMPLATE.uriTemplate)


# ============================================================================
# Prompt Template Tests
# ============================================================================


class TestPromptTemplates:
    """Tests for MCP prompt templates."""

    def test_prompts_defined(self):
        """Test prompts are defined."""
        from axom_mcp.server import PROMPTS

        assert PROMPTS is not None
        assert len(PROMPTS) >= 3

    def test_memory_workflow_prompt_exists(self):
        """Test memory-workflow prompt exists."""
        from axom_mcp.server import PROMPTS

        prompt_names = [p.name for p in PROMPTS]
        assert "memory-workflow" in prompt_names

    def test_debug_session_prompt_exists(self):
        """Test debug-session prompt exists."""
        from axom_mcp.server import PROMPTS

        prompt_names = [p.name for p in PROMPTS]
        assert "debug-session" in prompt_names

    def test_code_review_prompt_exists(self):
        """Test code-review prompt exists."""
        from axom_mcp.server import PROMPTS

        prompt_names = [p.name for p in PROMPTS]
        assert "code-review" in prompt_names

    def test_prompts_have_descriptions(self):
        """Test all prompts have descriptions."""
        from axom_mcp.server import PROMPTS

        for prompt in PROMPTS:
            assert prompt.description is not None
            assert len(prompt.description) > 0


# ============================================================================
# Module Exports Tests
# ============================================================================


class TestModuleExports:
    """Tests for module exports."""

    def test_create_server_exported(self):
        """Test create_server is exported."""
        from axom_mcp import create_server

        assert callable(create_server)

    def test_main_exported(self):
        """Test main is exported."""
        from axom_mcp import main

        assert callable(main)

    def test_run_server_exported(self):
        """Test run_server is exported."""
        from axom_mcp import run_server

        assert callable(run_server)

    def test_version_defined(self):
        """Test __version__ is defined."""
        from axom_mcp import __version__

        assert __version__ == "2.0.0"


# ============================================================================
# Drift Detection Tests
# ============================================================================


class TestServerDriftDetection:
    """Tests for detecting drift in server behavior."""

    @pytest.mark.drift
    def test_tool_count_unchanged(self):
        """Test that tool count hasn't drifted from expected."""
        from axom_mcp.server import TOOLS

        assert len(TOOLS) == 5, f"Tool count drifted: expected 5, got {len(TOOLS)}"

    @pytest.mark.drift
    def test_tool_names_unchanged(self):
        """Test that tool names haven't drifted from expected."""
        from axom_mcp.server import TOOLS

        expected = {
            "axom_mcp_memory",
            "axom_mcp_exec",
            "axom_mcp_analyze",
            "axom_mcp_discover",
            "axom_mcp_transform",
        }
        actual = {t.name for t in TOOLS}

        assert actual == expected, f"Tool names drifted: {actual} != {expected}"

    @pytest.mark.drift
    def test_memory_actions_unchanged(self):
        """Test that memory actions haven't drifted from expected."""
        from axom_mcp.server import TOOLS

        memory_tool = next(t for t in TOOLS if t.name == "axom_mcp_memory")
        actions = memory_tool.inputSchema["properties"]["action"]["enum"]
        expected = ["read", "write", "list", "search", "delete"]

        assert set(actions) == set(expected), (
            f"Memory actions drifted: {actions} != {expected}"
        )

    @pytest.mark.drift
    def test_memory_types_unchanged(self):
        """Test that memory types haven't drifted from expected."""
        from axom_mcp.server import TOOLS

        memory_tool = next(t for t in TOOLS if t.name == "axom_mcp_memory")
        types = memory_tool.inputSchema["properties"]["memory_type"]["enum"]
        expected = ["long_term", "short_term", "reflex", "dreams"]

        assert set(types) == set(expected), (
            f"Memory types drifted: {types} != {expected}"
        )

    @pytest.mark.drift
    def test_importance_levels_unchanged(self):
        """Test that importance levels haven't drifted from expected."""
        from axom_mcp.server import TOOLS

        memory_tool = next(t for t in TOOLS if t.name == "axom_mcp_memory")
        levels = memory_tool.inputSchema["properties"]["importance"]["enum"]
        expected = ["critical", "important", "normal", "low"]

        assert set(levels) == set(expected), (
            f"Importance levels drifted: {levels} != {expected}"
        )

    @pytest.mark.drift
    def test_exec_operations_unchanged(self):
        """Test that exec operations haven't drifted from expected."""
        from axom_mcp.server import TOOLS

        exec_tool = next(t for t in TOOLS if t.name == "axom_mcp_exec")
        ops = exec_tool.inputSchema["properties"]["operation"]["enum"]
        expected = ["read", "write", "shell"]

        assert set(ops) == set(expected), (
            f"Exec operations drifted: {ops} != {expected}"
        )

    @pytest.mark.drift
    def test_analyze_types_unchanged(self):
        """Test that analyze types haven't drifted from expected."""
        from axom_mcp.server import TOOLS

        analyze_tool = next(t for t in TOOLS if t.name == "axom_mcp_analyze")
        types = analyze_tool.inputSchema["properties"]["type"]["enum"]
        expected = ["debug", "review", "audit", "refactor", "test"]

        assert set(types) == set(expected), (
            f"Analyze types drifted: {types} != {expected}"
        )

    @pytest.mark.drift
    def test_analyze_depths_unchanged(self):
        """Test that analyze depths haven't drifted from expected."""
        from axom_mcp.server import TOOLS

        analyze_tool = next(t for t in TOOLS if t.name == "axom_mcp_analyze")
        depths = analyze_tool.inputSchema["properties"]["depth"]["enum"]
        expected = ["minimal", "low", "medium", "high", "max"]

        assert set(depths) == set(expected), (
            f"Analyze depths drifted: {depths} != {expected}"
        )

    @pytest.mark.drift
    def test_discover_domains_unchanged(self):
        """Test that discover domains haven't drifted from expected."""
        from axom_mcp.server import TOOLS

        discover_tool = next(t for t in TOOLS if t.name == "axom_mcp_discover")
        domains = discover_tool.inputSchema["properties"]["domain"]["enum"]
        expected = ["files", "tools", "memory", "capabilities", "all"]

        assert set(domains) == set(expected), (
            f"Discover domains drifted: {domains} != {expected}"
        )

    @pytest.mark.drift
    def test_transform_formats_unchanged(self):
        """Test that transform formats haven't drifted from expected."""
        from axom_mcp.server import TOOLS

        transform_tool = next(t for t in TOOLS if t.name == "axom_mcp_transform")
        formats = transform_tool.inputSchema["properties"]["output_format"]["enum"]
        expected = ["json", "yaml", "csv", "markdown", "code"]

        assert set(formats) == set(expected), (
            f"Transform formats drifted: {formats} != {expected}"
        )

    @pytest.mark.drift
    def test_tool_annotations_keys_unchanged(self):
        """Test that tool annotation keys haven't drifted."""
        from axom_mcp.server import TOOL_ANNOTATIONS

        expected_keys = {"memory", "exec", "analyze", "discover", "transform"}
        actual_keys = set(TOOL_ANNOTATIONS.keys())

        assert actual_keys == expected_keys, (
            f"Tool annotation keys drifted: {actual_keys} != {expected_keys}"
        )

    @pytest.mark.drift
    def test_annotation_properties_unchanged(self):
        """Test that annotation properties haven't drifted."""
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
                f"{tool_name} annotation props drifted: {actual_props} != {expected_props}"
            )
