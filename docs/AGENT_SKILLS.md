# Official TESSERA agent Skills bundle

Candidate for [#121](https://github.com/LuigiFerronatto/TESSERA/issues/121).
Bundle schema/version: `1`. Distribution: `tessera-agent-memory`.

Five small, provider-neutral Skills teach existing public operations:

| Skill | Purpose |
|---|---|
| tessera-init | Explicit source/store selection, dry-run, authorized apply and partial-failure verification |
| tessera-write | Canonical write gate, actual persistence, stable identity and no blind retry |
| tessera-query | Bounded deterministic evidence retrieval with provenance and empty-result handling |
| tessera-doctor | Read-only configuration/corpus diagnostics and accurate exit-code interpretation |
| tessera-benchmark | Reproduce checkout-only deterministic sanity and separate required quality runs |

Each folder contains a standard `SKILL.md` with name, trigger description,
compatibility metadata, exact supported commands, output interpretation and
failure/safety boundaries. No provider credentials, runtime-specific hook
installation, retrieval implementation or final-answer policy is bundled.

## Read or package the resources

The wheel and sdist contain `tessera/agent_skills/<name>/SKILL.md`.
The read-only Python API works without the optional MCP or LLM extras:

```python
from tessera.agent_skills import (
    AGENT_SKILL_BUNDLE_VERSION, list_agent_skill_names, read_agent_skill,
)

assert AGENT_SKILL_BUNDLE_VERSION == "1"
for name in list_agent_skill_names():
    text = read_agent_skill(name)
    # Hand this folder/name and SKILL.md text to the user's chosen skill loader.
```

Loading resources never copies files to a project, changes an agent runtime,
installs hooks, writes memories, or executes example commands. To install a Skill,
use the chosen consumer's supported folder/skill-loader procedure and an explicitly
approved destination. Do not assume a universal hidden home-directory location.
Unknown names and path traversal are rejected by the reader API.

`tessera skills list/install` retains its existing meaning: bundled semantic
procedural-anchor notes. It does not install this agent instruction bundle.
Those five old anchor resources and their behavior remain unchanged.

## Compatibility and boundaries

The bundle targets the current public `0.0.3` contracts; feature detection is
required because a version string alone does not identify a particular build.
Check command help and required result fields, and handle errors explicitly.
The presence of `tessera.agent_skills` plus bundle version `1` identifies this
bundle. Older installs without that module cannot be assumed to contain it.

The query Skill explicitly handles the known empty-corpus JSON limitation in
some builds through a same-scope public Python fallback; it does not treat plain
diagnostic output as evidence. The read-only doctor Skill uses `corpus doctor`,
not the separate write/read smoke doctor. A write result is checked via the
current flat `admission`/`persisted` JSON fields. MCP users must discover the
current schema and inspect the result envelope.

The benchmark Skill requires a source checkout: benchmark code/data are still
excluded from the runtime package. No model, dataset, private-corpus upload or
paid inference is implied by reading a Skill. No future Context Compiler,
Working Context, semantic Agent API or full QUMem state capability is claimed.

## Reproducible validation

```bash
python -m pytest tests/test_agent_skills_bundle.py tests/test_packaging_contract.py -q
python -m pytest -ra
python -m build
```

Tests execute the actual shell examples extracted from the Skills against an
isolated synthetic project: dry-run leaves bytes/mtimes unchanged, authorized
apply selects the intended store, write yields truthful flat JSON, query returns
the saved evidence, diagnostics do not mutate the project, rejected writes stay
absent, and the benchmark command emits real four-query metrics. Resource loading
is read-only, unknown names cannot escape the bundle, and existing procedural
anchors remain a separate package contract.

Artifact checks compare every SKILL.md byte across checkout, sdist and wheel and
exercise the installed resource API outside the source checkout. This validates
the package and commands; it does not claim broad agent task-success improvements
or native integration certification for every skill-capable runtime.
