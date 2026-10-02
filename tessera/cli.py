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
from contextlib import redirect_stderr
import os
import sys
import warnings
from pathlib import Path
from typing import Dict

from .config import (
    CANONICAL_STORAGE_ENV,
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
from . import __version__
from .presentation import (
    ArgumentParser, CliFailure, OutputPolicy, UiEvent, emit, event, output_policy,
    EXIT_FILESYSTEM, EXIT_INTERNAL, EXIT_CANCELLED, EXIT_PROVIDER, SafeDiagnostics, say, stage,
)

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
    interactive = OutputPolicy.detect(args).interactive
    console = None
    if interactive:
        from .display import get_console, print_banner
        console = get_console(getattr(args, "plain", False))
        if not args.quiet:
            print_banner(console)
    if mode is None and compatibility_positional:
        mode = "project"  # documented compatibility for `tessera init PATH`
    if mode is None:
        if not interactive:
            raise ConfigurationError(
                "init needs --project [PATH] or --global NAME in non-interactive mode"
            )
        say("TESSERA\nPersistent memory for this project\n")
        say(
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
            say("Initialization cancelled; no files were changed.")
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
                from .init_presentation import show_existing_configuration
                show_existing_configuration(current, existing_path)
                if store_path is None and args.sources is None and not args.source:
                    choice = _init_input(
                        "1. Keep this configuration and update the index\n"
                        "2. Change configuration / re-run source selection\n"
                        "3. Cancel\nSelection [1]: "
                    ).strip() or "1"
                    if choice == "3":
                        raise InitializationCancelled("initialization cancelled")
                    if choice == "1":
                        selection = ConfigurationResolver(cwd=root, environ={}).resolve(project=root)
                        if args.dry_run:
                            return emit(args, "init.keep", {
                                "applied": False, "mode": "dry-run", "config_changed": False,
                                "storage_selection": selection.to_dict(),
                            })
                        if _init_input("Update the index with this configuration? [y/N]: ").strip().lower() not in {"y", "yes"}:
                            raise InitializationCancelled("initialization cancelled")
                        args.storage_selection = selection
                        args.storage_dir = selection.storage_dir
                        return cmd_index(args)
                    if choice != "2":
                        raise ConfigurationError("existing configuration selection must be 1, 2, or 3")
                try:
                    default_store = str(Path(current.store.path).relative_to(root))
                except ValueError:
                    default_store = current.store.path
            if store_path is None:
                store_path = _init_input(
                    f"Where should newly generated TESSERA memories be stored? [{default_store}]: "
                ).strip() or default_store
            # The interactive path is deliberately richer than the stable
            # non-interactive/JSON paths: show a live discovery status while
            # walking the project.
            discovery = _interactive_discovery(root, console=console)
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
            emit(args, "init", {
                "schema_version": SCHEMA_VERSION,
                "mode": "dry-run" if args.dry_run else "apply",
                "plan": plan.to_dict(),
                "applied": False,
                "error": {"code": "preflight_failed", "message": message},
            })
        else:
            _render_initialization_plan(plan, dry_run=args.dry_run)
            say(f"Cannot apply: {message}", file=sys.stderr)
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
            emit(args, "init", {
                "schema_version": SCHEMA_VERSION, "mode": "dry-run",
                "plan": plan.to_dict(), "applied": False,
            })
            return 0
    else:
        _render_initialization_plan(plan, dry_run=args.dry_run)
        if args.dry_run:
            return 0
    if interactive:
        answer = _init_input("Proceed? [y/N]: ").strip().lower()
        if answer not in {"y", "yes"}:
            say("Initialization cancelled; no files were changed.")
            return 1
    try:
        # Presentation owns terminal activity; application receives no Console.
        with stage("progress.index"):
            result = apply_initialization_plan(plan)
    except InitializationApplyError as exc:
        if args.json:
            emit(args, "init", {
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
            })
        else:
            say(f"Initialization incomplete: {exc}", file=sys.stderr)
            if exc.config_applied:
                say("Configuration was saved; correct the problem and rerun `tessera init`.", file=sys.stderr)
            else:
                say("Configuration was not saved; correct the problem and rerun `tessera init`.", file=sys.stderr)
            say("Source files modified: 0", file=sys.stderr)
        return 3
    result_payload = result.to_dict()
    return emit(args, "init", {
        "schema_version": SCHEMA_VERSION, "plan": plan.to_dict(),
        "applied": True, "result": result_payload,
        # Established init JSON aliases remain stable.
        "storage_selection": result_payload["storage_selection"],
        "indexed_nodes": result_payload["indexed_nodes"],
    })


def _init_input(prompt: str) -> str:
    try:
        from .presentation import prompt_input
        return prompt_input(prompt)
    except (EOFError, KeyboardInterrupt) as exc:
        raise InitializationCancelled("initialization cancelled") from exc


def _interactive_discovery(root: Path, *, console=None):
    from .source_discovery import discover_sources, discover_sources_for_configuration

    config_path = root / ".tessera" / "config.yaml"
    event(UiEvent("progress.discovery"))
    if config_path.exists():
        selection = ConfigurationResolver(cwd=root, environ={}).resolve(project=root)
        discovery = discover_sources_for_configuration(selection)
    else:
        discovery = discover_sources(root)
    from .init_presentation import show_discovery
    show_discovery(discovery)
    return discovery


def _interactive_source_choice(discovery):
    selectable = [item.path for item in discovery.files if item.kind == "file" and item.selectable]
    if not selectable:
        say("\nNo compatible project sources were found. You can still initialize an empty generated-memory store.")
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
        say("Selectable sources:")
        for index, path in enumerate(selectable, start=1):
            say(f"  {index}. {path}")
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
    from .init_presentation import render_initialization_plan
    render_initialization_plan(plan, dry_run=dry_run)


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
    return emit(args, "write", result.to_dict(), 0 if result.persisted else 2)


def cmd_index(args):
    engine = _engine_for_args(args)
    with stage("progress.index"):
        engine.build_index(use_cache=True)
    return emit(args, "index", {
        "schema_version": 1, "storage_dir": args.storage_dir,
        "nodes": engine.graph.number_of_nodes(), "edges": engine.graph.number_of_edges(),
        "stats": getattr(engine, "last_index_stats", {}),
        "artifacts": {"binary": str(engine.index_cache_pkl), "readable": str(engine.index_cache_json)},
        "warnings": engine.processing_warnings,
    })


def cmd_query(args):
    engine = _engine_for_args(args)
    engine.build_index()
    # Empty corpora are successful empty retrieval, exactly like the Engine API.
    results = engine.retrieve_context(
        query_text=args.query, top_n=args.top_n,
        resolve_conflicts=not args.no_resolve_conflicts,
    ) if engine.graph.number_of_nodes() else []
    return emit(args, "query", results)


def cmd_list(args):
    engine = _engine_for_args(args)
    engine.build_index()
    rows = []
    for node_id, data in sorted(engine.graph.nodes(data=True)):
        node_type = data.get("node_type")
        if node_type not in {"factual", "preference", "procedural_anchor"}:
            continue
        if args.type and node_type != args.type:
            continue
        rows.append({"id": node_id, "type": node_type,
                     "filename": data.get("filename", ""), "filepath": data.get("filepath", "")})
    return emit(args, "list", rows)


def cmd_skills_install(args):
    engine = _engine_for_args(args)
    paths = install_default_skills(engine)
    return emit(args, "skills.install", {
        "schema_version": 1, "paths": [str(path) for path in paths],
        "storage_dir": os.path.abspath(args.storage_dir),
    })


def cmd_skills_list(args):
    return emit(args, "skills.list", [path.stem for path in list_default_skill_files()])


def cmd_start(args):
    engine = _engine_for_args(args)
    engine.build_index()
    llm_fn = _optional_backend(args)
    try:
        with stage("progress.reason"):
            result = TesseraOrchestrator(engine, llm_fn=llm_fn).run(task_instruction=args.task, top_n=args.top_n)
    except (RuntimeError, ConnectionError, TimeoutError) as exc:
        raise CliFailure("provider_failure", f"The selected optional service failed ({type(exc).__name__}).",
                         exit_code=EXIT_PROVIDER, suggested_command="Check the selected provider's configuration and availability.") from exc
    return emit(args, "start", result.to_dict())


def _optional_backend(args):
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
        raise CliFailure("provider_configuration", str(exc), exit_code=EXIT_PROVIDER,
                         suggested_command="tessera start --help") from exc
    if llm_fn is None:
        raise CliFailure("provider_missing", "No optional backend selected.", exit_code=EXIT_PROVIDER,
                         suggested_command="tessera start --help")
    event(UiEvent("provider.selected", fields={"backend": backend_name}))
    return llm_fn


def cmd_decompose(args):
    from .models import Episode
    engine = _engine_for_args(args)
    engine.build_index()
    llm_fn = _optional_backend(args)
    event(UiEvent("progress.decompose"))
    result = engine.decompose_and_write_episode_result(
        mem_id_prefix=args.mem_id_prefix, episode_id=args.episode_id or args.mem_id_prefix,
        episode=Episode(beginning=args.beginning, middle=args.middle, end=args.end),
        llm_fn=llm_fn, tags=args.tags.split(",") if args.tags else [],
    )
    engine.build_index()
    if result.decomposition.fallback_reason:
        event(UiEvent("decomposition.fallback", level="warning", fields={
            "decomposition_mode": result.decomposition.mode,
            "fallback_reason": result.decomposition.fallback_reason,
        }))
    from dataclasses import asdict
    return emit(args, "decompose", asdict(result))


def cmd_stats(args):
    engine = _engine_for_args(args)
    engine.build_index()
    type_counts: Dict[str, int] = {}
    for _node_id, data in engine.graph.nodes(data=True):
        node_type = data.get("node_type", "unknown")
        type_counts[node_type] = type_counts.get(node_type, 0) + 1
    return emit(args, "stats", {
        "schema_version": 1, "storage_dir": args.storage_dir,
        "type_counts": type_counts, "edges": engine.graph.number_of_edges(),
    })


def cmd_doctor(args):
    from .diagnostics import run_doctor
    report = run_doctor(args.storage_dir, configuration=getattr(args, "storage_selection", None))
    return emit(args, "doctor", report.to_dict(), 0 if report.all_ok else 1)


def cmd_corpus_doctor(args):
    from .corpus_diagnostics import run_corpus_doctor
    configuration = getattr(args, "storage_selection", None) or _selection_from_args(args)
    report = run_corpus_doctor(configuration)
    code = 1 if report.errors else 2 if args.strict and report.warnings else 0
    return emit(args, "corpus.doctor", report.to_dict(), code)


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
        event(UiEvent("configuration.warning", level="warning", fields={"message": str(warning.message)}))
    return selection


def cmd_config_show(args):
    selection = _selection_from_args(args)
    return emit(args, "config.show", {"schema_version": SCHEMA_VERSION, "storage_selection": selection.to_dict()})


def cmd_config_list(args):
    path = global_registry_path()
    registry = GlobalRegistry.load(path)
    stores = [{"name": name, "store_id": record.id, "storage_dir": record.path}
              for name, record in sorted(registry.stores.items())]
    return emit(args, "config.list", {"schema_version": SCHEMA_VERSION, "registry_path": str(path), "stores": stores})


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
    return emit(args, "config.doctor", payload, 0 if healthy else 1)


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
    return emit(args, "config.unregister", payload)


def cmd_quickstart(args):
    from .diagnostics import apply_quickstart_plan, build_quickstart_plan
    plan = build_quickstart_plan(project_root=args.project_root, storage_dir=args.storage_dir)
    if args.apply:
        plan = apply_quickstart_plan(plan)
    return emit(args, "quickstart", plan.to_dict())


def cmd_banner(args):
    from .display import TESSERA_TAGLINE, get_console, print_banner
    if not getattr(args, "json", False):
        console = get_console(force_plain=getattr(args, "plain", False))
        if console is not None:
            print_banner(console)
            return 0
    return emit(args, "banner", {"name": "TESSERA", "tagline": TESSERA_TAGLINE})


def cmd_update(args):
    from .update import check_for_update, install_latest
    if getattr(args, "json", False) and not args.check:
        raise CliFailure("invalid_usage", "JSON update requires --check; installing requires explicit interactive confirmation.", exit_code=2,
                         suggested_command="tessera update --check --json")
    found = check_for_update(force=True)
    emit(args, "update", {"installed": __version__, "latest": found[1] if found else None})
    if not found or args.check:
        return 0
    if not OutputPolicy.detect(args).interactive:
        raise CliFailure("interaction_required", "Run interactively or pass --check to inspect updates.", exit_code=2)
    from .presentation import prompt_input
    answer = prompt_input("Install this update? [y/N]: ").strip().lower()
    if answer not in {"y", "yes"}:
        say("Update cancelled.")
        return 0
    return install_latest()


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


def _add_presentation_arguments(parser):
    options = {
        "--plain": {"action": "store_true", "help": "Plain line-oriented output"},
        "--no-color": {"action": "store_true", "help": "Keep layout without color"},
        "--json": {"action": "store_true", "help": "One machine-readable JSON result"},
        "--quiet": {"action": "store_true", "help": "Essential results only"},
        "--verbose": {"action": "store_true", "help": "Resolved paths, IDs and stage diagnostics"},
        "--debug": {"action": "store_true", "help": "Developer traceback on stderr and detailed results"},
        "--lang": {"choices": ["en"], "help": "Message language (v1 supports English)"},
    }
    for option, kwargs in options.items():
        if option not in parser._option_string_actions:
            parser.add_argument(option, default=argparse.SUPPRESS, **kwargs)
        else:
            parser._option_string_actions[option].default = argparse.SUPPRESS
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            for child in action.choices.values():
                _add_presentation_arguments(child)


def build_parser():
    parser = ArgumentParser(prog="tessera", description="Tessera — Temporal Evolving State Synthesis with Explicit Relations and Atomic Memories CLI")
    parser.add_argument("--version", "--v", action="store_true", help="Show the installed TESSERA version")
    sub = parser.add_subparsers(dest="command", required=False)

    # Compatibility parent; all parsers receive the complete output policy
    # below, with suppressed defaults preserving flags supplied at any level.
    plain_parent = ArgumentParser(add_help=False)
    plain_parent.add_argument("--plain", action="store_true",
                               help="Force plain-text output (no colors/tables), even on a TTY.")

    p_status = sub.add_parser("status", help="Read-only project dashboard", parents=[plain_parent])
    p_status.add_argument("--project", default=None, metavar="PATH")
    p_status.set_defaults(func=cmd_dashboard)

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
    p_init.add_argument("--yes", action="store_true", help="Accept the fully specified init plan; requires --non-interactive")
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
    p_query.add_argument("--full", action="store_true", help="Show complete source bodies")
    p_query.add_argument("--explain", action="store_true", help="Show ranking components (not confidence)")
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

    p_update = sub.add_parser("update", help="Check for and install a newer TESSERA release")
    p_update.add_argument("--check", action="store_true", help="Only check; do not prompt or install")
    p_update.set_defaults(func=cmd_update)

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

    p_corpus = sub.add_parser("corpus", help="Inspect configured corpus and derived-index health")
    corpus_sub = p_corpus.add_subparsers(dest="corpus_command", required=True)
    p_corpus_doctor = corpus_sub.add_parser(
        "doctor",
        help="Run deterministic read-only source, identity, relation, and evidence diagnostics",
        parents=[plain_parent],
    )
    p_corpus_doctor.add_argument("storage_dir", nargs="?", default=None, help=STORAGE_HELP)
    _add_store_selection_arguments(p_corpus_doctor)
    p_corpus_doctor.add_argument("--json", action="store_true", help="Emit the versioned JSON report")
    p_corpus_doctor.add_argument(
        "--verbose",
        action="store_true",
        help="List every selected source and inferred field",
    )
    p_corpus_doctor.add_argument(
        "--strict",
        action="store_true",
        help="Return exit code 2 for warning-only reports (errors always return 1)",
    )
    p_corpus_doctor.set_defaults(func=cmd_corpus_doctor)

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

    _add_presentation_arguments(parser)
    return parser


def cmd_dashboard(args):
    """Inspect configuration and corpus without creating directories or rebuilding."""
    root = getattr(args, "project", None) or os.getcwd()
    config_path = discover_project_config(root)
    if not config_path and not os.environ.get(CANONICAL_STORAGE_ENV):
        return emit(args, "dashboard", {"schema_version": 1, "configured": False})
    from .corpus_diagnostics import run_corpus_doctor
    selection = ConfigurationResolver().resolve(project=root)
    report = run_corpus_doctor(selection)
    codes = {finding.code for finding in report.findings}
    freshness = {"stale_source_version", "source_not_indexed", "source_removed", "stale_evidence"}
    index_status = "missing" if "index_missing" in codes else (
        "needs attention" if report.errors or codes & freshness else "inspected; no freshness issue detected"
    )
    return emit(args, "dashboard", {
        "schema_version": 1, "configured": True,
        "project": Path(selection.project_root).name if selection.project_root else None,
        "config_path": selection.config_path, "configuration_source": selection.source,
        "storage_dir": selection.storage_dir,
        "index_dir": selection.index_dir, "index_status": index_status,
        "sources": report.counts["sources_selected"], "counts": report.counts,
        "source_files_modified": 0,
    })


def _run_command(args, parser):
    if args.lang != "en":
        parser.error("only the English catalog is supported; use --lang en")
    if args.version:
        return emit(args, "version", {"version": __version__})
    if args.command is None:
        return cmd_dashboard(args)
    if args.command in {"query", "start"}:
        text_field = "query" if args.command == "query" else "task"
        if getattr(args, text_field) is None:
            setattr(args, text_field, args.storage_dir)
            args.storage_dir = None
        if getattr(args, text_field) is None:
            parser.error(f"{args.command} requires {text_field} text")
    if getattr(args, "top_n", 1) < 1:
        parser.error("--top-n must be greater than zero")
    if getattr(args, "yes", False) and not args.non_interactive:
        parser.error("--yes requires a fully specified --non-interactive init plan")
    if hasattr(args, "storage_dir") and args.command not in {"init", "quickstart"}:
        if args.command == "doctor":
            if args.storage_dir is None:
                configured_project = discover_project_config(os.getcwd())
                configured_environment = bool(os.environ.get(CANONICAL_STORAGE_ENV))
                if configured_project or configured_environment:
                    selection = _selection_from_args(args)
                    args.storage_selection = selection
                    args.storage_dir = selection.storage_dir
                else:
                    args.storage_dir = resolve_storage_dir(None)
            else:
                args.storage_dir = resolve_storage_dir(args.storage_dir)
        else:
            selection = _selection_from_args(args)
            args.storage_selection = selection
            args.storage_dir = selection.storage_dir
    if args.verbose and getattr(args, "storage_selection", None):
        event(UiEvent("configuration.resolved", fields=args.storage_selection.to_dict()))
    return args.func(args) or 0


def main(argv=None):
    arguments = list(sys.argv[1:] if argv is None else argv)
    # Detect JSON before parsing so malformed usage/help also honors the wire contract.
    options = arguments[:arguments.index("--")] if "--" in arguments else arguments
    args = argparse.Namespace(json="--json" in options, debug="--debug" in options)
    exception_info = None
    try:
        with output_policy(OutputPolicy.detect(args)):
            parser = build_parser()
            args = parser.parse_args(arguments)
        for name in ("json", "plain", "no_color", "quiet", "verbose", "debug"):
            if not hasattr(args, name):
                setattr(args, name, False)
        if not hasattr(args, "lang"):
            args.lang = os.environ.get("TESSERA_LANG", "en")
        selected_policy = OutputPolicy.detect(args)
        with output_policy(selected_policy), redirect_stderr(SafeDiagnostics(sys.stderr, selected_policy)):
            return _run_command(args, parser)
    except InitializationCancelled:
        # Compatibility: init cancellation before apply has historically returned 1.
        return emit(args, "init.cancelled", {
            "schema_version": SCHEMA_VERSION, "applied": False, "cancelled": True,
        }, 1)
    except (KeyboardInterrupt, EOFError):
        exception_info = sys.exc_info()
        failure = CliFailure("cancelled", "Operation cancelled. Inspect state before retrying a mutating command.", exit_code=EXIT_CANCELLED)
    except ConfigurationError as exc:
        exception_info = sys.exc_info()
        failure = CliFailure("configuration_error", str(exc), exit_code=2,
                             suggested_command="tessera config doctor")
    except CliFailure as exc:
        exception_info = sys.exc_info()
        failure = exc
    except BrokenPipeError:
        # Prevent a second error when Python flushes buffered stdout at shutdown.
        try:
            null = os.open(os.devnull, os.O_WRONLY)
            try:
                os.dup2(null, sys.stdout.fileno())
            finally:
                os.close(null)
        except (OSError, ValueError):
            pass
        return 0
    except OSError as exc:
        exception_info = sys.exc_info()
        failure = CliFailure("filesystem_error", str(exc), exit_code=EXIT_FILESYSTEM,
                             suggested_command="Check the resolved paths and filesystem permissions.")
    except Exception:
        exception_info = sys.exc_info()
        failure = CliFailure("internal_error", "An unexpected internal error occurred.", exit_code=EXIT_INTERNAL,
                             suggested_command="Repeat with --debug to inspect developer diagnostics.")
    # Expected failures never expose a traceback unless explicitly requested.
    if getattr(args, "debug", False) and exception_info:
        import traceback
        traceback.print_exception(*exception_info, file=sys.stderr)
    context = failure.context
    if getattr(args, "storage_selection", None):
        context.update({"config": args.storage_selection.config_path, "store": args.storage_dir})
    if not context:
        if getattr(args, "storage_dir", None) or getattr(args, "store", None):
            context["store"] = getattr(args, "store", None) or args.storage_dir
        elif not getattr(args, "global_name", None):
            try:
                location = discover_project_config(getattr(args, "project", None) or os.getcwd())
                if location:
                    context["config"] = str(location)
            except OSError:
                pass
    payload = failure.to_dict()
    if getattr(args, "command", None) == "init":
        payload["applied"] = False
    return emit(args, "error", payload, failure.exit_code)


if __name__ == "__main__":
    sys.exit(main())
