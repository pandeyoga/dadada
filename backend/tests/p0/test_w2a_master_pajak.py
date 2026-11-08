"""Regresi W2-A — MASTER PAJAK (docs/audit/12 keputusan #15, FN-12): satu sumber tarif/NPOPTKP/NJOP/BANK_FEE, boleh ditimpa per proyek.

    API_BASE=http://localhost:8080/api DB_NAME=sipro_w2a MONGO_URL=... python -m pytest backend/tests/p0/test_w2a_master_pajak.py -n 0 --noconftest -q

Bagian "resolver/migrasi" memanggil modul backend LANGSUNG (tanpa server; `aio.run`, DB = DB_NAME); sisanya menembak server hidup.
Tes yang MENIMPA pajak memakai tingkat PROYEK milik tes ini dan mengembalikannya (reset) di `finally`; satu-satunya tes yang menyentuh
tingkat organisasi (kompatibilitas `/finance/config/tax`) mereset kuncinya di `finally`.
"""
import os
import sys
import uuid

import pytest

import aio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from test_p0_masuk import FINANCE, MANAGER, OWNER, SALES, SUPER, World, call, ok  # noqa: E402

ORG = "org-sipro"
FINLEAD = "finlead@sipro.co.id"
PM, MARKETING, SITE, DM = ("pm@sipro.co.id", "marketing@sipro.co.id", "site@sipro.co.id", "dm@sipro.co.id")
K_NPOPTKP, K_BPHTB, K_PPH = "tax.master.npoptkp", "tax.master.bphtb_rate", "tax.master.pph_final_rate"
K_NJOP, K_BANKFEE, K_PPN_RATE, K_PPN_MODE = "tax.master.njop_per_m2", "tax.master.bank_fee_pct_of_plafon", "tax.ppn.rate", "tax.ppn.mode"
ALASAN = "uji W2-A master pajak"


@pytest.fixture(scope="module")
def world():
    return World()


@pytest.fixture(scope="module")
def world_b():
    return World()


@pytest.fixture(scope="module")
def allin():
    rows = ok(call(OWNER, "GET", "/allin-schemes"))["data"]
    return {r["code"]: r["id"] for r in rows}


def _put(key, value, project_id=None, who=FINLEAD, reason=ALASAN):
    body = {"value": value, "reason": reason, "scope": "project" if project_id else "org"}
    if project_id:
        body["scope_id"] = project_id
    return call(who, "PUT", f"/settings/{key}", json=body)


def _reset(key, project_id=None):
    params = {"scope": "project", "scope_id": project_id} if project_id else {"scope": "org"}
    call(OWNER, "POST", f"/settings/{key}/reset", params=params)


def _eff(project_id=None, who=FINANCE):
    params = {"project_id": project_id} if project_id else None
    return ok(call(who, "GET", "/finance/config/tax", params=params))["data"]


def _preview(allin, sid, project_id, price=650_000_000, **extra):
    r = call(OWNER, "GET", f"/allin-schemes/{allin[sid]}/preview", params={"price": price, "project_id": project_id, **extra})
    comps = {c["code"]: c for c in ok(r)["data"]["components"]}
    return comps, ok(r)["data"]


# ================================================================== registri kunci
def test_kunci_master_terdaftar_dengan_metadata():
    rows = {r["key"]: r for r in ok(call(OWNER, "GET", "/settings", params={"group": "master_pajak"}))["data"]}
    assert set(rows) == {K_NPOPTKP, K_BPHTB, K_PPH, K_NJOP, K_BANKFEE, K_PPN_RATE, K_PPN_MODE}
    bawaan = {K_NPOPTKP: 80_000_000, K_BPHTB: 5.0, K_PPH: 2.5, K_NJOP: 0, K_BANKFEE: 0, K_PPN_RATE: 12.0, K_PPN_MODE: "eksklusif"}
    for k, r in rows.items():
        assert r["levels"] == ["org", "project"] and r["sensitive"] is True and r["writer"] == ["finance", "manage"], k
        assert r["default_value"] == bawaan[k], (k, r["default_value"])
        assert r["group_label"] == "Master Pajak & PPN"
    assert rows[K_PPN_MODE]["options"] == ["eksklusif", "inklusif", "bebas_ppn"] and rows[K_PPN_MODE]["unavailable"] == {}


