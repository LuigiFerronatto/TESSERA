"""Repository-only experiment reproducibility and gate checks."""

def test_frozen_sweep_generation_and_predeclared_gates():
    import json
    from benchmarks.vector_backends.scale_sweep import PLAN_PATH, compare, generate_fixture
    plan = json.loads(PLAN_PATH.read_text())
    assert plan["sizes"] == [256, 2048, 8192]
    assert plan["dimensions"] == [16, 64]
    assert plan["ann_epsilon"] == 0.5
    first = generate_fixture(plan, 32, 4)
    assert first == generate_fixture(plan, 32, 4)
    assert len(set(map(tuple, first["vectors"]))) == 32
    oracle = {"backend": "exact-flat", "signatures": {"q": [["a", .99], ["b", .98]]}}
    same = compare(oracle, oracle, plan)
    assert same["mechanics_gate"] and same["mean_recall_at_10"] == 1
    miss = {"backend": "ckdtree-ann", "signatures": {"q": [["x", 0], ["y", -.5]]}}
    result = compare(miss, oracle, plan)
    assert not result["mechanics_gate"] and result["mean_recall_at_10"] == 0
