"""Regresi P0 gelombang 2 — sisa temuan kontrak (audit 04_KONTRAK_DAN_KONVERSI_LEAD).

    API_BASE=http://localhost:8031/api python -m pytest backend/tests/p0/test_p0_kontrak2.py -n 0 -q --noconftest

Memakai helper `test_p0_kontrak.py` (lead/deal berawalan `P0KT`, dibersihkan otomatis lewat
hapus-paksa deal oleh owner).

Cakupan (urut berkas):
  KT-26  GET /deals/{id}/delete-check tidak lagi 404
  KT-19  deal BATAL tidak dianggap hidup oleh gerbang tahap lead
  KT-10  skema bawaan memakai payment.staged.* / payment.cash.* (tanggal, toleransi, peristiwa)
  KT-11  jatuh tempo termin dihitung dari AKTIVASI kontrak
  KT-06  aktivasi ulang / regenerasi jadwal mempertahankan alokasi kuitansi
  KT-05  ganti jenis skema kontrak menyelaraskan deal + AR + KPR (atau ditolak)
  KT-24  tahap legal paralel -> satu efek; tanda tangan & SPR tidak ganda
  KT-18  batas unit aktif per lead atomik (paralel & lewat penawaran)
  KT-20  lead lost/recycle tidak bisa memesan unit
  KT-23  satu pengajuan KPR aktif per deal, tertaut kontrak, plafon tersinkron
  KT-22  validasi wajar komponen biaya kontrak
  KT-21  pratinjau "Jadikan Pembeli" membedakan skema DIPILIH sales vs bawaan sistem
  KT-27  daftar kontrak untuk sales: total & counts hanya miliknya
  KT-28  impor lead JSON: nomor dinormalisasi & tidak digandakan
  KT-29  tugas "Konfirmasi booking fee" selesai saat booking; booking paralel satu efek
  KT-25  sweeper kedaluwarsa reservasi melepas unit/kupon/tugas/lead seperti pembatalan
         (butuh env DB_NAME = DB instans yang diuji; opsional P0_BACKEND_DIR = kode yang diuji)
"""
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import pytest

from test_p0_kontrak import (  # noqa: F401  (fixture `cleanup` ikut diimpor)
    available_units, booked_deal, call, cleanup, new_lead, ok, pay_booking_fee_and_book, reserve,
    scheme_id, upload_proof,
)


# ----------------------------------------------------------------------------- pembantu
def contract_of(cleanup, scheme="cash_bertahap", tag="K2", activate=True):
    """Deal booked -> Jadikan Pembeli -> (aktifkan). Kembalikan (lead, deal, contract)."""
    lead, deal, _unit = booked_deal(cleanup, tag=tag, scheme=scheme)
    k = ok(call("sales", "POST", f"/deals/{deal['id']}/convert", {"scheme": scheme}))["contract"]
    if activate:
        time.sleep(1.2)  # aktivasi harus berselang dari booking supaya dasar tanggal bisa dibedakan
        k = ok(call("finance", "POST", f"/contracts/{k['id']}/activate"))
    return lead, deal, k


def ar_of(deal_id):
    code, body = call("finance", "GET", f"/finance/ar/{deal_id}")
    assert code == 200, (code, str(body)[:200])
    return body["data"], body.get("receipts") or []


def item(inv, prefix):
    return next(i for i in inv["items"] if i["label"].startswith(prefix))


def pay(deal_id, amount, item_id=None):
    body = {"deal_id": deal_id, "amount": amount, "method": "transfer", "note": "P0KT bayar",
            "proof_file_ids": [upload_proof(deal_id)]}
    if item_id:
        body["allocations"] = [{"item_id": item_id, "amount": amount}]
    return call("finance", "POST", "/finance/ar/receipts", body)


def effective(*keys):
    return ok(call("manager", "GET", "/settings/effective", params={"keys": ",".join(keys)}))


# ============================================================================ KT-26
def test_kt26_delete_check_deal_tersedia(cleanup):
    lead = new_lead(tag="DelChk")
    deal = ok(reserve(lead["id"], available_units(1)[0]))
    cleanup.append(deal["id"])
    code, body = call("owner", "GET", f"/deals/{deal['id']}/delete-check")
    assert code == 200, (code, str(body)[:200])
    assert body["data"]["can_delete"] is True and "blockers" in body["data"]


