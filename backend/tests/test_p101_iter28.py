"""P101 iter28: Deal cancel (batalkan reservasi) + fund requests module."""
import os
import time

import pytest
import requests

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") + "/api"
PW = "Sipro#2026"


def _login(email):
    s = requests.Session()
    r = s.post(f"{BASE}/auth/login", json={"email": email, "password": PW}, timeout=30)
    assert r.status_code == 200, r.text
    tok = r.json().get("token") or r.json().get("access_token")
    if tok:
        s.headers["Authorization"] = f"Bearer {tok}"
    return s


@pytest.fixture(scope="module")
def sa():
    return _login("superadmin@sipro.co.id")


@pytest.fixture(scope="module")
def fin():
    return _login("finance@sipro.co.id")


@pytest.fixture(scope="module")
def sales():
    return _login("sales@sipro.co.id")


def _get_available_units(sa, need=2):
    r = sa.get(f"{BASE}/units", params={"status": "available", "limit": 10})
    assert r.status_code == 200, r.text
    return r.json()["data"][:need]


def _pick_lead(sa, exclude_ids=()):
    r = sa.get(f"{BASE}/leads", params={"limit": 50})
    leads = r.json()["data"]
    for l in leads:
        if l["id"] in exclude_ids:
            continue
        if l.get("stage") in ("acquisition", "nurturing", "appointment"):
            return l
    return None


# ---- Deal cancel flow ----

class TestDealCancel:
    def test_preview_unpaid_and_admin_cancel_paid(self, sa, fin):
        units = _get_available_units(sa, 2)
        assert len(units) >= 1
        lead = _pick_lead(sa)
        assert lead
        r = sa.post(f"{BASE}/deals/reserve", json={
            "unit_id": units[0]["id"], "lead_id": lead["id"],
            "booking_fee": 5000000, "notes": "iter28-admin"
        })
        assert r.status_code == 200, r.text
        deal = r.json()["data"]

        # preview unpaid as super_admin
        pv = sa.get(f"{BASE}/deals/{deal['id']}/cancel-preview").json()["data"]
        assert pv["can_cancel"] is True
        assert pv["requires_admin"] is False

        # pay BF
        r = fin.post(f"{BASE}/booking-fee/deals/{deal['id']}/pay",
                     json={"amount": 5000000, "method": "transfer", "note": "iter28"})
        assert r.status_code == 200, r.text

        # sales preview shows can_cancel false with admin blocked_reason
        sales = _login("sales@sipro.co.id")
        pv_s = sales.get(f"{BASE}/deals/{deal['id']}/cancel-preview").json()["data"]
        assert pv_s["can_cancel"] is False
        assert "admin" in (pv_s.get("blocked_reason") or "").lower()
        # sales cancel blocked
        r = sales.post(f"{BASE}/deals/{deal['id']}/cancel", json={"reason": "coba sales cancel"})
        assert r.status_code in (400, 403), r.text

        # admin preview: refund_modes present
        pv_a = sa.get(f"{BASE}/deals/{deal['id']}/cancel-preview").json()["data"]
        assert pv_a["can_cancel"] is True
        assert pv_a["requires_admin"] is True
        assert set(pv_a["refund_modes"]) >= {"full", "partial", "forfeit"}

        # admin cancel without refund_mode → 400
        r = sa.post(f"{BASE}/deals/{deal['id']}/cancel", json={"reason": "test batal admin"})
        assert r.status_code == 400, r.text

        # admin cancel partial ok
        r = sa.post(f"{BASE}/deals/{deal['id']}/cancel", json={
            "reason": "iter28 partial refund", "refund_mode": "partial", "refund_amount": 2000000
        })
        assert r.status_code == 200, r.text
        d = r.json()["data"]
        assert d["status"] == "cancelled"

        # unit back to available (via list filter)
        rr = sa.get(f"{BASE}/units", params={"q": units[0]["code"], "limit": 5}).json()["data"]
        u = next((x for x in rr if x["id"] == units[0]["id"]), None)
        assert u and u["status"] == "available"

        # bf invoice reflects refund
        bf = sa.get(f"{BASE}/booking-fee/deals/{deal['id']}").json()["data"]["invoice"]
        assert float(bf.get("refunded_total") or 0) == 2000000
        assert float(bf.get("forfeited_total") or 0) == 3000000

        # lead stage back to nurturing
        ld = sa.get(f"{BASE}/leads/{lead['id']}").json()["data"]
        assert ld.get("stage") == "nurturing"

    def test_sales_cancel_unpaid_own(self, sales, sa):
        units = _get_available_units(sa, 2)
        # find lead owned by sales, stage nurturing/appointment/acquisition
        leads = sales.get(f"{BASE}/leads", params={"limit": 50}).json()["data"]
        ml = next((l for l in leads if l.get("stage") in ("acquisition", "nurturing", "appointment")), None)
        if not ml or not units:
            pytest.skip("no candidate lead/unit for sales")
        r = sales.post(f"{BASE}/deals/reserve", json={
            "unit_id": units[0]["id"], "lead_id": ml["id"], "booking_fee": 1000000,
            "notes": "iter28-sales"
        })
        assert r.status_code == 200, r.text
        deal = r.json()["data"]
        # preview
        pv = sales.get(f"{BASE}/deals/{deal['id']}/cancel-preview").json()["data"]
        assert pv["can_cancel"] is True
        assert pv["requires_admin"] is False
        # short reason rejected
        r = sales.post(f"{BASE}/deals/{deal['id']}/cancel", json={"reason": "no"})
        assert r.status_code in (400, 422), r.text
        # ok cancel
        r = sales.post(f"{BASE}/deals/{deal['id']}/cancel", json={"reason": "pembeli mundur iter28"})
        assert r.status_code == 200, r.text
        assert r.json()["data"]["status"] == "cancelled"
        rr = sa.get(f"{BASE}/units", params={"q": units[0]["code"], "limit": 5}).json()["data"]
        u = next((x for x in rr if x["id"] == units[0]["id"]), None)
        assert u and u["status"] == "available"


