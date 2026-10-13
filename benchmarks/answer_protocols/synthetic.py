"""Invented oracle-format transport checks, never LongMemEval quality results."""

from pathlib import Path
from typing import Any, Dict
from .common import canonical, digest, write_new
from .evaluation import score_persisted
from .reader import draft_configuration, make_request, run_scripted


def row(question_id: str = "synthetic-color") -> Dict[str, Any]:
    # Literal mock messages model only the frozen #28 interface. This is not a
    # second renderer, not a dataset adapter and not a retrieval experiment.
    messages = [{"role": "system", "content": "Synthetic transport fixture: use supplied evidence only."},
                {"role": "user", "content": "Question: What color is the invented marker? Evidence: The marker is blue."}]
    return {"query_id": question_id, "renderer": "R0", "messages": messages,
            "input_sha256": digest(messages), "metrics": {}}


def oracle_run(destination: Path) -> Dict[str, Any]:
    if destination.exists():
        raise ValueError("refusing to overwrite an earlier synthetic run")
    destination.mkdir(parents=True, mode=0o700)
    answer = canonical({"answer": "blue", "abstained": False, "citations": []})
    abstain = canonical({"answer": "", "abstained": True, "citations": []})
    cases = [
        ("synthetic-color", "blue", False, [{"raw_response": answer, "provider_error": None}]),
        ("synthetic-unknown_abs", "", True, [{"raw_response": abstain, "provider_error": None}]),
        ("synthetic-parse-retry", "blue", False, [{"raw_response": "malformed", "provider_error": None},
                                               {"raw_response": answer, "provider_error": None}]),
        ("synthetic-provider-failure", "blue", False, [{"raw_response": None, "provider_error": "synthetic_timeout"}]),
    ]
    scores, hashes = [], []
    for index, (qid, expected, should_abstain, script) in enumerate(cases):
        frozen_row = row(qid)
        if should_abstain:
            frozen_row["messages"][1]["content"] = "Question: Where is the invented marker? Evidence: No location was supplied."
            frozen_row["input_sha256"] = digest(frozen_row["messages"])
        request = make_request(frozen_row, capture_sha256=digest("synthetic-frozen-evidence"),
                               policy_sha256=digest("synthetic-policy"), configuration=draft_configuration())
        path = destination / f"case-{index:02d}"
        capture = run_scripted(request, script, path)
        hashes.append(capture["capture_sha256"])
        scores.append(score_persisted(path, {"question_id": qid, "answer": expected,
                                            "should_abstain": should_abstain}))
    summary = {"schema_version": "reader-oracle-plumbing/1", "interpretation": "SYNTHETIC_ONLY_NOT_TESSERA_PERFORMANCE",
               "cases": len(cases), "provider_calls": 0, "cost_usd": 0,
               "captures_sha256": digest(hashes), "scores_sha256": digest(scores),
               "successful_captures": sum(score["status"] == "ok" for score in scores),
               "provider_failures": sum(score["status"] == "provider_failure" for score in scores),
               "reader_selection": None, "judge_selection": None, "quality_acceptance": None}
    write_new(destination / "j0-synthetic-scores.json", scores)
    write_new(destination / "summary.json", summary)
    return summary
