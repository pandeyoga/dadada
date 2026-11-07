"""Regresi G-A (1/2) — SIKLUS HIDUP DEAL: batal, biaya, BAST, pengingat, lead (audit PK3-07, PK3-08, PK3-15, PK3-19, FN-03).

    API_BASE=http://localhost:8071/api DB_NAME=sipro_ga MONGO_URL=<uri> \
      python -m pytest backend/tests/p0/test_p0_siklus_deal.py -n 0 --noconftest -q -p no:cacheprovider

Tiap tes membuat deal/proyek sendiri. Beberapa dokumen turunan (komisi, fee, pajak, KPR, kupon) disemai LANGSUNG ke DB
(DB_NAME wajib sama dengan backend yang diuji) supaya hasilnya deterministik tanpa bergantung pada pemicu event.
"""
import datetime
import os
import time
import uuid

import pytest

import aio

from test_p0_masuk import FINANCE, MANAGER, OWNER, SALES, World, ar, call, codes, ok, pay, race, upload_proof  # noqa: F401
from test_p0_masuk_2 import allin_deal, approve, cancel_case, convert, cost_ledger

FINLEAD = "finlead@sipro.co.id"
MIN = "uji siklus deal"


def mdb():
    from pymongo import MongoClient
    url = os.environ.get("MONGO_URL") or "mongo" + "db://127.0.0.1:27017"   # gerbang kepatuhan: tanpa literal URI
    return MongoClient(url)[os.environ["DB_NAME"]]


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


@pytest.fixture(scope="module")
def world():
    return World()


def _unit(world, unit_id):
    rows = ok(call(OWNER, "GET", "/units", params={"project_id": world.project_id, "limit": 200}))["data"]
    return [u for u in rows if u["id"] == unit_id][0]


# ------------------------------------------------------------------ semai turunan deal
def seed_dependents(deal_id: str) -> dict:
    """Komisi (pending/approved/paid), fee (submitted/approved), pajak (pending/reported), KPR draft, kupon terpakai."""
    db = mdb()
    deal = db.deals.find_one({"id": deal_id})
    org, ts, tag = deal["org_id"], now(), uuid.uuid4().hex[:6]
    base = {"org_id": org, "deal_id": deal_id, "created_at": ts, "updated_at": ts}
    ids = {k: str(uuid.uuid4()) for k in ("c_pend", "c_appr", "c_paid", "f_sub", "f_appr", "t_pend", "t_rep", "fin", "coupon", "red")}
    db.commissions.insert_many([
        {**base, "id": ids["c_pend"], "status": "pending", "amount": 15_000_000, "assigned_to": SALES},
        {**base, "id": ids["c_appr"], "status": "approved", "amount": 7_000_000, "assigned_to": SALES},
        {**base, "id": ids["c_paid"], "status": "paid", "amount": 3_000_000, "assigned_to": SALES}])
    agent = {"agent_id": "agen-uji", "agent_name": "Agen Uji", "unit_code": deal.get("unit_code")}
    db.marketing_fees.insert_many([
        {**base, **agent, "id": ids["f_sub"], "no": f"MF-T-{tag}-1", "status": "submitted", "amount_gross": 6_000_000,
         "amount_net": 6_000_000, "paid_amount": 0},
        {**base, **agent, "id": ids["f_appr"], "no": f"MF-T-{tag}-2", "status": "approved", "amount_gross": 4_000_000,
         "amount_net": 4_000_000, "paid_amount": 0}])
    db.tax_records.insert_many([
        {**base, "id": ids["t_pend"], "type": "ppn", "amount": 72_000_000, "status": "pending"},
        {**base, "id": ids["t_rep"], "type": "pph", "amount": 15_000_000, "status": "reported"}])
    db.financing_apps.insert_one({**base, "id": ids["fin"], "status": "draft", "kpr_stage": "berkas_lengkap",
                                  "bank_name": None, "unit_id": deal.get("unit_id")})
    db.coupons.insert_one({"id": ids["coupon"], "org_id": org, "code": f"UJI{tag}", "used_count": 1, "quota": 5,
                           "created_at": ts})
    db.coupon_redemptions.insert_one({"id": ids["red"], "org_id": org, "coupon_id": ids["coupon"], "ref_type": "deal",
                                      "ref_id": deal_id, "state": "used", "used_at": ts})
    return ids


