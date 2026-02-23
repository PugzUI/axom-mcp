"""Integration tests for database verification and end-to-end memory flows."""

from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

from axom_mcp.database import DatabaseManager, close_db_manager, get_db_manager
from axom_mcp.handlers.discover import handle_discover
from axom_mcp.handlers.exec import handle_exec
from axom_mcp.handlers.memory import handle_memory


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.database
async def test_database_manager_initializes_required_schema(tmp_path):
    """DatabaseManager should create required tables and FTS index."""
    db_path = tmp_path / "integration_schema.db"
    manager = DatabaseManager(str(db_path))

    await manager.initialize()

    conn = manager._get_conn()
    async with conn.execute(
        "SELECT name FROM sqlite_master WHERE type IN ('table', 'view')"
    ) as cursor:
        schema_objects = {row[0] for row in await cursor.fetchall()}

    await manager.close()

    assert "memories" in schema_objects
    assert "memories_fts" in schema_objects
    assert "memory_access_log" in schema_objects


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.database
async def test_memory_handler_round_trip_with_real_sqlite(tmp_path, monkeypatch):
    """Write/read/search/delete should work through handler + real SQLite."""
    db_path = tmp_path / "integration_memory.db"

    await close_db_manager()
    monkeypatch.setenv("AXOM_DB_PATH", str(db_path))

    write_result = json.loads(
        await handle_memory(
            {
                "action": "write",
                "name": "integration_roundtrip_20260223",
                "content": "TASK|Round-trip integration|OUTCOME|success",
                "memory_type": "long_term",
                "importance": "high",
                "tags": ["Integration", "DB"],
                "source_agent": "pytest",
            }
        )
    )
    assert write_result["success"] is True

    read_result = json.loads(
        await handle_memory(
            {
                "action": "read",
                "name": "integration_roundtrip_20260223",
            }
        )
    )
    assert read_result["success"] is True
    assert read_result["memory"]["name"] == "integration_roundtrip_20260223"

    search_result = json.loads(
        await handle_memory(
            {
                "action": "search",
                "query": "round-trip integration",
                "limit": 5,
            }
        )
    )
    assert search_result["success"] is True
    assert search_result["count"] >= 1

    delete_result = json.loads(
        await handle_memory(
            {
                "action": "delete",
                "name": "integration_roundtrip_20260223",
            }
        )
    )
    assert delete_result["success"] is True

    missing_result = json.loads(
        await handle_memory(
            {
                "action": "read",
                "name": "integration_roundtrip_20260223",
            }
        )
    )
    assert "error" in missing_result

    await close_db_manager()


