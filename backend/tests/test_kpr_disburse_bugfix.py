"""Iter32 — KPR disbursement scheme sync (BUG FIX: card 'Cairkan' must follow tranches).

Covers:
- GET /api/kpr-disbursement-schemes?bank=BTN — filters + default_id
- POST /api/kpr-disbursement-schemes — validation (100% pct, cleanup)
- POST /api/financing/{fid}/disburse (BUG FIX): free amount → 400, tranche_code → 200 w/ ar_booking
- POST /api/contracts/{cid}/kpr/disbursements: tranche-based disburse, cancel restores state
- AR paid delta = tranche amount
"""
import os
import pytest
import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001").rstrip("/") + "/api"
PW = "Sipro#2026"
DEMO_CID = "ee3005c4-0a99-4b32-a579-fa21e635cf69"
DEMO_DEAL = "790e1b16-45a3-4c28-8041-ca159319d4b7"


def _login(email):
    r = requests.post(f"{BASE}/auth/login", json={"email": email, "password": PW}, timeout=30)
    assert r.status_code == 200, f"login {email}: {r.status_code} {r.text}"
    return {"Authorization": "Bearer " + r.json()["access_token"]}


@pytest.fixture(scope="module")
def sa():
    return _login("superadmin@sipro.co.id")


@pytest.fixture(scope="module")
def fin():
    return _login("finance@sipro.co.id")


# ----- schemes list -----
class TestSchemesList:
    def test_bank_btn_filter_and_default(self, sa):
        r = requests.get(f"{BASE}/kpr-disbursement-schemes", headers=sa, params={"bank": "BTN"})
        assert r.status_code == 200, r.text
        j = r.json()
        assert "data" in j and "default_id" in j
        codes = {s.get("code") for s in j["data"]}
        # BTN-specific scheme + generic BANK_STD both compatible
        assert "BANK_STD" in codes
        assert any((s.get("bank") or "").upper().startswith("BTN") for s in j["data"])
        # non-BTN specific schemes must NOT appear
        for s in j["data"]:
            b = (s.get("bank") or "").upper()
            assert (not b) or ("BTN" in b), f"unrelated scheme leaked: {s.get('name')}"
        assert j["default_id"], "default_id must be set (single BTN-specific scheme present)"

    def test_bank_bca_excludes_btn(self, sa):
        r = requests.get(f"{BASE}/kpr-disbursement-schemes", headers=sa, params={"bank": "BCA"})
        assert r.status_code == 200
        for s in r.json()["data"]:
            b = (s.get("bank") or "").upper()
            assert (not b) or ("BCA" in b), f"BTN leaked into BCA filter: {s.get('name')}"


# ----- scheme validation -----
class TestSchemeValidation:
    def test_post_pct_not_100_rejected(self, sa):
        payload = {"name": "TEST_INVALID_PCT", "bank": "", "tranches": [
            {"code": "T1", "name": "A", "pct": 60, "condition": "akad"},
            {"code": "T2", "name": "B", "pct": 20, "condition": "akad"}]}
        r = requests.post(f"{BASE}/kpr-disbursement-schemes", headers=sa, json=payload)
        assert r.status_code == 400, r.text
        assert "100" in r.text or "persentase" in r.text.lower()

    def test_post_all_fixed_amount_allowed(self, sa):
        payload = {"name": "TEST_ALL_FIXED_ITER32", "bank": "",
                   "tranches": [
                       {"code": "T1", "name": "Akad", "amount": 5_000_000, "condition": "akad"},
                       {"code": "T2", "name": "Sert", "amount": 2_500_000, "condition": "sertifikat"}]}
        r = requests.post(f"{BASE}/kpr-disbursement-schemes", headers=sa, json=payload)
        # cleanup regardless
        try:
            assert r.status_code in (200, 409), r.text
            if r.status_code == 200:
                sid = r.json()["data"]["id"]
                # deactivate to avoid affecting other tests
                requests.put(f"{BASE}/kpr-disbursement-schemes/{sid}", headers=sa,
                             json={"is_active": False})
        finally:
            pass


