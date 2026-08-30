"""TESSERA engine facade with integrated auditable evidence provenance.

The historical engine implementation lives unchanged in ``engine_core.py``.
This facade adds the Foundation Evidence Ledger contract without obscuring or
rewriting retrieval logic: index -> canonical metadata -> evidence ledger ->
structured retrieval provenance.
"""

import json
import os
from typing import Any, Dict, List, Optional

# Preserve the engine module's existing public constants/types/functions for
# callers that import them from ``tessera.engine``.
from .engine_core import *  # noqa: F401,F403
from .engine_core import TesseraEngine as _CoreTesseraEngine
from .evidence import (
    EvidenceLedger,
    enrich_retrieval_results,
    ledger_from_graph,
    retrieval_results_contract,
)


class TesseraEngine(_CoreTesseraEngine):
    """Core TESSERA engine plus a derived, rebuildable Evidence Ledger.

    Source files remain authoritative. Evidence records are reconstructed from
    Canonical Metadata after every index load/build and are returned alongside
    retrieval results as structured provenance.
    """

    def __init__(self, storage_dir: str, weights: Optional[Dict[str, float]] = None):
        super().__init__(storage_dir=storage_dir, weights=weights)
        self.evidence_ledger = EvidenceLedger()
        self.evidence_cache_json = os.path.join(self.index_cache_dir, "evidence.json")

    def _rebuild_evidence_ledger(self) -> None:
        self.evidence_ledger = ledger_from_graph(self.graph)
        for node_id, data in self.graph.nodes(data=True):
            records = self.evidence_ledger.for_memory(node_id)
            if records:
                # Derived metadata only. Never written back into source files.
                data["evidence_record"] = records[0].to_dict()
            else:
                data.pop("evidence_record", None)

    def _persist_evidence_summary(self) -> None:
        os.makedirs(self.index_cache_dir, exist_ok=True)
        payload = {
            "schema_version": 1,
            "derived": True,
            "source_of_truth": "source_files",
            "records": self.evidence_ledger.to_list(),
        }
        with open(self.evidence_cache_json, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)

    def build_index(
        self,
        recursive: bool = True,
        use_cache: bool = True,
        persist: bool = True,
    ) -> None:
        # Let the unchanged core handle parsing/indexing/cache semantics, then
        # derive evidence from the canonical metadata already attached to nodes.
        # We persist once after evidence has been attached, avoiding two graph
        # snapshots during a fresh build.
        super().build_index(recursive=recursive, use_cache=use_cache, persist=False)
        self._rebuild_evidence_ledger()
        if persist:
            super().save_index()
            self._persist_evidence_summary()

    def retrieve_context(
        self,
        query_text: str,
        top_n: int = 7,
        resolve_conflicts: bool = True,
        weights: Optional[Dict[str, float]] = None,
    ) -> List[Dict[str, Any]]:
        results = super().retrieve_context(
            query_text=query_text,
            top_n=top_n,
            resolve_conflicts=resolve_conflicts,
            weights=weights,
        )
        return enrich_retrieval_results(self, results)

    def retrieve_context_contract(self, *args: Any, **kwargs: Any) -> List[Dict[str, Any]]:
        """Return retrieval results in the shared Engine/CLI/MCP contract."""
        return retrieval_results_contract(self.retrieve_context(*args, **kwargs))
