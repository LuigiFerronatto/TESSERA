"""
TesseraEngine — the core of the Temporal Evolving State Synthesis with Explicit Relations and Atomic Memories system.

Integrates physical note persistence (Markdown + YAML frontmatter), the
heterogeneous knowledge graph index, Dynamic Weighted PageRank (DW-PR)
subgraph retrieval, and temporal conflict resolution.
"""

import datetime
import os
from typing import Any, Dict, List, Literal, Optional, Tuple

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

# Relation types that receive a retrieval boost — they anchor procedural
# stability (skills that stabilize a service/deployment/generalization).
PROCEDURAL_RELATION_BOOST_TYPES = {
    "stabilizes_service",
    "standardizes_deployment",
    "generalization_of",
}
PROCEDURAL_RELATION_BOOST_FACTOR = 1.35

# How many top TF-IDF matches to consider as seed nodes for subgraph expansion.
# Kept wide (30, not 5) so dense, highly-similar note sets — e.g. dozens of
# evolving preference notes about the same topic — don't get truncated before
# the ConflictResolver ever sees the full temporal history.
SEED_NODE_LIMIT = 30
SEED_NODE_MIN_SIMILARITY = 0.01

MEMORY_NODE_TYPES = {"factual", "preference", "procedural_anchor"}

# Tessera's native schema expects `id` / `node_type` / `tags` / `entities`.
# Some external corpora (e.g. LAO's own `.claude/memory/`) use a different,
# equally valid frontmatter shape: `name` / `description` / `metadata.type`.
# These are the `metadata.type` values recognized as indexable memory notes
# when a file uses that "foreign" schema instead of Tessera's native one.
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

