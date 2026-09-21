#!/usr/bin/env python3
"""POC — SESI 2026-06 (lanjutan ke-5): **nilai tagihan supplier · riwayat nilai roll ·
papan bisa ditindak**

KENAPA POC INI ADA
==================
Ketiga pekerjaan ini menutup kelas cacat yang sama: keputusan/nilai yang benar tetapi
TIDAK TERLIHAT.
  · papan tagihan supplier menyebut jumlah dokumen tanpa menyebut uangnya;
  · HPP roll bisa naik dari empat arah berbeda tanpa satu pun jejak siapa & atas dasar
    apa (inilah yang membuat selisih Rp 900.000 di buku CV Kanda Suka bertahan
    berbulan-bulan);
  · papan menyebut apa yang menunggu tanda tangan tetapi tanda tangannya harus
    diberikan di layar lain.

YANG DIBUKTIKAN
---------------
N1 **Nilai rupiah tagihan supplier & kontrabon** muncul di baris papan (`amount`),
   dibaca dari field dokumen NYATA (`vendor_bills.grand_total`,
   `contra_bons.totals.net_payable`) — bukan 0 dan bukan ditebak.
N2 **Riwayat nilai roll**: revaluasi retur antar-PT MENULIS jejak (`old → new`, alasan,
   aktor, dokumen, `delta_value`), endpoint `/api/inventory/rolls/{id}/cost-history`
   mengembalikannya, roll badan usaha lain **403**, dan migrasi startup yang mengisi
   HPP roll baru juga berjejak (`startup_backfill`).
N3 **Papan bisa ditindak**: baris papan membawa `action` (path pintu keputusan yang
   SUDAH ada) hanya bila peran itu BERWENANG — peran tanpa izin dapat `None`; antrean
   yang keputusannya butuh pilihan/berbaris (`contra_bon_dispute`, `inspection_hold`)
   sengaja TIDAK dapat tombol; dan menekan tombolnya benar-benar menyelesaikan dokumen
   (diuji ujung-ke-ujung lewat HTTP pada tagihan supplier buatan POC).
N4 **NOL RESIDU** (INV-GATE-01) — diukur, plus bukti-merah pengukurnya sendiri.

Usage:  python backend/test_core_sesi_2026_06c_poc.py
"""
import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / "backend" / ".env")
except Exception:  # noqa: BLE001
    pass

import httpx  # noqa: E402

sys.path.insert(0, str(ROOT / "scripts" / "guardrails"))
from _common import DbSnapshot  # noqa: E402

BASE = os.environ.get("POC_BASE", "http://localhost:8001")
PWD = "demo12345"
G, R, Y, B, DIM, X = ("\033[92m", "\033[91m", "\033[93m", "\033[1m", "\033[2m", "\033[0m")
TOUCHED = ["inventory_rolls", "journal_entries", "interco_returns", "warehouse_transfers",
           "vendor_bills", "roll_cost_history", "audit_logs", "sessions", "login_attempts",
           "notifications"]
TANDA = "POC_SESI_2026_06C"
NILAI_TAGIHAN = 43_500_000.0

PASS = FAIL = 0


