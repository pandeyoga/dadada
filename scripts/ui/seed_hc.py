#!/usr/bin/env python3
"""Menyemai data uji untuk skrip peramban scripts/ui/ronde_perbaikan.js (lewat API, bukan DB langsung).

Memakai ulang pembantu tes P0 (`backend/tests/p0/test_p0_masuk*.py`): proyek + 80 unit baru per jalankan, deal,
kontrak, kuitansi, permintaan material, PO, izin, komplain, rekening kas. Hasilnya ditulis sebagai JSON
(`SIPRO_UI_SEED_OUT`, bawaan `<tmp>/sipro-ui-seed.json`) dan dibaca skrip peramban.

    API_BASE=http://localhost:8073/api python3 scripts/ui/seed_hc.py
"""
import json
import os
import sys
import tempfile
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "backend", "tests", "p0"))

from test_p0_masuk import FINANCE, MANAGER, OWNER, SALES, World, call, ok, pay  # noqa: E402
from test_p0_masuk_2 import allin_deal, approve, cancel_case, convert  # noqa: E402,F401

FINLEAD = "finlead@sipro.co.id"
OUT = os.environ.get("SIPRO_UI_SEED_OUT") or os.path.join(tempfile.gettempdir(), "sipro-ui-seed.json")


def uid(p="H"):
    return f"{p}{uuid.uuid4().hex[:6].upper()}"


def material(world, name, stock=100):
    pid = world.project_id
    mid = ok(call(OWNER, "POST", "/materials", json={"project_id": pid, "name": f"{name} {uid()}", "uom": "sak"}))["data"]["id"]
    if stock:
        ok(call(OWNER, "POST", "/materials/txn", json={
            "project_id": pid, "material_id": mid, "type": "in", "qty": stock, "note": "UIHC stok awal"}))
    return mid


def po_partial(world, mid, qty=100, recv=60):
    po = ok(call(FINANCE, "POST", "/procurement/pos", json={
        "project_id": world.project_id, "po_type": "material", "vendor": f"Vendor UIHC {uid()}",
        "items": [{"description": "Semen UIHC", "material_id": mid, "uom": "sak", "qty": qty, "unit_price": 55_000}]}))["data"]
    ok(call(OWNER, "POST", f"/procurement/pos/{po['id']}/approve", json={}))
    ok(call(OWNER, "POST", "/procurement/grns", json={"po_id": po["id"], "items": [{"po_item_index": 0, "qty_received": recv}]}))
    return po["id"], po.get("po_number") or po.get("number")


def bank(opening):
    body = {"kind": "bank", "name": f"Rek UIHC {uid('R')}", "bank_name": "Bank Uji", "account_no": uid("NO"),
            "opening_balance": opening}
    return ok(call(FINANCE, "POST", "/cash-bank/accounts", json=body))["data"]


def transfer(src, dst, amount):
    r = ok(call(FINANCE, "POST", "/cash-bank/transfers", json={
        "kind": "transfer", "from_account_id": src["id"], "to_account_id": dst["id"],
        "amount": amount, "fee": 0, "reference": uid("UIHC")}))["data"]
    return {"id": r["id"], "no": r.get("no")}


def lead_of(deal_id):
    return ok(call(OWNER, "GET", f"/deals/{deal_id}"))["data"]["lead_id"]


def main():
    world = World()
    out = {"project_id": world.project_id,
           "project_name": ok(call(OWNER, "GET", f"/projects/{world.project_id}"))["data"]["project"]["name"]}

    # (a) pembatalan dengan titipan biaya + invoice biaya terbuka (kotak pengakuan biaya): tiga kontrak
    from test_p0_masuk import upload_proof
    for key in ("cancel_cost", "cancel_cost_reject", "cancel_cost_stale"):
        d = allin_deal(world)
        ok(call(FINANCE, "POST", f"/cost-invoices/{d['invoice']['id']}/pay",
                json={"amount": 20_000_000, "proof_file_ids": [upload_proof()]}))
        c = ok(call(MANAGER, "POST", "/cancellations", json={"contract_id": d["contract_id"],
                                                             "reason": "uji peramban batal dengan titipan biaya"}))["data"]
        out[key] = {"deal_id": d["deal_id"], "contract_id": d["contract_id"], "cancel_id": c["id"], "unit_code": d["unit_code"]}

    # (f) batal reservasi satu-klik: satu deal dengan titipan biaya + invoice biaya terbuka, satu deal biasa
    d = allin_deal(world)
    ok(call(FINANCE, "POST", f"/cost-invoices/{d['invoice']['id']}/pay",
            json={"amount": 20_000_000, "proof_file_ids": [upload_proof()]}))
    out["deal_cancel_cost"] = {"deal_id": d["deal_id"], "lead_id": lead_of(d["deal_id"]), "unit_code": d["unit_code"]}
    p = world.new_deal()
    out["deal_cancel_plain"] = {"deal_id": p["deal_id"], "lead_id": p["lead_id"], "unit_code": p["unit_code"]}

    # (d) void kuitansi: satu yang sah (finlead), satu pada deal yang sudah batal (ditolak server)
    v = world.new_deal()
    resp = ok(pay(v["deal_id"], 100_000_000))
    rid = (resp.get("data") or resp)["receipt"]["id"]
    out["void_ok"] = {"deal_id": v["deal_id"], "receipt_id": rid, "unit_code": v["unit_code"]}
    b = cancel_case(world, paid=100_000_000)
    approve(b["cancel_id"])
    out["void_batal"] = {"deal_id": b["deal_id"], "contract_id": b["contract_id"], "unit_code": b["unit_code"]}

    # (e) aksi yang kini bisa 400/409
    out["req_approve"] = ok(call(OWNER, "POST", "/materials/requisitions", json={
        "project_id": world.project_id, "items": [{"material_id": material(world, "UIHC Req"), "qty": 5}],
        "purpose": "UIHC setuju basi"}))["data"]["id"]
    out["req_reject"] = ok(call(OWNER, "POST", "/materials/requisitions", json={
        "project_id": world.project_id, "items": [{"material_id": material(world, "UIHC Req2"), "qty": 5}],
        "purpose": "UIHC tolak basi"}))["data"]["id"]
    pname = f"Izin UIHC {uid()}"
    out["permit"] = ok(call(OWNER, "POST", "/permits", json={
        "project_id": world.project_id, "type": "IMB", "name": pname}))["data"]["id"]
    out["permit_name"] = pname
    cust = ok(call(OWNER, "GET", "/customers", params={"limit": 1}))["data"][0]
    subject = f"Komplain UIHC {uid()}"
    out["complaint"] = ok(call(OWNER, "POST", "/complaints", json={
        "customer_id": cust["id"], "subject": subject, "message": "pesan uji peramban",
        "channel": "telepon", "notify_customer": False}))["data"]["id"]
    out["complaint_subject"] = subject
    out["po_id"], out["po_number"] = po_partial(world, material(world, "UIHC PO", stock=0))
    unit = world.units[-1]
    ok(call(OWNER, "POST", f"/masterplan/units/{unit['id']}/block", json={"blocked": True, "reason": "UIHC blokir uji peramban"}))
    out["unit_block"] = {"unit_id": unit["id"], "code": unit["code"], "project_id": world.project_id}
    src, dst = bank(50_000_000), bank(0)
    out["transfer_src"], out["transfer_dst"] = src["name"], dst["name"]
    out["transfer_approve"] = transfer(src, dst, 1_000_000)
    out["transfer_reject"] = transfer(src, dst, 2_000_000)
    with open(OUT, "w") as f:
        json.dump(out, f, indent=1)
    print(OUT)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
