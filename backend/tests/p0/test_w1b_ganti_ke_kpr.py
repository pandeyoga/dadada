"""Regresi W1-B #14 — ganti skema KONTRAK ke KPR setelah kontrak dibuat (FN-11): `contract.scheme_change_to_kpr`.

    API_BASE=http://localhost:8073/api DB_NAME=sipro_w1b python -m pytest backend/tests/p0/test_w1b_ganti_ke_kpr.py -n 0 -q --noconftest

Sebelum W1-B: `POST /contracts/{id}/scheme {"scheme":"kpr"}` → 200, tetapi komponen KPR-only (BANK_FEE, INSURANCE) tidak pernah
ditagih. Sesudah: bawaan MENOLAK (400, petunjuk batalkan + kontrak baru) di SEMUA jalur (jenis kontrak, jadwal AR, skema kontrak);
`izinkan_manual` = perilaku lama; `hitung_ulang_dengan_persetujuan` = amandemen all-in yang menghitung ulang komponen KPR.
Tiap tes membuat deal sendiri; pengaturan org/proyek yang diubah dikembalikan di `finally`.
"""
import os
import sys
import time
from contextlib import contextmanager

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from test_p0_masuk import FINANCE, OWNER, SALES, TAG, World, ar, call, convert, ok, pay  # noqa: E402

FINLEAD = "finlead@sipro.co.id"
KEY = "contract.scheme_change_to_kpr"


@pytest.fixture(scope="module")
def world():
    return World()


@contextmanager
def setting(value, scope="org", scope_id=None):
    body = {"value": value, "reason": "uji W1-B", "scope": scope}
    if scope_id:
        body["scope_id"] = scope_id
    ok(call(OWNER, "PUT", f"/settings/{KEY}", json=body))
    try:
        yield
    finally:
        call(OWNER, "POST", f"/settings/{KEY}/reset", params={"scope": scope, **({"scope_id": scope_id} if scope_id else {})})


def _allin_id(code="EXCLUDE"):
    rows = ok(call(SALES, "GET", "/allin-schemes"))["data"]
    return next(s["id"] for s in rows if s["code"] == code)


def _contract(world, scheme="Cash Bertahap (3x)", allin=True):
    """Deal → booking → Jadikan Pembeli (kontrak berjenis cash). Dengan `allin` skema biaya all-in EXCLUDE ikut tersnapshot."""
    unit = world.units[world.next_unit]
    world.next_unit += 1
    phone = "+62812" + str(int(time.time() * 1000))[-9:]
    lead = ok(call(SALES, "POST", "/leads", json={"name": f"Uji KPR {TAG} {world.next_unit}", "phone": phone, "source": "manual"}))["data"]
    body = {"unit_id": unit["id"], "lead_id": lead["id"], "booking_fee": 0, "scheme_id": world.scheme[scheme]}
    if allin:
        body["allin_scheme_id"] = _allin_id()
    deal = ok(call(SALES, "POST", "/deals/reserve", json=body))["data"]
    ok(call(SALES, "POST", f"/deals/{deal['id']}/book", json={}))
    d = {"deal_id": deal["id"], "unit_code": unit["code"], "project_id": world.project_id}
    d["contract_id"] = convert(d)
    return d


def _kontrak(cid):
    return ok(call(OWNER, "GET", f"/contracts/{cid}"))["data"]


def _komponen(cid):
    return {c["code"]: int(c.get("amount") or 0) for c in (_kontrak(cid).get("costs") or {}).get("components") or []}


def _reconcile_ok(timeout=30):
    end = time.time() + timeout
    while True:
        d = ok(call(FINANCE, "GET", "/finance/reconcile"))["data"]
        if d["ok"] or time.time() > end:
            return d["ok"]
        time.sleep(1.5)


def _kpr_scheme_id(world):
    return world.scheme["Standar KPR (DP 20%)"]


