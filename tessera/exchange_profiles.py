"""Bounded portable views over existing canonical records (#204).

Independent implementation from TESSERA contracts. No competitor source/schema
is used. Profiles do not create another canonical model or access-control policy.
"""
from __future__ import annotations

import csv
from datetime import datetime
import io
import json
import re
from urllib.parse import quote

from .canonical import compute_sha256, effective_tags
from .okf import (
    ExchangeError, ExchangeRecord, MAX_BUNDLE_BYTES, MAX_ENTRIES,
    _canonical_payload, _dump, _json_value, _restore, _safe_path, _link_path, LINK, export_records,
)

JSON_PROFILE = "tessera-canonical-json-v1"
JSON_FILENAME = "memories.json"
PROFILES = {"okf", "canonical-json", "markdown", "obsidian", "csv"}
TIME_FIELDS = {"observed_at", "recorded_at", "valid_from", "valid_until"}
FILTERS = {"ids", "exclude_ids", "private_ids", "drawers", "scope_levels", "scope_paths", "source_paths",
           "time_field", "time_from", "time_to"}


def _instant(value):
    if not isinstance(value, str) or "T" not in value:
        raise ExchangeError("Time filters require ISO datetimes with explicit offsets")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ExchangeError("Invalid time filter value") from exc
    if result.utcoffset() is None:
        raise ExchangeError("Time filters require explicit offsets")
    return result


def select_records(records, selection=None):
    """Exact, caller-selected filters; never infer privacy or cross-project reach."""
    selection = dict(selection or {})
    if set(selection) - FILTERS:
        raise ExchangeError("Unknown selection field")
    for key in FILTERS - {"time_field", "time_from", "time_to"}:
        if key in selection:
            value = selection[key]
            if not isinstance(value, list) or not all(isinstance(v, str) and v for v in value):
                raise ExchangeError("Selection lists require non-empty strings")
            selection[key] = sorted(set(value))
    if any(k in selection for k in ("time_from", "time_to")):
        if selection.get("time_field") not in TIME_FIELDS:
            raise ExchangeError("Time ranges require an explicit canonical time_field")
    elif "time_field" in selection:
        raise ExchangeError("time_field requires time_from or time_to")
    lower = _instant(selection["time_from"]) if "time_from" in selection else None
    upper = _instant(selection["time_to"]) if "time_to" in selection else None
    if lower and upper and lower >= upper:
        raise ExchangeError("Time range must have increasing bounds")
    selected, excluded = [], []
    ids = set()
    for record in sorted(records, key=lambda r: r.canonical.identity.id):
        c = record.canonical
        if c.identity.id in ids:
            raise ExchangeError("Duplicate canonical identity in selection")
        ids.add(c.identity.id)
        reasons = []
        if c.identity.id in selection.get("private_ids", []):
            reasons.append("caller_declared_private")
        if c.identity.id in selection.get("exclude_ids", []):
            reasons.append("explicit_exclusion")
        dimensions = {"ids": c.identity.id, "drawers": c.classification.drawer,
                      "scope_levels": c.scope.level, "scope_paths": c.scope.path, "source_paths": c.source.path}
        for key, value in dimensions.items():
            if key in selection and value not in selection[key]:
                reasons.append("filter:" + key)
        if lower or upper:
            try:
                at = _instant(getattr(c.temporal, selection["time_field"]))
                if (lower and at < lower) or (upper and at >= upper):
                    reasons.append("filter:time")
            except ExchangeError:
                reasons.append("time_missing_or_ambiguous")
        if reasons:
            excluded.append({"id": c.identity.id, "source_path": c.source.path, "reasons": reasons})
        else:
            selected.append(record)
    unknown = {key: sorted(set(selection.get(key, [])) - ids) for key in ("ids", "exclude_ids", "private_ids")}
    if any(unknown.values()):
        raise ExchangeError("Unknown requested/excluded/private identity; review the selection")
    return selected, {
        "identity_warnings": [{"id": r.canonical.identity.id, "reason": "source_path_inferred_identity; no Engine identity manifest consulted"}
                              for r in selected if r.canonical.metadata_origin.get("id") == "inferred"],
        "selection": selection, "records_seen": len(records), "records_selected": len(selected),
        "excluded": excluded, "declared_private_excluded": sum("caller_declared_private" in item["reasons"] for item in excluded),
        "privacy_policy": "caller-declared IDs only; no automatic #257 exposure decision",
        "project_boundary": "explicit input source root; no project discovery or corpus merge",
        "time_range": "inclusive lower, exclusive upper; missing/ambiguous values excluded",
    }


