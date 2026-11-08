"""Regresi W2-B — INFRASTRUKTUR kebijakan tingkat KONTRAK: `GET/PUT/DELETE /contracts/{id}/policy[/{key}]` + snapshot kebijakan saat kontrak lahir.

    API_BASE=http://localhost:8086/api DB_NAME=sipro_w2b MONGO_URL=<uri> \
      python -m pytest backend/tests/p0/test_w2b_kebijakan_kontrak.py -n 0 --noconftest -q -p no:cacheprovider

Kendaraan uji = kunci `bphtb.borne_by` / `bphtb.developer_share_pct` (satu-satunya kunci ber-level kontrak saat ini). Perilaku PER OPSI BPHTB
(angka tagihan, titipan, jurnal) ada di `test_w2b_bphtb.py`. Penimpaan pengaturan di tingkat proyek `World` tes / organisasi SELALU direset di `finally`.

Merah-di-kode-lama: bagian HTTP (endpoint belum ada → 404; kunci belum terdaftar). Tes resolver/penangan (`aio.run`) memanggil modul worktree ini
yang tidak ada di kode lama, jadi "merah-lama" hanya berlaku untuk bagian HTTP.
"""
import os
import sys

import pytest

import aio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from test_p0_masuk import FINANCE, MANAGER, OWNER, SALES, SUPER, World, call, codes, ok, race  # noqa: E402
from test_p0_siklus_deal import mdb  # noqa: E402
from w2b_common import (ALASAN, BPHTB_500JT, DEVELOPER, DIBAGI, FINLEAD, K_BY, K_PCT, NOTARIS, PEMBELI, allin_id, bayar_invoice, comps,  # noqa: E402
                        contract, delete, live_invoices, new_contract, policy_of, put, row, settings)

ORG = "org-sipro"
NUSA = "owner@nusaproperti.co.id"
SALES2, PM, MARKETING = "sales2@sipro.co.id", "pm@sipro.co.id", "marketing@sipro.co.id"


@pytest.fixture(scope="module")
def world():
    return World()


# ================================================================== registri kunci
def test_kunci_bphtb_terdaftar_dengan_metadata():
    rows = {r["key"]: r for r in ok(call(OWNER, "GET", "/settings", params={"group": "kebijakan"}))["data"]}
    by, pct = rows[K_BY], rows[K_PCT]
    assert by["levels"] == ["org", "project", "contract"] and pct["levels"] == ["org", "project", "contract"]
    assert by["writer"] == ["finance", "manage"] and by["sensitive"] is True and pct["sensitive"] is True
    assert by["default_value"] == PEMBELI and by["origin"] == "default"
    assert by["options"] == [PEMBELI, DEVELOPER, DIBAGI] and by["unavailable"] == {}, "semua opsi punya perilaku nyata → tak ada yang 'belum tersedia'"
    assert pct["default_value"] == 50 and pct["type"] == "pct" and (pct["min"], pct["max"]) == (0, 100)
    assert set(by["option_labels"]) == {PEMBELI, DEVELOPER, DIBAGI}


def test_kunci_kontrak_tidak_bisa_ditulis_di_tingkat_kontrak_lewat_settings(world):
    r = call(OWNER, "PUT", f"/settings/{K_BY}", json={"value": DEVELOPER, "reason": ALASAN, "scope": "contract", "scope_id": "x"})
    assert r.status_code in (400, 422), (r.status_code, r.text[:200])   # tingkat kontrak hanya lewat endpoint kontrak


def test_validasi_pengaturan_org_proyek(world):
    pid = world.project_id
    assert call(FINLEAD, "PUT", f"/settings/{K_BY}", json={"value": "ngawur", "reason": ALASAN, "scope": "project", "scope_id": pid}).status_code == 400
    assert call(FINLEAD, "PUT", f"/settings/{K_PCT}", json={"value": 101, "reason": ALASAN, "scope": "project", "scope_id": pid}).status_code == 400
    assert call(FINLEAD, "PUT", f"/settings/{K_PCT}", json={"value": -1, "reason": ALASAN, "scope": "project", "scope_id": pid}).status_code == 400
    assert call(FINLEAD, "PUT", f"/settings/{K_BY}", json={"value": DEVELOPER, "scope": "project", "scope_id": pid}).status_code == 400   # sensitif: alasan wajib
    for who in (FINANCE, SALES, MANAGER, PM, MARKETING):   # hanya finance:manage
        r = call(who, "PUT", f"/settings/{K_BY}", json={"value": DEVELOPER, "reason": ALASAN, "scope": "project", "scope_id": pid})
        assert r.status_code == 403, (who, r.status_code)


