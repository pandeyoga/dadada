#!/usr/bin/env python3
"""Probe alur uang end-to-end lewat API + tie-out GL.

A. SPK dari RAB → lingkup otomatis → pekerjaan diverifikasi → termin → opname → setuju
   → AP otomatis → jurnal (Dr 1-1600 / Cr 2-1100 + 2-1200) → bayar → jurnal.
B. AR: reservasi → jadwal termin → penerimaan → jurnal (Dr Bank / Cr 2-1400) → BAST → RevRec.
Semua data uji bertanda TEST_/PROBE dan dihapus di akhir (kecuali --keep).
"""
import os
import sys
import time

import requests
from dotenv import dotenv_values
from pymongo import MongoClient

ENV = dotenv_values("/app/backend/.env")
BASE = (os.environ.get("REACT_APP_BACKEND_URL")
        or dotenv_values("/app/frontend/.env")["REACT_APP_BACKEND_URL"]).rstrip("/") + "/api"
PWD = "Sipro#2026"
db = MongoClient(ENV["MONGO_URL"])[ENV["DB_NAME"]]
KEEP = "--keep" in sys.argv
FAILS = []


def login(email):
    s = requests.Session()
    r = s.post(f"{BASE}/auth/login", json={"email": email, "password": PWD}, timeout=20)
    r.raise_for_status()
    s.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
    return s


def check(cond, msg):
    print(("  [OK] " if cond else "  [FAIL] ") + msg)
    if not cond:
        FAILS.append(msg)


def gl(code, source_id=None, event=None):
    q = {"lines.account_code": code}
    if source_id:
        q["source_id"] = source_id
    dr = cr = 0
    for je in db.journal_entries.find(q, {"_id": 0, "lines": 1}):
        for ln in je["lines"]:
            if ln["account_code"] == code:
                dr += ln["debit"]
                cr += ln["credit"]
    return dr, cr


def deal_price(did):
    return int((db.deals.find_one({"id": did}, {"_id": 0, "price": 1}) or {}).get("price") or 0)


def _png(seed: int) -> bytes:
    import struct, zlib
    w = h = 8
    raw = b"".join(b"\x00" + bytes(v for x in range(w) for v in ((seed * 37 + x * 11 + y * 7) % 256, (seed * 13 + x) % 256, (y * 29 + seed) % 256)) for y in range(h))
    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")


UPLOADED = []


def verify_via_api(item_id: str, unit: dict) -> None:
    """Alur bukti asli: site mulai → foto (watermark) → ajukan + checklist lulus → PM verifikasi."""
    item = db.build_items.find_one({"id": item_id}, {"_id": 0})
    label = f"{unit['code']} · {item['step_code']}"
    if item["status"] == "blocked":
        # Gerbang (mis. masa curing) diterobos PM dengan alasan — tercatat di jejak audit.
        r = pm.post(f"{BASE}/build/items/{item_id}/override",
                    json={"reason_code": "schedule_recovery", "note": "Probe: pemulihan jadwal, curing sudah cukup di lapangan"})
        check(r.status_code == 200, f"{label} gerbang diterobos PM dengan alasan ({r.status_code} {r.text[:120] if r.status_code != 200 else ''})")
        item = db.build_items.find_one({"id": item_id}, {"_id": 0})
    r = site.post(f"{BASE}/build/items/{item_id}/start")
    check(r.status_code == 200, f"{label} mulai dikerjakan ({r.status_code} {r.text[:120] if r.status_code != 200 else ''})")
    photos = []
    for k in range(int(item.get("min_photos") or 1)):
        seed = int(time.time() * 1000) % 100000 + k
        r = site.post(f"{BASE}/files/upload", files={"file": (f"probe_{seed}.png", _png(seed), "image/png")},
                      data={"owner_type": "build_item", "owner_id": item_id, "watermark": f"PROBE {label}"})
        if r.status_code == 200:
            photos.append(r.json()["data"]["id"])
            UPLOADED.append(r.json()["data"]["id"])
    check(len(photos) == int(item.get("min_photos") or 1), f"{label} {len(photos)} foto bukti terunggah (min {item.get('min_photos')})")
    r = site.post(f"{BASE}/build/items/{item_id}/submit", json={
        "note": f"Probe: pekerjaan {item['step_code']} selesai sesuai spesifikasi",
        "photo_file_ids": photos,
        "checklist": [{"code": c["code"], "result": "pass"} for c in (item.get("checklist") or [])]})
    check(r.status_code == 200, f"{label} diajukan dengan bukti ({r.status_code} {r.text[:160] if r.status_code != 200 else ''})")
    r = site.post(f"{BASE}/build/items/{item_id}/verify", json={"note": "coba verifikasi sendiri"})
    check(r.status_code == 403, f"{label} pengaju tidak boleh memverifikasi sendiri ({r.status_code})")
    r = pm.post(f"{BASE}/build/items/{item_id}/verify", json={"note": "Probe: diverifikasi PM"})
    check(r.status_code == 200, f"{label} diverifikasi PM ({r.status_code} {r.text[:160] if r.status_code != 200 else ''})")
    fresh = db.build_items.find_one({"id": item_id}, {"_id": 0, "status": 1, "verified_by": 1, "evidence": 1})
    check(fresh["status"] == "done" and fresh["verified_by"] == "pm@sipro.co.id" and len(fresh.get("evidence") or []) >= len(photos),
          f"{label} done + verified_by PM + {len(fresh.get('evidence') or [])} bukti tersimpan")


