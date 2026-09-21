"""Sisipkan Surat Jalan uji (belum diangkut) untuk uji FB-02 Logistik.

Pakai: python tests/fb02_seed_shipments.py [jumlah]
Semua dokumen ber-`created_by` "TEST_FB02" agar mudah dibersihkan.
"""
import asyncio
import sys
import uuid
from datetime import datetime, timezone

from dotenv import dotenv_values
from motor.motor_asyncio import AsyncIOMotorClient

env = dotenv_values("/app/backend/.env")
client = AsyncIOMotorClient(env["MONGO_URL"])
db = client[env["DB_NAME"]]


async def main(n: int):
    base = await db.shipments.find_one({"entity_id": "ent_ksc"}, {"_id": 0, "rolls": 0})
    now = datetime.now(timezone.utc).isoformat()
    made = []
    for i in range(n):
        doc = dict(base)
        doc["id"] = f"shp_test{uuid.uuid4().hex[:8]}"
        doc["shipment_no"] = f"SJ-TEST{i + 1:02d}"
        doc["logistics_id"] = None
        doc["logistics_number"] = ""
        doc["logistics_status"] = ""
        doc["created_by"] = "TEST_FB02"
        doc["created_at"] = now
        await db.shipments.insert_one(doc)
        made.append((doc["id"], doc["shipment_no"]))
    print(made)


if __name__ == "__main__":
    asyncio.run(main(int(sys.argv[1]) if len(sys.argv) > 1 else 2))