# ================================================================== GET: nilai efektif + asal + opsi
def test_get_policy_bentuk_dan_asal_skema_exclude(world):
    d = new_contract(world, "EXCLUDE")
    p = policy_of(d["contract_id"])
    assert p["contract_id"] == d["contract_id"] and p["state"] in ("draft", "active") and p["history"] == []
    keys = {r["key"]: r for r in p["keys"]}
    assert set(keys) == {K_BY, K_PCT}, "hanya kunci ber-level kontrak"
    r = keys[K_BY]
    assert r["value"] == PEMBELI and r["origin"] == "skema" and r["override"] is None and r["editable"] is True and r["locked_reason"] is None
    assert r["options"] == [PEMBELI, DEVELOPER, DIBAGI] and set(r["option_labels"]) == set(r["options"]) and r["unavailable"] == {}
    assert r["sensitive"] is True and r["writer"] == ["finance", "manage"] and r["default_value"] == PEMBELI
    assert r["inherited"]["value"] == PEMBELI and r["inherited"]["origin"] == "default"
    assert r["snapshot"]["value"] == PEMBELI and r["snapshot"]["origin"] == "skema"
    assert p["summary"]["bphtb"]["total"] == BPHTB_500JT and p["summary"]["bphtb"]["buyer"] == BPHTB_500JT and p["summary"]["bphtb"]["developer"] == 0
    assert keys[K_PCT]["value"] == 50 and keys[K_PCT]["origin"] == "default"


def test_get_policy_all_in_standar_mengikuti_skema_developer(world):
    d = new_contract(world, "ALLIN_STD")
    r = row(d["contract_id"])
    assert r["value"] == DEVELOPER and r["origin"] == "skema", "bawaan = perilaku lama: skema All-in Standar menanggung BPHTB di developer"
    assert comps(d["contract_id"])["BPHTB"] == ("developer_borne", BPHTB_500JT)


# ================================================================== snapshot lahir saat kontrak dibuat
def test_snapshot_lahir_saat_kontrak_dibuat(world):
    d = new_contract(world)
    c = contract(d["contract_id"])
    snap = c["policy_snapshot"]
    assert set(snap) == {K_BY, K_PCT}
    assert snap[K_BY]["value"] == PEMBELI and snap[K_BY]["origin"] == "skema" and snap[K_BY]["at"]
    assert snap[K_PCT]["value"] == 50 and snap[K_PCT]["origin"] == "default"
    assert not c.get("policy_overrides"), "snapshot BUKAN penimpaan"
    assert not c.get("policy_snapshot_lazy"), "snapshot lahir bersama kontrak, bukan dibekukan malas"


def test_bawaan_org_diganti_kemudian_tidak_mengubah_kontrak_lama_tetapi_kontrak_baru_mengikuti(world):
    lama = new_contract(world, "EXCLUDE")
    inv0 = [(i["number"], i["total"]) for i in live_invoices(lama["contract_id"])]
    try:
        ok(call(FINLEAD, "PUT", f"/settings/{K_BY}", json={"value": DEVELOPER, "reason": ALASAN, "scope": "project", "scope_id": world.project_id}))
        # kontrak lama: nilai, komponen, invoice TIDAK berubah; pengaturan baru hanya tampil sebagai nilai warisan
        r = row(lama["contract_id"])
        assert r["value"] == PEMBELI and r["origin"] == "skema" and r["inherited"] == {**r["inherited"], "value": DEVELOPER, "origin": "project"}
        assert comps(lama["contract_id"])["BPHTB"] == ("customer_pass_through", BPHTB_500JT)
        assert [(i["number"], i["total"]) for i in live_invoices(lama["contract_id"])] == inv0
        # kontrak yang LAHIR sesudahnya memakai pilihan proyek, tercatat sebagai asal 'project'
        baru = new_contract(world, "EXCLUDE")
        rb = row(baru["contract_id"])
        assert rb["value"] == DEVELOPER and rb["origin"] == "project" and rb["snapshot"]["origin"] == "project"
        assert comps(baru["contract_id"])["BPHTB"] == ("developer_borne", BPHTB_500JT)
        assert [(i["code"], i["amount"]) for i in live_invoices(baru["contract_id"])[0]["items"]] == [("NOTARY_FEE", NOTARIS)]
    finally:
        call(OWNER, "POST", f"/settings/{K_BY}/reset", params={"scope": "project", "scope_id": world.project_id})
    # setelah pengaturan dikembalikan, kontrak 'baru' pun tidak ikut berubah (sudah beku)
    assert comps(baru["contract_id"])["BPHTB"] == ("developer_borne", BPHTB_500JT)
    assert row(baru["contract_id"])["value"] == DEVELOPER


