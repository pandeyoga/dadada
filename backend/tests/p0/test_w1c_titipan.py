"""Regresi W1-C #12 — titipan biaya (2-1470) & invoice biaya terbuka pada DEAL BATAL (docs/audit/12).

    API_BASE=http://localhost:8076/api DB_NAME=sipro_w1c MONGO_URL=<uri> \
      python -m pytest backend/tests/p0/test_w1c_titipan.py -n 0 --noconftest -q -p no:cacheprovider

Kunci: cancel.cost_deposit.policy (refund_dan_batalkan_invoice [bawaan] | manual_dengan_pengakuan [perilaku lama] | hangus_sebagian),
.forfeit_pct (0–100), .requires_approval (bool, bawaan true). Penimpaan dipasang di TINGKAT PROYEK world tes lalu dikembalikan.

Merah-di-kode-lama: bagian HTTP (kunci belum ada; batal dengan titipan biaya diblok 400; endpoint permohonan 404). Tes in-process
(penutup kedaluwarsa) memanggil modul worktree ini.
"""
import os
import sys

import pytest

import aio
from test_p0_masuk import FINANCE, MANAGER, OWNER, SALES, SUPER, World, call, codes, ok, race
from test_p0_masuk_2 import cost_ledger
from test_p0_siklus_deal import mdb
from test_p0_sisa_siklus import _biaya_deal, _n_jurnal
from test_p0_sisa_siklus_2 import _bayar_biaya, _hapus_dan_pindai, _salur
from w1c_common import (FINLEAD, HANGUS, K_APR, K_PCT, K_POL, MANUAL_COST, REFUND, bank, check, journals, lines_of,
                        policies, put_policy, reconcile_ok, wait_until)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
ORG = "org-sipro"
SPS = "/cancel-cost-settlements"


@pytest.fixture(scope="module")
def world():
    return World()


@pytest.fixture(scope="module")
def world_b():
    return World()


# ------------------------------------------------------------------ pembantu
def _deal(world, bayar=20_000_000, salur=0):
    d = _biaya_deal(world, bayar)
    if salur:
        ok(_salur(d["contract_id"], salur))
    return d


def _cancel(deal_id, who=OWNER, **extra):
    return call(who, "POST", f"/deals/{deal_id}/cancel", json={"reason": "uji W1-C titipan biaya batal", **extra})


def _sett(deal_id):
    return mdb().cost_deposit_settlements.find_one({"deal_id": deal_id})


def _decide(sid, approved=True, who=FINLEAD, note="uji W1-C setuju refund titipan biaya"):
    return call(who, "POST", f"{SPS}/{sid}/decision", json={"approved": approved, "note": note})


def _refund(sid, amount=None, acc=None, who=FINANCE, **extra):
    body = {"method": "transfer", **({"amount": amount} if amount else {}), **({"cash_account_id": acc} if acc else {}), **extra}
    return call(who, "POST", f"{SPS}/{sid}/refund", json=body)


def _bank_balance(acc_id):
    return int([a for a in ok(call(FINANCE, "GET", "/cash-bank/accounts"))["data"] if a["id"] == acc_id][0]["balance"])


def _green():
    green, bad = reconcile_ok()
    assert green, f"rekonsiliasi merah: {[(c['code'], c['diff']) for c in bad]}"


def _refund_debt_matched():
    led = ok(call(FINANCE, "GET", "/finance/refund-debt"))["data"]["ledger"]
    assert led["matched"], led
    return led


# ================================================================== katalog
def test_katalog_kunci_titipan_biaya():
    rows = {r["key"]: r for r in ok(call(OWNER, "GET", "/settings", params={"group": "kebijakan"}))["data"]}
    p = rows[K_POL]
    assert p["value"] == REFUND and p["origin"] == "default" and p["levels"] == ["org", "project"] and p["unavailable"] == {}
    assert p["options"] == [REFUND, MANUAL_COST, HANGUS]
    assert rows[K_PCT]["value"] == 0 and rows[K_PCT]["type"] == "pct" and rows[K_PCT]["max"] == 100
    assert rows[K_APR]["value"] is True and rows[K_APR]["type"] == "bool"
    assert all(rows[k]["sensitive"] for k in (K_POL, K_PCT, K_APR))


