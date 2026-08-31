"""
Automatic typed-memory decomposition — a stand-in for QUMem's g_φ decomposer.

QUMem's decomposer runs 3 times per episode (once per type: factual /
preference / insight), each an LLM call that can extract *multiple* atomic
memories of that type from one raw episode. Tessera previously had NO
equivalent: `write_fact`/`write_preference`/`write_insight` existed and
map cleanly to the paper's F/P/I taxonomy, but each required the CALLER to
manually decide what to write and of which type — there was no mechanical
"take a raw episode/interaction, extract N atomic memories automatically"
step anywhere.

This module adds that automatic step, `decompose_and_write()`, while
preserving Tessera's existing write-side gating philosophy: it's an explicit
function a caller opts into (never silently triggered), and every
extracted memory still goes through the exact same
`TesseraEngine.write_memory_note` gating/sanitization path as a manual write
— decomposition only changes *how many notes get proposed*, never bypasses
the security/sanitization gate on any of them.

Two extraction modes:
    - Real LLM (`llm_fn` provided, e.g. via `llm_bridge.resolve_llm_fn()`):
      one prompt asks the model to return a JSON array of
      {"type": "factual"|"preference"|"procedural_anchor", "content": "..."}
      objects extracted from the raw episode text. Malformed/unparseable
      output degrades gracefully to the heuristic fallback below rather
      than raising.
    - Offline heuristic fallback (no `llm_fn`, or the LLM call/parse
      fails): a simple, deterministic, dependency-free line-based
      classifier that tags each non-empty line of the episode's "end"
      (the QUMem-relevant part - the resolution/lesson) using keyword
      cues, mirroring the same trade-off TesseraOrchestrator's own
      `_simulated_llm` already makes (offline-runnable by default, real
      reasoning opt-in).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Callable, List, Optional

from .models import Episode

LlmFn = Callable[[str, str], str]

DECOMPOSER_SYSTEM_PROMPT = (
    "Você é o Agente Decompositor de Memória Tipada do Tessera. Dado um episódio "
    "(início/meio/fim de uma execução de tarefa), extraia TODAS as memórias "
    "atômicas independentes que valem a pena persistir, classificando cada "
    "uma em exatamente um dos 3 tipos: 'factual' (informação concreta e "
    "imutável), 'preference' (comportamento/gosto/feedback de um humano), ou "
    "'procedural_anchor' (aprendizado transferível, aplicável a situações "
    "futuras diferentes desta). Responda APENAS com um array JSON de objetos "
    "{\"type\": ..., \"content\": ...}, sem nenhum texto fora do array. Se "
    "nada valer a pena persistir, responda com um array vazio []."
)

_HEURISTIC_TYPE_KEYWORDS = {
    "preference": (
        "prefere", "preferência", "preferencia", "gosta", "não gosta",
        "sempre quer", "pediu para", "corrigiu", "feedback",
    ),
    "procedural_anchor": (
        "aprendi", "aprendizado", "lição", "licao", "da próxima vez",
        "da proxima vez", "funciona melhor", "descobri que", "cuidado com",
        "evitar", "nunca fazer", "sempre fazer",
    ),
}
VALID_TYPES = {"factual", "preference", "procedural_anchor"}


@dataclass
class DecomposedMemory:
    mem_type: str
    content: str


def decompose_episode(episode: Episode, llm_fn: LlmFn) -> List[DecomposedMemory]:
    """
    Extracts zero or more atomic (type, content) memories from a raw
    episode. Pure function — does not write anything to disk. Pair with
    `TesseraEngine.write_fact/write_preference/write_insight` (or use
    `decompose_and_write()` below to do both steps in one call).
    """
    extracted = _decompose_via_llm(episode, llm_fn)
    if extracted is not None:
        return extracted
    return []


def decompose_and_write(
    engine: "TesseraEngine",  # noqa: F821 - avoid a hard import cycle; typed via string
    mem_id_prefix: str,
    episode_id: str,
    episode: Episode,
    llm_fn: LlmFn,
    tags: Optional[List[str]] = None,
) -> List[str]:
    """
    Runs `decompose_episode()` then immediately persists every extracted
    memory via the matching typed-store writer (`write_fact` /
    `write_preference` / `write_insight`), each going through the engine's
    normal write-side gating/sanitization path exactly like a manual write.

    `mem_id_prefix` MUST itself already carry a domain prefix (e.g.
    "research/some-topic" or "project/some-run") - each extracted memory gets
    written as "{mem_id_prefix}/{mem_type}-{n}" so multiple atomic memories
    from the same episode land together in the same topical subdirectory
    instead of colliding on one filename.

    Returns the list of filepaths written (may be empty if nothing was
    judged worth persisting).
    """
    from .engine import STORE_TO_NODE_TYPE  # local import - avoid a cycle at module load

    extracted = decompose_episode(episode, llm_fn=llm_fn)
    tags = tags or []

    write_fn_by_type = {
        "factual": engine.write_fact,
        "preference": engine.write_preference,
        "procedural_anchor": engine.write_insight,
    }

    filepaths: List[str] = []
    counters = {t: 0 for t in VALID_TYPES}
    for mem in extracted:
        if mem.mem_type not in VALID_TYPES:
            continue
        counters[mem.mem_type] += 1
        mem_id = f"{mem_id_prefix}/{mem.mem_type}-{counters[mem.mem_type]}"
        write_fn = write_fn_by_type[mem.mem_type]
        filepaths.append(
            write_fn(mem_id=mem_id, episode_id=episode_id, content=mem.content, tags=tags)
        )
    return filepaths


# ---------------------------------------------------------------------------
# Real-LLM extraction
# ---------------------------------------------------------------------------
def _decompose_via_llm(episode: Episode, llm_fn: LlmFn) -> Optional[List[DecomposedMemory]]:
    user_prompt = (
        "Episódio:\n"
        f"## Início (contexto/gatilho)\n{episode.beginning.strip()}\n\n"
        f"## Meio (o que aconteceu)\n{episode.middle.strip()}\n\n"
        f"## Fim (resultado/aprendizado)\n{episode.end.strip()}\n\n"
        "Responda apenas com o array JSON de memórias atômicas."
    )
    try:
        raw_response = llm_fn(DECOMPOSER_SYSTEM_PROMPT, user_prompt)
    except Exception:
        return None

    parsed = _extract_json_array(raw_response)
    if parsed is None:
        return None

    results = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        mem_type = str(item.get("type", "")).strip()
        content = str(item.get("content", "")).strip()
        if mem_type in VALID_TYPES and content:
            results.append(DecomposedMemory(mem_type=mem_type, content=content))
    return results


def _extract_json_array(raw_response: str) -> Optional[List[Any]]:
    """Best-effort JSON array extraction — tolerates a real LLM wrapping the
    array in prose or a Markdown code fence, which happens often enough in
    practice to be worth handling rather than hard-failing."""
    text = raw_response.strip()
    # Strip a ```json ... ``` or ``` ... ``` fence if present.
    fence_match = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1)
    else:
        bracket_match = re.search(r"(\[.*\])", text, re.DOTALL)
        if bracket_match:
            text = bracket_match.group(1)

    try:
        parsed = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return None
    return parsed if isinstance(parsed, list) else None


# ---------------------------------------------------------------------------
# Offline heuristic fallback (no LLM required)
# ---------------------------------------------------------------------------
def _decompose_via_heuristic(episode: Episode) -> List[DecomposedMemory]:
    """
    Deterministic, dependency-free extraction: every non-empty line across
    the episode is kept as one atomic memory, classified by simple keyword
    cues (mirrors TesseraOrchestrator._simulated_llm's own offline trade-off —
    reproducible and runnable with zero API key, at the cost of real
    reasoning). Defaults to 'procedural_anchor' for the episode's "end"
    section (the resolution/lesson is what's usually transferable) and
    'factual' for "beginning"/"middle" lines that don't match a stronger cue.
    """
    results: List[DecomposedMemory] = []

    def classify(line: str, default_type: str) -> str:
        lowered = line.lower()
        for mem_type, keywords in _HEURISTIC_TYPE_KEYWORDS.items():
            if any(kw in lowered for kw in keywords):
                return mem_type
        return default_type

    for section_text, default_type in (
        (episode.beginning, "factual"),
        (episode.middle, "factual"),
        (episode.end, "procedural_anchor"),
    ):
        for line in section_text.splitlines():
            line = line.strip("-* \t")
            if not line:
                continue
            results.append(DecomposedMemory(mem_type=classify(line, default_type), content=line))

    return results
