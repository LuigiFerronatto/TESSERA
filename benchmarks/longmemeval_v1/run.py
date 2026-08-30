"""CLI runner for the deterministic LongMemEval V1 retrieval baseline."""

import argparse
import json
import platform
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from tessera import TesseraEngine

from . import (
    ADAPTER_VERSION,
    BENCHMARK_NAME,
    BENCHMARK_VERSION,
    DATASET_SHA256,
    DATASET_URL,
    SOURCE_COMMIT,
    SOURCE_REPOSITORY,
    TESSERA_BASELINE_COMMIT,
)
from .adapter import write_instance_corpus
from .dataset import (
    SELECTION_ALGORITHM,
    SELECTION_SEED,
    deterministic_subset,
    is_abstention,
    load_dataset,
    question_type_counts,
    selected_question_records,
    sha256_file,
)
from .metrics import calculate_metrics, first_relevant_position, whitespace_tokens
from .schemas import validate_artifact_bundle


LATENCY_METRICS = {
    "indexing_latency_ms", "total_indexing_latency_ms",
    "query_latency_p50_ms", "query_latency_p95_ms",
}


def _write_json(path: Path, payload: Any) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def _result_for_instance(
    instance: Dict[str, Any], dataset_sha256: str, top_k: int
) -> Dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="tessera-lme-v1-") as temporary:
        corpus_dir = Path(temporary) / "corpus"
        documents = write_instance_corpus(instance, corpus_dir, dataset_sha256)
        engine = TesseraEngine(storage_dir=str(corpus_dir))
        index_started = time.perf_counter()
        engine.build_index(use_cache=False, persist=False)
        indexing_latency_ms = (time.perf_counter() - index_started) * 1000

        query_started = time.perf_counter()
        hits = engine.retrieve_context_contract(instance["question"], top_n=top_k)
        query_latency_ms = (time.perf_counter() - query_started) * 1000

        abstention = is_abstention(instance)
        ground_truth = [] if abstention else [
            str(value) for value in instance["answer_session_ids"]
        ]
        retrieved = []
        for rank, hit in enumerate(hits, 1):
            frontmatter = hit.get("frontmatter") or {}
            session_id = str(frontmatter.get("session_id", ""))
            provenance_present = bool(
                hit.get("provenance")
                and frontmatter.get("question_id") == instance["question_id"]
                and session_id
            )
            body = hit.get("body") or ""
            retrieved.append(
                {
                    "rank": rank,
                    "memory_id": hit["id"],
                    "session_id": session_id,
                    "score": hit["score"],
                    "is_relevant": session_id in set(ground_truth),
                    "provenance_present": provenance_present,
                    "context_characters": len(body),
                    "context_tokens": whitespace_tokens(body),
                }
            )
        retrieved_ids = [item["session_id"] for item in retrieved]
        return {
            "question_id": instance["question_id"],
            "question_type": instance["question_type"],
            "is_abstention": abstention,
            "question": instance["question"],
            "ground_truth_session_ids": ground_truth,
            "corpus_memory_ids": [document.memory_id for document in documents],
            "retrieved": retrieved,
            "first_evidence_position": first_relevant_position(retrieved_ids, ground_truth),
            "latency_ms": query_latency_ms,
            "indexing_latency_ms": indexing_latency_ms,
        }


def _scorecard_markdown(scorecard: Dict[str, Any], manifest: Dict[str, Any]) -> str:
    metrics = scorecard["metrics"]
    lines = [
        "# LongMemEval V1 — TESSERA retrieval baseline",
        "",
        "> Minimal deterministic session-retrieval baseline. This is not the official full ",
        "> LongMemEval result and does not evaluate answer generation or a reader.",
        "",
        "## Run",
        "",
        f"- Dataset SHA-256: `{manifest['dataset_sha256']}`",
        f"- LongMemEval commit: `{manifest['source_commit']}`",
        f"- TESSERA baseline commit: `{manifest['tessera_commit']}`",
        f"- Selected instances: {manifest['selected_instances']}",
        f"- Abstention instances: {manifest['abstention_instances']}",
        f"- Top-K: {manifest['top_k']}",
        "- Retrieval granularity: session",
        "- Token count: whitespace (not model tokens)",
        "",
        "## Scorecard",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
    ]
    for name, value in metrics.items():
        rendered = "null" if value is None else f"{value:.6f}" if isinstance(value, float) else str(value)
        lines.append(f"| `{name}` | {rendered} |")
    lines.extend(
        [
            "",
            "## Limitations",
            "",
            "- The deterministic-small subset has 50/500 questions and is not an official full score.",
            "- Only session retrieval is measured; no reader, generation, QA evaluator, or LLM judge runs.",
            "- Whitespace token counts are deterministic approximations, not model-specific tokens.",
            "- Abstention reports retrieval emptiness separately and is excluded from relevance metrics.",
            "",
        ]
    )
    return "\n".join(lines)


