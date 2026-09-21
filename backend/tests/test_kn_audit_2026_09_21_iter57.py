"""KN audit 2026-09-21 iter57 — konversi satuan (B12/B16/B22/B27), D17-D26, gate lama.

Menguji:
- KN-B27: create_inbound_roll quantity=100 unit='yard' pd produk base meter → ~91.44m
- KN-B16: rebuild_balance mengonversi roll ber-unit yard ke meter di on_hand_qty
- KN-B12: apply_cycle_count_adjustment memakan reserved/hold saat available habis
- KN-B22: _normalize_return_items_to_base 10 yard → 9.14 m; simpan input asli
- KN-D18: GET /api/sales-orders/stats/summary revenue.{7d,30d,90d}.{count,grand_total}
- KN-D25: GET /api/inventory/balances → header X-Total-Count & X-Truncated, sku/name terisi
- Gate lama: product-motifs scope ent_ksc; data-hygiene/log scope; customers POST X-Entity-Id all → 409
- Regresi impor: GET /api/ → 200; tidak ada `except: pass` di services/routers.
"""
from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import uuid
from typing import Any

import pytest
import requests
from pymongo import MongoClient

sys.path.insert(0, "/app/backend")

# Motor mengikat client ke event loop pertama yang menyentuhnya; pakai SATU loop
# di seluruh modul supaya tidak ada "attached to a different loop".
_LOOP = asyncio.new_event_loop()
asyncio.set_event_loop(_LOOP)


def _run(coro):
    return _LOOP.run_until_complete(coro)

API = [l.split("=", 1)[1].strip() for l in open("/app/frontend/.env")
       if l.startswith("REACT_APP_BACKEND_URL=")][0].rstrip("/") + "/api"
PW = os.environ.get("KN_TEST_PASSWORD", "demo12345")
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")
YARD_TO_METER = 0.9144


@pytest.fixture(scope="module")
def admin():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": "admin@kainnusantara.id", "password": PW}, timeout=20)
    if r.status_code != 200:
        pytest.skip(f"login gagal {r.status_code}")
    s.headers.update({"Authorization": "Bearer " + r.json()["token"], "X-Entity-Id": "ent_ksc"})
    return s


@pytest.fixture(scope="module")
def mongo():
    cli = MongoClient(MONGO_URL)
    yield cli[DB_NAME]
    cli.close()


# ── Regresi impor & no bare except ────────────────────────────────────────────
def test_no_bare_except_in_services_routers():
    r = subprocess.run(
        ["grep", "-rE", r"^\s*except\s*:", "/app/backend/services/", "/app/backend/routers/"],
        capture_output=True, text=True,
    )
    assert not r.stdout.strip(), f"masih ada `except: pass` di kode: {r.stdout[:500]}"


def test_root_api_200():
    r = requests.get(f"{API}/", timeout=10)
    assert r.status_code == 200, r.text[:200]


# ── KN-B27: create_inbound_roll unit yard → meter ─────────────────────────────
def test_kn_b27_create_inbound_roll_yard_to_meter(mongo):
    async def run():
        from services import roll_service
        prod = mongo.products.find_one({"base_unit": "meter"}, {"id": 1})
        wh = mongo.warehouses.find_one({}, {"id": 1})
        assert prod and wh
        roll = await roll_service.create_inbound_roll(
            product_id=prod["id"], warehouse_id=wh["id"],
            owner_entity_id="ent_ksc", quantity=100, unit="yard",
            acquired_via="manual_inbound", ref_id=f"TEST_ITER57_{uuid.uuid4().hex[:6]}",
            created_by="TEST_iter57",
        )
        return roll, prod["id"], wh["id"]

    roll, pid, wid = _run(run()) if False else _run(run())
    try:
        assert roll["unit"] == "meter", f"unit hasil harus meter, got {roll['unit']}"
        assert abs(roll["length_initial"] - 100 * YARD_TO_METER) < 0.05, \
            f"length_initial ≠ 91.44: {roll['length_initial']}"
        assert abs(roll["length_remaining"] - 100 * YARD_TO_METER) < 0.05
    finally:
        # cleanup roll + movement + rebuild
        mongo.inventory_rolls.delete_one({"id": roll["id"]})
        mongo.inventory_movements.delete_many({"roll_id": roll["id"]})
        from services import roll_service as rs
        _run(rs.rebuild_balance(pid, wid, "ent_ksc"))


