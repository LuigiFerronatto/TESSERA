"""
Tessera task hook — automatically intercepts a task and triggers the detective
trio (Need -> Planner -> Retrieval -> Inference) *before* the main agent acts,
instead of requiring every caller to remember to invoke the orchestrator by
hand.

This is the "in practice" piece of the 3-pillar memory architecture:

    1. Episodes    — memories are structured beginning/middle/end
       (see `tessera.models.Episode`), not one undifferentiated block.
    2. Typed stores — everything learned is filed into exactly 3 drawers:
       facts / preferences / insights (see `tessera.engine.STORE_*` +
       `TesseraEngine.write_fact/write_preference/write_insight`).
    3. The hook + detective trio — this module. When the consuming agent
       is about to run a task, `on_task_start` intercepts it, runs the
       3-agent orchestrator pipeline (Need -> Planner -> Inference) against
       the 3 typed stores, and returns a validated context block ready to
       inject into the main agent's prompt.

Usage — wrap any task execution:

    from tessera import TesseraEngine
    from tessera.hooks import TesseraTaskHook

    engine = TesseraEngine(storage_dir="./memories")
    hook = TesseraTaskHook(engine)

    context = hook.on_task_start("Como faço deploy do banco configurado pela Maria?")
    # -> inject `context.consolidated_context` into the main agent's prompt

    # ... main agent does the task ...

    hook.on_task_end(
        task_instruction="Como faço deploy do banco configurado pela Maria?",
        store="insights",
        summary="Descobri que o deploy falha se a porta 5432 já está em uso; "
                "checar com lsof antes de subir o serviço.",
    )

`on_task_end` is optional glue: it's a thin, explicit call for the caller to
record a new episodic memory once the task finishes (the hook does not try
to auto-infer *what* was learned — that judgment call stays with the calling
agent/human, consistent with Tessera's write-side gating philosophy of never
silently persisting unreviewed content).
"""

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from .engine import TesseraEngine
from .models import Entity, Episode
from .orchestrator import TesseraOrchestrator, LlmFn, OrchestratorResult

# A hook subscriber: called with the OrchestratorResult right after the
# detective trio finishes, before on_task_start returns. Lets callers log,
# emit metrics, or stream the reasoning steps without subclassing anything.
HookSubscriber = Callable[[OrchestratorResult], None]


@dataclass
class TaskInterceptionResult:
    """What `TesseraTaskHook.on_task_start` hands back to the calling agent."""

    consolidated_context: str
    information_need: str
    retrieval_query: str
    stores_queried: List[str]
    raw_memories: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "consolidated_context": self.consolidated_context,
            "information_need": self.information_need,
            "retrieval_query": self.retrieval_query,
            "stores_queried": self.stores_queried,
            "raw_memories": self.raw_memories,
        }


