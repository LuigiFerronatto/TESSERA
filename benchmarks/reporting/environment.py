"""Capture and compare the pinned forward benchmark environment."""

import hashlib
import importlib.metadata
import json
import platform
import sys
from pathlib import Path
from typing import Any, Callable, Dict, Mapping, Optional


PACKAGE_FIELDS = {
    "numpy_version": "numpy",
    "scipy_version": "scipy",
    "scikit_learn_version": "scikit-learn",
    "networkx_version": "networkx",
    "pyyaml_version": "PyYAML",
}
FINGERPRINT_FIELDS = (
    "python_implementation", "python_version", "python_full_version", "os",
    "platform", "architecture", "numpy_version", "scipy_version",
    "scikit_learn_version", "networkx_version", "pyyaml_version",
    "constraints_file", "constraints_sha256",
)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def environment_fingerprint(environment: Mapping[str, Any]) -> str:
    """Hash only normalized, declared environment identity fields."""
    payload = {name: environment[name] for name in FINGERPRINT_FIELDS}
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return _sha256_bytes(encoded)


def runtime_probe() -> Mapping[str, str]:
    """Return runtime facts; injectable as a unit in record tests."""
    values = {
        "python_implementation": platform.python_implementation(),
        "python_version": platform.python_version(),
        "python_full_version": " ".join(sys.version.split()),
        "os": platform.system(),
        "platform": platform.platform(),
        "architecture": platform.machine(),
    }
    for field, distribution in PACKAGE_FIELDS.items():
        values[field] = importlib.metadata.version(distribution)
    return values


def collect_environment(
    constraints_path: Path,
    *,
    repository_dirty: bool,
    repository_root: Path,
    probe: Optional[Callable[[], Mapping[str, str]]] = None,
) -> Dict[str, Any]:
    """Build the complete schema-1.1 environment record."""
    constraints = constraints_path.resolve()
    root = repository_root.resolve()
    try:
        relative_constraints = constraints.relative_to(root).as_posix()
    except ValueError as exc:
        raise ValueError("constraints file must be inside the repository") from exc
    if not constraints.is_file():
        raise ValueError(f"constraints file does not exist: {relative_constraints}")
    if repository_dirty:
        raise ValueError("dirty worktree cannot produce a versioned benchmark record")
    environment: Dict[str, Any] = dict((probe or runtime_probe)())
    missing = sorted(set(FINGERPRINT_FIELDS[:-2]) - set(environment))
    if missing:
        raise ValueError(f"environment probe missing fields: {', '.join(missing)}")
    environment.update(
        {
            "repository_dirty": False,
            "repository_root": ".",
            "constraints_file": relative_constraints,
            "constraints_sha256": _sha256_bytes(constraints.read_bytes()),
            "complete": True,
        }
    )
    environment["fingerprint_sha256"] = environment_fingerprint(environment)
    return environment


def validate_environment_reference(
    record: Mapping[str, Any], reference: Mapping[str, Any]
) -> Dict[str, Any]:
    """Reject environment drift even when paired worktrees drift together."""
    current = record["environment"]
    expected = reference["environment"]
    if not current.get("complete") or not expected.get("complete"):
        raise ValueError("forward environment comparison requires complete records")
    checks = {
        "constraints_sha256": (
            expected["constraints_sha256"], current["constraints_sha256"]
        ),
        "fingerprint_sha256": (
            expected["fingerprint_sha256"], current["fingerprint_sha256"]
        ),
    }
    drift = {
        name: {"expected": before, "actual": after}
        for name, (before, after) in checks.items()
        if before != after
    }
    if drift:
        fields = ", ".join(sorted(drift))
        raise ValueError(f"forward benchmark environment drift: {fields}")
    return {
        "compatible": True,
        "constraints_sha256": current["constraints_sha256"],
        "fingerprint_sha256": current["fingerprint_sha256"],
        "reference_record_id": reference["record_id"],
    }
