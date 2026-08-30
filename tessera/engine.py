"""
TesseraEngine — the core of the Temporal Evolving State Synthesis with Explicit Relations and Atomic Memories system.

Integrates physical note persistence (Markdown + YAML frontmatter), the
heterogeneous knowledge graph index, Dynamic Weighted PageRank (DW-PR)
subgraph retrieval, and temporal conflict resolution.
"""

import datetime
import os
from typing import Any, Dict, List, Optional, Tuple

import networkx as nx
import numpy as np
import yaml
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .conflict import ConflictResolver
from .models import (
    NODE_TYPE_TO_STORE,
    STORE_FACTS,
    STORE_INSIGHTS,
    STORE_PREFERENCES,
    STORE_TO_NODE_TYPE,
    Connection,
    Entity,
    Episode,
    InvalidFrontmatterError,
    MemoryFrontmatter,
)
from .security import WriteGatingEngine

PROCEDURAL_RELATION_BOOST_TYPES = {
    "stabilizes_service",
    "standardizes_deployment",
    "generalization_of",
}
PROCEDURAL_RELATION_BOOST_FACTOR = 1.35
SEED_NODE_LIMIT = 30
SEED_NODE_MIN_SIMILARITY = 0.01
MEMORY_NODE_TYPES = {"factual", "preference", "procedural_anchor"}
FOREIGN_MEMORY_METADATA_TYPES = {
    "learning",
    "project",
    "reference",
    "user",
    "feedback",
    "experiment-result",
    "hypothesis",
    "governance",
    "pipeline",
}


