"""Deterministic source-format adapters for canonical text ingestion."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

import yaml


SUPPORTED_SOURCE_FORMATS = ("markdown", "text")
SOURCE_FORMAT_SUFFIXES = {
    ".md": "markdown",
    ".markdown": "markdown",
    ".txt": "text",
}
SUPPORTED_SOURCE_SUFFIXES = frozenset({".md", ".txt"})
RECURSIVE_SOURCE_PATTERNS = ("**/*.md", "**/*.txt")
NON_RECURSIVE_SOURCE_PATTERNS = ("*.md", "*.txt")


def source_format_for_path(path: Union[str, Path]) -> Optional[str]:
    """Return the canonical format for a supported source path."""
    return SOURCE_FORMAT_SUFFIXES.get(Path(path).suffix.lower())


def is_supported_source_path(path: Union[str, Path]) -> bool:
    """Return whether discovery and indexing admit the source suffix."""
    return Path(path).suffix.lower() in SUPPORTED_SOURCE_SUFFIXES


def split_markdown(raw_text: str) -> Tuple[Dict[str, Any], str]:
    """Split YAML frontmatter without silently accepting malformed metadata."""
    lines = raw_text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return {}, raw_text

    closing = None
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            closing = idx
            break
    if closing is None:
        raise ValueError("Malformed YAML frontmatter: opening '---' has no closing delimiter")

    frontmatter_raw = "".join(lines[1:closing])
    body = "".join(lines[closing + 1 :])
    try:
        parsed = yaml.safe_load(frontmatter_raw)
    except yaml.YAMLError as exc:
        raise ValueError(f"Malformed YAML frontmatter: {exc}") from exc
    if parsed is None:
        parsed = {}
    if not isinstance(parsed, dict):
        raise ValueError("Malformed YAML frontmatter: root must be a mapping")
    return parsed, body


def split_source(
    raw_text: str,
    *,
    path: Optional[Union[str, Path]] = None,
    source_format: Optional[str] = None,
) -> Tuple[Dict[str, Any], str]:
    """Return metadata and body according to the source's explicit format.

    Plain-text files are body-only documents. Text that happens to begin with
    ``---`` is never interpreted as YAML and the source is never rewritten.
    """
    resolved_format = source_format or (source_format_for_path(path) if path is not None else None)
    if resolved_format == "markdown":
        return split_markdown(raw_text)
    if resolved_format == "text":
        return {}, raw_text
    # Preserve the historical direct-parser behavior for callers that provide
    # an unknown extension. Source discovery and Engine iteration still admit
    # only the supported suffixes above.
    return {}, raw_text
