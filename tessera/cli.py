"""
Command-line interface for Tessera.

Usage:
    tessera init <storage_dir>
    tessera write <storage_dir> --id ID --type factual|preference|procedural_anchor \\
        --episode EP_ID --content "..." --tags tag1,tag2 --entity "Name:description"
    tessera index <storage_dir>
    tessera query <storage_dir> "question text" [--top-n 3] [--no-resolve-conflicts]
"""

import argparse
import os
import sys
import json
from typing import Dict

from .engine import TesseraEngine
from .models import Connection, Entity
from .orchestrator import TesseraOrchestrator
from .skills import install_default_skills, list_default_skill_files

# Default storage directory, used whenever `storage_dir` is omitted from the
# command line. Resolution order: `--dir` flag > `LAO_MEM_DIR` env var >
# `./memories` in the current working directory. This lets `tessera list`,
# `tessera query "..."`, etc. work without repeating the path every time once
# `LAO_MEM_DIR` is exported (e.g. `export LAO_MEM_DIR=.claude/memory`).
DEFAULT_STORAGE_DIR = os.environ.get("LAO_MEM_DIR", "./memories")


def _parse_entities(raw_entities):
    entities = []
    for raw in raw_entities or []:
        if ":" in raw:
            name, desc = raw.split(":", 1)
        else:
            name, desc = raw, ""
        entities.append(Entity(name.strip(), desc.strip()))
    return entities


def _parse_connections(raw_connections):
    """
    Parses repeatable --related-to "target_id:relation_type" flags into
    Connection objects. relation_type defaults to "related_to" if omitted.
    """
    connections = []
    for raw in raw_connections or []:
        if ":" in raw:
            target_id, relation = raw.split(":", 1)
        else:
            target_id, relation = raw, "related_to"
        connections.append(Connection(target_memory_id=target_id.strip(), relation_type=relation.strip()))
    return connections


def cmd_init(args):
    engine = TesseraEngine(storage_dir=args.storage_dir)
    engine.build_index()
    from .display import get_console, render_init_result

    console = get_console(force_plain=getattr(args, "plain", False))
    if console is not None:
        render_init_result(console, os.path.abspath(args.storage_dir), engine.graph.number_of_nodes())
        return
    print(f"✔ Diretório de memórias inicializado em: {os.path.abspath(args.storage_dir)}")
    print(f"  ({engine.graph.number_of_nodes()} nós já encontrados/indexados)")


def cmd_write(args):
    engine = TesseraEngine(storage_dir=args.storage_dir)
    tags = args.tags.split(",") if args.tags else []
    entities = _parse_entities(args.entity)
    active_connections = _parse_connections(args.related_to)
    result = engine.write_memory_note_result(
        mem_id=args.id,
        mem_type=args.type,
        episode_id=args.episode,
        content=args.content,
        tags=tags,
        entities=entities,
        active_connections=active_connections,
    )
    if getattr(args, "json", False):
        print(json.dumps(result.to_dict(), ensure_ascii=False, sort_keys=True))
        return 0 if result.persisted else 2

    if not result.persisted:
        decision = result.decision
        print(
            f"✘ Nota não gravada: admission={decision.admission.value}; "
            f"reasons={','.join(decision.reasons)}",
            file=sys.stderr,
        )
        return 2

    filepath = result.filepath or ""
    conn_ids = [c.target_memory_id for c in active_connections]

    from .display import get_console, render_write_result

    console = get_console(force_plain=getattr(args, "plain", False))
    if console is not None:
        render_write_result(console, filepath, args.id, args.type, conn_ids)
        return 0
    print(f"✔ Nota de memória gravada em: {filepath}")
    print(
        f"  security: admission={result.decision.admission.value}; "
        f"content_changed={str(result.decision.content_changed).lower()}; "
        f"is_sanitized={str(result.decision.is_sanitized).lower()}"
    )
    if active_connections:
        print(f"  ({len(active_connections)} conexão(ões) explícita(s) registrada(s): "
              f"{', '.join(conn_ids)})")
    return 0


