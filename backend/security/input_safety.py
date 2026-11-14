"""Input security and safety guardrails.

Protects privacy by redacting PHI (SSNs, phone numbers, MRNs), checks for
prompt injection / jailbreak attempts, and filters injected instructions
before the query enters the LangGraph reasoning pipeline.
"""

import re
from typing import NamedTuple

# ---------------------------------------------------------------------------
# PHI redaction patterns
# ---------------------------------------------------------------------------
_PHI_PATTERNS = [
    # US Social Security Numbers: 123-45-6789
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[SSN REDACTED]"),
    # US phone numbers: (123) 456-7890 / 123-456-7890 / 123.456.7890
    (re.compile(r"\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}"), "[PHONE REDACTED]"),
    # Medical Record Numbers (MRN): MRN: 1234567 or MR# 1234567
    (re.compile(r"\bMR(?:N|#)?[\s:]*\d{5,10}\b", re.IGNORECASE), "[MRN REDACTED]"),
    # Date of birth patterns: DOB: 01/01/1990
    (re.compile(r"\bDOB[\s:]*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b", re.IGNORECASE), "[DOB REDACTED]"),
    # Email addresses
    (re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"), "[EMAIL REDACTED]"),
]

# ---------------------------------------------------------------------------
# Prompt injection / jailbreak detection patterns
# ---------------------------------------------------------------------------
_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"ignore\s+your\s+(system\s+)?prompt",
    r"you\s+are\s+now\s+(a|an)\s+\w+",        # "You are now an unrestricted AI"
    r"act\s+as\s+(if\s+you\s+are|a|an)\s+\w+",
    r"pretend\s+(you\s+are|to\s+be)\s+",
    r"disregard\s+(all\s+)?previous",
    r"forget\s+(all\s+)?previous\s+(instructions|context)",
    r"override\s+(your\s+)?(instructions|safety)",
    r"jailbreak",
    r"dan\s+mode",                              # DAN prompt injection
    r"prompt\s+injection",
]

_INJECTION_RE = re.compile(
    "|".join(_INJECTION_PATTERNS),
    re.IGNORECASE,
)


class SanitizationResult(NamedTuple):
    """Result of a sanitize_input() call."""

    is_safe: bool
    sanitized_query: str
    reason: str


async def sanitize_input(query: str) -> SanitizationResult:
    """Sanitize a patient query before it enters the verification pipeline.

    Performs two checks in order:
    1. Prompt injection / jailbreak detection – returns is_safe=False immediately.
    2. PHI redaction – replaces SSNs, phone numbers, MRNs, DOBs, and emails.

    Args:
        query: Raw patient query string from the API request.

    Returns:
        SanitizationResult with is_safe flag, sanitized text, and reason string.
    """
    if not query or not query.strip():
        return SanitizationResult(
            is_safe=False,
            sanitized_query="",
            reason="Empty query rejected.",
        )

    # 1. Prompt injection check
    if _INJECTION_RE.search(query):
        return SanitizationResult(
            is_safe=False,
            sanitized_query="",
            reason="Potential prompt injection detected. Request rejected.",
        )

    # 2. PHI redaction
    cleaned = query
    for pattern, replacement in _PHI_PATTERNS:
        cleaned = pattern.sub(replacement, cleaned)

    return SanitizationResult(
        is_safe=True,
        sanitized_query=cleaned,
        reason="OK",
    )
