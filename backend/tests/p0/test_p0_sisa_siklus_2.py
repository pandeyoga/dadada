"""Regresi H-A (2/2) — uang biaya SESUDAH batal (FN-03), tagihan AP atas PO batal (PG-06), hapus-paksa tanpa yatim.

    API_BASE=http://localhost:8071/api DB_NAME=sipro_ha MONGO_URL=<uri> \
      python -m pytest backend/tests/p0/test_p0_sisa_siklus_2.py -n 0 --noconftest -q -p no:cacheprovider

Bagian 1/2 (kedaluwarsa, janji temu, dokumen draft, gerbang biaya batal satu-klik) ada di `test_p0_sisa_siklus.py`.
Pemindai yatim di sini memeriksa SEMUA koleksi (bukan daftar tetap): dokumen baru yang lupa dimasukkan ke kaskade
hapus-paksa menggagalkan tes.
"""
import os
import sys
import uuid

import pytest

from test_p0_masuk import FINANCE, MANAGER, OWNER, World, call, ok
from test_p0_siklus_deal import FINLEAD, drop_seeds, mdb, now, seed_dependents
from test_p0_siklus_hapus import events_idle, rich_deal, wait_until
from test_p0_sisa_siklus import _biaya_deal, _n_jurnal
from test_p0_masuk import upload_proof
from test_p0_masuk_2 import kpr_deal


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))   # impor modul backend yang murni (tanpa DB)


@pytest.fixture(scope="module")
def world():
    return World()


# ================================================================== FN-03 sisa — uang biaya sesudah batal
def _bayar_biaya(iid, amount=1_000_000, who=FINANCE, **extra):
    return call(who, "POST", f"/cost-invoices/{iid}/pay",
                json={"amount": amount, "proof_file_ids": [upload_proof(who)], **extra})


def _salur(cid, amount=1_000_000, who=FINANCE, **extra):
    return call(who, "POST", f"/contracts/{cid}/cost-disbursements",
                json={"component_code": "NOTARY_FEE", "amount": amount, "payee": "Notaris Uji H-A", **extra})


def _batal_dengan_pengakuan(d):
    ok(call(OWNER, "POST", f"/deals/{d['deal_id']}/cancel", json={
        "reason": "uji sisa siklus batal untuk uang biaya", "acknowledge_costs": True,
        "cost_note": "uang biaya akan diputuskan pemilik secara terpisah"}))
    assert mdb().deals.find_one({"id": d["deal_id"]})["status"] == "cancelled"


def _jejak_uang(d):
    db = mdb()
    return (db.cost_receipts.count_documents({"deal_id": d["deal_id"]}),
            db.cost_disbursements.count_documents({"deal_id": d["deal_id"]}), _n_jurnal(d["deal_id"]))


def test_bayar_dan_salur_biaya_sebelum_batal_normal_sesudahnya_ditolak(world):
    d = _biaya_deal(world)
    ok(_bayar_biaya(d["invoice"]["id"]))                 # kontrol: deal hidup → bayar & salur normal
    ok(_salur(d["contract_id"]))
    _batal_dengan_pengakuan(d)
    sebelum = _jejak_uang(d)
    r = _bayar_biaya(d["invoice"]["id"], 1_100_000)     # nominal beda → bukan klik-ganda (409), murni gerbang batal
    assert r.status_code == 400 and "DIBATALKAN" in r.text and "override_cancelled" in r.text, (r.status_code, r.text[:300])
    r = _salur(d["contract_id"], 1_100_000)
    assert r.status_code == 400 and "DIBATALKAN" in r.text, (r.status_code, r.text[:300])
    assert _jejak_uang(d) == sebelum, "tidak ada kuitansi/penyaluran/jurnal baru"


def test_terobosan_hanya_untuk_pemegang_finance_approve_dengan_alasan_dan_tercatat(world):
    d = _biaya_deal(world)
    _batal_dengan_pengakuan(d)
    sebelum = _jejak_uang(d)
    # tanpa finance:approve: ditolak (peran bawaan yang bisa membayar biaya SEMUANYA pemegang approve, jadi diuji pada fungsinya)
    import cancellation_costs as cc
    with pytest.raises(PermissionError):
        cc.override_of({"email": "x"}, False, True, "alasan cukup panjang untuk uji")
    assert cc.override_of({"email": "x"}, False, False, None) is None, "tidak diminta → tanpa terobosan"
    # pemegang izin, tetapi alasan terlalu pendek
    r = _bayar_biaya(d["invoice"]["id"], 1_200_000, who=FINLEAD, override_cancelled=True, override_reason="singkat")
    assert r.status_code == 400 and "Alasan terobosan" in r.text, (r.status_code, r.text[:300])
    assert _jejak_uang(d) == sebelum
    # terobosan sah: berjalan, tercatat di kuitansi & audit log
    alasan = "bayar notaris yang sudah bekerja sebelum batal, disetujui pemilik"
    r = _bayar_biaya(d["invoice"]["id"], 1_300_000, who=FINLEAD, override_cancelled=True, override_reason=alasan)
    rc = ok(r)["data"]["receipt"]
    assert rc["cancel_override"]["reason"] == alasan and rc["cancel_override"]["by"] == FINLEAD, rc
    assert mdb().audit_logs.find_one({"entity_id": d["invoice"]["id"], "action": "override_cancelled"})
    r = _salur(d["contract_id"], 1_400_000, who=FINLEAD, override_cancelled=True, override_reason=alasan)
    disb = ok(r)["data"]["disbursement"]
    assert disb["cancel_override"]["reason"] == alasan
    assert mdb().audit_logs.find_one({"entity_id": disb["id"], "action": "override_cancelled"})


