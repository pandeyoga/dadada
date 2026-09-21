#!/usr/bin/env python3
"""DIAGNOSA SAJA (P-1 · INV-RFID-01): daftar `rfid_tag_id` yang dipakai >1 roll aktif.

TIDAK mengubah data — roll mana yang berhak atas tag adalah keputusan gudang.
Pakai: python3 scripts/diagnose_rfid_duplicate_tags.py [--json]
"""
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from pymongo import MongoClient

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / "backend" / ".env")
sys.path.insert(0, str(ROOT / "scripts" / "guardrails"))
from verify_rfid_tag_unique import PHYSICAL, duplicates  # noqa: E402


def main() -> int:
    db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    dups = duplicates(db.inventory_rolls)
    rows = []
    for d in dups:
        rolls = list(db.inventory_rolls.find(
            {"rfid_tag_id": d["_id"], "status": {"$in": PHYSICAL}},
            {"_id": 0, "id": 1, "roll_no": 1, "status": 1, "warehouse_id": 1, "owner_entity_id": 1,
             "length_remaining": 1, "parent_roll_id": 1, "created_at": 1}).sort("created_at", 1))
        tag = db.rfid_tags.find_one({"id": d["_id"]}, {"_id": 0, "epc": 1, "roll_id": 1})
        rows.append({"tag_id": d["_id"], "epc": (tag or {}).get("epc"),
                     "tag_menunjuk_roll": (tag or {}).get("roll_id"), "jumlah_roll": d["n"], "rolls": rolls})
    if "--json" in sys.argv:
        print(json.dumps({"tag_kembar": len(rows), "detail": rows}, ensure_ascii=False, indent=1, default=str))
        return 0
    print(f"Tag RFID kembar pada roll aktif: {len(rows)}")
    for r in rows:
        print(f"\n• {r['tag_id']} (EPC {r['epc']}) — {r['jumlah_roll']} roll; rfid_tags menunjuk {r['tag_menunjuk_roll']}")
        for x in r["rolls"]:
            mark = "← pemegang sah menurut rfid_tags" if x["id"] == r["tag_menunjuk_roll"] else ""
            print(f"    {x.get('roll_no'):<14} {x.get('status'):<10} {x.get('warehouse_id'):<12} sisa {x.get('length_remaining')} "
                  f"induk={x.get('parent_roll_id') or '-'} {mark}")
    print("\nTidak ada yang diubah. Tag untuk roll yang BUKAN pemegang sah harus dilepas/ditulis ulang oleh gudang "
          "(Gudang → RFID → roll belum bertag).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