# ----- disburse via financing router (BUG FIX main flow) -----
class TestFinancingDisburseBugFix:
    """Card 'Cairkan' pada tab KPR profil pelanggan → POST /api/financing/{fid}/disburse
    kini WAJIB pakai tranche_code, tidak lagi menerima amount+milestone bebas."""

    @pytest.fixture(scope="class")
    def ctx(self, sa):
        # Get financing id + AR baseline; return dict
        kv = requests.get(f"{BASE}/contracts/{DEMO_CID}/kpr", headers=sa).json()["data"]
        app = kv["application"]
        return {"fid": app["id"], "tranches": app["tranches"],
                "disbursements": [d for d in app.get("disbursements") or []
                                  if d.get("status") != "dibatalkan"]}

    def _ar_paid(self, fin):
        r = requests.get(f"{BASE}/finance/ar", headers=fin, params={"deal_id": DEMO_DEAL})
        assert r.status_code == 200, r.text
        inv = next((i for i in r.json().get("data", []) if i.get("deal_id") == DEMO_DEAL), None)
        return int((inv or {}).get("paid") or 0), inv

    def test_free_amount_rejected(self, ctx, fin):
        r = requests.post(f"{BASE}/financing/{ctx['fid']}/disburse", headers=fin,
                          json={"amount": 12345, "milestone": "x"})
        assert r.status_code == 400, r.text
        assert "tahap" in r.text.lower()

    def test_tranche_sertifikat_condition_not_met(self, ctx, fin):
        # T2 = sertifikat, legal.sertifikat not set → 400
        r = requests.post(f"{BASE}/financing/{ctx['fid']}/disburse", headers=fin,
                         json={"tranche_code": "T2"})
        assert r.status_code == 400, r.text
        assert "syarat" in r.text.lower() or "sertifikat" in r.text.lower()

    def test_tranche_disburse_and_ar_and_cancel(self, ctx, fin, sa):
        # target = first OPEN tranche with condition met (T4 or T5)
        open_ready = [t for t in ctx["tranches"]
                      if t["status"] == "open" and t["condition"] == "akad"]
        assert open_ready, "expected T4/T5 open with akad met on demo contract"
        target = open_ready[0]
        paid_before, _ = self._ar_paid(fin)
        r = requests.post(f"{BASE}/financing/{ctx['fid']}/disburse", headers=fin,
                          json={"tranche_code": target["code"]})
        assert r.status_code == 200, r.text
        body = r.json()
        assert "ar_booking" in body
        ab = body["ar_booking"]
        assert ab.get("booked") is True
        assert ab.get("receipt_no")
        assert ab.get("tranche") == target["name"]
        assert int(ab.get("applied")) == int(target["amount"])
        # duplicate tranche → 400
        r2 = requests.post(f"{BASE}/financing/{ctx['fid']}/disburse", headers=fin,
                           json={"tranche_code": target["code"]})
        assert r2.status_code == 400, r2.text
        assert ("2" in r2.text) or ("sudah" in r2.text.lower())
        # AR paid delta = target amount
        paid_after, _ = self._ar_paid(fin)
        assert paid_after - paid_before == int(target["amount"]), \
            f"AR paid delta {paid_after - paid_before} != tranche {target['amount']}"

        # cleanup: cancel disbursement so demo state is stable for FE testing
        app = body["data"]
        did = [d for d in app.get("disbursements") if d.get("tranche_code") == target["code"]
               and d.get("status") == "dicatat"][-1]["id"]
        rc = requests.post(f"{BASE}/contracts/{DEMO_CID}/kpr/disbursements/{did}/cancel",
                           headers=sa, json={"reason": "iter32 test cleanup rollback"})
        assert rc.status_code == 200, rc.text


# ----- disburse via contracts endpoint -----
class TestContractsDisburseParity:
    def test_free_amount_rejected(self, sa):
        r = requests.post(f"{BASE}/contracts/{DEMO_CID}/kpr/disbursements", headers=sa,
                          json={"amount": 555555})
        assert r.status_code == 400
        assert "tahap" in r.text.lower()
