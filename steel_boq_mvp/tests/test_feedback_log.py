import json

import feedback_log as fl


def _rec(tmp_path, **kw):
    base = dict(
        log_path=tmp_path / "fb.jsonl", drawing_id="d1", page_no=1, member_id="B1",
        field="quantity", ai_value=4, ai_confidence=0.6, ai_flags=["count_uncertain"],
        human_value=5, action="corrected", prompt_version="v1", model="m",
        image_ref="p1.png", consent=True,
    )
    base.update(kw)
    return fl.record_feedback(**base)


def test_default_no_consent_never_trains(tmp_path):
    r = _rec(tmp_path, consent=False)
    assert fl.quality_gate(r) == "rejected"


def test_unreadable_stored_as_null_and_approved(tmp_path):
    r = _rec(tmp_path, field="length_mm", ai_value=6000, human_value=999, action="marked_unreadable")
    assert r["human_value"] is None
    assert fl.quality_gate(r) == "approved"


def test_confirmed_is_positive_example(tmp_path):
    r = _rec(tmp_path, action="confirmed", human_value=123)
    assert r["human_value"] == 4
    assert fl.quality_gate(r) == "approved"


def test_implausible_values_rejected(tmp_path):
    assert fl.quality_gate(_rec(tmp_path, field="length_mm", ai_value=6000, human_value=99999)) == "rejected"
    assert fl.quality_gate(_rec(tmp_path, field="section", ai_value=None, human_value="banana")) == "rejected"
    assert fl.quality_gate(_rec(tmp_path, field="quantity", human_value=2.5)) == "rejected"


def test_big_correction_needs_engineer(tmp_path):
    r = _rec(tmp_path, ai_value=4, human_value=20)
    assert fl.quality_gate(r) == "needs_engineer"
    recs = fl.apply_gate([r])
    assert recs[0]["training_status"] == "pending"
    recs = fl.apply_gate(recs, engineer_approved={r["id"]})
    assert recs[0]["training_status"] == "approved"


def test_export_valid_json_and_marks_used(tmp_path):
    a = _rec(tmp_path, ai_value=4, human_value=5)
    b = _rec(tmp_path, field="section", ai_value=None, human_value="H-300x150x6.5x9")
    recs = fl.apply_gate(fl.load(tmp_path / "fb.jsonl"))
    out = tmp_path / "ds.jsonl"
    assert fl.export_dataset(recs, out) == 1
    ex = json.loads(out.read_text(encoding="utf-8").splitlines()[0])
    row = json.loads(ex["messages"][1]["content"])[0]
    assert row["quantity"] == 5 and row["section"].startswith("H-300")
    assert set(row) == set(fl.gc.KEYS)
    assert all(r["training_status"] == "used" for r in recs)
    assert a and b


def test_metrics(tmp_path):
    _rec(tmp_path, ai_confidence=0.95, action="confirmed")
    _rec(tmp_path, ai_confidence=0.95, human_value=9)
    m = fl.metrics(fl.load(tmp_path / "fb.jsonl"))
    assert m["per_field"]["quantity"]["correction_rate"] == 0.5
    assert m["accuracy_at_conf_0.9"] == 0.5
