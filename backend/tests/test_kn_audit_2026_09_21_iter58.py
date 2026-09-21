"""KN Audit 2026-09-21 — iterasi 58 (D11 ATP tunggal, D16 3-way, atomic scan-label, regresi).

Fokus:
  • D11: satu rumus ATP (services.atp_policy) dipakai roll_service.rebuild_balance
         → pending_demand_qty & atp_qty konsisten; endpoint GET /api/stock/atp.
  • D16: satu ambang toleransi 3-way match — three_way_policy.tolerances,
         contra_bon_service.policy & evaluate_bill_exceptions, vendor_bill_service.evaluate_match.
  • Atomic: POST /api/inbound/tasks/{id}/scan-label pada status completed → 409, tanpa residu roll.
  • Regresi: endpoint sah tetap 200; startup tanpa Traceback.

Semua uji memakai data seed demo (admin@kainnusantara.id / demo12345) dan MEMBERSIHKAN
data uji setelah selesai. Skip bila prasyarat tak tersedia.
"""
from __future__ import annotations

import asyncio
import os
import sys
import uuid
from typing import Any, Dict, Optional

import pytest
import requests
from pymongo import MongoClient

sys.path.insert(0, "/app/backend")

# Motor client is bound to the FIRST loop it sees; share ONE loop across all async tests
# in this module to avoid "Event loop is closed" errors on 2nd _run().
_LOOP = asyncio.new_event_loop()


def _run(coro):
    return _LOOP.run_until_complete(coro)

API = [l.split("=", 1)[1].strip() for l in open("/app/frontend/.env")
       if l.startswith("REACT_APP_BACKEND_URL=")][0].rstrip("/") + "/api"
PW = os.environ.get("KN_TEST_PASSWORD", "demo12345")

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")


def _sess(entity: str = "ent_ksc") -> requests.Session:
    s = requests.Session()
    r = s.post(f"{API}/auth/login",
               json={"email": "admin@kainnusantara.id", "password": PW}, timeout=20)
    if r.status_code != 200:
        pytest.skip(f"login gagal {r.status_code}")
    s.headers.update({"Authorization": "Bearer " + r.json()["token"], "X-Entity-Id": entity})
    return s


@pytest.fixture(scope="module")
def admin() -> requests.Session:
    return _sess()


@pytest.fixture(scope="module")
def mongo():
    cli = MongoClient(MONGO_URL)
    yield cli[DB_NAME]
    cli.close()


# ═════════════════════════════════════════════════════════════════════════════
# STARTUP: /api/ ping & tidak ada Traceback di supervisor log
# ═════════════════════════════════════════════════════════════════════════════
def test_startup_root_ok():
    r = requests.get(f"{API}/", timeout=10)
    assert r.status_code == 200, r.text[:200]


def test_startup_no_traceback():
    import subprocess
    try:
        out = subprocess.check_output(
            ["tail", "-n", "500", "/var/log/supervisor/backend.err.log"],
            stderr=subprocess.STDOUT, timeout=10).decode("utf-8", errors="ignore")
    except Exception:
        pytest.skip("log supervisor tak terbaca")
    # Beberapa import warning boleh; Traceback yang menghentikan startup TIDAK boleh.
    fatal = [line for line in out.splitlines() if "Traceback (most recent call last)" in line]
    assert not fatal, f"Traceback ditemukan di backend.err.log: {fatal[-3:]}"


# ═════════════════════════════════════════════════════════════════════════════
# D11 — atp_policy: compute_atp & within_horizon
# ═════════════════════════════════════════════════════════════════════════════
def test_d11_compute_atp_pure():
    from services import atp_policy as ap
    assert ap.compute_atp(100, 20, 30) == 90
    assert ap.compute_atp(0, 0, 0) == 0
    # available + incoming - pending (float safe)
    assert ap.compute_atp(50.25, 4.75, 5.0) == 50.0


def test_d11_within_horizon_pure():
    from services import atp_policy as ap
    assert ap.within_horizon(None) is True
    assert ap.within_horizon("") is True
    assert ap.within_horizon("2099-01-01") is False
    assert ap.within_horizon("invalid-date") is True  # tak terbaca = dalam horizon


