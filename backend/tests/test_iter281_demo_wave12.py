"""Iterasi 281 — Catatan demo gelombang 1+2: AS-01, MD-04, MD-05, MD-07, PB-02 (MD-03 = UI)."""
import os
import uuid
import requests
import pytest


def _read_frontend_env():
    p = "/app/frontend/.env"
    if os.path.exists(p):
        for line in open(p):
            if line.startswith("REACT_APP_BACKEND_URL="):
                return line.split("=", 1)[1].strip()
    return ""


BASE = (os.environ.get("REACT_APP_BACKEND_URL") or _read_frontend_env()).rstrip("/")
PWD = "demo12345"
TAG = uuid.uuid4().hex[:6].upper()


def _hdr(email):
    r = requests.post(f"{BASE}/api/auth/login", json={"email": email, "password": PWD}, timeout=30)
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}", "X-Entity-Id": "ent_ksc"}


@pytest.fixture(scope="module")
def admin():
    return _hdr("admin@kainnusantara.id")


def test_AS01_setting_require_so_validation_mati(admin):
    d = requests.get(f"{BASE}/api/settings/effective?entity_id=ent_ksc", headers=admin, timeout=30).json()
    assert d["sales"]["require_so_validation"] is False
    ev = requests.get(f"{BASE}/api/settings/evaluate-approval?doc_type=sales_order&amount=150000000&entity_id=ent_ksc",
                      headers=admin, timeout=30).json()
    assert ev["requires_approval"] is False


def test_AS01_katalog_pengaturan_memuat_sakelar(admin):
    r = requests.get(f"{BASE}/api/config/registry", headers=admin, timeout=30)
    assert r.status_code == 200, r.text
    assert "sales.require_so_validation" in r.text


def test_MD05_proofing_tanpa_kolom_ukur(admin):
    r = requests.get(f"{BASE}/api/rnd/meta", headers=admin, timeout=30)
    assert r.status_code == 200, r.text
    types = r.json().get("sample_types") or r.json().get("types") or []
    pf = next((t for t in types if (t.get("code") or t.get("value")) == "proofing"), None)
    assert pf is not None, types
    assert not pf.get("measurement_fields"), pf
    lab = next(t for t in types if (t.get("code") or t.get("value")) == "labdip")
    assert "delta_e" in (lab.get("measurement_fields") or [])


def test_MD07_nama_warna_ganda_dan_pencarian(admin):
    code = f"QA-{TAG}"
    r = requests.post(f"{BASE}/api/color-library", headers=admin, timeout=30,
                      json={"code": code, "name": f"Biru Uji {TAG}", "hex": "#1A2B3C", "system": "KN",
                            "family": "Biru", "factory_name": f"NavyPabrik{TAG}"})
    assert r.status_code in (200, 201), r.text
    cid = r.json()["id"]
    assert r.json()["factory_name"] == f"NavyPabrik{TAG}"
    rows = requests.get(f"{BASE}/api/color-library?q=navypabrik{TAG.lower()}", headers=admin, timeout=30).json()
    rows = rows.get("items", rows) if isinstance(rows, dict) else rows
    assert any(c["id"] == cid for c in rows), "pencarian nama pabrik tidak menemukan warna"
    r = requests.patch(f"{BASE}/api/color-library/{cid}", headers=admin, timeout=30, json={"factory_name": "Ganti"})
    assert r.status_code == 200 and r.json()["factory_name"] == "Ganti", r.text


def test_PB02_rekening_bank_supplier(admin):
    r = requests.post(f"{BASE}/api/suppliers", headers=admin, timeout=30, json={
        "name": f"Supplier Impor Uji {TAG}", "origin_type": "import", "country": "China",
        "bank": {"bank_name": "HSBC", "account_no": "123456", "account_holder": "Uji Ltd",
                 "swift_code": "hsbc hkhh hkh", "currency": "usd"}})
    assert r.status_code in (200, 201), r.text
    s = r.json()
    assert s["bank"]["swift_code"] == "HSBCHKHHHKH" and s["bank"]["currency"] == "USD"
    r = requests.patch(f"{BASE}/api/suppliers/{s['id']}", headers=admin, timeout=30,
                       json={"data": {"bank": {"bank_name": "BCA", "account_no": "999", "currency": "idr"}}})
    assert r.status_code == 200, r.text
    d = requests.get(f"{BASE}/api/suppliers/{s['id']}", headers=admin, timeout=30).json()
    assert d["bank"]["bank_name"] == "BCA" and d["bank"]["currency"] == "IDR" and d["bank"]["swift_code"] == ""
