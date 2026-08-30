## Executive takeaway
<!-- What changed and why should a maintainer care? 2–4 lines. -->

## Em linguagem simples
<!-- Explain the task conversationally before the technical detail. -->

## Objetivo
<!-- What specific problem does this PR try to solve? -->

## Issue / Test Card
Closes #

**Hypothesis:**

**Baseline:**

**Success gate:**

**Decision so far:** `PENDING | KEEP | ITERATE | REVERT | DROP | DEFER`

## O que mudou tecnicamente
- 

## Exemplo antes / depois
### Before
```text

```

### After
```text

```

## Como testar
```bash
# exact reproducible commands
```

## Evidências
<!-- CI, benchmark artifacts, query examples and relevant measurements. -->

| Metric | Baseline | This PR | Delta |
| --- | ---: | ---: | ---: |
|  |  |  |  |

## Learnings
### O que funcionou
- 

### O que falhou / surpreendeu
- 

### Limitações conhecidas
- 

## Arquitetura / invariants checklist
- [ ] Source files remain the source of truth; index/artifacts are derived and rebuildable.
- [ ] TESSERA returns structured evidence, not the final answer for the agent.
- [ ] Exactly 3 semantic drawers remain: `facts`, `preferences`, `insights`.
- [ ] New concepts are facets/metadata unless there is explicit evidence for a drawer change.
- [ ] No mandatory generative LLM was introduced in the basic path.
- [ ] Retrieval relevance was not conflated with confidence, authority or utility.
- [ ] No silent mutation of user source files.

## Follow-ups
<!-- New work becomes a new Issue/Test Card; do not hide unrelated TODOs in this PR. -->
- [ ] None

## Merge gate
- [ ] Issue/Test Card linked
- [ ] Tests green
- [ ] Relevant sanity/benchmark gate green or explicitly waived with rationale
- [ ] Evidence & Learnings updated in the Issue
- [ ] Final decision recorded
