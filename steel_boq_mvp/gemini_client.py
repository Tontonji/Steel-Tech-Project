"""Gemini Vision extraction call and defensive JSON parsing.

All google-genai SDK usage is isolated in ``call_gemini`` so API drift
only breaks one function. Tests inject a fake client.
"""
from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass, field

from dotenv import load_dotenv

DEFAULT_MODEL = "gemini-3.8-flash"

# Verbatim from the research spec. Do not paraphrase.
PROMPT = """You are reading a structural steel drawing (framing plan or member schedule).
Extract every distinct steel member you can identify. For each member, return:
- member_id: the label/tag shown on the drawing (e.g. B1, C2, GB-01)
- section: the section designation (e.g. H-300x300x10x15, W12x26)
- length_mm: member length in millimeters if shown or derivable from dimensions
- quantity: number of instances of this member type
- notes: anything ambiguous, illegible, or inferred rather than directly read

Return ONLY a JSON array of objects with these exact keys. No prose, no markdown
fences, no explanation. If a value cannot be determined, use null for that field
and explain briefly in notes."""

KEYS = ("member_id", "section", "length_mm", "quantity", "notes")


class GeminiError(Exception):
    """Base class for extraction errors."""


class MissingApiKeyError(GeminiError):
    pass


class GeminiParseError(GeminiError):
    def __init__(self, message: str, raw: str = ""):
        super().__init__(message)
        self.raw = raw


@dataclass
class ExtractionResult:
    rows: list[dict]
    raw_text: str
    model: str
    latency_s: float
    page_count: int
    finish_info: str | None = field(default=None)


def get_api_key() -> str:
    load_dotenv()
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key or key == "your_key_here":
        raise MissingApiKeyError(
            "GEMINI_API_KEY is not set. Copy .env.example to .env and add your key."
        )
    return key


def get_model_name() -> str:
    load_dotenv()
    return os.environ.get("GEMINI_MODEL", "").strip() or DEFAULT_MODEL


_FENCE_RE = re.compile(r"^```[a-zA-Z0-9_-]*[ \t]*\r?\n?(.*?)\r?\n?```$", re.DOTALL)


def strip_fences(text: str) -> str:
    text = (text or "").strip()
    m = _FENCE_RE.match(text)
    if m:
        return m.group(1).strip()
    return text


def _to_int(v):
    if v is None or isinstance(v, bool):
        return None
    try:
        return int(round(float(str(v).strip().replace(",", ""))))
    except (ValueError, TypeError):
        return None


def _to_float(v):
    if v is None or isinstance(v, bool):
        return None
    try:
        return float(str(v).strip().replace(",", ""))
    except (ValueError, TypeError):
        return None


def _to_str(v):
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def parse_gemini_json(text: str) -> list[dict]:
    """Parse the model response into a list of member dicts with exactly KEYS.

    Raises GeminiParseError (with .raw preserved) on empty, non-JSON or non-list input.
    """
    raw = text if text is not None else ""
    cleaned = strip_fences(raw)
    if not cleaned:
        raise GeminiParseError("Model returned an empty response.", raw=raw)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise GeminiParseError(f"Response was not valid JSON: {e.msg} (pos {e.pos})", raw=raw) from e

    if isinstance(data, dict):
        list_values = [v for v in data.values() if isinstance(v, list)]
        if len(list_values) == 1:
            data = list_values[0]
        else:
            raise GeminiParseError("Response JSON was an object, not an array of members.", raw=raw)
    if not isinstance(data, list):
        raise GeminiParseError("Response JSON was not an array.", raw=raw)

    rows: list[dict] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        rows.append(
            {
                "member_id": _to_str(item.get("member_id")),
                "section": _to_str(item.get("section")),
                "length_mm": _to_float(item.get("length_mm")),
                "quantity": _to_int(item.get("quantity")),
                "notes": _to_str(item.get("notes")),
            }
        )
    return rows


def _make_client(api_key: str):
    from google import genai

    return genai.Client(api_key=api_key)


def call_gemini(
    png_pages: list[bytes], *, model: str, api_key: str, client=None
) -> tuple[str, str | None]:
    """Send page images + PROMPT to Gemini. Returns (text, finish_info)."""
    from google.genai import types

    if client is None:
        client = _make_client(api_key)
    contents = [types.Part.from_bytes(data=png, mime_type="image/png") for png in png_pages]
    contents.append(PROMPT)
    config = types.GenerateContentConfig(response_mime_type="application/json", temperature=0)
    resp = client.models.generate_content(model=model, contents=contents, config=config)
    text = getattr(resp, "text", None)
    finish_info = None
    if text is None:
        try:
            cands = getattr(resp, "candidates", None) or []
            finish_info = "; ".join(str(getattr(c, "finish_reason", "?")) for c in cands) or repr(resp)
        except Exception:  # pragma: no cover - defensive
            finish_info = repr(resp)
        text = ""
    return text, finish_info


def extract_members(
    png_pages: list[bytes], *, model: str | None = None, api_key: str | None = None, client=None
) -> ExtractionResult:
    model = model or get_model_name()
    if client is None and api_key is None:
        api_key = get_api_key()
    t0 = time.perf_counter()
    text, finish_info = call_gemini(png_pages, model=model, api_key=api_key or "", client=client)
    try:
        rows = parse_gemini_json(text)
    except GeminiParseError as e:
        if finish_info and not e.raw:
            e.raw = f"<no text; finish_reason: {finish_info}>"
        raise
    latency = time.perf_counter() - t0
    return ExtractionResult(
        rows=rows,
        raw_text=text,
        model=model,
        latency_s=latency,
        page_count=len(png_pages),
        finish_info=finish_info,
    )
