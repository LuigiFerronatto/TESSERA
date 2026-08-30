"""Versioned benchmark ledger and deterministic comparison utilities."""

from .schema import SCHEMA_VERSION, validate_record

__all__ = ["SCHEMA_VERSION", "validate_record"]
