"""Regresi W1-A / keputusan #13 — reservasi KEDALUWARSA dengan booking fee SUDAH dibayar
(`reservation.expiry.paid_booking_fee` = perpanjang | antrean_refund | hangus, + `extend_days`, `max_extensions`).

    API_BASE=http://localhost:8070/api DB_NAME=sipro_w1a MONGO_URL=<uri> \
      python -m pytest backend/tests/p0/test_w1a_kedaluwarsa_bf.py -n 0 --noconftest -q -p no:cacheprovider

Sweeper dijalankan SUNGGUHAN (`engine_sweepers.reservation_expiry_sweeper` di proses terpisah, DB instans yang sama — pola H-A);
bukti merah di kode lama: arahkan `API_BASE`/`DB_NAME` ke backend lama dan `P0_BACKEND_DIR=<checkout lama>/backend`. Bagian HTTP
(kunci pengaturan, refund lewat jalur yang ada, rekonsiliasi) merah di kode lama karena kuncinya tidak ada; perilaku sweeper
merah karena kode lama melepas unit tanpa menyentuh uang booking fee.

Penimpaan hanya di tingkat PROYEK uji (tidak menyentuh tes lain) dan selalu dikembalikan di `finally`. Deal yang sengaja
ditahan/diperpanjang dibatalkan di akhir tes supaya tidak tertinggal reservasi berbayar yang menggantung di DB bersama.
"""
import datetime
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path

import pytest

import aio
from test_p0_masuk import FINANCE, OWNER, SALES, World, call, ok, upload_proof
from test_p0_sisa_siklus import jalankan_sweeper, kedaluwarsakan
from test_p0_siklus_deal import drop_seeds, mdb, now, seed_dependents

BACKEND = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND))

MODE = "reservation.expiry.paid_booking_fee"
DAYS = "reservation.expiry.extend_days"
MAXX = "reservation.expiry.max_extensions"
FEE = 5_000_000


@pytest.fixture(scope="module")
def world():
    return World()


@pytest.fixture(scope="module")
def world2():
    return World()


# ------------------------------------------------------------------ pembantu
def put(key, value, scope="org", scope_id=None, who=OWNER):
    body = {"value": value, "reason": "uji W1A reservasi kedaluwarsa", "scope": scope}
    if scope_id:
        body["scope_id"] = scope_id
    return call(who, "PUT", f"/settings/{key}", json=body)


def reset(key, scope="org", scope_id=None):
    params = {"scope": scope}
    if scope_id:
        params["scope_id"] = scope_id
    call(OWNER, "POST", f"/settings/{key}/reset", params=params)


def bayar(deal_id, amount=FEE):
    ok(call(FINANCE, "POST", f"/booking-fee/deals/{deal_id}/pay", json={"amount": amount, "proof_file_ids": [upload_proof()]}))


def deal_berbayar(world, fee=FEE):
    d = world.new_deal(booking_fee=fee, book=False)
    bayar(d["deal_id"], fee)
    return d


def row(d):
    return mdb().deals.find_one({"id": d["deal_id"]})


def unit(d):
    return mdb().units.find_one({"id": d["unit_id"]})


def inv(d):
    return mdb().booking_fee_invoices.find_one({"deal_id": d["deal_id"]})


def deposit(d):
    return int((mdb().customer_deposits.find_one({"deal_id": d["deal_id"]}) or {}).get("balance") or 0)


def tugas(src):
    return list(mdb().tasks.find({"source_event": src}))


def notif(d, bagian):
    return list(mdb().notifications.find({"related_entity_id": d["deal_id"], "title": {"$regex": bagian}}))


def kedaluwarsa(d):
    kedaluwarsakan(d["deal_id"])


