"""Regresi W1-C #11 — akrual komisi / fee marketing / pajak yang sudah disetujui atau dibayar pada DEAL BATAL (docs/audit/12).

    API_BASE=http://localhost:8076/api DB_NAME=sipro_w1c MONGO_URL=<uri> \
      python -m pytest backend/tests/p0/test_w1c_akrual.py -n 0 --noconftest -q -p no:cacheprovider

Kunci: cancel.accrual_reversal.commission | .marketing_fee | .tax  (org + proyek). Bawaan `manual_keuangan` = perilaku lama PERSIS.
`balik_otomatis_yang_belum_dibayar` membalik akrual yang DISETUJUI-belum-dibayar dengan jurnal koreksi; `balik_otomatis_semua`
dan semua opsi otomatis pajak berstatus "belum tersedia" (tanpa akun piutang ke penerima / pajak yang sudah dilaporkan tidak boleh
dibalik otomatis). Semua penimpaan dipasang di TINGKAT PROYEK world tes lalu dikembalikan di `finally`.

Merah-di-kode-lama: bagian HTTP (kunci kebijakan belum ada → PUT 400/404; pembalikan tidak terjadi). Tes yang memanggil
`deal_cancel_cleanup` langsung (idempotensi penutup) selalu memakai kode worktree ini — lihat catatan di laporan.
"""
import os
import sys
import uuid

import pytest

import aio
from test_p0_masuk import FINANCE, OWNER, World, call, codes, ok, race
from test_p0_masuk_2 import approve, cancel_case
from test_p0_siklus_deal import mdb, now
from w1c_common import (K_COM, K_FEE, K_TAX, MANUAL, UNPAID, approve_commission, approved_fee, bank, check,
                        commission_of, journals, lines_of, policies, put_policy, reconcile_ok, wait_until)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
ORG = "org-sipro"


@pytest.fixture(scope="module")
def world():
    return World()


@pytest.fixture(scope="module")
def world_b():
    return World()


def _cancel(deal_id, who=OWNER):
    return ok(call(who, "POST", f"/deals/{deal_id}/cancel", json={"reason": "uji W1-C pembatalan akrual"}))


def _snap(deal_id):
    return (mdb().deals.find_one({"id": deal_id}) or {}).get("cancel_policy_snapshot") or {}


def _followup_task(deal_id):
    return mdb().tasks.find_one({"source_event": f"deal.cancel_followup:{deal_id}"})


def _reconcile():
    green, bad = reconcile_ok()
    assert green, f"rekonsiliasi merah: {[(c['code'], c['diff']) for c in bad]}"


# ================================================================== katalog kebijakan
def test_katalog_kunci_bawaan_level_dan_opsi_belum_tersedia():
    rows = {r["key"]: r for r in ok(call(OWNER, "GET", "/settings", params={"group": "kebijakan"}))["data"]}
    for k in (K_COM, K_FEE, K_TAX):
        assert rows[k]["value"] == MANUAL and rows[k]["origin"] == "default" and rows[k]["levels"] == ["org", "project"], rows[k]
        assert rows[k]["options"] == ["manual_keuangan", "balik_otomatis_yang_belum_dibayar", "balik_otomatis_semua"]
        assert rows[k]["sensitive"] is True
    assert set(rows[K_COM]["unavailable"]) == {"balik_otomatis_semua"}
    assert set(rows[K_FEE]["unavailable"]) == {"balik_otomatis_semua"}
    assert set(rows[K_TAX]["unavailable"]) == {"balik_otomatis_yang_belum_dibayar", "balik_otomatis_semua"}
    assert "piutang" in rows[K_COM]["unavailable"]["balik_otomatis_semua"]


def test_opsi_belum_tersedia_ditolak_server(world):
    pid = world.project_id
    for key, opsi in ((K_COM, "balik_otomatis_semua"), (K_FEE, "balik_otomatis_semua"),
                      (K_TAX, UNPAID), (K_TAX, "balik_otomatis_semua")):
        r = put_policy(key, opsi, pid)
        assert r.status_code == 400 and "belum tersedia" in r.text, (key, opsi, r.status_code, r.text[:200])
    assert put_policy(K_COM, "ngawur", pid).status_code == 400


