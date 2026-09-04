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
import warnings
from pathlib import Path
from typing import Dict

from .config import (
    CANONICAL_STORAGE_ENV,
    LEGACY_STORAGE_ENV,
    SCHEMA_VERSION,
    ConfigurationError,
    ConfigurationResolver,
    GlobalRegistry,
    discover_project_config,
    global_registry_path,
    resolve_storage_dir,
    unregister_global_store,
)
from .init_flow import (
    SOURCE_MODES,
    InitRequest,
    InitializationApplyError,
    InitializationPlan,
    apply_initialization_plan,
    build_initialization_plan,
)
from .engine import TesseraEngine
from .models import Connection, Entity
from .orchestrator import TesseraOrchestrator
from .skills import install_default_skills, list_default_skill_files

STORAGE_HELP = (
    "Path to memory storage (default precedence: explicit argument, "
    "TESSERA_STORAGE_DIR, ./memories)"
)


class InitializationCancelled(ConfigurationError):
    """A user cancelled before the initialization apply boundary."""


def _engine_for_args(args):
    configuration = getattr(args, "storage_selection", None)
    if configuration is not None:
        return TesseraEngine(configuration=configuration)
    return TesseraEngine(storage_dir=args.storage_dir)


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
    if args.project is not None and args.global_name:
        raise ConfigurationError("--project and --global are mutually exclusive")
    mode = "global" if args.global_name else ("project" if args.project is not None else None)
    compatibility_positional = args.storage_dir
    store_path = args.store or compatibility_positional
    interactive = not args.non_interactive and not args.json and sys.stdin.isatty()
    if mode is None and compatibility_positional:
        mode = "project"  # documented compatibility for `tessera init PATH`
    if mode is None:
        if not interactive:
            raise ConfigurationError(
                "init needs --project [PATH] or --global NAME in non-interactive mode"
            )
        print("TESSERA\nPersistent memory for this project\n")
        print(
            "How would you like to configure TESSERA?\n"
            "1. This project (recommended)\n2. Named global store\n3. Cancel"
        )
        choice = _init_input("Selection [1]: ").strip() or "1"
        if choice == "1":
            mode = "project"
            args.project = "."
        elif choice == "2":
            mode = "global"
            args.global_name = _init_input("Named global store: ").strip()
        elif choice == "3":
            print("Initialization cancelled; no files were changed.")
            return 1
        else:
            raise ConfigurationError("init selection must be 1, 2, or 3")
    if args.store and compatibility_positional:
        raise ConfigurationError("pass either positional storage_dir or --store, not both")
    if compatibility_positional and args.sources is None:
        args.sources = "memory-only"
    if args.source and args.sources is None:
        args.sources = "custom"
    if args.source and args.sources not in {None, "custom"}:
        raise ConfigurationError("--source PATH requires --sources custom")
    if args.persist_exclusion and mode != "project":
        raise ConfigurationError("--persist-exclusion is available only for project initialization")
    if mode == "global" and args.sources not in {None, "memory-only"}:
        raise ConfigurationError("named global stores use only their generated-memory store as a source")
    if mode == "global" and args.source:
        raise ConfigurationError("named global stores do not accept project --source paths")
    if mode == "global" and args.index_path:
        raise ConfigurationError("named global indexes use the generated store's derived index path")
    if not interactive and mode == "project" and args.sources is None and not compatibility_positional:
        raise ConfigurationError(
            "non-interactive project init requires --sources recommended, custom, or memory-only"
        )

    project_root = args.project if mode == "project" else None
    if interactive:
        if mode == "project":
            root = Path(project_root or ".").expanduser().resolve(strict=False)
            existing_path = root / ".tessera" / "config.yaml"
            default_store = "memories"
            if existing_path.exists():
                from .config import ProjectConfig
                current = ProjectConfig.load(existing_path)
                try:
                    default_store = str(Path(current.store.path).relative_to(root))
                except ValueError:
                    default_store = current.store.path
            if store_path is None:
                store_path = _init_input(
                    f"Where should newly generated TESSERA memories be stored? [{default_store}]: "
                ).strip() or default_store
            discovery = _interactive_discovery(root)
            if args.sources is None:
                args.sources, custom = _interactive_source_choice(discovery)
                args.source = custom
            if args.sources == "custom" and not args.persist_exclusion:
                exclusions = _init_input(
                    "Optional: paths to save explicitly in .tessera-ignore (comma-separated, blank for none): "
                ).strip()
                if exclusions:
                    args.persist_exclusion = [item.strip() for item in exclusions.split(",") if item.strip()]
        else:
            if not args.global_name:
                args.global_name = _init_input("Named global store: ").strip()
            if not store_path:
                store_path = _init_input("Generated-memory store path: ").strip()
            args.sources = "memory-only"

    source_mode = args.sources or "memory-only"
    request = InitRequest(
        mode=mode,
        project_root=project_root,
        registry_name=args.global_name,
        store_path=store_path,
        source_mode=source_mode,
        source_paths=tuple(args.source or ()),
        persist_exclusions=tuple(args.persist_exclusion or ()),
        index_path=args.index_path,
        registry_path=str(global_registry_path()),
    )
    plan = build_initialization_plan(request)
    if plan.preflight_problems:
        message = "preflight failed: " + "; ".join(plan.preflight_problems)
        if args.json:
            print(json.dumps({
                "schema_version": SCHEMA_VERSION,
                "mode": "dry-run" if args.dry_run else "apply",
                "plan": plan.to_dict(),
                "applied": False,
                "error": {"code": "preflight_failed", "message": message},
            }, sort_keys=True))
        else:
            _render_initialization_plan(plan, dry_run=args.dry_run)
            print(f"Cannot apply: {message}", file=sys.stderr)
        return 2
    existing_material_change = (
        plan.current_configuration is not None and plan.material_config_change
    )
    if existing_material_change and not interactive and not args.dry_run and not args.update_existing:
        raise ConfigurationError(
            "existing configuration would change; inspect with --dry-run and repeat with --update-existing"
        )
    if args.json:
        if args.dry_run:
            print(json.dumps({
                "schema_version": SCHEMA_VERSION, "mode": "dry-run",
                "plan": plan.to_dict(), "applied": False,
            }, sort_keys=True))
            return 0
    else:
        _render_initialization_plan(plan, dry_run=args.dry_run)
        if args.dry_run:
            return 0
    if interactive:
        answer = _init_input("Proceed? [y/N]: ").strip().lower()
        if answer not in {"y", "yes"}:
            print("Initialization cancelled; no files were changed.")
            return 1
    try:
        result = apply_initialization_plan(plan)
    except InitializationApplyError as exc:
        if args.json:
            print(json.dumps({
                "schema_version": SCHEMA_VERSION,
                "applied": False,
                "partial_state": {
                    "config_applied": exc.config_applied,
                    "ignore_applied": exc.ignore_applied,
                    "store_prepared": exc.store_prepared,
                    "index_applied": False,
                    "source_files_modified": 0,
                },
                "error": str(exc),
                "plan": plan.to_dict(),
            }, sort_keys=True))
        else:
            print(f"Initialization incomplete: {exc}", file=sys.stderr)
            if exc.config_applied:
                print("Configuration was saved; correct the problem and rerun `tessera init`.", file=sys.stderr)
            else:
                print("Configuration was not saved; correct the problem and rerun `tessera init`.", file=sys.stderr)
            print("Source files modified: 0", file=sys.stderr)
        return 3
    if args.json:
        result_payload = result.to_dict()
        print(json.dumps({
            "schema_version": SCHEMA_VERSION,
            "plan": plan.to_dict(),
            "applied": True,
            "result": result_payload,
            # Compatibility aliases retained for the established init JSON
            # envelope while Issue #155 adds the complete semantic plan.
            "storage_selection": result_payload["storage_selection"],
            "indexed_nodes": result_payload["indexed_nodes"],
        }, sort_keys=True))
    else:
        print(f"✔ TESSERA configured {result.configuration.storage_dir}")
        print(f"✔ {result.indexed_nodes} nodes indexed from {len(result.indexed_sources)} selected files")
        print("✔ source files modified: 0")
        print("Next: `tessera doctor`, `tessera index`, or `tessera query \"...\"`")
    return 0