# ================================================================== tolak_buat_baru (BAWAAN)
def test_bawaan_tolak_ganti_jenis_kontrak_ke_kpr(world):
    d = _contract(world)
    before = _komponen(d["contract_id"])
    assert "BANK_FEE" not in before                                    # tak ikut karena dipesan sebagai tunai
    r = call(FINANCE, "POST", f"/contracts/{d['contract_id']}/scheme", json={"scheme": "kpr", "reason": "uji W1-B"})
    assert r.status_code == 400, (r.status_code, r.text[:300])
    msg = r.json()["detail"]
    assert "KPR" in msg and "batalkan" in msg.lower() and "kontrak baru" in msg.lower(), msg
    k = _kontrak(d["contract_id"])
    assert k["scheme"] == "cash_bertahap" and _komponen(d["contract_id"]) == before
    skema = {s["id"]: s for s in ok(call(OWNER, "GET", "/payment-schemes"))["data"]}
    assert skema[ar(d["deal_id"])["data"]["scheme_id"]]["kind"] == "cash_bertahap", "AR tidak disentuh"


def test_bawaan_tolak_juga_lewat_jadwal_ar_dan_tidak_menghalangi_arah_sebaliknya(world):
    d = _contract(world)
    r = call(FINANCE, "POST", f"/finance/ar/{d['deal_id']}/schedule", json={"scheme_id": _kpr_scheme_id(world)})
    assert r.status_code == 400 and "kontrak baru" in r.text.lower(), (r.status_code, r.text[:300])
    assert ar(d["deal_id"])["data"]["scheme_id"] == world.scheme["Cash Bertahap (3x)"]
    # skema kontrak yang berjenis KPR tidak bisa ditempelkan ke kontrak tunai (jalur ketiga, sudah ditolak sebelum W1-B)
    r = call(FINLEAD, "POST", f"/payment-schemes/contracts/{d['contract_id']}",
             json={"scheme_id": _kpr_scheme_id(world), "reason": "uji W1-B"})
    assert r.status_code == 400, (r.status_code, r.text[:300])
    assert _kontrak(d["contract_id"])["scheme"] == "cash_bertahap"


@contextmanager
def _pemicu_spr():
    """ASUMSI tes 'belum ada kontrak': sejak W1-A pemicu bawaan = booking dikonfirmasi, yang LANGSUNG membuat kontrak. Tes ini
    menyetel `spr_signed` (tingkat org) selama berjalan agar premis 'belum ada kontrak' berlaku; SELALU dikembalikan."""
    ok(call(OWNER, "PUT", "/settings/lead.won_trigger", json={"value": "spr_signed", "reason": "uji W1-B tanpa kontrak", "scope": "org"}))
    try:
        yield
    finally:
        call(OWNER, "POST", "/settings/lead.won_trigger/reset", params={"scope": "org"})


def test_tanpa_kontrak_dan_arah_non_kpr_tidak_dihalangi(world):
    # belum ada kontrak: komponen KPR-only dihitung saat kontrak lahir → ganti jadwal ke KPR tetap boleh
    with _pemicu_spr():
        _tanpa_kontrak_ganti_ke_kpr(world)
    # kontrak tunai → tunai lain tidak dihalangi gerbang KPR
    d = _contract(world)
    r = call(FINANCE, "POST", f"/contracts/{d['contract_id']}/scheme", json={"scheme": "cash_keras", "reason": "uji W1-B"})
    assert r.status_code == 200 and r.json()["data"]["scheme"] == "cash_keras", r.text[:300]


def test_bawaan_booking_langsung_membuat_kontrak_sehingga_ganti_jadwal_ke_kpr_ditolak(world):
    """Interaksi W1-A × W1-B: dengan pemicu bawaan (booking dikonfirmasi) kontrak sudah ada sejak booking, maka gerbang
    FN-11 (`tolak_buat_baru`) berlaku juga untuk jadwal AR — skema KPR harus dipilih sejak reservasi."""
    unit = world.units[world.next_unit]
    world.next_unit += 1
    lead = ok(call(SALES, "POST", "/leads", json={"name": f"Uji KPR3 {TAG}", "phone": "+62813" + str(int(time.time() * 1000))[-9:], "source": "manual"}))["data"]
    deal = ok(call(SALES, "POST", "/deals/reserve", json={"unit_id": unit["id"], "lead_id": lead["id"], "booking_fee": 0,
                                                          "scheme_id": world.scheme["Cash Bertahap (3x)"]}))["data"]
    ok(call(SALES, "POST", f"/deals/{deal['id']}/book", json={}))
    r = call(FINANCE, "POST", f"/finance/ar/{deal['id']}/schedule", json={"scheme_id": _kpr_scheme_id(world)})
    assert r.status_code == 400 and "KPR" in r.text, (r.status_code, r.text[:300])


