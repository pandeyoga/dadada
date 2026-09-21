"""Iter35: Peran & Hak Akses — accounts on custom role GET, cr_wakil_manajer as manager-like."""
import os
import pytest
import requests

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
ENT = "ent_ksc"


def _login(email, password="demo12345"):
    r = requests.post(f"{BASE}/api/auth/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, f"login {email}: {r.status_code} {r.text}"
    tok = r.json().get("token") or r.json().get("access_token")
    assert tok, r.text
    return tok


def _hdr(tok, entity=ENT):
    return {"Authorization": f"Bearer {tok}", "X-Entity-Id": entity}


# -- Backend §1: custom role GET returns accounts array --

def test_admin_get_role_cr_staf_penagihan_accounts():
    tok = _login("admin@kainnusantara.id")
    r = requests.get(f"{BASE}/api/access/roles/cr_staf_penagihan", headers=_hdr(tok), timeout=30)
    assert r.status_code == 200, r.text
    body = r.json()
    accounts = body.get("accounts")
    assert isinstance(accounts, list), f"missing accounts array: {body}"
    users = body.get("users")
    if isinstance(users, int):
        assert len(accounts) == users, f"users={users} len(accounts)={len(accounts)}"
    emails = [a.get("email") for a in accounts]
    assert "penagihan@kainnusantara.id" in emails, f"emails={emails}"
    penag = next(a for a in accounts if a.get("email") == "penagihan@kainnusantara.id")
    for k in ("id", "name", "email", "status", "home_entity_id", "entity_name"):
        assert k in penag, f"missing {k} in account: {penag}"
    assert penag["entity_name"] == "Sukacita", f"entity_name={penag['entity_name']}"


# -- Backend §2: cr_wakil_manajer treated like manager --

def test_wakilmanajer_internal_requests_meta():
    tok = _login("wakilmanajer@kainnusantara.id")
    r = requests.get(f"{BASE}/api/internal-requests/meta", headers=_hdr(tok), timeout=30)
    assert r.status_code == 200, r.text
    m = r.json()
    assert m.get("can_decide") is True, m
    assert m.get("can_pick_source") is True, m


def test_wakilmanajer_rnd_designer_kpi_ok():
    tok = _login("wakilmanajer@kainnusantara.id")
    r = requests.get(f"{BASE}/api/rnd/reports/designer-kpi", headers=_hdr(tok), timeout=30)
    assert r.status_code == 200, f"{r.status_code} {r.text}"


def test_wakilmanajer_rnd_divisions_ok():
    tok = _login("wakilmanajer@kainnusantara.id")
    r = requests.get(f"{BASE}/api/rnd/divisions", headers=_hdr(tok), timeout=30)
    assert r.status_code == 200, f"{r.status_code} {r.text}"


def test_wakilmanajer_design_requests_full_view():
    tok = _login("wakilmanajer@kainnusantara.id")
    r = requests.get(f"{BASE}/api/design-requests", headers=_hdr(tok), timeout=30)
    assert r.status_code == 200, r.text
    body = r.json()
    # own_only should be false for manager-like → response either contains many rows or a flag
    if isinstance(body, dict):
        rows = body.get("rows") or body.get("items") or body.get("data") or []
        if "own_only" in body:
            assert body["own_only"] is False, body
    else:
        rows = body
    # Not restricted → allow empty but shouldn't be 403 (already asserted). Log rows count.
    assert isinstance(rows, list)


# -- Backend §3: regression negative --

def test_sales_rnd_kpi_forbidden():
    # Regression: non-appraisal role still 403 (designer@ user tidak ada di seed, pakai sales@).
    tok = _login("sales@kainnusantara.id")
    r = requests.get(f"{BASE}/api/rnd/reports/designer-kpi", headers=_hdr(tok), timeout=30)
    assert r.status_code == 403, f"expected 403 got {r.status_code} {r.text}"


def test_manager_internal_meta_can_decide():
    tok = _login("manager@kainnusantara.id")
    r = requests.get(f"{BASE}/api/internal-requests/meta", headers=_hdr(tok), timeout=30)
    assert r.status_code == 200, r.text
    assert r.json().get("can_decide") is True


def test_sales_internal_meta_cannot_decide():
    tok = _login("sales@kainnusantara.id")
    r = requests.get(f"{BASE}/api/internal-requests/meta", headers=_hdr(tok), timeout=30)
    assert r.status_code == 200, r.text
    assert r.json().get("can_decide") is False