def wait_events():
    for _ in range(30):
        if not db.events.count_documents({"status": {"$in": ["pending", None]}}):
            return
        time.sleep(0.5)


su, fin, pm, site, sales, owner = (login(e) for e in (
    "superadmin@sipro.co.id", "finance@sipro.co.id", "pm@sipro.co.id", "site@sipro.co.id",
    "sales@sipro.co.id", "owner@sipro.co.id"))

# ============================================================ A. SPK → AP → GL
print("\nA. SPK dari RAB → opname → AP → GL")
proj = db.projects.find_one({}, {"_id": 0, "id": 1, "name": 1})
pid = proj["id"]
# unit yang punya jadwal bangun & item belum dipakai SPK lain
used = {r["build_item_id"] for r in db.spk_scope_items.find({}, {"build_item_id": 1})}
unit = None
for sch in db.build_schedules.find({"project_id": pid}, {"_id": 0, "unit_id": 1}):
    items = list(db.build_items.find({"unit_id": sch["unit_id"]}, {"_id": 0, "id": 1, "step_code": 1, "status": 1}).sort("order", 1))
    if items and not any(i["id"] in used for i in items) and items[0]["status"] in ("ready", "in_progress"):
        unit = db.units.find_one({"id": sch["unit_id"]}, {"_id": 0})
        break
assert unit, "tidak ada unit ber-jadwal yang bebas SPK"
steps = [i["step_code"] for i in db.build_items.find({"unit_id": unit["id"]}, {"_id": 0, "step_code": 1}).sort("order", 1)][:3]
orig_items = list(db.build_items.find({"unit_id": unit["id"]}))          # dokumen utuh untuk dipulihkan
orig_sched = db.build_schedules.find_one({"unit_id": unit["id"]})
tcode = unit["unit_type_code"]
print(f"  unit {unit['code']} tipe {tcode} langkah {steps}")
tpl_prev = db.rab_templates.find_one({"kind": "unit_type", "ref_code": tcode}, {"_id": 0})
items = [{"code": f"P{i+1:02d}", "description": f"TEST_PROBE {s}", "category": "struktur",
          "qty": 1, "unit_price": 10_000_000 * (i + 1), "step_code": s} for i, s in enumerate(steps)]
r = su.put(f"{BASE}/rab/templates/unit_type/{tcode}", json={"items": items})
check(r.status_code == 200, f"RAB tipe {tcode} disimpan ({len(items)} baris ber-step)")

sub = su.get(f"{BASE}/subcon/subcontractors", params={"active": "true"}).json()["data"][0]
d = su.post(f"{BASE}/rab/spk-draft", json={"project_id": pid, "mode": "unit", "unit_ids": [unit["id"]]}).json()["data"]
lines = [ln for u in d["units"] for ln in u["lines"]]
r = su.post(f"{BASE}/subcon/spk/from-rab", json={
    "subcontractor_id": sub["id"], "project_id": pid, "title": "TEST_PROBE SPK unit",
    "spk_kind": "unit", "unit_ids": [unit["id"]], "lines": lines, "retention_pct": 5,
    "contract_value": 1, "scope": "TEST_PROBE", "maintenance_days": 0, "start_date": "2026-06-01", "end_date": "2026-06-02"})