# ================================================================== komisi
def test_komisi_bawaan_manual_perilaku_lama_persis(world):
    d = world.new_deal()
    com = approve_commission(d["deal_id"])
    _cancel(d["deal_id"])
    c = mdb().commissions.find_one({"id": com["id"]})
    assert c["status"] == "approved" and c.get("cancel_followup"), "ditandai, TIDAK diubah"
    assert not journals("commission_reversal", com["id"]), "tanpa jurnal balik"
    assert _followup_task(d["deal_id"]) and "komisi disetujui/dibayar 1" in _followup_task(d["deal_id"])["description"]
    assert "Sistem TIDAK menjurnal balik otomatis." in _followup_task(d["deal_id"])["description"]
    snap = _snap(d["deal_id"])
    assert snap[K_COM] == {"value": MANUAL, "origin": "default"}, snap
    _reconcile()


def test_komisi_balik_otomatis_yang_belum_dibayar(world):
    d = world.new_deal()
    com = approve_commission(d["deal_id"])
    amt = int(com["amount"])
    z = check("2-1600")
    with policies(world.project_id, **{K_COM: UNPAID}):
        _cancel(d["deal_id"])
    c = mdb().commissions.find_one({"id": com["id"]})
    assert c["status"] == "cancelled" and not c.get("cancel_followup"), c
    assert c["accrual_reversal"]["mode"] == UNPAID and c["accrual_reversal"].get("journal_id")
    rev = journals("commission_reversal", com["id"])
    assert len(rev) == 1 and rev[0]["source_event"] == f"cancel.reverse:commission:{com['id']}"
    ln = lines_of(rev[0])
    assert ln["2-1600"] == (amt, 0) and ln["6-1100"] == (0, amt), ln        # cermin akrual: Dr utang komisi / Cr beban komisi
    assert _snap(d["deal_id"])[K_COM] == {"value": UNPAID, "origin": "project"}
    assert not _followup_task(d["deal_id"]), "tidak ada yang tersisa untuk Keuangan → tidak ada tugas manual"
    _reconcile()
    now_chk = check("2-1600")
    assert now_chk["ok"] and now_chk["gl"] == z["gl"] - amt and now_chk["subledger"] == z["subledger"] - amt, (z, now_chk)


def test_komisi_sudah_dibayar_tetap_manual_walau_mode_otomatis(world):
    d = world.new_deal()
    com = approve_commission(d["deal_id"])
    acc = bank()
    ok(call(OWNER, "POST", f"/finance/commissions/{com['id']}/pay", json={"cash_account_id": acc["id"]}))
    assert wait_until(lambda: journals("commission", com["id"]) and len(journals("commission", com["id"])) >= 2)
    with policies(world.project_id, **{K_COM: UNPAID}):
        _cancel(d["deal_id"])
    c = mdb().commissions.find_one({"id": com["id"]})
    assert c["status"] == "paid" and c.get("cancel_followup"), "yang sudah dibayar = tagih balik ke penerima (manual)"
    assert not journals("commission_reversal", com["id"])
    assert _followup_task(d["deal_id"])
    _reconcile()


def test_komisi_pending_selalu_dibatalkan_tanpa_jurnal(world):
    d = world.new_deal()
    com = commission_of(d["deal_id"])
    assert com["status"] == "pending"
    n0 = mdb().journal_entries.count_documents({})
    with policies(world.project_id, **{K_COM: UNPAID}):
        _cancel(d["deal_id"])
    assert mdb().commissions.find_one({"id": com["id"]})["status"] == "cancelled"
    assert not journals("commission_reversal", com["id"]) and mdb().journal_entries.count_documents(
        {"source_deal_id": d["deal_id"]}) == 0


def test_penutup_dua_kali_tidak_menjurnal_ulang(world):
    """Idempoten: penutup dipanggil ulang pada deal yang sama (mis. batal formal sesudah satu-klik) tidak melahirkan jurnal kedua."""
    import deal_cancel_cleanup as dcc
    d = world.new_deal()
    com = approve_commission(d["deal_id"])
    with policies(world.project_id, **{K_COM: UNPAID}):
        _cancel(d["deal_id"])
        n = len(journals("commission_reversal", com["id"]))
        deal = mdb().deals.find_one({"id": d["deal_id"]})
        deal.pop("_id", None)
        out = aio.run(dcc.close_deal_dependents(ORG, deal, actor=OWNER, reason="ulang uji", source="reservasi"))
    assert n == 1 and len(journals("commission_reversal", com["id"])) == 1, "satu jurnal balik, bukan dua"
    assert out["accrual_reversal"]["commission"]["reversed"] == [] and out["commissions_cancelled"] == 0
    _reconcile()