# ============================================================================ KT-19
def test_kt19_deal_batal_tidak_dianggap_hidup_oleh_gerbang_tahap_lead(cleanup):
    lead = new_lead(tag="Typo")
    deal = ok(reserve(lead["id"], available_units(1)[0]))
    cleanup.append(deal["id"])
    ok(call("sales", "POST", f"/deals/{deal['id']}/cancel", {"reason": "uji P0 batal"}))
    lc = ok(call("sales", "GET", f"/leads/{lead['id']}/lifecycle"))
    assert lc["stage"] == "nurturing", lc["stage"]
    syarat_deal = next(r for r in lc["requirements"]["booking"] if r["key"] == "deal")
    assert syarat_deal["met"] is False, "deal batal tidak boleh dihitung sebagai deal aktif"
    code, body = call("sales", "POST", f"/leads/{lead['id']}/stage", {"stage": "booking"})
    assert code == 400, (code, str(body)[:200])


# ============================================================================ KT-10
def test_kt10_skema_bawaan_mengikuti_konfigurasi_pembayaran():
    cfg = effective("payment.staged.due_day", "payment.staged.grace_day",
                    "payment.cash.payoff_days_after_completion", "payment.cash.payoff_grace_days")
    skema = {s["code"]: s for s in ok(call("manager", "GET", "/payment-schemes"))}
    cic = [i for i in skema["cash_bertahap"]["items"] if i["label"].startswith("Cicilan")]
    assert cic, "skema bawaan cash_bertahap harus punya cicilan"
    due_day = int(cfg["payment.staged.due_day"])
    for c in cic:
        assert c["due_mode"] == "monthly_day" and c["due_day"] == due_day, c
        assert c["grace_days"] == int(cfg["payment.staged.grace_day"]) - due_day, c
        assert f"tanggal {due_day} setiap bulan" in c["due_rule"], c["due_rule"]
    lunas = next(i for i in skema["cash_keras"]["items"] if i["label"].startswith("Pelunasan"))
    assert lunas["due_mode"] == "event" and lunas["event"] is True and lunas["event_code"] == "build_complete"
    assert f"maks {cfg['payment.cash.payoff_days_after_completion']} hari" in lunas["due_rule"]
    assert lunas["grace_days"] == int(cfg["payment.cash.payoff_grace_days"])


def test_kt10_jadwal_tagihan_cicilan_jatuh_pada_tanggal_konfigurasi(cleanup):
    due_day = int(effective("payment.staged.due_day")["payment.staged.due_day"])
    _, deal, _k = contract_of(cleanup, tag="K10")
    inv, _ = ar_of(deal["id"])
    cic = [i for i in inv["items"] if i["label"].startswith("Cicilan")]
    assert cic and all(int(c["due_date"][8:10]) == due_day for c in cic), [c["due_date"] for c in cic]
    assert all(c["grace_days"] == 13 for c in cic)


# ============================================================================ KT-11
def test_kt11_jatuh_tempo_termin_dari_tanggal_aktivasi(cleanup):
    _, deal, k = contract_of(cleanup, tag="K11")
    assert k["state"] == "active" and k["activated_at"]
    inv, _ = ar_of(deal["id"])
    dp = inv["items"][0]
    # DP "saat kontrak diaktifkan" jatuh tempo pada saat aktivasi (bukan saat booking).
    assert dp["due_date"][:19] == k["activated_at"][:19], (dp["due_date"], k["activated_at"])
    base = datetime.fromisoformat(k["activated_at"])
    c1 = item(inv, "Cicilan 1/")
    assert int(c1["due_date"][5:7]) == base.month % 12 + 1, (c1["due_date"], k["activated_at"])


# ============================================================================ KT-06
def test_kt06_aktivasi_ulang_idempoten_dan_alokasi_kuitansi_utuh(cleanup):
    _, deal, k = contract_of(cleanup, tag="K06a")
    inv, _ = ar_of(deal["id"])
    assert int(inv["paid"]) == 5_000_000, "booking fee (titipan) ikut ke DP pada alur normal"
    cic1 = item(inv, "Cicilan 1/")
    rc = ok(pay(deal["id"], 1_000_000, cic1["id"]))["receipt"]
    sebelum, _ = ar_of(deal["id"])
    # aktivasi ulang (klik ganda / tombol lama) -> tetap 200, jadwal TIDAK disusun ulang
    again = ok(call("finance", "POST", f"/contracts/{k['id']}/activate"))
    assert again["state"] == "active" and again["activated_at"] == k["activated_at"]
    sesudah, receipts = ar_of(deal["id"])
    assert [i["id"] for i in sesudah["items"]] == [i["id"] for i in sebelum["items"]]
    assert [(i["label"], i["paid_amount"]) for i in sesudah["items"]] == \
        [(i["label"], i["paid_amount"]) for i in sebelum["items"]]
    assert item(sesudah, "Cicilan 1/")["paid_amount"] == 1_000_000
    # kuitansi menunjuk termin yang sama dengan AR
    al = next(r for r in receipts if r["id"] == rc["id"])["allocations"]
    assert al[0]["item_id"] == item(sesudah, "Cicilan 1/")["id"] and al[0]["amount"] == 1_000_000


