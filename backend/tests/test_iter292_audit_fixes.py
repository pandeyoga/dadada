"""Iteration 292 — verification of AUDIT_KN_2026-09-02 fixes (F-01..F-08, E-01, E-02, U-02)."""
import os
import pytest
import requests
from dotenv import dotenv_values
from pymongo import MongoClient

fe = dotenv_values("/app/frontend/.env")
BASE = (os.environ.get("REACT_APP_BACKEND_URL") or fe.get("REACT_APP_BACKEND_URL")).rstrip("/") + "/api"
be = dotenv_values("/app/backend/.env")
MONGO_URL = be.get("MONGO_URL")
DB_NAME = be.get("DB_NAME")

PWD = "demo12345"


@pytest.fixture(scope="session")
def db():
    return MongoClient(MONGO_URL)[DB_NAME]


def _login(email):
    r = requests.post(f"{BASE}/auth/login", json={"email": email, "password": PWD}, timeout=60)
    assert r.status_code == 200, r.text[:300]
    return r.json()["token"]


@pytest.fixture(scope="session")
def admin_token():
    return _login("admin@kainnusantara.id")


@pytest.fixture(scope="session")
def sales3_token():
    return _login("sales3@kainnusantara.id")


def H(token, entity="ent_ksc"):
    return {"Authorization": f"Bearer {token}", "X-Entity-Id": entity, "Content-Type": "application/json"}


# ---------- F-02 / F-03 / F-04: GL sync ----------
class TestGlSync:
    def test_gl_sync_shape_and_no_vendor_bill_repost(self, admin_token):
        r = requests.post(f"{BASE}/gl/sync", headers=H(admin_token), timeout=180)
        assert r.status_code == 200, r.text[:400]
        d = r.json()
        for k in ["sales_orders", "cash_transactions", "vendor_bills", "sales_cogs", "skipped_closed", "errors"]:
            assert k in d, f"missing key {k} in {d}"
        assert d["vendor_bills"] == 0, f"vendor bills re-posted: {d}"

    def test_no_double_posting_vendor_bill_vs_subcon(self, db):
        cur = db.journal_entries.find(
            {"source_type": {"$in": ["vendor_bill", "subcon_service"]},
             "status": {"$ne": "void"}, "reversed": {"$ne": True}},
            {"_id": 0, "source_id": 1, "source_type": 1})
        m = {}
        for je in cur:
            m.setdefault(je.get("source_id"), set()).add(je.get("source_type"))
        dupes = [k for k, v in m.items() if len(v) > 1]
        assert not dupes, f"source_ids with both vendor_bill & subcon_service JE: {dupes[:10]}"


# ---------- F-05 / F-06: AR receipt allocation validation ----------
class TestArReceiptGuards:
    def test_cross_customer_allocation_rejected_400(self, admin_token, db):
        before = len((db.sales_orders.find_one({"id": "so_008"}) or {}).get("payments", []) or [])
        r = requests.post(f"{BASE}/ar-receipts", headers=H(admin_token), json={
            "customer_id": "cust_toko_kain", "amount": 100000, "method": "transfer",
            "allocations": [{"order_id": "so_008", "amount": 100000}]}, timeout=60)
        assert r.status_code == 400, f"expected 400 got {r.status_code}: {r.text[:300]}"
        after = len((db.sales_orders.find_one({"id": "so_008"}) or {}).get("payments", []) or [])
        assert after == before, "orphan payment written on so_008"

    def test_cross_entity_allocation_rejected_403(self, admin_token, db):
        before = len((db.sales_orders.find_one({"id": "so_008"}) or {}).get("payments", []) or [])
        r = requests.post(f"{BASE}/ar-receipts", headers=H(admin_token, "ent_kanda"), json={
            "customer_id": "cust_butik_bali", "entity_id": "ent_kanda", "amount": 100000,
            "method": "transfer", "allocations": [{"order_id": "so_008", "amount": 100000}]}, timeout=60)
        assert r.status_code == 403, f"expected 403 got {r.status_code}: {r.text[:300]}"
        after = len((db.sales_orders.find_one({"id": "so_008"}) or {}).get("payments", []) or [])
        assert after == before, "orphan payment written on so_008"


# ---------- F-07: simulate-payment overpay guard ----------
class TestSimulatePaymentGuard:
    def test_overpay_paid_order_rejected(self, admin_token):
        r = requests.post(f"{BASE}/sales-orders/so_007/simulate-payment", headers=H(admin_token),
                          json={"amount": 1000000, "method": "transfer"}, timeout=60)
        assert r.status_code == 400, f"expected 400 got {r.status_code}: {r.text[:300]}"

    def test_payments_not_exceeding_grand_total(self, db):
        so = db.sales_orders.find_one({"id": "so_007"}, {"_id": 0})
        total_paid = sum(float(p.get("amount", 0)) for p in (so.get("payments") or []))
        assert total_paid <= float(so.get("grand_total", 0)) + 0.01, \
            f"paid {total_paid} > grand_total {so.get('grand_total')}"