def run_baseline(
    dataset_path: Path,
    subset: str,
    limit: int,
    top_k: int,
    output_dir: Path,
    created_at: Optional[str] = None,
) -> Dict[str, Any]:
    if top_k != 10:
        raise ValueError("LongMemEval V1 baseline fixes top_k=10")
    dataset_sha256 = sha256_file(dataset_path)
    if dataset_sha256 != DATASET_SHA256:
        raise ValueError(
            f"dataset checksum mismatch: expected {DATASET_SHA256}, got {dataset_sha256}"
        )
    instances = load_dataset(dataset_path)
    if subset == "full":
        selected = sorted(instances, key=lambda item: item["question_id"])
        quotas = question_type_counts(selected)
        algorithm = "full-question-id-order"
    else:
        selected, quotas = deterministic_subset(instances, limit=limit)
        algorithm = SELECTION_ALGORITHM

    results = [_result_for_instance(instance, dataset_sha256, top_k) for instance in selected]
    metrics = calculate_metrics(results, top_k=top_k)
    selection = selected_question_records(selected)
    created_at = created_at or datetime.now(timezone.utc).isoformat()
    retrieval_configuration = {
        "engine": "TesseraEngine.retrieve_context_contract",
        "weights": "runtime-defaults",
        "resolve_conflicts": True,
        "top_k": top_k,
        "reader": None,
    }
    manifest = {
        "benchmark": BENCHMARK_NAME,
        "benchmark_version": BENCHMARK_VERSION,
        "source_repository": SOURCE_REPOSITORY,
        "source_commit": SOURCE_COMMIT,
        "dataset_url": DATASET_URL,
        "dataset_file": dataset_path.name,
        "dataset_sha256": dataset_sha256,
        "dataset_instances": len(instances),
        "selected_instances": len(selected),
        "selection_algorithm": algorithm,
        "selection_seed": SELECTION_SEED,
        "selected_question_ids": [item["question_id"] for item in selected],
        "question_type_quotas": quotas,
        "abstention_instances": sum(is_abstention(item) for item in selected),
        "retrieval_granularity": "session",
        "top_k": top_k,
        "license": "MIT",
        "tessera_commit": TESSERA_BASELINE_COMMIT,
        "python_version": platform.python_version(),
        "adapter_version": ADAPTER_VERSION,
        "token_count_method": "whitespace",
        "created_at": created_at,
        "retrieval_configuration": retrieval_configuration,
        "run_count": 1,
    }
    scorecard = {
        "schema_version": 1,
        "benchmark": BENCHMARK_NAME,
        "subset": subset,
        "counts": {
            "dataset_instances": len(instances),
            "selected_instances": len(selected),
            "positive_instances": sum(not is_abstention(item) for item in selected),
            "abstention_instances": sum(is_abstention(item) for item in selected),
        },
        "metrics": metrics,
        "metric_definitions": {
            "relevance": "binary answer_session_ids membership",
            "recall": "relevant sessions retrieved divided by relevant sessions",
            "mrr": "reciprocal rank of first relevant session",
            "ndcg_at_10": "binary relevance, logarithmic discount",
            "evidence_hit_rate": "non-abstention queries with a relevant Top-K session",
            "first_evidence_position": "mean first relevant rank among queries with a hit",
            "provenance_coverage": "results retaining provenance plus question/session metadata",
            "abstention": "excluded from relevance metrics; retrieval emptiness reported separately",
            "tokens": "whitespace-delimited count, not model tokens",
        },
        "run_configuration": retrieval_configuration,
        "limitations": [
            "50-question subset is not an official full LongMemEval score",
            "retrieval only; no reader, generation, or LLM-as-judge",
            "latency is environment-dependent",
        ],
    }
    bundle = {"manifest": manifest, "results": results, "scorecard": scorecard}
    validate_artifact_bundle(bundle)
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(output_dir / "manifest.json", manifest)
    _write_json(output_dir / "selected_questions.json", selection)
    _write_json(output_dir / "results.json", results)
    _write_json(output_dir / "scorecard.json", scorecard)
    (output_dir / "scorecard.md").write_text(
        _scorecard_markdown(scorecard, manifest), encoding="utf-8"
    )
    return bundle


def reproducibility_payload(output_dir: Path) -> Dict[str, Any]:
    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    selected = json.loads((output_dir / "selected_questions.json").read_text(encoding="utf-8"))
    results = json.loads((output_dir / "results.json").read_text(encoding="utf-8"))
    scorecard = json.loads((output_dir / "scorecard.json").read_text(encoding="utf-8"))
    manifest.pop("created_at", None)
    for result in results:
        result.pop("latency_ms", None)
        result.pop("indexing_latency_ms", None)
    for metric in LATENCY_METRICS:
        scorecard["metrics"].pop(metric, None)
    return {
        "manifest": manifest,
        "selected_questions": selected,
        "results": results,
        "scorecard": scorecard,
    }


def compare_runs(first: Path, second: Path) -> bool:
    return reproducibility_payload(first) == reproducibility_payload(second)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-path", type=Path, required=True)
    parser.add_argument("--subset", choices=("deterministic-small", "full"), required=True)
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    bundle = run_baseline(
        args.dataset_path, args.subset, args.limit, args.top_k, args.output_dir
    )
    print(json.dumps(bundle["scorecard"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