def _tanpa_kontrak_ganti_ke_kpr(world):
    unit = world.units[world.next_unit]
    world.next_unit += 1
    lead = ok(call(SALES, "POST", "/leads", json={"name": f"Uji KPR2 {TAG}", "phone": "+62813" + str(int(time.time() * 1000))[-9:], "source": "manual"}))["data"]
    deal = ok(call(SALES, "POST", "/deals/reserve", json={"unit_id": unit["id"], "lead_id": lead["id"], "booking_fee": 0,
                                                          "scheme_id": world.scheme["Cash Bertahap (3x)"]}))["data"]
    ok(call(SALES, "POST", f"/deals/{deal['id']}/book", json={}))
    r = call(FINANCE, "POST", f"/finance/ar/{deal['id']}/schedule", json={"scheme_id": _kpr_scheme_id(world)})
    assert r.status_code == 200, (r.status_code, r.text[:300])


# ================================================================== izinkan_manual = perilaku lama
def test_izinkan_manual_perilaku_lama(world):
    d = _contract(world)
    with setting("izinkan_manual"):
        out = ok(call(FINANCE, "POST", f"/contracts/{d['contract_id']}/scheme", json={"scheme": "kpr", "reason": "uji W1-B"}))
    assert out["data"]["scheme"] == "kpr"
    assert "BANK_FEE" not in _komponen(d["contract_id"]), "perilaku lama: komponen KPR-only tidak terbawa (diurus manual)"
    skema = {s["id"]: s for s in ok(call(OWNER, "GET", "/payment-schemes"))["data"]}
    assert skema[ar(d["deal_id"])["data"]["scheme_id"]]["kind"] == "kpr"
    d2 = _contract(world)
    with setting("izinkan_manual"):
        r = call(FINANCE, "POST", f"/finance/ar/{d2['deal_id']}/schedule", json={"scheme_id": _kpr_scheme_id(world)})
    assert r.status_code == 200, (r.status_code, r.text[:300])


def test_penimpaan_per_proyek(world):
    d = _contract(world)
    with setting("izinkan_manual"), setting("tolak_buat_baru", scope="project", scope_id=world.project_id):
        r = call(FINANCE, "POST", f"/contracts/{d['contract_id']}/scheme", json={"scheme": "kpr", "reason": "uji W1-B"})
        assert r.status_code == 400, "proyek menimpa organisasi (izinkan) → tetap tolak"
    d2 = _contract(world)
    with setting("tolak_buat_baru"), setting("izinkan_manual", scope="project", scope_id=world.project_id):
        r = call(FINANCE, "POST", f"/contracts/{d2['contract_id']}/scheme", json={"scheme": "kpr", "reason": "uji W1-B"})
        assert r.status_code == 200, (r.status_code, r.text[:300])


