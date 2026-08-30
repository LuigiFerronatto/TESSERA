import copy
import importlib
import sys
import types
import warnings
from pathlib import Path
from typing import Literal, get_type_hints
from unittest.mock import Mock

import pytest
import yaml

import tessera.engine_core as engine_core
from tessera import TesseraEngine


INVALID_FORMATS = ("json", "yaml", "", "MD", "markdown", " ", None)
ERROR_TEMPLATE = (
    "Unsupported persist_format {value!r}; supported format is 'md'. "
    "No memory was persisted."
)


def _tree_snapshot(root: Path):
    """Capture every relative path plus the exact bytes of every file."""
    if not root.exists():
        return ()
    snapshot = []
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        relative = path.relative_to(root).as_posix()
        snapshot.append((relative + "/", None) if path.is_dir() else (relative, path.read_bytes()))
    return tuple(snapshot)


def _runtime_snapshot(engine: TesseraEngine):
    return {
        "file_registry": copy.deepcopy(engine.file_registry),
        "graph_nodes": copy.deepcopy(list(engine.graph.nodes(data=True))),
        "graph_edges": copy.deepcopy(list(engine.graph.edges(data=True))),
        "node_corpus": copy.deepcopy(engine.node_corpus),
        "node_ids": copy.deepcopy(engine.node_ids),
        "identity_manifest": copy.deepcopy(engine.identity_manifest),
        "evidence_ledger": copy.deepcopy(engine.evidence_ledger.to_list()),
    }


def _forbidden_call(*_args, **_kwargs):
    raise AssertionError("invalid persistence format reached a forbidden side effect")


@pytest.mark.parametrize("persist_format", INVALID_FORMATS)
def test_engine_rejects_unsupported_format_before_every_side_effect(
    tmp_path, monkeypatch, persist_format
):
    storage = tmp_path / "storage"
    engine = TesseraEngine(storage_dir=str(storage))
    tree_before = _tree_snapshot(storage)
    runtime_before = _runtime_snapshot(engine)

    monkeypatch.setattr(engine.gating_engine, "audit_and_sanitize", _forbidden_call)
    monkeypatch.setattr(engine_core, "MemoryFrontmatter", _forbidden_call)

    class ForbiddenDateTime:
        @classmethod
        def now(cls, *_args, **_kwargs):
            return _forbidden_call()

    monkeypatch.setattr(engine_core.datetime, "datetime", ForbiddenDateTime)

    with warnings.catch_warnings(record=True) as emitted:
        warnings.simplefilter("always")
        with pytest.raises(ValueError) as raised:
            engine.write_memory_note(
                mem_id="rejected",
                mem_type="factual",
                episode_id="issue-94",
                content="This content must never reach the security gate.",
                tags=["issue-94"],
                entities=[],
                persist_format=persist_format,
            )

    assert str(raised.value) == ERROR_TEMPLATE.format(value=persist_format)
    assert emitted == []
    assert _tree_snapshot(storage) == tree_before
    assert list(storage.iterdir()) == []
    assert _runtime_snapshot(engine) == runtime_before


def test_rejected_write_cannot_overwrite_source_cache_registry_graph_or_ledger(
    tmp_path, monkeypatch
):
    storage = tmp_path / "storage"
    engine = TesseraEngine(storage_dir=str(storage))
    filepath = Path(
        engine.write_memory_note(
            mem_id="contract/existing",
            mem_type="factual",
            episode_id="issue-94",
            content="Original canonical Markdown body.",
            tags=["contract"],
            entities=[],
        )
    )
    engine.build_index(use_cache=False, persist=True)

    tree_before = _tree_snapshot(storage)
    runtime_before = _runtime_snapshot(engine)
    source_before = filepath.read_bytes()
    monkeypatch.setattr(engine.gating_engine, "audit_and_sanitize", _forbidden_call)

    with pytest.raises(ValueError) as raised:
        engine.write_memory_note(
            mem_id="contract/existing",
            mem_type="factual",
            episode_id="issue-94",
            content="Attempted overwrite that must not be persisted.",
            tags=["mutated"],
            entities=[],
            persist_format="json",
        )

    assert str(raised.value) == ERROR_TEMPLATE.format(value="json")
    assert filepath.read_bytes() == source_before
    assert _tree_snapshot(storage) == tree_before
    assert _runtime_snapshot(engine) == runtime_before


def test_rejected_prefixed_write_does_not_create_parent_directory(tmp_path):
    storage = tmp_path / "storage"
    engine = TesseraEngine(storage_dir=str(storage))
    tree_before = _tree_snapshot(storage)

    with pytest.raises(ValueError):
        engine.write_memory_note(
            mem_id="new-domain/rejected",
            mem_type="factual",
            episode_id="issue-94",
            content="No parent directory may be created.",
            tags=[],
            entities=[],
            persist_format="json",
        )

    assert _tree_snapshot(storage) == tree_before
    assert not (storage / "new-domain").exists()


def test_engine_public_type_contract_is_markdown_literal():
    annotation = get_type_hints(TesseraEngine.write_memory_note)["persist_format"]
    assert annotation == Literal["md"]