def test_balapan_bayar_komisi_dan_batal_tidak_ada_uang_hilang_atau_ganda(world):
    for _ in range(3):
        d = world.new_deal()
        com = approve_commission(d["deal_id"])
        acc = bank()
        with policies(world.project_id, **{K_COM: UNPAID}):
            rs = race([lambda: call(OWNER, "POST", f"/finance/commissions/{com['id']}/pay", json={"cash_account_id": acc["id"]}),
                       lambda: call(OWNER, "POST", f"/deals/{d['deal_id']}/cancel", json={"reason": "uji balapan komisi W1-C"})])
        assert rs[1].status_code == 200, (rs[1].status_code, rs[1].text[:200])
        assert codes([rs[0]])[0] in (200, 400, 409), (rs[0].status_code, rs[0].text[:200])
        c = mdb().commissions.find_one({"id": com["id"]})
        rev = journals("commission_reversal", com["id"])
        if c["status"] == "paid":
            assert not rev and c.get("cancel_followup"), "kalah balapan → dibayar, ditandai manual"
        else:
            assert c["status"] == "cancelled" and len(rev) == 1 and not c.get("paid_at"), c
        wait_until(lambda: True, timeout=1)
    _reconcile()


# ================================================================== fee marketing
def test_fee_balik_otomatis_yang_belum_dibayar_dengan_pph(world):
    d = world.new_deal()
    fee = approved_fee(d["deal_id"])                       # 2% × 500 jt = 10 jt bruto, PPh 5% = 500 rb, neto 9,5 jt
    gross, pph, net = fee["amount_gross"], fee["pph_amount"], fee["amount_net"]
    assert (gross, pph, net) == (10_000_000, 500_000, 9_500_000)
    with policies(world.project_id, **{K_FEE: UNPAID}):
        _cancel(d["deal_id"])
    f = mdb().marketing_fees.find_one({"id": fee["id"]})
    assert f["status"] == "cancelled" and not f.get("cancel_followup") and f["accrual_reversal"]["journal_id"], f
    rev = journals("marketing_fee_reversal", fee["id"])
    assert len(rev) == 1
    ln = lines_of(rev[0])
    assert ln["2-1500"] == (net, 0) and ln["2-1300"] == (pph, 0) and ln["6-1200"] == (0, gross), ln
    assert mdb().agents.find_one({"id": fee["agent_id"]})["fee_total"] == 0, "total agen mengikuti fee approved/paid"
    assert _snap(d["deal_id"])[K_FEE]["value"] == UNPAID
    _reconcile()


def test_fee_bawaan_manual_tidak_dibalik(world):
    d = world.new_deal()
    fee = approved_fee(d["deal_id"])
    _cancel(d["deal_id"])
    f = mdb().marketing_fees.find_one({"id": fee["id"]})
    assert f["status"] == "approved" and f.get("cancel_followup") and not journals("marketing_fee_reversal", fee["id"])
    _reconcile()


def test_fee_dibayar_sebagian_atau_penuh_tetap_manual(world):
    acc = bank()
    d1, d2 = world.new_deal(), world.new_deal()
    f1, f2 = approved_fee(d1["deal_id"]), approved_fee(d2["deal_id"])
    ok(call(FINANCE, "POST", f"/marketing/fees/{f1['id']}/pay", json={"amount": 3_000_000, "cash_account_id": acc["id"]}))
    ok(call(FINANCE, "POST", f"/marketing/fees/{f2['id']}/pay", json={"cash_account_id": acc["id"]}))
    with policies(world.project_id, **{K_FEE: UNPAID}):
        _cancel(d1["deal_id"])
        _cancel(d2["deal_id"])
    a, b = (mdb().marketing_fees.find_one({"id": f["id"]}) for f in (f1, f2))
    assert a["status"] == "approved" and a["paid_amount"] == 3_000_000 and a.get("cancel_followup"), "sebagian dibayar → manual"
    assert b["status"] == "paid" and b.get("cancel_followup")
    assert not journals("marketing_fee_reversal", f1["id"]) and not journals("marketing_fee_reversal", f2["id"])
    assert "sudah dibayar" in _followup_task(d1["deal_id"])["description"], "alasan tidak bisa dibalik otomatis disebut"
    _reconcile()


