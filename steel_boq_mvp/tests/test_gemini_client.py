import types as pytypes

import pytest

import gemini_client as gc


def test_prompt_is_verbatim():
    assert "You are reading a structural steel drawing (framing plan or member schedule)." in gc.PROMPT
    assert "- member_id: the label/tag shown on the drawing (e.g. B1, C2, GB-01)" in gc.PROMPT
    assert "Return ONLY a JSON array of objects with these exact keys." in gc.PROMPT
    assert gc.PROMPT.rstrip().endswith("and explain briefly in notes.")


def test_strip_fences_json_lang():
    assert gc.strip_fences("```json\n[1]\n```") == "[1]"


def test_strip_fences_plain():
    assert gc.strip_fences("  ```\n[1]\n```  ") == "[1]"


def test_strip_fences_no_fence():
    assert gc.strip_fences("[1]") == "[1]"


def test_parse_clean_array():
    rows = gc.parse_gemini_json(
        '[{"member_id":"B1","section":"H-300x150x6.5x9","length_mm":6000,"quantity":8,"notes":null}]'
    )
    assert rows == [
        {"member_id": "B1", "section": "H-300x150x6.5x9", "length_mm": 6000.0, "quantity": 8, "notes": None}
    ]


def test_parse_fenced():
    rows = gc.parse_gemini_json('```json\n[{"member_id":"B1"}]\n```')
    assert rows[0]["member_id"] == "B1"


def test_parse_dict_wrapped_unwraps():
    rows = gc.parse_gemini_json('{"members": [{"member_id": "C1"}]}')
    assert rows[0]["member_id"] == "C1"


def test_parse_missing_keys_none_and_extras_dropped():
    rows = gc.parse_gemini_json('[{"member_id":"B1","extra":"x"}]')
    assert set(rows[0].keys()) == set(gc.KEYS)
    assert rows[0]["section"] is None
    assert "extra" not in rows[0]


def test_parse_coerces_numeric_strings():
    rows = gc.parse_gemini_json('[{"member_id":"B1","quantity":"2","length_mm":"6000"}]')
    assert rows[0]["quantity"] == 2
    assert rows[0]["length_mm"] == 6000.0


def test_parse_bad_numeric_becomes_none():
    rows = gc.parse_gemini_json('[{"member_id":"B1","quantity":"two","length_mm":"SEE PLAN"}]')
    assert rows[0]["quantity"] is None
    assert rows[0]["length_mm"] is None


def test_parse_prose_raises_with_raw():
    raw = 'Here is the table: [{"member_id":"B1"}]'
    with pytest.raises(gc.GeminiParseError) as ei:
        gc.parse_gemini_json(raw)
    assert ei.value.raw == raw


def test_parse_empty_raises():
    with pytest.raises(gc.GeminiParseError):
        gc.parse_gemini_json("")


def test_parse_non_list_raises():
    with pytest.raises(gc.GeminiParseError):
        gc.parse_gemini_json('{"a": 1, "b": 2}')


def test_get_api_key_missing(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(gc, "load_dotenv", lambda *a, **k: None)
    with pytest.raises(gc.MissingApiKeyError):
        gc.get_api_key()


def test_get_model_name_env_override(monkeypatch):
    monkeypatch.setattr(gc, "load_dotenv", lambda *a, **k: None)
    monkeypatch.setenv("GEMINI_MODEL", "gemini-2.5-pro")
    assert gc.get_model_name() == "gemini-2.5-pro"
    monkeypatch.delenv("GEMINI_MODEL")
    assert gc.get_model_name() == gc.DEFAULT_MODEL


class FakeModels:
    def __init__(self, text):
        self.text = text
        self.calls = []

    def generate_content(self, *, model, contents, config):
        self.calls.append({"model": model, "contents": contents, "config": config})
        return pytypes.SimpleNamespace(text=self.text, candidates=[])


class FakeClient:
    def __init__(self, text):
        self.models = FakeModels(text)


def test_extract_members_with_fake_client():
    client = FakeClient('[{"member_id":"B1","section":"W12x26","length_mm":4200,"quantity":3,"notes":null}]')
    res = gc.extract_members([b"png1", b"png2"], model="m", api_key="k", client=client)
    call = client.models.calls[0]
    assert call["model"] == "m"
    assert len(call["contents"]) == 3  # 2 images + prompt
    assert call["contents"][-1] == gc.PROMPT
    assert call["config"].response_mime_type == "application/json"
    assert res.rows[0]["member_id"] == "B1"
    assert res.latency_s > 0
    assert res.page_count == 2
    assert res.raw_text.startswith("[")


def test_extract_members_parse_error_keeps_raw():
    client = FakeClient("no json here")
    with pytest.raises(gc.GeminiParseError) as ei:
        gc.extract_members([b"png"], model="m", api_key="k", client=client)
    assert ei.value.raw == "no json here"


def test_extract_members_none_text():
    client = FakeClient(None)
    with pytest.raises(gc.GeminiParseError):
        gc.extract_members([b"png"], model="m", api_key="k", client=client)
