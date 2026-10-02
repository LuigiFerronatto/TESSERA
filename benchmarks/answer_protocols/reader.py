"""Pinned-reader artifact contracts and synthetic capture; no provider adapter."""

import json
from pathlib import Path
from typing import Any, Dict, List

from .common import (bytes_digest, canonical, decode, digest, exact, integer,
                     read, reject_labels, sha, string, write_new)


REQUEST_VERSION = "tessera-reader-request-draft/1"
CAPTURE_VERSION = "tessera-reader-capture-synthetic/1"
READER_FIELDS = {
    "provider", "model", "model_revision", "endpoint_class", "prompt_version",
    "system_prompt_sha256", "renderer", "renderer_version", "temperature", "top_p",
    "seed", "max_output_tokens", "timeout_seconds", "retry_policy",
    "structured_output_schema", "question_count", "question_ids_sha256",
    "retrieval_artifact_sha256", "environment_fingerprint", "created_at",
    "tokenizer_revision", "message_overhead_policy",
}
OUTPUT_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["answer", "abstained", "citations"],
    "properties": {"answer": {"type": "string"}, "abstained": {"type": "boolean"},
                   "citations": {"type": "array", "uniqueItems": True,
                                 "items": {"type": "string"}}},
}


def draft_configuration() -> Dict[str, Any]:
    return {"schema_version": "tessera-reader-configuration-draft/1", "status": "DRAFT",
            "selection": {key: None for key in sorted(READER_FIELDS)}}


def validate_configuration(config: Any) -> None:
    exact(config, {"schema_version", "status", "selection"}, "reader configuration")
    if config["schema_version"] != "tessera-reader-configuration-draft/1" or config["status"] != "DRAFT":
        raise ValueError("only an unselected draft configuration is supported")
    exact(config["selection"], READER_FIELDS, "reader selection")
    if any(value is not None for value in config["selection"].values()):
        raise ValueError("this preparation runner cannot select a real reader")


def messages(value: Any) -> None:
    if not isinstance(value, list) or len(value) != 2:
        raise ValueError("expected frozen system/user messages")
    for item, role in zip(value, ("system", "user")):
        exact(item, {"role", "content"}, "message")
        if item["role"] != role:
            raise ValueError("unexpected message role/order")
        string(item["content"], "message.content")


def make_request(rendered: Dict[str, Any], *, capture_sha256: str,
                 policy_sha256: str, configuration: Dict[str, Any]) -> Dict[str, Any]:
    """Consume an opaque #28 row unchanged, never retrieve or render evidence.

The caller obtains both expected hashes from a separately verified #28 manifest.
This adapter checks the row hash and shape; it cannot certify the producer or
absence of labels hidden in prose. Quality execution remains blocked.
"""
    reject_labels(rendered)
    exact(rendered, {"query_id", "renderer", "messages", "input_sha256", "metrics"}, "#28 row")
    string(rendered["query_id"], "query_id")
    if rendered["renderer"] not in ("R0", "R1", "R2"):
        raise ValueError("unknown #28 renderer arm")
    if not isinstance(rendered["metrics"], dict):
        raise ValueError("#28 metrics must be an object")
    messages(rendered["messages"])
    sha(rendered["input_sha256"], "input_sha256")
    if digest(rendered["messages"]) != rendered["input_sha256"]:
        raise ValueError("frozen message checksum mismatch")
    sha(capture_sha256, "capture_sha256")
    sha(policy_sha256, "policy_sha256")
    validate_configuration(configuration)
    request = {
        "schema_version": REQUEST_VERSION,
        # No abstention suffix, category or external question ID in the request.
        "question_ref": digest(rendered["query_id"]),
        "frozen_evidence_sha256": capture_sha256, "reader_input_policy_sha256": policy_sha256,
        "renderer": rendered["renderer"], "configuration_sha256": digest(configuration),
        "input_sha256": rendered["input_sha256"],
        "payload": {"messages": rendered["messages"], "response_schema": OUTPUT_SCHEMA},
    }
    request = json.loads(canonical(request))
    request["request_sha256"] = digest(request)
    validate_request(request)
    return request


def validate_request(request: Any) -> None:
    exact(request, {"schema_version", "question_ref", "frozen_evidence_sha256",
                    "reader_input_policy_sha256", "renderer", "configuration_sha256",
                    "input_sha256", "payload", "request_sha256"}, "reader request")
    if request["schema_version"] != REQUEST_VERSION or request["renderer"] not in ("R0", "R1", "R2"):
        raise ValueError("unsupported reader request")
    for key in ("question_ref", "frozen_evidence_sha256", "reader_input_policy_sha256",
                "configuration_sha256", "input_sha256", "request_sha256"):
        sha(request[key], key)
    exact(request["payload"], {"messages", "response_schema"}, "reader payload")
    messages(request["payload"]["messages"])
    reject_labels(request["payload"]["messages"])
    if canonical(request["payload"]["response_schema"]) != canonical(OUTPUT_SCHEMA):
        raise ValueError("unrecognized response schema")
    if digest(request["payload"]["messages"]) != request["input_sha256"]:
        raise ValueError("input checksum mismatch")
    if digest({k: v for k, v in request.items() if k != "request_sha256"}) != request["request_sha256"]:
        raise ValueError("request checksum mismatch")


def validate_output(output: Any) -> None:
    exact(output, {"answer", "abstained", "citations"}, "reader output")
    string(output["answer"], "answer", empty=True)
    if type(output["abstained"]) is not bool:
        raise ValueError("abstained must be boolean")
    if output["abstained"] != (not output["answer"].strip()):
        raise ValueError("abstention requires an empty answer, answer requires text")
    refs = output["citations"]
    if not isinstance(refs, list):
        raise ValueError("citations must be a list")
    for ref in refs:
        string(ref, "citation")
    if len(refs) != len(set(refs)):
        raise ValueError("duplicate citation")