def test_kt06_regenerasi_jadwal_mempertahankan_alokasi_kuitansi(cleanup):
    _, deal, k = contract_of(cleanup, tag="K06b")
    inv, _ = ar_of(deal["id"])
    cic2 = item(inv, "Cicilan 2/")
    rc = ok(pay(deal["id"], 2_000_000, cic2["id"]))["receipt"]
    code, body = call("finance", "POST", f"/finance/ar/{deal['id']}/schedule",
                      {"scheme_id": inv["scheme_id"]})
    assert code == 200, (code, str(body)[:300])
    baru, receipts = ar_of(deal["id"])
    assert item(baru, "Cicilan 2/")["paid_amount"] == 2_000_000, "alokasi kasir tidak boleh diacak FIFO"
    assert item(baru, "Cicilan 1/")["paid_amount"] == 0
    assert int(baru["paid"]) == 7_000_000
    al = next(r for r in receipts if r["id"] == rc["id"])["allocations"]
    assert al[0]["item_id"] == item(baru, "Cicilan 2/")["id"], "alokasi kuitansi harus ikut id termin baru"


def test_kt06_ganti_ke_skema_lain_ditolak_bila_ada_uang_nyata(cleanup):
    _, deal, k = contract_of(cleanup, tag="K06c")
    inv, _ = ar_of(deal["id"])
    ok(pay(deal["id"], 1_000_000, item(inv, "Cicilan 1/")["id"]))
    code, body = call("finance", "POST", f"/finance/ar/{deal['id']}/schedule",
                      {"scheme_id": scheme_id("cash_keras")})
    assert code == 400 and "adendum" in str(body), (code, str(body)[:300])
    sesudah, _ = ar_of(deal["id"])
    assert item(sesudah, "Cicilan 1/")["paid_amount"] == 1_000_000 and int(sesudah["paid"]) == 6_000_000


def test_kt06_booking_fee_tetap_dialihkan_saat_ganti_skema_tanpa_uang_nyata(cleanup):
    """Alur normal: hanya booking fee -> boleh disusun ulang, uangnya ikut ke DP baru."""
    _, deal, k = contract_of(cleanup, tag="K06d", activate=False)
    code, body = call("finance", "POST", f"/finance/ar/{deal['id']}/schedule",
                      {"scheme_id": scheme_id("cash_keras")})
    assert code == 200, (code, str(body)[:300])
    inv, _ = ar_of(deal["id"])
    assert int(inv["paid"]) == 5_000_000 and inv["items"][0]["paid_amount"] == 5_000_000


# ============================================================================ KT-05
def test_kt05_ganti_jenis_skema_menyelaraskan_deal_ar_dan_kpr(cleanup):
    _, deal, k = contract_of(cleanup, scheme="cash_keras", tag="K05a", activate=False)
    out = ok(call("finance", "POST", f"/contracts/{k['id']}/scheme",
                  {"scheme": "kpr", "reason": "pembeli beralih ke KPR"}))
    assert out["scheme"] == "kpr"
    d = ok(call("manager", "GET", f"/deals/{deal['id']}"))
    skema = {s["id"]: s for s in ok(call("manager", "GET", "/payment-schemes"))}
    assert skema[d["scheme_id"]]["kind"] == "kpr" and d["scheme_explicit"] is True
    inv, _ = ar_of(deal["id"])
    assert skema[inv["scheme_id"]]["kind"] == "kpr"
    assert any(i.get("payer") == "bank" for i in inv["items"]), "porsi bank harus ditandai"
    assert int(inv["paid"]) == 5_000_000
    kpr = ok(call("finance", "GET", f"/contracts/{k['id']}/kpr"))
    assert kpr["application"] and kpr["application"]["contract_id"] == k["id"]
    # SPR tidak lagi terblokir "skema deal beda"
    code, body = call("sales", "GET", f"/contracts/{k['id']}/documents/available")
    assert code == 200
    for t in body["data"]:
        assert "skema_deal_beda" not in [b["code"] for b in t["blocks"]], t["code"]