def _record_payload(record):
    canonical = _canonical_payload(record.canonical)
    _restore(canonical)
    if not isinstance(record.body, str) or canonical["source"]["content_hash"] != compute_sha256(record.body):
        raise ExchangeError("Record body differs from canonical hash")
    _safe_path(record.path)
    return {"path": record.path, "canonical": canonical, "body": record.body,
            "external_frontmatter": record.external_frontmatter, "extension_extra": record.extension_extra or {}}


def _published_manifest(manifest):
    counts = {}
    for item in manifest.get("excluded", []):
        for reason in item["reasons"]:
            counts[reason] = counts.get(reason, 0) + 1
    return {"profile": manifest["profile"], "schema_version": 1,
            "records_seen": manifest["records_seen"], "records_selected": manifest["records_selected"],
            "excluded_by_reason": counts, "declared_private_excluded": manifest["declared_private_excluded"],
            "selection_fields": sorted(manifest["selection"]),
            "privacy_policy": "record exclusion only; no transitive content redaction or automatic exposure decision"}


def canonical_json(records, manifest):
    paths = [r.path.casefold() for r in records]
    if len(set(paths)) != len(paths):
        raise ExchangeError("Duplicate canonical JSON source path")
    payload = {"profile": JSON_PROFILE, "schema_version": 1,
               "records": [_record_payload(r) for r in sorted(records, key=lambda r: r.canonical.identity.id)],
               "manifest": _published_manifest(manifest)}
    _json_value(payload)
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"


def parse_canonical_json(text):
    """Decode only this versioned profile, preserving the existing canonical data."""
    if not isinstance(text, str) or len(text.encode("utf-8")) > MAX_BUNDLE_BYTES:
        raise ExchangeError("Canonical JSON exceeds the supported size")
    def pairs(items):
        value = {}
        for key, item in items:
            if key in value:
                raise ExchangeError("Duplicate JSON key")
            value[key] = item
        return value
    def invalid_constant(value):
        raise ExchangeError("Non-finite JSON number")
    try:
        payload = json.loads(text, object_pairs_hook=pairs, parse_constant=invalid_constant)
    except (ValueError, RecursionError) as exc:
        raise ExchangeError("Invalid canonical JSON: " + str(exc)) from exc
    _json_value(payload)
    if not isinstance(payload, dict) or set(payload) != {"profile", "schema_version", "records", "manifest"}:
        raise ExchangeError("Invalid canonical JSON envelope")
    if payload["profile"] != JSON_PROFILE or type(payload["schema_version"]) is not int or payload["schema_version"] != 1:
        raise ExchangeError("Unsupported canonical JSON profile/version")
    if not isinstance(payload["records"], list) or len(payload["records"]) > MAX_ENTRIES or not isinstance(payload["manifest"], dict):
        raise ExchangeError("Invalid canonical JSON records/manifest")
    records, identities, paths = [], set(), set()
    for item in payload["records"]:
        if not isinstance(item, dict) or set(item) != {"path", "canonical", "body", "external_frontmatter", "extension_extra"}:
            raise ExchangeError("Invalid canonical JSON record")
        canonical = _restore(item["canonical"])
        path = _safe_path(item["path"])
        if not path.endswith(".md") or not isinstance(item["body"], str):
            raise ExchangeError("Canonical JSON requires a Markdown source path and string body")
        if canonical.source.content_hash != compute_sha256(item["body"]):
            raise ExchangeError("Canonical JSON body hash mismatch")
        if canonical.identity.id in identities or path.casefold() in paths:
            raise ExchangeError("Duplicate canonical JSON identity/path")
        if (item["external_frontmatter"] is not None and not isinstance(item["external_frontmatter"], dict)) or not isinstance(item["extension_extra"], dict):
            raise ExchangeError("Invalid exchange extensions")
        identities.add(canonical.identity.id)
        paths.add(path.casefold())
        records.append(ExchangeRecord(canonical, item["body"], path, item["external_frontmatter"], item["extension_extra"]))
    return records, payload["manifest"]


