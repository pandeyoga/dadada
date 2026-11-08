"""Regresi W0 — fondasi kebijakan terkonfigurasi (docs/audit/12): resolver kontrak→klaster→proyek→org→bawaan,
level penimpaan yang sah, opsi "belum tersedia", dan kunci percontohan `deposit.on_cancelled_deal` (titipan pada deal batal).

    API_BASE=http://localhost:8060/api DB_NAME=sipro_w0 python -m pytest backend/tests/p0/test_w0_kebijakan.py -n 0 -q --noconftest

Bagian "resolver" memanggil kode backend LANGSUNG (tanpa server; `aio.run`); bagian "perilaku" menembak server hidup.
"""
import os
import sys

import pytest

import aio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from test_p0_masuk import FINANCE, OWNER, SUPER, World, call, ok, upload_proof  # noqa: E402

KEY = "deposit.on_cancelled_deal"
ORG = "org-sipro"


@pytest.fixture(scope="module")
def world():
    return World()


# ------------------------------------------------------------------ resolver (tanpa server)
@pytest.fixture()
def spec_uji(monkeypatch):
    """Kunci buatan yang mengizinkan tingkat kontrak dan menandai satu opsi 'belum tersedia'."""
    import settings_policy as sp
    import settings_store as cfg
    spec = sp._d("zz.uji.kontrak", "bebas", "enum", "Uji kontrak", "kunci uji resolver",
                 ref_group="deposit_cancelled_deal_policy", levels=("org", "project", "contract"),
                 unavailable={"tolak": "belum dibangun"})
    monkeypatch.setitem(cfg.DEFAULTS, spec["key"], spec)
    return spec["key"]


def _rows(monkeypatch, key, rows):
    import settings_store as cfg

    async def fake(_org):
        return {key: rows}
    monkeypatch.setattr(cfg, "_rows", fake)


def test_resolver_urutan_dan_asal(spec_uji, monkeypatch):
    import policy
    wajib = "wajib_alasan_dan_antrean_refund"
    _rows(monkeypatch, spec_uji, [])
    assert aio.run(policy.resolve_with_origin(spec_uji, org_id=ORG)) == ("bebas", "default")
    _rows(monkeypatch, spec_uji, [{"scope": "org", "scope_id": ORG, "value": wajib}])
    assert aio.run(policy.resolve_with_origin(spec_uji, org_id=ORG, project_id="p1")) == (wajib, "org")
    _rows(monkeypatch, spec_uji, [{"scope": "org", "scope_id": ORG, "value": wajib},
                                  {"scope": "project", "scope_id": "p1", "value": "bebas"}])
    assert aio.run(policy.resolve_with_origin(spec_uji, org_id=ORG, project_id="p1")) == ("bebas", "project")
    assert aio.run(policy.resolve_with_origin(spec_uji, org_id=ORG, project_id="p2")) == (wajib, "org")
    kontrak = {"policy_overrides": {spec_uji: {"value": wajib}}}
    assert aio.run(policy.resolve_with_origin(spec_uji, org_id=ORG, project_id="p1", contract=kontrak)) == (wajib, "contract")


def test_penimpaan_kontrak_usang_atau_tidak_diizinkan_diabaikan(spec_uji, monkeypatch):
    import policy
    _rows(monkeypatch, spec_uji, [{"scope": "project", "scope_id": "p1", "value": "bebas"}])
    # opsi yang kemudian berstatus 'belum tersedia' / bukan opsi sah tidak boleh diam-diam berlaku
    for stale in ("tolak", "ngawur"):
        k = {"policy_overrides": {spec_uji: {"value": stale}}}
        assert aio.run(policy.resolve_with_origin(spec_uji, org_id=ORG, project_id="p1", contract=k)) == ("bebas", "project")
    # kunci yang levelnya TIDAK memuat 'contract' mengabaikan penimpaan kontrak
    k = {"policy_overrides": {KEY: {"value": "tolak"}}}
    assert aio.run(policy.resolve_with_origin(KEY, org_id=ORG, contract=k))[1] != "contract"


def test_snapshot_merekam_nilai_dan_asal(spec_uji, monkeypatch):
    import policy
    _rows(monkeypatch, spec_uji, [{"scope": "project", "scope_id": "p1", "value": "bebas"}])
    snap = aio.run(policy.snapshot([spec_uji], org_id=ORG, project_id="p1"))
    assert snap == {spec_uji: {"value": "bebas", "origin": "project"}}
    with pytest.raises(KeyError):
        aio.run(policy.resolve("tidak.ada.kunci", org_id=ORG))


def test_set_value_menolak_opsi_belum_tersedia_dan_level_tak_sah(spec_uji):
    import settings_store as cfg
    with pytest.raises(ValueError, match="belum tersedia"):
        aio.run(cfg.set_value(spec_uji, "tolak", actor="uji", reason="uji opsi belum tersedia"))
    with pytest.raises(ValueError, match="hanya bisa diatur di tingkat"):
        aio.run(cfg.set_value(KEY, "bebas", actor="uji", reason="uji level", scope="cluster", scope_id="c1"))


def test_spec_tidak_boleh_menjadikan_opsi_belum_tersedia_sebagai_bawaan():
    import settings_policy as sp
    with pytest.raises(ValueError):
        sp._d("zz.x", "tolak", "enum", "x", "x", ref_group="deposit_cancelled_deal_policy", unavailable={"tolak": "n/a"})
    with pytest.raises(ValueError):
        sp._d("zz.y", "bebas", "enum", "y", "y", ref_group="deposit_cancelled_deal_policy", unavailable={"bukan_opsi": "n/a"})


