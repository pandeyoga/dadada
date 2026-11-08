"""Regresi W1-B #9 — ganti skema pembayaran SETELAH ada pembayaran (IN-14): pemetaan alokasi (`payment.scheme_change.allocation`).

    API_BASE=http://localhost:8073/api DB_NAME=sipro_w1b python -m pytest backend/tests/p0/test_w1b_alokasi_skema.py -n 0 -q --noconftest

Sebelum W1-B: ganti skema pada deal yang sudah dibayar langsung disusun ulang (label cocok) atau ditolak "terbitkan adendum"
(label berbeda) — Keuangan tidak punya jalan untuk memetakan uang yang sudah masuk. Sesudah: penerapan DITAHAN (HTTP 202) sampai
Keuangan menyerahkan pemetaan per kuitansi (bawaan) atau mengonfirmasi hitungan sistem; semua opsi diuji di sini.
Tiap tes membuat deal sendiri; pengaturan org yang diubah dikembalikan di `finally`.
"""
import os
import sys
import time
from contextlib import contextmanager

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from test_p0_masuk import FINANCE, MANAGER, OWNER, SALES, World, ar, call, convert, ok, pay, race, upload_proof  # noqa: E402

FINLEAD = "finlead@sipro.co.id"
KEY = "payment.scheme_change.allocation"
TARGET = "Cash keras (DP 80% + pelunasan)"      # 2 termin: 400 jt + 100 jt (harga unit 500 jt)
ALASAN = "uji pemetaan alokasi W1-B"


@pytest.fixture(scope="module")
def world():
    return World()


def _mongo():
    from pymongo import MongoClient
    url = os.environ.get("MONGO_URL") or ("mongo" + "db://127.0.0.1:27017")
    return MongoClient(url)[os.environ.get("DB_NAME", "sipro_w1b")]


@contextmanager
def setting(value, key=KEY, scope="org", scope_id=None):
    """Ubah pengaturan sementara; SELALU dikembalikan (reset) — suite penuh memakai org yang sama."""
    body = {"value": value, "reason": "uji W1-B", "scope": scope}
    if scope_id:
        body["scope_id"] = scope_id
    ok(call(OWNER, "PUT", f"/settings/{key}", json=body))
    try:
        yield
    finally:
        call(OWNER, "POST", f"/settings/{key}/reset", params={"scope": scope, **({"scope_id": scope_id} if scope_id else {})})


def _paid_deal(world):
    """Deal 'Cash Bertahap (3x)' dengan dua kuitansi nyata: 100 jt → DP 30% dan 60 jt → Termin 40%."""
    d = world.new_deal()
    did = d["deal_id"]
    inv = ar(did)["data"]
    r1 = ok(pay(did, 100_000_000, allocations=[{"item_id": inv["items"][0]["id"], "amount": 100_000_000}]))["data"]["receipt"]
    r2 = ok(pay(did, 60_000_000, allocations=[{"item_id": inv["items"][1]["id"], "amount": 60_000_000}]))["data"]["receipt"]
    d.update(r1=r1["id"], r2=r2["id"], old_ids=[i["id"] for i in inv["items"]])
    return d


def _schedule(did, world, scheme=TARGET, email=FINANCE, reason=ALASAN):
    return call(email, "POST", f"/finance/ar/{did}/schedule", json={"scheme_id": world.scheme[scheme], "reason": reason})


def _hold(world, d, scheme=TARGET):
    r = _schedule(d["deal_id"], world, scheme)
    assert r.status_code == 202, (r.status_code, r.text[:400])
    assert r.json()["held"] is True
    return r.json()["data"]


def _map(r1, r2, a1, a2):
    """a1/a2 = [(no, nominal)] untuk kuitansi 1 dan 2."""
    return [{"receipt_id": r1, "allocations": [{"no": n, "amount": a} for n, a in a1]},
            {"receipt_id": r2, "allocations": [{"no": n, "amount": a} for n, a in a2]}]


def _apply(rid, mapping=None, reason=ALASAN, confirm=False, email=FINLEAD):
    body = {"reason": reason, "confirm": confirm}
    if mapping is not None:
        body["mapping"] = mapping
    return call(email, "POST", f"/finance/scheme-changes/{rid}/apply", json=body)


def _receipt(did, rid):
    return next(r for r in ar(did)["receipts"] if r["id"] == rid)


def _reconcile_ok(timeout=30):
    end = time.time() + timeout
    while True:
        d = ok(call(FINANCE, "GET", "/finance/reconcile"))["data"]
        if d["ok"] or time.time() > end:
            return d["ok"]
        time.sleep(1.5)