def test_kontrak_lama_tanpa_snapshot_dibekukan_malas_dan_idempoten(world):
    d = new_contract(world, "ALLIN_STD")
    cid = d["contract_id"]
    mdb().contracts.update_one({"id": cid}, {"$unset": {"policy_snapshot": "", "policy_snapshot_lazy": ""}})   # meniru kontrak sebelum W2-B
    p1 = policy_of(cid)
    c1 = mdb().contracts.find_one({"id": cid})
    assert c1["policy_snapshot_lazy"] is True and c1["policy_snapshot"][K_BY]["value"] == DEVELOPER and c1["policy_snapshot"][K_BY]["origin"] == "skema"
    assert {r["key"]: r["value"] for r in p1["keys"]}[K_BY] == DEVELOPER
    policy_of(cid)
    policy_of(cid)
    c2 = mdb().contracts.find_one({"id": cid})
    assert c2["policy_snapshot"] == c1["policy_snapshot"], "pembacaan berulang tidak membekukan ulang"


def test_pembekuan_malas_paralel_satu_pemenang(world):
    d = new_contract(world)
    cid = d["contract_id"]
    mdb().contracts.update_one({"id": cid}, {"$unset": {"policy_snapshot": "", "policy_snapshot_lazy": ""}})
    rs = race([lambda: call(FINLEAD, "GET", f"/contracts/{cid}/policy") for _ in range(4)])
    assert codes(rs) == [200] * 4
    ats = {r.json()["data"]["keys"][0]["snapshot"]["at"] for r in rs}
    assert len(ats) == 1, "semua pembaca melihat snapshot pemenang yang sama"


# ================================================================== PUT / DELETE
def test_put_menimpa_riwayat_dan_delete_kembali_mengikuti_proyek(world):
    d = new_contract(world, "EXCLUDE")
    cid = d["contract_id"]
    r = put(cid, K_BY, DEVELOPER, "pembeli minta BPHTB ditanggung developer (kesepakatan SPR)")
    out = ok(r)["data"]
    assert out["value"] == DEVELOPER and out["origin"] == "contract" and out["changed_components"] is True
    rw = row(cid)
    assert rw["value"] == DEVELOPER and rw["origin"] == "contract" and rw["override"]["by"] == FINLEAD
    assert rw["override"]["reason"].startswith("pembeli minta") and rw["override"]["at"]
    assert contract(cid)["policy_overrides"][K_BY]["value"] == DEVELOPER
    h = policy_of(cid)["history"]
    assert len(h) == 1 and h[0]["key"] == K_BY and (h[0]["from"], h[0]["to"], h[0]["by"], h[0]["action"]) == (PEMBELI, DEVELOPER, FINLEAD, "set")
    assert h[0]["from_origin"] == "skema" and h[0]["to_origin"] == "contract" and h[0]["at"] and h[0]["reason"].startswith("pembeli minta")
    assert comps(cid)["BPHTB"] == ("developer_borne", BPHTB_500JT)
    # ganti lagi → riwayat terbaru di depan
    ok(put(cid, K_BY, DIBAGI, "disepakati ulang dibagi dua dengan developer"))
    h = policy_of(cid)["history"]
    assert [(x["from"], x["to"]) for x in h] == [(DEVELOPER, DIBAGI), (PEMBELI, DEVELOPER)]
    # DELETE → kembali mengikuti proyek/organisasi (nilai hidup: bawaan → perlakuan skema EXCLUDE = pembeli)
    out = ok(delete(cid, K_BY, "kembali mengikuti pengaturan proyek"))["data"]
    assert out["origin"] == "default" and out["value"] == PEMBELI
    rw = row(cid)
    assert rw["override"] is None and rw["value"] == PEMBELI and rw["origin"] == "skema" and rw["snapshot"]["origin"] == "default"
    assert "policy_overrides" in contract(cid) and K_BY not in contract(cid)["policy_overrides"]
    assert comps(cid)["BPHTB"] == ("customer_pass_through", BPHTB_500JT) and "BPHTB_DEV" not in comps(cid)
    h = policy_of(cid)["history"]
    assert len(h) == 3 and h[0]["action"] == "clear" and h[0]["to_origin"] == "default"