class TesseraEngine:
    def __init__(self, storage_dir: str, weights: Optional[Dict[str, float]] = None):
        self.storage_dir = storage_dir
        self.graph = nx.DiGraph()
        self.file_registry: Dict[str, str] = {}
        self.node_corpus: Dict[str, str] = {}
        self.node_ids: List[str] = []
        self.tfidf_matrix = None
        self.vectorizer = TfidfVectorizer(token_pattern=r"(?u)\b\w+\b")
        self.gating_engine = WriteGatingEngine()
        self.weights = {
            "lexical_tfidf": 0.28,
            "lexical_overlap": 0.12,
            "title": 0.3,
            "metadata": 0.2,
            "relations": 0.1,
            "recency": 0.0,
        }
        if weights:
            self.weights.update(weights)
        self._today_provider = None
        if not os.path.exists(storage_dir):
            os.makedirs(storage_dir)
        self.index_cache_dir = os.path.join(storage_dir, ".tessera_index")
        self.index_cache_pkl = os.path.join(self.index_cache_dir, "graph.pkl")
        self.index_cache_json = os.path.join(self.index_cache_dir, "graph.json")

    def set_today_provider(self, provider: Any) -> None:
        self._today_provider = provider

    def get_today(self) -> datetime.date:
        if self._today_provider:
            return self._today_provider()
        return datetime.date.today()

    def write_memory_note(
        self,
        mem_id: str,
        mem_type: str,
        episode_id: str,
        content: str,
        tags: List[str],
        entities: List[Entity],
        description: str = "",
        provenance_turns: Optional[List[int]] = None,
        active_connections: Optional[List[Connection]] = None,
        persist_format: str = "md",
    ) -> str:
        if "/" not in mem_id.strip("/"):
            import warnings
            warnings.warn(
                f"write_memory_note: mem_id={mem_id!r} has no domain prefix "
                "(expected '<domain>/<slug>', e.g. 'research/some-topic/note' "
                "or 'lao/some-learning') - this note will be written loose at "
                "storage_dir's root instead of inside a topical subdirectory. "
                "This is very likely unintentional.",
                stacklevel=2,
            )
        provenance_turns = provenance_turns or []
        active_connections = active_connections or []
        sanitized_content, threat_score, is_sanitized = self.gating_engine.audit_and_sanitize(content, tags)
        gating_status = "flagged_and_sanitized" if threat_score > self.gating_engine.toxicity_threshold else "passed"
        now = datetime.datetime.now().astimezone().isoformat()
        frontmatter_data = MemoryFrontmatter(
            memory_id=mem_id,
            memory_type=mem_type,
            created_at=now,
            last_updated_at=now,
            episode_id=episode_id,
            description=description,
            provenance_turns=provenance_turns,
            tags=tags,
            entities=entities,
            active_connections=active_connections,
            gating_status=gating_status,
            toxicity_score=threat_score,
            sanitized=is_sanitized,
        )
        frontmatter_dict = frontmatter_data.to_dict()
        filepath_base = os.path.join(self.storage_dir, mem_id)
        os.makedirs(os.path.dirname(filepath_base) or self.storage_dir, exist_ok=True)
        if persist_format == "json":
            import json
            filepath = f"{filepath_base}.json"
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump({"frontmatter": frontmatter_dict, "body": sanitized_content.strip()}, f, indent=2, ensure_ascii=False)
        else:
            yaml_frontmatter = yaml.dump(frontmatter_dict, default_flow_style=False, sort_keys=False, allow_unicode=True)
            filepath = f"{filepath_base}.md"
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(f"---\n{yaml_frontmatter}---\n\n{sanitized_content.strip()}\n")
        self.file_registry[mem_id] = filepath
        return filepath

    def write_fact(self, mem_id: str, episode_id: str, content: str, tags=None, entities=None, active_connections=None) -> str:
        return self.write_memory_note(mem_id, "factual", episode_id, content, tags or [], entities or [], active_connections=active_connections)

    def write_preference(self, mem_id: str, episode_id: str, content: str, tags=None, entities=None, active_connections=None) -> str:
        return self.write_memory_note(mem_id, "preference", episode_id, content, tags or [], entities or [], active_connections=active_connections)

    def write_insight(self, mem_id: str, episode_id: str, content: str, tags=None, entities=None, active_connections=None) -> str:
        return self.write_memory_note(mem_id, "procedural_anchor", episode_id, content, tags or [], entities or [], active_connections=active_connections)

    def write_episode(self, mem_id: str, store: str, episode_id: str, episode: Episode, tags=None, entities=None, active_connections=None) -> str:
        if store not in STORE_TO_NODE_TYPE:
            raise ValueError(f"store inválida: {store!r}. Use STORE_FACTS, STORE_PREFERENCES ou STORE_INSIGHTS.")
        return self.write_memory_note(mem_id, STORE_TO_NODE_TYPE[store], episode_id, episode.to_markdown_body(), tags or [], entities or [], active_connections=active_connections)

    def decompose_and_write_episode(self, mem_id_prefix: str, episode_id: str, episode: Episode, llm_fn: Optional[Any] = None, tags=None) -> List[str]:
        from .decomposer import decompose_and_write
        return decompose_and_write(engine=self, mem_id_prefix=mem_id_prefix, episode_id=episode_id, episode=episode, llm_fn=llm_fn, tags=tags)

    def retrieve_from_store(self, query_text: str, store: str, top_n: int = 7, resolve_conflicts: bool = True) -> List[Dict[str, Any]]:
        if store not in STORE_TO_NODE_TYPE:
            raise ValueError(f"store inválida: {store!r}. Use STORE_FACTS, STORE_PREFERENCES ou STORE_INSIGHTS.")
        target_node_type = STORE_TO_NODE_TYPE[store]
        candidates = self.retrieve_context(query_text=query_text, top_n=max(top_n * 4, 12), resolve_conflicts=resolve_conflicts)
        return [m for m in candidates if m.get("type") == target_node_type][:top_n]

    def build_index(self, recursive: bool = True, use_cache: bool = True, persist: bool = True) -> None:
        if use_cache and self._load_index_if_fresh():
            return
        self.graph.clear(); self.file_registry.clear(); self.node_corpus.clear(); pending_connections = []
        if not os.path.exists(self.storage_dir):
            return
        for filepath in self._iter_markdown_files(recursive=recursive):
            filename = os.path.relpath(filepath, self.storage_dir)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    raw_text = f.read()
                frontmatter, body = self._parse_markdown(raw_text)
                frontmatter = self._normalize_frontmatter(frontmatter or {}, filepath)
                mem_id = frontmatter.get("id")
                if not mem_id:
                    continue
                if mem_id in self.graph:
                    mem_id = f"{mem_id}__{abs(hash(filepath)) % 10_000}"
                self.file_registry[mem_id] = filepath
                node_type = frontmatter.get("node_type", "factual")
                tags_str = " ".join(frontmatter.get("tags", []))
                entities_str = " ".join([e.get("name", "") for e in frontmatter.get("entities", [])])
                description = frontmatter.get("description", "") or ""
                self.node_corpus[mem_id] = f"{description} {body} {tags_str} {entities_str}"
                self.graph.add_node(mem_id, node_type=node_type, filepath=filepath, filename=filename, frontmatter=frontmatter, body=body)
                for ent in frontmatter.get("entities", []):
                    ent_name = ent.get("name")
                    if not ent_name:
                        continue
                    ent_id = f"ent_{ent_name.lower().replace(' ', '_')}"
                    if ent_id not in self.graph:
                        self.graph.add_node(ent_id, node_type="entity", name=ent_name, description=ent.get("description", ""))
                        self.node_corpus[ent_id] = f"{ent_name}: {ent.get('description', '')}"
                    self.graph.add_edge(mem_id, ent_id, relation_type="mentions")
                for tag in frontmatter.get("tags", []):
                    tag_id = f"tag_{tag.lower()}"
                    if tag_id not in self.graph:
                        self.graph.add_node(tag_id, node_type="tag", tag_name=tag)
                        self.node_corpus[tag_id] = f"Tag: {tag}"
                    self.graph.add_edge(mem_id, tag_id, relation_type="tagged_with")
                for conn in frontmatter.get("active_connections", []):
                    pending_connections.append((mem_id, conn.get("target_memory_id"), conn.get("relation_type")))
            except Exception as e:
                print(f"[Aviso] Falha ao processar a nota física {filename}: {e}")
        for src, dest, rel in pending_connections:
            if src in self.graph and dest in self.graph:
                self.graph.add_edge(src, dest, relation_type=rel)
        if self.node_corpus:
            self.node_ids = list(self.node_corpus.keys())
            self.tfidf_matrix = self.vectorizer.fit_transform([self.node_corpus[nid] for nid in self.node_ids])
        if persist:
            self.save_index()

    def _source_fingerprint(self) -> Tuple[int, float]:
        count = 0; latest_mtime = 0.0
        for filepath in self._iter_markdown_files(recursive=True):
            count += 1
            try: latest_mtime = max(latest_mtime, os.path.getmtime(filepath))
            except OSError: pass
        return count, latest_mtime

    def save_index(self) -> None:
        import json, pickle
        os.makedirs(self.index_cache_dir, exist_ok=True)
        snapshot = {"storage_dir": os.path.abspath(self.storage_dir), "fingerprint": self._source_fingerprint(), "graph": self.graph, "file_registry": self.file_registry, "node_corpus": self.node_corpus, "node_ids": self.node_ids, "tfidf_matrix": self.tfidf_matrix, "vectorizer": self.vectorizer}
        with open(self.index_cache_pkl, "wb") as f: pickle.dump(snapshot, f)
        readable = {"storage_dir": os.path.abspath(self.storage_dir), "generated_at": datetime.datetime.now().astimezone().isoformat(), "num_nodes": self.graph.number_of_nodes(), "num_edges": self.graph.number_of_edges(), "nodes": {node_id: {"node_type": data.get("node_type"), "filepath": data.get("filepath"), "tags": data.get("frontmatter", {}).get("tags", []) if data.get("frontmatter") else None} for node_id, data in self.graph.nodes(data=True)}}
        with open(self.index_cache_json, "w", encoding="utf-8") as f: json.dump(readable, f, indent=2, ensure_ascii=False)

    def _load_index_if_fresh(self) -> bool:
        import pickle
        if not os.path.exists(self.index_cache_pkl): return False
        try:
            with open(self.index_cache_pkl, "rb") as f: snapshot = pickle.load(f)
        except Exception: return False
        if snapshot.get("fingerprint") != self._source_fingerprint(): return False
        self.graph = snapshot["graph"]; self.file_registry = snapshot["file_registry"]; self.node_corpus = snapshot["node_corpus"]; self.node_ids = snapshot["node_ids"]; self.tfidf_matrix = snapshot["tfidf_matrix"]; self.vectorizer = snapshot["vectorizer"]
        return True

    def _iter_markdown_files(self, recursive: bool):
        scan_dirs = [self.storage_dir]; individual_files = []; roots = [os.getcwd()]
        try:
            roots.append(os.path.dirname(os.path.dirname(os.path.abspath(self.storage_dir))))
        except Exception: pass
        seen_roots = set(); unique_roots = []
        for r in roots:
            abs_r = os.path.abspath(r)
            if abs_r not in seen_roots:
                seen_roots.add(abs_r); unique_roots.append(abs_r)
        for root in unique_roots:
            storage_dir_abs = os.path.abspath(self.storage_dir); root_abs = os.path.abspath(root)
            if storage_dir_abs.startswith(root_abs):
                for folder in ["experiments", "newsletters", "docs"]:
                    path = os.path.join(root, folder)
                    if os.path.isdir(path) and os.path.abspath(path) not in [os.path.abspath(d) for d in scan_dirs]: scan_dirs.append(os.path.abspath(path))
                try:
                    for filename in os.listdir(root):
                        if filename.endswith(".md"):
                            p = os.path.abspath(os.path.join(root, filename))
                            if p not in individual_files: individual_files.append(p)
                except Exception: pass
        for s_dir in scan_dirs:
            if recursive:
                for root, dirs, files in os.walk(s_dir):
                    dirs[:] = [d for d in dirs if d not in (".tessera_index", ".git", "node_modules", "venv", ".venv-browser-agent", ".browser-harness", "Tessera")]
                    for filename in files:
                        if filename.endswith(".md"): yield os.path.join(root, filename)
            else:
                try:
                    for filename in os.listdir(s_dir):
                        if filename.endswith(".md"): yield os.path.join(s_dir, filename)
                except Exception: pass
        for filepath in individual_files:
            if os.path.exists(filepath): yield filepath

    def _normalize_frontmatter(self, frontmatter: Dict[str, Any], filepath: str) -> Dict[str, Any]:
        if "id" in frontmatter and "node_type" in frontmatter: return frontmatter
        normalized = dict(frontmatter)
        name = normalized.get("name")
        if isinstance(name, list): name = name[0] if name else None
        if not name: name = os.path.splitext(os.path.basename(filepath))[0]
        normalized["id"] = str(name)
        metadata = normalized.get("metadata"); meta_type = metadata.get("type") if isinstance(metadata, dict) else None
        node_type_map = {"user": "preference", "feedback": "preference", "reference": "factual", "hypothesis": "factual", "experiment-result": "factual", "governance": "procedural_anchor", "pipeline": "procedural_anchor", "learning": "procedural_anchor", "project": "factual"}
        filename_lower = os.path.basename(filepath).lower()
        fallback_type = "procedural_anchor" if any(x in filename_lower for x in ("claude.md", "gemini.md", "agents.md", "agentes.md", "instruction", "rule", "convention", "guide")) else "factual"
        normalized["node_type"] = node_type_map.get(meta_type, fallback_type)
        tags = list(normalized.get("tags") or [])
        if isinstance(metadata, dict):
            for key in ("category", "phase", "topic", "type"):
                val = metadata.get(key)
                if isinstance(val, str) and val not in tags: tags.append(val)
        normalized["tags"] = tags
        normalized.setdefault("entities", []); normalized.setdefault("active_connections", [])
        if isinstance(metadata, dict):
            related_to = metadata.get("related_to")
            if isinstance(related_to, list) and not normalized["active_connections"]:
                seen = set()
                for target in related_to:
                    if isinstance(target, str) and target.strip() and target.strip() not in seen:
                        target = target.strip(); seen.add(target)
                        normalized["active_connections"].append({"target_memory_id": target, "relation_type": "related_to", "cosine_similarity": 0.0})
        return normalized

    def retrieve_context(self, query_text: str, top_n: int = 7, resolve_conflicts: bool = True, weights: Optional[Dict[str, float]] = None) -> List[Dict[str, Any]]:
        if not self.graph or not self.node_corpus or self.tfidf_matrix is None: return []
        import re, math
        query_vec = self.vectorizer.transform([query_text]); similarities = cosine_similarity(query_vec, self.tfidf_matrix).flatten(); sorted_indices = np.argsort(similarities)[::-1]
        seed_nodes = []; seed_similarities = {}
        for idx in sorted_indices[:SEED_NODE_LIMIT]:
            if similarities[idx] > SEED_NODE_MIN_SIMILARITY:
                nid = self.node_ids[idx]; seed_nodes.append(nid); seed_similarities[nid] = similarities[idx]
        if not seed_nodes: return []
        subgraph_nodes = set(seed_nodes)
        for seed in seed_nodes:
            subgraph_nodes.update(self.graph.successors(seed)); subgraph_nodes.update(self.graph.predecessors(seed))
        subgraph = self.graph.subgraph(subgraph_nodes).copy(); all_sub_nodes = list(subgraph.nodes()); sub_texts = [self.node_corpus.get(nid, "") for nid in all_sub_nodes]; sub_vecs = self.vectorizer.transform(sub_texts); sub_sims = cosine_similarity(query_vec, sub_vecs).flatten(); node_sim_map = dict(zip(all_sub_nodes, sub_sims))
        for u, v in list(subgraph.edges()):
            relation_boost = PROCEDURAL_RELATION_BOOST_FACTOR if subgraph[u][v].get("relation_type", "") in PROCEDURAL_RELATION_BOOST_TYPES else 1.0
            subgraph[u][v]["weight"] = max(0.01, float((node_sim_map.get(v, 0.0) + 0.1) * relation_boost))
        try:
            personalization = {nid: seed_similarities.get(nid, 0.0) for nid in subgraph.nodes()}; p_sum = sum(personalization.values()); personalization = {k: v / p_sum for k, v in personalization.items()} if p_sum > 0 else None
            pagerank_scores = nx.pagerank(subgraph, alpha=0.85, weight="weight", personalization=personalization)
        except Exception:
            pagerank_scores = nx.pagerank(subgraph, alpha=0.85, weight="weight")
        retrieved_memories = []
        memory_pageranks = [pagerank_scores.get(nid, 0.0) for nid in pagerank_scores if nid in self.graph.nodes and self.graph.nodes[nid].get("node_type") in MEMORY_NODE_TYPES]
        max_pagerank = max(memory_pageranks) if memory_pageranks else 1.0
        weights_used = dict(self.weights); weights_used.update(weights or {})
        query_tokens = set(re.findall(r"\b\w+\b", query_text.lower())); query_clean = " ".join(re.findall(r"\b\w+\b", query_text.lower()))
        for node_id, pr_score in pagerank_scores.items():
            if node_id not in self.graph.nodes: continue
            node_data = self.graph.nodes[node_id]; node_type = node_data.get("node_type")
            if node_type not in MEMORY_NODE_TYPES: continue
            related_ids = sorted({nb for nb in set(self.graph.successors(node_id)) | set(self.graph.predecessors(node_id)) if nb != node_id and self.graph.nodes[nb].get("node_type") in MEMORY_NODE_TYPES})
            raw_tfidf = float(node_sim_map.get(node_id, 0.0)); body_text = node_data.get("body", ""); body_tokens = set(re.findall(r"\b\w+\b", body_text.lower())); term_overlap = len(query_tokens & body_tokens) / max(1, len(query_tokens))
            clean_id_tokens = set(re.findall(r"\b\w+\b", node_id.lower().replace("/", " ").replace("-", " ").replace("_", " "))); title_score = len(query_tokens & clean_id_tokens) / max(1, len(query_tokens))
            fm = node_data.get("frontmatter", {}); tags = [str(t).lower() for t in fm.get("tags", [])]; entity_names = [str(e.get("name", "")).lower() for e in fm.get("entities", []) if isinstance(e, dict)]; metadata_tokens = set()
            for tag in tags: metadata_tokens.update(re.findall(r"\b\w+\b", tag))
            for ent_name in entity_names: metadata_tokens.update(re.findall(r"\b\w+\b", ent_name))
            metadata_score = len(query_tokens & metadata_tokens) / max(1, len(query_tokens)); normalized_relations = pr_score / max_pagerank if max_pagerank > 0 else 0.0
            is_procedural_intent = any(tk in query_tokens for tk in ("como", "procedimento", "fluxo", "passo", "tutorial", "deploy", "configurar", "setup", "erro", "bug", "how")) or "como fazer" in query_clean or "how to" in query_clean
            is_preference_intent = any(tk in query_tokens for tk in ("prefere", "gosto", "comportamento", "estilo", "feedback", "tom", "preferência", "preferencia")) or "comportamento do" in query_clean
            is_factual_intent = any(tk in query_tokens for tk in ("fato", "fact", "quem", "quando", "onde", "valor", "endpoint", "versão", "versao", "id", "nome", "name"))
            type_boost = 1.3 if node_type == "procedural_anchor" and is_procedural_intent else 1.3 if node_type == "preference" and is_preference_intent else 1.2 if node_type == "factual" and is_factual_intent else 1.0
            recency_raw_score = 1.0; date_str = fm.get("last_updated_at") or fm.get("created_at") or fm.get("date")
            if date_str:
                try:
                    dt = datetime.datetime.strptime(str(date_str)[:10], "%Y-%m-%d").date(); days = (self.get_today() - dt).days; recency_raw_score = 1.1 if days <= 0 else 1.0 + 0.1 * math.exp(-days / 60.0)
                except Exception: pass
            recency_weight = float(weights_used.get("recency", 0.0)); recency_applied_multiplier = recency_raw_score if recency_weight > 0.0 else 1.0
            base_relevance = weights_used.get("lexical_tfidf", 0.28) * raw_tfidf + weights_used.get("lexical_overlap", 0.12) * term_overlap + weights_used.get("title", 0.3) * title_score + weights_used.get("metadata", 0.2) * metadata_score + weights_used.get("relations", 0.1) * normalized_relations
            final_score = base_relevance * type_boost * recency_applied_multiplier
            paragraphs = [p.strip() for p in re.split(r"\n\s*\n", body_text) if p.strip()] or [line.strip() for line in body_text.splitlines() if line.strip()]
            relevant_evidence = None; evidence_info = None
            if paragraphs:
                best_para_score = -1.0; best_para = None
                for p in paragraphs:
                    p_tokens = set(re.findall(r"\b\w+\b", p.lower())); overlap = len(query_tokens & p_tokens); jaccard = overlap / len(query_tokens | p_tokens) if (query_tokens | p_tokens) else 0.0; para_score = overlap + jaccard
                    if para_score > best_para_score: best_para_score = para_score; best_para = p
                if best_para and best_para_score >= 1.0:
                    relevant_evidence = best_para; evidence_info = {"text": relevant_evidence, "score": float(best_para_score), "strategy": "paragraph_lexical"}
            retrieved_memories.append({"id": node_id, "type": node_type, "filepath": node_data.get("filepath"), "filename": node_data.get("filename"), "score": float(final_score), "score_explain": {"lexical_tfidf": float(raw_tfidf), "lexical_overlap": float(term_overlap), "lexical_score": float(raw_tfidf * 0.7 + term_overlap * 0.3), "title": float(title_score), "metadata": float(metadata_score), "raw_pagerank": float(pr_score), "normalized_relations": float(normalized_relations), "relations_contribution": float(normalized_relations * weights_used.get("relations", 0.1)), "type_boost": float(type_boost), "recency_raw_score": float(recency_raw_score), "recency_weight": recency_weight, "recency_applied_multiplier": float(recency_applied_multiplier), "recency_contribution": float(recency_applied_multiplier - 1.0), "recency_boost": float(recency_applied_multiplier)}, "relevant_evidence": relevant_evidence, "evidence_info": evidence_info, "body": body_text.strip(), "frontmatter": fm, "related_ids": related_ids})
        retrieved_memories.sort(key=lambda x: x["score"], reverse=True)
        if resolve_conflicts:
            retrieved_memories = ConflictResolver.resolve_temporal_conflicts(retrieved_memories); retrieved_memories.sort(key=lambda x: x["score"], reverse=True)
        return retrieved_memories[:top_n]

    def _parse_markdown(self, raw_text: str) -> Tuple[Optional[Dict[str, Any]], str]:
        text = raw_text.strip()
        if not text.startswith("---"): return None, raw_text
        parts = text.split("---", 2)
        if len(parts) >= 3:
            try: return yaml.safe_load(parts[1]), parts[2]
            except yaml.YAMLError:
                repaired = self._repair_frontmatter_yaml(parts[1])
                try: return yaml.safe_load(repaired), parts[2]
                except Exception as e: raise InvalidFrontmatterError(f"YAML parsing error: {e}") from e
        return None, raw_text

    @staticmethod
    def _repair_frontmatter_yaml(frontmatter_raw: str) -> str:
        import re
        fixed_lines = []; key_line_re = re.compile(r"^(\s*)([A-Za-z0-9_]+):\s+(.*)$")
        for line in frontmatter_raw.splitlines():
            match = key_line_re.match(line)
            if not match: fixed_lines.append(line); continue
            indent, key, value = match.groups(); stripped = value.strip(); starts_quoted_with_trailer = len(stripped) > 1 and stripped[0] in "\"'" and not (stripped.endswith(stripped[0]) and stripped.count(stripped[0]) == 2)
            looks_like_nested_or_safe = (not stripped or stripped.startswith(("-", "[", "{")) or (stripped.startswith(("\"", "'")) and not starts_quoted_with_trailer) or ":" not in stripped) and not starts_quoted_with_trailer
            if looks_like_nested_or_safe: fixed_lines.append(line); continue
            fixed_lines.append(f'{indent}{key}: "{stripped.replace(chr(34), chr(92)+chr(34))}"')
        return "\n".join(fixed_lines)
