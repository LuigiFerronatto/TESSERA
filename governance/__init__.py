"""Deterministic TESSERA repository-governance helpers.

This package is intentionally separate from the `tessera` runtime package
(see `pyproject.toml` -> `[tool.setuptools] packages = ["tessera"]`) and is
never included in a built wheel/sdist. It backs the deterministic merge
governor workflow (`.github/workflows/tessera-merge-governor.yml`) and is
covered by static governance tests in `tests/test_governance_workflows.py`.
"""
