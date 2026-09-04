"""Offline tests for scripts/sync_project_board.py.

All GitHub access is mocked at the `run_gh` boundary so these tests never
require network access, `gh` authentication, or a real Project. See
docs/PROJECT_BOARD_SYNC.md for the field model this exercises.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import sync_project_board as sut  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures: portfolio routing bodies
# ---------------------------------------------------------------------------

READY_BLOCK = """## Executive takeaway

Some prose.

## Portfolio routing

- **Type:** executable Test Card
- **Status:** READY
- **Priority:** P0
- **Phase:** M1 — Configuration / Onboarding
- **Depends on:** none
- **Active blockers:** none
- **Benchmark applicability:** SMOKE_ONLY

## Decision question

More prose.
"""

BLOCKED_BLOCK = """## Portfolio routing

- **Type:** onboarding Test Card
- **Status:** BLOCKED
- **Priority:** P1
- **Phase:** M1 — Productization / Release
- **Depends on:** #155 init UX
- **Active blocker:** #155 only

## Decision question
"""

AUTHORITATIVE_SPLIT_BLOCK = """## Authoritative portfolio routing

> This block supersedes older status/dependency notes below.

- **Type:** split Test Card
- **Status:** P0 containment ready; full experiment blocked
- **Priority:** P0 containment / P1 research
- **Phase:** M0 then M4
- **Depends on:** containment: none; full supersession: #15, #73

<!-- PORTFOLIO-ROUTING:END -->

## Executive takeaway

Older historical notes that must not leak into parsed fields.
"""

TRACKER_BLOCK = """## Authoritative portfolio routing

- **Type:** epic / tracker
- **Status:** planned
- **Priority:** P1
- **Phase:** M3 — Retrieval & Graph

<!-- PORTFOLIO-ROUTING:END -->

## Executive takeaway
"""

DEFERRED_BLOCK = """## Authoritative portfolio routing

- **Type:** child executable Test Card
- **Status:** READY
- **Priority:** P1
- **Phase:** M3 — Retrieval & Graph
- **Depends on:** #96

<!-- PORTFOLIO-ROUTING:END -->
"""

NO_BLOCK = """## Executive takeaway

