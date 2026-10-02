"""Small strict artifact primitives, compatible with #28 canonical JSON hashes."""

import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any


LABEL_KEYS = {
    "answer", "answers", "expected_answer", "expected_answers", "ground_truth",
    "ground_truth_session_ids", "answer_session_ids", "has_answer", "is_relevant",
    "is_abstention", "label", "labels", "evidence_labels", "reference_answer",
    "reference_answers", "question_type", "verdict", "rationale",
}


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def bytes_digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def exact(value: Any, keys: set, name: str) -> None:
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError(f"{name}: closed schema mismatch")


def string(value: Any, name: str, empty: bool = False) -> None:
    if not isinstance(value, str) or (not empty and not value.strip()):
        raise ValueError(f"{name}: expected string")


def sha(value: Any, name: str, length: int = 64) -> None:
    if not isinstance(value, str) or not re.fullmatch(r"[a-f0-9]{%d}" % length, value):
        raise ValueError(f"{name}: invalid hash")


def number(value: Any, name: str, minimum: float = 0) -> None:
    if type(value) not in (int, float) or not math.isfinite(value) or value < minimum:
        raise ValueError(f"{name}: invalid finite number")


def integer(value: Any, name: str, minimum: int = 1) -> None:
    if type(value) is not int or value < minimum:
        raise ValueError(f"{name}: invalid integer")


def reject_labels(value: Any) -> None:
    # Structural guard, not a semantic classifier for source prose. A reviewed,
    # label-free producer remains mandatory; hashing cannot prove cleanliness.
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str) or key.lower() in LABEL_KEYS:
                raise ValueError("evaluator-owned fields are forbidden in reader inputs")
            reject_labels(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            reject_labels(child)


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON object key")
        result[key] = value
    return result


def decode(text: str) -> Any:
    def invalid_constant(value):
        raise ValueError("non-finite JSON number")
    return json.loads(text, object_pairs_hook=_pairs, parse_constant=invalid_constant)


def read(path: Path) -> Any:
    return decode(path.read_text(encoding="utf-8"))


def write_new(path: Path, value: Any) -> None:
    # Exclusive creation never hides an earlier attempt or a completed run.
    with path.open("x", encoding="utf-8") as handle:
        handle.write(canonical(value) + "\n")
