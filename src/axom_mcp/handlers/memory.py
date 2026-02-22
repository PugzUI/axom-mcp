"""Memory tool handler for Axom MCP.

This module handles all memory operations:
- write: Store a new memory
- read: Retrieve a specific memory by name
- list: List memories with optional filters
- search: Full-text search across memories
- delete: Remove a memory by name
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict

from ..database import get_db_manager
from ..schemas import ImportanceLevel, MemoryInput, MemoryType

logger = logging.getLogger(__name__)


async def handle_memory(arguments: Dict[str, Any]) -> str:
    """Handle axom_mcp_memory tool calls.

    Args:
        arguments: Tool arguments containing action and parameters

    Returns:
        JSON string with operation result
    """
    # Validate input
    input_data = MemoryInput(**arguments)
    action = input_data.action

    db = await get_db_manager()

    if action == "write":
        return await _handle_write(input_data, db)
    elif action == "read":
        return await _handle_read(input_data, db)
    elif action == "list":
        return await _handle_list(input_data, db)
    elif action == "search":
        return await _handle_search(input_data, db)
    elif action == "delete":
        return await _handle_delete(input_data, db)
    elif action == "associate":
        return await _handle_associate(input_data, db)
    else:
        return json.dumps({"error": f"Unknown action: {action}"})


async def _handle_write(input_data: MemoryInput, db) -> str:
    """Write a new memory."""
    if not input_data.name:
        return json.dumps({"error": "name is required for write action"})
    if not input_data.content:
        return json.dumps({"error": "content is required for write action"})

    memory_type = input_data.memory_type or MemoryType.LONG_TERM
    importance = input_data.importance or ImportanceLevel.NORMAL

    try:
        memory_id = await db.create_memory(
            name=input_data.name,
            content=input_data.content,
            memory_type=(
                memory_type.value
                if isinstance(memory_type, MemoryType)
                else memory_type
            ),
            importance=(
                importance.value
                if isinstance(importance, ImportanceLevel)
                else importance
            ),
            tags=input_data.tags,
            source_agent=input_data.source_agent,
            expires_in_days=input_data.expires_in_days,
        )
        return json.dumps(
            {
                "success": True,
                "id": str(memory_id),
                "name": input_data.name,
                "message": f"Memory '{input_data.name}' stored successfully",
            }
        )
    except Exception as e:
        logger.error(f"Failed to write memory: {e}")
        return json.dumps({"error": str(e)})


async def _handle_read(input_data: MemoryInput, db) -> str:
    """Read a memory by name including associated memories."""
    if not input_data.name:
        return json.dumps({"error": "name is required for read action"})

    try:
        memory = await db.get_memory_by_name(input_data.name)
        if memory is None:
            return json.dumps({"error": f"Memory not found: {input_data.name}"})

        # Get associated memories with 1-level extension
        associated_memories = await db.get_associated_memories(str(memory["id"]))

        # Format associated memories
        formatted_associations = []
        for assoc in associated_memories:
            formatted_associations.append(
                {
                    "id": str(assoc["id"]),
                    "name": assoc["name"],
                    "memory_type": assoc["memory_type"],
                    "importance": assoc["importance"],
                    "tags": assoc.get("tags", []),
                    "created_at": (
                        assoc["created_at"].isoformat()
                        if assoc.get("created_at")
                        else None
                    ),
                }
            )

        return json.dumps(
            {
                "success": True,
                "memory": {
                    "id": str(memory["id"]),
                    "name": memory["name"],
                    "content": memory["content"],
                    "memory_type": memory["memory_type"],
                    "importance": memory["importance"],
                    "tags": memory.get("tags", []),
                    "source_agent": memory.get("source_agent"),
                    "parent_memory_id": memory.get("parent_memory_id"),
                    "created_at": (
                        memory["created_at"].isoformat()
                        if memory.get("created_at")
                        else None
                    ),
                    "updated_at": (
                        memory["updated_at"].isoformat()
                        if memory.get("updated_at")
                        else None
                    ),
                    "associated_memories": formatted_associations,
                },
            }
        )
    except Exception as e:
        logger.error(f"Failed to read memory: {e}")
        return json.dumps({"error": str(e)})


async def _handle_list(input_data: MemoryInput, db) -> str:
    """List memories with optional filters."""
    limit = input_data.limit or 50

    try:
        memory_type = None
        if input_data.memory_type:
            memory_type = (
                input_data.memory_type.value
                if isinstance(input_data.memory_type, MemoryType)
                else input_data.memory_type
            )

        importance = None
        if input_data.importance:
            importance = (
                input_data.importance.value
                if isinstance(input_data.importance, ImportanceLevel)
                else input_data.importance
            )

        memories = await db.list_memories(
            memory_type=memory_type,
            importance=importance,
            limit=limit,
        )

        return json.dumps(
            {
                "success": True,
                "count": len(memories),
                "memories": [
                    {
                        "name": m["name"],
                        "memory_type": m["memory_type"],
                        "importance": m["importance"],
                        "tags": m.get("tags", []),
                        "created_at": (
                            m["created_at"].isoformat() if m.get("created_at") else None
                        ),
                    }
                    for m in memories
                ],
            }
        )
    except Exception as e:
        logger.error(f"Failed to list memories: {e}")
        return json.dumps({"error": str(e)})


async def _handle_search(input_data: MemoryInput, db) -> str:
    """Search memories by query."""
    if not input_data.query:
        return json.dumps({"error": "query is required for search action"})

    limit = input_data.limit or 10

    try:
        memory_type = None
        if input_data.memory_type:
            memory_type = (
                input_data.memory_type.value
                if isinstance(input_data.memory_type, MemoryType)
                else input_data.memory_type
            )

        importance = None
        if input_data.importance:
            importance = (
                input_data.importance.value
                if isinstance(input_data.importance, ImportanceLevel)
                else input_data.importance
            )

        memories = await db.search_memories(
            query=input_data.query,
            memory_type=memory_type,
            importance=importance,
            tags=input_data.tags,
            limit=limit,
        )

        return json.dumps(
            {
                "success": True,
                "query": input_data.query,
                "count": len(memories),
                "results": [
                    {
                        "name": m["name"],
                        "content": (
                            m["content"][:500] + "..."
                            if len(m["content"]) > 500
                            else m["content"]
                        ),
                        "memory_type": m["memory_type"],
                        "importance": m["importance"],
                        "relevance": m.get("rank", 0),
                    }
                    for m in memories
                ],
            }
        )
    except Exception as e:
        logger.error(f"Failed to search memories: {e}")
        return json.dumps({"error": str(e)})


async def _handle_delete(input_data: MemoryInput, db) -> str:
    """Delete a memory by name."""
    if not input_data.name:
        return json.dumps({"error": "name is required for delete action"})

    try:
        deleted = await db.delete_memory(input_data.name)
        if deleted:
            return json.dumps(
                {
                    "success": True,
                    "message": f"Memory '{input_data.name}' deleted successfully",
                }
            )
        else:
            return json.dumps({"error": f"Memory not found: {input_data.name}"})
    except Exception as e:
        logger.error(f"Failed to delete memory: {e}")
        return json.dumps({"error": str(e)})


async def _handle_associate(input_data: MemoryInput, db) -> str:
    """Create a simple association between memories using UUID arrays."""
    if not input_data.name:
        return json.dumps(
            {"error": "name (source memory) is required for associate action"}
        )
    if not input_data.target_memory_name:
        return json.dumps(
            {"error": "target_memory_name is required for associate action"}
        )

    try:
        source_memory = await db.get_memory_by_name(input_data.name)
        if not source_memory:
            return json.dumps({"error": f"Source memory not found: {input_data.name}"})

        target_memory = await db.get_memory_by_name(input_data.target_memory_name)
        if not target_memory:
            return json.dumps(
                {"error": f"Target memory not found: {input_data.target_memory_name}"}
            )

        # Add target memory ID to source memory's associated_memories array
        success = await db.add_association(
            source_id=source_memory["id"], target_id=target_memory["id"]
        )

        if success:
            return json.dumps(
                {
                    "success": True,
                    "message": f"Associated '{input_data.name}' with '{input_data.target_memory_name}'",
                }
            )
        else:
            return json.dumps({"error": "Failed to create association"})
    except Exception as e:
        logger.error(f"Failed to associate memories: {e}")
        return json.dumps({"error": str(e)})
