# TESSERA Foundation — Roadmap (v0.x)

Este documento estabelece as garantias fundamentais e o plano de evolução do **TESSERA** com base no conceito de **Structured Evidence** e na arquitetura de memória agnóstica para agentes autônomos.

---

## O Contrato Fundamental do TESSERA

O TESSERA não gera a resposta final no lugar do agente. Seu papel é **esconder a complexidade da infraestrutura de memória** e devolver ao agente uma **evidência estruturada, navegável e auditável** para que ele tome decisões e faça seu raciocínio.

```
Agent
  │
  │ natural-language query
  ▼
TESSERA
  ├─ encontra memórias
  ├─ sabe onde estão
  ├─ entende metadata
  ├─ conhece relações
  └─ esconde a arquitetura interna
  │
  ▼
Structured Evidence
  ├─ identity
  ├─ type
  ├─ score
  ├─ source
  ├─ relations
  ├─ metadata
  └─ full content
  │
  ▼
Agent reasons (O agente principal executa a inferência e responde)
```

---

## As Cinco Garantias Fundamentais

Qualquer agente que consuma o TESSERA deve ter cinco garantias fundamentais:

1. **Encontrar (Find):** Localizar o conhecimento certo baseado na relevância léxica, semântica e estrutural.
2. **Explicar (Explain):** Devolver evidência relevante específica da query (Query-aware evidence) sem perder o conteúdo completo.
3. **Rastrear (Track):** Conectar notas por relações tipadas úteis no retrieval.
4. **Permanecer Consistente (Consistency):** Indexação incremental e idempotente robusta, livre de orfandade ou duplicações.
5. **Provar (Prove):** Proveniência rigorosa com caminhos, spans, hashes de conteúdo e metadados de indexação.

---

## Roadmap — TESSERA Foundation

### 0. Freeze Current Contract (Phase 0) — 🟢 CONCLUÍDO
Antes de qualquer melhoria estrutural de ranking ou dados, garantimos que o formato de saída do TESSERA esteja congelado e protegido contra regressões.
- **Implementação:** Fixtures de testes com queries reais e validação rigorosa da existência dos campos:
  - `id` (name/identity)
  - `type`
  - `score`
  - `filepath` & `filename` (source/path)
  - `related_ids` (relations)
  - `frontmatter` (metadata)
  - `body` (content)
- **Status:** Coberto em `tests/test_contract_regression.py` e validado contra regressões.

### 1. FIND THE RIGHT THING (Retrieval & Ranking) — 🟡 PRÓXIMO PASSO
Melhorar o retrieval e ranking determinístico sem LLM.
- **Objetivos:**
  - Normalização da intenção da query.
  - Combinação refinada de score léxico + semântico.
  - Atribuição de pesos de tipo (type boosts) e pesos de escopo (scope weights).
  - Utilização ativa das relações estruturais (PageRank/DW-PR).
  - Temporal relevance e atenuação por tempo.
  - Diversificação e redução de redundâncias de documentos quase duplicados.
  - Explicação visível do score total em modo `--debug`.

### 2. EXPLAIN WHY IT MATCHED (Relevant Evidence)
Oferecer Query-aware Evidence preservando o conteúdo completo da memória.
- **Objetivos:**
  - Adicionar a propriedade `relevant_evidence` contendo o trecho exato que responde à query.
  - Mostrar esse trecho de forma clara no output CLI e MCP, vindo antes do conteúdo original.

### 3. PROVE WHERE IT CAME FROM (Provenance)
Garantir rastreabilidade cirúrgica de cada cartão atômico.
- **Objetivos:**
  - Adicionar a estrutura de `provenance` no YAML e no output:
    ```yaml
    source:
      file: docs/ARCHITECTURE.md
      start_line: 182
      end_line: 194
      content_hash: "a3f5c71b..."
      indexed_at: "2026-08-30T15:30:00Z"
    ```
  - Permitir auditoria offline direta da verdade acreditada pelo TESSERA.

### 4. KEEP MEMORY CONSISTENT (Incremental Indexing)
Tornar o pipeline de indexação 100% idempotente e incremental.
- **Objetivos:**
  - Detecção rápida de alterações (created, changed, renamed, moved, deleted).
  - Prevenção de nós órfãos, links quebrados ou duplicações após renomeações.
  - Log analítico de varredura ultra-rápido.

### 5. MEASURE EVERYTHING (Sanity Benchmark)
Benchmark de sanidade real com dataset de queries locais do LAO.
- **Objetivos:**
  - Medição empírica de métricas de Retrieval (Recall@k, Precision@k, MRR, nDCG).
  - Medição de eficiência de tokens e latência offline vs. online.
  - Abordagem de ablation testing dos componentes do TESSERA.
