"""ITER-302 — RETEST S#092: Pusat Persetujuan hanya admin/manager/sales(+sales_admin baca).

Cakupan:
- GET /api/approvals/my-queue → 403 untuk md@, finance@, wh.admin@
- GET /api/approvals/my-queue → 200 untuk manager@, salesadmin@, admin@
- Meja per peran tetap memuat normal (tanpa 403 baru)
"""
import os

import pytest
import requests
from dotenv import dotenv_values

frontend_env = dotenv_values("/app/frontend/.env")
base_url = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not base_url:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
BASE_URL = base_url.rstrip("/")
API = f"{BASE_URL}/api"
ENTITY = "ent_ksc"
PASSWORD = "demo12345"


def login(email: str) -> str:
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": PASSWORD}, timeout=60)
    if r.status_code != 200:
        pytest.fail(f"login {email} → {r.status_code}: {r.text[:300]}")
    token = r.json().get("access_token") or r.json().get("token")
    assert token, f"no token for {email}: {r.text[:300]}"
    return token


def headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "X-Entity-Id": ENTITY}


@pytest.fixture(scope="module")
def tokens():
    emails = ["admin", "manager", "salesadmin", "finance", "md", "wh.admin", "sales"]
    return {e: login(f"{e}@kainnusantara.id") for e in emails}


# --- Modul: approvals (Pusat Persetujuan) -----------------------------------
class TestApprovalQueueRbac:
    @pytest.mark.parametrize("who", ["md", "finance", "wh.admin"])
    def test_denied_roles_get_403(self, tokens, who):
        r = requests.get(f"{API}/approvals/my-queue", params={"entity_id": ENTITY},
                         headers=headers(tokens[who]), timeout=60)
        assert r.status_code == 403, f"{who} → {r.status_code} body={r.text[:400]}"

    @pytest.mark.parametrize("who", ["manager", "salesadmin", "admin"])
    def test_allowed_roles_get_200(self, tokens, who):
        r = requests.get(f"{API}/approvals/my-queue", params={"entity_id": ENTITY},
                         headers=headers(tokens[who]), timeout=60)
        assert r.status_code == 200, f"{who} → {r.status_code} body={r.text[:400]}"
        data = r.json()
        assert isinstance(data, (list, dict))

    def test_sales_role_has_no_generic_approval_view(self, tokens):
        """Desain: peran `sales` memakai endpoint price_approval, bukan antrean lintas modul."""
        r = requests.get(f"{API}/approvals/my-queue", params={"entity_id": ENTITY},
                         headers=headers(tokens["sales"]), timeout=60)
        assert r.status_code == 403, f"sales → {r.status_code} {r.text[:300]}"

    @pytest.mark.parametrize("who", ["md", "finance", "wh.admin"])
    def test_matrix_endpoint_also_denied(self, tokens, who):
        r = requests.get(f"{API}/approvals/matrix", params={"entity_id": ENTITY},
                         headers=headers(tokens[who]), timeout=60)
        assert r.status_code in (403, 404), f"{who} matrix → {r.status_code} {r.text[:300]}"


# --- Modul: meja peran (regresi tidak ada 403 baru) -------------------------
class TestRoleDesksStillWork:
    @pytest.mark.parametrize("who,path", [
        ("md", "/md/desk"),
        ("wh.admin", "/warehouse-admin/desk"),
        ("finance", "/finance/desk"),
    ])
    def test_desk_loads(self, tokens, who, path):
        r = requests.get(f"{API}{path}", params={"entity_id": ENTITY},
                         headers=headers(tokens[who]), timeout=90)
        assert r.status_code == 200, f"{who} {path} → {r.status_code} {r.text[:400]}"


# --- Modul: profil izin (approval tercabut di permission_settings) ----------
class TestPermissionMatrixPersisted:
    @pytest.mark.parametrize("who", ["md", "finance", "wh.admin"])
    def test_me_has_no_approval_view(self, tokens, who):
        r = requests.get(f"{API}/auth/me", headers=headers(tokens[who]), timeout=60)
        assert r.status_code == 200, r.text[:300]
        me = r.json()
        assert "_id" not in me, "MongoDB _id leaked in /auth/me"
        perms = me.get("permissions") or me.get("matrix") or {}
        if isinstance(perms, dict) and "approval" in perms:
            assert "view" not in (perms.get("approval") or []), \
                f"{who} still has approval.view: {perms.get('approval')}"