def test_uang_biaya_ditolak_juga_setelah_pembatalan_kontrak_formal(world):
    d = _biaya_deal(world)
    c = ok(call(MANAGER, "POST", "/cancellations", json={
        "contract_id": d["contract_id"], "reason": "uji sisa siklus batal formal dengan titipan biaya"}))["data"]
    ok(call(OWNER, "POST", f"/cancellations/{c['id']}/decision", json={
        "approved": True, "note": "uji sisa siklus setuju", "acknowledge_costs": True,
        "cost_note": "uang biaya diputuskan pemilik terpisah"}))
    sebelum = _jejak_uang(d)
    r = _bayar_biaya(d["invoice"]["id"])
    assert r.status_code == 400 and "DIBATALKAN" in r.text, (r.status_code, r.text[:300])
    r = _salur(d["contract_id"])
    assert r.status_code == 400 and "DIBATALKAN" in r.text, (r.status_code, r.text[:300])
    assert _jejak_uang(d) == sebelum


# ================================================================== PG-06 sisa — tagihan AP atas PO yang batal
def _po_dengan_tagihan(world, setujui=True):
    po = ok(call(FINANCE, "POST", "/procurement/pos", json={
        "project_id": world.project_id, "po_type": "general", "vendor": f"Vendor H-A {uuid.uuid4().hex[:6]}",
        "items": [{"description": "Semen uji H-A", "uom": "sak", "qty": 10, "unit_price": 100_000}]}))["data"]
    ok(call(OWNER, "POST", f"/procurement/pos/{po['id']}/approve", json={}))
    ok(call(FINANCE, "POST", "/procurement/grns", json={"po_id": po["id"], "items": [{"po_item_index": 0, "qty_received": 10}]}))
    bill = ok(call(FINANCE, "POST", "/procurement/bills", json={
        "po_id": po["id"], "claimed": 1_000_000, "retention_pct": 0}))["data"]
    if setujui:
        ok(call(OWNER, "POST", f"/finance/ap/bills/{bill['id']}/approve"))
    return po["id"], bill["id"]


def _batalkan_po_langsung(pid):
    """Keadaan WARISAN: PO sudah `cancelled` padahal tagihannya ada (sebelum batal-PO dijaga). Lewat DB, bukan API."""
    mdb().purchase_orders.update_one({"id": pid}, {"$set": {"status": "cancelled", "updated_at": now()}})


def test_tagihan_menunggu_persetujuan_atas_po_batal_tidak_bisa_disetujui_dan_terlihat_di_daftar(world):
    pid, bid = _po_dengan_tagihan(world, setujui=False)
    _batalkan_po_langsung(pid)
    r = call(OWNER, "POST", f"/finance/ap/bills/{bid}/approve")
    assert r.status_code == 400 and "DIBATALKAN" in r.text, (r.status_code, r.text[:300])
    assert mdb().ap_invoices.find_one({"id": bid})["status"] == "pending_approval"
    assert mdb().journal_entries.count_documents({"source_id": bid}) == 0
    # terlihat di daftar AP: tanda `po_cancelled` + filter
    rows = ok(call(FINANCE, "GET", "/finance/ap/bills", params={"po_cancelled": "true", "limit": 200}))["data"]
    mine = [b for b in rows if b["id"] == bid]
    assert mine and mine[0]["po_cancelled"] is True, rows[:3]
    rows = ok(call(FINANCE, "GET", "/finance/ap/bills", params={"po_cancelled": "false", "limit": 200}))["data"]
    assert bid not in [b["id"] for b in rows]
    assert all(b["po_cancelled"] is False for b in rows if b.get("po_id"))
    detail = ok(call(FINANCE, "GET", f"/finance/ap/bills/{bid}"))["data"]
    assert detail["bill"]["po_cancelled"] is True and detail["po"]["status"] == "cancelled"
    po = ok(call(OWNER, "GET", f"/procurement/pos/{pid}"))
    assert [b["po_cancelled"] for b in po["bills"]] == [True]


