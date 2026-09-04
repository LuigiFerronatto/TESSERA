"""Safe planning and application boundary for ``tessera init``.

Issue #155 owns selection, planning, confirmation and orchestration.  Filesystem
classification remains entirely in :mod:`tessera.source_discovery`, project
configuration serialization remains in :mod:`tessera.config`, and indexing
remains in :class:`tessera.engine.TesseraEngine`.
"""

from __future__ import annotations

import os
import stat
import uuid
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Dict, Optional, Sequence, Tuple

from .config import (
    PROJECT_SCHEMA_VERSION,
    ConfigurationError,
    ConfigurationResolver,
    IndexRecord,
    ProjectConfig,
    ResolvedConfiguration,
    SourceRootRecord,
    StoreRecord,
    apply_init_plan,
    build_init_plan,
    safe_atomic_text_write,
)
from .source_discovery import (
    IGNORE_FILENAME,
    SourceClassification,
    SourceDiscoveryPlan,
    discover_sources,
)


SOURCE_MODES = ("recommended", "custom", "memory-only")
_BLOCKING_DISCOVERY_WARNINGS = {
    "invalid_ignore_pattern",
    "unreadable_ignore_file",
    "unsafe_ignore_file",
    "configured_source_forbidden",
}


@dataclass(frozen=True)
class InitRequest:
    mode: str
    project_root: Optional[str] = None
    registry_name: Optional[str] = None
    store_path: Optional[str] = None
    source_mode: Optional[str] = None
    source_paths: Tuple[str, ...] = ()
    persist_exclusions: Tuple[str, ...] = ()
    index_path: Optional[str] = None
    registry_path: Optional[str] = None


@dataclass(frozen=True)
class InitializationPlan:
    mode: str
    project_root: Optional[str]
    config_path: str
    store_id: str
    generated_memory_store: str
    source_mode: str
    selected_sources: Tuple[str, ...]
    source_roots: Tuple[SourceRootRecord, ...]
    index_path: str
    discovery: Optional[SourceDiscoveryPlan]
    ignore_path: Optional[str]
    ignore_changes: Tuple[str, ...]
    proposed_ignore_text: Optional[str]
    config_changes: Tuple[str, ...]
    planned_mutations: Dict[str, Any]
    warnings: Tuple[str, ...]
    registry_name: Optional[str] = None
    current_configuration: Optional[Dict[str, Any]] = None
    proposed_configuration: Optional[Dict[str, Any]] = None
    preflight_problems: Tuple[str, ...] = ()

    @property
    def material_config_change(self) -> bool:
        return bool(self.planned_mutations.get("config"))

    def to_dict(self) -> Dict[str, Any]:
        discovery = self.discovery
        totals = discovery.totals if discovery else {
            classification.value: 0 for classification in SourceClassification
        }
        optional_count = totals.get(SourceClassification.SUPPORTED.value, 0)
        return {
            "mode": self.mode,
            "scope": self.mode,
            "project_root": self.project_root,
            "config_path": self.config_path,
            "store": {
                "id": self.store_id,
                "path": self.generated_memory_store,
            },
            "source_mode": self.source_mode,
            "sources": {
                "selected": list(self.selected_sources),
                "selected_count": len(self.selected_sources),
                "selected_count_kind": "project_sources_outside_generated_store",
                "generated_memory_store_included": True,
                "recommended_count": totals.get(SourceClassification.RECOMMENDED.value, 0),
                "optional_count": optional_count,
                "ignored_count": totals.get(SourceClassification.IGNORED.value, 0),
                "forbidden_count": totals.get(SourceClassification.FORBIDDEN.value, 0),
                "roots": [
                    {"path": item.path, "include": list(item.include)}
                    for item in self.source_roots
                ],
            },
            "index": {"path": self.index_path, "requested": True},
            "config_changes": list(self.config_changes),
            "ignore": {
                "path": self.ignore_path,
                "changes": list(self.ignore_changes),
            },
            "planned_mutations": dict(self.planned_mutations),
            "deletes": [],
            "source_files_modified": 0,
            "warnings": list(self.warnings),
            "preflight_problems": list(self.preflight_problems),
            "existing_configuration": self.current_configuration,
            "proposed_configuration": self.proposed_configuration,
            "discovery": discovery.to_dict() if discovery else None,
        }


