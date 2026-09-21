"""FASE SL P1 — receipt_variances tampil di detail PO, papan PO, dan konteks tagihan (finance).

Data: PO KSC/PO-00014 (po_78d343ce4efd) sudah punya 1 catatan selisih (roll RL-00058
label ≠ aktual) dari penerimaan scan-label yang diselesaikan main agent.
"""
import os
import pytest
import requests


def _base():
    url = os.environ.get("REACT_APP_BACKEND_URL", "").strip()
    if not url:
        with open("/app/frontend/.env") as f:
            for ln in f:
                if ln.startswith("REACT_APP_BACKEND_URL="):
                    url = ln.split("=", 1)[1].strip()
    return url.rstrip("/")


BASE = _base()
PO_ID = "po_78d343ce4efd"
PO_NO = "KSC/PO-00014"


def _hdr(email):
    r = requests.post(f"{BASE}/api/auth/login", json={"email": email, "password": "demo12345"}, timeout=30)
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}", "X-Entity-Id": "ent_ksc"}


@pytest.fixture(scope="module")
def admin():
    return _hdr("admin@kainnusantara.id")


@pytest.fixture(scope="module")
def finance():
    # Peran `finance` demo tidak memegang vendor_bill.view (matriks izin lama); manajer yang menagih.
    return _hdr("manager@kainnusantara.id")


@pytest.fixture(scope="module")
def md():
    return _hdr("md@kainnusantara.id")


def test_po_detail_has_receipt_variances(admin):
    r = requests.get(f"{BASE}/api/purchase-orders/{PO_ID}", headers=admin, timeout=30)
    assert r.status_code == 200, r.text
    rv = r.json().get("receipt_variances") or []
    assert rv, "PO harus memuat receipt_variances"
    v = rv[-1]
    for k in ("expected_qty", "received_qty", "diff_qty", "unit", "note", "recorded_by", "recorded_at", "task_id"):
        assert k in v, f"field {k} hilang"
    assert v["po_number"] == PO_NO
    assert v["label_variance_rolls"], "roll ber-flag label≠aktual harus tercatat"


def test_po_list_row_carries_variances(admin):
    r = requests.get(f"{BASE}/api/purchase-orders", headers=admin, params={"page": 1, "page_size": 50}, timeout=30)
    assert r.status_code == 200, r.text
    body = r.json()
    items = body.get("items") if isinstance(body, dict) else body
    row = next((p for p in items if p.get("id") == PO_ID), None)
    assert row is not None
    assert row.get("receipt_variances"), "baris daftar PO harus membawa receipt_variances (badge baris)"


def test_billing_context_exposes_variances_for_finance(finance):
    r = requests.get(f"{BASE}/api/purchase-orders/{PO_ID}/billing-context", headers=finance, timeout=30)
    assert r.status_code == 200, r.text
    d = r.json()
    assert "receipt_variances" in d
    assert d["receipt_variances"], "finance harus melihat catatan selisih sebelum menagih"
    assert d["receipt_variances"][-1]["po_number"] == PO_NO


def test_po_board_row_has_variance_summary(md):
    r = requests.get(f"{BASE}/api/purchase-orders/board", headers=md, params={"q": "PO-00014"}, timeout=30)
    assert r.status_code == 200, r.text
    rows = r.json().get("items") or []
    row = next((x for x in rows if x.get("po_id") == PO_ID), None)
    assert row is not None, "PO-00014 harus ada di papan"
    s = row.get("receipt_variance")
    assert isinstance(s, dict)
    assert s["count"] >= 1 and s["flagged_rolls"] >= 1
    assert s["label"] and s["notes"]


def test_po_board_row_without_variance_is_none(md):
    r = requests.get(f"{BASE}/api/purchase-orders/board", headers=md, params={"page_size": 50}, timeout=30)
    assert r.status_code == 200
    rows = r.json().get("items") or []
    assert all("receipt_variance" in x for x in rows)
    others = [x for x in rows if x.get("po_id") != PO_ID]
    assert any(x["receipt_variance"] is None for x in others), "PO tanpa catatan selisih harus None (bukan 0)"


def test_scan_label_stats_report(admin):
    wh = _hdr("warehouse@kainnusantara.id")
    r = requests.get(f"{BASE}/api/inbound/scan-label/stats", headers=wh, timeout=30)
    assert r.status_code == 200, r.text
    rows = r.json()
    assert isinstance(rows, list) and rows
    row = next((x for x in rows if "Cirebon" in (x.get("supplier_name") or "")), rows[0])
    for k in ("total_rolls", "manual_override", "manual_pct", "variance_flagged", "variance_pct", "confirmed"):
        assert k in row
    assert row["variance_flagged"] >= 1