def test_delete_mengikuti_pilihan_proyek_yang_berlaku_sekarang(world):
    d = new_contract(world, "EXCLUDE")
    cid = d["contract_id"]
    ok(put(cid, K_BY, DIBAGI))
    with settings(world.project_id, **{K_BY: DEVELOPER}):
        out = ok(delete(cid, K_BY))["data"]
        assert out["origin"] == "project" and out["value"] == DEVELOPER
        assert comps(cid)["BPHTB"] == ("developer_borne", BPHTB_500JT) and "BPHTB_DEV" not in comps(cid)
        rw = row(cid)
        assert rw["value"] == DEVELOPER and rw["origin"] == "project" and rw["override"] is None
    assert row(cid)["value"] == DEVELOPER, "proyek dikembalikan tetapi kontrak sudah beku pada nilai terakhir"


def test_delete_tanpa_penimpaan_ditolak(world):
    d = new_contract(world)
    r = delete(d["contract_id"], K_BY)
    assert r.status_code == 400 and "tidak sedang ditimpa" in r.text, (r.status_code, r.text[:200])


@pytest.mark.parametrize("value,reason,potongan", [
    (DEVELOPER, "", "alasan wajib"),
    (DEVELOPER, "pendek", "alasan wajib"),
    (DEVELOPER, "   123456789   ", "alasan wajib"),   # 9 karakter bermakna
    ("ngawur", ALASAN, "pilihan tidak valid"),
    ("", ALASAN, "pilihan tidak valid"),
])
def test_put_validasi_alasan_dan_opsi(world, value, reason, potongan):
    d = new_contract(world)
    r = put(d["contract_id"], K_BY, value, reason)
    assert r.status_code == 400 and potongan in r.text, (r.status_code, r.text[:300])
    assert contract(d["contract_id"]).get("policy_overrides") in (None, {}), "tidak ada yang tersimpan"
    assert comps(d["contract_id"])["BPHTB"][0] == "customer_pass_through"


@pytest.mark.parametrize("val", [-1, 101, "abc"])
def test_put_porsi_developer_di_luar_rentang_ditolak(world, val):
    d = new_contract(world)
    assert put(d["contract_id"], K_PCT, val).status_code == 400


def test_delete_alasan_wajib(world):
    d = new_contract(world)
    ok(put(d["contract_id"], K_BY, DEVELOPER))
    r = delete(d["contract_id"], K_BY, None)
    assert r.status_code == 400 and "alasan wajib" in r.text
    assert row(d["contract_id"])["override"] is not None, "masih tertimpa"


def test_kunci_yang_bukan_level_kontrak_atau_tak_dikenal_ditolak(world):
    d = new_contract(world)
    for key in ("deposit.on_cancelled_deal", "tax.ppn.mode", "zz.tidak.ada"):
        r = put(d["contract_id"], key, "bebas")
        assert r.status_code == 400, (key, r.status_code, r.text[:200])
        assert delete(d["contract_id"], key).status_code == 400
    assert "tingkat kontrak" in put(d["contract_id"], "deposit.on_cancelled_deal", "bebas").text


