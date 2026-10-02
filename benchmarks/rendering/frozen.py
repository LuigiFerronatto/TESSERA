"""Closed, label-isolated capture format for already retrieved Engine evidence."""

import hashlib
import json
import math
import re
from typing import Any, Dict, Mapping, Sequence


CAPTURE_VERSION = "tessera-renderer-capture/1"
FORBIDDEN_KEYS = {
    "answer", "answers", "expected_answer", "ground_truth", "ground_truth_session_ids",
    "answer_session_ids", "has_answer", "is_relevant", "is_abstention", "label",
    "labels", "evidence_labels", "reference_answer", "reference_answers",
}
HIT_FIELDS = {
    "id", "score", "body", "relevant_evidence", "related_ids", "provenance", "evidence",
}
RECORD_FIELDS = {
    "schema_version", "evidence_id", "memory_id", "source", "span", "fingerprint",
    "extraction",
}
SOURCE_FIELDS = {
    "document_id", "path", "document_hash", "content_hash", "format",
}


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def reject_labels(value: Any, path: str = "input") -> None:
    """Reject evaluator-owned fields, including inside discarded Engine metadata.

This is a field boundary, not a classifier for arbitrary source prose. Callers
must use the trusted, label-free corpus adapter; never pass evaluator results.
"""
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError(f"{path}: object keys must be strings")
            if key.lower() in FORBIDDEN_KEYS:
                raise ValueError(f"{path}.{key}: evaluator labels are forbidden")
            reject_labels(item, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            reject_labels(item, f"{path}[{index}]")


def _object(value: Any, fields: set, path: str) -> None:
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError(f"{path}: expected exactly {sorted(fields)}")


def _string(value: Any, path: str, empty: bool = False) -> None:
    if not isinstance(value, str) or (not empty and not value.strip()):
        raise ValueError(f"{path}: expected {'a' if empty else 'a non-empty'} string")


def _sha(value: Any, size: int, path: str) -> None:
    if not isinstance(value, str) or not re.fullmatch(f"[0-9a-f]{{{size}}}", value):
        raise ValueError(f"{path}: expected a lowercase {size}-character SHA")


def _evidence(record: Any, memory_id: str, path: str) -> None:
    if record is None:
        return
    _object(record, RECORD_FIELDS, path)
    if type(record["schema_version"]) is not int or record["schema_version"] != 1:
        raise ValueError(f"{path}: unsupported evidence schema")
    for field in ("evidence_id", "memory_id"):
        _string(record[field], f"{path}.{field}")
    if record["memory_id"] != memory_id:
        raise ValueError(f"{path}: memory identity mismatch")
    _sha(record["fingerprint"], 64, f"{path}.fingerprint")
    _object(record["source"], SOURCE_FIELDS, f"{path}.source")
    for field in SOURCE_FIELDS:
        _string(record["source"][field], f"{path}.source.{field}")
    for field in ("document_hash", "content_hash"):
        _sha(record["source"][field], 64, f"{path}.source.{field}")
    _object(record["span"], {"start_line", "end_line"}, f"{path}.span")
    start, end = record["span"]["start_line"], record["span"]["end_line"]
    if not (start is None and end is None):
        if (type(start) is not int or type(end) is not int or start < 1 or end < start):
            raise ValueError(f"{path}.span: expected ordered positive lines or both null")
    _object(record["extraction"], {"method", "inferred"}, f"{path}.extraction")
    _string(record["extraction"]["method"], f"{path}.extraction.method")
    if type(record["extraction"]["inferred"]) is not bool:
        raise ValueError(f"{path}.extraction.inferred: expected boolean")


def validate_capture(capture: Any) -> None:
    reject_labels(capture)
    _object(capture, {"schema_version", "source", "queries", "capture_sha256"}, "capture")
    if capture["schema_version"] != CAPTURE_VERSION:
        raise ValueError("unsupported capture version")
    source = capture["source"]
    _object(source, {"tessera_commit", "retrieval_contract_commit",
                     "retrieval_configuration_sha256"}, "source")
    _sha(source["tessera_commit"], 40, "source.tessera_commit")
    _sha(source["retrieval_contract_commit"], 40, "source.retrieval_contract_commit")
    _sha(source["retrieval_configuration_sha256"], 64, "source.retrieval_configuration_sha256")
    if not isinstance(capture["queries"], list) or not capture["queries"]:
        raise ValueError("queries must be a non-empty list")
    query_ids = set()
    for query in capture["queries"]:
        _object(query, {"query_id", "query", "hits"}, "query")
        _string(query["query_id"], "query_id")
        _string(query["query"], "query")
        if query["query_id"] in query_ids:
            raise ValueError("duplicate query ID")
        query_ids.add(query["query_id"])
        if not isinstance(query["hits"], list):
            raise ValueError("hits must be a list")
        memory_ids = set()
        for hit in query["hits"]:
            _object(hit, HIT_FIELDS, "hit")
            _string(hit["id"], "hit.id")
            if hit["id"] in memory_ids:
                raise ValueError("duplicate memory ID within query")
            memory_ids.add(hit["id"])
            if (type(hit["score"]) not in (int, float)
                    or not math.isfinite(hit["score"])):
                raise ValueError("score must be finite and numeric")
            _string(hit["body"], "hit.body", empty=True)
            span = hit["relevant_evidence"]
            if span is not None:
                _string(span, "hit.relevant_evidence")
                if span not in hit["body"]:
                    raise ValueError("selected evidence must occur verbatim in its own body")
            related = hit["related_ids"]
            if not isinstance(related, list):
                raise ValueError("related_ids must be a list")
            for related_id in related:
                _string(related_id, "related_id")
            if len(related) != len(set(related)):
                raise ValueError("duplicate related ID")
            for field in ("provenance", "evidence"):
                _evidence(hit[field], hit["id"], f"hit.{field}")
            if span is None and hit["evidence"] is not None:
                raise ValueError("query-specific evidence requires a selected span")
    _sha(capture["capture_sha256"], 64, "capture_sha256")
    payload = {key: value for key, value in capture.items() if key != "capture_sha256"}
    if capture["capture_sha256"] != digest(payload):
        raise ValueError("capture checksum mismatch; evidence must remain frozen")


def capture_evidence(queries: Sequence[Mapping[str, Any]], *, tessera_commit: str,
                     retrieval_contract_commit: str,
                     retrieval_configuration: Mapping[str, Any]) -> Dict[str, Any]:
    """Snapshot raw Engine hits once without re-ranking, inference, or source I/O.

Caller supplies ``query_id``, ``query``, and ``hits`` only for each query. The
projection deliberately excludes frontmatter, paths, type, and score_explain.
IDs, order, numeric scores, full bodies and selected spans remain unchanged.
"""
    reject_labels(queries)
    reject_labels(retrieval_configuration)
    if not isinstance(retrieval_configuration, Mapping):
        raise ValueError("retrieval_configuration must be an object")
    projected = []
    for query in queries:
        _object(query, {"query_id", "query", "hits"}, "query")
        hits = []
        if not isinstance(query["hits"], list):
            raise ValueError("hits must be a list")
        for hit in query["hits"]:
            if not isinstance(hit, Mapping):
                raise ValueError("hit must be an object")
            if not {"id", "score", "body"} <= set(hit):
                raise ValueError("hit requires id, score and body")
            hits.append({
                "id": hit["id"], "score": hit["score"], "body": hit["body"],
                "relevant_evidence": hit.get("relevant_evidence"),
                "related_ids": hit.get("related_ids", []),
                "provenance": hit.get("provenance"), "evidence": hit.get("evidence"),
            })
        projected.append({"query_id": query["query_id"], "query": query["query"], "hits": hits})
    capture = {
        "schema_version": CAPTURE_VERSION,
        "source": {"tessera_commit": tessera_commit,
                   "retrieval_contract_commit": retrieval_contract_commit,
                   "retrieval_configuration_sha256": digest(retrieval_configuration)},
        "queries": projected,
    }
    # Copy all nested values so later caller mutations cannot modify the snapshot.
    capture = json.loads(canonical_json(capture))
    capture["capture_sha256"] = digest(capture)
    validate_capture(capture)
    return capture
