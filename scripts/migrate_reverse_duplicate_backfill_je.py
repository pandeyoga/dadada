#!/usr/bin/env python3
"""F-03/F-04 (audit 2026-09-02) — balik JE DUPLIKAT hasil backfill.

Kelas cacat: `backfill_journals()` memposting ulang dokumen yang sudah berjurnal lewat
jalur lain (source_type berbeda):
  * vendor_bills ber-`bill_type=makloon_service` → sudah `subcon_service`, lalu dobel `vendor_bill`
  * cash_transactions ber-`gl_posted:true`       → sudah oleh dokumen induk, lalu dobel `cash_transaction`

Usage:
    python scripts/migrate_reverse_duplicate_backfill_je.py --report   # hanya laporkan
    python scripts/migrate_reverse_duplicate_backfill_je.py --apply    # reversal (append-only)
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from dotenv import load_dotenv  # noqa: E402

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "backend", ".env"))

from db import db  # noqa: E402
from services import gl_service  # noqa: E402


async def find_duplicates():
    out = []
    makloon_ids = [b["id"] for b in await db.vendor_bills.find(
        {"bill_type": "makloon_service"}, {"_id": 0, "id": 1}).to_list(50000)]
    async for je in db.journal_entries.find(
            {"source_type": "vendor_bill", "status": {"$ne": "void"}, "reversed": {"$ne": True},
             "source_id": {"$in": makloon_ids}}, {"_id": 0}):
        if await gl_service._already_posted("subcon_service", je["source_id"]):
            out.append(("vendor_bill", je))
    cash_ids = [c["id"] for c in await db.cash_transactions.find(
        {"gl_posted": True}, {"_id": 0, "id": 1}).to_list(50000)]
    async for je in db.journal_entries.find(
            {"source_type": "cash_transaction", "status": {"$ne": "void"}, "reversed": {"$ne": True},
             "source_id": {"$in": cash_ids}}, {"_id": 0}):
        out.append(("cash_transaction", je))
    return out


async def main(apply: bool):
    dups = await find_duplicates()
    print(f"JE duplikat backfill ditemukan: {len(dups)}")
    for kind, je in dups:
        print(f"  [{kind}] {je.get('number')} · {je.get('entity_id')} · source_id={je.get('source_id')} "
              f"· Cr {je.get('total_credit')}")
    if not apply:
        print("\n(mode --report; jalankan --apply untuk membalik)")
        return
    n = 0
    for kind, je in dups:
        revs = await gl_service.reverse_document(
            kind, je["source_id"], reason="duplikat backfill (audit 2026-09-02 F-03/F-04)",
            actor_name="migrasi", rev_suffix="_dup_reversal")
        n += len(revs)
    print(f"\nReversal dibuat: {n}")


if __name__ == "__main__":
    asyncio.run(main(apply="--apply" in sys.argv))