def test_opsi_belum_tersedia_ditolak_server(world, monkeypatch):
    """Tidak ada pengaturan 'mati': opsi yang ditandai `unavailable` ditolak `coerce` sebelum menyentuh kontrak (tes in-process)."""
    import contract_policy as cp
    import settings_store as cfg
    d = new_contract(world)
    monkeypatch.setitem(cfg.DEFAULTS[K_BY], "unavailable", {DIBAGI: "uji: belum dibangun"})
    with pytest.raises(ValueError, match="belum tersedia"):
        aio.run(cp.set_override(ORG, d["contract_id"], K_BY, DIBAGI, ALASAN, FINLEAD))
    assert contract(d["contract_id"]).get("policy_overrides") in (None, {})
    aio.run(cp.set_override(ORG, d["contract_id"], K_BY, DEVELOPER, ALASAN, FINLEAD))   # opsi lain tetap jalan


# ================================================================== izin
def test_izin_penulisan_hanya_manajer_keuangan_owner_super_admin(world):
    d = new_contract(world)
    cid = d["contract_id"]
    for who in (FINANCE, SALES, MANAGER, PM, MARKETING):   # staf Keuangan punya contracts:update tetapi TIDAK finance:manage
        r = put(cid, K_BY, DEVELOPER, who=who)
        assert r.status_code == 403, (who, r.status_code, r.text[:150])
        assert delete(cid, K_BY, who=who).status_code == 403
    assert contract(cid).get("policy_overrides") in (None, {})
    for who in (FINLEAD, OWNER, SUPER):
        ok(put(cid, K_BY, DEVELOPER, who=who))
        ok(delete(cid, K_BY, who=who))


def test_izin_membaca_dan_lingkup_sales(world):
    d = new_contract(world, who=SALES)
    cid = d["contract_id"]
    assert call(SALES, "GET", f"/contracts/{cid}/policy").status_code == 200          # kontrak miliknya
    assert call(SALES2, "GET", f"/contracts/{cid}/policy").status_code == 403         # bukan miliknya
    for who in (FINANCE, MANAGER, PM, OWNER, FINLEAD):
        assert call(who, "GET", f"/contracts/{cid}/policy").status_code == 200, who


def test_org_lain_404(world):
    d = new_contract(world)
    cid = d["contract_id"]
    assert call(NUSA, "GET", f"/contracts/{cid}/policy").status_code == 404
    assert call(NUSA, "PUT", f"/contracts/{cid}/policy/{K_BY}", json={"value": DEVELOPER, "reason": ALASAN}).status_code == 404
    assert call(NUSA, "DELETE", f"/contracts/{cid}/policy/{K_BY}", params={"reason": ALASAN}).status_code == 404
    assert call(OWNER, "GET", "/contracts/tidak-ada/policy").status_code == 404
    assert contract(cid).get("policy_overrides") in (None, {})


# ================================================================== penolakan: kontrak batal / uang sudah bergerak
def test_kontrak_batal_ditolak(world):
    d = new_contract(world)
    cid = d["contract_id"]
    ok(put(cid, K_BY, DEVELOPER))
    ok(call(OWNER, "POST", f"/deals/{d['deal_id']}/cancel", json={"reason": "uji W2-B kontrak batal tidak boleh diubah kebijakannya"}))
    r = put(cid, K_BY, PEMBELI)
    assert r.status_code == 400 and "DIBATALKAN" in r.text, (r.status_code, r.text[:300])
    assert delete(cid, K_BY).status_code == 400
    rw = row(cid)
    assert rw["editable"] is False and "DIBATALKAN" in rw["locked_reason"] and rw["value"] == DEVELOPER, "pembacaan tetap boleh"


