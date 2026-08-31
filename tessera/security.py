"""Deterministic write-side detection, transformation, and admission policy.

This module implements a narrow, auditable hostile-pattern gate. It is not a
semantic prompt-injection classifier. Decisions are completed before any
canonical memory, index, graph, registry, or Evidence Ledger mutation.
"""

from dataclasses import dataclass
from enum import Enum
import hashlib
import re
from typing import Any, Dict, List, Optional, Sequence, Tuple


class WriteAdmission(str, Enum):
    ACCEPT = "accept"
    ACCEPT_SANITIZED = "accept_sanitized"
    REJECT = "reject"
    REVIEW = "review"


REDACTION_MARK = "[CONTEÚDO REMOVIDO POR INFRAÇÃO DE SEGURANÇA]"

HOSTILE_PATTERNS: Tuple[Tuple[str, str], ...] = (
    ("ignore_previous_instructions_pt", r"ignore as (?:instruções|instrucoes|regras) anteriores"),
    ("change_primary_directive_pt", r"mude sua diretriz principal"),
    ("hostile_system_role_pt", r"aja como um sistema hostil"),
    ("delete_memories_pt", r"delete todas as memórias"),
    ("hate_directive_pt", r"você deve odiar"),
    ("pretend_role_pt", r"finja ser"),
    ("ignore_previous_instructions_en", r"ignore (?:all |the )?previous instructions"),
    ("disregard_prior_rules_en", r"disregard (?:all |the )?prior (?:rules|instructions)"),
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
    "empty_content": 0,
    "hostile_instruction_detected": 10,
    "suspicious_tag_detected": 20,
    "documentary_context_detected": 30,
    "hostile_instruction_redacted": 40,
    "hostile_pattern_remains": 50,
    "manual_review_required": 60,
    "safe_content": 70,
}


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


def _redact_directives(content: str) -> str:
    transformed = content
    for _reason, pattern in HOSTILE_PATTERNS:
        transformed = re.sub(rf"(?i){pattern}[^\n]*", REDACTION_MARK, transformed)
    return transformed


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
        elif self.admission in {WriteAdmission.REJECT, WriteAdmission.REVIEW}:
            if has_candidate or self.persisted_hash is not None or self.content_changed:
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
            transformed = _redact_directives(content_text)
            if transformed != content_text and not contains_hostile_pattern(transformed):
                return WriteGateDecision(
                    True, True, WriteAdmission.ACCEPT_SANITIZED,
                    _ordered_reasons(("hostile_instruction_detected", "hostile_instruction_redacted")),
                    original_hash, content_sha256(transformed), threat_score, transformed,
                )
            return WriteGateDecision(
                True, False, WriteAdmission.REVIEW,
                _ordered_reasons(("hostile_instruction_detected", "hostile_pattern_remains", "manual_review_required")),
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

    def audit_and_sanitize(self, content_text: str, tags: List[str]) -> Tuple[str, float, bool]:
        """Compatibility projection; review/reject is never accepted by the Engine."""
        decision = self.evaluate(content_text, tags)
        candidate = decision.persistence_candidate
        return (content_text if candidate is None else candidate, decision.threat_score, decision.is_sanitized)
