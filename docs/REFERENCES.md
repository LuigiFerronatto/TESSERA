# Referências Científicas

Este índice curto reúne os papers de memória de longo prazo que influenciam o TESSERA.

Para a análise auditável — **o que a fonte afirma → como o TESSERA interpreta → o que deve ser testado → o que está implementado** — use:

- [research/REFERENCES.md](research/REFERENCES.md): bibliografia, sinais e relação com a arquitetura;
- [research/PAPER_NOTES.md](research/PAPER_NOTES.md): notas estruturadas e hipóteses experimentais.

A presença de uma fonte nesta lista não significa que seu método foi implementado ou validado pelo TESSERA.

## Papers de referência

1. Heng Wang et al. **QUMem: Personalized Memory for Query-Conditioned User-State Inference in LLM Agents**. 2026.  
   https://arxiv.org/abs/2608.16168

2. Geng Li et al. **GraphMemix: Query-Aware Evidence Forests for Long-Term Multimodal Agent Memory**. 2026.  
   https://arxiv.org/abs/2608.26983

3. Zhichen Liu et al. **LiveMem: Maintaining Memory State Continuity in Long-Running LLM Inference**. 2026.  
   https://arxiv.org/abs/2608.02515

4. Ben Wang et al. **FinPerMA: A Theory-Informed, Event-Grounded Personalized-Memory Benchmark for LLM Agents**. 2026.  
   https://arxiv.org/abs/2608.04095

5. Rebecca Westhäußer, Wolfgang Minker e Sebastian Zepf. **Enabling Personalized Long-term Interactions in LLM-based Agents through Persistent Memory and User Profiles**. 2025.  
   https://arxiv.org/abs/2510.07925

6. Yian Wang, Agam Goyal, Yuen Chen e Hari Sundaram. **State Contamination in Memory-Augmented LLM Agents**. 2026.  
   https://arxiv.org/abs/2605.16746

7. Hung Pham Van et al. **MemORAI: Memory Organization and Retrieval via Adaptive Graph Intelligence for LLM Conversational Agents**. Findings of ACL 2026.  
   https://aclanthology.org/2026.findings-acl.1408/  
   Preprint: https://arxiv.org/abs/2605.01386

## Regra de uso

Ao citar qualquer paper na documentação ou em uma decisão de arquitetura:

```text
fonte primária
→ afirmação da fonte
→ interpretação do TESSERA
→ Test Card / experimento
→ evidência produzida pelo TESSERA
```

Não transforme resultados externos em claims do TESSERA e não descreva uma capacidade como implementada apenas porque ela aparece em um paper de referência.
