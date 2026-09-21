"""Iter37: PREVIEW peran + MOVE USERS massal (custom_role_service).

Covers:
 - POST /api/access/roles/preview (role_id/base_role/levels)
 - POST /api/access/roles/{rid}/move-users (target validation & mass move)
"""
import os
import requests
import pytest

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
ENT = "ent_ksc"
TITLE_INVOICE = "Terbitkan faktur & tagih"


def _login(email, password="demo12345"):
    r = requests.post(f"{BASE}/api/auth/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, f"login {email}: {r.status_code} {r.text}"
    return r.json().get("token") or r.json().get("access_token")


@pytest.fixture(scope="module")
def admin_hdr():
    tok = _login("admin@kainnusantara.id")
    return {"Authorization": f"Bearer {tok}", "X-Entity-Id": ENT, "Content-Type": "application/json"}


# ---------- PREVIEW ----------
class TestPreview:
    def test_preview_existing_role_no_levels(self, admin_hdr):
        r = requests.post(f"{BASE}/api/access/roles/preview",
                          json={"role_id": "cr_staf_penagihan", "levels": {}}, headers=admin_hdr, timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert TITLE_INVOICE in data["turn_alerts"], data
        assert isinstance(data["screens"], list) and len(data["screens"]) > 0

    def test_preview_existing_role_ar_none_drops_invoice(self, admin_hdr):
        r = requests.post(f"{BASE}/api/access/roles/preview",
                          json={"role_id": "cr_staf_penagihan", "levels": {"ar": "none"}},
                          headers=admin_hdr, timeout=30)
        assert r.status_code == 200, r.text
        assert TITLE_INVOICE not in r.json()["turn_alerts"]

    def test_preview_base_role_finance(self, admin_hdr):
        r = requests.post(f"{BASE}/api/access/roles/preview",
                          json={"base_role": "finance", "levels": {}}, headers=admin_hdr, timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert TITLE_INVOICE in data["turn_alerts"]
        assert isinstance(data["screens"], list) and len(data["screens"]) > 0

    def test_preview_unknown_base_role_400(self, admin_hdr):
        r = requests.post(f"{BASE}/api/access/roles/preview",
                          json={"base_role": "xxx"}, headers=admin_hdr, timeout=30)
        assert r.status_code == 400, r.text

    def test_preview_unknown_level_400(self, admin_hdr):
        r = requests.post(f"{BASE}/api/access/roles/preview",
                          json={"base_role": "finance", "levels": {"ar": "bogus"}},
                          headers=admin_hdr, timeout=30)
        assert r.status_code == 400, r.text

    def test_preview_does_not_persist(self, admin_hdr):
        # after ar:none preview, actual role must still have ar=manage
        r = requests.get(f"{BASE}/api/access/roles/cr_staf_penagihan", headers=admin_hdr, timeout=30)
        assert r.status_code == 200, r.text
        levels = r.json().get("levels") or {}
        ar = levels.get("ar")
        ar_lvl = ar.get("level") if isinstance(ar, dict) else ar
        assert ar_lvl == "manage", f"ar level changed: {ar_lvl}"


# ---------- MOVE USERS ----------
@pytest.fixture(scope="module")
def move_ctx(admin_hdr):
    # create test role & user, cleanup after
    role_id = None
    user_id = None
    try:
        r = requests.post(f"{BASE}/api/access/roles",
                          json={"label": "TEST_Pindah", "base_role": "sales", "levels": {}},
                          headers=admin_hdr, timeout=30)
        assert r.status_code == 200, r.text
        role_id = r.json()["id"]

        r = requests.post(f"{BASE}/api/users", json={
            "name": "TEST Pindah", "email": "test_pindah@kainnusantara.id",
            "role": role_id, "password": "demo12345",
            "home_entity_id": "ent_ksc", "allowed_entity_ids": ["ent_ksc"],
        }, headers=admin_hdr, timeout=30)
        assert r.status_code in (200, 201), r.text
        user_id = r.json().get("id") or r.json().get("user", {}).get("id")
        assert user_id, r.text
        yield {"role_id": role_id, "user_id": user_id}
    finally:
        # cleanup user
        if user_id:
            try:
                requests.delete(f"{BASE}/api/users/{user_id}", headers=admin_hdr, timeout=30)
            except Exception:
                pass
        # cleanup role (may already be deleted by test)
        if role_id:
            try:
                requests.delete(f"{BASE}/api/access/roles/{role_id}", headers=admin_hdr, timeout=30)
            except Exception:
                pass


class TestMoveUsers:
    def test_move_to_admin_denied(self, admin_hdr, move_ctx):
        r = requests.post(f"{BASE}/api/access/roles/{move_ctx['role_id']}/move-users",
                          json={"to_role": "admin"}, headers=admin_hdr, timeout=30)
        assert r.status_code == 400, r.text

    def test_move_to_same_denied(self, admin_hdr, move_ctx):
        r = requests.post(f"{BASE}/api/access/roles/{move_ctx['role_id']}/move-users",
                          json={"to_role": move_ctx["role_id"]}, headers=admin_hdr, timeout=30)
        assert r.status_code == 400, r.text

    def test_move_to_nonexistent_404(self, admin_hdr, move_ctx):
        r = requests.post(f"{BASE}/api/access/roles/{move_ctx['role_id']}/move-users",
                          json={"to_role": "nonexistent"}, headers=admin_hdr, timeout=30)
        assert r.status_code == 404, r.text

    def test_move_to_sales_ok(self, admin_hdr, move_ctx):
        r = requests.post(f"{BASE}/api/access/roles/{move_ctx['role_id']}/move-users",
                          json={"to_role": "sales"}, headers=admin_hdr, timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["moved"] == 1
        assert move_ctx["user_id"] in data["user_ids"]

        # user role now sales
        u = requests.get(f"{BASE}/api/users/{move_ctx['user_id']}", headers=admin_hdr, timeout=30)
        assert u.status_code == 200, u.text
        assert u.json().get("role") == "sales"

        # role now empty and deletable
        rr = requests.get(f"{BASE}/api/access/roles/{move_ctx['role_id']}", headers=admin_hdr, timeout=30)
        assert rr.status_code == 200, rr.text
        assert rr.json().get("users") == 0
        assert rr.json().get("deletable") is True

    def test_delete_empty_role_ok(self, admin_hdr, move_ctx):
        r = requests.delete(f"{BASE}/api/access/roles/{move_ctx['role_id']}",
                            headers=admin_hdr, timeout=30)
        assert r.status_code == 200, r.text