# ================================================================== resolver (tanpa server)
def _fake_rows(monkeypatch, rows):
    import settings_store as cfg

    async def fake(_org):
        out = {}
        for key, scope, sid, value in rows:
            out.setdefault(key, []).append({"scope": scope, "scope_id": sid, "value": value})
        return out
    monkeypatch.setattr(cfg, "_rows", fake)


def test_resolver_urutan_proyek_org_bawaan_dan_asal(monkeypatch):
    import tax_master as tm
    _fake_rows(monkeypatch, [])
    m = aio.run(tm.resolve("p1", org_id=ORG))
    assert (m["npoptkp"], m["bphtb_rate"], m["pph_final_rate"], m["ppn_rate"], m["ppn_mode"]) == (80_000_000, 5.0, 2.5, 12.0, "eksklusif")
    assert set(m["origins"].values()) == {"default"}
    _fake_rows(monkeypatch, [(K_NPOPTKP, "org", ORG, 70_000_000), (K_NPOPTKP, "project", "p1", 60_000_000),
                             (K_PPN_MODE, "project", "p1", "bebas_ppn")])
    p1 = aio.run(tm.resolve("p1", org_id=ORG))
    assert p1["npoptkp"] == 60_000_000 and p1["origins"]["npoptkp"] == "project" and p1["ppn_mode"] == "bebas_ppn"
    p2 = aio.run(tm.resolve("p2", org_id=ORG))   # proyek lain & tanpa proyek jatuh ke organisasi / bawaan
    assert p2["npoptkp"] == 70_000_000 and p2["origins"]["npoptkp"] == "org" and p2["ppn_mode"] == "eksklusif"
    assert aio.run(tm.resolve(None, org_id=ORG))["npoptkp"] == 70_000_000


def test_config_for_bentuk_lama_dan_snapshot(monkeypatch):
    import tax_master as tm
    _fake_rows(monkeypatch, [(K_PPH, "project", "p1", 1.0), (K_PPN_MODE, "project", "p1", "inklusif")])
    c = aio.run(tm.config_for(ORG, "p1"))
    assert (c["pph_rate"], c["bphtb_rate"], c["ppn_rate"], c["npoptkp"]) == (1.0, 5.0, 12.0, 80_000_000)   # bentuk `finance_config` lama
    assert c["policy_snapshot"] == {K_PPN_MODE: {"value": "inklusif", "origin": "project"}, K_PPN_RATE: {"value": 12.0, "origin": "default"}}


# ================================================================== izin
@pytest.mark.parametrize("who", [FINANCE, SALES, MANAGER, PM, MARKETING, SITE, DM])
def test_peran_lain_tidak_boleh_mengubah_pajak(who, world):
    awal = _eff()
    body = {k: awal[k] for k in ("ppn_rate", "bphtb_rate", "pph_rate", "npoptkp")}
    assert call(who, "PUT", "/finance/config/tax", json=body).status_code == 403, "staf/peran lain tidak boleh menulis konfigurasi pajak"
    for key, val in ((K_NPOPTKP, 1), (K_PPN_MODE, "inklusif")):
        r = _put(key, val, world.project_id, who=who)
        assert r.status_code == 403, (who, key, r.status_code, r.text[:150])
    assert call(who, "POST", "/settings/bulk", json={"items": [
        {"key": K_BPHTB, "value": 1, "reason": ALASAN, "scope": "project", "scope_id": world.project_id}]}).status_code == 403
    assert call(who, "POST", f"/settings/{K_PPH}/reset", params={"scope": "project", "scope_id": world.project_id}).status_code == 403
    assert _eff(world.project_id)["npoptkp"] == 80_000_000   # tidak ada yang berubah


@pytest.mark.parametrize("who", [FINLEAD, OWNER, SUPER])
def test_owner_super_admin_dan_manajer_keuangan_boleh(who, world):
    try:
        r = _put(K_NPOPTKP, 61_000_000, world.project_id, who=who)
        assert r.status_code == 200, (who, r.status_code, r.text[:200])
        assert _eff(world.project_id)["npoptkp"] == 61_000_000
        awal = _eff()
        body = {k: awal[k] for k in ("ppn_rate", "bphtb_rate", "pph_rate", "npoptkp")}
        r2 = call(who, "PUT", "/finance/config/tax", json=body)   # nilai sama → tidak ada yang berubah
        assert r2.status_code == 200 and r2.json()["changed"] == []
    finally:
        _reset(K_NPOPTKP, world.project_id)