# ---- Fund requests ----

class TestFundRequests:
    def test_full_flow(self, sales, fin):
        # expense create
        r = sales.post(f"{BASE}/fund-requests", json={
            "type": "expense", "title": "ATK iter28", "amount": 250000, "category": "atk_kantor"
        })
        assert r.status_code == 200, r.text
        fr = r.json()["data"]
        assert fr["status"] == "submitted"
        assert (fr.get("no") or "").startswith("PGJ/")

        # reimbursement without attachment
        r = sales.post(f"{BASE}/fund-requests", json={
            "type": "reimbursement", "title": "Bensin", "amount": 100000
        })
        assert r.status_code == 400, r.text

        # advance flow
        r = sales.post(f"{BASE}/fund-requests", json={
            "type": "advance", "title": "Kas bon iter28", "amount": 500000, "category": "transport"
        })
        assert r.status_code == 200, r.text
        adv = r.json()["data"]

        # sales list: only own, can_approve false
        j = sales.get(f"{BASE}/fund-requests").json()
        assert j["can_approve"] is False
        ids = {x["id"] for x in j["data"]}
        assert fr["id"] in ids and adv["id"] in ids

        # finance list: can_approve true
        jf = fin.get(f"{BASE}/fund-requests").json()
        assert jf["can_approve"] is True

        # sales approve own → 403
        r = sales.post(f"{BASE}/fund-requests/{fr['id']}/approve", json={})
        assert r.status_code == 403, r.text

        # finance approve
        r = fin.post(f"{BASE}/fund-requests/{fr['id']}/approve", json={"approved_amount": 200000})
        assert r.status_code == 200, r.text
        assert r.json()["data"]["status"] == "approved"

        # disburse non-advance → status settled with journal_ids
        r = fin.post(f"{BASE}/fund-requests/{fr['id']}/disburse", json={"amount": 200000, "source": "bank"})
        assert r.status_code == 200, r.text
        d = r.json()["data"]
        assert d["status"] == "settled"
        assert d.get("journal_ids")

        # advance approve then disburse (status disbursed), then settle
        fin.post(f"{BASE}/fund-requests/{adv['id']}/approve", json={})
        r = fin.post(f"{BASE}/fund-requests/{adv['id']}/disburse", json={"source": "kas"})
        assert r.status_code == 200, r.text
        assert r.json()["data"]["status"] == "disbursed"
        r = sales.post(f"{BASE}/fund-requests/{adv['id']}/settle", json={
            "items": [{"category": "transport", "description": "Grab", "amount": 350000}]
        })
        assert r.status_code == 200, r.text
        d = r.json()["data"]
        assert d["status"] == "settled"
        assert float(d.get("returned_amount") or 0) == 150000

        # reject requires status submitted/approved
        r = fin.post(f"{BASE}/fund-requests/{fr['id']}/reject", json={"reason": "already settled"})
        assert r.status_code in (400, 409), r.text

        # cancel by requester on submitted
        r = sales.post(f"{BASE}/fund-requests", json={
            "type": "expense", "title": "To cancel", "amount": 50000, "category": "atk_kantor"
        })
        fr2 = r.json()["data"]
        r = sales.post(f"{BASE}/fund-requests/{fr2['id']}/cancel", json={"reason": "batal"})
        assert r.status_code == 200, r.text

        # summary
        for c in (sales, fin):
            r = c.get(f"{BASE}/fund-requests/summary")
            assert r.status_code == 200, r.text
            assert "data" in r.json()
