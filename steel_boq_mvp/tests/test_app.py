"""In-process end-to-end test of app.py using Streamlit's AppTest.

The file uploader and the Gemini call are patched; PDF rendering, parsing,
DataFrame building, logging and Excel export all run for real.
"""
import json
from pathlib import Path

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

import gemini_client as gc
APP = Path(__file__).resolve().parents[1] / "app.py"

FAKE_RESPONSE = json.dumps(
    [
        {"member_id": "B1", "section": "H-300x150x6.5x9", "length_mm": 6000, "quantity": 8, "notes": None},
        {"member_id": "P1", "section": "W12x26", "length_mm": 4200, "quantity": 3, "notes": None},
        {"member_id": "CH-2", "section": "[250x90x9x13", "length_mm": None, "quantity": 6, "notes": "length shown as dash"},
    ]
)


class FakeUpload:
    def __init__(self, name: str, data: bytes):
        self.name = name
        self.size = len(data)
        self._data = data

    def getvalue(self) -> bytes:
        return self._data


@pytest.fixture
def patched_env(monkeypatch, tmp_path):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GEMINI_MODEL", "fake-model")
    monkeypatch.setattr(gc, "load_dotenv", lambda *a, **k: None)
    monkeypatch.setenv("BOQ_LOG_DIR", str(tmp_path / "logs"))
    return tmp_path


def _make_app(upload, monkeypatch, log_dir: Path, response_text: str | None = FAKE_RESPONSE, raise_exc=None):
    monkeypatch.setattr(st, "file_uploader", lambda *a, **k: upload)

    class FakeModels:
        def generate_content(self, *, model, contents, config):
            if raise_exc:
                raise raise_exc
            return type("R", (), {"text": response_text, "candidates": []})()

    class FakeClient:
        models = FakeModels()

    monkeypatch.setattr(gc, "_make_client", lambda api_key: FakeClient())
    return AppTest.from_file(str(APP), default_timeout=60)


def test_no_upload_shows_info(patched_env, monkeypatch):
    at = _make_app(None, monkeypatch, patched_env)
    at.run()
    assert not at.exception
    assert any("Upload a PDF" in i.value for i in at.info)


def test_missing_key_message(monkeypatch, tmp_path):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(gc, "load_dotenv", lambda *a, **k: None)
    at = _make_app(None, monkeypatch, tmp_path)
    at.run()
    assert not at.exception
    assert any("GEMINI_API_KEY" in e.value for e in at.error)


def test_bad_pdf_friendly_error(patched_env, monkeypatch):
    at = _make_app(FakeUpload("bad.pdf", b"not a pdf at all"), monkeypatch, patched_env)
    at.run()
    assert not at.exception
    assert any("Couldn't read this file" in e.value for e in at.error)


def test_full_flow_with_sample(patched_env, monkeypatch, sample_pdf_bytes):
    at = _make_app(FakeUpload("sample_schedule.pdf", sample_pdf_bytes), monkeypatch, patched_env)
    at.run()
    assert not at.exception
    # 3 pages -> 3 checkboxes, page 1 pre-selected
    assert len(at.checkbox) == 3
    assert at.checkbox[0].value is True
    at.checkbox[1].set_value(True)
    at.button[0].click().run()
    assert not at.exception
    assert not at.error, [e.value for e in at.error]
    # data editor rendered with 3 rows, metrics computed
    metrics = {m.label: m.value for m in at.metric}
    assert metrics["Distinct members"] == "3"
    assert metrics["Total quantity"] == "17"
    # log written with pages [0, 1]
    logs = list((patched_env / "logs").glob("*.json"))
    assert len(logs) == 1
    data = json.loads(logs[0].read_text(encoding="utf-8"))
    assert data["pages"] == [0, 1]
    assert data["model"] == "fake-model"
    assert data["error"] is None
    assert len(data["parsed_rows"]) == 3
    assert data["latency_s"] > 0
    # a rerun (e.g. an edit) must not call Gemini again / write another log
    at.run()
    assert len(list((patched_env / "logs").glob("*.json"))) == 1


def test_non_json_response_shows_raw(patched_env, monkeypatch, sample_pdf_bytes):
    at = _make_app(
        FakeUpload("sample_schedule.pdf", sample_pdf_bytes), monkeypatch, patched_env, response_text="Sorry, I cannot."
    )
    at.run()
    at.button[0].click().run()
    assert not at.exception
    assert any("Could not parse" in e.value for e in at.error)
    assert any("Raw Gemini response" in x.label for x in at.expander)
    logs = list((patched_env / "logs").glob("*.json"))
    assert len(logs) == 1
    data = json.loads(logs[0].read_text(encoding="utf-8"))
    assert data["error"] and data["raw_response"] == "Sorry, I cannot."