def test_pengaturan_lain_tetap_butuh_settings_manage(world):
    """Pelonggaran HANYA untuk kunci pajak: kunci lain (mis. masa keep unit) tetap khusus pemegang `settings:manage`."""
    for who in (FINLEAD, FINANCE):
        r = call(who, "PUT", "/settings/reservation.hold_days", json={"value": 7, "reason": ALASAN, "scope": "org"})
        assert r.status_code == 403, (who, r.status_code)


# ================================================================== penimpaan proyek + alasan + validasi
def test_penimpaan_proyek_wajib_alasan_tercatat_dan_tidak_bocor(world, world_b):
    r = call(FINLEAD, "PUT", f"/settings/{K_NPOPTKP}", json={"value": 60_000_000, "scope": "project", "scope_id": world.project_id})
    assert r.status_code == 400 and "alasan" in r.text.lower(), (r.status_code, r.text[:200])
    try:
        ok(_put(K_NPOPTKP, 60_000_000, world.project_id, reason="NPOPTKP Perda kabupaten proyek A Rp 60 juta"))
        a, b, org = _eff(world.project_id), _eff(world_b.project_id), _eff()
        assert a["npoptkp"] == 60_000_000 and a["origins"]["npoptkp"] == "project"
        assert b["npoptkp"] == org["npoptkp"] == 80_000_000 and b["origins"]["npoptkp"] == "default"
        hist = ok(call(OWNER, "GET", f"/settings/{K_NPOPTKP}/history"))["data"]
        assert any(h["scope"] == "project" and h["scope_id"] == world.project_id and "Perda kabupaten" in (h.get("reason") or "")
                   and h["by"] == FINLEAD for h in hist)
    finally:
        _reset(K_NPOPTKP, world.project_id)
    assert _eff(world.project_id)["npoptkp"] == 80_000_000


@pytest.mark.parametrize("key,value", [(K_BPHTB, 500), (K_BPHTB, -1), (K_PPH, 101), (K_NPOPTKP, -1), (K_PPN_RATE, 100.5),
                                       (K_PPN_MODE, "ngawur"), (K_NJOP, -5), (K_BANKFEE, 150)])
def test_nilai_di_luar_rentang_ditolak(key, value, world):
    r = _put(key, value, world.project_id)
    assert r.status_code == 400, (key, value, r.status_code, r.text[:150])


# ================================================================== kompatibilitas /finance/config/tax
def _legacy_doc():
    import db as dbm

    async def baca():
        return await dbm.db.finance_configs.find_one({"org_id": ORG, "key": "finance_config"}, {"_id": 0})
    return aio.run(baca())


def test_kompat_menulis_master_bukan_dokumen_lama(world):
    legacy_before = _legacy_doc()
    # (a) penimpaan proyek lewat bentuk lama WAJIB beralasan
    body = {"ppn_rate": 12, "bphtb_rate": 5, "pph_rate": 1, "npoptkp": 60_000_000, "project_id": world.project_id}
    assert call(FINLEAD, "PUT", "/finance/config/tax", json=body).status_code == 400
    try:
        r = ok(call(FINLEAD, "PUT", "/finance/config/tax", json={**body, "reason": "proyek rumah sederhana: PPh final 1%"}))
        assert sorted(r["changed"]) == sorted([K_PPH, K_NPOPTKP])   # hanya nilai yang BERUBAH yang ditulis
        e = _eff(world.project_id)
        assert (e["pph_rate"], e["npoptkp"], e["origins"]["pph_final_rate"]) == (1.0, 60_000_000, "project")
        rows = {x["key"]: x for x in ok(call(OWNER, "GET", "/settings", params={"group": "master_pajak", "project_id": world.project_id}))["data"]}
        assert rows[K_PPH]["value"] == 1.0 and rows[K_PPH]["origin"] == "project"
        assert _eff()["pph_rate"] == 2.5   # organisasi tidak ikut berubah
        # (b) tingkat organisasi lewat bentuk lama → master level org (bukan dokumen `finance_configs`)
        ok(call(FINLEAD, "PUT", "/finance/config/tax", json={"ppn_rate": 12, "bphtb_rate": 5, "pph_rate": 3, "npoptkp": 80_000_000}))
        assert _eff()["pph_rate"] == 3.0 and _eff()["origins"]["pph_final_rate"] == "org"
        row = [x for x in ok(call(OWNER, "GET", "/settings", params={"group": "master_pajak"}))["data"] if x["key"] == K_PPH][0]
        assert row["value"] == 3.0 and row["origin"] == "org"
    finally:
        _reset(K_PPH)
        _reset(K_PPH, world.project_id)
        _reset(K_NPOPTKP, world.project_id)
    legacy_after = _legacy_doc()
    assert legacy_after == legacy_before, "dokumen finance_config lama tidak boleh menjadi sumber kedua (tidak ditulis lagi)"
    assert _eff()["pph_rate"] == 2.5


