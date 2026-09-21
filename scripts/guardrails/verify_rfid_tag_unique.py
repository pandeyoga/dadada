#!/usr/bin/env python3
"""INV-RFID-01 — satu `rfid_tag_id` untuk satu roll aktif (P-1 gelombang 2026-09).

KODE (K1): pintu tunggal potongan `insert_child_roll()` WAJIB me-reset `rfid_tag_id`
menjadi None — potongan adalah benda fisik baru, tagnya tidak boleh diwarisi.
DATA (D1): tidak ada `rfid_tag_id` yang dipakai >1 roll berstatus fisik (PHYSICAL_STATUSES
rfid_service). Data lama yang kembar TIDAK diperbaiki otomatis — pakai
`scripts/diagnose_rfid_duplicate_tags.py` lalu keputusan gudang.

Pakai:  python3 scripts/guardrails/verify_rfid_tag_unique.py [--self-test]
"""
from __future__ import annotations

import ast
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
from _common import Guard, BACKEND, G, R, X  # noqa: E402

PHYSICAL = ["available", "reserved", "allocated", "quarantine", "committed", "picked", "packed", "hold"]
RE_RESET = re.compile(r"""\[\s*["']rfid_tag_id["']\s*\]\s*=\s*None|["']rfid_tag_id["']\s*:\s*None""")


def child_door_source(src: str) -> str | None:
    tree = ast.parse(src)
    lines = src.splitlines()
    for n in tree.body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == "insert_child_roll":
            return "\n".join(lines[n.lineno - 1:n.end_lineno])
    return None


def check_code(src: str) -> list[str]:
    fn = child_door_source(src)
    if fn is None:
        return ["K1 `insert_child_roll()` tidak ditemukan di roll_service.py — pintu tunggal potongan hilang."]
    if not RE_RESET.search(fn):
        return ["K1 backend/services/roll_service.py insert_child_roll(): potongan MEWARISI `rfid_tag_id` induk "
                "(dua benda fisik, satu tag). Tambahkan `doc[\"rfid_tag_id\"] = None`."]
    return []


def duplicates(coll) -> list[dict]:
    return list(coll.aggregate([
        {"$match": {"rfid_tag_id": {"$nin": [None, ""]}, "status": {"$in": PHYSICAL}}},
        {"$group": {"_id": "$rfid_tag_id", "n": {"$sum": 1}, "rolls": {"$push": "$roll_no"}}},
        {"$match": {"n": {"$gt": 1}}}, {"$sort": {"n": -1}}]))


def check_data() -> tuple[list[str], bool]:
    try:
        if not os.environ.get("MONGO_URL"):
            from dotenv import load_dotenv
            load_dotenv(BACKEND / ".env")
        from pymongo import MongoClient
        cli = MongoClient(os.environ["MONGO_URL"], serverSelectionTimeoutMS=2500)
        db = cli[os.environ.get("DB_NAME", "test_database")]
        db.command("ping")
    except Exception:  # noqa: BLE001
        return [], False
    dups = duplicates(db.inventory_rolls)
    if not dups:
        return [], True
    return [f"D1 {len(dups)} tag dipakai >1 roll aktif: " +
            "; ".join(f"{d['_id']}×{d['n']} ({', '.join(str(r) for r in d['rolls'][:4])})" for d in dups[:5]) +
            " — jalankan scripts/diagnose_rfid_duplicate_tags.py; keputusan roll mana yang berhak = gudang."], True


def run() -> int:
    g = Guard("INV-RFID-01", "satu tag RFID untuk satu roll aktif; potongan tidak mewarisi tag induk")
    src = (BACKEND / "services" / "roll_service.py").read_text(errors="ignore")
    g.bump()
    for v in check_code(src):
        g.add(v)
    viol, reachable = check_data()
    if reachable:
        g.bump()
        for v in viol:
            g.add(v)
    else:
        print("  (Mongo tak terjangkau — lapisan DATA dilewati)")
    return g.finish()


def self_test() -> int:
    fails = 0

    def case(name, red_expected, viol):
        nonlocal fails
        ok = bool(viol) == red_expected
        fails += 0 if ok else 1
        print(f"  [{G if ok else R}{'PASS' if ok else 'FAIL'}{X}] {name} → {'MERAH' if viol else 'hijau'}")

    good = "async def insert_child_roll(child, parent):\n    doc = dict(child)\n    doc[\"rfid_tag_id\"] = None\n    return doc\n"
    good2 = "async def insert_child_roll(child, parent):\n    doc = {**child, \"rfid_tag_id\": None}\n    return doc\n"
    bad = "async def insert_child_roll(child, parent):\n    doc = dict(child)\n    doc[\"roll_no\"] = 'x'\n    return doc\n"
    none = "async def other():\n    pass\n"
    case("K1 reset lewat item assignment → hijau", False, check_code(good))
    case("K1 reset lewat literal dict → hijau", False, check_code(good2))
    case("K1 potongan mewarisi tag → MERAH", True, check_code(bad))
    case("K1 pintu tunggal hilang → MERAH", True, check_code(none))

    class _Coll:
        def __init__(self, docs): self.docs = docs
        def aggregate(self, _p):
            cnt = {}
            for d in self.docs:
                if d.get("rfid_tag_id") and d.get("status") in PHYSICAL:
                    cnt.setdefault(d["rfid_tag_id"], []).append(d.get("roll_no"))
            return [{"_id": k, "n": len(v), "rolls": v} for k, v in cnt.items() if len(v) > 1]
    case("D1 dua roll aktif satu tag → MERAH", True,
         duplicates(_Coll([{"rfid_tag_id": "t1", "status": "available", "roll_no": "A"}, {"rfid_tag_id": "t1", "status": "reserved", "roll_no": "B"}])))
    case("D1 tag sama tapi satu roll sudah sold → hijau", False,
         duplicates(_Coll([{"rfid_tag_id": "t1", "status": "available", "roll_no": "A"}, {"rfid_tag_id": "t1", "status": "sold", "roll_no": "B"}])))
    case("D1 tag berbeda → hijau", False,
         duplicates(_Coll([{"rfid_tag_id": "t1", "status": "available"}, {"rfid_tag_id": "t2", "status": "available"}])))
    print(f"{G if not fails else R}  SELF-TEST {'HIJAU' if not fails else 'MERAH'} ({fails} gagal).{X}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(self_test() if "--self-test" in sys.argv else run())