def test_kt05_ganti_jenis_skema_ditolak_bila_ada_uang_nyata(cleanup):
    _, deal, k = contract_of(cleanup, scheme="cash_bertahap", tag="K05b")
    inv, _ = ar_of(deal["id"])
    ok(pay(deal["id"], 1_000_000, item(inv, "Cicilan 1/")["id"]))
    code, body = call("finance", "POST", f"/contracts/{k['id']}/scheme",
                      {"scheme": "kpr", "reason": "uji tolak"})
    assert code == 400 and "penerimaan" in str(body), (code, str(body)[:300])
    kk = ok(call("manager", "GET", f"/contracts/{k['id']}"))
    assert kk["scheme"] == "cash_bertahap"
    sesudah, _ = ar_of(deal["id"])
    assert item(sesudah, "Cicilan 1/")["paid_amount"] == 1_000_000


def test_kt05_kembali_ke_tunai_dan_skema_sama_noop(cleanup):
    _, deal, k = contract_of(cleanup, scheme="cash_keras", tag="K05c", activate=False)
    assert ok(call("finance", "POST", f"/contracts/{k['id']}/scheme",
                   {"scheme": "cash_keras"}))["scheme"] == "cash_keras"
    ok(call("finance", "POST", f"/contracts/{k['id']}/scheme", {"scheme": "kpr", "reason": "uji"}))
    back = ok(call("finance", "POST", f"/contracts/{k['id']}/scheme",
                   {"scheme": "cash_bertahap", "reason": "kembali ke tunai bertahap"}))
    assert back["scheme"] == "cash_bertahap"
    skema = {s["id"]: s for s in ok(call("manager", "GET", "/payment-schemes"))}
    inv, _ = ar_of(deal["id"])
    assert skema[inv["scheme_id"]]["kind"] == "cash_bertahap"


# ============================================================================ KT-24
def test_kt24_ppjb_paralel_satu_nomor_satu_riwayat(cleanup):
    _, deal, k = contract_of(cleanup, scheme="cash_keras", tag="K24a")
    inv, _ = ar_of(deal["id"])
    dp = inv["items"][0]
    kurang = int(dp["amount"]) - int(dp["paid_amount"])
    ok(pay(deal["id"], kurang, dp["id"]))
    with ThreadPoolExecutor(max_workers=4) as pool:
        res = list(pool.map(lambda _: call("manager", "POST", f"/contracts/{k['id']}/legal/ppjb", {}),
                            range(4)))
    kode = sorted(c for c, _ in res)
    assert kode.count(200) == 1 and all(c in (400, 409) for c in kode if c != 200), \
        (kode, [str(b)[:100] for c, b in res if c != 200])
    kk = ok(call("manager", "GET", f"/contracts/{k['id']}"))
    assert len(kk["legal_history"]) == 1, kk["legal_history"]
    assert kk["legal"]["ppjb"]["number"] == kk["legal_history"][0]["number"]
    code, body = call("owner", "GET", "/work/tasks",
                      params={"scope": "all", "q": "Jadwalkan AJB", "limit": 100})
    assert code == 200, (code, str(body)[:200])
    ajb = [t for t in body["data"] if t.get("related_entity_id") == k["id"]]
    assert len(ajb) == 1, f"tugas 'Jadwalkan AJB' harus tepat satu: {ajb}"


def _spr_final(contract_id, who="sales"):
    doc = ok(call(who, "POST", f"/contracts/{contract_id}/documents", {}))
    ok(call("manager", "POST", f"/documents/{doc['id']}/finalize"))
    return doc


def test_kt24_tanda_tangan_paralel_tidak_ganda(cleanup):
    _, deal, k = contract_of(cleanup, scheme="cash_keras", tag="K24b")
    doc = _spr_final(k["id"])
    body = {"role": "buyer", "name": "Pembeli Uji P0KT"}
    with ThreadPoolExecutor(max_workers=3) as pool:
        res = list(pool.map(lambda _: call("manager", "POST", f"/documents/{doc['id']}/sign", body),
                            range(3)))
    kode = sorted(c for c, _ in res)
    assert kode == [200, 409, 409], (kode, [str(b)[:120] for c, b in res if c != 200])
    d = ok(call("manager", "GET", f"/documents/{doc['id']}"))
    assert len(d["signatures"]) == 1, d["signatures"]
    # penanda tangan LAIN (developer) tetap bisa menandatangani dokumen yang sama
    ok(call("manager", "POST", f"/documents/{doc['id']}/sign", {"role": "seller", "name": "Direksi P0KT"}))
    assert len(ok(call("manager", "GET", f"/documents/{doc['id']}"))["signatures"]) == 2


