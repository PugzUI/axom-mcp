"""Additional branch-focused tests to drive coverage toward 100%."""

from __future__ import annotations

import asyncio
import importlib
import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from mcp.types import (
    CallToolRequest,
    GetPromptRequest,
    ListPromptsRequest,
    ListResourcesRequest,
    ListResourceTemplatesRequest,
    ListToolsRequest,
    ReadResourceRequest,
)

from axom_mcp import server
from axom_mcp.database import DatabaseManager, Memory, close_db_manager, get_db_manager
from axom_mcp.handlers import analyze, discover, transform
from axom_mcp.handlers import exec as exec_handler


@pytest.mark.asyncio
async def test_server_request_handlers_and_prompt_variants(tmp_path, monkeypatch):
    db_path = tmp_path / "server_handlers.db"
    await close_db_manager()
    monkeypatch.setenv("AXOM_DB_PATH", str(db_path))

    db = await get_db_manager()
    await db.create_memory(
        name="srv_read_20260223", content="content", memory_type="long_term"
    )

    s = server.create_server()
    handlers = s.request_handlers

    tools_result = await handlers[ListToolsRequest](ListToolsRequest())
    assert len(tools_result.root.tools) == 5

    unknown_tool = await handlers[CallToolRequest](
        CallToolRequest(params={"name": "unknown", "arguments": {}})
    )
    assert "Unknown tool" in unknown_tool.root.content[0].text

    known_tool = await handlers[CallToolRequest](
        CallToolRequest(
            params={
                "name": "axom_mcp_transform",
                "arguments": {"input": '{"a":1}', "output_format": "json"},
            }
        )
    )
    assert "success" in known_tool.root.content[0].text

    resources = await handlers[ListResourcesRequest](ListResourcesRequest())
    assert len(resources.root.resources) >= 1

    templates = await handlers[ListResourceTemplatesRequest](
        ListResourceTemplatesRequest()
    )
    assert len(templates.root.resourceTemplates) == 3

    memory_res = await handlers[ReadResourceRequest](
        ReadResourceRequest(params={"uri": "memory://srv_read_20260223"})
    )
    assert "srv_read_20260223" in memory_res.root.contents[0].text

    type_res = await handlers[ReadResourceRequest](
        ReadResourceRequest(params={"uri": "memory://type/long_term"})
    )
    assert "long_term" in type_res.root.contents[0].text

    tag_res = await handlers[ReadResourceRequest](
        ReadResourceRequest(params={"uri": "memory://tag/test"})
    )
    assert "tag" in tag_res.root.contents[0].text

    with pytest.raises(ValueError):
        await handlers[ReadResourceRequest](
            ReadResourceRequest(params={"uri": "bad://uri"})
        )

    prompts = await handlers[ListPromptsRequest](ListPromptsRequest())
    assert len(prompts.root.prompts) == 6

    for name, args in [
        ("memory-workflow", {"task_description": "x"}),
        ("debug-session", {"error_description": "boom", "context": "ctx"}),
        ("systematic-debug", {"error_description": "boom", "context": "ctx"}),
        ("code-review", {"target_path": "src", "focus_area": "security"}),
        ("complex-problem", {"topic": "auth bug"}),
        ("store-pattern", {"pattern_name": "p", "description": "d"}),
    ]:
        gp = await handlers[GetPromptRequest](
            GetPromptRequest(params={"name": name, "arguments": args})
        )
        assert len(gp.root.messages) == 1

    with pytest.raises(ValueError):
        await handlers[GetPromptRequest](
            GetPromptRequest(params={"name": "missing", "arguments": {}})
        )

    await close_db_manager()


@pytest.mark.asyncio
async def test_server_lifespan_and_main_run(monkeypatch):
    async def ok_get_db():
        return object()

    async def ok_close_db():
        return None

    monkeypatch.setattr(server, "get_db_manager", ok_get_db)
    monkeypatch.setattr(server, "close_db_manager", ok_close_db)
    monkeypatch.setenv("AXOM_CLEANUP_INTERVAL", "0")

    async with server.server_lifespan(None):
        pass

    cancelled = {"flag": False}

    async def fake_periodic(_interval=None):
        try:
            while True:
                await asyncio.sleep(3600)
        except asyncio.CancelledError:
            cancelled["flag"] = True
            # Raise it properly for the await to see
            raise

    monkeypatch.setenv("AXOM_CLEANUP_INTERVAL", "1")
    monkeypatch.setattr(server, "_periodic_cleanup_loop", fake_periodic)
    async with server.server_lifespan(None):
        await asyncio.sleep(0)
    assert cancelled["flag"] is True

    async def bad_get_db():
        raise RuntimeError("db fail")

    monkeypatch.setattr(server, "get_db_manager", bad_get_db)
    with pytest.raises(RuntimeError):
        async with server.server_lifespan(None):
            pass

    class _DummyStdio:
        async def __aenter__(self):
            return ("r", "w")

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class _DummyServer:
        async def run(self, r, w, opts):
            assert r == "r" and w == "w" and opts == "opts"

        def create_initialization_options(self):
            return "opts"

    monkeypatch.setattr(server, "create_server", lambda: _DummyServer())
    monkeypatch.setattr(server, "stdio_server", lambda: _DummyStdio())
    await server.run_server()

    called = {"ok": False}

    def fake_run(coro):
        called["ok"] = True
        assert asyncio.iscoroutine(coro)
        coro.close()

    monkeypatch.setattr(server.asyncio, "run", fake_run)
    server.main()
    assert called["ok"] is True