def test_fee_submitted_dibatalkan_tanpa_jurnal(world):
    d = world.new_deal()
    fee = ok(call(OWNER, "POST", "/marketing/fees", json={
        "agent_id": __import__("w1c_common").new_agent(), "deal_id": d["deal_id"], "basis": "fixed", "value": 5_000_000,
        "trigger": "booking"}))["data"]
    with policies(world.project_id, **{K_FEE: UNPAID}):
        _cancel(d["deal_id"])
    assert mdb().marketing_fees.find_one({"id": fee["id"]})["status"] == "cancelled"
    assert not journals("marketing_fee_reversal", fee["id"]) and not journals("marketing_fee", fee["id"])


# ================================================================== pajak
def test_pajak_dilaporkan_tidak_pernah_dibalik_dan_snapshot_tercatat(world):
    d = world.new_deal()
    tid = str(uuid.uuid4())
    mdb().tax_records.insert_one({"id": tid, "org_id": ORG, "deal_id": d["deal_id"], "type": "pph", "amount": 15_000_000,
                                  "status": "reported", "created_at": now(), "updated_at": now()})
    try:
        with policies(world.project_id, **{K_COM: UNPAID, K_FEE: UNPAID}):
            _cancel(d["deal_id"])
        t = mdb().tax_records.find_one({"id": tid})
        assert t["status"] == "reported" and t.get("cancel_followup"), "pajak yang sudah dilaporkan ditandai, TIDAK dibalik"
        assert _snap(d["deal_id"])[K_TAX]["value"] == MANUAL
        assert not [j for j in journals(event_re=f"cancel.reverse") if j.get("source_deal_id") == d["deal_id"]]
    finally:
        mdb().tax_records.delete_one({"id": tid})


# ================================================================== override proyek, ke depan saja, jalur formal
def test_override_proyek_hanya_berlaku_di_proyek_itu_dan_snapshot_ke_depan(world, world_b):
    a, b = world.new_deal(), world_b.new_deal()
    ca, cb = approve_commission(a["deal_id"]), approve_commission(b["deal_id"])
    with policies(world.project_id, **{K_COM: UNPAID}):
        _cancel(a["deal_id"])
        _cancel(b["deal_id"])          # proyek B tidak menimpa → bawaan org (manual)
    assert mdb().commissions.find_one({"id": ca["id"]})["status"] == "cancelled"
    cb2 = mdb().commissions.find_one({"id": cb["id"]})
    assert cb2["status"] == "approved" and cb2.get("cancel_followup")
    assert _snap(a["deal_id"])[K_COM] == {"value": UNPAID, "origin": "project"}
    assert _snap(b["deal_id"])[K_COM] == {"value": MANUAL, "origin": "default"}
    # mengganti kebijakan kemudian TIDAK menyentuh pembatalan lama (berlaku ke depan saja)
    with policies(world_b.project_id, **{K_COM: UNPAID}):
        pass
    assert mdb().commissions.find_one({"id": cb["id"]})["status"] == "approved"
    assert _snap(a["deal_id"])[K_COM]["value"] == UNPAID
    _reconcile()


def test_jalur_formal_membalik_akrual_dan_menyimpan_snapshot_di_dokumen_pembatalan(world):
    d = cancel_case(world, paid=100_000_000)
    com = approve_commission(d["deal_id"])
    with policies(world.project_id, **{K_COM: UNPAID}):
        doc = approve(d["cancel_id"])
    dep = doc["settlement"]["dependents"]
    assert dep["policy_snapshot"][K_COM]["value"] == UNPAID
    assert [r["id"] for r in dep["accrual_reversal"]["commission"]["reversed"]] == [com["id"]]
    assert mdb().commissions.find_one({"id": com["id"]})["status"] == "cancelled"
    assert len(journals("commission_reversal", com["id"])) == 1
    _reconcile()
