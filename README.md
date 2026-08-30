# Tessera — Temporal Evolving State Synthesis with Explicit Relations and Atomic Memories

**Tessera** é o mecanismo de persistência e recuperação de memória de longo
prazo projetado para agentes autônomos — criado para o **LAO** (Lab
Autonomous Officer), mas utilizável por qualquer agente/aplicação Python.

Diferente de arquiteturas tradicionais de memória (RAG plano com busca
vetorial sobre blocos de texto isolados), o Tessera armazena memórias físicas
em arquivos **Markdown legíveis por humanos** e usa um **grafo de
conhecimento heterogêneo** em memória, com recuperação via **Dynamic
Weighted PageRank (DW-PR)**, para trazer contexto relevante sem saturar a
janela do modelo, sem desalinhamento temporal e sem propagação de ruído.

> 📖 Quer entender a fundo o *porquê* e o *como* funciona? Veja
> [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) (racional científico +
> diagrama de fluxo) e [`docs/CODE_EXPLANATION.md`](docs/CODE_EXPLANATION.md)
> (explicação classe a classe).
>
> ⚡ Quer só o comando pra colar? Veja
> [`docs/CHEATSHEET.md`](docs/CHEATSHEET.md) — referência rápida com todos
> os comandos CLI/MCP/API e exemplos testados ao vivo.

---

## ✨ O que o Tessera resolve

| Problema comum em agentes de longa duração | Como o Tessera resolve |
|---|---|
| Contexto satura com histórico bruto de diálogo | Memórias tipadas (`factual`, `preference`, `procedural_anchor`) em cartões atômicos |
| Preferências antigas competem com as atuais | `ConflictResolver` mantém só a nota cronologicamente mais recente por assunto |
| RAG plano traz ruído semanticamente próximo mas irrelevante | Busca por subgrafo (seed nodes → expansão 1-hop → PageRank ponderado) |
| Agentes falham em tarefas de setup/infra repetidas vezes | "Âncoras procedimentais" (skills destiladas de execuções passadas) |
| Injeção de instruções hostis contamina a memória futura | `WriteGatingEngine` audita e sanitiza **antes** de gravar em disco |

## 🚀 Instalação

Requer Python ≥ 3.9.

### Opção 1 — script de um comando só (`install.sh`, recomendado)

```bash
cd tessera
./install.sh                  # instala core + [mcp] + [llm] no ambiente Python atual
./install.sh --venv           # idem, mas cria/reaproveita um .venv isolado antes
./install.sh --venv --dev     # inclui extras[dev] (pytest) também
./install.sh --minimal        # só o core, sem [mcp]/[llm]
./install.sh --quickstart     # ao final, já roda `tessera quickstart` (dry-run)
./install.sh --help           # lista todas as flags
```

O script detecta `uv` automaticamente (usa se disponível, senão cai para
`pip`), instala em modo **editável** (`-e .`), confirma que os comandos
`tessera`/`tessera-mcp` ficaram no `PATH`, e roda `tessera doctor` no final para
validar a instalação de ponta a ponta. Se seu ambiente tiver um mirror
PyPI corporativo inacessível (ex: proxy interno bloqueado), o script
detecta a falha e tenta de novo com `--index-url https://pypi.org/simple`
explícito, automaticamente — sem exigir configuração manual. É idempotente
(seguro rodar de novo a qualquer momento; nunca apaga dados de nenhum
`storage_dir` de memórias já existente).

### Opção 2 — manual

```bash
cd tessera

# Com uv (recomendado — gerenciador de pacotes Python ultrarrápido)
uv pip install -e .

# Ou com pip tradicional
pip install -e .
```

Isso instala o pacote `tessera` (importável) e os comandos `tessera` e `tessera-mcp`
no seu `PATH`. O nome de distribuição no PyPI é `tessera`.

Dependências: `networkx`, `numpy`, `PyYAML`, `scikit-learn` (instaladas
automaticamente).

Para rodar os testes:

```bash
pip install -e ".[dev]"
pytest tests/
```

Para o servidor MCP (opcional):

```bash
pip install -e ".[mcp]"
```

## ⚡ Quickstart (como biblioteca)

```python
from tessera import TesseraEngine, Entity, Connection

engine = TesseraEngine(storage_dir="./memories")

# 1. Grava uma memória factual
engine.write_memory_note(
    mem_id="mem_fact_001",
    mem_type="factual",
    episode_id="ep_001",
    content="Maria configurou a replicação de leitura do PostgreSQL.",
    tags=["postgresql", "infraestrutura"],
    entities=[Entity("Maria", "Engenheira de dados.")],
)

# 2. Grava uma âncora procedimental (skill) conectada ao fato acima
engine.write_memory_note(
    mem_id="sk_deploy_db",
    mem_type="procedural_anchor",
    episode_id="ep_002",
    content="1. Validar porta 5432 livre.\n2. Iniciar serviço.\n3. Rodar pg_dump.",
    tags=["postgresql", "devops"],
    entities=[Entity("PostgreSQL", "Banco de dados relacional.")],
    active_connections=[Connection(target_memory_id="mem_fact_001", relation_type="stabilizes_service")],
)

# 3. (Re)constrói o índice do grafo a partir do disco
engine.build_index()

# 4. Recupera contexto relevante para uma tarefa/pergunta
resultados = engine.retrieve_context(
    query_text="Como faço deploy seguro do banco configurado pela Maria?",
    top_n=3,
    resolve_conflicts=True,
)
for r in resultados:
    print(r["id"], r["type"], r["score"])
    print(r["body"])
```

