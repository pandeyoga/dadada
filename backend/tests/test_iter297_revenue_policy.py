"""Sesi #089 — KEB-PDPT: kebijakan pengakuan pendapatan.

* Pembayaran SEBELUM kirim TIDAK memicu pendapatan; kasnya Cr 2-1400 Uang Muka Pelanggan.
* Saat dikirim: pendapatan + HPP lahir, uang muka direklas Dr 2-1400 / Cr 1-1200.
* Void kwitansi uang muka SETELAH reklas → pembalik reklas (Dr 1-1200 / Cr 2-1400).
* Kwitansi SETELAH kirim tetap Cr 1-1200 (perilaku lama).
Uji tingkat layanan (langsung ke services), dokumen ber-tag `_test_kebpdpt` dan dihapus.
Usage: cd /app && python -m pytest backend/tests/test_iter297_revenue_policy.py -q -n0
"""
import asyncio
import sys
import uuid

import pytest

sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv  # noqa: E402

load_dotenv("/app/backend/.env")

from db import db  # noqa: E402
from services import gl_service as gl  # noqa: E402

TAG = "_test_kebpdpt"
ENT = "ent_ksc"


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def _order(oid, status, paid, payments):
    return {"id": oid, "number": f"TEST/SO-{oid[-6:]}", "entity_id": ENT, "status": status,
            "customer_id": "cust_test", "customer_name": "Uji KEB-PDPT",
            "items": [{"product_id": "prd_test", "quantity": 10, "unit_price": 100000,
                       "unit_cost": 60000, "base_quantity": 10}],
            "total_amount": 1000000, "grand_total": 1110000, "ppn_amount": 110000,
            "payment_method": "transfer", "paid_total": paid, "payments": payments,
            "created_at": "2026-09-01T00:00:00+00:00", TAG: True}


def _receipt(rid, oid, amount):
    return {"id": rid, "number": f"TEST/AR-{rid[-6:]}", "entity_id": ENT, "customer_id": "cust_test",
            "customer_name": "Uji KEB-PDPT", "amount": amount, "method": "transfer",
            "applied_total": amount, "unapplied_amount": 0.0, "used_deposit": 0.0,
            "allocations": [{"order_id": oid, "applied": amount}], "status": "posted",
            "receipt_date": "2026-09-02T00:00:00+00:00", TAG: True}


def _cash(cid, rid, amount):
    return {"id": cid, "number": f"TEST/CASH-{cid[-6:]}", "cash_type": "kas_besar", "direction": "in",
            "amount": amount, "category": "penagihan", "description": "uji", "entity_id": ENT,
            "ref_type": "ar_receipt", "ref_id": rid, "txn_date": "2026-09-02T00:00:00+00:00",
            "status": "posted", TAG: True}


def _lines(je):
    return {(l["account_code"], round(l["debit"], 2), round(l["credit"], 2)) for l in je["lines"]}


@pytest.fixture(autouse=True)
def _cleanup():
    yield
    run(_purge())


async def _purge():
    for coll in (db.sales_orders, db.ar_receipts, db.cash_transactions, db.shipments):
        await coll.delete_many({TAG: True})
    await db.journal_entries.delete_many({"source_label": {"$regex": r"^TEST/"}})
    await db.journal_entries.delete_many({"source_id": {"$regex": r"^(so|rcp|cash|shp)_kebpdpt_"}})
    await db.journal_entries.delete_many({"ref.order_id": {"$regex": r"^so_kebpdpt_"}})


def _ids():
    u = uuid.uuid4().hex[:8]
    return f"so_kebpdpt_{u}", f"rcp_kebpdpt_{u}", f"cash_kebpdpt_{u}"


