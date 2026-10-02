"""Opt-in typed model identities and application-owned adapter resolution.

Parsing and inspection are offline: no credential lookup, SDK imports, model
loads or downloads. A profile never enables a pipeline stage. Applications may
register factories explicitly; no provider implementation is bundled here.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field, fields
from enum import Enum
from pathlib import Path
from types import MappingProxyType
from typing import Any, Callable, ClassVar, Dict, Mapping, Optional, Tuple, Union
from urllib.parse import urlsplit

from .config_errors import ConfigurationError


class Capability(str, Enum):
    EMBEDDING = "embedding"
    GENERATION = "generation"
    RERANKING = "reranking"


# Schema support is distinct from installed runtime adapters.
PROVIDER_CAPABILITIES = MappingProxyType({
    "local": frozenset(Capability),
    "google": frozenset({Capability.EMBEDDING, Capability.GENERATION}),
    "openai": frozenset({Capability.EMBEDDING, Capability.GENERATION}),
    "openai-compatible": frozenset({Capability.EMBEDDING, Capability.GENERATION}),
    "anthropic": frozenset({Capability.GENERATION}),
    "custom": frozenset(Capability),
})
_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\Z")
_ENV = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")
_DIGEST = re.compile(r"sha256:[0-9a-fA-F]{64}\Z")
_COMMIT = re.compile(r"[0-9a-fA-F]{40}|[0-9a-fA-F]{64}\Z")


def _name(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not _NAME.fullmatch(value):
        raise ConfigurationError(f"{field_name} must be a simple non-empty name")
    return value


def _text(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip() or any(ord(c) < 32 for c in value):
        raise ConfigurationError(f"{field_name} must be a non-empty, single-line string")
    return value


def _closed(value: Any, allowed: set, context: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ConfigurationError(f"{context} must be a mapping")
    if any(not isinstance(key, str) or key not in allowed for key in value):
        # Never interpolate rejected keys or values: they may contain secrets.
        raise ConfigurationError(f"{context} contains unsupported fields; use only documented fields")
    return value


@dataclass(frozen=True)
class CredentialReference:
    source: str
    variable: str

    def __post_init__(self) -> None:
        if self.source != "env":
            raise ConfigurationError("credential.source must be env; inline credentials are forbidden")
        if not isinstance(self.variable, str) or not _ENV.fullmatch(self.variable):
            raise ConfigurationError("credential.variable must be an environment variable name")

    @classmethod
    def from_mapping(cls, value: Any) -> "CredentialReference":
        raw = _closed(value, {"source", "variable"}, "credential")
        if set(raw) != {"source", "variable"}:
            raise ConfigurationError("credential requires source and variable")
        return cls(raw["source"], raw["variable"])

    def to_mapping(self) -> Dict[str, str]:
        return {"source": self.source, "variable": self.variable}


@dataclass(frozen=True)
class ModelReference:
    """A stage-facing capability/profile pair, independent of vendor names."""

    capability: Capability
    profile: str

    def __post_init__(self) -> None:
        try:
            object.__setattr__(self, "capability", Capability(self.capability))
        except (TypeError, ValueError):
            raise ConfigurationError("unknown model capability") from None
        _name(self.profile, "profile")


@dataclass(frozen=True)
class ModelProfile:
    provider: str
    model: str
    model_revision: Optional[str] = None
    backend: Optional[str] = None
    device: Optional[str] = None
    fingerprint: Optional[str] = None
    credential: Optional[CredentialReference] = None
    endpoint: Optional[str] = None
    adapter: Optional[str] = None
    capability: ClassVar[Capability]

    def __post_init__(self) -> None:
        if type(self) is ModelProfile:
            raise ConfigurationError("choose an embedding, generation or reranking profile")
        if not isinstance(self.provider, str) or self.provider not in PROVIDER_CAPABILITIES:
            raise ConfigurationError("unknown model provider; choose a documented provider or custom")
        if self.capability not in PROVIDER_CAPABILITIES[self.provider]:
            raise ConfigurationError("provider does not support this model capability")
        _text(self.model, "model")
        for name in ("model_revision", "backend", "device", "fingerprint", "adapter"):
            value = getattr(self, name)
            if value is not None:
                _text(value, name)
        if self.credential is not None and not isinstance(self.credential, CredentialReference):
            raise ConfigurationError("credential must be an environment reference")
        if self.fingerprint is not None and not _DIGEST.fullmatch(self.fingerprint):
            raise ConfigurationError("fingerprint must be a sha256 content digest")
        if self.provider == "local":
            if self.credential is not None or self.endpoint is not None:
                raise ConfigurationError("local profiles cannot have credentials or network endpoints")
            if not self.backend:
                raise ConfigurationError("local profiles require an explicit backend")
        elif self.provider != "custom" and (self.backend is not None or self.device is not None):
            raise ConfigurationError("backend and device are local/custom profile fields")
        if self.provider == "custom":
            _name(self.adapter, "custom adapter")
        elif self.adapter is not None:
            raise ConfigurationError("adapter is only valid for custom providers")
        if self.endpoint is not None:
            if self.provider not in {"openai-compatible", "custom"}:
                raise ConfigurationError("endpoint is only valid for compatible/custom providers")
            _text(self.endpoint, "endpoint")
            try:
                url = urlsplit(self.endpoint)
                valid = bool(url.hostname) and not (url.username or url.password or url.query or url.fragment)
                valid = valid and (url.scheme == "https" or (url.scheme == "http" and url.hostname in {"localhost", "127.0.0.1", "::1"}))
                _ = url.port
            except ValueError:
                valid = False
            if not valid:
                raise ConfigurationError("endpoint must be HTTPS (or loopback HTTP), without credentials, query or fragment")
        if self.provider == "openai-compatible" and self.endpoint is None:
            raise ConfigurationError("openai-compatible profiles require an explicit endpoint")

    def to_mapping(self) -> Dict[str, Any]:
        result = {item.name: getattr(self, item.name) for item in fields(self) if getattr(self, item.name) is not None}
        if self.credential is not None:
            result["credential"] = self.credential.to_mapping()
        return result

    def identity(self) -> Dict[str, Any]:
        """Inspectable model identity; credential references are not identity."""
        return {"capability": self.capability.value, **{
            key: value for key, value in self.to_mapping().items() if key != "credential"
        }}

    def reproducibility_warnings(self) -> Tuple[str, ...]:
        # A revision label or model name alone does not prove immutable content.
        # Even a supplied digest is a declaration, not a downloaded-file check.
        if self.fingerprint or (self.model_revision and _COMMIT.fullmatch(self.model_revision)):
            return ("declared_identity_not_verified",)
        return ("mutable_or_unpinned_model", "declared_identity_not_verified")

    def local_path(self, base: Path) -> Optional[Path]:
        """Resolve an explicitly path-shaped local model without touching it."""
        if self.provider != "local":
            return None
        path = Path(self.model)
        prefixes = ("./", "../", "~/", "." + os.sep, ".." + os.sep, "~" + os.sep)
        if path.is_absolute() or self.model.startswith(prefixes):
            path = path.expanduser()
            return Path(os.path.abspath(path if path.is_absolute() else base / path))
        return None  # e.g. organization/model is a hub identifier, not a path


@dataclass(frozen=True)
class EmbeddingProfile(ModelProfile):
    dimensions: Optional[int] = None
    normalization: Optional[str] = None
    capability: ClassVar[Capability] = Capability.EMBEDDING

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.dimensions is not None and (type(self.dimensions) is not int or self.dimensions <= 0):
            raise ConfigurationError("embedding dimensions must be a positive integer")
        if self.normalization is not None and self.normalization not in ("none", "l2"):
            raise ConfigurationError("embedding normalization must be none or l2")


@dataclass(frozen=True)
class GenerationProfile(ModelProfile):
    capability: ClassVar[Capability] = Capability.GENERATION


@dataclass(frozen=True)
class RerankingProfile(ModelProfile):
    capability: ClassVar[Capability] = Capability.RERANKING


Profile = Union[EmbeddingProfile, GenerationProfile, RerankingProfile]
_GROUPS = {"embeddings": EmbeddingProfile, "generation": GenerationProfile, "reranking": RerankingProfile}


@dataclass(frozen=True)
class ModelProfiles:
    embeddings: Mapping[str, EmbeddingProfile] = field(default_factory=dict)
    generation: Mapping[str, GenerationProfile] = field(default_factory=dict)
    reranking: Mapping[str, RerankingProfile] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for group, expected in _GROUPS.items():
            profiles = getattr(self, group)
            if not isinstance(profiles, Mapping):
                raise ConfigurationError("model profile groups must be mappings")
            for name, profile in profiles.items():
                _name(name, "model profile name")
                if type(profile) is not expected:
                    raise ConfigurationError("model profile has the wrong capability type")
            object.__setattr__(self, group, MappingProxyType(dict(profiles)))

    def __deepcopy__(self, memo: Dict[int, Any]) -> "ModelProfiles":
        # Frozen profiles and copied read-only groups are safe to share across
        # the MCP runtime's disposable Engine snapshots.
        return self

    @classmethod
    def from_mapping(cls, value: Any) -> "ModelProfiles":
        raw = _closed(value, set(_GROUPS), "models")
        groups = {}
        for group, profile_type in _GROUPS.items():
            items = raw.get(group, {})
            if not isinstance(items, Mapping):
                raise ConfigurationError("model profile group must be a mapping")
            parsed = {}
            for name, candidate in items.items():
                _name(name, "model profile name")
                record = dict(_closed(candidate, {item.name for item in fields(profile_type)}, "model profile"))
                if "provider" not in record or "model" not in record:
                    raise ConfigurationError("model profile requires provider and model")
                if "credential" in record:
                    record["credential"] = CredentialReference.from_mapping(record["credential"])
                parsed[name] = profile_type(**record)
            groups[group] = parsed
        return cls(**groups)

    def to_mapping(self) -> Dict[str, Any]:
        return {group: {name: profile.to_mapping() for name, profile in sorted(getattr(self, group).items())}
                for group in _GROUPS if getattr(self, group)}

    def resolve(self, reference: ModelReference) -> Profile:
        if not isinstance(reference, ModelReference):
            raise ConfigurationError("resolve requires a typed ModelReference")
        group = "embeddings" if reference.capability == Capability.EMBEDDING else reference.capability.value
        try:
            return getattr(self, group)[reference.profile]
        except KeyError:
            raise ConfigurationError("unknown model profile for requested capability; configure it in models") from None


class ModelAvailabilityError(RuntimeError):
    """An explicitly selected optional model cannot be prepared."""

    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


class ModelAdapterRegistry:
    """Explicit application factories keyed by capability, provider and backend.

    register() and prepare() never auto-import a configured module name. The
    application owns trusted factories and their capability-specific interfaces.
    prepare() checks only the selected reference, not other configured models.
    """

    def __init__(self) -> None:
        self._factories: Dict[tuple, Callable[[Profile], Any]] = {}

    def register(self, capability: Capability, provider: str, factory: Callable[[Profile], Any], *, name: Optional[str] = None) -> None:
        try:
            capability = Capability(capability)
        except (TypeError, ValueError):
            raise ConfigurationError("unknown model capability") from None
        if not isinstance(provider, str) or provider not in PROVIDER_CAPABILITIES or capability not in PROVIDER_CAPABILITIES[provider]:
            raise ConfigurationError("unsupported provider capability")
        if not callable(factory):
            raise ConfigurationError("adapter factory must be callable")
        if name is not None:
            _text(name, "adapter name")
        key = (capability, provider, name)
        if key in self._factories:
            raise ConfigurationError("adapter already registered for this provider capability")
        self._factories[key] = factory

    def prepare(self, profiles: ModelProfiles, reference: ModelReference, *, environ: Optional[Mapping[str, str]] = None) -> Any:
        profile = profiles.resolve(reference)
        if profile.credential is not None:
            env = os.environ if environ is None else environ
            # The value is used only as a presence check, never stored/returned.
            if not env.get(profile.credential.variable, "").strip():
                raise ModelAvailabilityError("missing_credential", "Set the environment variable named by the selected credential reference before preparing this model")
        key = (profile.capability, profile.provider, profile.adapter or profile.backend)
        factory = self._factories.get(key)
        if factory is None:
            raise ModelAvailabilityError("adapter_unavailable", "Register an application adapter for the selected capability, provider and backend/adapter name; configuration alone does not install one")
        try:
            return factory(profile)
        except ImportError:
            raise ModelAvailabilityError("optional_dependency_unavailable", "Install the optional dependencies required by the selected application adapter, then retry") from None
