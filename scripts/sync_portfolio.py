#!/usr/bin/env python3
"""Audit and synchronize TESSERA's native GitHub Issue relationships.

The audited relationship model lives in ``docs/portfolio-relationships.yaml``.
Running this command is read-only unless ``--apply`` is supplied::

    python scripts/sync_portfolio.py relationships
    python scripts/sync_portfolio.py relationships --apply

``blocked_by`` is the canonical directed dependency edge. GitHub derives the
inverse ``blocking`` view; this tool never stores or mutates a second copy.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional, Sequence

import yaml


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL = ROOT / "docs" / "portfolio-relationships.yaml"
API_VERSION = "2022-11-28"
AUTO_ISSUE_PREFIXES = ("[aw]", "[lifecycle]")
REASON_CODES = {
    "ACTIVE_BLOCKER",
    "ARCHITECTURAL_RELATION",
    "AUTHORITATIVE_COORDINATES_WITH",
    "AUTHORITATIVE_DEPENDS_ON",
    "EXPLICIT_EPIC_CHILD",
    "EXPLICIT_PARENT",
    "REMAINING_BLOCKER",
    "RESEARCH_RELATION",
    "ROADMAP_DEPENDENCY",
    "SPLIT_SCOPE_NOT_NATIVE_BLOCKER",
    "TRACKER_RELATION",
}


class SyncError(RuntimeError):
    """A safe, user-facing synchronization failure."""


@dataclass(frozen=True, order=True)
class RelationEvidence:
    issue: int
    reason_code: str
    source: str


@dataclass(frozen=True)
class IssueRelations:
    issue_number: int
    parent: Optional[RelationEvidence] = None
    blocked_by: tuple[RelationEvidence, ...] = ()
    relates_to: tuple[RelationEvidence, ...] = ()


@dataclass(frozen=True)
class IssueRecord:
    number: int
    database_id: int
    node_id: str
    title: str
    state: str
    body: str


@dataclass(frozen=True)
class CurrentRelations:
    parent: Optional[int] = None
    blocked_by: frozenset[int] = frozenset()
    relates_to: frozenset[int] = frozenset()


@dataclass
class IssuePlan:
    issue_number: int
    parent_add: Optional[int] = None
    parent_remove: Optional[int] = None
    blocked_add: set[int] = field(default_factory=set)
    blocked_remove: set[int] = field(default_factory=set)
    relates_add: set[int] = field(default_factory=set)
    relates_remove: set[int] = field(default_factory=set)

    @property
    def changed(self) -> bool:
        return any(
            (
                self.parent_add is not None,
                self.parent_remove is not None,
                self.blocked_add,
                self.blocked_remove,
                self.relates_add,
                self.relates_remove,
            )
        )


@dataclass(frozen=True)
class PortfolioModel:
    repository: str
    inspected: tuple[int, ...]
    ignored_prefixes: tuple[str, ...]
    relations: Mapping[int, IssueRelations]

    @classmethod
    def load(cls, path: Path) -> "PortfolioModel":
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        if raw.get("schema_version") != 1:
            raise SyncError(f"unsupported relationship schema in {path}")

        relation_map: dict[int, IssueRelations] = {}
        for raw_number, raw_relations in (raw.get("issues") or {}).items():
            number = int(raw_number)
            parent = _evidence(raw_relations.get("parent"))
            blocked = tuple(_evidence(item) for item in raw_relations.get("blocked_by", []))
            relates = tuple(_evidence(item) for item in raw_relations.get("relates_to", []))
            relation_map[number] = IssueRelations(number, parent, blocked, relates)

        # Relates-to is undirected. Store each edge once in YAML, then project it
        # onto both issues for comparison with GitHub's symmetric view.
        for number, relations in tuple(relation_map.items()):
            for edge in relations.relates_to:
                reverse = relation_map.get(edge.issue, IssueRelations(edge.issue))
                if any(item.issue == number for item in reverse.relates_to):
                    raise SyncError(
                        f"relates-to edge #{number}<->#{edge.issue} is stored twice; "
                        "keep one canonical declaration"
                    )
                relation_map[edge.issue] = IssueRelations(
                    reverse.issue_number,
                    reverse.parent,
                    reverse.blocked_by,
                    reverse.relates_to
                    + (RelationEvidence(number, edge.reason_code, edge.source),),
                )

        model = cls(
            repository=str(raw["repository"]),
            inspected=tuple(int(number) for number in raw["scope"]["issue_numbers"]),
            ignored_prefixes=tuple(raw["scope"].get("ignored_title_prefixes", AUTO_ISSUE_PREFIXES)),
            relations=relation_map,
        )
        model.validate()
        return model

    def desired(self, issue_number: int) -> IssueRelations:
        return self.relations.get(issue_number, IssueRelations(issue_number))

    def validate(self) -> None:
        inspected = set(self.inspected)
        if len(inspected) != len(self.inspected):
            raise SyncError("scope.issue_numbers contains duplicates")

        parent_edges: dict[int, int] = {}
        dependency_edges: dict[int, set[int]] = {}
        for number, relations in self.relations.items():
            if number not in inspected:
                raise SyncError(f"issue #{number} has relations but is outside the inspected scope")
            targets = []
            if relations.parent:
                targets.append(relations.parent.issue)
                parent_edges[number] = relations.parent.issue
            blocked_targets = {edge.issue for edge in relations.blocked_by}
            dependency_edges[number] = blocked_targets
            targets.extend(blocked_targets)
            targets.extend(edge.issue for edge in relations.relates_to)
            if number in targets:
                raise SyncError(f"issue #{number} has a self relationship")
            if len(targets) != len(set(targets)):
                raise SyncError(f"issue #{number} repeats a target across relationship types")
            for edge in _all_evidence(relations):
                if not edge.reason_code or not edge.source:
                    raise SyncError(f"issue #{number} has relationship evidence without rationale")
                if edge.issue not in inspected:
                    raise SyncError(
                        f"issue #{number} targets #{edge.issue}, which is outside the inspected scope"
                    )
                if edge.reason_code not in REASON_CODES:
                    raise SyncError(
                        f"issue #{number} uses unknown reason code {edge.reason_code!r}"
                    )

        for start in parent_edges:
            seen: set[int] = set()
            current = start
            while current in parent_edges:
                if current in seen:
                    raise SyncError(f"parent cycle detected from issue #{start}")
                seen.add(current)
                current = parent_edges[current]

        def visit(number: int, visiting: set[int], visited: set[int]) -> None:
            if number in visited:
                return
            if number in visiting:
                raise SyncError(f"dependency cycle detected at issue #{number}")
            visiting.add(number)
            for prerequisite in dependency_edges.get(number, set()):
                visit(prerequisite, visiting, visited)
            visiting.remove(number)
            visited.add(number)

        visited: set[int] = set()
        for number in dependency_edges:
            visit(number, set(), visited)


def _evidence(raw: Optional[Mapping[str, Any]]) -> Optional[RelationEvidence]:
    if raw is None:
        return None
    return RelationEvidence(int(raw["issue"]), str(raw["reason_code"]), str(raw["source"]))


def _all_evidence(relations: IssueRelations) -> Iterable[RelationEvidence]:
    if relations.parent:
        yield relations.parent
    yield from relations.blocked_by
    yield from relations.relates_to


class GitHubReader:
    """Read current Issue state using public GitHub interfaces.

    Parent and dependency data come from GraphQL. ``Relates to`` is still a
    public preview and is absent from the public REST/GraphQL schemas as of the
    API version above. GitHub's read-only issue-picker projection is used to
    audit that relationship until an official API field is published.
    """

    def __init__(self, repository: str) -> None:
        self.repository = repository
        self.owner, self.repo = repository.split("/", 1)

    def issues(self) -> dict[int, IssueRecord]:
        raw = _gh_json(
            "api",
            "--paginate",
            "-H",
            f"X-GitHub-Api-Version: {API_VERSION}",
            f"repos/{self.repository}/issues?state=all&per_page=100&direction=asc",
        )
        return {
            int(item["number"]): IssueRecord(
                number=int(item["number"]),
                database_id=int(item["id"]),
                node_id=str(item["node_id"]),
                title=str(item["title"]),
                state=str(item["state"]),
                body=str(item.get("body") or ""),
            )
            for item in raw
            if "pull_request" not in item
        }

    def native_relations(
        self, issues: Mapping[int, IssueRecord], scope: Sequence[int]
    ) -> dict[int, CurrentRelations]:
        graph = self._graphql_relationships()
        node_to_number = {issue.node_id: issue.number for issue in issues.values()}
        related_by_issue: dict[int, set[int]] = {}
        with ThreadPoolExecutor(max_workers=min(12, len(scope))) as executor:
            pending = {
                executor.submit(self._relates_to, number, node_to_number): number
                for number in scope
            }
            for future in as_completed(pending):
                related_by_issue[pending[future]] = future.result()
        current: dict[int, CurrentRelations] = {}
        for number in scope:
            node = graph.get(number, {})
            current[number] = CurrentRelations(
                parent=(node.get("parent") or {}).get("number"),
                blocked_by=frozenset(
                    int(item["number"]) for item in node.get("blockedBy", {}).get("nodes", [])
                ),
                relates_to=frozenset(related_by_issue[number]),
            )
        return current

    def _graphql_relationships(self) -> dict[int, Mapping[str, Any]]:
        query = """
        query($owner:String!,$repo:String!,$cursor:String){
          repository(owner:$owner,name:$repo){
            issues(first:100,after:$cursor,orderBy:{field:CREATED_AT,direction:ASC}){
              nodes{id number parent{id number} blockedBy(first:100){nodes{id number}}}
              pageInfo{hasNextPage endCursor}
            }
          }
        }
        """
        cursor: Optional[str] = None
        nodes: list[Mapping[str, Any]] = []
        while True:
            args = [
                "api",
                "graphql",
                "-f",
                f"query={query}",
                "-F",
                f"owner={self.owner}",
                "-F",
                f"repo={self.repo}",
            ]
            if cursor:
                args.extend(("-F", f"cursor={cursor}"))
            payload = _gh_json(*args)
            connection = payload["data"]["repository"]["issues"]
            nodes.extend(connection["nodes"])
            if not connection["pageInfo"]["hasNextPage"]:
                break
            cursor = connection["pageInfo"]["endCursor"]
        return {int(node["number"]): node for node in nodes}

    def _relates_to(self, issue_number: int, node_to_number: Mapping[str, int]) -> set[int]:
        url = (
            f"https://github.com/{self.repository}/issues/{issue_number}/"
            "dependencies_picker_relationships.json"
        )
        request = urllib.request.Request(url, headers={"User-Agent": "tessera-portfolio-sync/1"})
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                payload = json.load(response)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise SyncError(f"could not read relates-to relationships for #{issue_number}: {exc}") from exc
        nodes = payload["data"]["node"].get("relatesTo", {}).get("nodes", [])
        return {node_to_number[node["id"]] for node in nodes if node["id"] in node_to_number}


class GitHubWriter:
    def __init__(self, repository: str, issues: Mapping[int, IssueRecord]) -> None:
        self.repository = repository
        self.issues = issues

    def apply(self, plans: Sequence[IssuePlan]) -> None:
        relates_changes = [
            plan for plan in plans if plan.relates_add or plan.relates_remove
        ]
        if relates_changes:
            raise SyncError(
                "GitHub's public REST and GraphQL APIs do not yet expose the public-preview "
                "'Relates to' mutation. Synchronize the listed relates-to changes in the web UI, "
                "then rerun --apply; no mutations were performed."
            )

        for plan in plans:
            if plan.parent_remove is not None:
                _gh(
                    "api",
                    "--method",
                    "DELETE",
                    "-H",
                    f"X-GitHub-Api-Version: {API_VERSION}",
                    f"repos/{self.repository}/issues/{plan.issue_number}/sub_issue",
                )
            if plan.parent_add is not None:
                _gh(
                    "api",
                    "--method",
                    "POST",
                    "-H",
                    f"X-GitHub-Api-Version: {API_VERSION}",
                    f"repos/{self.repository}/issues/{plan.parent_add}/sub_issues",
                    "-F",
                    f"sub_issue_id={self.issues[plan.issue_number].database_id}",
                )
            for target in sorted(plan.blocked_remove):
                _gh(
                    "api",
                    "--method",
                    "DELETE",
                    "-H",
                    f"X-GitHub-Api-Version: {API_VERSION}",
                    f"repos/{self.repository}/issues/{plan.issue_number}/dependencies/"
                    f"blocked_by/{self.issues[target].database_id}",
                )
            for target in sorted(plan.blocked_add):
                _gh(
                    "api",
                    "--method",
                    "POST",
                    "-H",
                    f"X-GitHub-Api-Version: {API_VERSION}",
                    f"repos/{self.repository}/issues/{plan.issue_number}/dependencies/blocked_by",
                    "-F",
                    f"issue_id={self.issues[target].database_id}",
                )


def build_plan(
    model: PortfolioModel, current: Mapping[int, CurrentRelations]
) -> list[IssuePlan]:
    plans = {number: IssuePlan(issue_number=number) for number in model.inspected}
    for number in model.inspected:
        desired = model.desired(number)
        actual = current[number]
        desired_parent = desired.parent.issue if desired.parent else None
        desired_blocked = {edge.issue for edge in desired.blocked_by}
        plan = plans[number]
        if actual.parent != desired_parent:
            plan.parent_remove = actual.parent
            plan.parent_add = desired_parent
        plan.blocked_add = desired_blocked - set(actual.blocked_by)
        plan.blocked_remove = set(actual.blocked_by) - desired_blocked

    # Relates-to is one undirected edge. Compare and plan each pair exactly
    # once, even though GitHub projects the relationship onto both issues.
    scope = set(model.inspected)
    desired_pairs = {
        tuple(sorted((number, edge.issue)))
        for number in model.inspected
        for edge in model.desired(number).relates_to
        if edge.issue in scope
    }
    current_pairs = {
        tuple(sorted((number, target)))
        for number in model.inspected
        for target in current[number].relates_to
        if target in scope
    }
    for left, right in desired_pairs - current_pairs:
        plans[left].relates_add.add(right)
    for left, right in current_pairs - desired_pairs:
        plans[left].relates_remove.add(right)

    return [plans[number] for number in model.inspected if plans[number].changed]


def ignored_textual_links(
    model: PortfolioModel, issues: Mapping[int, IssueRecord]
) -> int:
    known = set(issues)
    count = 0
    for number in model.inspected:
        body_targets = {
            int(match)
            for match in re.findall(r"(?<![\w/])#(\d+)\b", issues[number].body)
            if int(match) in known and int(match) != number
        }
        desired = model.desired(number)
        kept = {edge.issue for edge in _all_evidence(desired)}
        count += len(body_targets - kept)
    return count


def _reason(model: PortfolioModel, issue_number: int, relation: str, target: int) -> str:
    desired = model.desired(issue_number)
    if relation == "parent":
        edge = desired.parent
    else:
        edge = next(
            (
                item
                for item in getattr(desired, relation)
                if item.issue == target
            ),
            None,
        )
    return f" [{edge.reason_code}]" if edge else ""


def render_report(
    model: PortfolioModel,
    issues: Mapping[int, IssueRecord],
    current: Mapping[int, CurrentRelations],
    plans: Sequence[IssuePlan],
    applied: bool,
) -> str:
    scope = set(model.inspected)
    desired_relates = {
        tuple(sorted((number, edge.issue)))
        for number in model.inspected
        for edge in model.desired(number).relates_to
        if edge.issue in scope
    }
    current_relates = {
        tuple(sorted((number, target)))
        for number in model.inspected
        for target in current[number].relates_to
        if target in scope
    }
    desired_count = sum(
        (1 if relation.parent else 0) + len(relation.blocked_by)
        for relation in (model.desired(number) for number in model.inspected)
    ) + len(desired_relates)
    current_count = sum(
        (1 if relation.parent else 0) + len(relation.blocked_by)
        for relation in current.values()
    ) + len(current_relates)
    counts = {
        "add parent": sum(plan.parent_add is not None and plan.parent_remove is None for plan in plans),
        "change parent": sum(plan.parent_add is not None and plan.parent_remove is not None for plan in plans),
        "remove parent": sum(plan.parent_add is None and plan.parent_remove is not None for plan in plans),
        "add blocked-by": sum(len(plan.blocked_add) for plan in plans),
        "remove blocked-by": sum(len(plan.blocked_remove) for plan in plans),
        "add relates-to": sum(len(plan.relates_add) for plan in plans),
        "remove relates-to": sum(len(plan.relates_remove) for plan in plans),
    }
    lines = [
        "TESSERA Issue Relationships Sync",
        "",
        f"Repository: {model.repository}",
        "",
        f"Issues inspected: {len(model.inspected)}",
        f"Relationships currently present: {current_count}",
        f"Relationships desired: {desired_count}",
        "",
        "Planned:",
    ]
    lines.extend(f"  {label + ':':<22}{value}" for label, value in counts.items())
    lines.extend(("", f"Ignored textual links: {ignored_textual_links(model, issues)}"))

    for plan in plans:
        lines.extend(("", f"#{plan.issue_number} {issues[plan.issue_number].title}"))
        if plan.parent_add is not None or plan.parent_remove is not None:
            lines.append("  Parent:")
            if plan.parent_remove is not None:
                lines.append(f"    - #{plan.parent_remove}")
            if plan.parent_add is not None:
                lines.append(
                    f"    + #{plan.parent_add}{_reason(model, plan.issue_number, 'parent', plan.parent_add)}"
                )
        if plan.blocked_add or plan.blocked_remove:
            lines.append("  Blocked by:")
            lines.extend(f"    - #{target}" for target in sorted(plan.blocked_remove))
            lines.extend(
                f"    + #{target}{_reason(model, plan.issue_number, 'blocked_by', target)}"
                for target in sorted(plan.blocked_add)
            )
        if plan.relates_add or plan.relates_remove:
            lines.append("  Relates to:")
            lines.extend(f"    - #{target}" for target in sorted(plan.relates_remove))
            lines.extend(
                f"    + #{target}{_reason(model, plan.issue_number, 'relates_to', target)}"
                for target in sorted(plan.relates_add)
            )
        blocking = sorted(
            other.issue_number
            for other in plans
            if plan.issue_number in other.blocked_add
        )
        if blocking:
            lines.append("  Blocking (derived):")
            lines.extend(f"    + #{target}" for target in blocking)

    lines.extend(
        (
            "",
            "Synchronization applied." if applied else "No mutations performed.",
            "" if applied else "Run with --apply to synchronize.",
        )
    )
    return "\n".join(lines).rstrip()


def _gh(*args: str) -> str:
    try:
        completed = subprocess.run(
            ("gh", *args), check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
    except FileNotFoundError as exc:
        raise SyncError("GitHub CLI (gh) is required") from exc
    except subprocess.CalledProcessError as exc:
        message = exc.stderr.strip() or exc.stdout.strip() or "unknown GitHub CLI error"
        raise SyncError(message) from exc
    return completed.stdout


def _gh_json(*args: str) -> Any:
    output = _gh(*args)
    try:
        return json.loads(output)
    except json.JSONDecodeError as exc:
        raise SyncError("GitHub CLI returned invalid JSON") from exc


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", nargs="?", default="relationships", choices=("relationships",))
    parser.add_argument("--apply", action="store_true", help="apply the displayed plan")
    parser.add_argument("--dry-run", action="store_true", help="explicit alias for the read-only default")
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    args = parser.parse_args(argv)
    if args.apply and args.dry_run:
        parser.error("--apply and --dry-run are mutually exclusive")
    return args


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    try:
        model = PortfolioModel.load(args.model)
        reader = GitHubReader(model.repository)
        issues = reader.issues()
        missing = sorted(set(model.inspected) - set(issues))
        if missing:
            raise SyncError(f"configured issues do not exist: {missing}")
        ignored = [
            issue.number
            for issue in issues.values()
            if issue.state == "open"
            and issue.title.lower().startswith(tuple(prefix.lower() for prefix in model.ignored_prefixes))
        ]
        overlap = sorted(set(ignored) & set(model.inspected))
        if overlap:
            raise SyncError(f"automatic/lifecycle issues must not be in scope: {overlap}")

        current = reader.native_relations(issues, model.inspected)
        plans = build_plan(model, current)
        if args.apply:
            GitHubWriter(model.repository, issues).apply(plans)
        print(render_report(model, issues, current, plans, args.apply))
        return 0
    except SyncError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
