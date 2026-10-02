"""ID-only full-500 preparation and a fail-closed, reviewed-preregistration gate."""

from pathlib import Path
from typing import Any, Dict, List

from benchmarks.longmemeval_v1 import DATASET_SHA256, DATASET_URL, SOURCE_COMMIT
from benchmarks.longmemeval_v1.dataset import load_dataset, sha256_file
from .common import digest, exact, integer, number, sha, string

FULL_VERSION = "longmemeval-full500-id-manifest/1"
FULL_QUESTION_IDS_SHA256 = "a4849b8afda6b6ed31ead4fc28d00784d2d5fef945be87642f5ce3ab710b21c4"
PREREG_VERSION = "longmemeval-full500-preregistration-draft/1"
DEPENDENCIES = (28, 74, 96, 100, 103, 104)
PIN_FIELDS = {"provider", "model", "model_revision", "endpoint_class", "prompt_sha256",
              "configuration_sha256", "manifest_sha256"}


def selection_from_dataset(path: Path) -> Dict[str, Any]:
    # Check bytes again on each invocation/cache restore before parsing.
    if sha256_file(path) != DATASET_SHA256:
        raise ValueError("dataset checksum mismatch")
    dataset = load_dataset(path, expected_instances=500)
    ids = [row["question_id"] for row in dataset]
    manifest = {"schema_version": FULL_VERSION, "dataset_url": DATASET_URL,
                "dataset_sha256": DATASET_SHA256,
                "dataset_revision": "content-sha256:" + DATASET_SHA256,
                "upstream_code_revision": SOURCE_COMMIT,
                "order_policy": "pinned-file-order-v1", "question_count": 500,
                "question_ids": ids, "question_ids_sha256": digest(ids)}
    validate_selection(manifest)
    return manifest


def validate_selection(manifest: Any) -> None:
    exact(manifest, {"schema_version", "dataset_url", "dataset_sha256", "dataset_revision",
                     "upstream_code_revision", "order_policy", "question_count",
                     "question_ids", "question_ids_sha256"}, "ID manifest")
    if (manifest["schema_version"] != FULL_VERSION or manifest["dataset_url"] != DATASET_URL
            or manifest["dataset_sha256"] != DATASET_SHA256
            or manifest["dataset_revision"] != "content-sha256:" + DATASET_SHA256
            or manifest["upstream_code_revision"] != SOURCE_COMMIT
            or manifest["order_policy"] != "pinned-file-order-v1"):
        raise ValueError("unrecognized pinned dataset/selection contract")
    integer(manifest["question_count"], "question_count")
    ids = manifest["question_ids"]
    if not isinstance(ids, list) or len(ids) != 500 or manifest["question_count"] != 500:
        raise ValueError("exactly 500 question IDs are required")
    for qid in ids:
        string(qid, "question_id")
    if len(set(ids)) != 500:
        raise ValueError("duplicate question ID")
    if (digest(ids) != manifest["question_ids_sha256"]
            or manifest["question_ids_sha256"] != FULL_QUESTION_IDS_SHA256):
        raise ValueError("question order/hash mismatch")


def draft_preregistration(selection: Dict[str, Any]) -> Dict[str, Any]:
    validate_selection(selection)
    return {
        "schema_version": PREREG_VERSION, "status": "DRAFT_NOT_AUTHORIZATION",
        "profile": "full-500", "selection_sha256": digest(selection),
        "question_ids_sha256": selection["question_ids_sha256"],
        "dataset_sha256": selection["dataset_sha256"], "tessera_commit": None,
        "adapter_version": None, "environment_fingerprint": None,
        "retrieval": {"contract_commit": None, "configuration_sha256": None, "artifact_sha256": None},
        "renderer": {"commit": None, "version": None, "policy_sha256": None},
        "reader": {key: None for key in sorted(PIN_FIELDS)},
        "judge": {key: None for key in sorted(PIN_FIELDS | {"rubric_sha256", "calibration_review_sha256"})},
        "deterministic_metrics_version": None,
        "policies": {"retry": None, "failure": None, "exclusion": None, "repeatability": None,
                     "statistics": None, "artifact_retention": None},
        "decision_thresholds_sha256": None,
        "budget": {"currency": "USD", "cost_ceiling": None, "maximum_run_attempts": None},
        "dependencies": [{"issue": issue, "canonical_commit": None, "decision": None,
                          "evidence_url": None} for issue in DEPENDENCIES],
        "review": {"reviewer": None, "approved_at": None, "evidence_url": None},
        "execution_authorization": None,
    }