class TestAdvancePolicy:
    def test_payment_before_shipment_is_liability_not_revenue(self):
        oid, rid, cid = _ids()
        run(db.sales_orders.insert_one(_order(oid, "confirmed", 500000,
            [{"id": "pay1", "amount": 500000, "receipt_id": rid}])))
        run(db.ar_receipts.insert_one(_receipt(rid, oid, 500000)))
        run(db.cash_transactions.insert_one(_cash(cid, rid, 500000)))

        # pembayaran TIDAK melahirkan pendapatan
        assert run(gl.post_order_revenue_and_cogs(oid))["revenue"] is None
        assert not run(gl.order_revenue_posted(oid))

        je = run(gl.post_cash_transaction(run(db.cash_transactions.find_one({"id": cid}, {"_id": 0}))))
        assert je is not None
        ls = _lines(je)
        assert (gl.ACC_KAS_BESAR, 500000.0, 0.0) in ls
        assert (gl.ACC_UANG_MUKA_PELANGGAN, 0.0, 500000.0) in ls, ls
        assert not any(a == gl.ACC_PIUTANG for a, _, _ in ls), "uang muka tidak boleh Cr Piutang"

        o = run(db.sales_orders.find_one({"id": oid}, {"_id": 0}))
        assert o["payments"][0].get("gl_bucket") == "advance"
        assert gl.order_advance_total(o) == 500000.0
        assert run(gl.order_advance_unrecognized(o)) == 500000.0

        # dikirim → pendapatan + reklas
        run(db.sales_orders.update_one({"id": oid}, {"$set": {"status": "shipped"}}))
        res = run(gl.post_order_revenue_and_cogs(oid))
        assert res["revenue"] is not None
        rev = _lines(res["revenue"])
        assert (gl.ACC_PIUTANG, 1110000.0, 0.0) in rev
        assert (gl.ACC_PENDAPATAN, 0.0, 1000000.0) in rev
        assert res["advance_reclass"] is not None
        rc = _lines(res["advance_reclass"])
        assert rc == {(gl.ACC_UANG_MUKA_PELANGGAN, 500000.0, 0.0), (gl.ACC_PIUTANG, 0.0, 500000.0)}
        o = run(db.sales_orders.find_one({"id": oid}, {"_id": 0}))
        assert run(gl.order_advance_unrecognized(o)) == 0.0

        # idempotent
        again = run(gl.post_order_revenue_and_cogs(oid))
        assert again["revenue"] is None and again["advance_reclass"] is None

        # void setelah reklas → pembalik reklas
        rev_je = run(gl.post_advance_reclass_reversal(o, rid, 500000, label="void uji"))
        assert rev_je is not None
        assert _lines(rev_je) == {(gl.ACC_PIUTANG, 500000.0, 0.0), (gl.ACC_UANG_MUKA_PELANGGAN, 0.0, 500000.0)}
        assert run(gl.post_advance_reclass_reversal(o, rid, 500000)) is None  # idempotent

    def test_payment_after_shipment_still_credits_receivable(self):
        oid, rid, cid = _ids()
        run(db.sales_orders.insert_one(_order(oid, "shipped", 0, [])))
        res = run(gl.post_order_revenue_and_cogs(oid))
        assert res["revenue"] is not None and res["advance_reclass"] is None

        run(db.sales_orders.update_one({"id": oid}, {"$set": {"paid_total": 1110000,
            "payments": [{"id": "pay1", "amount": 1110000, "receipt_id": rid}]}}))
        run(db.ar_receipts.insert_one(_receipt(rid, oid, 1110000)))
        run(db.cash_transactions.insert_one(_cash(cid, rid, 1110000)))
        je = run(gl.post_cash_transaction(run(db.cash_transactions.find_one({"id": cid}, {"_id": 0}))))
        ls = _lines(je)
        assert (gl.ACC_PIUTANG, 0.0, 1110000.0) in ls
        assert not any(a == gl.ACC_UANG_MUKA_PELANGGAN for a, _, _ in ls)
        o = run(db.sales_orders.find_one({"id": oid}, {"_id": 0}))
        assert o["payments"][0].get("gl_bucket") is None

    def test_reclass_without_revenue_is_noop(self):
        oid, rid, _ = _ids()
        run(db.sales_orders.insert_one(_order(oid, "confirmed", 200000,
            [{"id": "pay1", "amount": 200000, "receipt_id": rid, "gl_bucket": "advance"}])))
        o = run(db.sales_orders.find_one({"id": oid}, {"_id": 0}))
        assert run(gl.post_advance_reclass(o)) is None
        assert run(gl.post_advance_reclass_reversal(o, rid, 200000)) is None


def _shipment(shid, oid, qty, created_at):
    return {"id": shid, "shipment_no": f"TEST/SJ-{shid[-6:]}", "entity_id": ENT, "order_id": oid,
            "product_id": "prd_test", "qty": qty, "unit": "yard", "status": "dispatched",
            "created_at": created_at, TAG: True}