check(r.status_code == 200, f"SPK dari RAB terbit: {r.status_code} {r.text[:200] if r.status_code != 200 else ''}")
spk = r.json()["data"]
cv = spk["contract_value"]
check(cv == sum(i["unit_price"] for i in items), f"nilai kontrak SPK = Σ RAB ({cv:,})")
check(spk["auto_scope"]["added"] == len(steps), f"lingkup otomatis {spk['auto_scope']}")
su.post(f"{BASE}/subcon/spk/{spk['id']}/status", json={"status": "active", "note": "probe"})

# belum ada pekerjaan terverifikasi → termin ditolak
r = site.post(f"{BASE}/subcon/claims", json={"spk_id": spk["id"], "period": "T1"})
check(r.status_code == 400, f"termin tanpa pekerjaan terverifikasi ditolak ({r.status_code})")

# verifikasi 2 dari 3 pekerjaan LEWAT API: mandor mulai → unggah foto → ajukan + checklist → PM verifikasi
scope = sorted(db.spk_scope_items.find({"spk_id": spk["id"]}, {"_id": 0}), key=lambda r: r.get("order") or 0)
ver = scope[:2]
for row in ver:
    verify_via_api(row["build_item_id"], unit)
pv = su.get(f"{BASE}/subcon/spk/{spk['id']}/opname")
gross_exp = sum(s["value"] for s in ver)
if pv.status_code == 200:
    check(pv.json()["data"]["gross"] == gross_exp, f"opname preview gross = Σ terverifikasi ({gross_exp:,})")
else:
    print(f"  (preview endpoint {pv.status_code} — dilewati)")

r = site.post(f"{BASE}/subcon/claims", json={"spk_id": spk["id"], "period": "T1"})
check(r.status_code == 200, f"termin item-based diajukan ({r.status_code} {r.text[:150] if r.status_code != 200 else ''})")
claim = r.json()["data"]
check(claim["basis"] == "items" and claim["gross_est"] == gross_exp, f"gross_est termin = {claim['gross_est']:,}")
# opname: keluarkan 1 baris
drop = claim["lines"][1]["scope_item_id"]
r = pm.post(f"{BASE}/subcon/claims/{claim['id']}/verify",
            json={"exclude": [drop], "reason": "volume kurang 4 m2 (probe)"})
check(r.status_code == 200, f"opname mengurangi 1 baris ({r.status_code})")
gross_final = claim["lines"][0]["value"]
r = fin.post(f"{BASE}/subcon/claims/{claim['id']}/approve")
check(r.status_code == 200, f"termin disetujui finance ({r.status_code} {r.text[:150] if r.status_code != 200 else ''})")
claim = r.json()["data"]
check(claim["gross"] == gross_final, f"gross termin final = {gross_final:,}")
ret_exp = round(gross_final * 5 / 100)
check(claim["retention_held"] == ret_exp and claim["net"] == gross_final - ret_exp,
      f"retensi 5% = {ret_exp:,}, net = {gross_final - ret_exp:,}")
bill = db.ap_invoices.find_one({"id": claim["ap_bill_id"]}, {"_id": 0})
check(bill and bill["status"] == "approved" and bill["claimed"] == gross_final,
      "AP otomatis terbit & disetujui dari termin")
wait_events()
je = db.journal_entries.find_one({"source_type": "ap_bill", "source_id": bill["id"]}, {"_id": 0})
check(bool(je), "jurnal AP disetujui ada")
if je:
    m = {ln["account_code"]: (ln["debit"], ln["credit"]) for ln in je["lines"]}
    check(m.get("1-1600") == (gross_final, 0), f"Dr 1-1600 WIP {gross_final:,}")
    check(m.get("2-1100") == (0, gross_final - ret_exp), f"Cr 2-1100 Utang Usaha {gross_final - ret_exp:,}")
    check(m.get("2-1200") == (0, ret_exp), f"Cr 2-1200 Utang Retensi {ret_exp:,}")
    check(je["total_debit"] == je["total_credit"], "jurnal seimbang")