# ── KN-B16: rebuild_balance konversi roll unit yard ───────────────────────────
def test_kn_b16_rebuild_balance_converts_yard_roll(mongo):
    from services import roll_service
    prod = mongo.products.find_one({"base_unit": "meter"}, {"id": 1})
    wh = mongo.warehouses.find_one({}, {"id": 1})
    assert prod and wh
    rid = f"TEST_ITER57_ROLL_{uuid.uuid4().hex[:8]}"
    mongo.inventory_rolls.insert_one({
        "id": rid, "product_id": prod["id"], "warehouse_id": wh["id"],
        "owner_entity_id": "ent_ksc", "status": "available",
        "length_initial": 100.0, "length_remaining": 100.0,
        "unit": "yard", "grade": "A",
        "ownership_type": "internal",
        "created_at": "2026-01-01T00:00:00+00:00",
    })
    try:
        # baseline
        base_bal = mongo.inventory_balances.find_one(
            {"product_id": prod["id"], "warehouse_id": wh["id"], "owner_entity_id": "ent_ksc"},
            {"available_qty": 1, "on_hand_qty": 1},
        ) or {}
        before_avail = float(base_bal.get("available_qty", 0) or 0)
        before_onhand = float(base_bal.get("on_hand_qty", 0) or 0)
        # rebuild
        doc = _run(
            roll_service.rebuild_balance(prod["id"], wh["id"], "ent_ksc")
        )
        # delta available (dan on_hand) harus ≈ 91.44 bukan 100
        after_avail = float(doc.get("available_qty", 0) or 0)
        after_onhand = float(doc.get("on_hand_qty", 0) or 0)
        delta_avail = after_avail - before_avail
        delta_onhand = after_onhand - before_onhand
        # bisa ada roll uji tunggal — kontribusinya 91.44
        assert abs(delta_avail - 100 * YARD_TO_METER) < 0.5, \
            f"delta available {delta_avail:.2f} ≠ 91.44 (100 mentah = bug)"
        assert abs(delta_onhand - 100 * YARD_TO_METER) < 0.5, \
            f"delta on_hand {delta_onhand:.2f} ≠ 91.44"
    finally:
        mongo.inventory_rolls.delete_one({"id": rid})
        _run(
            roll_service.rebuild_balance(prod["id"], wh["id"], "ent_ksc"))


# ── KN-B12: cycle-count adjust menembus reserved ──────────────────────────────
def test_kn_b12_cycle_count_reduces_reserved_when_available_empty(mongo):
    from services import roll_service
    prod = mongo.products.find_one({"base_unit": "meter"}, {"id": 1})
    assert prod
    # buat warehouse & entitas uji terisolasi
    wid = f"wh_test_iter57_{uuid.uuid4().hex[:6]}"
    ent = "ent_ksc"
    rid = f"TEST_ITER57_RSV_{uuid.uuid4().hex[:8]}"
    mongo.warehouses.insert_one({"id": wid, "name": "TEST_ITER57_WH", "entity_id": ent})
    mongo.inventory_rolls.insert_one({
        "id": rid, "product_id": prod["id"], "warehouse_id": wid,
        "owner_entity_id": ent, "status": "reserved",
        "length_initial": 50.0, "length_remaining": 50.0, "unit": "meter",
        "grade": "A", "reserved_ref": "TEST_ITER57_SO",
        "ownership_type": "internal",
        "created_at": "2026-01-01T00:00:00+00:00",
    })
    try:
        result = _run(
            roll_service.apply_cycle_count_adjustment(
                prod["id"], wid, ent, diff=-30.0,
                session_id=f"TEST_ITER57_CC_{uuid.uuid4().hex[:6]}",
                created_by="TEST_iter57",
            )
        )
        # harus mengembalikan negatif (removed) tidak melempar
        assert result == -30.0 or abs(result - -30.0) < 0.01, f"result={result}"
        # roll reserved berkurang menjadi 20
        r = mongo.inventory_rolls.find_one({"id": rid}, {"length_remaining": 1, "status": 1})
        assert abs(r["length_remaining"] - 20.0) < 0.01, f"length_remaining={r['length_remaining']}"
    finally:
        mongo.inventory_rolls.delete_one({"id": rid})
        mongo.inventory_movements.delete_many({"warehouse_id": wid})
        mongo.warehouses.delete_one({"id": wid})
        mongo.inventory_balances.delete_many({"warehouse_id": wid})


