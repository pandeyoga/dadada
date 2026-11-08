"""Regresi W2-C — MODEL BIAYA KONTRAK (keputusan #6 / KT-03): kunci `contract.cost_model` + `contract.cost_free_input_needs_approval`.

    API_BASE=http://localhost:8083/api DB_NAME=sipro_w2c MONGO_URL=<url> python -m pytest backend/tests/p0/test_w2c_model_biaya_kontrak.py \
        -n 0 --noconftest -q -p no:cacheprovider

Bawaan: `input_bebas_invoice` + persetujuan input bebas = true. Jalur "input bebas" = `POST /contracts/{id}/costs` (BPHTB, notaris, bank,
asuransi, PPh penjual), komponen manual saat reservasi, dan amandemen dengan komponen manual. Perilaku per opsi:
  * input_bebas_invoice + persetujuan : isian DITAHAN (202) → permohonan → disetujui pemegang izin persetujuan Keuangan (pemohon ≠ penyetuju)
  * input_bebas_invoice, tanpa persetujuan : berlaku seketika (perilaku lama)
  * wajib_all_in : isian bebas DITOLAK 400 (komponen manual reservasi/amandemen juga); isian non-komponen (potongan) tetap langsung
  * persetujuan : SEMUA isian biaya kontrak (termasuk potongan/DP) lewat permohonan
Tiap tes memasang pengaturan di tingkat PROYEK milik tes (World) atau org dan MENGEMBALIKANNYA di `finally`. Merah di kode lama (kunci tak ada).
"""
import time
import uuid

import pytest

from test_p0_masuk import FINANCE, OWNER, SALES, World, call, ok, race
from test_p0_masuk_2 import convert

FINLEAD = "finlead@sipro.co.id"
MODEL, APPR = "contract.cost_model", "contract.cost_free_input_needs_approval"
TAG = uuid.uuid4().hex[:5].upper()


@pytest.fixture(scope="module")
def world():
    return World()


def sebab(r):
    try:
        return str(r.json().get("detail"))
    except Exception:  # noqa: BLE001
        return r.text[:300]


def setel(world, **kv):
    for key, value in kv.items():
        k = {"model": MODEL, "appr": APPR}[key]
        ok(call(OWNER, "PUT", f"/settings/{k}", json={"value": value, "reason": "uji model biaya kontrak W2-C",
                                                       "scope": "project", "scope_id": world.project_id}))


def kembalikan(world):
    for k in (MODEL, APPR):
        call(OWNER, "POST", f"/settings/{k}/reset", params={"scope": "project", "scope_id": world.project_id})


@pytest.fixture()
def bersih(world):
    kembalikan(world)
    yield
    kembalikan(world)


def kontrak(world):
    d = world.new_deal(booking_fee=0)
    return convert(d), d


def get_k(cid):
    return ok(call(OWNER, "GET", f"/contracts/{cid}"))["data"]


def costs_of(cid):
    return get_k(cid).get("costs") or {}


def post_costs(who, cid, body):
    return call(who, "POST", f"/contracts/{cid}/costs", json=body)


def reqs(cid, who=FINANCE):
    return ok(call(who, "GET", f"/contracts/{cid}/cost-requests"))["data"]


def decide(who, rid, approve=True, note=None):
    return call(who, "POST", f"/cost-requests/{rid}/decide", json={"approve": approve, "note": note})


# ------------------------------------------------------------------ bawaan
def test_bawaan_input_bebas_invoice_dengan_persetujuan_dan_tingkat_override():
    eff = ok(call(OWNER, "GET", "/settings/effective", params={"keys": f"{MODEL},{APPR}"}))["data"]
    assert eff == {MODEL: "input_bebas_invoice", APPR: True}, eff
    specs = {s["key"]: s for s in ok(call(OWNER, "GET", "/settings", params={"group": "kebijakan", "q": "contract.cost"}))["data"]}
    for k in (MODEL, APPR):
        assert specs[k]["sensitive"] is True and set(specs[k]["levels"]) == {"org", "project"}, specs[k]
    assert specs[MODEL]["options"] == ["input_bebas_invoice", "wajib_all_in", "persetujuan"], specs[MODEL]["options"]
    assert not specs[MODEL]["unavailable"], "ketiga opsi dibangun dan teruji"
    r = call(OWNER, "PUT", f"/settings/{MODEL}", json={"value": "ngawur", "reason": "uji", "scope": "org"})
    assert r.status_code == 400


