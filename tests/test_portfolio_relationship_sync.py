import importlib.util
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "sync_portfolio.py"
MODEL = ROOT / "docs" / "portfolio-relationships.yaml"


def _module():
    spec = importlib.util.spec_from_file_location("sync_portfolio", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_relationship_model_is_valid_and_canonical() -> None:
    sync = _module()
    model = sync.PortfolioModel.load(MODEL)

    assert model.repository == "LuigiFerronatto/TESSERA"
    assert 194 not in model.inspected  # [aw] issue
    assert 195 not in model.inspected  # [aw] issue
    assert 199 not in model.inspected  # [aw] issue
    assert 189 not in model.inspected  # generated lifecycle issue

    assert model.desired(141).parent.issue == 145
    assert {edge.issue for edge in model.desired(141).blocked_by} == {15, 16, 137, 140}
    assert {edge.issue for edge in model.desired(141).relates_to} == {20}

    assert model.desired(196).parent.issue == 170
    assert {edge.issue for edge in model.desired(177).blocked_by} == {196}
    assert 177 not in {edge.issue for edge in model.desired(196).relates_to}


def test_relates_to_is_declared_once_and_projected_symmetrically() -> None:
    sync = _module()
    model = sync.PortfolioModel.load(MODEL)

    assert 196 in {edge.issue for edge in model.desired(193).relates_to}
    assert 193 in {edge.issue for edge in model.desired(196).relates_to}

    raw = MODEL.read_text(encoding="utf-8")
    assert "blocking:" not in raw


def test_split_scope_does_not_block_the_whole_issue() -> None:
    sync = _module()
    model = sync.PortfolioModel.load(MODEL)

    assert model.desired(16).blocked_by == ()
    related = {edge.issue: edge.reason_code for edge in model.desired(16).relates_to}
    assert related[15] == "SPLIT_SCOPE_NOT_NATIVE_BLOCKER"
    assert related[73] == "SPLIT_SCOPE_NOT_NATIVE_BLOCKER"


def test_plan_derives_additions_removals_and_parent_changes() -> None:
    sync = _module()
    model = sync.PortfolioModel.load(MODEL)
    current = {number: sync.CurrentRelations() for number in model.inspected}
    current[196] = sync.CurrentRelations(
        parent=177,
        relates_to=frozenset({169, 171, 190}),
    )

    plans = {plan.issue_number: plan for plan in sync.build_plan(model, current)}
    hook_core = plans[196]
    assert hook_core.parent_remove == 177
    assert hook_core.parent_add == 170
    assert hook_core.relates_remove == set()

    added_relates = {
        tuple(sorted((plan.issue_number, target)))
        for plan in plans.values()
        for target in plan.relates_add
    }
    assert {(138, 196), (191, 196), (193, 196)} <= added_relates


def test_apply_fails_closed_before_partial_mutation_when_relates_to_differs() -> None:
    sync = _module()
    writer = sync.GitHubWriter("LuigiFerronatto/TESSERA", {})
    plan = sync.IssuePlan(issue_number=196, relates_add={193})

    with pytest.raises(sync.SyncError, match="no mutations were performed"):
        writer.apply([plan])


def test_cli_is_dry_run_by_default() -> None:
    sync = _module()
    args = sync.parse_args(["relationships"])
    assert not args.apply
    assert not args.dry_run