def sapu_paralel(n):
    """n proses sweeper SERENTAK (dua worker) terhadap DB instans yang sama."""
    backend = os.environ.get("P0_BACKEND_DIR") or str(BACKEND)
    cmd = [sys.executable, "-c", "import asyncio, engine_sweepers as e; print('SWEPT', asyncio.run(e.reservation_expiry_sweeper()))"]
    ps = [subprocess.Popen(cmd, cwd=backend, env={**os.environ}, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
          for _ in range(n)]
    for p in ps:
        _, err = p.communicate(timeout=240)
        assert p.returncode == 0, err[-600:]


def reconcile_ok(timeout=40):
    end = time.time() + timeout
    while True:
        x = ok(call(FINANCE, "GET", "/finance/reconcile"))["data"]
        if x["ok"] or time.time() > end:
            return x["ok"]
        time.sleep(1.5)


def batalkan(d, mode="full"):
    """Jalur batal yang ada — dipakai tes sebagai 'keputusan manusia' sekaligus pembersih."""
    return ok(call(OWNER, "POST", f"/deals/{d['deal_id']}/cancel",
                   json={"reason": "uji W1A keputusan manusia atas reservasi tertahan", "refund_mode": mode, "method": "transfer"}))


def sisa_hari(d):
    return (datetime.datetime.fromisoformat(row(d)["reserved_until"]) - datetime.datetime.now(datetime.timezone.utc)).total_seconds() / 86400


# ================================================================== kunci pengaturan
def test_kunci_terdaftar_dengan_bawaan_jawaban_pemilik_dan_validasi():
    rows = {r["key"]: r for r in ok(call(OWNER, "GET", "/settings", params={"group": "kebijakan"}))["data"]}
    assert rows[MODE]["default_value"] == "perpanjang" and rows[MODE]["options"] == ["perpanjang", "antrean_refund", "hangus"]
    assert not rows[MODE].get("unavailable"), "ketiga opsi sudah berperilaku"
    assert rows[DAYS]["default_value"] == 7 and rows[MAXX]["default_value"] == 2
    for k in (MODE, DAYS, MAXX):
        assert rows[k]["levels"] == ["org", "project"] and rows[k]["sensitive"] is True
    assert put(MODE, "ngawur").status_code == 400
    assert put(DAYS, 0).status_code == 400 and put(DAYS, 91).status_code == 400
    assert put(MAXX, -1).status_code == 400 and put(MAXX, 13).status_code == 400
    assert call(OWNER, "PUT", f"/settings/{MODE}", json={"value": "hangus"}).status_code == 400, "sensitif wajib alasan"
    assert put(MODE, "hangus", "cluster", "c1").status_code == 400, "tingkat klaster tidak sah"


# ================================================================== SSOT "booking fee terbayar"
def test_booking_fee_terbayar_dihitung_dari_kuitansi_bukan_penanda_salinan():
    """Kuitansi void tidak dihitung; refund/hangus dikurangkan. Org sintetis → tidak menyentuh buku org lain."""
    import reservation_expiry as rx
    org, did = f"org-w1a-uji-{uuid.uuid4().hex[:6]}", str(uuid.uuid4())
    base = {"org_id": org, "deal_id": did, "created_at": now()}
    mdb().receipts.insert_many([
        {**base, "id": str(uuid.uuid4()), "kind": "booking_fee", "amount": 5_000_000},
        {**base, "id": str(uuid.uuid4()), "kind": "booking_fee", "amount": 2_000_000, "status": "void"},
        {**base, "id": str(uuid.uuid4()), "kind": "booking_fee_refund", "amount": 1_000_000, "forfeited": 500_000},
        {**base, "id": str(uuid.uuid4()), "kind": "payment", "amount": 99_000_000}])   # bukan booking fee
    try:
        assert aio.run(rx.booking_fee_held(org, did)) == {"paid": 5_000_000, "returned": 1_500_000, "held": 3_500_000}
        assert aio.run(rx.booking_fee_held(org, "tidak-ada"))["held"] == 0
    finally:
        mdb().receipts.delete_many({"org_id": org})


def test_penanda_salinan_deal_tidak_dipercaya_dua_arah(world):
    """Penanda `booking_fee_status` berbohong: 'verified' tanpa kuitansi → tetap dilepas; 'unverified' padahal ada kuitansi → diperpanjang."""
    palsu = world.new_deal(booking_fee=FEE, book=False)                 # tagihan ada, TIDAK dibayar
    mdb().deals.update_one({"id": palsu["deal_id"]}, {"$set": {"booking_fee_status": "verified", "booking_fee_paid_at": now()}})
    nyata = deal_berbayar(world)
    mdb().deals.update_one({"id": nyata["deal_id"]}, {"$set": {"booking_fee_status": "unverified", "booking_fee_paid_at": None}})
    kedaluwarsa(palsu), kedaluwarsa(nyata)
    jalankan_sweeper()
    assert row(palsu)["status"] == "expired" and unit(palsu)["status"] == "available"
    assert row(nyata)["status"] == "reserved" and row(nyata)["reservation_extensions"] == 1 and unit(nyata)["status"] == "reserved"
    batalkan(nyata)


# ================================================================== tanpa booking fee terbayar: TIDAK berubah
def test_tanpa_booking_fee_terbayar_tetap_kedaluwarsa_dan_unit_dilepas(world):
    nol = world.new_deal(booking_fee=0, book=False)                   # tanpa booking fee
    belum = world.new_deal(booking_fee=FEE, book=False)               # ada tagihan, belum dibayar
    for d in (nol, belum):
        kedaluwarsa(d)
    jalankan_sweeper()
    for d in (nol, belum):
        assert row(d)["status"] == "expired" and row(d).get("reservation_extensions") is None
        u = unit(d)
        assert u["status"] == "available" and not u.get("reserved_by_deal")
        assert not tugas(f"deal.expiry_extend:{d['deal_id']}:1") and not tugas(f"deal.expiry_refund:{d['deal_id']}")
    assert inv(belum)["status"] == "cancelled", "tagihan yang belum dibayar tetap ditutup seperti sebelumnya"


# ================================================================== perpanjang (bawaan)
def test_bawaan_perpanjang_unit_tidak_dilepas_idempoten_dan_tetap_bisa_dibooking(world):
    d = deal_berbayar(world)
    ids = seed_dependents(d["deal_id"])
    try:
        kedaluwarsa(d)
        jalankan_sweeper()
        r = row(d)
        assert r["status"] == "reserved" and r["reservation_extensions"] == 1, r.get("status")
        assert 6.9 < sisa_hari(d) < 7.1, f"diperpanjang 7 hari dari sekarang, dapat {sisa_hari(d):.2f}"
        u = unit(d)
        assert u["status"] == "reserved" and u["reserved_by_deal"] == d["deal_id"], "unit TIDAK dilepas"
        log = r["reservation_extension_log"]
        assert len(log) == 1 and log[0]["n"] == 1 and log[0]["of"] == 2 and log[0]["booking_fee_held"] == FEE
        assert log[0]["policy_snapshot"][MODE]["value"] == "perpanjang"
        # turunan deal TIDAK ditutup (deal masih hidup)
        assert mdb().commissions.find_one({"id": ids["c_pend"]})["status"] == "pending"
        # tugas sales & Keuangan + notifikasi ke keduanya
        ts, tf = tugas(f"deal.expiry_extend:{d['deal_id']}:1"), tugas(f"deal.expiry_extend:fin:{d['deal_id']}:1")
        assert len(ts) == 1 and ts[0]["assigned_to"] == SALES and ts[0]["status"] == "open"
        assert len(tf) == 1 and tf[0]["assigned_to"] is None and tf[0]["status"] == "open"
        penerima = {n["user_email"] for n in notif(d, "diperpanjang")}
        assert SALES in penerima and FINANCE in penerima, penerima
        # idempoten: putaran sweeper berikutnya tidak memperpanjang lagi untuk jatuh tempo yang sama
        until = r["reserved_until"]
        jalankan_sweeper(), jalankan_sweeper()
        r2 = row(d)
        assert r2["reservation_extensions"] == 1 and r2["reserved_until"] == until and len(r2["reservation_extension_log"]) == 1
        assert len(tugas(f"deal.expiry_extend:{d['deal_id']}:1")) == 1 and len(notif(d, "diperpanjang")) == len(penerima)
        # pembeli yang sudah membayar masih bisa dikonfirmasi booking setelah diperpanjang
        ok(call(SALES, "POST", f"/deals/{d['deal_id']}/book", json={}))
        assert row(d)["status"] == "booked"
    finally:
        drop_seeds(ids)


def test_dua_worker_serentak_hanya_satu_perpanjangan_per_jatuh_tempo(world):
    d = deal_berbayar(world)
    kedaluwarsa(d)
    sapu_paralel(3)
    r = row(d)
    assert r["status"] == "reserved" and r["reservation_extensions"] == 1 and len(r["reservation_extension_log"]) == 1, r
    assert len(tugas(f"deal.expiry_extend:{d['deal_id']}:1")) == 1 and len(tugas(f"deal.expiry_extend:fin:{d['deal_id']}:1")) == 1
    batalkan(d)


def test_perpanjangan_habis_tidak_dilepas_diam_diam_tugas_sekali_lalu_manusia_memutuskan(world):
    pid = world.project_id
    d = deal_berbayar(world)
    try:
        ok(put(MAXX, 1, "project", pid))
        kedaluwarsa(d)
        jalankan_sweeper()                                              # perpanjangan ke-1
        assert row(d)["reservation_extensions"] == 1
        kedaluwarsa(d)
        jalankan_sweeper()                                              # jatuh tempo lagi, batas habis → TAHAN
        r = row(d)
        assert r["status"] == "reserved" and r["reservation_extensions"] == 1 and r["expiry_hold"]["max"] == 1, r.get("status")
        assert unit(d)["status"] == "reserved" and unit(d)["reserved_by_deal"] == d["deal_id"], "unit tetap ditahan"
        ts, tf = tugas(f"deal.expiry_hold:{d['deal_id']}"), tugas(f"deal.expiry_hold:fin:{d['deal_id']}")
        assert len(ts) == 1 and ts[0]["assigned_to"] == SALES and ts[0]["priority"] == "high"
        assert len(tf) == 1 and tf[0]["assigned_to"] is None and tf[0]["priority"] == "high"
        n_notif, hold_at = len(notif(d, "perpanjangan habis")), r["expiry_hold"]["at"]
        assert n_notif >= 2
        for _ in range(3):                                              # berulang kali: tidak ada tugas/notifikasi baru, tidak ada pelepasan
            jalankan_sweeper()
        r2 = row(d)
        assert r2["status"] == "reserved" and r2["expiry_hold"]["at"] == hold_at and r2["reservation_extensions"] == 1
        assert len(tugas(f"deal.expiry_hold:{d['deal_id']}")) == 1 and len(notif(d, "perpanjangan habis")) == n_notif
        assert unit(d)["status"] == "reserved"
        # keputusan manusia lewat jalur batal yang ada: unit dilepas, uang kembali ke pembeli
        out = batalkan(d)
        assert out["data"]["status"] == "cancelled" and unit(d)["status"] == "available"
        assert inv(d)["status"] == "refunded" and deposit(d) == 0
    finally:
        reset(MAXX, "project", pid)
    assert reconcile_ok()


def test_max_perpanjangan_nol_langsung_tertahan_tanpa_memperpanjang(world):
    pid = world.project_id
    d = deal_berbayar(world)
    try:
        ok(put(MAXX, 0, "project", pid))
        kedaluwarsa(d)
        jalankan_sweeper()
        r = row(d)
        assert r["status"] == "reserved" and r.get("reservation_extensions") is None and r["reserved_until"].startswith("2020")
        assert "expiry_hold" in r and len(tugas(f"deal.expiry_hold:{d['deal_id']}")) == 1
    finally:
        reset(MAXX, "project", pid)
        batalkan(d)


def test_lama_perpanjangan_dikonfigurasi_dan_dihitung_dari_saat_diproses(world):
    pid = world.project_id
    d = deal_berbayar(world)
    try:
        ok(put(DAYS, 3, "project", pid))
        kedaluwarsa(d)
        jalankan_sweeper()
        assert 2.9 < sisa_hari(d) < 3.1, sisa_hari(d)   # jatuh tempo 2020 + 3 hari masih lampau → dihitung dari sekarang
    finally:
        reset(DAYS, "project", pid)
        batalkan(d)


# ================================================================== antrean refund
def test_antrean_refund_unit_dilepas_uang_tetap_titipan_keuangan_diberi_tugas_refund(world):
    pid = world.project_id
    d = deal_berbayar(world)
    ids = seed_dependents(d["deal_id"])
    try:
        ok(put(MODE, "antrean_refund", "project", pid))
        kedaluwarsa(d)
        jalankan_sweeper()
        r = row(d)
        assert r["status"] == "expired" and r["expiry_paid_fee"]["mode"] == "antrean_refund" and r["expiry_paid_fee"]["held"] == FEE
        u = unit(d)
        assert u["status"] == "available" and not u.get("reserved_by_deal")
        # penutup bersama dipakai pada jalur pelepasan (turunan ditutup seperti batal)
        assert mdb().commissions.find_one({"id": ids["c_pend"]})["status"] == "cancelled"
        assert mdb().marketing_fees.find_one({"id": ids["f_sub"]})["status"] == "cancelled"
        assert mdb().financing_apps.find_one({"id": ids["fin"]})["status"] == "cancelled"
        assert mdb().coupons.find_one({"id": ids["coupon"]})["used_count"] == 0
        # uang TETAP tercatat sebagai titipan (kewajiban), tanpa jurnal baru
        i = inv(d)
        assert i["paid"] == FEE and i["refunded_total"] == 0 and i["forfeited_total"] == 0 and i["status"] == "paid"
        assert deposit(d) == FEE
        t = tugas(f"deal.expiry_refund:{d['deal_id']}")
        assert len(t) == 1 and t[0]["status"] == "open" and t[0]["assigned_to"] is None and t[0]["priority"] == "high"
        assert FINANCE in {n["user_email"] for n in notif(d, "menunggu refund")}
        jalankan_sweeper(), jalankan_sweeper()
        assert len(tugas(f"deal.expiry_refund:{d['deal_id']}")) == 1
        # Keuangan mengeksekusi lewat jalur refund booking fee yang SUDAH ada
        det = ok(call(FINANCE, "GET", f"/booking-fee/deals/{d['deal_id']}"))["data"]
        assert det["refund"]["eligible"] is True and det["refund"]["refundable"] == FEE
        ok(call(FINANCE, "POST", f"/booking-fee/deals/{d['deal_id']}/refund", json={"amount": FEE, "method": "transfer"}))
        assert deposit(d) == 0 and inv(d)["status"] == "refunded"
    finally:
        reset(MODE, "project", pid)
        drop_seeds(ids)
    assert reconcile_ok()


# ================================================================== hangus
def test_hangus_unit_dilepas_booking_fee_diakui_hangus_lewat_jalur_yang_ada(world):
    pid = world.project_id
    d = deal_berbayar(world)
    try:
        ok(put(MODE, "hangus", "project", pid))
        kedaluwarsa(d)
        jalankan_sweeper()
        r = row(d)
        assert r["status"] == "expired" and r["expiry_paid_fee"]["mode"] == "hangus" and r["expiry_paid_fee"]["outcome"] == "hangus"
        assert unit(d)["status"] == "available"
        i = inv(d)
        assert i["status"] == "forfeited" and i["forfeited_total"] == FEE and i["refunded_total"] == 0
        assert deposit(d) == 0
        je = list(mdb().journal_entries.find({"source_event": {"$regex": f"^bf:{i['id']}:forfeit:"}}))
        assert len(je) == 1, "tepat satu jurnal hangus"
        lines = {(ln["account_code"], int(ln.get("debit") or 0), int(ln.get("credit") or 0)) for ln in je[0]["lines"]}
        assert ("2-1450", FEE, 0) in lines and ("4-1200", 0, FEE) in lines
        assert FINANCE in {n["user_email"] for n in notif(d, "hangus")}
        jalankan_sweeper(), jalankan_sweeper()        # idempoten: tak ada jurnal kedua
        assert mdb().journal_entries.count_documents({"source_event": {"$regex": f"^bf:{i['id']}:forfeit:"}}) == 1
    finally:
        reset(MODE, "project", pid)
    assert reconcile_ok()


# ================================================================== penimpaan per proyek
def test_penimpaan_proyek_mengalahkan_org_proyek_lain_mengikuti_org(world, world2):
    a, b = deal_berbayar(world), deal_berbayar(world2)
    try:
        ok(put(MODE, "antrean_refund", "project", world.project_id))     # proyek 1 → antrean refund; proyek 2 → bawaan (perpanjang)
        eff = lambda pid: ok(call(OWNER, "GET", "/settings/effective", params={"keys": MODE, "project_id": pid}))["data"][MODE]   # noqa: E731
        assert eff(world.project_id) == "antrean_refund" and eff(world2.project_id) == "perpanjang"
        kedaluwarsa(a), kedaluwarsa(b)
        jalankan_sweeper()
        assert row(a)["status"] == "expired" and unit(a)["status"] == "available"
        assert row(b)["status"] == "reserved" and row(b)["reservation_extensions"] == 1 and unit(b)["status"] == "reserved"
    finally:
        reset(MODE, "project", world.project_id)
        batalkan(b)
        ok(call(FINANCE, "POST", f"/booking-fee/deals/{a['deal_id']}/refund", json={"amount": FEE, "method": "transfer"}))
    assert reconcile_ok()


def test_rekonsiliasi_hijau_akhir():
    assert reconcile_ok(), ok(call(FINANCE, "GET", "/finance/reconcile"))["data"]