# ------------------------------------------------------------------ API pengaturan
def _put(value, scope="org", scope_id=None, reason="uji W0 kebijakan", who=OWNER):
    body = {"value": value, "reason": reason, "scope": scope}
    if scope_id:
        body["scope_id"] = scope_id
    return call(who, "PUT", f"/settings/{KEY}", json=body)


def _reset(scope="org", scope_id=None):
    params = {"scope": scope}
    if scope_id:
        params["scope_id"] = scope_id
    call(OWNER, "POST", f"/settings/{KEY}/reset", params=params)


def test_listing_memuat_metadata_kebijakan():
    row = [r for r in ok(call(OWNER, "GET", "/settings", params={"group": "kebijakan"}))["data"] if r["key"] == KEY][0]
    assert row["value"] == "bebas" and row["origin"] == "default"
    assert row["options"] == ["bebas", "wajib_alasan_dan_antrean_refund", "tolak"]
    assert row["levels"] == ["org", "project"] and row["unavailable"] == {} and row["sensitive"] is True
    assert row["group_label"] == "Kebijakan Akuntansi & Pembatalan"


def test_put_validasi():
    assert _put("ngawur").status_code == 400
    assert call(OWNER, "PUT", f"/settings/{KEY}", json={"value": "bebas"}).status_code == 400, "sensitif wajib alasan"
    r = _put("bebas", scope="cluster", scope_id="c1")
    assert r.status_code == 400 and "tingkat" in r.text


def test_penimpaan_proyek_lebih_spesifik_dari_org(world):
    pid = world.project_id
    try:
        ok(_put("wajib_alasan_dan_antrean_refund"))
        ok(_put("tolak", scope="project", scope_id=pid))
        eff = ok(call(OWNER, "GET", "/settings/effective", params={"keys": KEY, "project_id": pid}))["data"]
        assert eff[KEY] == "tolak"
        eff = ok(call(OWNER, "GET", "/settings/effective", params={"keys": KEY}))["data"]
        assert eff[KEY] == "wajib_alasan_dan_antrean_refund"
        rows = ok(call(OWNER, "GET", "/settings", params={"group": "kebijakan", "project_id": pid}))["data"]
        row = [r for r in rows if r["key"] == KEY][0]
        assert row["value"] == "tolak" and row["origin"] == "project"
    finally:
        _reset("project", pid)
        _reset()
    row = [r for r in ok(call(OWNER, "GET", "/settings", params={"group": "kebijakan"}))["data"] if r["key"] == KEY][0]
    assert row["origin"] == "default" and row["value"] == "bebas"


# ------------------------------------------------------------------ perilaku: titipan pada deal batal
def _batal(world):
    d = world.new_deal()
    ok(call(OWNER, "POST", f"/deals/{d['deal_id']}/cancel", json={"reason": "uji W0 deal dibatalkan"}))
    return d["deal_id"]


def _titip(deal_id, note="pembeli transfer terlambat setelah deal batal", amount=1_000_000):
    return call(FINANCE, "POST", f"/finance/ar/{deal_id}/deposit",
                json={"amount": amount, "note": note, "proof_file_ids": [upload_proof()]})


def test_bawaan_bebas_deal_batal_tetap_bisa_menerima_titipan(world):
    did = _batal(world)
    out = ok(_titip(did, note=""))["data"]
    assert out["received"] == 1_000_000 and out["refund_task"] is False


def test_kebijakan_tolak_menolak_titipan_deal_batal_tetapi_tidak_deal_hidup(world):
    batal, hidup = _batal(world), world.new_deal()["deal_id"]
    try:
        ok(_put("tolak"))
        r = _titip(batal)
        assert r.status_code == 400 and "DIBATALKAN" in r.text and "menolak" in r.text, (r.status_code, r.text[:300])
        ok(_titip(hidup))   # deal hidup tidak terpengaruh
    finally:
        _reset()


def test_kebijakan_antrean_refund_wajib_alasan_dan_membuat_tugas(world):
    did = _batal(world)
    try:
        ok(_put("wajib_alasan_dan_antrean_refund"))
        r = _titip(did, note="singkat")
        assert r.status_code == 400 and "alasan" in r.text, (r.status_code, r.text[:300])
        out = ok(_titip(did, note="pembeli transfer terlambat tanggal 5"))["data"]
        assert out["received"] == 1_000_000 and out["refund_task"] is True
        rows = ok(call(OWNER, "GET", "/work/tasks", params={"scope": "all", "q": "Refund titipan deal batal", "limit": 100}))["data"]
        assert any(t.get("related_entity_id") == did and "Refund titipan" in (t.get("title") or "") for t in rows), \
            "tugas refund Keuangan tidak lahir"
    finally:
        _reset()


def test_penimpaan_proyek_mengalahkan_org_pada_perilaku(world):
    did = _batal(world)
    try:
        ok(_put("tolak"))
        ok(_put("bebas", scope="project", scope_id=world.project_id))
        ok(_titip(did))   # proyek ini 'bebas' walau organisasi 'tolak'
    finally:
        _reset("project", world.project_id)
        _reset()