Exemplo completo e executável em [`examples/quickstart.py`](examples/quickstart.py).

## 🖥️ Quickstart (via CLI)

Todo subcomando aceita `storage_dir` como argumento **opcional**. Se você
omitir, ele resolve nesta ordem: `--dir` (quando existir) → variável de
ambiente `LAO_MEM_DIR` → `./memories` no diretório atual. Isso é o que
estava faltando antes: rodar `tessera list` sem nenhum argumento não é um erro
de uso — ele simplesmente usa `./memories` (ou `$LAO_MEM_DIR` se exportado)
e, se não encontrar nada, agora imprime uma mensagem clara em vez de uma
lista vazia silenciosa.

```bash
# Inicializa o diretório de memórias
tessera init ./memories

# Grava uma nota
tessera write ./memories --id mem_fact_001 --type factual \
  --episode ep_001 \
  --content "Maria configurou a replicação de leitura do PostgreSQL." \
  --tags postgresql,infraestrutura \
  --entity "Maria:Engenheira de dados."

# Reconstrói o índice do grafo
tessera index ./memories

# Lista as memórias indexadas
tessera list ./memories

# Faz uma pergunta e recupera memórias relevantes
tessera query ./memories "Como faço deploy do banco configurado pela Maria?"

# Instala as 5 âncoras procedimentais (skills) padrão do Tessera
tessera skills install ./memories
tessera skills list

# Roda o pipeline completo Need -> Planner -> Retrieval -> Inference
tessera start ./memories "Como faço deploy seguro de um container docker?"
```

### Rodando contra a memória real do LAO (`.claude/memory/`)

A pasta `.claude/memory/` do LAO usa um schema de frontmatter diferente do
nativo do Tessera (`name`/`description`/`metadata.type` em vez de
`id`/`node_type`/`tags`) — o engine detecta e normaliza esse formato
automaticamente (ver `TesseraEngine._normalize_frontmatter`), então funciona
sem nenhuma conversão manual:

```bash
# Exporte uma vez por sessão de terminal — todos os comandos tessera passam a
# usar essa pasta por padrão, sem precisar repetir o caminho:
export LAO_MEM_DIR="$(pwd)/.claude/memory"   # rodando a partir da raiz do repo

tessera list                 # lista as ~250 notas já indexadas (recursivo, inclui subpastas)
tessera query "self improvement e correcao de mecanismo do LAO" --top-n 3
tessera start "quais gaps de arquitetura o LAO ja identificou sobre orquestracao multiagente"
```

> **⚠️ Pegadinha comum**: `export` só vale para a sessão de terminal atual.
> Se você abrir um terminal novo e rodar `tessera list` sem argumento, ele volta
> a usar `./memories` (o default embutido) e diz "nenhuma nota encontrada" —
> **isso não é um bug**, é o CLI genuinamente não sabendo qual pasta você
> quer, exatamente como projetado para funcionar em qualquer repo. Para
> tornar `.claude/memory/` o padrão permanentemente neste projeto, adicione
> ao seu `~/.bashrc`/`~/.zshrc`:
> ```bash
> export LAO_MEM_DIR="/caminho/absoluto/para/lab-autonomous-officer/.claude/memory"
> ```
> Ou sempre passe o caminho explicitamente: `tessera list .claude/memory`.
> O MCP server (`tessera` em `.mcp.json`) já resolve isso automaticamente
> via `env.LAO_MEM_DIR` — só o CLI standalone no seu terminal pessoal
> precisa dessa variável exportada à parte.

O que acontece "por baixo do capô" quando você roda isso:
1. `build_index()` varre `.claude/memory/` **recursivamente** (inclui
   `research/<topico>/`, `learnings/pipeline/`, etc.) — antes só lia o
   nível raiz.
2. Cada `.md` é normalizado: `name` → `id`, `metadata.type` (`learning`,
   `project`, `reference`, `user`, `feedback`, ...) → `node_type` (`factual`
   / `preference` / `procedural_anchor`), `description` + campos de
   `metadata` viram tags pesquisáveis.
3. Um pequeno reparo automático de YAML corrige o caso comum de dois pontos
   sem aspas dentro de uma `description` de uma linha só (ex.:
   `description: "Voice by Blip" (Thesis 2B, ...)`), sem descartar a nota.
4. Todo o resto do pipeline (TF-IDF → subgrafo → DW-PR → resolução de
   conflitos) roda exatamente igual, sem saber que o frontmatter era
   "estrangeiro".
5. O grafo resultante é **persistido em disco** dentro de
   `.claude/memory/.tessera_index/` (ver seção "Onde o grafo fica salvo"
   abaixo) — chamadas seguintes reaproveitam esse cache em vez de
   reprocessar os 200+ arquivos do zero.

Nenhuma nota `.md` original é modificada — a normalização acontece só em
memória, durante `build_index()`. O único artefato novo em disco é a pasta
`.tessera_index/` (índice derivado, git-ignorada).

