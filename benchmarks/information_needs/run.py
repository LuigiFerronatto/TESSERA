"""Run #139 mechanics or replay captured provider calls on a frozen corpus.

Provider calls must be captured by an application with authorized access and
explicit token/time/spend limits. This runner never calls a remote provider.
Replay uses exact prompt hashes so unrelated/changed prompts cannot be scored.
"""
import argparse
import hashlib
import json
import math
import statistics
import tempfile

import yaml
from pathlib import Path

from tessera import TesseraEngine, TesseraOrchestrator
from tessera.information_needs import InformationNeedsError

FIXTURE = Path(__file__).with_name("scenarios.json")


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def load_fixture():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def mock_responses(scenario, variant):
    """An oracle test double proves plumbing only, never model quality."""
    facets = scenario["facets"]
    if variant == "N0":
        first = "Historical factual and preference evidence about " + scenario["task"]
    else:
        descriptions = ["; ".join(facets)] if variant == "N1" and facets else facets
        first = json.dumps({
            "status": scenario["status"], "reason": "Synthetic mechanics fixture; not a model prediction.",
            "needs": [{"id": f"need-{i+1}", "description": facet,
                       "purpose": "Establish historical evidence for the task."}
                      for i, facet in enumerate(descriptions)],
        })
    return [first, "project kickoff review report format preference lesson", "Synthetic context; no state quality claim."]


def run_experiment(*, replay=None, review=None, capture_fn=None, provider=None):
    """Run mocks, replay, or explicitly supplied application-owned capture.

    ``capture_fn(system, user, *, max_output_tokens, timeout_s)`` returns a dict
    with ``response`` and ``usage``. It must enforce these transport limits,
    disable hidden retries, and report actual provider usage. No adapters,
    credentials, environment variables or provider packages are discovered.
    """
    fixture = load_fixture()
    fixture_hash = digest(fixture)
    if capture_fn is not None:
        if replay is not None:
            raise ValueError("Choose capture or replay, not both")
        replay = {"mode": "provider_capture", "fixture_sha256": fixture_hash,
                  "provider": provider or {}, "runs": {}}
    if replay is not None:
        if replay.get("fixture_sha256") != fixture_hash or replay.get("mode") != "provider_capture":
            raise ValueError("Replay requires provider_capture mode and the exact frozen fixture hash")
        metadata = replay.get("provider", {})
        for key in ("name", "model_revision", "temperature", "max_output_tokens", "timeout_s", "captured_at", "adapter_revision"):
            if key not in metadata or metadata[key] is None:
                raise ValueError("Missing provider metadata: " + key)
        for key in ("name", "model_revision", "captured_at", "adapter_revision"):
            if not isinstance(metadata[key], str) or not metadata[key].strip():
                raise ValueError("Invalid provider identity: " + key)
        if type(metadata["temperature"]) not in (int, float) or not 0 <= metadata["temperature"] <= 2:
            raise ValueError("Invalid provider temperature")
        if capture_fn is None and set(replay.get("runs", {})) != {
            scenario["id"] + "/" + variant
            for scenario in fixture["scenarios"] for variant in ("N0", "N1", "N2")
        }:
            raise ValueError("Capture must include exactly the frozen scenario/variant runs")
        if type(metadata["max_output_tokens"]) is not int or type(metadata["timeout_s"]) not in (int, float) or not 1 <= metadata["max_output_tokens"] <= 2048 or not 0 < metadata["timeout_s"] <= 60:
            raise ValueError("Provider capture exceeds the frozen token/time budget")
    rows = []
    with tempfile.TemporaryDirectory(prefix="tessera-needs-") as tmp:
        engine = TesseraEngine(storage_dir=tmp)
        for note in fixture["corpus"]:
            frontmatter = {
                "id": note["id"], "node_type": note["type"],
                "created_at": "2026-03-01T00:00:00Z", "last_updated_at": "2026-03-01T00:00:00Z",
                "episode_id": "controlled-139", "description": note["type"] + " evidence",
            }
            Path(tmp, note["id"] + ".md").write_text(
                "---\n" + yaml.safe_dump(frontmatter, sort_keys=True) + "---\n" + note["text"] + "\n",
                encoding="utf-8",
            )
        engine.build_index()
        for scenario in fixture["scenarios"]:
            for variant in ("N0", "N1", "N2"):
                key = scenario["id"] + "/" + variant
                replies = mock_responses(scenario, variant) if replay is None else None
                recorded = []
                if capture_fn is not None:
                    replay["runs"][key] = {"calls": []}
                capture = None if replay is None else replay["runs"][key]

                def llm(system, user):
                    index = len(recorded)
                    if index >= 3:
                        raise ValueError("Pipeline exceeded three generation calls")
                    prompt_hash = digest({"system": system, "user": user})
                    entry = {"prompt_sha256": prompt_hash, "system": system, "user": user}
                    recorded.append(entry)
                    if replay is None:
                        answer = replies[index]
                        usage = None
                    else:
                        if capture_fn is not None:
                            call = capture_fn(
                                system, user, max_output_tokens=replay["provider"]["max_output_tokens"],
                                timeout_s=replay["provider"]["timeout_s"],
                            )
                            capture["calls"].append({**call, "prompt_sha256": prompt_hash})
                        call = capture["calls"][index]
                        if call["prompt_sha256"] != prompt_hash:
                            raise ValueError("Replay prompt hash mismatch for " + key)
                        answer, usage = call["response"], call["usage"]
                        if not isinstance(answer, str) or len(answer) > 8192:
                            raise ValueError("Captured response exceeds experiment text budget")
                        if not isinstance(usage, dict) or set(usage) != {"input_tokens", "output_tokens", "latency_ms"}:
                            raise ValueError("Missing per-call usage for " + key)
                        for metric, value in usage.items():
                            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                                raise ValueError("Invalid provider usage: " + metric)
                        if type(usage["input_tokens"]) is not int or type(usage["output_tokens"]) is not int:
                            raise ValueError("Token usage must be integer counts")
                        if usage["latency_ms"] > replay["provider"]["timeout_s"] * 1000:
                            raise ValueError("Captured latency exceeds provider deadline")
                        if usage["output_tokens"] > replay["provider"]["max_output_tokens"]:
                            raise ValueError("Captured output exceeds provider budget")
                    entry.update(response=answer, usage=usage)
                    return answer

                error = None
                try:
                    result = TesseraOrchestrator(engine, llm, information_need_variant=variant).run(scenario["task"], top_n=3)
                    result_dict = result.to_dict()
                    # Normalize only the temporary root; evidence IDs/hashes stay intact.
                    result_dict = json.loads(json.dumps(result_dict).replace(tmp, "$CORPUS"))
                    # Runtime timing is real but replay/mocks cannot estimate model latency.
                    if result.information_needs is not None:
                        result_dict["information_needs"]["measurement"]["elapsed_ms"] = None
                except InformationNeedsError as exc:
                    error, result_dict = exc.code, None
                if replay is not None:
                    # A replay mismatch/error must not look like provider validation failure.
                    if error == "provider_failure" or len(recorded) != len(capture["calls"]):
                        raise ValueError("Invalid/incomplete provider capture for " + key)
                rows.append({"id": key, "calls": recorded, "error": error, "result": result_dict})
    result = {
        "schema_version": 1, "fixture_sha256": fixture_hash,
        "mode": "mock_mechanics" if replay is None else "provider_replay",
        "quality_gate": "BLOCKED: independent facet/state/consumer-effort review and provider captures required",
        "contract_metrics": {
            variant: {
                "runs": len([r for r in rows if r["id"].endswith("/" + variant)]),
                "provider_callable_calls": sum(len(r["calls"]) for r in rows if r["id"].endswith("/" + variant)),
                "schema_errors": sum(r["error"] is not None for r in rows if r["id"].endswith("/" + variant)),
                "need_counts": [len(r["result"]["information_needs"]["needs"]) if variant != "N0" and r["result"] else None
                                for r in rows if r["id"].endswith("/" + variant)],
            } for variant in ("N0", "N1", "N2")
        },
        "quality_metrics": None,
        "provider_usage": None if replay is None else {
            metric: sum(call["usage"][metric] for row in rows for call in row["calls"])
            for metric in ("input_tokens", "output_tokens", "latency_ms")
        },
        "runs": rows,
    }
    if capture_fn is not None:
        result["provider_capture"] = replay
        result["mode"] = "provider_capture"
    if review is not None:
        if replay is None:
            raise ValueError("Mock results cannot receive an empirical quality score")
        result["quality_metrics"] = score_review(result, review)
        result["quality_gate"] = "PENDING: human N0/N1/N2 decision; no automatic KEEP decision"
    return result


