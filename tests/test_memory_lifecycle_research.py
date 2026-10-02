"""Structural gates for the read-only #179 comparative research artifact."""
import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs" / "evidence" / "179-memory-lifecycle"
ALLOWED_OWNERS = {120, 121, 137, 138, 167, 168, 169, 171, 177, 178, 15, 16}
LABELS = {"code", "docs", "inference", "unknown"}


def load(name):
    return json.loads((EVIDENCE / name).read_text(encoding="utf-8"))


def test_five_systems_cover_ten_distinct_dimensions():
    matrix = load("matrix.json")
    assert matrix["audit_version"] == "1.0"
    assert matrix["issue"] == 179
    assert matrix["decision"] == "PENDING"
    assert len(matrix["dimensions"]) == len(set(matrix["dimensions"])) == 10
    assert {s["system"] for s in matrix["systems"]} == {
        "MemPalace", "Mem0", "MemOS", "Letta", "Graphiti"
    }
    for system in matrix["systems"]:
        assert system["scope"]
        assert [r["dimension"] for r in system["dimensions"]] == matrix["dimensions"]


def test_every_claim_has_label_sources_and_existing_owners():
    matrix = load("matrix.json")
    sources = {s["id"]: s for s in load("sources.json")["sources"]}
    used_owners = set()
    used_sources = set()
    for system in matrix["systems"]:
        code_claims = 0
        for row in system["dimensions"]:
            assert row["claims"] and row["owning_issues"]
            assert set(row["owning_issues"]) <= ALLOWED_OWNERS
            used_owners.update(row["owning_issues"])
            assert row["lesson"]["confidence"] == "inference"
            assert row["lesson"]["claim"]
            for claim in row["claims"]:
                assert claim["confidence"] in LABELS
                assert claim["claim"] and claim["sources"]
                assert set(claim["sources"]) <= sources.keys()
                used_sources.update(claim["sources"])
                code_claims += claim["confidence"] == "code"
        assert code_claims > 0
    assert used_owners == ALLOWED_OWNERS
    assert used_sources <= sources.keys()


def test_primary_sources_are_pinned_and_fingerprinted():
    manifest = load("sources.json")
    repos = {r["repo"]: r for r in manifest["repositories"]}
    assert len(repos) == 7
    assert repos["MemPalace/mempalace"]["observed_default_branch"] == "develop"
    for repo in repos.values():
        assert re.fullmatch(r"[0-9a-f]{40}", repo["sha"])
        assert repo["release_claim"] is False
    ids = []
    for source in manifest["sources"]:
        ids.append(source["id"])
        revision = repos[source["repository"]]["sha"]
        assert source["revision"] == revision
        assert source["url"] == (
            f'https://github.com/{source["repository"]}/blob/{revision}/{source["path"]}'
        )
        assert re.fullmatch(r"[0-9a-f]{64}", source["content_sha256"])
        assert source["bytes"] > 0 and source["lines"] > 0
        assert source["kind"] in {"code", "docs"}
    assert len(ids) == len(set(ids))


def test_wide_csv_contains_all_required_columns_and_systems():
    required = {
        "system", "hook events", "supported harnesses", "capture strategy",
        "read-before-reasoning", "write-after-learning", "raw source preservation",
        "structured memory", "vector store", "LLM role", "temporal model",
        "working context model", "concurrency/failure handling", "TESSERA lesson",
        "TESSERA owning issue", "source links / commit or revision",
        "confidence: code|docs|inference|unknown",
    }
    with (EVIDENCE / "matrix.csv").open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        assert set(reader.fieldnames) == required
        rows = list(reader)
    assert len(rows) == 5
    assert {r["system"] for r in rows} == {s["system"] for s in load("matrix.json")["systems"]}
    for row in rows:
        assert all(row[column] for column in required)


def test_owner_snapshot_and_historical_boundaries_are_explicit():
    owners = load("owners.json")
    assert {o["issue"] for o in owners["owners"]} == ALLOWED_OWNERS
    assert next(o for o in owners["owners"] if o["issue"] == 120)["state"] == "closed"
    report = (ROOT / "docs/research/MEMORY_LIFECYCLE_2026-10-02.md").read_text()
    for marker in (
        "unreleased", "v3.6.0", "extraction-only", "archive", "reference_time",
        "FEEDBACK_RECEIVED", "NOT_APPLICABLE", "PENDING", "No new issue",
        "No competitor package was installed", "not a reproduced bug",
    ):
        assert marker in report
    assert report.count("| Capture lifecycle |") == 5
    assert report.count("| Operational concerns |") == 5


def test_rendered_matrix_preserves_each_claim_and_source_link():
    report = (ROOT / "docs/research/MEMORY_LIFECYCLE_2026-10-02.md").read_text()
    sources = {s["id"]: s for s in load("sources.json")["sources"]}
    with (EVIDENCE / "matrix.csv").open(encoding="utf-8", newline="") as stream:
        exported = {r["system"]: r for r in csv.DictReader(stream)}
    for system in load("matrix.json")["systems"]:
        csv_text = " ".join(exported[system["system"]].values())
        for row in system["dimensions"]:
            assert row["lesson"]["claim"] in report
            assert row["lesson"]["claim"] in csv_text
            for claim in row["claims"]:
                assert claim["claim"].replace("|", " / ") in report
                assert claim["claim"] in csv_text
                assert f'**{claim["confidence"]}**: {claim["claim"]}'.replace("|", " / ") in report
                for source_id in claim["sources"]:
                    assert f'[{source_id}]({sources[source_id]["url"]})' in report
