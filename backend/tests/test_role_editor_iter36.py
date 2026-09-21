"""Iter36: cr_wakil_manajer diakui require_role → /api/home/manager 200; regresi sales 403, manager 200."""
import os
import requests

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
ENT = "ent_ksc"


def _login(email, password="demo12345"):
    r = requests.post(f"{BASE}/api/auth/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, f"login {email}: {r.status_code} {r.text}"
    return r.json().get("token") or r.json().get("access_token")


def _hdr(tok, entity=ENT):
    return {"Authorization": f"Bearer {tok}", "X-Entity-Id": entity}


def test_wakilmanajer_home_manager_200():
    tok = _login("wakilmanajer@kainnusantara.id")
    r = requests.get(f"{BASE}/api/home/manager", params={"entity_id": ENT}, headers=_hdr(tok), timeout=30)
    assert r.status_code == 200, f"{r.status_code} {r.text}"


def test_manager_home_manager_200():
    tok = _login("manager@kainnusantara.id")
    r = requests.get(f"{BASE}/api/home/manager", params={"entity_id": ENT}, headers=_hdr(tok), timeout=30)
    assert r.status_code == 200, f"{r.status_code} {r.text}"


def test_sales_home_manager_403():
    tok = _login("sales@kainnusantara.id")
    r = requests.get(f"{BASE}/api/home/manager", params={"entity_id": ENT}, headers=_hdr(tok), timeout=30)
    assert r.status_code == 403, f"expected 403 got {r.status_code} {r.text}"
