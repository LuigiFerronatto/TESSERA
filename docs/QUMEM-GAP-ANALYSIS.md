# Tessera vs. QUMem — auditoria de fidelidade científica (2026-08-26)

O design do Tessera se declara fundamentado no paper **QUMem** (arXiv
2608.16168) — ver `REFERENCES.md`. Esta auditoria releu o paper por
completo (Abstract, Introduction, Related Work, Method §3.1–3.4,
Experiments, Ablations, Conclusion) e comparou cada uma das 3 contribuições
centrais do paper contra o código real (`engine.py`, `orchestrator.py`,
`models.py`, `conflict.py`, `hooks.py`), para separar "o que já está
fidedigno" de "o que é uma simplificação deliberada" de "o que é um gap
real que vale corrigir".

## Bug concreto corrigido nesta rodada (não é sobre o paper, é sobre robustez)

`TesseraEngine.write_memory_note()` fazia `os.path.join(storage_dir,
f"{mem_id}.md")` e escrevia direto, sem `os.makedirs(...)`. Isso causou,
em produção (run autônomo `/lao` de 2026-08-25/26, engine Gemini), um
`mem_id` sem prefixo de domínio (`voice-ai-blip-integration-strategy`,
sem `/`) cair solto na raiz de `.claude/memory/`, ao lado de
`MEMORY.md`/`README.md`, em vez de dentro de `research/<topico>/`.

Corrigido com 3 mudanças:
1. `engine.py`: `os.makedirs(os.path.dirname(filepath) or storage_dir,
   exist_ok=True)` antes do `open()` — nunca mais crasha em prefixo novo.
2. `engine.py`: `write_memory_note()` agora emite `warnings.warn(...)`
   quando `mem_id` não tem `/` — não bloqueia a escrita (uma run autônoma
   nunca deveria travar por uma questão de nomenclatura), mas torna o
   problema visível.
3. `mcp_server.py`: o docstring da tool `write_memory` agora exige
   explicitamente o formato `"<domínio>/<slug>"` com exemplos e menciona o
   incidente real — antes disso, nada no MCP tool guiava o LLM chamador.

Arquivo mal posicionado já foi movido para
`research/voice-ai-agentive-space/` (onde suas notas irmãs já viviam) com
o `id` de frontmatter corrigido, e o índice foi reconstruído (`tessera
doctor` confirma: 279 nós, 460 arestas, round-trip OK).

## 1. Dynamic Episode Construction — **✅ IMPLEMENTADO (2026-08-26, heurística)**

**Paper**: um classificador binário de continuidade leve (`f_θ`), rodado
turno a turno, decide se o próximo turno pertence ao mesmo episódio ou
fecha um novo. Episódios emergem dinamicamente da conversa, não são
delimitados manualmente.

**Tessera hoje** (~~antes desta rodada~~): `Episode` (`models.py`) é um
dataclass estático (`beginning`/`middle`/`end`) que o chamador preenche
explicitamente via `write_episode()`. Não existe nenhum mecanismo de
detecção automática de fronteira — busquei "continuity"/"boundary"/
"classifier" no código, zero ocorrências fora de `security.py` (que é
sobre outra coisa).

**Implementado**: `tessera/episode_boundary.py` — `EpisodeBoundaryTracker`,
uma heurística leve (não um classificador fine-tuned, custo desproporcional
ao ganho no estágio atual) que fecha um episódio automaticamente por (a)
timeout (`timeout_minutes`, default 30min) ou (b) queda de similaridade
TF-IDF entre o novo turno e o texto acumulado do episódio corrente
(`similarity_threshold`, default 0.03). Reaproveita o mesmo
`TfidfVectorizer`/`cosine_similarity` que `TesseraEngine.retrieve_context` já
usa para retrieval, sem dependência nova. Testado: fechamento por timeout
confirmado (gap de 45min fecha o episódio); fechamento por deriva de
tópico funciona para turnos com sobreposição lexical suficiente — para
frases muito curtas e lexicalmente disjuntas, TF-IDF puro é fraco (esperado
e documentado no próprio módulo), então o timeout continua sendo o sinal
mais confiável na prática. Não tem CLI/MCP dedicado ainda — é uma
primitiva de biblioteca (`from tessera.episode_boundary import
EpisodeBoundaryTracker`) para quem processa uma sequência de turnos
programaticamente antes de chamar `write_episode`/`decompose_and_write_episode`.

