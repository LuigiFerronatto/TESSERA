"""
Tessera quickstart example.

Run with:
    python examples/quickstart.py
(after `pip install -e .` from the Tessera/ directory)
"""

import tempfile

from tessera import TesseraEngine, Connection, Entity


def main():
    with tempfile.TemporaryDirectory() as storage_dir:
        engine = TesseraEngine(storage_dir=storage_dir)

        # 1. Write a factual memory.
        engine.write_memory_note(
            mem_id="mem_fact_001",
            mem_type="factual",
            episode_id="ep_001",
            content="Maria configurou com sucesso a replicação de leitura do PostgreSQL.",
            tags=["postgresql", "infraestrutura"],
            entities=[Entity("Maria", "Engenheira de dados.")],
        )

        # 2. Write a procedural anchor (a "skill") connected to the fact above.
        engine.write_memory_note(
            mem_id="sk_deploy_db",
            mem_type="procedural_anchor",
            episode_id="ep_002",
            content=(
                "### Procedimento de Deploy do PostgreSQL\n"
                "1. Validar a porta 5432 livre.\n"
                "2. Iniciar o serviço com systemctl.\n"
                "3. Gerar dump de segurança com pg_dump."
            ),
            tags=["postgresql", "devops"],
            entities=[Entity("PostgreSQL", "Banco de dados relacional.")],
            active_connections=[Connection(target_memory_id="mem_fact_001", relation_type="stabilizes_service")],
        )

        # 3. Build the knowledge graph index.
        engine.build_index()

        # 4. Retrieve relevant memories for a query.
        results = engine.retrieve_context(
            query_text="Como faço deploy seguro do PostgreSQL configurado pela Maria?",
            top_n=3,
            resolve_conflicts=True,
        )

        for i, r in enumerate(results, 1):
            print(f"[{i}] {r['id']} ({r['type']}) score={r['score']:.4f}")
            print(r["body"].strip())
            print("-" * 60)


if __name__ == "__main__":
    main()
