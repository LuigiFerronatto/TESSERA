# Guia Técnico de Explicação de Código: Tessera

> Nota (reorganização): este guia foi originalmente escrito sobre o arquivo
> monolítico `memory_graph_retrieval_v2.py`. O código de produção atual vive
> no pacote instalável `tessera/`, dividido em módulos (`models.py`,
> `security.py`, `conflict.py`, `engine.py`). A tabela abaixo já reflete o
> mapeamento atualizado; o racional científico e o comportamento descritos
> permanecem válidos — a v3 (usada como base do pacote) só ampliou o limite
> de seed nodes de 5 para 30 (ver [`archive/README.md`](../archive/README.md)).

Este documento apresenta o racional científico e uma explicação detalhada
linha a linha do código-fonte do Tessera (Temporal Evolving State Synthesis with Explicit Relations and Atomic Memories).

Este motor foi arquitetado para servir como o sistema de persistência
inteligente de memórias de produção do LAO (Lab Autonomous Officer),
garantindo a execução de tarefas complexas sem o risco de timeouts,
desalinhamento temporal ou vulnerabilidades de segurança por injeção de dados.

## 🧬 Mapeamento Científico para o Código
O código foi projetado traduzindo diretamente os conceitos fundamentais descritos em papers de ponta de IA e sistemas multiagentes:

Conceito Científico Problema de Origem Solução Implementada no Código Classe/Método Correspondente
Typed Memory & Episódios (QUMem) Acúmulo desordenado de logs e estouro de tokens de contexto [3, 8, 10]. Notas atômicas organizadas sob tipos funcionais estritos (factual, preference, procedural_anchor) contendo proveniência estruturada [3, 10]. tessera.models.MemoryFrontmatter, tessera.engine.TesseraEngine.write_memory_note
Procedural Anchors (Skills as Anchors) Agentes falhando em tarefas básicas de infraestrutura e sintaxe de shell [1, 2]. Nós de primeira classe do tipo procedural_anchor contendo checklists de validação e armadilhas comuns para estabilizar execuções [1, 2]. tessera.models.Connection, tessera.engine.TesseraEngine.build_index
DW-PR & Subgraph Expansion (MemORAI) RAG plano (similaridade de cosseno pura) trazendo blocos soltos e irrelevantes [6]. Identificação rápida de nós sementes, expansão local de vizinhança de 1-hop e execução de PageRank com pesos de aresta dinâmicos ponderados por relevância e boosts funcionais [6]. tessera.engine.TesseraEngine.retrieve_context
Write-Side Gating (State Contamination) Envenenamento de estado de agente via "lavagem de memória" (memory laundering) em resumos futuros [12]. Auditoria heurística e purificação literal do conteúdo da nota antes de consolidar o arquivo Markdown físico no disco [12]. tessera.security.WriteGatingEngine.audit_and_sanitize
Temporal Alignment & Trajectory (FinPerMA) Rigidez em perfis consolidados que falham em capturar mudanças de escolhas do usuário ao longo do tempo [13]. Resolução ativa de conflitos baseada em cronologia fina e identificação de chaves temáticas para priorizar as escolhas vigentes [3, 10, 13]. tessera.conflict.ConflictResolver.resolve_temporal_conflicts
## 📁 Estrutura Lógica de Fluxo de Dados
[Ingestão / Gravação]
 Conteúdo Bruto do LAO ──► WriteGatingEngine (Auditoria & Sanitização) ──► Geração do Frontmatter YAML ──► Gravação Física em .md

[Recuperação / Retrieval]
 Consulta de IA ──► Busca Semântica (TF-IDF) ──► Seleção de Nós Semente ──► Expansão 1-Hop (Subgrafo)
                         │
                         ▼
                   Cálculo do PageRank Dinâmico (DW-PR) com Boost Procedural ──► Ordenação de Memórias
                         │
                         ▼
                   ConflictResolver (Filtro Cronológico e de Preferências Mutáveis) ──► Retorno do Contexto Limpo ao LAO
## 🔍 Detalhamento das Classes e Métodos

### 1. Modelo de Domínio e Metadados (`tessera/models.py`)
A classe MemoryFrontmatter utiliza @dataclass do Python para estruturar os metadados em conformidade com o formato unificado de cartões atômicos do A-MEM:

memory_id: Chave primária da nota.
memory_type: Classificação funcional da memória (factual, preference ou procedural_anchor) [3, 10].
active_connections: Conexões estruturadas entre nós, permitindo ao grafo rastrear links conceituais e heranças lógicas (ex: um procedimento que estabiliza um serviço ou se alinha com uma preferência do usuário).
security: Bloco que registra o status de segurança, nível de ameaça analisado e se a informação passou por sanitização ativa antes da escrita [12].
### 2. Gating de Escrita e Proteção contra Contaminação (`tessera/security.py`)
O motor de segurança atua ativamente antes do processo de compressão (resumo) ou persistência da memória, mitigando o risco de Memory Laundering [12].

