"""Deterministic write-side detection, transformation, and admission policy.

This module implements a narrow, auditable hostile-pattern gate. It is not a
semantic prompt-injection classifier. Decisions are completed before any
canonical memory, index, graph, registry, or Evidence Ledger mutation.
"""

from dataclasses import dataclass
from enum import Enum
import hashlib
from pathlib import Path, PureWindowsPath
import re
import unicodedata
from typing import Any, Dict, List, Optional, Sequence, Tuple


class WriteAdmission(str, Enum):
    ACCEPT = "accept"
    ACCEPT_SANITIZED = "accept_sanitized"
    REJECT = "reject"
    REVIEW = "review"


REDACTION_MARK = "[CONTEÚDO REMOVIDO POR INFRAÇÃO DE SEGURANÇA]"

HOSTILE_PATTERNS: Tuple[Tuple[str, str], ...] = (
    ("ignore_previous_instructions_pt", r"ignore\s+as\s+(?:instruções|instrucoes|regras)\s+anteriores"),
    ("change_primary_directive_pt", r"mude\s+sua\s+diretriz\s+principal"),
    ("hostile_system_role_pt", r"aja\s+como\s+um\s+sistema\s+hostil"),
    ("delete_memories_pt", r"delete\s+todas\s+as\s+memórias"),
    ("hate_directive_pt", r"você\s+deve\s+odiar"),
    ("pretend_role_pt", r"finja\s+ser"),
    ("ignore_previous_instructions_en", r"ignore\s+(?:(?:all|the)\s+)?previous\s+instructions"),
    ("disregard_prior_rules_en", r"disregard\s+(?:(?:all|the)\s+)?prior\s+(?:rules|instructions)"),
)

# Backward-compatible public pattern list.
MALICIOUS_PATTERNS = [rf"(?i){pattern}" for _reason, pattern in HOSTILE_PATTERNS]
SUSPICIOUS_TAGS = {"override", "root", "bypass", "malicious", "malicious_injection"}
DOCUMENTARY_MARKERS = re.compile(
    r"(?i)\b(?:security research|security analysis|documentary example|quoted example|"
    r"pesquisa de segurança|analise de segurança|análise de segurança|exemplo documentado)\b"
)
HASH_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
REASON_ORDER = {
    "invalid_memory_id_or_path": 0,
    "empty_content": 10,
    "hostile_instruction_detected": 20,
    "suspicious_tag_detected": 30,
    "documentary_context_detected": 40,
    "direct_hostile_instruction_rejected": 50,
    "hostile_instruction_redacted": 60,
    "hostile_pattern_remains": 70,
    "manual_review_required": 80,
    "safe_content": 90,
}

WINDOWS_RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{number}" for number in range(1, 10)),
    *(f"LPT{number}" for number in range(1, 10)),
}
WINDOWS_FORBIDDEN_CHARACTERS = frozenset('<>:"\\|?*')
WHOLE_CONTENT_REDACTION_RULE = "whole_content_redaction_v1"


def content_sha256(content: str) -> str:
    """Hash the exact UTF-8 content payload crossing the write-gate boundary."""
    return "sha256:" + hashlib.sha256(content.encode("utf-8")).hexdigest()


def _ordered_reasons(reasons: Sequence[str]) -> Tuple[str, ...]:
    return tuple(sorted(set(reasons), key=lambda item: (REASON_ORDER.get(item, 999), item)))


def _hostile_matches(content: str) -> List[Tuple[str, re.Match]]:
    matches: List[Tuple[str, re.Match]] = []
    for reason, pattern in HOSTILE_PATTERNS:
        match = re.search(pattern, content, flags=re.IGNORECASE)
        if match is not None:
            matches.append((reason, match))
    return matches


def contains_hostile_pattern(content: str) -> bool:
    return bool(_hostile_matches(content))


def _is_documentary(content: str, matches: Sequence[Tuple[str, re.Match]]) -> bool:
    if DOCUMENTARY_MARKERS.search(content):
        return True
    for _reason, match in matches:
        line_start = content.rfind("\n", 0, match.start()) + 1
        line_end = content.find("\n", match.end())
        if line_end == -1:
            line_end = len(content)
        line = content[line_start:line_end].lstrip()
        if line.startswith(">"):
            return True
        prefix = content[: match.start()]
        suffix = content[match.end() :]
        if prefix.count("```") % 2 == 1:
            return True
        if prefix.count('"') % 2 == 1 and '"' in suffix:
            return True
        if prefix.count("'") % 2 == 1 and "'" in suffix:
            return True
    return False


