"""
TESSERA MCP Server — exposes the TESSERA engine as a Model Context Protocol server.

Tools:
    rebuild_index()                 — re-scans the storage dir and rebuilds the graph.
    query_memories(query, top_n)    — DW-PR retrieval + conflict containment.
    query_store(query, store)       — same, scoped to one typed store.
    write_memory(...)               — gated, sanitized write of a new memory note.
    decompose_episode(...)          — QUMem-style automatic typed decomposition: mechanically
                                       extracts N atomic facts/preferences/insights from a raw
                                       beginning/middle/end episode instead of writing one note
                                       per type by hand.
    query_memories_pipeline(task, top_n)
                                     — optional Need->Planner->Inference pipeline using the
                                       configured LLM backend around deterministic retrieval.
    get_index_composition()         — real notes vs. internal tag/entity node breakdown.
    run_doctor(storage_dir)          — post-install smoke tests (equivalent to `tessera doctor`).
    run_quickstart(project_root, storage_dir, apply) — project detection + MCP config
                                       generation (equivalent to `tessera quickstart`).

Resources:
    memories://{memory_id}          — raw content of a single memory note.
    graph://index                   — JSON stats about the current graph index.

Run directly:
    TESSERA_STORAGE_DIR=/path/to/memories python -m tessera.mcp_server
    # or, after `pip install tessera[mcp]`:
    tessera-mcp

Claude Desktop / Cursor config example:
    {
      "mcpServers": {
        "tessera": {
          "command": "tessera-mcp",
          "env": { "TESSERA_STORAGE_DIR": "/absolute/path/to/memories" }
        }
      }
    }
"""

import os
from typing import Any, Dict, List, Literal, Optional

from .config import resolve_runtime_configuration
from .models import Connection, Entity
from .evidence import retrieval_results_contract

from .mcp_runtime import EngineProxy, MCPRuntime, RuntimeFailure, current_runtime as _current_runtime

from functools import partial

_default_runtime = MCPRuntime()
current_runtime = partial(_current_runtime, _default_runtime)
_engine = EngineProxy(_default_runtime)
_hook = None  # Optional orchestration is constructed only for an assisted request.


class _LazyServer:
    """Keep importing the adapter free of configuration, filesystem and SDK activity."""

    name = "tessera"

    def run(self):
        create_server().run()


mcp = _LazyServer()


def create_server(configuration=None, *, provider=None, provider_options=None,
                  request_timeout=60.0):
    """Create an isolated stdio server; no Engine/provider is started until lifespan."""
    from .mcp_transport import build_server

    return build_server(MCPRuntime(
        configuration=configuration, provider=provider,
        provider_options=provider_options, request_timeout=request_timeout,
    ))


def rebuild_index() -> Dict[str, Any]:
    """Re-scans the memory storage directory and rebuilds the in-memory knowledge graph."""
    _engine.build_index()
    return {
        "storage_dir": _engine.storage_dir,
        "nodes": _engine.graph.number_of_nodes(),
        "edges": _engine.graph.number_of_edges(),
    }


def query_memories(query: str, top_n: int = 7, resolve_conflicts: bool = True) -> List[Dict[str, Any]]:
    """
    Retrieves the most relevant memory notes for a query using DW-PR subgraph
    search, preserving possible-conflict preference/factual history.

    Each result includes `filepath` (so a caller can jump straight to the
    file) and `related_ids` (other memory notes directly connected in the
    graph via tags/entities/active_connections), mirroring the CLI's
    `--paths-only` / `--show-related` output.
    """
    results = _engine.retrieve_context(query_text=query, top_n=top_n, resolve_conflicts=resolve_conflicts)
    return retrieval_results_contract(results)


def write_memory(
    mem_id: str,
    mem_type: str,
    episode_id: str,
    content: str,
    tags: Optional[List[str]] = None,
    entity_names: Optional[List[str]] = None,
    connect_to: Optional[List[str]] = None,
    relation_type: str = "related_to",
    description: str = "",
    persist_format: Literal["md"] = "md",
) -> Dict[str, Any]:
    """
    Evaluates and, only when admitted, writes a memory note. The returned
    canonical contract separates threat detection, actual transformation,
    admission, hashes, and persistence. Review/reject never rebuild the index.
    This narrow deterministic gate is not comprehensive semantic protection.

    `mem_type` must be one of: factual, preference, procedural_anchor.

    `mem_id` SHOULD carry a domain prefix: "<domain>/<slug>", for example
    "research/browser-actions/verified-collections-thesis" or
    "project/runtime-invoke-reliability". A prefixed ID keeps notes inside a
    topical subdirectory and improves discoverability. Avoid bare slugs when
    a meaningful domain is available.

    FRONTMATTER AND BODY — Provide a clear `description` and a robust `content`
    string containing the full Markdown body. Do not persist empty or anemic
    memory bodies.

    PERSIST FORMAT — `persist_format` accepts exactly "md", the canonical
    writable format discovered by TESSERA's source pipeline. Unsupported values
    fail before persistence and before the MCP-triggered index rebuild. Arbitrary
    JSON persistence/ingestion is not supported.

    `connect_to` accepts target memory IDs to create explicit graph edges
    (`active_connections`) using `relation_type`. Omit it when there are no
    explicit source-backed connections to create.
    """
    entities = [Entity(name) for name in (entity_names or [])]
    active_connections = [
        Connection(target_memory_id=target_id, relation_type=relation_type)
        for target_id in (connect_to or [])
    ]

    result = _engine.write_memory_note_result(
        mem_id=mem_id,
        mem_type=mem_type,
        episode_id=episode_id,
        content=content,
        tags=tags or [],
        entities=entities,
        active_connections=active_connections,
        description=description,
        persist_format=persist_format,
    )
    if result.persisted:
        _engine.build_index()
    payload = result.to_dict()
    payload["mem_id"] = mem_id  # compatibility alias for existing MCP clients
    payload["connected_to"] = [c.target_memory_id for c in active_connections]
    return payload


