"""Edge-branch tests for uncovered control-flow paths."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from mcp.types import (
    CallToolRequest,
    GetPromptRequest,
    ListResourcesRequest,
    ReadResourceRequest,
)

from axom_mcp import server
from axom_mcp.database import DatabaseManager, close_db_manager, get_db_manager
from axom_mcp.handlers import analyze, discover, memory, transform
from axom_mcp.handlers import exec as exec_handler


@pytest.mark.asyncio
async def test_memory_handler_all_error_and_success_paths(monkeypatch):
    db = SimpleNamespace(
        create_memory=AsyncMock(return_value="id1"),
        get_memory_by_name=AsyncMock(return_value=None),
        get_associated_memories=AsyncMock(return_value=[]),
        list_memories=AsyncMock(return_value=[]),
        search_memories=AsyncMock(return_value=[]),
        delete_memory_by_name=AsyncMock(return_value=False),
        add_association=AsyncMock(return_value=False),
    )
    monkeypatch.setattr(memory, "get_db_manager", AsyncMock(return_value=db))

    # Unknown action branch via mocked schema object.
    monkeypatch.setattr(memory, "MemoryInput", lambda **_: SimpleNamespace(action="unknown"))
    unknown = json.loads(await memory.handle_memory({}))
    assert "Unknown action" in unknown["error"]

    # Write validation branches.
    assert (
        "name is required"
        in json.loads(await memory._handle_write(SimpleNamespace(name=None, content="x"), db))[
            "error"
        ]
    )
    assert (
        "content is required"
        in json.loads(await memory._handle_write(SimpleNamespace(name="n", content=None), db))[
            "error"
        ]
    )

    # Write exception branch.
    db.create_memory = AsyncMock(side_effect=RuntimeError("write-fail"))
    write_err = json.loads(
        await memory._handle_write(
            SimpleNamespace(
                name="n",
                content="c",
                memory_type=None,
                importance=None,
                tags=None,
                source_agent=None,
                expires_in_days=None,
            ),
            db,
        )
    )
    assert "error" in write_err

    # Read required/error/not-found/success/exception.
    assert (
        "name is required"
        in json.loads(await memory._handle_read(SimpleNamespace(name=None), db))["error"]
    )
    read_nf = json.loads(await memory._handle_read(SimpleNamespace(name="x"), db))
    assert "Memory not found" in read_nf["error"]

    db.get_memory_by_name = AsyncMock(
        return_value={
            "id": "1",
            "name": "n",
            "content": "c",
            "memory_type": "long_term",
            "importance": "low",
            "tags": [],
            "source_agent": None,
            "parent_memory_id": None,
            "created_at": "2026",
            "updated_at": "2026",
        }
    )
    db.get_associated_memories = AsyncMock(
        return_value=[
            {
                "id": "2",
                "name": "a",
                "memory_type": "short_term",
                "importance": "low",
                "tags": ["t"],
                "created_at": "2026",
            }
        ]
    )
    read_ok = json.loads(await memory._handle_read(SimpleNamespace(name="n"), db))
    assert read_ok["success"] is True

    db.get_memory_by_name = AsyncMock(side_effect=RuntimeError("read-fail"))
    assert "error" in json.loads(await memory._handle_read(SimpleNamespace(name="n"), db))

    # List/search/delete/associate branches.
    db.list_memories = AsyncMock(
        return_value=[
            {
                "name": "n",
                "memory_type": "long_term",
                "importance": "low",
                "tags": [],
                "created_at": "2026",
            }
        ]
    )
    list_ok = json.loads(
        await memory._handle_list(SimpleNamespace(limit=10, memory_type=None, importance=None), db)
    )
    assert list_ok["success"] is True

    db.list_memories = AsyncMock(side_effect=RuntimeError("list-fail"))
    assert "error" in json.loads(
        await memory._handle_list(SimpleNamespace(limit=1, memory_type=None, importance=None), db)
    )

    assert (
        "query is required"
        in json.loads(
            await memory._handle_search(
                SimpleNamespace(query=None, limit=1, memory_type=None, importance=None, tags=None),
                db,
            )
        )["error"]
    )

    db.search_memories = AsyncMock(
        return_value=[
            {
                "name": "n",
                "content": "c",
                "memory_type": "long_term",
                "importance": "low",
                "rank": 1.0,
            }
        ]
    )
    search_ok = json.loads(
        await memory._handle_search(
            SimpleNamespace(query="q", limit=1, memory_type=None, importance=None, tags=None),
            db,
        )
    )
    assert search_ok["success"] is True

    db.search_memories = AsyncMock(side_effect=RuntimeError("search-fail"))
    assert "error" in json.loads(
        await memory._handle_search(
            SimpleNamespace(query="q", limit=1, memory_type=None, importance=None, tags=None),
            db,
        )
    )

    assert (
        "name is required"
        in json.loads(await memory._handle_delete(SimpleNamespace(name=None), db))["error"]
    )
    del_nf = json.loads(await memory._handle_delete(SimpleNamespace(name="n"), db))
    assert "Memory not found" in del_nf["error"]

    db.delete_memory_by_name = AsyncMock(return_value=True)
    del_ok = json.loads(await memory._handle_delete(SimpleNamespace(name="n"), db))
    assert del_ok["success"] is True

    db.delete_memory_by_name = AsyncMock(side_effect=RuntimeError("del-fail"))
    assert "error" in json.loads(await memory._handle_delete(SimpleNamespace(name="n"), db))

    assert (
        "source memory"
        in json.loads(
            await memory._handle_associate(SimpleNamespace(name=None, target_memory_name="x"), db)
        )["error"]
    )
    assert (
        "target_memory_name"
        in json.loads(
            await memory._handle_associate(SimpleNamespace(name="a", target_memory_name=None), db)
        )["error"]
    )

    db.get_memory_by_name = AsyncMock(side_effect=[None])
    assert (
        "Source memory not found"
        in json.loads(
            await memory._handle_associate(SimpleNamespace(name="a", target_memory_name="b"), db)
        )["error"]
    )

    db.get_memory_by_name = AsyncMock(side_effect=[{"id": "1"}, None])
    assert (
        "Target memory not found"
        in json.loads(
            await memory._handle_associate(SimpleNamespace(name="a", target_memory_name="b"), db)
        )["error"]
    )

    db.get_memory_by_name = AsyncMock(side_effect=[{"id": "1"}, {"id": "2"}])
    db.add_association = AsyncMock(return_value=False)
    assert (
        "Failed to create association"
        in json.loads(
            await memory._handle_associate(SimpleNamespace(name="a", target_memory_name="b"), db)
        )["error"]
    )

    db.add_association = AsyncMock(side_effect=RuntimeError("assoc-fail"))
    assert "error" in json.loads(
        await memory._handle_associate(SimpleNamespace(name="a", target_memory_name="b"), db)
    )


@pytest.mark.asyncio
async def test_handler_unknown_and_exception_branches(monkeypatch):
    # analyze unknown + exception + code_content None branches
    monkeypatch.setattr(
        analyze,
        "AnalyzeInput",
        lambda **_: SimpleNamespace(
            type="unknown", target="x", focus=None, depth=None, output_format=None
        ),
    )
    assert "Unknown analysis type" in json.loads(await analyze.handle_analyze({}))["error"]

    monkeypatch.setattr(
        analyze, "_validate_path", lambda _: (_ for _ in ()).throw(RuntimeError("bad"))
    )
    monkeypatch.setattr(
        analyze,
        "AnalyzeInput",
        lambda **_: SimpleNamespace(
            type="debug", target="x", focus=None, depth=None, output_format=None
        ),
    )
    assert "error" in json.loads(await analyze.handle_analyze({}))

    monkeypatch.setattr(
        analyze,
        "_validate_path",
        lambda _: SimpleNamespace(exists=lambda: False, is_file=lambda: False),
    )
    monkeypatch.setattr(
        analyze,
        "AnalyzeInput",
        lambda **_: SimpleNamespace(
            type="debug", target=None, focus=None, depth=None, output_format=None
        ),
    )
    assert "Could not read target" in json.loads(await analyze.handle_analyze({}))["error"]

    # exec unknown + exception
    monkeypatch.setattr(
        exec_handler,
        "ExecInput",
        lambda **_: SimpleNamespace(operation="unknown", target="x", data=None),
    )
    assert "Unknown operation" in json.loads(await exec_handler.handle_exec({}))["error"]

    async def boom_read(_):
        raise RuntimeError("boom")

    monkeypatch.setattr(
        exec_handler,
        "ExecInput",
        lambda **_: SimpleNamespace(operation="read", target="x", data=None),
    )
    monkeypatch.setattr(exec_handler, "_handle_read", boom_read)
    assert "error" in json.loads(await exec_handler.handle_exec({}))

    # discover unknown + exception
    monkeypatch.setattr(
        discover,
        "DiscoverInput",
        lambda **_: SimpleNamespace(domain="unknown", filter=None, limit=None, recursive=None),
    )
    assert "Unknown domain" in json.loads(await discover.handle_discover({}))["error"]

    monkeypatch.setattr(
        discover,
        "DiscoverInput",
        lambda **_: SimpleNamespace(domain="files", filter={}, limit=1, recursive=True),
    )

    async def bad_files(*args, **kwargs):
        raise RuntimeError("files boom")

    monkeypatch.setattr(discover, "_discover_files", bad_files)
    assert "error" in json.loads(await discover.handle_discover({}))


@pytest.mark.asyncio
async def test_database_remaining_paths(tmp_path, monkeypatch):
    db_path = tmp_path / "db_more.db"
    await close_db_manager()
    monkeypatch.setenv("AXOM_DB_PATH", str(db_path))
    db = await get_db_manager()

    # create_memory explicit expires and no tag normalization path
    mid = await db.create_memory(
        name="x", content="y", memory_type="reflex", expires_in_days=1, tags=[]
    )
    assert mid

    # line 332: get_memory none
    assert await db.get_memory("missing-id") is None

    # branch: source_agent filter in list_memories
    await db.create_memory(name="agented", content="a", source_agent="agent-1")
    filt = await db.list_memories(source_agent="agent-1", limit=5)
    assert filt

    # trigger add/remove exception branches by closing connection first
    await db.close()
    assert await db.add_association("a", "b") is False
    assert await db.remove_association("a", "b") is False

    # initialize exception branch
    bad = DatabaseManager(str(tmp_path / "dir" / "bad.db"))

    async def fail_connect(_):
        raise RuntimeError("connect-fail")

    monkeypatch.setattr("axom_mcp.database.aiosqlite.connect", fail_connect)
    with pytest.raises(RuntimeError):
        await bad.initialize()


@pytest.mark.asyncio
async def test_server_call_tool_and_list_resources_error_paths(monkeypatch):
    s = server.create_server()
    handlers = s.request_handlers

    async def boom(*args, **kwargs):
        raise RuntimeError("tool boom")

    monkeypatch.setattr(server, "handle_transform", boom)
    err = await handlers[CallToolRequest](
        CallToolRequest(
            params={
                "name": "axom_mcp_transform",
                "arguments": {"input": "x", "output_format": "json"},
            }
        )
    )
    assert "Error:" in err.root.content[0].text

    async def bad_db():
        raise RuntimeError("db fail")

    monkeypatch.setattr(server, "get_db_manager", bad_db)
    res = await handlers[ListResourcesRequest](ListResourcesRequest())
    # axom_tools is always present; memory list may be empty on error
    assert len(res.root.resources) >= 1
    assert res.root.resources[0].name == "axom_tools"

    # read resource unknown memory path branch
    async def ok_db():
        return SimpleNamespace(
            list_memories=AsyncMock(return_value=[]),
            search_memories=AsyncMock(return_value=[]),
            get_memory_by_name=AsyncMock(return_value=None),
        )

    monkeypatch.setattr(server, "get_db_manager", ok_db)
    with pytest.raises(ValueError):
        await handlers[ReadResourceRequest](
            ReadResourceRequest(params={"uri": "memory://missing_abc"})
        )


@pytest.mark.asyncio
async def test_prompt_includes_compact_recent_context_banner(monkeypatch):
    s = server.create_server()
    handlers = s.request_handlers

    db = SimpleNamespace(
        list_memories=AsyncMock(
            return_value=[
                {
                    "name": "ops_copy_env_example_to_env_20260224",
                    "tags": ["env", "config"],
                },
                {
                    "name": "feature_output_styles_formatter_20260224",
                    "tags": ["output", "style"],
                },
                {
                    "name": "feature_neon_terminal_panel_20260224",
                    "tags": ["neon", "ui"],
                },
                {
                    "name": "feature_should_not_appear_20260224",
                    "tags": ["ignored"],
                },
            ]
        )
    )

    async def fake_get_db():
        return db

    monkeypatch.setattr(server, "get_db_manager", fake_get_db)

    prompt = await handlers[GetPromptRequest](
        GetPromptRequest(params={"name": "memory-workflow", "arguments": {"task_description": "x"}})
    )
    text = prompt.root.messages[0].content.text

    assert "|Axom-Context:||" in text
    assert "|Axom-Memory||Search:||" in text
    assert "||env,config||output,style||neon,ui|" in text
    assert "feature_should_not_appear" not in text
    assert "ops_copy_env_example_to_env" not in text
    assert "feature_output_styles_formatter" not in text
    assert "feature_neon_terminal_panel" not in text
    assert "||env||config||output|" in text


@pytest.mark.asyncio
async def test_server_tool_output_styles(monkeypatch):
    s = server.create_server()
    handlers = s.request_handlers

    async def fake_transform(_arguments):
        return json.dumps(
            {
                "success": True,
                "count": 1,
                "results": [
                    {
                        "name": "preview_row",
                        "memory_type": "long_term",
                        "importance": "high",
                        "relevance": 0.3,
                    }
                ],
            }
        )

    monkeypatch.setattr(server, "handle_transform", fake_transform)

    request = CallToolRequest(
        params={
            "name": "axom_mcp_transform",
            "arguments": {"input": '{"a":1}', "output_format": "json"},
        }
    )

    # Default style: pretty_json.
    monkeypatch.delenv("AXOM_TOOL_OUTPUT_STYLE", raising=False)
    pretty_json_out = await handlers[CallToolRequest](request)
    pretty_json_text = pretty_json_out.root.content[0].text
    assert pretty_json_text.startswith("{\n")
    assert '"success": true' in pretty_json_text
    assert '\n  "count": 1' in pretty_json_text

    # Legacy compact JSON style.
    monkeypatch.setenv("AXOM_TOOL_OUTPUT_STYLE", "json")
    json_out = await handlers[CallToolRequest](request)
    json_text = json_out.root.content[0].text
    assert json_text.startswith('{"success": true')
    assert "\n" not in json_text

    # Rich markdown style with table + raw JSON block.
    monkeypatch.setenv("AXOM_TOOL_OUTPUT_STYLE", "pretty")
    pretty_out = await handlers[CallToolRequest](request)
    pretty_text = pretty_out.root.content[0].text
    assert "**axom_mcp_transform**" in pretty_text
    assert "status: success" in pretty_text
    assert "results:" in pretty_text
    assert "raw_json:" in pretty_text
    assert "```json" in pretty_text

    # Terminal-inspired neon style.
    monkeypatch.setenv("AXOM_TOOL_OUTPUT_STYLE", "neon")
    neon_out = await handlers[CallToolRequest](request)
    neon_text = neon_out.root.content[0].text
    assert "AXOM NEON PANEL ::" in neon_text
    assert "preview::results" in neon_text
    assert "```text" in neon_text
    assert "```json" in neon_text


def test_transform_uncovered_branches():
    # parse_input unknown format
    with pytest.raises(ValueError):
        transform._parse_input("x", "unknown")

    # yaml parser branches for false/float/quoted/nested dict path
    parsed = transform._parse_simple_yaml('a: false\nb: 3.14\nc: "q"\nd:\n  child: value')
    assert parsed["a"] is False

    # _apply_rule non-dict/list and aggregate count path
    assert transform._apply_rule("x", {"type": "field_mapping", "mapping": {"a": "b"}}) == "x"
    agg = transform._apply_rule(
        [{"g": "x"}, {"g": "x"}],
        {"type": "aggregate", "group_by": "g", "function": "count"},
    )
    assert agg[0]["count"] == 2

    # format output code path for non-code dict
    assert transform._format_output({"a": 1}, "code") == "{'a': 1}"

    # simple yaml list/dict formatting branches
    y = transform._format_simple_yaml([{"a": 1}, 2])
    assert "-" in y

    # csv empty and dict path
    assert transform._format_csv([]) == ""
    assert "a" in transform._format_csv([{"a": 1}])

    # markdown dict nested dict and list non-dict items
    md = transform._format_markdown({"x": {"y": 1}, "z": [1]})
    assert "**y**" in md


@pytest.mark.asyncio
async def test_exec_additional_paths(tmp_path, monkeypatch):
    # _handle_read file not found
    missing = json.loads(await exec_handler._handle_read(str(Path.cwd() / ".nope_cov")))
    assert "File not found" in missing["error"]

    # _handle_write value error branch from invalid path
    monkeypatch.delenv("AXOM_READ_ONLY", raising=False)
    bad_path = json.loads(await exec_handler._handle_write("/tmp/outside_cov", "x"))
    assert "outside allowed directories" in bad_path["error"]

    # _handle_write generic exception branch
    p = Path.cwd() / ".cov_write.txt"

    def fail_write(*args, **kwargs):
        raise OSError("disk")

    monkeypatch.setattr(Path, "write_text", fail_write)
    err = json.loads(await exec_handler._handle_write(str(p), "x"))
    assert "error" in err

    # _handle_shell generic exception branch
    async def fail_subproc(*args, **kwargs):
        raise OSError("subproc")

    monkeypatch.setattr(exec_handler.asyncio, "create_subprocess_shell", fail_subproc)
    shell_err = json.loads(await exec_handler._handle_shell("echo x"))
    assert "error" in shell_err

    # ChainEngine helper branches
    eng = exec_handler.ChainEngine()
    assert eng._evaluate_condition("${_result.ok}", {"_result": {"ok": True}}) is True
    assert eng._evaluate_condition("not-a-condition", {"_result": {}}) is False
    assert eng._get_variable("a.b", {"a": 1}) is None
    assert eng._substitute_variables(1, {"_result": {}}) == 1


@pytest.mark.asyncio
async def test_server_dispatch_and_memory_helper_branches(monkeypatch):
    # Hit remaining call_tool branches.
    s = server.create_server()
    handlers = s.request_handlers

    for name, args in [
        ("axom_mcp_memory", {"action": "list"}),
        ("axom_mcp_exec", {"operation": "shell", "target": "echo hi"}),
        ("axom_mcp_analyze", {"type": "debug", "target": "print('x')"}),
        ("axom_mcp_discover", {"domain": "tools"}),
    ]:
        out = await handlers[CallToolRequest](
            CallToolRequest(params={"name": name, "arguments": args})
        )
        assert out.root.content

    # Cover helper branches in memory handler.
    assert memory._to_iso_or_str(None) is None

    class T:
        def isoformat(self):
            return "iso"

    assert memory._to_iso_or_str(T()) == "iso"

    db = SimpleNamespace(
        list_memories=AsyncMock(return_value=[]),
        search_memories=AsyncMock(return_value=[]),
        get_memory_by_name=AsyncMock(side_effect=[{"id": "1"}, {"id": "2"}]),
        add_association=AsyncMock(return_value=True),
    )
    monkeypatch.setattr(memory, "get_db_manager", AsyncMock(return_value=db))
    assert json.loads(await memory.handle_memory({"action": "list"}))["success"] is True
    assoc = json.loads(
        await memory.handle_memory({"action": "associate", "name": "a", "target_memory_name": "b"})
    )
    assert assoc["success"] is True


@pytest.mark.asyncio
async def test_discover_and_exec_remaining_branches(monkeypatch):
    # _to_iso_or_str branches
    assert discover._to_iso_or_str(None) is None

    class T:
        def isoformat(self):
            return "iso"

    assert discover._to_iso_or_str(T()) == "iso"

    # include file_type checks and recursive include path
    files = json.loads(
        await discover._discover_files(
            {"path": str(Path.cwd()), "pattern": "*.py", "type": "file"}, 2, True
        )
    )
    assert files["success"] is True
    dirs = json.loads(
        await discover._discover_files(
            {"path": str(Path.cwd()), "pattern": "*", "type": "directory"}, 2, False
        )
    )
    assert dirs["success"] is True

    # PermissionError branch in _discover_files.
    orig_rglob = Path.rglob

    def raise_perm(self, pattern):
        raise PermissionError

    monkeypatch.setattr(Path, "rglob", raise_perm)
    perm = json.loads(
        await discover._discover_files({"path": str(Path.cwd()), "pattern": "*"}, 2, True)
    )
    assert perm["success"] is True
    monkeypatch.setattr(Path, "rglob", orig_rglob)

    assert discover._env_flag_enabled("AXOM_NOT_SET_FLAG", default=True) is True

    # Exec generic read exception branch.
    class BadPath:
        def exists(self):
            return True

        def is_file(self):
            return True

        def stat(self):
            return SimpleNamespace(st_size=0)

        def read_text(self, **kwargs):
            raise OSError("read")

    monkeypatch.setattr(exec_handler, "_validate_path", lambda _: BadPath())
    read_err = json.loads(await exec_handler._handle_read("x"))
    assert "error" in read_err

    # ChainEngine exception in condition evaluation + list substitution.
    eng = exec_handler.ChainEngine()
    monkeypatch.setattr(
        exec_handler.re,
        "match",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("regex")),
    )
    assert eng._evaluate_condition("${x}", {}) is False
    substituted = eng._substitute_variables(["${_result}", "${missing}"], {"_result": {"k": 1}})
    assert substituted[0].startswith("{")


def test_transform_remaining_branches(monkeypatch):
    # JSON decode error branch in format detection.
    assert transform._detect_format("{bad") in {"yaml", "code"}

    # Force yaml ImportError fallback in _parse_input.
    orig_import = __import__

    def fake_import(name, *args, **kwargs):
        if name == "yaml":
            raise ImportError("no yaml")
        return orig_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", fake_import)
    parsed = transform._parse_input("a: 1", "yaml")
    assert parsed["a"] == 1

    # code parse branch
    code_obj = transform._parse_input("const x = 1", "code")
    assert code_obj["language"] == "javascript"

    # list-item YAML branch when key has no value.
    y = transform._parse_simple_yaml("items:\n- one\n- two")
    assert y["items"] == ["one", "two"]

    # field mapping/filter list branches
    fm = transform._apply_rule([{"a": 1}], {"type": "field_mapping", "mapping": {"a": "b"}})
    assert fm[0]["b"] == 1
    flt = transform._apply_rule([{"a": 1, "b": 2}], {"type": "filter", "fields": ["a"]})
    assert flt[0] == {"a": 1}

    # sort branch.
    sorted_data = transform._apply_rule([{"a": 2}, {"a": 1}], {"type": "sort", "field": "a"})
    assert isinstance(sorted_data, list)

    # markdown template with non-dict data and scalar formatting branch.
    assert transform._format_markdown("x", template="plain") == "plain"
    assert transform._format_simple_yaml(123).strip() == "123"


@pytest.mark.asyncio
async def test_database_remaining_parse_and_close_paths(tmp_path, monkeypatch):
    db_path = tmp_path / "db_parse.db"
    await close_db_manager()
    monkeypatch.setenv("AXOM_DB_PATH", str(db_path))
    db = await get_db_manager()
    a = await db.create_memory(name="a", content="A")
    b = await db.create_memory(name="b", content="B")
    c = await db.create_memory(name="c", content="C")

    # force invalid associated_memories JSON for both add/remove decode branches
    await db.conn.execute("UPDATE memories SET associated_memories = '{bad' WHERE id = ?", (a,))
    await db.conn.commit()
    assert await db.add_association(a, b) is True
    assert await db.remove_association(a, b) is True

    # create nested association with invalid nested json branch
    await db.add_association(a, b)
    await db.conn.execute(
        "UPDATE memories SET associated_memories = ? WHERE id = ?",
        (json.dumps([b, c]), a),
    )
    await db.conn.execute("UPDATE memories SET associated_memories = '{bad' WHERE id = ?", (b,))
    await db.conn.commit()
    assoc = await db.get_associated_memories(a, include_extended=True)
    assert isinstance(assoc, list)
    assert isinstance(await db.get_associated_memories(a, include_extended=False), list)

    # get_access_log with no filters (WHERE 1=1 path)
    all_logs = await db.get_access_log(limit=5)
    assert isinstance(all_logs, list)

    # close_db_manager no-op branch when already closed
    await close_db_manager()
    await close_db_manager()


@pytest.mark.asyncio
async def test_remaining_lightweight_branches(monkeypatch):
    # discover: domain all and env flag helper
    all_res = json.loads(await discover.handle_discover({"domain": "all", "limit": 1}))
    assert all_res["success"] is True
    monkeypatch.setenv("AXOM_FLAG_TEST", "true")
    assert discover._env_flag_enabled("AXOM_FLAG_TEST") is True

    # exec: not-a-file branch, successful write branch, and execute_chain partial branches
    nf = json.loads(await exec_handler._handle_read(str(Path.cwd())))
    assert "Not a file" in nf["error"]
    outfile = Path.cwd() / ".cov_exec_success.txt"
    ok_write = json.loads(await exec_handler._handle_write(str(outfile), "ok"))
    assert ok_write["success"] is True
    outfile.unlink(missing_ok=True)

    eng = exec_handler.ChainEngine(handlers={"noop": AsyncMock(return_value={"ok": True})})
    empty = await eng.execute_chain({"a": 1}, [])
    assert empty["final_result"] == {"a": 1}
    full = await eng.execute_chain(
        {"success": True},
        [{"tool": "noop", "args": {"x": 1}, "condition": "${_result.success}"}],
    )
    assert full["steps"][0]["result"]["ok"] is True

    # memory enum conversion branches in list/search helpers
    db = SimpleNamespace(
        list_memories=AsyncMock(return_value=[]),
        search_memories=AsyncMock(return_value=[]),
    )
    list_out = json.loads(
        await memory._handle_list(
            SimpleNamespace(
                limit=5,
                memory_type=memory.MemoryType.LONG_TERM,
                importance=memory.ImportanceLevel.LOW,
            ),
            db,
        )
    )
    assert list_out["success"] is True
    search_out = json.loads(
        await memory._handle_search(
            SimpleNamespace(
                query="q",
                limit=5,
                memory_type=memory.MemoryType.LONG_TERM,
                importance=memory.ImportanceLevel.LOW,
                tags=None,
            ),
            db,
        )
    )
    assert search_out["success"] is True

    # analyze duplicate/refactor branches.
    dup_code = "x = 'longline12345'\n" * 4
    ref = await analyze._analyze_refactor(dup_code, None, "low")
    assert ref["type"] == "refactor"

    # transform remaining formatting/parser branches.
    yaml_parsed = transform._parse_input("a: 1", "yaml")
    assert yaml_parsed is not None
    _ = transform._parse_simple_yaml("# comment\n")
    parsed_md = transform._parse_markdown("intro\n# H")
    assert parsed_md["sections"]
    assert transform._format_output({"a": 1}, "markdown").startswith("# Data")
    assert transform._format_output({"code": "print(1)"}, "code") == "print(1)"
    assert "child" in transform._format_simple_yaml({"a": {"child": 1}})
    assert "a" in transform._format_csv({"a": 1})


@pytest.mark.asyncio
async def test_analyze_and_discover_remaining_statement_paths():
    # analyze line 70: read from a real file within cwd
    p = Path.cwd() / ".cov_analyze.py"
    p.write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    detailed = json.loads(
        await analyze.handle_analyze(
            {"type": "test", "target": str(p), "output_format": "detailed"}
        )
    )
    assert detailed["type"] == "test"
    p.unlink(missing_ok=True)

    # analyze line 89 and 91 paths via handle_analyze
    ref = json.loads(
        await analyze.handle_analyze(
            {"type": "refactor", "target": "if x:\n    if y:\n        pass"}
        )
    )
    assert ref["type"] == "refactor"
    tst = json.loads(
        await analyze.handle_analyze(
            {
                "type": "test",
                "target": "import pytest\ndef test_a():\n    assert True",
            }
        )
    )
    assert tst["type"] == "test"

    # analyze complexity branch
    long_func = "def big():\n" + "\n".join(["    x = 1" for _ in range(60)])
    rev = await analyze._analyze_review(long_func, None, "high")
    assert any(i["type"] == "complexity" for i in rev["issues"])

    # test indicator accumulation branch
    test_scan = await analyze._analyze_test(
        "def test_x():\n    assert True\nimport pytest", None, "low"
    )
    assert test_scan["issues_found"] is False

    # discover line 113 filter branch
    disc = json.loads(
        await discover._discover_files(
            {"path": str(Path.cwd()), "pattern": "*", "type": "file"}, 5, False
        )
    )
    assert disc["success"] is True


@pytest.mark.asyncio
async def test_database_remaining_statement_paths(tmp_path, monkeypatch):
    db_path = tmp_path / "db_final_edges.db"
    await close_db_manager()
    monkeypatch.setenv("AXOM_DB_PATH", str(db_path))
    db = await get_db_manager()

    source = await db.create_memory(name="src", content="s")
    target = await db.create_memory(name="tgt", content="t")
    nested = await db.create_memory(name="nested", content="n")

    # line 680
    assert await db.get_associated_memories("missing-id") == []

    # lines 684-685 malformed JSON
    await db.conn.execute(
        "UPDATE memories SET associated_memories = '{bad' WHERE id = ?", (source,)
    )
    await db.conn.commit()
    assert await db.get_associated_memories(source) == []

    # nested extension and dedupe loop paths
    await db.conn.execute(
        "UPDATE memories SET associated_memories = ? WHERE id = ?",
        (json.dumps([target, target]), source),
    )
    await db.conn.execute(
        "UPDATE memories SET associated_memories = ? WHERE id = ?",
        (json.dumps([nested]), target),
    )
    await db.conn.commit()
    assoc = await db.get_associated_memories(source, include_extended=True)
    assert len(assoc) >= 1

    # _row_to_dict malformed decode paths
    await db.conn.execute(
        "UPDATE memories SET metadata = '{bad', tags = '{bad', associated_memories = '{bad' WHERE id = ?",
        (source,),
    )
    await db.conn.commit()
    loaded = await db.get_memory(source)
    assert loaded is not None

    # remove_association malformed JSON decode except branch
    await db.conn.execute(
        "UPDATE memories SET associated_memories = '{bad' WHERE id = ?",
        (source,),
    )
    await db.conn.commit()
    assert await db.remove_association(source, target) is True

    # ensure_schema warning branch
    manager = DatabaseManager(str(tmp_path / "warn.db"))
    await manager.initialize()

    async def bad_executescript(_sql):
        raise RuntimeError("schema warning")

    manager.conn.executescript = bad_executescript  # type: ignore[assignment]
    await manager.ensure_schema()
    await manager.close()

    # close with no connection branch
    empty = DatabaseManager(str(tmp_path / "empty.db"))
    await empty.close()

    await close_db_manager()
