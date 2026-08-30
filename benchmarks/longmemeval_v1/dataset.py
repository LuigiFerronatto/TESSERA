"""Load, validate, checksum, and select LongMemEval V1 instances."""

import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


SELECTION_SEED = "tessera-lme-v1-96"
SELECTION_ALGORITHM = "sha256-stratified"
REQUIRED_FIELDS = {
    "question_id", "question", "question_type", "question_date",
    "haystack_session_ids", "haystack_dates", "haystack_sessions",
    "answer_session_ids",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_dataset(path: Path, expected_instances: Optional[int] = 500) -> List[Dict[str, Any]]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid LongMemEval dataset: {exc}") from exc
    validate_dataset(data, expected_instances=expected_instances)
    return data


def validate_dataset(data: Any, expected_instances: Optional[int] = 500) -> None:
    if not isinstance(data, list):
        raise ValueError("dataset must be a JSON list")
    if expected_instances is not None and len(data) != expected_instances:
        raise ValueError(f"dataset must contain {expected_instances} instances, got {len(data)}")
    seen = set()
    for index, instance in enumerate(data):
        if not isinstance(instance, dict):
            raise ValueError(f"instance {index} must be an object")
        missing = REQUIRED_FIELDS - set(instance)
        if missing:
            raise ValueError(f"instance {index} missing fields: {sorted(missing)}")
        question_id = instance["question_id"]
        if not isinstance(question_id, str) or not question_id:
            raise ValueError(f"instance {index} has invalid question_id")
        if question_id in seen:
            raise ValueError(f"duplicate question_id: {question_id}")
        seen.add(question_id)
        for field in ("question", "question_type", "question_date"):
            if not isinstance(instance[field], str) or not instance[field]:
                raise ValueError(f"instance {question_id} has invalid {field}")
        session_ids = instance["haystack_session_ids"]
        dates = instance["haystack_dates"]
        sessions = instance["haystack_sessions"]
        answers = instance["answer_session_ids"]
        if not all(isinstance(value, list) for value in (session_ids, dates, sessions, answers)):
            raise ValueError(f"instance {question_id} session/answer fields must be lists")
        if len(session_ids) != len(dates) or len(session_ids) != len(sessions):
            raise ValueError(f"instance {question_id} has misaligned session arrays")
        haystack_id_set = {str(value) for value in session_ids}
        answer_id_set = {str(value) for value in answers}
        if not question_id.endswith("_abs") and not answer_id_set.issubset(haystack_id_set):
            raise ValueError(f"instance {question_id} has answer sessions outside the haystack")
        seen_session_content: Dict[str, Any] = {}
        for session_index, session in enumerate(sessions):
            if not isinstance(session, list):
                raise ValueError(f"instance {question_id} session {session_index} must be a list")
            for turn_index, turn in enumerate(session):
                if not isinstance(turn, dict) or "role" not in turn or "content" not in turn:
                    raise ValueError(
                        f"instance {question_id} session {session_index} turn {turn_index} "
                        "must contain role and content"
                    )
                if turn["role"] not in {"user", "assistant"}:
                    raise ValueError(f"instance {question_id} has unsupported role {turn['role']!r}")
                if not isinstance(turn["content"], str):
                    raise ValueError(f"instance {question_id} has non-text turn content")
            stable_session_id = str(session_ids[session_index])
            if (
                stable_session_id in seen_session_content
                and seen_session_content[stable_session_id] != session
            ):
                raise ValueError(
                    f"instance {question_id} repeats session ID {stable_session_id} "
                    "with conflicting content"
                )
            seen_session_content[stable_session_id] = session


def is_abstention(instance: Dict[str, Any]) -> bool:
    return instance["question_id"].endswith("_abs")


def selection_hash(question_id: str, seed: str = SELECTION_SEED) -> str:
    return hashlib.sha256(f"{seed}:{question_id}".encode("utf-8")).hexdigest()


def _largest_remainder_quotas(counts: Dict[str, int], limit: int) -> Dict[str, int]:
    total = sum(counts.values())
    raw = {key: limit * count / total for key, count in counts.items()}
    quotas = {key: math.floor(value) for key, value in raw.items()}
    remaining = limit - sum(quotas.values())
    order = sorted(counts, key=lambda key: (-(raw[key] - quotas[key]), key))
    for key in order[:remaining]:
        quotas[key] += 1
    return quotas


def deterministic_subset(
    instances: Sequence[Dict[str, Any]],
    limit: int = 50,
    seed: str = SELECTION_SEED,
) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    if limit <= 0 or limit > len(instances):
        raise ValueError("limit must be between 1 and the dataset size")
    groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for instance in instances:
        groups[instance["question_type"]].append(instance)
    quotas = _largest_remainder_quotas({key: len(value) for key, value in groups.items()}, limit)

    selected: List[Dict[str, Any]] = []
    for question_type in sorted(groups):
        group = groups[question_type]
        quota = quotas[question_type]
        abstention_count = sum(is_abstention(item) for item in group)
        abstention_quota = min(abstention_count, round(quota * abstention_count / len(group)))
        abstentions = sorted(
            (item for item in group if is_abstention(item)),
            key=lambda item: (selection_hash(item["question_id"], seed), item["question_id"]),
        )
        positives = sorted(
            (item for item in group if not is_abstention(item)),
            key=lambda item: (selection_hash(item["question_id"], seed), item["question_id"]),
        )
        selected.extend(abstentions[:abstention_quota])
        selected.extend(positives[: quota - abstention_quota])

    if any(is_abstention(item) for item in instances) and not any(is_abstention(item) for item in selected):
        candidate = min(
            (item for item in instances if is_abstention(item)),
            key=lambda item: (selection_hash(item["question_id"], seed), item["question_id"]),
        )
        replace_index = next(
            index for index in range(len(selected) - 1, -1, -1)
            if selected[index]["question_type"] == candidate["question_type"]
            and not is_abstention(selected[index])
        )
        selected[replace_index] = candidate

    selected.sort(key=lambda item: (item["question_type"], selection_hash(item["question_id"], seed)))
    if len(selected) != limit:
        raise AssertionError(f"selection produced {len(selected)} instances, expected {limit}")
    return selected, quotas


def selected_question_records(
    selected: Iterable[Dict[str, Any]], seed: str = SELECTION_SEED
) -> List[Dict[str, Any]]:
    return [
        {
            "order": order,
            "question_id": item["question_id"],
            "question_type": item["question_type"],
            "is_abstention": is_abstention(item),
            "selection_hash": selection_hash(item["question_id"], seed),
        }
        for order, item in enumerate(selected, 1)
    ]


def question_type_counts(instances: Iterable[Dict[str, Any]]) -> Dict[str, int]:
    return dict(sorted(Counter(item["question_type"] for item in instances).items()))
