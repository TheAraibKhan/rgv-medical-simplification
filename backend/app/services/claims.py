from __future__ import annotations

import re
import uuid

from app.schemas.common import Claim, ClaimType


PATIENT_MARKERS = (
    "your ",
    "you have",
    "your report",
    "the report shows",
    "the report indicates",
    "there is",
    "there are",
    "no evidence",
    "does not show",
    "shows",
    "indicates",
)

GENERAL_MARKERS = (
    "general explanation",
    "general information",
    "means",
    "refers to",
    "is a condition",
    "is damage",
    "is defined as",
    "is air in",
    "typically",
    "generally",
    "in general",
    "can cause",
    "may cause",
)


def classify_claim(text: str) -> ClaimType:
    lowered = text.lower().strip()
    if any(lowered.startswith(marker) or f" {marker}" in lowered for marker in PATIENT_MARKERS):
        return ClaimType.PATIENT_SPECIFIC
    if any(marker in lowered for marker in GENERAL_MARKERS):
        return ClaimType.GENERAL_EXPLANATORY
    # Conservative default: statements not clearly general are treated as patient-specific.
    return ClaimType.PATIENT_SPECIFIC


def _split_sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]


def decompose(text: str) -> list[Claim]:
    claims: list[Claim] = []
    for sentence in _split_sentences(text):
        # Demo-safe decomposition: split on conjunctions only when they appear to join independent clauses.
        parts = re.split(r"\s+(?:and|but)\s+(?=(?:your|there|the|no|this|it)\b)", sentence, flags=re.I)
        for part in parts:
            normalized = part.strip(" .")
            if not normalized:
                continue
            claims.append(
                Claim(
                    claim_id=str(uuid.uuid4())[:8],
                    text=normalized,
                    claim_type=classify_claim(normalized),
                    polarity="NEGATED" if re.search(r"\b(no|not|without|absent)\b", normalized, re.I) else "AFFIRMED",
                )
            )
    return claims