def _init_input(prompt: str) -> str:
    try:
        return input(prompt)
    except (EOFError, KeyboardInterrupt) as exc:
        raise InitializationCancelled("initialization cancelled") from exc


def _interactive_discovery(root: Path):
    from .source_discovery import discover_sources, discover_sources_for_configuration

    config_path = root / ".tessera" / "config.yaml"
    if config_path.exists():
        selection = ConfigurationResolver(cwd=root, environ={}).resolve(project=root)
        discovery = discover_sources_for_configuration(selection)
    else:
        discovery = discover_sources(root)
    print("\nKnowledge sources found")
    for cluster in discovery.clusters:
        marker = "x" if cluster.recommended else (" " if cluster.selectable else "!")
        count = cluster.recommended_count + cluster.supported_count
        detail = f"{count} selectable"
        if cluster.forbidden_count:
            detail += f", {cluster.forbidden_count} forbidden"
        print(f"  [{marker}] {cluster.path:<28} {detail}")
    clustered = {item.path.split('/', 1)[0] for item in discovery.files if "/" in item.path}
    for item in discovery.files:
        if "/" in item.path and item.path.split('/', 1)[0] in clustered:
            continue
        marker = (
            "x" if item.selected_by_default
            else " " if item.selectable
            else "!" if item.classification == "FORBIDDEN"
            else "-"
        )
        print(f"  [{marker}] {item.path:<28} {item.classification.lower()}")
    return discovery