# ================================================================== manual_keuangan (BAWAAN)
def test_manual_ganti_skema_sesudah_dibayar_ditahan(world):
    d = _paid_deal(world)
    req = _hold(world, d)
    assert req["mode"] == "manual_keuangan" and req["status"] == "menunggu_pemetaan"
    assert req["paid_total"] == 160_000_000 and len(req["preview"]) == 2 and len(req["receipts"]) == 2
    # jadwal & kuitansi lama TIDAK berubah
    inv = ar(d["deal_id"])["data"]
    assert [i["id"] for i in inv["items"]] == d["old_ids"] and int(inv["paid"]) == 160_000_000
    assert inv["scheme_id"] == world.scheme["Cash Bertahap (3x)"]
    assert _receipt(d["deal_id"], d["r1"])["allocations"][0]["item_id"] == d["old_ids"][0]
    lst = ok(call(FINANCE, "GET", "/finance/scheme-changes", params={"deal_id": d["deal_id"]}))
    assert [x["id"] for x in lst["data"]] == [req["id"]]


def test_manual_validasi_pemetaan_ditolak(world):
    d = _paid_deal(world)
    req = _hold(world, d)
    rid, r1, r2 = req["id"], d["r1"], d["r2"]
    # peran tanpa finance:approve
    assert _apply(rid, _map(r1, r2, [(1, 100_000_000)], [(1, 60_000_000)]), email=MANAGER).status_code == 403
    assert _apply(rid, _map(r1, r2, [(1, 100_000_000)], [(1, 60_000_000)]), email=SALES).status_code == 403
    cases = {
        "alasan pendek": (_map(r1, r2, [(1, 100_000_000)], [(1, 60_000_000)]), "pendek"),
        "tanpa mapping": (None, ALASAN),
        "kuitansi belum dipetakan": ([{"receipt_id": r1, "allocations": [{"no": 1, "amount": 100_000_000}]}], ALASAN),
        "jumlah kurang": (_map(r1, r2, [(1, 100_000_000)], [(1, 50_000_000)]), ALASAN),
        "jumlah lebih": (_map(r1, r2, [(1, 100_000_000)], [(1, 70_000_000)]), ALASAN),
        "negatif": (_map(r1, r2, [(1, 110_000_000), (2, -10_000_000)], [(1, 60_000_000)]), ALASAN),
        "termin tidak ada": (_map(r1, r2, [(3, 100_000_000)], [(1, 60_000_000)]), ALASAN),
        "kuitansi asing": (_map(r1, "bukan-kuitansi", [(1, 100_000_000)], [(1, 60_000_000)]), ALASAN),
        "kuitansi ganda": (_map(r1, r1, [(1, 100_000_000)], [(1, 100_000_000)]), ALASAN),
    }
    for nama, (mp, why) in cases.items():
        r = _apply(rid, mp, reason=why)
        assert r.status_code == 400, (nama, r.status_code, r.text[:300])
    # kelebihan per termin: 100 jt + 60 jt ke termin 2 (nilai 100 jt)
    r = _apply(rid, _map(r1, r2, [(2, 100_000_000)], [(2, 60_000_000)]))
    assert r.status_code == 400 and "kelebihan" in r.text, r.text[:300]
    inv = ar(d["deal_id"])["data"]
    assert [i["id"] for i in inv["items"]] == d["old_ids"], "tak satu pun penolakan boleh mengubah AR"
    assert ok(call(FINANCE, "GET", f"/finance/scheme-changes/{rid}"))["data"]["status"] == "menunggu_pemetaan"


