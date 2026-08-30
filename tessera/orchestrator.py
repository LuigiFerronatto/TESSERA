"""
TesseraOrchestrator — a 3-agent retrieval pipeline (QUMem-style) on top of TesseraEngine.

Rather than letting a single generic agent both search memory and answer,
this orchestrator splits the job into three specialized reasoning steps —
a trio of "detective" agents that inspects the 3 typed stores (facts /
preferences / insights) before the main agent ever acts:

    1. Information-Need Agent   — analyzes the task and reasons about what
       history it actually needs: "what do I need to find out from past
       memory to answer/do this?"
    2. Retrieval Planner Agent  — turns that need into a focused search plan,
       decides which typed store(s) (facts / preferences / insights) are
       relevant, and pulls candidates from each via
       TesseraEngine.retrieve_from_store (DW-PR + ConflictResolver).
    3. User-State Inference Agent — joins the clues found across stores,
       discards memories that are now obsolete (ConflictResolver already
       drops superseded preferences/facts at retrieval time), and produces
       a validated summary of current state, ready to inject into the main
       agent's context.

Each "agent" step is just a prompt template + a call to `llm_fn`. By default
`llm_fn` is a deterministic, offline simulation (no API key required) so the
whole pipeline is runnable and testable without any LLM provider configured.
Pass your own `llm_fn` (e.g. wrapping `lao_core.engine_router.invoke`, the
Anthropic/OpenAI SDK, or any callable of `(system_prompt, user_prompt) -> str`)
to plug in a real model.

See `tessera.hooks` for the mechanism that *automatically* intercepts a task and
triggers this pipeline (rather than the caller invoking it by hand).
"""

import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from .engine import STORE_FACTS, STORE_INSIGHTS, STORE_PREFERENCES, TesseraEngine

LlmFn = Callable[[str, str], str]

ALL_STORES = [STORE_FACTS, STORE_PREFERENCES, STORE_INSIGHTS]

NEED_AGENT_SYSTEM_PROMPT = (
    "You are the Tessera Information-Need Agent. Given a task instruction, "
    "objectively decide which types of memory (factual, preference, "
    "procedural_anchor) are relevant and produce a short sentence describing "
    "the information need."
)

PLANNER_AGENT_SYSTEM_PROMPT = (
    "You are the Tessera Retrieval Planner Agent. Given an information need, "
    "rewrite it as an objective, keyword-rich search query for the memory "
    "graph TF-IDF index."
)

INFERENCE_AGENT_SYSTEM_PROMPT = (
    "You are the Tessera State Inference Agent. Given the raw retrieved memory notes "
    "(already chronologically resolved by the ConflictResolver), "
    "consolidate them into a clean, actionable, and non-redundant context block "
    "for the main agent.\n\n"
    "CRITICAL CONSTRAINTS FOR EXPLICIT GRAPH PROVENANCE & RELATIONAL TRACING:\n"
    "1. CITATION & ANCHORING: Every key fact, finding, or recommendation in the consolidated context "
    "MUST be explicitly cited with its source note ID (e.g., `[learnings/openai-tts-api-gpt4o-mini-tts-reference]`). "
    "Never state a consolidated memory without pointing directly to the note it came from.\n"
    "2. RELATIONSHIP EXPLANATIONS: Actively explain how the active connections (relationships) between "
    "notes strengthen or qualify the findings (e.g., 'This gap identified in [note-a] is bridged by the pattern "
    "validated in [note-b] which is connected to it in the graph...'). Show the network of knowledge, "
    "not just a list of facts.\n"
    "3. PRIMARY ANCHORS OF TRUTH: Start the consolidated block with a brief 'Primary Anchors of Truth' section "
    "highlighting the 1-2 most critical/recent notes for this specific task and their most important "
    "graph relationships (active connections).\n"
    "4. TEMPORALITY & EVOLUTION: Pay rigorous attention to update dates. Explicitly highlight when a newer note "
    "supersedes or refines older assumptions found in connected notes."
)