def _plain_label(value):
    return str(value).replace("\n", " ").replace("\r", " ").replace("[", "(").replace("]", ")").replace("|", "/")


def _escape_wiki_metadata(value):
    if isinstance(value, str):
        return value.replace("[[", "\\[\\[").replace("]]", "\\]\\]")
    if isinstance(value, list):
        return [_escape_wiki_metadata(v) for v in value]
    if isinstance(value, dict):
        return {k: _escape_wiki_metadata(v) for k, v in value.items()}
    return value


def _body_links(record, by_id, paths, obsidian):
    by_path = {r.path: identity for identity, r in by_id.items()}
    count = 0
    def replace(match):
        nonlocal count
        target = match.group(1)
        resolved = _link_path(record.path, target)
        if resolved is None:
            return match.group(0)
        count += 1
        label = _plain_label(match.group(0)[1:].split("](", 1)[0])
        identity = by_path.get(resolved)
        if identity not in paths:
            return label + " (not included in this export)"
        fragment = ("#" + quote(target.split("#", 1)[1], safe="-._~%")) if "#" in target else ""
        if obsidian:
            return "[[" + paths[identity][:-3] + fragment + "|" + label + "]]"
        return "[" + label + "](" + quote(paths[identity].split("/", 1)[-1]) + fragment + ")"
    rendered, fence = [], None
    for line in record.body.splitlines(keepends=True):
        marker = re.match(r"^ {0,3}(`{3,}|~{3,})", line)
        if marker:
            token = marker.group(1)
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence):
                fence = None
            rendered.append(line)
        elif fence is not None:
            rendered.append(line)
        else:
            parts = re.split(r"(`+[^`]*`+)", line)
            rendered.append("".join(part if i % 2 else LINK.sub(replace, part) for i, part in enumerate(parts)))
    return "".join(rendered), count


def _human_document(record, by_id, paths, *, obsidian):
    c = record.canonical
    payload = _canonical_payload(c)
    fm = {"id": c.identity.id, "name": c.identity.name, "drawer": c.classification.drawer,
          "kind": c.classification.kind, "scope": payload["scope"], "source": payload["source"],
          "temporal": payload["temporal"], "quality": payload["quality"],
          "relations": payload["relations"], "state_key": c.state_key, "superseded_at": c.superseded_at,
          "utility": c.utility, "tags": effective_tags(c.raw_frontmatter),
          "exchange_profile": "tessera-obsidian-v1" if obsidian else "tessera-human-markdown-v1",
          "canonical_companion": JSON_FILENAME}
    if obsidian:
        fm = _escape_wiki_metadata(fm)
    body, rewrites = _body_links(record, by_id, paths, obsidian)
    if obsidian:
        def wiki(match):
            nonlocal rewrites
            target = match.group(1).split("|", 1)[0].split("#", 1)[0]
            if target in {p[:-3] for p in paths.values()}:
                return match.group(0)
            rewrites += 1
            if target in paths:
                return "[[" + paths[target][:-3] + "|" + _plain_label(by_id[target].canonical.identity.name) + "]]"
            return _plain_label(match.group(1))  # no unresolved/generated wiki edge
        body = re.sub(r"\[\[([^\]\n]+)\]\]", wiki, body)
    lines = [body.rstrip("\n"), "", "## Related memories (export navigation)", ""]
    for rel in c.relations:
        label = _plain_label(by_id[rel.target].canonical.identity.name if rel.target in by_id else rel.target)
        if rel.target in paths:
            link = ("[[" + paths[rel.target][:-3] + "|" + label + "]]") if obsidian else ("[" + label + "](" + quote(paths[rel.target].split("/", 1)[-1]) + ")")
        else:
            link = label + " (not included in this export)"
        lines.append("- " + _plain_label(rel.type) + ": " + link + "; origin: " + _plain_label(rel.origin))
    if not c.relations:
        lines.append("No canonical relations recorded.")
    return _dump(fm, "\n".join(lines) + "\n"), rewrites


