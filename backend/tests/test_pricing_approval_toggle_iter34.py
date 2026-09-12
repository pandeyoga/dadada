"""ITER34 — Toggle approval_mode pada kupon/promo/skema diskon.

Menguji:
- PUT /api/pricing/coupons/{id}: set approval_mode 'always' / 'global' / invalid.
- PUT /api/pricing/promos/{id}: sama.
- GET /api/pricing/coupons: setiap baris punya approval_mode.
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001").rstrip("/")
API = f"{BASE_URL}/api"
PASSWORD = "Sipro#2026"


@pytest.fixture(scope="module")
def admin():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": "superadmin@sipro.co.id", "password": PASSWORD}, timeout=15)
    assert r.status_code == 200, r.text
    tok = r.json().get("access_token") or r.json().get("token")
    s.headers.update({"Authorization": f"Bearer {tok}", "Content-Type": "application/json"})
    return s


def _find(session, slug, code):
    r = session.get(f"{API}/pricing/{slug}", timeout=15)
    assert r.status_code == 200, r.text
    rows = r.json().get("data", [])
    for x in rows:
        if x.get("code") == code:
            return x, rows
    return None, rows


def _restore(session, slug, rule_id, original_mode):
    session.put(f"{API}/pricing/{slug}/{rule_id}",
                json={"approval_mode": original_mode, "requires_approval": original_mode == "always"}, timeout=15)


@pytest.mark.parametrize("slug,code", [("coupons", "SIPRO2026"), ("promos", "PROMO-LAUNCH")])
def test_toggle_approval_mode(admin, slug, code):
    row, rows = _find(admin, slug, code)
    if not row:
        pytest.skip(f"Seed {slug} {code} tidak ditemukan (rows={[r.get('code') for r in rows]})")

    original_mode = row.get("approval_mode") or ("always" if row.get("requires_approval") else "global")
    rule_id = row["id"]

    # GET list: setiap baris punya approval_mode
    for r in rows:
        assert "approval_mode" in r, f"approval_mode absen di baris {r.get('code')}"

    try:
        # 1. Set ke always
        r = admin.put(f"{API}/pricing/{slug}/{rule_id}",
                      json={"approval_mode": "always", "requires_approval": True}, timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()["data"]
        assert data["approval_mode"] == "always"
        assert data["requires_approval"] is True

        # GET verifikasi persist
        row2, _ = _find(admin, slug, code)
        assert row2["approval_mode"] == "always"
        assert row2["requires_approval"] is True

        # 2. Set kembali ke global
        r = admin.put(f"{API}/pricing/{slug}/{rule_id}",
                      json={"approval_mode": "global", "requires_approval": False}, timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()["data"]
        assert data["approval_mode"] == "global"
        assert data["requires_approval"] is False

        # 3. Nilai tidak valid → 400/422
        r = admin.put(f"{API}/pricing/{slug}/{rule_id}", json={"approval_mode": "bogus"}, timeout=15)
        assert r.status_code in (400, 422), r.text
    finally:
        _restore(admin, slug, rule_id, original_mode)


def test_get_coupons_has_approval_mode(admin):
    r = admin.get(f"{API}/pricing/coupons", timeout=15)
    assert r.status_code == 200
    rows = r.json().get("data", [])
    assert rows, "Tidak ada seed kupon"
    for x in rows:
        assert x.get("approval_mode") in ("global", "always", "never"), x
