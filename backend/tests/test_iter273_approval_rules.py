"""ITER-273 — Aturan Persetujuan: kontrak CRUD baru (skema mesin) + integrasi mesin evaluate."""
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


@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{API}/auth/login", json={"email": "admin@kainnusantara.id",
                                          "password": "demo12345"}, timeout=30)
    if r.status_code != 200:
        pytest.fail(f"login failed {r.status_code}: {r.text[:300]}")
    token = r.json().get("token")
    if not token:
        pytest.fail(f"no token in login response: {r.text[:300]}")
    s.headers.update({"Authorization": f"Bearer {token}", "X-Entity-Id": ENTITY})
    return s


@pytest.fixture(scope="module")
def created_ids():
    return []


@pytest.fixture(scope="module", autouse=True)
def cleanup(client, created_ids):
    yield
    for rid in created_ids:
        client.delete(f"{API}/approval-rules/{rid}", timeout=30)


# ── GET list: skema mesin & sort ─────────────────────────────────────────────
class TestListContract:
    def test_list_has_engine_schema_and_sorted(self, client):
        r = client.get(f"{API}/approval-rules", timeout=30)
        assert r.status_code == 200, r.text[:300]
        rules = r.json()
        assert isinstance(rules, list)
        assert len(rules) >= 9, f"expected >=9 seed rules, got {len(rules)}"
        for rule in rules:
            assert "_id" not in rule
            for f in ("id", "doc_type", "min_amount", "required_role", "sort", "active"):
                assert f in rule, f"missing {f} in {rule}"
            assert "max_amount" in rule
            assert rule["doc_type"] in ["sales_order", "purchase_order",
                                        "purchase_requisition", "discount"]
            assert rule["required_role"] in ["", "manager", "admin", "owner"]
            assert isinstance(rule["active"], bool)
            # tidak ada skema paralel yang bocor
            assert "threshold_min" not in rule and "is_active" not in rule
        keys = [(x["doc_type"], x["sort"]) for x in rules]
        assert keys == sorted(keys), f"not sorted by doc_type,sort: {keys}"

    def test_seed_rules_all_active(self, client):
        rules = client.get(f"{API}/approval-rules", timeout=30).json()
        seeded = [r for r in rules if not (r.get("description") or "").startswith("TEST_")]
        inactive = [r["id"] for r in seeded if r["active"] is False]
        assert not inactive, f"seed rules inactive: {inactive}"

    def test_filter_by_doc_type(self, client):
        r = client.get(f"{API}/approval-rules?doc_type=discount", timeout=30)
        assert r.status_code == 200
        assert all(x["doc_type"] == "discount" for x in r.json())


# ── POST validasi ────────────────────────────────────────────────────────────
class TestValidation:
    def test_bad_doc_type_400(self, client):
        r = client.post(f"{API}/approval-rules", json={"doc_type": "invoice",
                        "min_amount": 0, "max_amount": 100}, timeout=30)
        assert r.status_code == 400, f"{r.status_code}: {r.text[:200]}"

    def test_bad_role_400(self, client):
        r = client.post(f"{API}/approval-rules", json={"doc_type": "sales_order",
                        "min_amount": 0, "max_amount": 100,
                        "required_role": "supervisor"}, timeout=30)
        assert r.status_code == 400, f"{r.status_code}: {r.text[:200]}"

    def test_max_le_min_400(self, client):
        r = client.post(f"{API}/approval-rules", json={"doc_type": "sales_order",
                        "min_amount": 500, "max_amount": 500}, timeout=30)
        assert r.status_code == 400, f"{r.status_code}: {r.text[:200]}"

    def test_negative_min_422(self, client):
        r = client.post(f"{API}/approval-rules", json={"doc_type": "sales_order",
                        "min_amount": -5}, timeout=30)
        assert r.status_code in (400, 422), f"{r.status_code}: {r.text[:200]}"

    def test_discount_forces_is_percent(self, client, created_ids):
        r = client.post(f"{API}/approval-rules", json={
            "doc_type": "discount", "min_amount": 91, "max_amount": 92,
            "required_role": "owner", "sort": 99,
            "description": "TEST_iter273_disc"}, timeout=30)
        assert r.status_code == 200, r.text[:300]
        rule = r.json()
        created_ids.append(rule["id"])
        assert rule["is_percent"] is True
        got = client.get(f"{API}/approval-rules/{rule['id']}", timeout=30).json()
        assert got["is_percent"] is True
        assert got["min_amount"] == 91 and got["max_amount"] == 92


