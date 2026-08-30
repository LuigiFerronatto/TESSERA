# Tessera — Como Funciona e Próximas Evoluções

> Compartilhado no `#lao-innovation-lab` em 2026-08-25, como thread de
> detalhamento do post de evolução da memória do LAO.
> Iniciativa criada por **@LuigiFerronatto**.

---

## 1. O Problema Que Isso Resolve

O LAO precisa lembrar de coisas entre sessões: OKRs da Blip, preferências de
como o Luigi/o time quer que eu me comunique, aprendizados sobre bugs que já
encontrei antes, decisões arquiteturais já tomadas. O modelo antigo era um
punhado de arquivos `.md` soltos em `.claude/memory/`, lidos por `grep`/`glob`
sempre que alguma sessão precisava de contexto.

Isso quebra de três formas específicas:

1. **Sem noção de validade temporal** — se uma preferência mudou (ex: "não
   quero mais scripts assim, quero assim"), o arquivo antigo continua lá,
   contradizendo o novo, e um grep simples retorna os dois igualmente.
2. **Sem separação por função** — um "fato" (uma URL de API, um ID de
   database) e uma "preferência" (como o usuário gosta de receber updates)
   ficavam misturados no mesmo arquivo, então recuperar um trazia ruído do
   outro.
3. **Sem ranqueamento por relevância real** — recuperação por similaridade de
   texto pura ignora o quão "central"/conectada uma informação é no
   conhecimento acumulado. Uma nota isolada e uma nota bem referenciada por
   dezenas de outras pesavam igual.

**Tessera** foi desenhado especificamente para resolver essas três coisas, com
base em pesquisa publicada recentemente (não inventado do zero):

- **QUMem** (arXiv 2608.16168) — episódios + typed stores + pipeline de 3
  agentes para inferência de estado.
- **LiveMem** (arXiv 2608.02515) — continuidade/resolução de conflito
  temporal em memória de longa duração.
- **Range Retrieval com índices baseados em grafo** (arXiv 2502.13245) —
  fundamenta o uso de ranqueamento via grafo em vez de top-k por
  similaridade pura.

---

## 2. Os Três Pilares

### Pilar 1 — Episódios, não blocos arbitrários

Cada memória tem um `episode_id`: `start`, `middle` ou `end`. Isso preserva
o contexto de um evento inteiro (causa → decisão → resultado) em vez de
cortar arbitrariamente por contagem de tokens ou turnos. Uma decisão
("mudamos de X para Y") e o motivo ("porque X causava Z") continuam
rastreáveis como parte do mesmo evento, mesmo que estejam em notas
separadas no tempo.

### Pilar 2 — Typed Stores (as "gavetas")

Toda memória escrita é classificada em **uma de três gavetas**:

| Store | O que guarda | Exemplo real |
|---|---|---|
| **`factual`** | Informação concreta e imutável | Um endpoint, um ID de database Notion, um resultado de benchmark |
| **`preference`** | Comportamento, gosto, feedback do usuário | "LAO deve responder em primeira pessoa", "não escrever scripts rígidos de comunicação" |
| **`procedural_anchor`** | Insight transferível — um padrão reusável em situações futuras | "Verificação deve ser mandatória, não opcional", um plano de ação testado que funcionou |

Essa separação existe porque cada tipo tem uma **vida útil e uma regra de
conflito diferentes**: um fato raramente muda: uma preferência pode ser
substituída por uma mais recente; um insight procedural precisa ser
reutilizável em contextos novos, não apenas no contexto onde foi aprendido.

### Pilar 3 — Pipeline de 3 Agentes (Need → Planner → Inference)

Quando alguém (ou o próprio LAO) faz uma pergunta que precisa de memória,
três agentes entram em ação, em sequência:

```
Pergunta/Tarefa
      │
      ▼
┌─────────────────────────┐
│ 1. Information-Need     │  "O que eu preciso descobrir no histórico
│    Agent                │   de memórias para responder isso?"
└─────────────────────────┘
      │
      ▼
┌─────────────────────────┐
│ 2. Retrieval-Planning    │  Cria um plano de busca focado e aciona
│    Agent                 │  as ferramentas certas nas gavetas certas
│                          │  (factual / preference / procedural_anchor)
└─────────────────────────┘
      │
      ▼
┌─────────────────────────┐
│ 3. State-Inference       │  Junta as pistas, descarta memórias
│    Agent                 │  obsoletas/contraditórias, monta um resumo
│                          │  do estado atual e validado
└─────────────────────────┘
      │
      ▼
Contexto consolidado, pronto para o agente principal usar
```

Isso é fundamentalmente diferente de "pegar as top-5 notas mais parecidas
com a query e jogar no prompt" — o Tessera **interpreta** a evidência coletada
antes de devolver, já resolvendo contradições e filtrando o que está
desatualizado.

---

## 2.5. O Tessera Explicado de Forma Simples (A Analogia do Quadro de Cortiça)

Se a matemática e a teoria de grafos parecerem complicadas de início, esqueça as fórmulas. O Tessera funciona de uma forma extremamente intuitiva e física, quase como aquele **quadro de cortiça de investigador de polícia**, cheio de fotos espetadas e interligadas por fios de lã vermelha.

### A. Onde as informações ficam salvas?
Não existe um banco de dados misterioso ou binário indecifrável. 
*   **Cada memória é um arquivo de texto comum (`.md`)** salvo fisicamente na pasta `.claude/memory/`. Você pode abrir, ler e editar qualquer um manualmente quando quiser.
*   No topo de cada arquivo existe um cabeçalho simples (chamado Frontmatter YAML) com etiquetas estruturadas:
    ```yaml
    id: benchmark-azure-gateway
    type: factual
    tags: [benchmark, azure, latência]
    entities: [Azure Gateway, GPT-5.2]
    related_to: [custos-azure]
    ```
*   **E o tal do arquivo JSON (`graph.json`)?** Ele é apenas o nosso **"mapa de bolso"** (um cache rápido). O motor lê todos os arquivos `.md` uma vez, monta esse mapa no JSON e o consulta para que as buscas sejam instantâneas, evitando ter que abrir centenas de arquivos de texto do zero a cada pergunta.

### B. Como o Quadro de Cortiça se conecta? (As Linhas Vermelhas)
Imagine que o Tessera espeta três tipos de "alfinetes" no quadro:
1.  **Alfinetes de Notas (Azuis):** São os arquivos de texto (`.md`) com o conteúdo das memórias.
2.  **Alfinetes de Tags (Verdes):** São os tópicos ou tags (ex: `#benchmark`, `#azure`).
3.  **Alfinetes de Entidades (Vermelhos):** São os termos ou ferramentas de destaque (ex: `Luigi`, `Azure AI Gateway`).

O Tessera passa "linhas de lã vermelhas" entre esses alfinetes de forma automática:
*   **Ponte por Tag:** Se o seu teste de velocidade (`Nota A`) tem a tag `#azure`, ele passa um fio dela até o alfinete verde `azure`. Se uma nota sobre custos (`Nota B`) também tem a tag `#azure`, ela se conecta ao mesmo alfinete. **A Nota A e a Nota B agora estão relacionadas através da tag em comum.**
*   **Ponte por Entidade:** Se ambas as notas citarem a entidade `Azure AI Gateway`, elas ganham conexões até o alfinete vermelho do gateway.
*   **Fio Direto (related_to):** No topo da nota, você pode falar diretamente para conectar à `Nota C`. O Tessera passa uma linha direta de barbante entre elas.

### C. Como ele encontra memórias sem usar LLM? (Caminhando pelos fios)
Se você perguntar offline: *"Quanto tempo demora chamar a IA pelo gateway da Azure?"*
1.  **O Ponto de Partida:** O sistema busca por similaridade de texto clássica e cai na `Nota A` (que fala do benchmark). Essa nota vira nossa "âncora".
2.  **Seguindo os Barbantes:** A partir de `Nota A`, o motor caminha fisicamente pelas linhas de lã vermelha:
    *   Ele segue a ponte da tag `#azure` e descobre a `Nota B` (custos).
    *   Ele segue a ponte da entidade `Azure AI Gateway` e descobre a `Nota C` (um erro que aconteceu semana passada).
3.  **Ranking e Limpeza:** Mesmo que a pergunta não falasse sobre "custos" ou "erros", o sistema as encontrou porque elas estavam a "um palmo de barbante" de distância. Ele calcula quais notas têm mais linhas ligadas a elas (PageRank) e descarta as antigas que foram atualizadas (ConflictResolver).

### D. E como funcionam os Agentes no Modo Online (Com LLM)?
No modo online, você contrata **três investigadores auxiliares (agentes especialistas)** para irem ao quadro por você:
*   **O Investigador 1 (Necessidade - Need):** Lê sua tarefa e define o objetivo: *"Pra fazer isso, preciso descobrir o procedimento técnico e o tempo de resposta que usamos antes."*
*   **O Investigador 2 (Planejador - Planner):** Transforma o objetivo em uma busca certeira pro motor caminhar nos barbantes, escolhendo as gavetas certas (Fatos, Preferências ou Insights) para não perder tempo. O motor offline roda e resgata as notas físicas do quadro.
*   **O Investigador 3 (Inferência - Inference):** Lê todos os papéis coletados, joga fora o lixo e o que está desatualizado, e resume tudo em um único relatório limpo de uma página para o agente principal trabalhar.
*   *Se a rede cair ou o LLM falhar:* O Tessera aciona um **fallback offline determinístico** que simula os detetives localmente por regras, impedindo o pipeline do LAO de quebrar.

---

## 3. Como o Tessera Recupera (a parte técnica do "grafo")

Por baixo, o Tessera constrói um grafo de conhecimento a partir do
frontmatter YAML + tags + entidades de cada nota `.md`. A recuperação
não é um simples "top-k por similaridade de texto":

1. Um **seed inicial** é formado por similaridade TF-IDF (cosseno) entre a
   query e as notas.
2. Sobre um **subgrafo de 1-hop** a partir desse seed, o Tessera roda um
   **Dynamic Weighted PageRank (DW-PR)** — um PageRank que dá mais peso a
   notas bem conectadas ao restante do grafo.
3. Antes de devolver, o **Conflict Resolver** aplica resolução temporal:
   se duas notas `factual`/`preference` sobre a mesma entidade se
   contradizem, só a mais recente sobrevive no resultado.

Resultado prático: uma nota pode ranquear **acima** de outra mais parecida
textualmente, se estiver mais conectada ao conhecimento acumulado — e uma
nota obsoleta nunca chega ao agente, mesmo que o texto dela combine bem
com a pergunta.

---

## 4. Como Isso Roda no LAO Hoje

- **CLI**: `tessera init`, `tessera write`, `tessera query`, `tessera index`, `tessera
  start` (`.claude/memory/` é o storage_dir do LAO).
- **MCP Server** (`tessera`, registrado em `.mcp.json`): expõe
  `query_memories`, `query_store`, `write_memory`, `rebuild_index`,
  `get_memory`, `get_index_stats`, `query_memories_pipeline` — qualquer CLI
  (Claude Code, Copilot CLI, Gemini CLI) que tenha esse MCP conectado
  pode usar essas ferramentas diretamente.
- **Regra dura em CLAUDE.md/AGENTS.md/GEMINI.md/copilot-instructions.md**:
  nenhum agente deve dar `grep`/`glob`/`Read` cru em `.claude/memory/` —
  sempre tentar o Tessera primeiro (MCP ou CLI), só cair para arquivo bruto
  se o Tessera estiver indisponível, e dizer isso explicitamente quando cair.
- **Backend de LLM para o pipeline de 3 agentes**: Azure AI Gateway
  (HTTPS direto) como padrão — ~2.1s/chamada, 4-6x mais rápido que rodar
  via subprocess de CLI (`opencode` ~9.2s, `copilot` ~13.4s) — com
  `engine_router.py` como fallback automático.
- **Write-Gating**: toda escrita passa por um `WriteGatingEngine` que
  audita/sanitiza o conteúdo (score de toxicidade, detecção de tentativa
  de prompt-injection) antes de persistir no disco.

---

## 5. O Sonho: Tessera Plug-and-Play em Qualquer Repositório

Hoje o Tessera está acoplado ao LAO (`.claude/memory/` como storage padrão,
integrado via `.mcp.json` deste repositório). **O objetivo declarado é
transformar o Tessera num pacote instalável e agnóstico** — qualquer pessoa,
em qualquer repositório, qualquer CLI (Claude Code, Copilot CLI, Gemini
CLI, Cursor, o que for), deve poder rodar:

```bash
pip install tessera
tessera init ./meu-projeto/memory
tessera-mcp   # registra o MCP server, aponta pro storage_dir do projeto
```

...e ter o mesmo sistema de memória com episódios, typed stores e o
pipeline de 3 agentes funcionando imediatamente, sem precisar saber nada
sobre LAO ou sobre a Blip.

### O que já existe a favor disso:
- O pacote já é instalável via `pip install -e .` (tem `pyproject.toml`
  próprio, entry points `tessera` e `tessera-mcp`) **ou via `./Tessera/install.sh`**
  (venv opcional, extras, `tessera doctor` automático — instalador de um
  comando só, adicionado 2026-08-26).
- O `storage_dir` já é um argumento explícito em todo comando — nada está
  hardcoded para `.claude/memory/`.
- O MCP server já lê `LAO_MEM_DIR` via env var, então plugar em outro
  projeto é só mudar essa variável.

### O que falta para o "plug-and-play" de verdade (próximas evoluções):
1. **Publicar no PyPI** (`pip install tessera` de qualquer lugar, sem
   clonar o repo). *(ainda pendente)*
2. ✅ **Um wizard de setup** (`tessera quickstart`) — implementado
   2026-08-25: detecta o projeto atual (node/python/rust/go/genérico),
   reaproveita um `.claude/memory` existente ou sugere `./memories`, gera
   o bloco de config MCP pronto pra colar. `--apply` executa de verdade
   (cria o dir, roda o primeiro `tessera index`); sem a flag é dry-run.
   Equivalente MCP: `run_quickstart(...)`. **Complementado 2026-08-26**
   com `Tessera/install.sh` — instalador de um comando só (venv opcional,
   extras `[mcp,llm]`, `tessera doctor` automático no final, fallback
   automático para `--index-url https://pypi.org/simple` se um mirror
   corporativo estiver inacessível) — reduz "clonar → rodar 3-4 comandos
   manuais" para `./install.sh` sozinho.
3. **Zero acoplamento a nomes específicos do LAO** — hoje alguns exemplos/
   docs ainda citam `.claude/memory/`, `tessera` como nome do server;
   generalizar para que o nome do projeto/domínio seja um parâmetro, não
   um hardcode. *(ainda pendente — `tessera quickstart`/`install.sh` já
   deixam o storage_dir configurável por projeto, mas o nome do server
   MCP e alguns domínios de exemplo continuam LAO-specific)*
4. **Templates de domínio genéricos** — hoje `lao/`, `research/`,
   `learnings/` são específicos do LAO; permitir que qualquer projeto
   defina seus próprios domínios/typed-stores extras sem editar código.
   *(ainda pendente)*
5. **Modo sem LLM real (fallback determinístico) documentado como
   primeira classe** — para quem não tem um Azure Gateway/chave de API
   configurada, o pipeline de 3 agentes já roda em modo simulado
   (templates de string), então o "instalar e já funcionar" não depende
   de nenhuma chave de API para o caso básico. ✅ já era verdade e agora
   está documentado explicitamente no `README.md`/`CHEATSHEET.md` e
   confirmado pelo `tessera doctor` (marca Azure Gateway como checagem
   **opcional**, não obrigatória).
6. ✅ **Um pacote de testes de smoke-test pós-instalação** (`tessera doctor`)
   — implementado 2026-08-25: valida storage_dir gravável, índice
   constrói sem erro, round-trip de escrita+leitura, `rich`/`mcp`
   instalados, Azure Gateway configurado (opcional). Equivalente MCP:
   `run_doctor(...)`. Chamado automaticamente ao final de
   `Tessera/install.sh`.

Isso é o próximo horizonte de trabalho no Tessera depois da consolidação
atual (typed stores + episódios + hook + backend real de LLM) — o momento
em que ele deixa de ser "o sistema de memória do LAO" e passa a ser "um
sistema de memória que o LAO também usa", disponível pra qualquer squad.

---

## 6. Onde Olhar o Código

- `Tessera/README.md` — documentação completa, incluindo o formato exato de
  retorno de dados e a regra de uso por outros sistemas/CLIs.
- `Tessera/tessera/engine.py` — motor de recuperação (DW-PR, resolução de
  conflito temporal).
- `Tessera/tessera/llm_bridge.py` — os backends de LLM reais (Azure Gateway,
  engine_router).
- `Tessera/tessera/mcp_server.py` — as ferramentas MCP expostas.
- `.claude/memory/lao/tessera-scientific-grounding-qumem-livemem-graph-retrieval.md`
  — a nota de memória com a fundamentação científica completa (o próprio
  Tessera guardando o porquê do seu próprio design).
- `.claude/memory/lao/tessera-llm-backend-benchmark.md` — o benchmark de
  latência dos backends de LLM.

---

*Este documento em si é um exemplo do "explain the why, not just the
what" que rege a comunicação do LAO — não é só uma lista do que foi
construído, é o raciocínio por trás de cada decisão de design.*
