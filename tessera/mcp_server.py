"""
Tessera MCP Server — exposes the Tessera engine as a Model Context Protocol server.

Tools:
    rebuild_index()                 — re-scans the storage dir and rebuilds the graph.
    query_memories(query, top_n)    — DW-PR subgraph retrieval + conflict resolution.
    query_store(query, store)       — same, scoped to one typed store.
    write_memory(...)               — gated, sanitized write of a new memory note.
    decompose_episode(...)          — QUMem-style automatic typed decomposition: mechanically
                                       extracts N atomic facts/preferences/insights from a raw
                                       beginning/middle/end episode instead of writing one note
                                       per type by hand. Same use_llm/llm_backend/llm_engine
                                       options as query_memories_pipeline.
    query_memories_pipeline(task, top_n, use_llm, llm_backend, llm_engine)
                                     — full Need->Planner->Inference pipeline. Offline
                                       simulation by default; pass use_llm=True for a real
                                       LLM call per step (Azure Gateway or engine_router.py,
                                       same backends as `tessera start --use-llm`).
                                       (formerly `run_task_hook` — renamed 2026-08-25)
    get_index_composition()         — real notes vs. internal tag/entity node breakdown.
    run_doctor(storage_dir)         — post-install smoke tests (equivalent to `tessera doctor`).
    run_quickstart(project_root, storage_dir, apply) — project detection + MCP config
                                       generation (equivalent to `tessera quickstart`).

Resources:
    memories://{memory_id}          — raw content of a single memory note.
    graph://index                   — JSON stats about the current graph index.

Run directly:
    LAO_MEM_DIR=/path/to/memories python -m tessera.mcp_server
    # or, after `pip install tessera[mcp]`:
    tessera-mcp

Claude Desktop / Cursor config example:
    {
      "mcpServers": {
        "tessera": {
          "command": "tessera-mcp",
          "env": { "LAO_MEM_DIR": "/absolute/path/to/memories" }
        }
      }
    }
"""

import os
from typing import Any, Dict, List, Optional

from .engine import TesseraEngine
from .hooks import TesseraTaskHook
from .models import Connection, Entity

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as exc:  # pragma: no cover - only hit when 'mcp' extra isn't installed
    raise ImportError(
        "O servidor MCP requer o extra 'mcp'. Instale com: pip install 'tessera[mcp]'"
    ) from exc

DEFAULT_STORAGE_DIR = os.environ.get("LAO_MEM_DIR", "./memories")

