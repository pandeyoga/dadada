"""Regresi F4 — keadaan deal dibaca bersama oleh jalur uang (audit PK3-05/FZ-03, FZ-01/02, FZ-08, PK3-06).

    API_BASE=http://localhost:8054/api python -m pytest backend/tests/p0/test_p0_status_deal.py -n 0 -q --noconftest
"""
import time

import pytest

from test_p0_masuk import FINANCE, MANAGER, OWNER, SALES, World, ar, call, cl_balance, ok, pay
from test_p0_masuk_2 import approve as approve_cancel, cancel_case, convert

FINLEAD = "finlead@sipro.co.id"


@pytest.fixture(scope="module")
def world():
    return World()


def _void(rid, reason="uji F4 pembatalan kuitansi"):
    return call(FINLEAD, "POST", f"/finance/ar/receipts/{rid}/void", json={"reason": reason})


def _rid(resp):
    return (resp.get("data") or resp)["receipt"]["id"]


def _reconcile_ok(timeout=30):
    """Rekonsiliasi hijau SETELAH antrean event kosong (jurnal lahir dari event; dispatcher tiap ±8 dtk)."""
    end = time.time() + timeout
    while True:
        d = ok(call(FINANCE, "GET", "/finance/reconcile"))["data"]
        if d["ok"] or time.time() > end:
            return d["ok"]
        time.sleep(1.5)


# ------------------------------------------------------------------ PK3-05 / FZ-03 — BAST
def test_bast_deal_batal_ditolak_dan_tidak_menjurnal(world):
    d = cancel_case(world, paid=100_000_000)
    approve_cancel(d["cancel_id"])
    r = call(FINANCE, "POST", f"/finance/ar/{d['deal_id']}/bast")
    assert r.status_code == 400 and "DIBATALKAN" in r.text, (r.status_code, r.text[:200])
    deal = ok(call(OWNER, "GET", f"/deals/{d['deal_id']}"))["data"]
    assert deal["status"] == "cancelled", "deal batal tidak boleh hidup lagi menjadi completed"
    unit = [u for u in ok(call(OWNER, "GET", "/units", params={"project_id": world.project_id, "limit": 200}))["data"]
            if u["id"] == d["unit_id"]][0]
    assert unit["status"] != "sold"
    assert _reconcile_ok()


def test_bast_deal_reserved_ditolak(world):
    d = world.new_deal(book=False)
    r = call(FINANCE, "POST", f"/finance/ar/{d['deal_id']}/bast")
    assert r.status_code == 400 and "booked" in r.text, (r.status_code, r.text[:200])


def test_bast_deal_booked_tetap_berhasil(world):
    d = world.new_deal()
    ok(pay(d["deal_id"], 100_000_000))
    out = ok(call(FINANCE, "POST", f"/finance/ar/{d['deal_id']}/bast"))
    assert int(out["data"]["revenue"]) > 0
    assert ok(call(OWNER, "GET", f"/deals/{d['deal_id']}"))["data"]["status"] == "completed"


# ------------------------------------------------------------------ FZ-01 / FZ-02 — void kuitansi
def test_void_kuitansi_deal_batal_ditolak(world):
    d = cancel_case(world, paid=100_000_000)
    rid = [r for r in ar(d["deal_id"])["receipts"] if r.get("status") != "void"][0]["id"]
    approve_cancel(d["cancel_id"])
    r = _void(rid)
    assert r.status_code == 400 and "DIBATALKAN" in r.text, (r.status_code, r.text[:200])
    assert _reconcile_ok()


def test_void_kuitansi_prabast_setelah_bast_tidak_membuat_kewajiban_negatif(world):
    d = world.new_deal()
    rid = _rid(ok(pay(d["deal_id"], 100_000_000)))
    ok(call(FINANCE, "POST", f"/finance/ar/{d['deal_id']}/bast"))
    assert cl_balance(d["deal_id"]) == 0, "BAST menutup kewajiban kontrak"
    ok(_void(rid))
    assert cl_balance(d["deal_id"]) == 0, "void sesudah BAST tidak boleh membuat kewajiban kontrak negatif"
    inv = ar(d["deal_id"])["data"]
    assert int(inv["paid"]) == 0 and int(inv["outstanding"]) == int(inv["total"]), "piutang naik kembali"
    assert _reconcile_ok()


# ------------------------------------------------------------------ FZ-08 — tahap KPR pada kontrak batal
def test_tahap_kpr_pada_kontrak_batal_ditolak(world):
    d = world.new_deal(scheme="KPR (DP 0% + pencairan bank)")
    cid = convert(d)
    c = ok(call(MANAGER, "POST", "/cancellations", json={"contract_id": cid, "reason": "uji F4 batal sebelum KPR"}))["data"]
    approve_cancel(c["id"])
    r = call(FINANCE, "POST", f"/contracts/{cid}/kpr/stage/diajukan_ke_bank", json={"bank": "BTN"})
    assert r.status_code == 400 and "DIBATALKAN" in r.text, (r.status_code, r.text[:200])
    inv = ar(d["deal_id"])["data"]
    assert inv.get("status") != "unpaid" or int(inv.get("outstanding") or 0) == 0, "AR batal tidak boleh hidup lagi"