def project_records(records, *, profile, selection=None):
    if profile not in PROFILES:
        raise ExchangeError("Unsupported export profile")
    selected, manifest = select_records(records, selection)
    manifest = {**manifest, "profile": profile, "schema_version": 1}
    if profile == "okf":
        result = export_records(selected)
        result["report"]["selection_manifest"] = manifest
        return result
    # Every named view includes the same lossless canonical JSON companion.
    files = {JSON_FILENAME: canonical_json(selected, manifest)}
    lossy = []
    rewrites = escaped = 0
    paths = {r.canonical.identity.id: "memories/" + compute_sha256(r.canonical.identity.id)[:32] + ".md" for r in selected}
    if len(set(paths.values())) != len(paths):
        raise ExchangeError("Stable view filename collision")
    by_id = {r.canonical.identity.id: r for r in selected}
    if profile in {"markdown", "obsidian"}:
        for record in selected:
            text, count = _human_document(record, by_id, paths, obsidian=profile == "obsidian")
            files[paths[record.canonical.identity.id]] = text
            rewrites += count
        lossy = ["raw_frontmatter and producer extensions available in canonical companion", "original body presentation augmented with navigation"]
    elif profile == "csv":
        columns = ["id", "name", "drawer", "kind", "scope_path", "source_path", "observed_at", "valid_from", "valid_until"]
        out = io.StringIO(newline="")
        writer = csv.writer(out, lineterminator="\n")
        writer.writerow(columns)
        for record in selected:
            c = record.canonical
            values = [c.identity.id, c.identity.name, c.classification.drawer, c.classification.kind, c.scope.path,
                      c.source.path, c.temporal.observed_at, c.temporal.valid_from, c.temporal.valid_until]
            row = []
            for value in values:
                value = "" if value is None else str(value)
                if value.lstrip().startswith(("=", "+", "-", "@")) or value.startswith(("\t", "\r")):
                    value = "'" + value
                    escaped += 1
                row.append(value)
            writer.writerow(row)
        files["memories.csv"] = out.getvalue()
        lossy = ["body", "relations", "raw_frontmatter", "quality", "source hashes/span/document ID", "scope level/harness",
                 "recorded_at", "state_key", "superseded_at", "utility", "metadata_origin", "producer extensions", "optional lineage"]
    return {"files": dict(sorted(files.items())), "report": {
        "profile": profile, "schema_version": 1, "records_written": len(selected),
        "selection_manifest": manifest, "view_lossy_fields": lossy, "bundle_lossy_fields": [],
        "canonical_companion": JSON_FILENAME, "derived_fields_omitted": ["temporal.indexed_at"],
        "path_by_id": paths if profile in {"markdown", "obsidian"} else {},
        "obsidian_body_wikilinks_rewritten": rewrites, "csv_formula_cells_escaped": escaped,
        "file_hashes": {p: compute_sha256(t) for p, t in sorted(files.items())},
        "persistence": "NOT_PERFORMED", "semantic_admission": "NOT_PERFORMED", "decision": "ITERATE",
        "encryption_policy": "NOT_INTEGRATED (#256)", "exposure_policy": "NOT_INTEGRATED (#257)"}}
