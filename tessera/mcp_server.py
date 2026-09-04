"""
TESSERA MCP Server — exposes the TESSERA engine as a Model Context Protocol server.

Tools:
    rebuild_index()                 — re-scans the storage dir and rebuilds the graph.
    query_memories(query, top_n)    — DW-PR subgraph retrieval + conflict resolution.
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
from .engine import TesseraEngine
from .hooks import TesseraTaskHook
from .models import Connection, Entity
from .evidence import retrieval_results_contract

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as exc:  # pragma: no cover - only hit when 'mcp' extra isn't installed
    raise ImportError(
        "The MCP server requires the 'mcp' extra. Install it with: pip install 'tessera[mcp]'"
    ) from exc

DEFAULT_CONFIGURATION = resolve_runtime_configuration()
DEFAULT_STORAGE_DIR = DEFAULT_CONFIGURATION.storage_dir

mcp = FastMCP("tessera")
_engine = TesseraEngine(configuration=DEFAULT_CONFIGURATION)
_engine.build_index()
_hook = TesseraTaskHook(_engine)


@mcp.tool()
def rebuild_index() -> Dict[str, Any]:
    """Re-scans the memory storage directory and rebuilds the in-memory knowledge graph."""
    _engine.build_index()
    return {
        "storage_dir": _engine.storage_dir,
        "nodes": _engine.graph.number_of_nodes(),
        "edges": _engine.graph.number_of_edges(),
    }


@mcp.tool()
def query_memories(query: str, top_n: int = 7, resolve_conflicts: bool = True) -> List[Dict[str, Any]]:
    """
    Retrieves the most relevant memory notes for a query using DW-PR subgraph
    search, with temporal conflict resolution applied over preferences/facts.

    Each result includes `filepath` (so a caller can jump straight to the
    file) and `related_ids` (other memory notes directly connected in the
    graph via tags/entities/active_connections), mirroring the CLI's
    `--paths-only` / `--show-related` output.
    """
    results = _engine.retrieve_context(query_text=query, top_n=top_n, resolve_conflicts=resolve_conflicts)
    return retrieval_results_contract(results)


@mcp.tool()
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


@mcp.resource("memories://{memory_id}")
def get_memory(memory_id: str) -> str:
    """Returns the raw Markdown content (frontmatter + body) of a single memory note."""
    filepath = _engine.file_registry.get(memory_id)
    if not filepath or not os.path.exists(filepath):
        return f"Memory '{memory_id}' was not found in the current index."
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


@mcp.resource("graph://index")
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


@mcp.tool()
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
    return [
        {
            "id": r["id"],
            "type": r["type"],
            "score": r["score"],
            "body": r["body"],
            "filename": r.get("filename"),
        }
        for r in results
    ]


@mcp.tool()
def query_memories_pipeline(
    task_instruction: str,
    top_n: int = 7,
) -> Dict[str, Any]:
    """
    Runs the optional three-step pipeline (Information Need -> Retrieval Planner
    -> State Inference) around TESSERA retrieval. Returns the consolidated
    context plus the reasoning trail, including stores queried, rewritten query
    and raw memories that survived conflict resolution.

    This assisted mode is optional; direct deterministic retrieval remains a
    first-class TESSERA capability.
    """
    from .llm_bridge import resolve_llm_fn

    llm_fn, backend_used = resolve_llm_fn(return_backend_name=True)
    if llm_fn is None:
        raise ValueError("FATAL: A real LLM backend is required but none is configured.")

    result = _hook.on_task_start(task_instruction, top_n=top_n, llm_fn=llm_fn)
    payload = result.to_dict()
    payload["llm_backend_used"] = backend_used
    return payload


@mcp.tool()
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


@mcp.tool()
def run_doctor(storage_dir: Optional[str] = None) -> Dict[str, Any]:
    """
    Runs TESSERA's post-install smoke tests: storage writability, index build,
    write/read round-trip, optional dependencies and optional LLM backend
    configuration. Required checks failing means something is broken; optional
    checks are informational only.

    Defaults to the server's configured `TESSERA_STORAGE_DIR` (or `./memories`).
    """
    from .diagnostics import run_doctor as _run_doctor

    report = _run_doctor(storage_dir or _engine.storage_dir)
    return report.to_dict()


@mcp.tool()
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


@mcp.tool()
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
    from .models import Episode
    from .llm_bridge import resolve_llm_fn

    llm_fn, backend_used = resolve_llm_fn(return_backend_name=True)
    if llm_fn is None:
        raise ValueError("FATAL: A real LLM backend is required but none is configured.")

    episode = Episode(beginning=beginning, middle=middle, end=end)
    decomposition = _engine.decompose_and_write_episode_result(
        mem_id_prefix=mem_id_prefix,
        episode_id=episode_id or mem_id_prefix,
        episode=episode,
        llm_fn=llm_fn,
        tags=tags or [],
    )
    filepaths = list(decomposition.filepaths)
    mode = decomposition.decomposition.mode
    _engine.build_index()
    return {
        "mem_id_prefix": mem_id_prefix,
        "filepaths": filepaths,
        "count": len(filepaths),
        "llm_backend_used": backend_used if mode == "assisted" else None,
        "llm_backend_attempted": backend_used,
        "decomposition_mode": mode,
        "fallback_reason": decomposition.decomposition.fallback_reason,
    }


def main():
    mcp.run()


if __name__ == "__main__":
    main()