# ------------------------------------------------------------------ PK3-06 — pajak deal batal
def test_pajak_deal_batal_tidak_bisa_disetor(world):
    d = cancel_case(world, paid=100_000_000)
    approve_cancel(d["cancel_id"])
    rows = ok(call(FINANCE, "GET", "/tax/records", params={"limit": 200}))["data"]
    mine = [t for t in rows if t.get("deal_id") == d["deal_id"] and t.get("status") == "pending"]
    if not mine:
        pytest.skip("deal ini tidak melahirkan catatan pajak pending pada skema uji")
    r = call(FINANCE, "PUT", f"/tax/records/{mine[0]['id']}", json={"status": "paid", "ntpn": "NTPN-F4-0001"})
    assert r.status_code == 400 and "DIBATALKAN" in r.text, (r.status_code, r.text[:200])


# ------------------------------------------------------------------ PK3-04 — satu unit dijual dua kali
def _unit(world, unit_id):
    rows = ok(call(OWNER, "GET", "/units", params={"project_id": world.project_id, "limit": 200}))["data"]
    return [u for u in rows if u["id"] == unit_id][0]


def test_buka_blokir_tidak_melepas_unit_yang_sudah_booked(world):
    d = world.new_deal()
    assert _unit(world, d["unit_id"])["status"] == "booked"
    r = call("pm@sipro.co.id", "POST", f"/masterplan/units/{d['unit_id']}/block",
             json={"blocked": False, "reason": "uji F4 buka blokir unit terjual"})
    assert r.status_code == 400 and "tidak sedang diblokir" in r.text, (r.status_code, r.text[:200])
    assert _unit(world, d["unit_id"])["status"] == "booked"


def test_hapus_paksa_deal_lama_tidak_melepas_unit_deal_baru(world):
    a = world.new_deal()
    ok(call(OWNER, "POST", f"/deals/{a['deal_id']}/cancel", json={"reason": "uji F4 batal deal lama"}))
    lead = ok(call("sales@sipro.co.id", "POST", "/leads", json={
        "name": "Uji F4 pembeli baru", "phone": "+62812" + str(abs(hash(a["deal_id"])))[:9], "source": "manual"}))["data"]
    b = ok(call("sales@sipro.co.id", "POST", "/deals/reserve", json={
        "unit_id": a["unit_id"], "lead_id": lead["id"], "booking_fee": 0,
        "scheme_id": world.scheme["Cash Bertahap (3x)"]}))["data"]
    r = call(OWNER, "DELETE", f"/deals/{a['deal_id']}", params={"force": "true", "reason": "uji F4 hapus paksa deal lama"})
    assert r.status_code == 200, r.text[:200]
    u = _unit(world, a["unit_id"])
    assert u["status"] == "reserved" and (u.get("reserved_by_deal") == b["id"]), \
        f"unit deal BARU terlepas oleh hapus-paksa deal lama: {u['status']} / {u.get('reserved_by_deal')}"


# ------------------------------------------------------------------ bayar booking fee ‖ batalkan reservasi (G-B menemukan sisa balapan)
def test_bayar_booking_fee_dan_batal_bersamaan_tidak_merusak_rekonsiliasi(world):
    """Dulu 200/200: kuitansi + saldo titipan ada, tetapi pembatalan sudah memindahkan titipan sebelum titipan ini lahir →
    2-1450 di GL nol vs subledger Rp 5 jt (rekonsiliasi merah). Kini keduanya diserialkan per-deal (`deal_money`).

    CATATAN JUJUR: ini tes SOAK probabilistik. Pada skrip manual kode lama menghasilkan 1 dari 5 putaran tidak konsisten,
    tetapi tes ini (60 putaran total pada 2 run) belum berhasil merah pada kode lama — jangan dianggap bukti merah-dulu."""
    import random
    from test_p0_masuk import race, upload_proof
    for i in range(30):
        d = world.new_deal(booking_fee=5_000_000, book=False)["deal_id"]
        proof = upload_proof(FINANCE)
        # dua pertiga putaran dimulai SERENTAK (jendela yang terukur memunculkan cacat ±20%/putaran), sisanya dengan selisih acak
        t_bayar, t_batal = (0.0, 0.0) if i % 3 else (random.uniform(0, 0.05), random.uniform(0, 0.05))

        def bayar(d=d, proof=proof, t=t_bayar):
            time.sleep(t)
            return call(FINANCE, "POST", f"/booking-fee/deals/{d}/pay",
                        json={"amount": 5_000_000, "method": "transfer", "note": "uji balapan", "proof_file_ids": [proof]})

        def batal(d=d, t=t_batal):
            time.sleep(t)
            return call(SALES, "POST", f"/deals/{d}/cancel", json={"reason": "uji balapan bayar booking fee dan batal"})
        race([bayar, batal])
    assert _reconcile_ok(), "rekonsiliasi merah setelah balapan bayar-booking-fee ‖ batal"
