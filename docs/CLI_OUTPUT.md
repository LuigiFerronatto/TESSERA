# CLI output contract, version 1

Candidate delivery for [#166](https://github.com/LuigiFerronatto/TESSERA/issues/166)
and the bounded current-surface audit in [#119](https://github.com/LuigiFerronatto/TESSERA/issues/119).
This changes presentation, not Engine retrieval, source selection, admission,
provider activation, persistence, or MCP contracts.

## One result, three renderers

Commands emit `CommandResult(kind, data, exit_code)`. `data` is the domain result:
Rich and plain consume the same message source; JSON serializes that exact data.
`UiEvent(code, level, fields)` carries advisory diagnostics on stderr. Interactive
initialization adapts the existing #155 plan and numbered source picker through
safe presentation helpers. It does not implement another source-discovery policy.

Existing query JSON remains an array of **complete Engine hits**, including body,
evidence, scores, provenance and related IDs. Init/write/config/corpus JSON shapes
are retained, including their existing schema versions and compatibility fields.
New commands expose their semantic dictionaries/lists. There is deliberately no
new outer envelope around successful legacy payloads. An empty query is `[]` with
exit 0. Text/TSV/path-only output remains human/tool convenience, not a replacement
for the [retrieval contract](OUTPUT_CONTRACT.md).

## Global options and terminal behavior

All parser levels accept these options before or after the command/group:

| Option/context | Behavior |
|---|---|
| interactive stdout TTY | Width-aware Rich text hierarchy; source text is literal, never Rich markup |
| redirected stdout | Stable plain lines, regardless of `FORCE_COLOR`; never cursor control |
| `--plain` | Plain lines; no tables, panels, banners or animations except explicitly requested `banner` text |
| `--no-color`, `NO_COLOR`, `TESSERA_NO_COLOR` | Rich layout where available, no ANSI color; environment presence includes an empty value |
| `--json` | Exactly one valid JSON value on stdout, also on parser/config/provider/read/internal failure and `--help`; diagnostics only on stderr |
| `--quiet` | Suppress progress/advisory detail; keep essential results, warnings, errors and mutation-plan disclosures; never truncate JSON |
| `--verbose` | Resolved store/configuration diagnostics and additional IDs/counts; diagnostics stay on stderr |
| `--debug` | Developer traceback on stderr on failures; query ranking breakdown; never corrupt JSON stdout |
| `--lang en` | Explicit English catalog; overrides `TESSERA_LANG` |
| missing Rich | Plain fallback; domain semantics do not depend on Rich |
| ASCII-only encoding | Safe escaped human text and ASCII JSON escapes that decode losslessly |

Version 1 supports **English only**. Unsupported explicit languages fail with an
actionable usage error, rather than mixing catalogs. PT-BR/system-locale selection
and saved language preferences remain future catalog work. Localized domain data
and source content are not translated or changed in JSON.

Only the explicit `tessera update` command performs an update check. Ordinary
commands and `--version` no longer initiate advisory network/cache work. This keeps
read-only dashboard/version inspection deterministic and avoids hidden startup IO.

Long `index`, init-apply and assisted-context operations emit one delayed stage
line after 300 ms. Fast operations stay silent. Stages use no spinner/live region,
work in pipes, and cancel their timer before completion or exception. JSON stage
diagnostics require `--verbose`. No per-file animation or full-screen selector is
introduced. Init always uses the same numbered source selection in Rich/plain.

## Dashboard, diagnostics and search

`tessera` and `tessera status [--project PATH]` inspect project configuration and
consume the read-only Corpus Doctor. The established environment-store precedence
is honored and displayed explicitly, including when no project config exists.
They never construct an Engine, write a
config, create a store, rebuild an index, download a model, or probe a provider.
They report missing or stale index state without silently repairing it. Counts
are inspected source/metadata counts, not invented retrieval confidence.

`tessera doctor` retains its established runtime smoke semantics: it can rebuild
derived index state and perform temporary write probes. Use `config doctor`,
`corpus doctor` or `status` for read-only diagnostics. This change does not silently
make the existing runtime doctor an alias for the read-only corpus audit.

Human query defaults are compact numbered hits, source paths and up to 240
characters of selected evidence/body. `--full` displays full memory bodies;
`--explain` displays relevance-score components, explicitly **not confidence**;
`--show-related` displays related IDs. `--no-body` and `--paths-only` remain.
These options never remove fields from JSON.

## Safe interactions

Existing interactive init foregrounds the current config, store and index before
asking whether to keep it and update the index, change/reselect, or cancel. Keep
passes the existing resolved configuration to indexing and preserves config/source
selection bytes. Changing configuration retains #155's complete reviewable plan.

`--yes` applies only to a fully specified `init --non-interactive` plan. It does not
choose a missing project/global target or source policy, bypass `--update-existing`,
install an update, accept a model download, or configure a provider. It is rejected
on other commands. `init --dry-run` remains zero-mutation; `quickstart` remains a
plan unless `--apply` is supplied. Unsupported `--dry-run` uses fail before running
a command instead of pretending the command is non-mutating.

JSON never prompts. `update --json` requires `--check`; installation still requires
explicit interactive confirmation. Ctrl+C/EOF during init prompts retain #155's
pre-apply cancellation result. Interruption after apply has begun reports that
state must be inspected before retrying; presentation does not claim transaction
atomicity beyond the owning operation's contract.

Untrusted source text and file names cannot inject Rich markup or terminal
CSI/OSC/control sequences into human output. JSON preserves original evidence with
standard escapes. Credentials are not prompted for or written to project config.

## Errors and stable exit categories

New operational errors use:

```json
{"schema_version":1,"error":{"code":"filesystem_error","message":"...","suggested_command":"...","context":{"config":"...","store":"..."}},"exit_code":4}
```

No expected error prints a traceback without `--debug`. Internal-error messages
omit raw exception details by default. Established init preflight/partial-apply
and admission payloads remain compatible; consumers must retain their documented
command-specific handling instead of assuming all errors have identical fields.

| Exit | Category / compatibility meaning |
|---|---|
| 0 | Success, including empty query/list; inspect the result for emptiness |
| 1 | Existing failed diagnostic status or init cancelled before apply |
| 2 | Invalid usage/configuration; retained write rejection and strict corpus-warning status |
| 3 | Existing init partial-apply failure, with truthful partial-state fields |
| 4 | Read/filesystem operation failure outside a command's established partial-state contract |
| 5 | Optional provider missing, invalid, timed out or failed |
| 70 | Unexpected internal error |
| 130 | Ctrl+C/EOF outside the pre-apply init prompt compatibility path |

Exit 2's legacy categories deliberately share an integer; structured error codes
separate `invalid_usage` from `configuration_error`. Splitting these historical
integers would break callers. Empty retrieval does not become an error merely to
reserve a “no results” integer. Diagnostic statuses remain command-specific.

## Scope audit and evidence

- [Complete parser-derived command/option inventory](evidence/166/command-inventory.json)
- [Before/after real-terminal and pipe captures](evidence/166/terminal-snapshots.txt), at 60/80/120 columns; ANSI escapes stripped only in the saved readable transcript
- [Five-run version-startup smoke](evidence/166/startup.json), same environment, update checks disabled; descriptive measurement, not a performance claim
- `tests/test_issue_166_presentation.py`: real PTYs, no-color/plain/JSON, 1/3/20 hits, warning/error JSON, safe text, ASCII-only subprocess, delayed-stage cleanup, Ctrl+C, dry-run, repeated init, and configuration-byte preservation

### Current command taxonomy

| Surface | Purpose / effect | Machine payload |
|---|---|---|
| no args, status | Read-only project overview | dashboard dictionary |
| init | Review/apply explicit project/global setup | established #155 plan/result/partial state |
| index | Update derived index | nodes, edges, incremental stats, paths, warnings |
| query | Retrieve evidence; established index build/cache behavior | complete Engine hit array |
| list | Inventory indexed notes | ID/type/filename/filepath array |
| stats | Inspect index composition; established index build behavior | type counts and edges |
| write | Canonical gated memory write | established admission/write result |
| skills list/install | Bundled procedural-anchor IDs/install | ID list / installed paths |
| start | Explicit optional assisted reasoning | complete orchestrator result |
| decompose | Explicit optional extraction with canonical fallback | paths and decomposition mode/result |
| doctor | Existing runtime smoke including probes/index | existing DoctorReport dictionary |
| corpus doctor | Read-only source/evidence/index audit | existing versioned CorpusDoctorReport |
| config show/list/doctor | Read-only selection, registry and configuration checks | established config payloads |
| config unregister | Remove one named registry entry; retain store | established unregister payload |
| quickstart | MCP configuration plan, apply only explicitly | existing QuickstartPlan dictionary |
| banner, --version | Explicit identity/version | name/tagline / version |
| update --check | Advisory release check | installed/latest; null means no newer result was established |

### Explicit remaining #119/#166 integration boundaries

The [#119 reconciliation comment](https://github.com/LuigiFerronatto/TESSERA/issues/119#issuecomment-5504150323)
requires future surfaces only after their owning semantics are validated:

- integration/automatic-lifecycle status: #177/#178/#196
- intelligence profile selection and health: #157–#165
- enrichment preview/cost/status: #176
- pending review/admission workflow: #19
- cross-capability unified configuration/status: the above owning cards

This candidate does not invent `integrate`, `review`, AI-provider/model-download,
secure-keyring, automatic-learning or stale semantic-context states. The current
source/index/configuration surfaces and existing optional assisted commands are
rendered truthfully. Future capabilities can emit the same result/event model.
