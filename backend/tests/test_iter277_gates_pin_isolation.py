"""Iteration 277 tests: T1 (SO confirm gates), T2 (Internal Requests unblock for sales_admin), T3 (inspection entity isolation), light regression.

Run: cd /app/backend && python -m pytest tests/test_iter277_gates_pin_isolation.py -p no:randomly -n 0 -q -s
"""
import os
import pytest
import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
assert BASE, "REACT_APP_BACKEND_URL must be set"
API = f"{BASE}/api"
PWD = "demo12345"


def _login(email: str) -> str:
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": PWD}, timeout=30)
    assert r.status_code == 200, f"login failed for {email}: {r.status_code} {r.text}"
    return r.json()["token"]


def H(tok: str, ent: str = "ent_ksc") -> dict:
    return {"Authorization": f"Bearer {tok}", "X-Entity-Id": ent, "Content-Type": "application/json"}


# Fixtures ------------------------------------------------------------
@pytest.fixture(scope="module")
def tokens():
    return {
        "admin": _login("admin@kainnusantara.id"),
        "manager": _login("manager@kainnusantara.id"),
        "salesadmin": _login("salesadmin@kainnusantara.id"),
        "sales": _login("sales@kainnusantara.id"),
        "warehouse": _login("warehouse@kainnusantara.id"),
    }


@pytest.fixture(scope="module")
def so_index(tokens):
    """Fetch SOs at ent_ksc as salesadmin; return by ref."""
    r = requests.get(f"{API}/sales-orders", headers=H(tokens["salesadmin"], "ent_ksc"), timeout=30)
    assert r.status_code == 200
    data = r.json()
    items = data if isinstance(data, list) else data.get("items", [])
    return {it.get("ref_id") or it.get("code") or it.get("id"): it for it in items}


