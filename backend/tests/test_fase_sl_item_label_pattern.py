"""FASE SL P2 — pola label per Barang Supplier (supplier campur-label).

Barang Supplier `sit_b5ed6c7e1bc9` (NTT-IKAT-GRD → TNI-GRGD-001, supplier Ntt Weaving) diberi
pola GS1 sendiri; pola supplier tetap bawaan (auto/delimited). Scan pada task KSC/PO-00015
(`wms_f808e668a2e7`, 180 yard) harus membaca GS1 (pola barang) maupun teks berpemisah (pola supplier).
Semua roll uji dihapus kembali (undo scan).
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
ITEM = "sit_b5ed6c7e1bc9"
TASK = "wms_f808e668a2e7"


def _hdr(email):
    r = requests.post(f"{BASE}/api/auth/login", json={"email": email, "password": "demo12345"}, timeout=30)
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}", "X-Entity-Id": "ent_ksc"}


@pytest.fixture(scope="module")
def admin():
    return _hdr("admin@kainnusantara.id")


@pytest.fixture(scope="module")
def wh():
    return _hdr("warehouse@kainnusantara.id")


def _scan(wh, raw):
    return requests.post(f"{BASE}/api/inbound/tasks/{TASK}/scan-label", headers=wh, json={"raw": raw}, timeout=30)


def _undo(wh, roll_id):
    r = requests.delete(f"{BASE}/api/inbound/rolls/{roll_id}/scan", headers=wh, timeout=30)
    assert r.status_code == 200, r.text


def test_01_set_item_pattern(admin):
    r = requests.patch(f"{BASE}/api/supplier-items/{ITEM}", headers=admin,
                       json={"label_pattern": {"format": "gs1", "length_unit": "yard"}}, timeout=30)
    assert r.status_code == 200, r.text
    lp = r.json().get("label_pattern")
    assert lp and lp["format"] == "gs1"
    g = requests.get(f"{BASE}/api/supplier-items/{ITEM}", headers=admin, timeout=30).json()
    assert (g.get("label_pattern") or {}).get("format") == "gs1"


def test_02_scanned_rolls_exposes_item_patterns(wh):
    r = requests.get(f"{BASE}/api/inbound/tasks/{TASK}/scanned-rolls", headers=wh, timeout=30)
    assert r.status_code == 200, r.text
    d = r.json()
    pats = d.get("item_label_patterns") or []
    assert any(p["supplier_item_id"] == ITEM and p["format"] == "gs1" for p in pats)
    assert d["label_pattern"]["format"] == "auto"


def test_03_gs1_label_decoded_by_item_pattern(wh):
    r = _scan(wh, "(240)NTT-IKAT-GRD(10)DL-G1(21)PT-R1(3231)000300")
    assert r.status_code == 200, r.text
    roll = r.json()["roll"]
    try:
        assert roll["supplier_roll_no"] == "PT-R1"
        assert abs(float(roll["declared_length"]) - 30.0) < 0.01
    finally:
        _undo(wh, roll["id"])


def test_04_delimited_label_falls_back_to_supplier_pattern(wh):
    r = _scan(wh, "NTT-IKAT-GRD|DL-G1|PT-R2|30|5|BLU")
    assert r.status_code == 200, r.text
    roll = r.json()["roll"]
    try:
        assert roll["supplier_roll_no"] == "PT-R2"
        assert abs(float(roll["declared_length"]) - 30.0) < 0.01
    finally:
        _undo(wh, roll["id"])


def test_05_gs1_without_sku_implies_item(wh):
    r = _scan(wh, "(10)DL-G1(21)PT-R3(3231)000300")
    assert r.status_code == 200, r.text
    roll = r.json()["roll"]
    try:
        assert roll["supplier_roll_no"] == "PT-R3"
        assert roll.get("supplier_sku") == "NTT-IKAT-GRD"
    finally:
        _undo(wh, roll["id"])


def test_06_garbage_still_undecodable(wh):
    r = _scan(wh, "tanpa-pemisah-dan-bukan-gs1")
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "UNDECODABLE"


def test_07_clear_item_pattern_with_empty_object(admin, wh):
    r = requests.patch(f"{BASE}/api/supplier-items/{ITEM}", headers=admin, json={"label_pattern": {}}, timeout=30)
    assert r.status_code == 200, r.text
    assert r.json().get("label_pattern") is None
    d = requests.get(f"{BASE}/api/inbound/tasks/{TASK}/scanned-rolls", headers=wh, timeout=30).json()
    assert not d.get("item_label_patterns")
    # kembalikan pola GS1 supaya demo/UI tetap punya contoh supplier campur-label
    r = requests.patch(f"{BASE}/api/supplier-items/{ITEM}", headers=admin,
                       json={"label_pattern": {"format": "gs1", "length_unit": "yard"}}, timeout=30)
    assert r.status_code == 200
