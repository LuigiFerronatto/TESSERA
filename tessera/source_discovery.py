"""Root-bounded, read-only project source discovery.

Discovery proposes candidates for a later selection workflow.  It never changes
configuration, source files, ignore rules, or derived index state.
"""

from __future__ import annotations

import fnmatch
import os
import stat
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path, PurePosixPath
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, Union

from .config import ResolvedConfiguration, SourceRootRecord


DEFAULT_MAX_SOURCE_BYTES = 2 * 1024 * 1024
IGNORE_FILENAME = ".tessera-ignore"


class SourceClassification(str, Enum):
    SUPPORTED = "SUPPORTED"
    RECOMMENDED = "RECOMMENDED"
    IGNORED = "IGNORED"
    FORBIDDEN = "FORBIDDEN"


class SourceReason(str, Enum):
    PROJECT_ENTRYPOINT = "project_entrypoint"
    SUPPORTED_PROJECT_SOURCE = "supported_project_source"
    RECOMMENDED_PROJECT_DIRECTORY = "recommended_project_directory"
    CONFIGURED_SOURCE = "configured_source"
    IGNORED_BY_TESSERA_IGNORE = "ignored_by_tessera_ignore"
    RECOMMENDED_EXCLUSION = "recommended_exclusion"
    MANDATORY_EXCLUSION = "mandatory_exclusion"
    SENSITIVE_FILE = "sensitive_file"
    UNSUPPORTED_FORMAT = "unsupported_format"
    OVERSIZED = "oversized"
    OUTSIDE_ROOT = "outside_root"
    UNSAFE_SYMLINK = "unsafe_symlink"
    DERIVED_INDEX = "derived_index"
    SPECIAL_FILE = "special_file"
    UNREADABLE = "unreadable"
    IGNORE_FILE = "ignore_file"


@dataclass(frozen=True)
class SourceDiscoveryDiagnostic:
    code: str
    path: str
    detail: str

    def to_dict(self) -> Dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class SourceCandidate:
    path: str
    kind: str
    format: Optional[str]
    classification: str
    selectable: bool
    selected_by_default: bool
    reason: str
    size_bytes: Optional[int] = None
    matched_rule: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SourceCluster:
    path: str
    supported_count: int
    recommended_count: int
    ignored_count: int
    forbidden_count: int
    selectable: bool
    recommended: bool
    classification: str
    reason: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SourceDiscoveryPlan:
    project_root: str
    clusters: Tuple[SourceCluster, ...]
    files: Tuple[SourceCandidate, ...]
    totals: Dict[str, int]
    warnings: Tuple[SourceDiscoveryDiagnostic, ...]
    metrics: Dict[str, int]
    max_source_file_bytes: int
    supported_formats: Tuple[str, ...] = ("markdown",)
    schema_version: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "project_root": self.project_root,
            "clusters": [item.to_dict() for item in self.clusters],
            "files": [item.to_dict() for item in self.files],
            "totals": dict(self.totals),
            "warnings": [item.to_dict() for item in self.warnings],
            "metrics": dict(self.metrics),
            "max_source_file_bytes": self.max_source_file_bytes,
            "supported_formats": list(self.supported_formats),
        }


@dataclass(frozen=True)
class _IgnoreRule:
    pattern: str
    negated: bool
    directory_only: bool
    original: str

    def matches(self, path: str, *, is_dir: bool) -> bool:
        normalized = path.rstrip("/")
        pattern = self.pattern.rstrip("/")
        if self.directory_only:
            if normalized == pattern or normalized.startswith(pattern + "/"):
                return True
            if "/" not in pattern:
                return pattern in PurePosixPath(normalized).parts
            return False
        if "/" in pattern:
            return fnmatch.fnmatchcase(normalized, pattern)
        return fnmatch.fnmatchcase(PurePosixPath(normalized).name, pattern)