def test_validasi_persen_dan_opsi(world):
    assert put_policy(K_PCT, 101, world.project_id).status_code == 400
    assert put_policy(K_PCT, -1, world.project_id).status_code == 400
    assert put_policy(K_POL, "ngawur", world.project_id).status_code == 400


# ================================================================== bawaan: refund + batalkan invoice, dengan persetujuan
def test_bawaan_batal_tidak_diblok_lahir_permohonan_lalu_disetujui_dan_dibayar(world):
    d = _deal(world, bayar=20_000_000, salur=3_000_000)          # titipan 17 jt (3 jt sudah DISALURKAN ke notaris)
    cid, did, iid = d["contract_id"], d["deal_id"], d["invoice"]["id"]
    pv = ok(call(OWNER, "GET", f"/deals/{did}/cancel-preview"))["data"]
    h = pv["cost_holds"]
    assert h["titipan_balance"] == 17_000_000 and h["policy"] == REFUND and h["handled_by_policy"] is True
    assert pv["requires_cost_ack"] is False, "kebijakan menangani titipan/invoice → gerbang pengakuan tidak menahan"
    n_j0 = _n_jurnal(did)
    out = ok(_cancel(did))
    assert out["data"]["status"] == "cancelled"
    deal = mdb().deals.find_one({"id": did})
    assert deal["cancel_cost_ack"]["handled_by_policy"] == REFUND
    snap = deal["cancel_policy_snapshot"]
    assert snap[K_POL] == {"value": REFUND, "origin": "default"} and snap[K_APR]["value"] is True, snap

    s = _sett(did)
    assert s["state"] == "diajukan" and s["requested_by"] == OWNER and s["number"].startswith("RTB/")
    assert s["snapshot"]["titipan_balance"] == 17_000_000 and s["requires_approval"] is True
    assert _n_jurnal(did) == n_j0, "sebelum disetujui TIDAK ada jurnal"
    assert cost_ledger(cid)["titipan_balance"] == 17_000_000
    assert mdb().cost_invoices.find_one({"id": iid})["status"] == "partial", "invoice belum dibatalkan sebelum disetujui"
    assert mdb().tasks.find_one({"source_event": f"deal.cancel_followup:costsettle:{s['id']}", "status": "open"})

    # maker-checker: pemohon (OWNER) tidak boleh menyetujui; peran tanpa izin tidak boleh memutuskan
    r = _decide(s["id"], who=OWNER)
    assert r.status_code == 400 and "Pemohon tidak boleh" in r.text, (r.status_code, r.text[:200])
    assert _decide(s["id"], who=FINANCE).status_code == 403
    assert _decide(s["id"], who=SALES).status_code == 403
    assert _sett(did)["state"] == "diajukan" and _n_jurnal(did) == n_j0
    assert _refund(s["id"]).status_code == 400, "belum disetujui → belum bisa dibayar"

    # disetujui Manajer Keuangan: jurnal + subledger + invoice
    doc = ok(_decide(s["id"]))["data"]
    st = doc["settlement"]
    assert doc["state"] == "disetujui" and st["titipan_balance"] == 17_000_000 and st["refund_amount"] == 17_000_000
    assert st["forfeit_amount"] == 0 and doc["refund_outstanding"] == 17_000_000
    je = journals("cost_settlement", s["id"])
    assert len(je) == 1 and je[0]["source_event"] == f"costsettle:{s['id']}:approve"
    assert lines_of(je[0]) == {"2-1470": (17_000_000, 0), "2-1460": (0, 17_000_000)}
    led = cost_ledger(cid)
    assert led["titipan_balance"] == 0 and led["paid_out"] == 3_000_000 + 17_000_000
    inv = mdb().cost_invoices.find_one({"id": iid})
    assert inv["status"] == "cancelled" and inv["outstanding"] == 0 and inv["paid"] == 20_000_000, "sebagian dibayar → aman, uang tetap tercatat"
    assert inv["cancelled_outstanding"] == int(d["invoice"]["total"]) - 20_000_000
    assert mdb().tasks.find_one({"source_event": f"deal.cancel_followup:costsettle:{s['id']}"})["status"] == "done"
    _green()
    assert check("2-1470")["ok"] and _refund_debt_matched()["cost_refund_outstanding"] >= 17_000_000

    # idempoten: putusan kedua ditolak
    r = _decide(s["id"])
    assert r.status_code == 400 and "tidak bisa diputus dua kali" in r.text
    assert _decide(s["id"], approved=False, note="menolak sesudah disetujui").status_code == 400
    assert len(journals("cost_settlement", s["id"])) == 1

    # pembayaran refund bertahap lewat jalur uang keluar (money_op)
    acc = bank()
    b0 = _bank_balance(acc["id"])
    ok(_refund(s["id"], 10_000_000, acc["id"]))
    r = _refund(s["id"], 10_000_000, acc["id"])
    assert r.status_code in (400, 409), (r.status_code, r.text[:200])   # klik ganda identik: ditolak (sisa 7 jt / kunci anti-ganda)
    assert _refund(s["id"], 8_000_000, acc["id"]).status_code == 400, "melebihi sisa (7 jt)"
    done = ok(_refund(s["id"], 7_000_000, acc["id"]))["data"]
    assert done["state"] == "selesai" and done["refund_paid_total"] == 17_000_000 and done["refund_outstanding"] == 0
    assert b0 - _bank_balance(acc["id"]) == 17_000_000
    pay_j = journals("cost_settlement_refund")
    assert sum(lines_of(j).get("2-1460", (0, 0))[0] for j in pay_j if j["source_deal_id"] == did) == 17_000_000
    assert _refund(s["id"], 1_000_000, acc["id"]).status_code == 400
    _green()
    _refund_debt_matched()

    # deal batal tidak menagih biaya baru dan uang biaya tidak bergerak lagi
    r = call(FINANCE, "POST", f"/contracts/{cid}/cost-invoices")
    assert r.status_code == 400 and "batal" in r.text.lower(), (r.status_code, r.text[:200])
    assert _bayar_biaya(iid, 1_100_000).status_code == 400
    assert _salur(cid, 1_100_000).status_code == 400