def test_kompat_juga_menulis_mode_ppn_njop_dan_persen_plafon(world):
    body = {"ppn_rate": 12, "bphtb_rate": 5, "pph_rate": 2.5, "npoptkp": 80_000_000, "project_id": world.project_id,
            "reason": "uji kompat: mode PPN, NJOP, % plafon proyek"}
    try:
        r = ok(call(FINLEAD, "PUT", "/finance/config/tax", json={**body, "ppn_mode": "bebas_ppn", "njop_per_m2": 5_000_000,
                                                                  "bank_fee_pct_of_plafon": 0.75}))
        assert sorted(r["changed"]) == sorted([K_PPN_MODE, K_NJOP, K_BANKFEE])
        e = _eff(world.project_id)
        assert (e["ppn_mode"], e["njop_per_m2"], e["bank_fee_pct_of_plafon"]) == ("bebas_ppn", 5_000_000, 0.75)
        assert e["origins"]["ppn_mode"] == "project" and _eff()["ppn_mode"] == "eksklusif"
        assert call(FINLEAD, "PUT", "/finance/config/tax", json={**body, "ppn_mode": "ngawur"}).status_code == 400
        assert call(FINLEAD, "PUT", "/finance/config/tax", json={**body, "njop_per_m2": -1}).status_code == 400
        assert call(FINANCE, "PUT", "/finance/config/tax", json={**body, "ppn_mode": "inklusif"}).status_code == 403
    finally:
        for k in (K_PPN_MODE, K_NJOP, K_BANKFEE):
            _reset(k, world.project_id)
    assert _eff(world.project_id)["ppn_mode"] == "eksklusif"


# ================================================================== migrasi idempoten
def test_migrasi_finance_config_ke_master_idempoten():
    import db as dbm
    import settings_store as cfg
    import tax_master as tm
    org = f"org-w2a-mig-{uuid.uuid4().hex[:6]}"

    async def jalan():
        d = dbm.db
        await d.finance_configs.insert_one({"org_id": org, "key": "finance_config", "ppn_rate": 11.0, "bphtb_rate": 2.5,
                                            "pph_rate": 2.5, "npoptkp": 60_000_000})
        tm._DONE.discard(org)
        await tm.ensure_migrated(org)
        rows = {r["key"]: r async for r in d.settings.find({"org_id": org})}
        # yang SAMA dengan bawaan (pph 2.5) tidak membuat penimpaan; yang berbeda pindah ke level organisasi
        assert set(rows) == {K_PPN_RATE, K_BPHTB, K_NPOPTKP}, set(rows)
        assert rows[K_PPN_RATE]["value"] == 11.0 and rows[K_PPN_RATE]["scope"] == "org" and rows[K_PPN_RATE]["scope_id"] == org
        assert rows[K_NPOPTKP]["value"] == 60_000_000 and rows[K_BPHTB]["history"][0]["by"] == "migrasi"
        doc = await d.finance_configs.find_one({"org_id": org, "key": "finance_config"})
        assert doc["migrated_to_master"] is True
        cfg.invalidate()
        assert (await tm.resolve(None, org_id=org))["ppn_rate"] == 11.0
        # putaran kedua: tidak ada duplikat, tidak menimpa nilai master yang SUDAH diubah pengguna
        await cfg.set_value(K_NPOPTKP, 70_000_000, actor="uji", reason=ALASAN, org_id=org)
        tm._DONE.discard(org)
        await tm.ensure_migrated(org)
        assert await d.settings.count_documents({"org_id": org}) == 3
        assert (await tm.resolve(None, org_id=org))["npoptkp"] == 70_000_000
        # penanda hilang (mis. dokumen disalin ulang): nilai master yang sudah ada tetap menang
        await d.finance_configs.update_one({"org_id": org, "key": "finance_config"}, {"$unset": {"migrated_to_master": ""}})
        tm._DONE.discard(org)
        await tm.ensure_migrated(org)
        assert await d.settings.count_documents({"org_id": org}) == 3
        assert (await tm.resolve(None, org_id=org))["npoptkp"] == 70_000_000

    try:
        aio.run(jalan())
    finally:
        async def bersih():
            await dbm.db.settings.delete_many({"org_id": org})
            await dbm.db.finance_configs.delete_many({"org_id": org})
        aio.run(bersih())
        cfg.invalidate()
        tm._DONE.discard(org)


