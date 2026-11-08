"""Regresi H-A (1/2) — SISA siklus hidup deal: kedaluwarsa, janji temu & dokumen draft, gerbang biaya (audit PK3-08, FN-03).

    API_BASE=http://localhost:8071/api DB_NAME=sipro_ha MONGO_URL=<uri> \
      python -m pytest backend/tests/p0/test_p0_sisa_siklus.py -n 0 --noconftest -q -p no:cacheprovider

Bukti "merah di kode lama": jalankan terhadap backend kode lama (API_BASE/DB_NAME-nya) dan arahkan sweeper ke kode lama dengan
`P0_BACKEND_DIR=<checkout lama>/backend`. Tiap tes membuat deal/proyek sendiri. Dokumen turunan (komisi, fee, pajak, KPR, kupon)
disemai LANGSUNG ke DB lewat `seed_dependents` (DB_NAME wajib sama dengan backend yang diuji) dan selalu dibersihkan.
Bagian 2/2 (PG-06 AP, uang biaya setelah batal, hapus-paksa) ada di `test_p0_sisa_siklus_2.py`.
"""
import datetime
import os
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

from test_p0_masuk import FINANCE, OWNER, SALES, World, call, ok, upload_proof
from test_p0_masuk_2 import allin_deal, approve, cancel_case, cost_ledger
from test_p0_siklus_deal import assert_dependents_closed, drop_seeds, mdb, now, seed_dependents


@pytest.fixture(scope="module")
def world():
    return World()


# ------------------------------------------------------------------ pembantu
def _waktu(days: float) -> str:
    return (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=days)).isoformat()


def jalankan_sweeper() -> int:
    """`reservation_expiry_sweeper` dari kode yang diuji terhadap DB instans (proses terpisah)."""
    backend = os.environ.get("P0_BACKEND_DIR") or str(Path(__file__).resolve().parents[2])
    r = subprocess.run(
        [sys.executable, "-c",
         "import asyncio, engine_sweepers as e; print('SWEPT', asyncio.run(e.reservation_expiry_sweeper()))"],
        cwd=backend, env={**os.environ, "DB_NAME": os.environ["DB_NAME"]}, capture_output=True, text=True, timeout=180)
    assert r.returncode == 0, r.stderr[-800:]
    return int(r.stdout.strip().split()[-1])


def kedaluwarsakan(deal_id: str) -> None:
    mdb().deals.update_one({"id": deal_id}, {"$set": {"reserved_until": "2020-01-01T00:00:00+00:00"}})


def reserved_deal(world):
    """Deal `reserved` (belum booking) — satu-satunya jenis yang dikenai sweeper."""
    return world.new_deal(booking_fee=0, book=False)


def new_appt(lead_id: str, days: float = 3, who: str = SALES) -> str:
    r = call(who, "POST", "/appointments", json={
        "lead_id": lead_id, "title": f"Survei uji H-A {uuid.uuid4().hex[:6]}", "scheduled_at": _waktu(days),
        "type": "survey"})
    return ok(r)["data"]["id"]


def appt(aid: str) -> dict:
    return mdb().appointments.find_one({"id": aid})


def seed_appointments(lead_id: str) -> dict:
    """Mendatang (harus batal), selesai (harus tetap), sudah lewat tapi masih `scheduled` (sejarah, tetap)."""
    upcoming = new_appt(lead_id, 3)
    done = new_appt(lead_id, 5)
    ok(call(SALES, "POST", f"/appointments/{done}/status", json={"status": "done"}))
    past = str(uuid.uuid4())
    org = mdb().leads.find_one({"id": lead_id})["org_id"]
    mdb().appointments.insert_one({
        "id": past, "org_id": org, "lead_id": lead_id, "title": "Survei lewat (uji H-A)", "scheduled_at": _waktu(-4),
        "type": "survey", "status": "scheduled", "assigned_to": SALES, "created_by": "uji", "created_at": now(),
        "updated_at": now()})
    return {"upcoming": upcoming, "done": done, "past": past}


def assert_appointments(ids: dict) -> None:
    a = appt(ids["upcoming"])
    assert a["status"] == "cancelled" and a.get("cancelled_at") and a.get("cancelled_by") and a.get("cancel_reason"), a
    assert appt(ids["done"])["status"] == "done", "janji temu yang sudah selesai tidak boleh disentuh"
    assert appt(ids["past"])["status"] == "scheduled", "janji temu yang sudah lewat adalah sejarah, bukan 'mendatang'"
    # tugas survei yang lahir dari janji temu mendatang ikut ditutup; milik janji temu selesai tidak
    t = mdb().tasks.find_one({"source_event": f"appointment:{ids['upcoming']}"})
    assert t is None or t["status"] == "cancelled", t