### Onde o grafo fica salvo (`.tessera_index/`)

Toda vez que `build_index()` roda (via `tessera index`, `tessera list`,
`tessera query`, `tessera start`, ou o servidor MCP), o engine grava o resultado
dentro do próprio `storage_dir`, em uma subpasta dedicada:

```
<storage_dir>/.tessera_index/
├── graph.pkl    # snapshot binário completo (grafo + matriz TF-IDF + vetorizador)
│                # — usado para recarregar instantaneamente, sem reprocessar os .md
└── graph.json   # resumo legível: nós, arestas, tipo e filepath de cada nota
                 # — abra esse arquivo para inspecionar o que foi indexado
```

- **Cache automático**: em chamadas seguintes, `build_index()` primeiro
  calcula uma "fingerprint" barata do corpus (quantidade de arquivos +
  mtime mais recente). Se bater com o que está salvo em `graph.pkl`, o
  índice é recarregado do cache em vez de reparsear tudo — só quando você
  edita/adiciona/remove um `.md` é que ele reconstrói de fato.
- **`tessera index` sempre força reconstrução** (ignora o cache) — é o
  comando certo para usar depois de editar notas em massa e querer garantir
  que o índice reflita o estado atual.
- **Nunca é versionado**: `.tessera_index/` já está no `.gitignore` do
  repositório — é um artefato derivado (reconstruível a qualquer momento a
  partir dos `.md`), não uma fonte de verdade.
- **Para inspecionar manualmente** o que o Tessera indexou da sua pasta:
  ```bash
  cat "$LAO_MEM_DIR/.tessera_index/graph.json" | python3 -m json.tool | less
  ```



## 🧩 Skills iniciais (âncoras procedimentais padrão)

O Tessera vem com **5 âncoras procedimentais prontas** (`tessera/skills_library/`),
desenhadas para mitigar as classes de falha operacional onde skills mais
ajudam agentes autônomos (categoria SC2 — falhas de execução/validação):

| Skill | Mitiga |
|---|---|
| `sk_service_lifecycle` | `background_service_lifecycle_failure` — subir serviços sem checar porta/PID |
| `sk_docker_environment` | `environment_infrastructure_failure` — setup quebrado de Docker/volumes |
| `sk_runtime_verification` | `static_verification_without_runtime` — assumir sucesso sem testar de fato |
| `sk_schema_compliance` | `output_format_schema_mismatch` — JSON/YAML quebrado |
| `sk_shell_execution` | `shell_code_corruption` — pipes/redirecionamentos malformados |

Instale-as em qualquer diretório de memórias com `tessera skills install <dir>`
ou programaticamente com `tessera.install_default_skills(engine)`.

## 🏛️ Arquitetura de memória em 3 pilares

O Tessera organiza tudo o que é aprendido em torno de 3 pilares que trabalham
juntos:

### 1. Episódios (início, meio e fim — não blocos soltos)

Memórias de execução de tarefa não são um bloco único de texto: são
quebradas em **início** (contexto/gatilho), **meio** (o que aconteceu) e
**fim** (resultado/aprendizado), via `tessera.models.Episode`:

```python
from tessera import TesseraEngine, Episode, STORE_INSIGHTS

engine = TesseraEngine(storage_dir="./memories")

episodio = Episode(
    beginning="Tarefa: subir o serviço de banco de dados em background.",
    middle="Tentamos iniciar sem checar a porta 5432, que já estava ocupada.",
    end="Sempre checar a porta com lsof/netstat antes de subir o serviço.",
)
engine.write_episode(
    mem_id="insight_service_lifecycle",
    store=STORE_INSIGHTS,
    episode_id="ep_001",
    episode=episodio,
    tags=["devops", "database"],
)
```

Isso importa porque a parte transferível de um aprendizado costuma ser o
**fim** (o que resolveu/o que se aprendeu), não o "meio" passo-a-passo — e
separar as seções deixa isso explícito tanto para quem lê a nota quanto
para a consolidação feita pelo Agente de Inferência de Estado (pilar 3).

### 2. Gavetas tipadas (Typed Stores): fatos, preferências, insights

Tudo o que é aprendido é arquivado em exatamente **3 gavetas**, cada uma com
sua própria semântica de "o que fica obsoleto" e "o que gera boost de
recuperação":

| Gaveta | O que guarda | `node_type` interno | Exemplo |
|---|---|---|---|
| `facts` (fatos) | Informação concreta e imutável | `factual` | "O Postgres roda na porta 5432." |
| `preferences` (preferências) | Comportamento, gostos, feedback | `preference` | "Alex prefere relatórios em PDF." |
| `insights` (insights transferíveis) | Aprendizados de execução aplicáveis a situações futuras | `procedural_anchor` | "Checar a porta antes de subir o serviço evita falha silenciosa." |