def test_hanya_invoice_terbuka_tanpa_titipan_invoice_void_tanpa_jurnal(world):
    d = _deal(world, bayar=0)
    ok(_cancel(d["deal_id"]))
    s = _sett(d["deal_id"])
    assert s["state"] == "diajukan" and s["snapshot"]["titipan_balance"] == 0 and s["snapshot"]["open_invoice_total"] > 0
    doc = ok(_decide(s["id"]))["data"]
    assert doc["state"] == "selesai" and doc["settlement"]["refund_amount"] == 0, "tidak ada refund → langsung selesai"
    inv = mdb().cost_invoices.find_one({"id": d["invoice"]["id"]})
    assert inv["status"] == "void" and inv["outstanding"] == 0 and inv["voided_by"] == FINLEAD
    assert not journals("cost_settlement", s["id"]) and not mdb().cost_disbursements.find_one({"settlement_id": s["id"]})
    _green()


def test_tolak_permohonan_titipan_dan_invoice_tetap_ditangani_manual(world):
    d = _deal(world, bayar=20_000_000)
    ok(_cancel(d["deal_id"]))
    s = _sett(d["deal_id"])
    r = _decide(s["id"], approved=False, note="singkat")
    assert r.status_code == 400 and "Alasan penolakan" in r.text
    doc = ok(_decide(s["id"], approved=False, note="ditolak: dana ditahan untuk sengketa notaris"))["data"]
    assert doc["state"] == "ditolak"
    assert cost_ledger(d["contract_id"])["titipan_balance"] == 20_000_000 and not journals("cost_settlement", s["id"])
    assert mdb().cost_invoices.find_one({"id": d["invoice"]["id"]})["status"] == "partial"
    assert mdb().tasks.find_one({"source_event": f"deal.cancel_followup:costsettle-ditolak:{s['id']}", "status": "open"})
    assert _refund(s["id"]).status_code == 400
    assert _decide(s["id"]).status_code == 400, "yang sudah ditolak tidak bisa disetujui"
    _green()