# ================================================================== BPHTB: satu tarif, NPOPTKP per proyek
def test_bphtb_komponen_memakai_npoptkp_dan_tarif_master_per_proyek(world, world_b, allin):
    base_a, _ = _preview(allin, "EXCLUDE", world.project_id)
    assert base_a["BPHTB"]["amount"] == round((650_000_000 - 80_000_000) * 5 / 100)
    try:
        ok(_put(K_NPOPTKP, 60_000_000, world.project_id, reason="NPOPTKP Perda proyek A"))
        a, data = _preview(allin, "EXCLUDE", world.project_id)
        b, _ = _preview(allin, "EXCLUDE", world_b.project_id)
        assert data["npoptkp"] == 60_000_000 and a["BPHTB"]["amount"] == round((650_000_000 - 60_000_000) * 5 / 100)
        assert b["BPHTB"]["amount"] == base_a["BPHTB"]["amount"], "proyek lain tidak boleh ikut berubah"
        ok(_put(K_BPHTB, 2.5, world.project_id, reason="tarif BPHTB daerah proyek A"))
        a2, _ = _preview(allin, "EXCLUDE", world.project_id)
        assert a2["BPHTB"]["amount"] == round((650_000_000 - 60_000_000) * 2.5 / 100)
        assert "2.5%" in a2["BPHTB"]["formula"] and "60.000.000" in a2["BPHTB"]["formula"]
    finally:
        _reset(K_NPOPTKP, world.project_id)
        _reset(K_BPHTB, world.project_id)
    again, _ = _preview(allin, "EXCLUDE", world.project_id)
    assert again["BPHTB"]["amount"] == base_a["BPHTB"]["amount"]


def _deal(world, allin_id=None, scheme="Cash Bertahap (3x)"):
    from test_p0_masuk import SALES as S, TAG
    import time
    unit = world.units[world.next_unit]
    world.next_unit += 1
    lead = ok(call(S, "POST", "/leads", json={"name": f"Uji W2A {TAG} {world.next_unit}",
                                              "phone": "+62812" + str(int(time.time() * 1000))[-9:], "source": "manual"}))["data"]
    body = {"unit_id": unit["id"], "lead_id": lead["id"], "booking_fee": 0, "scheme_id": world.scheme[scheme]}
    if allin_id:
        body["allin_scheme_id"] = allin_id
    deal = ok(call(S, "POST", "/deals/reserve", json=body))["data"]
    ok(call(S, "POST", f"/deals/{deal['id']}/book", json={}))
    return {"deal_id": deal["id"], "unit_id": unit["id"]}