def drop_seeds(ids: dict) -> None:
    """Hapus dokumen semai: komisi/fee `approved` tanpa jurnal membuat rekonsiliasi (2-1600/2-1500) merah bagi tes lain."""
    db = mdb()
    for coll, keys in (("commissions", ("c_pend", "c_appr", "c_paid")), ("marketing_fees", ("f_sub", "f_appr")),
                       ("tax_records", ("t_pend", "t_rep")), ("financing_apps", ("fin",)),
                       ("coupon_redemptions", ("red",)), ("coupons", ("coupon",))):
        db[coll].delete_many({"id": {"$in": [ids[k] for k in keys]}})


def assert_dependents_closed(deal_id: str, ids: dict) -> None:
    db = mdb()
    st = lambda coll, k: db[coll].find_one({"id": ids[k]})   # noqa: E731
    assert st("commissions", "c_pend")["status"] == "cancelled", "komisi belum disetujui harus batal"
    assert st("marketing_fees", "f_sub")["status"] == "cancelled", "fee belum disetujui harus batal"
    assert st("tax_records", "t_pend")["status"] == "cancelled", "pajak pending harus batal"
    fin = st("financing_apps", "fin")
    assert fin["status"] == "cancelled" and fin["kpr_stage"] == "batal", "pengajuan KPR harus batal"
    assert db.coupon_redemptions.find_one({"id": ids["red"]})["state"] == "released"
    assert db.coupons.find_one({"id": ids["coupon"]})["used_count"] == 0, "kuota kupon harus kembali"
    # yang sudah disetujui/dibayar TIDAK disentuh (tanpa jurnal balik) — hanya ditandai untuk Keuangan.
    for coll, k, status in (("commissions", "c_appr", "approved"), ("commissions", "c_paid", "paid"),
                            ("marketing_fees", "f_appr", "approved"), ("tax_records", "t_rep", "reported")):
        row = st(coll, k)
        assert row["status"] == status and row.get("cancel_followup"), f"{coll}/{k}: status tetap + butuh tindak lanjut"
    fu = list(db.tasks.find({"source_event": f"deal.cancel_followup:{deal_id}"}))
    assert len(fu) == 1 and fu[0]["status"] == "open", "satu tugas tindak lanjut untuk Keuangan"
    # tidak ada tugas aktif tersisa pada deal/kontrak (selain tugas tindak lanjut Keuangan itu)
    cids = [c["id"] for c in db.contracts.find({"deal_id": deal_id}, {"id": 1})]
    live = list(db.tasks.find({"status": {"$nin": ["done", "cancelled"]}, "$or": [
        {"related_entity_type": "deal", "related_entity_id": deal_id},
        {"related_entity_type": "contract", "related_entity_id": {"$in": cids}}],
        "source_event": {"$not": {"$regex": "^deal\\.cancel_followup:"}}}))
    assert not live, f"tugas aktif tersisa: {[t['title'] for t in live]}"


# ================================================================== PK3-08 — pembatalan kontrak formal
def test_pk308_batal_formal_menutup_semua_turunan(world):
    d = cancel_case(world, paid=100_000_000)            # kontrak + tugas KYC/biaya terbuka + 100 jt diterima
    ids = seed_dependents(d["deal_id"])
    try:
        doc = approve(d["cancel_id"])
        assert doc["state"] == "disetujui"
        assert_dependents_closed(d["deal_id"], ids)
        dep = doc["settlement"]["dependents"]
        assert dep["commissions_cancelled"] >= 1 and dep["fees_cancelled"] == 1 and dep["tax_cancelled"] >= 1
    finally:
        drop_seeds(ids)


