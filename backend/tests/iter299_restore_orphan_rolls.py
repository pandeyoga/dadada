"""Pembersihan data uji iterasi 299 — pulangkan ROLL yang menggantung.

Roll yang `reserved_ref.type == "sales_order"` tetapi pesanannya SUDAH TIDAK ADA
(dokumen uji sudah dihapus fixture) tetap berstatus reserved/committed/in_transit_sales
sehingga stok demo terkuras dan pesanan 20 yard mulai ditolak 409 MIXED_LOT.
Skrip ini mengembalikannya ke `available` lalu me-rebuild saldo dari roll (SSOT).

Jalankan: cd /app/backend && python tests/iter299_restore_orphan_rolls.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db import db  # noqa: E402
from services.roll_service import rebuild_balance  # noqa: E402

STUCK = ["reserved", "committed", "in_transit_sales", "picked", "staged"]


async def main() -> None:
    order_ids = {d["id"] async for d in db.sales_orders.find({}, {"_id": 0, "id": 1})}
    touched = set()
    n = 0
    async for r in db.inventory_rolls.find(
            {"status": {"$in": STUCK}, "reserved_ref.type": "sales_order"}, {"_id": 0}):
        ref = (r.get("reserved_ref") or {}).get("id")
        if ref in order_ids:
            continue
        await db.inventory_rolls.update_one(
            {"id": r["id"]},
            {"$set": {"status": "available", "reserved_ref": None},
             "$unset": {"shipped_at": "", "earmarked_for": ""}})
        touched.add((r.get("product_id"), r.get("warehouse_id"), r.get("owner_entity_id")))
        n += 1
        print("restored", r.get("roll_no"), r.get("length_remaining"), r.get("lot"), "←", ref)
    for prod, wh, owner in touched:
        await rebuild_balance(prod, wh, owner)
        print("rebuild_balance", prod, wh, owner)
    print(f"total roll dipulihkan: {n}")


if __name__ == "__main__":
    asyncio.run(main())