# ================================================================== requires_approval = false
def test_tanpa_persetujuan_langsung_dijalankan_saat_batal(world):
    d = _deal(world, bayar=20_000_000)
    with policies(world.project_id, **{K_APR: False}):
        ok(_cancel(d["deal_id"]))
    s = _sett(d["deal_id"])
    assert s["state"] == "disetujui" and s["decision"]["by"] == "sistem:kebijakan" and s["decision"]["auto"] is True
    assert s["policy_snapshot"][K_APR] == {"value": False, "origin": "project"}
    assert len(journals("cost_settlement", s["id"])) == 1
    assert cost_ledger(d["contract_id"])["titipan_balance"] == 0
    assert mdb().cost_invoices.find_one({"id": d["invoice"]["id"]})["status"] == "cancelled"
    # uang keluar tetap langkah Keuangan terpisah (dijaga dana)
    kecil = bank(1_000_000)
    r = _refund(s["id"], None, kecil["id"])
    assert r.status_code == 400 and "dana" in r.text.lower(), (r.status_code, r.text[:200])
    assert mdb().cost_deposit_settlements.find_one({"id": s["id"]})["refund_paid_total"] == 0
    acc = bank()
    assert ok(_refund(s["id"], None, acc["id"]))["data"]["state"] == "selesai"
    _green()


# ================================================================== manual_dengan_pengakuan = perilaku lama persis
def test_manual_dengan_pengakuan_gerbang_lama_tanpa_jurnal_dan_tanpa_permohonan(world):
    d = _deal(world, bayar=20_000_000)
    with policies(world.project_id, **{K_POL: MANUAL_COST}):
        pv = ok(call(OWNER, "GET", f"/deals/{d['deal_id']}/cancel-preview"))["data"]
        assert pv["requires_cost_ack"] is True and pv["cost_holds"]["handled_by_policy"] is False
        r = _cancel(d["deal_id"])
        assert r.status_code == 400 and "titipan biaya" in r.text and "acknowledge_costs" in r.text, (r.status_code, r.text[:300])
        r = _cancel(d["deal_id"], acknowledge_costs=True, cost_note="singkat")
        assert r.status_code == 400 and "Catatan penanganan biaya" in r.text
        assert mdb().deals.find_one({"id": d["deal_id"]})["status"] == "booked"
        n_j = _n_jurnal(d["deal_id"])
        note = "titipan biaya dikembalikan lewat keputusan pemilik terpisah"
        ok(_cancel(d["deal_id"], acknowledge_costs=True, cost_note=note))
    deal = mdb().deals.find_one({"id": d["deal_id"]})
    assert deal["cancel_cost_ack"]["note"] == note and "handled_by_policy" not in deal["cancel_cost_ack"]
    assert deal["cancel_policy_snapshot"][K_POL] == {"value": MANUAL_COST, "origin": "project"}
    assert _sett(d["deal_id"]) is None, "tidak ada permohonan"
    assert _n_jurnal(d["deal_id"]) == n_j and cost_ledger(d["contract_id"])["titipan_balance"] == 20_000_000
    assert mdb().cost_invoices.find_one({"id": d["invoice"]["id"]})["status"] == "partial"
    _green()


def test_override_proyek_satu_proyek_manual_proyek_lain_bawaan(world, world_b):
    a, b = _deal(world), _deal(world_b)
    with policies(world.project_id, **{K_POL: MANUAL_COST}):
        assert _cancel(a["deal_id"]).status_code == 400, "proyek A: gerbang lama"
        ok(_cancel(b["deal_id"]))
        assert _sett(b["deal_id"])["state"] == "diajukan", "proyek B: bawaan org (refund)"
    assert mdb().deals.find_one({"id": b["deal_id"]})["cancel_policy_snapshot"][K_POL]["origin"] == "default"


