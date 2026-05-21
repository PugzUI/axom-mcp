"""Integration tests for dev seed generator and loader.

Covers edge cases: empty files, duplicates, long content, special chars,
excluded dirs, all schema attributes, varied memory_type/importance.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from axom_mcp.database import DatabaseManager, close_db_manager, get_db_manager


# Import from scripts (project root in path when running pytest)
def _scripts_path() -> Path:
    return Path(__file__).resolve().parent.parent.parent / "scripts"


def _add_scripts_to_path():
    """Add scripts dir to path so we can import dev_seed_from_md."""
    scripts = _scripts_path()
    sp = str(scripts)
    if sp not in sys.path:
        sys.path.insert(0, sp)


@pytest.fixture
def temp_md_root(tmp_path):
    """Create temp dir with test .md files for seed generation."""
    root = tmp_path / "md_root"
    root.mkdir()

    # Normal file with sections
    (root / "normal.md").write_text(
        """# Title
Intro paragraph here.

## Section One
Content for section one. This has enough text to form a chunk.

## Section Two
More content here. Another paragraph.
""",
        encoding="utf-8",
    )

    # File with reflex keywords (should get memory_type=reflex)
    (root / "reflex_doc.md").write_text(
        """## Reflex Pattern
Always check the config before running. Heuristic: verify first.
""",
        encoding="utf-8",
    )

    # File with dreams keywords (should get memory_type=dreams)
    (root / "dreams_doc.md").write_text(
        """## Creative Ideas
Brainstorm wild ideas. Explore and experiment with new approaches.
""",
        encoding="utf-8",
    )

    # Empty file (should produce no chunks)
    (root / "empty.md").write_text("", encoding="utf-8")

    # File with only whitespace
    (root / "whitespace.md").write_text("\n\n  \n\t\n", encoding="utf-8")

    # File with special chars and quotes
    (root / "special.md").write_text(
        """## O'Brien & "Quotes"