# ── CRUD + persistence ───────────────────────────────────────────────────────
class TestCrud:
    def test_create_patch_partial_delete(self, client, created_ids):
        r = client.post(f"{API}/approval-rules", json={
            "doc_type": "purchase_order", "min_amount": 1234, "max_amount": 5678,
            "required_role": "manager", "sort": 98, "active": True,
            "description": "TEST_iter273_crud"}, timeout=30)
        assert r.status_code == 200, r.text[:300]
        rule = r.json()
        rid = rule["id"]
        created_ids.append(rid)
        assert rule["min_amount"] == 1234 and rule["max_amount"] == 5678
        assert rule["required_role"] == "manager" and rule["active"] is True
        assert rule["entity_id"] == "all"

        # PATCH partial: hanya {active}
        p = client.patch(f"{API}/approval-rules/{rid}", json={"active": False}, timeout=30)
        assert p.status_code == 200, p.text[:300]
        assert p.json()["active"] is False
        g = client.get(f"{API}/approval-rules/{rid}", timeout=30).json()
        assert g["active"] is False
        assert g.get("is_active") is None, "field lama is_active tidak boleh ditulis"
        assert g["min_amount"] == 1234, "PATCH partial merusak field lain"

        # toggle back
        p2 = client.patch(f"{API}/approval-rules/{rid}", json={"active": True}, timeout=30)
        assert p2.status_code == 200 and p2.json()["active"] is True

        # PATCH range validation
        bad = client.patch(f"{API}/approval-rules/{rid}", json={"max_amount": 10}, timeout=30)
        assert bad.status_code == 400, f"{bad.status_code}: {bad.text[:200]}"

        # DELETE = soft delete
        d = client.delete(f"{API}/approval-rules/{rid}", timeout=30)
        assert d.status_code == 200, d.text[:300]
        after = client.get(f"{API}/approval-rules/{rid}", timeout=30)
        assert after.status_code == 200
        assert after.json()["active"] is False, "soft delete harus set active=false"

    def test_patch_unknown_404(self, client):
        r = client.patch(f"{API}/approval-rules/aprule_nope", json={"active": True}, timeout=30)
        assert r.status_code == 404, f"{r.status_code}: {r.text[:200]}"

    def test_patch_empty_400(self, client, created_ids):
        r = client.post(f"{API}/approval-rules", json={
            "doc_type": "sales_order", "min_amount": 77, "max_amount": 78,
            "sort": 97, "description": "TEST_iter273_empty"}, timeout=30)
        rid = r.json()["id"]
        created_ids.append(rid)
        e = client.patch(f"{API}/approval-rules/{rid}", json={}, timeout=30)
        assert e.status_code == 400, f"{e.status_code}: {e.text[:200]}"


# ── INTEGRASI MESIN: UI-created rule harus dibaca evaluate_approval ──────────
class TestEngineIntegration:
    def test_rule_drives_evaluate_and_removal_restores(self, client):
        base = client.get(f"{API}/settings/evaluate-approval",
                          params={"doc_type": "sales_order", "amount": 1500}, timeout=30)
        assert base.status_code == 200, base.text[:300]
        baseline = base.json()

        r = client.post(f"{API}/approval-rules", json={
            "doc_type": "sales_order", "min_amount": 1000, "max_amount": 2000,
            "required_role": "admin", "sort": 1, "entity_id": ENTITY,
            "description": "TEST_iter273_engine"}, timeout=30)
        assert r.status_code == 200, r.text[:300]
        rid = r.json()["id"]
        try:
            ev = client.get(f"{API}/settings/evaluate-approval",
                            params={"doc_type": "sales_order", "amount": 1500}, timeout=30)
            assert ev.status_code == 200, ev.text[:300]
            data = ev.json()
            assert data["requires_approval"] is True, data
            assert data["required_role"] == "admin", data
            assert data["rule_id"] == rid, data
        finally:
            d = client.delete(f"{API}/approval-rules/{rid}", timeout=30)
            assert d.status_code == 200

        after = client.get(f"{API}/settings/evaluate-approval",
                           params={"doc_type": "sales_order", "amount": 1500}, timeout=30).json()
        assert after.get("rule_id") != rid
        assert after.get("required_role") == baseline.get("required_role"), \
            f"baseline {baseline} vs after {after}"