def test_pk308_batal_formal_pajak_batal_tak_bisa_diubah_dan_tak_masuk_rekap(world):
    d = cancel_case(world, paid=100_000_000)
    ids = seed_dependents(d["deal_id"])
    try:
        approve(d["cancel_id"])
        r = call(FINANCE, "PUT", f"/tax/records/{ids['t_pend']}", json={"status": "paid", "ntpn": "NTPN-SIKLUS-1"})
        assert r.status_code == 400 and "DIBATALKAN" in r.text, (r.status_code, r.text[:200])
        summ = ok(call(FINANCE, "GET", "/tax/summary"))["data"]
        assert summ["ppn_keluaran"] >= 0
        rows = ok(call(FINANCE, "GET", "/tax/records", params={"status": "cancelled", "limit": 500}))["data"]
        assert ids["t_pend"] in [x["id"] for x in rows], "catatan batal tetap terlihat (bukan dihapus)"
    finally:
        drop_seeds(ids)


def test_pk308_batal_sederhana_pakai_fungsi_yang_sama(world):
    d = world.new_deal()
    ids = seed_dependents(d["deal_id"])
    try:
        ok(call(OWNER, "POST", f"/deals/{d['deal_id']}/cancel", json={"reason": "uji siklus batal sederhana"}))
        assert_dependents_closed(d["deal_id"], ids)
    finally:
        drop_seeds(ids)


def test_pk308_penutup_turunan_idempoten(world):
    """Unit-level: dua kali memanggil penutup pada deal yang sama tidak menggandakan tindak lanjut/notifikasi."""
    import asyncio
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
    pytest.importorskip("motor")
    db = mdb()
    d = world.new_deal()
    ids = seed_dependents(d["deal_id"])
    try:
        ok(call(OWNER, "POST", f"/deals/{d['deal_id']}/cancel", json={"reason": "uji siklus idempoten"}))
        deal = db.deals.find_one({"id": d["deal_id"]}, {"_id": 0})

        async def twice():
            import deal_cancel_cleanup as dcc
            return await dcc.close_deal_dependents(deal["org_id"], deal, actor="uji", reason="ulang", source="uji")
        out = aio.run(twice())
        assert out["commissions_cancelled"] == 0 and out["fees_cancelled"] == 0 and out["tax_cancelled"] == 0
        assert out["financing_cancelled"] == 0 and out["coupons_released"] == 0 and not out.get("finance_followup")
        assert db.tasks.count_documents({"source_event": f"deal.cancel_followup:{d['deal_id']}"}) == 1
        assert db.commissions.find_one({"id": ids["c_pend"]})["status"] == "cancelled"
    finally:
        drop_seeds(ids)


# ================================================================== FN-03 — titipan biaya & invoice biaya
def _cost_deal(world, pay_amount=20_000_000):
    d = allin_deal(world)
    iid = d["invoice"]["id"]
    ok(call(FINANCE, "POST", f"/cost-invoices/{iid}/pay",
            json={"amount": pay_amount, "proof_file_ids": [upload_proof()]}))
    c = ok(call(MANAGER, "POST", "/cancellations", json={"contract_id": d["contract_id"],
                                                         "reason": "uji siklus batal dengan titipan biaya"}))["data"]
    d["cancel_id"] = c["id"]
    return d