```python
from tessera import TesseraEngine, STORE_FACTS, STORE_PREFERENCES, STORE_INSIGHTS

engine = TesseraEngine(storage_dir="./memories")

engine.write_fact(mem_id="fact_pg_port", episode_id="ep1",
                   content="O Postgres roda na porta 5432.", tags=["postgres"])
engine.write_preference(mem_id="pref_pdf", episode_id="ep2",
                         content="Alex prefere relatórios em PDF.", tags=["relatorio"])
engine.write_insight(mem_id="insight_lsof", episode_id="ep3",
                      content="Checar a porta com lsof antes de subir o serviço.", tags=["devops"])
engine.build_index()

# Busca escopada a uma única gaveta, em vez de vasculhar tudo:
resultados = engine.retrieve_from_store("porta do banco", STORE_FACTS, top_n=3)
```

Fatos e preferências passam pelo `ConflictResolver` (a versão mais recente
substitui a antiga sobre o mesmo assunto); insights (`procedural_anchor`)
não sofrem obsolescência temporal do mesmo jeito e recebem o boost de
recuperação — eles existem justamente para estabilizar ação *futura*.

### 3. O hook + trio de agentes detetives (interceptação automática de tarefa)

Em vez de o agente principal (LAO) precisar lembrar de consultar a memória
manualmente antes de agir, `tessera.hooks.TesseraTaskHook` **intercepta a tarefa**
e dispara automaticamente um pipeline de inferência com 3 agentes
especializados — o mesmo `TesseraOrchestrator` descrito abaixo, mas encapsulado
como um hook plugável no ciclo de vida da tarefa:

```
[ INPUT: Pergunta/Tarefa do agente principal ]
                   │
                   ▼
1. Agente de Identificação de Necessidade (Information-Need Agent)
   → raciocina: "o que preciso descobrir no histórico pra responder isso?"
                   │
                   ▼
2. Agente de Planejamento de Busca (Retrieval Planner Agent)
   → decide quais gavetas abrir (facts/preferences/insights) e reescreve
     a consulta de busca, acionando `retrieve_from_store` em cada uma
                   │
                   ▼
        [ Execução do motor Tessera: grafo, DW-PR, ConflictResolver ]
                   │
                   ▼
3. Agente de Inferência de Estado (User-State Inference Agent)
   → junta as pistas encontradas nas gavetas, descarta o que ficou
     obsoleto (já feito pelo ConflictResolver) e monta um resumo validado
                   │
                   ▼
       [ OUTPUT: contexto consolidado, pronto pra injetar no prompt ]
```

```python
from tessera import TesseraEngine
from tessera.hooks import TesseraTaskHook

engine = TesseraEngine(storage_dir="./memories")
hook = TesseraTaskHook(engine)

# Chame isso no exato momento em que uma tarefa vai começar — é o hook em si.
contexto = hook.on_task_start("Como faço deploy seguro de um banco em background?")
print(contexto.stores_queried)        # ex.: ['insights'] — o planner decidiu que só precisa de insights
print(contexto.consolidated_context)  # injete isso no prompt do agente principal

# ... o agente principal executa a tarefa ...

# Ao final, registre explicitamente o que foi aprendido (escrita nunca é
# automática — fica a critério de quem chama, no espírito do write-gating):
hook.on_task_end(
    task_instruction="Como faço deploy seguro de um banco em background?",
    store="insights",
    summary="Confirmado: checar a porta antes de subir o serviço evita falha silenciosa.",
)
```

`hook.subscribe(callback)` permite plugar logging/observabilidade sem
herdar nada — o callback recebe o `OrchestratorResult` bruto de cada
interceptação.

## 🤖 TesseraOrchestrator — pipeline de 3 agentes (QUMem-style)

Em vez de deixar um único agente genérico buscar e responder (o que gera
confusão de estado), o `TesseraOrchestrator` separa o trabalho em 3 etapas
especializadas, cada uma plugável a um LLM real — é o motor por trás do
`TesseraTaskHook` acima, mas também pode ser usado diretamente:

```python
from tessera import TesseraEngine, TesseraOrchestrator

engine = TesseraEngine(storage_dir="./memories")
engine.build_index()

# Por padrão usa uma simulação determinística offline (sem chave de API).
# Passe seu próprio `llm_fn` para plugar um modelo real.
orchestrator = TesseraOrchestrator(engine)

result = orchestrator.run("Como faço deploy seguro de um container docker?")
print(result.information_need)       # 1. O que a tarefa realmente precisa do passado
print(result.retrieval_query)        # 2. Consulta refinada de busca
print(result.stores_queried)         # 2b. Quais gavetas (facts/preferences/insights) foram abertas
print(result.raw_memories)           # 3. Notas brutas recuperadas (DW-PR + ConflictResolver)
print(result.consolidated_context)   # 4. Contexto limpo, pronto para o prompt do agente
```

Para plugar um LLM real, passe `llm_fn=meu_callable(system_prompt, user_prompt) -> str`,
por exemplo envolvendo `lao_core.engine_router.invoke` ou o SDK da OpenAI/Anthropic.

**Importante**: os "3 agentes" (Need/Planner/Inference) não são IAs próprias —
são só nomes das 3 etapas do pipeline. Cada etapa é um prompt template + uma
chamada a `llm_fn`. Sem passar um `llm_fn` real, a simulação offline usa
apenas regras determinísticas de string (regex/template), sem nenhum
raciocínio de fato — isso existe para o pipeline ser 100% testável sem
depender de rede/API key, não para uso em produção.

### Usando um LLM real de verdade (não a simulação)