def cmd_index(args):
    print(f"[tessera] Indexando: {os.path.abspath(args.storage_dir)}", file=sys.stderr)
    engine = TesseraEngine(storage_dir=args.storage_dir)
    # `tessera index` means "rebuild now" — always force a fresh scan, ignoring
    # any existing cache, then persist the new result to .tessera_index/.
    engine.build_index(use_cache=False)

    from .display import get_console, render_index_result

    console = get_console(force_plain=getattr(args, "plain", False))
    if console is not None:
        render_index_result(
            console, args.storage_dir, engine.graph.number_of_nodes(), engine.graph.number_of_edges(),
            str(engine.index_cache_pkl), str(engine.index_cache_json),
        )
        return
    print(
        f"✔ Índice reconstruído: {engine.graph.number_of_nodes()} nós, "
        f"{engine.graph.number_of_edges()} arestas. (fonte: {args.storage_dir})"
    )
    print(
        f"  Persistido em: {engine.index_cache_pkl} (binário) e {engine.index_cache_json} (legível)",
        file=sys.stderr,
    )


def cmd_query(args):
    print(f"[tessera] storage_dir: {args.storage_dir}  |  query: {args.query!r}", file=sys.stderr)
    engine = TesseraEngine(storage_dir=args.storage_dir)
    engine.build_index()
    if engine.graph.number_of_nodes() == 0:
        print(
            f"Nenhuma nota de memória indexada em '{args.storage_dir}'. "
            "Verifique o caminho (ou exporte LAO_MEM_DIR)."
        )
        return
    results = engine.retrieve_context(
        query_text=args.query,
        top_n=args.top_n,
        resolve_conflicts=not args.no_resolve_conflicts,
    )
    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2, default=str))
        return
    if not results:
        print("Nenhuma memória relevante encontrada para essa consulta.")
        return

    if args.paths_only:
        # Just the file path of each hit, one per line — for piping into
        # another tool (cat/xargs/an editor), not for reading the body here.
        for r in results:
            print(r.get("filepath") or r.get("filename") or r["id"])
        return

    from .display import get_console, render_query_results

    console = get_console(force_plain=getattr(args, "plain", False))
    if console is not None:
        render_query_results(
            results, console, show_related=args.show_related, show_body=not args.no_body, show_debug=getattr(args, "debug", False)
        )
        return

    for i, r in enumerate(results, 1):
        print(f"\n[{i}] {r['id']} ({r['type']}) — score={r['score']:.4f}  [{r.get('filename', '')}]")
        if getattr(args, "debug", False) and r.get("score_explain"):
            exp = r["score_explain"]
            print(f"    debug: final={r['score']:.3f} | tfidf={exp.get('lexical_tfidf', 0.0):.2f} | overlap={exp.get('lexical_overlap', 0.0):.2f} | title={exp.get('title', 0.0):.2f} | metadata={exp.get('metadata', 0.0):.2f} | raw_pr={exp.get('raw_pagerank', 0.0):.4f} | relations={exp.get('normalized_relations', 0.0):.2f} | type_boost={exp.get('type_boost', 1.0):.1f} | recency_boost={exp.get('recency_boost', 1.0):.1f}")
        if r.get("related_ids"):
            print(f"    relacionadas: {', '.join(r['related_ids'])}")
        if not args.no_body:
            print(r["body"])



def cmd_list(args):
    print(f"[tessera] Usando storage_dir: {args.storage_dir}", file=sys.stderr)
    engine = TesseraEngine(storage_dir=args.storage_dir)
    engine.build_index()
    rows = []
    for node_id, data in sorted(engine.graph.nodes(data=True)):
        node_type = data.get("node_type")
        if node_type not in {"factual", "preference", "procedural_anchor"}:
            continue
        if args.type and node_type != args.type:
            continue
        rows.append((node_id, node_type, data.get("filename", ""), data.get("filepath", "")))

    if not rows:
        print(
            f"Nenhuma nota de memória encontrada em '{args.storage_dir}'. "
            "Verifique se o caminho está correto ou rode `tessera init <dir>` primeiro."
        )
        return

    if args.paths_only:
        # Just the filepath, one per line — for piping into cat/xargs/an editor.
        for _, _, _, filepath in rows:
            print(filepath)
    elif args.table:
        from .display import get_console, print_list_plain, render_list_table

        console = get_console(force_plain=getattr(args, "plain", False))
        if console is not None:
            render_list_table(rows, console)
        else:
            print_list_plain(rows)
    else:
        for node_id, node_type, filename, _ in rows:
            print(f"{node_id}\t{node_type}\t{filename}")

    print(f"\n({len(rows)} notas indexadas)", file=sys.stderr)