def get_memory(memory_id: str) -> str:
    """Returns the raw Markdown content (frontmatter + body) of a single memory note."""
    filepath = _engine.file_registry.get(memory_id)
    if not filepath or not os.path.exists(filepath):
        raise RuntimeFailure("NOT_FOUND", "Memory is absent from the current index.")
    from pathlib import Path

    path = Path(filepath)
    if any(part.is_symlink() for part in (path, *path.parents)):
        raise RuntimeFailure("SOURCE_CHANGED", "Indexed source became a symlink; rebuild the index.")
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


def get_index_stats() -> Dict[str, Any]:
    """Returns consolidated statistics about the current in-memory knowledge graph."""
    type_counts: Dict[str, int] = {}
    for _node_id, data in _engine.graph.nodes(data=True):
        node_type = data.get("node_type", "unknown")
        type_counts[node_type] = type_counts.get(node_type, 0) + 1

    return {
        "storage_dir": _engine.storage_dir,
        "nodes": _engine.graph.number_of_nodes(),
        "edges": _engine.graph.number_of_edges(),
        "node_type_distribution": type_counts,
    }


def query_store(query: str, store: str, top_n: int = 7, resolve_conflicts: bool = True) -> List[Dict[str, Any]]:
    """
    Retrieves memories scoped to a single typed store: 'facts', 'preferences',
    or 'insights'. Use this when you already know which drawer to open instead
    of searching across all three with `query_memories`.
    """
    results = _engine.retrieve_from_store(
        query_text=query,
        store=store,
        top_n=top_n,
        resolve_conflicts=resolve_conflicts,
    )
    return retrieval_results_contract(results)


def query_memories_pipeline(
    task_instruction: str,
    top_n: int = 7,
) -> Dict[str, Any]:
    """
    Runs the optional three-step pipeline (Information Need -> Retrieval Planner
    -> State Inference) around TESSERA retrieval. Returns the consolidated
    context plus the reasoning trail, including stores queried, rewritten query
    and raw memories preserved by non-destructive conflict containment.

    This assisted mode is optional; direct deterministic retrieval remains a
    first-class TESSERA capability.
    """
    from .orchestrator import TesseraOrchestrator

    llm_fn, backend_used = current_runtime().resolve_provider()
    # Preserve the hook's refresh-on-call behavior on the disposable snapshot.
    _engine.build_index(persist=False)
    result = TesseraOrchestrator(_engine, llm_fn=llm_fn).run(
        task_instruction, top_n=top_n
    )
    payload = result.to_dict()
    payload.pop("task_instruction", None)  # Preserve the existing hook output shape.
    payload["llm_backend_used"] = backend_used
    return payload


def get_index_composition() -> Dict[str, Any]:
    """
    Breaks down the current index by node type: real memory notes
    (factual/preference/procedural_anchor, backed by an actual .md file)
    vs. internal graph-only nodes (tag/entity) used by DW-PR ranking but not
    addressable as a note.
    """
    type_counts: Dict[str, int] = {}
    for _node_id, data in _engine.graph.nodes(data=True):
        node_type = data.get("node_type", "unknown")
        type_counts[node_type] = type_counts.get(node_type, 0) + 1

    note_types = {"factual", "preference", "procedural_anchor"}
    note_count = sum(n for t, n in type_counts.items() if t in note_types)
    internal_count = sum(n for t, n in type_counts.items() if t not in note_types)

    return {
        "storage_dir": _engine.storage_dir,
        "total_nodes": _engine.graph.number_of_nodes(),
        "total_edges": _engine.graph.number_of_edges(),
        "real_note_count": note_count,
        "internal_node_count": internal_count,
        "node_type_distribution": type_counts,
    }


def run_doctor(storage_dir: Optional[str] = None) -> Dict[str, Any]:
    """
    Runs TESSERA's post-install smoke tests: storage writability, index build,
    write/read round-trip, optional dependencies and optional LLM backend
    configuration. Required checks failing means something is broken; optional
    checks are informational only.

    Defaults to the server's configured `TESSERA_STORAGE_DIR` (or `./memories`).
    """
    from .diagnostics import run_doctor as _run_doctor

    report = _run_doctor(
        storage_dir or _engine.storage_dir,
        configuration=None if storage_dir else _engine.configuration,
    )
    return report.to_dict()


