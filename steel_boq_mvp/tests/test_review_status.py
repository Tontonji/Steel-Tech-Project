import review_status as rs


def _row(**kw):
    base = {"member_id": "B1", "section": "H-300x150x6.5x9", "length_mm": 6000.0,
            "quantity": 4, "notes": None}
    base.update(kw)
    return base


def test_clean_row_is_ok():
    r = rs.annotate([_row()])[0]
    assert r["confidence_score"] == 1.0
    assert r["review_status"] == rs.STATUS_OK
    assert r["confidence_flags"] == []


def test_missing_length_is_flagged_not_zeroed():
    r = rs.annotate([_row(length_mm=None)])[0]
    assert r["length_mm"] is None
    assert "length_unclear" in r["confidence_flags"]
    assert r["review_status"] == rs.STATUS_WARN


def test_missing_section_and_qty_needs_review():
    r = rs.annotate([_row(section=None, quantity=None)])[0]
    assert r["review_status"] == rs.STATUS_REVIEW


def test_verified_keeps_ai_score_separate():
    r = rs.annotate([_row(section=None, quantity=None, human_verified=True)])[0]
    assert r["review_status"] == rs.STATUS_VERIFIED
    assert r["confidence_score"] < rs.LOW


def test_boq_pending_until_verified():
    rows = rs.annotate([_row(), _row(member_id="B2", section=None, quantity=None)])
    assert rs.boq_state(rows) == {"state": "pending", "pending_count": 1,
                                  "warn_count": 0, "pending_ids": ["B2"]}
    rows[1]["review_status"] = rs.STATUS_VERIFIED
    assert rs.boq_state(rows)["state"] == "final"
