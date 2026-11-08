#!/usr/bin/env python3
"""Menyemai data uji peramban W2-C (permohonan isian bebas biaya kontrak, keputusan #6) — lewat API, bukan DB langsung.

Hasil JSON: `SIPRO_UI_SEED_W2C` (bawaan `<tmp>/sipro-ui-seed-w2c.json`), dibaca `scripts/ui/w2c_biaya_kontrak.js`.
Satu penyemaian hanya cukup untuk SATU kali jalan (skenarionya mengajukan/menyetujui/menolak).

    API_BASE=http://localhost:8083/api python3 scripts/ui/seed_w2c.py
"""
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "backend", "tests", "p0"))

from test_p0_masuk import OWNER, World, call, ok  # noqa: E402
from test_p0_masuk_2 import convert  # noqa: E402

OUT = os.environ.get("SIPRO_UI_SEED_W2C") or os.path.join(tempfile.gettempdir(), "sipro-ui-seed-w2c.json")


def main():
    world = World()
    out = {"project_id": world.project_id}
    for nama in ("ajukan", "tolak"):     # kontrak yang diisi lewat dialog UI (ajukan) / permohonannya ditolak (tolak)
        d = world.new_deal(booking_fee=0)
        cid = convert(d)
        k = ok(call(OWNER, "GET", f"/contracts/{cid}"))["data"]
        out[nama] = {"contract_id": cid, "number": k["number"], "deal_id": d["deal_id"], "customer_id": k["customer_id"]}
    with open(OUT, "w") as f:
        json.dump(out, f, indent=1)
    print(OUT)


if __name__ == "__main__":
    main()