class IgnoreRuleSet:
    """Documented `.tessera-ignore` subset: comments, !, *, ?, **, and dir/."""

    def __init__(self, rules: Sequence[_IgnoreRule] = ()) -> None:
        self.rules = tuple(rules)

    @classmethod
    def load(
        cls, path: Path, *, root: Path
    ) -> Tuple["IgnoreRuleSet", Tuple[SourceDiscoveryDiagnostic, ...]]:
        relative = _relative_display(path, root)
        if path.is_symlink():
            return cls(), (
                SourceDiscoveryDiagnostic(
                    "unsafe_ignore_file", relative,
                    ".tessera-ignore may not be a symlink",
                ),
            )
        if not path.exists():
            return cls(), ()
        try:
            mode = path.stat().st_mode
        except OSError as exc:
            return cls(), (
                SourceDiscoveryDiagnostic("unreadable_ignore_file", relative, str(exc)),
            )
        if not _readable(mode):
            return cls(), (
                SourceDiscoveryDiagnostic(
                    "unreadable_ignore_file", relative,
                    ".tessera-ignore has no read permission bits",
                ),
            )
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            return cls(), (
                SourceDiscoveryDiagnostic(
                    "unreadable_ignore_file", relative, str(exc),
                ),
            )
        rules: List[_IgnoreRule] = []
        diagnostics: List[SourceDiscoveryDiagnostic] = []
        for number, raw in enumerate(text.splitlines(), start=1):
            stripped = raw.strip()
            if not stripped or stripped.startswith("#"):
                continue
            negated = stripped.startswith("!")
            pattern = stripped[1:] if negated else stripped
            pattern = pattern.replace("\\", "/")
            if pattern.startswith("/"):
                pattern = pattern[1:]
            if (
                not pattern
                or pattern.startswith("/")
                or any(part == ".." for part in PurePosixPath(pattern).parts)
                or "[" in pattern
                or "]" in pattern
            ):
                diagnostics.append(
                    SourceDiscoveryDiagnostic(
                        "invalid_ignore_pattern",
                        relative,
                        f"line {number}: unsupported pattern {raw!r}",
                    )
                )
                continue
            rules.append(
                _IgnoreRule(
                    pattern=pattern,
                    negated=negated,
                    directory_only=pattern.endswith("/"),
                    original=stripped,
                )
            )
        return cls(rules), tuple(diagnostics)

    def classify(self, path: str, *, is_dir: bool) -> Tuple[bool, bool, Optional[str]]:
        ignored = False
        re_included = False
        matched: Optional[str] = None
        for rule in self.rules:
            if rule.matches(path, is_dir=is_dir):
                ignored = not rule.negated
                re_included = rule.negated
                matched = rule.original
        return ignored, re_included, matched

    def may_reinclude_under(self, directory: str) -> bool:
        normalized = directory.rstrip("/")
        prefix = normalized + "/"
        directory_parts = PurePosixPath(normalized).parts
        for rule in self.rules:
            if not rule.negated:
                continue
            pattern = rule.pattern.lstrip("/").rstrip("/")
            if "/" not in pattern:
                return True
            if rule.directory_only and rule.matches(normalized, is_dir=True):
                return True
            pattern_parts = PurePosixPath(pattern).parts
            wildcard_index = next(
                (
                    index
                    for index, part in enumerate(pattern_parts)
                    if any(character in part for character in "*?")
                ),
                len(pattern_parts),
            )
            literal_prefix = pattern_parts[:wildcard_index]
            shared = min(len(directory_parts), len(literal_prefix))
            if directory_parts[:shared] != literal_prefix[:shared]:
                continue
            if wildcard_index < len(pattern_parts) or pattern.startswith(prefix):
                return True
        return False


_ROOT_ENTRYPOINTS = {
    "readme.md",
    "agents.md",
    "claude.md",
    "gemini.md",
    "contributing.md",
}
_RECOMMENDED_DIRECTORIES = {"docs", "research", "memories", "memory"}
_CONVENIENCE_EXCLUSIONS = {
    "node_modules", ".venv", "venv", "dist", "build", "coverage",
    "archive", "tmp", "__pycache__", ".pytest_cache", ".mypy_cache",
    ".ruff_cache", ".tox",
}
_HARD_DENIED_FILENAMES = {"id_rsa", "id_ed25519", "credentials.json"}
_HARD_DENIED_SUFFIXES = {".pem", ".key"}
_HARD_DENIED_DIRECTORIES = {"secrets"}
_CLASSIFICATION_ORDER = {
    SourceClassification.RECOMMENDED.value: 0,
    SourceClassification.SUPPORTED.value: 1,
    SourceClassification.IGNORED.value: 2,
    SourceClassification.FORBIDDEN.value: 3,
}


