# Typed model profiles (Issue #157 candidate)

Status: experimental candidate, not yet on `main`. No model is selected by
default. Configuring profiles does not enable semantic retrieval, reranking or
generation, and ordinary Engine/CLI/MCP retrieval remains deterministic.

## Capability, profile, provider, model

A consuming application references a capability and profile name. The profile
selects a provider and concrete model identity:

```text
ModelReference("embedding", "local-default")
  -> models.embeddings.local-default
  -> provider + backend + model + declared identity
```

The capability names are `embedding`, `generation`, `reranking`. Configuration
uses `embeddings`, `generation`, `reranking` groups. `EmbeddingProfile`,
`GenerationProfile` and `RerankingProfile` are distinct immutable types. A name
may be reused in different groups; resolution never searches another group or
falls back to a different provider. Changing generation cannot change embeddings.
This is the reference boundary for future stage wiring, not a pipeline-stage
implementation (#160).

## Project configuration

Add optional `models` to schema-v2 `.tessera/config.yaml`. These fictional IDs
illustrate structure; they are not defaults or recommendations for real models.

```yaml
schema_version: 2
store:
  id: 00000000-0000-0000-0000-000000000001
  path: memories
sources:
  roots:
    - path: memories
      include: ['**/*.md', '**/*.txt']
index:
  path: .tessera/index
models:
  embeddings:
    local-default:
      provider: local
      backend: sentence-transformers
      model: example/encoder
      dimensions: 384
      normalization: l2
    cloud:
      provider: google
      model: example-embedding-model
      credential:
        source: env
        variable: EXAMPLE_MODEL_KEY
  generation:
    fast:
      provider: openai-compatible
      endpoint: https://api.example.test/v1
      model: example-fast-model
      credential:
        source: env
        variable: EXAMPLE_MODEL_KEY
    reasoning:
      provider: anthropic
      model: example-reasoning-model
  reranking:
    local-default:
      provider: local
      backend: sentence-transformers
      model: ./model-files/cross-encoder
```

Every profile requires `provider` and a non-empty `model`. Common optional
identity fields: `model_revision`, `backend`, `device`, `fingerprint`.
`fingerprint` is a `sha256:` content digest with 64 hexadecimal digits.
Only embeddings accept positive-integer `dimensions` and `normalization`
(`none` or `l2`). Unknown fields, unsupported provider/capability pairs and
inline credential values fail validation. Empty/missing groups configure nothing.

Local profiles require a backend and reject credentials/network endpoints.
`backend` and `device` are local/custom fields. Local hub IDs such as
`organization/model` are opaque identifiers. Path-shaped IDs (`./`, `../`, `~/`
or absolute paths) can be resolved explicitly with `profile.local_path(base)`;
it performs no model load, download or existence check. For project-relative
models, pass the selected project's root. For named-global models, use an
absolute path or explicitly pass the registry directory. This explicit base
avoids secretly resolving a global model relative to the current project.
Model files are not automatically added to corpus sources.

## Named-global stores and compatibility

The same optional groups belong to an individual named registry entry:

```yaml
schema_version: 1
stores:
  research:
    id: 00000000-0000-0000-0000-000000000002
    path: /absolute/path/to/research
    models:
      generation:
        reasoning:
          provider: custom
          adapter: application-generator
          model: application-version-1
```

`GlobalRegistry.models` maps store names to `ModelProfiles`. Selecting one
entry copies only that entry's profiles into `ResolvedConfiguration.models`.
There is no global model fallback or profile inheritance. Store/source/index
selection precedence is unchanged: explicit path, environment, nearest project,
then explicitly named global entry. Explicit paths and environment selections
have no profiles. A nearby project continues to win over a global selection,
as before; its corpus and profiles are not combined with the registry.

Project v1 input remains unchanged and model-free. Its conservative v2
serialization does not add profiles. Reinitialization preserves existing
profiles, including when sources/store paths change. Removing one registry
entry leaves other entries' profiles intact. Configs without models serialize
as before. No index migration/rebuild is necessary for profile changes because
this candidate does not use models in retrieval.

## Provider schema support versus execution support

| Provider | Embedding | Generation | Reranking | Additional schema requirement |
|---|---|---|---|---|
| local | yes | yes | yes | explicit backend |
| google | yes | yes | no | none |
| openai | yes | yes | no | none |
| openai-compatible | yes | yes | no | explicit endpoint |
| anthropic | no | yes | no | none |
| custom | yes | yes | yes | explicit application adapter name |

These are supported schema classes, not a promise that a particular model,
endpoint or backend implements the capability. No provider SDK or concrete
provider adapter is bundled. Capability/model availability must be validated by
the selected application adapter; unknown model IDs cannot be verified offline.
Endpoints accept HTTPS or loopback HTTP, with no URL userinfo, query or fragment.
No outbound requests are made while parsing, inspecting or resolving profiles.

## Python resolution and explicit application adapters

```python
from tessera.config import ConfigurationResolver
from tessera.model_profiles import Capability, ModelAdapterRegistry, ModelReference

configuration = ConfigurationResolver(environ={}).resolve()
reference = ModelReference(Capability.EMBEDDING, "local-default")
profile = configuration.models.resolve(reference)
print(profile.identity())
print(profile.reproducibility_warnings())
```

`tessera config show --json` also includes configured profiles in
`storage_selection.models`. That inspection never resolves environment values
or loads optional stacks. Profile identities exclude the credential reference;
config output retains the reference so users can inspect it.

An application may explicitly register its own trusted factory:

```python
registry = ModelAdapterRegistry()
registry.register(
    Capability.EMBEDDING, "local", make_application_encoder,
    name="sentence-transformers",
)
adapter = registry.prepare(configuration.models, reference)
```

`name` must equal a local `backend`, a custom `adapter`, or remain absent for
hosted providers. Registration is per capability and cannot silently overwrite
an existing registration. Factory code receives the correctly typed profile,
not credential values. The application owns the returned adapter interface,
its dependency installation, secret access and any explicit execution. Config
strings never trigger dynamic module imports or executable code selection.

`prepare` is the explicit optional boundary. Only here does an environment
reference receive a presence check. A missing/blank variable returns
`ModelAvailabilityError.code == "missing_credential"`; absent factories return
`adapter_unavailable`; an adapter's `ImportError` becomes
`optional_dependency_unavailable` without echoing the underlying exception.
Other application errors propagate rather than silently changing semantics;
application adapters must redact their own errors and logs. Parsing a valid
unavailable profile does not prevent unrelated deterministic core use.

## Credentials and reproducibility

Only `credential: {source: env, variable: ENVIRONMENT_VARIABLE_NAME}` is
supported. Never put secrets in identity strings, URLs, source files, config
or ignore files. TESSERA does not persist environment values, add model
configuration to index metadata, or emit secret values in model validation
errors. No model credentials are needed for local profiles or deterministic
retrieval, and startup never probes provider credentials or imports SDKs.

`identity()` exposes declared provider/model/revision/backend/dimensions/
normalization/device/fingerprint when available, plus capability. No inference
is made that a name or release label is immutable. `reproducibility_warnings()`
reports `mutable_or_unpinned_model` unless a full 40/64-digit hexadecimal
revision or SHA-256 fingerprint was declared. It always also reports
`declared_identity_not_verified`: this layer has not fetched or verified model
bytes. Provider/model aliases and hardware behavior remain adapter concerns.

## Limits and rollback

This candidate provides no model inference, semantic retrieval (#158),
reranking (#159), pipeline stage activation (#160), presets (#161), integrated
doctor checks (#162), model download/cache lifecycle (#163) or quality claims.
No network/provider purchases, credentials or concrete model defaults are
required by the tests. `SMOKE_ONLY` is appropriate because ranking is unchanged.

Remove the optional `models` sections before returning to an older TESSERA
version whose schema rejects them. Removing a profile neither deletes model
files nor changes memory/source/index ownership. The draft stage record and PR
retain a pending decision until review, exact-head CI and canonical merge.