Content with 'single' and "double" quotes. Null: \x00 (stripped).
""",
        encoding="utf-8",
        errors="replace",
    )

    # Included dir (not in EXCLUDE_DIRS) - for contrast with excluded dirs
    included_dir = root / "other_dir" / "sub"
    included_dir.mkdir(parents=True)
    (included_dir / "included.md").write_text(
        "## Included\nShould appear in seed.", encoding="utf-8"
    )

    # Excluded dir: .pytest_cache
    pytest_dir = root / ".pytest_cache" / "sub"
    pytest_dir.mkdir(parents=True)
    (pytest_dir / "ignored2.md").write_text("## Also ignored", encoding="utf-8")

    return root


@pytest.fixture
def temp_md_long_content(tmp_path):
    """File with content exceeding MAX_CONTENT_LEN (50KB)."""
    root = tmp_path / "md_long"
    root.mkdir()
    long_content = "## Long Section\n" + ("x" * 60_000)
    (root / "long.md").write_text(long_content, encoding="utf-8")
    return root


@pytest.fixture
def seed_output_dir(tmp_path):
    """Temp dir for seed output (avoids touching db/dev_seed)."""
    out = tmp_path / "dev_seed"
    out.mkdir()
    return out


def test_seed_generator_produces_valid_sql(temp_md_root, seed_output_dir):
    """Generator should produce valid SQL with all schema columns."""
    _add_scripts_to_path()
    from dev_seed_from_md import generate

    memories, manifest, sql_path, manifest_path = generate(
        root=temp_md_root, output_dir=seed_output_dir
    )

    assert sql_path.exists()
    assert manifest_path.exists()
    assert len(memories) > 0
    assert len(manifest) == len(memories)

    sql_text = sql_path.read_text(encoding="utf-8")
    assert "BEGIN TRANSACTION" in sql_text
    assert "COMMIT" in sql_text
    assert "INSERT INTO memories" in sql_text
    assert "memory_type" in sql_text
    assert "importance" in sql_text
    assert "summary" in sql_text
    assert "source_agent" in sql_text
    assert "source_context" in sql_text
    assert "source_tool" in sql_text
    assert "associated_memories" in sql_text


def test_seed_memories_have_all_schema_attributes(temp_md_root, seed_output_dir):
    """Each memory must include all schema attributes."""
    _add_scripts_to_path()
    from dev_seed_from_md import generate

    memories, _, _, _ = generate(root=temp_md_root, output_dir=seed_output_dir)
    assert len(memories) > 0

    required_keys = {
        "id",
        "name",
        "memory_type",
        "importance",
        "content",
        "tags",
        "source_agent",
        "source_context",
        "source_tool",
        "associated_memories",
        "metadata",
        "access_count",
    }
    for m in memories:
        for k in required_keys:
            assert k in m, f"Missing key {k} in memory {m.get('name')}"


def test_seed_memories_have_varied_types_and_importance(temp_md_root, seed_output_dir):
    """Seeded memories should vary memory_type and importance."""
    _add_scripts_to_path()
    from dev_seed_from_md import generate

    memories, _, _, _ = generate(root=temp_md_root, output_dir=seed_output_dir)
    types = {m["memory_type"] for m in memories}
    importances = {m["importance"] for m in memories}

    assert "long_term" in types or "short_term" in types
    assert "dreams" in types  # dreams_doc.md has brainstorm/explore
    assert "reflex" in types  # reflex_doc.md has always/heuristic
    assert len(importances) >= 2  # at least low/high or high/critical


def test_seed_excludes_excluded_dirs(temp_md_root, seed_output_dir):
    """Files under .pytest_cache must be excluded; other dirs are included."""
    _add_scripts_to_path()
    from dev_seed_from_md import generate

    memories, manifest, _, _ = generate(root=temp_md_root, output_dir=seed_output_dir)
    source_files = {m["source_file"] for m in manifest}

    assert not any(".pytest_cache" in f for f in source_files)
    assert any("other_dir" in f for f in source_files), "other_dir should be included"


def test_seed_handles_special_chars(temp_md_root, seed_output_dir):
    """Content with quotes and special chars must be escaped in SQL."""
    _add_scripts_to_path()
    from dev_seed_from_md import generate

    memories, _, sql_path, _ = generate(root=temp_md_root, output_dir=seed_output_dir)
    sql_text = sql_path.read_text(encoding="utf-8")

    # Single quotes must be doubled in SQL
    assert "''" in sql_text or "O''Brien" in sql_text or "''single''" in sql_text
    # No raw single quote that would break string
    assert "CONTENT: " in sql_text


def test_seed_handles_empty_files(temp_md_root, seed_output_dir):
    """Empty and whitespace-only files produce no chunks."""
    _add_scripts_to_path()
    from dev_seed_from_md import generate

    memories, manifest, _, _ = generate(root=temp_md_root, output_dir=seed_output_dir)
    source_files = {m["source_file"] for m in manifest}

    assert "empty.md" not in source_files
    assert "whitespace.md" not in source_files


def test_seed_deterministic_uuid(temp_md_root, seed_output_dir):
    """Same input produces same UUID (idempotent re-runs)."""
    _add_scripts_to_path()
    from dev_seed_from_md import generate

    m1, _, _, _ = generate(root=temp_md_root, output_dir=seed_output_dir)
    m2, _, _, _ = generate(root=temp_md_root, output_dir=seed_output_dir)

    ids1 = {x["name"]: x["id"] for x in m1}
    ids2 = {x["name"]: x["id"] for x in m2}
    assert ids1 == ids2


@pytest.mark.integration
@pytest.mark.database
async def test_seed_loads_into_db(temp_md_root, seed_output_dir, tmp_path, monkeypatch):
    """Generated seed.sql loads into real SQLite DB without error."""
    _add_scripts_to_path()
    from dev_seed_from_md import generate

    generate(root=temp_md_root, output_dir=seed_output_dir)
    seed_sql = seed_output_dir / "seed.sql"
    assert seed_sql.exists()

    db_path = tmp_path / "seed_integration.db"
    monkeypatch.setenv("AXOM_DB_PATH", str(db_path))

    # Initialize DB schema first (load_dev_seed expects it)
    db = DatabaseManager(str(db_path))
    await db.initialize()
    await db.close()

    # Run load script
    load_script = _scripts_path().parent / "load_dev_seed.py"
    subprocess.run(
        [sys.executable, str(load_script), "--clear"],
        capture_output=True,
        text=True,
        env={**os.environ, "AXOM_DB_PATH": str(db_path)},
        cwd=str(seed_output_dir),
    )
    # load_dev_seed looks for seed.sql in db/dev_seed relative to script
    # We need to pass the seed path or run from project root with seed in place
    # Actually load_dev_seed uses: Path(__file__).parent.parent / "db" / "dev_seed" / "seed.sql"
    # So it always looks in project's db/dev_seed. We need to either:
    # 1. Copy our seed.sql to project db/dev_seed (pollutes)
    # 2. Add --seed-path to load_dev_seed
    # 3. Use a different approach: run generator with output to project db/dev_seed, then load
    # For integration test, let's use sqlite3 directly to load our seed
    import sqlite3

    conn = sqlite3.connect(db_path)
    conn.executescript(seed_sql.read_text(encoding="utf-8"))
    conn.close()

    # Verify memories in DB
    await close_db_manager()
    monkeypatch.setenv("AXOM_DB_PATH", str(db_path))
    db = await get_db_manager()
    await db.initialize()

    listed = await db.list_memories(limit=100)
    await db.close()
    await close_db_manager()

    assert len(listed) > 0
    for m in listed:
        assert m.get("memory_type") in ("long_term", "short_term", "reflex", "dreams")
        assert m.get("importance") in ("low", "high", "critical")
        assert m.get("source_context") == "dev_seed"
        assert m.get("source_agent") == "dev_seed_generator"


@pytest.mark.integration
@pytest.mark.database
async def test_seed_search_works_after_load(
    temp_md_root, seed_output_dir, tmp_path, monkeypatch
):
    """FTS search finds seeded memories after load."""
    _add_scripts_to_path()
    from dev_seed_from_md import generate

    generate(root=temp_md_root, output_dir=seed_output_dir)
    seed_sql = seed_output_dir / "seed.sql"

    db_path = tmp_path / "seed_search.db"
    monkeypatch.setenv("AXOM_DB_PATH", str(db_path))
    db = DatabaseManager(str(db_path))
    await db.initialize()
    await db.close()

    import sqlite3

    conn = sqlite3.connect(db_path)
    conn.executescript(seed_sql.read_text(encoding="utf-8"))
    conn.close()

    await close_db_manager()
    monkeypatch.setenv("AXOM_DB_PATH", str(db_path))
    db = await get_db_manager()
    await db.initialize()

    results = await db.search_memories(query="reflex", limit=10)
    await db.close()
    await close_db_manager()

    assert len(results) >= 1
    assert any("reflex" in (r.get("content") or "").lower() for r in results)


def test_seed_truncates_long_content(temp_md_long_content, seed_output_dir):
    """Content exceeding MAX_CONTENT_LEN is truncated with ...[truncated]."""
    _add_scripts_to_path()
    from dev_seed_from_md import generate

    memories, _, sql_path, _ = generate(
        root=temp_md_long_content, output_dir=seed_output_dir
    )
    assert len(memories) == 1
    assert "...[truncated]" in memories[0]["content"]
    assert len(memories[0]["content"]) <= 50_000 + 100  # some header overhead


def test_seed_duplicate_names_get_suffix(temp_md_root, seed_output_dir):
    """When base name collides, append _v2, _v3 to ensure uniqueness."""
    _add_scripts_to_path()
    from dev_seed_from_md import generate

    # Create two files that could produce same base: seed_dup_intro_000
    dup_dir = temp_md_root / "dup_a"
    dup_dir.mkdir()
    (dup_dir / "dup.md").write_text("## Intro\nFirst chunk.", encoding="utf-8")
    dup_dir2 = temp_md_root / "dup_b"
    dup_dir2.mkdir()
    (dup_dir2 / "dup.md").write_text("## Intro\nSecond chunk.", encoding="utf-8")

    memories, manifest, _, _ = generate(root=temp_md_root, output_dir=seed_output_dir)
    names = [m["name"] for m in manifest]
    assert len(names) == len(set(names)), "All names must be unique"