# ================================================================== hitung_ulang_dengan_persetujuan
def test_hitung_ulang_ditahan_lalu_disetujui_membawa_komponen_kpr(world):
    d = _contract(world)
    cid = d["contract_id"]
    with setting("hitung_ulang_dengan_persetujuan"):
        r = call(FINANCE, "POST", f"/contracts/{cid}/scheme", json={"scheme": "kpr", "reason": "pembeli beralih ke KPR — uji W1-B"})
    assert r.status_code == 202, (r.status_code, r.text[:400])
    body = r.json()
    assert body["held"] is True and body["data"]["kind"] == "amandemen_kpr"
    diff = {x["code"]: x for x in body["data"]["diff"]}
    assert set(diff) == {"BANK_FEE", "INSURANCE"} and diff["INSURANCE"]["menjadi"] == 3_000_000 and diff["BANK_FEE"]["dari"] == 0
    assert body["data"]["total_selisih"] > 3_000_000
    # SELAMA menunggu, kontrak belum berubah
    assert _kontrak(cid)["scheme"] == "cash_bertahap" and "BANK_FEE" not in _komponen(cid)
    ams = ok(call(FINANCE, "GET", f"/contracts/{cid}/allin-amendments"))["data"]
    assert len(ams) == 1 and ams[0]["status"] == "pending" and ams[0]["then_scheme"] == "kpr"
    aid = ams[0]["id"]
    # pengaju tidak boleh menyetujui sendiri (SoD amandemen); peran tanpa finance:approve ditolak
    assert call(FINANCE, "POST", f"/allin-amendments/{aid}/decide", json={"approve": True, "note": "setuju sendiri"}).status_code in (400, 403)
    assert call(SALES, "POST", f"/allin-amendments/{aid}/decide", json={"approve": True}).status_code == 403
    assert _kontrak(cid)["scheme"] == "cash_bertahap"
    ok(call(FINLEAD, "POST", f"/allin-amendments/{aid}/decide", json={"approve": True, "note": "disetujui Keuangan"}))
    k = _kontrak(cid)
    assert k["scheme"] == "kpr"
    kom = _komponen(cid)
    assert kom["INSURANCE"] == 3_000_000 and kom["BANK_FEE"] > 0, kom
    skema = {s["id"]: s for s in ok(call(OWNER, "GET", "/payment-schemes"))["data"]}
    inv = ar(d["deal_id"])["data"]
    assert skema[inv["scheme_id"]]["kind"] == "kpr" and any(i.get("payer") == "bank" for i in inv["items"])
    assert ok(call(FINANCE, "GET", f"/contracts/{cid}/kpr"))["data"]["application"]["contract_id"] == cid
    assert _reconcile_ok()


def test_hitung_ulang_ditolak_keuangan_kontrak_tak_berubah(world):
    d = _contract(world)
    cid = d["contract_id"]
    with setting("hitung_ulang_dengan_persetujuan"):
        assert call(FINANCE, "POST", f"/contracts/{cid}/scheme", json={"scheme": "kpr", "reason": "uji tolak W1-B"}).status_code == 202
    aid = ok(call(FINANCE, "GET", f"/contracts/{cid}/allin-amendments"))["data"][0]["id"]
    ok(call(FINLEAD, "POST", f"/allin-amendments/{aid}/decide", json={"approve": False, "note": "ditolak, buat kontrak baru"}))
    k = _kontrak(cid)
    assert k["scheme"] == "cash_bertahap" and "BANK_FEE" not in _komponen(cid)


def test_hitung_ulang_tanpa_skema_allin_atau_dengan_uang_nyata_ditolak(world):
    d = _contract(world, allin=False)                                  # biaya manual/legacy → tak bisa dihitung ulang otomatis
    with setting("hitung_ulang_dengan_persetujuan"):
        r = call(FINANCE, "POST", f"/contracts/{d['contract_id']}/scheme", json={"scheme": "kpr", "reason": "uji W1-B"})
        assert r.status_code == 400 and "all-in" in r.text, (r.status_code, r.text[:300])
        d2 = _contract(world)
        inv = ar(d2["deal_id"])["data"]
        ok(pay(d2["deal_id"], 50_000_000, allocations=[{"item_id": inv["items"][0]["id"], "amount": 50_000_000}]))
        r = call(FINANCE, "POST", f"/contracts/{d2['contract_id']}/scheme", json={"scheme": "kpr", "reason": "uji W1-B"})
        assert r.status_code == 400 and "penerimaan" in r.text, (r.status_code, r.text[:300])
        # jalur selain ganti-jenis tidak menghitung ulang komponen → ditolak dengan petunjuk
        r = call(FINANCE, "POST", f"/finance/ar/{d['deal_id']}/schedule", json={"scheme_id": _kpr_scheme_id(world)})
        assert r.status_code == 400 and "hitung ulang" in r.text.lower(), (r.status_code, r.text[:300])
    assert _kontrak(d["contract_id"])["scheme"] == "cash_bertahap"


def test_pengaturan_enum_tervalidasi(world):
    r = call(OWNER, "PUT", f"/settings/{KEY}", json={"value": "ngawur", "reason": "uji W1-B"})
    assert r.status_code == 400, r.text[:200]
    row = next(x for x in ok(call(OWNER, "GET", "/settings", params={"q": KEY}))["data"] if x["key"] == KEY)
    assert row["value"] == "tolak_buat_baru" and row["options"] == ["tolak_buat_baru", "hitung_ulang_dengan_persetujuan", "izinkan_manual"]
    assert row["levels"] == ["org", "project"] and not row["unavailable"]