No portfolio routing block at all.
"""


def make_issue(number, title, body, state="OPEN", state_reason=None, milestone_number=None):
    return sut.Issue(
        number=number,
        title=title,
        body=body,
        state=state,
        state_reason=state_reason,
        milestone_number=milestone_number,
        url=f"https://github.com/LuigiFerronatto/tessera/issues/{number}",
    )


MILESTONES_BY_PHASE = {
    "M0": (1, "M0 — Contract & Safety"),
    "M1": (2, "M1 — Productization & Release"),
    "M2": (3, "M2 — Storage, Memory & Intelligence"),
    "M3": (4, "M3 — Retrieval & Graph"),
    "M4": (5, "M4 — Temporal & Trust"),
    "M5": (6, "M5 — Adaptive Learning & Agent Integration"),
}


def make_manifest(**overrides):
    base = dict(
        horizon_by_issue={155: "NOW"},
        queue_by_issue={155: 1},
        deferred_status_override=set(),
        trackers=set(),
        automation_title_prefixes=("[aw]",),
    )
    base.update(overrides)
    return sut.PortfolioManifest(**base)


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


class TestParsePortfolioRouting:
    def test_ready_block(self):
        routing = sut.parse_portfolio_routing(READY_BLOCK)
        assert routing.has_block
        assert routing.declared_status == "READY"
        assert routing.declared_priority == "P0"
        assert routing.declared_phase.startswith("M1")
        assert routing.depends_on == "none"
        assert routing.active_blockers == "none"

    def test_blocked_block_with_active_blocker(self):
        routing = sut.parse_portfolio_routing(BLOCKED_BLOCK)
        assert routing.declared_status == "BLOCKED"
        assert routing.active_blockers == "#155 only"

    def test_authoritative_block_stops_at_end_marker(self):
        routing = sut.parse_portfolio_routing(AUTHORITATIVE_SPLIT_BLOCK)
        assert routing.declared_status == "P0 containment ready; full experiment blocked"
        assert routing.declared_priority == "P0 containment / P1 research"
        assert "Older historical notes" not in (routing.routing_note or "")

    def test_no_block_returns_has_block_false(self):
        routing = sut.parse_portfolio_routing(NO_BLOCK)
        assert routing.has_block is False
        assert routing.declared_status is None

    def test_depends_on(self):
        routing = sut.parse_portfolio_routing(DEFERRED_BLOCK)
        assert routing.depends_on == "#96"


# ---------------------------------------------------------------------------
# Status classification
# ---------------------------------------------------------------------------


class TestClassifyStatus:
    def test_ready_no_blockers(self):
        routing = sut.parse_portfolio_routing(READY_BLOCK)
        issue = make_issue(155, "Init UX", READY_BLOCK)
        status, reasons = sut.classify_status(routing, issue, None, is_tracker=False, is_deferred_override=False)
        assert status == "Ready"
        assert "STATUS_READY_DECLARED" in reasons

    def test_blocked_dependency_open(self):
        routing = sut.parse_portfolio_routing(BLOCKED_BLOCK)
        issue = make_issue(118, "Onboarding", BLOCKED_BLOCK)
        status, reasons = sut.classify_status(
            routing, issue, None, is_tracker=False, is_deferred_override=False, open_issue_numbers=frozenset({155})
        )
        assert status == "Blocked"
        assert any("STATUS_BLOCKED_DEPENDENCY_OPEN" in r for r in reasons)

    def test_in_progress_with_active_draft_pr(self):
        routing = sut.parse_portfolio_routing(READY_BLOCK)
        issue = make_issue(155, "Init UX", READY_BLOCK)
        pr = sut.LinkedPr(number=201, is_draft=True, review_decision=None)
        status, reasons = sut.classify_status(routing, issue, pr, is_tracker=False, is_deferred_override=False)
        assert status == "In progress"
        assert "STATUS_IN_PROGRESS_DRAFT_PR_OPEN" in reasons

    def test_in_review_with_non_draft_pr(self):
        routing = sut.parse_portfolio_routing(READY_BLOCK)
        issue = make_issue(155, "Init UX", READY_BLOCK)
        pr = sut.LinkedPr(number=201, is_draft=False, review_decision="REVIEW_REQUIRED")
        status, reasons = sut.classify_status(routing, issue, pr, is_tracker=False, is_deferred_override=False)
        assert status == "In review"

    def test_done_when_closed_and_planned(self):
        routing = sut.parse_portfolio_routing(READY_BLOCK)
        issue = make_issue(155, "Init UX", READY_BLOCK, state="CLOSED", state_reason="COMPLETED")
        status, reasons = sut.classify_status(routing, issue, None, is_tracker=False, is_deferred_override=False)
        assert status == "Done"

    def test_dropped_maps_to_backlog_when_closed_not_planned(self):
        routing = sut.parse_portfolio_routing(READY_BLOCK)
        issue = make_issue(155, "Init UX", READY_BLOCK, state="CLOSED", state_reason="NOT_PLANNED")
        status, reasons = sut.classify_status(routing, issue, None, is_tracker=False, is_deferred_override=False)
        assert status == "Backlog"
        assert "STATUS_DROPPED_MAPPED_TO_BACKLOG_NO_NATIVE_OPTION" in reasons

    def test_deferred_maps_to_backlog(self):
        body = READY_BLOCK.replace("READY", "DEFERRED")
        routing = sut.parse_portfolio_routing(body)
        issue = make_issue(1, "x", body)
        status, reasons = sut.classify_status(routing, issue, None, is_tracker=False, is_deferred_override=False)
        assert status == "Backlog"
        assert "STATUS_DEFERRED_MAPPED_TO_BACKLOG_NO_NATIVE_OPTION" in reasons

    def test_deferred_override_forces_backlog_even_if_declared_ready(self):
        routing = sut.parse_portfolio_routing(DEFERRED_BLOCK)
        issue = make_issue(25, "graph expansion", DEFERRED_BLOCK)
        status, reasons = sut.classify_status(routing, issue, None, is_tracker=False, is_deferred_override=True)
        assert status == "Backlog"
        assert "STATUS_DEFERRED_OVERRIDE_MAPPED_TO_BACKLOG" in reasons

    def test_split_issue_16_like_status_is_ready(self):
        routing = sut.parse_portfolio_routing(AUTHORITATIVE_SPLIT_BLOCK)
        issue = make_issue(16, "Conflict resolution", AUTHORITATIVE_SPLIT_BLOCK)
        status, reasons = sut.classify_status(routing, issue, None, is_tracker=False, is_deferred_override=False)
        assert status == "Ready"

    def test_conditional_ready_blocked_when_referenced_issue_still_open(self):
        body = READY_BLOCK.replace("**Status:** READY", "**Status:** READY FOR DESIGN after #176 is accepted")
        routing = sut.parse_portfolio_routing(body)
        issue = make_issue(192, "Enrichment runtime", body)
        status, reasons = sut.classify_status(
            routing, issue, None, is_tracker=False, is_deferred_override=False, open_issue_numbers=frozenset({176})
        )
        assert status == "Blocked"
        assert any("STATUS_READY_CONDITIONAL_UNSATISFIED_DEPENDENCY_OPEN" in r for r in reasons)

    def test_conditional_ready_ready_when_referenced_issue_closed(self):
        body = READY_BLOCK.replace("**Status:** READY", "**Status:** READY FOR DESIGN after #176 is accepted")
        routing = sut.parse_portfolio_routing(body)
        issue = make_issue(192, "Enrichment runtime", body)
        status, reasons = sut.classify_status(
            routing, issue, None, is_tracker=False, is_deferred_override=False, open_issue_numbers=frozenset()
        )
        assert status == "Ready"
        assert any("STATUS_READY_CONDITIONAL_SATISFIED" in r for r in reasons)

    def test_conditional_ready_unverifiable_prose_falls_back_to_blocked(self):
        body = READY_BLOCK.replace("**Status:** READY", "**Status:** ready after baseline fixture is frozen")
        routing = sut.parse_portfolio_routing(body)
        issue = make_issue(138, "Episode construction", body)
        status, reasons = sut.classify_status(routing, issue, None, is_tracker=False, is_deferred_override=False)
        assert status == "Blocked"
        assert "STATUS_READY_CONDITIONAL_UNVERIFIABLE_CONSERVATIVE_BLOCKED" in reasons

    def test_blocked_text_stale_when_all_named_blockers_are_closed(self):
        routing = sut.parse_portfolio_routing(BLOCKED_BLOCK)
        issue = make_issue(118, "Onboarding", BLOCKED_BLOCK)
        status, reasons = sut.classify_status(
            routing, issue, None, is_tracker=False, is_deferred_override=False, open_issue_numbers=frozenset()
        )
        assert status == "Ready"
        assert any("STATUS_BLOCKED_TEXT_STALE_ALL_BLOCKERS_CLOSED" in r for r in reasons)

    def test_tracker_status_is_backlog(self):
        routing = sut.parse_portfolio_routing(TRACKER_BLOCK)
        issue = make_issue(14, "Epic", TRACKER_BLOCK)
        status, reasons = sut.classify_status(routing, issue, None, is_tracker=True, is_deferred_override=False)
        assert status == "Backlog"
        assert "TRACKER_STATUS_BACKLOG_NO_EXECUTION_QUEUE" in reasons

    def test_no_routing_block_falls_back_conservatively(self):
        routing = sut.parse_portfolio_routing(NO_BLOCK)
        issue = make_issue(999, "no block", NO_BLOCK)
        status, reasons = sut.classify_status(routing, issue, None, is_tracker=False, is_deferred_override=False)
        assert status == "Backlog"
        assert "STATUS_NO_ROUTING_BLOCK_CONSERVATIVE_BACKLOG_FALLBACK" in reasons


# ---------------------------------------------------------------------------
# Priority classification
# ---------------------------------------------------------------------------


class TestClassifyPriority:
    def test_p0(self):
        routing = sut.parse_portfolio_routing(READY_BLOCK)
        value, reasons = sut.classify_priority(routing)
        assert value == "P0"

    def test_p3_falls_back_to_p2_explicitly(self):
        body = READY_BLOCK.replace("**Priority:** P0", "**Priority:** P3")
        routing = sut.parse_portfolio_routing(body)
        value, reasons = sut.classify_priority(routing)
        assert value == "P2"
        assert "PRIORITY_P3_NOT_AVAILABLE_FALLBACK_P2" in reasons

    def test_not_declared(self):
        routing = sut.parse_portfolio_routing(NO_BLOCK)
        value, reasons = sut.classify_priority(routing)
        assert value is None
        assert reasons == ["PRIORITY_NOT_DECLARED"]

    def test_split_priority_takes_first_token(self):
        routing = sut.parse_portfolio_routing(AUTHORITATIVE_SPLIT_BLOCK)
        value, reasons = sut.classify_priority(routing)
        assert value == "P0"


# ---------------------------------------------------------------------------
# Milestone classification
# ---------------------------------------------------------------------------


class TestClassifyMilestone:
    def test_m1(self):
        routing = sut.parse_portfolio_routing(READY_BLOCK)
        number, title, reasons = sut.classify_milestone(routing, MILESTONES_BY_PHASE)
        assert number == 2
        assert title.startswith("M1")

    def test_cross_cutting_uses_first_phase(self):
        routing = sut.parse_portfolio_routing(AUTHORITATIVE_SPLIT_BLOCK)  # "M0 then M4"
        number, title, reasons = sut.classify_milestone(routing, MILESTONES_BY_PHASE)
        assert number == 1
        assert title.startswith("M0")

    def test_not_declared(self):
        routing = sut.parse_portfolio_routing(NO_BLOCK)
        number, title, reasons = sut.classify_milestone(routing, MILESTONES_BY_PHASE)
        assert number is None
        assert reasons == ["MILESTONE_NOT_DECLARED"]

    def test_phase_not_found_in_repo(self):
        body = READY_BLOCK.replace("M1 — Configuration", "M9 — Nonexistent")
        routing = sut.parse_portfolio_routing(body)
        number, title, reasons = sut.classify_milestone(routing, MILESTONES_BY_PHASE)
        assert number is None


# ---------------------------------------------------------------------------
# Portfolio manifest (Execution/Queue source)
# ---------------------------------------------------------------------------


class TestPortfolioManifest:
    def test_loads_real_manifest(self):
        manifest = sut.PortfolioManifest.load()
        assert manifest.horizon_by_issue[155] == "NOW"
        assert manifest.horizon_by_issue[135] == "NOW"
        assert manifest.horizon_by_issue[16] == "NOW"
        assert manifest.queue_by_issue[155] == 1
        assert manifest.queue_by_issue[135] == 2
        assert manifest.queue_by_issue[16] == 3
        assert 25 in manifest.deferred_status_override
        assert 14 in manifest.trackers

    def test_now_wip_is_exactly_three(self):
        manifest = sut.PortfolioManifest.load()
        now_issues = [n for n, h in manifest.horizon_by_issue.items() if h == "NOW"]
        assert len(now_issues) == 3

    def test_no_duplicate_queue_values(self):
        manifest = sut.PortfolioManifest.load()
        queues = list(manifest.queue_by_issue.values())
        assert len(queues) == len(set(queues))

    def test_issue_not_in_two_buckets(self, tmp_path):
        bad = tmp_path / "bad.yaml"
        bad.write_text(
            "now:\n  - issue: 1\n    queue: 1\nnext:\n  - issue: 1\n    queue: 2\n",
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="more than one horizon bucket"):
            sut.PortfolioManifest.load(bad)

    def test_duplicate_queue_detected(self, tmp_path):
        bad = tmp_path / "bad.yaml"
        bad.write_text(
            "now:\n  - issue: 1\n    queue: 1\nnext:\n  - issue: 2\n    queue: 1\n",
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="duplicate Queue"):
            sut.PortfolioManifest.load(bad)

    def test_is_automation(self):
        manifest = make_manifest()
        assert manifest.is_automation("[aw] Detection Runs")
        assert not manifest.is_automation("[M1 Init UX] Add interactive source selection")


# ---------------------------------------------------------------------------
# Full classify_issue integration (no GitHub access)
# ---------------------------------------------------------------------------


class TestClassifyIssue:
    def test_155_now_ready(self):
        manifest = make_manifest()
        issue = make_issue(155, "Init UX", READY_BLOCK)
        routing = sut.parse_portfolio_routing(READY_BLOCK)
        c = sut.classify_issue(issue, routing, manifest, None, MILESTONES_BY_PHASE)
        assert c.status == "Ready"
        assert c.horizon == "NOW"
        assert c.queue == 1
        assert c.priority == "P0"
        assert c.milestone_title.startswith("M1")

    def test_unscheduled_when_not_in_manifest(self):
        manifest = make_manifest()
        body = READY_BLOCK.replace("155", "9999")
        issue = make_issue(9999, "not scheduled", body)
        routing = sut.parse_portfolio_routing(body)
        c = sut.classify_issue(issue, routing, manifest, None, MILESTONES_BY_PHASE)
        assert c.horizon == "UNSCHEDULED"
        assert "EXECUTION_UNSCHEDULED_NOT_IN_PORTFOLIO_MANIFEST" in c.reasons

    def test_tracker_has_no_queue_or_horizon(self):
        manifest = make_manifest(trackers={14})
        issue = make_issue(14, "Epic", TRACKER_BLOCK)
        routing = sut.parse_portfolio_routing(TRACKER_BLOCK)
        c = sut.classify_issue(issue, routing, manifest, None, MILESTONES_BY_PHASE)
        assert c.is_tracker
        assert c.horizon is None
        assert c.queue is None
        assert c.status == "Backlog"


# ---------------------------------------------------------------------------
# WIP / Queue integrity validation
# ---------------------------------------------------------------------------


class TestValidatePlan:
    def _classification(self, issue, horizon, queue, is_tracker=False):
        return sut.Classification(issue=issue, title=str(issue), horizon=horizon, queue=queue, is_tracker=is_tracker)

    def test_wip_overflow_raises(self):
        classifications = [self._classification(n, "NOW", n) for n in (1, 2, 3, 4)]
        with pytest.raises(sut.PlanValidationError, match="WIP limit"):
            sut.validate_plan(classifications, now_wip_limit=3, allow_wip_overflow=False)

    def test_wip_overflow_allowed_with_override(self):
        classifications = [self._classification(n, "NOW", n) for n in (1, 2, 3, 4)]
        sut.validate_plan(classifications, now_wip_limit=3, allow_wip_overflow=True)  # no raise

    def test_trackers_do_not_count_toward_wip(self):
        classifications = [self._classification(n, "NOW", n) for n in (1, 2, 3)]
        classifications.append(self._classification(4, "NOW", None, is_tracker=True))
        sut.validate_plan(classifications, now_wip_limit=3, allow_wip_overflow=False)  # no raise

    def test_duplicate_queue_raises(self):
        classifications = [
            self._classification(1, "NOW", 1),
            self._classification(2, "NOW", 1),
        ]
        with pytest.raises(sut.PlanValidationError, match="Duplicate Queue"):
            sut.validate_plan(classifications, now_wip_limit=3, allow_wip_overflow=False)

    def test_negative_queue_raises(self):
        classifications = [self._classification(1, "NOW", -1)]
        with pytest.raises(sut.PlanValidationError, match="positive"):
            sut.validate_plan(classifications, now_wip_limit=3, allow_wip_overflow=False)

    def test_now_must_precede_next(self):
        classifications = [
            self._classification(1, "NOW", 5),
            self._classification(2, "NEXT", 1),
        ]
        with pytest.raises(sut.PlanValidationError, match="NOW queue positions"):
            sut.validate_plan(classifications, now_wip_limit=3, allow_wip_overflow=False)

    def test_missing_queue_allowed_for_later(self):
        classifications = [
            self._classification(1, "NOW", 1),
            self._classification(2, "LATER", None),
        ]
        sut.validate_plan(classifications, now_wip_limit=3, allow_wip_overflow=False)  # no raise


# ---------------------------------------------------------------------------
# Sync planning (diffing live vs desired)
# ---------------------------------------------------------------------------


class TestBuildPlan:
    def test_noop_when_live_matches_desired(self):
        c = sut.Classification(
            issue=155, title="x", status="Ready", horizon="NOW", queue=1, priority="P0", milestone_number=2
        )
        live = sut.LiveItem(item_id="ITEM1", status="Ready", horizon="NOW", queue=1.0, priority="P0")
        plan = sut.build_plan([c], {155: live}, {155: 2})
        assert plan[0].changes == []
        assert plan[0].milestone_change is None
        assert not plan[0].needs_add_to_project

    def test_detects_status_change(self):
        c = sut.Classification(issue=155, title="x", status="In progress")
        live = sut.LiveItem(item_id="ITEM1", status="Ready")
        plan = sut.build_plan([c], {155: live}, {})
        assert any(ch.field == "Status" and ch.after == "In progress" for ch in plan[0].changes)

    def test_detects_missing_item(self):
        c = sut.Classification(issue=155, title="x", status="Ready")
        plan = sut.build_plan([c], {}, {})
        assert plan[0].needs_add_to_project

    def test_detects_milestone_change(self):
        c = sut.Classification(issue=155, title="x", milestone_number=3)
        live = sut.LiveItem(item_id="ITEM1")
        plan = sut.build_plan([c], {155: live}, {155: 2})
        assert plan[0].milestone_change.after == 3

    def test_queue_float_vs_int_does_not_spuriously_diff(self):
        c = sut.Classification(issue=155, title="x", queue=1)
        live = sut.LiveItem(item_id="ITEM1", queue=1.0)
        plan = sut.build_plan([c], {155: live}, {})
        assert plan[0].changes == []


# ---------------------------------------------------------------------------
# Idempotency (dry-run twice with identical live state == zero changes)
# ---------------------------------------------------------------------------


class TestIdempotency:
    def test_second_dry_run_after_apply_state_is_zero_changes(self):
        manifest = make_manifest()
        issue = make_issue(155, "Init UX", READY_BLOCK)
        routing = sut.parse_portfolio_routing(READY_BLOCK)
        c = sut.classify_issue(issue, routing, manifest, None, MILESTONES_BY_PHASE)

        # Simulate live state now matching the classification exactly.
        live = sut.LiveItem(
            item_id="ITEM1",
            status=c.status,
            horizon=c.horizon,
            queue=float(c.queue) if c.queue is not None else None,
            priority=c.priority,
        )
        plan = sut.build_plan([c], {155: live}, {155: c.milestone_number})
        assert plan[0].changes == []
        assert plan[0].milestone_change is None


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


class TestRendering:
    def test_dry_run_json_roundtrips(self):
        c = sut.Classification(issue=155, title="Init UX", status="Ready", horizon="NOW", queue=1)
        live = sut.LiveItem(item_id=None)
        plan = sut.build_plan([c], {155: live}, {})
        payload = sut.render_json(plan, ignored=["#194 [aw] noise"], mode="dry-run")
        json.dumps(payload)  # must not raise
        assert payload["repository"] == "LuigiFerronatto/tessera"
        assert payload["summary"]["ignored"] == 1
        assert payload["items"][0]["issue"] == 155

    def test_dry_run_text_mentions_no_mutations(self):
        c = sut.Classification(issue=155, title="Init UX", status="Ready")
        live = sut.LiveItem(item_id="ITEM1", status="Ready")
        plan = sut.build_plan([c], {155: live}, {})
        text = sut.render_dry_run(plan, ignored=[], mode="dry-run")
        assert "No mutations performed." in text
        assert "Run with --apply" in text


# ---------------------------------------------------------------------------
# GraphQL / gh CLI plumbing (mocked subprocess boundary)
# ---------------------------------------------------------------------------


class TestGhCliPlumbing:
    def test_missing_gh_binary_raises(self, monkeypatch):
        monkeypatch.setattr(sut.shutil, "which", lambda name: None)
        with pytest.raises(sut.GhCliError, match="not found on PATH"):
            sut.check_auth()

    def test_missing_project_scope_raises(self, monkeypatch):
        monkeypatch.setattr(sut.shutil, "which", lambda name: "/usr/bin/gh")
        monkeypatch.setattr(sut, "run_gh", lambda args: "Logged in as x\nToken scopes: repo, read:org")
        with pytest.raises(sut.GhCliError, match="project"):
            sut.check_auth()

    def test_auth_ok_with_project_scope(self, monkeypatch):
        monkeypatch.setattr(sut.shutil, "which", lambda name: "/usr/bin/gh")
        monkeypatch.setattr(sut, "run_gh", lambda args: "Logged in as x\nToken scopes: repo, project")
        sut.check_auth()  # no raise

    def test_graphql_raises_on_error_payload(self, monkeypatch):
        monkeypatch.setattr(
            sut, "run_gh", lambda args, input_data=None: json.dumps({"errors": [{"message": "boom"}]})
        )
        with pytest.raises(sut.GhCliError, match="boom"):
            sut.graphql("query { x }")

    def test_graphql_returns_data_on_success(self, monkeypatch):
        monkeypatch.setattr(sut, "run_gh", lambda args, input_data=None: json.dumps({"data": {"ok": True}}))
        assert sut.graphql("query { x }") == {"ok": True}

    def test_run_gh_missing_binary(self, monkeypatch):
        def fake_run(*a, **k):
            raise FileNotFoundError()

        monkeypatch.setattr(sut.subprocess, "run", fake_run)
        with pytest.raises(sut.GhCliError, match="not found on PATH"):
            sut.run_gh(["auth", "status"])

    def test_run_gh_nonzero_exit_raises(self, monkeypatch):
        monkeypatch.setattr(
            sut.subprocess,
            "run",
            lambda *a, **k: SimpleNamespace(returncode=1, stdout="", stderr="bad scope"),
        )
        with pytest.raises(sut.GhCliError, match="bad scope"):
            sut.run_gh(["issue", "list"])


# ---------------------------------------------------------------------------
# Project schema discovery (mocked)
# ---------------------------------------------------------------------------


class TestDiscoverProjectSchema:
    def test_discovers_fields_and_options(self, monkeypatch):
        fixture = json.loads(
            (REPO_ROOT / "tests" / "fixtures" / "project_board_sync" / "project_fields.json").read_text()
        )
        monkeypatch.setattr(sut, "graphql", lambda query, **kw: fixture["data"])
        schema = sut.discover_project_schema()
        assert schema.project_id == "PVT_kwHOCdbSLs4BiQrN"
        status_field = schema.fields["Status"]
        assert status_field.options["Ready"] == "e18bf179"
        assert "Priority" in schema.fields

    def test_require_missing_field_raises_actionable_error(self):
        schema = sut.ProjectSchema(project_id="P1", fields={})
        with pytest.raises(sut.GhCliError, match="bootstrap-fields"):
            schema.require("Execution")


# ---------------------------------------------------------------------------
# Mutation guards
# ---------------------------------------------------------------------------


class TestApplySingleSelectGuards:
    def test_refuses_to_invent_missing_option(self):
        field = sut.ProjectField(field_id="F1", name="Status", data_type="SINGLE_SELECT", options={"Ready": "opt1"})
        schema = sut.ProjectSchema(project_id="P1", fields={"Status": field})
        with pytest.raises(sut.GhCliError, match="no option"):
            sut.apply_single_select(schema, "ITEM1", "Status", "Nonexistent")


# ---------------------------------------------------------------------------
# End-to-end classification against real fetched issue fixtures
# ---------------------------------------------------------------------------


class TestRealIssueFixtures:
    """Guards against parser regressions using real (frozen) issue bodies."""

    @pytest.fixture(autouse=True)
    def _load_fixture(self):
        path = REPO_ROOT / "tests" / "fixtures" / "project_board_sync" / "sample_issues.json"
        self.issues = json.loads(path.read_text())

    def _body(self, number):
        return next(i["body"] for i in self.issues if i["number"] == number)

    def test_155_declares_ready_p0_m1(self):
        routing = sut.parse_portfolio_routing(self._body(155))
        assert routing.declared_status == "READY"
        assert routing.declared_priority == "P0"
        assert routing.declared_phase.startswith("M1")

    def test_16_is_split_containment_ready(self):
        routing = sut.parse_portfolio_routing(self._body(16))
        assert "containment ready" in routing.declared_status.lower()

    def test_87_is_owner_decision_blocked(self):
        routing = sut.parse_portfolio_routing(self._body(87))
        assert "owner decision" in routing.declared_status.lower()

    def test_14_is_tracker_type(self):
        routing = sut.parse_portfolio_routing(self._body(14))
        assert "tracker" in (routing.declared_type or "").lower() or "epic" in (routing.declared_type or "").lower()

    def test_194_automation_has_no_routing_block(self):
        routing = sut.parse_portfolio_routing(self._body(194))
        assert routing.has_block is False
