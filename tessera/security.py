"""
Write-side gating engine — prevents State Contamination / Memory Laundering
by auditing and sanitizing content *before* it is ever persisted to disk.
"""

import re
from typing import List, Tuple

# Common patterns for hostile instruction injection / prompt contamination.
MALICIOUS_PATTERNS = [
    r"(?i)ignore as instruções anteriores",
    r"(?i)ignore as regras anteriores",
    r"(?i)mude sua diretriz principal",
    r"(?i)aja como um sistema hostil",
    r"(?i)delete todas as memórias",
    r"(?i)você deve odiar",
    r"(?i)finja ser",
    r"(?i)ignore (all |the )?previous instructions",
    r"(?i)disregard (all |the )?prior (rules|instructions)",
]

# Tags that signal a bypass/override attempt and should raise the threat score.
SUSPICIOUS_TAGS = {"override", "root", "bypass", "malicious", "malicious_injection"}

REDACTION_MARK = "[CONTEÚDO REMOVIDO POR INFRAÇÃO DE SEGURANÇA]"


class WriteGatingEngine:
    """
    Security engine for memory validation and sanitization (write-side gating).
    Prevents state contamination and "memory laundering" by scanning content
    for hostile instruction injections before a note is persisted physically.
    """

    def __init__(self, toxicity_threshold: float = 0.3):
        self.toxicity_threshold = toxicity_threshold

    def audit_and_sanitize(self, content_text: str, tags: List[str]) -> Tuple[str, float, bool]:
        """
        Analyzes memory content for hostile instruction injections, contradictory
        prompts, or latent toxicity before the note is written to disk.

        Returns (possibly-sanitized content, threat_score, was_sanitized).
        """
        threat_score = 0.01  # baseline safety score

        for pattern in MALICIOUS_PATTERNS:
            if re.search(pattern, content_text):
                threat_score += 1.10  # heavy penalty for direct injection attempts

        for tag in tags:
            if tag.lower() in SUSPICIOUS_TAGS:
                threat_score += 0.2

        is_sanitized = True
        if threat_score > self.toxicity_threshold:
            # In production, an LLM supervisor / heuristic classifier would rewrite
            # or block the injection. Here we simulate sanitization by purifying text.
            sanitized_text = re.sub(
                r"(?i)ignore as instruções anteriores.*$", REDACTION_MARK, content_text
            )
            sanitized_text = re.sub(
                r"(?i)ignore as regras anteriores.*$", REDACTION_MARK, sanitized_text
            )
            sanitized_text = re.sub(
                r"(?i)ignore.*diretriz.*$", REDACTION_MARK, sanitized_text
            )
            return sanitized_text, threat_score, is_sanitized

        return content_text, threat_score, is_sanitized