def score_review(report, review):
    """Score independent annotations, not provider self-ratings or string overlap."""
    if review.get("fixture_sha256") != report["fixture_sha256"] or review.get("report_sha256") != digest(report["runs"]):
        raise ValueError("Review must bind exact fixture and provider-replay outputs")
    if not review.get("reviewer") or review.get("status") != "independently_reviewed":
        raise ValueError("Independent review provenance is required")
    if set(review.get("runs", {})) != {row["id"] for row in report["runs"]}:
        raise ValueError("Review must cover every scenario and variant")
    measurements = {"N0": [], "N1": [], "N2": []}
    fields = {
        "need_coverage", "unsupported_need_rate", "duplicate_need_rate",
        "evidence_recall_at_3", "state_accuracy", "no_memory_needed_accuracy",
        "missed_critical_facets", "agent_authored_search_formulations",
        "duplicate_formulations_across_repeated_runs",
    }
    for row in report["runs"]:
        annotation = review["runs"][row["id"]]
        if set(annotation) != fields:
            raise ValueError("Review metric fields are incomplete or unknown")
        for name, value in annotation.items():
            if value is None:
                continue  # Explicitly not applicable; never converted into zero.
            count = name in {"missed_critical_facets", "agent_authored_search_formulations", "duplicate_formulations_across_repeated_runs"}
            if type(value) not in (int, float) or not 0 <= value <= (10000 if count else 1):
                raise ValueError("Invalid reviewed metric: " + name)
            if count and type(value) is not int:
                raise ValueError("Count metric must be an integer")
        measurements[row["id"].split("/")[1]].append(annotation)
    return {variant: {metric: {"mean": statistics.mean(values) if values else None,
                               "applicable_runs": len(values)}
                      for metric in sorted(fields)
                      for values in [[r[metric] for r in annotations if r[metric] is not None]]}
            for variant, annotations in measurements.items()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--mock", action="store_true", help="Offline mechanics only; no quality decision")
    group.add_argument("--replay", type=Path, help="Application-captured provider responses and usage")
    parser.add_argument("--review", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    report = run_experiment(
        replay=json.loads(args.replay.read_text()) if args.replay else None,
        review=json.loads(args.review.read_text()) if args.review else None,
    )
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("mode", "contract_metrics", "quality_gate")}, indent=2))


if __name__ == "__main__":
    main()