def validate_preregistration(record: Any, selection: Dict[str, Any]) -> None:
    template = draft_preregistration(selection)
    exact(record, set(template), "preregistration")
    for key in ("schema_version", "profile", "selection_sha256", "question_ids_sha256", "dataset_sha256"):
        if record[key] != template[key]:
            raise ValueError(f"{key}: preregistration/selection mismatch")
    if record["status"] not in ("DRAFT_NOT_AUTHORIZATION", "REVIEWED"):
        raise ValueError("unsupported preregistration status")
    for group in ("retrieval", "renderer", "reader", "judge", "policies", "budget", "review"):
        exact(record[group], set(template[group]), group)
    rows = record["dependencies"]
    if not isinstance(rows, list) or len(rows) != len(DEPENDENCIES):
        raise ValueError("missing dependency gates")
    for expected, row in zip(DEPENDENCIES, rows):
        exact(row, {"issue", "canonical_commit", "decision", "evidence_url"}, "dependency")
        if type(row["issue"]) is not int or row["issue"] != expected:
            raise ValueError("duplicate, missing or reordered dependency")
        if row["canonical_commit"] is not None:
            sha(row["canonical_commit"], "canonical_commit", 40)
        if row["decision"] is not None and row["decision"] != "KEEP":
            raise ValueError("dependencies must have an accepted KEEP decision")
        if row["evidence_url"] is not None:
            _url(row["evidence_url"])
    for key in ("tessera_commit", "adapter_version", "environment_fingerprint", "deterministic_metrics_version",
                "decision_thresholds_sha256", "execution_authorization"):
        _pin(key, record[key])
    for group in ("retrieval", "renderer", "reader", "judge", "policies", "review"):
        for key, value in record[group].items():
            _pin(key, value)
    if record["budget"]["currency"] != "USD":
        raise ValueError("this draft budget schema requires explicit USD")
    if record["budget"]["cost_ceiling"] is not None:
        number(record["budget"]["cost_ceiling"], "cost ceiling", 0.000001)
    if record["budget"]["maximum_run_attempts"] is not None:
        integer(record["budget"]["maximum_run_attempts"], "maximum run attempts")


def _url(value):
    string(value, "review evidence URL")
    if not value.startswith("https://") or any(c.isspace() for c in value):
        raise ValueError("review evidence requires an explicit HTTPS URL")


def _pin(key, value):
    if value is None:
        return
    if key.endswith("sha256"):
        sha(value, key)
    elif key.endswith("commit"):
        sha(value, key, 40)
    elif key == "evidence_url":
        _url(value)
    else:
        string(value, key)
        if value.strip().lower() in {"latest", "main", "default", "auto", "unknown", "tbd", "draft"}:
            raise ValueError(f"{key}: unresolved or mutable selection")


def readiness_errors(record: Any, selection: Dict[str, Any]) -> List[str]:
    validate_preregistration(record, selection)
    errors = []
    if record["status"] != "REVIEWED":
        errors.append("status: independent review has not accepted this preregistration")
    def visit(value, path):
        if value is None:
            errors.append(path + ": unselected/unreviewed")
        elif isinstance(value, dict):
            for key, child in value.items():
                visit(child, path + "." + key)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                visit(child, path + f"[{index}]")
    visit(record, "preregistration")
    return errors


def require_ready(record: Any, selection: Dict[str, Any]) -> None:
    errors = readiness_errors(record, selection)
    if errors:
        raise ValueError("execution blocked: " + "; ".join(errors))


def execute(record: Any, selection: Dict[str, Any]) -> None:
    require_ready(record, selection)
    # Even fabricated review strings cannot activate a provider, retrieve the
    # full set, inspect credentials, or turn this preparation into execution.
    raise RuntimeError("execution is deliberately unavailable in this preparation PR")
