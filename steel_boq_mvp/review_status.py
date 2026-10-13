"""Confidence / review-status layer for extracted steel members.

Confidence tiers and review logic for steel takeoff. Pure functions, no I/O.
The research PROMPT/KEYS in gemini_client are locked, so confidence is derived
from what the model returned (null fields + notes) rather than self-reported.

Rules carried over:
- Unreadable value = None + a flag; never guessed, never 0.
- ``confidence_score`` (AI-derived) and ``human_verified`` (person) are separate.
- A row below the low threshold and not verified blocks the BOQ total ("pending").
"""
from __future__ import annotations

HIGH = 0.90
LOW = 0.70

STATUS_OK = "ok"            # >= 0.90  auto-accept
STATUS_WARN = "warn"        # 0.70-0.89 soft warning, still counted
STATUS_REVIEW = "review"    # < 0.70   needs manual input
STATUS_VERIFIED = "verified"  # a person confirmed / edited

# (field, flag, penalty) applied when the field is missing.
_MISSING = (
    ("member_id", "id_unclear", 0.30),
    ("section", "section_unclear", 0.35),
    ("length_mm", "length_unclear", 0.25),
    ("quantity", "count_uncertain", 0.30),
)
_NOTE_HINTS = (
    ("inferred", "value_inferred", 0.15),
    ("estimat", "span_estimated", 0.15),
    ("illegible", "illegible", 0.25),
    ("ambiguous", "ambiguous", 0.15),
    ("unclear", "ambiguous", 0.15),
    ("assum", "value_inferred", 0.15),
)


def score_row(row: dict) -> tuple[float, list[str]]:
    """Return (confidence_score, confidence_flags) for one extracted member row."""
    score = 1.0
    flags: list[str] = []
    for field, flag, penalty in _MISSING:
        v = row.get(field)
        if v is None or (isinstance(v, str) and not v.strip()):
            score -= penalty
            flags.append(flag)
    note = (row.get("notes") or "").lower()
    for hint, flag, penalty in _NOTE_HINTS:
        if hint in note and flag not in flags:
            score -= penalty
            flags.append(flag)
    return round(max(score, 0.0), 2), flags


def status_for(confidence_score: float, human_verified: bool = False) -> str:
    if human_verified:
        return STATUS_VERIFIED
    if confidence_score >= HIGH:
        return STATUS_OK
    if confidence_score >= LOW:
        return STATUS_WARN
    return STATUS_REVIEW


def annotate(rows: list[dict]) -> list[dict]:
    """Add confidence_score / confidence_flags / human_verified / review_status.

    Existing ``human_verified`` is preserved; the AI score is never overwritten
    by verification (kept so the original AI value stays auditable).
    """
    out = []
    for r in rows or []:
        r = dict(r or {})
        score, flags = score_row(r)
        verified = bool(r.get("human_verified", False))
        r["confidence_score"] = score
        r["confidence_flags"] = flags
        r["human_verified"] = verified
        r["review_status"] = status_for(score, verified)
        out.append(r)
    return out


def boq_state(rows: list[dict]) -> dict:
    """Aggregate state. Total is 'pending' while any row still needs review."""
    pending = [r for r in rows if r.get("review_status") == STATUS_REVIEW]
    warned = [r for r in rows if r.get("review_status") == STATUS_WARN]
    return {
        "state": "pending" if pending else "final",
        "pending_count": len(pending),
        "warn_count": len(warned),
        "pending_ids": [r.get("member_id") for r in pending],
    }