def test_catatan_pajak_dan_komponen_bphtb_satu_tarif(world, allin):
    """FN-12b: tarif BPHTB dulu dua sumber (persen komponen vs finance_config). Kini SATU: master → keduanya sama."""
    try:
        ok(_put(K_BPHTB, 2.5, world.project_id, reason="tarif BPHTB daerah — uji satu sumber"))
        ok(_put(K_NPOPTKP, 60_000_000, world.project_id, reason="NPOPTKP Perda — uji satu sumber"))
        d = _deal(world, allin["EXCLUDE"])
        deal = ok(call(OWNER, "GET", f"/deals/{d['deal_id']}"))["data"]
        bphtb = [c for c in deal["costs"]["components"] if c["code"] == "BPHTB"][0]
        harga = int(deal["price"])
        harapan = round((harga - 60_000_000) * 2.5 / 100)
        assert bphtb["amount"] == harapan
        rec = [r for r in ok(call(FINANCE, "GET", "/tax/records", params={"type": "bphtb", "limit": 500}))["data"]
               if r["deal_id"] == d["deal_id"]][0]
        assert rec["rate"] == 2.5 and rec["amount"] == harapan and rec["base"] == harga - 60_000_000
    finally:
        _reset(K_BPHTB, world.project_id)
        _reset(K_NPOPTKP, world.project_id)


def test_pph_final_per_proyek_masuk_catatan_pajak(world):
    try:
        ok(_put(K_PPH, 1.0, world.project_id, reason="rumah sederhana PPh final 1% — uji"))
        d = _deal(world)
        rec = [r for r in ok(call(FINANCE, "GET", "/tax/records", params={"type": "pph", "limit": 500}))["data"]
               if r["deal_id"] == d["deal_id"]][0]
        deal = ok(call(OWNER, "GET", f"/deals/{d['deal_id']}"))["data"]
        assert rec["rate"] == 1.0 and rec["amount"] == round(int(deal["price"]) * 1.0 / 100)
    finally:
        _reset(K_PPH, world.project_id)


# ================================================================== NJOP
def test_perkiraan_plafon_dari_porsi_bank_skema_atau_simulasi_kpr():
    import quotation_engine as qe
    terms = [{"label": "DP 20%", "amount": 100}, {"label": "Pelunasan / KPR 80%", "amount": 400}]
    assert qe._plafon_estimate(terms, "kpr", 450, 500) == round(400 * 450 / 500)   # diskalakan ke harga bersih
    assert qe._plafon_estimate(terms, "cash_bertahap", 500, 500) == 0              # bukan skema KPR
    assert qe._plafon_estimate([{"label": "DP", "amount": 500}], "kpr", 500, 500) == 0   # tanpa termin bank → pakai simulasi KPR/rumus lama
    assert qe._plafon_estimate(terms, "kpr", 500, 0) == 0
    assert qe.kpr_estimate(500, {"tenor_months": 120, "annual_rate_pct": 8, "dp_pct": 20})["loan_amount"] == 400


def test_njop_menaikkan_dasar_bphtb_hanya_bila_dipakai(world, allin):
    try:
        ok(_put(K_NJOP, 6_000_000, world.project_id, reason="NJOP tanah Rp 6 juta/m² — uji"))
        # pratinjau: harga 400 jt, tanah 100 m² → NJOP 600 jt > harga → NPOP 600 jt
        a, _ = _preview(allin, "EXCLUDE", world.project_id, price=400_000_000, land_area=100)
        assert a["BPHTB"]["amount"] == round((600_000_000 - 80_000_000) * 5 / 100) and "NJOP" in a["BPHTB"]["formula"]
        # NJOP lebih RENDAH dari harga → harga transaksi yang dipakai
        b, _ = _preview(allin, "EXCLUDE", world.project_id, price=400_000_000, land_area=50)
        assert b["BPHTB"]["amount"] == round((400_000_000 - 80_000_000) * 5 / 100) and "NJOP" not in b["BPHTB"]["formula"]
        # luas tanah tidak diketahui → NJOP tidak diterapkan
        c, _ = _preview(allin, "EXCLUDE", world.project_id, price=400_000_000)
        assert c["BPHTB"]["amount"] == b["BPHTB"]["amount"]
        # jalur transaksi: luas tanah dari master unit (`luas_tanah`) → catatan pajak BPHTB mengikuti NJOP
        unit = world.units[world.next_unit]
        ok(call(OWNER, "PATCH", f"/masterplan/units/{unit['id']}", json={"land_area": 100}))
        d = _deal(world)
        deal = ok(call(OWNER, "GET", f"/deals/{d['deal_id']}"))["data"]
        rec = [r for r in ok(call(FINANCE, "GET", "/tax/records", params={"type": "bphtb", "limit": 500}))["data"]
               if r["deal_id"] == d["deal_id"]][0]
        assert rec["base"] == 600_000_000 - 80_000_000 and rec["amount"] == round(rec["base"] * 5 / 100), (rec, deal["price"])
    finally:
        _reset(K_NJOP, world.project_id)
    d2 = _deal(world)
    rec2 = [r for r in ok(call(FINANCE, "GET", "/tax/records", params={"type": "bphtb", "limit": 500}))["data"]
            if r["deal_id"] == d2["deal_id"]][0]
    assert rec2["base"] == 500_000_000 - 80_000_000   # NJOP 0 = tidak dipakai (perilaku lama)