# ── KN-B22: _normalize_return_items_to_base ────────────────────────────────────
def test_kn_b22_normalize_return_items(mongo):
    from services import return_service
    prod = mongo.products.find_one({"base_unit": "meter"}, {"id": 1})
    assert prod
    items = [{"product_id": prod["id"], "quantity_returned": 10, "unit": "yard",
              "reason": "TEST_ITER57"}]
    out = _run(
        return_service._normalize_return_items_to_base(items))
    assert len(out) == 1
    it = out[0]
    assert it["unit"] == "meter", f"unit={it['unit']}"
    assert abs(it["quantity_returned"] - 10 * YARD_TO_METER) < 0.05, \
        f"quantity_returned={it['quantity_returned']}"
    assert it.get("quantity_returned_input") == 10
    assert it.get("unit_input") == "yard"


# ── KN-D18: revenue.7d/30d/90d ────────────────────────────────────────────────
def test_kn_d18_sales_orders_stats_summary_revenue(admin, mongo):
    r = admin.get(f"{API}/sales-orders/stats/summary",
                  headers={"X-Entity-Id": "ent_ksc"}, timeout=30)
    assert r.status_code == 200, r.text[:200]
    body = r.json()
    assert "revenue" in body and "revenue_basis" in body, body
    rev = body["revenue"]
    for key in ("7d", "30d", "90d"):
        assert key in rev, f"missing {key} in revenue"
        assert "count" in rev[key] and "grand_total" in rev[key], rev[key]
        assert isinstance(rev[key]["count"], int)
        assert isinstance(rev[key]["grand_total"], (int, float))
    # cross-check with mongo aggregation quick sanity
    from datetime import datetime, timezone, timedelta
    cutoff = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()
    fulfilled = ["confirmed", "partially_picked", "picked", "partially_shipped",
                 "shipped", "dispatched", "done"]
    docs = list(mongo.sales_orders.find(
        {"entity_id": "ent_ksc", "status": {"$in": fulfilled},
         "created_at": {"$gte": cutoff}, "order_type": {"$ne": "sample"}},
        {"grand_total": 1, "total_amount": 1}))
    expected = sum(float(d.get("grand_total") or d.get("total_amount") or 0) for d in docs)
    assert abs(rev["90d"]["grand_total"] - round(expected, 2)) < 1.0, \
        f"grand_total 90d {rev['90d']['grand_total']} vs mongo {expected}"


# ── KN-D25: inventory/balances headers + sku/name terisi ──────────────────────
def test_kn_d25_inventory_balances_headers_and_names(admin):
    r = admin.get(f"{API}/inventory/balances",
                  headers={"X-Entity-Id": "ent_ksc"}, timeout=30)
    assert r.status_code == 200, r.text[:200]
    assert "X-Total-Count" in r.headers, list(r.headers.keys())
    assert "X-Truncated" in r.headers
    assert r.headers["X-Truncated"] in ("0", "1")
    rows = r.json()
    assert isinstance(rows, list)
    # sku & product_name terisi untuk baris berproduk
    missing = [row for row in rows if row.get("product_id") and (not row.get("sku") or not row.get("product_name"))]
    assert not missing, f"{len(missing)} baris tanpa sku/product_name; sample: {missing[:2]}"


# ── Gate lama: product-motifs scope ent_ksc ───────────────────────────────────
def test_product_motifs_scoped_to_entity(admin, mongo):
    r = admin.get(f"{API}/product-motifs", headers={"X-Entity-Id": "ent_ksc"}, timeout=30)
    assert r.status_code == 200, r.text[:200]
    body = r.json()
    items = body.get("items") if isinstance(body, dict) else body
    for m in items or []:
        ent = m.get("entity_id")
        # design_gallery motifs harus milik ent_ksc atau global (kosong/None)
        assert ent in (None, "", "ent_ksc"), f"motif bocor dari entitas {ent}: {m.get('id')}"


# ── Gate lama: data-hygiene log scoped ────────────────────────────────────────
def test_data_hygiene_log_scoped(admin):
    r = admin.get(f"{API}/data-hygiene/log", headers={"X-Entity-Id": "ent_ksc"}, timeout=30)
    assert r.status_code == 200, r.text[:200]
    body = r.json()
    rows = body.get("items") if isinstance(body, dict) else body
    for row in rows or []:
        ent = row.get("entity_id")
        assert ent in (None, "", "ent_ksc"), f"data-hygiene bocor: {row.get('id')} ent={ent}"


# ── Gate lama: POST /api/customers X-Entity-Id: all → 409 ─────────────────────
def test_customers_post_reject_entity_all(admin):
    r = admin.post(f"{API}/customers",
                   json={"name": "TEST_ITER57_CUST", "phone": "081200000000"},
                   headers={"X-Entity-Id": "all"}, timeout=20)
    assert r.status_code in (400, 409), f"POST customers ent=all lolos: {r.status_code} {r.text[:200]}"
