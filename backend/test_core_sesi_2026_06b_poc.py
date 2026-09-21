#!/usr/bin/env python3
"""POC — SESI 2026-06 (lanjutan ke-4): **selisih Kanda ditutup · tuduhan bisa diklik ·
lonceng berhalaman · papan keuangan**

KENAPA POC INI ADA
==================
Keempat pekerjaan sesi ini berjenis "salah tetapi TENANG": tidak ada galat, tidak ada
layar merah — hanya nilai yang hilang tanpa jurnal, tuduhan yang berhenti sebagai teks,
angka lencana yang tak bisa dibuktikan, dan uang yang tertahan tanpa satu pun papan yang
menyebutnya. Kelas seperti itu hanya bisa dijaga POC yang MEMBUAT keadaannya.

YANG DIBUKTIKAN
---------------
H1 **INV-GL-DRIFT ditutup di akarnya.** `on_return_task_executed` dulu membaca nilai
   roll HANYA dari `unit_cost`, sementara rekonsiliasi persediaan memakai
   `unit_cost or base_unit_cost`. Roll `RTN-00001` (Rp 90.000/unit tersimpan di
   `base_unit_cost`) karena itu menghasilkan `cost_back`/`carry_out` = 0 → jurnal
   `interco_return:…:goods_in` DILEWATI padahal barangnya benar-benar masuk gudang
   penjual: subledger naik Rp 900.000, GL 1-1300 tidak. POC: tanam kondisi itu,
   jalankan jembatannya, TUNTUT dua jurnal terbit dan drift kedua buku kembali nol.
H2 **Tuduhan bisa diklik.** Tiap `suspects[]` di `/api/gl/inventory-drift-explain`
   wajib membawa `ref` (roll / jurnal / akun) berisi id & kata kunci pencarian —
   sebelum ini kalimatnya menyebut nomor roll lalu berhenti di teks.
H3 **Lonceng berhalaman.** `/api/notifications?page=&page_size=` wajib menjawab
   envelope {items,total,page,has_more}, halaman ke-2 wajib berisi baris LAIN, dan
   `total` wajib >= jumlah yang belum dibaca (angka lencana bisa dibuktikan). Bentuk
   array telanjang TANPA parameter halaman tetap dipertahankan (kompatibel mundur),
   dan ISOLASI tidak dilonggarkan: sales PT lain tetap nol.
H4 **Papan Keuangan.** `/api/home/finance` memberi papan kontrabon (ACC · verifikasi ·
   sengketa) + tagihan supplier, angkanya IDENTIK dengan Pusat Persetujuan
   (`approval_backlog_service`, INV-HOME-01), dan badan usaha di luar penugasan
   dijawab 403.
H5 **NOL RESIDU** (INV-GATE-01) — diukur, plus bukti-merah pengukurnya sendiri.

Usage:  python backend/test_core_sesi_2026_06b_poc.py
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
           "notifications", "audit_logs", "sessions", "login_attempts"]
TANDA = "POC_SESI_2026_06B"
NILAI_UJI = 900_000.0        # sama besarnya dengan drift `ent_kanda` yang dilaporkan
PHYS = ["available", "reserved", "committed", "picked", "packed", "quarantine", "hold"]

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


def doc_counts(db, colls=None):
    return {c: db[c].count_documents({}) for c in (colls or TOUCHED)}


def residu(base, db):
    now = doc_counts(db)
    return {c: (base[c], now[c]) for c in base if base[c] != now[c]}


def drift_of(db, eid):
    rolls = db.inventory_rolls.find(
        {"owner_entity_id": eid, "status": {"$in": PHYS}},
        {"_id": 0, "length_remaining": 1, "unit_cost": 1, "base_unit_cost": 1})
    sub = sum(float(r.get("length_remaining") or 0)
              * float(r.get("unit_cost") or r.get("base_unit_cost") or 0) for r in rolls)
    gl = 0.0
    for je in db.journal_entries.find(
            {"entity_id": eid, "lines.account_code": "1-1300", "status": {"$ne": "void"}},
            {"_id": 0, "lines": 1}):
        for line in je.get("lines", []):
            if line.get("account_code") == "1-1300":
                gl += float(line.get("debit") or 0) - float(line.get("credit") or 0)
    return round(sub - gl, 2)


def papan_of(payload, key):
    for b in (payload.get("waiting_boards") or []):
        if b.get("key") == key:
            return b
    return {}


async def main() -> int:  # noqa: PLR0915
    print(f"{B}{'=' * 78}\n  POC SESI 2026-06b (selisih Kanda · tuduhan · lonceng · "
          f"papan keuangan)  ·  {BASE}\n{'=' * 78}{X}")
    from pymongo import MongoClient
    db = MongoClient(os.environ["MONGO_URL"], serverSelectionTimeoutMS=4000)[
        os.environ["DB_NAME"]]
    db.command("ping")

    from services import interco_return_service as icret

    base = doc_counts(db)
    snap = DbSnapshot(db, ["audit_logs", "sessions", "login_attempts",
                           "interco_transactions", "interco_returns",
                           "journal_entries", "interco_accounts",
                           "intercompany_eliminations", "purchase_orders"])
    snap.take()
    dibuat_roll = dibuat_trf = dibuat_icr = ""
    try:
        adm = login("admin@kainnusantara.id", entity="all")

        # ── H1 — barang retur antar-PT MASUK harus selalu berjurnal ───────────
        print(f"\n{B}▶ H1 — INV-GL-DRIFT: roll retur masuk gudang penjual WAJIB berjurnal{X}")
        ent_penjual, ent_pembeli = "ent_kanda", "ent_ksc"
        rp = f"icrp_{TANDA.lower()}"
        # Transaksi ASAL dipinjam dari data demo yang memang lengkap kembarannya
        # (`_refresh_origin` menuntut pasangan penjual/pembeli benar-benar ada).
        # Isinya dipulihkan lewat snapshot di akhir POC.
        asal = db.interco_returns.find_one(
            {"role": "returner", "origin_pair_id": {"$nin": ["", None]}},
            {"_id": 0, "origin_pair_id": 1}) or {}
        origin_pair = asal.get("origin_pair_id") or ""
        ok(bool(origin_pair),
           "ada transaksi antar-PT asal di data demo untuk dipakai POC", origin_pair)
        dibuat_trf = f"trn_{TANDA.lower()}"
        dibuat_icr = f"icr_{TANDA.lower()}"
        db.interco_returns.insert_many([
            {"id": dibuat_icr, "return_pair_id": rp, "role": "returner",
             "number": "POC/ICR-90001", "status": "approved",
             "seller_entity_id": ent_penjual, "buyer_entity_id": ent_pembeli,
             "subtotal": 1_200_000.0, "tax_amount": 0.0, "grand_total": 1_200_000.0,
             "items": [], "timeline": [], "origin_pair_id": origin_pair, "_poc": TANDA},
            {"id": dibuat_icr + "_r", "return_pair_id": rp, "role": "receiver",
             "number": "POC/ICR-90002", "status": "approved",
             "seller_entity_id": ent_penjual, "buyer_entity_id": ent_pembeli,
             "subtotal": 1_200_000.0, "tax_amount": 0.0, "grand_total": 1_200_000.0,
             "items": [], "timeline": [], "origin_pair_id": origin_pair, "_poc": TANDA}])
        transfer = {
            "id": dibuat_trf, "code": "POC/TRF-90001", "transfer_kind": "inter_entity",
            "entity_id": ent_pembeli, "source_entity_id": ent_pembeli,
            "dest_entity_id": ent_penjual, "status": "completed",
            "interco_return_pair_id": rp, "items": [], "_poc": TANDA}
        db.warehouse_transfers.insert_one(dict(transfer))
        # Kondisi cacatnya: `unit_cost` sudah 0 tetapi `base_unit_cost` MASIH bernilai —
        # persis keadaan roll `RTN-00001` yang bikin buku CV Kanda Suka berselisih.
        dibuat_roll = f"roll_{TANDA.lower()}"
        db.inventory_rolls.insert_one({
            "id": dibuat_roll, "roll_no": "POC-RTN-90001", "product_id": "prod_poc_90001",
            "owner_entity_id": ent_penjual, "entity_id": ent_penjual,
            "status": "available", "length_remaining": 10.0, "length_initial": 10.0,
            "unit": "yard", "unit_cost": 0.0, "base_unit_cost": NILAI_UJI / 10.0,
            "acquired": {"via": "transfer", "ref_id": dibuat_trf},
            "cost_basis": {"source": "sales_return", "previous_unit_cost": 0.0},
            "_poc": TANDA})

        drift_sebelum = drift_of(db, ent_penjual)
        ok(abs(drift_sebelum) >= NILAI_UJI - 1,
           "keadaan awal: roll bernilai Rp 900.000 ada di gudang penjual TANPA jurnal",
           f"Δ{drift_sebelum:,.0f}")

        hasil = await icret.on_return_task_executed(dict(transfer), "poc")
        gl = hasil.get("gl") or {}
        ok(abs(float(gl.get("goods_in") or 0) - NILAI_UJI) <= 1,
           "jurnal `goods_in` TERBIT sebesar nilai roll yang benar-benar masuk "
           "(dulu dilewati karena `unit_cost` = 0)", f"{gl}")
        ok(abs(float(gl.get("goods_out") or 0) - NILAI_UJI) <= 1,
           "jurnal `goods_out` ikut terbit di buku pembeli (dua sisi, bukan satu)")
        drift_sesudah = drift_of(db, ent_penjual)
        ok(abs(drift_sesudah) <= 1,
           "sesudah jembatan: subledger == GL 1-1300 di buku penjual (selisih LUNAS)",
           f"Δ{drift_sesudah:,.0f}")
        roll_akhir = db.inventory_rolls.find_one({"id": dibuat_roll}, {"_id": 0})
        ok(float(roll_akhir.get("unit_cost") or 0) > 0,
           "roll dinilai ulang ke harga perolehan yang dijurnalkan (bukan dinolkan diam-diam)",
           f"unit_cost={roll_akhir.get('unit_cost')}")

        # ── H1b — nol yang SENGAJA tidak boleh dihidupkan migrasi startup ─────
        print(f"\n{B}▶ H1b — HPP nol yang SENGAJA tidak boleh dihidupkan lagi saat backend start{X}")
        from bootstrap import backfill_costing_data
        prod = db.products.find_one({"harga_pokok": {"$gt": 0}},
                                    {"_id": 0, "id": 1, "harga_pokok": 1}) or {}
        roll_nol = f"roll_nol_{TANDA.lower()}"
        db.inventory_rolls.insert_one({
            "id": roll_nol, "roll_no": "POC-RTN-90002", "product_id": prod.get("id", ""),
            "owner_entity_id": ent_pembeli, "entity_id": ent_pembeli,
            "status": "available", "length_remaining": 10.0, "length_initial": 10.0,
            "unit": "yard", "unit_cost": 0.0, "base_unit_cost": 0.0,
            "condition": "damaged", "landed_cost_total": 0.0,
            "acquired": {"via": "return", "ref_id": "poc"}, "_poc": TANDA})
        await backfill_costing_data()
        sesudah = db.inventory_rolls.find_one({"id": roll_nol}, {"_id": 0})
        ok(float(sesudah.get("unit_cost") or 0) == 0.0
           and float(sesudah.get("base_unit_cost") or 0) == 0.0,
           "roll dihapus-buku (Rp 0) TETAP Rp 0 sesudah migrasi startup "
           "— dulu diisi ulang dari harga pokok produk tanpa jurnal 1-1300 "
           "(akar selisih Rp 900.000 di buku CV Kanda Suka)",
           f"unit_cost={sesudah.get('unit_cost')} base={sesudah.get('base_unit_cost')}")
        roll_kosong = f"roll_kosong_{TANDA.lower()}"
        db.inventory_rolls.insert_one({
            "id": roll_kosong, "roll_no": "POC-RTN-90003", "product_id": prod.get("id", ""),
            "owner_entity_id": ent_pembeli, "entity_id": ent_pembeli,
            "status": "available", "length_remaining": 5.0, "length_initial": 5.0,
            "unit": "yard", "landed_cost_total": 0.0, "_poc": TANDA})
        await backfill_costing_data()
        diisi = db.inventory_rolls.find_one({"id": roll_kosong}, {"_id": 0})
        ok(float(diisi.get("unit_cost") or 0) > 0,
           "roll yang BENAR-BENAR belum pernah dinilai tetap diisi migrasi "
           "(perbaikan tidak melumpuhkan gunanya)",
           f"unit_cost={diisi.get('unit_cost')}")

        # ── H2 — tuduhan bisa diklik (setiap suspect punya ALAMAT) ────────────
        print(f"\n{B}▶ H2 — penjelas selisih: tiap dugaan penyebab membawa alamat dokumen{X}")
        for eid in (ent_penjual, ent_pembeli):
            r = adm.get("/api/gl/inventory-drift-explain", params={"entity_id": eid})
            ok(r.status_code == 200, f"penjelas selisih {eid} bisa dibaca", f"{r.status_code}")
            suspects = (r.json() or {}).get("suspects") or []
            tanpa_alamat = [s["kind"] for s in suspects
                            if not ((s.get("ref") or {}).get("kind"))]
            ok(not tanpa_alamat,
               f"{eid}: {len(suspects)} tuduhan, semuanya punya `ref` yang bisa diklik",
               f"tanpa alamat: {tanpa_alamat}" if tanpa_alamat else "")
            for s in suspects:
                ref = s.get("ref") or {}
                ok(bool(ref.get("q") or ref.get("id")),
                   f"{eid}: tuduhan '{s['kind']}' menyebut dokumen yang bisa dicari",
                   f"{ref.get('kind')}:{ref.get('number') or ref.get('id')}")

        # ── H3 — lonceng berhalaman ───────────────────────────────────────────
        print(f"\n{B}▶ H3 — lonceng berhalaman: angka lencana bisa dibuktikan{X}")
        p1 = adm.get("/api/notifications", params={"page": 1, "page_size": 2}).json()
        ok(isinstance(p1, dict) and "items" in p1 and "total" in p1 and "has_more" in p1,
           "halaman 1 menjawab envelope {items,total,page,has_more}",
           f"total={p1.get('total')} has_more={p1.get('has_more')}")
        ok(len(p1.get("items") or []) <= 2, "page_size dipatuhi", f"{len(p1.get('items') or []) }")
        telanjang = adm.get("/api/notifications").json()
        ok(isinstance(telanjang, list),
           "TANPA parameter halaman bentuknya tetap array telanjang (kompatibel mundur)")
        if p1.get("has_more"):
            p2 = adm.get("/api/notifications", params={"page": 2, "page_size": 2}).json()
            id1 = {n["id"] for n in p1.get("items") or []}
            id2 = {n["id"] for n in p2.get("items") or []}
            ok(id2 and not (id1 & id2),
               "halaman 2 berisi baris LAIN (bisa ditelusuri sampai baris terakhir)",
               f"{len(id2)} baris baru")
            ok(p1.get("total") == p2.get("total"),
               "`total` konsisten antar halaman (angka lencana punya penyebut tetap)")
        belum = adm.get("/api/notifications/unread-count").json().get("count", 0)
        ok(int(p1.get("total") or 0) >= int(belum),
           "`total` >= jumlah belum dibaca — lencana selalu bisa dibuktikan dari daftar",
           f"total={p1.get('total')} belum_dibaca={belum}")
        sales_lain = login("sales3@kainnusantara.id", entity="ent_kanda")
        try:
            bocor = sales_lain.get("/api/notifications",
                                   params={"page": 1, "page_size": 50,
                                           "entity_id": "ent_ksc"})
            terlihat = [n for n in (bocor.json().get("items") or [])
                        if n.get("entity_id") == "ent_ksc"
                        and (n.get("severity") != "critical")]
            ok(not terlihat,
               "ISOLASI tetap: paginasi tidak membuka notifikasi non-kritis PT lain",
               f"{len(terlihat)} bocor" if terlihat else "")
        finally:
            sales_lain.close()

        # ── H4 — Papan Keuangan ───────────────────────────────────────────────
        print(f"\n{B}▶ H4 — Papan Keuangan: kontrabon & tagihan yang menahan uang{X}")
        fin = login("finance@kainnusantara.id", entity="ent_ksc")
        try:
            r = fin.get("/api/home/finance")
            ok(r.status_code == 200, "Meja Finance bisa membaca papannya", f"{r.status_code}")
            payload = r.json()
            kunci = [b.get("key") for b in payload.get("waiting_boards") or []]
            ok(kunci == ["contra_bon_approve", "contra_bon_verify",
                         "contra_bon_dispute", "vendor_bill"],
               "empat papan hadir dalam urutan tetap", f"{kunci}")
            backlog = adm.get("/api/approvals/backlog", params={"entity_id": "ent_ksc"})
            if backlog.status_code == 200:
                pusat = {i["key"]: i["count"]
                         for i in (backlog.json().get("all_items") or [])}
                beda = {k: (papan_of(payload, k).get("count"), pusat.get(k))
                        for k in kunci
                        if k in pusat and papan_of(payload, k).get("count") != pusat[k]}
                ok(not beda,
                   "angka papan IDENTIK dengan Pusat Persetujuan (INV-HOME-01)",
                   f"{beda}" if beda else f"{ {k: pusat.get(k) for k in kunci} }")
            for b in payload.get("waiting_boards") or []:
                ok("shown" in b and "truncated" in b,
                   f"papan {b.get('key')} membawa penanda `shown`/`truncated` "
                   "(angka judul tak boleh melebihi baris tanpa tanda)")
            tolak = fin.get("/api/home/finance", params={"entity_id": "ent_kanda"})
            ok(tolak.status_code == 403,
               "badan usaha di luar penugasan dijawab 403 (isolasi tak dilonggarkan)",
               f"{tolak.status_code}")
        finally:
            fin.close()
        adm.close()
    finally:
        db.inventory_rolls.delete_many({"_poc": TANDA})
        db.interco_returns.delete_many({"_poc": TANDA})
        db.warehouse_transfers.delete_many({"_poc": TANDA})
        db.journal_entries.delete_many({"source_type": "interco_return",
                                       "source_id": {"$regex": TANDA.lower()}})
        snap.restore()

    # ── H5 — nol residu (DIUKUR) ─────────────────────────────────────────────
    print(f"\n{B}▶ H5 — nol residu setelah POC (DIUKUR, bukan diklaim){X}")
    sisa = residu(base, db)
    ok(not sisa, "seluruh koleksi tersentuh kembali ke jumlah awal (INV-GATE-01)",
       f"{sisa}" if sisa else f"{len(base)} koleksi identik")
    sentinel = {"id": "poc_sesi_2026_06b_sentinel", "actor": "poc", "action": "sentinel",
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