# ------------------------------------------------------------------ input_bebas_invoice + persetujuan (bawaan)
def test_isian_bebas_ditahan_lalu_disetujui_pemohon_bukan_penyetuju(world, bersih):
    cid, _ = kontrak(world)
    r = post_costs(FINANCE, cid, {"bphtb": 40_000_000, "notary_fee": 7_500_000, "note": "uji W2-C"})
    assert r.status_code == 202, (r.status_code, sebab(r))
    body = r.json()
    assert body["held"] is True and "DITAHAN" in body["message"]
    req = body["data"]
    assert req["status"] == "pending" and req["requested_by"] == FINANCE and req["payload"] == {"bphtb": 40_000_000, "notary_fee": 7_500_000}
    assert req["policy_snapshot"][MODEL]["value"] == "input_bebas_invoice" and req["policy_snapshot"][APPR]["value"] is True
    c = costs_of(cid)
    assert "bphtb" not in c and "notary_fee" not in c, "angka lama tetap berlaku sampai disetujui"
    assert [x["status"] for x in reqs(cid)] == ["pending"]
    assert [x["id"] for x in ok(call(OWNER, "GET", "/cost-requests"))["data"]].count(req["id"]) == 1       # antrean Keuangan
    # staf Keuangan (tanpa izin persetujuan) tidak bisa memutuskan; satu permohonan menunggu per kontrak
    assert decide(FINANCE, req["id"]).status_code == 403
    r2 = post_costs(FINLEAD, cid, {"insurance": 1_000_000})
    assert r2.status_code == 409, (r2.status_code, sebab(r2))
    # penyetuju lain: berlaku seketika + jejak di riwayat biaya kontrak
    rr = decide(FINLEAD, req["id"], True, "sesuai invoice notaris")
    assert rr.status_code == 200 and rr.json()["data"]["status"] == "approved", (rr.status_code, sebab(rr))
    c = costs_of(cid)
    assert c["bphtb"] == 40_000_000 and c["notary_fee"] == 7_500_000
    hist = get_k(cid).get("costs_history") or []
    assert any(h.get("cost_request_id") == req["id"] and h["requested_by"] == FINANCE and h["by"] == FINLEAD for h in hist), hist
    again = decide(OWNER, req["id"])
    assert again.status_code == 400 and "sudah diputuskan" in sebab(again), (again.status_code, sebab(again))


def test_dua_pengajuan_serentak_satu_pemenang(world, bersih):
    cid, _ = kontrak(world)
    rs = race([lambda: post_costs(FINANCE, cid, {"bphtb": 11_000_000}), lambda: post_costs(FINANCE, cid, {"bphtb": 12_000_000})])
    assert sorted(r.status_code for r in rs) == [202, 409], [(r.status_code, sebab(r)) for r in rs]
    assert len([x for x in reqs(cid) if x["status"] == "pending"]) == 1


def test_pemohon_tidak_boleh_menyetujui_sendiri_walau_memegang_izin(world, bersih):
    cid, _ = kontrak(world)
    r = post_costs(FINLEAD, cid, {"bphtb": 30_000_000})
    assert r.status_code == 202, (r.status_code, sebab(r))
    rid = r.json()["data"]["id"]
    own = decide(FINLEAD, rid)
    assert own.status_code == 403 and "Pemohon" in sebab(own), (own.status_code, sebab(own))
    assert "bphtb" not in costs_of(cid)
    assert decide(OWNER, rid).status_code == 200
    assert costs_of(cid)["bphtb"] == 30_000_000


def test_ditolak_wajib_alasan_dibatalkan_pemohon_dan_angka_lama_tetap(world, bersih):
    cid, _ = kontrak(world)
    rid = post_costs(FINANCE, cid, {"bphtb": 9_000_000}).json()["data"]["id"]
    r = decide(OWNER, rid, False)
    assert r.status_code == 400 and "Alasan" in sebab(r), (r.status_code, sebab(r))
    r = decide(OWNER, rid, False, "angka tidak sesuai dokumen")
    assert r.status_code == 200 and r.json()["data"]["status"] == "rejected"
    assert "bphtb" not in costs_of(cid)
    # setelah ditolak boleh mengajukan lagi; hanya pemohon yang boleh membatalkan
    rid2 = post_costs(FINANCE, cid, {"bphtb": 8_000_000}).json()["data"]["id"]
    assert call(FINLEAD, "POST", f"/cost-requests/{rid2}/cancel").status_code == 403
    c = call(FINANCE, "POST", f"/cost-requests/{rid2}/cancel")
    assert c.status_code == 200 and c.json()["data"]["status"] == "cancelled"
    assert [x["status"] for x in reqs(cid)][0:2] == ["cancelled", "rejected"]


