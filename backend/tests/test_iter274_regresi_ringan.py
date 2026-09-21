"""Iter274 — regresi ringan sesi ini.

Cakupan:
1. Auth admin/manager (login demo12345)
2. GET /api/approval-rules (daftar aturan)
3. PATCH /api/approval-rules/{id} — validasi merged_max (400) + PATCH sah + restore
4. GET /api/settings/effective — section 'ui' & 'role_home'
5. GET /api/price-approvals (manager) — >=1 pending (read-only)
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
PWD = "demo12345"
ENT = "ent_ksc"


def _login(email):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": PWD}, timeout=30)
    if r.status_code != 200:
        pytest.fail(f"login {email} -> {r.status_code}: {r.text[:300]}")
    tok = r.json().get("access_token") or r.json().get("token")
    assert tok, f"no token in login response: {r.text[:300]}"
    return tok


def _sess(email):
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {_login(email)}", "X-Entity-Id": ENT,
                      "Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def admin():
    return _sess("admin@kainnusantara.id")


@pytest.fixture(scope="module")
def manager():
    return _sess("manager@kainnusantara.id")


# --- Modul: approval-rules -------------------------------------------------
class TestApprovalRules:
    def test_list_rules(self, admin):
        r = admin.get(f"{API}/approval-rules")
        assert r.status_code == 200, r.text[:300]
        rules = r.json()
        assert isinstance(rules, list) and len(rules) > 0
        for k in ("id", "doc_type", "min_amount", "required_role"):
            assert k in rules[0], f"missing {k} in {rules[0]}"
        assert all("_id" not in x for x in rules)

    def test_patch_min_greater_than_existing_max_rejected(self, admin):
        rules = admin.get(f"{API}/approval-rules").json()
        target = next((x for x in rules if x.get("max_amount")), None)
        assert target, "tidak ada aturan dengan max_amount untuk diuji"
        bad = float(target["max_amount"]) + 1_000_000
        r = admin.patch(f"{API}/approval-rules/{target['id']}", json={"min_amount": bad})
        assert r.status_code == 400, f"expected 400, got {r.status_code}: {r.text[:300]}"
        assert "max_amount harus lebih besar dari min_amount" in r.json().get("detail", "")
        # pastikan tidak berubah
        after = admin.get(f"{API}/approval-rules/{target['id']}").json()
        assert after["min_amount"] == target["min_amount"]

    def test_patch_valid_then_restore(self, admin):
        rules = admin.get(f"{API}/approval-rules").json()
        target = next((x for x in rules if x.get("max_amount")), None)
        assert target
        rid = target["id"]
        orig_min = target["min_amount"]
        new_min = float(orig_min) + 1 if float(orig_min) + 1 < float(target["max_amount"]) else 0
        r = admin.patch(f"{API}/approval-rules/{rid}", json={"min_amount": new_min})
        assert r.status_code == 200, r.text[:300]
        assert float(r.json()["min_amount"]) == new_min
        got = admin.get(f"{API}/approval-rules/{rid}").json()
        assert float(got["min_amount"]) == new_min, "PATCH tidak persist"
        assert got.get("max_amount") == target.get("max_amount"), "max_amount ikut berubah"
        # restore
        rb = admin.patch(f"{API}/approval-rules/{rid}", json={"min_amount": orig_min})
        assert rb.status_code == 200, rb.text[:300]
        assert float(admin.get(f"{API}/approval-rules/{rid}").json()["min_amount"]) == float(orig_min)

    def test_patch_unknown_rule_404(self, admin):
        r = admin.patch(f"{API}/approval-rules/nope-xyz", json={"min_amount": 1})
        assert r.status_code == 404, r.text[:200]

    def test_patch_empty_payload_400(self, admin):
        rid = admin.get(f"{API}/approval-rules").json()[0]["id"]
        r = admin.patch(f"{API}/approval-rules/{rid}", json={})
        assert r.status_code == 400


# --- Modul: settings ------------------------------------------------------
class TestSettingsEffective:
    def test_ui_and_role_home_sections(self, admin):
        r = admin.get(f"{API}/settings/effective")
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        body = data.get("settings", data)
        assert "ui" in body, f"section 'ui' tidak ada. keys={list(body.keys())[:20]}"
        assert body["ui"].get("show_coming_soon") is True
        assert body["ui"].get("coming_soon_collapsed") is True
        assert "role_home" in body, f"section 'role_home' tidak ada. keys={list(body.keys())[:20]}"
        assert isinstance(body["role_home"], dict) and len(body["role_home"]) > 0


# --- Modul: price approvals (read-only) ----------------------------------
class TestPriceApprovals:
    def test_manager_list_has_pending(self, manager):
        r = manager.get(f"{API}/price-approvals")
        assert r.status_code == 200, r.text[:300]
        rows = r.json()
        assert isinstance(rows, list) and len(rows) > 0
        assert all("_id" not in x for x in rows)
        pending = [x for x in rows if x.get("status") == "pending"]
        assert len(pending) >= 1, f"tidak ada pending. statuses={{x.get('status') for x in rows}}"


# --- Modul: integritas data demo ----------------------------------------
class TestDemoDataIntact:
    @pytest.mark.parametrize("path,expected", [
        ("/makloon-orders", 5),
        ("/products", 20),
    ])
    def test_counts(self, admin, path, expected):
        r = admin.get(f"{API}{path}")
        assert r.status_code == 200, f"{path} -> {r.status_code}: {r.text[:200]}"
        rows = r.json()
        rows = rows if isinstance(rows, list) else rows.get("items", rows.get("data", []))
        assert len(rows) == expected, f"{path} count {len(rows)} != {expected}"