@dataclass(frozen=True)
class InitializationResult:
    configuration: ResolvedConfiguration
    indexed_nodes: int
    indexed_relations: int
    indexed_sources: Tuple[str, ...]
    config_applied: bool = True
    ignore_applied: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "storage_selection": self.configuration.to_dict(),
            "indexed_nodes": self.indexed_nodes,
            "indexed_relations": self.indexed_relations,
            "indexed_sources": list(self.indexed_sources),
            "source_files_modified": 0,
            "config_applied": self.config_applied,
            "ignore_applied": self.ignore_applied,
        }


class InitializationApplyError(ConfigurationError):
    """An apply failed after one or more canonical mutations succeeded."""

    def __init__(
        self, message: str, *, config_applied: bool, ignore_applied: bool,
        store_prepared: bool,
    ):
        super().__init__(message)
        self.config_applied = config_applied
        self.ignore_applied = ignore_applied
        self.store_prepared = store_prepared


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _deterministic_store_id(mode: str, config_path: str, store_path: str) -> uuid.UUID:
    identity = (
        f"tessera:init:{mode}:{Path(config_path).resolve(strict=False)}:"
        f"{Path(store_path).resolve(strict=False)}"
    )
    return uuid.uuid5(uuid.NAMESPACE_URL, identity)


def _normalize_requested_path(value: str, root: Path) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConfigurationError("source paths must be non-empty project-relative paths")
    raw = value.strip().replace("\\", "/").rstrip("/")
    candidate = PurePosixPath(raw)
    if candidate.is_absolute() or ".." in candidate.parts or raw in {"", "."}:
        raise ConfigurationError(f"source must be a project-relative file or directory: {value!r}")
    physical = (root / Path(*candidate.parts)).resolve(strict=False)
    if not _is_relative_to(physical, root):
        raise ConfigurationError(f"source escapes the project boundary: {value!r}")
    return candidate.as_posix()


def _select_custom(
    discovery: SourceDiscoveryPlan, requested: Sequence[str], root: Path
) -> Tuple[str, ...]:
    if not requested:
        raise ConfigurationError("custom source mode requires at least one --source PATH")
    candidates = {item.path.rstrip("/"): item for item in discovery.files}
    selected = set()
    for raw in requested:
        path = _normalize_requested_path(raw, root)
        direct = candidates.get(path)
        descendants = [
            item for item in discovery.files
            if item.path.rstrip("/").startswith(path + "/")
        ]
        if direct is not None and direct.classification == SourceClassification.FORBIDDEN.value:
            raise ConfigurationError(
                f"forbidden source cannot be selected: {path} ({direct.reason})"
            )
        forbidden_descendants = [
            item for item in descendants
            if item.classification == SourceClassification.FORBIDDEN.value
        ]
        selectable = [
            item for item in ([direct] if direct is not None else []) + descendants
            if item is not None and item.kind == "file" and item.selectable
        ]
        if direct is not None and direct.kind == "file" and not direct.selectable:
            raise ConfigurationError(
                f"source is not selectable: {path} ({direct.reason})"
            )
        if not selectable:
            if forbidden_descendants:
                raise ConfigurationError(f"source contains no selectable files: {path}")
            raise ConfigurationError(f"source was not found as a safe Markdown candidate: {path}")
        selected.update(item.path for item in selectable)
    return tuple(sorted(selected, key=lambda item: (item.casefold(), item)))


def _selected_paths(
    source_mode: str,
    discovery: SourceDiscoveryPlan,
    requested: Sequence[str],
    root: Path,
) -> Tuple[str, ...]:
    if source_mode == "memory-only":
        return ()
    if source_mode == "recommended":
        return tuple(
            item.path for item in discovery.files
            if item.kind == "file" and item.selectable and item.selected_by_default
        )
    return _select_custom(discovery, requested, root)


def _source_roots(
    root: Path, store: Path, selected: Sequence[str]
) -> Tuple[SourceRootRecord, ...]:
    roots = [SourceRootRecord(str(store), ("**/*.md",))]
    selected_without_store = []
    for item in selected:
        physical = (root / item).resolve(strict=False)
        if _is_relative_to(physical, store):
            continue
        selected_without_store.append(item)
    if selected_without_store:
        roots.append(SourceRootRecord(str(root), tuple(selected_without_store)))
    return tuple(roots)


def _permission_problem(path: Path, *, directory_target: bool) -> Optional[str]:
    candidate = path if path.exists() else path.parent
    while not candidate.exists() and candidate.parent != candidate:
        candidate = candidate.parent
    if not candidate.exists():
        return f"no existing parent is available for {path}"
    try:
        mode = candidate.stat().st_mode
    except OSError as exc:
        return f"cannot inspect {candidate}: {exc}"
    required = stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH
    if not mode & required:
        return f"path is not writable: {candidate}"
    if not directory_target and path.exists() and path.is_dir():
        return f"file target is a directory: {path}"
    if directory_target and path.exists() and not path.is_dir():
        return f"directory target is a file: {path}"
    return None