def test_tagihan_disetujui_atas_po_batal_tidak_bisa_dibayar(world):
    pid, bid = _po_dengan_tagihan(world, setujui=True)
    _batalkan_po_langsung(pid)
    n_bayar = mdb().payments_out.count_documents({"bill_id": bid})
    for path, body in ((f"/finance/ap/bills/{bid}/pay", {"amount": 500_000}),
                       (f"/finance/ap/bills/{bid}/pay-withholding", {"bill_id": bid, "amount": 500_000, "kind": "pph23", "rate": 2.0})):
        r = call(FINLEAD, "POST", path, json=body)
        assert r.status_code == 400 and "DIBATALKAN" in r.text, (path, r.status_code, r.text[:300])
    b = mdb().ap_invoices.find_one({"id": bid})
    assert b["status"] == "approved" and int(b.get("paid") or 0) == 0
    assert mdb().payments_out.count_documents({"bill_id": bid}) == n_bayar, "tidak ada uang keluar"
    # tidak dihapus: tagihan lama tetap ada dan terlihat bertanda
    rows = ok(call(FINANCE, "GET", "/finance/ap/bills", params={"po_cancelled": "true", "limit": 200}))["data"]
    assert bid in [b["id"] for b in rows]


def test_tagihan_baru_atas_po_batal_ditolak_dan_po_hidup_tetap_normal(world):
    pid, _bid = _po_dengan_tagihan(world, setujui=True)       # PO hidup: setuju & bayar normal (kontrol)
    ok(call(FINLEAD, "POST", f"/finance/ap/bills/{_bid}/pay", json={"amount": 300_000}))
    assert mdb().ap_invoices.find_one({"id": _bid})["paid"] == 300_000
    _batalkan_po_langsung(pid)
    r = call(FINANCE, "POST", "/procurement/bills", json={"po_id": pid, "claimed": 100_000, "retention_pct": 0})
    assert r.status_code == 400 and "DIBATALKAN" in r.text, (r.status_code, r.text[:300])
    assert mdb().ap_invoices.count_documents({"po_id": pid}) == 1


# ================================================================== hapus-paksa: wa_reminders & pemindaian SEMUA koleksi
_ABAIKAN = {"audit_logs", "idempotency_keys", "counters"}
_MASTER = {"customers", "leads", "units", "projects", "users", "deals"}   # tetap ada setelah hapus-paksa deal


def _ids_turunan(did: str) -> list:
    """Semua `id` dokumen turunan deal (koleksi mana pun yang berkunci deal_id) + kontraknya + anak kontrak."""
    db, ids = mdb(), {did}
    names = [n for n in db.list_collection_names() if n not in _ABAIKAN and not n.startswith("system.")]
    for n in names:
        if n in _MASTER:
            continue
        for r in db[n].find({"$or": [{"deal_id": did}, {"source_deal_id": did}, {"converted_deal_id": did}]}, {"id": 1}):
            if r.get("id"):
                ids.add(r["id"])
    cids = [c["id"] for c in db.contracts.find({"deal_id": did}, {"id": 1})]
    ids.update(cids)
    for n in names:
        if n in _MASTER or not cids:
            continue
        for r in db[n].find({"contract_id": {"$in": cids}}, {"id": 1}):
            if r.get("id"):
                ids.add(r["id"])
    return sorted(ids)


def _pindai_yatim(ids: list) -> dict:
    """Koleksi mana pun yang MASIH memuat salah satu `ids` pada field tingkat-atas apa pun (skalar atau larik)."""
    db, hasil = mdb(), {}
    cond = {"$or": [{"$in": ["$$kv.v", ids]},
                    {"$and": [{"$isArray": "$$kv.v"}, {"$gt": [{"$size": {"$setIntersection": ["$$kv.v", ids]}}, 0]}]}]}
    pipe = [{"$match": {"$expr": {"$gt": [{"$size": {"$filter": {
        "input": {"$objectToArray": "$$ROOT"}, "as": "kv", "cond": cond}}}, 0]}}}, {"$limit": 5}]
    for n in db.list_collection_names():
        if n in _ABAIKAN or n.startswith("system."):
            continue
        rows = [{k: (str(v)[:60]) for k, v in r.items() if k not in ("_id", "content", "body", "created_at", "updated_at")}
                for r in db[n].aggregate(pipe)]
        if rows:
            hasil[n] = rows
    return hasil


