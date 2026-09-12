"""Steel Drawing -> BOQ converter (research MVP). Run: streamlit run app.py"""
from __future__ import annotations

import hashlib
import os
from datetime import datetime
from pathlib import Path

import streamlit as st

import boq_utils as bu
import gemini_client as gc
import pdf_utils as pu
import research_log as rl

LOG_DIR = Path(os.environ.get("BOQ_LOG_DIR") or Path(__file__).resolve().parent / "logs")
MAX_PAGES = 10
PAYLOAD_WARN_MB = 15

st.set_page_config(page_title="Steel Drawing -> BOQ", page_icon="🏗️", layout="wide")


# ---------------------------------------------------------------- helpers
@st.cache_data(show_spinner=False)
def _thumbnails(pdf_bytes: bytes) -> list[bytes]:
    doc = pu.open_pdf(pdf_bytes)
    try:
        return [pu.render_thumbnail_png(doc, i) for i in range(pu.page_count(doc))]
    finally:
        doc.close()


def _reset_results():
    for k in ("extraction", "extraction_error", "raw_response", "boq_df", "log_path", "run_ts"):
        st.session_state.pop(k, None)


def _reset_for_new_file(uploaded):
    _reset_results()
    st.session_state.pop("pdf_error", None)
    st.session_state.file_name = uploaded.name
    st.session_state.pdf_bytes = uploaded.getvalue()
    for k in list(st.session_state.keys()):
        if k.startswith("pg_"):
            del st.session_state[k]
    try:
        doc = pu.open_pdf(st.session_state.pdf_bytes)
        st.session_state.page_count = pu.page_count(doc)
        doc.close()
    except pu.PdfError as e:
        st.session_state.page_count = 0
        st.session_state.pdf_error = str(e)


def _run_extraction(selected: list[int], dpi: int, model: str):
    _reset_results()
    ts = datetime.now()
    st.session_state.run_ts = ts
    pages = pu.render_pages(st.session_state.pdf_bytes, selected, dpi=dpi)
    png_bytes = [b for _, b in pages]
    latency = None
    try:
        result = gc.extract_members(png_bytes, model=model)
        latency = result.latency_s
        st.session_state.extraction = result
        st.session_state.raw_response = result.raw_text
        st.session_state.boq_df = bu.rows_to_dataframe(result.rows)
        err = None
        parsed = result.rows
        raw = result.raw_text
    except gc.GeminiParseError as e:
        err = f"Could not parse the model response: {e}"
        parsed, raw = None, e.raw
        st.session_state.extraction_error = err
        st.session_state.raw_response = raw
    except gc.GeminiError as e:
        err = str(e)
        parsed, raw = None, None
        st.session_state.extraction_error = err
    except Exception as e:  # SDK / network errors
        err = f"{type(e).__name__}: {e}"
        parsed, raw = None, None
        st.session_state.extraction_error = (
            err + "\n\nIf this is a model-not-found error, set GEMINI_MODEL in .env to an available model."
        )
    st.session_state.log_path = rl.write_log(
        LOG_DIR,
        model=model,
        pages=selected,
        latency_s=latency,
        raw_response=raw,
        parsed_rows=parsed,
        source_filename=st.session_state.file_name,
        dpi=dpi,
        error=err,
        ts=ts,
    )


# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.header("Settings")
    model = gc.get_model_name()
    st.caption(f"Model: `{model}` (set GEMINI_MODEL in .env to change)")
    try:
        gc.get_api_key()
        api_ok = True
        st.success("GEMINI_API_KEY found")
    except gc.MissingApiKeyError:
        api_ok = False
        st.error("GEMINI_API_KEY missing")
    dpi = st.slider("Render DPI", min_value=200, max_value=300, value=220, step=10)
    if "extraction" in st.session_state:
        st.metric("Last extraction latency", f"{st.session_state.extraction.latency_s:.1f} s")
    if st.session_state.get("log_path"):
        st.caption(f"Log: `{Path(st.session_state.log_path).name}`")

# ---------------------------------------------------------------- main
st.title("Steel Drawing -> BOQ (Gemini Vision research MVP)")
st.caption(
    "Upload one CAD-exported structural steel PDF, pick the pages with the member schedule or "
    "framing plan, extract members with Gemini, correct the table, export to Excel. "
    "Each run writes a local JSON log for accuracy scoring."
)

if not api_ok:
    st.error(
        "**GEMINI_API_KEY is not set.** Copy `.env.example` to `.env` next to `app.py`, "
        "put your key in it, then restart the app. You can still preview PDF pages below."
    )

uploaded = st.file_uploader("Upload a PDF drawing", type=["pdf"])

if uploaded is None:
    for k in ("file_sig", "file_name", "pdf_bytes", "page_count", "pdf_error"):
        st.session_state.pop(k, None)
    _reset_results()
    st.info("Upload a PDF to begin. A synthetic sample is in `samples/sample_schedule.pdf`.")
    st.stop()