def _read_ignore_for_plan(path: Path) -> str:
    if path.is_symlink():
        raise ConfigurationError(f".tessera-ignore may not be a symlink: {path}")
    if not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ConfigurationError(f"cannot read {path}: {exc}") from exc


def _proposed_ignore(existing: str, additions: Sequence[str]) -> str:
    if not additions:
        return existing
    rendered = existing
    if rendered and not rendered.endswith("\n"):
        rendered += "\n"
    for item in additions:
        line = item.rstrip("/") + ("/" if item.endswith("/") else "")
        if line not in {existing_line.strip() for existing_line in rendered.splitlines()}:
            rendered += line + "\n"
    return rendered


def _validate_ignore_additions(
    additions: Sequence[str], discovery: SourceDiscoveryPlan, root: Path,
    *, existing_lines: Sequence[str] = (),
) -> Tuple[str, ...]:
    normalized = []
    for raw in additions:
        path = _normalize_requested_path(raw, root)
        direct = next(
            (item for item in discovery.files if item.path.rstrip("/") == path), None
        )
        descendants = [
            item for item in discovery.files
            if item.path.rstrip("/").startswith(path + "/")
        ]
        selectable = [item for item in descendants if item.selectable]
        if direct and direct.classification == SourceClassification.FORBIDDEN.value:
            raise ConfigurationError(f"forbidden paths cannot be persisted as preferences: {path}")
        suffix = "/" if descendants or (direct and direct.kind == "directory") else ""
        normalized_path = path + suffix
        if normalized_path in existing_lines:
            normalized.append(normalized_path)
            continue
        if not ((direct and direct.selectable) or selectable):
            reason = direct.reason if direct else "not discovered"
            raise ConfigurationError(f"only selectable exclusions may be persisted: {path} ({reason})")
        normalized.append(normalized_path)
    return tuple(sorted(set(normalized), key=lambda item: (item.casefold(), item)))


def _simulate_ignore(root: Path, text: str) -> SourceDiscoveryPlan:
    """Use #154's parser/scanner against an isolated shadow of the ignore file.

    The canonical project remains untouched.  The shadow contains only the
    proposed ignore file while discovery still scans the real project, so the
    scanner needs an explicit parser input.  Importing here avoids a second
    ignore implementation.
    """
    from .source_discovery import discover_sources_with_ignore_text

    return discover_sources_with_ignore_text(root, text)