@pytest.mark.parametrize("explicit_format", (False, True))
def test_markdown_write_round_trip_matches_clean_and_cached_index(
    tmp_path, explicit_format
):
    storage = tmp_path / "storage"
    memory_id = "contract/markdown-round-trip"
    engine = TesseraEngine(storage_dir=str(storage))
    kwargs = {"persist_format": "md"} if explicit_format else {}
    filepath = Path(
        engine.write_memory_note(
            mem_id=memory_id,
            mem_type="factual",
            episode_id="issue-94",
            content="Canonical Markdown remains retrievable after every rebuild path.",
            tags=["contract", "markdown"],
            entities=[],
            **kwargs,
        )
    )

    markdown_files = list(storage.rglob("*.md"))
    assert markdown_files == [filepath]
    assert filepath.suffix == ".md"
    assert list(storage.rglob("*.json")) == []

    raw = filepath.read_text(encoding="utf-8")
    _, frontmatter_text, body = raw.split("---", 2)
    frontmatter = yaml.safe_load(frontmatter_text)
    assert frontmatter["id"] == memory_id
    assert frontmatter["node_type"] == "factual"
    assert body.strip() == "Canonical Markdown remains retrievable after every rebuild path."

    clean = TesseraEngine(storage_dir=str(storage))
    clean.build_index(use_cache=False, persist=True)
    clean_results = clean.retrieve_context("canonical markdown rebuild", top_n=5)

    cached = TesseraEngine(storage_dir=str(storage))
    cached.build_index(use_cache=True, persist=False)
    cached_results = cached.retrieve_context("canonical markdown rebuild", top_n=5)

    assert [item["id"] for item in clean_results] == [memory_id]
    assert [item["id"] for item in cached_results] == [memory_id]
    assert clean.file_registry == cached.file_registry == {memory_id: str(filepath)}
    assert list(clean.graph).count(memory_id) == 1
    assert list(cached.graph).count(memory_id) == 1


def _load_mcp_server(monkeypatch, tmp_path):
    class FakeFastMCP:
        def __init__(self, _name):
            pass

        @staticmethod
        def tool():
            return lambda function: function

        @staticmethod
        def resource(_uri):
            return lambda function: function

    fastmcp_module = types.ModuleType("mcp.server.fastmcp")
    fastmcp_module.FastMCP = FakeFastMCP
    server_module = types.ModuleType("mcp.server")
    server_module.fastmcp = fastmcp_module
    mcp_module = types.ModuleType("mcp")
    mcp_module.server = server_module
    monkeypatch.setitem(sys.modules, "mcp", mcp_module)
    monkeypatch.setitem(sys.modules, "mcp.server", server_module)
    monkeypatch.setitem(sys.modules, "mcp.server.fastmcp", fastmcp_module)
    monkeypatch.setenv("TESSERA_STORAGE_DIR", str(tmp_path / "mcp-bootstrap"))
    monkeypatch.setenv("TESSERA_AZURE_GATEWAY_API_KEY", "test-only-placeholder")
    sys.modules.pop("tessera.mcp_server", None)
    return importlib.import_module("tessera.mcp_server")


def test_mcp_rejection_propagates_without_file_success_or_index_rebuild(
    tmp_path, monkeypatch
):
    mcp_server = _load_mcp_server(monkeypatch, tmp_path)
    storage = tmp_path / "storage"
    engine = TesseraEngine(storage_dir=str(storage))
    build_index = Mock(wraps=engine.build_index)
    monkeypatch.setattr(engine, "build_index", build_index)
    monkeypatch.setattr(engine.gating_engine, "audit_and_sanitize", _forbidden_call)
    monkeypatch.setattr(mcp_server, "_engine", engine)

    tree_before = _tree_snapshot(storage)
    runtime_before = _runtime_snapshot(engine)
    for persist_format in ("json", "yaml"):
        with pytest.raises(ValueError) as raised:
            mcp_server.write_memory(
                mem_id="contract/mcp-rejected",
                mem_type="factual",
                episode_id="issue-94",
                content="MCP must not acknowledge this write.",
                persist_format=persist_format,
            )
        assert str(raised.value) == ERROR_TEMPLATE.format(value=persist_format)
        assert _tree_snapshot(storage) == tree_before
        assert _runtime_snapshot(engine) == runtime_before

    assert build_index.call_count == 0


@pytest.mark.parametrize("explicit_format", (False, True))
def test_mcp_markdown_write_creates_one_source_and_rebuilds_index(
    tmp_path, monkeypatch, explicit_format
):
    mcp_server = _load_mcp_server(monkeypatch, tmp_path)
    storage = tmp_path / "storage"
    engine = TesseraEngine(storage_dir=str(storage))
    build_index = Mock(wraps=engine.build_index)
    monkeypatch.setattr(engine, "build_index", build_index)
    monkeypatch.setattr(mcp_server, "_engine", engine)
    kwargs = {"persist_format": "md"} if explicit_format else {}

    result = mcp_server.write_memory(
        mem_id="contract/mcp-markdown",
        mem_type="factual",
        episode_id="issue-94",
        content="MCP Markdown writes are immediately indexable.",
        tags=["contract"],
        **kwargs,
    )

    source_files = list(storage.rglob("*.md"))
    assert source_files == [Path(result["filepath"])]
    assert build_index.call_count == 1
    assert [item["id"] for item in engine.retrieve_context("immediately indexable", top_n=5)] == [
        "contract/mcp-markdown"
    ]
    assert get_type_hints(mcp_server.write_memory)["persist_format"] == Literal["md"]