def _interactive_source_choice(discovery):
    selectable = [item.path for item in discovery.files if item.kind == "file" and item.selectable]
    if not selectable:
        print("\nNo compatible project sources were found. You can still initialize an empty generated-memory store.")
        answer = _init_input("1. Generated-memory store only\n2. Cancel\nSelection [1]: ").strip() or "1"
        if answer == "2":
            raise InitializationCancelled("initialization cancelled")
        if answer != "1":
            raise ConfigurationError("source selection must be 1 or 2")
        return "memory-only", []
    answer = _init_input(
        "\nWhat should TESSERA use?\n"
        "1. Recommended sources\n2. Choose files/folders\n"
        "3. Generated-memory store only\n4. Cancel\nSelection [1]: "
    ).strip() or "1"
    if answer == "1":
        return "recommended", []
    if answer == "2":
        print("Selectable sources:")
        for index, path in enumerate(selectable, start=1):
            print(f"  {index}. {path}")
        raw = _init_input("Enter comma-separated numbers or project-relative paths: ").strip()
        selected = []
        for item in (part.strip() for part in raw.split(",") if part.strip()):
            if item.isdigit() and 1 <= int(item) <= len(selectable):
                selected.append(selectable[int(item) - 1])
            else:
                selected.append(item)
        return "custom", selected
    if answer == "3":
        return "memory-only", []
    if answer == "4":
        raise InitializationCancelled("initialization cancelled")
    raise ConfigurationError("source selection must be 1, 2, 3, or 4")


def _render_initialization_plan(plan: InitializationPlan, *, dry_run: bool) -> None:
    payload = plan.to_dict()
    sources = payload["sources"]
    print("\nInitialization plan:")
    print(f"  Scope: {plan.mode}")
    print(f"  Project: {plan.project_root or '-'}")
    print(f"  Configuration: {plan.config_path}")
    print(f"  Store id: {plan.store_id}")
    print(f"  Generated memories: {plan.generated_memory_store}")
    print(f"  Source mode: {plan.source_mode}")
    print(f"  Selected project sources: {sources['selected_count']} files")
    print(f"  Derived index: {plan.index_path}")
    print(f"  Ignored: {sources['ignored_count']}")
    print(f"  Forbidden: {sources['forbidden_count']}")
    print("  Source files modified: 0")
    print(f"  Configuration changes: {', '.join(plan.config_changes) or 'none'}")
    print(f"  Ignore changes: {', '.join(plan.ignore_changes) or 'none'}")
    print("  Indexing: will start after confirmation")
    if plan.current_configuration is not None:
        print("  Existing configuration: loaded and compared")
        _render_configuration_summary("Current", plan.current_configuration)
        if plan.proposed_configuration is not None:
            _render_configuration_summary("Proposed", plan.proposed_configuration)
    if plan.warnings:
        print("  Warnings:")
        for warning in plan.warnings:
            print(f"    - {warning}")
    if plan.preflight_problems:
        print("  Preflight problems:")
        for problem in plan.preflight_problems:
            print(f"    - {problem}")
    if dry_run:
        print("\nDRY RUN — no changes made")


