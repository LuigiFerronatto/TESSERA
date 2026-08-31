"""Contract regression tests for TESSERA to freeze the structured evidence contract."""

import tempfile
import pytest

from tessera import TesseraEngine, Connection, Entity

@pytest.fixture
def populated_engine():
    with tempfile.TemporaryDirectory() as tmp:
        engine = TesseraEngine(storage_dir=tmp)
        
        # Write some real-world-style sample notes
        engine.write_memory_note(
            mem_id="project/charter",
            mem_type="factual",
            episode_id="ep_project_001",
            content="O projeto existe para servir de ambiente de execução autônomo, não apenas como um agente isolado.",
            tags=["project", "purpose", "charter"],
            entities=[Entity("Project", "Example autonomous project")]
        )
        
        engine.write_memory_note(
            mem_id="project/learning-process",
            mem_type="procedural_anchor",
            episode_id="ep_project_002",
            content="O agente aprende registrando episódios de forma atômica no TESSERA e recuperando âncoras procedimentais diante de erros.",
            tags=["project", "learning"],
            entities=[Entity("Project", "Example autonomous project")]
        )
        
        engine.write_memory_note(
            mem_id="gotchas/copilot-worktree-error",
            mem_type="factual",
            episode_id="ep_copilot_001",
            content="Tivemos um erro crítico com o Copilot CLI onde a remoção de um worktree invalidou o CWD e quebrou os hooks subsequentes.",
            tags=["copilot", "gotcha", "error"],
            entities=[Entity("Copilot", "Copilot CLI")]
        )
        
        engine.write_memory_note(
            mem_id="project/memory-structure",
            mem_type="procedural_anchor",
            episode_id="ep_tessera_001",
            content="A memória do agente funciona usando TESSERA para separar fatos, preferências e insights (procedural anchors).",
            tags=["tessera", "memory", "structure"],
            entities=[Entity("TESSERA", "Memory infrastructure")],
            active_connections=[Connection(target_memory_id="project/learning-process", relation_type="supports")]
        )
        
        engine.build_index()
        yield engine

@pytest.mark.parametrize("query", [
    "por que o projeto existe?",
    "qual o propósito do projeto?",
    "como o agente aprende?",
    "qual erro tivemos com o Copilot?",
    "como funciona a memória do agente?"
])
def test_output_contract_preservation(populated_engine, query):
    """
    Ensure that retrieve_context returns structured evidence following the frozen contract.
    No future changes can accidentally remove: name (id), type, score, source/path, relations, metadata, or content.
    """
    results = populated_engine.retrieve_context(query, top_n=3)
    
    # Ensure we got some matches for our targeted queries
    assert len(results) > 0, f"Query '{query}' returned no memories, index or search might be broken."
    
    for item in results:
        # 1. Identity / Name (id)
        assert "id" in item, "Missing 'id' (name/identity) field from retrieval contract."
        assert isinstance(item["id"], str)
        assert len(item["id"]) > 0
        
        # 2. Type
        assert "type" in item, "Missing 'type' field from retrieval contract."
        assert item["type"] in ["factual", "preference", "procedural_anchor"]
        
        # 3. Score
        assert "score" in item, "Missing 'score' field from retrieval contract."
        assert isinstance(item["score"], (float, int))
        
        # 4. Source / Path
        assert "filepath" in item, "Missing 'filepath' (source path) field from retrieval contract."
        assert "filename" in item, "Missing 'filename' (source filename) field from retrieval contract."
        assert item["filepath"] is not None
        assert item["filename"] is not None
        
        # 5. Relations
        assert "related_ids" in item, "Missing 'related_ids' (relations) field from retrieval contract."
        assert isinstance(item["related_ids"], list)
        for rel in item["related_ids"]:
            assert isinstance(rel, str)
            
        # 6. Metadata
        assert "frontmatter" in item, "Missing 'frontmatter' (metadata) field from retrieval contract."
        assert isinstance(item["frontmatter"], dict)
        # Check that basic frontmatter fields exist
        assert "id" in item["frontmatter"]
        assert "node_type" in item["frontmatter"]
        
        # 7. Content
        assert "body" in item, "Missing 'body' (content) field from retrieval contract."
        assert isinstance(item["body"], str)
        assert len(item["body"].strip()) > 0