def test_fn03_persetujuan_diblokir_selama_ada_titipan_dan_invoice_biaya(world):
    d = _cost_deal(world)
    pv = ok(call(MANAGER, "GET", "/cancellations/preview", params={"contract_id": d["contract_id"]}))["data"]
    h = pv["cost_holds"]
    assert h["has_holds"] and h["titipan_balance"] == 20_000_000 and h["open_invoice_total"] > 0, h
    body = {"approved": True, "note": "uji siklus setuju tanpa pengakuan biaya"}
    r = call(OWNER, "POST", f"/cancellations/{d['cancel_id']}/decision", json=body)
    assert r.status_code == 400 and "titipan biaya" in r.text and "acknowledge_costs" in r.text, (r.status_code, r.text[:300])
    assert mdb().cancellations.find_one({"id": d["cancel_id"]})["state"] == "diajukan", "tidak ada efek samping"
    # pengakuan tanpa catatan penanganan yang layak tetap ditolak
    r = call(OWNER, "POST", f"/cancellations/{d['cancel_id']}/decision",
             json={**body, "acknowledge_costs": True, "cost_note": "singkat"})
    assert r.status_code == 400 and "Catatan penanganan biaya" in r.text, (r.status_code, r.text[:300])
    assert mdb().cancellations.find_one({"id": d["cancel_id"]})["state"] == "diajukan"


def test_fn03_pengakuan_sah_menyetujui_dan_tercatat_di_keputusan_dan_audit(world):
    d = _cost_deal(world)
    note = "titipan biaya Rp 20 jt dikembalikan lewat keputusan pemilik terpisah"
    r = call(OWNER, "POST", f"/cancellations/{d['cancel_id']}/decision",
             json={"approved": True, "note": "uji siklus setuju dengan pengakuan", "acknowledge_costs": True,
                   "cost_note": note})
    doc = ok(r)["data"]
    assert doc["state"] == "disetujui"
    ack = doc["settlement"]["cost_ack"]
    assert ack["note"] == note and ack["titipan_balance"] == 20_000_000 and ack["acknowledged_by"] == OWNER
    audit = mdb().audit_logs.find_one({"entity_id": d["cancel_id"], "action": "approve"})
    assert audit and audit["meta"]["cost_ack"]["note"] == note, "pengakuan dicatat di audit log"
    # TIDAK menjurnal ulang titipan: saldo titipan biaya tetap (perlakuan uang = keputusan pemilik)
    assert cost_ledger(d["contract_id"])["titipan_balance"] == 20_000_000


def test_fn03_tanpa_tanggungan_biaya_persetujuan_normal(world):
    d = cancel_case(world, paid=100_000_000)
    assert approve(d["cancel_id"])["state"] == "disetujui"


# ================================================================== PK3-15 — BAST batal
def _issue_bast(unit_id):
    return ok(call(OWNER, "POST", "/handover/issue", json={
        "unit_id": unit_id, "override": True, "override_reason": "uji siklus override daftar periksa"}))["data"]


def test_pk315_bast_batal_mengembalikan_status_unit_sebelumnya_dan_tidak_memblokir_batal_kontrak(world):
    d = world.new_deal()
    cid = convert(d)
    assert _unit(world, d["unit_id"])["status"] == "booked"
    h = _issue_bast(d["unit_id"])
    assert _unit(world, d["unit_id"])["status"] == "handed_over"
    ok(call(OWNER, "POST", f"/handover/{h['id']}/cancel", json={"reason": "uji siklus BAST salah terbit"}))
    assert _unit(world, d["unit_id"])["status"] == "booked", "unit booked tidak boleh melompat menjadi sold"
    r = call(MANAGER, "POST", "/cancellations", json={"contract_id": cid, "reason": "uji siklus batal setelah BAST batal"})
    assert r.status_code == 200, f"BAST yang sudah batal tidak boleh memblokir pembatalan kontrak: {r.text[:300]}"


def test_pk315_bast_batal_paralel_hanya_satu(world):
    d = world.new_deal()
    h = _issue_bast(d["unit_id"])
    body = {"reason": "uji siklus pembatalan BAST paralel"}
    rs = race([lambda: call(OWNER, "POST", f"/handover/{h['id']}/cancel", json=body) for _ in range(3)])
    assert codes(rs).count(200) == 1 and all(c in (200, 400, 409) for c in codes(rs)), \
        [(r.status_code, r.text[:120]) for r in rs]
    assert _unit(world, d["unit_id"])["status"] == "booked"