def cmd_skills_install(args):
    engine = TesseraEngine(storage_dir=args.storage_dir)
    paths = install_default_skills(engine)

    from .display import get_console, render_skills_install_result

    console = get_console(force_plain=getattr(args, "plain", False))
    if console is not None:
        render_skills_install_result(console, [str(p) for p in paths], os.path.abspath(args.storage_dir))
        return
    print(f"✔ {len(paths)} âncoras procedimentais instaladas em {os.path.abspath(args.storage_dir)}:")
    for p in paths:
        print(f"  - {p}")


def cmd_skills_list(args):
    skill_ids = [path.stem for path in list_default_skill_files()]

    from .display import get_console, render_skills_list_result

    console = get_console(force_plain=getattr(args, "plain", False))
    if console is not None:
        render_skills_list_result(console, skill_ids)
        return
    for skill_id in skill_ids:
        print(skill_id)


def cmd_start(args):
    """Runs the full Need -> Planner -> Retrieval -> Inference pipeline (TesseraOrchestrator)."""
    print(f"[tessera] storage_dir: {args.storage_dir}  |  task: {args.task!r}", file=sys.stderr)
    engine = TesseraEngine(storage_dir=args.storage_dir)
    engine.build_index()

    from .llm_bridge import resolve_llm_fn

    llm_fn, backend_name = resolve_llm_fn(return_backend_name=True)
    if llm_fn is None:
        print("[tessera] FATAL: A real LLM backend is required but none is configured.", file=sys.stderr)
        sys.exit(1)
        
    if backend_name == "azure":
        print(
            "[tessera] backend=azure (Azure AI Gateway, ~2s/call, "
            "~6s total for the 3-step pipeline).",
            file=sys.stderr,
        )
    else:
        azure_key_present = bool(os.environ.get("TESSERA_AZURE_GATEWAY_API_KEY"))
        hint = (
            "" if azure_key_present else
            " (dica: TESSERA_AZURE_GATEWAY_API_KEY não está no ambiente atual — "
            "rode 'set -a && source .env && set +a' antes, se quiser o backend "
            "Azure, ~5-6x mais rápido)"
        )
        print(
            f"[tessera] backend=engine_router (subprocess CLI, "
            f"~9-13s/call, ~30-40s total for the 3-step pipeline){hint}.",
            file=sys.stderr,
        )

    from .display import get_console, print_banner, render_query_results

    console = get_console(force_plain=getattr(args, "plain", False))
    if console is not None:
        print_banner(console)

    def step_callback(step_name, data):
        if console is not None:
            if step_name == "information_need":
                console.print(f"[bold]🧠 Necessidade de informação:[/bold] {data}")
            elif step_name == "retrieval_query":
                console.print(f"[bold]🔎 Consulta de busca planejada:[/bold] {data}")
            elif step_name == "target_stores":
                console.print(f"[bold]🗂️  Gavetas consultadas:[/bold] {', '.join(data)}")
            elif step_name == "raw_memories":
                console.print(f"[bold]📚 Memórias brutas recuperadas:[/bold] {len(data)}")
                if data:
                    console.print()
                    console.rule("[bold]Memórias usadas como evidência[/bold]", style="dim")
                    render_query_results(data, console, show_related=True, show_body=False)
            elif step_name == "consolidated_context":
                from rich.panel import Panel
                console.print()
                console.rule("[bold yellow]Contexto Consolidado[/bold yellow]")
                console.print(Panel(data, border_style="yellow"))
        else:
            if step_name == "information_need":
                print(f"🧠 Necessidade de informação: {data}")
            elif step_name == "retrieval_query":
                print(f"🔎 Consulta de busca planejada: {data}")
            elif step_name == "target_stores":
                print(f"🗂️  Gavetas consultadas: {', '.join(data)}")
            elif step_name == "raw_memories":
                print(f"📚 Memórias brutas recuperadas: {len(data)}")
                for i, m in enumerate(data, 1):
                    filepath = m.get("filepath") or m.get("filename") or ""
                    print(f"  [{i}] {m['id']} ({m['type']}) score={m['score']:.4f}  [{filepath}]")
            elif step_name == "consolidated_context":
                print("\n--- Contexto Consolidado ---")
                print(data)

    orchestrator = TesseraOrchestrator(engine, llm_fn=llm_fn)
    result = orchestrator.run(task_instruction=args.task, top_n=args.top_n, step_callback=step_callback)


