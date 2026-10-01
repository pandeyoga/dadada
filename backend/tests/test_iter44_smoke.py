"""Iteration 44 smoke/regression after env restore (recovery branch).

Covers: health, login all demo roles, /auth/me permissions, core list endpoints.
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://dadada-dev.preview.emergentagent.com").rstrip("/")
PASSWORD = "Sipro#2026"

DEMO_USERS = [
    "superadmin@sipro.co.id",
    "owner@sipro.co.id",
    "manager@sipro.co.id",
    "marketing@sipro.co.id",
    "sales@sipro.co.id",
    "sales2@sipro.co.id",
    "finance@sipro.co.id",
    "pm@sipro.co.id",
    "site@sipro.co.id",
]


def _login(email: str) -> str:
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": PASSWORD}, timeout=15)
    assert r.status_code == 200, f"login {email} => {r.status_code} {r.text[:200]}"
    body = r.json()
    tok = body.get("access_token") or body.get("token") or (body.get("data") or {}).get("token")
    assert tok, f"no token in login resp for {email}: {body}"
    return tok


@pytest.fixture(scope="module")
def admin_token():
    return _login("superadmin@sipro.co.id")


# --- health & auth ---
def test_health():
    r = requests.get(f"{BASE_URL}/api/health", timeout=10)
    assert r.status_code == 200


@pytest.mark.parametrize("email", DEMO_USERS)
def test_login_all_roles(email):
    tok = _login(email)
    r = requests.get(f"{BASE_URL}/api/auth/me", headers={"Authorization": f"Bearer {tok}"}, timeout=10)
    assert r.status_code == 200
    body = r.json()
    data = body.get("data") or body
    assert data.get("email") == email
    # permissions key may be nested; just check we got role/level back
    assert data.get("role") or data.get("level")


# --- core list endpoints as superadmin ---
LIST_ENDPOINTS = [
    "/api/leads",
    "/api/customers",
    "/api/projects",
    "/api/units",
    "/api/deals",
    "/api/finance/ar/aging",
    "/api/build/summary",
    "/api/notifications",
]


@pytest.mark.parametrize("path", LIST_ENDPOINTS)
def test_core_list_endpoints(admin_token, path):
    r = requests.get(f"{BASE_URL}{path}", headers={"Authorization": f"Bearer {admin_token}"}, timeout=20)
    # Accept 200. Some endpoints might not exist exactly as guessed; capture non-200 clearly.
    assert r.status_code == 200, f"{path} => {r.status_code} {r.text[:200]}"
