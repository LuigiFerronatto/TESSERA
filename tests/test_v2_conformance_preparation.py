import copy
import inspect
import json
from pathlib import Path
import socket

import pytest

from benchmarks.longmemeval_v2 import PROFILE, UPSTREAM_COMMIT
from benchmarks.longmemeval_v2.adapter import SyntheticTesseraMemory
from benchmarks.longmemeval_v2.cli import main, run_synthetic
from benchmarks.longmemeval_v2.contracts import (
    UnsupportedProtocol, bound_context, digest, invoke_query, query_payload,
    validate_context, validate_trajectory,
)
from benchmarks.longmemeval_v2.fixture import (
    image_bytes, synthetic_context_cost, synthetic_image_validator, trajectories, write_assets,
)


@pytest.fixture
def assets(tmp_path):
    root = tmp_path / "assets"
    write_assets(root)
    return root


def memory(assets, **kwargs):
    return SyntheticTesseraMemory(assets, profile=PROFILE, **kwargs)


def test_trajectory_insert_keeps_complete_source_and_provenance(assets):
    trajectory = trajectories()[0]
    original = copy.deepcopy(trajectory)
    with memory(assets) as backend:
        backend.insert(trajectory)
        trajectory["states"][0]["accessibility_tree"] = "mutated"
        snapshot = backend.trajectory_snapshot()
        assert snapshot == [original]
        snapshot.clear()
        assert backend.trajectory_snapshot() == [original]
        items = backend.query("blue toolkit")
        assert {i["type"] for i in items} == {"text", "image"}
        assert any("north door" in i["value"] for i in items if i["type"] == "text")
        audit = backend.audit()
        assert len(audit["provenance"]) == len(items)
        for source in audit["provenance"]:
            state = original["states"][source["state_index"]]
            assert source["trajectory_id"] == "workshop"
            assert source["step"] == state["step"]
            assert source["trajectory_sha256"] == digest(original)
            assert source["state_sha256"] == digest(state)
            assert source["screenshot_sha256"] == synthetic_image_validator(str(assets / state["screenshot"]))


def test_optional_query_image_transports_without_claiming_visual_retrieval(assets):
    with memory(assets) as backend:
        backend.insert(trajectories()[0])
        plain = backend.query("toolkit")
        assert backend.query("toolkit", "question_screenshots/synthetic.png") == plain
        assert backend.audit()["query_image_handling"] == "validated_not_used_for_retrieval"


@pytest.mark.parametrize("boundary", ["trajectory", "state"])
@pytest.mark.parametrize("key", ["question_id", "question_type", "answer", "answer_gold", "eval_function", "evaluator_config", "raw_question", "query_invocation_id"])
def test_evaluator_metadata_rejected_at_insert_boundaries(assets, boundary, key):
    trajectory = trajectories()[0]
    target = trajectory if boundary == "trajectory" else trajectory["states"][0]
    target[key] = "EVALUATOR_SECRET"
    with memory(assets) as backend, pytest.raises(ValueError, match="expected exactly"):
        backend.insert(trajectory)
    assert "EVALUATOR_SECRET" not in str(trajectory.get("id"))


def test_query_signature_excludes_all_evaluator_metadata(assets):
    assert list(inspect.signature(SyntheticTesseraMemory.query).parameters) == ["self", "query", "query_image"]
    with memory(assets) as backend:
        backend.insert(trajectories()[0])
        for key in ("question_id", "question_type", "answer", "raw_question", "evaluator_config"):
            with pytest.raises(TypeError):
                backend.query("toolkit", **{key: "secret"})
        with pytest.raises(ValueError):
            backend.query({"question": "toolkit", "answer": "secret"})


class Poison:
    def __deepcopy__(self, memo):
        raise AssertionError("private evaluator data inspected")
    def __str__(self):
        raise AssertionError("private evaluator data serialized")


def test_query_projection_never_exposes_evaluator_record_or_trace_to_engine(assets, monkeypatch):
    with memory(assets) as backend:
        backend.insert(trajectories()[0])
        expected = backend.query("blue toolkit")
        engine = backend._engine
        calls = []
        original = engine.retrieve_context_contract
        def spy(*args, **kwargs):
            calls.append((args, kwargs))
            return original(*args, **kwargs)
        monkeypatch.setattr(engine, "retrieve_context_contract", spy)
        secret = Poison()
        record = {"question": "blue toolkit", "id": secret, "question_type": secret,
                  "answer": secret, "eval_function": secret, "raw_question": secret,
                  "evaluator_config": secret}
        for trace in ("trace-a", "trace-b"):
            assert invoke_query(backend, record, trace) == expected
            assert backend.get_query_context() == {} and backend.audit() is None
        assert calls == [(("blue toolkit",), {"top_n": 7})] * 2
        assert "trace-a" not in repr(backend.trajectory_snapshot())


