"""Iteration 261 — multi-status SO filter (orders pipeline) + sales-return eligibility API.

Covers:
* GET /api/sales-orders?status=a,b,c  → $in semantics (pipeline cards)
* GET /api/sales-orders?status=single → unchanged behaviour
* GET /api/sales-return-policies/eligibility → window_days/deadline/days_remaining
* GET /api/purchase-orders (PO compact panel data source) sanity
"""
import os

import pytest
import requests
from dotenv import dotenv_values

fe = dotenv_values("/app/frontend/.env")
BASE = (os.environ.get("REACT_APP_BACKEND_URL") or fe.get("REACT_APP_BACKEND_URL")).rstrip("/")
PWD = "demo12345"
DIPROSES = ["confirmed", "partially_picked", "picked"]


def login(email):
    r = requests.post(f"{BASE}/api/auth/login", json={"email": email, "password": PWD}, timeout=60)
    assert r.status_code == 200, f"login {email} -> {r.status_code} {r.text[:300]}"
    return r.json()["token"]


@pytest.fixture(scope="module")
def mgr():
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {login('manager@kainnusantara.id')}",
                      "X-Entity-Id": "ent_ksc"})
    return s


@pytest.fixture(scope="module")
def admin():
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {login('admin@kainnusantara.id')}",
                      "X-Entity-Id": "ent_ksc"})
    return s


# ── Orders pipeline: multi-status filter ────────────────────────────────────
class TestOrdersMultiStatus:
    def test_all_orders_baseline(self, mgr):
        r = mgr.get(f"{BASE}/api/sales-orders", timeout=60)
        assert r.status_code == 200, r.text[:300]
        rows = r.json()
        assert isinstance(rows, list) and rows, "no sales orders in KSC scope"

    def test_comma_status_returns_only_those_statuses(self, mgr):
        r = mgr.get(f"{BASE}/api/sales-orders", params={"status": ",".join(DIPROSES)}, timeout=60)
        assert r.status_code == 200, r.text[:300]
        rows = r.json()
        assert isinstance(rows, list)
        bad = sorted({o["status"] for o in rows if o.get("status") not in DIPROSES})
        assert not bad, f"unexpected statuses leaked: {bad}"

    def test_comma_status_equals_union_of_singles(self, mgr):
        union = set()
        for st in DIPROSES:
            r = mgr.get(f"{BASE}/api/sales-orders", params={"status": st}, timeout=60)
            assert r.status_code == 200, r.text[:300]
            for o in r.json():
                assert o["status"] == st
                union.add(o["id"])
        r = mgr.get(f"{BASE}/api/sales-orders", params={"status": ",".join(DIPROSES)}, timeout=60)
        multi = {o["id"] for o in r.json()}
        assert multi == union, f"multi-status mismatch: only-multi={multi - union}, only-single={union - multi}"

    def test_whitespace_and_trailing_comma_tolerated(self, mgr):
        r = mgr.get(f"{BASE}/api/sales-orders", params={"status": " confirmed , picked ,"}, timeout=60)
        assert r.status_code == 200, r.text[:300]
        assert all(o["status"] in ("confirmed", "picked") for o in r.json())

    def test_unknown_status_returns_empty(self, mgr):
        r = mgr.get(f"{BASE}/api/sales-orders", params={"status": "tidak_ada_status"}, timeout=60)
        assert r.status_code == 200, r.text[:300]
        assert r.json() == []

    def test_no_mongo_object_id_leak(self, mgr):
        r = mgr.get(f"{BASE}/api/sales-orders", params={"status": ",".join(DIPROSES)}, timeout=60)
        assert "_id" not in (r.json()[0] if r.json() else {})

    def test_stats_summary_consistent_with_list(self, mgr):
        r = mgr.get(f"{BASE}/api/sales-orders/stats/summary", timeout=60)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        assert "by_status" in data and "total_orders" in data
        for st, info in data["by_status"].items():
            assert "count" in info and "total_amount" in info, (st, info)
        lst = mgr.get(f"{BASE}/api/sales-orders", timeout=60).json()
        if len(lst) < 200:  # list is capped at 200
            assert data["total_orders"] == len(lst)

    def test_requires_auth(self):
        r = requests.get(f"{BASE}/api/sales-orders?status=confirmed,picked", timeout=60)
        assert r.status_code in (401, 403), r.status_code


