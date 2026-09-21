"""Iter38: Konfigurasi Lanjutan (matriks permissions rinci) untuk Peran & Hak Akses.

Cakupan:
- GET /api/access/modules → resource_labels, action_labels, actions per module
- POST /api/access/roles/preview {permissions:{...}} valid + invalid (aksi/res tak dikenal)
- POST /api/access/roles {permissions} + GET → simpan matriks penuh, level derivation
- PATCH {permissions} → autoinject 'view', ubahan diringkas di changes.permissions
- PATCH {permissions:{}} → semua level none
- Regresi PATCH {levels:{...}} tetap berfungsi
- Regresi peran manager: permissions.order tetap 9 aksi.
"""
import os
import requests
import pytest

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
ENT = "ent_ksc"


def _login(email, password="demo12345"):
    r = requests.post(f"{BASE}/api/auth/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, f"login {email}: {r.status_code} {r.text}"
    return r.json().get("token") or r.json().get("access_token")


@pytest.fixture(scope="module")
def admin_hdr():
    tok = _login("admin@kainnusantara.id")
    return {"Authorization": f"Bearer {tok}", "X-Entity-Id": ENT, "Content-Type": "application/json"}


# ---------- MODULES META ----------
class TestModulesMeta:
    def test_modules_has_labels_and_actions(self, admin_hdr):
        r = requests.get(f"{BASE}/api/access/modules", headers=admin_hdr, timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        rl = data.get("resource_labels") or {}
        al = data.get("action_labels") or {}
        assert len(rl) >= 60, f"resource_labels count={len(rl)}"
        assert len(al) >= 60, f"action_labels count={len(al)}"
        assert rl.get("order") == "Pesanan Penjualan (SO)"
        assert al.get("create") == "Buat"
        mods = data.get("modules") or []
        assert isinstance(mods, list) and mods
        penjualan = next(m for m in mods if m["id"] == "penjualan")
        acts = penjualan.get("actions") or {}
        assert isinstance(acts, dict) and "order" in acts
        assert "create" in acts["order"] and "view" in acts["order"]


# ---------- PREVIEW WITH PERMISSIONS ----------
class TestPreviewPermissions:
    def test_preview_permissions_ok(self, admin_hdr):
        r = requests.post(f"{BASE}/api/access/roles/preview",
                          json={"role_id": "cr_staf_penagihan",
                                "permissions": {"order": ["create"], "tax_invoice": ["view", "create"]}},
                          headers=admin_hdr, timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        levels = data.get("levels") or {}
        penj = levels.get("penjualan") or {}
        assert penj.get("level") == "manage"
        assert penj.get("partial") is True
        assert "Terbitkan faktur & tagih" in (data.get("turn_alerts") or [])

    def test_preview_permissions_invalid_action_400(self, admin_hdr):
        r = requests.post(f"{BASE}/api/access/roles/preview",
                          json={"permissions": {"order": ["fly"]}},
                          headers=admin_hdr, timeout=30)
        assert r.status_code == 400, r.text
        assert "tidak berlaku" in r.text.lower() or "aksi" in r.text.lower()

    def test_preview_permissions_unknown_resource_400(self, admin_hdr):
        r = requests.post(f"{BASE}/api/access/roles/preview",
                          json={"permissions": {"unknown_res": ["view"]}},
                          headers=admin_hdr, timeout=30)
        assert r.status_code == 400, r.text


# ---------- SAVE PERMISSIONS ROUND-TRIP ----------
@pytest.fixture(scope="module")
def test_role(admin_hdr):
    role_id = None
    try:
        r = requests.post(f"{BASE}/api/access/roles",
                          json={"label": "TEST_Rinci", "base_role": "sales",
                                "permissions": {"order": ["view", "create"], "customer": ["view"]}},
                          headers=admin_hdr, timeout=30)
        assert r.status_code == 200, r.text
        role_id = r.json()["id"]
        yield role_id
    finally:
        if role_id:
            try:
                requests.delete(f"{BASE}/api/access/roles/{role_id}", headers=admin_hdr, timeout=30)
            except Exception:
                pass


class TestSavePermissions:
    def test_create_with_permissions(self, admin_hdr, test_role):
        r = requests.get(f"{BASE}/api/access/roles/{test_role}", headers=admin_hdr, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert sorted(d["permissions"].get("order", [])) == ["create", "view"]
        levels = d["levels"]
        assert levels["penjualan"]["level"] == "manage"
        assert levels["penjualan"]["partial"] is True
        assert levels["customer"]["level"] == "view"

    def test_patch_autoinject_view(self, admin_hdr, test_role):
        r = requests.patch(f"{BASE}/api/access/roles/{test_role}",
                           json={"permissions": {"order": ["create", "update"]}},
                           headers=admin_hdr, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "view" in d["permissions"].get("order", [])
        assert sorted(d["permissions"]["order"]) == ["create", "update", "view"]
        assert "permissions" in (d.get("changes") or {})

    def test_patch_legacy_levels_still_works(self, admin_hdr, test_role):
        r = requests.patch(f"{BASE}/api/access/roles/{test_role}",
                           json={"levels": {"customer": "view"}},
                           headers=admin_hdr, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["levels"]["customer"]["level"] == "view"

    def test_patch_empty_permissions_clears_all(self, admin_hdr, test_role):
        r = requests.patch(f"{BASE}/api/access/roles/{test_role}",
                           json={"permissions": {}},
                           headers=admin_hdr, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        for mid, lvl in (d.get("levels") or {}).items():
            assert lvl.get("level") == "none", f"module {mid} not none: {lvl}"


# ---------- REGRESSION: manager unchanged ----------
class TestRegressionManager:
    def test_manager_order_matches_defaults(self, admin_hdr):
        # Invariant: no frontend test should have persisted mutations to `manager`.
        from permissions_config import DEFAULT_PERMISSIONS
        r = requests.get(f"{BASE}/api/access/roles/manager", headers=admin_hdr, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        order_acts = sorted(d["permissions"].get("order", []))
        expected = sorted(DEFAULT_PERMISSIONS["manager"].get("order", []))
        assert order_acts == expected, f"manager.order drift: got {order_acts}, expected {expected}"
        # And role is not flagged as modified
        assert d.get("modified") is False, f"manager marked modified: {d.get('modified')}"
