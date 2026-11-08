"""Regresi W1-B #8 — persetujuan diskon BERTINGKAT menurut nilai (`discount.approval_mode`, `discount.approval_tiers`).

    API_BASE=http://localhost:8073/api DB_NAME=sipro_w1b python -m pytest backend/tests/p0/test_w1b_diskon_bertingkat.py -n 0 -q --noconftest

Yang diuji: validasi tabel tingkat (celah / tumpang tindih / tidak menaik / peran), bawaan IDENTIK perilaku lama (satu tingkat),
mode `satu_level` = perilaku lama, pemilihan peran penyetuju menurut TOTAL potongan, peran di bawah tingkat ditolak (403),
pemohon tidak boleh menyetujui sendiri, snapshot kebijakan saat permohonan lahir (mengganti pengaturan tak mengubah yang menunggu),
penimpaan per proyek — di jalur penawaran (`/quotations/{id}/decision`) DAN reservasi (`/deals/{id}/pricing-approval`).
Pengaturan org/proyek yang diubah dikembalikan di `finally` (suite penuh memakai org yang sama).
"""
import os
import sys
import time
import uuid
from contextlib import contextmanager

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from test_p0_masuk import MANAGER, OWNER, SALES, TAG, World, call, ok  # noqa: E402

FINLEAD = "finlead@sipro.co.id"        # finance_manager (memegang pricing:approve, bukan quotations:approve)
MODE, TIERS = "discount.approval_mode", "discount.approval_tiers"
TIER3 = [{"max_amount": 10_000_000, "role": "sales_manager"}, {"max_amount": 25_000_000, "role": "finance_manager"},
         {"max_amount": None, "role": "owner"}]
TIER_OWNER = [{"max_amount": 10_000_000, "role": "sales_manager"}, {"max_amount": None, "role": "owner"}]
DEFAULT = [{"max_amount": None, "role": "sales_manager"}]


@pytest.fixture(scope="module")
def world():
    return World()


@contextmanager
def setting(key, value, scope="org", scope_id=None):
    body = {"value": value, "reason": "uji W1-B", "scope": scope}
    if scope_id:
        body["scope_id"] = scope_id
    ok(call(OWNER, "PUT", f"/settings/{key}", json=body))
    try:
        yield
    finally:
        call(OWNER, "POST", f"/settings/{key}/reset", params={"scope": scope, **({"scope_id": scope_id} if scope_id else {})})


def _put(value, key=TIERS, scope="org", scope_id=None, reason="uji W1-B"):
    body = {"value": value, "scope": scope, **({"reason": reason} if reason else {})}
    if scope_id:
        body["scope_id"] = scope_id
    return call(OWNER, "PUT", f"/settings/{key}", json=body)


def _promo(world, amount):
    """Promo nominal `amount` yang SELALU butuh persetujuan (approval_mode=always) → total potongan = amount."""
    return ok(call(MANAGER, "POST", "/pricing/promos", json={
        "code": "PB" + uuid.uuid4().hex[:6].upper(), "name": f"Promo W1B {uuid.uuid4().hex[:5]}", "kind": "amount",
        "value": amount, "approval_mode": "always", "applies_project_ids": [world.project_id]}))["data"]


def _lead_unit(world):
    unit = world.units[world.next_unit]
    world.next_unit += 1
    lead = ok(call(SALES, "POST", "/leads", json={"name": f"Uji Diskon {TAG} {world.next_unit}",
                                                  "phone": "+62812" + str(int(time.time() * 1000))[-9:], "source": "manual"}))["data"]
    return lead, unit


def _quote(world, amount, who=SALES):
    lead, unit = _lead_unit(world)
    p = _promo(world, amount)
    q = ok(call(who, "POST", "/quotations", json={"lead_id": lead["id"], "unit_id": unit["id"], "booking_fee": 0,
                                                  "promo_id": p["id"], "discount_reason": "Pembeli pameran, dasar uji W1-B"}))["data"]
    assert q["state"] == "awaiting_approval", q["state"]
    return q


def _decide_q(qid, who, approve=True):
    return call(who, "POST", f"/quotations/{qid}/decision", json={"approve": approve, "reason": "keputusan uji W1-B"})


