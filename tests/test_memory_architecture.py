"""
Tests for the 3-pillar memory architecture:
  1. Episodes (begin/middle/end structured notes) — tessera.models.Episode
  2. Typed stores (facts / preferences / insights) — TesseraEngine.write_fact/
     write_preference/write_insight/write_episode/retrieve_from_store
  3. The automatic task hook (detective trio) — tessera.hooks.TesseraTaskHook
"""

import tempfile

import pytest

from tessera import (
    TesseraEngine,
    Entity,
    Episode,
    STORE_FACTS,
    STORE_INSIGHTS,
    STORE_PREFERENCES,
)
from tessera.hooks import TesseraTaskHook, TaskInterceptionResult


@pytest.fixture
def engine():
    with tempfile.TemporaryDirectory() as tmp:
        yield TesseraEngine(storage_dir=tmp)


# ----------------------------------------------------------------------
# Pillar 1: Episodes
# ----------------------------------------------------------------------
def test_episode_round_trips_through_markdown():
    ep = Episode(beginning="Contexto X", middle="Aconteceu Y", end="Aprendemos Z")
    body = ep.to_markdown_body()

    assert "## Início" in body
    assert "## Meio" in body
    assert "## Fim" in body

    parsed = Episode.from_markdown_body(body)
    assert parsed.beginning == "Contexto X"
    assert parsed.middle == "Aconteceu Y"
    assert parsed.end == "Aprendemos Z"


def test_episode_from_plain_body_falls_back_to_middle():
    parsed = Episode.from_markdown_body("Um texto qualquer sem estrutura de seções.")
    assert parsed.beginning == ""
    assert parsed.middle == "Um texto qualquer sem estrutura de seções."
    assert parsed.end == ""


def test_write_episode_persists_structured_sections(engine):
    ep = Episode(
        beginning="Tarefa: subir o serviço de banco em background.",
        middle="Tentamos iniciar sem checar a porta 5432, já ocupada.",
        end="Sempre checar a porta com lsof antes de subir o serviço.",
    )
    engine.write_episode(
        mem_id="insight_service", store=STORE_INSIGHTS, episode_id="ep1", episode=ep, tags=["devops"]
    )
    engine.build_index()

    node = engine.graph.nodes["insight_service"]
    assert node["node_type"] == "procedural_anchor"
    assert "## Início" in node["body"]
    assert "porta 5432" in node["body"]


# ----------------------------------------------------------------------
# Pillar 2: Typed stores (facts / preferences / insights)
# ----------------------------------------------------------------------
def test_write_fact_preference_insight_route_to_correct_node_type(engine):
    engine.write_fact(mem_id="fact_1", episode_id="ep1", content="O Postgres roda na porta 5432.")
    engine.write_preference(mem_id="pref_1", episode_id="ep2", content="Alex prefere PDF.")
    engine.write_insight(mem_id="insight_1", episode_id="ep3", content="Checar porta antes de subir serviço.")
    engine.build_index()

    assert engine.graph.nodes["fact_1"]["node_type"] == "factual"
    assert engine.graph.nodes["pref_1"]["node_type"] == "preference"
    assert engine.graph.nodes["insight_1"]["node_type"] == "procedural_anchor"


def test_retrieve_from_store_filters_by_typed_store(engine):
    engine.write_fact(
        mem_id="fact_db", episode_id="ep1",
        content="O banco de dados de produção roda na porta 5432.",
        tags=["database"], entities=[Entity("DB", "Banco de produção")],
    )
    engine.write_insight(
        mem_id="insight_db", episode_id="ep2",
        content="Sempre checar a porta do banco de dados antes de subir o serviço.",
        tags=["database"], entities=[Entity("DB", "Banco de produção")],
    )
    engine.build_index()

    fact_results = engine.retrieve_from_store("porta do banco de dados", STORE_FACTS, top_n=5)
    assert fact_results
    assert all(r["type"] == "factual" for r in fact_results)
    assert any(r["id"] == "fact_db" for r in fact_results)

    insight_results = engine.retrieve_from_store("porta do banco de dados", STORE_INSIGHTS, top_n=5)
    assert insight_results
    assert all(r["type"] == "procedural_anchor" for r in insight_results)
    assert any(r["id"] == "insight_db" for r in insight_results)


def test_retrieve_from_store_rejects_unknown_store(engine):
    engine.build_index()
    with pytest.raises(ValueError):
        engine.retrieve_from_store("qualquer coisa", "not_a_real_store")


# ----------------------------------------------------------------------
# Pillar 3: The automatic task hook (detective trio)
# ----------------------------------------------------------------------
def test_hook_on_task_start_returns_consolidated_context(engine):
    engine.write_insight(
        mem_id="insight_service", episode_id="ep1",
        content="Sempre checar se a porta 5432 está livre antes de subir o banco em background.",
        tags=["devops", "database"],
    )
    engine.build_index()

    hook = TesseraTaskHook(engine)
    result = hook.on_task_start("Como faço deploy seguro de um banco de dados em background?")

    assert isinstance(result, TaskInterceptionResult)
    assert result.stores_queried  # planner picked at least one store
    assert result.consolidated_context
    assert result.raw_memories


def test_hook_on_task_end_writes_to_requested_store(engine):
    engine.build_index()
    hook = TesseraTaskHook(engine)

    path = hook.on_task_end(
        task_instruction="tarefa de teste",
        store="insights",
        summary="Aprendizado registrado após a tarefa.",
    )
    assert path

    engine.build_index()
    written_nodes = [n for n, d in engine.graph.nodes(data=True) if d.get("node_type") == "procedural_anchor"]
    assert written_nodes


def test_hook_on_task_end_rejects_unknown_store(engine):
    engine.build_index()
    hook = TesseraTaskHook(engine)
    with pytest.raises(ValueError):
        hook.on_task_end(task_instruction="x", store="not_a_real_store", summary="y")


def test_hook_subscriber_is_called(engine):
    engine.write_fact(mem_id="fact_1", episode_id="ep1", content="Um fato qualquer.")
    engine.build_index()

    seen = []
    hook = TesseraTaskHook(engine, subscribers=[lambda result: seen.append(result)])
    hook.on_task_start("pergunta qualquer")

    assert len(seen) == 1
    assert seen[0].task_instruction == "pergunta qualquer"