Existem 2 backends prontos em `tessera/llm_bridge.py`, escolhidos automaticamente
por `resolve_llm_fn()` em ordem de velocidade (benchmark 2026-08-21, prompt
simples de 1 turno):

| Backend | Latência/chamada | Como funciona |
|---|---|---|
| **Azure AI Gateway** (padrão) | **~2.1s** | Chamada HTTPS direta (OpenAI-compatible), sem subprocess |
| `engine_router.py --engine opencode` | ~9.2s | Subprocess CLI (sst/opencode) |
| `engine_router.py --engine copilot` | ~13.4s | Subprocess CLI (GitHub Copilot CLI) |

O `TesseraOrchestrator` faz 3 chamadas por execução (Need → Planner → Inference),
então o backend Azure Gateway é ~4-6x mais rápido no total (~6s vs ~28-40s).

```bash
# Via CLI: liga o modo LLM real (tenta Azure Gateway primeiro, depois engine_router)
export TESSERA_AZURE_GATEWAY_API_KEY="..."   # ou configure no .env, ver .env.example
tessera start .claude/memory "Como o LAO classifica hipóteses?" --use-llm

# Forçar o fallback via engine_router (ex: sem credencial do gateway configurada)
tessera start .claude/memory "..." --use-llm --llm-backend engine_router --llm-engine opencode
```

```python
from tessera.llm_bridge import resolve_llm_fn
from tessera import TesseraEngine, TesseraOrchestrator

engine = TesseraEngine(storage_dir="./memories")
engine.build_index()

llm_fn = resolve_llm_fn()  # tenta Azure Gateway, depois engine_router.py, senão None
orchestrator = TesseraOrchestrator(engine, llm_fn=llm_fn)  # cai na simulação se llm_fn=None
result = orchestrator.run("Como faço deploy seguro de um container docker?")
```

Se nenhum backend estiver configurado (sem `TESSERA_AZURE_GATEWAY_API_KEY` e sem
`lao_core/engine_router.py` acessível), `resolve_llm_fn()` retorna `None` e o
orchestrator cai de volta na simulação offline — nunca falha o pipeline
inteiro por falta de um LLM real configurado.

## 🔌 Servidor MCP (Model Context Protocol)

O Tessera pode ser exposto como servidor MCP, permitindo que qualquer cliente
compatível (Claude Desktop, Cursor, VS Code Copilot, etc.) leia/escreva
memórias nativamente:

```bash
pip install -e ".[mcp]"
LAO_MEM_DIR=/caminho/para/memories tessera-mcp
```

Tools expostas: `rebuild_index`, `query_memories`, `query_store` (busca
escopada a uma gaveta: `facts`/`preferences`/`insights`), `write_memory`,
`query_memories_pipeline` (roda o trio de agentes detetives completo para
uma tarefa, igual ao `TesseraTaskHook.on_task_start`; suporta `use_llm=True`
para uma chamada real de LLM em cada etapa — ver seção "LLM real via MCP"
abaixo), `get_index_composition`, `run_doctor`, `run_quickstart`.
Resources expostos: `memories://{memory_id}`, `graph://index`.

Configuração de exemplo (`claude_desktop_config.json` ou `.vscode/mcp.json`):

```json
{
  "mcpServers": {
    "tessera": {
      "command": "tessera-mcp",
      "env": { "LAO_MEM_DIR": "/caminho/absoluto/para/memories" }
    }
  }
}
```

Código-fonte: [`tessera/mcp_server.py`](tessera/mcp_server.py).

## 📤 Como o Tessera retorna dados para o agente (formato exato)

Isso é a parte que costuma confundir: **o Tessera nunca "entrega o arquivo inteiro"** para o agente — ele devolve uma **lista de objetos estruturados** (JSON, via MCP; texto formatado, via CLI), já ranqueados e com conflitos temporais resolvidos. O agente lê esse retorno como contexto, não abre o `.md` no disco.

### Via MCP (`query_memories`, `query_store`) — o formato que um agente de verdade consome

```jsonc
// Retorno de query_memories(query="benchmark llm backend", top_n=1)
[
  {
    "id": "tessera-llm-backend-benchmark",     // slug = nome do arquivo sem .md
    "type": "factual",                       // gaveta tipada: factual | preference | procedural_anchor
    "score": 0.0689,                         // score do Dynamic Weighted PageRank (DW-PR), não é similaridade bruta
    "body": "Benchmark (2026-08-21) comparando latencia...",  // corpo INTEIRO da nota (texto, sem frontmatter)
    "filename": "tessera-llm-backend-benchmark.md"  // nome do arquivo original em disco, se o agente quiser abrir na íntegra
  }
]
```

- **`body`** é o texto completo da nota (menos o frontmatter YAML) — na prática, isso já É o conteúdo que o agente injeta no seu próprio contexto/prompt. Não tem paginação nem truncamento automático; se a nota for grande, o `body` vem grande.
- **`score`** não é "quão parecido é com a query" puro — é o resultado final do PageRank Dinâmico sobre o subgrafo (1-hop a partir dos nós-semente), então uma nota pouco parecida textualmente mas muito conectada a notas relevantes pode pontuar mais alto que uma nota "óbvia" isolada.
- **`filename`**/`id` deixam claro de qual arquivo aquilo veio, caso o agente precise abrir o `.md` original (ex.: para editar) — mas isso é exceção, não o fluxo padrão de leitura.
- **Conflitos já resolvidos antes de chegar aqui**: se duas notas do tipo `preference`/`factual` se contradizem (mesmo `id` de entidade, datas diferentes), o `ConflictResolver` já descartou a mais antiga — o agente nunca vê as duas.