class WriteGatingEngine:
    def audit_and_sanitize(self, content_text: str, tags: List[str]) -> Tuple[str, float, bool]:
        # Identifica tentativas de bypass ou envenenamento e higieniza o conteúdo.
Ação: Varre o texto em busca de instruções contraditórias (ex: "ignore as instruções anteriores"). Se detectado, o score de risco é elevado e o trecho hostil é expurgado do texto físico gravado no disco, neutralizando a injeção oculta [12].
### 3. Contenção Não Destrutiva de Conflitos (`tessera/conflict.py`)
O `ConflictResolver` preserva as memórias candidatas quando ainda não existe
regra determinística capaz de provar supersessão:

class ConflictResolver:
    @staticmethod
    def resolve_temporal_conflicts(retrieved_memories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
Funcionamento: devolve uma nova lista com os mesmos objetos, IDs, proveniência,
scores e ordem do ranking. A antiga chave aproximada (`primeira entidade +
primeira tag`) não é tratada como `state_key`, e recência sozinha não apaga
histórico. Validade temporal e supersessão completa continuam experimentais.
### 4. Construção Dinâmica de Grafo e DW-PR (`tessera/engine.py`)
A classe core do sistema gerencia o ciclo de vida físico e lógico do grafo de memórias:

write_memory_note(): Invoca o gating de segurança, monta o frontmatter YAML, gera o arquivo .md estruturado no disco físico e mapeia a proveniência dos turnos de diálogo originais para garantir auditabilidade total [6, 12].
build_index(): Limpa a memória lógica e reconstrói o grafo do zero a partir da leitura direta do diretório. Extrai entidades e tags semânticas descritas no frontmatter YAML, criando nós abstratos interligados às notas físicas de destino (factual, preference, procedural_anchor).
retrieve_context(): Executa o fluxo de busca adaptativo inspirado no MemORAI [6]:
Busca Semântica Primal: Calcula a similaridade cosseno TF-IDF entre a consulta ativa e a representação textual de todos os nós para eleger os nós sementes.
Filtro do Subgrafo Local: Executa uma expansão de vizinhança direta de 1 salto (sucessores e predecessores) a partir dos nós sementes, isolando um subgrafo focado e descartando nós ruidosos do restante do sistema de arquivos [6].
Ponderação DW-PR: O peso de propagação das arestas é calculado de forma flutuante baseando-se na similaridade de cosseno com a intenção de consulta. Além disso, conexões com arestas procedimentais (como "stabilizes_service") recebem um multiplicador de boost de força (1.35) para priorizar diretrizes operacionais estáveis e robustas no ambiente [1, 2].
PageRank Personalizado: Computa a distribuição estacionária do PageRank com personalização focada nos pesos das similaridades dos nós semente, resultando nos melhores caminhos lógicos para o LAO.
## 🚀 Como Integrar o Tessera no Pipeline do LAO (Exemplo Conceitual)
Em produção no repositório do LAO, o motor do Tessera funciona associado a um pipeline de agentes que interagem para executar e monitorar tarefas. Abaixo está um exemplo prático de como conectar o indexador de memórias a um loop de agente em Python:

from tessera import TesseraEngine, Entity, Connection

class LAOAgent:
    def __init__(self, workspace_path: str):
        # Inicializa o motor de memória apontando para a pasta física de Markdown
        self.memory_engine = TesseraEngine(storage_dir=f"{workspace_path}/memories")
        self.memory_engine.build_index()

    def run_task(self, task_instruction: str):
        # 1. Recupera o contexto e preserva possíveis conflitos para inspeção
        retrieved_context = self.memory_engine.retrieve_context(
            query_text=task_instruction,
            top_n=3,
            resolve_conflicts=True
        )

        # 2. Concatena o contexto higienizado e as âncoras procedimentais ao prompt da IA
        prompt_addition = "\n--- CONTEXTO DE MEMÓRIA RECUPERADO (Tessera) ---\n"
        for mem in retrieved_context:
            prompt_addition += f"[{mem['type'].upper()} - ID: {mem['id']}]\n{mem['body']}\n\n"

        print("⚡ Injetando o seguinte contexto de longo prazo alinhado ao LAO:")
        print(prompt_addition)

        # [A IA Executa a tarefa aqui usando as ferramentas e âncoras procedimentais...]

        # 3. Consolida a nova experiência (se houver aprendizado crítico de preferência ou procedimento)
        # Exemplo: O usuário mudou de ideia durante a sessão
        self.memory_engine.write_memory_note(
            mem_id="mem_pref_003",
            mem_type="preference",
            episode_id="ep_010",
            content="Alex agora prefere que os relatórios sejam gerados estritamente em formato PDF.",
            tags=["relatorio", "pdf"],
            entities=[{"name": "Alex", "description": "Operador principal."}]
        )
        # Sincroniza o índice de grafos local
        self.memory_engine.build_index()