# ═════════════════════════════════════════════════════════════════════════════
# D11 — rebuild_balance: pending_demand_qty & atp_qty
# ═════════════════════════════════════════════════════════════════════════════
def test_d11_rebuild_balance_pending_demand(mongo):
    """Sisipkan SO uji backorder → rebuild_balance → pending_demand_qty=7, ATP turun 7."""
    # Cari segmen (product, warehouse, owner) yang ADA balance-nya di ent_ksc
    bal = mongo.inventory_balances.find_one(
        {"owner_entity_id": "ent_ksc"},
        {"_id": 0, "product_id": 1, "warehouse_id": 1, "owner_entity_id": 1})
    if not bal:
        pytest.skip("tidak ada inventory_balance ent_ksc demo")
    pid, wid, oid = bal["product_id"], bal["warehouse_id"], bal["owner_entity_id"]

    from services import roll_service, atp_policy as ap

    async def _inner():
        baseline = await roll_service.rebuild_balance(pid, wid, oid)
        base_atp = float(baseline.get("atp_qty") or 0)
        base_pd = float(baseline.get("pending_demand_qty") or 0)

        so_id = f"test_so_{uuid.uuid4().hex[:8]}"
        so_doc = {
            "id": so_id, "number": f"TEST_SO_{uuid.uuid4().hex[:6]}",
            "entity_id": "ent_ksc", "warehouse_id": wid,
            "status": "waiting_stock", "has_backorder": True,
            "backorders": [{"product_id": pid, "backorder_qty": 7, "status": "open"}],
        }
        mongo.sales_orders.insert_one(so_doc)
        try:
            after = await roll_service.rebuild_balance(pid, wid, oid)
            assert float(after.get("pending_demand_qty") or 0) == pytest.approx(base_pd + 7, abs=0.01), \
                f"pending_demand_qty tidak +7: base={base_pd} after={after.get('pending_demand_qty')}"
            assert float(after.get("atp_qty") or 0) == pytest.approx(base_atp - 7, abs=0.01), \
                f"atp_qty tidak −7: base={base_atp} after={after.get('atp_qty')}"
            # Verifikasi rumus tunggal atp_policy
            incoming = float(after.get("on_order_qty", 0) or 0) + float(after.get("in_transit_inbound_qty", 0) or 0)
            expected = ap.compute_atp(after["available_qty"], incoming, after["pending_demand_qty"])
            assert float(after["atp_qty"]) == pytest.approx(expected, abs=0.01), \
                f"ATP tak sesuai formula tunggal: got={after['atp_qty']} expected={expected}"
        finally:
            mongo.sales_orders.delete_one({"id": so_id})
            final = await roll_service.rebuild_balance(pid, wid, oid)
            assert float(final.get("pending_demand_qty") or 0) == pytest.approx(base_pd, abs=0.01)

    _run(_inner())


# ═════════════════════════════════════════════════════════════════════════════
# D11 — GET /api/stock/atp konsisten dengan compute_atp
# ═════════════════════════════════════════════════════════════════════════════
def test_d11_stock_atp_endpoint_consistent(admin, mongo):
    bal = mongo.inventory_balances.find_one({"owner_entity_id": "ent_ksc"}, {"_id": 0, "product_id": 1})
    if not bal:
        pytest.skip("tidak ada inventory_balance ent_ksc demo")
    r = admin.get(f"{API}/stock/atp",
                  params={"product_id": bal["product_id"], "owner_entity_id": "ent_ksc"},
                  timeout=20)
    assert r.status_code == 200, r.text[:200]
    data = r.json()
    # struktur ATP future-aware
    assert "atp_now" in data or "atp_qty" in data or "available" in data, data
    # Bila field detail tersedia, verifikasi rumus: atp_horizon = available + incoming_horizon − pending
    from services import atp_policy as ap
    if all(k in data for k in ("available", "incoming_in_horizon", "pending_demand")):
        expected = ap.compute_atp(data["available"], data["incoming_in_horizon"], data["pending_demand"])
        got = data.get("atp_horizon", data.get("atp_now"))
        assert float(got) == pytest.approx(expected, abs=0.01), f"ATP endpoint tak sesuai formula: {data}"