def seed_docs(deal_id: str, contract_id: str = None) -> dict:
    """Draft terikat deal, draft terikat kontrak saja, final, ditandatangani."""
    org = mdb().deals.find_one({"id": deal_id})["org_id"]
    ts = now()
    base = {"org_id": org, "created_at": ts, "updated_at": ts, "signatures": [], "content": "isi uji H-A"}
    ids = {k: str(uuid.uuid4()) for k in ("draft", "draft_kontrak", "final", "signed")}
    rows = [{**base, "id": ids["draft"], "deal_id": deal_id, "status": "draft", "template_code": "SPR_CASH",
             "doc_number": f"UJI-DR-{ids['draft'][:6]}", "title": "SPR draft"},
            {**base, "id": ids["final"], "deal_id": deal_id, "status": "finalized", "template_code": "PPJB",
             "doc_number": f"UJI-FN-{ids['final'][:6]}", "title": "PPJB final"},
            {**base, "id": ids["signed"], "deal_id": deal_id, "status": "signed", "template_code": "SPR_CASH",
             "doc_number": f"UJI-SG-{ids['signed'][:6]}", "title": "SPR ditandatangani"}]
    if contract_id:
        rows.append({**base, "id": ids["draft_kontrak"], "contract_id": contract_id, "deal_id": None, "status": "draft",
                     "template_code": "ADENDUM_SPR", "doc_number": f"UJI-DK-{ids['draft_kontrak'][:6]}",
                     "title": "Adendum draft (terikat kontrak)"})
    mdb().documents.insert_many(rows)
    return ids


def assert_docs(ids: dict, kontrak: bool = False) -> None:
    db = mdb()
    d = db.documents.find_one({"id": ids["draft"]})
    assert d["status"] == "cancelled" and d.get("cancelled_at") and d.get("cancelled_by") and d.get("cancel_reason"), d
    assert d.get("status_before_cancel") == "draft"
    if kontrak:
        assert db.documents.find_one({"id": ids["draft_kontrak"]})["status"] == "cancelled", "draft terikat kontrak"
    assert db.documents.find_one({"id": ids["final"]})["status"] == "finalized", "dokumen final tidak disentuh"
    assert db.documents.find_one({"id": ids["signed"]})["status"] == "signed", "dokumen ditandatangani tidak disentuh"
    for k in ("draft", "final", "signed"):
        assert db.documents.find_one({"id": ids[k]}), "tidak ada dokumen yang dihapus"


def drop_docs(ids: dict) -> None:
    mdb().documents.delete_many({"id": {"$in": list(ids.values())}})


# ================================================================== PK3-08 sisa — kedaluwarsa memakai penutup bersama
def test_kedaluwarsa_menutup_turunan_seperti_batal_manual(world):
    d = reserved_deal(world)
    ids = seed_dependents(d["deal_id"])
    try:
        kedaluwarsakan(d["deal_id"])
        assert jalankan_sweeper() >= 1
        deal = mdb().deals.find_one({"id": d["deal_id"]})
        assert deal["status"] == "expired"
        assert_dependents_closed(d["deal_id"], ids)     # komisi/fee belum disetujui batal, KPR batal, kupon kembali, pajak batal,
        #                                                 yang disetujui/dibayar ditandai tindak lanjut Keuangan (tanpa jurnal balik)
        u = mdb().units.find_one({"id": d["unit_id"]})
        assert u["status"] == "available" and not u.get("reserved_by_deal") and not u.get("deal_id"), "unit tetap dilepas"
    finally:
        drop_seeds(ids)


def test_kedaluwarsa_idempoten_tidak_menggandakan_tindak_lanjut(world):
    d = reserved_deal(world)
    ids = seed_dependents(d["deal_id"])
    try:
        kedaluwarsakan(d["deal_id"])
        jalankan_sweeper()
        jalankan_sweeper()    # kedua kali: deal sudah `expired` → tak disentuh lagi
        assert mdb().tasks.count_documents({"source_event": f"deal.cancel_followup:{d['deal_id']}"}) == 1
        assert mdb().commissions.find_one({"id": ids["c_pend"]})["status"] == "cancelled"
    finally:
        drop_seeds(ids)


def test_kedaluwarsa_mencatat_uang_biaya_yang_menggantung_untuk_keuangan(world):
    """Sweeper tak bisa 'mengakui' titipan/invoice biaya — maka ia menaruhnya di tindak lanjut Keuangan (bukan diam)."""
    d = reserved_deal(world)
    org = mdb().deals.find_one({"id": d["deal_id"]})["org_id"]
    inv_id = str(uuid.uuid4())
    mdb().cost_invoices.insert_one({
        "id": inv_id, "org_id": org, "deal_id": d["deal_id"], "contract_id": None, "number": f"INB-UJI-{inv_id[:6]}",
        "items": [], "total": 9_000_000, "paid": 0, "outstanding": 9_000_000, "status": "unpaid",
        "created_at": now(), "updated_at": now()})
    try:
        kedaluwarsakan(d["deal_id"])
        jalankan_sweeper()
        fu = mdb().tasks.find_one({"source_event": f"deal.cancel_followup:{d['deal_id']}"})
        assert fu and "invoice biaya terbuka" in fu["description"], fu
    finally:
        mdb().cost_invoices.delete_one({"id": inv_id})