def _relative_display(path: Path, root: Path) -> str:
    try:
        relative = path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()
    return relative or "."


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _readable(mode: int) -> bool:
    return bool(mode & (stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH))


def _directory_accessible(mode: int) -> bool:
    return _readable(mode) and bool(mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH))


def _is_safe_sensitive_example(name: str) -> bool:
    lowered = name.lower()
    return ".example" in lowered or ".sample" in lowered or lowered.endswith(".template")


def _sensitive_reason(relative: str, *, is_dir: bool) -> Optional[SourceReason]:
    name = PurePosixPath(relative.rstrip("/")).name.lower()
    if is_dir and name in _HARD_DENIED_DIRECTORIES:
        return SourceReason.SENSITIVE_FILE
    if _is_safe_sensitive_example(name):
        return None
    if name in _HARD_DENIED_FILENAMES or Path(name).suffix.lower() in _HARD_DENIED_SUFFIXES:
        return SourceReason.SENSITIVE_FILE
    if name == ".env" or name.startswith(".env.") or name.startswith("credentials."):
        return SourceReason.SENSITIVE_FILE
    return None


def _configured_roots(
    configuration: Optional[ResolvedConfiguration], root: Path
) -> Tuple[Tuple[Path, Tuple[str, ...]], ...]:
    if configuration is None:
        return ()
    configured: List[Tuple[Path, Tuple[str, ...]]] = []
    for source in configuration.source_roots:
        physical = Path(source.path).expanduser().resolve(strict=False)
        if _is_relative_to(physical, root):
            configured.append((physical, tuple(source.include)))
    return tuple(configured)


def _configured_match(
    candidate: Path,
    configured: Sequence[Tuple[Path, Tuple[str, ...]]],
) -> bool:
    for source_root, patterns in configured:
        if not _is_relative_to(candidate, source_root):
            continue
        relative = candidate.relative_to(source_root).as_posix()
        if any(
            fnmatch.fnmatchcase(relative, pattern)
            or (pattern.startswith("**/") and fnmatch.fnmatchcase(relative, pattern[3:]))
            for pattern in patterns
        ):
            return True
    return False


def _directory_candidate(
    path: str, classification: SourceClassification, reason: SourceReason,
    *, matched_rule: Optional[str] = None,
) -> SourceCandidate:
    selectable = classification in {SourceClassification.RECOMMENDED, SourceClassification.SUPPORTED}
    return SourceCandidate(
        path=path.rstrip("/") + "/",
        kind="directory",
        format=None,
        classification=classification.value,
        selectable=selectable,
        selected_by_default=classification is SourceClassification.RECOMMENDED,
        reason=reason.value,
        matched_rule=matched_rule,
    )


def _sort_candidates(items: Iterable[SourceCandidate]) -> Tuple[SourceCandidate, ...]:
    return tuple(sorted(
        items,
        key=lambda item: (
            _CLASSIFICATION_ORDER[item.classification],
            item.path.casefold(),
            item.path,
        ),
    ))


