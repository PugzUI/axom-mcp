"""Verify Axom SQLite connectivity and required schema objects."""

from __future__ import annotations

import asyncio
import os
import sys

from axom_mcp.database import close_db_manager, get_db_manager


async def _run() -> int:
    db_path = os.getenv("AXOM_DB_PATH", os.path.expanduser("~/.axom/axom.db"))

    try:
        db = await get_db_manager()
        conn = db._get_conn()

        required_tables = {"memories", "memories_fts", "memory_access_log"}
        async with conn.execute(
            "SELECT name FROM sqlite_master WHERE type IN ('table', 'view')"
        ) as cursor:
            names = {row[0] for row in await cursor.fetchall()}

        missing = sorted(required_tables - names)
        if missing:
            print(f"[ERROR] Database verification failed for: {db_path}")
            print(f"[ERROR] Missing schema objects: {', '.join(missing)}")
            return 1

        print(f"[OK] Database verified: {db_path}")
        print(f"[OK] Schema objects present: {', '.join(sorted(required_tables))}")
        return 0
    except Exception as exc:
        print(f"[ERROR] Database verification failed for: {db_path}")
        print(f"[ERROR] {exc}")
        return 1
    finally:
        await close_db_manager()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_run()))
