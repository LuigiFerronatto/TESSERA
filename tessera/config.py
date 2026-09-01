"""Explicit, deterministic TESSERA configuration and store discovery.

This module selects a store; it never scans memory, constructs an Engine, or
prompts. The legacy resolver at the bottom remains for direct-library and MCP
compatibility while product CLI commands use :class:`ConfigurationResolver`.
"""

from __future__ import annotations

import os
import stat
import tempfile
import uuid
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Mapping, Optional

import yaml


SCHEMA_VERSION = 1
PROJECT_CONFIG_RELATIVE = Path(".tessera") / "config.yaml"
REGISTRY_FILENAME = "registry.yaml"
CANONICAL_STORAGE_ENV = "TESSERA_STORAGE_DIR"
LEGACY_STORAGE_ENV = "LAO_MEM_DIR"
DEFAULT_STORAGE_DIR = "./memories"


class LegacyStorageConfigurationWarning(FutureWarning):
    """Warns that a deprecated storage alias supplied the selected path."""


class ConfigurationError(ValueError):
    """An invalid, missing, or unsafe configuration decision."""


class _UniqueKeyLoader(yaml.SafeLoader):
    pass


def _construct_mapping(loader, node, deep=False):
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise ConfigurationError(f"duplicate configuration key: {key!r}")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping
)


def _load_yaml(path: Path) -> Dict[str, Any]:
    try:
        value = yaml.load(path.read_text(encoding="utf-8"), Loader=_UniqueKeyLoader)
    except ConfigurationError:
        raise
    except (OSError, yaml.YAMLError) as exc:
        raise ConfigurationError(f"cannot parse configuration {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ConfigurationError(f"configuration root in {path} must be a mapping")
    return value


def _closed_keys(value: Mapping[str, Any], allowed: set[str], context: str) -> None:
    unexpected = sorted(set(value) - allowed)
    if unexpected:
        raise ConfigurationError(
            f"unsupported key(s) in {context}: {', '.join(unexpected)}"
        )


def _validate_version(value: Mapping[str, Any], context: str) -> None:
    if value.get("schema_version") != SCHEMA_VERSION:
        raise ConfigurationError(
            f"unsupported schema_version in {context}: {value.get('schema_version')!r}; "
            f"expected {SCHEMA_VERSION}"
        )


def _canonical_path(value: str | os.PathLike[str], *, base: Optional[Path] = None) -> Path:
    if not isinstance(value, (str, os.PathLike)) or not str(value).strip():
        raise ConfigurationError("store path must be a non-empty path")
    raw = Path(value).expanduser()
    if not raw.is_absolute():
        if base is None:
            base = Path.cwd()
        if ".." in raw.parts:
            raise ConfigurationError("relative store paths may not contain '..'")
        raw = base / raw
    return raw.resolve(strict=False)


def _validate_store_id(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConfigurationError("store.id must be a non-empty string")
    try:
        parsed = uuid.UUID(value)
    except (ValueError, AttributeError) as exc:
        raise ConfigurationError("store.id must be a UUID") from exc
    return str(parsed)


@dataclass(frozen=True)
class StoreRecord:
    id: str
    path: str

    @classmethod
    def from_mapping(
        cls, value: Any, *, base: Optional[Path], context: str
    ) -> "StoreRecord":
        if not isinstance(value, dict):
            raise ConfigurationError(f"{context} must be a mapping")
        _closed_keys(value, {"id", "path"}, context)
        if "id" not in value or "path" not in value:
            raise ConfigurationError(f"{context} requires id and path")
        return cls(
            id=_validate_store_id(value["id"]),
            path=str(_canonical_path(value["path"], base=base)),
        )

    def to_mapping(self, *, relative_to: Optional[Path] = None) -> Dict[str, str]:
        path = self.path
        if relative_to is not None:
            try:
                path = str(Path(path).relative_to(relative_to)) or "."
            except ValueError:
                pass
        return {"id": self.id, "path": path}


@dataclass(frozen=True)
class ProjectConfig:
    project_root: Path
    config_path: Path
    store: StoreRecord

    @classmethod
    def load(cls, config_path: Path) -> "ProjectConfig":
        if config_path.is_symlink():
            raise ConfigurationError(f"project configuration may not be a symlink: {config_path}")
        config_path = config_path.resolve(strict=False)
        project_root = config_path.parent.parent.resolve(strict=False)
        raw = _load_yaml(config_path)
        _closed_keys(raw, {"schema_version", "store"}, str(config_path))
        _validate_version(raw, str(config_path))
        store = StoreRecord.from_mapping(
            raw.get("store"), base=project_root, context=f"store in {config_path}"
        )
        return cls(project_root=project_root, config_path=config_path, store=store)

    def to_mapping(self) -> Dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "store": self.store.to_mapping(relative_to=self.project_root),
        }


@dataclass(frozen=True)
class GlobalRegistry:
    path: Path
    stores: Dict[str, StoreRecord] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path, *, missing_ok: bool = True) -> "GlobalRegistry":
        # Preserve the lexical target so a later mutation can detect and
        # refuse a registry-file symlink instead of replacing its referent.
        path = path.expanduser().absolute()
        if not path.exists():
            if missing_ok:
                return cls(path=path, stores={})
            raise ConfigurationError(f"global registry does not exist: {path}")
        raw = _load_yaml(path)
        _closed_keys(raw, {"schema_version", "stores"}, str(path))
        _validate_version(raw, str(path))
        stores_raw = raw.get("stores")
        if not isinstance(stores_raw, dict):
            raise ConfigurationError(f"stores in {path} must be a mapping")
        stores: Dict[str, StoreRecord] = {}
        ids: Dict[str, str] = {}
        paths: Dict[str, tuple[str, str]] = {}
        for name, value in stores_raw.items():
            if not isinstance(name, str) or not name.strip():
                raise ConfigurationError("registry names must be non-empty strings")
            record = StoreRecord.from_mapping(
                value, base=None, context=f"stores.{name} in {path}"
            )
            serialized_path = value.get("path") if isinstance(value, dict) else None
            if not isinstance(serialized_path, str) or not Path(serialized_path).expanduser().is_absolute():
                raise ConfigurationError(f"stores.{name}.path must be absolute")
            if record.id in ids and ids[record.id] != name:
                raise ConfigurationError(
                    f"store id {record.id} is duplicated by {ids[record.id]!r} and {name!r}"
                )
            path_key = os.path.normcase(record.path)
            if path_key in paths and paths[path_key] != (name, record.id):
                other_name, other_id = paths[path_key]
                raise ConfigurationError(
                    f"store path {record.path} conflicts between {other_name!r} "
                    f"({other_id}) and {name!r} ({record.id})"
                )
            ids[record.id] = name
            paths[path_key] = (name, record.id)
            stores[name] = record
        return cls(path=path, stores=stores)

    def to_mapping(self) -> Dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "stores": {
                name: self.stores[name].to_mapping() for name in sorted(self.stores)
            },
        }