def test_manual_terapkan_jejak_void_dan_rekonsiliasi(world):
    d = _paid_deal(world)
    req = _hold(world, d)
    # 100 jt (kuitansi 1) → termin 1; 60 jt (kuitansi 2) dibelah: 40 jt termin 1 + 20 jt termin 2
    out = ok(_apply(req["id"], _map(d["r1"], d["r2"], [(1, 100_000_000)], [(1, 40_000_000), (2, 20_000_000)])))["data"]
    assert out["status"] == "diterapkan" and out["applied_by"] == FINLEAD and out["apply_reason"] == ALASAN
    inv = ar(d["deal_id"])["data"]
    assert inv["scheme_id"] == world.scheme[TARGET] and int(inv["paid"]) == 160_000_000
    t1, t2 = inv["items"]
    assert (t1["paid_amount"], t2["paid_amount"]) == (140_000_000, 20_000_000)
    assert t1["id"] not in d["old_ids"]
    r1, r2 = _receipt(d["deal_id"], d["r1"]), _receipt(d["deal_id"], d["r2"])
    assert [(a["item_id"], a["amount"]) for a in r1["allocations"]] == [(t1["id"], 100_000_000)]
    assert sorted((a["item_id"], a["amount"]) for a in r2["allocations"]) == sorted([(t1["id"], 40_000_000), (t2["id"], 20_000_000)])
    # kuitansi lama utuh sebagai jejak: nominal & nomor tetap, alokasi lama tersimpan
    assert int(r1["amount"]) == 100_000_000 and r1.get("status") != "void"
    assert r1["allocation_history"][0]["previous"][0]["item_id"] == d["old_ids"][0]
    assert r1["allocation_history"][0]["reason"] == ALASAN and r1["allocation_history"][0]["by"] == FINLEAD
    assert _reconcile_ok(), "ubah alokasi tidak boleh mengubah kas/GL"
    # void kuitansi sesudah pemetaan membalik TERMIN YANG BENAR (tautan tidak putus)
    ok(call(FINLEAD, "POST", f"/finance/ar/receipts/{d['r2']}/void", json={"reason": "uji void sesudah pemetaan"}))
    inv = ar(d["deal_id"])["data"]
    assert (inv["items"][0]["paid_amount"], inv["items"][1]["paid_amount"]) == (100_000_000, 0) and int(inv["paid"]) == 100_000_000
    assert _reconcile_ok()
    # permintaan yang sudah diterapkan tidak bisa diterapkan lagi
    assert _apply(req["id"], _map(d["r1"], d["r2"], [(1, 100_000_000)], [(1, 60_000_000)])).status_code == 400


def test_permintaan_terbuka_idempoten_dan_batal(world):
    d = _paid_deal(world)
    a = _hold(world, d)
    b = _hold(world, d)                                      # klik ganda / kirim ulang → permintaan yang SAMA
    assert a["id"] == b["id"]
    r = _schedule(d["deal_id"], world, "Cash bertahap (DP 80% + 6× cicilan)")
    assert r.status_code == 400 and "Sudah ada permintaan" in r.text, r.text[:300]
    assert call(FINLEAD, "POST", f"/finance/scheme-changes/{a['id']}/cancel", json={"reason": "x"}).status_code == 400
    c = ok(call(FINLEAD, "POST", f"/finance/scheme-changes/{a['id']}/cancel", json={"reason": "batal karena salah pilih skema"}))["data"]
    assert c["status"] == "dibatalkan"
    assert ar(d["deal_id"])["data"]["scheme_id"] == world.scheme["Cash Bertahap (3x)"]
    assert _apply(a["id"], _map(d["r1"], d["r2"], [(1, 100_000_000)], [(1, 60_000_000)])).status_code == 400
    assert _hold(world, d, "Cash bertahap (DP 80% + 6× cicilan)")["id"] != a["id"]      # kini boleh mengajukan yang lain


def test_apply_serentak_hanya_satu(world):
    d = _paid_deal(world)
    req = _hold(world, d)
    mp = _map(d["r1"], d["r2"], [(1, 100_000_000)], [(1, 60_000_000)])
    rs = race([lambda: _apply(req["id"], mp), lambda: _apply(req["id"], mp, email=FINANCE)])
    assert sorted(r.status_code for r in rs).count(200) == 1, [(r.status_code, r.text[:120]) for r in rs]
    inv = ar(d["deal_id"])["data"]
    assert int(inv["paid"]) == 160_000_000 and inv["items"][0]["paid_amount"] == 160_000_000
    assert len([r for r in ar(d["deal_id"])["receipts"] if r["id"] in (d["r1"], d["r2"])
                for _ in r.get("allocation_history") or []]) == 2, "pemetaan ditulis SEKALI"


