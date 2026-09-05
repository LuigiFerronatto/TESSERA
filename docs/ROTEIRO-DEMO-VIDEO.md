# Roteiro de Demo — Tessera no Terminal (para gravar e postar no Slack)

> Testado ao vivo em 2026-08-25 dentro do próprio repo `lab-autonomous-officer`.
> Todos os comandos abaixo rodam de verdade — copie e cole durante a gravação.

---

## Ferramenta de gravação

Você já tem **OBS Studio** instalado (`/usr/bin/obs`). É a opção mais simples:

1. Abra o OBS → **+** em "Sources" → **Window Capture** → selecione seu terminal.
2. (Opcional, mais bonito) Configure a fonte como **"Screen Capture"** e recorte
   só a área do terminal, com fonte grande (aumente o zoom do terminal antes:
   `Ctrl +` no GNOME Terminal/iTerm/etc — texto grande é essencial em vídeo).
3. Settings → Output → grave em `.mp4`.
4. Clique **Start Recording**, rode o roteiro abaixo, **Stop Recording**.
5. O arquivo fica em `~/Videos/` (ou o path configurado em Output).

**Alternativa leve, sem OBS** (grava direto o terminal como texto, converte pra
gif/vídeo depois — ótimo para quem quer algo mais "hacker" e leve pra subir):

```bash
# instala asciinema (grava sessão de terminal em texto puro)
pip install asciinema
asciinema rec tessera-demo.cast
# ... roda o roteiro ...
# Ctrl+D pra terminar a gravação

# converte pra gif (opcional, para postar sem precisar de player)
pip install agg   # asciinema gif generator
agg tessera-demo.cast tessera-demo.gif
```

Recomendação: **OBS** se quiser algo mais "produzido" (com sua voz explicando);
**asciinema** se quiser algo rápido, leve e sem áudio (o texto fala por si).

---

## Roteiro (± 5-6 minutos de gravação, 9 cenas)

### Cena 0 — O que é o Tessera (introdução, antes de qualquer comando)

Narre (fala de frente pra câmera/tela, sem terminal ainda, ou sobre um
slide/README aberto):
> "Isso aqui é o Tessera — Temporal Evolving State Synthesis with Explicit Relations and Atomic Memories. É o sistema de memória de
> longo prazo que eu construí pro LAO, o Lab Autonomous Officer. Hoje o LAO
> tem mais de 200 memórias — decisões, aprendizados, benchmarks, contexto de
> negócio — guardadas como arquivos Markdown legíveis por humano, mas
> organizadas por trás como um grafo de conhecimento.
>
> Mas para entender o valor real do Tessera, a gente precisa olhar para trás e ver como
> o LAO gerenciava o próprio conhecimento. Passamos por três fases claras de evolução:
>
> **1. A Fase do Brute-Force (O LEAD fazendo tudo):** No início, o próprio agente LEAD
> buscava memória rodando dezenas de comandos manuais de terminal por vez. Mesmo sabendo a arquitetura de pastas perfeitamente, o agente precisava engatilhar múltiplas queries de `grep`, `glob` e `find` em sequência — literalmente dezenas de processos bash *spawned* na máquina — apenas para cruzar referências e validar se um dado existia.
> Ele fazia isso em paralelo com outras tarefas complexas. O resultado? A janela de contexto
> explodia com logs e resultados de busca inúteis, as ações demoravam muito, o agente se perdia na linha de raciocínio e falhava
> em interligar os dados com os objetivos da Blip. Pior: ele tratava a memória recuperada
> como verdade absoluta, sem questionar relevância, validade ou se precisava ser atualizada ou excluída.
>
> **2. A Fase do Especialista (agent/memory.md):** Para resolver isso, criamos um agente especialista
> em memória, o `memory.md`. A nossa hipótese era: 'se tivermos um agente dedicado a trabalhar
> a memória, blindando o LEAD de interagir com os arquivos brutos, o LEAD terá foco total'. A hipótese
> se cumpriu e o especialista passou a gerenciar todo o sistema de memória. Só que esbarramos no
> gargalo da pesquisa: o agente de memória demorava muito tempo buscando e comparando arquivos de texto
> via processos de bash contínuos, gerando enorme overhead de tokens, e os hooks de contexto falhavam silenciosamente por timeout.
>
> **3. A Fase do Tessera (Memória Atômica e Adaptativa):** E é por isso que desenvolvemos o Tessera,
> trazendo os conceitos mais modernos de papers científicos de memória (como PageRank ponderado sobre
> grafos e bi-temporalidade). Com ele, a busca é semântica e instantânea, sem o overhead de varreduras manuais.
>
> A diferença do Tessera pra um RAG comum é que ele não é 'joga tudo num banco
> vetorial e busca por similaridade de texto'. Ele indexa cada nota com
> tipo (fato, preferência, procedimento), conecta memórias relacionadas por
> tag/entidade automaticamente, e ranqueia resultados com um PageRank
> ponderado sobre esse grafo — não só por parecença de texto.
>
> O que eu vou mostrar agora: onde uma busca simples de terminal (grep)
> funciona bem, onde ela para de funcionar, e onde o Tessera entra."