def test_isian_tidak_sah_ditolak_sekarang_bukan_baru_saat_disetujui(world, bersih):
    cid, _ = kontrak(world)
    harga = int(get_k(cid)["breakdown"]["gross_price"])
    for body in ({"bphtb": -5}, {"notary_fee": harga * 3}, {"dp_percent": 150}):
        r = post_costs(FINANCE, cid, body)
        assert r.status_code == 400, (body, r.status_code, sebab(r))
    assert reqs(cid) == []
    assert post_costs(SALES, cid, {"bphtb": 1_000_000}).status_code == 403          # sales tetap tidak berhak mengisi biaya


def test_isian_bukan_komponen_tetap_langsung_pada_model_bawaan(world, bersih):
    cid, _ = kontrak(world)
    r = post_costs(FINANCE, cid, {"promo_discount": 1_000_000})
    assert r.status_code == 200, (r.status_code, sebab(r))
    assert costs_of(cid)["promo_discount"] == 1_000_000 and reqs(cid) == []


# ------------------------------------------------------------------ input_bebas_invoice tanpa persetujuan = perilaku lama
def test_tanpa_persetujuan_isian_bebas_langsung_berlaku(world, bersih):
    setel(world, appr=False)
    cid, _ = kontrak(world)
    r = post_costs(FINANCE, cid, {"bphtb": 42_500_000, "notary_fee": 15_000_000})
    assert r.status_code == 200, (r.status_code, sebab(r))
    c = costs_of(cid)
    assert c["bphtb"] == 42_500_000 and c["notary_fee"] == 15_000_000 and reqs(cid) == []


def test_input_bebas_bisa_ditagih_lewat_invoice_biaya(world, bersih):
    """KT-03: biaya yang diketik bebas dulu tidak pernah bisa ditagih (invoice 400 'Tidak ada komponen biaya')."""
    setel(world, appr=False)
    cid, _ = kontrak(world)
    ok(post_costs(FINANCE, cid, {"bphtb": 42_500_000, "notary_fee": 15_000_000}))
    r = call(FINANCE, "POST", f"/contracts/{cid}/cost-invoices")
    assert r.status_code == 200, (r.status_code, sebab(r))
    inv = r.json()["data"]
    assert inv["total"] == 57_500_000 and sorted(i["code"] for i in inv["items"]) == ["BPHTB", "NOTARY_FEE"], inv
    led = ok(call(FINANCE, "GET", f"/contracts/{cid}/costs-ledger"))["data"]
    assert led["invoiced"] == 57_500_000 and led["uninvoiced"] == 0
    again = call(FINANCE, "POST", f"/contracts/{cid}/cost-invoices")
    assert again.status_code == 400 and "sudah terbit" in sebab(again)


# ------------------------------------------------------------------ wajib_all_in
def test_wajib_all_in_menolak_isian_bebas_di_semua_jalur(world, bersih):
    setel(world, model="wajib_all_in")
    cid, _ = kontrak(world)
    r = post_costs(FINANCE, cid, {"bphtb": 40_000_000})
    assert r.status_code == 400 and "All-in" in sebab(r), (r.status_code, sebab(r))
    assert reqs(cid) == [] and "bphtb" not in costs_of(cid)
    # isian yang BUKAN komponen biaya (potongan) tetap boleh
    assert post_costs(FINANCE, cid, {"promo_discount": 1_000_000}).status_code == 200
    # komponen manual saat reservasi: ditolak
    unit = world.units[world.next_unit]
    world.next_unit += 1
    lead = ok(call(OWNER, "POST", "/leads", json={"name": f"Uji W2C wajib {TAG}", "phone": "+62815" + str(time.time_ns())[-9:],
                                                  "source": "manual"}))["data"]
    base = {"unit_id": unit["id"], "lead_id": lead["id"], "booking_fee": 0, "scheme_id": world.scheme["Cash Bertahap (3x)"]}
    r = call(OWNER, "POST", "/deals/reserve", json={**base, "costs_manual": [{"code": "NOTARIS", "amount": 1_000_000}],
                                                    "costs_manual_reason": "uji wajib All-in W2-C"})
    assert r.status_code == 400 and "All-in" in sebab(r), (r.status_code, sebab(r))
    r = call(OWNER, "POST", "/deals/reserve", json={**base, "costs": {"bphtb": 1_000_000}})
    assert r.status_code == 400 and "All-in" in sebab(r), (r.status_code, sebab(r))
    # amandemen dengan komponen manual: ditolak; memilih skema All-in tetap jalan
    r = call(FINLEAD, "POST", f"/contracts/{cid}/allin-amendments", json={
        "items": [{"code": "BPHTB", "amount": 1_000_000}], "reason": "uji komponen manual W2-C"})
    assert r.status_code == 400 and "All-in" in sebab(r), (r.status_code, sebab(r))
    sch = next(s for s in ok(call(OWNER, "GET", "/allin-schemes"))["data"] if s["code"] == "EXCLUDE")
    r = call(FINLEAD, "POST", f"/contracts/{cid}/allin-amendments", json={"scheme_id": sch["id"], "reason": "pilih skema All-in W2-C"})
    assert r.status_code == 200, (r.status_code, sebab(r))


