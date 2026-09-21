#!/usr/bin/env python3
"""POC FASE M — MAKLOON (jalur "buat sendiri") LENGKAP, per rencana §M
`RENCANA_EKSEKUSI_MD_ERP.md`.

Yang dibuktikan (dan HARUS tetap benar selamanya):
  M1  Rantai `benang → tenun → celup` berjalan lewat API: SPK ber-`line_code`,
      tahap dari master (`steps[].stage_code`), output langkah N = input langkah N+1.
  M2  BIAYA PER TAHAP tercatat: `steps[].tariff_actual` terisi saat terima,
      tagihan jasa (`vendor_bills` makloon_service) lahir per langkah,
      dan WIP 1-1350 kembali NOL setelah siklus (GL seimbang).
  M3  Hasil makloon menghasilkan roll ber-grade **LEWAT DOKUMEN INSPEKSI**
      (`inspections` kind=makloon_output, FASE I): warna beda dari sample →
      baris DITAHAN (kebijakan pemilik #5), petugas gudang TIDAK bisa melepas
      (403), MANAJER melepas ber-alasan, lalu keputusan `terima` menutup SPK
      dengan `grade_after` terisi.
  M4  Tahap SCREEN di jalur printing = JASA MURNI: kain TIDAK bergerak
      (issue → 409), output = kain yang sama (tahap kain tidak berubah),
      dan biayanya DISERAP ke HPP kain cetak langkah berikutnya
      (`absorbed_service_value`) — bukan hilang, bukan mengubah tahap.
  M5  Papan per LINI: `?line=woven` menyaring SPK, dan akun manajer berpagar
      lini printing hanya melihat SPK printing.
  M6  NOL RESIDU: seluruh dokumen uji dihapus; jejak login/audit/notifikasi
      dibuang lewat selisih himpunan ID (pelajaran POC FASE N & S).

Jalankan:  cd /app/backend && python test_core_makloon_lini_poc.py
"""
from __future__ import annotations

import asyncio
import os
import sys
import uuid

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db import db  # noqa: E402
from core_utils import now_iso  # noqa: E402
from services.roll_service import create_inbound_roll  # noqa: E402

BASE = os.environ.get("POC_BASE_URL", "http://localhost:8001")
PW = "demo12345"
ENT = "ent_ksc"
WH = "wh_jakarta"
PARTNER = "mak_seed_tenun"
TAG = f"POCM-{uuid.uuid4().hex[:6]}"

PASS = 0
FAIL = 0


def ok(cond: bool, label: str, extra: str = "") -> bool:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [PASS] {label}" + (f"  ({extra})" if extra else ""))
    else:
        FAIL += 1
        print(f"  [FAIL] {label}" + (f"\n         → {extra}" if extra else ""))
    return cond


def login(email: str) -> dict:
    r = requests.post(f"{BASE}/api/auth/login", json={"email": email, "password": PW}, timeout=30)
    r.raise_for_status()
    return {"Authorization": f"Bearer {r.json()['token']}", "X-Entity-Id": ENT}


async def _ids(coll) -> set:
    return {d["id"] async for d in coll.find({}, {"_id": 0, "id": 1})}


async def gl_wip_delta(mko_id: str, bill_ids: list) -> float:
    """Δ 1-1350 (WIP subcon) dari seluruh JE milik satu SPK — harus NOL di akhir."""
    flt = {"$or": [{"source_id": {"$regex": mko_id}},
                   {"source_id": {"$in": bill_ids or ["__none__"]}}],
           "source_type": {"$in": ["subcon_issue", "subcon_service", "subcon_receipt",
                                   "subcon_service_unabsorbed"]}}
    total = 0.0
    async for je in db.journal_entries.find(flt, {"_id": 0, "lines": 1}):
        for l in je.get("lines", []):
            if l.get("account_code") == "1-1350":
                total += float(l.get("debit", 0) or 0) - float(l.get("credit", 0) or 0)
    return round(total, 2)


