# Tessera Cheatsheet — Todos os Comandos, Flags e Exemplos

> Referência rápida de todos os comandos do Tessera: CLI, MCP tools e API Python.
> Os exemplos usam o diretório genérico `./memories`. Pense nisso como o
> "keybinds cheatsheet" do Tessera — cole o
> comando, ajuste os argumentos, rode.

---

## Saída colorida (TUI) — `--plain`, cores automáticas

**(novo 2026-08-25)** Os comandos `list`, `query`, `start`, `init`, `write`,
`index` e `skills` agora renderizam com [Rich](https://github.com/Textualize/rich):
tabelas, painéis e cores por tipo de memória — `factual`=azul,
`preference`=magenta, `procedural_anchor`=verde, `tag`=cinza. O caminho do
arquivo aparece **sempre** numa linha própria, esmaecida/itálica e prefixada
com 📄 — nunca misturado com o conteúdo da nota, exatamente para você
conseguir distinguir "isso é onde está salvo" de "isso é o que está escrito".

- **Automático**: cor liga sozinha quando você está num terminal real (TTY)
  e desliga sozinha se a saída for redirecionada/pipeada (`tessera list > f.txt`,
  `tessera query ... | grep ...` continuam em texto puro, sem escapar códigos
  ANSI no arquivo).
- **Forçar texto puro**: passe `--plain` em qualquer um desses comandos, ou
  exporte `NO_COLOR=1` / `TESSERA_NO_COLOR=1` no ambiente.
- **Forçar cor mesmo com pipe** `(novo)`: exporte `FORCE_COLOR=1` ou
  `TESSERA_FORCE_COLOR=1` — útil se você quiser `tessera list --table | less -R`
  (o `-R` do `less` entende códigos ANSI) ou gravar a tela com `head`/`tail`
  no meio do pipe. **Sem isso, `tessera list --table | head -15` some com as
  cores** — não é bug, é o Rich detectando que a saída não é mais um
  terminal (o mesmo motivo por trás de nunca vazar ANSI num arquivo).
- **Ver o logo**: `tessera banner` (mesmo logo aparece automaticamente no topo
  de `tessera start` quando cor está ativa).

```bash
tessera query ./memories "decisão de arquitetura"      # painéis coloridos
tessera query ./memories "decisão de arquitetura" --plain  # texto puro
tessera list ./memories --table                              # tabela colorida
tessera list ./memories --table | less -R                     # colorida + paginada
FORCE_COLOR=1 tessera list ./memories --table | head -15       # colorida + head
tessera banner                                                    # só o logo
```

> ⚠️ **`tessera list` sem `--table` é formato cru** (`id<TAB>tipo<TAB>arquivo`,
> sem alinhamento nem cor) — de propósito, pra ser fácil de `grep`/`cut`/
> `awk`. Se você rodou só `tessera list` e achou "bagunçado", é esse o motivo:
> use `tessera list --table` para a versão organizada/colorida.

---

## Setup rápido

```bash
# ativa o venv que tem o `tessera` instalado (modo editável -e .)
source .venv-browser-agent/bin/activate

# opcional: escolha o storage canônico para os comandos sem caminho explícito
export TESSERA_STORAGE_DIR="$PWD/memories"
```

> Limite arquitetural: `query` é o caminho determinístico e não precisa de
> LLM. `start`, `decompose` e as tools MCP assistidas atuais exigem um backend
> real resolvível; não existe hoje flag `--use-llm` nem simulação offline nesses
> comandos. Consulte o contrato vinculante em
> [`ADR 0001`](adr/0001-core-vs-optional-llm-boundary.md).

> ⚠️ **Pegadinha comum**: `tessera list`/`tessera query` sem argumento de diretório
> sempre resolvem para `./memories` a menos que a env var `TESSERA_STORAGE_DIR`
> esteja exportada na sua sessão de shell (não basta estar no `.mcp.json` —
> isso só vale pro processo MCP). Fixe permanentemente com:
> ```bash
> echo 'export TESSERA_STORAGE_DIR="/caminho/absoluto/para/memories"' >> ~/.bashrc
> ```
> ou sempre passe o caminho explícito como primeiro argumento posicional.

---

## CLI — Referência completa

### `tessera init` — planejar e inicializar um projeto com segurança

```bash
# assistente interativo: descobre, seleciona, mostra o plano e confirma
tessera init

# automação/CI: todas as decisões materiais ficam explícitas
tessera init --project . --store memories \
  --sources recommended --non-interactive

# seleção customizada
tessera init --project . --store memories --sources custom \
  --source README.md --source docs --non-interactive

# somente as novas memórias geradas, sem fontes externas do projeto
tessera init --project . --store memories \
  --sources memory-only --non-interactive

# plano completo, sem criar config/store/index
tessera init --project . --store memories \
  --sources recommended --dry-run --json
```

Três locais diferentes são preservados: **memórias geradas** (`store.path`),
**fontes de conhecimento** (`sources.roots`) e **índice derivado**
(`index.path`). O modo interativo pede confirmação antes da primeira mutação.
`--dry-run` e cancelamento fazem zero mutações. Fontes `FORBIDDEN` nunca podem
ser selecionadas. Uma exclusão só é gravada em `.tessera-ignore` quando
`--persist-exclusion PATH` é passado explicitamente. Para mudar uma configuração
existente em modo não interativo, primeiro inspecione o dry-run e depois use
`--update-existing`.

O formato posicional antigo (`tessera init ./memories`) continua como alias de
compatibilidade, conservador e store-only. Para novos scripts, prefira as flags
explícitas acima.

---

### `tessera write <dir> [flags]` — gravar uma nova nota (write-gated)

| Flag | Obrigatória? | Descrição |
|---|---|---|
| `--id` | ✅ | ID/slug da nota. Use `"dominio/nome"` (ex: `"project/minha-nota"`) para gravar em subpasta. |
| `--type` | ✅ | `factual` \| `preference` \| `procedural_anchor` |
| `--episode` | ✅ | ID do episódio/sessão (use `"start"` se não tiver um real) |
| `--content` | ✅ | Corpo da nota (texto livre) |
| `--tags` | ❌ | Lista separada por vírgula: `"tag1,tag2,tag3"` |
| `--entity` | ❌ | Repetível. Formato `"Nome:descrição"` |
| `--related-to` | ❌ | **(novo 2026-08-25)** Repetível. Formato `"target_id:relation_type"` (relation_type default = `related_to`). Cria arestas explícitas (`active_connections`) no grafo. |

```bash
# exemplo simples
tessera write ./memories \
  --id "project/minha-nota" \
  --type factual \
  --episode start \
  --tags "exemplo,teste" \
  --content "Corpo da nota aqui."

# com entidades e múltiplas conexões explícitas
tessera write ./memories \
  --id "project/hipotese-classificacao" \
  --type factual \
  --episode start \
  --tags "governance,verification" \
  --entity "Strategist:agente que formula hipoteses" \
  --related-to "test-card-vs-product-hypothesis:supports" \
  --related-to "strategist-hypothesis-gate" \
  --content "O agente deve classificar hipóteses antes de executá-las."
```

Depois de escrever, **sempre reindexe** (a não ser que a próxima chamada já
rode `build_index()`, como `query`/`list` fazem automaticamente):
```bash
tessera index ./memories
```

---

### `tessera query <dir> "<pergunta>" [flags]` — busca semântica (DW-PR)

| Flag | Descrição |
|---|---|
| `--top-n N` | Quantos resultados retornar (default: 3) |
| `--no-resolve-conflicts` | Desliga a resolução temporal de conflitos entre notas |
| `--paths-only` | **(novo)** Só o caminho do arquivo de cada resultado, um por linha |
| `--show-related` | **(novo)** Mostra os ids de notas diretamente conectadas no grafo |
| `--no-body` | **(novo)** Omite o corpo da nota (mantém id/score/filename/related) |

```bash
# busca básica
tessera query ./memories "governanca de aprovacao de hipoteses" --top-n 5

# só os caminhos (bom pra pipe: cat, xargs, abrir no editor)
tessera query ./memories "decisão de arquitetura" --paths-only

# ver notas relacionadas sem carregar o corpo inteiro
tessera query ./memories "decisão de arquitetura" --show-related --no-body
```

**Não usa LLM.** É TF-IDF + cosine similarity + Personalized PageRank sobre
um subgrafo local — roda em ~1-2s, offline, sem custo de rede.

---

### `tessera list <dir> [flags]` — inventário (sem ranking)

| Flag | Descrição |
|---|---|
| `--type {factual,preference,procedural_anchor}` | Filtra por tipo |
| `--table` | **(novo)** Colunas alinhadas, legível no terminal |
| `--paths-only` | **(novo)** Só os caminhos de arquivo, um por linha |

```bash
tessera list ./memories --table | head -10
tessera list ./memories --type factual
tessera list ./memories --paths-only
tessera list ./memories | grep "notas indexadas"   # total rápido
```

> ℹ️ **Por que `tessera list` mostra 200 notas mas o índice tem 272 nós?**
> `tessera list` filtra intencionalmente para `node_type in {factual, preference,
> procedural_anchor}` — as notas reais em `.md`. O grafo completo
> (`.tessera_index/graph.json`) também guarda **72 nós `tag`** sintéticos (ex:
> `tag_scout`, `tag_planning`) usados internamente pelo DW-PR para conectar
> notas que compartilham uma tag. 200 notas + 72 tags = 272 nós — nada foi
> perdido, é só uma camada interna do índice que `list` não mostra por não
> ser uma "nota de memória" de verdade. Veja a distribuição completa com:
> ```bash
> tessera stats ./memories
> ```
> (novo comando, mostra a tabela colorida notas-reais vs. nós-internos —
> não precisa mais inspecionar `graph.json` na mão)

---

### `tessera index <dir>` — reconstruir o índice manualmente

```bash
tessera index ./memories
```
Roda um rebuild completo do grafo (parseia todos os `.md`, refaz TF-IDF,
persiste em `./memories/.tessera_index/graph.pkl` + `graph.json`).
`query`/`list`/`write` já chamam isso internamente (com cache por
fingerprint de arquivos), então normalmente você não precisa rodar manual —
só se quiser forçar um rebuild do zero.

---

### `tessera start <dir> "<tarefa>" [flags]` — pipeline assistido legado

O comando mais avançado: roda o orquestrador Need → Planner → Inference.

| Flag | Descrição |
|---|---|
| `--top-n N` | Quantas memórias brutas alimentar no pipeline (default: 3) |

```bash
# sem seleção explícita, nenhum backend opcional é ativado
tessera start ./memories "Resuma as decisões do projeto"
```
⚠️ `task` é **posicional**, não tem flag — sempre vem depois do `storage_dir`.
O comando faz três chamadas reais (Need → Planner → Inference) e falha se
nenhum backend puder ser resolvido. A busca interna continua sendo o retrieval
determinístico do Engine; o contexto consolidado é texto derivado e
`raw_memories` preserva os resultados de retrieval.

---

### `tessera decompose <dir> [flags]` — **(novo 2026-08-26)** decomposição automática de episódio

Equivalente ao `g_φ` do paper QUMem: em vez de gravar memórias uma a uma na
mão, você passa um episódio bruto (`beginning`/`middle`/`end`) e o Tessera
extrai **N memórias atômicas já tipadas** (factual/preference/
procedural_anchor) e grava todas de uma vez em `{prefix}/{tipo}-{n}.md`.

| Flag | Obrigatória? | Descrição |
|---|---|---|
| `--mem-id-prefix` | ✅ | Subpasta onde as memórias extraídas serão gravadas (ex: `"research/meu-topico"`) |
| `--episode-id` | ❌ | ID do episódio gravado em cada nota extraída (default: mesmo valor de `--mem-id-prefix`) |
| `--beginning` | ✅ | Texto do início do episódio |
| `--middle` | ✅ | Texto do meio do episódio (o grosso do conteúdo) |
| `--end` | ✅ | Texto do fim/resultado do episódio |
| `--tags` | ❌ | Lista separada por vírgula aplicada a todas as memórias extraídas |

```bash
# requer backend LLM real configurado
set -a && source .env && set +a
tessera decompose ./memories \
  --mem-id-prefix "research/meu-topico" \
  --beginning "Investigando timeout intermitente no serviço de pagamentos." \
  --middle "Encontramos que o pool de conexões do Postgres esgota sob carga; prefiro usar pgbouncer a aumentar o pool bruto." \
  --end "Corrigido configurando pgbouncer com pool_mode=transaction; taxa de erro caiu a zero." \
  --tags "postgres,performance"
```

Não há hoje fallback heurístico alcançável nesse comando. Falha de chamada ou
de parsing produz uma lista vazia. Cada memória extraída passa pelo
`WriteGatingEngine`; decomposição não contorna a auditoria/sanitização de
escrita.
Após rodar, **reindexe** (`tessera index <dir>`) para as novas notas entrarem
na busca — a não ser que a próxima chamada de `query`/`list` já dispare
isso sozinha via fingerprint cache.

Ver `Tessera/docs/QUMEM-GAP-ANALYSIS.md` (gap #2) para o racional completo e
a tabela de paridade Engine/Hook/CLI/MCP.

---

### `tessera skills` — gerenciar skills padrão (procedural anchors)

```bash
tessera skills list                          # lista as 5 skills embutidas
# sk_docker_environment, sk_runtime_verification, sk_schema_compliance,
# sk_service_lifecycle, sk_shell_execution
tessera skills install ./memories        # instala as 5 no storage_dir
```

---

### `tessera stats <dir>` — **(novo 2026-08-25)** composição do índice

```bash
tessera stats ./memories
```
Tabela colorida mostrando quantos nós de cada tipo existem no grafo —
`factual`/`preference`/`procedural_anchor` (notas reais em `.md`) vs.
`tag`/`entity` (nós sintéticos internos usados pelo DW-PR, não são
arquivos). É a resposta direta pra "por que `list` mostra 200 mas o índice
tem 272 nós" sem precisar abrir `graph.json` na mão.

---

### `tessera doctor <dir>` — **(novo 2026-08-25)** smoke test pós-instalação

```bash
tessera doctor ./memories
```
Roda uma bateria de checagens independentes (uma falha não esconde as
outras): `storage_dir` existe e é gravável, o índice constrói sem erro,
um round-trip de escrita+leitura funciona de fato (grava uma nota num
diretório temporário, reconstrói o índice, confirma que a busca acha a
nota de volta), `rich` está instalado e o extra `mcp` está instalado. O
doctor não inspeciona credenciais ou arquivos de provedores. As dependências
opcionais não fazem o comando falhar — o
resto é obrigatório. Exit code `0` = tudo OK, `1` = alguma checagem
obrigatória falhou (útil em CI/script).

---

### `tessera quickstart [flags]` — **(novo 2026-08-25)** onboarding num projeto novo

| Flag | Descrição |
|---|---|
| `--project-root <path>` | Projeto a detectar (default: diretório atual) |
| `--storage-dir <path>` | Força um `storage_dir` específico em vez de auto-detectar |
| `--apply` | Executa de verdade (cria `storage_dir`, roda o primeiro `index`). Sem essa flag é **dry-run** — só mostra o plano, não toca no disco. |

```bash
# dry-run: só mostra o que seria feito + o bloco de config MCP pronto pra colar
tessera quickstart

# aplica de verdade num projeto novo
tessera quickstart --project-root ~/meu-outro-projeto --apply
```
Detecta o tipo de projeto (`package.json`→node, `pyproject.toml`→python,
`Cargo.toml`→rust, `go.mod`→go, `.git`→genérico), propõe `./memories` na
raiz do projeto e imprime o bloco JSON com `TESSERA_STORAGE_DIR` pronto para `.mcp.json`/
`.gemini/settings.json`/config do Claude Desktop. Implementa os itens 2 e
3 do roadmap plug-and-play.

---

## MCP — Tools disponíveis (servidor `tessera`)

Registrado em `.mcp.json` (Claude Code/Copilot CLI) e `.gemini/settings.json`
(Gemini CLI). Nenhum comando de shell — são tool calls que qualquer agente
já consegue invocar diretamente.

### `query_memories(query, top_n=3, resolve_conflicts=True)`
Mesma busca do `tessera query`. Cada resultado já inclui `filepath` e
`related_ids` (equivalente a `--paths-only`/`--show-related`, sem precisar
de flag — sempre vem preenchido).

### `query_store(query, store, top_n=3, resolve_conflicts=True)`
Igual, mas filtra por typed store: `store="factual"` \| `"preference"` \|
`"procedural_anchor"`.

### `write_memory(mem_id, mem_type, episode_id, content, tags=None, entity_names=None, connect_to=None, relation_type="related_to", persist_format="md")`
Equivalente ao `tessera write`. `connect_to` aceita uma **lista** de ids
(múltiplas conexões explícitas em uma única chamada, igual ao `--related-to`
repetível da CLI). `persist_format` aceita somente `"md"`: Markdown é o formato
canônico gravável e indexável. Outros valores falham antes da gravação e do
rebuild; ingestão arbitrária de JSON não é suportada.

O retorno inclui o contrato canônico `threat_detected`, `content_changed`,
`admission`, `reasons`, `original_hash`, `persisted_hash`, `persisted` e o alias
compatível `is_sanitized`. IDs usam segmentos com `/`, sem caminhos absolutos,
`..`, barras invertidas ou escape por symlink. `reject` e `review` não gravam
nem reindexam; instruções hostis diretas conhecidas são rejeitadas.

### `get_memory(memory_id)`
Devolve o corpo bruto de uma nota específica pelo id.

### `get_index_stats()`
Contagem de nós/arestas do índice atual.

### `rebuild_index()`
Reconstrói o grafo em memória do processo MCP (não recarrega o código
Python — ver nota de troubleshooting abaixo).

### `query_memories_pipeline(task_instruction, top_n=7)` — pipeline assistido legado
Pipeline completo Need→Planner→Retrieval→Inference via MCP (equivalente ao
`tessera start`, sem sair do agente/CLI hospedeiro).

Nenhum backend é resolvido automaticamente. A assinatura MCP atual não aceita
seleção de adapter; a ampliação desse envelope pertence à issue #120:

```jsonc
{ "task_instruction": "...", "top_n": 7 }
```

- Sem um adapter configurado pela aplicação, a tool falha antes de executar.
- Falhas de compatibilidade são tipadas e nunca degradam para eco do prompt.

### `decompose_episode(mem_id_prefix, beginning, middle, end, episode_id="start", tags=None)`
Equivalente MCP de `tessera decompose`: extrai N memórias tipadas de um
episódio bruto e grava todas em `{mem_id_prefix}/{tipo}-{n}.md`, sem sair
do agente hospedeiro. Exige um backend LLM real resolvível e não aceita flags
de seleção ou simulação na assinatura atual.

```jsonc
{ "mem_id_prefix": "research/meu-topico", "beginning": "...", "middle": "...", "end": "..." }
```

### `get_index_composition()` — **(novo 2026-08-25)**
Equivalente MCP de `tessera stats`: quebra o total de nós do grafo em notas
reais (`factual`/`preference`/`procedural_anchor`) vs. nós internos
(`tag`/`entity`) — a mesma explicação do "200 notas vs. 272 nós",
disponível pro agente sem precisar rodar CLI.

### `run_doctor(storage_dir=None)` — **(novo 2026-08-25)**
Equivalente MCP de `tessera doctor`: roda as mesmas checagens (storage_dir
gravável, índice constrói, round-trip escrita+leitura, `rich`/`mcp`
instalados e fronteira opcional não sondada) e retorna um relatório estruturado
(`all_ok`, lista de checks com `ok`/`required`/`detail`). Se
`storage_dir` for omitido, usa o mesmo dir com que o servidor MCP foi
inicializado (`TESSERA_STORAGE_DIR`).

### `run_quickstart(project_root=None, storage_dir=None, apply=False)` — **(novo 2026-08-25)**
Equivalente MCP de `tessera quickstart`: detecta o tipo de projeto,
sugere/confirma um `storage_dir`, devolve o bloco de config MCP pronto
pra colar. Com `apply=False` (default) é só um plano — nada é gravado no
disco. Com `apply=True` cria o diretório e roda o primeiro `tessera index`
de verdade, igual ao `--apply` da CLI.

**Exemplo real testado** (Copilot CLI e Gemini CLi chamando o mesmo MCP):
```bash
copilot -p "Use query_memories do servidor tessera para buscar 'backend de llm mais rapido' e resuma o top resultado." --allow-all

gemini -p "Use query_memories do servidor tessera para buscar 'backend de llm mais rapido' e resuma o top resultado." --yolo
```

> ⚠️ **Troubleshooting**: o processo MCP é long-running — ele carrega o
> código Python **uma vez**, na inicialização. Se você editar
> `Tessera/tessera/*.py` enquanto o processo MCP já está rodando, `rebuild_index()`
> atualiza só o **grafo em memória**, não o código. Reinicie a conexão MCP
> (reconectar o servidor pelo host, ou matar o processo `tessera-mcp` e deixar
> reconectar) para pegar mudanças de código.

---

## API Python (uso direto, sem CLI/MCP)

```python
import sys
sys.path.insert(0, "Tessera")
from tessera.engine import TesseraEngine
from tessera.models import Entity, Connection

engine = TesseraEngine(storage_dir="./memories")
engine.build_index()

# busca
results = engine.retrieve_context("governanca de aprovacao", top_n=5)
for r in results:
    print(r["id"], r["score"], r.get("related_ids"))

# escrita com conexões explícitas
result = engine.write_memory_note_result(
    mem_id="project/exemplo",
    mem_type="factual",
    episode_id="start",
    content="Corpo da nota.",
    tags=["exemplo"],
    entities=[Entity("Strategist", "agente de hipoteses")],
    active_connections=[Connection(target_memory_id="project/charter", relation_type="supports")],
)
print(result.to_dict())
engine.build_index()  # reindexar após escrever
```

`write_memory_note(..., persist_format="md")` é o único formato público de
persistência. O default já é `"md"`; qualquer outro valor é rejeitado antes de
efeitos colaterais, e ingestão arbitrária de JSON não é suportada.
`write_memory_note_result()` expõe a decisão completa. O método legado
`write_memory_note()` continua retornando filepath para escritas aceitas e
lança `WriteGatingViolationError` em `reject`/`review`.

Na CLI, `tessera write ... --json` imprime exatamente o mesmo contrato do
Engine/MCP. Texto seguro permanece igual e nunca é marcado sanitizado; exemplos
hostis claramente citados/documentais vão para revisão sem persistência, e
instruções hostis diretas conhecidas são rejeitadas. `accept_sanitized` fica no
schema, mas o avaliador atual não o emite sem uma transformação integral e
versionada.

### Decomposição automática de episódio (`decompose_and_write_episode`)

```python
# A aplicação fornece seu próprio callable; TESSERA não escolhe provedor.
llm_fn = application_llm_fn

paths = engine.decompose_and_write_episode(
    mem_id_prefix="research/meu-topico",
    beginning="Investigando timeout intermitente...",
    middle="Encontramos que o pool esgota sob carga...",
    end="Corrigido com pgbouncer...",
    episode_id="start",
    tags=["postgres", "performance"],
    llm_fn=llm_fn,
)
engine.build_index()  # reindexar após escrever
print(paths)  # lista de caminhos gravados: research/meu-topico/factual-1.md, ...
```

Também acessível como função pura (sem precisar de um `TesseraEngine`), útil
para inspecionar as memórias extraídas antes de decidir gravar:

```python
from tessera.decomposer import decompose_episode
from tessera.models import Episode

memories = decompose_episode(
    Episode(beginning="...", middle="...", end="..."),
    llm_fn=llm_fn,
)
for m in memories:
    print(m.mem_type, m.content[:80])
```

### Detecção automática de fronteira de episódio (`EpisodeBoundaryTracker`)

```python
from tessera.episode_boundary import EpisodeBoundaryTracker

tracker = EpisodeBoundaryTracker()  # timeout=30min, threshold de deriva TF-IDF=0.03

# a cada novo turno da conversa/tarefa:
closed_episode = tracker.add_turn("texto do turno mais recente")
if closed_episode is not None:
    # episódio fechado automaticamente (timeout ou deriva de tópico) —
    # closed_episode já é um objeto Episode(beginning, middle, end) pronto
    # para passar a decompose_episode()/decompose_and_write_episode()
    paths = engine.decompose_and_write_episode(
        mem_id_prefix="research/topico-detectado",
        beginning=closed_episode.beginning,
        middle=closed_episode.middle,
        end=closed_episode.end,
        llm_fn=llm_fn,
    )
```
⚠️ É uma primitiva de **biblioteca apenas** — sem CLI/MCP dedicado ainda
(deliberado: fechamento de episódio turno-a-turno é um padrão de uso
programático contínuo, não uma chamada avulsa). A deriva por TF-IDF é
fraca para turnos curtos/lexicalmente disjuntos (similaridade de cosseno
zero mesmo quando semanticamente relacionados) — o timeout continua sendo
o sinal mais confiável na prática; ver `Tessera/docs/QUMEM-GAP-ANALYSIS.md`
gap #1 para o racional completo.

---

## Como funcionam as relações entre memórias (related_to)

Duas formas, ambas persistidas na mesma nota:

1. **Implícita (automática, sempre acontece)**: toda tag e toda entidade
   viram nós compartilhados no grafo (`tag_x`, `ent_y`). Duas notas que
   compartilham uma tag/entidade já ficam conectadas — é isso que alimenta o
   ranking DW-PR, sem nenhuma configuração.

2. **Explícita** (`active_connections`, campo `related_to` no frontmatter
   compatível): uma aresta direta nota→nota, com um `relation_type`. Grave
   via `--related-to` (CLI), `connect_to=[...]` (MCP), ou escrevendo
   `metadata.related_to: [id1, id2]` no frontmatter à mão — as três formas
   viram arestas reais no grafo.

```yaml
---
name: minha-nota
description: Descricao curta e clara (melhora a busca semantica)
metadata:
  type: governance
  category: exemplo
  date: 2026-08-25
  related_to:
    - outra-nota-1
    - outra-nota-2
---
```

---

## Referência rápida (tabela única)

| Quero... | Comando |
|---|---|
| Buscar por conceito/intenção | `tessera query <dir> "<pergunta>"` |
| Buscar e só ver os arquivos | `tessera query <dir> "<pergunta>" --paths-only` |
| Ver notas relacionadas de um resultado | `tessera query <dir> "<pergunta>" --show-related --no-body` |
| Listar tudo (inventário) | `tessera list <dir> --table` |
| Contar quantas notas existem | `tessera list <dir> \| grep "notas indexadas"` |
| Gravar uma nota simples | `tessera write <dir> --id ... --type ... --episode start --content ...` |
| Gravar com conexões explícitas | `tessera write <dir> ... --related-to "id1" --related-to "id2:relation"` |
| Rodar retrieval determinístico/offline | `tessera query <dir> "<pergunta>"` |
| Rodar pipeline assistido legado | `tessera start <dir> "<tarefa>"` (requer backend real) |
| Forçar reconstrução do índice | `tessera index <dir>` |
| Instalar skills padrão num novo repo | `tessera skills install <dir>` |
| Ver composição do índice (notas vs. nós internos) | `tessera stats <dir>` |
| Extrair N memórias tipadas de um episódio bruto de uma vez | `tessera decompose <dir> --mem-id-prefix ... --beginning ... --middle ... --end ...` |
| Decompor com backend real configurado | `tessera decompose <dir> ...` |
| Fechar episódios automaticamente por timeout/deriva de tópico (só biblioteca) | `EpisodeBoundaryTracker` (`tessera.episode_boundary`), sem CLI/MCP |
| Fazer um agente (Copilot/Gemini/Claude) usar isso sem shell | Tool calls MCP: `query_memories`, `write_memory`, `query_memories_pipeline` |

---

## Ver também

- `README.md` — visão geral e instalação
- `docs/adr/0001-core-vs-optional-llm-boundary.md` — limite entre core determinístico, adapters opcionais e agente consumidor
- `Tessera/docs/COMO-FUNCIONA-E-PROXIMOS-PASSOS.md` — arquitetura completa (3 pilares, grafo DW-PR, roadmap plug-and-play)
- `Tessera/docs/ROTEIRO-DEMO-VIDEO.md` — roteiro de gravação testado ao vivo
- `docs/adr/0001-core-vs-optional-llm-boundary.md` — contrato de core e adapters opcionais
