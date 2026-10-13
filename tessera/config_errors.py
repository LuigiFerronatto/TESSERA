"""Shared configuration error without importing runtime or optional adapters."""


class ConfigurationError(ValueError):
    """An invalid, missing, or unsafe configuration decision."""