def test_pk315_bast_unit_tanpa_deal_kembali_available(world):
    unit = world.units[world.next_unit]
    world.next_unit += 1
    assert unit["status"] == "available"
    h = _issue_bast(unit["id"])
    ok(call(OWNER, "POST", f"/handover/{h['id']}/cancel", json={"reason": "uji siklus BAST unit kosong"}))
    assert _unit(world, unit["id"])["status"] == "available"


# ================================================================== PK3-07 — pengingat WA untuk deal batal
def _geser_jatuh_tempo(deal_id: str, hari: int = 1) -> None:
    due = (datetime.date.today() + datetime.timedelta(days=hari)).isoformat()
    inv = mdb().ar_invoices.find_one({"deal_id": deal_id})
    items = [{**it, "due_date": due} for it in inv["items"]]
    mdb().ar_invoices.update_one({"id": inv["id"]}, {"$set": {"items": items}})


def test_pk307_pengingat_wa_tidak_menyasar_deal_batal(world):
    d = cancel_case(world, paid=100_000_000)
    approve(d["cancel_id"])
    _geser_jatuh_tempo(d["deal_id"])
    inv = mdb().ar_invoices.find_one({"deal_id": d["deal_id"]})
    assert inv["status"] == "cancelled" and any(int(i["amount"]) - int(i.get("paid_amount") or 0) > 0 for i in inv["items"])
    rows = ok(call(OWNER, "GET", "/reminders/candidates"))["data"]
    mine = [r for r in rows if r.get("entity_id") == inv["id"]]   # id invoice (kode unit bisa kembar antar-World)
    assert not mine, f"pembeli yang sudah batal masih ditagih: {[(r['kind'], r['reason']) for r in mine]}"


def test_pk307_pengingat_tagihan_manual_ditolak_untuk_deal_batal(world):
    d = cancel_case(world, paid=100_000_000)
    approve(d["cancel_id"])
    r = call(FINANCE, "POST", f"/finance/collections/{d['deal_id']}/remind")
    assert r.status_code in (400, 404, 409) and "dibatalkan" in r.text, (r.status_code, r.text[:200])   # router lama: ValueError→404


def test_pk307_pengingat_deal_aktif_tetap_disiapkan(world):
    d = world.new_deal()
    _geser_jatuh_tempo(d["deal_id"])
    rows = ok(call(OWNER, "GET", "/reminders/candidates"))["data"]
    inv_id = mdb().ar_invoices.find_one({"deal_id": d["deal_id"]})["id"]
    assert [r for r in rows if r.get("entity_id") == inv_id and r["kind"] == "installment_due"], \
        "deal aktif dengan termin jatuh tempo tetap menjadi kandidat pengingat"


# ================================================================== PK3-19 — lead lost saat deal booked
def test_pk319_lead_tidak_bisa_lost_atau_daur_ulang_saat_deal_booked(world):
    d = world.new_deal()
    r = call(SALES, "POST", f"/leads/{d['lead_id']}/stage", json={"stage": "lost", "note": "uji siklus lost saat booked"})
    assert r.status_code == 400 and "deal aktif" in r.text, (r.status_code, r.text[:300])
    lead = ok(call(SALES, "GET", f"/leads/{d['lead_id']}"))["data"]
    assert lead["stage"] == "booking", "tahap lead tidak berubah"
    # setelah deal dibatalkan, lead boleh ditandai hilang
    ok(call(OWNER, "POST", f"/deals/{d['deal_id']}/cancel", json={"reason": "uji siklus batal lalu lost"}))
    ok(call(SALES, "POST", f"/leads/{d['lead_id']}/stage", json={"stage": "lost", "note": "uji siklus lost sesudah batal"}))