def test_runtime_question_matches_materialized_upstream_shape():
    assert query_payload({"question": "Where?", "answer": Poison()}) == {"query": "Where?", "query_image": None}
    assert query_payload({"question": {"text": "Where?", "image": "source.png"}}) == {"query": "Where?", "query_image": "source.png"}
    with pytest.raises(ValueError):
        query_payload({"question": {"text": "Where?", "image": "source.png", "answer": "secret"}})


def test_query_cleanup_even_on_failure_and_cross_question_isolation(assets):
    with memory(assets) as backend:
        backend.insert(trajectories()[0])
        backend.query("toolkit")
        with pytest.raises(ValueError, match="missing image"):
            invoke_query(backend, {"question": {"text": "Where?", "image": "absent.png"}}, "trace")
        assert backend.get_query_context() == {} and backend.audit() is None
        assert backend.query("toolkit")


@pytest.mark.parametrize("kind", ["missing", "corrupt", "directory", "escape"])
def test_source_image_failures_are_explicit_and_insert_is_atomic(assets, tmp_path, kind):
    trajectory = trajectories()[0]
    path = assets / trajectory["states"][1]["screenshot"]
    path.unlink()
    if kind == "corrupt":
        path.write_bytes(b"not a PNG")
    elif kind == "directory":
        path.mkdir()
    elif kind == "escape":
        outside = tmp_path / "outside.png"
        outside.write_bytes(image_bytes())
        path.symlink_to(outside)
    with memory(assets) as backend:
        with pytest.raises((ValueError, UnsupportedProtocol)):
            backend.insert(trajectory)
        assert list(backend.corpus.iterdir()) == [] and backend.trajectory_snapshot() == []


def test_image_mutation_after_insert_invalidates_output_and_audit(assets):
    with memory(assets) as backend:
        backend.insert(trajectories()[0])
        assert backend.query("toolkit")
        (assets / "screenshots/workshop/0.png").write_bytes(b"corrupted")
        with pytest.raises(UnsupportedProtocol, match="image_unverified"):
            backend.query("toolkit")
        assert backend.audit() is None


@pytest.mark.parametrize("bad", [None, {}, [{"type": "text", "value": " "}], [{"type": "audio", "value": "x"}], [{"type": "text", "value": "x", "answer": "secret"}], [{"type": "image", "value": "missing.png"}]])
def test_context_schema_rejects_invalid_items(bad):
    with pytest.raises(ValueError):
        validate_context(bad, synthetic_image_validator)


@pytest.mark.parametrize("budget,expected", [(1, 0), (9, 1), (19, 1), (20, 2), (27, 3), (100, 3)])
def test_whole_item_budget_preserves_prefix_and_accounts_overhead(budget, expected):
    items = [{"type": "text", "value": "a"}, {"type": "image", "value": "a.png"}, {"type": "text", "value": "b"}]
    result = bound_context(items, budget, synthetic_context_cost)
    assert result["items"] == items[:expected]
    assert result["final_units"] <= budget
    assert result["original_units"] == 27


@pytest.mark.parametrize("bad", [True, False, 0, -1, 1.5, "10"])
def test_invalid_budgets_fail_closed(bad):
    with pytest.raises(ValueError):
        bound_context([], bad, synthetic_context_cost)


def test_official_tokenizer_never_falls_back_to_synthetic_counter():
    with pytest.raises(UnsupportedProtocol, match="official_tokenizer_unpinned"):
        bound_context([], 100)
    with pytest.raises(ValueError, match="non-monotone"):
        bound_context([{}, {}], 100, lambda items: [0, 10, 2][len(items)])
    for value in (True, -1, 0.5, "10"):
        with pytest.raises(ValueError):
            bound_context([{}], 100, lambda items: 0 if not items else value)


def test_adapter_budget_and_text_only_ablations(assets):
    for budget in (1, 9, 20, 100):
        with memory(assets, context_budget=budget) as backend:
            backend.insert(trajectories()[0])
            items = backend.query("toolkit")
            assert backend.audit()["final_units"] <= budget
            assert len(items) == len(backend.audit()["provenance"])
    with memory(assets, include_source_images=False) as backend:
        backend.insert(trajectories()[0])
        assert all(i["type"] == "text" for i in backend.query("toolkit"))