def test_tidak_ditahan_bila_tanpa_uang_nyata_atau_skema_sama(world):
    # (a) hanya booking fee/titipan → skema tetap boleh diganti seketika (dialihkan sistem ke DP baru)
    d = world.new_deal(booking_fee=5_000_000, book=False)
    ok(call(FINANCE, "POST", f"/booking-fee/deals/{d['deal_id']}/pay",
            json={"amount": 5_000_000, "method": "transfer", "proof_file_ids": [upload_proof()]}))
    ok(call(SALES, "POST", f"/deals/{d['deal_id']}/book", json={}))
    assert int(ar(d["deal_id"])["data"]["paid"]) == 5_000_000
    r = _schedule(d["deal_id"], world)
    assert r.status_code == 200, (r.status_code, r.text[:300])
    inv = ar(d["deal_id"])["data"]
    assert inv["scheme_id"] == world.scheme[TARGET] and int(inv["paid"]) == 5_000_000
    # (b) uang nyata tetapi skema SAMA (regenerasi) → alokasi per label dipertahankan, tidak ditahan
    d2 = _paid_deal(world)
    r = _schedule(d2["deal_id"], world, "Cash Bertahap (3x)")
    assert r.status_code == 200, (r.status_code, r.text[:300])
    assert ar(d2["deal_id"])["data"]["items"][0]["paid_amount"] == 100_000_000


def test_deal_batal_ditolak(world):
    d = _paid_deal(world)
    req = _hold(world, d)
    # deal berbayar tak bisa dibatalkan satu klik (alur Pembatalan Kontrak formal) → tandai batal langsung di DB uji
    _mongo().deals.update_one({"id": d["deal_id"]}, {"$set": {"status": "cancelled"}})
    r = _apply(req["id"], _map(d["r1"], d["r2"], [(1, 100_000_000)], [(1, 60_000_000)]))
    assert r.status_code == 400 and ("batal" in r.text.lower()), (r.status_code, r.text[:300])
    r = _schedule(d["deal_id"], world, "Cash bertahap (DP 80% + 6× cicilan)")
    assert r.status_code == 400 and "batal" in r.text.lower(), (r.status_code, r.text[:300])


# ================================================================== urut_termin_tertua & proporsional
def test_urut_termin_tertua_hitung_pratinjau_dan_konfirmasi(world):
    d = _paid_deal(world)
    with setting("urut_termin_tertua"):
        req = _hold(world, d)
    assert req["mode"] == "urut_termin_tertua" and req["status"] == "menunggu_konfirmasi"
    # hasil hitung sistem: 100 jt + 60 jt mengisi termin 1 (jatuh tempo terlama, nilai 400 jt)
    prop = {p["receipt_id"]: [(a["no"], a["amount"]) for a in p["allocations"]] for p in req["proposal"]}
    assert prop[d["r1"]] == [(1, 100_000_000)] and prop[d["r2"]] == [(1, 60_000_000)]
    assert _apply(req["id"]).status_code == 400                                     # tanpa konfirmasi
    assert _apply(req["id"], _map(d["r1"], d["r2"], [(2, 100_000_000)], [(2, 60_000_000)]), confirm=True).status_code == 400
    assert ar(d["deal_id"])["data"]["scheme_id"] == world.scheme["Cash Bertahap (3x)"], "penolakan tidak mengubah AR"
    out = ok(_apply(req["id"], confirm=True))["data"]
    assert out["status"] == "diterapkan"
    inv = ar(d["deal_id"])["data"]
    assert (inv["items"][0]["paid_amount"], inv["items"][1]["paid_amount"]) == (160_000_000, 0)
    assert _receipt(d["deal_id"], d["r1"])["allocations"][0]["item_id"] == inv["items"][0]["id"]
    assert _reconcile_ok()


def test_proporsional_hitung_pratinjau_dan_konfirmasi(world):
    d = _paid_deal(world)
    with setting("proporsional"):
        req = _hold(world, d)
    assert req["mode"] == "proporsional" and req["status"] == "menunggu_konfirmasi"
    tot = {}
    for p in req["proposal"]:
        for a in p["allocations"]:
            tot[a["no"]] = tot.get(a["no"], 0) + a["amount"]
    assert tot == {1: 128_000_000, 2: 32_000_000}, tot          # 160 jt dibagi sebanding 400 jt : 100 jt
    out = ok(_apply(req["id"], confirm=True))["data"]
    inv = ar(d["deal_id"])["data"]
    assert out["status"] == "diterapkan" and (inv["items"][0]["paid_amount"], inv["items"][1]["paid_amount"]) == (128_000_000, 32_000_000)
    assert int(inv["paid"]) == 160_000_000
    assert _reconcile_ok()