async def run() -> bool:
    print(f"\n=== POC FASE M — MAKLOON LENGKAP ({TAG}) ===")
    # M6 — jejak yang lahir selama POC dibuang lewat SELISIH HIMPUNAN (bukan tebakan).
    pre_audit = await _ids(db.audit_logs)
    pre_sessions = await _ids(db.sessions)
    pre_notifs = await _ids(db.notifications)

    now = now_iso()
    P_BENANG, P_GREY, P_CELUP = f"prod_{TAG}_benang", f"prod_{TAG}_grey", f"prod_{TAG}_celup"
    P_GREY2, P_PRINT = f"prod_{TAG}_grey2", f"prod_{TAG}_print"
    PIDS = [P_BENANG, P_GREY, P_CELUP, P_GREY2, P_PRINT]
    mko_ids: list = []
    ins_ids: list = []
    try:
        # ── SETUP: produk + stok bahan ────────────────────────────────────────
        for pid, name, unit, line in [
            (P_BENANG, f"{TAG} Benang Katun", "kg", ""),
            (P_GREY, f"{TAG} Grey Katun", "yard", "woven"),
            (P_CELUP, f"{TAG} Kain Celup", "yard", "woven"),
            (P_GREY2, f"{TAG} Grey Printing", "yard", "printing"),
            (P_PRINT, f"{TAG} Kain Cetak", "yard", "printing"),
        ]:
            await db.products.insert_one({
                "id": pid, "sku": pid.upper(), "name": name, "base_unit": unit,
                "category": "kain", "line_code": line, "status": "active",
                "created_at": now, "updated_at": now, "_poc": TAG})
        await create_inbound_roll(P_BENANG, WH, ENT, 100.0, lot=f"{TAG}-YARN", unit="kg",
                                  acquired_via="poc_seed", ref_id=TAG, unit_cost=100.0,
                                  created_by=TAG)
        await create_inbound_roll(P_GREY2, WH, ENT, 50.0, lot=f"{TAG}-GREY2", unit="yard",
                                  acquired_via="poc_seed", ref_id=TAG, unit_cost=200.0,
                                  created_by=TAG)

        admin = login("admin@kainnusantara.id")
        manager = login("manager@kainnusantara.id")
        wh_user = login("warehouse@kainnusantara.id")
        mgr_printing = login("manager.printing@kainnusantara.id")
        wh_uid = (await db.users.find_one({"email": "warehouse@kainnusantara.id"},
                                          {"_id": 0, "id": 1}))["id"]

        # ═════ M1 — rantai benang → tenun → celup (SPK A, lini woven) ═════════
        print("\n[M1] Rantai benang → tenun → celup lewat API")
        r = requests.post(f"{BASE}/api/makloon-orders", headers=admin, timeout=30, json={
            "mode": "process_only", "material_product_id": P_BENANG, "material_qty": 100,
            "from_warehouse_id": WH, "notes": TAG,
            "steps": [
                {"stage_code": "tenun", "makloon_id": PARTNER, "input_product_id": P_BENANG,
                 "output_product_id": P_GREY, "tolerance_pct": 50},
                {"stage_code": "celup", "makloon_id": PARTNER, "input_product_id": P_GREY,
                 "output_product_id": P_CELUP, "tolerance_pct": 50},
            ]})
        ok(r.status_code == 200, "SPK A lahir via API", r.text[:200])
        mko_a = r.json()
        mko_ids.append(mko_a["id"])
        steps = mko_a.get("steps", [])
        ok(len(steps) == 2 and steps[0].get("stage_code") == "tenun"
           and steps[1].get("stage_code") == "celup",
           "Tahap dari MASTER: steps[].stage_code = tenun, celup",
           str([s.get("stage_code") for s in steps]))
        ok(mko_a.get("line_code") == "woven", "SPK A ber-line_code=woven",
           str(mko_a.get("line_code")))
        # rantai terputus DITOLAK (output N ≠ input N+1)
        r = requests.post(f"{BASE}/api/makloon-orders", headers=admin, timeout=30, json={
            "mode": "process_only", "material_product_id": P_BENANG, "material_qty": 10,
            "from_warehouse_id": WH,
            "steps": [
                {"stage_code": "tenun", "input_product_id": P_BENANG, "output_product_id": P_GREY},
                {"stage_code": "celup", "input_product_id": P_GREY2, "output_product_id": P_CELUP},
            ]})
        ok(r.status_code == 400 and "terputus" in r.text,
           "Rantai terputus (input step 2 ≠ output step 1) → 400", r.text[:160])

        # issue + terima step 1 (tenun) — tarif manual 500rb
        r = requests.post(f"{BASE}/api/makloon-orders/{mko_a['id']}/issue",
                          headers=admin, json={"step_seq": 1}, timeout=30)
        ok(r.status_code == 200, "Issue step 1: benang keluar ke mitra", r.text[:160])
        r = requests.post(f"{BASE}/api/makloon-orders/{mko_a['id']}/receive",
                          headers=admin, timeout=30, json={
                              "step_seq": 1, "actual_output_qty": 95, "tariff": 500000,
                              "rolls": [{"lot": f"{TAG}-GREY-1", "length": 95, "grade": "A"}]})
        ok(r.status_code == 200, "Terima step 1: 95 yard grey (1 roll ber-LOT)", r.text[:200])
        # issue + terima step 2 (celup) — tarif manual 300rb
        r = requests.post(f"{BASE}/api/makloon-orders/{mko_a['id']}/issue",
                          headers=admin, json={"step_seq": 2}, timeout=30)
        ok(r.status_code == 200, "Issue step 2: grey keluar ke mitra celup", r.text[:160])
        r = requests.post(f"{BASE}/api/makloon-orders/{mko_a['id']}/receive",
                          headers=admin, timeout=30, json={
                              "step_seq": 2, "actual_output_qty": 90, "tariff": 300000,
                              "rolls": [{"lot": f"{TAG}-CELUP-1", "length": 90, "grade": "A"}]})
        ok(r.status_code == 200, "Terima step 2: 90 yard kain celup", r.text[:200])
        mko_a = r.json()
        ok(mko_a.get("status") == "completed", "SPK A selesai (completed)",
           str(mko_a.get("status")))

        # ═════ M2 — biaya per tahap tercatat + GL WIP nol ═════════════════════
        print("\n[M2] Biaya per tahap & GL")
        s1, s2 = mko_a["steps"][0], mko_a["steps"][1]
        ok(float((s1.get("tariff_actual") or {}).get("amount") or 0) == 500000.0,
           "steps[0].tariff_actual = Rp 500.000 (tercatat)", str(s1.get("tariff_actual", {}).get("amount")))
        ok(float((s2.get("tariff_actual") or {}).get("amount") or 0) == 300000.0,
           "steps[1].tariff_actual = Rp 300.000 (tercatat)", str(s2.get("tariff_actual", {}).get("amount")))
        bills_a = await db.vendor_bills.find(
            {"makloon_order_id": mko_a["id"], "bill_type": "makloon_service"},
            {"_id": 0, "id": 1, "net_amount": 1}).to_list(10)
        ok(len(bills_a) == 2 and round(sum(b["net_amount"] for b in bills_a), 2) == 800000.0,
           "2 tagihan jasa makloon lahir (total Rp 800.000)",
           f"n={len(bills_a)} total={sum(b['net_amount'] for b in bills_a)}")
        wip_a = await gl_wip_delta(mko_a["id"], [b["id"] for b in bills_a])
        ok(abs(wip_a) < 0.01, "WIP 1-1350 SPK A kembali NOL (GL seimbang)", f"Δ={wip_a}")

        # ═════ M3 — hasil makloon ber-grade LEWAT DOKUMEN INSPEKSI (FASE I) ═══
        print("\n[M3] Inspeksi hasil makloon → tahan warna → manajer melepas → grade")
        r = requests.post(f"{BASE}/api/inspections", headers=admin, timeout=30,
                          json={"kind": "makloon_output", "ref_doc_id": mko_a["id"]})
        ok(r.status_code == 200, "SPK inspeksi makloon_output lahir", r.text[:200])
        ins = r.json()
        ins_ids.append(ins["id"])
        ok(ins.get("ref_doc_number") == mko_a.get("mko_number"),
           "SPK menyebut nomor order makloonnya", str(ins.get("ref_doc_number")))
        celup_roll = await db.inventory_rolls.find_one(
            {"product_id": P_CELUP}, {"_id": 0, "id": 1})
        line = next((l for l in ins.get("lines", [])
                     if l.get("roll_id") == (celup_roll or {}).get("id")), None)
        ok(line is not None, "Baris SPK menunjuk roll kain celup", str(len(ins.get("lines", []))))

        requests.post(f"{BASE}/api/inspections/{ins['id']}/assign", headers=admin,
                      json={"assigned_to": wh_uid}, timeout=30)
        requests.post(f"{BASE}/api/inspections/{ins['id']}/start", headers=wh_user, timeout=30)
        # warna beda dari sample → DITAHAN (kebijakan pemilik #5)
        r = requests.post(f"{BASE}/api/inspections/{ins['id']}/lines/{line['id']}/inspect",
                          headers=wh_user, json={"color_result": "beda_shade"}, timeout=30)
        held = next((l for l in r.json().get("lines", []) if l.get("id") == line["id"]), {})
        ok(r.status_code == 200 and held.get("hold") is True,
           "Warna beda_shade → baris DITAHAN", f"hold={held.get('hold')}")
        # petugas gudang TIDAK boleh melepas tahanan
        r = requests.post(f"{BASE}/api/inspections/{ins['id']}/lines/{line['id']}/release-hold",
                          headers=wh_user,
                          json={"reason": "uji coba pelepasan oleh petugas gudang"}, timeout=30)
        ok(r.status_code == 403, "Petugas gudang melepas tahanan → 403", str(r.status_code))
        # MANAJER melepas, ber-alasan
        r = requests.post(f"{BASE}/api/inspections/{ins['id']}/lines/{line['id']}/release-hold",
                          headers=manager,
                          json={"reason": "Selisih warna disepakati pelanggan via sales."},
                          timeout=30)
        rel = next((l for l in r.json().get("lines", []) if l.get("id") == line["id"]), {})
        ok(r.status_code == 200 and rel.get("hold") is False,
           "Manajer melepas tahanan ber-alasan → hold lepas", r.text[:160])
        # hasil akhir baris: sesuai + terima → grade tercatat lewat dokumen
        r = requests.post(f"{BASE}/api/inspections/{ins['id']}/lines/{line['id']}/inspect",
                          headers=wh_user,
                          json={"color_result": "sesuai", "handfeel_result": "sesuai",
                                "decision": "terima"}, timeout=30)
        done_line = next((l for l in r.json().get("lines", []) if l.get("id") == line["id"]), {})
        ok(bool(done_line.get("grade_after")), "Baris punya grade_after (grade lewat dokumen)",
           str(done_line.get("grade_after")))
        roll_now = await db.inventory_rolls.find_one({"id": celup_roll["id"]},
                                                     {"_id": 0, "grade": 1})
        ok((roll_now or {}).get("grade") == done_line.get("grade_after"),
           "Grade roll fisik == grade_after dokumen (satu pintu)",
           f"roll={roll_now.get('grade')} dok={done_line.get('grade_after')}")
        r = requests.post(f"{BASE}/api/inspections/{ins['id']}/finish", headers=manager,
                          json={"decision": "terima", "remark": ""}, timeout=30)
        ok(r.status_code == 200 and r.json().get("status") == "done",
           "SPK inspeksi ditutup dengan keputusan terima", r.text[:160])

        # ═════ M4 — SCREEN (printing) = jasa murni, biaya diserap HPP kain ═════
        print("\n[M4] Tahap Screen: jasa murni, kain tidak berubah, biaya diserap")
        r = requests.post(f"{BASE}/api/makloon-orders", headers=admin, timeout=30, json={
            "mode": "process_only", "material_product_id": P_GREY2, "material_qty": 50,
            "from_warehouse_id": WH, "notes": TAG,
            "steps": [
                {"stage_code": "screen", "makloon_id": PARTNER, "input_product_id": P_GREY2},
                {"stage_code": "printing", "makloon_id": PARTNER, "input_product_id": P_GREY2,
                 "output_product_id": P_PRINT, "tolerance_pct": 50},
            ]})
        ok(r.status_code == 200, "SPK B (printing, dimulai tahap Screen) lahir", r.text[:200])
        mko_b = r.json()
        mko_ids.append(mko_b["id"])
        b1 = mko_b["steps"][0]
        ok(b1.get("material_flow") == "service_only" and b1.get("changes_stage") is False,
           "Screen = jasa murni & TIDAK mengubah tahap kain",
           f"flow={b1.get('material_flow')} changes={b1.get('changes_stage')}")
        ok(b1.get("output_product_id") == P_GREY2,
           "Output screen = kain yang sama (tahap kain tak bergeser)",
           str(b1.get("output_product_id")))
        r = requests.post(f"{BASE}/api/makloon-orders/{mko_b['id']}/issue",
                          headers=admin, json={"step_seq": 1}, timeout=30)
        ok(r.status_code == 409, "Issue kain pada langkah jasa murni → 409", str(r.status_code))
        r = requests.post(f"{BASE}/api/makloon-orders/{mko_b['id']}/record-service",
                          headers=admin, json={"step_seq": 1, "tariff": 750000}, timeout=30)
        ok(r.status_code == 200, "Catat Jasa screen Rp 750.000", r.text[:160])
        ok(float(r.json().get("service_absorption_pending") or 0) == 750000.0,
           "Jasa screen menunggu diserap kain (WIP)",
           str(r.json().get("service_absorption_pending")))
        r = requests.post(f"{BASE}/api/makloon-orders/{mko_b['id']}/issue",
                          headers=admin, json={"step_seq": 2}, timeout=30)
        ok(r.status_code == 200, "Issue step 2 (kain grey ke mitra cetak)", r.text[:160])
        r = requests.post(f"{BASE}/api/makloon-orders/{mko_b['id']}/receive",
                          headers=admin, timeout=30, json={
                              "step_seq": 2, "actual_output_qty": 48, "tariff": 200000,
                              "rolls": [{"lot": f"{TAG}-PRINT-1", "length": 48, "grade": "A"}]})
        ok(r.status_code == 200, "Terima step 2: 48 yard kain cetak", r.text[:200])
        mko_b = r.json()
        b2 = mko_b["steps"][1]
        ok(float(b2.get("absorbed_service_value") or 0) == 750000.0,
           "Biaya screen DISERAP ke HPP kain cetak (absorbed_service_value)",
           str(b2.get("absorbed_service_value")))
        # HPP kain cetak = bahan (50×200=10.000) + jasa cetak 200.000 + screen 750.000
        ok(float(b2.get("output_value") or 0) == 960000.0,
           "output_value kain cetak = 10.000 + 200.000 + 750.000 = Rp 960.000",
           str(b2.get("output_value")))
        bills_b = await db.vendor_bills.find(
            {"makloon_order_id": mko_b["id"], "bill_type": "makloon_service"},
            {"_id": 0, "id": 1}).to_list(10)
        wip_b = await gl_wip_delta(mko_b["id"], [b["id"] for b in bills_b])
        ok(abs(wip_b) < 0.01, "WIP 1-1350 SPK B kembali NOL (screen terserap)", f"Δ={wip_b}")

        # ═════ M5 — papan per LINI ═════════════════════════════════════════════
        print("\n[M5] Papan per lini")
        r = requests.get(f"{BASE}/api/makloon-orders?line=woven", headers=admin, timeout=30)
        ids_woven = {d["id"] for d in r.json()}
        ok(mko_a["id"] in ids_woven and mko_b["id"] not in ids_woven,
           "?line=woven: SPK woven tampil, SPK printing tidak")
        r = requests.get(f"{BASE}/api/makloon-orders", headers=mgr_printing, timeout=30)
        rows = r.json()
        ids_pr = {d["id"] for d in rows}
        ok(mko_b["id"] in ids_pr and mko_a["id"] not in ids_pr
           and all((d.get("line_code") or "") == "printing" for d in rows),
           "Manajer berpagar lini printing hanya melihat SPK printing",
           f"n={len(rows)}")

        print(f"\n=== HASIL POC FASE M: {PASS} PASS / {FAIL} FAIL ===")
        return FAIL == 0
    finally:
        # ═════ M6 — NOL RESIDU ═════════════════════════════════════════════════
        bill_ids = [b["id"] async for b in db.vendor_bills.find(
            {"makloon_order_id": {"$in": mko_ids}}, {"_id": 0, "id": 1})]
        await db.inspections.delete_many({"id": {"$in": ins_ids}})
        await db.makloon_orders.delete_many({"id": {"$in": mko_ids}})
        await db.vendor_bills.delete_many({"id": {"$in": bill_ids}})
        for mid in mko_ids:
            await db.journal_entries.delete_many({"source_id": {"$regex": mid}})
        if bill_ids:
            await db.journal_entries.delete_many({"source_id": {"$in": bill_ids}})
        lots = [x["id"] async for x in db.inventory_lots.find(
            {"product_id": {"$in": PIDS}}, {"_id": 0, "id": 1})]
        await db.inventory_lots.delete_many({"product_id": {"$in": PIDS}})
        if lots:
            await db.inventory_lots.update_many({}, {"$pull": {"parent_lot_ids": {"$in": lots}}})
            await db.inventory_lots.update_many({}, {"$pull": {"child_lot_ids": {"$in": lots}}})
        await db.inventory_rolls.delete_many({"product_id": {"$in": PIDS}})
        await db.inventory_movements.delete_many({"product_id": {"$in": PIDS}})
        await db.inventory_balances.delete_many({"product_id": {"$in": PIDS}})
        await db.products.delete_many({"id": {"$in": PIDS}})
        for coll, pre in ((db.audit_logs, pre_audit), (db.sessions, pre_sessions),
                          (db.notifications, pre_notifs)):
            born = (await _ids(coll)) - pre
            if born:
                await coll.delete_many({"id": {"$in": list(born)}})
        print("  [cleanup] seluruh data & jejak uji POC dihapus (selisih himpunan).")


if __name__ == "__main__":
    hasil = asyncio.get_event_loop().run_until_complete(run())
    raise SystemExit(0 if hasil else 1)
