"""Bersihkan posisi probe TEST_ dari LG-00007 (tidak ada endpoint hapus posisi)."""
import asyncio
import sys

sys.path.insert(0, "/app/backend")
from db import db  # noqa: E402


async def main():
    doc = await db.logistics_deliveries.find_one({"number": "KSC/LG-00007"}, {"_id": 0, "positions": 1, "id": 1})
    keep = [p for p in (doc.get("positions") or []) if not str(p.get("location", "")).startswith("TEST_")]
    removed = len(doc.get("positions") or []) - len(keep)
    await db.logistics_deliveries.update_one({"id": doc["id"]}, {"$set": {"positions": keep}})
    print("removed", removed, "kept", len(keep))
    for p in keep:
        print(" ", p.get("location"), p.get("lat"), p.get("lng"))


asyncio.run(main())