mcp = FastMCP("tessera")
_engine = TesseraEngine(storage_dir=DEFAULT_STORAGE_DIR)
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
    return [
        {
            "id": r["id"],
            "type": r["type"],
            "score": r["score"],
            "body": r["body"],
            "filename": r.get("filename"),
            "filepath": r.get("filepath"),
            "related_ids": r.get("related_ids", []),
        }
        for r in results
    ]


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
    persist_format: str = "md",
) -> Dict[str, Any]:
    """
    Writes (or overwrites) a memory note. Content is passed through the
    write-side gating engine (sanitization against state contamination /
    hostile instruction injection) before anything is persisted to disk.

    mem_type must be one of: factual, preference, procedural_anchor.

    IMPORTANT — mem_id MUST carry a domain prefix: "<domain>/<slug>", e.g.
    "research/browser-actions/verified-collections-thesis" or
    "lao/engine-router-invoke-reliability". Never pass a bare slug with no
    "/" (e.g. just "my-finding") — that writes the note loose at the memory
    store's root instead of inside a topical subdirectory, breaking
    discoverability and violating this project's own STRUCTURE.md
    convention (research/<topic>/, lao/, learnings/{pipeline,patterns,
    security}/, business/{okrs,context,team}/, project/, experiments/ —
    pick whichever matches the note's actual topic, or create a new
    "<domain>/" if none fit). This was silently violated once in production
    (2026-08-25/26, a Gemini-driven /lao run wrote a bare, unprefixed
    mem_id and the note landed at the memory root next to MEMORY.md/
    README.md) precisely because this docstring didn't say so explicitly.

    FRONTMATTER AND BODY — You MUST provide a clear `description` (passed directly
    to the note's frontmatter) and a robust `content` string containing the full
    markdown body (e.g. context, execution details, reasoning, results). Do not
    provide empty or anemic content bodies.

    PERSIST FORMAT — By default `persist_format` is "md", generating a markdown file.
    You may pass "json" to save directly as a JSON payload if desired.

    connect_to accepts a list of target memory ids to create explicit graph
    edges (active_connections), all tagged with the same relation_type —
    mirrors the CLI's repeatable `--related-to` flag. Pass a single-item
    list for one connection; omit/empty for none.
    """
    entities = [Entity(name) for name in (entity_names or [])]
    active_connections = [
        Connection(target_memory_id=target_id, relation_type=relation_type) for target_id in (connect_to or [])
    ]

    filepath = _engine.write_memory_note(
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
    _engine.build_index()
    return {"filepath": filepath, "mem_id": mem_id, "connected_to": [c.target_memory_id for c in active_connections]}


@mcp.resource("memories://{memory_id}")
def get_memory(memory_id: str) -> str:
    """Returns the raw Markdown content (frontmatter + body) of a single memory note."""
    filepath = _engine.file_registry.get(memory_id)
    if not filepath or not os.path.exists(filepath):
        return f"[Erro] Memória '{memory_id}' não encontrada no índice atual."
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
    or 'insights'. Use this when you already know which drawer to open
    instead of searching across all three with `query_memories`.
    """
    results = _engine.retrieve_from_store(
        query_text=query, store=store, top_n=top_n, resolve_conflicts=resolve_conflicts
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
    Runs the full 3-agent detective pipeline (Information-Need -> Retrieval
    Planner -> User-State Inference) for a task, exactly as if the LAO task
    hook had intercepted it. Returns a consolidated, validated context block
    plus the reasoning trail (which stores were queried, the rewritten
    search query, and the raw memories that survived conflict resolution).
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
    vs. internal graph-only nodes (tag/entity) used by DW-PR ranking but
    not addressable as a note. Answers "why does the note count look
    smaller than the total graph node count?" (e.g. 200 real notes + 72
    tag nodes = 272 total nodes) without needing shell access to graph.json.
    Equivalent to the CLI's `tessera stats`.
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
    Runs Tessera's post-install smoke tests: is storage_dir writable, does the
    index build without error, does a write+read round-trip work, are
    optional deps (rich, mcp extra) present, is a real LLM backend
    configured. Returns a structured report with `all_ok` and a list of
    individual checks (each with ok/detail/hint/required). Required checks
    failing means something is actually broken; optional checks (mcp extra,
    Azure Gateway key) failing is informational only and doesn't set
    all_ok=False. Defaults to the server's own configured storage_dir
    (LAO_MEM_DIR) if none is given.
    """
    from .diagnostics import run_doctor as _run_doctor

    report = _run_doctor(storage_dir or _engine.storage_dir)
    return report.to_dict()


@mcp.tool()
def run_quickstart(project_root: Optional[str] = None, storage_dir: Optional[str] = None, apply: bool = False) -> Dict[str, Any]:
    """
    Detects the current project (looks for package.json/pyproject.toml/
    Cargo.toml/go.mod/.git), proposes a storage_dir (reuses an existing
    '.claude/memory'-shaped dir if found, otherwise './memories' at the
    project root), and returns a ready-to-paste MCP config block for
    .mcp.json / .gemini/settings.json / Claude Desktop config.

    By default this is a dry-run (apply=False) — nothing is written to
    disk, it only returns the plan. Pass apply=True to actually create
    storage_dir and run the first index build.
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
    QUMem-style automatic typed decomposition: mechanically extracts N
    atomic facts/preferences/insights from a raw episode (beginning/middle/
    end) and writes each through the same gated typed-store path as a
    manual `write_memory` call — decomposition only decides *how many*
    notes get proposed, never bypasses the security/sanitization gate.

    This is the mechanical alternative to writing one note per type by
    hand: instead of deciding yourself whether something is a fact, a
    preference, or an insight, describe the whole episode and let the
    decomposer classify + split it for you.

    `mem_id_prefix` MUST carry a domain prefix (e.g. "research/some-topic"
    or "lao/some-run") - each extracted memory lands at
    "{mem_id_prefix}/{type}-{n}.md", grouping every atomic memory from this
    episode together in one topical subdirectory.
    """
    from .models import Episode

    from .llm_bridge import resolve_llm_fn
    llm_fn, backend_used = resolve_llm_fn(return_backend_name=True)
    if llm_fn is None:
        raise ValueError("FATAL: A real LLM backend is required but none is configured.")

    episode = Episode(beginning=beginning, middle=middle, end=end)
    filepaths = _engine.decompose_and_write_episode(
        mem_id_prefix=mem_id_prefix,
        episode_id=episode_id or mem_id_prefix,
        episode=episode,
        llm_fn=llm_fn,
        tags=tags or [],
    )
    _engine.build_index()
    return {
        "mem_id_prefix": mem_id_prefix,
        "filepaths": filepaths,
        "count": len(filepaths),
        "llm_backend_used": backend_used,
    }


def main():
    mcp.run()


if __name__ == "__main__":
    main()
