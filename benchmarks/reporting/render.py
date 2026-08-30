"""Deterministic Markdown rendering for ledger records and comparisons."""

from typing import Any, Dict, Iterable, Mapping


METRIC_LABELS = {
    "recall_at_1": "Recall@1",
    "recall_at_3": "Recall@3",
    "recall_at_5": "Recall@5",
    "recall_at_10": "Recall@10",
    "mrr": "MRR",
    "ndcg_at_10": "nDCG@10",
    "evidence_hit_rate": "Evidence hit rate",
    "first_evidence_position": "First evidence position",
    "provenance_coverage": "Provenance coverage",
    "abstention_retrieval_empty_rate": "Abstention retrieval empty rate",
    "average_context_characters": "Average context characters",
    "average_context_tokens": "Average whitespace tokens",
}


def _value(value: Any) -> str:
    if value is None:
        return "unavailable"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return f"{value:.10f}".rstrip("0").rstrip(".")
    return str(value)


def render_record(record: Mapping[str, Any]) -> str:
    metrics = record["metrics"]
    lines = [
        f"# {record['benchmark']} — canonical dev-50 baseline",
        "",
        "> Retrieval-only development record. It does not measure final-answer correctness,",
        "> run a reader, call an LLM judge, or represent the official full-500 result.",
        "",
        "## Record",
        "",
        f"- Record ID: `{record['record_id']}`",
        f"- Decision: `{record['decision']}`",
        f"- Issue / PR: #{record['issue']} / #{record['pull_request']}",
        f"- Measured commit: `{record['measured_commit']}`",
        f"- Merge commit: `{record['merge_commit']}`",
        f"- Retrieval contract: `{record['retrieval_contract_commit']}`",
        "",
        "## Experimental profile",
        "",
        f"- Profile: `{record['profile']}`",
        f"- Dataset: `{record['dataset']['name']}` (`{record['dataset']['revision']}`)",
        f"- Dataset SHA-256: `{record['dataset']['sha256']}`",
        f"- Queries: {record['dataset']['query_count']} "
        f"({record['dataset']['positive_count']} positive, "
        f"{record['dataset']['abstention_count']} abstention)",
        f"- Subset / Top-K / granularity: `{record['configuration']['subset']}` / "
        f"{record['configuration']['top_k']} / `{record['configuration']['granularity']}`",
        "- Reader / LLM judge: none / none",
        "",
        "## Retrieval metrics",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
    ]
    for name, label in METRIC_LABELS.items():
        lines.append(f"| {label} | {_value(metrics[name])} |")
    lines.extend(
        [
            "",
            "## Determinism and provenance",
            "",
            f"- Same-commit runs: {record['determinism']['run_count']}",
            f"- Equivalent: `{_value(record['determinism']['equivalent'])}`",
            f"- Normalized SHA-256: `{record['determinism']['normalized_sha256']}`",
            f"- Retrieval-result SHA-256: "
            f"`{record['determinism']['retrieval_result_sha256']}`",
            f"- Selected-query-order SHA-256: `{record['selection']['query_ids_sha256']}`",
            "",
            "## Cost and latency",
            "",
            f"- API calls: {record['cost']['api_calls']}",
            f"- LLM calls: {record['cost']['llm_calls']}",
            f"- Estimated cost: USD {_value(record['cost']['estimated_usd'])}",
            "- Latency is informational and unavailable as a comparable canonical value.",
            "",
            "## Plain-language interpretation",
            "",
            "- Recall@K is the proportion of expected evidence sessions recovered in the first K results; it is not answer accuracy.",
            "- Evidence hit rate is the percentage of positive questions with at least one expected evidence session in Top-K.",
            "- MRR measures how early the first relevant result appears; nDCG measures evidence presence and ordering.",
            "- Provenance coverage measures whether retrieved results remain traceable.",
            "- Abstention retrieval empty rate only reports whether retrieval returned no candidates; it does not measure correct answer-stage abstention.",
            "- This 50-query profile measures retrieval only and is a development gate, not an official full-500 score.",
            "",
            "## Limitations",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in record["limitations"])
    lines.extend(["", f"## Decision: `{record['decision']}`", ""])
    return "\n".join(lines)


def _metric_rows(metrics: Mapping[str, Mapping[str, Any]]) -> Iterable[str]:
    yield "| Metric | Baseline | Candidate | Absolute Δ | Relative Δ | Status | Gate |"
    yield "| --- | ---: | ---: | ---: | ---: | --- | --- |"
    for name, item in metrics.items():
        relative = _value(item["relative_delta"])
        yield (
            f"| {METRIC_LABELS.get(name, name)} | {_value(item['baseline'])} | "
            f"{_value(item['candidate'])} | {_value(item['absolute_delta'])} | "
            f"{relative} | {item['status']} | "
            f"{'yes' if item['decision_gating'] else 'no'} |"
        )


def render_comparison(comparison: Mapping[str, Any]) -> str:
    query = comparison["query_level"]
    regressions = query.get("regressions", [])
    improvements = query.get("improvements", [])
    takeaway = (
        "No decision-gating retrieval regression was detected."
        if comparison["decision"] == "KEEP"
        else "One or more decision-gating retrieval regressions require iteration."
    )
    lines = [
        "# Benchmark comparison",
        "",
        "## 1. Executive takeaway",
        "",
        takeaway,
        "",
        "## 2. Test Card and implementation under evaluation",
        "",
        f"- Baseline: `{comparison['baseline']['record_id']}` / `{comparison['baseline']['measured_commit']}`",
        f"- Candidate: `{comparison['candidate']['record_id']}` / `{comparison['candidate']['measured_commit']}`",
        "",
        "## 3. Experimental compatibility",
        "",
        f"- Compatible: `{_value(comparison['compatibility']['compatible'])}`",
        f"- Checked fields: {', '.join(comparison['compatibility']['checked_fields'])}",
        "",
        "## 4. Baseline versus candidate",
        "",
    ]
    lines.extend(_metric_rows(comparison["metrics"]))
    lines.extend(
        [
            "",
            "## 5. Aggregate metric deltas",
            "",
            f"- Decision-gating regressions: {comparison['summary']['gating_regressions']}",
            f"- Improvements: {comparison['summary']['improvements']}",
            f"- Unchanged: {comparison['summary']['unchanged']}",
            "",
            "## 6. Query-level improvements",
            "",
        ]
    )
    lines.extend(
        [f"- `{item['question_id']}`: {', '.join(item['classifications'])}" for item in improvements]
        or ["- None."]
    )
    lines.extend(["", "## 7. Query-level regressions", ""])
    lines.extend(
        [f"- `{item['question_id']}`: {', '.join(item['classifications'])}" for item in regressions]
        or ["- None."]
    )
    lines.extend(
        [
            "",
            "## 8. Determinism",
            "",
            f"- Candidate repeated runs equivalent: `{_value(comparison['determinism']['candidate_equivalent'])}`",
            f"- Same-commit normalized-hash rule applies: `{_value(comparison['determinism']['same_commit_hash_rule'])}`",
            f"- Normalized SHA-256 match: `{_value(comparison['determinism']['normalized_sha_match'])}`",
            f"- Same retrieval-result signature: `{_value(comparison['determinism']['retrieval_signature_match'])}`",
            f"- Determinism regression: `{_value(comparison['determinism']['regression'])}`",
            f"- Reconstructed baseline metrics match the versioned record: `{_value(comparison['baseline_runtime_drift']['metrics_match_versioned_record'])}`",
            f"- Reconstructed baseline retrieval signature matches the versioned record: `{_value(comparison['baseline_runtime_drift']['retrieval_signature_match_versioned_record'])}`",
            "- A reconstructed-baseline drift is reported separately from candidate code deltas because the canonical record did not capture a fully pinned dependency/platform environment.",
            "",
            "## 9. Provenance",
            "",
            f"- Provenance regression: `{_value(comparison['provenance']['regression'])}`",
            "",
            "## 10. Context size",
            "",
            f"- Character delta: {_value(comparison['metrics']['average_context_characters']['absolute_delta'])}",
            f"- Whitespace-token delta: {_value(comparison['metrics']['average_context_tokens']['absolute_delta'])}",
            "",
            "## 11. Latency",
            "",
            f"- Comparable environment: `{_value(comparison['latency']['comparable_environment'])}`",
            "- Latency remains informational unless both records explicitly declare comparable environments.",
            "",
            "## 12. API/LLM cost",
            "",
            f"- API calls delta: {_value(comparison['cost']['api_calls']['absolute_delta'])}",
            f"- LLM calls delta: {_value(comparison['cost']['llm_calls']['absolute_delta'])}",
            f"- Estimated USD delta: {_value(comparison['cost']['estimated_usd']['absolute_delta'])}",
            "",
            "## 13. Limitations",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in comparison["limitations"])
    lines.extend(
        [
            "",
            "## 14. Plain-language interpretation",
            "",
            "Recall@K measures expected evidence sessions recovered, not final-answer accuracy. Evidence hit rate measures positive questions with at least one expected session in Top-K. MRR measures how early the first relevant result appears, while nDCG also reflects ordering. Abstention retrieval emptiness is diagnostic only and does not prove correct answer abstention. Reader quality and LLM judging are separate future layers.",
            "",
            f"## 15. Decision: `{comparison['decision']}`",
            "",
        ]
    )
    return "\n".join(lines)
