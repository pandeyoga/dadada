#!/usr/bin/env python3
"""Penyemai uji peramban W1-B (#9): deal berbayar-nyata + permintaan ganti skema yang DITAHAN. Mencetak JSON ke stdout.

    SIPRO_UI_BASE=http://localhost:3073 python3 scripts/ui/seed_w1b.py

Memakai pembantu `backend/tests/p0/test_p0_masuk.py` (butuh `requests` + `pytest`); API lewat proksi UI (`$SIPRO_UI_BASE/api`).
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "backend", "tests", "p0"))
os.environ["API_BASE"] = os.environ.get("SIPRO_API_BASE") or (os.environ.get("SIPRO_UI_BASE", "http://localhost:3073").rstrip("/") + "/api")

import test_p0_masuk as m  # noqa: E402


def main():
    w = m.World()
    d = w.new_deal()
    did = d["deal_id"]
    inv = m.ar(did)["data"]
    r1 = m.ok(m.pay(did, 100_000_000, allocations=[{"item_id": inv["items"][0]["id"], "amount": 100_000_000}]))["data"]["receipt"]
    r2 = m.ok(m.pay(did, 60_000_000, allocations=[{"item_id": inv["items"][1]["id"], "amount": 60_000_000}]))["data"]["receipt"]
    r = m.call(m.FINANCE, "POST", f"/finance/ar/{did}/schedule",
               json={"scheme_id": w.scheme["Cash keras (DP 80% + pelunasan)"], "reason": "uji peramban W1-B"})
    assert r.status_code == 202, (r.status_code, r.text[:300])
    print(json.dumps({"deal_id": did, "unit_code": d["unit_code"], "r1": r1["id"], "r2": r2["id"],
                      "r1_no": r1["receipt_no"], "r2_no": r2["receipt_no"], "request_id": r.json()["data"]["id"]}))


if __name__ == "__main__":
    main()