# Tessera's native schema expects `id` / `node_type` / `tags` / `entities`.
# Some external corpora (e.g. LAO's own `.claude/memory/`) use a different,
# equally valid frontmatter shape: `name` / `description` / `metadata.type`.
# These are the `metadata.type` values recognized as indexable memory notes
# when a file uses that "foreign" schema instead of Tessera's native one.
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
    """
    Core Tessera search engine: ties together physical note ingestion, graph
    construction, DW-PR-weighted subgraph search, and write-side management.
    """

    def __init__(self, storage_dir: str, weights: Optional[Dict[str, float]] = None):
        self.storage_dir = storage_dir
        self.graph = nx.DiGraph()
        self.file_registry: Dict[str, str] = {}
        self.node_corpus: Dict[str, str] = {}
        self.node_ids: List[str] = []
        self.tfidf_matrix = None
        self.vectorizer = TfidfVectorizer(token_pattern=r"(?u)\b\w+\b")
        self.gating_engine = WriteGatingEngine()
        
        # Default weights for Multi-Signal Scoring (F10)
        self.weights = {
            "lexical_tfidf": 0.28,    # 0.7 of 0.4
            "lexical_overlap": 0.12,  # 0.3 of 0.4
            "title": 0.3,
            "metadata": 0.2,
            "relations": 0.1,
            "recency": 0.0,           # Recency is disabled by default (weight 0.0) in default ranking
        }
        if weights:
            self.weights.update(weights)
            
        self._today_provider = None

        if not os.path.exists(storage_dir):
            os.makedirs(storage_dir)

        # On-disk index cache: lives *inside* storage_dir so the graph
        # persists across CLI invocations instead of being rebuilt (and
        # discarded) in-memory every single time. Never mixed in with the
        # user's own memory notes (kept in a dedicated subfolder that
        # `_iter_markdown_files` explicitly skips).
        self.index_cache_dir = os.path.join(storage_dir, ".tessera_index")
        self.index_cache_pkl = os.path.join(self.index_cache_dir, "graph.pkl")
        self.index_cache_json = os.path.join(self.index_cache_dir, "graph.json")
        self.manifest_path = os.path.join(self.index_cache_dir, "identity_manifest.json")
        self.identity_manifest = self._load_identity_manifest()

    def set_today_provider(self, provider: Any) -> None:
        """Injects a custom provider to fetch 'today's date for determinism in testing."""
        self._today_provider = provider

    def get_today(self) -> datetime.date:
        """Resolves today's date, using the injected provider if any, else real today."""
        if self._today_provider:
            return self._today_provider()
        return datetime.date.today()

    def _load_identity_manifest(self) -> Dict[str, Any]:
        """Loads the stable identity manifest from disk."""
        if os.path.exists(self.manifest_path):
            try:
                import json
                with open(self.manifest_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_identity_manifest(self) -> None:
        """Saves the stable identity manifest to disk."""
        os.makedirs(os.path.dirname(self.manifest_path), exist_ok=True)
        try:
            import json
            with open(self.manifest_path, "w", encoding="utf-8") as f:
                json.dump(self.identity_manifest, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def _resolve_persistent_id(self, filepath: str, raw_text: str) -> Tuple[str, str]:
        """Resolves or generates both persistent memory ID and stable document ID."""
        import posixpath
        import re
        rel_path = os.path.relpath(filepath, self.storage_dir).replace(os.sep, "/")
        
        # 1. First, check if there is an explicit ID in the frontmatter
        from .canonical import _split_markdown, compute_sha256
        frontmatter, body = _split_markdown(raw_text)
        explicit_id = frontmatter.get("id") or frontmatter.get("memory_id")
        
        # 2. Extract content hash
        content_hash = compute_sha256(body)
        
        # 3. Look up in identity manifest by path
        if rel_path in self.identity_manifest:
            entry = self.identity_manifest[rel_path]
            mem_id = explicit_id or entry["id"]
            doc_id = entry.get("document_id") or f"doc_{compute_sha256(rel_path)[:12]}"
            return str(mem_id).strip(), doc_id
            
        # 4. Look up in identity manifest by content_hash to detect Rename/Move! (F5)
        # Verify old path no longer exists on disk to distinguish rename from copy/duplicates (F5)
        candidates = []
        for path, entry in self.identity_manifest.items():
            if entry["content_hash"] == content_hash:
                full_old_path = os.path.join(self.storage_dir, path.replace("/", os.sep))
                if not os.path.exists(full_old_path):
                    candidates.append((path, entry))
                    
        if len(candidates) == 1:
            # Unambiguous move/rename detected!
            old_path, entry = candidates[0]
            mem_id = explicit_id or entry["id"]
            doc_id = entry.get("document_id") or f"doc_{compute_sha256(old_path)[:12]}"
            return str(mem_id).strip(), doc_id
            
        # 5. Not found -> generate a new stable ID (clean path slug based)
        if explicit_id:
            mem_id = str(explicit_id).strip()
        else:
            slug = os.path.splitext(rel_path)[0]
            slug = re.sub(r'^\.+/', '', slug)
            slug = re.sub(r'/+', '/', slug)
            mem_id = slug.strip("/")
            
        doc_id = f"doc_{compute_sha256(rel_path)[:12]}"
        return mem_id, doc_id

    def _update_identity_manifest(self, filepath: str, canonical_meta: Any) -> None:
        """Updates the stable identity manifest with a parsed document's metadata."""
        rel_path = os.path.relpath(filepath, self.storage_dir).replace(os.sep, "/")
        stable_id = canonical_meta.identity.id
        doc_id = canonical_meta.source.document_id
        
        # Remove any stale path references sharing the same ID (Move detection)
        old_paths = [p for p, entry in self.identity_manifest.items() if entry["id"] == stable_id and p != rel_path]
        for old_p in old_paths:
            del self.identity_manifest[old_p]
            
        self.identity_manifest[rel_path] = {
            "id": stable_id,
            "document_id": doc_id,
            "content_hash": canonical_meta.source.content_hash,
            "updated_at": datetime.datetime.now().isoformat()
        }

    # ------------------------------------------------------------------
    # Write path
    # ------------------------------------------------------------------
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
        persist_format: Literal["md"] = "md",
    ) -> str:
        """
        Secure, incremental write flow:
        1. Validates the Markdown-only persistence contract before side effects.
        2. Runs security audit + sanitization (write-side gating).
        3. Formats the note as an atomic card (Markdown + YAML frontmatter).
        4. Persists it physically to disk.
        5. Returns the generated file path.

        ``persist_format`` accepts exactly ``"md"``. Any other value raises
        ``ValueError`` before warnings, sanitization, timestamps, frontmatter,
        filesystem writes, registry/graph updates, index rebuilds, or Evidence
        Ledger updates. Arbitrary JSON persistence/ingestion is not supported.

        `mem_id` SHOULD carry a domain prefix ("<domain>/<slug>", e.g.
        "research/browser-actions/thesis" or "lao/some-learning") so the
        note lands inside a topical subdirectory of storage_dir instead of
        loose at its root. A bare, unprefixed mem_id (no "/" at all) is
        accepted — writing must never hard-fail an autonomous run over a
        naming nit — but is a near-certain sign the caller (an LLM agent
        following a system prompt, most often) skipped that convention.
        Confirmed live 2026-08-25/26: a Gemini-driven `/lao` run wrote
        mem_id="voice-ai-blip-integration-strategy" with no prefix at all
        and the note silently landed at .claude/memory/'s own root, next to
        MEMORY.md/README.md/STRUCTURE.md, instead of inside e.g.
        research/<topic>/ or lao/ - nothing in this engine (or the write_memory
        MCP tool's docstring) told it any different. This warning is a
        stopgap until every caller-facing surface (MCP tool docstring, CLI
        --help, hooks.py's on_task_end mem_id default) is updated to make
        the domain prefix impossible to miss - see the "Improvements found
        auditing against the QUMem paper" notes in Tessera/docs/ for the full
        list this belongs to.
        """
        if persist_format != "md":
            raise ValueError(
                f"Unsupported persist_format {persist_format!r}; supported format is "
                "'md'. No memory was persisted."
            )

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

        sanitized_content, threat_score, is_sanitized = self.gating_engine.audit_and_sanitize(
            content, tags
        )

        gating_status = "passed"
        if threat_score > self.gating_engine.toxicity_threshold:
            gating_status = "flagged_and_sanitized"

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
        
        # `mem_id` commonly carries a domain prefix (e.g. "lao/some-slug") so
        # notes land inside a topical subdirectory instead of loose at
        # storage_dir's root. Without creating that subdirectory first, a
        # first-ever write to a brand-new domain prefix crashes with
        # FileNotFoundError deep inside an autonomous run (confirmed live
        # 2026-08-25/26: a Gemini-driven /lao run wrote mem_id="voice-ai-..."
        # with NO domain prefix at all and silently landed the note at
        # .claude/memory/'s root instead of e.g. research/<topic>/ - the
        # engine had no way to reject or redirect that, since it never
        # validates mem_id shape). This makedirs alone only fixes the crash
        # for prefixed ids that don't have their subdirectory yet; it does
        # NOT enforce a prefix - see write_memory_note's docstring/callers
        # for the convention every caller (CLI, MCP tool, hooks) must follow.
        os.makedirs(os.path.dirname(filepath_base) or self.storage_dir, exist_ok=True)

        yaml_frontmatter = yaml.dump(
            frontmatter_dict, default_flow_style=False, sort_keys=False, allow_unicode=True
        )
        markdown_body = f"---\n{yaml_frontmatter}---\n\n{sanitized_content.strip()}\n"
        filepath = f"{filepath_base}.md"
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(markdown_body)

        self.file_registry[mem_id] = filepath
        return filepath

    # ------------------------------------------------------------------
    # Typed stores ("gavetas") — facts / preferences / insights
    # ------------------------------------------------------------------
    # Tessera organizes everything learned into exactly 3 typed stores instead
    # of one undifferentiated pile of notes:
    #   - facts:       concrete, immutable information (what happened / what
    #                   is true) — maps to node_type="factual".
    #   - preferences: behavior, tastes, feedback, corrections from a human
    #                   or operator — maps to node_type="preference".
    #   - insights:    transferable learnings from task execution that can
    #                   be applied to *future*, different situations — maps
    #                   to node_type="procedural_anchor".
    # These thin wrappers exist so callers (the orchestrator's hook,
    # MCP tools, CLI) write with clear intent instead of remembering the
    # underlying node_type string.

    def write_fact(
        self,
        mem_id: str,
        episode_id: str,
        content: str,
        tags: Optional[List[str]] = None,
        entities: Optional[List[Entity]] = None,
        active_connections: Optional[List[Connection]] = None,
    ) -> str:
        """Writes a concrete, immutable fact to the `facts` store."""
        return self.write_memory_note(
            mem_id=mem_id,
            mem_type="factual",
            episode_id=episode_id,
            content=content,
            tags=tags or [],
            entities=entities or [],
            active_connections=active_connections,
        )

    def write_preference(
        self,
        mem_id: str,
        episode_id: str,
        content: str,
        tags: Optional[List[str]] = None,
        entities: Optional[List[Entity]] = None,
        active_connections: Optional[List[Connection]] = None,
    ) -> str:
        """
        Writes a behavior/taste/feedback statement to the `preferences` store.
        Superseded automatically by ConflictResolver at retrieval time when a
        newer preference about the same subject exists.
        """
        return self.write_memory_note(
            mem_id=mem_id,
            mem_type="preference",
            episode_id=episode_id,
            content=content,
            tags=tags or [],
            entities=entities or [],
            active_connections=active_connections,
        )

    def write_insight(
        self,
        mem_id: str,
        episode_id: str,
        content: str,
        tags: Optional[List[str]] = None,
        entities: Optional[List[Entity]] = None,
        active_connections: Optional[List[Connection]] = None,
    ) -> str:
        """
        Writes a transferable insight (a learning from executing a task that
        generalizes to future, different situations) to the `insights` store.
        Receives the procedural-anchor retrieval boost (see
        PROCEDURAL_RELATION_BOOST_TYPES) since these notes are meant to
        stabilize *future* action, not just describe the past.
        """
        return self.write_memory_note(
            mem_id=mem_id,
            mem_type="procedural_anchor",
            episode_id=episode_id,
            content=content,
            tags=tags or [],
            entities=entities or [],
            active_connections=active_connections,
        )

    def write_episode(
        self,
        mem_id: str,
        store: str,
        episode_id: str,
        episode: Episode,
        tags: Optional[List[str]] = None,
        entities: Optional[List[Entity]] = None,
        active_connections: Optional[List[Connection]] = None,
    ) -> str:
        """
        Writes a memory note structured as an *episode* (beginning / middle /
        end) instead of one undifferentiated content block, then files it
        into the given typed store (``STORE_FACTS`` / ``STORE_PREFERENCES`` /
        ``STORE_INSIGHTS``).

        Breaking a task execution into begin/middle/end lets retrieval later
        distinguish "why this started" from "what happened" from "what was
        learned/resolved" — which matters most for the `insights` store,
        where the "end" (the lesson) is what's actually transferable to a
        future, different situation, not the blow-by-blow "middle".
        """
        if store not in STORE_TO_NODE_TYPE:
            raise ValueError(
                f"store inválida: {store!r}. Use STORE_FACTS, STORE_PREFERENCES ou STORE_INSIGHTS."
            )
        mem_type = STORE_TO_NODE_TYPE[store]
        return self.write_memory_note(
            mem_id=mem_id,
            mem_type=mem_type,
            episode_id=episode_id,
            content=episode.to_markdown_body(),
            tags=tags or [],
            entities=entities or [],
            active_connections=active_connections,
        )

    def decompose_and_write_episode(
        self,
        mem_id_prefix: str,
        episode_id: str,
        episode: Episode,
        llm_fn: Optional[Any] = None,
        tags: Optional[List[str]] = None,
    ) -> List[str]:
        """
        QUMem-style automatic typed decomposition (see `tessera.decomposer`):
        rather than the caller manually deciding which typed store(s) an
        episode belongs to (as `write_episode` requires), this mechanically
        extracts N atomic facts/preferences/insights from the raw episode
        and writes each through the normal gated typed-store path.

        `llm_fn` is the same `(system_prompt, user_prompt) -> str` shape used
        by `TesseraOrchestrator`/`llm_bridge.resolve_llm_fn()` - pass a real one
        for actual reasoning; omit for the deterministic offline heuristic
        fallback (same offline-by-default philosophy as the rest of Tessera).

        Returns the list of filepaths written (each still goes through the
        same write-side gating/sanitization as a manual `write_fact`/
        `write_preference`/`write_insight` call - decomposition only decides
        *how many* notes get proposed, never bypasses the security gate).
        """
        from .decomposer import decompose_and_write

        return decompose_and_write(
            engine=self,
            mem_id_prefix=mem_id_prefix,
            episode_id=episode_id,
            episode=episode,
            llm_fn=llm_fn,
            tags=tags,
        )

    def retrieve_from_store(
        self, query_text: str, store: str, top_n: int = 7, resolve_conflicts: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Same retrieval pipeline as ``retrieve_context``, but scoped to a
        single typed store (``STORE_FACTS`` / ``STORE_PREFERENCES`` /
        ``STORE_INSIGHTS``). Useful when a caller (e.g. the Retrieval Planner
        agent) already knows which drawer it needs to open instead of
        searching all three indiscriminately.
        """
        if store not in STORE_TO_NODE_TYPE:
            raise ValueError(
                f"store inválida: {store!r}. Use STORE_FACTS, STORE_PREFERENCES ou STORE_INSIGHTS."
            )
        target_node_type = STORE_TO_NODE_TYPE[store]
        # Over-fetch then filter: DW-PR ranks across the whole graph, so we
        # ask for more candidates than top_n to make sure enough survive the
        # store filter without a second, disjoint pass over the graph.
        candidates = self.retrieve_context(
            query_text=query_text, top_n=max(top_n * 4, 12), resolve_conflicts=resolve_conflicts
        )
        filtered = [m for m in candidates if m.get("type") == target_node_type]
        return filtered[:top_n]

    # ------------------------------------------------------------------
    # Index build
    # ------------------------------------------------------------------
    def build_index(self, recursive: bool = True, use_cache: bool = True, persist: bool = True) -> None:
        """
        Scans the storage directory and (re)builds the heterogeneous
        knowledge graph in memory: memory notes, entities, tags, and their
        interrelations. Also (re)trains the TF-IDF vectorizer over the corpus.

        Args:
            recursive: when True (default), walks all subdirectories of
                ``storage_dir`` too — needed for corpora organized into
                topic folders (e.g. LAO's ``.claude/memory/research/<topic>/``).
            use_cache: when True (default), first tries to load a previously
                persisted index (``.tessera_index/graph.pkl``) if its fingerprint
                (file count + latest mtime across the corpus) still matches
                the notes on disk — this skips a full re-parse+re-vectorize
                on every CLI invocation when nothing actually changed.
            persist: when True (default), writes the freshly built index to
                ``.tessera_index/`` (pickle for fast reload + a human-readable
                JSON summary) once the scan finishes.
        """
        if use_cache and self._load_index_if_fresh():
            return

        self.graph.clear()
        self.file_registry.clear()
        self.node_corpus.clear()
        pending_connections = []

        if not os.path.exists(self.storage_dir):
            return

        explicit_ids_indexed = {}

        for filepath in self._iter_markdown_files(recursive=recursive):
            filename = os.path.relpath(filepath, self.storage_dir)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    raw_text = f.read()

                # Integrate Canonical Metadata Model (F2/F3/F4/F5/F7)
                from .canonical import parse_and_normalize, compute_sha256
                persistent_id, persistent_doc_id = self._resolve_persistent_id(filepath, raw_text)
                
                canonical_meta = parse_and_normalize(
                    raw_text, filepath, self.storage_dir,
                    persistent_id=persistent_id, persistent_doc_id=persistent_doc_id
                )
                self._update_identity_manifest(filepath, canonical_meta)

                mem_id = canonical_meta.identity.id
                if not mem_id:
                    continue
                
                # Check for explicit ID collisions (F3)
                if canonical_meta.metadata_origin.get("id") == "explicit":
                    if mem_id in explicit_ids_indexed:
                        raise ValueError(
                            f"Collision de IDs Explícitos Detectada: O ID '{mem_id}' foi declarado explicitamente "
                            f"em múltiplos arquivos: '{filepath}' e '{explicit_ids_indexed[mem_id]}'."
                        )
                    explicit_ids_indexed[mem_id] = filepath

                if mem_id in self.graph:
                    # Inferred collision suffix must be 100% deterministic (F3)
                    suffix = compute_sha256(filename.replace(os.sep, "/"))[:6]
                    mem_id = f"{mem_id}__{suffix}"

                self.file_registry[mem_id] = filepath
                
                # node_type represents classification kind for compatible graph lookups
                node_type = canonical_meta.classification.kind
                
                # Clone truly raw frontmatter to avoid mutating original (F4)
                import copy
                frontmatter_compat = copy.deepcopy(canonical_meta.raw_frontmatter or {})
                # Ensure frontmatter_compat has legacy fields
                frontmatter_compat["id"] = mem_id
                frontmatter_compat["node_type"] = node_type
                frontmatter_compat["drawer"] = canonical_meta.classification.drawer
                
                # For compatibility with display/search, we keep tags, entities, created_at, etc., in frontmatter
                frontmatter_compat["tags"] = frontmatter_compat.get("tags", [])
                frontmatter_compat["entities"] = frontmatter_compat.get("entities", [])
                
                # Map active_connections to canonical explicit relations
                active_connections_compat = []
                for rel in canonical_meta.relations:
                    if rel.origin == "explicit":
                        active_connections_compat.append({
                            "target_memory_id": rel.target,
                            "relation_type": rel.type
                        })
                frontmatter_compat["active_connections"] = active_connections_compat

                body = canonical_meta.raw_frontmatter.get("body", raw_text.split("---", 2)[2] if raw_text.startswith("---") and len(raw_text.split("---", 2)) >= 3 else raw_text)
                body = body.strip()

                tags_str = " ".join(frontmatter_compat["tags"])
                entities_str = " ".join([e.get("name", "") if isinstance(e, dict) else "" for e in frontmatter_compat["entities"]])
                description = frontmatter_compat.get("description", "") or ""
                self.node_corpus[mem_id] = f"{description} {body} {tags_str} {entities_str}"

                # Store the canonical metadata directly on the node!
                self.graph.add_node(
                    mem_id,
                    node_type=node_type,
                    filepath=filepath,
                    filename=filename,
                    frontmatter=frontmatter_compat,
                    body=body,
                    canonical_metadata=canonical_meta,
                )

                for ent in frontmatter_compat["entities"]:
                    if not isinstance(ent, dict):
                        continue
                    ent_name = ent.get("name")
                    if not ent_name:
                        continue
                    ent_desc = ent.get("description", "")
                    ent_id = f"ent_{ent_name.lower().replace(' ', '_')}"

                    if ent_id not in self.graph:
                        self.graph.add_node(ent_id, node_type="entity", name=ent_name, description=ent_desc)
                        self.node_corpus[ent_id] = f"{ent_name}: {ent_desc}"

                    self.graph.add_edge(mem_id, ent_id, relation_type="mentions")

                for tag in frontmatter_compat["tags"]:
                    tag_id = f"tag_{tag.lower()}"
                    if tag_id not in self.graph:
                        self.graph.add_node(tag_id, node_type="tag", tag_name=tag)
                        self.node_corpus[tag_id] = f"Tag: {tag}"

                    self.graph.add_edge(mem_id, tag_id, relation_type="tagged_with")

                # Add relations (explicit links, wikilinks, etc.) (F7)
                for rel in canonical_meta.relations:
                    # Ignore tag/entity connections that we already added above
                    if rel.target.startswith(("tag_", "ent_")):
                        continue
                    pending_connections.append(
                        (mem_id, rel.target, rel.type)
                    )

            except Exception as e:
                # Re-raise explicit collisions to fail build_index properly
                if isinstance(e, ValueError) and "Collision de IDs Explícitos" in str(e):
                    raise e
                print(f"[Aviso] Falha ao processar a nota física {filename}: {e}")
                continue

        for src, dest, rel in pending_connections:
            if src in self.graph and dest in self.graph:
                self.graph.add_edge(src, dest, relation_type=rel)

        if self.node_corpus:
            self.node_ids = list(self.node_corpus.keys())
            corpus_texts = [self.node_corpus[nid] for nid in self.node_ids]
            self.tfidf_matrix = self.vectorizer.fit_transform(corpus_texts)

        if persist:
            self.save_index()

    # ------------------------------------------------------------------
    # Index persistence (disk cache)
    # ------------------------------------------------------------------
    def _source_fingerprint(self) -> Tuple[int, float]:
        """
        Cheap signature of the current corpus state: (file count, max mtime)
        across every ``.md`` file under ``storage_dir``. Used to decide
        whether a cached index is still valid without re-parsing anything.
        """
        count = 0
        latest_mtime = 0.0
        for filepath in self._iter_markdown_files(recursive=True):
            count += 1
            try:
                mtime = os.path.getmtime(filepath)
            except OSError:
                continue
            if mtime > latest_mtime:
                latest_mtime = mtime
        return count, latest_mtime

    def save_index(self) -> None:
        """
        Persists the current in-memory graph/index to
        ``<storage_dir>/.tessera_index/``:
          - ``graph.pkl``: full binary snapshot (graph + TF-IDF matrix/
            vectorizer + corpus + file registry) for instant reload.
          - ``graph.json``: human-readable summary (nodes, edges, per-node
            type/filepath) so you can actually open and inspect what got
            indexed without deserializing pickle.
        """
        import json
        import pickle

        os.makedirs(self.index_cache_dir, exist_ok=True)
        self._save_identity_manifest()

        fingerprint = self._source_fingerprint()
        snapshot = {
            "storage_dir": os.path.abspath(self.storage_dir),
            "fingerprint": fingerprint,
            "graph": self.graph,
            "file_registry": self.file_registry,
            "node_corpus": self.node_corpus,
            "node_ids": self.node_ids,
            "tfidf_matrix": self.tfidf_matrix,
            "vectorizer": self.vectorizer,
        }
        with open(self.index_cache_pkl, "wb") as f:
            pickle.dump(snapshot, f)

        readable = {
            "storage_dir": os.path.abspath(self.storage_dir),
            "generated_at": datetime.datetime.now().astimezone().isoformat(),
            "num_nodes": self.graph.number_of_nodes(),
            "num_edges": self.graph.number_of_edges(),
            "nodes": {
                node_id: {
                    "node_type": data.get("node_type"),
                    "filepath": data.get("filepath"),
                    "tags": data.get("frontmatter", {}).get("tags", []) if data.get("frontmatter") else None,
                }
                for node_id, data in self.graph.nodes(data=True)
            },
        }
        with open(self.index_cache_json, "w", encoding="utf-8") as f:
            json.dump(readable, f, indent=2, ensure_ascii=False)

    def _load_index_if_fresh(self) -> bool:
        """
        Attempts to load ``.tessera_index/graph.pkl`` and validates its stored
        fingerprint against the corpus's current state. Returns True (and
        populates self.graph/etc.) only if the cache is still valid; False
        otherwise (caller should fall back to a full rebuild).
        """
        import pickle

        if not os.path.exists(self.index_cache_pkl):
            return False

        try:
            with open(self.index_cache_pkl, "rb") as f:
                snapshot = pickle.load(f)
        except Exception:  # noqa: BLE001 - any corrupt/incompatible cache -> rebuild
            return False

        if snapshot.get("fingerprint") != self._source_fingerprint():
            return False

        self.graph = snapshot["graph"]
        self.file_registry = snapshot["file_registry"]
        self.node_corpus = snapshot["node_corpus"]
        self.node_ids = snapshot["node_ids"]
        self.tfidf_matrix = snapshot["tfidf_matrix"]
        self.vectorizer = snapshot["vectorizer"]
        return True

    def _iter_markdown_files(self, recursive: bool):
        """Yields absolute paths to every ``.md`` file to index."""
        scan_dirs = [self.storage_dir]
        individual_files = []

        # Find potential project roots (current working dir or 2 steps up from storage_dir)
        roots = [os.getcwd()]
        try:
            two_up = os.path.dirname(os.path.dirname(os.path.abspath(self.storage_dir)))
            if os.path.exists(two_up) and os.path.isdir(two_up):
                roots.append(two_up)
        except Exception:
            pass

        # Deduplicate roots while preserving order
        seen_roots = set()
        unique_roots = []
        for r in roots:
            abs_r = os.path.abspath(r)
            if abs_r not in seen_roots:
                seen_roots.add(abs_r)
                unique_roots.append(abs_r)

        # Map the monorepo folders ONLY if storage_dir resides inside the project root
        # This keeps clean temporary/sandbox test environments isolated and pristine.
        for root in unique_roots:
            storage_dir_abs = os.path.abspath(self.storage_dir)
            root_abs = os.path.abspath(root)
            if storage_dir_abs.startswith(root_abs):
                # 1. Add specific research folders if they exist
                for folder in ["experiments", "newsletters", "docs"]:
                    path = os.path.join(root, folder)
                    if os.path.exists(path) and os.path.isdir(path):
                        abs_path = os.path.abspath(path)
                        if abs_path not in [os.path.abspath(d) for d in scan_dirs]:
                            scan_dirs.append(abs_path)
                
                # 2. Add individual top-level markdown files in the project root (e.g. GEMINI.md, AGENTS.md, README.md)
                try:
                    for filename in os.listdir(root):
                        if filename.endswith(".md"):
                            abs_filepath = os.path.abspath(os.path.join(root, filename))
                            if abs_filepath not in individual_files:
                                individual_files.append(abs_filepath)
                except Exception:
                    pass

        # Yield from directories
        for s_dir in scan_dirs:
            if recursive:
                for root, dirs, files in os.walk(s_dir):
                    # Exclude typical build/env/git/dependency folders from recursion
                    dirs[:] = [
                        d for d in dirs 
                        if d not in (
                            ".tessera_index", ".git", "node_modules", "venv", 
                            ".venv-browser-agent", ".browser-harness", "Tessera"
                        )
                    ]
                    for filename in files:
                        if filename.endswith(".md"):
                            yield os.path.join(root, filename)
            else:
                try:
                    for filename in os.listdir(s_dir):
                        if filename.endswith(".md"):
                            yield os.path.join(s_dir, filename)
                except Exception:
                    pass

        # Yield individual top-level files
        for filepath in individual_files:
            if os.path.exists(filepath):
                yield filepath

    def _normalize_frontmatter(self, frontmatter: Dict[str, Any], filepath: str) -> Dict[str, Any]:
        """
        Normalizes a parsed frontmatter dict into Tessera's native shape
        (``id`` / ``node_type`` / ``tags`` / ``entities`` / ``active_connections``).

        Tessera's own writer (``write_memory_note``) already produces the native
        shape, so this is a no-op for those notes. For "foreign" corpora that
        use ``name`` / ``description`` / ``metadata.type`` instead (e.g. LAO's
        ``.claude/memory/`` learnings), this maps fields across so the same
        engine (graph, DW-PR, conflict resolution) works unmodified on both.
        """
        if "id" in frontmatter and "node_type" in frontmatter:
            return frontmatter  # already native Tessera shape

        normalized = dict(frontmatter)

        name = normalized.get("name")
        if isinstance(name, list):  # a couple of template files have `name: [placeholder]`
            name = name[0] if name else None
        if not name:
            name = os.path.splitext(os.path.basename(filepath))[0]
        normalized["id"] = str(name)

        metadata = normalized.get("metadata")
        meta_type = metadata.get("type") if isinstance(metadata, dict) else None
        node_type_map = {
            "user": "preference",
            "feedback": "preference",
            "reference": "factual",
            "hypothesis": "factual",
            "experiment-result": "factual",
            "governance": "procedural_anchor",
            "pipeline": "procedural_anchor",
            "learning": "procedural_anchor",
            "project": "factual",
        }
        
        filename_lower = os.path.basename(filepath).lower()
        if "claude.md" in filename_lower or "gemini.md" in filename_lower or "agents.md" in filename_lower or "agentes.md" in filename_lower:
            fallback_type = "procedural_anchor"
        elif "instruction" in filename_lower or "rule" in filename_lower or "convention" in filename_lower or "guide" in filename_lower:
            fallback_type = "procedural_anchor"
        else:
            fallback_type = "factual"

        normalized["node_type"] = node_type_map.get(meta_type, fallback_type)

        # Fold `description` + any metadata scalars into searchable tags so
        # foreign notes remain retrievable even without an explicit `tags` list.
        tags = list(normalized.get("tags") or [])
        if isinstance(metadata, dict):
            for key in ("category", "phase", "topic", "type"):
                val = metadata.get(key)
                if isinstance(val, str) and val not in tags:
                    tags.append(val)
        normalized["tags"] = tags

        if "entities" not in normalized:
            normalized["entities"] = []
        if "active_connections" not in normalized:
            normalized["active_connections"] = []

        # Fold `metadata.related_to` (a plain list of target ids, LAO's
        # preferred foreign frontmatter shape) into real active_connections
        # edges, so a note authored with that shape gets the same explicit
        # graph linking as a native Tessera note written via --related-to.
        # Without this, related_to only ever fed the TF-IDF corpus above —
        # readable by a human, invisible to the graph/DW-PR ranking.
        if isinstance(metadata, dict):
            related_to = metadata.get("related_to")
            if isinstance(related_to, list) and not normalized["active_connections"]:
                existing_targets = set()
                for target in related_to:
                    if not isinstance(target, str) or not target.strip():
                        continue
                    target = target.strip()
                    if target in existing_targets:
                        continue
                    existing_targets.add(target)
                    normalized["active_connections"].append(
                        {"target_memory_id": target, "relation_type": "related_to", "cosine_similarity": 0.0}
                    )

        return normalized

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------
    def retrieve_context(
        self, query_text: str, top_n: int = 7, resolve_conflicts: bool = True, weights: Optional[Dict[str, float]] = None
    ) -> List[Dict[str, Any]]:
        """
        End-to-end adaptive retrieval (QUMem & MemORAI style):
        1. Finds seed nodes via semantic (TF-IDF cosine) similarity.
        2. Builds a local subgraph focused on the query intent (1-hop expansion).
        3. Dynamically weights edges based on similarity + procedural-anchor boosts (DW-PR).
        4. Runs personalized PageRank over the subgraph.
        5. Filters down to actual memory-note candidates using explainable multi-signal ranking.
        6. Applies temporal conflict resolution over preferences/facts.
        """
        if not self.graph or not self.node_corpus or self.tfidf_matrix is None:
            return []

        # 1. Seed node discovery.
        query_vec = self.vectorizer.transform([query_text])
        similarities = cosine_similarity(query_vec, self.tfidf_matrix).flatten()
        sorted_indices = np.argsort(similarities)[::-1]

        seed_nodes = []
        seed_similarities = {}
        for idx in sorted_indices[:SEED_NODE_LIMIT]:
            if similarities[idx] > SEED_NODE_MIN_SIMILARITY:
                nid = self.node_ids[idx]
                seed_nodes.append(nid)
                seed_similarities[nid] = similarities[idx]

        if not seed_nodes:
            return []

        # 2. 1-hop subgraph expansion (MemORAI).
        subgraph_nodes = set(seed_nodes)
        for seed in seed_nodes:
            subgraph_nodes.update(self.graph.successors(seed))
            subgraph_nodes.update(self.graph.predecessors(seed))

        subgraph = self.graph.subgraph(subgraph_nodes).copy()

        # 3. Dynamic edge weighting (DW-PR).
        all_sub_nodes = list(subgraph.nodes())
        sub_texts = [self.node_corpus.get(nid, "") for nid in all_sub_nodes]
        sub_vecs = self.vectorizer.transform(sub_texts)
        sub_sims = cosine_similarity(query_vec, sub_vecs).flatten()
        node_sim_map = dict(zip(all_sub_nodes, sub_sims))

        for u, v in list(subgraph.edges()):
            target_similarity = node_sim_map.get(v, 0.0)
            relation_type = subgraph[u][v].get("relation_type", "")

            relation_boost = (
                PROCEDURAL_RELATION_BOOST_FACTOR
                if relation_type in PROCEDURAL_RELATION_BOOST_TYPES
                else 1.0
            )

            dynamic_weight = (target_similarity + 0.1) * relation_boost
            subgraph[u][v]["weight"] = max(0.01, float(dynamic_weight))

        # 4. Personalized PageRank (DW-PR).
        try:
            personalization = {nid: seed_similarities.get(nid, 0.0) for nid in subgraph.nodes()}
            p_sum = sum(personalization.values())
            personalization = {k: v / p_sum for k, v in personalization.items()} if p_sum > 0 else None

            pagerank_scores = nx.pagerank(
                subgraph, alpha=0.85, weight="weight", personalization=personalization
            )
        except Exception:
            # Safe fallback if the subgraph is disconnected or a numerical error occurs.
            pagerank_scores = nx.pagerank(subgraph, alpha=0.85, weight="weight")

        import re
        import math

        # 5. Filter down to real memory-note candidates.
        retrieved_memories = []
        
        # We need the maximum PageRank score among the memory nodes to normalize PR scores.
        memory_pageranks = [pagerank_scores.get(nid, 0.0) for nid in pagerank_scores 
                            if nid in self.graph.nodes and self.graph.nodes[nid].get("node_type") in MEMORY_NODE_TYPES]
        max_pagerank = max(memory_pageranks) if memory_pageranks else 1.0

        # Resolve weights to use
        weights_used = dict(self.weights)
        if weights:
            weights_used.update(weights)

        # Normalize query tokens and phrase matching (F3 / Subset trap fix)
        query_tokens = set(re.findall(r"\b\w+\b", query_text.lower()))
        query_clean = " ".join(re.findall(r"\b\w+\b", query_text.lower()))

        for node_id, pr_score in pagerank_scores.items():
            if node_id not in self.graph.nodes:
                continue
            node_data = self.graph.nodes[node_id]
            node_type = node_data.get("node_type")

            if node_type in MEMORY_NODE_TYPES:
                # Related notes: direct graph neighbors (tags/entities/active_connections
                # in either direction) that are themselves memory notes, not tag/entity
                # nodes — lets a caller jump to connected notes without re-querying.
                related_ids = sorted(
                    {
                        nb
                        for nb in set(self.graph.successors(node_id)) | set(self.graph.predecessors(node_id))
                        if nb != node_id and self.graph.nodes[nb].get("node_type") in MEMORY_NODE_TYPES
                    }
                )
                
                # Compute Multi-Signal Score
                # A. Lexical Similarity
                raw_tfidf = float(node_sim_map.get(node_id, 0.0))
                
                body_text = node_data.get("body", "")
                body_tokens = set(re.findall(r"\b\w+\b", body_text.lower()))
                term_overlap = len(query_tokens & body_tokens) / max(1, len(query_tokens))
                
                # B. Title/ID Relevance
                clean_id_tokens = set(re.findall(r"\b\w+\b", node_id.lower().replace("/", " ").replace("-", " ").replace("_", " ")))
                title_score = len(query_tokens & clean_id_tokens) / max(1, len(query_tokens))
                
                # C. Metadata Relevance (Tags + Entities) - Normalize and tokenize to avoid multiword mismatch (F4)
                tags = [str(t).lower() for t in node_data.get("frontmatter", {}).get("tags", [])]
                entity_names = [str(e.get("name", "")).lower() for e in node_data.get("frontmatter", {}).get("entities", []) if isinstance(e, dict)]
                metadata_tokens = set()
                for tag in tags:
                    metadata_tokens.update(re.findall(r"\b\w+\b", tag))
                for ent_name in entity_names:
                    metadata_tokens.update(re.findall(r"\b\w+\b", ent_name))
                
                metadata_score = len(query_tokens & metadata_tokens) / max(1, len(query_tokens))
                
                # D. Graph Centrality (Normalized Personalized PageRank) (F7)
                normalized_relations = pr_score / max_pagerank if max_pagerank > 0 else 0.0
                
                # E. Intent Type Boost (F3 - matching with query tokens and phrase matching to avoid substring trap)
                type_boost = 1.0
                is_procedural_intent = any(tk in query_tokens for tk in ("como", "procedimento", "fluxo", "passo", "tutorial", "deploy", "configurar", "setup", "erro", "bug", "how")) or "como fazer" in query_clean or "how to" in query_clean
                is_preference_intent = any(tk in query_tokens for tk in ("prefere", "gosto", "comportamento", "estilo", "feedback", "tom", "preferência", "preferencia")) or "comportamento do" in query_clean
                is_factual_intent = any(tk in query_tokens for tk in ("fato", "fact", "quem", "quando", "onde", "valor", "endpoint", "versão", "versao", "id", "nome", "name"))
                
                if node_type == "procedural_anchor" and is_procedural_intent:
                    type_boost = 1.3
                elif node_type == "preference" and is_preference_intent:
                    type_boost = 1.3
                elif node_type == "factual" and is_factual_intent:
                    type_boost = 1.2
                    
                # F. Temporal Recency Boost (60-day exponential half-life) - Injected today Clock (F2)
                recency_score = 0.0
                fm = node_data.get("frontmatter", {})
                date_str = fm.get("last_updated_at") or fm.get("created_at") or fm.get("date")
                if date_str:
                    try:
                        date_str = str(date_str)[:10]
                        dt = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
                        today = self.get_today()
                        days = (today - dt).days
                        if days <= 0:
                            recency_score = 1.1
                        else:
                            recency_score = 1.0 + 0.1 * math.exp(-days / 60.0)
                    except Exception:
                        pass
                
                # Default is disabled (weight 0.0), only applies if explicitly enabled in weights
                recency_boost = 1.0
                if weights_used.get("recency", 0.0) > 0.0 and recency_score > 0.0:
                    recency_boost = recency_score
                
                # Combine Weighted Signals
                base_relevance = (
                    weights_used.get("lexical_tfidf", 0.28) * raw_tfidf +
                    weights_used.get("lexical_overlap", 0.12) * term_overlap +
                    weights_used.get("title", 0.3) * title_score +
                    weights_used.get("metadata", 0.2) * metadata_score +
                    weights_used.get("relations", 0.1) * normalized_relations
                )
                
                final_score = base_relevance * type_boost * recency_boost
                
                # Phase 2: Query-Aware Relevant Evidence Extraction (Deterministic, Local & Fast)
                # Gated by overlap threshold to return None when evidence is insufficient (F5)
                paragraphs = [p.strip() for p in re.split(r"\n\s*\n", body_text) if p.strip()]
                if not paragraphs:
                    paragraphs = [line.strip() for line in body_text.splitlines() if line.strip()]
                
                relevant_evidence = None
                evidence_info = None
                if paragraphs:
                    best_para_score = -1.0
                    best_para = None
                    for p in paragraphs:
                        p_tokens = set(re.findall(r"\b\w+\b", p.lower()))
                        overlap = len(query_tokens & p_tokens)
                        jaccard = overlap / len(query_tokens | p_tokens) if (query_tokens | p_tokens) else 0.0
                        para_score = overlap + jaccard
                        if para_score > best_para_score:
                            best_para_score = para_score
                            best_para = p
                    
                    # Threshold check: requires at least 1 overlapping query token (best_para_score >= 1.0)
                    if best_para and best_para_score >= 1.0:
                        relevant_evidence = best_para
                        evidence_info = {
                            "text": relevant_evidence,
                            "score": float(best_para_score),
                            "strategy": "paragraph_lexical"
                        }
                
                retrieved_memories.append(
                    {
                        "id": node_id,
                        "type": node_type,
                        "filepath": node_data.get("filepath"),
                        "filename": node_data.get("filename"),
                        "score": float(final_score),
                        "score_explain": {
                            "lexical_tfidf": float(raw_tfidf),
                            "lexical_overlap": float(term_overlap),
                            "lexical_score": float(raw_tfidf * 0.7 + term_overlap * 0.3),
                            "title": float(title_score),
                            "metadata": float(metadata_score),
                            "raw_pagerank": float(pr_score),
                            "normalized_relations": float(normalized_relations),
                            "relations_contribution": float(normalized_relations * weights_used.get("relations", 0.1)),
                            "type_boost": float(type_boost),
                            "recency_boost": float(recency_score if recency_score > 0 else 1.0),
                        },
                        "relevant_evidence": relevant_evidence,
                        "evidence_info": evidence_info,
                        "body": body_text.strip(),
                        "frontmatter": fm,
                        "related_ids": related_ids,
                    }
                )

        retrieved_memories.sort(key=lambda x: x["score"], reverse=True)

        # 6. Temporal conflict resolution (FinPerMA & QUMem).
        if resolve_conflicts:
            retrieved_memories = ConflictResolver.resolve_temporal_conflicts(retrieved_memories)
            retrieved_memories.sort(key=lambda x: x["score"], reverse=True)

        return retrieved_memories[:top_n]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _parse_markdown(self, raw_text: str) -> Tuple[Optional[Dict[str, Any]], str]:
        """Splits a note into (frontmatter dict, body text)."""
        text = raw_text.strip()
        if not text.startswith("---"):
            return None, raw_text

        parts = text.split("---", 2)
        if len(parts) >= 3:
            frontmatter_raw = parts[1]
            body = parts[2]
            try:
                frontmatter = yaml.safe_load(frontmatter_raw)
                return frontmatter, body
            except yaml.YAMLError:
                # Some hand-authored corpora (e.g. LAO's own memory notes) have
                # unquoted colons inside single-line scalar values (most often
                # `description: Some claim: with a colon in it`), which breaks
                # strict YAML parsing. Recover by auto-quoting the offending
                # `key: value` lines instead of discarding the whole note.
                repaired = self._repair_frontmatter_yaml(frontmatter_raw)
                try:
                    frontmatter = yaml.safe_load(repaired)
                    return frontmatter, body
                except Exception as e:
                    raise InvalidFrontmatterError(f"YAML parsing error: {e}") from e
        return None, raw_text

    @staticmethod
    def _repair_frontmatter_yaml(frontmatter_raw: str) -> str:
        """Best-effort auto-quoting of single-line scalar values containing
        unescaped colons, so a minor authoring slip doesn't sink an entire note."""
        import re

        fixed_lines = []
        key_line_re = re.compile(r"^(\s*)([A-Za-z0-9_]+):\s+(.*)$")
        for line in frontmatter_raw.splitlines():
            match = key_line_re.match(line)
            if not match:
                fixed_lines.append(line)
                continue
            indent, key, value = match.groups()
            stripped = value.strip()

            # A value that STARTS with a quote but has trailing content after
            # the closing quote (e.g. `"Voice by Blip" (Thesis 2B, ...)`) is
            # invalid YAML — a scalar can't have unquoted text following a
            # quoted string on the same line. Re-quote the whole value.
            starts_quoted_with_trailer = (
                len(stripped) > 1
                and stripped[0] in "\"'"
                and not (stripped.endswith(stripped[0]) and stripped.count(stripped[0]) == 2)
            )

            looks_like_nested_or_safe = (
                not stripped
                or stripped.startswith(("-", "[", "{"))
                or (stripped.startswith(("\"", "'")) and not starts_quoted_with_trailer)
                or ":" not in stripped
            ) and not starts_quoted_with_trailer

            if looks_like_nested_or_safe:
                fixed_lines.append(line)
                continue
            # Contains an un-quoted colon (or a broken quoted-then-trailing
            # value) in a plain scalar — re-quote the whole thing safely.
            escaped = stripped.replace('"', '\\"')
            fixed_lines.append(f'{indent}{key}: "{escaped}"')
        return "\n".join(fixed_lines)
