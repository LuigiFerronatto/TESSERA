"""Tests for TesseraOrchestrator and the bundled default skills."""

import tempfile

from tessera import TesseraEngine, TesseraOrchestrator, install_default_skills, SKILL_IDS


def test_install_default_skills_are_retrievable():
    with tempfile.TemporaryDirectory() as tmp:
        engine = TesseraEngine(storage_dir=tmp)
        paths = install_default_skills(engine)

        assert len(paths) == len(SKILL_IDS) == 5
        for skill_id in SKILL_IDS:
            assert skill_id in engine.graph.nodes

        results = engine.retrieve_context("como evitar erros de docker?", top_n=1)
        assert results
        assert results[0]["id"] == "sk_docker_environment"


def test_orchestrator_full_pipeline_with_simulated_llm():
    with tempfile.TemporaryDirectory() as tmp:
        engine = TesseraEngine(storage_dir=tmp)
        install_default_skills(engine)

        orchestrator = TesseraOrchestrator(engine)
        result = orchestrator.run("Como faço deploy seguro de um container docker?", top_n=2)

        assert result.information_need
        assert result.retrieval_query
        assert result.raw_memories
        assert "sk_docker_environment" in [m["id"] for m in result.raw_memories]
        assert "sk_docker_environment" in result.consolidated_context


def test_orchestrator_accepts_custom_llm_fn():
    calls = []

    def fake_llm(system_prompt: str, user_prompt: str) -> str:
        calls.append((system_prompt, user_prompt))
        return "resposta customizada"

    with tempfile.TemporaryDirectory() as tmp:
        engine = TesseraEngine(storage_dir=tmp)
        install_default_skills(engine)

        orchestrator = TesseraOrchestrator(engine, llm_fn=fake_llm)
        result = orchestrator.run("teste de shell")

        assert result.information_need == "resposta customizada"
        assert result.retrieval_query == "resposta customizada"
        assert len(calls) == 3  # need, planner, inference
