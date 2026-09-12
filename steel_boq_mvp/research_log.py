"""Local-only research logging: one timestamped JSON per extraction run.

Nothing here transmits data anywhere; files land in ``logs/`` next to the app.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from boq_utils import TS_FORMAT

APP_VERSION = "0.1.0"


def write_log(
    log_dir: Path | str,
    *,
    model: str,
    pages: list[int],
    latency_s: float | None,
    raw_response: str | None,
    parsed_rows: list[dict] | None,
    source_filename: str,
    dpi: int,
    error: str | None = None,
    ts: datetime | None = None,
) -> Path:
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    ts = ts or datetime.now()
    stamp = ts.strftime(TS_FORMAT)
    path = log_dir / f"{stamp}.json"
    # Avoid clobbering if two runs land in the same second.
    n = 1
    while path.exists():
        path = log_dir / f"{stamp}_{n}.json"
        n += 1
    payload = {
        "timestamp": ts.isoformat(timespec="seconds"),
        "app_version": APP_VERSION,
        "source_filename": source_filename,
        "model": model,
        "pages": list(pages),
        "dpi": dpi,
        "latency_s": latency_s,
        "error": error,
        "raw_response": raw_response,
        "parsed_rows": parsed_rows,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