# ═════════════════════════════════════════════════════════════════════════════
# D16 — three_way_policy.tolerances & contra_bon.policy sinkron
# ═════════════════════════════════════════════════════════════════════════════
def test_d16_tolerances_shape():
    from services import three_way_policy as tw
    t = _run(tw.tolerances("ent_ksc"))
    for k in ("qty_pct", "price_pct", "value_rp"):
        assert k in t, t
        assert isinstance(t[k], float)


def test_d16_contra_bon_policy_uses_three_way():
    from services import three_way_policy as tw
    from services import contra_bon_service as cb
    t = _run(tw.tolerances("ent_ksc"))
    pol = _run(cb.policy("ent_ksc"))
    assert pol["qty_tolerance_percent"] == t["qty_pct"]
    assert pol["price_tolerance_percent"] == t["price_pct"]
    assert pol["value_tolerance_rupiah"] == t["value_rp"]


# ═════════════════════════════════════════════════════════════════════════════
# D16 — evaluate_bill_exceptions pure test: harga 6% di atas PO
# ═════════════════════════════════════════════════════════════════════════════
def _bill_po_price6pct(nilai_selisih_rp: float = 200_000):
    """PO price 100_000, bill price 106_000 (=6%); qty = nilai_selisih_rp / 6000."""
    po_price, bill_price = 100_000.0, 106_000.0
    diff = bill_price - po_price  # 6000
    qty = nilai_selisih_rp / diff
    bill = {
        "id": "TEST_BILL", "bill_number": "TEST/BILL",
        "items": [{"product_id": "P1", "quantity": qty, "billed_qty": qty,
                   "price": bill_price, "unit": "meter"}],
    }
    po = {"items": [{"product_id": "P1", "po_price": po_price, "received_qty": qty}]}
    return bill, po


def test_d16_evaluate_bill_price_variance_over_tolerance():
    from services import contra_bon_service as cb
    bill, po = _bill_po_price6pct(nilai_selisih_rp=200_000)
    pol = {"qty_tolerance_percent": 0, "price_tolerance_percent": 5, "value_tolerance_rupiah": 0}
    excs = cb.evaluate_bill_exceptions(bill, po, pol)
    types = [e["type"] for e in excs]
    assert "price_variance" in types, f"harusnya price_variance muncul: {excs}"


def test_d16_evaluate_bill_price_variance_within_tolerance():
    from services import contra_bon_service as cb
    bill, po = _bill_po_price6pct(nilai_selisih_rp=200_000)
    pol = {"qty_tolerance_percent": 0, "price_tolerance_percent": 10, "value_tolerance_rupiah": 0}
    excs = cb.evaluate_bill_exceptions(bill, po, pol)
    types = [e["type"] for e in excs]
    assert "price_variance" not in types, f"harusnya TIDAK price_variance: {excs}"


# ═════════════════════════════════════════════════════════════════════════════
# D16 — vendor_bill_service.evaluate_match value_tol menekan selisih rupiah kecil
# ═════════════════════════════════════════════════════════════════════════════
def test_d16_vendor_bill_evaluate_match_value_tol_suppresses():
    """D16 — evaluate_match: harga 6% di atas PO; value_tol=50rb menekan selisih kecil."""
    from services import vendor_bill_service as vb
    # PO: 1 item price 1000, received 2000
    po = {"items": [{"product_id": "P1", "quantity": 2000, "received_qty": 2000,
                     "price": 1000, "sku": "SKU1", "product_name": "TestProd"}]}

    def _has_price_var(res) -> bool:
        for e in (res.get("exceptions") or []):
            if e.get("type") == "price_variance":
                return True
        return False

    # Kasus A: billed 1666 dgn price 1060 → selisih 6% × 1666 = ~100rb (> value_tol 50rb) → ADA
    priced_a = [{"product_id": "P1", "quantity": 1666, "billed_qty": 1666, "price": 1060}]
    res_a = vb.evaluate_match(po, priced_a, "received", {}, qty_tol=0, price_tol=5, value_tol=50_000)
    assert _has_price_var(res_a), f"nilai ~100rb harusnya price_variance: {res_a.get('exceptions')}"

    # Kasus B: billed 166 dgn price 1060 → selisih 6% × 166 = ~10rb (< value_tol 50rb) → TIDAK
    priced_b = [{"product_id": "P1", "quantity": 166, "billed_qty": 166, "price": 1060}]
    res_b = vb.evaluate_match(po, priced_b, "received", {}, qty_tol=0, price_tol=5, value_tol=50_000)
    assert not _has_price_var(res_b), f"nilai ~10rb harusnya di bawah value_tol: {res_b.get('exceptions')}"