def _reserve(world, amount, who=SALES):
    lead, unit = _lead_unit(world)
    p = _promo(world, amount)
    r = call(who, "POST", "/deals/reserve", json={"unit_id": unit["id"], "lead_id": lead["id"], "booking_fee": 0,
                                                  "promo_id": p["id"], "discount_reason": "Pembeli pameran, dasar uji W1-B"})
    return ok(r)["data"]


def _decide_d(did, who, approve=True):
    return call(who, "POST", f"/deals/{did}/pricing-approval", json={"approve": approve, "reason": "keputusan uji W1-B"})


# ================================================================== registry & validasi tabel tingkat
def test_bawaan_mode_bertingkat_dan_satu_tingkat_identik_perilaku_lama():
    rows = {x["key"]: x for x in ok(call(OWNER, "GET", "/settings", params={"q": "discount.approval"}))["data"]}
    assert rows[MODE]["value"] == "bertingkat" and rows[MODE]["options"] == ["satu_level", "bertingkat"], rows[MODE]
    assert rows[TIERS]["value"] == DEFAULT and rows[TIERS]["editor"] == "approval_tiers"
    assert rows[MODE]["levels"] == rows[TIERS]["levels"] == ["org", "project"]
    assert not rows[MODE]["unavailable"]


@pytest.mark.parametrize("nama,value,kata", [
    ("kosong", [], "kosong"),
    ("bukan daftar", {"max_amount": None, "role": "owner"}, "daftar"),
    ("celah di atas (tingkat terakhir berbatas)", [{"max_amount": 10_000_000, "role": "sales_manager"}], "CELAH"),
    ("celah min_amount", [{"max_amount": 10_000_000, "role": "sales_manager"},
                           {"min_amount": 12_000_000, "max_amount": None, "role": "owner"}], "CELAH"),
    ("tumpang tindih min_amount", [{"max_amount": 10_000_000, "role": "sales_manager"},
                                    {"min_amount": 8_000_000, "max_amount": None, "role": "owner"}], "TUMPANG"),
    ("batas sama", [{"max_amount": 10_000_000, "role": "sales_manager"}, {"max_amount": 10_000_000, "role": "finance_manager"},
                    {"max_amount": None, "role": "owner"}], "menaik"),
    ("tidak menaik", [{"max_amount": 20_000_000, "role": "sales_manager"}, {"max_amount": 10_000_000, "role": "finance_manager"},
                      {"max_amount": None, "role": "owner"}], "LEBIH BESAR"),
    ("tingkat setelah tak terbatas", [{"max_amount": None, "role": "sales_manager"}, {"max_amount": None, "role": "owner"}], "tak terbatas"),
    ("peran tak dikenal", [{"max_amount": None, "role": "kepala_suku"}], "tidak dikenal"),
    ("peran menurun", [{"max_amount": 10_000_000, "role": "owner"}, {"max_amount": None, "role": "sales_manager"}], "lebih rendah"),
    ("batas nol", [{"max_amount": 0, "role": "sales_manager"}, {"max_amount": None, "role": "owner"}], "lebih dari 0"),
    ("batas bukan angka", [{"max_amount": "banyak", "role": "sales_manager"}, {"max_amount": None, "role": "owner"}], "angka"),
    ("kolom asing", [{"max_amount": None, "role": "owner", "x": 1}], "tidak dikenal"),
    ("baris bukan objek", ["owner"], "objek"),
])
def test_validasi_tabel_tingkat_ditolak(nama, value, kata):
    r = _put(value)
    assert r.status_code == 400, (nama, r.status_code, r.text[:300])
    assert kata.lower() in r.text.lower(), (nama, r.text[:300])
    row = next(x for x in ok(call(OWNER, "GET", "/settings", params={"q": TIERS}))["data"] if x["key"] == TIERS)
    assert row["value"] == DEFAULT, "nilai tersimpan tidak berubah oleh pengajuan yang ditolak"


