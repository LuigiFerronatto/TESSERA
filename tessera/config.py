"""Deterministic runtime configuration shared by TESSERA front-ends."""

from __future__ import annotations

import os
import warnings
from typing import Mapping, Optional


CANONICAL_STORAGE_ENV = "TESSERA_STORAGE_DIR"
LEGACY_STORAGE_ENV = "LAO_MEM_DIR"
DEFAULT_STORAGE_DIR = "./memories"


class LegacyStorageConfigurationWarning(FutureWarning):
    """Warns that a deprecated storage alias supplied the selected path."""


def resolve_storage_dir(
    explicit: Optional[str] = None,
    *,
    environ: Optional[Mapping[str, str]] = None,
    warn_legacy: bool = True,
) -> str:
    """Resolve storage with explicit/canonical/compatibility/fallback precedence."""

    if explicit:
        return explicit
    env = os.environ if environ is None else environ
    canonical = env.get(CANONICAL_STORAGE_ENV)
    if canonical:
        return canonical
    legacy = env.get(LEGACY_STORAGE_ENV)
    if legacy:
        if warn_legacy:
            warnings.warn(
                f"{LEGACY_STORAGE_ENV} is deprecated; set "
                f"{CANONICAL_STORAGE_ENV} instead. The compatibility alias "
                "will be removed in a future release.",
                LegacyStorageConfigurationWarning,
                stacklevel=2,
            )
        return legacy
    return DEFAULT_STORAGE_DIR