@dataclass(frozen=True)
class StorageSelection:
    store_id: Optional[str]
    storage_dir: str
    source: str
    project_root: Optional[str] = None
    config_path: Optional[str] = None
    registry_name: Optional[str] = None
    registry_path: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "store_id": self.store_id,
            "storage_dir": self.storage_dir,
            "source": self.source,
            "project_root": self.project_root,
            "config_path": self.config_path,
            "registry_name": self.registry_name,
            "registry_path": self.registry_path,
        }


def global_registry_path(
    *,
    platform: Optional[str] = None,
    home: Optional[str | os.PathLike[str]] = None,
    environ: Optional[Mapping[str, str]] = None,
) -> Path:
    """Return the OS-appropriate registry path without touching the filesystem."""
    platform = platform or os.sys.platform
    env = os.environ if environ is None else environ
    home_path = Path(home).expanduser() if home is not None else Path.home()
    if platform.startswith("win"):
        root = Path(env.get("APPDATA") or (home_path / "AppData" / "Roaming"))
    elif platform == "darwin":
        root = home_path / "Library" / "Application Support"
    else:
        root = Path(env["XDG_CONFIG_HOME"]) if env.get("XDG_CONFIG_HOME") else home_path / ".config"
    return (root / "tessera" / REGISTRY_FILENAME).resolve(strict=False)


def discover_project_config(
    start: str | os.PathLike[str], *, home: Optional[str | os.PathLike[str]] = None
) -> Optional[Path]:
    """Check one exact marker per physical ancestor; never enumerate directories.

    Symlinks are resolved before traversal. When starting below the user's
    home, the home directory itself is a boundary and is not treated as a
    project. An explicit start equal to home may still select it.
    """
    current = Path(start).expanduser().resolve(strict=False)
    if current.exists() and current.is_file():
        current = current.parent
    home_path = (Path.home() if home is None else Path(home).expanduser()).resolve(strict=False)
    start_is_home = current == home_path
    while True:
        if current == home_path and not start_is_home:
            return None
        marker = current / PROJECT_CONFIG_RELATIVE
        if marker.is_file():
            return marker
        if current.parent == current:
            return None
        current = current.parent