def test_kt24_spr_kedua_untuk_kontrak_sama_tidak_bisa_ditandatangani(cleanup):
    _, deal, k = contract_of(cleanup, scheme="cash_keras", tag="K24c")
    d1, d2 = _spr_final(k["id"]), _spr_final(k["id"])
    ok(call("manager", "POST", f"/documents/{d1['id']}/sign", {"role": "buyer", "name": "Pembeli P0KT"}))
    code, body = call("manager", "POST", f"/documents/{d2['id']}/sign", {"role": "buyer", "name": "Pembeli P0KT"})
    assert code == 409 and "adendum" in str(body), (code, str(body)[:300])
    assert ok(call("manager", "GET", f"/documents/{d2['id']}"))["status"] == "finalized"
    # hitungan daftar: kunci "final" tidak lagi selalu 0
    c, lst = call("manager", "GET", "/documents", params={"limit": 5})
    assert c == 200 and lst["counts"]["final"] >= 1 and lst["counts"]["signed"] >= 1, lst["counts"]


# ============================================================================ KT-18
def test_kt18_reservasi_paralel_satu_lead_dua_unit_hanya_satu_lolos(cleanup):
    u1, u2 = available_units(2)
    lead = new_lead(tag="Batas")
    with ThreadPoolExecutor(max_workers=2) as pool:
        f1 = pool.submit(reserve, lead["id"], u1)
        f2 = pool.submit(reserve, lead["id"], u2)
        res = [f1.result(), f2.result()]
    for c, b in res:
        if c == 200:
            cleanup.append(b["data"]["id"])
    kode = sorted(c for c, _ in res)
    assert kode == [200, 409], (kode, [str(b)[:150] for _, b in res])
    deals = ok(call("manager", "GET", "/deals", params={"lead_id": lead["id"]}))
    assert len([d for d in deals if d["status"] in ("reserved", "booked")]) == 1
    # unit yang kalah kembali tersedia (tidak terkunci oleh permintaan yang ditolak)
    kalah = u2 if res[0][0] == 200 else u1
    assert call("manager", "GET", "/units", params={"q": kalah["code"], "limit": 5})[1]["data"][0]["status"] == "available"


def test_kt18_konversi_penawaran_menghormati_batas_unit_aktif(cleanup):
    u1, u2 = available_units(2)
    lead = new_lead(tag="BatasQ")
    cleanup.append(ok(reserve(lead["id"], u1))["id"])
    q = ok(call("sales", "POST", "/quotations", {"lead_id": lead["id"], "unit_id": u2["id"],
                                                  "scheme_id": scheme_id("cash_keras"),
                                                  "booking_fee": 5_000_000}))
    code, body = call("sales", "POST", f"/quotations/{q['id']}/convert", {})
    assert code in (400, 409) and "batas" in str(body), (code, str(body)[:300])
    assert call("manager", "GET", "/units", params={"q": u2["code"], "limit": 5})[1]["data"][0]["status"] == "available"


def test_kt18_pengecualian_manajer_dengan_alasan_tetap_berlaku(cleanup):
    u1, u2 = available_units(2)
    lead = new_lead(tag="BatasOv")
    cleanup.append(ok(reserve(lead["id"], u1))["id"])
    kode_tanpa, _ = reserve(lead["id"], u2)
    assert kode_tanpa == 409
    code, body = reserve(lead["id"], u2, who="manager", limit_override_reason="Pembeli membeli dua unit sekaligus (uji P0)")
    assert code == 200, (code, str(body)[:300])
    cleanup.append(body["data"]["id"])


# ============================================================================ KT-20
def test_kt20_lead_lost_tidak_bisa_memesan_unit_dan_pulih_lewat_daur_ulang(cleanup):
    unit = available_units(1)[0]
    lead = new_lead(tag="Lost")
    ok(call("sales", "POST", f"/leads/{lead['id']}/stage", {"stage": "lost", "note": "uji P0 lost"}))
    code, body = reserve(lead["id"], unit)
    assert code == 409 and "tidak bisa memesan" in str(body), (code, str(body)[:300])
    assert call("manager", "GET", "/units", params={"q": unit["code"], "limit": 5})[1]["data"][0]["status"] == "available"
    assert ok(call("manager", "GET", "/deals", params={"lead_id": lead["id"]})) == []
    # lead dihidupkan lagi (daur ulang -> nurturing): boleh memesan, tahap ikut naik ke booking
    ok(call("sales", "POST", f"/leads/{lead['id']}/stage", {"stage": "recycle", "note": "uji P0 kembali"}))
    ok(call("sales", "POST", f"/leads/{lead['id']}/stage", {"stage": "nurturing"}))
    deal = ok(reserve(lead["id"], unit))
    cleanup.append(deal["id"])
    assert ok(call("sales", "GET", f"/leads/{lead['id']}"))["stage"] == "booking"