# ================================================================== hangus_sebagian
def test_hangus_sebagian_pecah_refund_dan_pendapatan_lain_lain(world):
    d = _deal(world, bayar=20_000_000, salur=4_000_000)          # titipan 16 jt
    with policies(world.project_id, **{K_POL: HANGUS, K_PCT: 25}):
        ok(_cancel(d["deal_id"]))
        s = _sett(d["deal_id"])
        assert s["policy"] == HANGUS and s["forfeit_pct"] == 25
    doc = ok(_decide(s["id"]))["data"]
    st = doc["settlement"]
    assert st["titipan_balance"] == 16_000_000 and st["forfeit_amount"] == 4_000_000 and st["refund_amount"] == 12_000_000
    je = journals("cost_settlement", s["id"])
    assert len(je) == 1 and lines_of(je[0]) == {"2-1470": (16_000_000, 0), "2-1460": (0, 12_000_000), "4-1200": (0, 4_000_000)}
    kinds = {r["kind"]: r["amount"] for r in mdb().cost_disbursements.find({"settlement_id": s["id"]})}
    assert kinds == {"refund_pembatalan": 12_000_000, "hangus_pembatalan": 4_000_000}
    assert cost_ledger(d["contract_id"])["titipan_balance"] == 0
    _green()
    assert check("2-1470")["ok"]
    acc = bank()
    assert ok(_refund(s["id"], None, acc["id"]))["data"]["refund_payable"] == 12_000_000
    _refund_debt_matched()


def test_hangus_seratus_persen_tidak_ada_refund_dan_nol_persen_sama_dengan_refund_penuh(world):
    a, b = _deal(world, bayar=10_000_000), _deal(world, bayar=10_000_000)
    for d, pct, refund, forfeit in ((a, 100, 0, 10_000_000), (b, 0, 10_000_000, 0)):
        with policies(world.project_id, **{K_POL: HANGUS, K_PCT: pct, K_APR: False}):
            ok(_cancel(d["deal_id"]))
        s = _sett(d["deal_id"])
        st = s["settlement"]
        assert st["refund_amount"] == refund and st["forfeit_amount"] == forfeit, (pct, st)
        assert s["state"] == ("selesai" if refund == 0 else "disetujui")
    _green()


# ================================================================== jalur formal & penutup tanpa kunci pemanggil
def test_jalur_formal_tidak_diblok_dan_permohonan_lahir_dengan_sumber_nomor_pembatalan(world):
    d = _deal(world, bayar=20_000_000)
    c = ok(call(MANAGER, "POST", "/cancellations", json={"contract_id": d["contract_id"],
                                                         "reason": "uji W1-C pembatalan formal dengan titipan biaya"}))["data"]
    pv = ok(call(MANAGER, "GET", "/cancellations/preview", params={"contract_id": d["contract_id"]}))["data"]
    assert pv["cost_holds"]["handled_by_policy"] is True
    doc = ok(call(OWNER, "POST", f"/cancellations/{c['id']}/decision", json={"approved": True, "note": "uji W1-C setuju formal"}))["data"]
    assert doc["state"] == "disetujui" and doc["settlement"]["cost_ack"]["handled_by_policy"] == REFUND
    dep = doc["settlement"]["dependents"]
    assert dep["cost_deposit"]["handled"] is True and dep["policy_snapshot"][K_POL]["value"] == REFUND
    s = _sett(d["deal_id"])
    assert s["source"] == c["number"] and s["state"] == "diajukan"
    ok(_decide(s["id"]))
    _green()
    _refund_debt_matched()          # utang refund pembatalan + utang refund titipan biaya sama-sama di 2-1460


def test_penutup_kedaluwarsa_mengambil_kunci_sendiri_tanpa_deadlock(world):
    """Jalur kedaluwarsa memanggil penutup TANPA memegang `deal_money`; eksekusi otomatis harus mengambil kunci itu sendiri."""
    import deal_cancel_cleanup as dcc
    d = _deal(world, bayar=20_000_000)
    mdb().deals.update_one({"id": d["deal_id"]}, {"$set": {"status": "expired"}})
    deal = mdb().deals.find_one({"id": d["deal_id"]})
    deal.pop("_id", None)
    with policies(world.project_id, **{K_APR: False}):
        out = aio.run(dcc.close_deal_dependents(ORG, deal, actor="scheduler", reason="Reservasi kedaluwarsa",
                                                source="kedaluwarsa", money_locked=False))
    assert out["cost_deposit"]["handled"] is True and out["cost_deposit"]["state"] == "disetujui", out["cost_deposit"]
    s = _sett(d["deal_id"])
    assert s["state"] == "disetujui" and s["source"] == "kedaluwarsa" and s["requested_by"] == "scheduler"
    assert cost_ledger(d["contract_id"])["titipan_balance"] == 0
    # penutup dipanggil ulang: tidak melahirkan permohonan/jurnal kedua
    out2 = aio.run(dcc.close_deal_dependents(ORG, deal, actor="scheduler", reason="Reservasi kedaluwarsa",
                                             source="kedaluwarsa", money_locked=False))
    assert out2["cost_deposit"].get("idempotent") or out2["cost_deposit"].get("nothing_to_do")
    assert mdb().cost_deposit_settlements.count_documents({"deal_id": d["deal_id"]}) == 1
    assert len(journals("cost_settlement", s["id"])) == 1
    _green()