def cmd_decompose(args):
    """QUMem-style automatic typed decomposition of a raw episode (beginning/middle/end)
    into N atomic facts/preferences/insights, written through the normal gated path."""
    from .models import Episode

    print(f"[tessera] storage_dir: {args.storage_dir}  |  mem_id_prefix: {args.mem_id_prefix!r}", file=sys.stderr)
    engine = TesseraEngine(storage_dir=args.storage_dir)
    engine.build_index()

    from .llm_bridge import resolve_llm_fn

    llm_fn, backend_name = resolve_llm_fn(return_backend_name=True)
    if llm_fn is None:
        print("[tessera] FATAL: A real LLM backend is required but none is configured.", file=sys.stderr)
        sys.exit(1)
        
    print(f"[tessera] backend={backend_name}.", file=sys.stderr)

    episode = Episode(beginning=args.beginning, middle=args.middle, end=args.end)
    tags = args.tags.split(",") if args.tags else []

    filepaths = engine.decompose_and_write_episode(
        mem_id_prefix=args.mem_id_prefix,
        episode_id=args.episode_id or args.mem_id_prefix,
        episode=episode,
        llm_fn=llm_fn,
        tags=tags,
    )
    engine.build_index()

    from .display import get_console

    console = get_console(force_plain=getattr(args, "plain", False))
    if console is not None and filepaths:
        console.print(f"[bold green]✔[/bold green] {len(filepaths)} memória(s) atômica(s) extraída(s) e gravada(s):")
        for p in filepaths:
            console.print(f"  [dim]-[/dim] {p}")
        return
    if console is not None:
        console.print("[yellow]![/yellow] Nenhuma memória extraída deste episódio (nada julgado digno de persistir).")
        return

    if not filepaths:
        print("Nenhuma memória extraída deste episódio (nada julgado digno de persistir).")
        return
    print(f"✔ {len(filepaths)} memória(s) atômica(s) extraída(s) e gravada(s):")
    for p in filepaths:
        print(f"  - {p}")


def cmd_stats(args):
    engine = TesseraEngine(storage_dir=args.storage_dir)
    engine.build_index()

    type_counts: Dict[str, int] = {}
    for _node_id, data in engine.graph.nodes(data=True):
        node_type = data.get("node_type", "unknown")
        type_counts[node_type] = type_counts.get(node_type, 0) + 1
    edge_count = engine.graph.number_of_edges()

    from .display import get_console, print_stats_plain, render_stats_result

    console = get_console(force_plain=getattr(args, "plain", False))
    if console is not None:
        render_stats_result(console, args.storage_dir, type_counts, edge_count)
        return
    print_stats_plain(args.storage_dir, type_counts, edge_count)


def cmd_doctor(args):
    from .diagnostics import run_doctor
    from .display import get_console, print_doctor_report_plain, render_doctor_report

    report = run_doctor(args.storage_dir)

    console = get_console(force_plain=getattr(args, "plain", False))
    if console is not None:
        render_doctor_report(console, report)
    else:
        print_doctor_report_plain(report)

    sys.exit(0 if report.all_ok else 1)


def cmd_quickstart(args):
    from .diagnostics import apply_quickstart_plan, build_quickstart_plan
    from .display import get_console, print_quickstart_plan_plain, render_quickstart_plan

    plan = build_quickstart_plan(project_root=args.project_root, storage_dir=args.storage_dir)
    if args.apply:
        plan = apply_quickstart_plan(plan)

    console = get_console(force_plain=getattr(args, "plain", False))
    if console is not None:
        render_quickstart_plan(console, plan, applied=args.apply)
    else:
        print_quickstart_plan_plain(plan, applied=args.apply)


def cmd_banner(args):
    from .display import get_console, print_banner

    console = get_console(force_plain=getattr(args, "plain", False))
    if console is None:
        print("Tessera — Temporal Evolving State Synthesis with Explicit Relations and Atomic Memories")
        return
    print_banner(console)


