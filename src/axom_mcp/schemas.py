"""Pydantic models for Axom MCP tools.

This module defines all input/output schemas for the MCP tools with
comprehensive validation using Pydantic v2.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class MemoryType(StrEnum):
    """Axom memory types.

    Each type serves a specific purpose in the memory hierarchy:
    - long_term: Reusable patterns, decisions, facts
    - short_term: Task-specific context, working memory
    - reflex: Learned heuristics, "always check X before Y" patterns
    - dreams: Experimental ideas, creative explorations
    """

    LONG_TERM = "long_term"
    SHORT_TERM = "short_term"
    REFLEX = "reflex"
    DREAMS = "dreams"


class ImportanceLevel(StrEnum):
    """Memory importance levels for prioritization.

    Used to rank memories for retrieval and cleanup:
    - low: Useful but not essential
    - high: High value, should be preserved
    - critical: Must never be deleted, essential knowledge
    """

    LOW = "low"
    HIGH = "high"
    CRITICAL = "critical"


class MemoryWriteInput(BaseModel):
    """Input schema for memory write action."""

    model_config = {"extra": "forbid"}

    action: str = Field(default="write", pattern="^write$")
    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Unique identifier for the memory. Format: [type]_[descriptor]_[YYYYMMDD]",
    )
    content: str = Field(
        ...,
        min_length=1,
        max_length=1_000_000,
        description="Memory content. Recommended format: TASK|APPROACH|OUTCOME|GOTCHAS|RELATED",
    )
    memory_type: MemoryType = Field(
        default=MemoryType.LONG_TERM, description="Type of memory storage"
    )
    importance: ImportanceLevel = Field(
        default=ImportanceLevel.HIGH,
        description="Importance level for prioritization",
    )
    tags: list[str] | None = Field(
        default=None, max_length=20, description="Tags for categorization and search"
    )
    source_agent: str | None = Field(
        default=None,
        max_length=255,
        description="Identifier of the agent creating this memory",
    )
    parent_memory_name: str | None = Field(
        default=None, description="Parent memory name for hierarchical structure"
    )

    @field_validator("name")
    @classmethod
    def validate_name_format(cls, v: str) -> str:
        """Validate memory name follows naming convention."""
        parts = v.rsplit("_", 1)
        if len(parts) == 2 and len(parts[1]) == 8 and parts[1].isdigit():
            return v
        # Allow non-standard names but warn in description
        return v


class MemorySearchInput(BaseModel):
    """Input schema for memory search action."""

    model_config = {"extra": "forbid"}

    action: str = Field(default="search", pattern="^search$")
    query: str = Field(
        ..., min_length=1, max_length=1000, description="Search query string"
    )
    memory_type: MemoryType | None = Field(
        default=None, description="Filter by memory type"
    )
    importance: ImportanceLevel | None = Field(
        default=None, description="Filter by importance level"
    )
    tags: list[str] | None = Field(default=None, description="Filter by tags")
    limit: int | None = Field(
        default=10, ge=1, le=100, description="Maximum number of results"
    )


class MemoryReadInput(BaseModel):
    """Input schema for memory read action."""

    model_config = {"extra": "forbid"}

    action: str = Field(default="read", pattern="^read$")
    name: str = Field(
        ..., min_length=1, max_length=255, description="Name of the memory to retrieve"
    )


class MemoryListInput(BaseModel):
    """Input schema for memory list action."""

    model_config = {"extra": "forbid"}

    action: str = Field(default="list", pattern="^list$")
    memory_type: MemoryType | None = Field(
        default=None, description="Filter by memory type"
    )
    importance: ImportanceLevel | None = Field(
        default=None, description="Filter by importance level"
    )
    limit: int | None = Field(
        default=50, ge=1, le=200, description="Maximum number of results"
    )


class MemoryDeleteInput(BaseModel):
    """Input schema for memory delete action."""

    model_config = {"extra": "forbid"}

    action: str = Field(default="delete", pattern="^delete$")
    name: str = Field(
        ..., min_length=1, max_length=255, description="Name of the memory to delete"
    )


class MemoryInput(BaseModel):
    """Unified input schema for axom_mcp_memory tool."""

    model_config = {"extra": "forbid"}

    action: str = Field(
        ...,
        pattern="^(read|write|list|search|delete|associate)$",
        description="Memory operation to perform",
    )
    # Write fields
    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Memory identifier (required for read/write/delete)",
    )
    content: str | None = Field(
        default=None,
        max_length=1_000_000,
        description="Memory content (required for write)",
    )
    memory_type: MemoryType | None = Field(
        default=None, description="Type of memory storage"
    )
    importance: ImportanceLevel | None = Field(
        default=None, description="Importance level"
    )
    tags: list[str] | None = Field(
        default=None, max_length=20, description="Tags for categorization"
    )
    source_agent: str | None = Field(
        default=None, max_length=255, description="Source agent identifier"
    )
    # Association field (simplified)
    target_memory_name: str | None = Field(
        default=None,
        description="Target memory name for association (required for associate action)",
    )
    parent_memory_name: str | None = Field(
        default=None, description="Parent memory name for hierarchical structure"
    )
    # Search/List fields
    query: str | None = Field(
        default=None, max_length=1000, description="Search query (required for search)"
    )
    limit: int | None = Field(
        default=None, ge=1, le=200, description="Maximum results to return"
    )
    expires_in_days: int | None = Field(
        default=None, ge=1, description="Override default expiration in days"
    )


class ExecInput(BaseModel):
    """Input schema for axom_mcp_exec tool."""

    model_config = {"extra": "forbid"}

    operation: str = Field(
        ...,
        pattern="^(read|write|shell)$",
        description="Operation type: read, write, or shell",
    )
    target: str = Field(
        ...,
        min_length=1,
        max_length=4096,
        description="File path for read/write, or command for shell",
    )
    data: str | None = Field(
        default=None,
        max_length=10_000_000,
        description="Data to write (for write operation)",
    )
    chain: list[dict[str, Any]] | None = Field(
        default=None, max_length=10, description="Chain of subsequent operations"
    )


class AnalyzeInput(BaseModel):
    """Input schema for axom_mcp_analyze tool."""

    model_config = {"extra": "forbid"}

    type: str = Field(
        ..., pattern="^(debug|review|audit|refactor|test)$", description="Analysis type"
    )
    target: str = Field(..., min_length=1, description="File path or code to analyze")
    focus: str | None = Field(
        default=None,
        max_length=100,
        description="Focus area (e.g., security, performance)",
    )
    depth: str | None = Field(
        default="medium",
        pattern="^(minimal|low|medium|high|max)$",
        description="Analysis depth level",
    )
    output_format: str | None = Field(
        default="summary",
        pattern="^(summary|detailed|actionable)$",
        description="Output format preference",
    )
    chain: list[dict[str, Any]] | None = Field(
        default=None,
        max_length=10,
        description="Chain operations based on analysis results",
    )


class DiscoverInput(BaseModel):
    """Input schema for axom_mcp_discover tool."""

    model_config = {"extra": "forbid"}

    domain: str = Field(
        ...,
        pattern="^(files|tools|memory|capabilities|all)$",
        description="Discovery domain",
    )
    filter: dict[str, Any] | None = Field(
        default=None, description="Filter criteria (pattern, type, etc.)"
    )
    limit: int | None = Field(
        default=None, ge=1, le=1000, description="Maximum results"
    )
    recursive: bool | None = Field(default=None, description="Recursive discovery")
    chain: list[dict[str, Any]] | None = Field(
        default=None, max_length=10, description="Chain operations based on discovery"
    )


class TransformInput(BaseModel):
    """Input schema for axom_mcp_transform tool."""

    model_config = {"extra": "forbid"}

    input: str = Field(
        ..., min_length=1, max_length=10_000_000, description="Input data to transform"
    )
    input_format: str | None = Field(
        default=None,
        pattern="^(json|yaml|csv|markdown|code)$",
        description="Input format (auto-detected if not specified)",
    )
    output_format: str = Field(
        ..., pattern="^(json|yaml|csv|markdown|code)$", description="Output format"
    )
    rules: list[dict[str, Any]] | None = Field(
        default=None, description="Transformation rules"
    )
    template: str | None = Field(
        default=None, max_length=10000, description="Template for transformation"
    )
    chain: list[dict[str, Any]] | None = Field(
        default=None, max_length=10, description="Chain operations after transformation"
    )


# Response models


class MemoryResponse(BaseModel):
    """Response model for memory operations."""

    success: bool
    id: str | None = None
    name: str | None = None
    content: str | None = None
    memory_type: str | None = None
    importance: str | None = None
    tags: list[str] | None = None
    source_agent: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    message: str | None = None
    error: str | None = None


class MemoryListResponse(BaseModel):
    """Response model for memory list operation."""

    success: bool
    count: int
    memories: list[dict[str, Any]]
    error: str | None = None


class MemorySearchResponse(BaseModel):
    """Response model for memory search operation."""

    success: bool
    query: str
    count: int
    results: list[dict[str, Any]]
    error: str | None = None

    # Association models


# Access log models


class AccessType(StrEnum):
    """Types of memory access."""

    READ = "read"
    WRITE = "write"
    UPDATE = "update"
    DELETE = "delete"
    REFERENCE = "reference"
    SEARCH = "search"


class MemoryAccessLogInput(BaseModel):
    """Input schema for querying memory access logs."""

    model_config = {"extra": "forbid"}

    memory_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Filter by specific memory name",
    )
    accessed_by: str | None = Field(
        default=None, max_length=100, description="Filter by what accessed the memory"
    )
    access_type: AccessType | None = Field(
        default=None, description="Filter by access type"
    )
    limit: int = Field(
        default=50, ge=1, le=200, description="Maximum number of entries to return"
    )


class AccessLogEntry(BaseModel):
    """Model for a single access log entry."""

    id: str
    memory_id: str
    memory_name: str
    accessed_by: str | None = None
    access_type: str
    context: str | None = None
    created_at: str


class AccessLogResponse(BaseModel):
    """Response model for access log operations."""

    success: bool
    count: int
    entries: list[dict[str, Any]]
    error: str | None = None
