# ADR 0003: Configuration and store discovery

- Status: Accepted for the Issue #117 implementation candidate
- Date: 2026-08-31
- Issue: [#117](https://github.com/LuigiFerronatto/TESSERA/issues/117)

## Context

TESSERA's validated runtime accepted an explicit storage path, then
`TESSERA_STORAGE_DIR`, then deprecated `LAO_MEM_DIR`, and finally
`./memories`. That contract made a chosen store consistent across current
surfaces (#93), but did not let an installed product persist or explain how a
project or named user store was chosen.

Configuration discovery is not memory discovery. TESSERA must not scan user
directories, combine projects, inspect provider credentials, or make Engine
responsible for product setup.

## Decision

Project configuration is `<project-root>/.tessera/config.yaml`:

```yaml
schema_version: 1
store:
  id: 2d850c58-8f47-4cb9-aeec-b915c7bc93fd
  path: memories
```

The schema is closed. `id` is a persisted UUID. A relative path is resolved
against the physical project root and may not contain `..`. An explicitly
configured absolute path is supported and remains visibly absolute. Storage
symlinks are canonicalized to their physical target. `.tessera_index/` stays
derived state inside the store and never owns project configuration.

The global registry is discovery metadata only:

```yaml
schema_version: 1
stores:
  research:
    id: 2d850c58-8f47-4cb9-aeec-b915c7bc93fd
    path: /absolute/path/to/research
```

Registry paths are canonical and absolute. Names, IDs, and paths may not form
ambiguous collisions. Re-registering the same name at a moved path preserves
its ID. No entry is selected merely because it exists, and unregister removes
only registry metadata.

The registry locations are:

- Linux: `$XDG_CONFIG_HOME/tessera/registry.yaml`, falling back to
  `~/.config/tessera/registry.yaml`;
- macOS: `~/Library/Application Support/tessera/registry.yaml`;
- Windows: `%APPDATA%\tessera\registry.yaml`, with the conventional roaming
  directory below the supplied home as fallback.

The reusable `StorageSelection` result records store ID, canonical path,
source, project root/config path, and registry name/path. Product selection
precedence is:

1. explicit path (`--store`, positional compatibility, or API argument);
2. `TESSERA_STORAGE_DIR`;
3. deprecated warning-emitting `LAO_MEM_DIR`;
4. nearest project config;
5. an explicitly named global entry;
6. actionable configuration failure.

Project discovery resolves the starting path physically and checks only the
exact `.tessera/config.yaml` marker at each ancestor. Nearest wins. It neither
enumerates directory contents nor scans `$HOME`. When starting below the home
directory, home itself is a stopping boundary; an explicitly selected home may
be a project. Filesystem root is the other boundary.

`tessera init` builds an inspectable mutation plan before writing. Explicit
project/global flags avoid unnecessary questions. A TTY with missing mode asks
project versus global, gathers only missing fields, prints the plan, and asks
for confirmation. Non-TTY or `--non-interactive` with missing choices exits 2,
does not call `input()`, and performs no mutation. `--dry-run` never writes.
The old positional `tessera init PATH` remains a compatibility alias for an
explicit store configured to the current project.

Config writes use a same-directory temporary file, validation, file fsync,
atomic replace, and directory fsync where supported. Config targets or config
directories that are symlinks are refused for mutation. Config files contain
data only and cannot request command execution or credentials.

`tessera config doctor` is read-only and diagnoses configuration/discovery.
The existing `tessera doctor` remains the broader installed runtime smoke test.
Quickstart retains its pre-#117 compatibility output, while `init` is the
authoritative configuration bootstrap.

## Migration policy

Explicit storage arguments and `TESSERA_STORAGE_DIR` remain supported.
`LAO_MEM_DIR` remains a lower-priority compatibility alias with its actionable
deprecation warning. Direct library `resolve_storage_dir()` and the pre-#120
MCP bootstrap retain historical `./memories` fallback for compatibility.
Configuration-aware operational CLI commands do not silently create a store
when no explicit/environment/project/named-global selection exists.

Migration is neither automatic nor destructive. Existing callers may continue
to pass a path or environment variable. Users opt into persisted discovery via
`tessera init`. Conflicting layers follow precedence and are visible through
`tessera config show`. Stale entries remain until explicitly updated or
unregistered; neither action moves or deletes memory.

## Boundaries and consequences

`TesseraEngine` consumes the selected absolute path. It does not walk projects,
read registries, prompt, or mutate configuration. MCP adoption and lifecycle
remain #120. Clean onboarding remains #118, broad CLI design #119, official
Skills #121, and publication #134. A global registry never becomes a global
memory database, and no cross-project merge is introduced.
