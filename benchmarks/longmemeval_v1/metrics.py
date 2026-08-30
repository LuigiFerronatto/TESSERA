"""Reader-independent session retrieval metrics for LongMemEval V1."""

import math
import statistics
from typing import Any, Dict, Iterable, List, Optional, Sequence


def whitespace_tokens(text: str) -> int:
    return len(text.split())


def recall_at_k(retrieved_ids: Sequence[str], relevant_ids: Sequence[str], k: int) -> float:
    relevant = set(relevant_ids)
    if not relevant:
        return 0.0
    return len(relevant.intersection(retrieved_ids[:k])) / len(relevant)


def reciprocal_rank(retrieved_ids: Sequence[str], relevant_ids: Sequence[str]) -> float:
    relevant = set(relevant_ids)
    for rank, session_id in enumerate(retrieved_ids, 1):
        if session_id in relevant:
            return 1.0 / rank
    return 0.0


def ndcg_at_k(retrieved_ids: Sequence[str], relevant_ids: Sequence[str], k: int = 10) -> float:
    relevant = set(relevant_ids)
    if not relevant:
        return 0.0
    dcg = sum(
        1.0 / math.log2(rank + 1)
        for rank, session_id in enumerate(retrieved_ids[:k], 1)
        if session_id in relevant
    )
    ideal_hits = min(len(relevant), k)
    ideal = sum(1.0 / math.log2(rank + 1) for rank in range(1, ideal_hits + 1))
    return dcg / ideal if ideal else 0.0


def first_relevant_position(
    retrieved_ids: Sequence[str], relevant_ids: Sequence[str]
) -> Optional[int]:
    relevant = set(relevant_ids)
    return next(
        (rank for rank, session_id in enumerate(retrieved_ids, 1) if session_id in relevant),
        None,
    )


def _mean(values: Iterable[float]) -> float:
    materialized = list(values)
    return statistics.fmean(materialized) if materialized else 0.0


def _percentile(values: Sequence[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = max(1, math.ceil(percentile * len(ordered)))
    return ordered[rank - 1]


def calculate_metrics(results: List[Dict[str, Any]], top_k: int = 10) -> Dict[str, Any]:
    positives = [result for result in results if not result["is_abstention"]]
    abstentions = [result for result in results if result["is_abstention"]]

    def ids(result: Dict[str, Any]) -> List[str]:
        return [item["session_id"] for item in result["retrieved"]]

    first_positions = [
        first_relevant_position(ids(result), result["ground_truth_session_ids"])
        for result in positives
    ]
    found_positions = [position for position in first_positions if position is not None]
    retrieved = [item for result in results for item in result["retrieved"]]
    query_latencies = [float(result["latency_ms"]) for result in results]
    indexing_latencies = [float(result["indexing_latency_ms"]) for result in results]

    metrics: Dict[str, Any] = {}
    for k in (1, 3, 5, 10):
        metrics[f"recall_at_{k}"] = _mean(
            recall_at_k(ids(result), result["ground_truth_session_ids"], k)
            for result in positives
        )
    metrics.update(
        {
            "mrr": _mean(
                reciprocal_rank(ids(result), result["ground_truth_session_ids"])
                for result in positives
            ),
            "ndcg_at_10": _mean(
                ndcg_at_k(ids(result), result["ground_truth_session_ids"], 10)
                for result in positives
            ),
            "evidence_hit_rate": _mean(position is not None for position in first_positions),
            "first_evidence_position": _mean(found_positions) if found_positions else None,
            "provenance_coverage": _mean(item["provenance_present"] for item in retrieved),
            "average_context_characters": _mean(
                item["context_characters"] for item in retrieved
            ),
            "average_context_tokens": _mean(item["context_tokens"] for item in retrieved),
            "indexing_latency_ms": _mean(indexing_latencies),
            "total_indexing_latency_ms": sum(indexing_latencies),
            "query_latency_p50_ms": _percentile(query_latencies, 0.50),
            "query_latency_p95_ms": _percentile(query_latencies, 0.95),
            "abstention_retrieval_empty_rate": _mean(
                not result["retrieved"] for result in abstentions
            ),
        }
    )
    return metrics
