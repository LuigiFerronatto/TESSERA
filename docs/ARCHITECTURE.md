# Arquitetura do Tessera

> Este documento consolida o racional científico e o design técnico do Tessera.
> Para o "como usar" (instalação, CLI, exemplos), veja o [README](../README.md).
> Para a explicação linha a linha das classes/métodos, veja [CODE_EXPLANATION.md](CODE_EXPLANATION.md).
> Para o conceito de âncoras procedimentais em detalhe, veja [PROCEDURAL_ANCHORS.md](PROCEDURAL_ANCHORS.md).

## Por que não RAG plano

Buscas vetoriais planas (RAG tradicional) sofrem três problemas em agentes de
longa duração como o LAO:

1. **Saturação de contexto** — histórico bruto de diálogo cresce sem limite.
2. **Desalinhamento temporal** — preferências antigas competem com as atuais
   sem nenhum critério de recência.
3. **Propagação de ruído** — blocos de texto isolados, sem estrutura de
   relacionamento, poluem a recuperação com resultados semanticamente
   próximos mas irrelevantes.

O Tessera responde a isso com uma abordagem híbrida: cada memória é um **cartão
atômico** (Markdown + YAML frontmatter) e a recuperação usa um **grafo de
conhecimento heterogêneo** com PageRank ponderado dinamicamente, não apenas
similaridade de cosseno.

## Os quatro pilares científicos

| # | Pilar | Problema de origem | Solução no Tessera |
|---|-------|---------------------|------------------|
| 1 | **Decomposição de Memória Tipada** (QUMem) | Logs brutos saturam o contexto | Notas classificadas em `factual`, `preference`, `procedural_anchor` |
| 2 | **Âncoras Procedimentais** (Skills as Anchors) | Agentes falham em setup/sintaxe básicos | Nós `procedural_anchor` com checklists e known pitfalls |
| 3 | **Recuperação Adaptativa por Subgrafo (DW-PR)** (MemORAI) | RAG plano traz ruído irrelevante | Seed nodes → expansão 1-hop → PageRank ponderado dinamicamente |
| 4 | **Gating de Escrita** (anti State Contamination) | "Memory laundering" contamina o agente | Sanitização e auditoria antes de qualquer escrita em disco |

## Fluxo de dados

```
[ Ingestão / Escrita ]
Conteúdo bruto ──► WriteGatingEngine (audit_and_sanitize)
                 ──► MemoryFrontmatter (YAML)
                 ──► Gravação física em memories/{id}.md

[ Recuperação ]
Query ──► TF-IDF cosine similarity (seed nodes, top 30)
       ──► Expansão de subgrafo 1-hop (successors + predecessors)
       ──► Pesos dinâmicos de aresta (DW-PR, boost 1.35x em relações procedurais)
       ──► PageRank personalizado nos seed nodes
       ──► Filtro: apenas nós factual/preference/procedural_anchor
       ──► ConflictResolver (mantém só a nota mais recente por assunto)
       ──► top_n memórias retornadas
```

## Mapeamento código → conceito

| Classe / módulo | Responsabilidade |
|---|---|
| `tessera.models.Entity`, `Connection`, `MemoryFrontmatter` | Modelo de domínio dos cartões atômicos |
| `tessera.security.WriteGatingEngine` | Auditoria e sanitização antes da escrita física |
| `tessera.conflict.ConflictResolver` | Resolução cronológica de preferências/fatos conflitantes |
| `tessera.engine.TesseraEngine` | Orquestra escrita, indexação do grafo e recuperação (DW-PR) |
| `tessera.cli` | Interface de linha de comando (`tessera init/write/index/query`) |

## Estrutura física de memórias em disco

```
minha-app/
└── memories/
    ├── mem_fact_0312a.md      # Notas Factuais
    ├── mem_pref_0892f.md      # Notas de Preferências
    ├── sk_docker_setup_01.md  # Âncoras Procedimentais (Skills)
```

O índice do grafo é reconstruído em memória a cada `build_index()` — não há
banco de dados externo. **Se você apagar o índice, os `.md` continuam
100% legíveis e editáveis manualmente.** Essa é uma decisão deliberada de
design (desacoplamento leitura/escrita).

## Exemplo de nota física (`.md` com frontmatter)

```markdown
---
id: sk_docker_setup_01
node_type: procedural_anchor
tags: [docker, devops]
entities:
  - name: Docker
    description: Motor de containers.
active_connections:
  - target_memory_id: ent_docker_daemon
    relation_type: stabilizes_service
security:
  gating_status: passed
  toxicity_score: 0.012
  sanitized: true
---

# Fluxo de Configuração de Containers Docker

1. Verificar se o daemon está ativo (`docker info`).
2. Validar presença do `docker-compose.yml`.
3. Subir serviços com `docker-compose up -d --build`.
4. Testar saúde do serviço (`curl localhost:8080/health`).

## Known Pitfalls
* Rodar build antes do daemon estar ativo.
* Conflito de hostnames locais com as pontes de rede do container.
```

## Diferenciais de produção

- **Desacoplamento leitura/escrita** — o grafo é só um índice; os arquivos
  `.md` são a fonte de verdade e sobrevivem à perda do índice.
- **Alinhamento temporal (FinPerMA)** — trajetórias ordenadas de preferência
  evitam que o agente regrida a escolhas obsoletas.
- **Estabilidade de execução de tools** — âncoras procedimentais reduzem
  drasticamente erros de setup/sintaxe comparado a injetar logs de erro brutos.

## Histórico de versões

Veja [`archive/README.md`](../archive/README.md) para o histórico de v1 → v2 → v3
e o que mudou em cada uma. O pacote `tessera/` atual consolida a v3 (a mais madura),
dividida em módulos (`models.py`, `security.py`, `conflict.py`, `engine.py`, `cli.py`).