def build_initialization_plan(request: InitRequest) -> InitializationPlan:
    if request.mode not in {"project", "global"}:
        raise ConfigurationError("init mode must be project or global")
    if request.mode == "global":
        registry_target = request.registry_path
        if registry_target is None:
            from .config import global_registry_path
            registry_target = str(global_registry_path())
        if not request.store_path:
            raise ConfigurationError("global init requires --store PATH")
        base = build_init_plan(
            mode="global",
            store_path=request.store_path,
            registry_name=request.registry_name,
            registry_path=registry_target,
            id_factory=lambda: _deterministic_store_id(
                "global", registry_target or "", request.store_path or ""
            ),
        )
        from .config import GlobalRegistry

        registry = GlobalRegistry.load(Path(base.config_path))
        existing = registry.stores.get(request.registry_name or "")
        proposed_record = {"id": base.store_id, "path": base.storage_dir}
        current_record = (
            {"id": existing.id, "path": existing.path} if existing else None
        )
        config_changes = ()
        if existing is None:
            config_changes = ("create named global store",)
        elif Path(existing.path).resolve(strict=False) != Path(base.storage_dir).resolve(strict=False):
            config_changes = ("change named global generated-memory store",)
        problems = tuple(
            problem for problem in (
                _permission_problem(Path(base.config_path), directory_target=False),
                _permission_problem(Path(base.storage_dir), directory_target=True),
                _permission_problem(
                    Path(base.index_dir or Path(base.storage_dir) / ".tessera_index"),
                    directory_target=True,
                ),
            ) if problem
        )
        return InitializationPlan(
            mode="global",
            project_root=None,
            config_path=base.config_path,
            store_id=base.store_id,
            generated_memory_store=base.storage_dir,
            source_mode="memory-only",
            selected_sources=(),
            source_roots=base.source_roots,
            index_path=base.index_dir or str(Path(base.storage_dir) / ".tessera_index"),
            discovery=None,
            ignore_path=None,
            ignore_changes=(),
            proposed_ignore_text=None,
            config_changes=config_changes,
            planned_mutations={
                "config": bool(config_changes), "ignore_file": False, "store": not Path(base.storage_dir).exists(),
                "index": True, "source_files": 0,
            },
            warnings=(),
            registry_name=request.registry_name,
            current_configuration=current_record,
            proposed_configuration=proposed_record,
            preflight_problems=problems,
        )

    root = Path(request.project_root or os.getcwd()).expanduser().resolve(strict=False)
    if not root.exists() or not root.is_dir():
        raise ConfigurationError(f"project root must be an existing directory: {root}")
    config_path = root / ".tessera" / "config.yaml"
    current = ProjectConfig.load(config_path) if config_path.exists() else None
    store_value = request.store_path or (current.store.path if current else "memories")
    provisional = build_init_plan(
        mode="project",
        store_path=store_value,
        project_root=str(root),
        id_factory=lambda: _deterministic_store_id("project", str(config_path), str(root / store_value)),
    )
    store = Path(provisional.storage_dir).resolve(strict=False)
    index_path = (
        (root / request.index_path).resolve(strict=False)
        if request.index_path
        else Path(
            current.resolved_index().path
            if current
            else provisional.index_dir or root / ".tessera" / "index"
        ).resolve(strict=False)
    )
    if not _is_relative_to(index_path, root):
        raise ConfigurationError("index path must remain inside the project")
    if _is_relative_to(index_path, store):
        raise ConfigurationError("derived index must remain outside the generated-memory store")

    configured = None
    if current:
        configured = ResolvedConfiguration(
            current.store.id, current.store.path, "project_config",
            project_root=str(root), config_path=str(config_path),
            source_roots=current.resolved_sources(), index_dir=current.resolved_index().path,
            identity_root=str(root) if current.loaded_schema_version == PROJECT_SCHEMA_VERSION else current.store.path,
            config_schema_version=current.loaded_schema_version,
        )
    discovery = discover_sources(root, configured)
    blocking = [warning for warning in discovery.warnings if warning.code in _BLOCKING_DISCOVERY_WARNINGS]
    if blocking:
        details = "; ".join(f"{item.code}:{item.path}:{item.detail}" for item in blocking)
        raise ConfigurationError(f"source discovery cannot produce a safe plan: {details}")

    source_mode = request.source_mode or "memory-only"
    if source_mode not in SOURCE_MODES:
        raise ConfigurationError(f"source mode must be one of: {', '.join(SOURCE_MODES)}")
    selected = _selected_paths(source_mode, discovery, request.source_paths, root)
    ignore_path = root / IGNORE_FILENAME
    existing_ignore = _read_ignore_for_plan(ignore_path)
    existing_ignore_lines = tuple(
        line.strip() for line in existing_ignore.splitlines() if line.strip()
    )
    ignore_additions = _validate_ignore_additions(
        request.persist_exclusions, discovery, root,
        existing_lines=existing_ignore_lines,
    )
    proposed_ignore = _proposed_ignore(existing_ignore, ignore_additions)
    actual_ignore_changes = ignore_additions if proposed_ignore != existing_ignore else ()
    if actual_ignore_changes:
        discovery = _simulate_ignore(root, proposed_ignore)
        selected = tuple(
            item for item in selected
            if (root / item).resolve(strict=False) in {
                (root / candidate.path).resolve(strict=False)
                for candidate in discovery.files if candidate.selectable
            }
        )

    # The generated-memory store is always one readable source root, but it is
    # presented separately from selected existing project knowledge.
    selected = tuple(
        item for item in selected
        if not _is_relative_to((root / item).resolve(strict=False), store)
    )

    roots = _source_roots(root, store, selected)
    proposed = ProjectConfig(
        root, config_path, StoreRecord(provisional.store_id, str(store)), roots,
        IndexRecord(str(index_path)), PROJECT_SCHEMA_VERSION,
    )
    proposed_mapping = proposed.to_mapping()
    current_mapping = current.to_mapping() if current else None
    changes = []
    if current is None:
        changes.append("create project configuration")
    else:
        if current.loaded_schema_version == 1:
            changes.append("migrate configuration schema v1 to v2")
        if Path(current.store.path).resolve(strict=False) != store:
            changes.append("change generated-memory store")
        if current.resolved_sources() != roots:
            changes.append("change selected source corpus")
        if Path(current.resolved_index().path).resolve(strict=False) != index_path:
            changes.append("change derived index path")
        if current.loaded_schema_version == PROJECT_SCHEMA_VERSION and current_mapping == proposed_mapping:
            changes = []

    problems = tuple(
        problem for problem in (
            _permission_problem(config_path, directory_target=False),
            _permission_problem(store, directory_target=True),
            _permission_problem(index_path, directory_target=True),
            _permission_problem(ignore_path, directory_target=False) if actual_ignore_changes else None,
        ) if problem
    )
    warnings = tuple(
        f"{item.code}: {item.path}: {item.detail}" for item in discovery.warnings
    )
    return InitializationPlan(
        mode="project",
        project_root=str(root),
        config_path=str(config_path),
        store_id=provisional.store_id,
        generated_memory_store=str(store),
        source_mode=source_mode,
        selected_sources=selected,
        source_roots=roots,
        index_path=str(index_path),
        discovery=discovery,
        ignore_path=str(ignore_path),
        ignore_changes=actual_ignore_changes,
        proposed_ignore_text=proposed_ignore if actual_ignore_changes else None,
        config_changes=tuple(changes),
        planned_mutations={
            "config": bool(changes),
            "ignore_file": bool(actual_ignore_changes),
            "store": not store.exists(),
            "index": True,
            "source_files": 0,
        },
        warnings=warnings,
        current_configuration=current_mapping,
        proposed_configuration=proposed_mapping,
        preflight_problems=problems,
    )