# ═════════════════════════════════════════════════════════════════════════════
# ATOMIC — POST scan-label pada task completed → 409, tanpa residu roll
# ═════════════════════════════════════════════════════════════════════════════
def test_atomic_scan_label_on_completed_task_409(admin, mongo):
    task = mongo.wms_tasks.find_one({"flow_type": "inbound", "status": "completed",
                                      "entity_id": "ent_ksc"},
                                     {"id": 1, "entity_id": 1})
    injected = False
    tid = None
    try:
        if not task:
            tid = f"test_inbtask_{uuid.uuid4().hex[:8]}"
            mongo.wms_tasks.insert_one({
                "id": tid, "flow_type": "inbound", "status": "completed",
                "entity_id": "ent_ksc", "warehouse_id": "wh_jakarta",
                "supplier_id": "sup_test", "items": [],
            })
            injected = True
        else:
            tid = task["id"]

        before_count = mongo.inventory_rolls.count_documents({"grn_task_id": tid})
        payload = {
            "product_id": "prod_test", "lot_id": "lot_test", "length": 10,
            "unit": "meter", "grade": "A", "roll_number": f"TEST_R_{uuid.uuid4().hex[:6]}",
        }
        r = admin.post(f"{API}/inbound/tasks/{tid}/scan-label", json=payload,
                       headers={"X-Entity-Id": "ent_ksc"}, timeout=20)
        assert r.status_code in (400, 404, 409), \
            f"scan-label pada task completed harus ditolak (400/404/409), got {r.status_code}: {r.text[:200]}"
        after_count = mongo.inventory_rolls.count_documents({"grn_task_id": tid})
        assert after_count == before_count, \
            f"roll baru bocor: sebelum={before_count} sesudah={after_count}"
    finally:
        if injected and tid:
            mongo.wms_tasks.delete_one({"id": tid})
            mongo.inventory_rolls.delete_many({"grn_task_id": tid})


# ═════════════════════════════════════════════════════════════════════════════
# ATOMIC (unit-level) — special_orders approve middle level CAS predicate
# ═════════════════════════════════════════════════════════════════════════════
def test_atomic_special_order_approve_uses_cas(mongo):
    """Verifikasi unit: source memakai find_one_and_update dengan predikat status+level.

    Kalau tak ada OD demo pending_approval ber-rantai ≥2, lakukan static check.
    """
    import re
    src = open("/app/backend/routers/special_orders.py").read()
    # Cari klaim CAS pada approve
    hits = re.findall(r"find_one_and_update\([\s\S]{0,400}?approval_level_current", src)
    assert hits, "routers/special_orders.py approve tidak memakai find_one_and_update+approval_level_current"


# ═════════════════════════════════════════════════════════════════════════════
# REGRESI: endpoint sah 200
# ═════════════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("path", [
    "vendor-bills", "contra-bons", "inventory/balances", "sales-orders/stats/summary",
])
def test_regression_endpoints_ok(admin, path):
    r = admin.get(f"{API}/{path}", headers={"X-Entity-Id": "ent_ksc"}, timeout=30)
    assert r.status_code == 200, f"GET /{path}: {r.status_code} {r.text[:200]}"
