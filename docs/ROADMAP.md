# TESSERA — Experimental Roadmap

TESSERA é uma camada agnóstica de memória que esconde do agente a complexidade de armazenamento, indexação, relações, temporalidade e retrieval, enquanto preserva evidência, provenance e navegabilidade suficientes para que o próprio agente decida como usar aquela memória.

> TESSERA abstracts memory architecture away from the agent. It does not replace the cognition of the agent; it hides memory complexity so the agent can focus on cognition.

## Executive takeaway

A Foundation atual já prova **identidade estável, retrieval explicável, evidence query-aware, provenance e CI**. O próximo passo não é adicionar “mais inteligência” por intuição: primeiro tornamos indexing incremental e diagnosticável; depois começamos LongMemEval cedo; só então testamos relações, temporalidade, arbitration e adaptive retrieval como **ablations**.

Research recente refinou esses experimentos sem mudar a prioridade imediata:

```text
GraphMemix → query-aware graph expansion + evidence budget
CaSKG      → relation origin/confidence/validation
MemToC     → source/evidence arbitration + four-state abstention
RENDER     → retrieval quality ≠ renderer quality
```

Esses sinais viraram Test Cards próprios; não são capacidades já aprovadas do TESSERA.

## Product invariants

- Source text é a fonte da verdade; índice/cache/ledger são derivados e rebuildable.
- TESSERA retorna **structured evidence**, não a resposta final do agente.
- Existem exatamente **3 drawers semânticos**: `facts`, `preferences`, `insights`.
- `document_type`, harness, scope, temporal state, authority, confidence, relations, quality e utility são facets/metadata, não novas gavetas.
- TESSERA é text-first/auditável; código não é primary memory.
- Nenhum LLM generativo é obrigatório no caminho básico.
- Retrieval relevance ≠ confidence ≠ authority ≠ relation confidence ≠ temporal validity ≠ utility.
- User source files nunca são silenciosamente reescritos durante indexing.
- Relação existente ≠ relação confiável ≠ relação útil para a query atual.
- Conflito detectado ≠ conflito resolvido.

## Delivery model: Issue → Test Card → PR → Evidence → Decision

Toda mudança deve nascer como uma hipótese, não como uma feature presumidamente correta.

1. Abrir uma **Issue exclusiva** para uma unidade de trabalho/decisão.
2. Preencher o **Test Card** antes do código: hypothesis, baseline, experiment, metrics, success/failure signals.
3. Criar branch e PR vinculados (`Closes #...` quando aplicável).
4. PR precisa explicar a tarefa em três níveis: **Executive takeaway**, **Em linguagem simples**, **Technical implementation**.
5. Atualizar a Issue durante a execução com Evidence & Learnings.
6. Rodar CI + sanity/benchmark pertinente.
7. Registrar decisão explícita: **KEEP / ITERATE / REVERT / DROP / DEFER**.
8. Follow-up vira nova Issue; não esconder workstream dentro de TODO de PR.

Templates:
- `.github/ISSUE_TEMPLATE/test-card.md`
- `.github/pull_request_template.md`

Roadmap index vivo: **Issue #22**.

---

# Status atual

## Foundation — tornar a memória auditável e previsível

| Status | Issue | Capability | Implementation |
| --- | --- | --- | --- |
| ✅ | #7 | F0 Output Contract | PR #1 merged |
| ✅ | #8 | F10/F11 Explainable Ranking + Query-aware Evidence | PR #2 merged |
| ✅ | #9 | F2-F5/F7 Canonical Metadata + Classification + Stable Identity | PR #3 merged |
| ✅ | #10 | F1/F12 CI + deterministic sanity evaluation | PR #4 merged |
| ✅ | #11 | F6 Evidence Ledger + Provenance | PR #6 merged |
| ⬜ | #12 | F8 Incremental & Idempotent Indexing | **Next technical Test Card** |
| ⬜ | #13 | F9 Metadata Doctor | Planned after #12 |

## Intelligence — testar se estrutura adicional melhora retrieval

| Status | Issue | Experiment |
| --- | --- | --- |
| ⬜ | #14 | Typed Relations + controlled graph expansion |
| ⬜ | #25 | Query-aware graph expansion + evidence budget |
| ⬜ | #26 | Relation origin + confidence + validation |
| ⬜ | #15 | Temporal Model + State Keys |
| ⬜ | #16 | Conflict Resolution + Supersession |
| ⬜ | #27 | Evidence / Source Arbitration |
| ⬜ | #32 | Source authority + scope + instruction precedence |