def ok(cond, label, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [{G}PASS{X}] {label}" + (f" {DIM}{extra}{X}" if extra else ""))
    else:
        FAIL += 1
        print(f"  [{R}FAIL{X}] {label}" + (f" {R}{extra}{X}" if extra else ""))
    return bool(cond)


def login(email, entity="ent_ksc"):
    c = httpx.Client(base_url=BASE, timeout=120.0)
    r = c.post("/api/auth/login", json={"email": email, "password": PWD})
    r.raise_for_status()
    c.headers.update({"Authorization": f"Bearer {r.json()['token']}",
                      "X-Entity-Id": entity})
    return c


def doc_counts(db):
    return {c: db[c].count_documents({}) for c in TOUCHED}


def residu(base, db):
    now = doc_counts(db)
    return {c: (base[c], now[c]) for c in base if base[c] != now[c]}


def papan(payload, key):
    for b in (payload.get("waiting_boards") or []):
        if b.get("key") == key:
            return b
    return {}


def baris(board, number):
    for r in (board.get("rows") or []):
        if r.get("number") == number:
            return r
    return {}


async def main() -> int:  # noqa: PLR0915
    print(f"{B}{'=' * 78}\n  POC SESI 2026-06c (nilai tagihan · riwayat nilai roll · "
          f"papan bisa ditindak)  ·  {BASE}\n{'=' * 78}{X}")
    from pymongo import MongoClient
    db = MongoClient(os.environ["MONGO_URL"], serverSelectionTimeoutMS=4000)[
        os.environ["DB_NAME"]]
    db.command("ping")

    from services import interco_return_service as icret

    base = doc_counts(db)
    snap = DbSnapshot(db, ["audit_logs", "sessions", "login_attempts",
                           "interco_transactions", "interco_returns", "vendor_bills",
                           "journal_entries", "interco_accounts",
                           "intercompany_eliminations", "purchase_orders"])
    snap.take()
    try:
        adm = login("admin@kainnusantara.id", entity="ent_ksc")

        # ── N1 — nilai rupiah di papan tagihan supplier & kontrabon ───────────
        print(f"\n{B}▶ N1 — papan menyebut UANG-nya, bukan cuma jumlah dokumennya{X}")
        sup = db.suppliers.find_one({}, {"_id": 0, "id": 1, "name": 1}) or {}
        bill_id = f"vb_{TANDA.lower()}"
        db.vendor_bills.insert_one({
            "id": bill_id, "bill_number": "POC/VB-90001", "entity_id": "ent_ksc",
            "status": "pending_approval", "bill_type": "makloon",
            "supplier_id": sup.get("id", ""), "supplier_name": sup.get("name", "Pemasok POC"),
            "supplier_invoice_no": "INV-POC-90001",
            "grand_total": NILAI_TAGIHAN, "net_amount": NILAI_TAGIHAN,
            "ppn_amount": 0.0, "aux_cost": 0.0, "tariff": 0.0,
            "bill_date": "2026-06-01T00:00:00+00:00",
            "po_id": (db.purchase_orders.find_one({}, {"_id": 0, "id": 1}) or {}).get("id", ""),
            "items": [],
            "created_at": "2026-06-01T00:00:00+00:00", "created_by": "poc",
            "created_by_id": "poc", "refs": {}, "_poc": TANDA})
        fin_home = adm.get("/api/home/finance").json()
        pb = papan(fin_home, "vendor_bill")
        row = baris(pb, "POC/VB-90001")
        ok(abs(float(row.get("amount") or 0) - NILAI_TAGIHAN) < 1,
           "baris tagihan supplier membawa nominal rupiahnya (dulu selalu Rp 0)",
           f"amount={row.get('amount')}")
        ok(row.get("note") in ("INV-POC-90001", "makloon"),
           "baris menyebut nomor faktur supplier sebagai keterangan",
           f"note={row.get('note')!r}")
        cbv = papan(fin_home, "contra_bon_verify")
        nilai_cb = [float(r.get("amount") or 0) for r in (cbv.get("rows") or [])]
        ok(not nilai_cb or all(v > 0 for v in nilai_cb),
           "baris kontrabon menunggu verifikasi juga bernilai (net yang akan dibayar)",
           f"{nilai_cb}")

        # ── N3 — papan bisa ditindak ──────────────────────────────────────────
        print(f"\n{B}▶ N3 — tombol keputusan di baris papan (wewenang diputuskan SERVER){X}")
        aksi = row.get("action") or {}
        ok(aksi.get("path") == f"/vendor-bills/{bill_id}/approve",
           "admin: baris tagihan membawa path pintu keputusan yang SUDAH ada",
           f"{aksi.get('path')}")
        ok(aksi.get("method") == "POST" and aksi.get("label") == "Setujui",
           "aksi menyebut metode & label yang jelas")
        fin = login("finance@kainnusantara.id", entity="ent_ksc")
        try:
            frow = baris(papan(fin.get("/api/home/finance").json(), "vendor_bill"),
                         "POC/VB-90001")
            ok(frow.get("action") is None,
               "peran TANPA izin `vendor_bill.approve` tidak diberi tombol "
               "(layar tidak pernah menebak wewenang)")
        finally:
            fin.close()
        wh = adm.get("/api/home/warehouse").json()
        insp = papan(wh, "inspection_hold")
        ok(all((r.get("action") is None) for r in (insp.get("rows") or [])),
           "barang ditahan QC SENGAJA tanpa tombol (pelepasan per BARIS + alasan wajib)",
           f"{len(insp.get('rows') or [])} baris")
        disp = papan(fin_home, "contra_bon_dispute")
        ok(all((r.get("action") is None) for r in (disp.get("rows") or [])),
           "kontrabon bersengketa SENGAJA tanpa tombol (keputusannya butuh PILIHAN)")
        trf = papan(wh, "transfer")
        ok(all(str((r.get("action") or {}).get("path", "")).startswith("/transfers/")
               for r in (trf.get("rows") or [])) or not (trf.get("rows") or []),
           "papan gudang: transfer menunggu ACC membawa pintu keputusannya")
        # …dan tombolnya benar-benar bekerja (ujung-ke-ujung lewat HTTP).
        r_act = adm.post(f"/api{aksi['path']}", json={})
        ok(r_act.status_code == 200,
           "menekan tombol dari papan MENYELESAIKAN dokumennya (bukan cuma tampak aktif)",
           f"HTTP {r_act.status_code} · {r_act.text[:90]}")
        sesudah = db.vendor_bills.find_one({"id": bill_id}, {"_id": 0}) or {}
        ok(sesudah.get("status") != "pending_approval",
           "status tagihan berpindah dari 'menunggu ACC' sesudah ditindak",
           f"status={sesudah.get('status')} approval={sesudah.get('approval_status')}")
        pb2 = papan(adm.get("/api/home/finance").json(), "vendor_bill")
        ok(not baris(pb2, "POC/VB-90001"),
           "barisnya HILANG dari papan sesudah diputuskan (angka papan ikut turun)",
           f"count={pb2.get('count')}")

        # ── N2 — riwayat nilai roll ───────────────────────────────────────────
        print(f"\n{B}▶ N2 — riwayat nilai (HPP) roll: siapa mengubah & atas dasar apa{X}")
        asal = db.interco_returns.find_one(
            {"role": "returner", "origin_pair_id": {"$nin": ["", None]}},
            {"_id": 0, "origin_pair_id": 1}) or {}
        rp = f"icrp_{TANDA.lower()}"
        trf_id = f"trn_{TANDA.lower()}"
        for role in ("returner", "receiver"):
            db.interco_returns.insert_one({
                "id": f"icr_{TANDA.lower()}_{role}", "return_pair_id": rp, "role": role,
                "number": f"POC/ICR-9000{1 if role == 'returner' else 2}",
                "status": "approved", "seller_entity_id": "ent_kanda",
                "buyer_entity_id": "ent_ksc", "subtotal": 900_000.0, "tax_amount": 0.0,
                "grand_total": 900_000.0, "items": [], "timeline": [],
                "origin_pair_id": asal.get("origin_pair_id", ""), "_poc": TANDA})
        transfer = {"id": trf_id, "code": "POC/TRF-90001",
                    "transfer_kind": "inter_entity", "entity_id": "ent_ksc",
                    "source_entity_id": "ent_ksc", "dest_entity_id": "ent_kanda",
                    "status": "completed", "interco_return_pair_id": rp,
                    "items": [], "_poc": TANDA}
        db.warehouse_transfers.insert_one(dict(transfer))
        roll_id = f"roll_{TANDA.lower()}"
        db.inventory_rolls.insert_one({
            "id": roll_id, "roll_no": "POC-RTN-90001", "product_id": "prod_poc_90001",
            "owner_entity_id": "ent_kanda", "entity_id": "ent_kanda",
            "status": "available", "length_remaining": 10.0, "length_initial": 10.0,
            "unit": "yard", "unit_cost": 0.0, "base_unit_cost": 90_000.0,
            "acquired": {"via": "transfer", "ref_id": trf_id},
            "cost_basis": {"source": "sales_return", "previous_unit_cost": 0.0},
            "_poc": TANDA})
        await icret.on_return_task_executed(dict(transfer), "Penguji POC")
        jejak = list(db.roll_cost_history.find({"roll_id": roll_id}, {"_id": 0}))
        ok(len(jejak) == 1, "revaluasi retur antar-PT MENULIS satu jejak nilai",
           f"{len(jejak)} jejak")
        j = jejak[0] if jejak else {}
        ok(j.get("reason") == "interco_return_revalue" and j.get("actor") == "Penguji POC",
           "jejak menyebut ALASAN & AKTOR-nya (bukan 'update')",
           f"{j.get('reason')} · {j.get('actor')}")
        ok(abs(float(j.get("delta_value") or 0)) > 0 and j.get("reason_label"),
           "jejak menyebut selisih NILAI roll + kalimat manusianya",
           f"delta={j.get('delta_value')} · {j.get('reason_label')}")
        adm_kanda = login("admin@kainnusantara.id", entity="ent_kanda")
        try:
            r = adm_kanda.get(f"/api/inventory/rolls/{roll_id}/cost-history")
            ok(r.status_code == 200 and (r.json().get("count") or 0) >= 1,
               "endpoint riwayat nilai roll mengembalikan jejaknya",
               f"HTTP {r.status_code}")
        finally:
            adm_kanda.close()
        sales_lain = login("sales@kainnusantara.id", entity="ent_ksc")
        try:
            r = sales_lain.get(f"/api/inventory/rolls/{roll_id}/cost-history")
            ok(r.status_code in (403, 404),
               "roll badan usaha lain TIDAK bisa dibaca (isolasi tak dilonggarkan)",
               f"HTTP {r.status_code}")
        finally:
            sales_lain.close()
        # Migrasi startup juga berjejak.
        from bootstrap import backfill_costing_data
        prod = db.products.find_one({"harga_pokok": {"$gt": 0}},
                                    {"_id": 0, "id": 1}) or {}
        roll_baru = f"roll_baru_{TANDA.lower()}"
        db.inventory_rolls.insert_one({
            "id": roll_baru, "roll_no": "POC-RTN-90002", "product_id": prod.get("id", ""),
            "owner_entity_id": "ent_ksc", "entity_id": "ent_ksc", "status": "available",
            "length_remaining": 5.0, "length_initial": 5.0, "unit": "yard",
            "landed_cost_total": 0.0, "_poc": TANDA})
        await backfill_costing_data()
        j2 = db.roll_cost_history.find_one({"roll_id": roll_baru}, {"_id": 0}) or {}
        ok(j2.get("reason") == "startup_backfill",
           "migrasi startup ikut berjejak — kenaikan nilai persediaan mustahil diam-diam",
           f"{j2.get('old_unit_cost')} → {j2.get('new_unit_cost')}")
        adm.close()
    finally:
        for coll, q in (("inventory_rolls", {"_poc": TANDA}),
                        ("interco_returns", {"_poc": TANDA}),
                        ("warehouse_transfers", {"_poc": TANDA}),
                        ("vendor_bills", {"_poc": TANDA}),
                        ("roll_cost_history", {"roll_id": {"$regex": TANDA.lower()}}),
                        ("journal_entries", {"source_id": {"$regex": TANDA.lower()}}),
                        ("journal_entries", {"source_type": "vendor_bill",
                                             "source_id": f"vb_{TANDA.lower()}"})):
            db[coll].delete_many(q)
        snap.restore()

    # ── N4 — nol residu (DIUKUR) ─────────────────────────────────────────────
    print(f"\n{B}▶ N4 — nol residu setelah POC (DIUKUR, bukan diklaim){X}")
    sisa = residu(base, db)
    ok(not sisa, "seluruh koleksi tersentuh kembali ke jumlah awal (INV-GATE-01)",
       f"{sisa}" if sisa else f"{len(base)} koleksi identik")
    sentinel = {"id": "poc_2026_06c_sentinel", "actor": "poc", "action": "sentinel",
                "entity_type": "gate", "entity_id": "INV-GATE-01"}
    db.audit_logs.insert_one(sentinel)
    ok("audit_logs" in residu(base, db),
       "BUKTI-MERAH: pengukur residu MEMERAH saat 1 dokumen sengaja nyangkut")
    db.audit_logs.delete_one({"_id": sentinel["_id"]})
    ok(not residu(base, db), "sentinel ikut dibersihkan (POC ini nol residu)")

    print(f"\n{B}{'=' * 78}{X}")
    print(f"  HASIL: {G}{PASS} PASS{X} · {R}{FAIL} FAIL{X} dari {PASS + FAIL} pemeriksaan")
    print(f"{B}{'=' * 78}{X}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
