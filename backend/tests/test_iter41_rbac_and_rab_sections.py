"""Iter 41 — BUG (build 'can') + FEATURE (RAB granular per section) + admin endpoints.

Scope:
- login super_admin & site_engineer
- /api/build/unit/{unit_id} returns can.submit=true for site_engineer
- /api/build/items/{id}/start is 403 for role w/o construction:update, ok for role w/ it (on 'ready' item)
- /api/admin/rab-sections gating: umum only for site_engineer -> boq scope=fasum 403, umum 200, rab templates 403, summary 403
- /api/auth/me includes rab_sections
- reset rab-sections at the end
"""
import os
import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"

SUPER = {"email": "superadmin@sipro.co.id", "password": "Sipro#2026"}
SITE = {"email": "site@sipro.co.id", "password": "Sipro#2026"}
PM = {"email": "pm@sipro.co.id", "password": "Sipro#2026"}


def _login(cred):
    r = requests.post(f"{API}/auth/login", json=cred, timeout=30)
    assert r.status_code == 200, f"login {cred['email']}: {r.status_code} {r.text}"
    tok = r.json().get("access_token")
    assert tok
    return tok


def _h(tok):
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def tokens():
    return {"super": _login(SUPER), "site": _login(SITE), "pm": _login(PM)}


@pytest.fixture(scope="module")
def project_id(tokens):
    r = requests.get(f"{API}/projects", headers=_h(tokens["super"]), timeout=30)
    assert r.status_code == 200, r.text
    js = r.json()
    rows = js.get("data") or js.get("items") or js
    if isinstance(rows, dict):
        rows = rows.get("data") or []
    assert rows, "no projects"
    return rows[0]["id"]


@pytest.fixture(scope="module", autouse=True)
def reset_rab_sections_after(tokens):
    yield
    # ALWAYS reset at end of module
    r = requests.put(f"{API}/admin/rab-sections",
                     headers=_h(tokens["super"]),
                     json={"sections": {}}, timeout=30)
    assert r.status_code == 200, f"reset failed: {r.text}"


# ============== Login ==============
class TestAuth:
    def test_login_super(self):
        assert _login(SUPER)

    def test_login_site(self):
        assert _login(SITE)

    def test_auth_me_has_rab_sections(self, tokens):
        r = requests.get(f"{API}/auth/me", headers=_h(tokens["site"]), timeout=30)
        assert r.status_code == 200
        me = r.json().get("data") or r.json()
        assert "rab_sections" in me, f"me missing rab_sections: {me}"
        # default (unrestricted) -> should contain all four
        for s in ["unit", "fasum", "umum", "summary"]:
            assert s in (me["rab_sections"] or []), f"default should include {s}, got {me['rab_sections']}"


# ============== Build 'can' object ==============
class TestBuildCan:
    def test_site_engineer_can_submit_on_unit_bundle(self, tokens):
        # find a unit_id via build schedules
        r = requests.get(f"{API}/build/schedules", headers=_h(tokens["site"]), timeout=30)
        assert r.status_code == 200, r.text
        rows = (r.json().get("data") or [])
        assert rows, "no build schedules seeded"
        unit_id = rows[0].get("unit_id")
        assert unit_id
        r2 = requests.get(f"{API}/build/unit/{unit_id}", headers=_h(tokens["site"]), timeout=30)
        assert r2.status_code == 200, r2.text
        can = r2.json().get("can") or {}
        assert can.get("submit") is True, f"expected can.submit True for site_engineer, got {can}"
        assert can.get("verify") is False, f"expected can.verify False for site_engineer, got {can}"

    def test_pm_can_verify(self, tokens):
        r = requests.get(f"{API}/build/schedules", headers=_h(tokens["pm"]), timeout=30)
        assert r.status_code == 200
        rows = r.json().get("data") or []
        if not rows:
            pytest.skip("no schedules")
        unit_id = rows[0]["unit_id"]
        r2 = requests.get(f"{API}/build/unit/{unit_id}", headers=_h(tokens["pm"]), timeout=30)
        assert r2.status_code == 200
        can = r2.json().get("can") or {}
        assert can.get("verify") is True, f"PM should verify, got {can}"