def run_quickstart(
    project_root: Optional[str] = None,
    storage_dir: Optional[str] = None,
    apply: bool = False,
) -> Dict[str, Any]:
    """
    Detects the current project, proposes a storage directory and returns a
    ready-to-paste MCP configuration block.

    By default this is a dry run (`apply=False`). Pass `apply=True` to create
    the selected storage directory and run the first index build.
    """
    from .diagnostics import apply_quickstart_plan, build_quickstart_plan

    plan = build_quickstart_plan(project_root=project_root, storage_dir=storage_dir)
    if apply:
        plan = apply_quickstart_plan(plan)
    return plan.to_dict()


def decompose_episode(
    mem_id_prefix: str,
    beginning: str,
    middle: str,
    end: str,
    episode_id: Optional[str] = None,
    tags: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    QUMem-style automatic typed decomposition: extracts N atomic
    facts/preferences/insights from a raw episode and writes each through the
    same gated typed-store path as a manual `write_memory` call.

    `mem_id_prefix` SHOULD carry a domain prefix, for example
    "research/some-topic" or "project/some-run". Extracted memories are stored
    under "{mem_id_prefix}/{type}-{n}.md".
    """
    arguments = dict(
        mem_id_prefix=mem_id_prefix, beginning=beginning, middle=middle, end=end,
        episode_id=episode_id, tags=tags,
    )
    prepared = prepare_decomposition(arguments)
    return persist_decomposition(arguments, prepared)


def prepare_decomposition(arguments):
    """Call the optional provider without giving it a persistence continuation."""
    from .decomposer import decompose_episode_result
    from .models import Episode

    llm_fn, backend = current_runtime().resolve_provider()
    result = decompose_episode_result(
        Episode(arguments["beginning"], arguments["middle"], arguments["end"]), llm_fn
    )
    if result.mode != "assisted":
        raise RuntimeFailure("PROVIDER_FAILED", "Assisted decomposition failed; no notes were written.")
    return result, backend


def persist_decomposition(arguments, prepared):
    """Reuse the canonical typed writer/gate with already accepted local candidates."""
    import json
    from .models import Episode

    result, backend = prepared
    local_response = json.dumps([
        {"type": item.mem_type, "content": item.content} for item in result.memories
    ])
    decomposition = _engine.decompose_and_write_episode_result(
        mem_id_prefix=arguments["mem_id_prefix"],
        episode_id=arguments.get("episode_id") or arguments["mem_id_prefix"],
        episode=Episode(arguments["beginning"], arguments["middle"], arguments["end"]),
        llm_fn=lambda *_: local_response, tags=arguments.get("tags") or [],
    )
    filepaths = list(decomposition.filepaths)
    if filepaths:
        _engine.build_index()
    return {
        "mem_id_prefix": arguments["mem_id_prefix"], "filepaths": filepaths,
        "count": len(filepaths), "llm_backend_used": backend,
        "llm_backend_attempted": backend, "decomposition_mode": "assisted",
        "fallback_reason": None,
    }


def get_server_health() -> Dict[str, Any]:
    """Report runtime readiness/configuration without probing providers or writing notes."""
    return current_runtime().health()


TOOLS = (
    rebuild_index, query_memories, write_memory, query_store,
    query_memories_pipeline, get_index_composition, run_doctor, run_quickstart,
    decompose_episode, get_server_health,
)
RESOURCES = {"graph://index": get_index_stats, "server://health": get_server_health}


def main(argv=None):
    import argparse
    from .config import ConfigurationResolver

    parser = argparse.ArgumentParser(description="TESSERA MCP stdio server")
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--store", help="Explicit writable store path")
    selection.add_argument("--project", help="Project configuration discovery root")
    selection.add_argument("--global", dest="global_name", help="Registered global store name")
    parser.add_argument("--request-timeout", type=float, default=60.0,
                        help="Seconds for queue/read/assisted phases; started writes finish")
    args = parser.parse_args(argv)
    try:
        configuration = (
            ConfigurationResolver().resolve(
                explicit=args.store, project=args.project, global_name=args.global_name,
            ) if any((args.store, args.project, args.global_name))
            else resolve_runtime_configuration()
        )
        create_server(configuration, request_timeout=args.request_timeout).run(transport="stdio")
    except ImportError:
        parser.exit(2, "tessera-mcp: Install the optional transport with pip install 'tessera[mcp]'.\n")
    except Exception:
        import json
        from .mcp_runtime import SCHEMA_VERSION

        parser.exit(2, json.dumps({
            "schema_version": SCHEMA_VERSION, "operation": "startup", "data": None,
            "error": {"code": "SERVER_FAILED", "message":
                "Check the configured store/index paths, permissions and positive request timeout."},
        }) + "\n")


if __name__ == "__main__":
    main()