@pytest.mark.integration
@pytest.mark.database
def test_verify_db_script_passes_with_temp_database(tmp_path):
    """scripts/verify_db.py should validate connectivity and schema."""
    db_path = tmp_path / "integration_verify.db"

    env = dict(os.environ)
    env["AXOM_DB_PATH"] = str(db_path)

    result = subprocess.run(
        [sys.executable, "scripts/verify_db.py"],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "[OK] Database verified" in result.stdout


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.database
async def test_database_associations_and_access_log(tmp_path, monkeypatch):
    """Association operations and access-log retrieval should work on real SQLite."""
    db_path = tmp_path / "integration_assoc.db"

    await close_db_manager()
    monkeypatch.setenv("AXOM_DB_PATH", str(db_path))
    db = await get_db_manager()

    source_id = await db.create_memory(
        name="source_assoc_20260223",
        content="source",
        memory_type="long_term",
    )
    target_id = await db.create_memory(
        name="target_assoc_20260223",
        content="target",
        memory_type="short_term",
    )

    assert await db.add_association(source_id, target_id) is True
    associated = await db.get_associated_memories(source_id)
    assert any(m["id"] == target_id for m in associated)

    # Trigger access logging via read path.
    loaded = await db.get_memory(source_id)
    assert loaded is not None

    access_log = await db.get_access_log(memory_id=source_id, limit=10)
    assert len(access_log) >= 1
    assert access_log[0]["memory_id"] == source_id

    assert await db.remove_association(source_id, target_id) is True
    associated_after = await db.get_associated_memories(
        source_id, include_extended=False
    )
    assert all(m["id"] != target_id for m in associated_after)

    # Re-associate and verify delete-by-id prunes stale links.
    assert await db.add_association(source_id, target_id) is True
    assert await db.delete_memory(target_id) is True
    associated_after_delete = await db.get_associated_memories(
        source_id, include_extended=False
    )
    assert all(m["id"] != target_id for m in associated_after_delete)
    async with db.conn.execute(
        "SELECT associated_memories FROM memories WHERE id = ?",
        (source_id,),
    ) as cursor:
        row = await cursor.fetchone()
    assert row is not None
    assert target_id not in json.loads(row["associated_memories"])

    await close_db_manager()


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.database
async def test_database_cleanup_and_stats(tmp_path, monkeypatch):
    """Cleanup should archive expired memories and stats should reflect state."""
    db_path = tmp_path / "integration_cleanup.db"

    await close_db_manager()
    monkeypatch.setenv("AXOM_DB_PATH", str(db_path))
    db = await get_db_manager()

    await db.create_memory(
        name="expired_cleanup_20260223",
        content="expired memory",
        memory_type="short_term",
        expires_in_days=-1,
    )
    await db.create_memory(
        name="active_cleanup_20260223",
        content="active memory",
        memory_type="long_term",
    )
    source_id = await db.create_memory(
        name="cleanup_assoc_source_20260223",
        content="source",
        memory_type="long_term",
    )
    target_expired_id = await db.create_memory(
        name="cleanup_assoc_target_20260223",
        content="target",
        memory_type="long_term",
    )
    assert await db.add_association(source_id, target_expired_id) is True
    await db.conn.execute(
        "UPDATE memories SET expires_at = '2020-01-01T00:00:00+00:00' WHERE id = ?",
        (target_expired_id,),
    )
    await db.conn.commit()

    cleanup = await db.cleanup_expired_memories()
    assert cleanup["expired_deleted"] >= 1

    stats = await db.get_memory_stats()
    assert stats["total_memories"] >= 1

    async with db.conn.execute(
        "SELECT associated_memories FROM memories WHERE id = ?",
        (source_id,),
    ) as cursor:
        row = await cursor.fetchone()
    assert row is not None
    assert target_expired_id not in json.loads(row["associated_memories"])

    await close_db_manager()


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.database
async def test_discover_memory_domain_with_real_db(tmp_path, monkeypatch):
    """Discover memory domain should succeed against initialized SQLite DB."""
    db_path = tmp_path / "integration_discover.db"

    await close_db_manager()
    monkeypatch.setenv("AXOM_DB_PATH", str(db_path))

    # Seed via memory handler to emulate normal data shape.
    write_result = json.loads(
        await handle_memory(
            {
                "action": "write",
                "name": "discover_memory_20260223",
                "content": "TASK|discover memory test|OUTCOME|ok",
                "memory_type": "long_term",
            }
        )
    )
    assert write_result["success"] is True

    discover_result = json.loads(
        await handle_discover({"domain": "memory", "limit": 5})
    )
    assert discover_result["success"] is True
    assert discover_result["domain"] == "memory"
    assert "statistics" in discover_result
    assert "recent_memories" in discover_result

    await close_db_manager()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_exec_respects_read_only_and_path_restrictions(tmp_path, monkeypatch):
    """Exec handler should enforce AXOM_READ_ONLY and path validation."""
    test_file = tmp_path / "exec_guard.txt"

    monkeypatch.setenv("AXOM_READ_ONLY", "1")
    denied_write = json.loads(
        await handle_exec(
            {
                "operation": "write",
                "target": str(test_file),
                "data": "blocked",
            }
        )
    )
    assert "error" in denied_write
    assert "AXOM_READ_ONLY" in denied_write["error"]

    denied_shell = json.loads(
        await handle_exec({"operation": "shell", "target": "echo blocked"})
    )
    assert "error" in denied_shell
    assert "AXOM_READ_ONLY" in denied_shell["error"]

    monkeypatch.delenv("AXOM_READ_ONLY", raising=False)
    invalid_read = json.loads(
        await handle_exec(
            {"operation": "read", "target": "/tmp/definitely_outside_repo.txt"}
        )
    )
    assert "error" in invalid_read
    assert "outside allowed directories" in invalid_read["error"]
