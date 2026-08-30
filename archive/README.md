# Histórico de Versões (Arquivo)

Estes arquivos são mantidos apenas como referência histórica. **O código de
produção agora vive no pacote `tessera/`** na raiz do projeto — não importe
nada diretamente destes arquivos legados.

| Arquivo | O que era | Por que foi substituído |
|---|---|---|
| `v1_memory_graph_retrieval.py` | Protótipo inicial (`MemoryGraphIndex`) | Sem gating de escrita, sem resolução de conflitos temporais, seed nodes limitados a 5 — puramente uma prova de conceito de grafo + TF-IDF + PageRank. |
| `v2_memory_graph_retrieval.py` | Reescrita completa introduzindo `TesseraEngine`, `WriteGatingEngine`, `ConflictResolver`, `MemoryFrontmatter` | Primeira versão "de produção", mas com o limite de seed nodes ainda em 5 — insuficiente para datasets densos (o `ConflictResolver` não enxergava o histórico temporal completo). |
| `v3_memory_graph_retrieval_original.py` | Mesma arquitetura da v2 | Único fix: `SEED_NODE_LIMIT` de 5 → 30 e `SEED_NODE_MIN_SIMILARITY` de 0.05 → 0.01, para que o resolvedor de conflitos receba todo o horizonte temporal relevante antes de filtrar. Esta é a versão usada como base do pacote `tessera/` atual. |

## O que mudou na reorganização para `tessera/`

A v3 foi exatamente o motor levado para o pacote — **nenhuma lógica foi
alterada**, apenas dividida em módulos com responsabilidade única:

- `tessera/models.py` ← dataclasses `Entity`, `Connection`, `MemoryFrontmatter` + exceções
- `tessera/security.py` ← `WriteGatingEngine`
- `tessera/conflict.py` ← `ConflictResolver`
- `tessera/engine.py` ← `TesseraEngine` (write/build_index/retrieve_context)
- `tessera/cli.py` ← novo: interface de linha de comando (`tessera init/write/index/query`)

Isso torna o projeto testável por módulo, instalável via `pip install -e .`,
e evita que qualquer consumidor precise saber qual "vX" usar.
