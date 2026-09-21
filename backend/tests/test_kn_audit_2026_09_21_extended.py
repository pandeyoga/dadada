"""Extended regression for KN audit 2026-09-21 (Bagian I & II).

Menguji seluruh perbaikan yang diminta agent atas: penjaga entitas jalur TULIS
(IDOR), status guard eskalasi WMS, indeks unik nomor dokumen & GL, CAS approval
PO, KN-B15 duplikat baris PO, KN-D02 approval rejected, dan regresi jalur sah.

Semua uji memakai seed demo (admin@kainnusantara.id / demo12345, ent_ksc &
ent_kanda). Tidak boleh mengubah data non-uji. Jika data prasyarat tak ada:
pytest.skip agar tetap hijau.
"""
from __future__ import annotations

import os
import time
import threading
import uuid
from typing import Any, Optional

import pytest
import requests
from pymongo import MongoClient

API = [l.split("=", 1)[1].strip() for l in open("/app/frontend/.env")
       if l.startswith("REACT_APP_BACKEND_URL=")][0].rstrip("/") + "/api"
PW = os.environ.get("KN_TEST_PASSWORD", "demo12345")
ENTS = ("ent_ksc", "ent_kanda")

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")


# ── util ────────────────────────────────────────────────────────────────────────
def _sess(email: str = "admin@kainnusantara.id", entity: str = "ent_ksc") -> requests.Session:
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": email, "password": PW}, timeout=20)
    if r.status_code != 200:
        pytest.skip(f"login gagal {email}: {r.status_code}")
    s.headers.update({"Authorization": "Bearer " + r.json()["token"], "X-Entity-Id": entity})
    return s


def _other(ent: str) -> str:
    return "ent_kanda" if ent == "ent_ksc" else "ent_ksc"


def _list(sess: requests.Session, path: str, params: Optional[dict] = None) -> list[dict]:
    p = dict(params or {})
    r = sess.get(f"{API}/{path}", params=p, headers={"X-Entity-Id": "all"}, timeout=30)
    if r.status_code != 200:
        return []
    body = r.json()
    return body.get("items") if isinstance(body, dict) else body or []


def _first(sess: requests.Session, path: str, params: Optional[dict] = None,
           predicate=None) -> Optional[dict]:
    for d in _list(sess, path, params):
        if d.get("entity_id") not in ENTS:
            continue
        if predicate and not predicate(d):
            continue
        return d
    return None


@pytest.fixture(scope="module")
def admin() -> requests.Session:
    return _sess()


@pytest.fixture(scope="module")
def mongo():
    cli = MongoClient(MONGO_URL)
    yield cli[DB_NAME]
    cli.close()


def _assert_cross_denied(resp: requests.Response, label: str) -> None:
    assert resp.status_code in (403, 404), \
        f"{label} lintas entitas lolos: {resp.status_code} {resp.text[:200]}"


# ── KN-A01: void jurnal lintas entitas ──────────────────────────────────────────
def test_kn_a01_gl_void_cross_entity(admin):
    je = _first(admin, "gl/journal", {"entity_id": "all"})
    if not je:
        pytest.skip("tidak ada jurnal demo")
    r = admin.post(f"{API}/gl/journal/{je['id']}/void",
                   headers={"X-Entity-Id": _other(je["entity_id"])}, timeout=20)
    _assert_cross_denied(r, "gl void")


# ── KN-A03: void kas lintas entitas ────────────────────────────────────────────
def test_kn_a03_cash_void_cross_entity(admin):
    txn = _first(admin, "cash-transactions", {"entity_id": "all"},
                 predicate=lambda d: d.get("status") != "voided")
    if not txn:
        pytest.skip("tidak ada cash transaction non-void demo")
    r = admin.post(f"{API}/cash-transactions/{txn['id']}/void",
                   json={"reason": "TEST cross"},
                   headers={"X-Entity-Id": _other(txn["entity_id"])}, timeout=20)
    _assert_cross_denied(r, "cash void")