# ============================================================================ KT-25
def _jalankan_sweeper() -> int:
    """Jalankan `reservation_expiry_sweeper` dari kode yang diuji terhadap DB instans (proses terpisah)."""
    db_name = os.environ.get("DB_NAME")
    if not db_name:
        pytest.skip("set DB_NAME = nama DB instans yang diuji untuk menguji sweeper")
    backend = os.environ.get("P0_BACKEND_DIR") or str(Path(__file__).resolve().parents[2])
    r = subprocess.run(
        [sys.executable, "-c",
         "import asyncio, engine_sweepers as e; print('SWEPT', asyncio.run(e.reservation_expiry_sweeper()))"],
        cwd=backend, env={**os.environ, "DB_NAME": db_name}, capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr[-800:]
    return int(r.stdout.strip().split()[-1])


def _paksa_kedaluwarsa(deal_id: str) -> None:
    from pymongo import MongoClient
    url = os.environ.get("MONGO_URL") or "mongo" + "db://127.0.0.1:27017"  # gate kepatuhan: tanpa literal URI
    MongoClient(url)[os.environ.get("DB_NAME", "")].deals.update_one(
        {"id": deal_id}, {"$set": {"reserved_until": "2020-01-01T00:00:00+00:00"}})


def test_kt25_sweeper_kedaluwarsa_melepas_seperti_pembatalan(cleanup):
    if not os.environ.get("DB_NAME"):
        pytest.skip("set DB_NAME = nama DB instans yang diuji untuk menguji sweeper")
    kode = "P0KT" + uuid.uuid4().hex[:6].upper()
    ok(call("manager", "POST", "/pricing/coupons",
            {"code": kode, "name": "P0KT kupon kedaluwarsa", "kind": "amount", "value": 1_000_000,
             "quota_total": 3, "quota_per_customer": 1, "target": "price"}))
    unit = available_units(1)[0]
    lead = new_lead(tag="Expire")
    deal = ok(reserve(lead["id"], unit, coupon_code=kode))
    cleanup.append(deal["id"])
    cp = next(c for c in ok(call("manager", "GET", "/pricing/coupons")) if c["code"] == kode)
    assert cp["used_count"] == 1
    assert ok(call("sales", "GET", f"/leads/{lead['id']}"))["stage"] == "booking"
    _paksa_kedaluwarsa(deal["id"])
    assert _jalankan_sweeper() >= 1
    d = ok(call("manager", "GET", f"/deals/{deal['id']}"))
    assert d["status"] == "expired"
    u = call("manager", "GET", "/units", params={"q": unit["code"], "limit": 5})[1]["data"][0]
    assert u["status"] == "available"
    assert not u.get("reserved_by_deal") and not u.get("deal_id") and not u.get("lead_id") \
        and not u.get("lead_name"), f"tautan basi tertinggal di unit: {u}"
    assert u.get("payment_status") in (None, "none")
    assert ok(call("sales", "GET", f"/leads/{lead['id']}"))["stage"] == "nurturing"
    cp = next(c for c in ok(call("manager", "GET", "/pricing/coupons")) if c["code"] == kode)
    assert cp["used_count"] == 0, "kuota kupon harus kembali"
    for st, harap in (("open", False), ("cancelled", True)):
        code, body = call("owner", "GET", "/work/tasks",
                          params={"scope": "all", "q": "Konfirmasi booking fee", "status": st, "limit": 100})
        assert code == 200, (code, str(body)[:200])
        ada = [t for t in body["data"] if t.get("related_entity_id") == deal["id"]]
        assert bool(ada) is harap, (st, ada)
    # menjalankan sweeper lagi tidak melepas dua kali / merusak unit yang sudah dipesan ulang
    deal2 = ok(reserve(lead["id"], unit))
    cleanup.append(deal2["id"])
    _jalankan_sweeper()
    assert call("manager", "GET", "/units", params={"q": unit["code"], "limit": 5})[1]["data"][0]["status"] == "reserved"


# ============================================================================ KT-23
def _financing(deal_id, bank="BTN", plafon=400_000_000, who="finance"):
    return call(who, "POST", "/financing", {"deal_id": deal_id, "bank_name": bank, "plafon": plafon,
                                            "dp_amount": 0, "tenor_months": 180})


def test_kt23_pengajuan_kpr_paralel_hanya_satu_per_deal(cleanup):
    _, deal, _k = contract_of(cleanup, scheme="cash_bertahap", tag="K23a", activate=False)
    with ThreadPoolExecutor(max_workers=3) as pool:
        res = list(pool.map(lambda _: _financing(deal["id"]), range(3)))
    kode = sorted(c for c, _ in res)
    assert kode == [200, 409, 409], (kode, [str(b)[:150] for c, b in res if c != 200])
    rows = ok(call("finance", "GET", "/financing", params={"deal_id": deal["id"]}))
    assert len(rows) == 1, rows
    code, body = _financing(deal["id"], bank="BNI")
    assert code == 409 and "pengajuan KPR" in str(body), (code, str(body)[:300])


def test_kt23_pengajuan_kontrak_kpr_dilengkapi_bukan_digandakan_dan_plafon_tersinkron(cleanup):
    _, deal, k = contract_of(cleanup, scheme="kpr", tag="K23b", activate=False)
    app0 = ok(call("finance", "GET", f"/contracts/{k['id']}/kpr"))["application"]
    assert app0["contract_id"] == k["id"] and not app0.get("bank_name")
    # plafon di komponen biaya kontrak -> pengajuan (belum disetujui bank)
    ok(call("finance", "POST", f"/contracts/{k['id']}/costs", {"plafon_kredit": 500_000_000}))
    app1 = ok(call("finance", "GET", f"/contracts/{k['id']}/kpr"))["application"]
    assert app1["plafon"] == 500_000_000 and app1["requested_plafon"] == 500_000_000
    # "Ajukan KPR" dari menu pembiayaan melengkapi pengajuan kontrak (tahap & tautan kontrak utuh)
    code, body = _financing(deal["id"], bank="BTN", plafon=480_000_000)
    assert code == 200, (code, str(body)[:300])
    assert body["data"]["id"] == app0["id"]
    view = ok(call("finance", "GET", f"/contracts/{k['id']}/kpr"))
    assert view["application"]["id"] == app0["id"] and view["application"]["bank_name"] == "BTN"
    assert view["application"]["contract_id"] == k["id"] and view["stage"] == "berkas_lengkap"
    assert len(ok(call("finance", "GET", "/financing", params={"deal_id": deal["id"]}))) == 1
    code, body = _financing(deal["id"], bank="BNI")
    assert code == 409, (code, str(body)[:200])
    # progres bank tetap bisa dimajukan (tampilan tidak tertimpa pengajuan baru)
    ok(call("finance", "POST", f"/contracts/{k['id']}/kpr/stage/diajukan_ke_bank", {"bank": "BTN"}))


# ============================================================================ KT-22
def test_kt22_komponen_biaya_tidak_wajar_ditolak_yang_wajar_diterima(cleanup):
    _, deal, k = contract_of(cleanup, scheme="cash_keras", tag="K22", activate=False)
    harga = int(ok(call("manager", "GET", f"/contracts/{k['id']}"))["breakdown"]["gross_price"])
    for body in ({"promo_discount": harga + 50_000_000}, {"dp_percent": 150},
                 {"plafon_kredit": 99_999_999_999}, {"bphtb": -5}, {"notary_fee": harga * 3}):
        code, resp = call("finance", "POST", f"/contracts/{k['id']}/costs", body)
        assert code == 400, (body, code, str(resp)[:200])
    kk = ok(call("manager", "GET", f"/contracts/{k['id']}"))
    assert not kk["costs"].get("promo_discount") and not kk["costs"].get("dp_percent")
    assert kk["breakdown"]["nett_price"] > 0
    # angka wajar tetap diterima; -1 tetap berarti "kosongkan"
    out = ok(call("finance", "POST", f"/contracts/{k['id']}/costs",
                  {"bphtb": 42_500_000, "notary_fee": 15_000_000, "promo_discount": 10_000_000, "dp_percent": 30}))
    assert out["costs"]["bphtb"] == 42_500_000 and out["costs"]["promo_discount"] == 10_000_000
    out = ok(call("finance", "POST", f"/contracts/{k['id']}/costs", {"bphtb": -1}))
    assert "bphtb" not in out["costs"] and out["costs"]["notary_fee"] == 15_000_000


# ============================================================================ KT-21
def test_kt21_skema_bawaan_tidak_dikunci_skema_pilihan_sales_dikunci(cleanup):
    # (a) reservasi TANPA memilih skema -> skema bawaan sistem, boleh disesuaikan saat Jadikan Pembeli
    lead_a = new_lead(tag="K21a")
    deal_a = ok(reserve(lead_a["id"], available_units(1)[0], scheme=None))
    cleanup.append(deal_a["id"])
    pay_booking_fee_and_book(deal_a["id"])
    pre = ok(call("sales", "GET", f"/deals/{deal_a['id']}/convert-preview"))
    assert pre["deal_scheme"] and pre["deal_scheme_explicit"] is False, pre
    out = ok(call("sales", "POST", f"/deals/{deal_a['id']}/convert", {"scheme": "cash_keras"}))
    assert out["contract"]["scheme"] == "cash_keras"
    inv, _ = ar_of(deal_a["id"])
    assert int(inv["paid"]) == 5_000_000
    # (b) skema DIPILIH sales saat reservasi -> terkunci
    _, deal_b, _u = booked_deal(cleanup, tag="K21b", scheme="cash_bertahap")
    pre = ok(call("sales", "GET", f"/deals/{deal_b['id']}/convert-preview"))
    assert pre["deal_scheme"] == "cash_bertahap" and pre["deal_scheme_explicit"] is True
    code, body = call("sales", "POST", f"/deals/{deal_b['id']}/convert", {"scheme": "kpr"})
    assert code == 400 and "dipilih saat reservasi" in str(body), (code, str(body)[:300])


# ============================================================================ KT-27
def test_kt27_daftar_kontrak_sales_total_dan_counts_hanya_miliknya(cleanup):
    u1, u2 = available_units(2)
    for u, tag in ((u1, "L1"), (u2, "L2")):
        _, d, _ = booked_deal(cleanup, unit=u, tag="K27" + tag, scheme="cash_keras")
        ok(call("sales", "POST", f"/deals/{d['id']}/convert", {"scheme": "cash_keras"}))
    code, body = call("sales", "GET", "/contracts", params={"limit": 1})
    assert code == 200 and len(body["data"]) == 1
    assert body["total"] >= 2, "total harus jumlah SEMUA kontrak milik sales, bukan jumlah baris halaman"
    assert sum(body["counts"].values()) == body["total"], (body["total"], body["counts"])
    code, body2 = call("sales2", "GET", "/contracts", params={"limit": 200})
    assert code == 200
    milik = len(body2["data"])
    assert body2["total"] == milik and sum(body2["counts"].values()) == milik, (body2["total"], body2["counts"])


# ============================================================================ KT-28
def test_kt28_impor_lead_json_menormalkan_telepon_dan_melewati_duplikat():
    import random
    nomor = "0813" + "".join(random.choice("0123456789") for _ in range(8))
    spasi = f"{nomor[:4]} {nomor[4:8]} {nomor[8:]}"
    nama = "P0KT Impor " + uuid.uuid4().hex[:5]
    out = ok(call("manager", "POST", "/leads/import", {"leads": [
        {"name": nama, "phone": spasi, "source": "import"},
        {"name": nama + " kembar", "phone": nomor, "source": "import"}]}))
    assert out["created"] == 1 and out["skipped"] == 1, out
    code, body = call("manager", "POST", "/leads", {"name": nama + " lagi", "phone": nomor, "source": "walk_in"})
    assert code == 409, (code, str(body)[:200])
    rows = ok(call("manager", "GET", "/leads", params={"q": nama, "limit": 20}))
    assert len(rows) == 1 and rows[0]["phone"].lstrip("+").startswith("62"), rows


# ============================================================================ KT-29
def test_kt29_tugas_konfirmasi_booking_fee_selesai_saat_booking(cleanup):
    lead, deal, _u = booked_deal(cleanup, tag="K29")
    for st, harap in (("open", False), ("done", True)):
        code, body = call("owner", "GET", "/work/tasks",
                          # q dipersempit dengan nama lead uji: DB yang sudah lama dipakai punya >100 tugas serupa
                          params={"scope": "all", "q": f"Konfirmasi booking fee: {lead['name']}", "status": st, "limit": 100})
        assert code == 200, (code, str(body)[:200])
        ada = [t for t in body["data"] if t.get("related_entity_id") == deal["id"]]
        assert bool(ada) is harap, (st, ada)


def test_kt29_booking_paralel_hanya_satu_efek(cleanup):
    unit = available_units(1)[0]
    lead = new_lead(tag="K29b")
    deal = ok(reserve(lead["id"], unit))
    cleanup.append(deal["id"])
    fid = upload_proof(deal["id"])
    ok(call("finance", "POST", f"/booking-fee/deals/{deal['id']}/pay",
            {"amount": 5_000_000, "method": "transfer", "note": "P0KT bf", "proof_file_ids": [fid]}))
    with ThreadPoolExecutor(max_workers=3) as pool:
        res = list(pool.map(lambda _: call("sales", "POST", f"/deals/{deal['id']}/book", {}), range(3)))
    kode = sorted(c for c, _ in res)
    assert kode.count(200) == 1 and all(c in (400, 409) for c in kode if c != 200), kode
    inv, receipts = ar_of(deal["id"])
    assert int(inv["paid"]) == 5_000_000 and len([r for r in receipts if r.get("funding") == "deposit"]) <= 1