@dataclass
class OrchestratorResult:
    task_instruction: str
    information_need: str
    retrieval_query: str
    raw_memories: List[Dict[str, Any]] = field(default_factory=list)
    consolidated_context: str = ""
    stores_queried: List[str] = field(default_factory=lambda: list(ALL_STORES))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_instruction": self.task_instruction,
            "information_need": self.information_need,
            "retrieval_query": self.retrieval_query,
            "raw_memories": self.raw_memories,
            "consolidated_context": self.consolidated_context,
            "stores_queried": self.stores_queried,
        }


class TesseraOrchestrator:
    """
    Runs the Need → Planner → Retrieval → Inference pipeline end-to-end over
    a given TesseraEngine. `llm_fn` is required to make each reasoning step actually "think".
    """

    def __init__(self, engine: TesseraEngine, llm_fn: Optional[LlmFn] = None):
        self.engine = engine
        
        if llm_fn is None:
            from .llm_bridge import resolve_llm_fn
            resolved_fn, _ = resolve_llm_fn(return_backend_name=True)
            if not resolved_fn:
                # Use offline simulated llm instead of raising ValueError, as documented.
                self.llm_fn = self._simulated_llm
            else:
                self.llm_fn = resolved_fn
        else:
            self.llm_fn = llm_fn

    def _simulated_llm(self, system_prompt: str, user_prompt: str) -> str:
        """Deterministic offline string-template simulation so the pipeline runs offline/testable."""
        if system_prompt == NEED_AGENT_SYSTEM_PROMPT:
            match = re.search(r"Task instruction:\s*(.*?)(?:\n|$)", user_prompt, re.IGNORECASE)
            task = match.group(1).strip() if match else "the task"
            return f"Need to retrieve factual and procedural memory notes related to: {task}"
        
        elif system_prompt == PLANNER_AGENT_SYSTEM_PROMPT:
            match = re.search(r"Information need:\s*(.*?)(?:\n|$)", user_prompt, re.IGNORECASE)
            need = match.group(1).strip() if match else "query"
            clean_query = need.replace("Need to retrieve factual and procedural memory notes related to:", "").strip()
            return clean_query
            
        elif system_prompt == INFERENCE_AGENT_SYSTEM_PROMPT:
            # Look for the Retrieved memory notes section in the user prompt
            match = re.search(r"Retrieved memory notes:\n(.*?\n\n|.*?$)", user_prompt, re.DOTALL | re.IGNORECASE)
            notes_block = match.group(1).strip() if match else ""
            
            summary_parts = [
                "### Primary Anchors of Truth (Simulated)\n"
            ]
            note_headers = re.findall(r"\[[a-zA-Z_]+\s*\|\s*([a-zA-Z0-9_\-/]+)\s*\|.*?\]", user_prompt)
            if note_headers:
                for idx, nid in enumerate(note_headers, 1):
                    summary_parts.append(f"{idx}. Provenance from note: {nid}")
                summary_parts.append("\n### Consolidated Context (Simulated)")
                summary_parts.append(notes_block)
            else:
                summary_parts.append("(No relevant memory found for this task.)")
            return "\n".join(summary_parts)
            
        else:
            return user_prompt

    # ------------------------------------------------------------------
    # Pipeline steps
    # ------------------------------------------------------------------
    def identify_information_need(self, task_instruction: str) -> str:
        """Step 1 (Information-Need Agent): what historical context does this task
        actually depend on? Reasons logically about what must be discovered
        in the memory history to answer/execute the task."""
        return self.llm_fn(
            NEED_AGENT_SYSTEM_PROMPT,
            f"Task instruction: {task_instruction}\n"
            "Respond in one objective sentence describing what kind of past "
            "memory (fact, preference, or procedure) is needed.",
        )

    def plan_retrieval(self, information_need: str) -> str:
        """Step 2a (Retrieval Planner Agent): turn the information need into a
        concrete search query."""
        return self.llm_fn(
            PLANNER_AGENT_SYSTEM_PROMPT,
            f"Information need: {information_need}\n"
            "Respond only with the rewritten search query.",
        )

    def plan_target_stores(self, information_need: str) -> List[str]:
        """
        Step 2b (Retrieval Planner Agent): decides which typed store(s) —
        facts / preferences / insights — the search plan should open, instead
        of blindly querying all three. Falls back to all 3 stores whenever
        the need doesn't clearly point at a subset (safer than under-fetching).
        """
        need_lower = information_need.lower()
        stores: List[str] = []
        if any(kw in need_lower for kw in ("fato", "fact", "concret", "imutáve", "imutav")):
            stores.append(STORE_FACTS)
        if any(kw in need_lower for kw in ("preferênc", "preferenc", "gosto", "comportamento", "feedback")):
            stores.append(STORE_PREFERENCES)
        if any(
            kw in need_lower
            for kw in ("insight", "procedimento", "procedural", "aprendizado", "skill", "habilidade")
        ):
            stores.append(STORE_INSIGHTS)
        return stores or list(ALL_STORES)

    def infer_user_state(self, task_instruction: str, raw_memories: List[Dict[str, Any]]) -> str:
        """Step 3 (User-State Inference Agent): joins the clues found across
        stores and consolidates them into a clean, deduplicated context block.
        Obsolete memories were already discarded by ConflictResolver at
        retrieval time, so this step only needs to synthesize what survived."""
        if not raw_memories:
            return "(No relevant memory found for this task.)"

        notes_block_parts = []
        for m in raw_memories:
            fm = m.get("frontmatter", {})
            date_str = fm.get("last_updated_at") or fm.get("created_at") or "Unknown date"
            if len(date_str) > 10:
                date_str = date_str[:10]  # Just YYYY-MM-DD to save tokens and keep it readable
            
            rels = m.get("related_ids", [])
            rels_str = f" | connected to: {', '.join(rels)}" if rels else ""
            
            header = f"[{m['type'].upper()} | {m['id']} | Updated at: {date_str}{rels_str} | score={m['score']:.3f}]"
            notes_block_parts.append(f"{header}\n{m['body']}")

        notes_block = "\n\n".join(notes_block_parts)

        return self.llm_fn(
            INFERENCE_AGENT_SYSTEM_PROMPT,
            f"Task instruction: {task_instruction}\n\n"
            f"Retrieved memory notes:\n{notes_block}\n\n"
            "Consolidate this focusing on the current state-of-the-art, evidencing the temporal evolution.",
        )

    # ------------------------------------------------------------------
    # Full pipeline
    # ------------------------------------------------------------------
    def run(self, task_instruction: str, top_n: int = 7, resolve_conflicts: bool = True, step_callback: Optional[Callable[[str, Any], None]] = None) -> OrchestratorResult:
        information_need = self.identify_information_need(task_instruction)
        if step_callback:
            step_callback("information_need", information_need)

        retrieval_query = self.plan_retrieval(information_need)
        if step_callback:
            step_callback("retrieval_query", retrieval_query)

        target_stores = self.plan_target_stores(information_need)
        if step_callback:
            step_callback("target_stores", target_stores)

        raw_memories: List[Dict[str, Any]] = []
        for store in target_stores:
            raw_memories.extend(
                self.engine.retrieve_from_store(
                    query_text=retrieval_query,
                    store=store,
                    top_n=top_n,
                    resolve_conflicts=resolve_conflicts,
                )
            )
        # Re-rank the merged, cross-store candidates by score and cap to top_n
        # overall (each store call already capped to top_n *per store*).
        raw_memories.sort(key=lambda m: m.get("score", 0.0), reverse=True)
        raw_memories = raw_memories[:top_n]

        if not raw_memories:
            # Fallback: try the original task instruction directly in case the
            # simulated/real planner rewrite drifted too far from the corpus.
            raw_memories = self.engine.retrieve_context(
                query_text=task_instruction, top_n=top_n, resolve_conflicts=resolve_conflicts
            )

        if step_callback:
            step_callback("raw_memories", raw_memories)

        consolidated_context = self.infer_user_state(task_instruction, raw_memories)
        if step_callback:
            step_callback("consolidated_context", consolidated_context)

        return OrchestratorResult(
            task_instruction=task_instruction,
            information_need=information_need,
            retrieval_query=retrieval_query,
            stores_queried=target_stores,
            raw_memories=raw_memories,
            consolidated_context=consolidated_context,
        )