def test_hapus_paksa_membersihkan_wa_reminders_dan_tidak_menyisakan_rujukan_di_koleksi_mana_pun(world):
    d = rich_deal(world)
    did, db = d["deal_id"], mdb()
    org = db.deals.find_one({"id": did})["org_id"]
    ar_id = db.ar_invoices.find_one({"deal_id": did})["id"]
    bf_id, ho_id, ts = str(uuid.uuid4()), str(uuid.uuid4()), now()
    db.booking_fee_invoices.insert_one({"id": bf_id, "org_id": org, "deal_id": did, "no": f"BF-UJI-{bf_id[:6]}", "amount": 1,
                                        "paid": 0, "outstanding": 1, "status": "unpaid", "created_at": ts})
    db.unit_handovers.insert_one({"id": ho_id, "org_id": org, "deal_id": did, "unit_id": f"u-{ho_id}", "state": "cancelled",
                                  "created_at": ts})
    tag, rem = uuid.uuid4().hex[:6], []
    for etype, eid, key in (("ar_invoice", ar_id, f"installment_due:{ar_id}:{tag}"),
                            ("ar_invoice", ar_id, f"arrears_warning:{did}:{tag}"),
                            ("booking_fee_invoice", bf_id, f"booking_fee_due:{bf_id}:{tag}"),
                            ("unit_handover", ho_id, f"warranty_expiring:{ho_id}:{tag}")):
        rid = str(uuid.uuid4())
        db.wa_reminders.insert_one({"id": rid, "org_id": org, "kind": "installment_due", "dedup_key": key, "entity_type": etype,
                                    "entity_id": eid, "status": "sent", "created_at": ts})
        rem.append(rid)
    kontrol = str(uuid.uuid4())      # pengingat deal LAIN: harus tetap ada
    db.wa_reminders.insert_one({"id": kontrol, "org_id": org, "kind": "installment_due", "dedup_key": f"installment_due:lain:{tag}",
                                "entity_type": "ar_invoice", "entity_id": "ar-deal-lain", "status": "sent", "created_at": ts})
    ids = _ids_turunan(did)
    try:
        assert len(ids) > 8 and ar_id in ids and bf_id in ids
        ok(call(OWNER, "DELETE", f"/deals/{did}", params={"reason": "uji sisa siklus hapus paksa wa_reminders"}))
        assert wait_until(events_idle, 40), "antrean event tidak kosong"
        assert db.wa_reminders.count_documents({"id": {"$in": rem}}) == 0, "log pengingat WA deal yang dihapus harus ikut hilang"
        assert db.wa_reminders.find_one({"id": kontrol}), "pengingat deal lain tidak boleh tersentuh"
        yatim = _pindai_yatim(ids)
        assert not yatim, f"rujukan yatim ke deal/turunannya yang sudah dihapus: {yatim}"
    finally:
        db.wa_reminders.delete_one({"id": kontrol})


def _hapus_dan_pindai(d, alasan):
    ids = _ids_turunan(d["deal_id"])
    ok(call(OWNER, "DELETE", f"/deals/{d['deal_id']}", params={"reason": alasan}))
    assert wait_until(events_idle, 40), "antrean event tidak kosong"
    yatim = _pindai_yatim(ids)
    assert not yatim, f"rujukan yatim ke deal/turunannya yang sudah dihapus: {yatim}"
    return ids


def test_hapus_paksa_deal_biaya_batal_formal_dengan_turunan_tidak_menyisakan_rujukan(world):
    """Deal all-in (invoice/kuitansi/penyaluran biaya) + turunan semai + pembatalan formal (jurnal, BAP, kupon) lalu hapus-paksa."""
    d = _biaya_deal(world)
    ok(_salur(d["contract_id"]))
    ids_semai = seed_dependents(d["deal_id"])
    try:
        c = ok(call(MANAGER, "POST", "/cancellations", json={
            "contract_id": d["contract_id"], "reason": "uji sisa siklus batal formal lalu hapus paksa"}))["data"]
        ok(call(OWNER, "POST", f"/cancellations/{c['id']}/decision", json={
            "approved": True, "note": "uji sisa siklus setuju", "acknowledge_costs": True,
            "cost_note": "uang biaya diputuskan pemilik terpisah"}))
        assert wait_until(events_idle, 40)
        ids = _hapus_dan_pindai(d, "uji sisa siklus hapus paksa deal batal formal")
        assert c["id"] in ids or len(ids) > 10
    finally:
        drop_seeds(ids_semai)


def test_hapus_paksa_deal_kpr_dengan_pencairan_tidak_menyisakan_rujukan(world):
    d = kpr_deal(world)
    ok(call(FINANCE, "POST", f"/contracts/{d['contract_id']}/kpr/disbursements",
            json={"tranche_code": "T1", "file_id": upload_proof()}))
    assert wait_until(events_idle, 40)
    assert mdb().financing_apps.count_documents({"deal_id": d["deal_id"]}) >= 1
    _hapus_dan_pindai(d, "uji sisa siklus hapus paksa deal KPR")
