# PR Evolution Audit — #120 MCP transport

## Canonical lifecycle

- Issue #120: CLOSED / IMPLEMENTED (VALIDATED pending canonical post-merge CI/Benchmark Ledger confirmation).
- Branch: `test-card/120-mcp-runtime-robustness`.
- Starting main: `a88600b491528cddb746bf909a303aefabf01e45`.
- #227/#228 merged and #227 closed before this branch started. Main
  [CI](https://github.com/LuigiFerronatto/TESSERA/actions/runs/34383633784) and
  [Benchmark Ledger](https://github.com/LuigiFerronatto/TESSERA/actions/runs/34383633763)
  succeeded on that SHA.
- Classification: runtime implementation; benchmark `SMOKE_ONLY`.
- Candidate: PR #229 head `09dff4d0fdeda0e761e3f9a4d6cb7d66a3b0f211`.
- Canonical merge: `b4ead4d7407b8caa2571e1e366616a468f2ef74f` (PR #229, merged into `main`).
- Decision: `KEEP`, from the independent Maintainer Audit on the exact candidate above,
  with no supported P0/P1 findings. Exact-head CI, Benchmark Ledger and Merge
  Governor all passed prior to merge.

## Delivery history consumed

| Delivery | Canonical merge | Capability consumed |
|---|---|---|
| #68/#98 evidence | `fb23012ba4b2fddc3912d7cb593391a04fe45ae7` | Lossless retrieval/evidence projection |
| #92/#108 write gate | `9ab03f7a52bb63ef8942cc8bf292a51ea90e5b05` | Admission, transformation and persistence result |
| #95/#126 runtime separation | `6d4a32b021dba7cbd7ac40244eaf6a6f7ce99599` | No implicit provider/backend probing |
| #116/#131 | `0dd6e5c8c3e720cc39b1e666abed98a9fa3357e4` | Wheel/sdist and optional dependency boundary |
| #117/#150 | `61cf76fbd6ed61972f0f5abae515ba9bffca4b55` | Canonical configuration and discovery |
| #153/#173 | `2508676d472088733702b6ed920fc829df9a7681` | Store/source/index separation |
| #135 decomposition | `c324ac2f46d48f7b49769b2fea9df0a2a93b42de` | Pure assisted/fallback result and canonical typed writers |
| #118/#225 | `0ee5bbfe3a4b6cd9ecbcbfbcfdbfa65620700c3d` | Clean installed onboarding; one runtime delivery |
| #227/#228 | `a88600b491528cddb746bf909a303aefabf01e45` | Lifecycle reconciliation; not runtime delivery |

## Every-tool and startup audit

| Surface | Before on audited main | Candidate boundary |
|---|---|---|
| Package import | Eager hook/orchestrator imports, no provider selected | Lazy compatible public optional exports |
| Server import | Resolve config, construct Engine, build disk index, construct hook | No config/filesystem/provider/SDK activity |
| Startup | Ambient config at import, shared eager globals | Explicit factory config, lifespan, isolated runtime, stdio only |
| `query_memories` | Lossless #68 results | Same Engine/projection, versioned transport envelope |
| `query_store` | Five-field projection lost evidence | Same ordered Engine results, lossless projection |
| `write_memory` | Canonical gated persistence/rebuild | Same gate/result, serialized commit ownership |
| `rebuild_index` | Unsynchronized graph mutation | Serialized Engine mutation |
| `get_index_composition` | Unsynchronized graph read | Serialized read |
| `query_memories_pipeline` | Optional resolver with no explicit selection; hook rebuild | Explicit lazy provider over disposable Engine snapshot |
| `decompose_episode` | Assisted failure could write deterministic fallback notes | Provider preparation completes before canonical gated commit; failed remote assistance does not write |
| `run_doctor` | Reconstructed only writable path | Retains full canonical configuration unless explicit override |
| `run_quickstart` | Canonical plan/apply | Same explicit apply, serialized; dry-run stays read-only |
| `memories://{id}` | Missing resource was successful text | Structured not-found; raw Markdown on success; reject changed symlink |
| `graph://index` | Unsynchronized graph stats | Serialized stats with versioned JSON |
| Health | No operational endpoint | Read-only `get_server_health` / `server://health` |

There is no ranking, candidate-set, graph algorithm, semantic drawer, memory
format, provider SDK or benchmark judge implementation in this change. The new
response envelope is an explicit transport migration; nested Engine data remains
lossless. Python/CLI #135 fallback semantics remain unchanged.

## Evidence

Clean baseline: **538 passed, 5 skipped**. An earlier simultaneous noneditable
install generated `build/lib` during inventory testing; its one environmental
failure was removed from baseline interpretation and the full clean baseline
was rerun. The direct before probe confirms import creates the store/index and
typed retrieval drops eight existing evidence/traceability fields.

Candidate: **542 passed, 5 skipped**, including four new ownership/real-protocol
checks; the earlier focused configuration/write/evidence matrix passed 144 tests.
Six historical static routing assertions were updated because #120 is now
IN_PROGRESS / NOW, with one active executable card and two ready executable cards.

The standalone stdio experiment passed **18 grouped protocol scenarios**, both
in development and from the clean installed wheel outside the checkout. It
covers handshake/negotiation, all ten tools, resources, strict arguments, evidence
parity, provider absence/failure/invalid output/timeout/cancellation, concurrent
queued/started writes and EOF during provider preparation/commit. Testing exposed
a duplicate-response failure after a cancelled shielded write; delivering pending
cancellation after the worker drains prevents the SDK from responding twice.
A second real protocol regression reproduced the same failure when that writer
raises `OSError`; the checkpoint now runs after lock release in `finally`,
covering worker success and failure. The full suite was rerun: 542 passed,
5 skipped, and all 18 scenarios passed in a newly created installed environment.

`python -m build` produced a 34-entry wheel and 44-entry sdist. The wheel's runtime
bytes match the checkout; the fresh MCP environment imports only installed
`site-packages`, contains all 42 public exports, MCP SDK 1.30.0 and no provider or
development dependencies. The base 3.9/3.12 artifact matrix remains a CI gate.

Sanity remains Hit@1 **0.75**, Hit@3/5 **1.00**, MRR **0.875**, evidence hit **1.00**,
417.75 average returned characters, with the missing-evidence check passing.
LongMemEval was not rerun: no retrieval/ranking implementation changed.
Project #9 dry-run after selecting #120 reported **changes = 0**.

[Versioned evidence](evidence/120-mcp/validation.json) records hashes, build method,
artifact inventories, installed location, protocol scenarios and quality metrics.
Exact-head CI, independent Maintainer Audit and Merge Governor evidence belongs
to the PR; none is inferred from the local checks.

The predecessor `02a411a30621593bfd4c17fb620b9499a79bc892` passed all six
[CI jobs](https://github.com/LuigiFerronatto/TESSERA/actions/runs/34387596857),
[Benchmark Ledger](https://github.com/LuigiFerronatto/TESSERA/actions/runs/34387596875)
and [independent KEEP](https://github.com/LuigiFerronatto/TESSERA/pull/229#issuecomment-5606666989).
The additional cancelled-writer-error regression and fix require fresh gates;
that predecessor audit does not carry to the new head.

## Remaining boundary

No #171 semantic API, #167 packet, #169 compiler, #121 Skills, release or owner/legal
decision is absorbed. No provider failure can schedule a late memory commit.
Started writes are not cancellable transactions; multi-note storage failures may
leave earlier admitted notes. #120 is `IMPLEMENTED` as of the canonical merge
`b4ead4d7407b8caa2571e1e366616a468f2ef74f`; it is not marked `VALIDATED` until
canonical post-merge CI/Benchmark Ledger evidence on that merge commit is
confirmed. Candidate and canonical merge count as one delivery.