class ConfigurationResolver:
    """Resolve one canonical store using the Issue #117 precedence contract."""

    def __init__(
        self,
        *,
        environ: Optional[Mapping[str, str]] = None,
        registry_path: Optional[str | os.PathLike[str]] = None,
        cwd: Optional[str | os.PathLike[str]] = None,
        home: Optional[str | os.PathLike[str]] = None,
    ) -> None:
        self.environ = os.environ if environ is None else environ
        self.cwd = Path(cwd or os.getcwd()).resolve(strict=False)
        self.home = Path(home).resolve(strict=False) if home is not None else None
        self.registry_path = Path(registry_path).resolve(strict=False) if registry_path else global_registry_path(environ=self.environ, home=home)

    def resolve(
        self,
        *,
        explicit: Optional[str] = None,
        project: Optional[str | os.PathLike[str]] = None,
        global_name: Optional[str] = None,
        warn_legacy: bool = True,
    ) -> StorageSelection:
        if explicit:
            return StorageSelection(None, str(_canonical_path(explicit)), "explicit")
        canonical = self.environ.get(CANONICAL_STORAGE_ENV)
        if canonical:
            return StorageSelection(None, str(_canonical_path(canonical)), "environment")
        legacy = self.environ.get(LEGACY_STORAGE_ENV)
        if legacy:
            if warn_legacy:
                warnings.warn(
                    f"{LEGACY_STORAGE_ENV} is deprecated; set {CANONICAL_STORAGE_ENV} "
                    "instead. The compatibility alias will be removed in a future release.",
                    LegacyStorageConfigurationWarning,
                    stacklevel=2,
                )
            return StorageSelection(None, str(_canonical_path(legacy)), "environment")

        project_start = self.cwd if project is None else Path(project).expanduser().resolve(strict=False)
        config_path = discover_project_config(project_start, home=self.home)
        if config_path is not None:
            config = ProjectConfig.load(config_path)
            return StorageSelection(
                config.store.id,
                config.store.path,
                "project_config",
                project_root=str(config.project_root),
                config_path=str(config.config_path),
            )

        if global_name:
            registry = GlobalRegistry.load(self.registry_path)
            if global_name not in registry.stores:
                available = ", ".join(sorted(registry.stores)) or "none"
                raise ConfigurationError(
                    f"global store {global_name!r} is not registered; available: {available}"
                )
            record = registry.stores[global_name]
            return StorageSelection(
                record.id,
                record.path,
                "global_registry",
                registry_name=global_name,
                registry_path=str(registry.path),
            )
        raise ConfigurationError(
            "no TESSERA store is configured; pass --store, set TESSERA_STORAGE_DIR, "
            "run `tessera init --project --non-interactive`, or select --global NAME"
        )


def _safe_atomic_yaml_write(path: Path, value: Mapping[str, Any]) -> None:
    """Validate, fsync, and atomically replace a non-symlink config target."""
    path = path.absolute()
    if path.is_symlink():
        raise ConfigurationError(f"refusing to replace symlink configuration: {path}")
    parent = path.parent
    if parent.exists() and parent.is_symlink():
        raise ConfigurationError(f"refusing to write through symlink directory: {parent}")
    parent.mkdir(parents=True, exist_ok=True)
    rendered = yaml.safe_dump(dict(value), sort_keys=False, allow_unicode=True)
    yaml.load(rendered, Loader=_UniqueKeyLoader)
    temporary: Optional[str] = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=parent, prefix=f".{path.name}.",
            suffix=".tmp", delete=False
        ) as handle:
            temporary = handle.name
            os.chmod(temporary, stat.S_IRUSR | stat.S_IWUSR)
            handle.write(rendered)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        temporary = None
        try:
            directory_fd = os.open(parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        except OSError:
            pass
    finally:
        if temporary:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass


def write_project_config(config: ProjectConfig) -> None:
    raw = config.to_mapping()
    StoreRecord.from_mapping(raw["store"], base=config.project_root, context="store")
    _safe_atomic_yaml_write(config.config_path, raw)


def write_global_registry(registry: GlobalRegistry) -> None:
    raw = registry.to_mapping()
    ids: set[str] = set()
    paths: set[str] = set()
    for name, record in registry.stores.items():
        _validate_store_id(record.id)
        if not Path(record.path).expanduser().is_absolute():
            raise ConfigurationError(f"registry path for {name!r} must be absolute")
        path = str(_canonical_path(record.path))
        key = os.path.normcase(path)
        if record.id in ids or key in paths:
            raise ConfigurationError(f"conflicting registry entry: {name}")
        ids.add(record.id)
        paths.add(key)
    _safe_atomic_yaml_write(registry.path, raw)


@dataclass(frozen=True)
class InitPlan:
    mode: str
    store_id: str
    storage_dir: str
    config_path: str
    registry_name: Optional[str]
    creates: tuple[str, ...]
    updates: tuple[str, ...]
    deletes: tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "operation": "init",
            "mode": self.mode,
            "store_id": self.store_id,
            "storage_dir": self.storage_dir,
            "config_path": self.config_path,
            "registry_name": self.registry_name,
            "creates": list(self.creates),
            "updates": list(self.updates),
            "deletes": list(self.deletes),
        }