## 2. Typed Memory Decomposition — **✅ IMPLEMENTADO (2026-08-26, LLM real testado)**

**Paper**: um decompositor `g_φ` roda 3x por episódio (uma vez por tipo:
factual/preference/insight), cada chamada de LLM podendo extrair *múltiplas*
memórias atômicas daquele tipo.

**Tessera hoje** (~~antes desta rodada~~): `write_fact`/`write_preference`/
`write_insight` em `engine.py` mapeiam 1:1 para a taxonomia F/P/I do paper
— isso está correto e fiel. O que faltava era a automação: era o
*chamador* (skill, hook, agente) que decidia manualmente quantas notas
escrever e de qual tipo.

**Implementado**: `tessera/decomposer.py` — `decompose_episode()` (função
pura) e `decompose_and_write()` (decompõe + grava), expostos em 3 camadas
para manter paridade total:
- `TesseraEngine.decompose_and_write_episode(mem_id_prefix, episode_id, episode, llm_fn, tags)`
- `TesseraTaskHook.on_task_end_auto(task_instruction, episode, mem_id_prefix, llm_fn, tags)`
  — alternativa automática ao `on_task_end` manual existente
- CLI: `tessera decompose <storage_dir> --mem-id-prefix ... --beginning ... --middle ... --end ... --llm-backend <explicit-compatibility-name>`
- MCP: tool `decompose_episode(mem_id_prefix, beginning, middle, end, episode_id=None, tags=None)`

Cada memória extraída ainda passa pelo `WriteGatingEngine` normal (a
decomposição só decide *quantas* notas propor, nunca contorna o gate de
segurança). Dois modos de extração:
- **LLM real**: 1 chamada ao modelo pede um array JSON
  `[{"type": ..., "content": ...}, ...]`; parsing tolerante a fences
  Markdown/prosa ao redor. Um array válido é autoritativo: `[]` significa
  sucesso sem candidatos e nunca aciona fallback. Falha esperada do provedor,
  resposta não analisável ou root/schema inválido aciona a heurística local;
  erros de programação e invariantes não são silenciados. **Testado ao vivo com o backend Azure Gateway
  real** (não simulado) — um episódio de exemplo (bug de connection-pool
  em produção) extraiu corretamente 8 memórias atômicas (6 facts, 1
  preference, 1 procedural_anchor) em 4.6s; outro exemplo (bug de índice
  composto) extraiu 5 memórias em ~3s. Saída malformada degrada
  graciosamente para a heurística offline em vez de falhar.
- **Heurística offline** (sem callable ou como fallback diagnosticado): classificador
  determinístico por linha + palavras-chave (sem dependência de rede/API
  key, retry, modelo, embedding ou segundo provedor). CLI/MCP mantêm sua
  exigência atual de seleção de backend; uma falha depois da seleção usa essa
  mesma implementação canônica do Engine/Hook.

