"""Independent, strict public-schema controls; no upstream code is imported."""

import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


class UnsupportedProtocol(RuntimeError):
    """A required official contract has not been implemented or pinned."""


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def closed_object(value: Any, keys: set, name: str) -> None:
    if type(value) is not dict or set(value) != keys:
        raise ValueError(f"{name}: expected exactly {sorted(keys)}")


def text(value: Any, name: str, *, empty: bool = False) -> str:
    if type(value) is not str or (not empty and not value.strip()):
        raise ValueError(f"{name}: expected {'a' if empty else 'a non-empty'} string")
    return value


def positive_integer(value: Any, name: str) -> int:
    if type(value) is not int or value <= 0:
        raise ValueError(f"{name}: expected a positive integer")
    return value


def validate_trajectory(value: Any) -> Dict[str, Any]:
    """Supported public states form, not the legacy private content form.

    Unknown fields fail closed, including evaluator metadata at every structural
    boundary. This cannot detect an answer intentionally embedded in source prose.
    """
    closed_object(value, {"id", "domain", "environment", "goal", "outcome",
                          "start_url", "states"}, "trajectory")
    for key in ("id", "environment", "start_url"):
        text(value[key], key)
    text(value["goal"], "goal", empty=True)
    if value["domain"] not in ("web", "enterprise"):
        raise ValueError("trajectory: unsupported domain")
    if value["outcome"] not in ("success", "failure"):
        raise ValueError("trajectory: unsupported outcome")
    if type(value["states"]) is not list or not value["states"]:
        raise ValueError("trajectory: states must be a non-empty list")
    for index, state in enumerate(value["states"]):
        closed_object(state, {"state_index", "step", "url", "action", "thought",
                              "accessibility_tree", "screenshot"}, "state")
        if type(state["state_index"]) is not int or state["state_index"] != index:
            raise ValueError("state_index must match ordered state position")
        if type(state["step"]) is not int or state["step"] < 0:
            raise ValueError("step must be a non-negative integer")
        for key in ("url", "screenshot"):
            text(state[key], key)
        text(state["accessibility_tree"], "accessibility_tree", empty=True)
        for key in ("action", "thought"):
            if state[key] is not None:
                text(state[key], key, empty=True)
    return copy.deepcopy(value)


def validate_context(items: Any, image_validator: Callable[[str], Any]) -> List[Dict[str, str]]:
    if type(items) is not list:
        raise ValueError("context must be a list")
    for item in items:
        closed_object(item, {"type", "value"}, "context item")
        text(item["value"], "context value")
        if item["type"] == "image":
            path = Path(item["value"])
            if not path.is_file():
                raise ValueError("missing image: context image must be an existing file")
            image_validator(item["value"])
        elif item["type"] != "text":
            raise ValueError("context type must be text or image")
    return copy.deepcopy(items)


def bound_context(items: List[Dict[str, str]], max_tokens: int,
                  counter: Optional[Callable] = None) -> Dict[str, Any]:
    """Exercise whole-item prefix enforcement with an explicitly injected counter.

    There is no default fake tokenizer. Tests supply synthetic item costs and
    must label their counts as synthetic units, never official/model tokens.
    """
    positive_integer(max_tokens, "context budget")
    if counter is None:
        raise UnsupportedProtocol("official_tokenizer_unpinned: Qwen3.5-9B processor revision required")
    counts = [counter(copy.deepcopy(items[:n])) for n in range(len(items) + 1)]
    if any(type(n) is not int or n < 0 for n in counts) or counts[0] != 0:
        raise ValueError("counter must produce non-negative integers and zero for empty context")
    if any(a > b for a, b in zip(counts, counts[1:])):
        raise ValueError("non-monotone counter: prefix budget contract unsupported")
    retained = max(n for n, count in enumerate(counts) if count <= max_tokens)
    return {"items": copy.deepcopy(items[:retained]), "original_units": counts[-1],
            "final_units": counts[retained], "retained_items": retained}


def query_payload(runtime_record: Any) -> Dict[str, Optional[str]]:
    """Evaluator-side projection. The raw record never reaches a memory instance.

    Matches harness runtime question shape, after public_data materialization.
    Only the question field is inspected; other evaluator fields are opaque.
    """
    if type(runtime_record) is not dict:
        raise ValueError("runtime record must be an object")
    if "image" in runtime_record:
        raise ValueError("public question image must be materialized into runtime question first")
    question = runtime_record.get("question")
    if type(question) is str:
        return {"query": text(question, "query"), "query_image": None}
    closed_object(question, {"text", "image"}, "runtime question")
    return {"query": text(question["text"], "query"),
            "query_image": text(question["image"], "query image")}


def invoke_query(memory: Any, runtime_record: Any, invocation_id: str) -> Any:
    """Mirror only the metadata isolation/lifecycle boundary, not an evaluator."""
    payload = query_payload(runtime_record)
    memory.set_query_context(query_invocation_id=text(invocation_id, "invocation id"))
    try:
        return memory.query(**payload)
    finally:
        memory.clear_query_context()
