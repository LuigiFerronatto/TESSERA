"""Unlabeled independent-human review packet; no model calls or inferred labels."""

from typing import Any, Dict
from .common import canonical, digest, exact, sha, string

CASES = (
    "correct", "partially_correct", "unsupported", "explicit_abstention",
    "incorrect_abstention", "temporally_stale", "conflicting_claims", "malformed",
)
VERDICTS = ("correct", "incorrect", "abstain_correct", "abstain_incorrect")
JUDGE_FIELDS = (
    "judge_contract_version", "provider", "model", "model_revision", "endpoint_class",
    "prompt_version", "prompt_sha256", "rubric_version", "rubric_sha256", "temperature",
    "top_p", "seed", "max_output_tokens", "timeout_seconds", "retry_policy",
    "response_schema_version", "calibration_fixture_revision", "calibration_fixture_sha256",
    "reader_artifact_sha256", "dataset_revision", "dataset_sha256", "environment_fingerprint",
    "created_at",
)


def draft_packet() -> Dict[str, Any]:
    """Coverage slots, not labeled examples or an accepted calibration sample."""
    packet = {
        "schema_version": "judge-human-calibration-draft/1", "status": "DRAFT",
        "judge_selection": {key: None for key in JUDGE_FIELDS},
        "thresholds": {"accuracy_min": None, "macro_f1_min": None, "kappa_min": None,
                       "repeat_agreement_min": None, "parse_failure_max": None},
        "sampling": {"fixture_revision": None, "fixture_sha256": None, "license_review": None,
                     "split_membership_sha256": None, "sample_size": None},
        "review": {"reader_author": None, "reviewer_one": None, "reviewer_two": None,
                   "adjudicator": None, "approval_evidence": None},
        "coverage_slots": [{"category": category, "case_refs": [], "human_labels": None,
                            "human_rationales": None, "disagreement_resolution": None}
                           for category in CASES],
    }
    packet["packet_sha256"] = digest(packet)
    return packet


def validate_draft_packet(packet: Any) -> None:
    exact(packet, {"schema_version", "status", "judge_selection", "thresholds", "sampling",
                   "review", "coverage_slots", "packet_sha256"}, "judge packet")
    # Canonical template equality closes every nested field and forbids invented
    # model identities, human labels, accepted thresholds and simulated approval.
    if canonical(packet) != canonical(draft_packet()):
        raise ValueError("draft packet must remain unselected and unlabeled; review is a separate artifact")


def validate_human_review(review: Any) -> None:
    """Validate an eventual review's mechanics, never certify its authenticity.

Not invoked by CI with real data. Tests use clearly synthetic reviewer names.
The two independent initial labels remain even after adjudication.
"""
    exact(review, {"case_ref", "reader_author", "reviews", "adjudication", "reference_label"}, "human review")
    sha(review["case_ref"], "case_ref")
    string(review["reader_author"], "reader_author")
    rows = review["reviews"]
    if not isinstance(rows, list) or len(rows) != 2:
        raise ValueError("two independent reviews are required")
    ids = set()
    for row in rows:
        exact(row, {"reviewer", "label", "rationale", "evidence_sha256"}, "individual review")
        string(row["reviewer"], "reviewer")
        if row["reviewer"] in ids or row["reviewer"] == review["reader_author"]:
            raise ValueError("reviewers must be distinct and independent of reader author")
        ids.add(row["reviewer"])
        if row["label"] not in VERDICTS:
            raise ValueError("unsupported human label")
        string(row["rationale"], "human rationale")
        sha(row["evidence_sha256"], "human review evidence")
    labels = {row["label"] for row in rows}
    if len(labels) == 1:
        if review["adjudication"] is not None or review["reference_label"] not in labels:
            raise ValueError("unanimous reviews must be retained without substituted labels")
    else:
        decision = review["adjudication"]
        exact(decision, {"reviewer", "label", "rationale", "evidence_sha256"}, "adjudication")
        string(decision["reviewer"], "adjudicator")
        if decision["reviewer"] in ids or decision["reviewer"] == review["reader_author"]:
            raise ValueError("adjudicator must be independent")
        if decision["label"] not in VERDICTS or review["reference_label"] != decision["label"]:
            raise ValueError("adjudication/reference mismatch")
        string(decision["rationale"], "adjudication rationale")
        sha(decision["evidence_sha256"], "adjudication evidence")