@pytest.mark.asyncio
async def test_periodic_cleanup_loop_and_interval_parsing(monkeypatch):
    class _DB:
        def __init__(self):
            self.calls = 0

        async def cleanup_expired_memories(self):
            self.calls += 1
            if self.calls == 1:
                return {"ok": True}
            raise RuntimeError("boom")

    db = _DB()

    async def fake_get_db():
        return db

    sleeps = {"n": 0}

    async def fake_sleep(_):
        sleeps["n"] += 1
        if sleeps["n"] >= 3:
            raise asyncio.CancelledError()
        return None

    monkeypatch.setattr(server, "get_db_manager", fake_get_db)
    monkeypatch.setattr(server.asyncio, "sleep", fake_sleep)

    with pytest.raises(asyncio.CancelledError):
        await server._periodic_cleanup_loop(1)
    assert db.calls == 2

    monkeypatch.setenv("AXOM_CLEANUP_INTERVAL", "bad-value")
    assert server._get_cleanup_interval_seconds() == 3600


def test___main___module_import_executes_line():
    import axom_mcp.__main__ as main_mod

    importlib.reload(main_mod)


@pytest.mark.asyncio
async def test_analyze_internal_paths(tmp_path, monkeypatch):
    assert analyze._validate_path(str(Path.cwd()))
    with pytest.raises(ValueError):
        analyze._validate_path("/tmp/definitely_outside_cwd_or_home_123")

    sample_file = tmp_path / "sample.py"
    sample_file.write_text("def x():\n    pass\n", encoding="utf-8")
    result = json.loads(
        await analyze.handle_analyze(
            {"type": "debug", "target": str(sample_file), "output_format": "detailed"}
        )
    )
    assert result["type"] == "debug"

    actionable = await analyze.handle_analyze(
        {
            "type": "review",
            "target": "def f():\n    pass\n",
            "output_format": "actionable",
            "focus": "maintainability",
        }
    )
    assert "Action Items" in actionable

    err = json.loads(
        await analyze.handle_analyze({"type": "audit", "target": "x", "depth": "high"})
    )
    assert "summary" in err

    ref = await analyze._analyze_refactor(
        "if x:\n    if y:\n        pass\n"
        + "\n".join(["abcde12345" for _ in range(3)]),
        None,
        "low",
    )
    assert ref["type"] == "refactor"

    tst = await analyze._analyze_test("def foo():\n    return 1", None, "low")
    assert tst["issues_found"] is True

    formatted = analyze._format_actionable({"type": "debug", "summary": "s"})
    assert "Analysis" in formatted

    async def boom(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(analyze, "_analyze_debug", boom)
    bad = json.loads(
        await analyze.handle_analyze({"type": "debug", "target": "print('x')"})
    )
    assert "error" in bad


def test_transform_internal_paths(monkeypatch):
    assert transform._detect_format('{"a":1}') == "json"
    assert transform._detect_format("---\na: 1") == "yaml"
    assert transform._detect_format("a,b\n1,2") == "csv"
    assert transform._detect_format("# title") == "markdown"
    assert transform._detect_format("plain") == "code"

    parsed_yaml = transform._parse_simple_yaml(
        "a: true\nb: 2\nc: 1.5\nd: 'x'\nlist:\n- i1"
    )
    assert parsed_yaml["a"] is True

    md = transform._parse_markdown("# H\n- a\n[txt](https://x)\n```py\nprint(1)\n```")
    assert md["headers"] and md["links"] and md["code_blocks"]

    assert transform._detect_language("public class A {}") == "java"
    assert transform._detect_language("module A\nend") == "ruby"
    assert transform._detect_language("<?php $x = 1;") == "php"
    assert transform._detect_language("#include <stdio.h>\nint main(){}") in {
        "c",
        "cpp",
    }

    data = [{"k": "b", "v": 2}, {"k": "a", "v": 1}]
    sorted_data = transform._apply_rule(data, {"type": "sort", "field": "k"})
    assert sorted_data[0]["k"] == "a"

    agg = transform._apply_rule(
        [{"g": "x", "n": 1}, {"g": "x", "n": 3}],
        {
            "type": "aggregate",
            "group_by": "g",
            "aggregate_field": "n",
            "function": "sum",
        },
    )
    assert agg[0]["sum"] == 4

    assert transform._apply_rule({"a": 1}, {"type": "unknown"}) == {"a": 1}

    assert transform._format_output({"a": 1}, "json").startswith("{")

    orig_import = __import__

    def fake_import(name, *args, **kwargs):
        if name == "yaml":
            raise ImportError("no yaml")
        return orig_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", fake_import)
    yaml_out = transform._format_output({"a": 1}, "yaml")
    assert "a:" in yaml_out

    csv_out = transform._format_csv([1, 2])
    assert "value" in csv_out

    md_tmpl = transform._format_markdown({"x": 1}, "X={{x}}")
    assert md_tmpl == "X=1"

    md_dict = transform._format_markdown({"k": ["i"]})
    assert "# Data" in md_dict

    md_list = transform._format_markdown([{"a": 1}, "b"])
    assert "Item 1" in md_list

    assert transform._format_markdown("raw") == "raw"

    with pytest.raises(ValueError):
        transform._format_output({"a": 1}, "unknown")


@pytest.mark.asyncio
async def test_transform_handle_error_path():
    bad = json.loads(
        await transform.handle_transform(
            {"input": "{bad", "input_format": "json", "output_format": "yaml"}
        )
    )
    assert "error" in bad


@pytest.mark.asyncio
async def test_exec_paths_and_chain_engine(tmp_path, monkeypatch):
    with pytest.raises(ValueError):
        exec_handler._validate_path("/tmp/definitely_outside_cwd_or_home_456")

    d = tmp_path / "d"
    d.mkdir()
    not_file = json.loads(await exec_handler._handle_read(str(d)))
    assert "error" in not_file

    big = Path.cwd() / ".cov_big.txt"
    big.write_text("a" * (exec_handler.MAX_FILE_SIZE + 1), encoding="utf-8")
    too_big = json.loads(await exec_handler._handle_read(str(big)))
    assert "too large" in too_big["error"]
    big.unlink(missing_ok=True)

    nodata = json.loads(await exec_handler._handle_write(str(tmp_path / "x.txt"), None))
    assert "error" in nodata

    class _Proc:
        returncode = 0

        def __init__(self):
            self.killed = False

        async def communicate(self):
            return (b"", b"")

        def kill(self):
            self.killed = True

    proc = _Proc()

    async def fake_subprocess(*args, **kwargs):
        return proc

    async def fake_wait_for(*args, **kwargs):
        raise TimeoutError

    monkeypatch.setattr(
        exec_handler.asyncio, "create_subprocess_shell", fake_subprocess
    )
    monkeypatch.setattr(exec_handler.asyncio, "wait_for", fake_wait_for)

    timeout = json.loads(await exec_handler._handle_shell("echo x"))
    assert "timed out" in timeout["error"]
    assert proc.killed is True

    engine = exec_handler.ChainEngine(
        handlers={
            "ok": AsyncMock(return_value=json.dumps({"success": True, "n": 1})),
            "boom": AsyncMock(side_effect=RuntimeError("x")),
        }
    )

    out = await engine.execute_chain(
        {"success": True, "value": 1},
        [
            {"tool": "ok", "args": {"x": "${_result.value}"}},
            {"tool": "missing", "args": {}},
            {"tool": "ok", "args": {}, "condition": "${_result.success} == false"},
            {"tool": "boom", "args": {}},
        ],
    )
    assert out["success"] is True
    assert any(step.get("skipped") for step in out["steps"])


@pytest.mark.asyncio
async def test_discover_error_and_all_paths(tmp_path, monkeypatch):
    missing = json.loads(
        await discover._discover_files(
            {"path": str(Path.cwd() / ".cov_missing"), "pattern": "*"}, 10, True
        )
    )
    assert "error" in missing

    # Invalid path falls back to cwd and still succeeds.
    fallback = json.loads(
        await discover._discover_files(
            {"path": "/tmp/definitely_outside_cwd_or_home_789", "pattern": "*.py"},
            5,
            False,
        )
    )
    assert fallback["success"] is True

    async def bad_db():
        raise RuntimeError("db unavailable")

    monkeypatch.setattr(discover, "get_db_manager", bad_db)
    mem_err = json.loads(await discover._discover_memory(5))
    assert mem_err["success"] is False

    all_result = json.loads(await discover._discover_all({}, 5, False))
    assert all_result["success"] is True


@pytest.mark.asyncio
async def test_database_edge_paths_and_serialization(tmp_path, monkeypatch):
    db_path = tmp_path / "db_edges.db"
    await close_db_manager()
    monkeypatch.setenv("AXOM_DB_PATH", str(db_path))

    db = await get_db_manager()

    # _get_conn error path
    disconnected = DatabaseManager(str(tmp_path / "other.db"))
    with pytest.raises(RuntimeError):
        disconnected._get_conn()

    # Memory.to_dict enum/string branches
    m = Memory(id="1", memory_type="long_term", importance="low")
    d = m.to_dict()
    assert d["memory_type"] == "long_term"

    mid = await db.create_memory(
        name="edge_db_20260223",
        content="edge",
        memory_type="long_term",
        importance="low",
        tags=["B", "a"],
        metadata={"x": 1},
    )

    found = await db.get_memory(mid)
    assert found is not None
    assert await db.get_memory("missing") is None
    assert await db.get_memory_by_name("missing") is None

    await db.update_memory(
        mid, content="edge2", importance="high", tags=["x"], metadata={"k": 2}
    )
    no_update = await db.update_memory(mid)
    assert no_update is not None

    # search/list filter branches
    listed = await db.list_memories(
        memory_type="long_term", importance="high", tags=["x"], limit=10
    )
    assert listed
    searched = await db.search_memories(
        query=None,
        memory_type="long_term",
        importance="high",
        tags=["x"],
        limit=10,
    )
    assert searched

    # delete false and true branches
    assert await db.delete_memory("missing") is False
    assert await db.delete_memory_by_name("missing") is False

    # association false paths
    assert await db.add_association("missing", "target") is False
    assert await db.remove_association("missing", "target") is False

    # create malformed JSON rows to hit decode fallbacks
    await db.conn.execute(
        "UPDATE memories SET tags = '{bad', metadata = '{bad', associated_memories = '{bad' WHERE id = ?",
        (mid,),
    )
    await db.conn.commit()
    malformed = await db.get_memory(mid)
    assert malformed is not None

    # prune-association edge branches
    assert await db._prune_association_references([]) == 0
    await db.conn.execute(
        "UPDATE memories SET associated_memories = '' WHERE id = ?",
        (mid,),
    )
    await db.conn.commit()
    await db._prune_association_references(["x"])
    await db.conn.execute(
        "UPDATE memories SET associated_memories = '{}' WHERE id = ?",
        (mid,),
    )
    await db.conn.commit()
    await db._prune_association_references(["x"])
    await db.conn.execute(
        "UPDATE memories SET associated_memories = '{bad' WHERE id = ?",
        (mid,),
    )
    await db.conn.commit()
    await db._prune_association_references(["x"])

    # cleanup/log branches
    await db.conn.execute(
        "INSERT INTO memories (id, name, memory_type, importance, content, tags, metadata, created_at, updated_at, accessed_at, expires_at, access_count, associated_memories) VALUES (?, ?, 'short_term', 'low', 'c', '[]', '{}', '2020-01-01T00:00:00+00:00', '2020-01-01T00:00:00+00:00', '2020-01-01T00:00:00+00:00', '2020-01-01T00:00:00+00:00', 0, '[]')",
        ("expired-old", "exp_old"),
    )
    await db.conn.execute(
        "INSERT INTO memory_access_log (id, memory_id, accessed_by, access_type, created_at) VALUES (?, ?, 'x', 'read', '2020-01-01T00:00:00+00:00')",
        ("log-old", mid),
    )
    await db.conn.commit()

    cleanup = await db.cleanup_expired_memories()
    assert cleanup["expired_deleted"] >= 1
    assert "logs_deleted" in cleanup

    stats = await db.get_memory_stats()
    assert "breakdown" in stats

    access = await db.get_access_log(
        memory_id=mid, accessed_by="system", access_type="read", limit=10
    )
    assert isinstance(access, list)

    # ensure schema file missing branch
    monkeypatch.setattr(
        "builtins.open",
        lambda *args, **kwargs: (_ for _ in ()).throw(FileNotFoundError()),
    )
    with pytest.raises(FileNotFoundError):
        await disconnected.ensure_schema()

    await close_db_manager()