## Adaptive — usar apenas a complexidade necessária por query

| Status | Issue | Experiment |
| --- | --- | --- |
| ⬜ | #17 | Query Compiler + Adaptive Retrieval |
| ⬜ | #19 | Write Gating / Memory Admission |

## Evaluation / State

| Status | Issue | Experiment |
| --- | --- | --- |
| ⬜ | #18 | LongMemEval V1/V2 adapters + ablations |
| ⬜ | #28 | RAW vs EVIDENCE vs STRUCTURED rendering ablation |
| ⬜ | #20 | State Reconstruction + Evidence Sufficiency + Abstention |

## Learning — somente depois de provar as camadas anteriores

| Status | Issue | Experiment |
| --- | --- | --- |
| ⬜ | #21 | Experience Traces + Derived Insights + Utility Feedback |

---

# Research-derived experiment map

Esses Test Cards existem para transformar papers em hipóteses mensuráveis, não em features automáticas.

| Research signal | TESSERA Test Card | Pergunta que vamos medir |
| --- | --- | --- |
| GraphMemix | #25 | Query-aware/budgeted graph expansion supera 1-hop indiscriminado em qualidade/custo? |
| CaSKG | #26 | Relation confidence/validation reduz expansão nociva sem destruir recall? |
| MemToC | #27 | Evidence Arbitration melhora source selection e abstention versus silent winner? |
| MemToC | #20 | Quatro estados (`sufficient`, `insufficient`, `conflicting`, `ambiguous`) melhoram control flow? |
| MemToC + harness scope | #32 | Authority + scope + precedence resolvem instruções melhor que newest/relevance wins? |
| RENDER | #28 | O renderer muda downstream QA quando retrieval/evidence ficam congelados? |

### Relações: quatro dimensões que não devem ser misturadas

```text
relation_type
→ o que a relação significa

relation_origin
→ de onde a relação veio

relation_confidence
→ quanto acreditamos que a aresta está correta

query_relevance
→ quanto vale navegar esta aresta nesta query
```

### Evidence status futuro

```text
sufficient
→ continue

insufficient
→ search / expand

conflicting
→ inspect provenance / arbitration

ambiguous
→ verify / ask / tool call
```

TESSERA fornece esse sinal de infraestrutura; o consuming agent continua responsável pela decisão cognitiva final.

---

# Recommended execution order

```text
CURRENT FOUNDATION
  #12 Incremental & Idempotent Indexing
      ↓
  #13 Metadata Doctor
      ↓
MEASURE EARLY
  #18 LongMemEval V1 baseline/adapter
    └─ #28 Renderer control starts here
      ↓
RELATIONS ABLATIONS
  #14 Typed Relations / controlled expansion
    ├─ #25 Query-aware evidence budget
    └─ #26 Relation confidence / validation
      ↓
TEMPORAL + STATE
  #15 Temporal Model + State Keys
      ↓
CONFLICT / TRUST
  #16 Conflict/Supersession
    ├─ #27 Evidence Arbitration
    └─ #32 Authority / scope / instruction precedence
      ↓
ADAPTIVE
  #17 Query Compiler/Adaptive Retrieval
  #19 Write Gating
      ↓
STATE / ABSTENTION
  #20 State Reconstruction + 4-state evidence status
      ↓
LEARNING
  #21 Experience + Utility
```

LongMemEval não deve existir apenas no fim. O adapter/base benchmark começa assim que Foundation estiver estável o suficiente, e as novas camadas entram depois como **ablations mensuráveis**.

---

# Foundation pipeline — o que existe hoje

```text
TEXT FILES
   ↓
① DISCOVER
   ↓
② UNDERSTAND
   ├── document type
   ├── metadata
   ├── scope
   └── semantic drawer
   ↓
③ NORMALIZE
   ├── explicit metadata
   ├── inferred metadata
   └── stable identity
   ↓
④ TRACE
   ├── source
   ├── spans
   ├── hashes
   └── evidence ledger
   ↓
⑤ CONNECT
   ├── explicit links
   ├── relations
   └── graph
   ↓
⑥ INDEX
   └── current rebuild/cache behavior
   ↓
⑦ RETRIEVE
   ├── candidates
   ├── explainable ranking
   └── relevant evidence
   ↓
⑧ RETURN
   └── structured evidence + provenance
   ↓
AGENT
```

