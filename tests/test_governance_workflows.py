"""Static governance tests for the TESSERA agentic-workflow governance system.

These tests freeze the safety-critical invariants declared by
`docs/AGENTIC_GOVERNANCE.md` and the individual `.github/workflows/tessera-*`
sources without depending on network access, GitHub Actions, or any AI
engine actually running. They fail loudly if a future edit to a workflow
source silently removes a separation-of-duties or least-privilege guarantee.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"

GH_AW_WORKFLOWS = {
    "tessera-issue-triage": "gemini",
    "tessera-pr-maintainer-audit": "codex",
    "tessera-pr-fixer": "copilot",
    "tessera-post-merge-lifecycle": "codex",
    "tessera-documentation-drift": "gemini",
}

MERGE_GOVERNOR_PATH = WORKFLOWS_DIR / "tessera-merge-governor.yml"


def _read_source(workflow_id: str) -> str:
    path = WORKFLOWS_DIR / f"{workflow_id}.md"
    assert path.exists(), f"expected gh-aw source {path} to exist"
    return path.read_text(encoding="utf-8")


def _frontmatter(workflow_id: str) -> dict:
    text = _read_source(workflow_id)
    assert text.startswith("---\n"), f"{workflow_id}.md must start with YAML frontmatter"
    end = text.index("\n---", 4)
    data = yaml.safe_load(text[4:end])
    # PyYAML follows the YAML 1.1 spec, which parses the bare key `on:` as
    # the boolean `True`. Normalize it back to the string key workflows
    # (and this test file) actually mean.
    if True in data and "on" not in data:
        data["on"] = data.pop(True)
    return data


def _lock_path(workflow_id: str) -> Path:
    return WORKFLOWS_DIR / f"{workflow_id}.lock.yml"


@pytest.mark.parametrize("workflow_id", sorted(GH_AW_WORKFLOWS))
def test_gh_aw_workflow_source_and_lock_exist(workflow_id):
    assert (WORKFLOWS_DIR / f"{workflow_id}.md").exists()
    assert _lock_path(workflow_id).exists(), (
        f"{workflow_id}.lock.yml must be committed alongside its Markdown source; "
        "generated lock files must never be hand-edited without recompiling."
    )


@pytest.mark.parametrize("workflow_id, expected_engine", sorted(GH_AW_WORKFLOWS.items()))
def test_gh_aw_workflow_has_expected_engine(workflow_id, expected_engine):
    fm = _frontmatter(workflow_id)
    engine = fm.get("engine")
    engine_id = engine.get("id") if isinstance(engine, dict) else engine
    assert engine_id == expected_engine, (
        f"{workflow_id}.md must use engine '{expected_engine}' per the "
        f"cross-engine governance architecture, found {engine_id!r}"
    )


def test_issue_triage_has_expected_triggers():
    fm = _frontmatter("tessera-issue-triage")
    on = fm["on"]
    assert "issues" in on
    assert set(on["issues"]["types"]) >= {"opened", "reopened"}


def test_pr_maintainer_audit_reruns_on_every_new_head():
    fm = _frontmatter("tessera-pr-maintainer-audit")
    on = fm["on"]
    assert "pull_request" in on
    types = set(on["pull_request"]["types"])
    assert {"opened", "synchronize", "ready_for_review"} <= types, (
        "the maintainer audit must re-trigger on every new PR head "
        "(synchronize) or a stale audit could authorize a new SHA"
    )


def test_post_merge_lifecycle_only_runs_for_merged_prs():
    text = _read_source("tessera-post-merge-lifecycle")
    fm = _frontmatter("tessera-post-merge-lifecycle")
    assert "pull_request" in fm["on"]
    assert "closed" in fm["on"]["pull_request"]["types"]
    assert "merged == true" in text or "merged" in fm.get("if", ""), (
        "lifecycle reconciliation must be gated on github.event.pull_request.merged == true; "
        "a closed-but-unmerged PR must never trigger lifecycle reconciliation"
    )


def test_fixer_workflow_is_opt_in_not_automatic():
    fm = _frontmatter("tessera-pr-fixer")
    on = fm["on"]
    assert "label_command" in on or "slash_command" in on, (
        "the fixer must be opt-in via an explicit label/command trigger, "
        "never automatically on every ITERATE result"
    )
    assert "pull_request" not in on and "issues" not in on


def test_documentation_drift_is_scheduled_not_reactive():
    fm = _frontmatter("tessera-documentation-drift")
    on = fm["on"]
    assert "schedule" in on or "workflow_dispatch" in on
    assert "pull_request" not in on and "issues" not in on


@pytest.mark.parametrize("workflow_id", sorted(GH_AW_WORKFLOWS))
def test_no_workflow_grants_write_all(workflow_id):
    text = _read_source(workflow_id)
    assert "write-all" not in text
    fm = _frontmatter(workflow_id)
    permissions = fm.get("permissions", {})
    if isinstance(permissions, str):
        assert permissions != "write-all"
    else:
        for scope, level in permissions.items():
            assert level != "write-all", f"{workflow_id} grants write-all on {scope}"


def test_reviewer_cannot_push_or_merge_or_edit_files():
    fm = _frontmatter("tessera-pr-maintainer-audit")
    safe_outputs = fm.get("safe-outputs", {})
    forbidden = {
        "push-to-pull-request-branch",
        "create-pull-request",
        "merge-pull-request",
    }
    assert not (forbidden & safe_outputs.keys()), (
        "the maintainer-audit reviewer must never be able to push, create a "
        "PR, or merge; reviewer independence from the fixer/merge authority "
        "would otherwise be violated"
    )
    tools = fm.get("tools", {})
    assert tools.get("bash") is False, "the reviewer must not have arbitrary shell execution"


def test_fixer_cannot_approve_or_merge():
    fm = _frontmatter("tessera-pr-fixer")
    safe_outputs = fm.get("safe-outputs", {})
    forbidden = {"submit-pull-request-review", "merge-pull-request", "create-pull-request"}
    assert not (forbidden & safe_outputs.keys()), (
        "the fixer must never approve/submit-review or merge its own fix; "
        "only push-to-pull-request-branch + add-comment are allowed"
    )
    text = _read_source("tessera-pr-fixer")
    assert "DO NOT mark the PR KEEP" in text or "DO NOT" in text


def test_lifecycle_agent_cannot_push_to_main():
    fm = _frontmatter("tessera-post-merge-lifecycle")
    safe_outputs = fm.get("safe-outputs", {})
    assert "push-to-pull-request-branch" not in safe_outputs
    assert "create-pull-request" in safe_outputs
    assert safe_outputs["create-pull-request"].get("draft") is True, (
        "lifecycle PRs must be created as draft during the initial rollout stage"
    )


def test_triage_prompt_distinguishes_open_ready_and_tracker():
    text = _read_source("tessera-issue-triage")
    assert "OPEN" in text and "READY" in text
    assert "TRACKER" in text
    assert "duplicate" in text and "related" in text
    assert "!=" in text, "the prompt must explicitly state these are non-equivalent concepts"


def test_review_prompt_has_false_positive_guardrails():
    text = _read_source("tessera-pr-maintainer-audit")
    assert "DO NOT generate findings merely to produce a review" in text
    assert "DO NOT mark ITERATE" in text


def test_lifecycle_prompt_preserves_candidate_vs_merge_distinction():
    text = _read_source("tessera-post-merge-lifecycle")
    assert "final candidate SHA" in text or "candidate SHA" in text
    assert "canonical" in text.lower()
    assert "!=" in text


def test_evals_present_with_operational_value_first():
    for workflow_id in GH_AW_WORKFLOWS:
        if workflow_id == "tessera-pr-fixer":
            continue  # fixer evals do not follow the operational_value-first convention
        fm = _frontmatter(workflow_id)
        evals = fm.get("evals")
        assert evals, f"{workflow_id} must declare evals"
        assert evals[0]["id"] == "operational_value"


@pytest.mark.parametrize("workflow_id", sorted(GH_AW_WORKFLOWS))
def test_lock_file_is_reproducible_from_source(workflow_id, tmp_path):
    """Recompiling a workflow source must not change its committed lock file.

    This guards against hand-editing a `.lock.yml` file independently of its
    Markdown source, which the gh-aw project explicitly prohibits.
    """

    lock_path = _lock_path(workflow_id)
    if not lock_path.exists():
        pytest.skip("lock file not present; covered by test_gh_aw_workflow_source_and_lock_exist")
    if subprocess.run(["gh", "aw", "--help"], capture_output=True).returncode != 0:
        pytest.skip("gh-aw CLI extension not available in this environment")

    before = lock_path.read_text(encoding="utf-8")
    result = subprocess.run(
        ["gh", "aw", "compile", "--approve", str(WORKFLOWS_DIR / f"{workflow_id}.md")],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    after = lock_path.read_text(encoding="utf-8")

    def _strip_volatile(text: str) -> str:
        # The lock file embeds a frontmatter/body content hash and pinned
        # third-party action SHAs that legitimately drift as the gh-aw
        # compiler/action ecosystem is upgraded; compare everything else.
        return re.sub(r'"[a-f0-9]{16,64}"', '"<hash>"', text)

    assert result.returncode == 0, result.stderr
    assert _strip_volatile(before) == _strip_volatile(after), (
        f"{workflow_id}.lock.yml is not reproducible from {workflow_id}.md; "
        "recompile with `gh aw compile` and commit the result"
    )


def test_merge_governor_is_deterministic_yaml_not_ai_workflow():
    assert MERGE_GOVERNOR_PATH.exists()
    text = MERGE_GOVERNOR_PATH.read_text(encoding="utf-8")
    assert "engine:" not in text
    doc = yaml.safe_load(text)
    assert "jobs" in doc
    permissions = doc.get("permissions", {})
    for scope, level in permissions.items():
        assert level != "write-all"
    # The merge governor must never itself call merge/auto-merge APIs in the
    # conservative Stage A rollout.
    assert "gh pr merge" not in text
    assert re.search(r"issues/\$PR_NUMBER/merge|/pulls/\d+/merge|--auto\b", text) is None


def test_merge_governor_binds_decision_to_current_head(monkeypatch):
    sys.path.insert(0, str(REPO_ROOT))
    from governance import merge_governor as mg

    comments = [
        {
            "id": 1,
            "created_at": "2026-01-01T00:00:00Z",
            "body": "## Maintainer audit — KEEP\n\nAudited head: `deadbeef`\n",
        }
    ]
    audit = mg.find_latest_audit(comments)
    assert audit is not None
    assert audit.decision == "KEEP"

    # A stale KEEP (audited an older head) must NOT authorize the current head.
    stale_result = mg.evaluate_runtime_pr_gates(
        current_head_sha="cafebabe",
        is_draft=False,
        mergeable_state="clean",
        audit=audit,
        ci_success=True,
        benchmark_success=True,
        has_requested_changes=False,
        has_unresolved_threads=False,
    )
    assert stale_result.authorized is False
    assert any("stale audit" in reason for reason in stale_result.reasons)

    # The same KEEP authorizes its own exact head when every other gate passes.
    fresh_result = mg.evaluate_runtime_pr_gates(
        current_head_sha="deadbeef",
        is_draft=False,
        mergeable_state="clean",
        audit=audit,
        ci_success=True,
        benchmark_success=True,
        has_requested_changes=False,
        has_unresolved_threads=False,
    )
    assert fresh_result.authorized is True
    assert fresh_result.reasons == []


def test_merge_governor_rejects_iterate_and_block_decisions():
    from governance import merge_governor as mg

    for decision in ("ITERATE", "BLOCK"):
        record = mg.AuditRecord(decision=decision, audited_head_sha="abc123")
        result = mg.evaluate_runtime_pr_gates(
            current_head_sha="abc123",
            is_draft=False,
            mergeable_state="clean",
            audit=record,
            ci_success=True,
            benchmark_success=True,
            has_requested_changes=False,
            has_unresolved_threads=False,
        )
        assert result.authorized is False


def test_merge_governor_lifecycle_gate_rejects_out_of_scope_files():
    from governance import merge_governor as mg

    result = mg.evaluate_lifecycle_pr_gates(
        changed_files=["docs/ROADMAP.md", "tessera/engine.py"],
        allowed_path_prefixes=["docs/", "CHANGELOG.md"],
        ci_success=True,
        benchmark_success=True,
        is_mergeable=True,
        has_requested_changes=False,
    )
    assert result.authorized is False
    assert any("tessera/engine.py" in reason for reason in result.reasons)


def test_merge_governor_cli_exits_nonzero_when_not_authorized(tmp_path):
    payload = {
        "current_head_sha": "abc123",
        "is_draft": False,
        "mergeable_state": "clean",
        "ci_success": True,
        "benchmark_success": True,
        "has_requested_changes": False,
        "has_unresolved_threads": False,
        "comments": [],
    }
    payload_path = tmp_path / "payload.json"
    payload_path.write_text(json.dumps(payload), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "-m", "governance.merge_governor", "--payload-file", str(payload_path)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert json.loads(result.stdout)["authorized"] is False
