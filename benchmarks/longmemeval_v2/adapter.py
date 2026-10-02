"""Isolated TESSERA adapter mechanics for the synthetic profile ONLY.

Not registered with or importable by the official V2 harness. No ranking changes,
image understanding, provider calls, persistence, or official tokenization.
"""

import copy
from pathlib import Path
import tempfile
import threading
from typing import Any, Dict, Optional

import yaml

from tessera import TesseraEngine

from . import PROFILE
from .contracts import (UnsupportedProtocol, bound_context, digest, positive_integer,
                        text, validate_context, validate_trajectory)
from .fixture import synthetic_context_cost, synthetic_image_validator


class SyntheticTesseraMemory:
    """One instance owns exactly one haystack, in a private temporary corpus."""

    def __init__(self, assets_root: Path, *, profile: str, context_budget: int = 100,
                 top_n: int = 7, include_source_images: bool = True):
        if profile != PROFILE:
            raise UnsupportedProtocol("official_execution_not_supported: synthetic preparation only")
        self.assets_root = Path(assets_root).resolve(strict=True)
        if not self.assets_root.is_dir():
            raise ValueError("assets root must be a directory")
        self.context_budget = positive_integer(context_budget, "context budget")
        self.top_n = positive_integer(top_n, "top_n")
        if type(include_source_images) is not bool:
            raise ValueError("include_source_images must be boolean")
        self.include_source_images = include_source_images
        self._temporary = tempfile.TemporaryDirectory(prefix="tessera-v2-synthetic-")
        self.corpus = Path(self._temporary.name)
        self._engine = None
        self._trajectories: Dict[str, Any] = {}
        self._sources: Dict[str, Any] = {}
        self._local = threading.local()
        self._closed = False
        self._sealed = False

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def _check_open(self):
        if self._closed:
            raise RuntimeError("memory is closed")

    def close(self):
        self.clear_query_context()
        self._temporary.cleanup()
        self._engine = None
        self._trajectories.clear()
        self._sources.clear()
        self._closed = True

    def _asset(self, value: str) -> Path:
        text(value, "image path")
        raw = Path(value)
        candidate = raw if raw.is_absolute() else self.assets_root / raw
        path = candidate.resolve()
        if not path.is_relative_to(self.assets_root):
            raise ValueError("image path escapes assets root")
        synthetic_image_validator(str(path))
        return path

    def insert(self, trajectory: Dict[str, Any]) -> None:
        self._check_open()
        if self._sealed:
            raise RuntimeError("haystack is sealed after its first query")
        value = validate_trajectory(trajectory)
        if value["id"] in self._trajectories:
            raise ValueError("duplicate trajectory insertion")
        if self._trajectories and value["domain"] != next(iter(self._trajectories.values()))["domain"]:
            raise ValueError("cross-domain haystack insertion")
        prepared = []
        # Validate all source images before writing any state. Text-only ablations
        # also fail on missing source evidence, rather than silently accepting it.
        for state in value["states"]:
            asset = self._asset(state["screenshot"])
            memory_id = "v2-synthetic/" + digest([value["id"], state["state_index"]])
            body = "\n".join((f"Goal: {value['goal']}", f"Outcome: {value['outcome']}",
                               f"Start URL: {value['start_url']}", f"State URL: {state['url']}",
                               f"Action: {state['action'] or ''}", f"Thought: {state['thought'] or ''}",
                               state["accessibility_tree"])) + "\n"
            provenance = {"trajectory_id": value["id"], "state_index": state["state_index"],
                          "step": state["step"], "trajectory_sha256": digest(value),
                          "state_sha256": digest(state),
                          "screenshot": asset.relative_to(self.assets_root).as_posix(),
                          "screenshot_sha256": synthetic_image_validator(str(asset)),
                          "representation": "source_text_and_original_image"}
            header = yaml.safe_dump({"id": memory_id, "node_type": "factual", "tags": []}, sort_keys=True)
            prepared.append((memory_id, "---\n" + header + "---\n" + body, provenance))
        for memory_id, document, provenance in prepared:
            (self.corpus / (digest(memory_id) + ".md")).write_text(document, encoding="utf-8")
            self._sources[memory_id] = provenance
        self._trajectories[value["id"]] = value

    def set_query_context(self, *, query_invocation_id: str):
        self._check_open()
        self._local.context = {"query_invocation_id": text(query_invocation_id, "invocation id")}

    def get_query_context(self):
        return dict(getattr(self._local, "context", {}))

    def clear_query_context(self):
        for attribute in ("context", "audit"):
            if hasattr(self._local, attribute):
                delattr(self._local, attribute)

    def query(self, query: str, query_image: Optional[str] = None):
        self._check_open()
        self._local.audit = None  # no stale successful audit after a failure
        text(query, "query")
        if query_image is not None:
            self._asset(query_image)  # transport validation, NOT visual retrieval
        self._sealed = True
        if self._engine is None and self._sources:
            self._engine = TesseraEngine(storage_dir=str(self.corpus))
            self._engine.build_index(use_cache=False, persist=False)
        hits = [] if self._engine is None else self._engine.retrieve_context_contract(query, top_n=self.top_n)
        items, sources = [], []
        for hit in hits:
            provenance = self._sources[hit["id"]]
            asset = self._asset(provenance["screenshot"])
            if synthetic_image_validator(str(asset)) != provenance["screenshot_sha256"]:
                raise ValueError("source image changed after insertion")
            items.append({"type": "text", "value": text(hit["body"], "retrieved text")})
            sources.append(copy.deepcopy(provenance))
            if self.include_source_images:
                items.append({"type": "image", "value": str(asset)})
                sources.append(copy.deepcopy(provenance))
        validated = validate_context(items, synthetic_image_validator)
        bounded = bound_context(validated, self.context_budget, synthetic_context_cost)
        self._local.audit = {"profile": PROFILE, "budget_unit": "synthetic_test_units_not_tokens",
                             "original_units": bounded["original_units"],
                             "final_units": bounded["final_units"],
                             "budget": self.context_budget,
                             "query_image_handling": "validated_not_used_for_retrieval",
                             "provenance": sources[:bounded["retained_items"]]}
        return bounded["items"]

    def audit(self):
        return copy.deepcopy(getattr(self._local, "audit", None))

    def trajectory_snapshot(self):
        return copy.deepcopy(list(self._trajectories.values()))

    def _save_backend(self, output_dir):
        raise UnsupportedProtocol("save_load_not_supported: no V2 persisted-state contract accepted")

    def _load_backend(self, input_dir):
        raise UnsupportedProtocol("save_load_not_supported: no V2 persisted-state contract accepted")