@dataclass(frozen=True)
class MemoryPathValidation:
    valid: bool
    destination: Optional[Path]
    reason: Optional[str]


def validate_memory_path(storage_dir: str, memory_id: str) -> MemoryPathValidation:
    """Resolve a portable logical ID to a contained Markdown destination.

    Validation follows existing symlinks and rejects destinations outside the
    resolved storage root. The result is computed before any write-side
    mutation. Forward slashes are the only accepted logical separator.
    """
    invalid = MemoryPathValidation(False, None, "invalid_memory_id_or_path")
    if not isinstance(memory_id, str) or not memory_id:
        return invalid
    if "\x00" in memory_id or "\\" in memory_id:
        return invalid
    if memory_id.startswith("/") or memory_id.endswith("/") or "//" in memory_id:
        return invalid
    windows_path = PureWindowsPath(memory_id)
    if windows_path.drive or windows_path.root or windows_path.is_absolute():
        return invalid

    segments = memory_id.split("/")
    if any(segment in {"", ".", ".."} for segment in segments):
        return invalid
    for segment in segments:
        if unicodedata.normalize("NFC", segment) != segment:
            return invalid
        if segment.endswith((" ", ".")):
            return invalid
        if any(ord(character) < 32 or character in WINDOWS_FORBIDDEN_CHARACTERS for character in segment):
            return invalid
        if segment.split(".", 1)[0].upper() in WINDOWS_RESERVED_NAMES:
            return invalid

    try:
        root = Path(storage_dir).resolve(strict=False)
        candidate = root.joinpath(*segments).with_name(segments[-1] + ".md")
        destination = candidate.resolve(strict=False)
    except (OSError, RuntimeError):
        return invalid
    try:
        relative = destination.relative_to(root)
    except ValueError:
        return invalid
    if not relative.parts or destination == root:
        return invalid

    # Reject case-fold aliases while walking existing parents. This prevents
    # one logical ID from naming different files on case-sensitive and
    # case-insensitive supported platforms.
    logical_parent = root
    try:
        for segment in segments[:-1]:
            resolved_parent = logical_parent.resolve(strict=False)
            resolved_parent.relative_to(root)
            if logical_parent.is_dir():
                collisions = [
                    child.name for child in logical_parent.iterdir()
                    if child.name.casefold() == segment.casefold() and child.name != segment
                ]
                if collisions:
                    return invalid
            logical_parent = logical_parent / segment
        if logical_parent.is_dir():
            expected_name = segments[-1] + ".md"
            if any(
                child.name.casefold() == expected_name.casefold()
                and child.name != expected_name
                for child in logical_parent.iterdir()
            ):
                return invalid
    except (OSError, RuntimeError, ValueError):
        return invalid
    return MemoryPathValidation(True, destination, None)


@dataclass(frozen=True)
class WriteGateDecision:
    threat_detected: bool
    content_changed: bool
    admission: WriteAdmission
    reasons: Tuple[str, ...]
    original_hash: str
    persisted_hash: Optional[str]
    threat_score: float
    persistence_candidate: Optional[str] = None
    transformation_rule: Optional[str] = None

    def __post_init__(self) -> None:
        if not HASH_RE.fullmatch(self.original_hash):
            raise ValueError("original_hash must be sha256:<64 lowercase hexadecimal characters>")
        if self.persisted_hash is not None and not HASH_RE.fullmatch(self.persisted_hash):
            raise ValueError("persisted_hash must be null or sha256:<64 lowercase hexadecimal characters>")
        if self.reasons != _ordered_reasons(self.reasons):
            raise ValueError("reasons must be unique and deterministically ordered")

        has_candidate = self.persistence_candidate is not None
        candidate_hash = content_sha256(self.persistence_candidate) if has_candidate else None
        if candidate_hash != self.persisted_hash:
            raise ValueError("persisted_hash must hash the exact UTF-8 persistence candidate")
        if self.content_changed != (has_candidate and self.original_hash != self.persisted_hash):
            raise ValueError("content_changed must equal original_hash != persisted_hash")

        if self.admission == WriteAdmission.ACCEPT:
            if not has_candidate or self.content_changed or self.original_hash != self.persisted_hash:
                raise ValueError("accept requires an unchanged persistence candidate")
        elif self.admission == WriteAdmission.ACCEPT_SANITIZED:
            if not has_candidate or not self.content_changed:
                raise ValueError("accept_sanitized requires changed persisted content")
            if contains_hostile_pattern(self.persistence_candidate or ""):
                raise ValueError("accept_sanitized cannot retain a confirmed hostile pattern")
            if (
                self.transformation_rule != WHOLE_CONTENT_REDACTION_RULE
                or self.persistence_candidate != REDACTION_MARK
            ):
                raise ValueError("accept_sanitized requires a complete bounded transformation")
        elif self.admission in {WriteAdmission.REJECT, WriteAdmission.REVIEW}:
            if (
                has_candidate
                or self.persisted_hash is not None
                or self.content_changed
                or self.transformation_rule is not None
            ):
                raise ValueError("reject/review cannot carry an accepted persistence candidate")

    @property
    def is_sanitized(self) -> bool:
        return self.admission == WriteAdmission.ACCEPT_SANITIZED and self.content_changed

    def to_dict(self) -> Dict[str, Any]:
        return {
            "threat_detected": self.threat_detected,
            "content_changed": self.content_changed,
            "admission": self.admission.value,
            "reasons": list(self.reasons),
            "original_hash": self.original_hash,
            "persisted_hash": self.persisted_hash,
            "threat_score": self.threat_score,
            "is_sanitized": self.is_sanitized,
        }