def test_hitung_sistem_tidak_muat_ditolak_saat_diajukan(world):
    d = world.new_deal()
    did = d["deal_id"]
    inv = ar(did)["data"]
    ok(pay(did, 150_000_000, allocations=[{"item_id": inv["items"][0]["id"], "amount": 150_000_000}]))
    ok(pay(did, 200_000_000, allocations=[{"item_id": inv["items"][1]["id"], "amount": 200_000_000}]))
    # skema KPR 100% porsi bank: setoran pembeli 350 jt tidak boleh dipasang ke porsi bank → tidak muat
    with setting("urut_termin_tertua"):
        r = _schedule(did, world, "KPR (DP 0% + pencairan bank)")
    assert r.status_code == 400 and "tidak muat" in r.text, r.text[:300]
    assert ar(did)["data"]["scheme_id"] == world.scheme["Cash Bertahap (3x)"]


def test_override_tingkat_proyek(world):
    d = _paid_deal(world)
    with setting("proporsional", scope="project", scope_id=world.project_id):
        req = _hold(world, d)
    assert req["mode"] == "proporsional", "penimpaan proyek menang atas bawaan organisasi"
    d2 = _paid_deal(world)
    assert _hold(world, d2)["mode"] == "manual_keuangan", "tanpa penimpaan → bawaan organisasi"


def test_kebijakan_direkam_saat_lahir_pengaturan_berganti_tidak_mengubah(world):
    d = _paid_deal(world)
    with setting("urut_termin_tertua"):
        req = _hold(world, d)
    # pengaturan sudah kembali ke manual, tetapi permintaan ini tetap memakai kebijakan saat ia lahir
    got = ok(call(FINANCE, "GET", f"/finance/scheme-changes/{req['id']}"))["data"]
    assert got["mode"] == "urut_termin_tertua" and got["policy_snapshot"]["payment_scheme_change_allocation"]["value"] == "urut_termin_tertua"
    assert _apply(req["id"], confirm=False).status_code == 400
    assert ok(_apply(req["id"], confirm=True))["data"]["status"] == "diterapkan"


# ================================================================== jalur lain: skema kontrak
def test_set_for_contract_dan_ganti_jenis_ditahan_lalu_diterapkan(world):
    d = _paid_deal(world)
    cid = convert(d)
    # (a) tetapkan skema lain (jenis sama) pada kontrak → ditahan
    r = call(FINLEAD, "POST", f"/payment-schemes/contracts/{cid}",
             json={"scheme_id": world.scheme["Cash bertahap (DP 80% + 6× cicilan)"], "reason": "uji skema kontrak W1-B"})
    assert r.status_code == 202, (r.status_code, r.text[:300])
    req = r.json()["data"]
    assert req["op"] == "contract_scheme_id" and req["contract_id"] == cid
    k = ok(call(OWNER, "GET", f"/contracts/{cid}"))["data"]
    assert k.get("payment_scheme_id") != world.scheme["Cash bertahap (DP 80% + 6× cicilan)"]
    mp = _map(d["r1"], d["r2"], [(1, 100_000_000)], [(1, 60_000_000)])
    assert ok(_apply(req["id"], mp))["data"]["status"] == "diterapkan"
    k = ok(call(OWNER, "GET", f"/contracts/{cid}"))["data"]
    assert k["payment_scheme_id"] == world.scheme["Cash bertahap (DP 80% + 6× cicilan)"]
    inv = ar(d["deal_id"])["data"]
    assert inv["scheme_id"] == world.scheme["Cash bertahap (DP 80% + 6× cicilan)"] and inv["items"][0]["paid_amount"] == 160_000_000
    assert _reconcile_ok()


def test_ganti_jenis_skema_kontrak_dengan_uang_nyata_ditahan(world):
    d = _paid_deal(world)
    cid = convert(d)
    r = call(FINLEAD, "POST", f"/contracts/{cid}/scheme", json={"scheme": "cash_keras", "reason": "uji ganti jenis W1-B"})
    assert r.status_code == 202, (r.status_code, r.text[:300])
    req = r.json()["data"]
    assert req["op"] == "contract_kind" and req["mode"] == "manual_keuangan"
    assert ok(call(OWNER, "GET", f"/contracts/{cid}"))["data"]["scheme"] == "cash_bertahap", "kontrak belum berubah"
    assert [p["amount"] for p in req["preview"]] == [400_000_000, 100_000_000]
    mp = _map(d["r1"], d["r2"], [(1, 100_000_000)], [(1, 60_000_000)])
    assert ok(_apply(req["id"], mp))["data"]["status"] == "diterapkan"
    assert ok(call(OWNER, "GET", f"/contracts/{cid}"))["data"]["scheme"] == "cash_keras"
    assert ar(d["deal_id"])["data"]["items"][0]["paid_amount"] == 160_000_000
    assert _reconcile_ok()