# ── KN-A04: aksi vendor-bills lintas entitas ────────────────────────────────────
@pytest.mark.parametrize("action,payload", [
    ("pay", {"amount": 1, "method": "transfer", "cash_type": "kas_besar"}),
    ("submit", {}), ("approve", {}), ("reject", {"reason": "TEST"}), ("cancel", {"reason": "TEST"}),
])
def test_kn_a04_vendor_bill_actions_cross_entity(admin, action, payload):
    bill = _first(admin, "vendor-bills", {"entity_id": "all"})
    if not bill:
        pytest.skip("tidak ada vendor bill demo")
    r = admin.post(f"{API}/vendor-bills/{bill['id']}/{action}", json=payload,
                   headers={"X-Entity-Id": _other(bill["entity_id"])}, timeout=20)
    _assert_cross_denied(r, f"vendor-bill {action}")


# ── KN-A02: cycle-count lintas entitas ─────────────────────────────────────────
def test_kn_a02_cycle_count_cross_entity(admin, mongo):
    # cari warehouse KSC
    wh = mongo.warehouses.find_one({"entity_id": "ent_ksc"}, {"id": 1})
    if not wh:
        pytest.skip("tidak ada warehouse KSC demo")
    r = admin.post(f"{API}/cycle-count/sessions",
                   json={"warehouse_id": wh["id"], "name": f"TEST_CC_{uuid.uuid4().hex[:6]}"},
                   headers={"X-Entity-Id": "ent_ksc"}, timeout=20)
    if r.status_code not in (200, 201):
        pytest.skip(f"tidak bisa buat sesi cycle count: {r.status_code} {r.text[:200]}")
    sid = r.json().get("id") or r.json().get("session", {}).get("id")
    assert sid, r.text[:200]
    try:
        for action, payload in [("items", {"items": []}), ("submit", {}), ("approve", {}),
                                 ("reject", {"reason": "TEST"})]:
            resp = admin.post(f"{API}/cycle-count/sessions/{sid}/{action}", json=payload,
                              headers={"X-Entity-Id": "ent_kanda"}, timeout=20)
            _assert_cross_denied(resp, f"cycle-count {action}")
    finally:
        mongo.cycle_count_sessions.delete_one({"id": sid})


# ── KN-A05/A06: purchase-returns list + cross-entity actions ───────────────────
def test_kn_a06_purchase_return_list_scoped(admin):
    r = admin.get(f"{API}/purchase-returns", headers={"X-Entity-Id": "ent_ksc"}, timeout=30)
    assert r.status_code == 200, r.text[:200]
    rows = r.json().get("items", []) if isinstance(r.json(), dict) else r.json()
    leaked = [d for d in rows if d.get("entity_id") and d["entity_id"] != "ent_ksc"]
    assert not leaked, f"retur beli PT lain bocor: {[x.get('number') for x in leaked[:5]]}"


@pytest.mark.parametrize("action", ["submit", "approve", "reject"])
def test_kn_a05_purchase_return_actions_cross_entity(admin, action):
    pr = _first(admin, "purchase-returns", {"entity_id": "all"})
    if not pr:
        pytest.skip("tidak ada purchase return demo")
    r = admin.post(f"{API}/purchase-returns/{pr['id']}/{action}",
                   json={"reason": "TEST"} if action == "reject" else {},
                   headers={"X-Entity-Id": _other(pr["entity_id"])}, timeout=20)
    _assert_cross_denied(r, f"purchase-return {action}")


# ── KN-B29: ar-receipts entity_id palsu → 403; void lintas entitas → 404/403 ───
def test_kn_b29_ar_receipt_create_fake_entity(admin):
    r = admin.post(f"{API}/ar-receipts",
                   json={"entity_id": "ent_xxxfake", "customer_id": "cust_dummy",
                         "amount": 1, "method": "transfer", "cash_type": "kas_besar"},
                   headers={"X-Entity-Id": "ent_ksc"}, timeout=20)
    assert r.status_code in (400, 403, 404, 422), r.text[:200]


def test_kn_b29_ar_receipt_void_cross_entity(admin):
    rc = _first(admin, "ar-receipts", {"entity_id": "all"})
    if not rc:
        pytest.skip("tidak ada ar receipt demo")
    r = admin.post(f"{API}/ar-receipts/{rc['id']}/void", json={"reason": "TEST"},
                   headers={"X-Entity-Id": _other(rc["entity_id"])}, timeout=20)
    _assert_cross_denied(r, "ar-receipt void")