`mem_id_prefix` é obrigatoriamente prefixado por domínio (reforça o fix do
bug #0 acima) — cada memória extraída vira
`{mem_id_prefix}/{tipo}-{n}.md`, agrupando todas as memórias de um mesmo
episódio na mesma subpasta.

## 3. Query-Conditioned 3-Agent Retrieval Planning — **SIMPLIFICAÇÃO REAL (não implementado nesta rodada)**

**Paper**: o Retrieval-Planning Agent (`A_2`) produz um **plano
multi-query**: 𝒫_q = {(q̃_j, 𝒟_j)}, várias sub-queries reescritas, cada
uma mirando um subconjunto diferente de typed stores.

**Tessera hoje** (`orchestrator.py`):
- `plan_target_stores()` é uma heurística de keyword-matching simples
  (substrings tipo "fato"/"fact", "preferênc", "insight"/"procedural" na
  string da necessidade de informação).
- `plan_retrieval()` produz **uma única** query reescrita, não um plano de
  múltiplas sub-queries.

Isso é uma simplificação deliberada e razoável para o volume atual de uso
(a maioria das tarefas tem 1 necessidade de informação clara, não várias
facetas concorrentes) — mas é o ponto onde Tessera mais diverge do paper.

**Recomendação concreta**: se `query_memories_pipeline` (ex-`run_task_hook`)
começar a ser usado para tarefas mais compostas (ex: "preciso saber
preferências de estilo E decisões técnicas anteriores E aprendizados de
erro sobre X" — 3 facetas diferentes), vale estender `plan_retrieval()`
para retornar uma lista de `(sub_query, target_stores)` em vez de uma
tupla única, e `retrieve_context()` já suporta ser chamado múltiplas vezes
com merge de resultados no chamador. Não é urgente hoje.

## 4. Conflict Resolution — contenção segura, supersessão ainda pendente

**Paper**: cita abordagens tipo Zep (grafo de conhecimento temporal) como
related work para lidar com validade temporal de fatos.

**Tessera hoje**: o P0 de #16 contém o risco preservando todos os candidatos
na ordem ranqueada. O algoritmo anterior agrupava por
`entity[0] + first_tag` e mantinha apenas o registro mais recente. Essa chave
causava falso merge, dependia da ordem dos metadados e não provava que duas
memórias representavam o mesmo estado.

O método público e o parâmetro de compatibilidade continuam existindo, mas o
fluxo normal não apaga histórico. Isto não implementa `state_key`, validade
temporal, trajetória `Tq` nem supersessão: #15 e o slice posterior de #16
continuam donos dessas decisões.

## 5. Eficiência — não comparável diretamente

O paper otimiza para "3 chamadas de LLM por episódio + 1 classificador
local barato". Tessera, não fazendo decomposição automática nem detecção de
fronteira, não paga (nem ganha) esse custo — é uma filosofia de design
diferente (mais "escrita explícita e gated" do que "pipeline de extração
automática"), não uma ineficiência a ser corrigida.

## Resumo — priorização sugerida

| # | Gap | Severidade | Ação |
|---|---|---|---|
| 0 | `write_memory_note` sem `makedirs`, sem aviso de `mem_id` sem domínio | 🔴 Bug confirmado em produção | ✅ Corrigido (engine.py + mcp_server.py docstring) |
| 1 | Sem detecção dinâmica de fronteira de episódio | 🟡 Gap real vs. paper | ✅ Implementado (`episode_boundary.py`, heurística timeout+TF-IDF) |
| 2 | Decomposição típica é manual, não automática | 🟡 Divergência de design documentada | ✅ Implementado (`decomposer.py` + engine/hooks/CLI/MCP), testado com LLM real (Azure Gateway, ~3-5s, 5-8 memórias/episódio) |
| 3 | Retrieval planning é single-query, keyword-heurístico | 🟢 Simplificação aceitável no volume atual | Documentado, plano de extensão descrito - não implementado |
| 4 | Filtro destrutivo por `entity[0]+first_tag` | 🔴 Perda de evidência/trajetória | ✅ P0 contido: todos os candidatos preservados; supersessão completa continua pendente |

## Como usar as duas novas capacidades (paridade Engine/Hook/CLI/MCP)

| Capacidade | Engine (Python) | Hook (Python) | CLI | MCP tool |
|---|---|---|---|---|
| Decomposição automática | `TesseraEngine.decompose_and_write_episode(...)` | `TesseraTaskHook.on_task_end_auto(...)` | `tessera decompose <dir> --mem-id-prefix ... --beginning ... --middle ... --end ... --llm-backend <name>` | `decompose_episode(mem_id_prefix, beginning, middle, end, episode_id=None, tags=None)` |
| Fronteira de episódio | `from tessera.episode_boundary import EpisodeBoundaryTracker` | — (primitiva de biblioteca, sem wiring de hook ainda) | — (sem CLI dedicado; uso é programático) | — (sem MCP tool dedicado; uso é programático) |

Ver `Tessera/README.md`, seção "🧩 Decomposição automática de episódios" e "🕐 Detecção de fronteira de episódio", para exemplos de uso completos.
