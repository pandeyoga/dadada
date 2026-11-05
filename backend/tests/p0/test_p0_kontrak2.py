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
  KT-24  tahap legal paralel -> satu efek
"""
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from test_p0_kontrak import (  # noqa: F401  (fixture `cleanup` ikut diimpor)
    available_units, booked_deal, call, cleanup, new_lead, ok, reserve, scheme_id, upload_proof,
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