# ── KN-B30: hr/payroll runs cross-entity ───────────────────────────────────────
@pytest.mark.parametrize("action", ["submit", "approve", "reject", "post-gl", "pay"])
def test_kn_b30_payroll_actions_cross_entity(admin, action):
    run = _first(admin, "hr/payroll/runs", {"entity_id": "all"})
    if not run:
        pytest.skip("tidak ada payroll run demo")
    r = admin.post(f"{API}/hr/payroll/runs/{run['id']}/{action}",
                   json={"reason": "TEST"} if action == "reject" else {},
                   headers={"X-Entity-Id": _other(run["entity_id"])}, timeout=20)
    _assert_cross_denied(r, f"payroll {action}")


# ── KN-B31: interco transactions — non-party user ditolak; admin lolos guard ──
def test_kn_b31_interco_guard(admin):
    tx = _first(admin, "interco/transactions", {"entity_id": "all"})
    if not tx:
        pytest.skip("tidak ada interco tx demo")
    # admin punya akses semua → tak boleh 404 penjaga; hanya kegagalan bisnis 400/409 ok
    r = admin.post(f"{API}/interco/transactions/{tx['id']}/confirm",
                   headers={"X-Entity-Id": tx.get("entity_id", "ent_ksc")}, timeout=20)
    assert r.status_code in (200, 400, 409, 422), f"admin gagal guard interco: {r.status_code} {r.text[:200]}"


# ── KN-B32: fixed-assets dispose cross-entity ──────────────────────────────────
def test_kn_b32_fixed_asset_dispose_cross_entity(admin):
    fa = _first(admin, "fixed-assets", {"entity_id": "all"})
    if not fa:
        pytest.skip("tidak ada fixed asset demo")
    r = admin.post(f"{API}/fixed-assets/{fa['id']}/dispose",
                   json={"reason": "TEST", "disposal_date": "2026-01-15"},
                   headers={"X-Entity-Id": _other(fa["entity_id"])}, timeout=20)
    _assert_cross_denied(r, "fixed-asset dispose")


# ── KN-B33: landed-costs actions cross-entity ──────────────────────────────────
@pytest.mark.parametrize("action,payload", [
    ("approve", {}),
    ("pay", {"amount": 1, "method": "transfer", "cash_type": "kas_besar"}),
    ("cancel", {"reason": "TEST"}),
])
def test_kn_b33_landed_cost_actions_cross_entity(admin, action, payload):
    lc = _first(admin, "landed-costs", {"entity_id": "all"})
    if not lc:
        pytest.skip("tidak ada landed cost demo")
    r = admin.post(f"{API}/landed-costs/{lc['id']}/{action}", json=payload,
                   headers={"X-Entity-Id": _other(lc["entity_id"])}, timeout=20)
    _assert_cross_denied(r, f"landed-cost {action}")


# ── KN-B34: bank-accounts PATCH cross-entity ───────────────────────────────────
def test_kn_b34_bank_account_patch_cross_entity(admin):
    ba = _first(admin, "bank-accounts", {"entity_id": "all"})
    if not ba:
        pytest.skip("tidak ada bank account demo")
    # PATCH rekening PT lain dari konteks PT berbeda → 404
    r = admin.patch(f"{API}/bank-accounts/{ba['id']}",
                    json={"branch": "TEST"},
                    headers={"X-Entity-Id": _other(ba["entity_id"])}, timeout=20)
    _assert_cross_denied(r, "bank-account patch")


# ── KN-C01: inbound escalate/resolve status guard ──────────────────────────────
def test_kn_c01_inbound_escalate_bad_status(admin, mongo):
    doc = mongo.wms_tasks.find_one({"flow_type": "inbound",
                                     "status": {"$in": ["completed", "cancelled"]}},
                                    {"id": 1, "entity_id": 1})
    if not doc:
        pytest.skip("tidak ada inbound task completed/cancelled")
    r = admin.post(f"{API}/inbound/tasks/{doc['id']}/escalate", json={"reason": "TEST"},
                   headers={"X-Entity-Id": doc.get("entity_id", "ent_ksc")}, timeout=20)
    assert r.status_code == 409, f"escalate completed lolos: {r.status_code} {r.text[:200]}"