```bash
cd ~/Desktop/Workspace/lab-autonomous-officer
clear
tessera list .claude/memory | grep "notas indexadas"
```

*(Mostra rapidamente o total de notas reais já indexadas — contextualiza a
escala antes de entrar nos comandos individuais)*

### Cena 1 — O que grep faz bem (pra ser justo)

Narre:
> "Antes de mostrar o Tessera, deixa eu ser justo: grep é rápido e funciona
> muito bem quando você lembra a palavra exata."

```bash
clear
time grep -rli "ai voice" .claude/memory/
```

*(Retorna ~15 arquivos reais em ~13ms — grep genuinamente funciona aqui,
porque "ai voice" existe literalmente em nomes de pasta/arquivo)*

### Cena 2 — Onde grep para de funcionar (o caso real)

Narre:
> "O problema não é grep ser lento. É grep só entender a palavra exata.
> Quando você lembra o CONCEITO, mas não a frase literal do arquivo,
> grep simplesmente não acha nada — mesmo a informação existindo."

```bash
clear
time (grep -rli "quanto tempo demora chamar a IA pelo gateway da azure comparado a rodar via linha de comando" .claude/memory/ || echo "Not Found")
```

*(Retorna "Not Found" em ~15-20ms — vazio, mesmo com a nota
`tessera-llm-backend-benchmark.md` existindo e respondendo exatamente essa
pergunta, só que com outras palavras)*

### Cena 3 — A mesma pergunta, via Tessera

```bash
time tessera query .claude/memory "quanto tempo demora chamar a IA pelo gateway da azure comparado a rodar via linha de comando" --top-n 1
```

*(Isso retorna a nota certa: `lao/tessera-llm-backend-benchmark`, com o texto
completo do benchmark — em ~1,6-1,9s, contra os ~15ms do grep vazio)*

Narre:
> "O Tessera entende a INTENÇÃO da pergunta, não só o texto literal. Ele é
> mais lento que grep — cerca de 100x mais lento em termos absolutos — mas
> acha a informação que grep simplesmente não consegue achar. A troca é
> honesta: você paga ~1,5 segundo a mais para recuperar por conceito, não
> por palavra.
>
> Mas e aí, como ele faz essa mágica por baixo dos panos no modo offline, sem gastar um centavo de LLM ou rede?
> É o seguinte: primeiro, ele pega a minha pergunta em português normal e usa uma parada clássica de busca chamada **TF-IDF com similaridade de cosseno** pra achar os arquivos mais parecidos (que são as 'sementes').
> Depois, ele olha pro **grafo de conhecimento** que montamos com as notas do LAO e faz uma expansão de 1-hop: ele puxa todos os arquivos conectados (por tags ou entidades) até um nível de distância.
> Aí vem o pulo do gato: ele roda uma versão modificada do algoritmo **PageRank do Google** (o Dynamic Weighted PageRank) sobre esse pedaço do grafo, dando um bônus de peso para arestas de procedimentos importantes. O PageRank faz os arquivos mais relevantes 'ganharem força' no ranking.
> Por fim, ele roda um **ConflictResolver** de contenção: possíveis conflitos continuam visíveis, porque uma data mais recente não prova sozinha que a memória anterior deixou de valer. A busca continua determinística e offline sem apagar evidência histórica."

### Cena 4 — Benchmark lado a lado (a tabela de verdade)

Narre:
> "Pra deixar isso bem claro, aqui está a mesma pergunta rodada em 4
> ferramentas diferentes, cronometradas de verdade:"