# ================================================================== PK3-08 sisa — janji temu & dokumen draft (tiga jalur)
def test_batal_manual_membatalkan_janji_temu_mendatang_dan_dokumen_draft(world):
    d = world.new_deal(booking_fee=0, book=False)
    appts, docs = seed_appointments(d["lead_id"]), seed_docs(d["deal_id"])
    try:
        ok(call(OWNER, "POST", f"/deals/{d['deal_id']}/cancel", json={"reason": "uji sisa siklus batal manual"}))
        assert_appointments(appts)
        assert_docs(docs)
    finally:
        drop_docs(docs)


def test_batal_formal_membatalkan_janji_temu_mendatang_dan_dokumen_draft_tanpa_menyentuh_bap(world):
    d = cancel_case(world, paid=100_000_000)
    appts, docs = seed_appointments(d["lead_id"]), seed_docs(d["deal_id"], d["contract_id"])
    try:
        doc = approve(d["cancel_id"])
        assert doc["state"] == "disetujui"
        assert_appointments(appts)
        assert_docs(docs, kontrak=True)
        bap = mdb().documents.find_one({"id": doc["document_id"]})
        assert bap["status"] == "draft" and bap.get("cancellation_id"), "BAP pembatalan adalah dokumen hasil batal — jangan ikut dibatalkan"
        assert doc["settlement"]["dependents"]["documents_cancelled"] >= 2
    finally:
        drop_docs(docs)


def test_kedaluwarsa_membatalkan_janji_temu_mendatang_dan_dokumen_draft(world):
    d = reserved_deal(world)
    appts, docs = seed_appointments(d["lead_id"]), seed_docs(d["deal_id"])
    try:
        kedaluwarsakan(d["deal_id"])
        jalankan_sweeper()
        assert_appointments(appts)
        assert_docs(docs)
    finally:
        drop_docs(docs)


def test_janji_temu_lead_dengan_deal_hidup_lain_tidak_disentuh(world):
    """Lead masih punya deal lain yang hidup → janji temunya bisa jadi untuk deal itu: dibiarkan. Kontrol positif: lead
    biasa (tanpa deal lain) pada tes yang sama janji temunya DIBATALKAN."""
    d, polos = world.new_deal(booking_fee=0, book=False), world.new_deal(booking_fee=0, book=False)
    org = mdb().deals.find_one({"id": d["deal_id"]})["org_id"]
    lain = str(uuid.uuid4())
    mdb().deals.insert_one({"id": lain, "org_id": org, "lead_id": d["lead_id"], "status": "reserved",
                            "unit_id": None, "created_at": now(), "updated_at": now()})
    try:
        aid, aid_polos = new_appt(d["lead_id"], 4), new_appt(polos["lead_id"], 4)
        ok(call(OWNER, "POST", f"/deals/{d['deal_id']}/cancel", json={"reason": "uji sisa siklus deal lain hidup"}))
        ok(call(OWNER, "POST", f"/deals/{polos['deal_id']}/cancel", json={"reason": "uji sisa siklus lead polos"}))
        assert appt(aid)["status"] == "scheduled", "lead punya deal hidup lain → janji temu dibiarkan"
        assert appt(aid_polos)["status"] == "cancelled"
    finally:
        mdb().deals.delete_one({"id": lain})


def test_dokumen_draft_batal_tidak_bisa_difinalisasi_atau_ditandatangani(world):
    d = world.new_deal(booking_fee=0, book=False)
    docs = seed_docs(d["deal_id"])
    try:
        ok(call(OWNER, "POST", f"/deals/{d['deal_id']}/cancel", json={"reason": "uji sisa siklus draft terkunci"}))
        r = call(OWNER, "POST", f"/documents/{docs['draft']}/finalize")
        assert r.status_code == 400, (r.status_code, r.text[:200])
        r = call(OWNER, "POST", f"/documents/{docs['draft']}/sign", json={"role": "buyer", "name": "Pembeli Uji"})
        assert r.status_code == 400, (r.status_code, r.text[:200])
        assert mdb().documents.find_one({"id": docs["draft"]})["status"] == "cancelled"
    finally:
        drop_docs(docs)