def _build_clusters(files: Sequence[SourceCandidate]) -> Tuple[SourceCluster, ...]:
    grouped: Dict[str, List[SourceCandidate]] = {}
    for item in files:
        clean = item.path.rstrip("/")
        parts = PurePosixPath(clean).parts
        if len(parts) <= 1:
            continue
        grouped.setdefault(parts[0] + "/", []).append(item)
    clusters: List[SourceCluster] = []
    for path, children in grouped.items():
        counts = {classification.value: 0 for classification in SourceClassification}
        for child in children:
            counts[child.classification] += 1
        if counts[SourceClassification.RECOMMENDED.value]:
            classification = SourceClassification.RECOMMENDED
        elif counts[SourceClassification.SUPPORTED.value]:
            classification = SourceClassification.SUPPORTED
        elif counts[SourceClassification.FORBIDDEN.value]:
            classification = SourceClassification.FORBIDDEN
        else:
            classification = SourceClassification.IGNORED
        reasons = {child.reason for child in children}
        if SourceReason.CONFIGURED_SOURCE.value in reasons:
            reason = SourceReason.CONFIGURED_SOURCE
        elif path.rstrip("/").lower() in _RECOMMENDED_DIRECTORIES:
            reason = SourceReason.RECOMMENDED_PROJECT_DIRECTORY
        elif classification is SourceClassification.FORBIDDEN:
            reason = SourceReason.MANDATORY_EXCLUSION
        elif classification is SourceClassification.IGNORED:
            reason = SourceReason.RECOMMENDED_EXCLUSION
        else:
            reason = SourceReason.SUPPORTED_PROJECT_SOURCE
        clusters.append(SourceCluster(
            path=path,
            supported_count=counts[SourceClassification.SUPPORTED.value],
            recommended_count=counts[SourceClassification.RECOMMENDED.value],
            ignored_count=counts[SourceClassification.IGNORED.value],
            forbidden_count=counts[SourceClassification.FORBIDDEN.value],
            selectable=classification in {
                SourceClassification.RECOMMENDED,
                SourceClassification.SUPPORTED,
            },
            recommended=classification is SourceClassification.RECOMMENDED,
            classification=classification.value,
            reason=reason.value,
        ))
    return tuple(sorted(
        clusters,
        key=lambda item: (
            _CLASSIFICATION_ORDER[item.classification],
            item.path.casefold(),
            item.path,
        ),
    ))


