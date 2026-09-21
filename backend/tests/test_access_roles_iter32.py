"""Backend tests for PERAN & HAK AKSES (iteration 32).

Endpoints covered: GET /api/access/modules, GET/POST /api/access/roles,
PATCH/DELETE /api/access/roles/{rid}, POST /api/access/roles/{rid}/reset.
Also validates non-admin (sales) is blocked (403), custom role usage in POST /api/users,
and login-as-custom-role permissions.
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
ENTITY = "ent_ksc"


def _login(email: str, password: str = "demo12345") -> str:
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": email, "password": password},
                      headers={"X-Entity-Id": ENTITY}, timeout=30)
    assert r.status_code == 200, f"login {email} -> {r.status_code} {r.text}"
    return r.json()["token"]


def _h(token: str):
    return {"Authorization": f"Bearer {token}", "X-Entity-Id": ENTITY,
            "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def admin_token():
    return _login("admin@kainnusantara.id")


@pytest.fixture(scope="module")
def sales_token():
    return _login("sales@kainnusantara.id")


# --- Modules & roles listing ---
def test_modules_catalog(admin_token):
    r = requests.get(f"{BASE_URL}/api/access/modules", headers=_h(admin_token), timeout=30)
    assert r.status_code == 200
    data = r.json()
    modules = data["modules"]
    assert isinstance(modules, list) and len(modules) == 24
    sample = modules[0]
    for key in ("id", "label", "description", "resources", "nav", "actions"):
        assert key in sample, f"missing {key} in module"
    assert set(data["levels"].keys()) >= {"none", "view", "manage"}


def test_roles_list_builtin_and_custom(admin_token):
    r = requests.get(f"{BASE_URL}/api/access/roles", headers=_h(admin_token), timeout=30)
    assert r.status_code == 200
    roles = r.json()["roles"]
    builtin = [x for x in roles if not x["custom"]]
    custom = [x for x in roles if x["custom"]]
    assert len(builtin) == 11, f"expected 11 builtin, got {len(builtin)}"
    assert any(x["id"] == "cr_staf_penagihan" for x in custom), "cr_staf_penagihan should exist"
    admin = next(x for x in roles if x["id"] == "admin")
    assert admin["locked"] is True
    for role in roles:
        assert "levels" in role and isinstance(role["levels"], dict)
        for mod, lv in role["levels"].items():
            assert "level" in lv and "partial" in lv


def test_non_admin_forbidden(sales_token):
    r = requests.get(f"{BASE_URL}/api/access/roles", headers=_h(sales_token), timeout=30)
    assert r.status_code == 403


# --- Create custom role ---
@pytest.fixture(scope="module")
def created_custom(admin_token):
    payload = {
        "label": "TEST_Peran Uji QA",
        "description": "role qa iter32",
        "base_role": "sales",
        "levels": {"customer": "manage", "penjualan": "view", "rnd": "none"},
    }
    r = requests.post(f"{BASE_URL}/api/access/roles", headers=_h(admin_token),
                      json=payload, timeout=30)
    assert r.status_code == 200, f"create failed: {r.status_code} {r.text}"
    data = r.json()
    yield data
    # Cleanup: reassign any lingering users first
    try:
        users_resp = requests.get(f"{BASE_URL}/api/users", headers=_h(admin_token), timeout=30).json()
        ulist = users_resp.get("users", users_resp) if isinstance(users_resp, dict) else users_resp
        for u in ulist:
            if u.get("role") == data["id"]:
                requests.patch(f"{BASE_URL}/api/users/{u['id']}", headers=_h(admin_token),
                               json={"data": {"role": "sales"}}, timeout=30)
    except Exception:
        pass
    requests.delete(f"{BASE_URL}/api/access/roles/{data['id']}", headers=_h(admin_token), timeout=30)


def test_create_role_fields(created_custom):
    d = created_custom
    assert d["id"].startswith("cr_")
    assert d["custom"] is True
    assert d["levels"]["customer"]["level"] == "manage"
    assert d["levels"]["penjualan"]["level"] == "view"
    assert d["levels"]["rnd"]["level"] == "none"


def test_create_role_shows_in_roles_endpoint(admin_token, created_custom):
    r = requests.get(f"{BASE_URL}/api/roles", headers=_h(admin_token), timeout=30)
    assert r.status_code == 200
    body = r.json()
    roles = body["roles"] if isinstance(body, dict) and "roles" in body else body
    match = next((x for x in roles if x.get("id") == created_custom["id"]), None)
    assert match is not None, "custom role missing in /api/roles"
    assert match.get("custom") is True
    nav = match.get("nav") or {}
    # Should have nav add/remove keys (may be empty lists, but present)
    assert "add" in nav and "remove" in nav


def test_create_label_conflict(admin_token, created_custom):
    r = requests.post(f"{BASE_URL}/api/access/roles", headers=_h(admin_token),
                      json={"label": created_custom["label"], "levels": {}}, timeout=30)
    assert r.status_code == 409


def test_create_label_too_short(admin_token):
    r = requests.post(f"{BASE_URL}/api/access/roles", headers=_h(admin_token),
                      json={"label": "x", "levels": {}}, timeout=30)
    assert r.status_code == 400


def test_create_base_role_admin_blocked(admin_token):
    r = requests.post(f"{BASE_URL}/api/access/roles", headers=_h(admin_token),
                      json={"label": "TEST_from_admin", "base_role": "admin", "levels": {}}, timeout=30)
    assert r.status_code == 400


# --- Patch custom role ---
def test_patch_custom_role(admin_token, created_custom):
    rid = created_custom["id"]
    new_label = "TEST_Peran Uji QA 2"
    r = requests.patch(f"{BASE_URL}/api/access/roles/{rid}", headers=_h(admin_token),
                       json={"label": new_label, "levels": {"inventory": "view"}}, timeout=30)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["label"] == new_label
    assert d["levels"]["inventory"]["level"] == "view"


def test_patch_admin_forbidden(admin_token):
    r = requests.patch(f"{BASE_URL}/api/access/roles/admin", headers=_h(admin_token),
                       json={"levels": {"customer": "view"}}, timeout=30)
    assert r.status_code == 403


def test_patch_builtin_label_forbidden(admin_token):
    r = requests.patch(f"{BASE_URL}/api/access/roles/sales", headers=_h(admin_token),
                       json={"label": "renamed"}, timeout=30)
    assert r.status_code == 400


# --- Reset builtin (MUST reset back to keep environment clean) ---
def test_patch_and_reset_builtin_sales(admin_token):
    # Save baseline: check current 'modified' flag
    # Ensure clean baseline first
    requests.post(f"{BASE_URL}/api/access/roles/sales/reset",
                  headers=_h(admin_token), timeout=30)

    r = requests.patch(f"{BASE_URL}/api/access/roles/sales", headers=_h(admin_token),
                       json={"levels": {"rnd": "none"}}, timeout=30)
    assert r.status_code == 200
    d = r.json()
    assert d["modified"] is True
    try:
        rr = requests.post(f"{BASE_URL}/api/access/roles/sales/reset",
                           headers=_h(admin_token), timeout=30)
        assert rr.status_code == 200
        assert rr.json()["modified"] is False
    finally:
        requests.post(f"{BASE_URL}/api/access/roles/sales/reset",
                      headers=_h(admin_token), timeout=30)


# --- Users use custom role, delete guarded ---
def test_delete_custom_role_when_in_use(admin_token, created_custom):
    rid = created_custom["id"]
    # Create test user using custom role
    import time, uuid
    unique = uuid.uuid4().hex[:8]
    user_payload = {
        "name": "TEST_QA User",
        "email": f"TEST_qauser_iter32_{unique}@example.com",
        "password": "demo12345",
        "role": rid,
        "home_entity_id": ENTITY,
        "allowed_entity_ids": [ENTITY],
    }
    ur = requests.post(f"{BASE_URL}/api/users", headers=_h(admin_token),
                       json=user_payload, timeout=30)
    if ur.status_code not in (200, 201):
        pytest.fail(f"/api/users create failed ({ur.status_code}): {ur.text[:300]}")
    user_id = ur.json().get("id") or ur.json().get("user", {}).get("id")

    try:
        # Delete while in use -> 409
        dr = requests.delete(f"{BASE_URL}/api/access/roles/{rid}",
                             headers=_h(admin_token), timeout=30)
        assert dr.status_code == 409

        # Change user to other role, then delete should succeed
        if user_id:
            up = requests.patch(f"{BASE_URL}/api/users/{user_id}",
                                headers=_h(admin_token),
                                json={"data": {"role": "sales"}}, timeout=30)
            assert up.status_code in (200, 201), f"user role change failed: {up.status_code} {up.text[:200]}"
        dr2 = requests.delete(f"{BASE_URL}/api/access/roles/{rid}",
                              headers=_h(admin_token), timeout=30)
        assert dr2.status_code == 200
        assert dr2.json().get("deleted") is True

        # Verify gone
        rr = requests.get(f"{BASE_URL}/api/access/roles/{rid}", headers=_h(admin_token), timeout=30)
        assert rr.status_code == 404
    finally:
        if user_id:
            requests.delete(f"{BASE_URL}/api/users/{user_id}", headers=_h(admin_token), timeout=30)


# --- Custom role login (existing penagihan@) ---
def test_login_custom_role_penagihan():
    tok = _login("penagihan@kainnusantara.id")
    r = requests.get(f"{BASE_URL}/api/auth/me",
                     headers={"Authorization": f"Bearer {tok}", "X-Entity-Id": ENTITY}, timeout=30)
    assert r.status_code == 200
    me = r.json()
    perms = me.get("permissions") or me.get("user", {}).get("permissions") or {}
    # Should have at least some finance-ish permissions but limited
    assert isinstance(perms, dict) and len(perms) > 0