ret = db.subcon_retentions.find_one({"ap_bill_id": bill["id"]}, {"_id": 0})
check(bool(ret) and ret["amount"] == ret_exp, "baris retensi terdaftar")
spk_now = su.get(f"{BASE}/subcon/spk/{spk['id']}").json()["data"]
check(spk_now["progress_pct"] == round(gross_exp / cv * 100), f"progres SPK = terverifikasi/kontrak ({spk_now['progress_pct']}%)")
check(spk_now.get("billed_pct") == round(gross_final / cv * 100), f"billed_pct = {spk_now.get('billed_pct')}%")
# baris yang dikeluarkan kembali claimable
row = db.spk_scope_items.find_one({"id": drop}, {"_id": 0})
check(row["claim_id"] is None and row["pending_claim_id"] is None, "baris yang dikeluarkan opname dilepas lagi")

# bayar sebagian + lunas
net = bill["net"]
r = fin.post(f"{BASE}/finance/ap/bills/{bill['id']}/pay", json={"amount": net // 2, "note": "probe 1"})
check(r.status_code == 200, f"bayar AP sebagian ({r.status_code})")
r = fin.post(f"{BASE}/finance/ap/bills/{bill['id']}/pay", json={"amount": net - net // 2, "note": "probe 2"})
check(r.status_code == 200 and r.json()["data"]["status"] == "paid", "bayar AP lunas")
r = fin.post(f"{BASE}/finance/ap/bills/{bill['id']}/pay", json={"amount": 1, "note": "lebih"})
check(r.status_code == 400, "bayar melebihi tagihan ditolak")
wait_events()
dr, cr = gl("2-1100", source_id=bill["id"])
check(dr == cr == net, f"2-1100 tagihan ini: kredit {cr:,} = debit {dr:,} (lunas)")
paid_je = list(db.journal_entries.find({"source_id": bill["id"], "memo": {"$regex": "Pembayaran"}}, {"_id": 0}))
bank_cr = sum(ln["credit"] for j in paid_je for ln in j["lines"] if ln["account_code"].startswith("1-12") or ln["account_code"].startswith("1-11"))
check(bank_cr == net, f"kas/bank keluar = net {net:,} (aktual {bank_cr:,}; akun {[ln['account_code'] for j in paid_je for ln in j['lines']]})")

# termin ke-2: baris ke-3 diverifikasi + baris yang tadi dikeluarkan
verify_via_api(scope[2]["build_item_id"], unit)
r = site.post(f"{BASE}/subcon/claims", json={"spk_id": spk["id"], "period": "T2"})
check(r.status_code == 200 and r.json()["data"]["gross_est"] == scope[1]["value"] + scope[2]["value"],
      "termin 2 = baris dikeluarkan + baris baru terverifikasi")
c2 = r.json()["data"]
r = fin.post(f"{BASE}/subcon/claims/{c2['id']}/approve")
check(r.status_code == 200, "termin 2 disetujui (tanpa opname, langsung dari submitted)")
wait_events()
spk_now = su.get(f"{BASE}/subcon/spk/{spk['id']}").json()["data"]
check(spk_now["progress_pct"] == 100 and spk_now["billed_pct"] == 100, "SPK 100% terverifikasi & tertagih")
r = site.post(f"{BASE}/subcon/claims", json={"spk_id": spk["id"], "period": "T3"})
check(r.status_code == 400, "termin 3 ditolak — tidak ada pekerjaan tersisa (anti bayar ganda)")

# pencairan retensi termin 1 (masa pemeliharaan 0 hari)
ret_id = ret["id"]
dr0, cr0 = gl("2-1200")
r = pm.post(f"{BASE}/subcon/retentions/{ret_id}/request-release", json={"reason": "masa pemeliharaan selesai (probe)"})
check(r.status_code == 200, f"pengajuan pencairan retensi ({r.status_code} {r.text[:200] if r.status_code != 200 else ''})")
r = owner.post(f"{BASE}/subcon/retentions/{ret_id}/release", json={"reason": "disetujui finance (probe)"})
check(r.status_code == 200, f"pencairan retensi ({r.status_code} {r.text[:200] if r.status_code != 200 else ''})")
wait_events()
dr1, cr1 = gl("2-1200")
check((cr0 - dr0) - (cr1 - dr1) == ret_exp, f"2-1200 turun {ret_exp:,} setelah pencairan")
b0 = db.ap_invoices.find_one({"id": bill["id"]}, {"_id": 0, "retention_released": 1})
check(b0.get("retention_released") is True, "tagihan termin asal ditandai retention_released")
rel_bill = db.ap_invoices.find_one({"retention_id": ret_id}, {"_id": 0})
check(rel_bill and rel_bill["status"] == "approved" and rel_bill["net"] == ret_exp, "tagihan AP pencairan retensi terbit (approved)")
r = fin.post(f"{BASE}/finance/ap/bills/{rel_bill['id']}/pay", json={"amount": ret_exp, "note": "bayar retensi probe"})
check(r.status_code == 200 and r.json()["data"]["status"] == "paid", "retensi dibayar lunas")
wait_events()
summ = fin.get(f"{BASE}/finance/summary").json()
summ = summ.get("data", summ)
dr, cr = gl("2-1200")
check(summ["ap_retention_held"] == cr - dr, f"ringkasan ap_retention_held {summ['ap_retention_held']:,} = GL 2-1200 {cr - dr:,}")
dr, cr = gl("2-1100")
check(summ["ap_outstanding"] == cr - dr, f"ringkasan ap_outstanding {summ['ap_outstanding']:,} = GL 2-1100 {cr - dr:,}")

# ============================================================ B. AR → penerimaan → BAST
print("\nB. AR — reservasi → termin → penerimaan → GL → BAST")
free = db.units.find_one({"project_id": pid, "status": "available"}, {"_id": 0})
active = {d["lead_id"] for d in db.deals.find({"status": {"$nin": ["cancelled", "expired", "lost", "released"]}}, {"lead_id": 1})}
lead = db.leads.find_one({"id": {"$nin": list(active)}}, {"_id": 0})
addon = db.addon_items.find_one({"active": True, "pricing_mode": "lump_sum"}, {"_id": 0})
r = sales.post(f"{BASE}/deals/reserve", json={"lead_id": lead["id"], "unit_id": free["id"], "notes": "TEST_PROBE", "addons": [{"code": addon["code"], "qty": 1}]})
if r.status_code != 200:
    r = su.post(f"{BASE}/deals/reserve", json={"lead_id": lead["id"], "unit_id": free["id"], "notes": "TEST_PROBE", "addons": [{"code": addon["code"], "qty": 1}]})
check(r.status_code == 200, f"reservasi unit {free['code']} ({r.status_code} {r.text[:200] if r.status_code != 200 else ''})")
deal = r.json()["data"] if r.status_code == 200 else None
deal_id = (deal or {}).get("id") or (deal or {}).get("deal", {}).get("id")
if deal_id:
    r = su.post(f"{BASE}/deals/{deal_id}/book", json={"note": "probe"})
    print(f"  booked → {r.status_code} {r.text[:120] if r.status_code != 200 else ''}")
    wait_events()
    inv = db.ar_invoices.find_one({"deal_id": deal_id}, {"_id": 0})
    check(bool(inv), "jadwal AR terbit saat booked")
    if inv:
        check(inv.get("addon_total", 0) == addon["unit_price"], f"AR memuat baris add-on {addon['unit_price']:,} (total {inv['total']:,} vs harga deal {deal_price(deal_id):,})")
        # RAB HPP unit tersedia? (tipe unit bebas ini)
        wip0 = gl("1-1600")
        first = inv["items"][0]
        amt = first["amount"] - first.get("paid_amount", 0)
        cl0 = (db.contract_liabilities.find_one({"deal_id": deal_id}) or {}).get("balance", 0)
        dr0, cr0 = gl("2-1400")
        r = fin.post(f"{BASE}/finance/ar/receipts", json={"deal_id": deal_id, "amount": amt, "method": "transfer", "note": "probe"})
        check(r.status_code == 200, f"penerimaan termin 1 {amt:,} ({r.status_code} {r.text[:150] if r.status_code != 200 else ''})")
        wait_events()
        dr1, cr1 = gl("2-1400")
        check((cr1 - dr1) - (cr0 - dr0) == amt, f"2-1400 naik {amt:,} (aktual {(cr1 - dr1) - (cr0 - dr0):,})")
        rc = db.receipts.find_one({"deal_id": deal_id, "note": "probe"}, {"_id": 0})
        je = db.journal_entries.find_one({"source_type": "receipt", "source_id": rc["id"]}, {"_id": 0})
        check(bool(je), "jurnal penerimaan menunjuk kuitansi")
        if je:
            bank = [ln for ln in je["lines"] if ln["debit"]]
            check(bank and bank[0]["debit"] == amt and bank[0]["account_type"] == "asset", f"Dr kas/bank {bank[0]['account_code']} {amt:,}")
        # overpay ditolak
        inv = db.ar_invoices.find_one({"deal_id": deal_id}, {"_id": 0})
        r = fin.post(f"{BASE}/finance/ar/receipts", json={"deal_id": deal_id, "amount": inv["outstanding"] + 5_000_000, "method": "transfer"})
        check(r.status_code == 400, "kelebihan bayar tanpa izin titipan ditolak")
        r = fin.post(f"{BASE}/finance/ar/receipts", json={"deal_id": deal_id, "amount": inv["outstanding"] + 5_000_000,
                                                          "method": "transfer", "allow_overpay": True, "note": "probe lunas"})
        check(r.status_code == 200 and r.json()["data"]["paid_off"], "pelunasan + kelebihan 5jt → titipan")
        wait_events()
        dep = db.customer_deposits.find_one({"deal_id": deal_id}, {"_id": 0})
        check(dep and dep["balance"] == 5_000_000, "saldo titipan 5jt")
        cl = db.contract_liabilities.find_one({"deal_id": deal_id})
        check(cl["balance"] == inv["total"], f"kewajiban kontrak = total AR {inv['total']:,} (aktual {cl['balance']:,})")
        r = fin.post(f"{BASE}/finance/ar/{deal_id}/deposit/refund", json={"amount": 5_000_000, "note": "probe refund"})
        check(r.status_code == 200, f"refund titipan ({r.status_code})")
        wait_events()
        # BAST
        r = fin.post(f"{BASE}/finance/ar/{deal_id}/bast")
        check(r.status_code == 200, f"BAST/RevRec ({r.status_code} {r.text[:150] if r.status_code != 200 else ''})")
        wait_events()
        rr = db.revenue_recognitions.find_one({"deal_id": deal_id}, {"_id": 0})
        je = db.journal_entries.find_one({"source_type": "revrec", "source_id": (rr or {}).get("id")}, {"_id": 0})
        check(bool(je), "jurnal RevRec ada")
        if je:
            m = {ln["account_code"]: (ln["debit"], ln["credit"]) for ln in je["lines"]}
            print(f"    revrec lines: {m}  revenue={rr['revenue']:,} cleared={rr['contract_liability_cleared']:,} cogs={rr['cogs']:,}")
            check(m.get("4-1100", (0, 0))[1] == rr["revenue"], "Cr 4-1100 = pendapatan")
            check(m.get("2-1400", (0, 0))[0] == rr["contract_liability_cleared"], "Dr 2-1400 = kewajiban kontrak yang dilepas")
            check(rr["revenue"] == inv["total"], f"pendapatan = total AR {inv['total']:,} (aktual {rr['revenue']:,}) — bila beda, harga deal ≠ AR")
            check("1-1300" not in m, "tidak ada piutang sisa (AR sudah lunas) → 1-1300 tidak muncul")
            check(je["total_debit"] == je["total_credit"], "jurnal RevRec seimbang (dengan add-on)")
            print(f"    cogs_source={rr.get('cogs_source')} rab_hpp={rr.get('rab_hpp')}")
            rab_row = next((u for u in su.get(f"{BASE}/rab/projects/{pid}/summary").json()["data"]["per_unit"] if u["unit_id"] == free["id"]), {})
            if rab_row.get("rab_type"):
                check(rr["cogs_source"] == "rab" and rr["cogs"] == rab_row["hpp"], f"HPP = HPP RAB unit {rab_row['hpp']:,}")
            else:
                check(rr["cogs_source"] == "estimate_70pct", "tipe tanpa RAB → HPP estimasi 70% ditandai")
            wdr, wcr = gl("1-1600")
            check(wdr - wcr >= 0, f"WIP 1-1600 tidak negatif (saldo {wdr - wcr:,})")
            acc = m.get("2-1700")
            print(f"    akrual HPP 2-1700 pada jurnal ini: {acc}")

# ============================================================ C. tie-out global
print("\nC. Tie-out GL")
tb = su.get(f"{BASE}/gl/trial-balance").json()
tbd = tb.get("data", tb)
check(tbd.get("balanced"), f"neraca saldo seimbang (D {tbd.get('total_debit', 0):,} / K {tbd.get('total_credit', 0):,})")
bs = su.get(f"{BASE}/gl/balance-sheet").json()
bsd = bs.get("data", bs)
check(bsd.get("balanced"), f"neraca seimbang: aset {bsd.get('total_assets', 0):,} vs L+E+NI {bsd.get('total_liab_equity', 0):,}")
ap_open = sum(b["net"] - b["paid"] for b in db.ap_invoices.find({"status": {"$in": ["approved", "partial"]}}))
dr, cr = gl("2-1100")
check(cr - dr == ap_open, f"2-1100 = Σ AP disetujui belum lunas ({ap_open:,} vs GL {cr - dr:,})")
ret_open = sum(r["amount"] for r in db.subcon_retentions.find({"state": {"$ne": "released"}}))
ret_bills = sum(b.get("retention_held", 0) for b in db.ap_invoices.find({"status": {"$in": ["approved", "partial", "paid"]}, "retention_released": {"$ne": True}}))
dr, cr = gl("2-1200")
print(f"    2-1200 GL {cr - dr:,} | Σ subcon_retentions held {ret_open:,} | Σ ap_invoices.retention_held belum lepas {ret_bills:,}")
check(cr - dr == ret_bills, "2-1200 = Σ retensi tagihan disetujui belum dilepas")
cl = sum(c["balance"] for c in db.contract_liabilities.find({"recognized": {"$ne": True}}))
dr, cr = gl("2-1400")
check(cr - dr == cl, f"2-1400 = Σ kewajiban kontrak ({cl:,} vs {cr - dr:,})")
ap_sum = fin.get(f"{BASE}/finance/summary").json()
apd = ap_sum.get("data", ap_sum)
print(f"    finance/summary ap_retention_held={apd.get('ap_retention_held'):,} ap_outstanding={apd.get('ap_outstanding'):,}")

# ============================================================ D. pengajuan vendor_payment → AP
print("\nD. Pengajuan keuangan vendor_payment ↔ tagihan AP")
r = fin.post(f"{BASE}/finance/ap/bills", json={"vendor": "TEST_PROBE Vendor", "project_id": pid, "claimed": 12_000_000,
                                               "retention_pct": 0, "note": "TEST_PROBE tagihan vendor"})
vbill = r.json()["data"]
fin.post(f"{BASE}/finance/ap/bills/{vbill['id']}/approve")
wait_events()
exp0 = gl("6-1300")
r = pm.post(f"{BASE}/fund-requests", json={"type": "vendor_payment", "title": "TEST_PROBE bayar vendor", "amount": 20_000_000,
                                           "ap_bill_id": vbill["id"], "category": "lainnya"})
check(r.status_code == 400, f"pengajuan melebihi sisa tagihan ditolak ({r.status_code})")
r = pm.post(f"{BASE}/fund-requests", json={"type": "vendor_payment", "title": "TEST_PROBE bayar vendor", "amount": 12_000_000,
                                           "ap_bill_id": vbill["id"], "category": "lainnya"})
check(r.status_code == 200, f"pengajuan vendor_payment menunjuk tagihan AP ({r.status_code} {r.text[:150] if r.status_code != 200 else ''})")
freq = r.json()["data"]
check(freq.get("payee_name") == "TEST_PROBE Vendor" and freq.get("ap_bill_id") == vbill["id"], "penerima & tagihan terisi dari AP")
r = site.post(f"{BASE}/fund-requests", json={"type": "vendor_payment", "title": "TEST_PROBE dobel", "amount": 1_000_000,
                                             "ap_bill_id": vbill["id"], "category": "lainnya"})
check(r.status_code == 400, f"pengajuan kedua atas tagihan yang sama ditolak ({r.status_code})")
r = fin.post(f"{BASE}/fund-requests/{freq['id']}/approve", json={"note": "ok"})
check(r.status_code == 200, "pengajuan disetujui finance")
r = fin.post(f"{BASE}/fund-requests/{freq['id']}/disburse", json={"source": "bank", "note": "cair probe"})
check(r.status_code == 200, f"pencairan ({r.status_code} {r.text[:150] if r.status_code != 200 else ''})")
wait_events()
vb = db.ap_invoices.find_one({"id": vbill["id"]}, {"_id": 0})
check(vb["status"] == "paid" and vb["paid"] == 12_000_000, "tagihan AP lunas lewat pencairan pengajuan")
check(gl("6-1300") == exp0, "tidak ada beban baru (6-1300 tidak berubah) — tidak dicatat dua kali")
check(not db.journal_entries.find_one({"source_type": "fund_request", "source_id": freq["id"]}), "tidak ada jurnal pengajuan terpisah")
dr, cr = gl("2-1100", source_id=vbill["id"])
check(dr == cr == 12_000_000, "2-1100 tagihan vendor: kredit = debit (lunas)")
fr_doc = db.fund_requests.find_one({"id": freq["id"]}, {"_id": 0})
check(fr_doc.get("status") == "settled" and fr_doc.get("ap_payment_id") and fr_doc.get("journal_ids"), "pengajuan settled + jejak pembayaran AP & jurnal")
rec = fin.get(f"{BASE}/finance/reconcile").json()["data"]
check(rec["ok"] and all(c["ok"] for c in rec["checks"]), f"GET /finance/reconcile ok (failed={rec['failed']})")
hpp = fin.get(f"{BASE}/finance/hpp-unit", params={"project_id": pid}).json()["data"]
check(any(r_["unit_id"] == unit["id"] and r_["billed"] == cv for r_ in hpp["rows"]), f"laporan HPP unit: {unit['code']} ditagih = kontrak {cv:,}")

# ============================================================ bersih-bersih
if not KEEP:
    print("\nbersih-bersih data probe…")
    if deal_id:
        su.delete(f"{BASE}/deals/{deal_id}", params={"reason": "hapus data probe otomatis"})
    ids = [c["id"] for c in db.progress_claims.find({"spk_id": spk["id"]})]
    bills = [c["ap_bill_id"] for c in db.progress_claims.find({"spk_id": spk["id"]}) if c.get("ap_bill_id")]
    rets = list(db.subcon_retentions.find({"spk_id": spk["id"]}))
    bills += [r["release_bill_id"] for r in rets if r.get("release_bill_id")]
    db.journal_entries.delete_many({"source_id": {"$in": bills + [r["id"] for r in rets]}})
    db.payments_out.delete_many({"bill_id": {"$in": bills}})
    db.subcon_retentions.delete_many({"spk_id": spk["id"]})
    db.ap_invoices.delete_many({"id": {"$in": bills}})
    db.progress_claims.delete_many({"spk_id": spk["id"]})
    for it in orig_items:
        db.build_items.replace_one({"id": it["id"]}, it)
    if orig_sched:
        db.build_schedules.replace_one({"id": orig_sched["id"]}, orig_sched)
    db.files.delete_many({"id": {"$in": UPLOADED}})
    db.file_blobs.delete_many({"file_id": {"$in": UPLOADED}})
    db.build_submissions.delete_many({"item_id": {"$in": [i["id"] for i in orig_items]}, "note": {"$regex": "^Probe"}})
    db.spk_scope_items.delete_many({"spk_id": spk["id"]})
    db.spk.delete_one({"id": spk["id"]})
    if tpl_prev:
        db.rab_templates.replace_one({"kind": "unit_type", "ref_code": tcode}, tpl_prev)
    else:
        db.rab_templates.delete_one({"kind": "unit_type", "ref_code": tcode})
    db.rab_template_versions.delete_many({"ref_code": tcode, "items.description": {"$regex": "TEST_PROBE"}})
    db.events.delete_many({"data.label": {"$regex": "TEST_PROBE"}})
    db.journal_entries.delete_many({"source_id": vbill["id"]})
    db.payments_out.delete_many({"bill_id": vbill["id"]})
    db.ap_invoices.delete_one({"id": vbill["id"]})
    db.fund_requests.delete_many({"title": {"$regex": "TEST_PROBE"}})

print("\n" + ("SEMUA LULUS" if not FAILS else f"{len(FAILS)} GAGAL:\n- " + "\n- ".join(FAILS)))
sys.exit(1 if FAILS else 0)