def discover_sources(
    project_root: Union[os.PathLike, str],
    configuration: Optional[ResolvedConfiguration] = None,
    *,
    max_file_size: int = DEFAULT_MAX_SOURCE_BYTES,
) -> SourceDiscoveryPlan:
    """Return a deterministic discovery plan without mutating project state."""
    if max_file_size <= 0:
        raise ValueError("max_file_size must be positive")
    lexical_root = Path(project_root).expanduser()
    root = lexical_root.resolve(strict=True)
    if not root.is_dir():
        raise ValueError(f"project_root is not a directory: {root}")
    ignore_rules, diagnostics = IgnoreRuleSet.load(root / IGNORE_FILENAME, root=root)
    warnings: List[SourceDiscoveryDiagnostic] = list(diagnostics)
    candidates: List[SourceCandidate] = []
    configured = _configured_roots(configuration, root)
    mandatory_paths = {PurePosixPath(".git"), PurePosixPath(".tessera/index")}
    index_path: Optional[Path] = None
    if configuration and configuration.index_dir:
        index_path = Path(configuration.index_dir).expanduser().resolve(strict=False)
        if _is_relative_to(index_path, root):
            mandatory_paths.add(PurePosixPath(index_path.relative_to(root).as_posix()))
    metrics = {"directories_visited": 0, "entries_stat": 0}

    def scan(directory: Path) -> None:
        metrics["directories_visited"] += 1
        try:
            entries = sorted(os.scandir(directory), key=lambda item: (item.name.casefold(), item.name))
        except OSError as exc:
            relative = _relative_display(directory, root)
            warnings.append(SourceDiscoveryDiagnostic("unreadable", relative, str(exc)))
            candidates.append(_directory_candidate(relative, SourceClassification.IGNORED, SourceReason.UNREADABLE))
            return
        for entry in entries:
            path = Path(entry.path)
            relative = path.relative_to(root).as_posix()
            metrics["entries_stat"] += 1
            try:
                info = entry.stat(follow_symlinks=False)
            except OSError as exc:
                warnings.append(SourceDiscoveryDiagnostic("unreadable", relative, str(exc)))
                candidates.append(SourceCandidate(
                    path=relative, kind="unknown", format=None,
                    classification=SourceClassification.IGNORED.value,
                    selectable=False, selected_by_default=False,
                    reason=SourceReason.UNREADABLE.value,
                ))
                continue

            if stat.S_ISLNK(info.st_mode):
                try:
                    target = path.resolve(strict=True)
                    reason = SourceReason.UNSAFE_SYMLINK if _is_relative_to(target, root) else SourceReason.OUTSIDE_ROOT
                except (OSError, RuntimeError):
                    reason = SourceReason.UNSAFE_SYMLINK
                warnings.append(SourceDiscoveryDiagnostic(reason.value, relative, "symlinks are not traversed"))
                candidates.append(SourceCandidate(
                    path=relative, kind="symlink", format=None,
                    classification=SourceClassification.FORBIDDEN.value,
                    selectable=False, selected_by_default=False, reason=reason.value,
                ))
                continue

            is_dir = stat.S_ISDIR(info.st_mode)
            pure = PurePosixPath(relative)
            is_derived = any(pure == item or item in pure.parents for item in mandatory_paths)
            if relative == ".tessera_index" or relative.startswith(".tessera_index/"):
                is_derived = True
            if pure == PurePosixPath(".git") or PurePosixPath(".git") in pure.parents:
                candidates.append(_directory_candidate(relative, SourceClassification.FORBIDDEN, SourceReason.MANDATORY_EXCLUSION))
                continue
            if is_derived:
                candidates.append(_directory_candidate(relative, SourceClassification.FORBIDDEN, SourceReason.DERIVED_INDEX))
                continue
            sensitive = _sensitive_reason(relative, is_dir=is_dir)
            if sensitive is not None:
                item = _directory_candidate(relative, SourceClassification.FORBIDDEN, sensitive) if is_dir else SourceCandidate(
                    path=relative, kind="file", format=None,
                    classification=SourceClassification.FORBIDDEN.value,
                    selectable=False, selected_by_default=False, reason=sensitive.value,
                    size_bytes=info.st_size,
                )
                candidates.append(item)
                continue
            ignored, re_included, matched_rule = ignore_rules.classify(relative, is_dir=is_dir)
            top = pure.parts[0].lower() if pure.parts else ""
            convenience = top in _CONVENIENCE_EXCLUSIONS
            if is_dir:
                if not _directory_accessible(info.st_mode):
                    warnings.append(SourceDiscoveryDiagnostic("unreadable", relative, "directory is not readable/searchable"))
                    candidates.append(_directory_candidate(relative, SourceClassification.IGNORED, SourceReason.UNREADABLE))
                    continue
                if ignored:
                    candidates.append(_directory_candidate(
                        relative, SourceClassification.IGNORED,
                        SourceReason.IGNORED_BY_TESSERA_IGNORE,
                        matched_rule=matched_rule,
                    ))
                    if ignore_rules.may_reinclude_under(relative):
                        scan(path)
                    continue
                if convenience and not re_included:
                    candidates.append(_directory_candidate(
                        relative, SourceClassification.IGNORED,
                        SourceReason.RECOMMENDED_EXCLUSION,
                    ))
                    if ignore_rules.may_reinclude_under(relative):
                        scan(path)
                    continue
                scan(path)
                continue

            if not stat.S_ISREG(info.st_mode):
                candidates.append(SourceCandidate(
                    path=relative, kind="special", format=None,
                    classification=SourceClassification.FORBIDDEN.value,
                    selectable=False, selected_by_default=False,
                    reason=SourceReason.SPECIAL_FILE.value,
                ))
                continue
            if relative == IGNORE_FILENAME:
                candidates.append(SourceCandidate(
                    path=relative, kind="file", format=None,
                    classification=SourceClassification.IGNORED.value,
                    selectable=False, selected_by_default=False,
                    reason=SourceReason.IGNORE_FILE.value,
                    size_bytes=info.st_size,
                ))
                continue
            if not _readable(info.st_mode):
                warnings.append(SourceDiscoveryDiagnostic("unreadable", relative, "file has no read permission bits"))
                candidates.append(SourceCandidate(
                    path=relative, kind="file", format=None,
                    classification=SourceClassification.IGNORED.value,
                    selectable=False, selected_by_default=False,
                    reason=SourceReason.UNREADABLE.value,
                    size_bytes=info.st_size,
                ))
                continue
            if ignored:
                candidates.append(SourceCandidate(
                    path=relative, kind="file", format="markdown" if path.suffix.lower() == ".md" else None,
                    classification=SourceClassification.IGNORED.value,
                    selectable=False, selected_by_default=False,
                    reason=SourceReason.IGNORED_BY_TESSERA_IGNORE.value,
                    size_bytes=info.st_size, matched_rule=matched_rule,
                ))
                continue
            if convenience and not re_included:
                candidates.append(SourceCandidate(
                    path=relative, kind="file", format="markdown" if path.suffix.lower() == ".md" else None,
                    classification=SourceClassification.IGNORED.value,
                    selectable=False, selected_by_default=False,
                    reason=SourceReason.RECOMMENDED_EXCLUSION.value,
                    size_bytes=info.st_size,
                ))
                continue
            if path.suffix.lower() != ".md":
                candidates.append(SourceCandidate(
                    path=relative, kind="file", format=None,
                    classification=SourceClassification.IGNORED.value,
                    selectable=False, selected_by_default=False,
                    reason=SourceReason.UNSUPPORTED_FORMAT.value,
                    size_bytes=info.st_size,
                ))
                continue
            if info.st_size > max_file_size:
                candidates.append(SourceCandidate(
                    path=relative, kind="file", format="markdown",
                    classification=SourceClassification.IGNORED.value,
                    selectable=False, selected_by_default=False,
                    reason=SourceReason.OVERSIZED.value,
                    size_bytes=info.st_size,
                ))
                continue
            physical = path.resolve(strict=False)
            if not _is_relative_to(physical, root):
                candidates.append(SourceCandidate(
                    path=relative, kind="file", format="markdown",
                    classification=SourceClassification.FORBIDDEN.value,
                    selectable=False, selected_by_default=False,
                    reason=SourceReason.OUTSIDE_ROOT.value,
                    size_bytes=info.st_size,
                ))
                continue
            configured_match = _configured_match(physical, configured)
            root_entrypoint = len(pure.parts) == 1 and pure.name.lower() in _ROOT_ENTRYPOINTS
            recommended_dir = top in _RECOMMENDED_DIRECTORIES
            if configured_match:
                classification = SourceClassification.RECOMMENDED
                reason = SourceReason.CONFIGURED_SOURCE
            elif root_entrypoint:
                classification = SourceClassification.RECOMMENDED
                reason = SourceReason.PROJECT_ENTRYPOINT
            elif recommended_dir:
                classification = SourceClassification.RECOMMENDED
                reason = SourceReason.RECOMMENDED_PROJECT_DIRECTORY
            else:
                classification = SourceClassification.SUPPORTED
                reason = SourceReason.SUPPORTED_PROJECT_SOURCE
            candidates.append(SourceCandidate(
                path=relative, kind="file", format="markdown",
                classification=classification.value,
                selectable=True,
                selected_by_default=classification is SourceClassification.RECOMMENDED,
                reason=reason.value,
                size_bytes=info.st_size,
                matched_rule=matched_rule if re_included else None,
            ))

    scan(root)
    ordered = _sort_candidates(candidates)
    for item in ordered:
        if item.classification != SourceClassification.FORBIDDEN.value or not configured:
            continue
        candidate_path = (root / item.path.rstrip("/")).resolve(strict=False)
        if item.kind == "directory":
            configured_conflict = any(
                source_root == candidate_path or _is_relative_to(source_root, candidate_path)
                for source_root, _patterns in configured
            )
        else:
            configured_conflict = _configured_match(candidate_path, configured)
        if configured_conflict:
            warnings.append(SourceDiscoveryDiagnostic(
                "configured_source_forbidden",
                item.path,
                f"configured source conflicts with mandatory policy: {item.reason}",
            ))
    totals = {classification.value: 0 for classification in SourceClassification}
    for item in ordered:
        totals[item.classification] += 1
    metrics.update({
        "supported_candidates": totals[SourceClassification.SUPPORTED.value],
        "recommended_candidates": totals[SourceClassification.RECOMMENDED.value],
        "ignored_candidates": totals[SourceClassification.IGNORED.value],
        "forbidden_candidates": totals[SourceClassification.FORBIDDEN.value],
    })
    return SourceDiscoveryPlan(
        project_root=str(root),
        clusters=_build_clusters(ordered),
        files=ordered,
        totals=totals,
        warnings=tuple(sorted(warnings, key=lambda item: (item.code, item.path, item.detail))),
        metrics=metrics,
        max_source_file_bytes=max_file_size,
    )


def discover_sources_for_configuration(
    configuration: ResolvedConfiguration,
    *,
    max_file_size: int = DEFAULT_MAX_SOURCE_BYTES,
) -> SourceDiscoveryPlan:
    if not configuration.project_root:
        raise ValueError("source discovery requires a project configuration root")
    return discover_sources(
        configuration.project_root,
        configuration,
        max_file_size=max_file_size,
    )
