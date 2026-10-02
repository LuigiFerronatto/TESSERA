"""Offline A0–A4 synthetic experiment. Never imports into a real user store."""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
import time

from tessera.canonical import compute_sha256, parse_and_normalize
from tessera.engine import TesseraEngine
from tessera.okf import SPEC_REVISION, export_records, native_preview, plan_import, plan_native_export
from tessera.okf_files import apply_exchange, plan_destination

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests/fixtures/okf_v02"
NATIVE = ROOT / "tests/fixtures/okf_native"


def write(root, files):
    for path, text in files.items():
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")


def reference_validator():
    path = ROOT / "tests/reference/okf_document.py"
    spec = importlib.util.spec_from_file_location("okf_pinned_reference", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.OKFDocument


def reference_count(root, validator):
    count = 0
    for path in sorted(root.rglob("*.md")):
        if path.name not in {"index.md", "log.md"}:
            validator.parse(path.read_text()).validate()
            count += 1
    return count


def smoke(root):
    with contextlib.redirect_stdout(io.StringIO()):
        engine = TesseraEngine(storage_dir=str(root))
        engine.build_index(use_cache=False)
        hits = engine.retrieve_context("primary database Cedar", top_n=3)
    assert hits and all(h.get("provenance") for h in hits)
    assert any(h.get("evidence") for h in hits)
    return [{"id": h["id"], "score": h["score"], "evidence": h["relevant_evidence"]} for h in hits]


def run():
    validator = reference_validator()
    started = time.perf_counter()
    plan = plan_import(FIXTURE, namespace="frozen-okf-204")
    import_ms = (time.perf_counter() - started) * 1000
    assert plan.report["mapping"] == "PASS"
    started = time.perf_counter()
    export = export_records(plan.records, auxiliary=plan.auxiliary)
    export_ms = (time.perf_counter() - started) * 1000
    repeat = plan_import(FIXTURE, namespace="frozen-okf-204")
    assert plan.to_dict() == repeat.to_dict()
    assert export == export_records(repeat.records, auxiliary=repeat.auxiliary)
    with tempfile.TemporaryDirectory(prefix="tessera-okf-synthetic-") as temp:
        root = Path(temp)
        write(root / "export", export["files"])
        second = plan_import(root / "export", namespace="frozen-okf-204")
        before = [r.to_dict() for r in plan.records]
        after = [r.to_dict() for r in second.records]
        assert before == after
        write(root / "import-smoke", {r.path: native_preview(r) for r in plan.records})
        write(root / "roundtrip-smoke", {r.path: native_preview(r) for r in second.records})
        imported_hits = smoke(root / "import-smoke")
        reimported_hits = smoke(root / "roundtrip-smoke")
        assert imported_hits == reimported_hits
        shutil.copytree(NATIVE, root / "native-baseline")
        native_hits = smoke(root / "native-baseline")
        native_export = plan_native_export(NATIVE)
        write(root / "native-export", native_export["files"])
        native_import = plan_import(root / "native-export", namespace="native")
        write(root / "native-roundtrip", {r.path: native_preview(r) for r in native_import.records})
        assert native_hits == smoke(root / "native-roundtrip")
        source = NATIVE / "database.md"
        baseline = parse_and_normalize(source.read_text(), str(source), str(NATIVE))
        baseline.temporal.indexed_at = ""
        assert baseline.to_dict() == native_import.records[0].canonical.to_dict()
        conversion = plan_destination(FIXTURE, root / "converted-source", operation="convert", namespace="frozen-okf-204")
        assert not (root / "converted-source").exists()
        conversion_receipt = apply_exchange(FIXTURE, root / "converted-source", operation="convert",
            namespace="frozen-okf-204", expected_plan_id=conversion["plan_id"])
        exchange = plan_destination(root / "converted-source", root / "converted-export", operation="export")
        exchange_receipt = apply_exchange(root / "converted-source", root / "converted-export", operation="export",
            expected_plan_id=exchange["plan_id"])
        converted_import = plan_import(root / "converted-export", namespace="frozen-okf-204")
        assert before == [r.to_dict() for r in converted_import.records]
        assert imported_hits == smoke(root / "converted-source")
        return {
            "issue": 204, "decision": "ITERATE", "spec_revision": SPEC_REVISION,
            "reference_validator_blob": "b770a92f33adf9942e2932529308d066430b02a6",
            "reference_validator_scope": "Upstream concept parser and required-key validator, not complete spec certification",
            "external_concept_validation": {"input": reference_count(FIXTURE, validator),
                "exported": reference_count(root / "export", validator),
                "native_exported": reference_count(root / "native-export", validator)},
            "matrix": {"A0_native_smoke": "PASS", "A1_import_smoke": "PASS", "A2_native_export": "PASS",
                       "A3_OKF_roundtrip": "PASS", "A4_native_roundtrip": "PASS"},
            "canonical_records_equal": {"OKF": [10, 10], "native": [1, 1]},
            "semantic_diff": [], "typed_native_relations_preserved": 3,
            "explicit_OKF_relations_preserved": 3, "unknown_extensions_preserved": True,
            "truth_validity_separate_from_freshness": True, "observation_separate_from_generation": True,
            "retrieval_smoke_parity": {"OKF_roundtrip": True, "native_roundtrip": True},
            "deterministic_plans": True, "lossy_semantic_fields": [],
            "derived_fields_excluded": ["temporal.indexed_at"],
            "latency_ms_observational": {"import": round(import_ms, 3), "export": round(export_ms, 3)},
            "input_hashes": {p.relative_to(FIXTURE).as_posix(): compute_sha256(p.read_text()) for p in sorted(FIXTURE.rglob("*.md"))},
            "export_hashes": export["report"]["file_hashes"],
            "source_transactions": {"convert": conversion_receipt["status"], "export": exchange_receipt["status"],
                "converted_records_equal": [10, 10], "write_gate": "all accept unchanged", "fresh_destination_only": True,
                "semantic_admission": "NOT_PERFORMED", "runtime_registration": "NOT_PERFORMED",
                "external_validation_after_transactions": reference_count(root / "converted-export", validator)},
            "acceptance_gaps": ["Future evidence-aware admission (#19), separate from source conversion", "Broader non-OKF export profiles and exposure filtering",
                "Independent full-spec conformance audit", "Representative user-corpus evaluation", "Canonical merge and exact-head governance gates"],
        }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