class TestProRataPerShipment:
    """Tahap 2 — pendapatan per surat jalan sebanding barang yang keluar."""

    def test_two_shipments_prorata_then_closing_remainder(self):
        oid, rid, cid = _ids()
        u = oid.split("_")[-1]
        run(db.sales_orders.insert_one(_order(oid, "confirmed", 500000,
            [{"id": "pay1", "amount": 500000, "receipt_id": rid}])))
        run(db.ar_receipts.insert_one(_receipt(rid, oid, 500000)))
        run(db.cash_transactions.insert_one(_cash(cid, rid, 500000)))
        run(gl.post_cash_transaction(run(db.cash_transactions.find_one({"id": cid}, {"_id": 0}))))

        # SJ-1: 4 dari 10 yard (40%) → pesanan partially_shipped
        sh1 = f"shp_kebpdpt_{u}a"
        run(db.shipments.insert_one(_shipment(sh1, oid, 4, "2026-09-03T01:00:00+00:00")))
        run(db.sales_orders.update_one({"id": oid}, {"$set": {"status": "partially_shipped"}}))
        res = run(gl.post_order_revenue_and_cogs(oid))
        assert res["revenue"] is not None and res["revenue"]["source_type"] == "shipment_revenue"
        ls = _lines(res["revenue"])
        assert (gl.ACC_PIUTANG, 444000.0, 0.0) in ls, ls          # 40% × 1.110.000
        assert (gl.ACC_PENDAPATAN, 0.0, 400000.0) in ls            # 40% × 1.000.000
        assert (gl.ACC_PPN_OUT, 0.0, 44000.0) in ls                # 40% × 110.000
        assert res["cogs"] is not None and _lines(res["cogs"]) == {
            (gl.ACC_HPP, 240000.0, 0.0), (gl.ACC_PERSEDIAAN, 0.0, 240000.0)}  # 4 × 60.000
        # reklas uang muka pro-rata: min(500.000, AR 444.000)
        assert _lines(res["advance_reclass"]) == {
            (gl.ACC_UANG_MUKA_PELANGGAN, 444000.0, 0.0), (gl.ACC_PIUTANG, 0.0, 444000.0)}
        o = run(db.sales_orders.find_one({"id": oid}, {"_id": 0}))
        assert run(gl.order_advance_unrecognized(o)) == 56000.0
        # tidak ada jurnal per-pesanan (legacy) yang ikut lahir
        assert not run(gl._already_posted("sales_order", oid))
        # idempotent
        again = run(gl.post_order_revenue_and_cogs(oid))
        assert again["revenue"] is None and again["advance_reclass"] is None

        # SJ-2 penutup: 6 yard → shipped → sisa (bukan 60% mentah) supaya total = grand
        sh2 = f"shp_kebpdpt_{u}b"
        run(db.shipments.insert_one(_shipment(sh2, oid, 6, "2026-09-03T02:00:00+00:00")))
        run(db.sales_orders.update_one({"id": oid}, {"$set": {"status": "shipped"}}))
        res2 = run(gl.post_order_revenue_and_cogs(oid))
        rev2 = next(x["revenue"] for x in res2["shipments"] if x["shipment_id"] == sh2)
        ls2 = _lines(rev2)
        assert (gl.ACC_PIUTANG, 666000.0, 0.0) in ls2
        assert (gl.ACC_PENDAPATAN, 0.0, 600000.0) in ls2
        assert (gl.ACC_PPN_OUT, 0.0, 66000.0) in ls2
        tot = run(gl.order_revenue_recognized(oid))
        assert tot == {"revenue": 1000000.0, "ppn": 110000.0, "ar": 1110000.0}
        assert _lines(res2["advance_reclass"]) == {
            (gl.ACC_UANG_MUKA_PELANGGAN, 56000.0, 0.0), (gl.ACC_PIUTANG, 0.0, 56000.0)}
        o = run(db.sales_orders.find_one({"id": oid}, {"_id": 0}))
        assert run(gl.order_advance_unrecognized(o)) == 0.0
        assert run(gl.order_advance_reclassed(oid)) == 500000.0

        # void kwitansi uang muka setelah reklas penuh → pembalik 500.000
        rv = run(gl.post_advance_reclass_reversal(o, rid, 500000, label="void uji"))
        assert _lines(rv) == {(gl.ACC_PIUTANG, 500000.0, 0.0), (gl.ACC_UANG_MUKA_PELANGGAN, 0.0, 500000.0)}
        assert run(gl.order_advance_reclassed(oid)) == 0.0

    def test_cancel_reverses_shipment_journals(self):
        oid, _, _ = _ids()
        u = oid.split("_")[-1]
        run(db.sales_orders.insert_one(_order(oid, "shipped", 0, [])))
        run(db.shipments.insert_one(_shipment(f"shp_kebpdpt_{u}c", oid, 10, "2026-09-03T01:00:00+00:00")))
        res = run(gl.post_order_revenue_and_cogs(oid))
        assert res["revenue"]["source_type"] == "shipment_revenue"
        revs = run(gl.reverse_order_journals(oid, reason="uji batal"))
        types = sorted(r["source_type"] for r in revs)
        assert types == ["shipment_cogs_reversal", "shipment_revenue_reversal"]
        rl = _lines(next(r for r in revs if r["source_type"] == "shipment_revenue_reversal"))
        assert (gl.ACC_PIUTANG, 0.0, 1110000.0) in rl and (gl.ACC_PENDAPATAN, 1000000.0, 0.0) in rl
        assert run(gl.reverse_order_journals(oid)) == []   # idempotent
