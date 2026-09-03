#!/usr/bin/env python3
"""Deterministic, auditable sync of TESSERA issue portfolio routing to
GitHub Projects v2 (https://github.com/users/LuigiFerronatto/projects/9).

See docs/PROJECT_BOARD_SYNC.md for the full field model and architecture
decision. Summary:

    Status     -- operational state (Backlog/Blocked/Ready/In progress/
                  In review/Done). Derived from each issue's own
                  "## Portfolio routing" / "## Authoritative portfolio
                  routing" block, overlaid with live GitHub state
                  (closed/open, linked PR draft/review state).
    HORIZON    -- when we intend to pull the work (NOW/NEXT/LATER/
                  UNSCHEDULED). Derived from governance/portfolio_execution.yaml,
                  NOT from issue bodies and NOT from regex-parsing ROADMAP.md.
    Queue      -- ordinal position within HORIZON. Same source as HORIZON.
    Priority   -- P0/P1/P2 (P3 has no native Project option; see
                  PRIORITY_P3_FALLBACK_TO_P2). Derived from the issue's own
                  declared "**Priority:**" line.
    Milestone  -- native GitHub issue milestone (M0..M5), derived from the
                  issue's own declared "**Phase:**" line, using the FIRST
                  named phase for cross-cutting issues.

Safety contract:
  * default invocation (no flags) is a dry run; `--apply` is required to
    mutate anything.
  * never hard-codes ProjectV2/field/option/item node IDs; everything is
    discovered via `gh api graphql` at run time.
  * never invents Status/Execution/Priority/Milestone options; if a
    required Project field/option is missing, use --bootstrap-fields to
    create only the missing pieces (after showing exactly what will be
    created), otherwise fail with an actionable diagnostic.

Scope: this tool only reads/classifies/syncs currently OPEN issues. Closed
issues already on the board (Done/Dropped) are left untouched -- Execution/
Queue stop being meaningful once an issue is closed, and re-deriving Status
for closed issues risks clobbering a historical Done/Dropped card. The
`classify_status` function itself is closed-issue-aware (and unit-tested
that way) so it can be reused if this scope is ever deliberately widened,
but `main()` does not fetch or plan changes for closed issues today.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable, Optional

import yaml

REPO_OWNER = "LuigiFerronatto"
REPO_NAME = "tessera"
REPO = f"{REPO_OWNER}/{REPO_NAME}"
PROJECT_OWNER = "LuigiFerronatto"
PROJECT_NUMBER = 9

FIELD_STATUS = "Status"
FIELD_HORIZON = "HORIZON"
FIELD_QUEUE = "Queue"
FIELD_PRIORITY = "Priority"

DEFAULT_NOW_WIP_LIMIT = 3

AUTOMATION_STATUS_FALLBACK_PRIORITY = "P2"  # used only when P3 is declared

PORTFOLIO_YAML_PATH = Path(__file__).resolve().parent.parent / "governance" / "portfolio_execution.yaml"

STATUS_OPTIONS = ("Backlog", "Blocked", "Ready", "In progress", "In review", "Done")
HORIZON_OPTIONS = ("NOW", "NEXT", "LATER", "UNSCHEDULED")
PRIORITY_OPTIONS = ("P0", "P1", "P2")


# ---------------------------------------------------------------------------
# gh CLI / GraphQL plumbing
# ---------------------------------------------------------------------------


class GhCliError(RuntimeError):
    """Raised when the `gh` CLI is missing, unauthenticated, or under-scoped."""


def run_gh(args: list[str], *, input_data: Optional[str] = None) -> str:
    """Run a `gh` subcommand and return stdout, raising GhCliError on failure."""
    try:
        proc = subprocess.run(
            ["gh", *args],
            input=input_data,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise GhCliError(
            "GitHub CLI ('gh') was not found on PATH. Install it from "
            "https://cli.github.com/ before running this script."
        ) from exc
    if proc.returncode != 0:
        raise GhCliError(
            f"`gh {' '.join(args)}` failed (exit {proc.returncode}):\n{proc.stderr.strip()}"
        )
    return proc.stdout


def graphql(query: str, **variables: Any) -> dict:
    """Run a GraphQL query/mutation through `gh api graphql` and return `data`."""
    args = ["api", "graphql", "-f", f"query={query}"]
    for key, value in variables.items():
        if isinstance(value, bool):
            args += ["-F", f"{key}={'true' if value else 'false'}"]
        elif isinstance(value, (int, float)):
            args += ["-F", f"{key}={value}"]
        else:
            args += ["-f", f"{key}={value}"]
    out = run_gh(args)
    payload = json.loads(out)
    if "errors" in payload and payload["errors"]:
        raise GhCliError(f"GraphQL errors: {json.dumps(payload['errors'], indent=2)}")
    return payload["data"]


def check_auth() -> None:
    """Verify `gh` exists, is authenticated, and has the `project` scope."""
    if shutil.which("gh") is None:
        raise GhCliError(
            "GitHub CLI ('gh') was not found on PATH. Install it from "
            "https://cli.github.com/ before running this script."
        )
    try:
        status = run_gh(["auth", "status"])
    except GhCliError as exc:
        raise GhCliError(f"`gh auth status` failed: {exc}") from exc
    if "project" not in status:
        raise GhCliError(
            "GitHub CLI is authenticated, but the token may not have the "
            "'project' scope required to read/update Projects v2.\n\n"
            "Required permission:\n  project\n\n"
            "Try:\n  gh auth refresh -s project"
        )


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclasses.dataclass
class ProjectField:
    field_id: str
    name: str
    data_type: str
    options: dict[str, str] = dataclasses.field(default_factory=dict)  # name -> option id


@dataclasses.dataclass
class ProjectSchema:
    project_id: str
    fields: dict[str, ProjectField]  # by name

    def require(self, name: str) -> ProjectField:
        if name not in self.fields:
            raise GhCliError(
                f"Project field '{name}' was not found on Project #{PROJECT_NUMBER}.\n"
                f"Run with --bootstrap-fields to create only the missing fields, "
                f"after reviewing exactly what would be created."
            )
        return self.fields[name]


@dataclasses.dataclass
class Issue:
    number: int
    title: str
    body: str
    state: str  # OPEN / CLOSED
    state_reason: Optional[str]
    milestone_number: Optional[int]
    url: str


@dataclasses.dataclass
class LinkedPr:
    number: int
    is_draft: bool
    review_decision: Optional[str]


@dataclasses.dataclass
class PortfolioRouting:
    declared_type: Optional[str] = None
    declared_status: Optional[str] = None
    declared_priority: Optional[str] = None
    declared_phase: Optional[str] = None
    depends_on: Optional[str] = None
    active_blockers: Optional[str] = None
    routing_note: Optional[str] = None
    has_block: bool = False


@dataclasses.dataclass
class Classification:
    issue: int
    title: str
    status: Optional[str] = None
    horizon: Optional[str] = None
    queue: Optional[int] = None
    priority: Optional[str] = None
    milestone_number: Optional[int] = None
    milestone_title: Optional[str] = None
    reasons: list[str] = dataclasses.field(default_factory=list)
    ignored: bool = False
    is_tracker: bool = False


# ---------------------------------------------------------------------------
# Portfolio manifest (governance/portfolio_execution.yaml)
# ---------------------------------------------------------------------------


@dataclasses.dataclass
class PortfolioManifest:
    horizon_by_issue: dict[int, str]
    queue_by_issue: dict[int, int]
    deferred_status_override: set[int]
    trackers: set[int]
    automation_title_prefixes: tuple[str, ...]

    @classmethod
    def load(cls, path: Path = PORTFOLIO_YAML_PATH) -> "PortfolioManifest":
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        horizon_by_issue: dict[int, str] = {}
        queue_by_issue: dict[int, int] = {}
        for bucket_key, horizon_name in (
            ("now", "NOW"),
            ("next", "NEXT"),
            ("later", "LATER"),
        ):
            for entry in raw.get(bucket_key, []) or []:
                num = int(entry["issue"])
                if num in horizon_by_issue:
                    raise ValueError(
                        f"{path}: issue #{num} appears in more than one horizon bucket."
                    )
                horizon_by_issue[num] = horizon_name
                if "queue" in entry and entry["queue"] is not None:
                    queue_by_issue[num] = int(entry["queue"])
        queues = list(queue_by_issue.values())
        if len(queues) != len(set(queues)):
            dupes = sorted({q for q in queues if queues.count(q) > 1})
            raise ValueError(f"{path}: duplicate Queue values: {dupes}")
        return cls(
            horizon_by_issue=horizon_by_issue,
            queue_by_issue=queue_by_issue,
            deferred_status_override=set(int(x) for x in raw.get("deferred_status_override", []) or []),
            trackers=set(int(x) for x in raw.get("trackers", []) or []),
            automation_title_prefixes=tuple(raw.get("automation_title_prefixes", []) or []),
        )

    def is_automation(self, title: str) -> bool:
        return any(title.startswith(prefix) for prefix in self.automation_title_prefixes)


# ---------------------------------------------------------------------------
# Portfolio routing block parser
# ---------------------------------------------------------------------------

_ROUTING_HEADER_RE = re.compile(
    r"^##\s+(?:Authoritative portfolio routing|Portfolio routing)\s*$",
    re.MULTILINE,
)
_FIELD_RE = re.compile(r"^-\s+\*\*([^*:]+):\*\*\s*(.*)$")


def parse_portfolio_routing(body: str) -> PortfolioRouting:
    """Parse the authoritative "## Portfolio routing" block from an issue body.

    Stops at `<!-- PORTFOLIO-ROUTING:END -->` if present, otherwise at the
    next `##` heading, otherwise at end of string.
    """
    match = _ROUTING_HEADER_RE.search(body)
    if not match:
        return PortfolioRouting(has_block=False)

    rest = body[match.end():]
    end_marker = rest.find("<!-- PORTFOLIO-ROUTING:END -->")
    if end_marker != -1:
        block = rest[:end_marker]
    else:
        next_heading = re.search(r"^##\s+\S", rest, re.MULTILINE)
        block = rest[: next_heading.start()] if next_heading else rest

    fields: dict[str, str] = {}
    for line in block.splitlines():
        m = _FIELD_RE.match(line.strip())
        if m:
            key = m.group(1).strip().lower()
            fields[key] = m.group(2).strip()

    return PortfolioRouting(
        declared_type=fields.get("type"),
        declared_status=fields.get("status"),
        declared_priority=fields.get("priority"),
        declared_phase=fields.get("phase"),
        depends_on=fields.get("depends on"),
        active_blockers=fields.get("active blocker") or fields.get("active blockers"),
        routing_note=fields.get("routing note"),
        has_block=True,
    )


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------


def _extract_referenced_issues(text: Optional[str]) -> list[int]:
    if not text:
        return []
    return [int(n) for n in re.findall(r"#(\d+)", text)]


def classify_status(
    routing: PortfolioRouting,
    issue: Issue,
    linked_pr: Optional[LinkedPr],
    is_tracker: bool,
    is_deferred_override: bool,
    open_issue_numbers: frozenset[int] = frozenset(),
) -> tuple[Optional[str], list[str]]:
    """Return (status_option_name, reason_codes).

    `open_issue_numbers` is the set of currently-open issue numbers in the
    repository. It is used to check whether a declared blocker/conditional
    dependency is actually still open (live evidence overrides stale text
    per spec section 19/20: "se uma issue depende de outra que está
    fechada/VALIDATED, trate blocker como satisfeito").
    """
    reasons: list[str] = []


    if issue.state == "CLOSED":
        if issue.state_reason == "NOT_PLANNED":
            reasons.append("STATUS_DROPPED_MAPPED_TO_BACKLOG_NO_NATIVE_OPTION")
            return "Backlog", reasons
        reasons.append("STATUS_DONE_ISSUE_CLOSED")
        return "Done", reasons

    if linked_pr is not None:
        if linked_pr.is_draft:
            reasons.append("STATUS_IN_PROGRESS_DRAFT_PR_OPEN")
            return "In progress", reasons
        reasons.append("STATUS_IN_REVIEW_NON_DRAFT_PR_OPEN")
        return "In review", reasons

    declared = (routing.declared_status or "").strip().lower()

    if is_tracker or "tracker" in declared:
        reasons.append("TRACKER_STATUS_BACKLOG_NO_EXECUTION_QUEUE")
        return "Backlog", reasons

    if not routing.has_block:
        reasons.append("STATUS_NO_ROUTING_BLOCK_CONSERVATIVE_BACKLOG_FALLBACK")
        return "Backlog", reasons

    if is_deferred_override:
        reasons.append("STATUS_DEFERRED_OVERRIDE_MAPPED_TO_BACKLOG")
        return "Backlog", reasons

    if "deferred" in declared:
        reasons.append("STATUS_DEFERRED_MAPPED_TO_BACKLOG_NO_NATIVE_OPTION")
        return "Backlog", reasons

    if "ready" in declared and "blocked" in declared:
        # Split cards like #16: "P0 containment ready; full experiment
        # blocked". Surface as Ready -- the executable slice can start now
        # -- while preserving the split nuance in reasons rather than
        # silently discarding the still-blocked portion.
        reasons.append("STATUS_SPLIT_READY_PARTIAL_BLOCK declared=" + repr(declared))
        return "Ready", reasons

    if "blocked" in declared:
        blockers = _extract_referenced_issues(routing.active_blockers or routing.depends_on)
        still_open = [b for b in blockers if b in open_issue_numbers]
        if blockers and not still_open:
            reasons.append(f"STATUS_BLOCKED_TEXT_STALE_ALL_BLOCKERS_CLOSED blockers={blockers}")
            return "Ready", reasons
        if blockers:
            reasons.append(f"STATUS_BLOCKED_DEPENDENCY_OPEN blockers={still_open}")
        else:
            reasons.append("STATUS_BLOCKED_DECLARED")
        return "Blocked", reasons

    if "ready" in declared:
        # Watch for conditional qualifiers ("READY FOR X after #176 ...",
        # "ready after baseline fixture is frozen"): a bare "ready"
        # substring match is not enough evidence when the declared text
        # itself gates readiness behind something else. Prefer verifiable
        # live evidence (referenced issue closed) over an unconditional
        # match, and fall back to a conservative Blocked when the gate
        # cannot be verified rather than inventing readiness.
        conditional = re.search(r"\bafter\b", declared)
        if conditional:
            referenced = _extract_referenced_issues(declared)
            if referenced:
                still_open = [r for r in referenced if r in open_issue_numbers]
                if not still_open:
                    reasons.append(f"STATUS_READY_CONDITIONAL_SATISFIED refs={referenced}")
                    return "Ready", reasons
                reasons.append(f"STATUS_READY_CONDITIONAL_UNSATISFIED_DEPENDENCY_OPEN refs={still_open}")
                return "Blocked", reasons
            reasons.append("STATUS_READY_CONDITIONAL_UNVERIFIABLE_CONSERVATIVE_BLOCKED")
            return "Blocked", reasons
        reasons.append("STATUS_READY_DECLARED")
        return "Ready", reasons

    if declared in ("planned", "active"):
        reasons.append("STATUS_PLANNED_OR_ACTIVE_CONSERVATIVE_BACKLOG_FALLBACK")
        return "Backlog", reasons

    reasons.append("STATUS_UNRECOGNIZED_DECLARED_VALUE_CONSERVATIVE_BACKLOG_FALLBACK")
    return "Backlog", reasons


def classify_priority(routing: PortfolioRouting) -> tuple[Optional[str], list[str]]:
    if not routing.declared_priority:
        return None, ["PRIORITY_NOT_DECLARED"]
    m = re.search(r"P([0-3])", routing.declared_priority)
    if not m:
        return None, ["PRIORITY_UNPARSEABLE"]
    value = f"P{m.group(1)}"
    if value not in PRIORITY_OPTIONS:
        return (
            AUTOMATION_STATUS_FALLBACK_PRIORITY,
            [f"PRIORITY_{value}_NOT_AVAILABLE_FALLBACK_{AUTOMATION_STATUS_FALLBACK_PRIORITY}"],
        )
    return value, [f"PRIORITY_FROM_AUTHORITATIVE_DECLARATION={value}"]


def classify_milestone(
    routing: PortfolioRouting, milestones_by_phase: dict[str, tuple[int, str]]
) -> tuple[Optional[int], Optional[str], list[str]]:
    if not routing.declared_phase:
        return None, None, ["MILESTONE_NOT_DECLARED"]
    m = re.search(r"M([0-5])", routing.declared_phase)
    if not m:
        return None, None, ["MILESTONE_UNPARSEABLE_PHASE"]
    phase_key = f"M{m.group(1)}"
    if phase_key not in milestones_by_phase:
        return None, None, [f"MILESTONE_{phase_key}_NOT_FOUND_IN_REPO"]
    number, title = milestones_by_phase[phase_key]
    return number, title, [f"MILESTONE_FROM_AUTHORITATIVE_PHASE={phase_key} (primary of '{routing.declared_phase}')"]


def classify_issue(
    issue: Issue,
    routing: PortfolioRouting,
    manifest: PortfolioManifest,
    linked_pr: Optional[LinkedPr],
    milestones_by_phase: dict[str, tuple[int, str]],
    open_issue_numbers: frozenset[int] = frozenset(),
) -> Classification:
    is_tracker = issue.number in manifest.trackers
    is_deferred_override = issue.number in manifest.deferred_status_override

    status, status_reasons = classify_status(
        routing,
        issue,
        linked_pr,
        is_tracker=is_tracker,
        is_deferred_override=is_deferred_override,
        open_issue_numbers=open_issue_numbers,
    )

    horizon = manifest.horizon_by_issue.get(issue.number)
    queue = manifest.queue_by_issue.get(issue.number)
    horizon_reasons: list[str] = []
    if is_tracker:
        horizon = None
        queue = None
        horizon_reasons.append("TRACKER_NO_EXECUTION_QUEUE")
    elif horizon is None:
        horizon = "UNSCHEDULED"
        horizon_reasons.append("EXECUTION_UNSCHEDULED_NOT_IN_PORTFOLIO_MANIFEST")
    else:
        horizon_reasons.append(f"EXECUTION_{horizon}_CANONICAL_QUEUE_MANIFEST")

    priority, priority_reasons = classify_priority(routing)
    milestone_number, milestone_title, milestone_reasons = classify_milestone(routing, milestones_by_phase)

    return Classification(
        issue=issue.number,
        title=issue.title,
        status=status,
        horizon=horizon,
        queue=queue,
        priority=priority,
        milestone_number=milestone_number,
        milestone_title=milestone_title,
        reasons=[*status_reasons, *horizon_reasons, *priority_reasons, *milestone_reasons],
        is_tracker=is_tracker,
    )


# ---------------------------------------------------------------------------
# WIP / Queue integrity validation
# ---------------------------------------------------------------------------


class PlanValidationError(RuntimeError):
    pass


def validate_plan(classifications: list[Classification], now_wip_limit: int, allow_wip_overflow: bool) -> None:
    now_items = [c for c in classifications if c.horizon == "NOW" and not c.is_tracker]
    if len(now_items) > now_wip_limit and not allow_wip_overflow:
        issues = ", ".join(f"#{c.issue}" for c in now_items)
        raise PlanValidationError(
            f"NOW contains {len(now_items)} executable issues; configured WIP limit is "
            f"{now_wip_limit}.\n\nIssues:\n{issues}\n\n"
            f"Pass --allow-wip-overflow to bypass this check explicitly."
        )

    scheduled = [c for c in classifications if c.queue is not None]
    queues = [c.queue for c in scheduled]
    if len(queues) != len(set(queues)):
        dupes = sorted({q for q in queues if queues.count(q) > 1})
        raise PlanValidationError(f"Duplicate Queue values planned: {dupes}")
    if any(q <= 0 for q in queues):
        raise PlanValidationError("Queue values must be positive.")

    now_queues = [c.queue for c in classifications if c.horizon == "NOW" and c.queue is not None]
    next_queues = [c.queue for c in classifications if c.horizon == "NEXT" and c.queue is not None]
    later_queues = [c.queue for c in classifications if c.horizon == "LATER" and c.queue is not None]
    if now_queues and next_queues and max(now_queues) >= min(next_queues):
        raise PlanValidationError("NOW queue positions must all precede NEXT queue positions.")
    if next_queues and later_queues and max(next_queues) >= min(later_queues):
        raise PlanValidationError("NEXT queue positions must all precede LATER queue positions.")


# ---------------------------------------------------------------------------
# GitHub reading
# ---------------------------------------------------------------------------


def fetch_open_issues() -> list[Issue]:
    out = run_gh(
        [
            "issue", "list",
            "--repo", REPO,
            "--state", "open",
            "--limit", "500",
            "--json", "number,title,body,state,stateReason,milestone,url",
        ]
    )
    raw = json.loads(out)
    issues = []
    for item in raw:
        issues.append(
            Issue(
                number=item["number"],
                title=item["title"],
                body=item.get("body") or "",
                state=item["state"],
                state_reason=item.get("stateReason"),
                milestone_number=(item.get("milestone") or {}).get("number"),
                url=item["url"],
            )
        )
    return issues


def fetch_open_prs_by_closing_issue() -> dict[int, LinkedPr]:
    data = graphql(
        """
        query {
          repository(owner: "%s", name: "%s") {
            pullRequests(states: OPEN, first: 100) {
              nodes {
                number
                isDraft
                reviewDecision
                closingIssuesReferences(first: 10) { nodes { number } }
              }
            }
          }
        }
        """
        % (REPO_OWNER, REPO_NAME)
    )
    result: dict[int, LinkedPr] = {}
    for pr in data["repository"]["pullRequests"]["nodes"]:
        linked = LinkedPr(number=pr["number"], is_draft=pr["isDraft"], review_decision=pr.get("reviewDecision"))
        for ref in pr["closingIssuesReferences"]["nodes"]:
            result[ref["number"]] = linked
    return result


def fetch_repo_milestones_by_phase() -> dict[str, tuple[int, str]]:
    out = run_gh(["api", f"repos/{REPO}/milestones", "--jq", ". "])
    raw = json.loads(out)
    by_phase: dict[str, tuple[int, str]] = {}
    for m in raw:
        match = re.match(r"(M[0-5])\b", m["title"])
        if match:
            by_phase[match.group(1)] = (m["number"], m["title"])
    return by_phase


# ---------------------------------------------------------------------------
# Project discovery
# ---------------------------------------------------------------------------


def discover_project_schema() -> ProjectSchema:
    data = graphql(
        """
        query {
          user(login: "%s") {
            projectV2(number: %d) {
              id
              fields(first: 50) {
                nodes {
                  ... on ProjectV2FieldCommon { id name dataType }
                  ... on ProjectV2SingleSelectField { id name dataType options { id name } }
                }
              }
            }
          }
        }
        """
        % (PROJECT_OWNER, PROJECT_NUMBER)
    )
    project = data["user"]["projectV2"]
    fields: dict[str, ProjectField] = {}
    for node in project["fields"]["nodes"]:
        if "name" not in node:
            continue
        options = {opt["name"]: opt["id"] for opt in node.get("options", [])} if node.get("options") else {}
        fields[node["name"]] = ProjectField(
            field_id=node["id"], name=node["name"], data_type=node["dataType"], options=options
        )
    return ProjectSchema(project_id=project["id"], fields=fields)


@dataclasses.dataclass
class LiveItem:
    item_id: Optional[str]
    status: Optional[str] = None
    horizon: Optional[str] = None
    queue: Optional[float] = None
    priority: Optional[str] = None
    milestone_number: Optional[int] = None


def fetch_live_items(issue_numbers: list[int]) -> dict[int, LiveItem]:
    """Fetch each issue's Project #9 item id + current field values.

    Uses one GraphQL call per issue (issue.projectItems), which is simple,
    auditable, and avoids paginating the whole project when only a subset
    of issues is being synced.
    """
    result: dict[int, LiveItem] = {}
    for number in issue_numbers:
        data = graphql(
            """
            query {
              repository(owner: "%s", name: "%s") {
                issue(number: %d) {
                  projectItems(first: 10) {
                    nodes {
                      id
                      project { number }
                      fieldValues(first: 20) {
                        nodes {
                          __typename
                          ... on ProjectV2ItemFieldSingleSelectValue {
                            name
                            field { ... on ProjectV2FieldCommon { name } }
                          }
                          ... on ProjectV2ItemFieldNumberValue {
                            number
                            field { ... on ProjectV2FieldCommon { name } }
                          }
                        }
                      }
                    }
                  }
                }
              }
            }
            """
            % (REPO_OWNER, REPO_NAME, number)
        )
        nodes = data["repository"]["issue"]["projectItems"]["nodes"]
        match = next((n for n in nodes if n["project"]["number"] == PROJECT_NUMBER), None)
        if match is None:
            result[number] = LiveItem(item_id=None)
            continue
        live = LiveItem(item_id=match["id"])
        for fv in match["fieldValues"]["nodes"]:
            field_name = (fv.get("field") or {}).get("name")
            if field_name == FIELD_STATUS:
                live.status = fv.get("name")
            elif field_name == FIELD_HORIZON:
                live.horizon = fv.get("name")
            elif field_name == FIELD_QUEUE:
                live.queue = fv.get("number")
            elif field_name == FIELD_PRIORITY:
                live.priority = fv.get("name")
        result[number] = live
    return result


# ---------------------------------------------------------------------------
# Planning
# ---------------------------------------------------------------------------


@dataclasses.dataclass
class FieldChange:
    field: str
    before: Any
    after: Any


@dataclasses.dataclass
class PlannedItem:
    classification: Classification
    live: LiveItem
    changes: list[FieldChange]
    needs_add_to_project: bool
    milestone_change: Optional[FieldChange]


def build_plan(
    classifications: list[Classification],
    live_items: dict[int, LiveItem],
    live_milestones: dict[int, Optional[int]],
) -> list[PlannedItem]:
    plan: list[PlannedItem] = []
    for c in classifications:
        live = live_items.get(c.issue, LiveItem(item_id=None))
        changes: list[FieldChange] = []

        if c.status is not None and live.status != c.status:
            changes.append(FieldChange(FIELD_STATUS, live.status, c.status))
        if c.horizon is not None and live.horizon != c.horizon:
            changes.append(FieldChange(FIELD_HORIZON, live.horizon, c.horizon))

        live_queue_int = int(live.queue) if live.queue is not None else None
        if c.queue != live_queue_int:
            changes.append(FieldChange(FIELD_QUEUE, live_queue_int, c.queue))
        if c.priority is not None and live.priority != c.priority:
            changes.append(FieldChange(FIELD_PRIORITY, live.priority, c.priority))

        milestone_change = None
        current_milestone = live_milestones.get(c.issue)
        if c.milestone_number is not None and current_milestone != c.milestone_number:
            milestone_change = FieldChange("Milestone (issue)", current_milestone, c.milestone_number)

        plan.append(
            PlannedItem(
                classification=c,
                live=live,
                changes=changes,
                needs_add_to_project=(live.item_id is None),
                milestone_change=milestone_change,
            )
        )
    return plan


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def render_dry_run(plan: list[PlannedItem], ignored: list[str], mode: str) -> str:
    lines: list[str] = []
    lines.append("TESSERA Project Board Sync")
    lines.append("")
    lines.append(f"Project:\n  {PROJECT_OWNER} / Project #{PROJECT_NUMBER}")
    lines.append("")
    lines.append(f"Repository:\n  {REPO}")
    lines.append("")

    trackers = [p for p in plan if p.classification.is_tracker]
    executable = [p for p in plan if not p.classification.is_tracker]
    changed = [p for p in plan if p.changes or p.milestone_change or p.needs_add_to_project]
    noop = [p for p in plan if p not in changed]

    lines.append(f"Issues inspected: {len(plan) + len(ignored)}")
    lines.append(f"Executable issues: {len(executable)}")
    lines.append(f"Trackers: {len(trackers)}")
    lines.append(f"Automation issues ignored: {len(ignored)}")
    lines.append(f"No-op: {len(noop)}")
    lines.append(f"Changes planned: {len(changed)}")
    lines.append("")

    for p in changed:
        c = p.classification
        lines.append(f"#{c.issue} — {c.title[:60]}")
        if p.needs_add_to_project:
            lines.append(f"  #{c.issue} is not in Project #{PROJECT_NUMBER}")
            lines.append("  Action: add item")
        for ch in p.changes:
            lines.append(f"  {ch.field + ':':<12}{ch.before!r} → {ch.after!r}")
        if p.milestone_change:
            lines.append(
                f"  {'Milestone:':<12}{p.milestone_change.before!r} → {p.milestone_change.after!r}"
            )
        for reason in c.reasons:
            lines.append(f"    reason: {reason}")
        lines.append("")

    if mode == "dry-run":
        lines.append("No mutations performed.")
        lines.append("Run with --apply to synchronize.")
    return "\n".join(lines)


def render_json(plan: list[PlannedItem], ignored: list[str], mode: str) -> dict:
    changed = [p for p in plan if p.changes or p.milestone_change or p.needs_add_to_project]
    trackers = [p for p in plan if p.classification.is_tracker]
    items = []
    for p in plan:
        c = p.classification
        item_changes = {ch.field: {"from": ch.before, "to": ch.after} for ch in p.changes}
        if p.milestone_change:
            item_changes["Milestone"] = {
                "from": p.milestone_change.before,
                "to": p.milestone_change.after,
            }
        items.append(
            {
                "issue": c.issue,
                "classification": {
                    "status": c.status,
                    "execution": c.horizon,
                    "queue": c.queue,
                    "priority": c.priority,
                    "milestone": c.milestone_title,
                },
                "changes": item_changes,
                "add_to_project": p.needs_add_to_project,
                "reasons": c.reasons,
            }
        )
    return {
        "project": {"owner": PROJECT_OWNER, "number": PROJECT_NUMBER},
        "repository": REPO,
        "mode": mode,
        "summary": {
            "issues_inspected": len(plan) + len(ignored),
            "changes": len(changed),
            "noops": len(plan) - len(changed),
            "ignored": len(ignored),
            "trackers": len(trackers),
        },
        "items": items,
    }


# ---------------------------------------------------------------------------
# Mutation
# ---------------------------------------------------------------------------


def add_item_to_project(schema: ProjectSchema, issue_node_id: str) -> str:
    data = graphql(
        """
        mutation {
          addProjectV2ItemById(input: {projectId: "%s", contentId: "%s"}) {
            item { id }
          }
        }
        """
        % (schema.project_id, issue_node_id)
    )
    return data["addProjectV2ItemById"]["item"]["id"]


def apply_single_select(schema: ProjectSchema, item_id: str, field_name: str, option_name: str) -> None:
    field = schema.require(field_name)
    if option_name not in field.options:
        raise GhCliError(
            f"Project field '{field_name}' has no option '{option_name}'. "
            f"Known options: {sorted(field.options)}. Refusing to invent an option id."
        )
    graphql(
        """
        mutation {
          updateProjectV2ItemFieldValue(input: {
            projectId: "%s"
            itemId: "%s"
            fieldId: "%s"
            value: { singleSelectOptionId: "%s" }
          }) { projectV2Item { id } }
        }
        """
        % (schema.project_id, item_id, field.field_id, field.options[option_name])
    )


def apply_number(schema: ProjectSchema, item_id: str, field_name: str, value: int) -> None:
    field = schema.require(field_name)
    graphql(
        """
        mutation {
          updateProjectV2ItemFieldValue(input: {
            projectId: "%s"
            itemId: "%s"
            fieldId: "%s"
            value: { number: %d }
          }) { projectV2Item { id } }
        }
        """
        % (schema.project_id, item_id, field.field_id, value)
    )


def apply_issue_milestone(number: int, milestone_number: int) -> None:
    run_gh(["issue", "edit", str(number), "--repo", REPO, "--milestone", str(milestone_number)])


def apply_plan(
    schema: ProjectSchema,
    plan: list[PlannedItem],
    issue_node_ids: dict[int, str],
) -> tuple[list[int], list[tuple[int, str]]]:
    """Apply the plan. Returns (succeeded_issue_numbers, failed=(issue, error))."""
    succeeded: list[int] = []
    failed: list[tuple[int, str]] = []

    for p in plan:
        c = p.classification
        if not p.changes and not p.milestone_change and not p.needs_add_to_project:
            continue
        try:
            item_id = p.live.item_id
            if p.needs_add_to_project:
                item_id = add_item_to_project(schema, issue_node_ids[c.issue])

            for ch in p.changes:
                if ch.field == FIELD_QUEUE:
                    apply_number(schema, item_id, FIELD_QUEUE, ch.after)
                else:
                    apply_single_select(schema, item_id, ch.field, ch.after)

            if p.milestone_change:
                apply_issue_milestone(c.issue, p.milestone_change.after)

            succeeded.append(c.issue)
        except GhCliError as exc:
            failed.append((c.issue, str(exc)))

    return succeeded, failed


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def build_classifications(
    issues: list[Issue],
    manifest: PortfolioManifest,
    linked_prs: dict[int, LinkedPr],
    milestones_by_phase: dict[str, tuple[int, str]],
) -> tuple[list[Classification], list[str]]:
    classifications: list[Classification] = []
    ignored: list[str] = []
    open_issue_numbers = frozenset(i.number for i in issues if i.state == "OPEN")
    for issue in issues:
        if manifest.is_automation(issue.title):
            ignored.append(f"#{issue.number} {issue.title} (automation issue prefix)")
            continue
        routing = parse_portfolio_routing(issue.body)
        classification = classify_issue(
            issue, routing, manifest, linked_prs.get(issue.number), milestones_by_phase, open_issue_numbers
        )
        classifications.append(classification)
    return classifications, ignored


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="Apply the computed plan (default is dry-run).")
    parser.add_argument(
        "--dry-run", action="store_true", help="Explicit no-op flag: this is the default behavior anyway."
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON to stdout.")
    parser.add_argument(
        "--now-wip-limit", type=int, default=DEFAULT_NOW_WIP_LIMIT, help="Max executable issues allowed in NOW."
    )
    parser.add_argument(
        "--allow-wip-overflow", action="store_true", help="Bypass the NOW WIP-limit validation error explicitly."
    )
    parser.add_argument(
        "--bootstrap-fields", action="store_true", help="Create only missing Project fields/options (not implemented for existing-schema TESSERA project; reserved for future use)."
    )
    args = parser.parse_args(argv)
    mode = "apply" if args.apply else "dry-run"

    try:
        check_auth()

        manifest = PortfolioManifest.load()
        issues = fetch_open_issues()
        linked_prs = fetch_open_prs_by_closing_issue()
        milestones_by_phase = fetch_repo_milestones_by_phase()

        classifications, ignored = build_classifications(issues, manifest, linked_prs, milestones_by_phase)

        validate_plan(classifications, args.now_wip_limit, args.allow_wip_overflow)

        numbers = [c.issue for c in classifications]
        live_items = fetch_live_items(numbers)
        live_milestones = {i.number: i.milestone_number for i in issues}

        plan = build_plan(classifications, live_items, live_milestones)

        if args.apply:
            schema = discover_project_schema()
            issue_node_ids = {}
            needs_ids = [p.classification.issue for p in plan if p.needs_add_to_project]
            if needs_ids:
                data = graphql(
                    """
                    query {
                      repository(owner: "%s", name: "%s") {
                        %s
                      }
                    }
                    """
                    % (
                        REPO_OWNER,
                        REPO_NAME,
                        " ".join(f'i{n}: issue(number: {n}) {{ id }}' for n in needs_ids),
                    )
                )
                for n in needs_ids:
                    issue_node_ids[n] = data["repository"][f"i{n}"]["id"]

            succeeded, failed = apply_plan(schema, plan, issue_node_ids)
            if args.json:
                print(json.dumps({"mode": "apply", "succeeded": succeeded, "failed": failed}, indent=2))
            else:
                print(f"Applied {len(succeeded)} item(s); {len(failed)} failure(s).", file=sys.stderr)
                for issue_number, err in failed:
                    print(f"  FAILED #{issue_number}: {err}", file=sys.stderr)
            return 1 if failed else 0

        if args.json:
            print(json.dumps(render_json(plan, ignored, mode), indent=2))
        else:
            print(render_dry_run(plan, ignored, mode))
        return 0

    except (GhCliError, PlanValidationError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
