"""Run only a frozen synthetic, offline #176 protocol/mechanics exercise."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import tempfile

from tessera.enrichment import EnrichmentProfile, prepare_plan, replay_capture

FIXTURE_SHA256 = "1a10b7b92189ce8e0a0d4a9af5bcc5563d7be40bdeac2acaea257e931e78b862"


def run_experiment():
    data = Path(__file__).with_name("synthetic-v1.json").read_bytes()
    if hashlib.sha256(data).hexdigest() != FIXTURE_SHA256:
        raise ValueError("frozen fixture checksum mismatch")
    fixture = json.loads(data)
    profile = EnrichmentProfile("synthetic-enrichment", "1", "A3", "local", "synthetic", "none", "synthetic-v1")
    variants = {}
    with tempfile.TemporaryDirectory(prefix="tessera-enrichment-176-") as directory:
        root = Path(directory)
        for source in fixture["sources"]:
            (root / source["path"]).write_bytes(source["raw"].encode("utf-8"))
        selected = [source["path"] for source in fixture["sources"]]
        before = {path: (root / path).read_bytes() for path in selected}
        for mode in ("A1", "A2", "A3"):
            active = replace(profile, mode=mode)
            plan = prepare_plan(root, selected, "synthetic-176-v1", active)
            by_path = {source["source_path"]: source for source in plan["sources"]}
            capture = {"schema_version": 1, "plan_id": plan["plan_id"],
                       "profile_fingerprint": plan["profile_fingerprint"], "capture_kind": "synthetic", "records": []}
            for source in fixture["sources"]:
                descriptor = by_path[source["path"]]
                if not descriptor["eligible"]:
                    continue
                lines = source["raw"].splitlines(keepends=True)
                proposals = [{"claim": item["claim"], "drawer": item["drawer"], "confidence": .5,
                              "uncertainty": ["synthetic; human review absent"],
                              "supporting_spans": [{"start_line": item["line"], "end_line": item["line"],
                                                    "quote": lines[item["line"] - 1]}]} for item in source["claims"]]
                metadata = []
                if proposals:
                    metadata = [{"field": "tags", "value": ["synthetic-candidate"], "confidence": .5,
                                 "uncertainty": ["not human labeled"], "supporting_spans": proposals[0]["supporting_spans"]}]
                relations = []
                if mode == "A3" and source["path"] == "contradiction.md":
                    relations = [{"type": "contradicts", "target_source_document_id": by_path["legacy.md"]["source_document_id"],
                                  "confidence": .5, "uncertainty": ["no conflict decision"],
                                  "supporting_spans": proposals[0]["supporting_spans"]}]
                # Deliberately aggressive capture: exact duplicate and malformed
                # evidence exercise rejection/dedup, not semantic quality.
                if source["path"] == "legacy.md" and mode != "A1":
                    proposals += [dict(proposals[0]), {**proposals[0], "supporting_spans": [{"start_line": 999, "end_line": 999, "quote": "invented"}]}]
                capture["records"].append({"cache_key": descriptor["cache_key"], "status": "success",
                                          "usage": {"input_tokens": 0, "output_tokens": 0, "cost_usd": None, "latency_ms": None},
                                          "response": {"claims": proposals if mode != "A1" else [], "metadata": metadata, "relations": relations}})
            report = replay_capture(root, selected, "synthetic-176-v1", active, capture)
            assert report == replay_capture(root, selected, "synthetic-176-v1", active, capture)
            variants[mode] = {"counts": report["counts"], "usage": report["usage"], "quality": report["quality"],
                              "metadata_candidates": len(report["metadata_candidates"]),
                              "relation_candidates": len(report["relation_candidates"])}
        unchanged = before == {path: (root / path).read_bytes() for path in selected}
        assert unchanged
        assert set(selected) == {path.name for path in root.iterdir()}
    return {"schema_version": 1, "issue": 176, "fixture_sha256": FIXTURE_SHA256,
            "evidence_class": "synthetic_protocol_only", "decision": "ITERATE", "source_bytes_unchanged": unchanged,
            "human_labels": None, "provider_calls": 0, "model_downloads": 0,
            "baselines": {"E0_raw_source": {"source_documents": len(fixture["sources"]), "retrieval_quality": None},
                          "E1_structural_only": {"source_documents": len(fixture["sources"]), "structural_segments": variants["A3"]["counts"]["structural_segments"], "retrieval_quality": None},
                          "E2_aggressive_decomposition": {"status": "synthetic capture only; no AI quality result"},
                          "E3_admission_dedup": {"status": "blocked on #19 and semantic dedup; exact duplicate check only"},
                          "E4_source_fallback_relations": {"status": "source preservation tested; validated-relation consumer blocked"}},
            "variants": variants,
            "missing_evidence": ["reviewed legacy corpus and human labels", "explicit source-content consent", "chosen model route and funded budget",
                                 "Recall/MRR/nDCG and context/state quality comparisons", "semantic support and relation precision",
                                 "#192 unchanged-source cache savings and interruption tests", "#19 admission and canonical #137 lineage integration"]}


if __name__ == "__main__":
    print(json.dumps(run_experiment(), indent=2, ensure_ascii=False, sort_keys=True))