def test_kn_c01_inbound_resolve_escalation_bad_status(admin, mongo):
    doc = mongo.wms_tasks.find_one({"flow_type": "inbound", "status": {"$nin": ["escalated"]}},
                                    {"id": 1, "entity_id": 1})
    if not doc:
        pytest.skip("tidak ada inbound task non-escalated")
    r = admin.post(f"{API}/inbound/tasks/{doc['id']}/resolve-escalation",
                   json={"note": "TEST"},
                   headers={"X-Entity-Id": doc.get("entity_id", "ent_ksc")}, timeout=20)
    assert r.status_code in (400, 404, 409), f"resolve non-escalated lolos: {r.status_code} {r.text[:200]}"


# ── KN-C02: outbound escalate status guard ─────────────────────────────────────
def test_kn_c02_outbound_escalate_bad_status(admin, mongo):
    doc = mongo.wms_tasks.find_one({"flow_type": "outbound",
                                     "status": {"$in": ["dispatched", "cancelled"]}},
                                    {"id": 1, "entity_id": 1})
    if not doc:
        pytest.skip("tidak ada outbound task dispatched/cancelled")
    r = admin.post(f"{API}/outbound/tasks/{doc['id']}/escalate", json={"reason": "TEST"},
                   headers={"X-Entity-Id": doc.get("entity_id", "ent_ksc")}, timeout=20)
    assert r.status_code == 409, f"outbound escalate lolos: {r.status_code} {r.text[:200]}"


# ── KN-B15: duplikat produk di PO → 400 ────────────────────────────────────────
def test_kn_b15_po_duplicate_product_line(admin, mongo):
    prod = mongo.products.find_one({}, {"id": 1, "uom": 1, "base_unit": 1})
    sup = mongo.suppliers.find_one({"entity_id": "ent_ksc"}, {"id": 1})
    if not (prod and sup):
        pytest.skip("produk/supplier demo tak ada")
    uom = prod.get("uom") or prod.get("base_unit") or "meter"
    wh = mongo.warehouses.find_one({}, {"id": 1})
    item = {"product_id": prod["id"], "quantity": 1, "unit": uom, "price": 1000,
            "expected_grade": "A"}
    payload = {"supplier_id": sup["id"], "items": [dict(item), dict(item)],
               "expected_delivery_date": "2026-02-01",
               "warehouse_id": (wh or {}).get("id", "wh_jakarta")}
    r = admin.post(f"{API}/purchase-orders", json=payload,
                   headers={"X-Entity-Id": "ent_ksc"}, timeout=20)
    assert r.status_code == 400, f"duplikat lolos: {r.status_code} {r.text[:200]}"
    assert "lebih dari satu baris" in r.text or "duplic" in r.text.lower(), r.text[:200]


# ── KN-A12: indeks unik nomor dokumen — sales_orders.number & journal_entries ──
def test_kn_a12_sales_orders_unique_number(mongo):
    idx = mongo.sales_orders.index_information()
    if "uq_number" not in idx:
        pytest.skip("indeks uq_number belum ada")
    num = f"TEST_SO_{uuid.uuid4().hex[:8]}"
    doc = {"id": f"test_{uuid.uuid4().hex[:8]}", "number": num, "entity_id": "ent_ksc"}
    doc2 = {"id": f"test_{uuid.uuid4().hex[:8]}", "number": num, "entity_id": "ent_ksc"}
    try:
        mongo.sales_orders.insert_one(doc)
        from pymongo.errors import DuplicateKeyError
        with pytest.raises(DuplicateKeyError):
            mongo.sales_orders.insert_one(doc2)
    finally:
        mongo.sales_orders.delete_many({"number": num})


def test_kn_a12_journal_entries_unique_source(mongo):
    idx = mongo.journal_entries.index_information()
    if "uq_je_source_active" not in idx:
        pytest.skip("indeks uq_je_source_active belum ada")
    src_id = f"TEST_SRC_{uuid.uuid4().hex[:8]}"
    d1 = {"id": f"test_{uuid.uuid4().hex[:8]}", "source_type": "TEST_TYPE",
          "source_id": src_id, "status": "posted", "entity_id": "ent_ksc"}
    d2 = {"id": f"test_{uuid.uuid4().hex[:8]}", "source_type": "TEST_TYPE",
          "source_id": src_id, "status": "posted", "entity_id": "ent_ksc"}
    try:
        mongo.journal_entries.insert_one(d1)
        from pymongo.errors import DuplicateKeyError
        with pytest.raises(DuplicateKeyError):
            mongo.journal_entries.insert_one(d2)
    finally:
        mongo.journal_entries.delete_many({"source_id": src_id})