| Comando | Tempo real | Achou a nota certa? |
|---|---|---|
| `grep -rli "<paráfrase>"` | ~0,015-0,017s | ❌ Not Found |
| `grep -rli "ai voice"` (termo literal) | ~0,013s | ✅ (mas só porque a palavra existe literalmente) |
| `find -iname "*azure*gateway*"` | ~0,002s | ❌ (find busca nome de arquivo, não conteúdo) |
| `tessera query "<mesma paráfrase>"` | ~1,6-1,9s | ✅ Acha `tessera-llm-backend-benchmark`, score 0.033 |

```bash
# roda os 4 ao vivo, um atrás do outro, pra provar os números na hora
Q="quanto tempo demora chamar a IA pelo gateway da azure comparado a rodar via linha de comando"
time (grep -rli "$Q" .claude/memory/ || echo "Not Found")
time (find .claude/memory -iname "*azure*gateway*" || echo "Not Found")
time tessera query .claude/memory "$Q" --top-n 1 --no-body
```

Narre:
> "grep e find são ferramentas de correspondência de texto — rápidas,
> literais, cegas para significado. Tessera é uma ferramenta de recuperação
> semântica — mais lenta em milissegundos absolutos, mas é a única das
> quatro que realmente entende o que você quis dizer."

### Cena 5 — Mostrando a escala (quantas memórias existem)

```bash
tessera list .claude/memory | grep "notas indexadas"
```

*(A própria saída do comando já diz o total: "(200 notas indexadas)")*

Narre:
> "Isso não é 5 arquivos. São 200 memórias diferentes — e o Tessera
> acha a certa em milissegundos, sem eu precisar saber onde ela está."

### Cena 6 — Escrevendo uma memória nova (write-gated)

```bash
tessera write .claude/memory \
  --id "demo-exemplo-live-para-video" \
  --type factual \
  --episode start \
  --tags "demo,video,exemplo" \
  --content "Esta e uma nota de exemplo criada ao vivo durante a gravacao do video de demo do Tessera para o canal lao-innovation-lab."
```

*(Mostra a mensagem "✔ Nota de memória gravada em: ...")*

Narre:
> "Toda escrita passa por um filtro de segurança automático antes de tocar
> o disco — nunca é um arquivo cru sendo salvo sem checagem."

```bash
# reindexa e confirma que a nova nota já é buscável
tessera index .claude/memory
tessera query .claude/memory "exemplo criado durante gravacao de video para o slack" --top-n 1
```

*(Limpa o exemplo depois de gravar, para não poluir a memória real:)*
```bash
rm .claude/memory/demo-exemplo-live-para-video.md
tessera index .claude/memory
```

### Cena 7 — O pipeline completo de 3 agentes, com LLM real (a parte mais impressionante)

```bash
# carrega as credenciais do Azure Gateway do .env para a sessão do shell
set -a && source .env && set +a

time tessera start .claude/memory "Qual backend de LLM devo usar para rodar o pipeline do Tessera mais rapido?" --use-llm
```