# ================================================================== konkurensi
def test_dua_penyetuju_serempak_satu_jurnal_dan_dua_pembayaran_serempak_tidak_melebihi_utang(world):
    d = _deal(world, bayar=20_000_000)
    ok(_cancel(d["deal_id"], who=SUPER))
    s = _sett(d["deal_id"])
    rs = race([lambda: _decide(s["id"], who=FINLEAD), lambda: _decide(s["id"], who=OWNER)])
    assert codes(rs).count(200) == 1 and all(c in (200, 400, 409) for c in codes(rs)), [(r.status_code, r.text[:120]) for r in rs]
    assert len(journals("cost_settlement", s["id"])) == 1, "satu jurnal, bukan dua"
    assert cost_ledger(d["contract_id"])["titipan_balance"] == 0
    assert mdb().cost_disbursements.count_documents({"settlement_id": s["id"]}) == 1
    acc = bank()
    rs = race([lambda: _refund(s["id"], 12_000_000, acc["id"]), lambda: _refund(s["id"], 12_000_000, acc["id"], who=FINLEAD)])
    assert codes(rs).count(200) == 1 and all(c in (200, 400, 409) for c in codes(rs)), [(r.status_code, r.text[:120]) for r in rs]
    paid = mdb().cost_deposit_settlements.find_one({"id": s["id"]})["refund_paid_total"]
    assert paid == 12_000_000
    assert _bank_balance(acc["id"]) == 5_000_000_000 - paid, "kas keluar sama dengan yang tercatat (tidak ganda)"
    _green()


def test_batal_dan_bayar_invoice_biaya_serempak_tidak_ada_uang_hilang_atau_ganda(world):
    for _ in range(2):
        d = _deal(world, bayar=5_000_000)
        iid = d["invoice"]["id"]
        rs = race([lambda: _bayar_biaya(iid, 2_000_000), lambda: _cancel(d["deal_id"])])
        assert rs[1].status_code == 200, (rs[1].status_code, rs[1].text[:200])
        assert rs[0].status_code in (200, 400, 409), (rs[0].status_code, rs[0].text[:200])
        s = wait_until(lambda: _sett(d["deal_id"]))
        assert s, "permohonan lahir"
        receipts = sum(int(r["amount"]) for r in mdb().cost_receipts.find({"deal_id": d["deal_id"], "status": {"$ne": "void"}}))
        assert receipts in (5_000_000, 7_000_000) and receipts == (7_000_000 if rs[0].status_code == 200 else 5_000_000)
        doc = ok(_decide(s["id"]))["data"]
        assert doc["settlement"]["titipan_balance"] == receipts, "refund = seluruh yang diterima (bayar yang menang tercatat)"
        assert cost_ledger(d["contract_id"])["titipan_balance"] == 0
    _green()


def test_hapus_paksa_deal_menyapu_permohonan_dan_jurnalnya(world):
    d = _deal(world, bayar=20_000_000)
    ok(_cancel(d["deal_id"]))
    s = _sett(d["deal_id"])
    ok(_decide(s["id"]))
    ids = _hapus_dan_pindai(d, "uji W1-C hapus paksa dengan permohonan refund titipan biaya")
    assert ids, "ada turunan yang dipindai"
    assert mdb().cost_deposit_settlements.count_documents({"deal_id": d["deal_id"]}) == 0
    assert not journals("cost_settlement", s["id"])