### Via CLI (`tessera query`) — a mesma informação, formatada para leitura humana no terminal

```
$ tessera query .claude/memory "tessera llm backend benchmark" --top-n 1

[1] tessera-llm-backend-benchmark (factual) — score=0.0689  [tessera-llm-backend-benchmark.md]
Benchmark (2026-08-21) comparando latencia de backends de LLM real...
```

Mesma estrutura (`id`, `type`, `score`, `filename`, corpo completo), só que impressa como texto no stdout em vez de JSON — é isso que um agente rodando `tessera query ... via Bash` lê e usa como contexto, exatamente como leria o resultado de um `grep`, só que já filtrado/ranqueado/deduplicado.

### Via `tessera start` (orchestrator completo) — contexto já sintetizado, não uma lista de notas

`tessera start`/`query_memories_pipeline` vão um passo além: em vez de devolver a lista crua de notas, o **Agente de Inferência de Estado** (3ª etapa do orchestrator) consolida tudo em um único bloco de texto (`consolidated_context`) pronto pra colar no prompt do agente principal — é a diferença entre "aqui estão 3 notas relacionadas" e "aqui está o resumo do que essas 3 notas dizem, sem redundância".

## 🧠 LLM real via MCP (`query_memories_pipeline(..., use_llm=True)`)

Por padrão, tanto `tessera start` quanto `query_memories_pipeline` (MCP) rodam
as 3 etapas do orchestrator (Need → Planner → Inference) contra uma
**simulação offline determinística** (templates de string, sem chamar
nenhum modelo) — é assim que o pipeline continua 100% testável e usável
sem nenhuma credencial configurada.

Para acionar uma **chamada real de LLM** em cada etapa via MCP (equivalente
ao `tessera start ... --use-llm` da CLI), passe:

```jsonc
// Tool call: query_memories_pipeline
{
  "task_instruction": "Qual backend de LLM devo usar para rodar o pipeline mais rápido?",
  "use_llm": true,
  "llm_backend": "azure"   // ou "engine_router"
}
```

- `llm_backend="azure"` (padrão) — chama o Azure AI Gateway interno da
  Blip via HTTPS direto (~2s/chamada, ~6s no total pras 3 etapas).
  Requer `TESSERA_AZURE_GATEWAY_API_KEY` configurada **no ambiente do
  processo MCP** (não no shell do agente que está chamando a tool — o
  processo `tessera-mcp` já está rodando e só lê o ambiente uma vez, no boot).
- `llm_backend="engine_router"` — delega cada etapa pro
  `lao_core/engine_router.py invoke` (claude/copilot/gemini/opencode, com
  failover por saúde/cooldown já embutido). Mais lento (~9-13s/chamada),
  mas funciona sem credencial Azure, desde que uma dessas CLIs esteja
  disponível. `llm_engine` escolhe uma engine específica; deixe `None` pra
  deixar o `engine_router` escolher por prioridade/saúde.
- Se `use_llm=true` mas nenhum backend estiver configurado/acessível, cai
  de volta pra simulação offline automaticamente (mesmo comportamento da
  CLI) — o campo `llm_backend_used` no retorno diz qual caminho foi
  realmente usado (`"azure"` / `"engine_router"` / `"simulated"`).

**Pegadinha importante**: o processo MCP lê variáveis de ambiente **uma
única vez**, na inicialização. Se você exportar
`TESSERA_AZURE_GATEWAY_API_KEY` no seu shell depois que o servidor MCP já
está conectado, essa chamada não vai enxergar a chave até você reiniciar a
conexão MCP — mesma pegadinha já documentada pro `resolve_llm_fn()` da CLI.

## 🌐 Como outros sistemas/CLIs devem usar o Tessera (regra prática)

**Regra de ouro: para qualquer pergunta que dependa de memória (`.claude/memory/`), o agente deve tentar o Tessera primeiro — nunca `grep`/`glob`/`Read` cru no diretório de memórias.**

Isso vale igualmente para Claude Code, Copilot CLI e Gemini CLI (essa regra está espelhada em `CLAUDE.md`, `AGENTS.md`, `GEMINI.md` e `.github/copilot-instructions.md` — arquivos agnósticos de CLI). O motivo não é estilo, é correção: um `grep` bruto não sabe que duas notas se contradizem e uma está obsoleta; o Tessera já resolveu isso antes de devolver qualquer coisa.

**Ordem de fallback recomendada, do mais rico pro mais simples:**

