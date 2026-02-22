"""Axom Database Layer - SQLite integration for persistent memory storage.

This module provides the database layer for Axom MCP, handling all
SQLite operations for memory storage and retrieval.
Migrated from PostgreSQL to SQLite for simplified deployment.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

import aiosqlite
import asyncio

logger = logging.getLogger(__name__)


class MemoryType(str, Enum):
    """Axom memory types.

    Each type serves a specific purpose in the memory hierarchy:
    - long_term: Reusable patterns, decisions, facts
    - short_term: Task-specific context, working memory
    - reflex: Learned heuristics, "always check X before Y" patterns
    - dreams: Experimental ideas, creative explorations
    """

    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"
    REFLEX = "reflex"
    DREAMS = "dreams"


class ImportanceLevel(str, Enum):
    """Memory importance levels for prioritization."""

    CRITICAL = "critical"
    IMPORTANT = "important"
    NORMAL = "normal"
    LOW = "low"


class MemoryStatus(str, Enum):
    """Memory status for lifecycle management."""

    ACTIVE = "active"
    ARCHIVED = "archived"
    FORGOTTEN = "forgotten"
    DELETED = "deleted"


@dataclass
class Memory:
    """Represents an Axom memory entry in the database."""

    id: str
    name: Optional[str] = None
    memory_type: MemoryType = MemoryType.SHORT_TERM
    importance: ImportanceLevel = ImportanceLevel.NORMAL
    status: MemoryStatus = MemoryStatus.ACTIVE
    content: str = ""
    summary: Optional[str] = None
    tags: List[str] = None
    source_agent: Optional[str] = None
    source_context: Optional[str] = None
    source_tool: Optional[str] = None
    parent_memory_id: Optional[str] = None
    associated_memories: List[str] = None
    metadata: Dict[str, Any] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    accessed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    access_count: int = 0

    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.associated_memories is None:
            self.associated_memories = []
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert memory to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "memory_type": self.memory_type.value
            if isinstance(self.memory_type, MemoryType)
            else self.memory_type,
            "importance": self.importance.value
            if isinstance(self.importance, ImportanceLevel)
            else self.importance,
            "status": self.status.value
            if isinstance(self.status, MemoryStatus)
            else self.status,
            "content": self.content,
            "summary": self.summary,
            "tags": self.tags,
            "source_agent": self.source_agent,
            "source_context": self.source_context,
            "source_tool": self.source_tool,
            "parent_memory_id": self.parent_memory_id,
            "associated_memories": self.associated_memories,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "accessed_at": self.accessed_at.isoformat() if self.accessed_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "access_count": self.access_count,
        }


class DatabaseManager:
    """Manages Axom SQLite database connections and operations."""

    # Default expiration in days for each memory type
    DEFAULT_EXPIRATION = {
        "short_term": 30,  # 1 month
        "long_term": 365,  # 12 months
        "reflex": 90,  # 3 months
        "dreams": 180,  # 6 months
    }

    def __init__(self, database_path: str):
        self.database_path = database_path
        self.conn: Optional[aiosqlite.Connection] = None

        # Load expiration configuration from environment
        self.expiration_days = {
            "short_term": int(
                os.getenv(
                    "AXOM_EXPIRE_SHORT_TERM", self.DEFAULT_EXPIRATION["short_term"]
                )
            ),
            "long_term": int(
                os.getenv("AXOM_EXPIRE_LONG_TERM", self.DEFAULT_EXPIRATION["long_term"])
            ),
            "reflex": int(
                os.getenv("AXOM_EXPIRE_REFLEX", self.DEFAULT_EXPIRATION["reflex"])
            ),
            "dreams": int(
                os.getenv("AXOM_EXPIRE_DREAMS", self.DEFAULT_EXPIRATION["dreams"])
            ),
        }

    async def initialize(self) -> None:
        """Initialize Axom database connection."""
        try:
            # Ensure directory exists
            db_dir = os.path.dirname(self.database_path)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir)

            self.conn = await aiosqlite.connect(self.database_path)
            # Enable row_factory for dict-like access
            self.conn.row_factory = aiosqlite.Row
            logger.info(f"Axom database connection initialized: {self.database_path}")

            # Ensure database schema exists
            await self.ensure_schema()

        except Exception as e:
            logger.error(f"Failed to initialize Axom database: {e}")
            raise

    async def ensure_schema(self) -> None:
        """Ensure the Axom database schema exists."""
        
        # Read schema from axom_db_sqlite.sql file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(current_dir))
        schema_path = os.path.join(project_root, "axom_db_sqlite.sql")

        try:
            with open(schema_path, "r", encoding='utf-8') as f:
                schema_sql = f.read()
        except FileNotFoundError:
            logger.error(f"Schema file not found at {schema_path}")
            raise

        # executescript is synchronous in standard sqlite3, 
        # but aiosqlite provides an async version.
        try:
            await self.conn.executescript(schema_sql)
        except Exception as e:
            # Ignore some expected errors (e.g., table already exists)
            if "already exists" not in str(e).lower():
                logger.warning(f"Schema statement warning: {e}")

        await self.conn.commit()
        logger.info("Database schema ensured from axom_db_sqlite.sql")

    async def close(self) -> None:
        """Close database connection."""
        if self.conn:
            await self.conn.close()
            logger.info("Database connection closed")

    async def create_memory(
        self,
        name: str,
        content: str,
        memory_type: str = "long_term",
        importance: str = "normal",
        tags: Optional[List[str]] = None,
        source_agent: Optional[str] = None,
        source_context: Optional[str] = None,
        source_tool: Optional[str] = None,
        parent_memory_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        expires_in_days: Optional[int] = None,
    ) -> str:
        """Create a new memory in the database.

        Args:
            name: Unique identifier for the memory
            content: Memory content
            memory_type: Type of memory (long_term, short_term)
            importance: Importance level (critical, important, normal, low)
            tags: List of tags for categorization
            source_agent: Identifier of the agent creating this memory
            source_context: Context information
            source_tool: Tool that created this memory
            parent_memory_id: Optional parent memory ID
            metadata: Additional metadata
            expires_in_days: Optional expiration time in days

        Returns:
            ID (UUID string) of the created memory
        """
        if tags is None:
            tags = []
        if metadata is None:
            metadata = {}

        # Generate UUID
        memory_id = str(uuid.uuid4())

        # Determine expiration: explicit value takes precedence, otherwise use type default
        expires_at = None
        if expires_in_days:
            # Explicit expiration specified in days
            expires_at = (datetime.now(timezone.utc) + timedelta(days=expires_in_days)).isoformat()
        elif self.expiration_days.get(memory_type, 0) > 0:
            # Use default expiration for memory type
            expires_at = (datetime.now(timezone.utc) + timedelta(
                days=self.expiration_days[memory_type]
            )).isoformat()

        # Normalize and sort tags for consistent storage
        if tags:
            tags = sorted([tag.lower() for tag in tags])

        # Serialize to JSON strings
        tags_json = json.dumps(tags)
        metadata_json = json.dumps(metadata)

        now = datetime.now(timezone.utc).isoformat()

        await self.conn.execute(
            """
            INSERT INTO memories (
                id, name, memory_type, importance, content, tags, source_agent,
                source_context, source_tool, parent_memory_id, metadata, expires_at,
                created_at, updated_at, accessed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                memory_id,
                name,
                memory_type,
                importance,
                content,
                tags_json,
                source_agent,
                source_context,
                source_tool,
                parent_memory_id,
                metadata_json,
                expires_at,
                now,
                now,
                now,
            ),
        )
        await self.conn.commit()

        logger.info(f"Created memory '{name}' with ID {memory_id}")
        return memory_id

    async def get_memory(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a memory by ID."""
        async with self.conn.execute(
            "SELECT * FROM memories WHERE id = ? AND status = 'active'",
            (memory_id,),
        ) as cursor:
            row = await cursor.fetchone()

        if row:
            await self._update_access(memory_id)
            return self._row_to_dict(row)
        return None

    async def get_memory_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Retrieve a memory by name."""
        async with self.conn.execute(
            "SELECT * FROM memories WHERE name = ? AND status = 'active'",
            (name,),
        ) as cursor:
            row = await cursor.fetchone()

        if row:
            await self._update_access(str(row["id"]))
            return self._row_to_dict(row)
        return None

    async def list_memories(
        self,
        memory_type: Optional[str] = None,
        importance: Optional[str] = None,
        tags: Optional[List[str]] = None,
        source_agent: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """List memories with optional filtering."""

        conditions = ["status = 'active'"]
        params = []

        if memory_type:
            conditions.append("memory_type = ?")
            params.append(memory_type)

        if importance:
            conditions.append("importance = ?")
            params.append(importance)

        if tags:
            # For SQLite, we check if any of the provided tags exist in the JSON array
            # This is a simplified approach - check each tag in Python
            pass  # We'll filter in Python for tag matching

        if source_agent:
            conditions.append("source_agent = ?")
            params.append(source_agent)

        params.append(limit)

        query = f"""
            SELECT * FROM memories
            WHERE {" AND ".join(conditions)}
            ORDER BY created_at DESC, id DESC
            LIMIT ?
        """

        async with self.conn.execute(query, params) as cursor:
            rows = await cursor.fetchall()

        results = [self._row_to_dict(row) for row in rows]

        # Filter by tags if provided (since JSON array matching is complex in SQLite)
        if tags:
            results = [
                r for r in results
                if any(tag.lower() in [t.lower() for t in r.get("tags", [])] for tag in tags)
            ]

        return results

    async def search_memories(
        self,
        query: str,
        memory_type: Optional[str] = None,
        importance: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Search memories by content using FTS5."""

        # Use FTS5 for full-text search
        conditions = ["m.status = 'active'"]
        params = []

        # Join with FTS table
        fts_query = "memories_fts MATCH ?"
        params.append(query)

        if memory_type:
            conditions.append("m.memory_type = ?")
            params.append(memory_type)

        if importance:
            conditions.append("m.importance = ?")
            params.append(importance)

        params.append(limit)

        # Use FTS5 with bm25 ranking
        sql_query = f"""
            SELECT m.*, bm25(memories_fts) as rank
            FROM memories m
            JOIN memories_fts fts ON m.id = fts.id
            WHERE {fts_query} AND {" AND ".join(conditions)}
            ORDER BY rank
            LIMIT ?
        """

        async with self.conn.execute(sql_query, params) as cursor:
            rows = await cursor.fetchall()

        results = [self._row_to_dict(row) for row in rows]

        # Filter by tags if provided
        if tags:
            results = [
                r for r in results
                if any(tag.lower() in [t.lower() for t in r.get("tags", [])] for tag in tags)
            ]

        return results

    async def update_memory(
        self,
        memory_id: str,
        content: Optional[str] = None,
        importance: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Update an existing memory."""

        updates = []
        params = []

        if content is not None:
            updates.append("content = ?")
            params.append(content)

        if importance is not None:
            updates.append("importance = ?")
            params.append(importance)

        if tags is not None:
            updates.append("tags = ?")
            params.append(json.dumps(tags))

        if metadata is not None:
            updates.append("metadata = ?")
            params.append(json.dumps(metadata))

        if not updates:
            return await self.get_memory(memory_id)

        # Add updated_at timestamp
        updates.append("updated_at = ?")
        params.append(datetime.now(timezone.utc).isoformat())

        params.append(memory_id)

        query = f"""
            UPDATE memories
            SET {", ".join(updates)}
            WHERE id = ? AND status = 'active'
        """

        await self.conn.execute(query, params)
        await self.conn.commit()

        return await self.get_memory(memory_id)

    async def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory by ID (soft delete by setting status)."""
        cursor = await self.conn.execute(
            "UPDATE memories SET status = 'deleted' WHERE id = ? AND status = 'active'",
            (memory_id,),
        )
        await self.conn.commit()

        return cursor.rowcount > 0

    async def delete_memory_by_name(self, name: str) -> bool:
        """Delete a memory by name (soft delete by setting status)."""
        cursor = await self.conn.execute(
            "UPDATE memories SET status = 'deleted' WHERE name = ? AND status = 'active'",
            (name,),
        )
        await self.conn.commit()

        return cursor.rowcount > 0

    async def cleanup_expired_memories(self) -> Dict[str, Any]:
        """Run the database cleanup process to archive expired memories.

        This method:
        - Archives memories that have passed their expires_at time
        - Permanently deletes memories archived for more than 30 days
        - Removes access logs older than 90 days

        Returns:
            Dictionary with cleanup results
        """
        now = datetime.now(timezone.utc).isoformat()
        thirty_days_ago = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        ninety_days_ago = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()

        # Get counts before cleanup
        async with self.conn.execute(
            "SELECT COUNT(*) FROM memories WHERE expires_at < ? AND status = 'active'",
            (now,),
        ) as cursor:
            expired_before = (await cursor.fetchone())[0]

        async with self.conn.execute(
            "SELECT COUNT(*) FROM memories WHERE status = 'archived' AND updated_at < ?",
            (thirty_days_ago,),
        ) as cursor:
            await cursor.fetchone()

        # Archive expired memories
        await self.conn.execute(
            "UPDATE memories SET status = 'archived' WHERE expires_at < ? AND status = 'active'",
            (now,),
        )

        # Permanently delete old archived memories
        cursor = await self.conn.execute(
            "DELETE FROM memories WHERE status = 'archived' AND updated_at < ?",
            (thirty_days_ago,),
        )
        permanently_deleted = cursor.rowcount

        # Clean up old access logs
        cursor = await self.conn.execute(
            "DELETE FROM memory_access_log WHERE created_at < ?",
            (ninety_days_ago,),
        )
        logs_deleted = cursor.rowcount

        await self.conn.commit()

        return {
            "expired_archived": expired_before,
            "permanently_deleted": permanently_deleted,
            "logs_deleted": logs_deleted,
        }

    async def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        async with self.conn.execute("""
            SELECT
                memory_type,
                importance,
                status,
                COUNT(*) as count
            FROM memories
            GROUP BY memory_type, importance, status
            ORDER BY memory_type, importance, status
        """) as cursor:
            stats = await cursor.fetchall()

        async with self.conn.execute(
            "SELECT COUNT(*) FROM memories WHERE status = 'active'"
        ) as cursor:
            total = (await cursor.fetchone())[0]

        return {"total_active": total, "breakdown": [dict(row) for row in stats]}

    async def add_association(
        self,
        source_id: str,
        target_id: str,
    ) -> bool:
        """Add a memory to another memory's associated_memories list."""
        try:
            # Get current associated_memories
            async with self.conn.execute(
                "SELECT associated_memories FROM memories WHERE id = ?",
                (source_id,),
            ) as cursor:
                row = await cursor.fetchone()

            if not row:
                return False

            # Parse current associations from JSON
            current = []
            if row["associated_memories"]:
                try:
                    current = json.loads(row["associated_memories"])
                except json.JSONDecodeError:
                    pass

            # Add target if not already present
            if target_id not in current:
                current.append(target_id)

            # Update the record
            await self.conn.execute(
                "UPDATE memories SET associated_memories = ? WHERE id = ?",
                (json.dumps(current), source_id),
            )
            await self.conn.commit()

            return True
        except Exception as e:
            logger.error(f"Failed to add association: {e}")
            return False

    async def get_associated_memories(
        self, memory_id: str, include_extended: bool = True
    ) -> List[Dict[str, Any]]:
        """Get associated memories for a memory with optional 1-level extension.

        Args:
            memory_id: Memory ID
            include_extended: Whether to include memories associated with associated memories (1 level deep)

        Returns:
            List of associated memory records
        """
        # Get current associated_memories
        async with self.conn.execute(
            "SELECT associated_memories FROM memories WHERE id = ?",
            (memory_id,),
        ) as cursor:
            row = await cursor.fetchone()

        if not row or not row["associated_memories"]:
            return []

        try:
            associated_ids = json.loads(row["associated_memories"])
        except json.JSONDecodeError:
            return []

        if not associated_ids:
            return []

        # Get direct associations
        placeholders = ",".join(["?"] * len(associated_ids))
        async with self.conn.execute(
            f"SELECT * FROM memories WHERE id IN ({placeholders}) AND status = 'active'",
            associated_ids,
        ) as cursor:
            direct_associations = await cursor.fetchall()

        if not include_extended:
            return [self._row_to_dict(row) for row in direct_associations]

        # Get extended associations (1 level deep)
        extended_associations = []
        for assoc in direct_associations:
            assoc_id = str(assoc["id"])
            async with self.conn.execute(
                "SELECT associated_memories FROM memories WHERE id = ?",
                (assoc_id,),
            ) as cursor:
                assoc_row = await cursor.fetchone()

            if assoc_row and assoc_row["associated_memories"]:
                try:
                    nested_ids = json.loads(assoc_row["associated_memories"])
                    nested_ids = [nid for nid in nested_ids if nid != memory_id]
                    if nested_ids:
                        placeholders = ",".join(["?"] * len(nested_ids))
                        async with self.conn.execute(
                            f"SELECT * FROM memories WHERE id IN ({placeholders}) AND status = 'active'",
                            nested_ids,
                        ) as cursor:
                            nested = await cursor.fetchall()
                        extended_associations.extend(nested)
                except json.JSONDecodeError:
                    pass

        # Combine and deduplicate
        all_associations = list(direct_associations) + extended_associations
        unique_associations = []
        seen_ids = set()
        for assoc in all_associations:
            assoc_id = str(assoc["id"])
            if assoc_id not in seen_ids:
                seen_ids.add(assoc_id)
                unique_associations.append(assoc)

        return [self._row_to_dict(row) for row in unique_associations]

    async def remove_association(
        self,
        source_id: str,
        target_id: str,
    ) -> bool:
        """Remove a memory from another memory's associated_memories list."""
        try:
            # Get current associated_memories
            async with self.conn.execute(
                "SELECT associated_memories FROM memories WHERE id = ?",
                (source_id,),
            ) as cursor:
                row = await cursor.fetchone()

            if not row:
                return False

            # Parse current associations from JSON
            current = []
            if row["associated_memories"]:
                try:
                    current = json.loads(row["associated_memories"])
                except json.JSONDecodeError:
                    pass

            # Remove target if present
            if target_id in current:
                current.remove(target_id)

            # Update the record
            await self.conn.execute(
                "UPDATE memories SET associated_memories = ? WHERE id = ?",
                (json.dumps(current), source_id),
            )
            await self.conn.commit()

            return True
        except Exception as e:
            logger.error(f"Failed to remove association: {e}")
            return False

    async def get_access_log(
        self,
        memory_id: Optional[str] = None,
        accessed_by: Optional[str] = None,
        access_type: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get memory access log entries.

        Args:
            memory_id: Filter by specific memory
            accessed_by: Filter by what accessed the memory
            access_type: Filter by access type
            limit: Maximum number of entries to return

        Returns:
            List of access log entries
        """
        conditions = []
        params = []

        if memory_id:
            conditions.append("mal.memory_id = ?")
            params.append(memory_id)

        if accessed_by:
            conditions.append("mal.accessed_by = ?")
            params.append(accessed_by)

        if access_type:
            conditions.append("mal.access_type = ?")
            params.append(access_type)

        params.append(limit)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else "WHERE 1=1"

        query = f"""
            SELECT mal.*, m.name as memory_name
            FROM memory_access_log mal
            JOIN memories m ON mal.memory_id = m.id
            {where_clause}
            ORDER BY mal.created_at DESC
            LIMIT ?
        """

        async with self.conn.execute(query, params) as cursor:
            rows = await cursor.fetchall()

        return [dict(row) for row in rows]

    async def _update_access(self, memory_id: str) -> None:
        """Update access tracking for a memory."""
        # Insert into access log (trigger will update memories table)
        access_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        await self.conn.execute(
            """
            INSERT INTO memory_access_log (id, memory_id, accessed_by, access_type, created_at)
            VALUES (?, ?, 'system', 'read', ?)
        """,
            (access_id, memory_id, now),
        )
        await self.conn.commit()

    def _row_to_dict(self, row) -> Dict[str, Any]:
        """Convert database row to dictionary."""
        # Parse metadata from JSON
        metadata = {}
        if row["metadata"]:
            try:
                metadata = json.loads(row["metadata"])
            except json.JSONDecodeError:
                metadata = {}

        # Parse tags from JSON
        tags = []
        if row["tags"]:
            try:
                tags = json.loads(row["tags"])
            except json.JSONDecodeError:
                tags = []

        # Parse associated_memories from JSON
        associated_memories = []
        if row.get("associated_memories"):
            try:
                associated_memories = json.loads(row["associated_memories"])
            except json.JSONDecodeError:
                associated_memories = []

        # Parse timestamps
        def parse_timestamp(ts):
            if ts is None:
                return None
            try:
                # Handle SQLite datetime format
                return datetime.fromisoformat(str(ts))
            except (ValueError, TypeError):
                return None

        return {
            "id": str(row["id"]),
            "name": row["name"],
            "memory_type": row["memory_type"],
            "importance": row["importance"],
            "status": row["status"],
            "content": row["content"],
            "summary": row["summary"],
            "tags": tags,
            "source_agent": row["source_agent"],
            "source_context": row["source_context"],
            "source_tool": row["source_tool"],
            "parent_memory_id": str(row["parent_memory_id"])
            if row.get("parent_memory_id")
            else None,
            "associated_memories": associated_memories,
            "metadata": metadata,
            "created_at": str(row["created_at"]) if row["created_at"] else None,
            "updated_at": str(row["updated_at"]) if row["updated_at"] else None,
            "accessed_at": str(row["accessed_at"]) if row["accessed_at"] else None,
            "expires_at": str(row["expires_at"]) if row["expires_at"] else None,
            "access_count": row["access_count"],
        }


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None
_db_manager_lock = asyncio.Lock()


async def get_db_manager() -> DatabaseManager:
    """Get or create the global database manager."""
    global _db_manager

    if _db_manager is None:
        async with _db_manager_lock:
            # Check for explicit path first
            db_path = os.getenv("AXOM_DB_PATH")
            
            if not db_path:
                # Use default path: ~/.axom/axom.db
                home = os.path.expanduser("~")
                db_dir = os.path.join(home, ".axom")
                db_path = os.path.join(db_dir, "axom.db")

            # Normalize path for Windows
            db_path = os.path.normpath(db_path)

            _db_manager = DatabaseManager(db_path)
            await _db_manager.initialize()

    return _db_manager


async def close_db_manager() -> None:
    """Close the global database manager."""
    global _db_manager
    if _db_manager:
        await _db_manager.close()
        _db_manager = None