*(Testado ao vivo em 2026-08-25 - roda de verdade contra `.claude/memory` real,
com `--use-llm` chamando o Azure AI Gateway (gpt-5.2). Leva ~6-8s no total
(3 chamadas reais de LLM), e retorna:*

1. **Necessidade de informação** — o próprio modelo decidindo o que precisa
   verificar (não um template fixo)
2. **Consulta de busca planejada** — os termos de busca que o modelo decidiu
   usar
3. **Contexto consolidado** — um resumo em Markdown, já sintetizado a partir
   das notas reais do repositório (`tessera-llm-backend-benchmark`,
   `tessera-scientific-grounding...`, etc), citando números exatos do benchmark

*Sem `--use-llm` o mesmo comando roda em modo simulado offline (instantâneo,
sem custo/rede) — útil como fallback se a rede cair durante a gravação:*
```bash
tessera start .claude/memory "Qual backend de LLM devo usar para rodar o pipeline do Tessera mais rapido?"
```

Narre:
> "Isso aqui não é busca simples. É o pipeline cognitivo completo com LLM ligado — a parte mais animal do Tessera.
> Em vez de dar uma query direta, a gente aciona um trio de 'agentes detetives' inspirados em papers de memória de longo prazo. Olha o fluxo:
>
> Primeiro, o **Agente de Necessidade (Need)** analisa o prompt principal e se pergunta: 'Cara, o que eu realmente preciso resgatar do passado do LAO pra fazer isso?'. Ele define a intenção da busca de forma lógica.
> Depois, o **Agente de Planejamento (Planner)** traduz essa necessidade em uma query de busca otimizada pro nosso motor. E ele é esperto: decide em quais 'gavetas tipadas' do Tessera (Facts, Preferences ou Insights) buscar, evitando ler arquivos inúteis e cruzar dados à toa.
> Aí, o motor offline que mostrei na Cena 3 entra em ação, puxa as notas e o ConflictResolver preserva possíveis conflitos em vez de escolher um vencedor por recência.
> Por fim, o **Agente de Inferência de Estado** recebe toda a evidência ranqueada e consolida um resumo Markdown para o LEAD, sem tratar “mais novo” como sinônimo de “mais verdadeiro”.
>
> E o melhor de tudo: se a rede cair ou o Azure Gateway falhar, o Tessera tem um **fallback determinístico offline** que simula esses três agentes localmente sem quebrar o fluxo.
> Note o tempo: ~6-8 segundos para as 3 chamadas reais de LLM na nuvem do Azure, entregando uma síntese perfeita pro agente trabalhar!"

### Cena 8 — Terminal 2: qualquer CLI pode usar isso via MCP (Copilot + Gemini)

> Abra um SEGUNDO terminal para essa cena — a ideia é mostrar que o mesmo
> servidor `tessera` funciona plugado em CLIs diferentes, sem nenhum código
> extra por engine.

```bash
clear
echo "=== Copilot CLI chamando o MCP tessera ==="
copilot -p "Use a tool query_memories do servidor MCP tessera para buscar 'backend de llm mais rapido' e resuma o resultado top 1." --allow-all
```

*(Testado ao vivo em 2026-08-25 — Copilot CLI chama `query_memories` via MCP
e devolve um resumo correto do benchmark, em ~25s, mostrando uso de AI
Credits no rodapé)*

```bash
clear
echo "=== Gemini CLI chamando o MESMO MCP tessera ==="
gemini -p "Use a tool query_memories do servidor MCP tessera para buscar 'backend de llm mais rapido' e resuma o resultado top 1." --yolo
```

*(Testado ao vivo em 2026-08-25 — Gemini CLI chama o mesmo `query_memories`
via MCP e devolve um resumo igualmente correto. Pode aparecer ruído de stack
trace `GemmaClassifierStrategy`/`LocalLiteRtLmClient` no stderr — é de um
roteador de modelo local experimental do Gemini, não afeta o resultado; pode
cortar essa parte na edição se preferir um clipe mais limpo)*

Narre:
> "Essa é a parte que importa pra qualquer time: o Tessera não é uma feature
> de um CLI só. É um servidor MCP — um padrão aberto. Claude Code, Copilot
> CLI, Gemini CLI... qualquer engine que fale MCP já consegue ler e escrever
> na mesma memória, sem reescrever nada."

### Encerramento

```bash
echo "Tessera: memoria que entende, nao so armazena."
```

---

## Dicas de gravação

- **Aumente a fonte do terminal** antes de gravar (importante para quem vai
  assistir no Slack em thumbnail pequeno).
- **Limpe a tela** (`clear`) antes de cada cena, para o vídeo não ficar poluído.
- Se for narrar ao vivo, fale devagar e deixe 1-2s de silêncio depois de cada
  comando rodar, antes de começar a explicar o resultado.
- Grave em blocos curtos (cada "Cena" pode ser um clipe separado) se preferir
  editar depois em vez de gravar tudo de uma vez sem cortes.
- Se usar asciinema/gif: sem áudio, então o texto do terminal PRECISA falar
  por si — considere adicionar `echo "// comentário explicando"` antes de
  cada comando, como fizemos no roteiro acima.
- **Sobre a Cena 8 (Terminal 2)**: precisa de dois terminais lado a lado
  (ou dois clipes separados editados depois) — um para o fluxo CLI puro
  (Cenas 1-7), outro mostrando Copilot/Gemini chamando o mesmo MCP.

## Onde postar

Suba o vídeo/gif como reply na mesma thread do post de evolução do Tessera em
`#lao-innovation-lab` (a thread já tem: benchmark + papers + arquitetura +
roadmap plug-and-play em texto — o vídeo é a prova viva disso tudo).
