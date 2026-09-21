"""Backfill PB-01 — isi `payment_term`/`payment_due_date` PO lama (belum lunas) dari termin
supplier, supaya antrean "Hutang supplier jatuh tempo" di Meja Finance terisi. Idempotent:
hanya PO tanpa `payment_due_date`. Jalankan: python scripts/backfill_po_payment_due.py"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from dotenv import load_dotenv  # noqa: E402

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "backend", ".env"))

from db import db  # noqa: E402
from services.supplier_service import payment_due_date, resolve_payment_term  # noqa: E402


async def main() -> None:
    n = 0
    async for po in db.purchase_orders.find(
            {"$or": [{"payment_due_date": {"$exists": False}}, {"payment_due_date": ""}],
             "status": {"$nin": ["cancelled", "closed", "draft", "rejected"]},
             "po_type": {"$ne": "blanket"}, "payment_status": {"$ne": "paid"}},
            {"_id": 0, "id": 1, "supplier_id": 1, "entity_id": 1, "expected_delivery_date": 1, "created_at": 1}):
        sup = await db.suppliers.find_one({"id": po.get("supplier_id", "")}, {"_id": 0, "payment_term_code": 1}) or {}
        term = await resolve_payment_term(sup.get("payment_term_code") or "NET30", po.get("entity_id") or "")
        if not term:
            continue
        anchor = po.get("expected_delivery_date") or (po.get("created_at") or "")[:10]
        await db.purchase_orders.update_one({"id": po["id"]}, {"$set": {
            "payment_term_code": term["code"], "payment_term": term,
            "payment_due_date": payment_due_date(term, anchor)}})
        n += 1
    print(f"backfill payment_due_date: {n} PO")


if __name__ == "__main__":
    asyncio.run(main())
