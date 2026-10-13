"""Human-feedback log for uncertain steel members -> training dataset.

Feedback loop for the steel takeoff MVP.
Local JSONL storage (one file per run dir); no network, no keys.

Loop: AI row (review_status != ok) -> person confirms/corrects/marks unreadable
-> record_feedback() -> quality_gate() -> approve -> export_dataset().
Training data is a by-product of the person finishing their own work.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

import boq_utils as bu
import gemini_client as gc

ACTIONS = ("confirmed", "corrected", "marked_unreadable")
STATUSES = ("pending", "approved", "rejected", "used")
# Fields a person can verify on a steel member row (== gemini_client.KEYS minus notes).
FIELDS = ("member_id", "section", "length_mm", "quantity")

MAX_LENGTH_MM = 30000.0   # single steel member beyond this is implausible
MAX_QTY = 500
BIG_CORRECTION = 0.5      # relative change that forces engineer review


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def record_feedback(
    log_path: Path,
    *,
    drawing_id: str,
    page_no: int,
    member_id: str | None,
    field: str,
    ai_value,
    ai_confidence: float | None,
    ai_flags: list[str] | None,
    human_value,
    action: str,
    prompt_version: str,
    model: str,
    image_ref: str | None = None,
    user_role: str = "user",
    consent: bool = False,
) -> dict:
    """Append one feedback record. ``consent`` defaults to False (never train)."""
    if action not in ACTIONS:
        raise ValueError(f"action must be one of {ACTIONS}")
    if field not in FIELDS:
        raise ValueError(f"field must be one of {FIELDS}")
    if action == "marked_unreadable":
        human_value = None  # train as null + flag, never 0
    elif action == "confirmed":
        human_value = ai_value
    rec = {
        "id": uuid.uuid4().hex,
        "drawing_id": drawing_id,
        "page_no": page_no,
        "member_id": member_id,
        "field_path": field,
        "ai_value": ai_value,
        "ai_confidence": ai_confidence,
        "ai_flags": list(ai_flags or []),
        "human_value": human_value,
        "action": action,
        "prompt_version": prompt_version,
        "model": model,
        "image_ref": image_ref,
        "user_role": user_role,
        "consent": bool(consent),
        "created_at": _now(),
        "training_status": "pending",
    }
    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


def load(log_path: Path) -> list[dict]:
    p = Path(log_path)
    if not p.exists():
        return []
    return [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]


def save(log_path: Path, records: list[dict]) -> None:
    Path(log_path).write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records), encoding="utf-8"
    )


def _big_change(ai, human) -> bool:
    if ai is None:
        return False  # person filled a blank the AI left null; nothing to disagree with
    try:
        a, h = float(ai), float(human)
    except (TypeError, ValueError):
        return ai != human
    return a == 0 or abs(h - a) / abs(a) > BIG_CORRECTION


def quality_gate(rec: dict) -> str:
    """Return 'rejected', 'needs_engineer' or 'approved' for one record."""
    if not rec.get("consent"):
        return "rejected"
    v, field, action = rec.get("human_value"), rec["field_path"], rec["action"]
    if action == "marked_unreadable":
        return "approved"  # teaches the model to answer null + flag
    if v is None:
        return "rejected"
    if field == "section" and bu.parse_section(str(v)) is None:
        return "rejected"  # not a recognisable steel designation
    if field == "length_mm":
        try:
            if not 0 < float(v) <= MAX_LENGTH_MM:
                return "rejected"
        except (TypeError, ValueError):
            return "rejected"
    if field == "quantity":
        try:
            n = float(v)
            if n < 0 or n != int(n) or n > MAX_QTY:
                return "rejected"
        except (TypeError, ValueError):
            return "rejected"
    if action == "corrected" and _big_change(rec.get("ai_value"), v):
        return "needs_engineer"
    return "approved"


def apply_gate(records: list[dict], engineer_approved: set[str] | None = None) -> list[dict]:
    """Set training_status on pending records. ``engineer_approved`` = record ids."""
    ok = engineer_approved or set()
    for r in records:
        if r["training_status"] != "pending":
            continue
        verdict = quality_gate(r)
        if verdict == "needs_engineer":
            verdict = "approved" if r["id"] in ok else "pending"
        r["training_status"] = verdict
    return records


def export_dataset(records: list[dict], out_path: Path) -> int:
    """Write approved + consented rows as chat-style JSONL. Returns rows written.

    One example per (drawing, page, member). The assistant content is valid JSON
    (no markdown fence) using the exact gemini_client.KEYS.
    """
    groups: dict[tuple, list[dict]] = {}
    for r in records:
        if r["training_status"] == "approved" and r.get("consent"):
            groups.setdefault((r["drawing_id"], r["page_no"], r["member_id"]), []).append(r)
    n = 0
    with Path(out_path).open("w", encoding="utf-8") as f:
        for (_, _, mid), recs in groups.items():
            row = {k: None for k in gc.KEYS}
            row["member_id"] = mid
            flags = []
            for r in recs:
                row[r["field_path"]] = r["human_value"]
                if r["action"] == "marked_unreadable":
                    flags.append(f"{r['field_path']} unreadable")
            row["notes"] = "; ".join(flags) or None
            example = {
                "messages": [
                    {"role": "user", "content": gc.PROMPT, "image_ref": recs[0]["image_ref"]},
                    {"role": "assistant", "content": json.dumps([row], ensure_ascii=False)},
                ],
                "prompt_version": recs[0]["prompt_version"],
            }
            f.write(json.dumps(example, ensure_ascii=False) + "\n")
            n += 1
    for r in records:
        if r["training_status"] == "approved" and r.get("consent"):
            r["training_status"] = "used"
    return n


def metrics(records: list[dict]) -> dict:
    """Correction rate per field + calibration of AI confidence."""
    per_field: dict[str, dict] = {}
    for r in records:
        s = per_field.setdefault(r["field_path"], {"total": 0, "corrected": 0})
        s["total"] += 1
        s["corrected"] += r["action"] != "confirmed"
    for s in per_field.values():
        s["correction_rate"] = round(s["corrected"] / s["total"], 2)
    hi = [r for r in records if (r.get("ai_confidence") or 0) >= 0.9]
    calib = None
    if hi:
        calib = round(sum(r["action"] == "confirmed" for r in hi) / len(hi), 2)
    return {"per_field": per_field, "accuracy_at_conf_0.9": calib}