def test_tabel_sah_diterima_dinormalisasi_dan_butuh_alasan():
    assert _put(TIER3, reason=None).status_code == 400            # sensitif → alasan wajib
    with setting(TIERS, [{"min_amount": 0, "max_amount": "10000000", "role": "sales_manager"},
                         {"min_amount": 10_000_000, "max_amount": None, "role": "owner"}]):
        row = next(x for x in ok(call(OWNER, "GET", "/settings", params={"q": TIERS}))["data"] if x["key"] == TIERS)
        assert row["value"] == [{"max_amount": 10_000_000, "role": "sales_manager"}, {"max_amount": None, "role": "owner"}]
    assert _put(TIER3, key=MODE).status_code == 400
    assert _put("tanpa_persetujuan_sampai_batas", key=MODE).status_code == 400, "hanya dua opsi mode"


# ================================================================== penawaran: bawaan = perilaku lama
def test_bawaan_penawaran_manajer_menyetujui_berapa_pun(world):
    q = _quote(world, 40_000_000)
    pol = q["approval_policy"]
    assert pol["mode"] == "bertingkat" and pol["required_role"] == "sales_manager" and pol["total_discount"] == 40_000_000
    assert _decide_q(q["id"], MANAGER).status_code == 200


def test_satu_level_perilaku_lama_termasuk_pembuat_boleh(world):
    with setting(MODE, "satu_level"), setting(TIERS, TIER_OWNER):
        q = _quote(world, 40_000_000, who=MANAGER)             # pembuat = manajer; tabel diabaikan di mode ini
        assert q["approval_policy"]["mode"] == "satu_level" and "required_role" not in q["approval_policy"]
        assert _decide_q(q["id"], MANAGER).status_code == 200


# ================================================================== penawaran: bertingkat
def test_bertingkat_peran_di_bawah_tingkat_ditolak_dan_cukup_diterima(world):
    with setting(TIERS, TIER_OWNER):
        kecil, besar = _quote(world, 8_000_000), _quote(world, 40_000_000)
        assert kecil["approval_policy"]["required_role"] == "sales_manager" and kecil["approval_policy"]["tier_index"] == 1
        assert besar["approval_policy"]["required_role"] == "owner" and besar["approval_policy"]["tier_index"] == 2
        r = _decide_q(besar["id"], MANAGER)
        assert r.status_code == 403 and "Owner" in r.text and "di bawah tingkat" in r.text, (r.status_code, r.text[:300])
        got = ok(call(MANAGER, "GET", f"/quotations/{besar['id']}"))["data"]
        assert got["state"] == "awaiting_approval", "penolakan peran tidak mengubah status"
        assert _decide_q(besar["id"], OWNER).status_code == 200
        assert _decide_q(kecil["id"], MANAGER).status_code == 200            # tingkat 1 cukup manajer
    # batas tepat: D == max_amount masuk tingkat itu
    with setting(TIERS, TIER_OWNER):
        tepat = _quote(world, 10_000_000)
        assert tepat["approval_policy"]["required_role"] == "sales_manager"


def test_bertingkat_pemohon_tidak_boleh_menyetujui_sendiri_tingkat_mana_pun(world):
    q = _quote(world, 8_000_000, who=MANAGER)                 # manajer membuat penawarannya sendiri, tingkat 1 (cukup manajer)
    r = _decide_q(q["id"], MANAGER)
    assert r.status_code == 403 and "sendiri" in r.text, (r.status_code, r.text[:300])
    assert _decide_q(q["id"], OWNER).status_code == 200       # orang lain yang berwenang boleh
    with setting(TIERS, DEFAULT):
        q2 = _quote(world, 8_000_000, who=OWNER)
        assert _decide_q(q2["id"], OWNER).status_code == 403, "owner pun tidak boleh memutuskan permohonannya sendiri"


def test_snapshot_pengaturan_berganti_tidak_mengubah_permohonan_menunggu(world):
    with setting(TIERS, TIER_OWNER):
        q = _quote(world, 40_000_000)                          # lahir dengan: butuh owner
    # pengaturan kembali ke satu tingkat (manajer cukup) — permohonan ini tetap butuh owner
    assert _decide_q(q["id"], MANAGER).status_code == 403
    q_baru = _quote(world, 40_000_000)
    assert _decide_q(q_baru["id"], MANAGER).status_code == 200
    assert _decide_q(q["id"], OWNER).status_code == 200