# ── Return eligibility ─────────────────────────────────────────────────────
class TestReturnEligibility:
    @pytest.fixture(scope="class")
    def any_order_id(self, mgr):
        rows = mgr.get(f"{BASE}/api/sales-orders", timeout=60).json()
        assert rows
        return rows[0]["id"]

    def test_eligibility_shape(self, mgr, any_order_id):
        r = mgr.get(f"{BASE}/api/sales-return-policies/eligibility",
                    params={"order_id": any_order_id, "return_type": "retur"}, timeout=60)
        assert r.status_code == 200, r.text[:400]
        d = r.json()
        for key in ("eligible", "window_days", "deadline", "days_remaining"):
            assert key in d, f"missing '{key}' in {sorted(d)}"
        assert isinstance(d["eligible"], bool)
        assert isinstance(d["window_days"], int) and d["window_days"] >= 0
        if d["days_remaining"] is not None:
            assert isinstance(d["days_remaining"], int)
        assert isinstance(d.get("allowed_return_types", []), list)

    def test_eligibility_without_return_type(self, mgr, any_order_id):
        r = mgr.get(f"{BASE}/api/sales-return-policies/eligibility",
                    params={"order_id": any_order_id}, timeout=60)
        assert r.status_code == 200, r.text[:300]
        assert "window_days" in r.json()

    def test_eligibility_unknown_order_404(self, mgr):
        r = mgr.get(f"{BASE}/api/sales-return-policies/eligibility",
                    params={"order_id": "ORDER-TIDAK-ADA"}, timeout=60)
        assert r.status_code == 404, f"{r.status_code} {r.text[:200]}"

    def test_eligibility_missing_param_422(self, mgr):
        r = mgr.get(f"{BASE}/api/sales-return-policies/eligibility", timeout=60)
        assert r.status_code == 422, r.status_code

    def test_eligibility_requires_auth(self, any_order_id):
        r = requests.get(f"{BASE}/api/sales-return-policies/eligibility",
                         params={"order_id": any_order_id}, timeout=60)
        assert r.status_code in (401, 403), r.status_code

    def test_eligibility_matches_active_return(self, mgr):
        """Panel is rendered from an ACTIVE return's order_id — that path must work."""
        r = mgr.get(f"{BASE}/api/sales-returns", timeout=60)
        assert r.status_code == 200, r.text[:300]
        rows = r.json()
        rows = rows.get("items", rows) if isinstance(rows, dict) else rows
        active = [x for x in rows if x.get("status") in
                  ("draft", "pending_approval", "approved", "inspecting", "inspected")
                  and x.get("order_id")]
        if not active:
            pytest.skip("no active sales return with order_id in demo data")
        ret = active[0]
        r = mgr.get(f"{BASE}/api/sales-return-policies/eligibility",
                    params={"order_id": ret["order_id"],
                            "return_type": ret.get("return_type") or ""}, timeout=60)
        assert r.status_code == 200, r.text[:400]
        assert "deadline" in r.json()


# ── PO compact panel data source ───────────────────────────────────────────
class TestPurchaseOrders:
    def test_po_list_and_detail(self, admin):
        r = admin.get(f"{BASE}/api/purchase-orders", timeout=60)
        assert r.status_code == 200, r.text[:300]
        rows = r.json()
        rows = rows.get("items", rows) if isinstance(rows, dict) else rows
        assert rows, "no purchase orders"
        po = rows[0]
        for key in ("id", "status"):
            assert key in po, sorted(po)
        assert po.get("po_number") or po.get("number"), sorted(po)
        d = admin.get(f"{BASE}/api/purchase-orders/{po['id']}", timeout=60)
        assert d.status_code == 200, d.text[:300]
        body = d.json()
        assert "_id" not in body
        assert isinstance(body.get("items", []), list)