def build_parser():
    parser = argparse.ArgumentParser(prog="tessera", description="Tessera — Temporal Evolving State Synthesis with Explicit Relations and Atomic Memories CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    # Shared --plain flag for the 3 commands with colorized Rich output
    # (query/list/start) — forces plain-text rendering even on a TTY (color
    # is already auto-disabled when piped/NO_COLOR is set; --plain is for
    # when you're on a real terminal but still want the old scriptable text).
    plain_parent = argparse.ArgumentParser(add_help=False)
    plain_parent.add_argument("--plain", action="store_true",
                               help="Force plain-text output (no colors/tables), even on a TTY.")

    p_init = sub.add_parser("init", help="Initialize a memory storage directory", parents=[plain_parent])
    p_init.add_argument("storage_dir", nargs="?", default=DEFAULT_STORAGE_DIR,
                         help=f"Path to the memory storage dir (default: {DEFAULT_STORAGE_DIR!r}, from --dir/LAO_MEM_DIR/./memories)")
    p_init.set_defaults(func=cmd_init)

    p_write = sub.add_parser("write", help="Write a new memory note", parents=[plain_parent])
    p_write.add_argument("storage_dir", nargs="?", default=DEFAULT_STORAGE_DIR,
                          help=f"Path to the memory storage dir (default: {DEFAULT_STORAGE_DIR!r})")
    p_write.add_argument("--id", required=True)
    p_write.add_argument("--type", required=True, choices=["factual", "preference", "procedural_anchor"])
    p_write.add_argument("--episode", required=True)
    p_write.add_argument("--content", required=True)
    p_write.add_argument("--tags", default="")
    p_write.add_argument("--json", action="store_true", help="Emit the canonical write decision as JSON")
    p_write.add_argument("--entity", action="append", help='Format "Name:description", repeatable')
    p_write.add_argument("--related-to", action="append",
                          help='Format "target_memory_id:relation_type" (relation_type defaults to '
                               '"related_to"), repeatable. Creates explicit graph edges, mirroring '
                               'what /lao-save-learning documents.')
    p_write.set_defaults(func=cmd_write)

    p_index = sub.add_parser("index", help="Rebuild the in-memory knowledge graph index", parents=[plain_parent])
    p_index.add_argument("storage_dir", nargs="?", default=DEFAULT_STORAGE_DIR,
                          help=f"Path to the memory storage dir (default: {DEFAULT_STORAGE_DIR!r})")
    p_index.set_defaults(func=cmd_index)

    p_query = sub.add_parser("query", help="Retrieve relevant memories for a query", parents=[plain_parent])
    p_query.add_argument("storage_dir", nargs="?", default=DEFAULT_STORAGE_DIR,
                           help=f"Path to the memory storage dir (default: {DEFAULT_STORAGE_DIR!r})")
    p_query.add_argument("query")
    p_query.add_argument("--top-n", type=int, default=7)
    p_query.add_argument("--no-resolve-conflicts", action="store_true")
    p_query.add_argument("--paths-only", action="store_true",
                           help="Print only the filepath of each hit (one per line), no body/score")
    p_query.add_argument("--show-related", action="store_true",
                           help="Also print the ids of directly-connected notes (graph neighbors)")
    p_query.add_argument("--no-body", action="store_true",
                           help="Print id/score/filename/related but skip the note body text")
    p_query.add_argument("--debug", action="store_true",
                         help="Show explainable score breakdown for retrieved memories")
    p_query.add_argument("--json", action="store_true",
                         help="Print the complete machine-readable retrieval contract as JSON")
    p_query.set_defaults(func=cmd_query)

    p_list = sub.add_parser("list", help="List indexed memory notes", parents=[plain_parent])
    p_list.add_argument("storage_dir", nargs="?", default=DEFAULT_STORAGE_DIR,
                         help=f"Path to the memory storage dir (default: {DEFAULT_STORAGE_DIR!r})")
    p_list.add_argument("--type", choices=["factual", "preference", "procedural_anchor"], default=None)
    p_list.add_argument("--paths-only", action="store_true",
                         help="Print only the filepath of each note (one per line)")
    p_list.add_argument("--table", action="store_true",
                         help="Aligned human-readable columns instead of tab-separated output")
    p_list.set_defaults(func=cmd_list)

    p_skills = sub.add_parser("skills", help="Manage bundled default skills (procedural anchors)")
    skills_sub = p_skills.add_subparsers(dest="skills_command", required=True)

    p_skills_install = skills_sub.add_parser("install", help="Install the 5 bundled default skills into a storage dir",
                                              parents=[plain_parent])
    p_skills_install.add_argument("storage_dir", nargs="?", default=DEFAULT_STORAGE_DIR,
                                   help=f"Path to the memory storage dir (default: {DEFAULT_STORAGE_DIR!r})")
    p_skills_install.set_defaults(func=cmd_skills_install)

    p_skills_list = skills_sub.add_parser("list", help="List the bundled default skill IDs", parents=[plain_parent])
    p_skills_list.set_defaults(func=cmd_skills_list)

    p_start = sub.add_parser(
        "start", help="Run the full Need->Planner->Retrieval->Inference orchestrator pipeline for a task",
        parents=[plain_parent],
    )
    p_start.add_argument("storage_dir", nargs="?", default=DEFAULT_STORAGE_DIR,
                          help=f"Path to the memory storage dir (default: {DEFAULT_STORAGE_DIR!r})")
    p_start.add_argument("task")
    p_start.add_argument("--top-n", type=int, default=7)
    p_start.set_defaults(func=cmd_start)

    p_decompose = sub.add_parser(
        "decompose",
        help="QUMem-style: mechanically extract N atomic facts/preferences/insights from a raw episode",
        parents=[plain_parent],
    )
    p_decompose.add_argument("storage_dir", nargs="?", default=DEFAULT_STORAGE_DIR,
                              help=f"Path to the memory storage dir (default: {DEFAULT_STORAGE_DIR!r})")
    p_decompose.add_argument("--mem-id-prefix", required=True,
                              help='Domain-prefixed prefix, e.g. "research/some-topic" or "lao/some-run" - '
                                   'each extracted memory is written as "{prefix}/{type}-{n}".')
    p_decompose.add_argument("--episode-id", default=None,
                              help="Episode id to stamp on every extracted note (default: same as --mem-id-prefix).")
    p_decompose.add_argument("--beginning", required=True, help="Episode's beginning (goal/context/trigger).")
    p_decompose.add_argument("--middle", required=True, help="Episode's middle (what actually happened).")
    p_decompose.add_argument("--end", required=True, help="Episode's end (outcome/resolution/lesson).")
    p_decompose.add_argument("--tags", default="", help="Comma-separated tags applied to every extracted note.")
    p_decompose.set_defaults(func=cmd_decompose)

    p_banner = sub.add_parser("banner", help="Print the Tessera ASCII logo/banner", parents=[plain_parent])
    p_banner.set_defaults(func=cmd_banner)

    p_stats = sub.add_parser(
        "stats", help="Show index composition: real notes vs. internal tag/entity graph nodes",
        parents=[plain_parent],
    )
    p_stats.add_argument("storage_dir", nargs="?", default=DEFAULT_STORAGE_DIR,
                          help=f"Path to the memory storage dir (default: {DEFAULT_STORAGE_DIR!r})")
    p_stats.set_defaults(func=cmd_stats)

    p_doctor = sub.add_parser(
        "doctor", help="Run post-install smoke tests (writable dir, index builds, write/read round-trip, deps)",
        parents=[plain_parent],
    )
    p_doctor.add_argument("storage_dir", nargs="?", default=DEFAULT_STORAGE_DIR,
                           help=f"Path to the memory storage dir (default: {DEFAULT_STORAGE_DIR!r})")
    p_doctor.set_defaults(func=cmd_doctor)

    p_quickstart = sub.add_parser(
        "quickstart", help="Detect the current project and generate a ready-to-paste MCP config block",
        parents=[plain_parent],
    )
    p_quickstart.add_argument("--project-root", default=None,
                               help="Project root to detect (default: current directory)")
    p_quickstart.add_argument("--storage-dir", dest="storage_dir", default=None,
                               help="Force a specific storage_dir instead of auto-detecting one")
    p_quickstart.add_argument("--apply", action="store_true",
                               help="Actually create storage_dir and run the first index build (default: dry-run plan only)")
    p_quickstart.set_defaults(func=cmd_quickstart)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args) or 0
    except BrokenPipeError:
        # Harmless: happens when output is piped into `head`/`grep -m` and the
        # reader closes early. Exit quietly instead of printing a traceback.
        sys.stderr.close()
        sys.exit(0)


if __name__ == "__main__":
    sys.exit(main())