# ================================================================== BANK_FEE dari plafon
def test_bank_fee_persen_plafon_hanya_bila_dinyalakan_dan_plafon_diketahui(world, world_b, allin):
    lama, _ = _preview(allin, "EXCLUDE", world.project_id, scheme="kpr")
    assert lama["BANK_FEE"]["amount"] == round(650_000_000 * 1.0 / 100) and "harga" in lama["BANK_FEE"]["formula"]
    try:
        ok(_put(K_BANKFEE, 0.5, world.project_id, reason="provisi bank 0,5% dari plafon — uji"))
        tanpa, _ = _preview(allin, "EXCLUDE", world.project_id, scheme="kpr")                       # plafon belum diketahui
        assert tanpa["BANK_FEE"]["amount"] == lama["BANK_FEE"]["amount"], "tanpa plafon: rumus lama"
        pakai, _ = _preview(allin, "EXCLUDE", world.project_id, scheme="kpr", plafon=500_000_000)   # plafon SP3K
        assert pakai["BANK_FEE"]["amount"] == round(500_000_000 * 0.5 / 100) and "plafon" in pakai["BANK_FEE"]["formula"]
        lain, _ = _preview(allin, "EXCLUDE", world_b.project_id, scheme="kpr", plafon=500_000_000)  # proyek lain tak berubah
        assert lain["BANK_FEE"]["amount"] == lama["BANK_FEE"]["amount"]
        # penawaran/reservasi: plafon = porsi bank pada skema pembayaran KPR terpilih (yang juga dipakai jadwal AR)
        unit = world.units[world.next_unit]

        def bank_fee(scheme_name, kpr=None):
            body = {"unit_id": unit["id"], "scheme_id": world.scheme[scheme_name], "allin_scheme_id": allin["EXCLUDE"]}
            if kpr:
                body["kpr"] = kpr
            q = ok(call(SALES, "POST", "/quotations/simulate", json=body))["data"]
            return [c for c in q["costs"]["components"] if c["code"] == "BANK_FEE"][0], int(q["net_price"])
        bf, net = bank_fee("KPR (DP 0% + pencairan bank)")          # 100% porsi bank
        assert abs(bf["amount"] - round(net * 0.5 / 100)) <= 1 and "plafon" in bf["formula"], (bf, net)
        bf2, net2 = bank_fee("Standar KPR (DP 20%)")                # hanya termin 'Pelunasan / KPR 30%' = porsi bank
        assert abs(bf2["amount"] - round(net2 * 0.30 * 0.5 / 100)) <= 1 and "plafon" in bf2["formula"], (bf2, net2)
        # skema non-KPR tidak memuat komponen KPR-only (BANK_FEE) sama sekali
        q3 = ok(call(SALES, "POST", "/quotations/simulate", json={
            "unit_id": unit["id"], "scheme_id": world.scheme["Cash Bertahap (3x)"], "allin_scheme_id": allin["EXCLUDE"]}))["data"]
        assert "BANK_FEE" not in [c["code"] for c in q3["costs"]["components"]]
    finally:
        _reset(K_BANKFEE, world.project_id)
    sesudah, _ = _preview(allin, "EXCLUDE", world.project_id, scheme="kpr", plafon=500_000_000)
    assert sesudah["BANK_FEE"]["amount"] == lama["BANK_FEE"]["amount"]