A parte incremental/idempotente de `INDEX` ainda é #12; não deve ser apresentada como capability implementada antes do Test Card fechar.

---

# Target pipeline — se os Test Cards forem KEEP

```text
QUERY
  ↓
Candidate Retrieval
  ↓
Seed Evidence
  ↓
Query-Aware Graph Expansion
  ↓
Relation Type / Origin / Confidence
  ↓
Temporal Validity + State Keys
  ↓
Authority / Scope / Precedence
  ↓
Conflict Detection
  ↓
Evidence Arbitration
  ↓
Evidence Status
  ├── sufficient
  ├── insufficient
  ├── conflicting
  └── ambiguous
  ↓
Renderer
  ├── RAW
  ├── EVIDENCE
  └── STRUCTURED
  ↓
CONSUMING AGENT
```

Esse pipeline é **target architecture**, não descrição do `main` atual.

---

# Test Card lifecycle

Cada Issue é um experimento vivo e deve ser atualizada com:

- **Hypothesis** — o que acreditamos que a mudança melhora.
- **Baseline** — comportamento atual antes da alteração.
- **Experiment** — mudança + controle/comparação.
- **Metrics** — qualidade, tokens, latency, correctness, provenance etc.
- **Evidence** — CI, benchmark artifacts, outputs reproduzíveis.
- **Learnings** — acertos, falhas, surpresas, limitações.
- **Decision** — KEEP / ITERATE / REVERT / DROP / DEFER.
- **Follow-ups** — novas Issues.

Uma implementação tecnicamente correta pode terminar em **DROP** se não produzir ganho real. Esse resultado é válido e deve ser preservado como aprendizado do roadmap.

---

# Current retrieval baseline

O CI determinístico introduzido no PR #4 mantém um sanity baseline de regressão:

- Hit@1: **75%**
- Hit@3: **100%**
- Hit@5: **100%**
- MRR: **0.875**
- Evidence hit rate: **100%**

Isso não é benchmark competitivo. É apenas um alarme de regressão. Exemplo de limitação preservada deliberadamente: a paráfrase `pq o LAO existe?` ainda pode falhar no Top-1 lexical, e não deve ser “corrigida” com tuning específico antes das ablations/benchmark (#18).

---

# Current capabilities — examples

Hoje o TESSERA já consegue:

```text
query: "qual o propósito do LAO?"
  → explainable multi-signal ranking
  → relevant_evidence
  → full memory
  → related IDs / graph signal
  → canonical metadata
  → stable source identity
  → provenance + source version hashes
  → exact evidence span when uniquely provable
```

Também preservamos falhas úteis como baseline:

```text
query: "pq o LAO existe?"
  → gold memory pode aparecer em #2 em vez de #1
```

Isso é tratado como **evidência de uma limitação de paráfrase/semantic recall**, não como motivo para tuning ad hoc.

---

# Documentation / research layer

Current reference docs:

- `docs/OVERVIEW.md` — executive + colloquial + technical project overview.
- `docs/FEATURES.md` — implemented capability catalog.
- `docs/CONCEPTS.md` — canonical vocabulary and semantic distinctions.
- `docs/QUERY_EXAMPLES.md` — current examples + clearly marked future targets.
- `docs/research/REFERENCES.md` — primary research/product sources.
- `docs/research/PAPER_NOTES.md` — what each paper says and how it maps to Test Cards.
- `docs/research/COMPETITIVE_LANDSCAPE.md` — products/frameworks/research comparison.
- `docs/research/DECISION_TRACE.md` — source → insight → issue → decision trace.

Documentation follow-ups remain tracked separately so docs do not become a single giant task.

---

# GitHub Project fields recommended

O board de GitHub Projects v2 deve espelhar estas Issues com os seguintes fields:

- `Phase`: Foundation / Intelligence / Adaptive / Evaluation / State / Learning
- `Status`: Backlog / Ready / In Progress / Measuring / Decision / Done / Dropped
- `Decision`: Pending / Keep / Iterate / Revert / Drop / Defer
- `Test Card`: Draft / Ready / Updated
- `Impact`: Low / Medium / High / Transformational
- `Evidence`: Missing / Partial / Sufficient
- `Benchmark Gate`: N/A / Pending / Pass / Fail
- `PR`: linked PR

> Limitação operacional atual: Issues + arquivos versionados são a fonte operacional do roadmap. Um board visual deve espelhar esses cards, não criar uma segunda fonte de verdade.