# ---------------- T1: SO confirm gates ----------------
class TestT1_ConfirmGates:
    def test_T1_config_verification_default_true(self, tokens):
        # config as admin
        r = requests.get(
            f"{API}/config/effective",
            params={"q": "sales_admin.require_verification_before_confirm"},
            headers=H(tokens["admin"], "ent_ksc"),
            timeout=30,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        # Response may be {items:[{key,value}]} or {value:...}
        val = None
        if isinstance(body, dict):
            if "value" in body:
                val = body["value"]
            elif "items" in body and body["items"]:
                val = body["items"][0].get("value")
            elif "sales_admin.require_verification_before_confirm" in body:
                val = body["sales_admin.require_verification_before_confirm"]
        print("effective config resp:", body)
        assert val is True, f"expected True, got {val!r}"

    def test_T1a_confirm_approved_not_verified_returns_409(self, tokens, so_index):
        # Find an 'approved' SO in KSC that has not been verified. SO-0005 per problem statement.
        target = None
        for ref, so in so_index.items():
            if so.get("status") == "approved":
                target = so
                if ref and "SO-0005" in ref:
                    break
        assert target, f"no approved SO found in KSC. refs={list(so_index.keys())[:20]}"
        sid = target["id"]
        r = requests.post(
            f"{API}/sales-orders/{sid}/confirm",
            headers=H(tokens["salesadmin"], "ent_ksc"),
            json={},
            timeout=30,
        )
        print("T1a confirm resp:", r.status_code, r.text[:400])
        assert r.status_code == 409
        detail = (r.json().get("detail") or "")
        if isinstance(detail, dict):
            detail = str(detail)
        assert "Verifikasi" in detail or "verifikasi" in detail
        assert "Meja Admin Sales" in detail or "meja admin sales" in detail.lower()

    def test_T1b_confirm_waiting_approval_manager_gate(self, tokens, so_index):
        # SO-0007 KSC: waiting_approval
        target = None
        for ref, so in so_index.items():
            if ref and "SO-0007" in ref:
                target = so
                break
        if not target:
            # any waiting_approval SO
            for so in so_index.values():
                if so.get("status") == "waiting_approval":
                    target = so
                    break
        assert target, f"no waiting_approval SO found: {list(so_index.keys())[:20]}"
        sid = target["id"]
        # First verify (should succeed) OR verification gate fires first
        r_verify = requests.post(
            f"{API}/sales-orders/{sid}/verify",
            headers=H(tokens["salesadmin"], "ent_ksc"),
            json={"note": ""},
            timeout=30,
        )
        print("T1b verify:", r_verify.status_code, r_verify.text[:400])
        # per spec: verification -> ACC manager -> confirm ordering. verify may return 200 or 409 (not yet approved).
        r_c = requests.post(
            f"{API}/sales-orders/{sid}/confirm",
            headers=H(tokens["salesadmin"], "ent_ksc"),
            json={},
            timeout=30,
        )
        print("T1b confirm:", r_c.status_code, r_c.text[:400])
        assert r_c.status_code == 409
        detail = r_c.json().get("detail") or ""
        if isinstance(detail, dict):
            detail = str(detail)
        assert ("belum disetujui manajer" in detail.lower()) or ("verifikasi" in detail.lower()), detail

    def test_T1c_happy_path_verify_then_confirm(self, tokens):
        # Refetch fresh SO list to catch changes
        r = requests.get(f"{API}/sales-orders", headers=H(tokens["salesadmin"], "ent_ksc"), timeout=30)
        assert r.status_code == 200
        data = r.json()
        items = data if isinstance(data, list) else data.get("items", [])
        target = None
        for so in items:
            if so.get("status") == "approved":
                target = so
                break
        assert target, "no approved SO available"
        sid = target["id"]
        r_v = requests.post(
            f"{API}/sales-orders/{sid}/verify",
            headers=H(tokens["salesadmin"], "ent_ksc"),
            json={"note": ""},
            timeout=30,
        )
        print("T1c verify:", r_v.status_code, r_v.text[:400])
        assert r_v.status_code == 200, r_v.text
        r_c = requests.post(
            f"{API}/sales-orders/{sid}/confirm",
            headers=H(tokens["salesadmin"], "ent_ksc"),
            json={},
            timeout=30,
        )
        print("T1c confirm:", r_c.status_code, r_c.text[:400])
        assert r_c.status_code == 200, r_c.text
        # verify status becomes confirmed
        r_g = requests.get(f"{API}/sales-orders/{sid}", headers=H(tokens["salesadmin"], "ent_ksc"), timeout=30)
        assert r_g.status_code == 200
        assert r_g.json().get("status") == "confirmed", r_g.json().get("status")


# ---------------- T2: Internal Requests ----------------
class TestT2_InternalRequests:
    def test_T2a_meta_salesadmin_can_decide_and_pick_source(self, tokens):
        r = requests.get(f"{API}/internal-requests/meta", headers=H(tokens["salesadmin"], "ent_ksc"), timeout=30)
        assert r.status_code == 200, r.text
        j = r.json()
        print("T2a meta:", j)
        assert j.get("can_decide") is True
        assert j.get("can_pick_source") is True

    def test_T2b_list_and_detail_and_sources(self, tokens):
        r = requests.get(f"{API}/internal-requests", headers=H(tokens["salesadmin"], "ent_ksc"), timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        items = data if isinstance(data, list) else data.get("items", [])
        assert len(items) >= 1, "list expected non-empty"
        # find PIN-00001 (field is 'number')
        pin1 = None
        for it in items:
            ref = it.get("number") or it.get("ref_id") or it.get("code") or ""
            if "PIN-00001" in ref:
                pin1 = it
                break
        assert pin1, f"KSC/PIN-00001 not found in list: {[it.get('number') for it in items]}"
        pytest.pin1_id = pin1["id"]

        rd = requests.get(f"{API}/internal-requests/{pin1['id']}", headers=H(tokens["salesadmin"], "ent_ksc"), timeout=30)
        print("T2b detail:", rd.status_code, rd.text[:300])
        assert rd.status_code == 200

        rs = requests.get(f"{API}/internal-requests/{pin1['id']}/sources", headers=H(tokens["salesadmin"], "ent_ksc"), timeout=30)
        print("T2b sources:", rs.status_code, rs.text[:400])
        assert rs.status_code == 200
        srcs = rs.json()
        cands = srcs.get("candidates") if isinstance(srcs, dict) else srcs
        assert cands, f"expected candidates, got {srcs}"
        # ent_kanda should appear
        has_kanda = any((c.get("entity_id") == "ent_kanda") for c in cands)
        assert has_kanda, f"ent_kanda missing in candidates: {cands}"

    def test_T2c_convert_creates_interco_pair(self, tokens):
        pin_id = getattr(pytest, "pin1_id", None)
        assert pin_id, "T2b must run first"
        r = requests.post(
            f"{API}/internal-requests/{pin_id}/convert",
            headers=H(tokens["salesadmin"], "ent_ksc"),
            json={"source_entity_id": "ent_kanda", "submit_now": True, "notes": "TEST_T2"},
            timeout=60,
        )
        print("T2c convert:", r.status_code, r.text[:500])
        assert r.status_code == 200, r.text
        body = r.json()
        interco = body.get("interco") or {}
        assert interco.get("pair_id"), f"expected interco.pair_id, got {body}"
        # detail -> status converted
        rd = requests.get(f"{API}/internal-requests/{pin_id}", headers=H(tokens["salesadmin"], "ent_ksc"), timeout=30)
        assert rd.status_code == 200
        assert rd.json().get("status") == "converted", rd.json().get("status")

    def test_T2d_sales_role_unchanged(self, tokens):
        rm = requests.get(f"{API}/internal-requests/meta", headers=H(tokens["sales"], "ent_ksc"), timeout=30)
        assert rm.status_code == 200
        j = rm.json()
        assert j.get("can_decide") is False, j
        # list -> only own
        rl = requests.get(f"{API}/internal-requests", headers=H(tokens["sales"], "ent_ksc"), timeout=30)
        assert rl.status_code == 200
        items = rl.json() if isinstance(rl.json(), list) else rl.json().get("items", [])
        # need a pin id belonging to someone else to test sources 403
        # try known pin1 id
        pin_id = getattr(pytest, "pin1_id", None)
        if pin_id:
            rs = requests.get(f"{API}/internal-requests/{pin_id}/sources", headers=H(tokens["sales"], "ent_ksc"), timeout=30)
            print("T2d sales /sources:", rs.status_code, rs.text[:200])
            assert rs.status_code == 403


# ---------------- T3: inspection entity isolation ----------------
class TestT3_InspectionIsolation:
    @pytest.fixture(scope="class")
    def kanda_inspection_id(self, tokens):
        r = requests.get(f"{API}/inspections", headers=H(tokens["manager"], "ent_kanda"), timeout=30)
        assert r.status_code == 200
        data = r.json()
        items = data if isinstance(data, list) else data.get("items", [])
        target = None
        for it in items:
            ref = it.get("ref_id") or it.get("code") or ""
            if "INS-00001" in ref:
                target = it
                break
        if not target and items:
            target = items[0]
        assert target, f"no KANDA inspection found: {items}"
        print("kanda ins:", target.get("ref_id"), target.get("id"))
        return target["id"]

    @pytest.fixture(scope="class")
    def ksc_inspection_id(self, tokens):
        r = requests.get(f"{API}/inspections", headers=H(tokens["manager"], "ent_ksc"), timeout=30)
        assert r.status_code == 200
        data = r.json()
        items = data if isinstance(data, list) else data.get("items", [])
        target = None
        for it in items:
            ref = it.get("ref_id") or it.get("code") or ""
            if "INS-00001" in ref:
                target = it
                break
        if not target and items:
            target = items[0]
        assert target
        return target["id"]

    def test_T3a_manager_ksc_scope_gets_404_for_kanda(self, tokens, kanda_inspection_id):
        r = requests.get(f"{API}/inspections/{kanda_inspection_id}", headers=H(tokens["manager"], "ent_ksc"), timeout=30)
        print("T3a detail ksc-scope:", r.status_code, r.text[:200])
        assert r.status_code == 404
        rp = requests.get(f"{API}/inspections/{kanda_inspection_id}/pdf", headers=H(tokens["manager"], "ent_ksc"), timeout=30)
        print("T3a pdf ksc-scope:", rp.status_code)
        assert rp.status_code == 404

    def test_T3a_manager_kanda_scope_gets_200(self, tokens, kanda_inspection_id):
        r = requests.get(f"{API}/inspections/{kanda_inspection_id}", headers=H(tokens["manager"], "ent_kanda"), timeout=30)
        assert r.status_code == 200, r.text
        rp = requests.get(f"{API}/inspections/{kanda_inspection_id}/pdf", headers=H(tokens["manager"], "ent_kanda"), timeout=30)
        assert rp.status_code == 200

    def test_T3a_manager_all_scope_gets_200(self, tokens, kanda_inspection_id):
        r = requests.get(f"{API}/inspections/{kanda_inspection_id}", headers=H(tokens["manager"], "all"), timeout=30)
        assert r.status_code == 200, r.text
        rp = requests.get(f"{API}/inspections/{kanda_inspection_id}/pdf", headers=H(tokens["manager"], "all"), timeout=30)
        assert rp.status_code == 200

    def test_T3b_warehouse_ksc_only_404_for_kanda(self, tokens, kanda_inspection_id):
        r = requests.get(f"{API}/inspections/{kanda_inspection_id}", headers=H(tokens["warehouse"], "ent_ksc"), timeout=30)
        print("T3b warehouse kanda:", r.status_code, r.text[:200])
        assert r.status_code == 404

    def test_T3b_manager_ksc_scope_ksc_inspection_ok(self, tokens, ksc_inspection_id):
        r = requests.get(f"{API}/inspections/{ksc_inspection_id}", headers=H(tokens["manager"], "ent_ksc"), timeout=30)
        assert r.status_code == 200, r.text


# ---------------- Light regression ----------------
class TestRegression:
    def test_desk_salesadmin_has_8_queues(self, tokens):
        r = requests.get(f"{API}/sales-admin/desk", headers=H(tokens["salesadmin"], "ent_ksc"), timeout=30)
        assert r.status_code == 200, r.text
        j = r.json()
        # count queues (be tolerant to shape)
        qs = j.get("queues") or j.get("items") or []
        print("desk queues count:", len(qs), "shape keys:", list(j.keys())[:10])
        assert len(qs) >= 8

    def test_home_manager_200(self, tokens):
        r = requests.get(f"{API}/home/manager", headers=H(tokens["manager"], "ent_ksc"), timeout=30)
        print("home/manager:", r.status_code, r.text[:120])
        assert r.status_code == 200
