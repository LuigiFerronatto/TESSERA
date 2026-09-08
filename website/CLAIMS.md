# Published claim checklist

Verified 2026-09-05 against local HEAD and freshly fetched origin/main, both `708c973e23d5c4eb8a52d359a2cadc153e161a90`. Local files are authoritative; the browser's cached GitHub README predates source selection. No roadmap capability is promoted to shipped behavior.

| Published claim | Implementation and contract evidence |
| --- | --- |
| Text-first memory and evidence layer for agents | README introduction; `tessera/engine.py:TesseraEngine`; `examples/quickstart.py` |
| Markdown sources remain authoritative | `docs/ARCHITECTURE.md`; `tessera/engine_core.py:build_index`; `tests/test_canonical_compatibility.py` |
| Read/index sources, writable memory store, rebuildable index have different roles | README Quickstart; `tessera/config.py:ResolvedConfiguration`; `tests/test_issue_153_configuration_v2.py`; ADR 0003 |
| Relevant excerpts plus original content | `docs/OUTPUT_CONTRACT.md`; `tessera/engine_core.py:retrieve_context`; `tests/test_retrieval_ranking_evidence.py` |
| Source identity, version hashes, exact spans where provable | `tessera/evidence.py`; `tessera/engine.py`; `tests/test_evidence_ledger.py` |
| Inspectable relevance signals; score is not truth/confidence | OUTPUT_CONTRACT score semantics; `tests/test_retrieval_ranking_evidence.py` |
| Explicit links and related memory IDs | `tessera/models.py:Connection`; `engine_core.py:retrieve_context`; `examples/quickstart.py` |
| Python, CLI, optional MCP | `pyproject.toml` scripts and extras; `tessera/mcp_server.py:query_memories`; README Python API |
| Basic retrieval needs no generative model | README deliberate boundaries; ADR 0001; engine implementation |
| Temporal arbitration and automatic supersession are unfinished | README status; ARCHITECTURE implemented/planned; OUTPUT_CONTRACT absent fields; `tests/test_conflict_containment.py` and current main's containment fix |
| Python 3.9+; install from the repository | `pyproject.toml`; README Install. Do not use the unverified PyPI package name as an install instruction. |

Demo: fictional Project Atlas, two separate Markdown notes retained at once. September 1 says launch September 12; September 8 says moved to September 26. This is not source revision history, automatic supersession, or a live engine in the browser. `scripts/capture-example.py` writes these notes through the real public API, builds the index and verifies evidence/source/span/relations. The browser presents a deterministic illustrative sequence. The date conclusion is explicitly a reader interpretation.

The shown Python query is executed by that script against its prepared fixture. Its output is captured locally in `verification/retrieval.json`; no numeric ranking or fabricated source hash is marketed. Production domain is unknown: no canonical, absolute social URL or deployment configured. No paid assets, external publication, testimonials, adoption or speed comparisons.