1. **`query_memories_pipeline(task_instruction)`** (MCP) ou `tessera start <dir> "<tarefa>"` (CLI) — quando a pergunta é ampla/aberta ("o que já sabemos sobre X?"). Roda o pipeline completo (Need→Planner→Retrieval→Inference) e devolve contexto já sintetizado.
2. **`query_memories(query, top_n)`** (MCP) ou `tessera query <dir> "<busca>"` (CLI) — quando o agente já sabe exatamente o que está buscando e só quer as notas brutas ranqueadas, sem a etapa de síntese.
3. **`query_store(query, store, top_n)`** (MCP) — quando o agente já sabe que só quer uma gaveta específica (ex.: só `preferences`, pra responder "o que o usuário prefere?").
4. **Só então**, se o Tessera estiver fora do ar (erro de MCP, índice corrompido) ou o agente precisar editar o arquivo físico diretamente, cair para `Read`/`grep`/`glob` — e dizer explicitamente que é um fallback, não o caminho normal.

**Para gravar** (não ler): nunca `Write`/`Edit` direto em `.claude/memory/*.md`. Sempre `write_memory` (MCP) ou `tessera write` (CLI) — isso passa a nota pelo `WriteGatingEngine` antes de tocar o disco (bloqueia contaminação de estado/instruções maliciosas persistidas como se fossem memória legítima).

**⚠️ `mem_id` SEMPRE com prefixo de domínio.** Todo `mem_id`/`--id`/`mem_id_prefix` deve seguir `"<domínio>/<slug>"` (ex: `"research/browser-actions/thesis"`, `"lao/algum-aprendizado"`) — nunca um slug solto sem `/`. Um `mem_id` sem prefixo grava a nota solta na raiz de `storage_dir`, ao lado de `MEMORY.md`/`README.md`, quebrando a convenção de pastas por domínio (`research/<topico>/`, `lao/`, `learnings/`, `business/`, etc. — ver `STRUCTURE.md`). Isso já aconteceu em produção (run autônomo `/lao`, engine Gemini, 2026-08-25) — `write_memory_note()` agora emite um `warnings.warn(...)` quando detecta isso (não bloqueia a escrita, só avisa), mas o hábito certo é sempre prefixar.

### 🧩 Decomposição automática de episódios (`tessera decompose` / `decompose_episode`)

Inspirado no decompositor `g_φ` do paper QUMem: em vez de você decidir manualmente "isso é um fato, isso é uma preferência, isso é um insight" e chamar `write_fact`/`write_preference`/`write_insight` um por um, descreva o episódio inteiro (início/meio/fim) e deixe o Tessera extrair e classificar automaticamente N memórias atômicas — cada uma ainda passa pelo mesmo `WriteGatingEngine` de uma escrita manual.

```bash
# Offline (heurística por palavras-chave, sem LLM, roda sem nenhuma credencial):
tessera decompose .claude/memory \
  --mem-id-prefix "research/checkout-latency-fix" \
  --beginning "Tarefa: investigar lentidão no endpoint de busca." \
  --middle "Descobrimos que faltava um índice composto na tabela de produtos." \
  --end "Criamos o índice e a query caiu de 4s para 80ms. O time pediu para sempre rodar EXPLAIN ANALYZE antes de aprovar uma migration. Índices na ordem errada não ajudam em nada."

# Com LLM real (mesmo backend do `tessera start --use-llm`):
tessera decompose .claude/memory --mem-id-prefix "research/checkout-latency-fix" \
  --beginning "..." --middle "..." --end "..." --use-llm
```

Testado ao vivo com o backend Azure Gateway real (não simulado): a partir de um único episódio, extraiu corretamente **4-8 memórias atômicas** (facts + 1 preference + 1-2 procedural_anchor) em ~2-5s, cada uma gravada em `{mem_id_prefix}/{tipo}-{n}.md`. Equivalente MCP: tool `decompose_episode(...)`, mesmos parâmetros `use_llm`/`llm_backend`/`llm_engine` do `query_memories_pipeline`. Ver `tessera/docs/QUMEM-GAP-ANALYSIS.md` para o racional completo (o que no paper isso aproxima, e o que continua sendo uma simplificação deliberada).

### 🕐 Detecção de fronteira de episódio (`tessera.episode_boundary.EpisodeBoundaryTracker`)

O paper QUMem usa um classificador de continuidade turno-a-turno para decidir dinamicamente onde um episódio começa/termina, em vez de exigir que o chamador delimite manualmente. Tessera não tinha nenhum equivalente — `Episode(beginning, middle, end)` sempre foi preenchido à mão. `EpisodeBoundaryTracker` (Python, sem CLI/MCP dedicado ainda — é uma primitiva de biblioteca para quem está processando uma conversa/sequência de turnos programaticamente) fecha um episódio automaticamente por:

1. **Timeout**: gap de tempo grande demais entre turnos (`timeout_minutes`, padrão 30min).
2. **Deriva de tópico**: similaridade TF-IDF do novo turno vs. o episódio acumulado cai abaixo de um limiar (`similarity_threshold`).

```python
from tessera.episode_boundary import EpisodeBoundaryTracker

tracker = EpisodeBoundaryTracker()
for turn_text in conversation_turns:
    closed = tracker.add_turn(turn_text)
    if closed is not None:
        engine.write_episode(mem_id=..., store=..., episode=closed, ...)
tail = tracker.flush()  # não esquecer o episódio ainda aberto no final
```