def test_amandemen_komponen_manual_tetap_jalan_pada_model_bawaan(world, bersih):
    """Amandemen = alur persetujuan yang SUDAH ada (pengaju ≠ pemutus) → dipakai ulang apa adanya untuk komponen manual."""
    cid, _ = kontrak(world)
    r = call(FINLEAD, "POST", f"/contracts/{cid}/allin-amendments", json={
        "items": [{"code": "BPHTB", "amount": 1_000_000}], "reason": "uji komponen manual W2-C"})
    assert r.status_code == 200, (r.status_code, sebab(r))


def test_invoice_biaya_ditolak_pada_wajib_all_in_untuk_biaya_bebas_lama(world, bersih):
    setel(world, appr=False)
    cid, _ = kontrak(world)
    ok(post_costs(FINANCE, cid, {"bphtb": 5_000_000}))
    setel(world, model="wajib_all_in")
    r = call(FINANCE, "POST", f"/contracts/{cid}/cost-invoices")
    assert r.status_code == 400 and "All-in" in sebab(r), (r.status_code, sebab(r))


# ------------------------------------------------------------------ persetujuan (semua perubahan)
def test_persetujuan_menahan_semua_isian_termasuk_bukan_komponen_apa_pun_kunci_persetujuan(world, bersih):
    setel(world, model="persetujuan", appr=False)            # kunci persetujuan input bebas diabaikan pada model ini
    cid, _ = kontrak(world)
    r = post_costs(FINANCE, cid, {"promo_discount": 2_000_000, "dp_percent": 30})
    assert r.status_code == 202, (r.status_code, sebab(r))
    c = costs_of(cid)
    assert "promo_discount" not in c and "dp_percent" not in c
    assert decide(FINLEAD, r.json()["data"]["id"], True).status_code == 200
    c = costs_of(cid)
    assert c["promo_discount"] == 2_000_000 and c["dp_percent"] == 30


# ------------------------------------------------------------------ tingkat override proyek vs org
def test_proyek_menimpa_organisasi(world, bersih):
    try:
        ok(call(OWNER, "PUT", f"/settings/{MODEL}", json={"value": "wajib_all_in", "reason": "uji tingkat org W2-C", "scope": "org"}))
        setel(world, model="input_bebas_invoice")
        eff_p = ok(call(OWNER, "GET", "/settings/effective", params={"keys": MODEL, "project_id": world.project_id}))["data"][MODEL]
        eff_o = ok(call(OWNER, "GET", "/settings/effective", params={"keys": MODEL}))["data"][MODEL]
        assert (eff_p, eff_o) == ("input_bebas_invoice", "wajib_all_in")
        cid, _ = kontrak(world)
        r = post_costs(FINANCE, cid, {"bphtb": 3_000_000})
        assert r.status_code == 202, (r.status_code, sebab(r))      # proyek ini input bebas (+ persetujuan bawaan), org lain wajib All-in
    finally:
        call(OWNER, "POST", f"/settings/{MODEL}/reset", params={"scope": "org"})


def test_rekonsiliasi_hijau_setelah_uji_model_biaya():
    end = time.time() + 40
    while True:
        d = ok(call(FINANCE, "GET", "/finance/reconcile"))["data"]
        if d["ok"] or time.time() > end:
            break
        time.sleep(1.5)
    assert d["ok"], [c for c in d["checks"] if not c.get("ok")]