def attempt(number_: int, raw_response: Any, *, provider_error: Any = None) -> Dict[str, Any]:
    """Parse mock response only; finite zero usage is explicitly synthetic."""
    integer(number_, "attempt")
    if provider_error is not None:
        string(provider_error, "provider error")
        if raw_response is not None:
            raise ValueError("provider failure cannot contain a successful response")
        status, parsed, raw_hash = "provider_failure", None, None
    else:
        string(raw_response, "raw response", empty=True)
        raw_hash = bytes_digest(raw_response.encode("utf-8"))
        try:
            parsed = decode(raw_response)
            validate_output(parsed)
            status = "ok"
        except (ValueError, TypeError):
            parsed, status = None, "parse_failure"
    return {"attempt": number_, "status": status, "raw_response": raw_response,
            "raw_response_sha256": raw_hash, "output": parsed, "provider_error": provider_error,
            "usage": {"accounting": "synthetic_not_measured", "latency_ms": 0,
                      "input_tokens": 0, "output_tokens": 0, "cost_usd": 0}}


def validate_capture(capture: Any) -> None:
    exact(capture, {"schema_version", "execution_mode", "request", "attempts", "capture_sha256"}, "capture")
    if capture["schema_version"] != CAPTURE_VERSION or capture["execution_mode"] != "SYNTHETIC_ONLY":
        raise ValueError("real execution is not implemented or authorized")
    validate_request(capture["request"])
    rows = capture["attempts"]
    if not isinstance(rows, list) or not 1 <= len(rows) <= 3:
        raise ValueError("synthetic capture requires one to three preserved attempts")
    for i, row in enumerate(rows, 1):
        exact(row, {"attempt", "status", "raw_response", "raw_response_sha256", "output", "provider_error", "usage"}, "attempt")
        integer(row["attempt"], "attempt")
        if row["attempt"] != i:
            raise ValueError("missing, duplicate or reordered attempt")
        expected = attempt(i, row["raw_response"], provider_error=row["provider_error"])
        if canonical(row) != canonical(expected):
            raise ValueError("attempt hash, parse, or accounting mismatch")
        if row["status"] == "ok" and i != len(rows):
            raise ValueError("cannot silently replace successful output")
    sha(capture["capture_sha256"], "capture_sha256")
    if digest({k: v for k, v in capture.items() if k != "capture_sha256"}) != capture["capture_sha256"]:
        raise ValueError("capture checksum mismatch")


def capture_synthetic(request: Dict[str, Any], attempts: List[Dict[str, Any]]) -> Dict[str, Any]:
    capture = json.loads(canonical({"schema_version": CAPTURE_VERSION,
                                  "execution_mode": "SYNTHETIC_ONLY",
                                  "request": request, "attempts": attempts}))
    capture["capture_sha256"] = digest(capture)
    validate_capture(capture)
    return capture


def persist_capture(destination: Path, capture: Dict[str, Any]) -> None:
    validate_capture(capture)
    destination.mkdir(parents=True, exist_ok=False, mode=0o700)
    write_new(destination / "request.json", capture["request"])
    for row in capture["attempts"]:
        write_new(destination / f"attempt-{row['attempt']:03d}.json", row)
    write_new(destination / "capture.json", capture)
    # Completion is written last. An interrupted artifact cannot be scored.
    write_new(destination / "complete.json", {"capture_sha256": capture["capture_sha256"]})


def load_capture(destination: Path) -> Dict[str, Any]:
    capture = read(destination / "capture.json")
    validate_capture(capture)
    if read(destination / "complete.json") != {"capture_sha256": capture["capture_sha256"]}:
        raise ValueError("missing or mismatched persistence receipt")
    if canonical(read(destination / "request.json")) != canonical(capture["request"]):
        raise ValueError("persisted request mismatch")
    expected = {"capture.json", "request.json", "complete.json"}
    for row in capture["attempts"]:
        name = f"attempt-{row['attempt']:03d}.json"
        expected.add(name)
        if canonical(read(destination / name)) != canonical(row):
            raise ValueError("persisted attempt mismatch")
    if {p.name for p in destination.iterdir()} != expected:
        raise ValueError("untracked attempt or file in capture")
    return capture


def run_scripted(request: Dict[str, Any], script: List[Dict[str, Any]], destination: Path) -> Dict[str, Any]:
    """Exercise write-before-inference ordering with literal local mock responses.

No callables, model adapters, credentials or network clients are accepted.
A failed/incomplete directory is retained, never overwritten or auto-resumed.
"""
    validate_request(request)
    if not isinstance(script, list) or not 1 <= len(script) <= 3:
        raise ValueError("one to three local scripted attempts required")
    for item in script:
        exact(item, {"raw_response", "provider_error"}, "scripted attempt")
    destination.mkdir(parents=True, exist_ok=False, mode=0o700)
    write_new(destination / "request.json", request)
    rows = []
    for index, item in enumerate(script, 1):
        row = attempt(index, item["raw_response"], provider_error=item["provider_error"])
        rows.append(row)
        write_new(destination / f"attempt-{index:03d}.json", row)
        if row["status"] == "ok":
            if index != len(script):
                raise ValueError("script may not replace a successful response")
            break
    capture = capture_synthetic(request, rows)
    write_new(destination / "capture.json", capture)
    write_new(destination / "complete.json", {"capture_sha256": capture["capture_sha256"]})
    return load_capture(destination)
