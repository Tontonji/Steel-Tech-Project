import json
import re
from datetime import datetime

import research_log as rl


def test_write_log_creates_json(tmp_path):
    ts = datetime(2026, 9, 8, 12, 0, 0)
    path = rl.write_log(
        tmp_path / "logs",
        model="gemini-2.5-flash",
        pages=[0, 1],
        latency_s=1.234,
        raw_response='[{"member_id":"B1"}]',
        parsed_rows=[{"member_id": "B1", "section": None, "length_mm": None, "quantity": None, "notes": None}],
        source_filename="sample.pdf",
        dpi=220,
        ts=ts,
    )
    assert path.exists()
    assert re.match(r"^\d{8}_\d{6}\.json$", path.name)
    data = json.loads(path.read_text(encoding="utf-8"))
    for key in ("timestamp", "model", "pages", "latency_s", "raw_response", "parsed_rows", "source_filename", "dpi", "error"):
        assert key in data
    assert data["error"] is None
    assert data["parsed_rows"][0]["member_id"] == "B1"
    assert data["pages"] == [0, 1]


def test_write_log_with_error(tmp_path):
    path = rl.write_log(
        tmp_path,
        model="m",
        pages=[0],
        latency_s=0.5,
        raw_response="garbage",
        parsed_rows=None,
        source_filename="x.pdf",
        dpi=200,
        error="Response was not valid JSON",
    )
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["error"].startswith("Response was not valid JSON")
    assert data["parsed_rows"] is None
