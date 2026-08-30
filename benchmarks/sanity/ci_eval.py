"""Deterministic TESSERA sanity evaluation used by CI.

This is intentionally small and synthetic. It is a regression gate for the
memory engine itself, not a competitive benchmark such as LongMemEval.
"""

import argparse
import json
import os
import tempfile
import time
from typing import Dict, List

from tessera import Entity, TesseraEngine


CASES = [
    {
        "id": "lao-purpose-pt",
        "query": "qual o propósito do LAO?",
        "gold": "lao/charter",
    },
    {
        "id": "lao-purpose-colloquial",
        "query": "pq o LAO existe?",
        "gold": "lao/charter",
    },
    {
        "id": "lao-learning",
        "query": "como o LAO aprende?",
        "gold": "lao/learning-process",
    },
    {
        "id": "copilot-error",
        "query": "qual erro tivemos com o Copilot?",
        "gold": "gotchas/copilot-worktree-error",
    },
]


def _build_fixture_engine(storage_dir: str) -> TesseraEngine:
    engine = TesseraEngine(storage_dir=storage_dir)
    engine.write_memory_note(
        mem_id="lao/charter",
        mem_type="factual",
        episode_id="ep_lao_purpose",
        content=(
            "O propósito do LAO (Lab Autonomous Officer) é funcionar como um "
            "runtime de inovação para agentes autônomos, permitindo pesquisar, "
            "testar hipóteses e acumular aprendizados de forma persistente."
        ),
        tags=["lao", "purpose", "charter", "runtime"],
        entities=[Entity("LAO", "Lab Autonomous Officer")],
    )
    engine.write_memory_note(
        mem_id="lao/learning-process",
        mem_type="procedural_anchor",
        episode_id="ep_lao_learning",
        content=(
            "O LAO aprende registrando episódios e aprendizados no TESSERA e "
            "recuperando memórias relevantes nas execuções seguintes."
        ),
        tags=["lao", "learning", "tessera"],
        entities=[Entity("LAO", "Lab Autonomous Officer")],
    )
    engine.write_memory_note(
        mem_id="gotchas/copilot-worktree-error",
        mem_type="factual",
        episode_id="ep_copilot_error",
        content=(
            "O Copilot CLI removeu um worktree enquanto ainda dependia daquele "
            "diretório; o CWD ficou inválido e os hooks subsequentes falharam."
        ),
        tags=["copilot", "worktree", "error", "gotcha"],
        entities=[Entity("Copilot", "Copilot CLI")],
    )
    engine.write_memory_note(
        mem_id="research/unrelated-newsletter",
        mem_type="factual",
        episode_id="ep_noise",
        content=(
            "Uma newsletter recente comentou tendências gerais de agentes e "
            "automação no mercado de software."
        ),
        tags=["newsletter", "agents", "market"],
        entities=[],
    )
    engine.build_index(use_cache=False)
    return engine


def run_eval(output_dir: str) -> Dict[str, object]:
    os.makedirs(output_dir, exist_ok=True)
    per_query: List[Dict[str, object]] = []
    reciprocal_ranks: List[float] = []
    latencies: List[float] = []
    context_sizes: List[int] = []
    evidence_hits = 0

    with tempfile.TemporaryDirectory() as storage_dir:
        engine = _build_fixture_engine(storage_dir)

        for case in CASES:
            started = time.perf_counter()
            results = engine.retrieve_context(case["query"], top_n=5)
            elapsed_ms = (time.perf_counter() - started) * 1000.0
            latencies.append(elapsed_ms)

            ids = [item["id"] for item in results]
            try:
                rank = ids.index(case["gold"]) + 1
                reciprocal_rank = 1.0 / rank
            except ValueError:
                rank = None
                reciprocal_rank = 0.0
            reciprocal_ranks.append(reciprocal_rank)

            returned_chars = sum(len(item.get("body", "")) for item in results)
            context_sizes.append(returned_chars)

            gold_hit = next((item for item in results if item["id"] == case["gold"]), None)
            evidence_ok = bool(gold_hit and gold_hit.get("relevant_evidence"))
            if evidence_ok:
                evidence_hits += 1

            per_query.append(
                {
                    "query_id": case["id"],
                    "query": case["query"],
                    "gold": case["gold"],
                    "gold_rank": rank,
                    "top_results": ids,
                    "gold_relevant_evidence": (
                        gold_hit.get("relevant_evidence") if gold_hit else None
                    ),
                    "latency_ms": round(elapsed_ms, 3),
                    "returned_chars": returned_chars,
                }
            )

        # Evidence-sufficiency regression: nonsense must never fabricate a snippet.
        missing_results = engine.retrieve_context("xyzabcqwe", top_n=1)
        missing_evidence = (
            missing_results[0].get("relevant_evidence") if missing_results else None
        )
        if missing_evidence is not None:
            raise SystemExit(
                "Sanity failure: unrelated query produced relevant_evidence instead of None"
            )

    total = len(CASES)
    summary: Dict[str, object] = {
        "dataset": "tessera-sanity-ci-v1",
        "queries": total,
        "hit_at_1": sum(1 for item in per_query if item["gold_rank"] == 1) / total,
        "hit_at_3": sum(
            1
            for item in per_query
            if item["gold_rank"] is not None and int(item["gold_rank"]) <= 3
        )
        / total,
        "hit_at_5": sum(
            1
            for item in per_query
            if item["gold_rank"] is not None and int(item["gold_rank"]) <= 5
        )
        / total,
        "mrr": sum(reciprocal_ranks) / total,
        "evidence_hit_rate": evidence_hits / total,
        "average_latency_ms": sum(latencies) / total,
        "average_returned_chars": sum(context_sizes) / total,
        "missing_evidence_check": "passed",
    }

    with open(os.path.join(output_dir, "eval-summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    with open(os.path.join(output_dir, "eval-results.json"), "w", encoding="utf-8") as f:
        json.dump(per_query, f, indent=2, ensure_ascii=False)

    print(json.dumps(summary, indent=2, ensure_ascii=False))

    # Conservative regression thresholds for the controlled fixture.
    if float(summary["hit_at_1"]) < 0.75:
        raise SystemExit("Sanity failure: Hit@1 fell below 0.75")
    if float(summary["hit_at_3"]) < 1.0:
        raise SystemExit("Sanity failure: Hit@3 fell below 1.0")
    if float(summary["hit_at_5"]) < 1.0:
        raise SystemExit("Sanity failure: Hit@5 fell below 1.0")
    if float(summary["mrr"]) < 0.80:
        raise SystemExit("Sanity failure: MRR fell below 0.80")

    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="artifacts/sanity")
    args = parser.parse_args()
    run_eval(args.output_dir)


if __name__ == "__main__":
    main()