# ---------- F-08: interco settlement netting guard ----------
class TestIntercoSettlement:
    @pytest.fixture(scope="class")
    def interco_id(self, db):
        doc = db.interco_transactions.find_one({
            "role": "seller", "seller_entity_id": "ent_kanda", "buyer_entity_id": "ent_ksc",
            "status": {"$in": ["confirmed", "invoiced", "received", "partially_settled"]}}, {"_id": 0})
        if not doc:
            pytest.skip("no matching interco transaction in seed")
        return doc["id"]

    OPEN = ("confirmed", "shipped", "received", "invoiced")

    def _open_remaining(self, db, seller, buyer):
        rows = list(db.interco_transactions.find(
            {"seller_entity_id": seller, "buyer_entity_id": buyer, "role": "seller",
             "status": {"$in": list(self.OPEN)}}, {"_id": 0}))
        return rows, round(sum(float(d.get("grand_total") or 0) - float(d.get("settled_amount") or 0)
                               - float(d.get("returned_amount") or 0) for d in rows), 2)

    def test_netting_over_reverse_receivable_rejected(self, admin_token, db):
        """payer=ent_kanda settles KSC->Kanda bills (4.15jt) while reverse open AR is only 3.24jt."""
        rows, total = self._open_remaining(db, "ent_ksc", "ent_kanda")
        _, reverse = self._open_remaining(db, "ent_kanda", "ent_ksc")
        if total <= reverse:
            pytest.skip(f"seed data cannot exceed reverse AR (total={total}, reverse={reverse})")
        before = db.interco_settlements.count_documents({})
        r = requests.post(f"{BASE}/interco/settlements", headers=H(admin_token, "ent_kanda"), json={
            "payer_entity_id": "ent_kanda", "payee_entity_id": "ent_ksc", "method": "netting",
            "transactions": [{"interco_id": d["id"]} for d in rows]}, timeout=60)
        assert r.status_code == 400, f"expected 400 got {r.status_code}: {r.text[:400]}"
        assert "piutang balik" in r.text.lower(), f"unexpected message: {r.text[:300]}"
        assert db.interco_settlements.count_documents({}) == before, "settlement persisted despite 400"

    def test_netting_within_reverse_receivable_allowed(self, admin_token, db, interco_id):
        """Sanity: netting <= reverse open AR is accepted (guard is not blanket-blocking)."""
        _, reverse = self._open_remaining(db, "ent_ksc", "ent_kanda")
        assert reverse > 0
        r = requests.post(f"{BASE}/interco/settlements", headers=H(admin_token), json={
            "payer_entity_id": "ent_ksc", "payee_entity_id": "ent_kanda", "method": "netting",
            "transactions": [{"interco_id": interco_id, "applied_amount": 1000}]}, timeout=60)
        assert r.status_code == 200, f"expected 200 got {r.status_code}: {r.text[:400]}"

    def test_default_method_is_transfer(self, admin_token, interco_id):
        r = requests.post(f"{BASE}/interco/settlements", headers=H(admin_token), json={
            "payer_entity_id": "ent_ksc", "payee_entity_id": "ent_kanda",
            "transactions": [{"interco_id": interco_id, "applied_amount": 500}]}, timeout=60)
        assert r.status_code == 200, f"expected 200 got {r.status_code}: {r.text[:400]}"
        assert r.json().get("method") == "transfer", r.json().get("method")

    def test_transfer_allowed(self, admin_token, interco_id):
        r = requests.post(f"{BASE}/interco/settlements", headers=H(admin_token), json={
            "payer_entity_id": "ent_ksc", "payee_entity_id": "ent_kanda", "method": "transfer",
            "transactions": [{"interco_id": interco_id, "applied_amount": 1000}]}, timeout=60)
        assert r.status_code == 200, f"expected 200 got {r.status_code}: {r.text[:400]}"


# ---------- E-01: stock-breakdown reservation scoping ----------
class TestStockBreakdownScope:
    def test_reservations_scoped_and_projected(self, sales3_token):
        r = requests.get(f"{BASE}/products/prod_batik_mega/stock-breakdown",
                         headers=H(sales3_token, "ent_kanda"), timeout=60)
        assert r.status_code == 200, r.text[:300]
        res = r.json().get("reservations") or []
        leaks = ["grand_total", "shipping_address", "payments"]
        for item in res:
            assert item.get("entity_id") == "ent_kanda", f"cross-entity reservation leaked: {item}"
            for f in leaks:
                assert f not in item, f"field {f} leaked in reservation: {item}"


# ---------- E-02: cycle-count session scoping ----------
class TestCycleCountScope:
    def test_kanda_scope_excludes_ksc_sessions(self, admin_token):
        r = requests.get(f"{BASE}/cycle-count/sessions", headers=H(admin_token, "ent_kanda"), timeout=60)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        items = data if isinstance(data, list) else data.get("items", data.get("sessions", []))
        bad = [s for s in items if s.get("entity_id") == "ent_ksc"]
        assert not bad, f"ent_ksc sessions visible under ent_kanda: {[s.get('id') for s in bad]}"

    def test_detail_of_other_entity_session_404(self, admin_token):
        r = requests.get(f"{BASE}/cycle-count/sessions/cc_seed_001",
                         headers=H(admin_token, "ent_kanda"), timeout=60)
        assert r.status_code == 404, f"expected 404 got {r.status_code}: {r.text[:200]}"

    def test_ksc_scope_lists_sessions(self, admin_token):
        r = requests.get(f"{BASE}/cycle-count/sessions", headers=H(admin_token), timeout=60)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        items = data if isinstance(data, list) else data.get("items", data.get("sessions", []))
        assert len(items) >= 2, f"expected >=2 ent_ksc sessions, got {len(items)}"


# ---------- U-02: document print HTML ----------
class TestDocumentPrint:
    def test_generate_and_print(self, admin_token):
        r = requests.post(f"{BASE}/documents/generate", headers=H(admin_token),
                          json={"document_type": "invoice", "source_id": "so_001"}, timeout=60)
        assert r.status_code == 200, r.text[:300]
        doc_id = r.json().get("id")
        assert doc_id, r.text[:300]
        p = requests.get(f"{BASE}/documents/{doc_id}/print", headers=H(admin_token), timeout=60)
        assert p.status_code == 200, p.text[:300]
        assert "text/html" in p.headers.get("content-type", ""), p.headers.get("content-type")