def test_ditolak_setelah_kuitansi_biaya_diterima(world):
    d = new_contract(world, "EXCLUDE")
    cid = d["contract_id"]
    inv = live_invoices(cid)[0]
    out = ok(put(cid, K_BY, PEMBELI))["data"]     # pilihan eksplisit yang SAMA dengan skema: hanya penanda berganti
    assert out["changed_components"] is False and out["after"] is None, "tanpa perubahan nilai → invoice tidak dibatalkan/diterbitkan ulang"
    assert [i["number"] for i in live_invoices(cid)] == [inv["number"]]
    ok(bayar_invoice(inv, 1_000_000))
    assert row(cid)["editable"] is False and "kuitansi biaya" in row(cid)["locked_reason"]
    for r in (put(cid, K_BY, DEVELOPER), put(cid, K_PCT, 30), delete(cid, K_BY)):
        assert r.status_code == 400 and "kuitansi biaya" in r.text, (r.status_code, r.text[:300])
    assert comps(cid)["BPHTB"] == ("customer_pass_through", BPHTB_500JT)
    assert [i["status"] for i in live_invoices(cid)] == ["partial"], "invoice tidak dibatalkan"


def test_ditolak_setelah_beban_developer_dicatat(world):
    d = new_contract(world, "ALLIN_STD")
    cid = d["contract_id"]
    ok(call(FINANCE, "POST", f"/contracts/{cid}/cost-expenses", json={"component_code": "BPHTB", "amount": BPHTB_500JT, "vendor": "KPP Uji W2B"}))
    r = put(cid, K_BY, PEMBELI)
    assert r.status_code == 400 and "Beban BPHTB developer sudah dicatat" in r.text, (r.status_code, r.text[:300])


def test_ditolak_bila_catatan_pajak_bphtb_sudah_dilaporkan(world):
    d = new_contract(world)
    cid = d["contract_id"]
    rec = mdb().tax_records.find_one({"deal_id": d["deal_id"], "type": "bphtb"})
    assert rec, "catatan pajak BPHTB lahir bersama jadwal AR"
    mdb().tax_records.update_one({"id": rec["id"]}, {"$set": {"status": "reported"}})
    try:
        r = put(cid, K_BY, DEVELOPER)
        assert r.status_code == 400 and "dilaporkan/disetor" in r.text, (r.status_code, r.text[:300])
    finally:
        mdb().tax_records.update_one({"id": rec["id"]}, {"$set": {"status": rec["status"]}})
    ok(put(cid, K_BY, DEVELOPER))


def test_ditolak_selama_amandemen_skema_biaya_menunggu(world):
    d = new_contract(world, "EXCLUDE")
    cid = d["contract_id"]
    ok(call(FINANCE, "POST", f"/contracts/{cid}/allin-amendments", json={"scheme_id": allin_id("ALLIN_STD"), "reason": "uji W2-B amandemen menunggu keputusan"}))
    r = put(cid, K_BY, DEVELOPER)
    assert r.status_code == 400 and "amandemen" in r.text, (r.status_code, r.text[:300])


def test_kontrak_tanpa_komponen_bphtb_ditolak_dengan_petunjuk(world):
    d = new_contract(world, allin=False)
    r = put(d["contract_id"], K_BY, DEVELOPER)
    assert r.status_code == 400 and "tidak memuat komponen BPHTB" in r.text, (r.status_code, r.text[:300])
    rw = row(d["contract_id"])
    assert rw["editable"] is False and "amandemen skema biaya" in rw["locked_reason"]