def _render_configuration_summary(label: str, mapping: Dict) -> None:
    store = mapping.get("store", mapping)
    sources = mapping.get("sources", {}).get("roots", [])
    index = mapping.get("index", {})
    print(f"  {label}:")
    print(f"    Generated memories: {store.get('path', '-')}")
    if sources:
        include_count = sum(len(root.get("include", [])) for root in sources)
        print(f"    Source allow-list entries: {include_count}")
    print(f"    Derived index: {index.get('path', '-')}")


def cmd_write(args):
    engine = _engine_for_args(args)
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
    engine = _engine_for_args(args)
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
    engine = _engine_for_args(args)
    engine.build_index()
    if engine.graph.number_of_nodes() == 0:
        print(
            f"Nenhuma nota de memória indexada em '{args.storage_dir}'. "
            "Verifique o caminho (ou defina TESSERA_STORAGE_DIR)."
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
    engine = _engine_for_args(args)
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
    engine = _engine_for_args(args)
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
    engine = _engine_for_args(args)
    engine.build_index()

    from .llm_bridge import resolve_llm_fn

    try:
        llm_fn, backend_name = resolve_llm_fn(
            backend=args.llm_backend, endpoint=args.compat_endpoint,
            api_key=args.compat_api_key, contact_id=args.compat_contact_id,
            subscription_id=args.compat_subscription_id,
            tenant_id=args.compat_tenant_id, router_path=args.compat_router_path,
            return_backend_name=True,
        )
    except RuntimeError as exc:
        print(f"[tessera] optional backend configuration failed: {exc}", file=sys.stderr)
        return 2
    if llm_fn is None:
        print(
            "[tessera] No optional backend selected. Pass a custom llm_fn in "
            "Python or explicitly select a configured compatibility adapter.",
            file=sys.stderr,
        )
        return 2
    print(f"[tessera] backend={backend_name} (explicit compatibility selection).", file=sys.stderr)

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
    engine = _engine_for_args(args)
    engine.build_index()

    from .llm_bridge import resolve_llm_fn

    try:
        llm_fn, backend_name = resolve_llm_fn(
            backend=args.llm_backend, endpoint=args.compat_endpoint,
            api_key=args.compat_api_key, contact_id=args.compat_contact_id,
            subscription_id=args.compat_subscription_id,
            tenant_id=args.compat_tenant_id, router_path=args.compat_router_path,
            return_backend_name=True,
        )
    except RuntimeError as exc:
        print(f"[tessera] optional backend configuration failed: {exc}", file=sys.stderr)
        return 2
    if llm_fn is None:
        print("[tessera] No optional backend selected.", file=sys.stderr)
        return 2
        
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
    engine = _engine_for_args(args)
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

    report = run_doctor(
        args.storage_dir,
        configuration=getattr(args, "storage_selection", None),
    )

    console = get_console(force_plain=getattr(args, "plain", False))
    if console is not None:
        render_doctor_report(console, report)
    else:
        print_doctor_report_plain(report)

    return 0 if report.all_ok else 1


def _selection_from_args(args):
    if getattr(args, "store", None) and getattr(args, "storage_dir", None):
        raise ConfigurationError("pass either positional storage_dir or --store, not both")
    resolver = ConfigurationResolver()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        selection = resolver.resolve(
            explicit=getattr(args, "store", None) or getattr(args, "storage_dir", None),
            project=getattr(args, "project", None),
            global_name=getattr(args, "global_name", None),
        )
    for warning in caught:
        print(f"[tessera] warning: {warning.message}", file=sys.stderr)
    return selection


def cmd_config_show(args):
    selection = _selection_from_args(args)
    payload = {"schema_version": SCHEMA_VERSION, "storage_selection": selection.to_dict()}
    if args.json:
        print(json.dumps(payload, sort_keys=True))
    else:
        for key, value in selection.to_dict().items():
            print(f"{key}: {value if value is not None else '-'}")
    return 0


def cmd_config_list(args):
    path = global_registry_path()
    registry = GlobalRegistry.load(path)
    stores = [
        {"name": name, "store_id": record.id, "storage_dir": record.path}
        for name, record in sorted(registry.stores.items())
    ]
    payload = {"schema_version": SCHEMA_VERSION, "registry_path": str(path), "stores": stores}
    if args.json:
        print(json.dumps(payload, sort_keys=True))
    elif stores:
        for store in stores:
            print(f"{store['name']}\t{store['store_id']}\t{store['storage_dir']}")
    else:
        print("No global stores are registered.")
    return 0


def cmd_config_doctor(args):
    checks = []
    source_discovery = None
    project_path = discover_project_config(args.project or os.getcwd())
    if project_path:
        try:
            from .config import ProjectConfig
            project_config = ProjectConfig.load(project_path)
            checks.append({"name": "project_config", "ok": True, "detail": str(project_path)})
            if Path(project_config.store.path).is_symlink():
                checks.append({"name": "project_store_symlink", "ok": False, "detail": project_config.store.path})
        except ConfigurationError as exc:
            checks.append({"name": "project_config", "ok": False, "detail": str(exc)})
    else:
        checks.append({"name": "project_config", "ok": True, "detail": "not found", "required": False})
    registry_path = global_registry_path()
    try:
        registry = GlobalRegistry.load(registry_path)
        checks.append({"name": "global_registry", "ok": True, "detail": str(registry_path)})
        if args.global_name:
            checks.append({
                "name": f"requested_global:{args.global_name}",
                "ok": args.global_name in registry.stores,
                "detail": "registered" if args.global_name in registry.stores else "missing explicitly requested global store",
            })
        for name, record in sorted(registry.stores.items()):
            exists = Path(record.path).is_dir()
            checks.append({
                "name": f"registry_store:{name}",
                "ok": exists,
                "detail": record.path if exists else f"stale or missing path: {record.path}",
            })
    except ConfigurationError as exc:
        checks.append({"name": "global_registry", "ok": False, "detail": str(exc)})
    selection = None
    try:
        selection = _selection_from_args(args)
        selected_path = Path(selection.storage_dir)
        exists = selected_path.is_dir()
        writable = exists and os.access(selected_path, os.W_OK)
        symlink = selected_path.is_symlink()
        checks.extend([
            {"name": "selected_store_exists", "ok": exists, "detail": str(selected_path)},
            {"name": "selected_store_writable", "ok": writable, "detail": str(selected_path)},
            {"name": "selected_store_symlink", "ok": not symlink, "detail": "physical canonical path" if not symlink else str(selected_path), "required": False},
        ])
        index_path = Path(selection.index_dir)
        checks.append({
            "name": "derived_index_separate",
            "ok": index_path != selected_path,
            "detail": str(index_path),
        })
        for position, source_root in enumerate(selection.source_roots):
            source_path = Path(source_root.path)
            checks.append({
                "name": f"source_root:{position}",
                "ok": source_path.is_dir(),
                "detail": str(source_path),
            })
        if selection.project_root:
            from .source_discovery import discover_sources_for_configuration

            source_discovery = discover_sources_for_configuration(selection)
            invalid_codes = {
                "invalid_ignore_pattern",
                "unreadable_ignore_file",
                "unsafe_ignore_file",
                "configured_source_forbidden",
            }
            blocking_warnings = [
                warning for warning in source_discovery.warnings
                if warning.code in invalid_codes
            ]
            checks.append({
                "name": "source_discovery_policy",
                "ok": not blocking_warnings,
                "detail": (
                    "structured discovery plan available"
                    if not blocking_warnings
                    else "; ".join(
                        f"{warning.code}:{warning.path}:{warning.detail}"
                        for warning in blocking_warnings
                    )
                ),
            })
    except ConfigurationError as exc:
        checks.append({"name": "storage_selection", "ok": False, "detail": str(exc)})
    healthy = all(check["ok"] for check in checks if check.get("required", True))
    payload = {
        "schema_version": SCHEMA_VERSION,
        "healthy": healthy,
        "project_config_path": str(project_path) if project_path else None,
        "registry_path": str(registry_path),
        "storage_selection": selection.to_dict() if selection else None,
        "source_discovery": source_discovery.to_dict() if source_discovery else None,
        "checks": checks,
    }
    if args.json:
        print(json.dumps(payload, sort_keys=True))
    else:
        for check in checks:
            print(f"{'OK' if check['ok'] else 'PROBLEM'} {check['name']}: {check['detail']}")
    return 0 if healthy else 1


def cmd_config_unregister(args):
    path = global_registry_path()
    removed = unregister_global_store(args.name, path)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "removed_registry_name": args.name,
        "store_id": removed.id,
        "storage_dir": removed.path,
        "store_deleted": False,
        "registry_path": str(path),
    }
    if args.json:
        print(json.dumps(payload, sort_keys=True))
    else:
        print(f"Unregistered {args.name!r}; only registry metadata was removed.")
        print(f"Store retained: {removed.path}")
    return 0


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