def apply_initialization_plan(plan: InitializationPlan) -> InitializationResult:
    if plan.preflight_problems:
        raise ConfigurationError("preflight failed: " + "; ".join(plan.preflight_problems))
    base = build_init_plan(
        mode=plan.mode,
        store_path=plan.generated_memory_store,
        project_root=plan.project_root,
        registry_name=plan.registry_name,
        registry_path=plan.config_path if plan.mode == "global" else None,
        id_factory=lambda: uuid.UUID(plan.store_id),
    )
    if plan.mode == "project":
        base = type(base)(
            mode=base.mode, store_id=plan.store_id,
            storage_dir=plan.generated_memory_store, config_path=plan.config_path,
            registry_name=None, creates=base.creates, updates=base.updates,
            source_roots=plan.source_roots, index_dir=plan.index_path,
            identity_root=plan.project_root, deletes=(),
        )
    config_applied = False
    ignore_applied = False
    apply_started = False
    try:
        apply_started = True
        if plan.planned_mutations.get("config"):
            selection = apply_init_plan(base)
            config_applied = True
        else:
            resolver = ConfigurationResolver(
                cwd=plan.project_root or os.getcwd(),
                environ={},
                registry_path=plan.config_path,
            )
            selection = resolver.resolve(
                project=plan.project_root if plan.mode == "project" else None,
                global_name=plan.registry_name if plan.mode == "global" else None,
            )
            Path(selection.storage_dir).mkdir(parents=True, exist_ok=True)
        if plan.proposed_ignore_text is not None and plan.ignore_path:
            safe_atomic_text_write(Path(plan.ignore_path), plan.proposed_ignore_text)
            ignore_applied = True
            # Re-run the canonical #154 scanner after the approved ignore write.
            post_ignore = discover_sources(Path(plan.project_root or "."), selection)
            blocking = [
                item for item in post_ignore.warnings
                if item.code in _BLOCKING_DISCOVERY_WARNINGS
            ]
            if blocking:
                raise ConfigurationError("persisted ignore rules failed discovery validation")
        from .engine import TesseraEngine

        engine = TesseraEngine(configuration=selection)
        engine.build_index(use_cache=True)
        indexed = tuple(sorted(engine.file_registry.values()))
        allowed = {
            str(path.resolve(strict=False))
            for source in plan.source_roots
            for pattern in source.include
            for path in Path(source.path).glob(pattern)
            if path.is_file() and path.suffix.lower() == ".md"
        }
        if any(str(Path(path).resolve(strict=False)) not in allowed for path in indexed):
            raise ConfigurationError("indexing escaped the selected source set")
        return InitializationResult(
            selection, engine.graph.number_of_nodes(), engine.graph.number_of_edges(), indexed,
            config_applied=config_applied, ignore_applied=ignore_applied,
        )
    except Exception as exc:
        if apply_started or config_applied:
            raise InitializationApplyError(
                f"initialization apply failed: {exc}",
                config_applied=config_applied, ignore_applied=ignore_applied,
                store_prepared=Path(plan.generated_memory_store).is_dir(),
            ) from exc
        raise