# ================================================================== konkurensi
def test_dua_perubahan_bersamaan_tidak_merusak_keadaan(world):
    d = new_contract(world, "EXCLUDE")
    cid = d["contract_id"]
    rs = race([lambda: put(cid, K_BY, DEVELOPER), lambda: put(cid, K_BY, DIBAGI), lambda: put(cid, K_BY, PEMBELI)])
    assert all(r.status_code in (200, 409) for r in rs), [(r.status_code, r.text[:120]) for r in rs]
    assert 200 in codes(rs)
    live = live_invoices(cid)
    assert len(live) <= 1, "paling banyak SATU invoice biaya aktif"
    c = comps(cid)
    ov = contract(cid)["policy_overrides"][K_BY]["value"]
    led = {PEMBELI: {"BPHTB": ("customer_pass_through", BPHTB_500JT)}, DEVELOPER: {"BPHTB": ("developer_borne", BPHTB_500JT)},
           DIBAGI: {"BPHTB": ("customer_pass_through", BPHTB_500JT // 2), "BPHTB_DEV": ("developer_borne", BPHTB_500JT // 2)}}[ov]
    assert {k: v for k, v in c.items() if k.startswith("BPHTB")} == led, "komponen mengikuti penimpaan yang menang"
    diharapkan = sum(v[1] for v in c.values() if v[0] == "customer_pass_through")
    assert (live[0]["total"] if live else 0) == diharapkan, "invoice aktif = jumlah komponen yang ditagih ke pembeli"


# ================================================================== resolver: kontrak > snapshot > proyek > org (in-process)
def _fake_rows(monkeypatch, rows):
    import settings_store as cfg

    async def fake(_org):
        out = {}
        for key, scope, sid, value in rows:
            out.setdefault(key, []).append({"scope": scope, "scope_id": sid, "value": value})
        return out
    monkeypatch.setattr(cfg, "_rows", fake)


def test_resolver_urutan_kontrak_snapshot_proyek_org_bawaan(monkeypatch):
    import policy
    _fake_rows(monkeypatch, [])
    run = lambda **kw: aio.run(policy.resolve_with_origin(K_BY, org_id=ORG, project_id="p1", **kw))   # noqa: E731
    assert run() == (PEMBELI, "default")
    _fake_rows(monkeypatch, [(K_BY, "org", ORG, DEVELOPER)])
    assert run() == (DEVELOPER, "org")
    _fake_rows(monkeypatch, [(K_BY, "org", ORG, DEVELOPER), (K_BY, "project", "p1", DIBAGI)])
    assert run() == (DIBAGI, "project")
    assert aio.run(policy.resolve_with_origin(K_BY, org_id=ORG, project_id="p2")) == (DEVELOPER, "org")
    beku = {"policy_snapshot": {K_BY: {"value": PEMBELI, "origin": "default", "at": "x"}}}
    assert run(contract=beku) == (PEMBELI, "snapshot"), "nilai beku menang atas pengaturan hidup — bawaan diganti kemudian tak mengubah kontrak"
    penimpaan = {**beku, "policy_overrides": {K_BY: {"value": DEVELOPER, "by": "x", "at": "x", "reason": "x"}}}
    assert run(contract=penimpaan) == (DEVELOPER, "contract"), "penimpaan kontrak menang atas snapshot"
    usang = {"policy_snapshot": {K_BY: {"value": "opsi_dicabut", "origin": "org"}}, "policy_overrides": {K_BY: {"value": "juga_usang"}}}
    assert run(contract=usang) == (DIBAGI, "project"), "nilai usang diabaikan, jatuh ke tingkat berikutnya"
    assert aio.run(policy.resolve(K_BY, org_id=ORG, project_id="p1", contract=penimpaan)) == DEVELOPER


def test_keputusan_bphtb_urutan_dan_kebekuan_asal_eksplisit(monkeypatch):
    import bphtb_policy as bp
    _fake_rows(monkeypatch, [(K_BY, "org", ORG, DEVELOPER)])
    dec = aio.run(bp.decide(ORG, "p1"))
    assert (dec["borne_by"], dec["borne_by_origin"], dec["explicit"]) == (DEVELOPER, "org", True)
    # snapshot kontrak yang asalnya eksplisit mengikat; yang asalnya bawaan/skema TIDAK (kontrak itu mengikuti skema)
    beku = {"policy_snapshot": {K_BY: {"value": DIBAGI, "origin": "project"}}}
    assert aio.run(bp.decide(ORG, "p1", beku))["borne_by"] == DIBAGI
    nonexplicit = {"policy_snapshot": {K_BY: {"value": PEMBELI, "origin": "skema"}}}
    assert aio.run(bp.decide(ORG, "p1", nonexplicit))["borne_by"] == DEVELOPER, "snapshot non-eksplisit tidak mengikat"
    both = {**beku, "policy_overrides": {K_BY: {"value": PEMBELI}}}
    assert aio.run(bp.decide(ORG, "p1", both))["borne_by"] == PEMBELI
    assert aio.run(bp.decide(ORG, "p1", both, skip_contract=True))["borne_by"] == DEVELOPER
    _fake_rows(monkeypatch, [])
    dec = aio.run(bp.decide(ORG, "p1"))
    assert (dec["borne_by"], dec["explicit"], dec["share_pct"]) == (PEMBELI, False, 50.0)
