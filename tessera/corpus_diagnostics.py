"""Read-only diagnostics for configured TESSERA source corpora and indexes."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from .canonical import DRAWERS, CanonicalMetadata, parse_and_normalize
from .config import ResolvedConfiguration
from .source_formats import is_supported_source_path, split_source


_EXCLUDED_DIRECTORY_NAMES = {
    ".browser-harness",
    ".git",
    ".tessera_index",
    ".venv-browser-agent",
    "Tessera",
    "node_modules",
    "venv",
}
_SEVERITY_ORDER = {"error": 0, "warning": 1}


@dataclass(frozen=True)
class CorpusFinding:
    code: str
    severity: str
    message: str
    path: Optional[str] = None
    hint: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {key: value for key, value in asdict(self).items() if value is not None}


@dataclass(frozen=True)
class SourceDiagnostic:
    path: str
    format: str
    metadata_state: str
    memory_id: Optional[str]
    id_origin: Optional[str]
    inferred_fields: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        value = asdict(self)
        value["inferred_fields"] = list(self.inferred_fields)
        return value


@dataclass
class CorpusDoctorReport:
    project_root: Optional[str]
    storage_dir: str
    index_dir: str
    status: str = "healthy"
    sources: List[SourceDiagnostic] = field(default_factory=list)
    findings: List[CorpusFinding] = field(default_factory=list)
    counts: Dict[str, int] = field(default_factory=dict)
    source_files_modified: int = 0

    @property
    def errors(self) -> int:
        return sum(item.severity == "error" for item in self.findings)

    @property
    def warnings(self) -> int:
        return sum(item.severity == "warning" for item in self.findings)

    @property
    def exit_code(self) -> int:
        return 1 if self.errors else 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": 1,
            "status": self.status,
            "project_root": self.project_root,
            "storage_dir": self.storage_dir,
            "index_dir": self.index_dir,
            "counts": dict(sorted(self.counts.items())),
            "source_files_modified": self.source_files_modified,
            "sources": [item.to_dict() for item in self.sources],
            "findings": [item.to_dict() for item in self.findings],
        }


def _relative(path: Path, base: Path) -> str:
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        return os.path.relpath(path, base).replace(os.sep, "/")


def _identity_base(path: Path, configuration: ResolvedConfiguration) -> Path:
    store = Path(configuration.storage_dir).resolve(strict=False)
    resolved = path.resolve(strict=False)
    try:
        resolved.relative_to(store)
        return store
    except ValueError:
        return Path(configuration.identity_root).resolve(strict=False)


def _configured_sources(
    configuration: ResolvedConfiguration,
) -> Tuple[List[Path], List[CorpusFinding]]:
    index_root = Path(configuration.index_dir).resolve(strict=False)
    identity_root = Path(configuration.identity_root).resolve(strict=False)
    selected: Dict[str, Path] = {}
    findings: List[CorpusFinding] = []
    for source_root in configuration.source_roots:
        root = Path(source_root.path).expanduser().resolve(strict=False)
        if not root.exists():
            findings.append(
                CorpusFinding(
                    "source_root_missing",
                    "error",
                    "Configured source root does not exist.",
                    _relative(root, identity_root),
                    "Correct the source root or run `tessera init` again.",
                )
            )
            continue
        if not root.is_dir():
            findings.append(
                CorpusFinding(
                    "source_root_not_directory",
                    "error",
                    "Configured source root is not a directory.",
                    _relative(root, identity_root),
                )
            )
            continue
        for pattern in source_root.include:
            for candidate in root.glob(pattern):
                if not candidate.is_file() or not is_supported_source_path(candidate):
                    continue
                resolved = candidate.resolve(strict=False)
                display_path = _relative(candidate.absolute(), identity_root)
                try:
                    relative_to_root = resolved.relative_to(root)
                except ValueError:
                    findings.append(
                        CorpusFinding(
                            "unsafe_symlink",
                            "error",
                            "Configured source resolves outside its source root.",
                            display_path,
                            "Remove the symlink from the selected source set.",
                        )
                    )
                    continue
                if any(part in {".git", ".tessera_index"} for part in relative_to_root.parts[:-1]):
                    continue
                has_wildcard = any(character in pattern for character in "*?[")
                if has_wildcard and any(
                    part in _EXCLUDED_DIRECTORY_NAMES for part in relative_to_root.parts[:-1]
                ):
                    continue
                try:
                    resolved.relative_to(index_root)
                    continue
                except ValueError:
                    pass
                selected[os.path.normcase(str(resolved))] = resolved
    return sorted(selected.values(), key=lambda item: _relative(item, identity_root)), findings


def _load_json(path: Path) -> Tuple[Optional[Any], Optional[CorpusFinding]]:
    if not path.is_file():
        return None, None
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return None, CorpusFinding(
            "invalid_index_artifact",
            "error",
            f"Derived index artifact cannot be read as JSON: {exc}",
            str(path),
            "Delete the derived index and run `tessera index`.",
        )


def _nested_metadata(frontmatter: Mapping[str, Any]) -> Mapping[str, Any]:
    nested = frontmatter.get("metadata")
    return nested if isinstance(nested, Mapping) else {}


def _first(frontmatter: Mapping[str, Any], *keys: str) -> Any:
    nested = _nested_metadata(frontmatter)
    for mapping in (frontmatter, nested):
        for key in keys:
            if mapping.get(key) is not None:
                return mapping[key]
    return None


def _metadata_state(frontmatter: Mapping[str, Any]) -> str:
    if not frontmatter:
        return "none"
    identity = _first(frontmatter, "id", "memory_id")
    classification = _first(
        frontmatter, "document_type", "node_type", "memory_type", "kind", "type"
    )
    return "complete" if identity and classification else "partial"


def _valid_iso8601(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, (dt.date, dt.datetime)):
        return True
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        dt.datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        try:
            dt.date.fromisoformat(value.strip())
        except ValueError:
            return False
    return True


def _validate_explicit_metadata(
    path: str, frontmatter: Mapping[str, Any]
) -> List[CorpusFinding]:
    findings: List[CorpusFinding] = []
    explicit_id = _first(frontmatter, "id", "memory_id")
    if explicit_id is not None and not str(explicit_id).strip():
        findings.append(CorpusFinding("invalid_identity", "error", "Explicit identity is empty.", path))
    drawer = _first(frontmatter, "drawer")
    if drawer is not None and str(drawer).strip() not in DRAWERS:
        findings.append(
            CorpusFinding(
                "invalid_drawer",
                "error",
                f"Explicit drawer {drawer!r} is outside the canonical three-drawer contract.",
                path,
                "Use facts, preferences, or insights.",
            )
        )
    scope = frontmatter.get("scope")
    if scope is not None and not isinstance(scope, (str, Mapping)):
        findings.append(
            CorpusFinding("invalid_scope", "error", "Explicit scope must be a string or mapping.", path)
        )
    for key in ("active_connections", "connections"):
        value = _first(frontmatter, key)
        if value is not None and not isinstance(value, list):
            findings.append(
                CorpusFinding(
                    "invalid_relations",
                    "error",
                    f"Explicit {key} must be a list.",
                    path,
                )
            )
    related_to = _first(frontmatter, "related_to")
    if related_to is not None and not isinstance(related_to, (str, list)):
        findings.append(
            CorpusFinding(
                "invalid_relations",
                "error",
                "Explicit related_to must be a string or list.",
                path,
            )
        )
    for key in (
        "observed_at",
        "valid_from",
        "valid_until",
        "recorded_at",
        "created_at",
        "date",
    ):
        value = _first(frontmatter, key)
        if value is not None and not _valid_iso8601(value):
            findings.append(
                CorpusFinding(
                    "invalid_date",
                    "error",
                    f"Explicit {key} value is not ISO-8601: {value!r}.",
                    path,
                )
            )
    return findings


def _manifest_hash_matches(entry: Mapping[str, Any], metadata: CanonicalMetadata) -> bool:
    file_hash = entry.get("file_hash")
    if file_hash:
        return file_hash == metadata.source.document_hash
    content_hash = entry.get("content_hash")
    return not content_hash or content_hash == metadata.source.content_hash


def _relation_aliases(
    documents: Sequence[Tuple[SourceDiagnostic, CanonicalMetadata]],
) -> Dict[str, set[str]]:
    aliases: Dict[str, set[str]] = {}
    for diagnostic, metadata in documents:
        path_without_suffix = str(Path(diagnostic.path).with_suffix("")).replace(os.sep, "/")
        values = {
            metadata.identity.id,
            metadata.source.document_id,
            path_without_suffix,
            Path(path_without_suffix).name,
        }
        for value in values:
            aliases.setdefault(value, set()).add(metadata.identity.id)
    return aliases


def run_corpus_doctor(configuration: ResolvedConfiguration) -> CorpusDoctorReport:
    """Audit configured sources and derived index state without writing anything."""
    report = CorpusDoctorReport(
        project_root=configuration.project_root,
        storage_dir=configuration.storage_dir,
        index_dir=configuration.index_dir,
    )
    source_paths, discovery_findings = _configured_sources(configuration)
    report.findings.extend(discovery_findings)
    before_hashes: Dict[str, str] = {}
    documents: List[Tuple[SourceDiagnostic, CanonicalMetadata]] = []
    explicit_ids: Dict[str, List[str]] = {}
    inferred_counts: Dict[str, int] = {}

    manifest_path = Path(configuration.index_dir) / "identity_manifest.json"
    evidence_path = Path(configuration.index_dir) / "evidence.json"
    manifest_raw, manifest_error = _load_json(manifest_path)
    evidence_raw, evidence_error = _load_json(evidence_path)
    if manifest_error:
        report.findings.append(manifest_error)
    if evidence_error:
        report.findings.append(evidence_error)
    manifest: Mapping[str, Any] = manifest_raw if isinstance(manifest_raw, Mapping) else {}
    if manifest_raw is not None and not isinstance(manifest_raw, Mapping):
        report.findings.append(
            CorpusFinding(
                "invalid_identity_manifest",
                "error",
                "Identity manifest root must be a mapping.",
                str(manifest_path),
            )
        )

    for path in source_paths:
        source_path = _relative(path, _identity_base(path, configuration))
        try:
            raw_bytes = path.read_bytes()
            before_hashes[str(path)] = hashlib.sha256(raw_bytes).hexdigest()
            raw_text = raw_bytes.decode("utf-8")
        except (OSError, UnicodeError) as exc:
            report.findings.append(
                CorpusFinding("unreadable_source", "error", f"Source cannot be read as UTF-8: {exc}", source_path)
            )
            continue
        try:
            frontmatter, _body = split_source(raw_text, path=path)
            manifest_entry = manifest.get(source_path)
            persistent_id = manifest_entry.get("id") if isinstance(manifest_entry, Mapping) else None
            persistent_doc_id = manifest_entry.get("document_id") if isinstance(manifest_entry, Mapping) else None
            metadata = parse_and_normalize(
                raw_text,
                str(path),
                str(_identity_base(path, configuration)),
                persistent_id=persistent_id,
                persistent_doc_id=persistent_doc_id,
            )
        except ValueError as exc:
            report.findings.append(
                CorpusFinding(
                    "malformed_frontmatter",
                    "error",
                    str(exc),
                    source_path,
                    "Correct the YAML frontmatter and run `tessera index` again.",
                )
            )
            continue

        report.findings.extend(_validate_explicit_metadata(source_path, frontmatter))
        inferred_fields = tuple(
            sorted(
                key
                for key, origin in metadata.metadata_origin.items()
                if origin in {"default", "inferred"}
            )
        )
        for key in inferred_fields:
            inferred_counts[key] = inferred_counts.get(key, 0) + 1
        diagnostic = SourceDiagnostic(
            path=source_path,
            format=metadata.source.format,
            metadata_state=_metadata_state(frontmatter),
            memory_id=metadata.identity.id,
            id_origin=metadata.metadata_origin.get("id"),
            inferred_fields=inferred_fields,
        )
        report.sources.append(diagnostic)
        documents.append((diagnostic, metadata))
        if metadata.metadata_origin.get("id") == "explicit":
            explicit_ids.setdefault(metadata.identity.id, []).append(source_path)

        if not isinstance(manifest_entry, Mapping):
            if isinstance(manifest_raw, Mapping):
                report.findings.append(
                    CorpusFinding(
                        "source_not_indexed",
                        "warning",
                        "Source is absent from the derived identity manifest.",
                        source_path,
                        "Run `tessera index` to refresh derived state.",
                    )
                )
        else:
            if manifest_entry.get("id") != metadata.identity.id:
                report.findings.append(
                    CorpusFinding(
                        "stale_identity",
                        "warning",
                        "Derived identity does not match the current source identity.",
                        source_path,
                        "Run `tessera index` to refresh derived state.",
                    )
                )
            if not _manifest_hash_matches(manifest_entry, metadata):
                report.findings.append(
                    CorpusFinding(
                        "stale_source_version",
                        "warning",
                        "Derived identity manifest points to an older source version.",
                        source_path,
                        "Run `tessera index` to refresh derived state.",
                    )
                )

    current_paths = {
        _relative(path, _identity_base(path, configuration)) for path in source_paths
    }
    for stale_path in sorted(set(manifest) - current_paths):
        report.findings.append(
            CorpusFinding(
                "stale_manifest_entry",
                "warning",
                "Derived identity manifest references a source that is no longer selected.",
                stale_path,
                "Run `tessera index` to retract stale derived state.",
            )
        )

    for memory_id, paths in sorted(explicit_ids.items()):
        if len(paths) > 1:
            report.findings.append(
                CorpusFinding(
                    "duplicate_explicit_identity",
                    "error",
                    f"Explicit identity {memory_id!r} is declared by multiple sources: {', '.join(sorted(paths))}.",
                )
            )
    manifest_ids: Dict[str, List[str]] = {}
    for manifest_source, entry in manifest.items():
        if isinstance(entry, Mapping) and entry.get("id"):
            manifest_ids.setdefault(str(entry["id"]), []).append(str(manifest_source))
    for memory_id, paths in sorted(manifest_ids.items()):
        if len(paths) > 1:
            report.findings.append(
                CorpusFinding(
                    "duplicate_manifest_identity",
                    "error",
                    f"Derived manifest identity {memory_id!r} maps to multiple sources: {', '.join(sorted(paths))}.",
                )
            )

    aliases = _relation_aliases(documents)
    relation_count = resolved_relations = broken_relations = ambiguous_relations = 0
    for diagnostic, metadata in documents:
        for relation in metadata.relations:
            relation_count += 1
            targets = aliases.get(relation.target, set())
            if len(targets) == 1:
                resolved_relations += 1
            elif len(targets) > 1:
                ambiguous_relations += 1
                report.findings.append(
                    CorpusFinding(
                        "ambiguous_relation",
                        "warning",
                        f"Relation target {relation.target!r} resolves to multiple source identities.",
                        diagnostic.path,
                    )
                )
            else:
                broken_relations += 1
                report.findings.append(
                    CorpusFinding(
                        "broken_relation",
                        "warning",
                        f"Relation target {relation.target!r} is not present in the configured corpus.",
                        diagnostic.path,
                    )
                )

    evidence_records: Iterable[Any] = ()
    if isinstance(evidence_raw, Mapping):
        raw_records = evidence_raw.get("records", [])
        if isinstance(raw_records, list):
            evidence_records = raw_records
        else:
            report.findings.append(
                CorpusFinding(
                    "invalid_evidence_ledger",
                    "error",
                    "Evidence ledger records must be a list.",
                    str(evidence_path),
                )
            )
    elif evidence_raw is not None:
        report.findings.append(
            CorpusFinding(
                "invalid_evidence_ledger",
                "error",
                "Evidence ledger root must be a mapping.",
                str(evidence_path),
            )
        )
    metadata_by_path = {metadata.source.path: metadata for _item, metadata in documents}
    evidence_count = stale_evidence = 0
    for record in evidence_records:
        evidence_count += 1
        if not isinstance(record, Mapping) or not isinstance(record.get("source"), Mapping):
            stale_evidence += 1
            report.findings.append(
                CorpusFinding(
                    "invalid_evidence_record",
                    "error",
                    "Evidence record is missing its source mapping.",
                    str(evidence_path),
                )
            )
            continue
        source = record["source"]
        source_path = str(source.get("path") or "")
        metadata = metadata_by_path.get(source_path)
        if metadata is None:
            stale_evidence += 1
            report.findings.append(
                CorpusFinding(
                    "stale_evidence",
                    "warning",
                    "Evidence references a source that is no longer selected.",
                    source_path,
                )
            )
        elif (
            source.get("document_hash") != metadata.source.document_hash
            or source.get("content_hash") != metadata.source.content_hash
        ):
            stale_evidence += 1
            report.findings.append(
                CorpusFinding("stale_evidence", "warning", "Evidence points to an older source version.", source_path)
            )

    if manifest_raw is None and manifest_error is None:
        report.findings.append(
            CorpusFinding(
                "index_missing",
                "warning",
                "No derived identity manifest exists for the configured corpus.",
                str(manifest_path),
                "Run `tessera index` to create rebuildable derived state.",
            )
        )
    if isinstance(manifest_raw, Mapping) and evidence_raw is None and evidence_error is None:
        report.findings.append(
            CorpusFinding(
                "evidence_ledger_missing",
                "warning",
                "The identity manifest exists but the derived evidence ledger is missing.",
                str(evidence_path),
                "Run `tessera index` to rebuild derived evidence state.",
            )
        )

    after_hashes: Dict[str, str] = {}
    for raw_path in sorted(before_hashes):
        path = Path(raw_path)
        try:
            after_hashes[raw_path] = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError:
            after_hashes[raw_path] = "missing"
    report.source_files_modified = sum(
        after_hashes.get(path) != digest for path, digest in before_hashes.items()
    )
    if report.source_files_modified:
        report.findings.append(
            CorpusFinding(
                "source_mutation_detected",
                "error",
                f"{report.source_files_modified} source file(s) changed during the read-only audit.",
            )
        )

    report.sources.sort(key=lambda item: item.path)
    report.findings.sort(
        key=lambda item: (
            _SEVERITY_ORDER.get(item.severity, 9),
            item.path or "",
            item.code,
            item.message,
        )
    )
    metadata_states = {"complete": 0, "partial": 0, "none": 0}
    for item in report.sources:
        metadata_states[item.metadata_state] += 1
    report.counts = {
        "sources_selected": len(source_paths),
        "sources_parsed": len(report.sources),
        "metadata_complete": metadata_states["complete"],
        "metadata_partial": metadata_states["partial"],
        "metadata_none": metadata_states["none"],
        "explicit_identities": sum(item.id_origin == "explicit" for item in report.sources),
        "inferred_identities": sum(item.id_origin != "explicit" for item in report.sources),
        "inferred_metadata_fields": sum(inferred_counts.values()),
        "relations": relation_count,
        "relations_resolved": resolved_relations,
        "relations_broken": broken_relations,
        "relations_ambiguous": ambiguous_relations,
        "manifest_entries": len(manifest),
        "evidence_records": evidence_count,
        "stale_evidence_records": stale_evidence,
        "errors": report.errors,
        "warnings": report.warnings,
    }
    report.status = "error" if report.errors else "warning" if report.warnings else "healthy"
    return report


def print_corpus_doctor_plain(report: CorpusDoctorReport, *, verbose: bool = False) -> None:
    counts = report.counts
    print(f"tessera corpus doctor — {report.status}")
    print(f"sources: selected={counts['sources_selected']} parsed={counts['sources_parsed']}")
    print(
        "metadata: "
        f"complete={counts['metadata_complete']} partial={counts['metadata_partial']} "
        f"none={counts['metadata_none']} inferred_fields={counts['inferred_metadata_fields']}"
    )
    print(
        "relations: "
        f"total={counts['relations']} resolved={counts['relations_resolved']} "
        f"broken={counts['relations_broken']} ambiguous={counts['relations_ambiguous']}"
    )
    print(
        "derived index: "
        f"manifest={counts['manifest_entries']} evidence={counts['evidence_records']} "
        f"stale_evidence={counts['stale_evidence_records']}"
    )
    print(f"source files modified: {report.source_files_modified}")
    print(f"findings: errors={report.errors} warnings={report.warnings}")
    for finding in report.findings:
        location = f" {finding.path}:" if finding.path else ""
        print(f"[{finding.severity.upper()}]{location} {finding.code} — {finding.message}")
        if finding.hint:
            print(f"  fix: {finding.hint}")
    if verbose:
        for source in report.sources:
            inferred = ",".join(source.inferred_fields) or "none"
            print(
                f"[SOURCE] {source.path} metadata={source.metadata_state} "
                f"id={source.memory_id or '-'} id_origin={source.id_origin or '-'} inferred={inferred}"
            )