```
tessera/
├── tessera/                     # Pacote Python instalável (código de produção)
│   ├── __init__.py           # API pública (TesseraEngine, TesseraOrchestrator, Entity, ...)
│   ├── models.py             # Dataclasses: Entity, Connection, MemoryFrontmatter
│   ├── security.py           # WriteGatingEngine (anti contaminação de estado)
│   ├── conflict.py           # ConflictResolver (resolução cronológica)
│   ├── engine.py             # TesseraEngine (escrita, indexação, retrieval DW-PR)
│   ├── orchestrator.py       # TesseraOrchestrator (pipeline Need->Planner->Retrieval->Inference)
│   ├── skills.py             # install_default_skills() — instala as 5 skills padrão
│   ├── skills_library/       # As 5 âncoras procedimentais padrão (.md, package data)
│   ├── mcp_server.py         # Servidor Model Context Protocol (tools + resources)
│   └── cli.py                # Comando `tessera` (init/write/index/list/query/skills/start)
├── tessera_mcp_server.py         # Atalho de compatibilidade: `python3 tessera_mcp_server.py`
├── tests/
│   ├── test_engine.py        # Testes unitários rápidos (pytest)
│   └── stress_test.py        # Suíte de estresse/benchmark em escala (190 memórias)
├── examples/
│   └── quickstart.py         # Exemplo mínimo executável
├── docs/
│   ├── ARCHITECTURE.md       # Racional científico + diagrama de fluxo de dados
│   ├── CODE_EXPLANATION.md   # Explicação linha a linha de cada classe/método
│   ├── PROCEDURAL_ANCHORS.md # Aprofundamento sobre âncoras procedimentais (skills)
│   └── REFERENCES.md         # Placeholder para as referências científicas citadas
├── archive/                  # Versões anteriores (v1, v2, v3) mantidas como histórico
│   └── README.md             # O que mudou em cada versão
├── pyproject.toml            # Empacotamento (pip install -e . / uv pip install -e .)
├── install.sh                 # Instalador de um comando só (venv opcional + doctor automático)
└── README.md                 # Este arquivo
```

## 🧠 Como funciona (resumo)

1. **Escrita**: todo novo conteúdo passa pelo `WriteGatingEngine`, que audita
   o texto em busca de instruções hostis/contraditórias e sanitiza antes de
   gravar. A nota é serializada como Markdown com frontmatter YAML
   (`MemoryFrontmatter`) e persistida fisicamente em `{storage_dir}/{id}.md`.
2. **Indexação**: `build_index()` varre o diretório, reconstrói um grafo
   dirigido (`networkx.DiGraph`) conectando memórias ↔ entidades ↔ tags ↔
   conexões explícitas (`active_connections`), e treina um vetorizador
   TF-IDF sobre o corpus textual de todos os nós.
3. **Recuperação**: `retrieve_context(query)` calcula similaridade de
   cosseno para achar até 30 *seed nodes*, expande 1 hop (sucessores +
   predecessores) para formar um subgrafo focado, pondera dinamicamente as
   arestas (com boost de 1.35x para relações procedurais como
   `stabilizes_service`), roda PageRank personalizado nos seed nodes, filtra
   só nós de memória real (não tags/entidades abstratas) e por fim aplica o
   `ConflictResolver` para descartar preferências/fatos obsoletos sobre o
   mesmo assunto, mantendo só a versão cronologicamente mais recente.
4. **Resultado**: uma lista ordenada de memórias (`top_n`) prontas para
   serem injetadas no prompt do agente — sem saturar o contexto, sem
   contradições temporais, sem ruído.

Para o detalhamento científico completo (papers/conceitos de origem:
QUMem, MemORAI, FinPerMA, State Contamination), veja
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## 🔒 Segurança

O `WriteGatingEngine` detecta padrões comuns de injeção de instrução
hostil (ex.: "ignore as instruções anteriores") e tags suspeitas
(`override`, `bypass`, `root`, ...), elevando um score de ameaça e
substituindo o trecho malicioso por um marcador de redação antes de
qualquer gravação em disco — nunca depois. Veja `tests/test_engine.py::test_write_gating_sanitizes_hostile_content`
e a suíte completa em `tests/stress_test.py` para exemplos verificáveis.

## 🤝 Contribuindo / Instalando em outro projeto

Como o Tessera é um pacote Python padrão (`pyproject.toml` + `setuptools`),
qualquer pessoa pode instalá-lo em outro repositório:

```bash
# uv
uv add "tessera @ git+https://github.com/blip-ai/lao-lab-autonomous-officer.git#subdirectory=tessera"

# pip
pip install "git+https://github.com/blip-ai/lao-lab-autonomous-officer.git#subdirectory=tessera"
```

ou, localmente, clonando o repositório e rodando `pip install -e ./tessera`
(ou `uv pip install -e ./tessera`) — ou, mais simples, `cd tessera && ./install.sh`
(que já cuida de venv opcional, extras e `tessera doctor` de verificação).

Não há chave de API nem serviço externo necessário para o motor em si —
tudo roda localmente com arquivos `.md` no disco. O servidor MCP e o
`TesseraOrchestrator` são as únicas peças pensadas para se conectar a um LLM
real (via `llm_fn` plugável ou um cliente MCP), mas mesmo assim funcionam
totalmente offline por padrão (com simulação determinística).