def build_init_plan(
    *,
    mode: str,
    store_path: Optional[str],
    project_root: Optional[str] = None,
    registry_name: Optional[str] = None,
    registry_path: Optional[str | os.PathLike[str]] = None,
    id_factory: Callable[[], Any] = uuid.uuid4,
) -> InitPlan:
    if mode not in {"project", "global"}:
        raise ConfigurationError("init mode must be project or global")
    if mode == "project":
        root = Path(project_root or os.getcwd()).expanduser().resolve(strict=False)
        config_path = root / PROJECT_CONFIG_RELATIVE
        storage = _canonical_path(store_path or "memories", base=root)
        existing = ProjectConfig.load(config_path) if config_path.exists() else None
        store_id = existing.store.id if existing else str(id_factory())
    else:
        if not registry_name:
            raise ConfigurationError("global init requires --global NAME")
        if not store_path:
            raise ConfigurationError("global init requires --store PATH")
        config_path = Path(registry_path).resolve(strict=False) if registry_path else global_registry_path()
        registry = GlobalRegistry.load(config_path)
        existing = registry.stores.get(registry_name)
        store_id = existing.id if existing else str(id_factory())
        storage = _canonical_path(store_path)
    store_id = _validate_store_id(store_id)
    creates = []
    updates = []
    for candidate in (storage, config_path):
        (updates if candidate.exists() else creates).append(str(candidate))
    return InitPlan(
        mode=mode,
        store_id=store_id,
        storage_dir=str(storage),
        config_path=str(config_path),
        registry_name=registry_name if mode == "global" else None,
        creates=tuple(creates),
        updates=tuple(updates),
    )


def apply_init_plan(plan: InitPlan) -> StorageSelection:
    storage = Path(plan.storage_dir)
    record = StoreRecord(plan.store_id, str(storage.resolve(strict=False)))
    config_path = Path(plan.config_path)
    if plan.mode == "project":
        project_root = config_path.parent.parent.resolve(strict=False)
        storage.mkdir(parents=True, exist_ok=True)
        write_project_config(ProjectConfig(project_root, config_path, record))
        return StorageSelection(
            record.id, record.path, "project_config", str(project_root), str(config_path)
        )
    registry = GlobalRegistry.load(config_path)
    stores = dict(registry.stores)
    for name, other in stores.items():
        if name != plan.registry_name and os.path.normcase(other.path) == os.path.normcase(record.path):
            raise ConfigurationError(
                f"store path {record.path} is already registered as {name!r}"
            )
        if name != plan.registry_name and other.id == record.id:
            raise ConfigurationError(f"store id {record.id} is already registered as {name!r}")
    storage.mkdir(parents=True, exist_ok=True)
    stores[plan.registry_name or ""] = record
    write_global_registry(GlobalRegistry(config_path, stores))
    return StorageSelection(
        record.id, record.path, "global_registry",
        registry_name=plan.registry_name, registry_path=str(config_path),
    )


def unregister_global_store(name: str, registry_path: Path) -> StoreRecord:
    registry = GlobalRegistry.load(registry_path)
    if name not in registry.stores:
        raise ConfigurationError(f"global store {name!r} is not registered")
    stores = dict(registry.stores)
    removed = stores.pop(name)
    write_global_registry(GlobalRegistry(registry.path, stores))
    return removed


def resolve_storage_dir(
    explicit: Optional[str] = None,
    *,
    environ: Optional[Mapping[str, str]] = None,
    warn_legacy: bool = True,
) -> str:
    """Legacy direct-library resolver: explicit/env/deprecated-env/./memories."""
    if explicit:
        return explicit
    env = os.environ if environ is None else environ
    canonical = env.get(CANONICAL_STORAGE_ENV)
    if canonical:
        return canonical
    legacy = env.get(LEGACY_STORAGE_ENV)
    if legacy:
        if warn_legacy:
            warnings.warn(
                f"{LEGACY_STORAGE_ENV} is deprecated; set "
                f"{CANONICAL_STORAGE_ENV} instead. The compatibility alias "
                "will be removed in a future release.",
                LegacyStorageConfigurationWarning,
                stacklevel=2,
            )
        return legacy
    return DEFAULT_STORAGE_DIR