# ================================================================== FN-03 sisa — gerbang biaya di jalur batal satu-klik
def _biaya_deal(world, bayar=20_000_000):
    d = allin_deal(world)
    if bayar:
        ok(call(FINANCE, "POST", f"/cost-invoices/{d['invoice']['id']}/pay",
                json={"amount": bayar, "proof_file_ids": [upload_proof()]}))
    return d


def _n_jurnal(deal_id: str) -> int:
    return mdb().journal_entries.count_documents({"$or": [{"source_deal_id": deal_id}, {"source_event": {"$regex": deal_id}}]})


def test_batal_satu_klik_diblokir_selama_ada_titipan_biaya_dan_invoice_terbuka(world):
    d = _biaya_deal(world)
    pv = ok(call(OWNER, "GET", f"/deals/{d['deal_id']}/cancel-preview"))["data"]
    h = pv["cost_holds"]
    assert pv["requires_cost_ack"] and h["titipan_balance"] == 20_000_000 and h["open_invoice_total"] > 0, h
    r = call(OWNER, "POST", f"/deals/{d['deal_id']}/cancel", json={"reason": "uji sisa siklus batal tanpa pengakuan"})
    assert r.status_code == 400 and "titipan biaya" in r.text and "acknowledge_costs" in r.text, (r.status_code, r.text[:300])
    assert mdb().deals.find_one({"id": d["deal_id"]})["status"] == "booked", "tidak ada efek samping"
    r = call(OWNER, "POST", f"/deals/{d['deal_id']}/cancel", json={
        "reason": "uji sisa siklus batal catatan pendek", "acknowledge_costs": True, "cost_note": "singkat"})
    assert r.status_code == 400 and "Catatan penanganan biaya" in r.text, (r.status_code, r.text[:300])
    assert mdb().deals.find_one({"id": d["deal_id"]})["status"] == "booked"
    assert mdb().units.find_one({"id": mdb().deals.find_one({"id": d["deal_id"]})["unit_id"]})["status"] != "available"


def test_batal_satu_klik_hanya_invoice_biaya_terbuka_tanpa_titipan_tetap_diblokir(world):
    d = _biaya_deal(world, bayar=0)
    r = call(OWNER, "POST", f"/deals/{d['deal_id']}/cancel", json={"reason": "uji sisa siklus invoice terbuka"})
    assert r.status_code == 400 and "invoice biaya terbuka" in r.text, (r.status_code, r.text[:300])
    assert mdb().deals.find_one({"id": d["deal_id"]})["status"] == "booked"


def test_batal_satu_klik_dengan_pengakuan_sah_tercatat_di_deal_dan_audit_tanpa_jurnal_baru(world):
    d = _biaya_deal(world)
    note = "titipan biaya Rp 20 jt dikembalikan lewat keputusan pemilik terpisah"
    n_before, led0 = _n_jurnal(d["deal_id"]), cost_ledger(d["contract_id"])
    r = call(OWNER, "POST", f"/deals/{d['deal_id']}/cancel", json={
        "reason": "uji sisa siklus batal dengan pengakuan", "acknowledge_costs": True, "cost_note": note})
    assert r.status_code == 200, (r.status_code, r.text[:300])
    deal = mdb().deals.find_one({"id": d["deal_id"]})
    assert deal["status"] == "cancelled"
    ack = deal["cancel_cost_ack"]
    assert ack["note"] == note and ack["titipan_balance"] == 20_000_000 and ack["acknowledged_by"] == OWNER, ack
    audit = mdb().audit_logs.find_one({"entity_id": d["deal_id"], "action": "cancel"})
    assert audit and audit["meta"]["cost_ack"]["note"] == note, "pengakuan dicatat di audit log"
    # TIDAK menjurnal ulang titipan/invoice biaya: perlakuan uangnya tetap keputusan pemilik
    assert _n_jurnal(d["deal_id"]) == n_before, "tidak boleh ada jurnal baru akibat batal + pengakuan"
    assert cost_ledger(d["contract_id"])["titipan_balance"] == led0["titipan_balance"] == 20_000_000


def test_batal_satu_klik_tanpa_tanggungan_biaya_tetap_normal(world):
    d = world.new_deal(booking_fee=0, book=False)
    pv = ok(call(OWNER, "GET", f"/deals/{d['deal_id']}/cancel-preview"))["data"]
    assert pv["cost_holds"]["has_holds"] is False and pv["requires_cost_ack"] is False
    ok(call(OWNER, "POST", f"/deals/{d['deal_id']}/cancel", json={"reason": "uji sisa siklus batal tanpa biaya"}))
    assert mdb().deals.find_one({"id": d["deal_id"]})["status"] == "cancelled"
    assert "cancel_cost_ack" not in mdb().deals.find_one({"id": d["deal_id"]})
