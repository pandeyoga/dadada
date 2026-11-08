#!/usr/bin/env python3
"""Menyemai data uji peramban W1-C (permohonan refund titipan biaya pada deal batal) — lewat API, bukan DB langsung.

Hasil JSON: `SIPRO_UI_SEED_W1C` (bawaan `<tmp>/sipro-ui-seed-w1c.json`), dibaca `scripts/ui/w1c_titipan.js`.
Satu penyemaian hanya cukup untuk SATU kali jalan (skenarionya menyetujui/menolak/membayar).

    API_BASE=http://localhost:8076/api python3 scripts/ui/seed_w1c.py
"""
import json
import os
import sys
import tempfile
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "backend", "tests", "p0"))

from test_p0_masuk import FINANCE, OWNER, World, call, ok, upload_proof  # noqa: E402
from test_p0_masuk_2 import allin_deal  # noqa: E402

OUT = os.environ.get("SIPRO_UI_SEED_W1C") or os.path.join(tempfile.gettempdir(), "sipro-ui-seed-w1c.json")


def cost_deal(world, bayar=20_000_000, salur=3_000_000):
    """Deal all-in dengan titipan biaya (`bayar`, dikurangi `salur` yang sudah disalurkan ke notaris) + invoice biaya terbuka."""
    d = allin_deal(world)
    ok(call(FINANCE, "POST", f"/cost-invoices/{d['invoice']['id']}/pay",
            json={"amount": bayar, "proof_file_ids": [upload_proof()]}))
    if salur:
        ok(call(FINANCE, "POST", f"/contracts/{d['contract_id']}/cost-disbursements",
                json={"component_code": "NOTARY_FEE", "amount": salur, "payee": "Notaris Uji W1-C"}))
    lead_id = ok(call(OWNER, "GET", f"/deals/{d['deal_id']}"))["data"]["lead_id"]
    return {"deal_id": d["deal_id"], "contract_id": d["contract_id"], "lead_id": lead_id, "unit_code": d["unit_code"]}


def cancelled_with_request(world, **kw):
    """Deal batal (oleh OWNER) + permohonan refund titipan biaya `diajukan` (pemohon = OWNER)."""
    d = cost_deal(world, **kw)
    ok(call(OWNER, "POST", f"/deals/{d['deal_id']}/cancel", json={"reason": "uji peramban W1-C batal dengan titipan biaya"}))
    rows = ok(call(OWNER, "GET", "/cancel-cost-settlements", params={"deal_id": d["deal_id"]}))["data"]
    assert len(rows) == 1 and rows[0]["state"] == "diajukan", rows
    return {**d, "settlement_id": rows[0]["id"], "number": rows[0]["number"]}


def main():
    world = World()
    acc = ok(call(FINANCE, "POST", "/cash-bank/accounts", json={
        "kind": "bank", "name": f"Rek W1C UI {uuid.uuid4().hex[:6].upper()}", "bank_name": "Bank Uji W1C",
        "account_no": uuid.uuid4().hex[:10].upper(), "opening_balance": 5_000_000_000}))["data"]
    ok(call(FINANCE, "POST", f"/cash-bank/accounts/{acc['id']}/set-default"))     # kolom "Dari rekening" memilih default
    out = {"project_id": world.project_id, "bank_id": acc["id"], "bank_name": acc["name"],
           "dialog_deal": cost_deal(world),                     # deal HIDUP dengan titipan biaya (dialog batal menampilkan kebijakan)
           "req_approve": cancelled_with_request(world),        # disetujui lalu dibayar lewat UI
           "req_reject": cancelled_with_request(world),         # ditolak lewat UI
           "req_stale": cancelled_with_request(world)}          # diputus "dari sisi lain" sebelum tombol UI ditekan (400 + muat ulang)
    with open(OUT, "w") as f:
        json.dump(out, f, indent=1)
    print(OUT)


if __name__ == "__main__":
    main()