def test_penimpaan_tingkat_proyek_menang_atas_organisasi(world):
    with setting(TIERS, DEFAULT), setting(TIERS, TIER_OWNER, scope="project", scope_id=world.project_id):
        q = _quote(world, 40_000_000)
        assert q["approval_policy"]["required_role"] == "owner"
        assert q["approval_policy"]["policy"]["discount_approval_tiers"]["origin"] == "project"
    with setting(TIERS, TIER_OWNER), setting(MODE, "satu_level", scope="project", scope_id=world.project_id):
        q = _quote(world, 40_000_000)
        assert q["approval_policy"]["mode"] == "satu_level" and _decide_q(q["id"], MANAGER).status_code == 200


# ================================================================== reservasi (SPR)
def test_reservasi_bertingkat_tiga_tingkat(world):
    with setting(TIERS, TIER3):
        d1 = _reserve(world, 8_000_000)
        d2 = _reserve(world, 20_000_000)
        d3 = _reserve(world, 40_000_000)
        for d, role in ((d1, "sales_manager"), (d2, "finance_manager"), (d3, "owner")):
            pa = d["pricing_approval"]
            assert pa["state"] == "pending" and pa["policy_snapshot"]["required_role"] == role, pa
        # tingkat 2 (finance_manager): manajer penjualan di bawah tingkat, finance_manager cukup
        r = _decide_d(d2["id"], MANAGER)
        assert r.status_code == 403 and "Manajer Keuangan" in r.text, (r.status_code, r.text[:300])
        assert _decide_d(d2["id"], FINLEAD).status_code == 200
        # tingkat 3 (owner): finance_manager masih di bawah
        assert _decide_d(d3["id"], FINLEAD).status_code == 403
        assert _decide_d(d3["id"], OWNER).status_code == 200
        # tingkat 1: manajer cukup; peran lebih tinggi juga boleh
        assert _decide_d(d1["id"], MANAGER).status_code == 200
        assert call(OWNER, "GET", f"/deals/{d3['id']}").json()["data"]["pricing_approval"]["state"] == "approved"


def test_reservasi_pembuat_berwenang_langsung_disetujui_di_bawah_tingkat_menunggu(world):
    with setting(TIERS, TIER_OWNER):
        kecil = _reserve(world, 8_000_000, who=MANAGER)       # dalam kewenangan manajer → langsung disetujui (perilaku lama)
        assert kecil["pricing_approval"]["state"] == "approved" and kecil["pricing_approval"]["self_approved"] is True
        besar = _reserve(world, 40_000_000, who=MANAGER)      # di atas kewenangan manajer → TIDAK self-approved
        pa = besar["pricing_approval"]
        assert pa["state"] == "pending" and pa["policy_snapshot"]["required_role"] == "owner", pa
        r = _decide_d(besar["id"], MANAGER)                    # pemohon sendiri + peran kurang
        assert r.status_code == 403, (r.status_code, r.text[:300])
        assert _decide_d(besar["id"], OWNER).status_code == 200


def test_reservasi_bawaan_dan_satu_level_perilaku_lama(world):
    d = _reserve(world, 40_000_000)                            # bawaan: satu tingkat sales_manager
    assert d["pricing_approval"]["policy_snapshot"]["required_role"] == "sales_manager"
    assert _decide_d(d["id"], MANAGER).status_code == 200
    with setting(MODE, "satu_level"), setting(TIERS, TIER_OWNER):
        d2 = _reserve(world, 40_000_000)
        assert d2["pricing_approval"]["policy_snapshot"]["mode"] == "satu_level"
        assert _decide_d(d2["id"], FINLEAD).status_code == 200


def test_permohonan_tanpa_snapshot_diperlakukan_perilaku_lama(world):
    """Permohonan yang lahir sebelum W1-B (tanpa `policy_snapshot`) tidak dihambat tabel tingkat."""
    from pymongo import MongoClient
    mdb = MongoClient(os.environ.get("MONGO_URL") or ("mongo" + "db://127.0.0.1:27017"))[os.environ.get("DB_NAME", "sipro_w1b")]
    with setting(TIERS, TIER_OWNER):
        d = _reserve(world, 40_000_000)
        mdb.deals.update_one({"id": d["id"]}, {"$unset": {"pricing_approval.policy_snapshot": ""}})
        assert _decide_d(d["id"], MANAGER).status_code == 200
