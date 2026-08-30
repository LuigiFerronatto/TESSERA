import os
import re
import yaml
import networkx as nx
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

class MemoryGraphIndex:
    """
    Indexador de Memória Baseado em Grafo de Conhecimento Heterogêneo.
    Inspirado nos conceitos de:
    - QUMem (Invocação de agentes com busca condicionada por tipo de memória)
    - MemORAI (Dynamic Weighted PageRank e expansão de vizinhança adaptativa)
    - State Contamination (Prevenção de poluição de estado cognitivo)
    """

    def __init__(self):
        self.graph = nx.DiGraph()
        self.file_registry = {}  # Mapeia memory_id -> caminho do arquivo .md
        self.node_corpus = {}    # Mapeia node_id -> descrição em texto para busca semântica
        self.vectorizer = TfidfVectorizer()

    def load_from_directory(self, directory_path):
        """
        Varre um diretório buscando arquivos .md, extrai o YAML Frontmatter e reconstrói 
        o grafo de conhecimento heterogêneo de forma incremental.
        """
        if not os.path.exists(directory_path):
            raise FileNotFoundError(f"Diretório não encontrado: {directory_path}")

        # Fila temporária para criar conexões entre notas após todos os nós estarem declarados
        pending_connections = []

        for filename in os.listdir(directory_path):
            if not filename.endswith(".md"):
                continue
            
            filepath = os.path.join(directory_path, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                raw_text = f.read()

            # Processa o frontmatter e o corpo markdown
            frontmatter, body = self._parse_markdown(raw_text)
            if not frontmatter:
                continue

            mem_id = frontmatter.get("id") or frontmatter.get("memory_id")
            if not mem_id:
                continue

            self.file_registry[mem_id] = filepath
            node_type = frontmatter.get("node_type") or frontmatter.get("memory_type", "factual")
            
            # Texto unificado do nó usado para o cálculo de similaridade cosseno (TF-IDF)
            node_text = f"{body} " + " ".join(frontmatter.get("tags", []))
            self.node_corpus[mem_id] = node_text

            # 1. Adiciona o nó principal da nota de memória
            self.graph.add_node(
                mem_id, 
                node_type=node_type, 
                filepath=filepath,
                title=filename,
                frontmatter=frontmatter,
                body=body
            )

            # 2. Registra as entidades do frontmatter no grafo
            for entity in frontmatter.get("entities", []):
                ent_name = entity.get("name")
                ent_desc = entity.get("description", "")
                ent_id = f"ent_{ent_name.lower().replace(' ', '_')}"
                
                if ent_id not in self.graph:
                    self.graph.add_node(ent_id, node_type="entity", name=ent_name, description=ent_desc)
                    self.node_corpus[ent_id] = f"{ent_name}: {ent_desc}"
                
                # Conecta a nota de memória ao nó da entidade (direcionado)
                self.graph.add_edge(mem_id, ent_id, relation_type="mentions")

            # 3. Registra as tags do frontmatter no grafo
            for tag in frontmatter.get("tags", []):
                tag_id = f"tag_{tag.lower()}"
                if tag_id not in self.graph:
                    self.graph.add_node(tag_id, node_type="tag", tag_name=tag)
                    self.node_corpus[tag_id] = f"Tag: {tag}"
                
                self.graph.add_edge(mem_id, tag_id, relation_type="tagged_with")

            # Armazena as conexões cruzadas do frontmatter para construir no final
            for conn in frontmatter.get("active_connections", []):
                pending_connections.append((mem_id, conn.get("target_memory_id"), conn.get("relation_type")))

        # Estabelece as conexões de relacionamento ativo (active_connections)
        for source_id, target_id, relation in pending_connections:
            if source_id in self.graph and target_id in self.graph:
                self.graph.add_edge(source_id, target_id, relation_type=relation)

        # Treina o vetorizador TF-IDF com todas as representações textuais dos nós
        if self.node_corpus:
            self.node_ids = list(self.node_corpus.keys())
            corpus_texts = [self.node_corpus[nid] for nid in self.node_ids]
            self.tfidf_matrix = self.vectorizer.fit_transform(corpus_texts)

    def query(self, query_text, top_n=3):
        """
        Executa a busca adaptativa baseada em subgrafos em duas etapas:
        1. Identifica os nós sementes com base na similaridade cosseno TF-IDF.
        2. Expande para um subgrafo focado de 1-hop.
        3. Calcula dinamicamente os pesos de propagação das arestas (DW-PR).
        4. Executa PageRank com personalização nos nós sementes.
        """
        if not self.graph or not self.node_corpus:
            return []

        # Etapa 1: Calcular similaridade da busca com o corpus de nós
        query_vec = self.vectorizer.transform([query_text])
        similarities = cosine_similarity(query_vec, self.tfidf_matrix).flatten()
        sorted_indices = np.argsort(similarities)[::-1]
        
        seed_nodes = []
        seed_similarities = {}
        for idx in sorted_indices[:5]:
            if similarities[idx] > 0.05:  # Filtro de corte mínimo de relevância
                nid = self.node_ids[idx]
                seed_nodes.append(nid)
                seed_similarities[nid] = similarities[idx]

        if not seed_nodes:
            return []

        # Etapa 2: Expansão de vizinhança de 1-hop para construir o Subgrafo Focado
        subgraph_nodes = set(seed_nodes)
        for seed in seed_nodes:
            subgraph_nodes.update(self.graph.successors(seed))
            subgraph_nodes.update(self.graph.predecessors(seed))

        subgraph = self.graph.subgraph(subgraph_nodes).copy()

        # Etapa 3: Ponderação Dinâmica de Arestas (Dynamic Weighted PageRank)
        all_sub_nodes = list(subgraph.nodes())
        sub_texts = [self.node_corpus.get(nid, "") for nid in all_sub_nodes]
        sub_vecs = self.vectorizer.transform(sub_texts)
        sub_sims = cosine_similarity(query_vec, sub_vecs).flatten()
        node_sim_map = dict(zip(all_sub_nodes, sub_sims))

        for u, v in list(subgraph.edges()):
            target_similarity = node_sim_map.get(v, 0.0)
            relation_type = subgraph[u][v].get("relation_type", "")
            
            # Impulsiona o peso para conexões procedimentais ou de alinhamento crítico
            relation_boost = 1.3 if relation_type in ["standardizes_deployment", "stabilizes_service"] else 1.0
            
            # Calcula o peso com base na similaridade do nó de destino
            dynamic_weight = (target_similarity + 0.1) * relation_boost
            subgraph[u][v]['weight'] = max(0.01, float(dynamic_weight))

        # Etapa 4: Executar PageRank com personalização (DW-PR)
        try:
            personalization = {nid: seed_similarities.get(nid, 0.0) for nid in subgraph.nodes()}
            pers_sum = sum(personalization.values())
            if pers_sum > 0:
                personalization = {k: v / pers_sum for k, v in personalization.items()}
            else:
                personalization = None

            pagerank_scores = nx.pagerank(
                subgraph, 
                alpha=0.85, 
                weight='weight', 
                personalization=personalization
            )
        except Exception:
            pagerank_scores = nx.pagerank(subgraph, alpha=0.85, weight='weight')

        # Etapa 5: Filtra as notas físicas de memória candidatas a serem injetadas no contexto da IA
        retrieved_memories = []
        for node_id, score in pagerank_scores.items():
            node_data = self.graph.nodes[node_id]
            node_type = node_data.get("node_type")
            
            # Apenas memórias reais (.md) devem ser injetadas, não nós abstratos de tags/entidades
            if node_type in ["factual", "preference", "procedural_anchor"]:
                retrieved_memories.append({
                    "id": node_id,
                    "type": node_type,
                    "filepath": node_data.get("filepath"),
                    "title": node_data.get("title"),
                    "score": float(score),
                    "body": node_data.get("body", "").strip()
                })

        # Ordena as memórias com base no score consolidado do PageRank Dinâmico
        retrieved_memories.sort(key=lambda x: x["score"], reverse=True)
        return retrieved_memories[:top_n]

    def _parse_markdown(self, raw_text):
        """Utilitário interno para extração de frontmatter YAML e corpo de texto."""
        match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", raw_text, re.DOTALL)
        if match:
            frontmatter_raw = match.group(1)
            body = match.group(2)
            try:
                frontmatter = yaml.safe_load(frontmatter_raw)
                return frontmatter, body
            except Exception as e:
                print(f"Erro ao parsear o YAML Frontmatter: {e}")
                return None, raw_text
        return None, raw_text

# Bloco de Demonstração Interativo de Inicialização
if __name__ == "__main__":
    import tempfile
    
    # Criamos um diretório temporário para simular nossa pasta física de notas de memórias .md
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"--- Iniciando Simulação do Sistema em: {temp_dir} ---")
        
        # Criação de notas Mock Markdown no diretório
        mem_factual_content = """---
id: mem_fact_01
memory_type: factual
tags: [python, postgresql, backend]
entities:
  - name: Maria
    description: Desenvolvedora líder de arquitetura e infraestrutura de banco de dados.
active_connections:
  - target_memory_id: sk_deploy_db
    relation_type: standardizes_deployment
---
A engenheira Maria configurou com sucesso a replicação de leitura do PostgreSQL no servidor secundário.
"""
        
        mem_procedural_content = """---
id: sk_deploy_db
node_type: procedural_anchor
tags: [postgresql, devops, backup]
entities:
  - name: PostgreSQL
    description: Banco de dados relacional oficial utilizado em produção.
active_connections: []
---
### Procedimento de Instanciação e Backup do PostgreSQL
1. Validar se a porta 5432 não possui serviços concorrentes escutando.
2. Iniciar o serviço do postgres usando 'systemctl start postgresql'.
3. Gerar dump de segurança de tabelas críticas por meio de pg_dump.
"""

        # Escrevendo as notas físicas (.md)
        with open(os.path.join(temp_dir, "maria_postgresql_fact.md"), "w", encoding="utf-8") as f:
            f.write(mem_factual_content)
        with open(os.path.join(temp_dir, "sk_deploy_db.md"), "w", encoding="utf-8") as f:
            f.write(mem_procedural_content)
            
        # Carregando as notas para o indexador
        index = MemoryGraphIndex()
        index.load_from_directory(temp_dir)
        
        # Query de teste
        query_teste = "Preciso de um passo a passo para restaurar e subir o banco PostgreSQL da Maria"
        print(f"Query executada: '{query_teste}'\n")
        
        results = index.query(query_teste, top_n=2)
        for i, res in enumerate(results, 1):
            print(f"Rank {i} | Tipo: {res['type'].upper()} | ID: {res['id']} | Score: {res['score']:.4f}")
            print(f"Caminho do Arquivo: {res['title']}")
            print(f"Conteúdo:\n{res['body']}")
            print("-" * 60)