@dataclass(frozen=True)
class WriteResult:
    memory_id: str
    filepath: Optional[str]
    persisted: bool
    decision: WriteGateDecision

    def __post_init__(self) -> None:
        accepted = self.decision.admission in {
            WriteAdmission.ACCEPT,
            WriteAdmission.ACCEPT_SANITIZED,
        }
        if self.persisted != accepted:
            raise ValueError("persisted must match an accepted admission")
        if self.persisted != (self.filepath is not None):
            raise ValueError("filepath must exist if and only if persistence succeeded")

    def to_dict(self) -> Dict[str, Any]:
        payload = {"memory_id": self.memory_id, "filepath": self.filepath, "persisted": self.persisted}
        payload.update(self.decision.to_dict())
        return payload


class WriteGatingEngine:
    """Narrow deterministic policy for known hostile instruction patterns."""

    def __init__(self, toxicity_threshold: float = 0.3):
        self.toxicity_threshold = toxicity_threshold

    def evaluate(self, content_text: str, tags: List[str]) -> WriteGateDecision:
        original_hash = content_sha256(content_text)
        if not content_text.strip():
            return WriteGateDecision(
                False, False, WriteAdmission.REJECT, ("empty_content",),
                original_hash, None, 0.01,
            )

        matches = _hostile_matches(content_text)
        suspicious_tags = sorted({tag.lower() for tag in tags} & SUSPICIOUS_TAGS)
        threat_score = round(0.01 + (1.10 * len(matches)) + (0.20 * len(suspicious_tags)), 12)

        if matches and _is_documentary(content_text, matches):
            return WriteGateDecision(
                True, False, WriteAdmission.REVIEW,
                _ordered_reasons(("hostile_instruction_detected", "documentary_context_detected", "manual_review_required")),
                original_hash, None, threat_score,
            )

        if matches:
            return WriteGateDecision(
                True, False, WriteAdmission.REJECT,
                _ordered_reasons(("hostile_instruction_detected", "direct_hostile_instruction_rejected")),
                original_hash, None, threat_score,
            )

        if suspicious_tags:
            return WriteGateDecision(
                True, False, WriteAdmission.REVIEW,
                _ordered_reasons(("suspicious_tag_detected", "manual_review_required")),
                original_hash, None, threat_score,
            )

        return WriteGateDecision(
            False, False, WriteAdmission.ACCEPT, ("safe_content",),
            original_hash, original_hash, threat_score, content_text,
        )

    def reject_invalid_memory_id(self, content_text: str) -> WriteGateDecision:
        """Return a fail-closed decision without running content admission."""
        return WriteGateDecision(
            False, False, WriteAdmission.REJECT, ("invalid_memory_id_or_path",),
            content_sha256(content_text), None, 0.0,
        )

    def audit_and_sanitize(self, content_text: str, tags: List[str]) -> Tuple[str, float, bool]:
        """Compatibility projection; review/reject is never accepted by the Engine."""
        decision = self.evaluate(content_text, tags)
        candidate = decision.persistence_candidate
        return (content_text if candidate is None else candidate, decision.threat_score, decision.is_sanitized)