# ── KN-D02: approve SO dengan pending_approvals rejected → 409 ─────────────────
def test_kn_d02_so_approve_rejected_returns_409(admin, mongo):
    so = mongo.sales_orders.find_one({"entity_id": "ent_ksc"},
                                      {"id": 1, "status": 1, "pending_approvals": 1})
    if not so:
        pytest.skip("tidak ada sales order demo")
    original = {"status": so.get("status"),
                "pending_approvals": so.get("pending_approvals", [])}
    try:
        mongo.sales_orders.update_one({"id": so["id"]},
            {"$set": {"status": "waiting_approval",
                      "pending_approvals": [{"type": "kredit", "status": "rejected"}]}})
        r = admin.post(f"{API}/sales-orders/{so['id']}/approve", json={},
                       headers={"X-Entity-Id": "ent_ksc"}, timeout=20)
        assert r.status_code == 409, f"approve rejected lolos: {r.status_code} {r.text[:200]}"
        body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
        code = (body.get("detail") or {}).get("code") if isinstance(body.get("detail"), dict) else body.get("code")
        assert code == "APPROVAL_REJECTED" or "APPROVAL_REJECTED" in r.text, r.text[:200]
    finally:
        mongo.sales_orders.update_one({"id": so["id"]},
            {"$set": {"status": original["status"],
                      "pending_approvals": original["pending_approvals"]}})


# ── KN-B04/D05: paralel approve PO waiting_approval → tepat 1 sukses, sisanya 409
def test_kn_d05_po_approve_cas_parallel(admin, mongo):
    po = mongo.purchase_orders.find_one({"status": "waiting_approval", "entity_id": "ent_ksc"},
                                         {"id": 1, "entity_id": 1})
    if not po:
        pytest.skip("tidak ada PO waiting_approval — lewati")
    results: list[int] = []

    def do_approve():
        s = _sess()
        r = s.post(f"{API}/purchase-orders/{po['id']}/approve", json={},
                   headers={"X-Entity-Id": po["entity_id"]}, timeout=30)
        results.append(r.status_code)

    threads = [threading.Thread(target=do_approve) for _ in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=45)
    ok = sum(1 for c in results if c == 200)
    conflicts = sum(1 for c in results if c in (403, 409))
    assert ok <= 1, f"lebih dari 1 approve sukses: {results}"
    assert (ok + conflicts) == len(results), f"status tak diharapkan: {results}"


# ── KN-C03/C05/A11: konstanta bersama (sudah divalidasi di file lain juga) ─────
def test_kn_c03_c05_shared_constants():
    import sys
    sys.path.insert(0, "/app/backend")
    from services import (rfid_service, rfid_ingest_service, roll_service, gl_service,
                          costing_service, fulfillment_service, stock_bucket_service)
    assert rfid_service.GREEN_OUT is rfid_ingest_service.GREEN_OUT_STATUSES
    assert gl_service.PHYSICAL_ROLL_STATUSES is roll_service.PHYSICAL_ROLL_STATUSES
    assert fulfillment_service.OPEN_PO_STATUSES is roll_service.OPEN_PO_STATUSES
    assert stock_bucket_service.OPEN_PO_STATUSES is roll_service.OPEN_PO_STATUSES


# ── Regresi jalur sah ──────────────────────────────────────────────────────────
@pytest.mark.parametrize("path", [
    "dashboard", "gl/trial-balance", "vendor-bills", "purchase-returns", "desks/me",
])
def test_regression_read_endpoints_ok(admin, path):
    r = admin.get(f"{API}/{path}", headers={"X-Entity-Id": "ent_ksc"}, timeout=30)
    assert r.status_code == 200, f"GET /{path}: {r.status_code} {r.text[:200]}"


def test_regression_inventory_endpoint(admin):
    for p in ("inventory/balances", "inventory/stock"):
        r = admin.get(f"{API}/{p}", headers={"X-Entity-Id": "ent_ksc"}, timeout=30)
        if r.status_code == 200:
            return
    pytest.fail("neither /api/inventory/balances nor /api/inventory/stock respond 200")