class TesseraTaskHook:
    """
    Intercepts a task instruction and runs the 3-agent detective pipeline
    (TesseraOrchestrator) automatically, so the calling agent doesn't need to
    manually decide when/how to query memory before acting.
    """

    def __init__(
        self,
        engine: TesseraEngine,
        llm_fn: Optional[LlmFn] = None,
        subscribers: Optional[List[HookSubscriber]] = None,
    ):
        self.engine = engine
        self._llm_fn = llm_fn
        self._orchestrator: Optional[TesseraOrchestrator] = None
        self.subscribers = list(subscribers or [])

    @property
    def orchestrator(self) -> TesseraOrchestrator:
        """Construct assisted orchestration only when an assisted call needs it."""
        if self._orchestrator is None:
            self._orchestrator = TesseraOrchestrator(self.engine, llm_fn=self._llm_fn)
        return self._orchestrator

    def subscribe(self, callback: HookSubscriber) -> None:
        """Registers a callback invoked with the raw OrchestratorResult on every
        `on_task_start` call — useful for logging/tracing/metrics."""
        self.subscribers.append(callback)

    # ------------------------------------------------------------------
    # The hook itself
    # ------------------------------------------------------------------
    def on_task_start(
        self,
        task_instruction: str,
        top_n: int = 7,
        resolve_conflicts: bool = True,
        llm_fn: Optional[LlmFn] = None,
    ) -> TaskInterceptionResult:
        """
        Call this the moment a task is about to start (this IS the hook —
        wire it into whatever task-dispatch mechanism the main agent uses,
        e.g. a PreToolUse-style hook, a middleware, or a plain function call
        at the top of the task handler).

        Runs, in order:
          1. Information-Need Agent — what history does this task need?
          2. Retrieval Planner Agent — which store(s) + what search query?
          3. Retrieval — pulls candidates from the relevant typed store(s),
             preserving possible-conflict history.
          4. User-State Inference Agent — consolidates retrieved memories
             into one clean, validated context block.

        `llm_fn`: overrides this call's LLM backend for the 3 pipeline
        steps, without needing to re-instantiate the hook/orchestrator.
        None (default) keeps the explicit `llm_fn` the hook was constructed
        with; if none exists, the assisted call fails before provider activity.

        Returns a `TaskInterceptionResult` ready to inject into the main
        agent's context/prompt.
        """
        self.engine.build_index()  # pick up any notes written since last run
        orchestrator = self.orchestrator
        if llm_fn is not None:
            orchestrator = TesseraOrchestrator(self.engine, llm_fn=llm_fn)
        result = orchestrator.run(
            task_instruction, top_n=top_n, resolve_conflicts=resolve_conflicts
        )

        for subscriber in self.subscribers:
            subscriber(result)

        return TaskInterceptionResult(
            consolidated_context=result.consolidated_context,
            information_need=result.information_need,
            retrieval_query=result.retrieval_query,
            stores_queried=result.stores_queried,
            raw_memories=result.raw_memories,
        )

    def on_task_end(
        self,
        task_instruction: str,
        store: str,
        summary: str,
        mem_id: Optional[str] = None,
        episode: Optional[Episode] = None,
        tags: Optional[List[str]] = None,
        entities: Optional[List[Entity]] = None,
    ) -> str:
        """
        Records what was learned once a task finishes, filing it into the
        given typed store (`tessera.engine.STORE_FACTS` / `STORE_PREFERENCES` /
        `STORE_INSIGHTS`). Pass `episode` to structure the note as
        beginning/middle/end instead of a single `summary` block — when both
        are given, `episode` takes precedence and `summary` is ignored.

        This is deliberately explicit (not auto-triggered): what actually
        gets persisted as a new memory is always a conscious decision by the
        calling agent, matching Tessera's write-side gating philosophy — the
        hook automates *retrieval*, never silent, unreviewed *writes*.
        """
        import hashlib

        if mem_id is None:
            digest = hashlib.sha1(task_instruction.encode("utf-8")).hexdigest()[:10]
            mem_id = f"episode_{digest}"

        content = episode.to_markdown_body() if episode is not None else summary

        write_fn = {
            "facts": self.engine.write_fact,
            "preferences": self.engine.write_preference,
            "insights": self.engine.write_insight,
        }.get(store)
        if write_fn is None:
            raise ValueError(
                f"store inválida: {store!r}. Use 'facts', 'preferences' ou 'insights'."
            )

        return write_fn(
            mem_id=mem_id,
            episode_id=mem_id,
            content=content,
            tags=tags or [],
            entities=entities or [],
        )

    def on_task_end_auto(
        self,
        task_instruction: str,
        episode: Episode,
        mem_id_prefix: Optional[str] = None,
        llm_fn: Optional[LlmFn] = None,
        tags: Optional[List[str]] = None,
    ) -> List[str]:
        """
        QUMem-style automatic alternative to `on_task_end`: instead of the
        caller manually picking ONE store for the whole episode, this
        mechanically decomposes the episode into N atomic memories across
        facts/preferences/insights (see `tessera.decomposer`) and writes each
        through the same gated typed-store path.

        `mem_id_prefix` MUST carry a domain prefix (e.g. "research/topic" or
        "project/some-run"); defaults to "episode_<sha1-of-task>" (bare, no
        domain) with a warning from the underlying write path if omitted —
        always pass an explicit, domain-prefixed prefix in real usage.

        `llm_fn` overrides the hook's own LLM backend just for this call
        (None keeps whatever the hook/orchestrator was constructed with —
        offline heuristic decomposition if none was ever configured).

        Returns the list of filepaths written (may be fewer than 3 if the
        episode didn't contain memories of every type — e.g. a purely
        factual episode produces zero preference/insight notes).
        """
        import hashlib

        from .decomposer import decompose_and_write

        if mem_id_prefix is None:
            digest = hashlib.sha1(task_instruction.encode("utf-8")).hexdigest()[:10]
            mem_id_prefix = f"episode_{digest}"

        resolved_llm_fn = llm_fn if llm_fn is not None else self._llm_fn

        return decompose_and_write(
            engine=self.engine,
            mem_id_prefix=mem_id_prefix,
            episode_id=mem_id_prefix,
            episode=episode,
            llm_fn=resolved_llm_fn,
            tags=tags,
        )
