"""Tests specifically covering Phase 1: Retrieval & Ranking (Multi-Signal Scoring & Debug) and Phase 2: Query-Aware Evidence."""

import tempfile
import pytest

from tessera import TesseraEngine, Connection, Entity

@pytest.fixture
def populated_engine():
    with tempfile.TemporaryDirectory() as tmp:
        engine = TesseraEngine(storage_dir=tmp)
        
        # Write some real-world-style sample notes
        # Node matching 'lao' purpose
        engine.write_memory_note(
            mem_id="lao/charter",
            mem_type="factual",
            episode_id="ep_lao_001",
            content="""# LAO Charter
O propósito do LAO (Lab Autonomous Officer) é fornecer um runtime de execução de agentes autônomos de alta confiabilidade.

Este é o parágrafo irrelevante que não deve ser selecionado pela busca como evidência relevante.
""",
            tags=["lao", "purpose", "charter"],
            entities=[Entity("LAO", "Lab Autonomous Officer")]
        )
        
        # Node sharing tags but not directly about purpose
        engine.write_memory_note(
            mem_id="lao/learning-process",
            mem_type="procedural_anchor",
            episode_id="ep_lao_002",
            content="O LAO aprende registrando episódios de forma atômica no TESSERA e recuperando âncoras procedimentais diante de erros.",
            tags=["lao", "learning"],
            entities=[Entity("LAO", "Lab Autonomous Officer")]
        )
        
        engine.build_index()
        yield engine

def test_explainable_score_contains_all_signals(populated_engine):
    """Verify that score_explain is present and populated with all expected fields."""
    results = populated_engine.retrieve_context("propósito do LAO", top_n=2)
    assert len(results) > 0
    
    for r in results:
        assert "score_explain" in r
        exp = r["score_explain"]
        for field in ["lexical", "title", "metadata", "relations", "type_boost", "recency_boost"]:
            assert field in exp
            assert isinstance(exp[field], float)

def test_query_aware_evidence_extraction(populated_engine):
    """Verify that relevant_evidence extracts the exact paragraph containing the answer."""
    results = populated_engine.retrieve_context("O propósito do LAO", top_n=1)
    assert len(results) > 0
    hit = results[0]
    
    # It must extract the first paragraph, which contains the target query terms
    assert "propósito do LAO" in hit["relevant_evidence"]
    assert "parágrafo irrelevante" not in hit["relevant_evidence"]

def test_ranking_robustness_on_paraphrases(populated_engine):
    """Verify that paraphases of 'purpose' correctly place lao/charter as #1."""
    queries = [
        "pq o LAO existe?",
        "qual o propósito do LAO?",
        "qual a missão do LAO?",
        "por que ele foi criado?",
        "what is LAO's purpose?"
    ]
    for q in queries:
        results = populated_engine.retrieve_context(q, top_n=2)
        assert len(results) > 0
        # The charter node should rank first due to title matching, tf-idf, or tags
        assert results[0]["id"] == "lao/charter", f"Query '{q}' failed to rank 'lao/charter' as #1."
