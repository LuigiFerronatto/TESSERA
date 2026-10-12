"""Deterministic source-format adapters; never authority or execution policy.

Adapters declare filename-derived classification defaults. Canonical normalization
still owns explicit metadata, source hashes/spans and write/retrieval semantics.
Registries are immutable values: registration returns a new registry, so one
consumer cannot change another consumer's default parsing behavior.
"""
from dataclasses import asdict, dataclass
import os
from typing import Dict, Optional, Tuple


@dataclass(frozen=True)
class AdapterMetadata:
    adapter_id: str
    document_type: str
    harness: Optional[str]
    evidence: str

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class HarnessAdapter:
    """Filename rules with explicit, inspectable defaults and no side effects.

    Match rules are case-insensitive basename rules, never directory discovery.
    A harness label identifies a file convention; it grants no trust/precedence.
    """
    adapter_id: str
    filenames: Tuple[str, ...] = ()
    suffixes: Tuple[str, ...] = ()
    prefixes: Tuple[str, ...] = ()
    document_type: str = "harness_instructions"
    harness: Optional[str] = None

    def __post_init__(self) -> None:
        if not isinstance(self.adapter_id, str) or not self.adapter_id.strip():
            raise ValueError("Adapter ID must be a nonempty string")
        if self.document_type not in {"harness_instructions", "skill_instructions"}:
            raise ValueError("Instruction adapters cannot create semantic memory drawers")
        if self.harness is not None and (not isinstance(self.harness, str) or not self.harness.strip()):
            raise ValueError("Harness must be a nonempty string or None")
        for field in ("filenames", "suffixes", "prefixes"):
            values = getattr(self, field)
            if isinstance(values, str):
                raise ValueError("Filename rules must be a sequence of strings")
            normalized = []
            for value in values:
                if not isinstance(value, str) or not value or "/" in value or "\\" in value:
                    raise ValueError("Filename rules must be nonempty basenames")
                normalized.append(value.lower())
            object.__setattr__(self, field, tuple(sorted(set(normalized))))
        if not (self.filenames or self.suffixes or self.prefixes):
            raise ValueError("An instruction adapter needs at least one filename rule")

    def matches(self, filename: str) -> bool:
        name = filename.lower()
        return (name in self.filenames
                or any(name.endswith(s) for s in self.suffixes)
                or any(name.startswith(p) for p in self.prefixes))

    def metadata(self, filename: str) -> AdapterMetadata:
        return AdapterMetadata(self.adapter_id, self.document_type, self.harness,
                               "filename:" + filename)


def _generic_metadata(filename: str) -> AdapterMetadata:
    """Preserve the pre-registry generic classification contract exactly."""
    name = filename.lower()
    if "decision" in name or name.startswith("adr"):
        document_type = "decision_record"
    elif "experiment" in name:
        document_type = "experiment_record"
    elif "report" in name:
        document_type = "report"
    elif name == "readme.md":
        document_type = "project_context"
    else:
        document_type = "memory"
    return AdapterMetadata("generic", document_type, None, "filename:" + filename)


@dataclass(frozen=True)
class HarnessAdapterRegistry:
    adapters: Tuple[HarnessAdapter, ...] = ()

    def __post_init__(self) -> None:
        adapters = tuple(self.adapters)
        if any(not isinstance(a, HarnessAdapter) for a in adapters):
            raise TypeError("Registry entries must be HarnessAdapter values")
        names = [a.adapter_id for a in adapters]
        if len(set(names)) != len(names) or "generic" in names:
            raise ValueError("Adapter IDs must be unique; generic is reserved")
        object.__setattr__(self, "adapters", tuple(sorted(adapters, key=lambda a: a.adapter_id)))

    def register(self, adapter: HarnessAdapter) -> "HarnessAdapterRegistry":
        return HarnessAdapterRegistry(self.adapters + (adapter,))

    def inspect(self, filepath: str) -> AdapterMetadata:
        filename = os.path.basename(os.fspath(filepath))
        matches = [a for a in self.adapters if a.matches(filename)]
        if len(matches) > 1:
            raise ValueError("Ambiguous instruction adapters: " + ", ".join(a.adapter_id for a in matches))
        return matches[0].metadata(filename) if matches else _generic_metadata(filename)


DEFAULT_HARNESS_ADAPTERS = HarnessAdapterRegistry((
    HarnessAdapter("agents", filenames=("AGENTS.md",)),
    HarnessAdapter("claude", filenames=("CLAUDE.md",), harness="claude"),
    HarnessAdapter("gemini", filenames=("GEMINI.md",), harness="gemini"),
    HarnessAdapter("copilot", filenames=("copilot-instructions.md",), harness="copilot"),
    HarnessAdapter("skill", filenames=("SKILL.md",), suffixes=(".skill.md",),
                   prefixes=("sk_",), document_type="skill_instructions"),
))