sig = (uploaded.name, uploaded.size, hashlib.sha1(uploaded.getvalue()).hexdigest()[:16])
if st.session_state.get("file_sig") != sig:
    st.session_state.file_sig = sig
    _reset_for_new_file(uploaded)

if st.session_state.get("pdf_error"):
    st.error(f"{st.session_state.pdf_error} Please upload a valid, CAD-exported PDF.")
    st.stop()

n_pages = st.session_state.page_count
thumbs = _thumbnails(st.session_state.pdf_bytes)

# --- page overview / selection
left, right = st.columns([1, 3])
with left:
    st.image(thumbs[0], caption="Page 1", width=220)
with right:
    st.markdown(f"**{uploaded.name}** — {n_pages} page{'s' if n_pages != 1 else ''}")
    if n_pages == 1:
        selected = [0]
        st.caption("Single page: it will be sent as-is.")
    else:
        st.markdown("Select the page(s) containing the member schedule or framing plan:")
        selected = []
        cols = st.columns(4)
        for i in range(n_pages):
            with cols[i % 4]:
                st.image(thumbs[i], width=140)
                if st.checkbox(f"Page {i + 1}", key=f"pg_{i}", value=(i == 0)):
                    selected.append(i)

if len(selected) > MAX_PAGES:
    st.warning(f"Only the first {MAX_PAGES} selected pages will be sent.")
    selected = selected[:MAX_PAGES]

est_mb = len(selected) * (dpi / 220) ** 2 * 1.2
if est_mb > PAYLOAD_WARN_MB:
    st.warning(f"Estimated payload ~{est_mb:.0f} MB. Consider fewer pages or a lower DPI.")

run = st.button(
    "Extract members with Gemini",
    type="primary",
    disabled=(not selected) or (not api_ok),
    help="Sends the selected pages to Gemini once. Editing the table does not re-run extraction.",
)
if run:
    with st.spinner(f"Rendering {len(selected)} page(s) at {dpi} DPI and calling {model}..."):
        _run_extraction(selected, dpi, model)
    st.rerun()

# --- results
if st.session_state.get("extraction_error"):
    st.error(st.session_state.extraction_error)
    if st.session_state.get("raw_response"):
        with st.expander("Raw Gemini response", expanded=True):
            st.code(st.session_state.raw_response, language="json")
    if st.session_state.get("log_path"):
        st.caption(f"Failure logged to `{st.session_state.log_path}`")

if "extraction" in st.session_state:
    res: gc.ExtractionResult = st.session_state.extraction
    st.subheader("Extracted members")
    if res.rows:
        st.caption(
            f"{len(res.rows)} rows from {res.page_count} page(s) in {res.latency_s:.1f} s with `{res.model}`. "
            "Edit cells to correct the AI; corrections flow into the Excel export."
        )
    else:
        st.warning("The model returned no members. Check the raw response below and try other pages or a higher DPI.")

    edited = st.data_editor(
        st.session_state.boq_df,
        num_rows="dynamic",
        width="stretch",
        key="editor",
        column_config={
            "member_id": st.column_config.TextColumn("Member ID"),
            "section": st.column_config.TextColumn("Section"),
            "length_mm": st.column_config.NumberColumn("Length (mm)", min_value=0, step=1),
            "quantity": st.column_config.NumberColumn("Qty", min_value=0, step=1),
            "unit_weight_kg_m": st.column_config.NumberColumn("Unit wt (kg/m)", format="%.1f"),
            "notes": st.column_config.TextColumn("Notes", width="large"),
        },
    )
    # Re-coerce: dynamic rows come back as object dtype. Recompute unit weight for edited sections.
    records = edited.to_dict("records")
    for r in records:
        r["unit_weight_kg_m"] = None
    df = bu.rows_to_dataframe(records)
    summary = bu.summarize(df)

    m1, m2, m3 = st.columns(3)
    m1.metric("Distinct members", summary["distinct_members"])
    m2.metric("Total quantity", summary["total_quantity"])
    m3.metric("Total weight (kg, where derivable)", "—" if summary["total_weight_kg"] is None else f"{summary['total_weight_kg']:,.0f}")

    fname = bu.build_filename(st.session_state.file_name, st.session_state.get("run_ts"))
    st.download_button(
        "Download as Excel",
        data=bu.to_excel_bytes(df, summary),
        file_name=fname,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    with st.expander("Raw Gemini response"):
        st.code(st.session_state.raw_response or "", language="json")
    st.caption(
        "Unit weights are approximate: H/I and channel sections use 7850 kg/m³ × (2·b·tf + (h−2·tf)·tw), "
        "ignoring root fillets (~1–2 % low); W-shapes convert lb/ft × 1.488. Angles, plates and unknown "
        "designations are left blank."
    )