def test_lifecycle_isolation_duplicate_and_cross_domain_rejection(assets):
    with memory(assets) as first, memory(assets) as second:
        assert first.corpus != second.corpus
        first.insert(trajectories()[0])
        with pytest.raises(ValueError, match="duplicate"):
            first.insert(trajectories()[0])
        with pytest.raises(ValueError, match="cross-domain"):
            first.insert(trajectories()[1])
        second.insert(trajectories()[1])
        assert all(p["trajectory_id"] == "stockroom" for _ in [second.query("lantern")] for p in second.audit()["provenance"])
        assert "north door" not in str(second.trajectory_snapshot())
        first.query("toolkit")
        with pytest.raises(RuntimeError, match="sealed"):
            first.insert(trajectories()[0])
        first_path = first.corpus
    assert not first_path.exists()
    with pytest.raises(RuntimeError, match="closed"):
        first.query("toolkit")


def test_unsupported_persistence_and_official_profiles_are_honest(assets, tmp_path):
    with pytest.raises(UnsupportedProtocol, match="official_execution_not_supported"):
        SyntheticTesseraMemory(assets, profile="longmemeval-v2-small")
    with memory(assets) as backend:
        for method in (backend._save_backend, backend._load_backend):
            with pytest.raises(UnsupportedProtocol, match="save_load_not_supported"):
                method(tmp_path / "state")
    assert not (tmp_path / "state").exists()


def test_repeatability_no_network_and_clear_incomplete_claims(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("network access forbidden")
    monkeypatch.setattr(socket, "socket", forbidden)
    first, second = run_synthetic(), run_synthetic()
    assert first == second
    assert first["provider_calls"] == 0 and first["official_conformance"] is False
    assert first["official_evaluation"] == "NOT_RUN"
    assert {r["domain"] for r in first["domains"]} == {"web", "enterprise"}


def test_cli_reproducible_output_and_containment(tmp_path):
    for name in ("one", "two"):
        assert main(["--output-dir", str(tmp_path / name), "--allow-dirty-worktree"]) == 0
    for name in ("manifest.json", "conformance.json"):
        assert (tmp_path / "one" / name).read_bytes() == (tmp_path / "two" / name).read_bytes()
    manifest = json.loads((tmp_path / "one/manifest.json").read_text())
    assert manifest["upstream_commit"] == UPSTREAM_COMMIT
    assert manifest["dataset_loaded"] is False
    with pytest.raises(FileExistsError):
        main(["--output-dir", str(tmp_path / "one"), "--allow-dirty-worktree"])
    target = Path(__file__).resolve().parents[1] / "benchmarks/v2-forbidden-output"
    with pytest.raises(ValueError, match="outside checkout"):
        main(["--output-dir", str(target), "--allow-dirty-worktree"])
    assert not target.exists()


def test_pins_and_runtime_boundaries():
    root = Path(__file__).resolve().parents[1]
    pins = json.loads((root / "benchmarks/longmemeval_v2/protocol.json").read_text())
    assert pins["upstream"]["commit"] == UPSTREAM_COMMIT
    assert pins["dataset"]["corpus_downloaded"] is False
    assert pins["official_processor"]["revision"] is None
    for name in ("transformers", "torch", "Pillow", "openai"):
        assert name not in (root / "pyproject.toml").read_text()
    assert "prune benchmarks" in (root / "MANIFEST.in").read_text()


def test_synthetic_image_check_uses_bounded_read(assets, monkeypatch):
    def unbounded_read_forbidden(*args, **kwargs):
        raise AssertionError("do not read arbitrary unsupported files in full")
    monkeypatch.setattr(Path, "read_bytes", unbounded_read_forbidden)
    path = assets / "question_screenshots/synthetic.png"
    assert synthetic_image_validator(str(path))
    with path.open("ab") as stream:
        stream.write(b"x" * 1000000)
    with pytest.raises(UnsupportedProtocol, match="image_unverified"):
        synthetic_image_validator(str(path))


def test_public_question_requires_explicit_runtime_materialization():
    with pytest.raises(ValueError, match="materialized"):
        query_payload({"question": "Where?", "image": "source.png", "answer": Poison()})


def test_query_context_is_thread_local_and_defensive(assets):
    from concurrent.futures import ThreadPoolExecutor
    with memory(assets) as backend:
        backend.set_query_context(query_invocation_id="parent")
        returned = backend.get_query_context()
        returned["answer"] = "must not be retained"
        with pytest.raises(TypeError):
            backend.set_query_context(query_invocation_id="parent", answer="secret")
        def child():
            assert backend.get_query_context() == {}
            backend.set_query_context(query_invocation_id="child")
            assert backend.get_query_context() == {"query_invocation_id": "child"}
            backend.clear_query_context()
        with ThreadPoolExecutor(max_workers=1) as pool:
            pool.submit(child).result()
        assert backend.get_query_context() == {"query_invocation_id": "parent"}