def _add_optional_backend_arguments(parser):
    parser.add_argument(
        "--llm-backend",
        metavar="NAME",
        default=None,
        help="Explicitly select a deprecated compatibility adapter (no default backend).",
    )
    parser.add_argument("--compat-endpoint", default=None, help=argparse.SUPPRESS)
    parser.add_argument("--compat-api-key", default=None, help=argparse.SUPPRESS)
    parser.add_argument("--compat-contact-id", default=None, help=argparse.SUPPRESS)
    parser.add_argument("--compat-subscription-id", default=None, help=argparse.SUPPRESS)
    parser.add_argument("--compat-tenant-id", default=None, help=argparse.SUPPRESS)
    parser.add_argument("--compat-router-path", default=None, help=argparse.SUPPRESS)


def _add_store_selection_arguments(parser):
    parser.add_argument("--store", default=None, help="Explicit canonical store path")
    parser.add_argument("--project", default=None, metavar="PATH", help="Start project-config discovery at PATH")
    parser.add_argument("--global", dest="global_name", default=None, metavar="NAME", help="Select this exact global registry entry")


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

    p_init = sub.add_parser("init", help="Configure and initialize an explicit TESSERA store", parents=[plain_parent])
    p_init.add_argument("storage_dir", nargs="?", default=None, help=STORAGE_HELP)
    p_init.add_argument("--project", nargs="?", const=".", default=None, metavar="PATH", help="Write project config (default PATH: current directory)")
    p_init.add_argument("--global", dest="global_name", default=None, metavar="NAME", help="Write/update this named global registry entry")
    p_init.add_argument("--store", default=None, metavar="PATH", help="Store path (positional path remains a compatibility alias)")
    p_init.add_argument(
        "--sources", choices=SOURCE_MODES, default=None,
        help="Source selection policy: recommended, custom, or memory-only",
    )
    p_init.add_argument(
        "--source", action="append", default=None, metavar="PATH",
        help="Safe project-relative file/directory (repeatable; requires --sources custom)",
    )
    p_init.add_argument(
        "--persist-exclusion", action="append", default=None, metavar="PATH",
        help="Explicitly add a selectable exclusion to .tessera-ignore (repeatable)",
    )
    p_init.add_argument(
        "--index-path", default=None, metavar="PATH",
        help="Project-relative derived index path (default: .tessera/index)",
    )
    p_init.add_argument(
        "--update-existing", action="store_true",
        help="Allow a declared non-interactive material update to existing configuration",
    )
    p_init.add_argument("--non-interactive", action="store_true", help="Never prompt; fail when choices are missing")
    p_init.add_argument("--dry-run", action="store_true", help="Show the complete mutation plan without writing")
    p_init.add_argument("--json", action="store_true", help="Emit stable machine-readable output")
    p_init.set_defaults(func=cmd_init)

    p_write = sub.add_parser("write", help="Write a new memory note", parents=[plain_parent])
    p_write.add_argument("storage_dir", nargs="?", default=None, help=STORAGE_HELP)
    _add_store_selection_arguments(p_write)
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
                               'the generic connection schema.')
    p_write.set_defaults(func=cmd_write)

    p_index = sub.add_parser("index", help="Rebuild the in-memory knowledge graph index", parents=[plain_parent])
    p_index.add_argument("storage_dir", nargs="?", default=None, help=STORAGE_HELP)
    _add_store_selection_arguments(p_index)
    p_index.set_defaults(func=cmd_index)

    p_query = sub.add_parser("query", help="Retrieve relevant memories for a query", parents=[plain_parent])
    p_query.add_argument("storage_dir", nargs="?", default=None, help=STORAGE_HELP)
    _add_store_selection_arguments(p_query)
    p_query.add_argument("query", nargs="?", help="Query text (storage path may be omitted)")
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
    p_list.add_argument("storage_dir", nargs="?", default=None, help=STORAGE_HELP)
    _add_store_selection_arguments(p_list)
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
    p_skills_install.add_argument("storage_dir", nargs="?", default=None, help=STORAGE_HELP)
    _add_store_selection_arguments(p_skills_install)
    p_skills_install.set_defaults(func=cmd_skills_install)

    p_skills_list = skills_sub.add_parser("list", help="List the bundled default skill IDs", parents=[plain_parent])
    p_skills_list.set_defaults(func=cmd_skills_list)

    p_start = sub.add_parser(
        "start", help="Run the full Need->Planner->Retrieval->Inference orchestrator pipeline for a task",
        parents=[plain_parent],
    )
    p_start.add_argument("storage_dir", nargs="?", default=None, help=STORAGE_HELP)
    _add_store_selection_arguments(p_start)
    p_start.add_argument("task", nargs="?", help="Task text (storage path may be omitted)")
    p_start.add_argument("--top-n", type=int, default=7)
    _add_optional_backend_arguments(p_start)
    p_start.set_defaults(func=cmd_start)

    p_decompose = sub.add_parser(
        "decompose",
        help="QUMem-style: mechanically extract N atomic facts/preferences/insights from a raw episode",
        parents=[plain_parent],
    )
    p_decompose.add_argument("storage_dir", nargs="?", default=None, help=STORAGE_HELP)
    _add_store_selection_arguments(p_decompose)
    p_decompose.add_argument("--mem-id-prefix", required=True,
                              help='Domain-prefixed prefix, e.g. "research/some-topic" or "project/some-run" - '
                                   'each extracted memory is written as "{prefix}/{type}-{n}".')
    p_decompose.add_argument("--episode-id", default=None,
                              help="Episode id to stamp on every extracted note (default: same as --mem-id-prefix).")
    p_decompose.add_argument("--beginning", required=True, help="Episode's beginning (goal/context/trigger).")
    p_decompose.add_argument("--middle", required=True, help="Episode's middle (what actually happened).")
    p_decompose.add_argument("--end", required=True, help="Episode's end (outcome/resolution/lesson).")
    p_decompose.add_argument("--tags", default="", help="Comma-separated tags applied to every extracted note.")
    _add_optional_backend_arguments(p_decompose)
    p_decompose.set_defaults(func=cmd_decompose)

    p_banner = sub.add_parser("banner", help="Print the Tessera ASCII logo/banner", parents=[plain_parent])
    p_banner.set_defaults(func=cmd_banner)

    p_stats = sub.add_parser(
        "stats", help="Show index composition: real notes vs. internal tag/entity graph nodes",
        parents=[plain_parent],
    )
    p_stats.add_argument("storage_dir", nargs="?", default=None, help=STORAGE_HELP)
    _add_store_selection_arguments(p_stats)
    p_stats.set_defaults(func=cmd_stats)

    p_doctor = sub.add_parser(
        "doctor", help="Run post-install smoke tests (writable dir, index builds, write/read round-trip, deps)",
        parents=[plain_parent],
    )
    p_doctor.add_argument("storage_dir", nargs="?", default=None, help=STORAGE_HELP)
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

    p_config = sub.add_parser("config", help="Inspect TESSERA project/global store configuration")
    config_sub = p_config.add_subparsers(dest="config_command", required=True)

    p_config_show = config_sub.add_parser("show", help="Show the one resolved storage selection")
    _add_store_selection_arguments(p_config_show)
    p_config_show.add_argument("--json", action="store_true")
    p_config_show.set_defaults(func=cmd_config_show)

    p_config_list = config_sub.add_parser("list", help="List explicit global registry entries (no filesystem scan)")
    p_config_list.add_argument("--json", action="store_true")
    p_config_list.set_defaults(func=cmd_config_list)

    p_config_doctor = config_sub.add_parser("doctor", help="Read-only configuration/discovery diagnostics")
    _add_store_selection_arguments(p_config_doctor)
    p_config_doctor.add_argument("--json", action="store_true")
    p_config_doctor.set_defaults(func=cmd_config_doctor)

    p_config_unregister = config_sub.add_parser("unregister", help="Remove only one named registry entry")
    p_config_unregister.add_argument("name")
    p_config_unregister.add_argument("--json", action="store_true")
    p_config_unregister.set_defaults(func=cmd_config_unregister)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command in {"query", "start"}:
        text_field = "query" if args.command == "query" else "task"
        if getattr(args, text_field) is None:
            setattr(args, text_field, args.storage_dir)
            args.storage_dir = None
        if getattr(args, text_field) is None:
            parser.error(f"{args.command} requires {text_field} text")
    try:
        if hasattr(args, "storage_dir") and args.command not in {"init", "quickstart"}:
            if args.command == "doctor":
                if args.storage_dir is None:
                    configured_project = discover_project_config(os.getcwd())
                    configured_environment = any(
                        os.environ.get(name)
                        for name in (CANONICAL_STORAGE_ENV, LEGACY_STORAGE_ENV)
                    )
                    if configured_project or configured_environment:
                        selection = _selection_from_args(args)
                        args.storage_selection = selection
                        args.storage_dir = selection.storage_dir
                    else:
                        args.storage_dir = resolve_storage_dir(None)
                else:
                    with warnings.catch_warnings(record=True) as caught:
                        warnings.simplefilter("always")
                        args.storage_dir = resolve_storage_dir(args.storage_dir)
                    for warning in caught:
                        print(f"[tessera] warning: {warning.message}", file=sys.stderr)
            else:
                selection = _selection_from_args(args)
                args.storage_selection = selection
                args.storage_dir = selection.storage_dir
        return args.func(args) or 0
    except InitializationCancelled:
        if getattr(args, "json", False) and args.command == "init":
            print(json.dumps({"schema_version": SCHEMA_VERSION, "applied": False, "cancelled": True}, sort_keys=True))
        else:
            print("Initialization cancelled; no files were changed.")
        return 1
    except ConfigurationError as exc:
        if getattr(args, "json", False) and args.command == "init":
            print(json.dumps({
                "schema_version": SCHEMA_VERSION,
                "applied": False,
                "error": {"code": "configuration_error", "message": str(exc)},
            }, sort_keys=True))
        else:
            print(f"tessera: configuration error: {exc}", file=sys.stderr)
        return 2
    except BrokenPipeError:
        # Harmless: happens when output is piped into `head`/`grep -m` and the
        # reader closes early. Exit quietly instead of printing a traceback.
        sys.stderr.close()
        sys.exit(0)


if __name__ == "__main__":
    sys.exit(main())