# ============== start endpoint permission enforcement ==============
class TestStartPermission:
    def test_role_without_update_gets_403(self, tokens):
        # sales role has no construction:update
        sales_tok = _login({"email": "sales@sipro.co.id", "password": "Sipro#2026"})
        # any item id works (permission enforced BEFORE existence check)
        r = requests.post(f"{API}/build/items/nonexistent-id/start",
                          headers=_h(sales_tok), timeout=30)
        assert r.status_code == 403, f"expected 403 for sales, got {r.status_code} {r.text}"

    def test_site_engineer_permitted_reaches_business_logic(self, tokens):
        # Site engineer has construction:update — should NOT be 403 (may 400/404 based on state)
        r = requests.get(f"{API}/build/items?limit=5", headers=_h(tokens["site"]), timeout=30)
        assert r.status_code == 200, r.text
        items = r.json().get("data") or []
        if not items:
            pytest.skip("no build items")
        # Pick any item; we only care it's NOT 403
        item_id = items[0]["id"]
        r2 = requests.post(f"{API}/build/items/{item_id}/start",
                           headers=_h(tokens["site"]), timeout=30)
        assert r2.status_code != 403, (
            f"site_engineer should have construction:update but got 403: {r2.text}")


# ============== RAB granular section access ==============
class TestRabSections:
    def test_restrict_site_to_umum_only(self, tokens, project_id):
        # 1) apply restriction
        r = requests.put(f"{API}/admin/rab-sections", headers=_h(tokens["super"]),
                         json={"sections": {"site_engineer": ["umum"]}}, timeout=30)
        assert r.status_code == 200, r.text

        # 2) auth/me reflects restriction
        r_me = requests.get(f"{API}/auth/me", headers=_h(_login(SITE)), timeout=30)
        assert r_me.status_code == 200
        me = r_me.json().get("data") or r_me.json()
        assert me.get("rab_sections") == ["umum"], f"expected only umum, got {me.get('rab_sections')}"

        site_tok = _login(SITE)
        # 3) boq fasum -> 403
        r_fasum = requests.get(f"{API}/boq/items?project_id={project_id}&scope=fasum",
                               headers=_h(site_tok), timeout=30)
        assert r_fasum.status_code == 403, f"fasum should be 403 got {r_fasum.status_code} {r_fasum.text}"

        # 4) boq umum -> 200
        r_umum = requests.get(f"{API}/boq/items?project_id={project_id}&scope=umum",
                              headers=_h(site_tok), timeout=30)
        assert r_umum.status_code == 200, f"umum should be 200 got {r_umum.status_code} {r_umum.text}"

        # 5) rab templates -> 403
        r_tpl = requests.get(f"{API}/rab/templates/unit_type", headers=_h(site_tok), timeout=30)
        assert r_tpl.status_code == 403, f"templates should be 403 got {r_tpl.status_code} {r_tpl.text}"

        # 6) rab summary -> 403
        r_sum = requests.get(f"{API}/rab/projects/{project_id}/summary",
                             headers=_h(site_tok), timeout=30)
        assert r_sum.status_code == 403, f"summary should be 403 got {r_sum.status_code} {r_sum.text}"

    def test_reset_restores_access(self, tokens, project_id):
        r = requests.put(f"{API}/admin/rab-sections", headers=_h(tokens["super"]),
                         json={"sections": {}}, timeout=30)
        assert r.status_code == 200
        site_tok = _login(SITE)
        for path in [
            f"/boq/items?project_id={project_id}&scope=fasum",
            f"/boq/items?project_id={project_id}&scope=umum",
            f"/rab/templates/unit_type",
            f"/rab/projects/{project_id}/summary",
        ]:
            r = requests.get(f"{API}{path}", headers=_h(site_tok), timeout=30)
            assert r.status_code == 200, f"after reset {path} -> {r.status_code} {r.text}"


# ============== Admin permissions payload includes rab_sections ==============
class TestAdminPermissions:
    def test_permissions_has_rab_sections(self, tokens):
        r = requests.get(f"{API}/admin/permissions", headers=_h(tokens["super"]), timeout=30)
        assert r.status_code == 200
        data = r.json().get("data") or {}
        rs = data.get("rab_sections")
        assert rs, "permissions payload missing rab_sections"
        assert "meta" in rs and "map" in rs
        codes = [m["code"] for m in rs["meta"]]
        assert set(codes) == {"unit", "fasum", "umum", "summary"}

    def test_rab_sections_endpoint(self, tokens):
        r = requests.get(f"{API}/admin/rab-sections", headers=_h(tokens["super"]), timeout=30)
        assert r.status_code == 200
        d = r.json().get("data") or {}
        assert "roles" in d and "meta" in d and "map" in d
