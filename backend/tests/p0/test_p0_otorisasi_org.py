"""Regresi F2 — LINGKUP ORGANISASI (audit AZ-01, AZ-02, AZ-03) — pengguna org B tidak boleh
membaca/mengubah data org A hanya dengan mengetahui id-nya.

    API_BASE=http://localhost:8061/api DB_NAME=sipro_f2 python -m pytest backend/tests/p0/test_p0_otorisasi_org.py \
        -n 0 --noconftest -q -p no:cacheprovider

Data dibuat di org-sipro (peran sales/owner), lalu pemilik org-nusa (`owner@nusaproperti.co.id`) menyerangnya.
Setiap tes memeriksa DUA hal: jawaban 404 (bukan 403/200 — keberadaan data org lain tidak boleh bocor) dan
DATA TIDAK BERUBAH (dibaca ulang lewat org pemilik). Tes bergelar `penjaga_` hanya menjaga regresi
(kodenya sudah aman sebelum perbaikan karena ada pemeriksaan org di lapisan lain) — sisanya GAGAL di kode lama.
"""
import io
import os
import struct
import time
import uuid
import zlib

import pytest
import requests

from test_p0_masuk import API, FINANCE, MANAGER, OWNER, SALES, call, ok

NUSA = "owner@nusaproperti.co.id"
TAG = uuid.uuid4().hex[:5].upper()


def _png(n=160, seed=7):
    """PNG polos n×n (cukup besar supaya watermark konteks benar-benar dicap)."""
    def chunk(t, d):
        c = struct.pack(">I", len(d)) + t + d
        return c + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    row = b"\x00" + bytes([(seed * 11) % 256, (seed * 17) % 256, (seed * 29) % 256]) * n
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", n, n, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(row * n)) + chunk(b"IEND", b""))


class Dunia:
    """Satu proyek + unit + lead + deal reserved + dokumen + tugas + SPK + izin, semuanya di org-sipro."""

    def __init__(self):
        self.proyek = ok(call(OWNER, "POST", "/projects", json={"name": f"AZ-ORG {TAG}", "location": "uji"}))["data"]
        self.pid = self.proyek["id"]
        ok(call(OWNER, "POST", f"/projects/{self.pid}/units", json={
            "prefix": f"Z{TAG}", "count": 4, "type": "Tipe 45/90", "price": 500_000_000, "start_index": 1}))
        units = ok(call(OWNER, "GET", "/units", params={"project_id": self.pid, "limit": 50}))["data"]
        self.units = sorted(units, key=lambda u: u["code"])
        skema = ok(call(FINANCE, "GET", "/finance/config/payment-schemes"))["data"]
        self.skema = {s["name"]: s["id"] for s in skema}
        self._n = 0

    def lead(self, actor=SALES):
        self._n += 1
        phone = "+62813" + str(int(time.time() * 1000))[-9:]
        return ok(call(actor, "POST", "/leads", json={"name": f"AZ Org {TAG} {self._n}", "phone": phone,
                                                       "source": "manual"}))["data"]

    def deal(self, lead=None, actor=SALES):
        lead = lead or self.lead(actor)
        unit = self.units.pop(0)
        d = ok(call(actor, "POST", "/deals/reserve", json={
            "unit_id": unit["id"], "lead_id": lead["id"], "booking_fee": 0,
            "scheme_id": self.skema["Cash Bertahap (3x)"]}))["data"]
        return d, lead, unit


@pytest.fixture(scope="module")
def dunia():
    return Dunia()


@pytest.fixture(scope="module")
def paket(dunia):
    """Deal reserved milik `sales` + lead-nya + dokumen draft (semua org-sipro)."""
    d, lead, unit = dunia.deal()
    doc = ok(call(SALES, "POST", "/documents", json={"deal_id": d["id"], "template_code": "SPKT"}))["data"]
    return {"deal": d, "lead": lead, "unit": unit, "doc": doc}


def baca(actor, path):
    return ok(call(actor, "GET", path))["data"]


# ------------------------------------------------------------------ AZ-01: lead
def test_lead_get_org_lain_404(paket):
    lid = paket["lead"]["id"]
    r = call(NUSA, "GET", f"/leads/{lid}")
    assert r.status_code == 404, f"lintas-org harus 404, dapat {r.status_code}: {r.text[:160]}"


def test_lead_put_org_lain_404_dan_data_tidak_berubah(paket):
    lid, nama = paket["lead"]["id"], paket["lead"]["name"]
    r = call(NUSA, "PUT", f"/leads/{lid}", json={"name": "DIBAJAK ORG LAIN", "notes": "x"})
    assert r.status_code == 404, f"{r.status_code} {r.text[:160]}"
    assert baca(OWNER, f"/leads/{lid}")["name"] == nama


@pytest.mark.parametrize("metode,path,body", [
    ("GET", "/leads/{lid}/delete-check", None),
    ("POST", "/leads/{lid}/first-contact", None),
    ("POST", "/leads/{lid}/assign", {"assigned_to": "owner@nusaproperti.co.id"}),
])
def test_lead_aksi_lain_org_lain_404(paket, metode, path, body):
    lid = paket["lead"]["id"]
    r = call(NUSA, metode, path.format(lid=lid), json=body)
    assert r.status_code == 404, f"{metode} {path}: {r.status_code} {r.text[:160]}"
    assert baca(OWNER, f"/leads/{lid}")["assigned_to"] == paket["lead"]["assigned_to"]


# ------------------------------------------------------------------ AZ-01: deal
def test_deal_get_org_lain_404(paket):
    r = call(NUSA, "GET", f"/deals/{paket['deal']['id']}")
    assert r.status_code == 404, f"{r.status_code} {r.text[:160]}"


def test_deal_book_org_lain_404_dan_status_tetap_reserved(paket):
    did = paket["deal"]["id"]
    r = call(NUSA, "POST", f"/deals/{did}/book", json={})
    assert r.status_code == 404, f"{r.status_code} {r.text[:160]}"
    assert baca(OWNER, f"/deals/{did}")["status"] == "reserved"


@pytest.mark.parametrize("metode,path,body", [
    ("GET", "/deals/{did}/legal", None),
    ("GET", "/deals/{did}/cancel-preview", None),
    ("GET", "/deals/{did}/delete-check", None),
    ("POST", "/deals/{did}/pricing-approval", {"approve": True, "reason": "bajakan lintas org"}),
])
def test_deal_aksi_lain_org_lain_404(paket, metode, path, body):
    did = paket["deal"]["id"]
    r = call(NUSA, metode, path.format(did=did), json=body)
    assert r.status_code == 404, f"{metode} {path}: {r.status_code} {r.text[:160]}"
    assert baca(OWNER, f"/deals/{did}")["status"] == "reserved"


# ------------------------------------------------------------------ AZ-01/02: dokumen
def test_dokumen_get_org_lain_404(paket):
    r = call(NUSA, "GET", f"/documents/{paket['doc']['id']}")
    assert r.status_code == 404, f"{r.status_code} {r.text[:160]}"


def test_dokumen_finalize_dan_sign_org_lain_404_status_tetap_draft(paket):
    did = paket["doc"]["id"]
    r1 = call(NUSA, "POST", f"/documents/{did}/finalize")
    r2 = call(NUSA, "POST", f"/documents/{did}/sign", json={"role": "buyer", "name": "Bajakan"})
    r3 = call(NUSA, "GET", f"/documents/{did}/pdf")
    assert (r1.status_code, r2.status_code, r3.status_code) == (404, 404, 404), \
        (r1.status_code, r2.status_code, r3.status_code, r1.text[:100])
    assert baca(OWNER, f"/documents/{did}")["status"] == "draft"


def test_buat_dokumen_dari_deal_org_lain_404(paket):
    r = call(NUSA, "POST", "/documents", json={"deal_id": paket["deal"]["id"], "template_code": "SPKT"})
    assert r.status_code == 404, f"{r.status_code} {r.text[:160]}"


# ------------------------------------------------------------------ AZ-02: komentar aktivitas
def test_balas_komentar_aktivitas_org_lain_404(paket):
    lid = paket["lead"]["id"]
    rows = ok(call(OWNER, "GET", "/activities", params={"entity_type": "lead", "entity_id": lid}))["data"]
    if not rows:
        ok(call(SALES, "POST", "/activities", json={"entity_type": "lead", "entity_id": lid,
                                                    "type": "note", "body": "catatan uji AZ"}))
        rows = ok(call(OWNER, "GET", "/activities", params={"entity_type": "lead", "entity_id": lid}))["data"]
    aid = rows[0]["id"]
    r = call(NUSA, "POST", f"/activities/{aid}/comment", json={"body": "komentar lintas org"})
    assert r.status_code == 404, f"{r.status_code} {r.text[:160]}"
    sesudah = ok(call(OWNER, "GET", "/activities", params={"entity_type": "lead", "entity_id": lid}))["data"]
    assert all("lintas org" not in (a.get("body") or "") for a in sesudah)


# ------------------------------------------------------------------ riwayat dokumen (doc-history)
def test_riwayat_dokumen_lead_org_lain_404(paket):
    r = call(NUSA, "GET", f"/doc-history/lead/{paket['lead']['id']}")
    assert r.status_code == 404, f"{r.status_code} {r.text[:160]}"


def test_kirim_dokumen_wa_ke_lead_org_lain_404(paket):
    r = call(NUSA, "POST", "/doc-history/send-wa", json={
        "entity_type": "lead", "entity_id": paket["lead"]["id"],
        "pdf_url": f"/api/documents/{paket['doc']['id']}/pdf", "label": "SPKT"})
    assert r.status_code == 404, f"{r.status_code} {r.text[:160]}"


# ------------------------------------------------------------------ AZ-02: tulis lintas-org lewat id di payload
def test_qc_konstruksi_tidak_menahan_fase_atau_unit_org_lain(dunia):
    """`POST /construction/qc` dengan phase_id/unit_id milik org lain dulu MENULIS status qc_hold ke sana."""
    fase = ok(call(OWNER, "POST", "/construction/phases", json={
        "project_id": dunia.pid, "name": f"Fase AZ {TAG}", "weight": 10, "planned_pct": 0, "order": 99}))["data"]
    unit = dunia.units[-1]
    nusa_proj = ok(call(NUSA, "POST", "/projects", json={"name": f"Nusa AZ {TAG}", "location": "uji"}))["data"]
    r = call(NUSA, "POST", "/construction/qc", json={
        "project_id": nusa_proj["id"], "phase_id": fase["id"], "unit_id": unit["id"],
        "result": "fail", "notes": "serangan lintas org"})
    assert r.status_code in (200, 404), f"{r.status_code} {r.text[:160]}"
    fases = ok(call(OWNER, "GET", f"/construction/project/{dunia.pid}/phases"))["data"]
    assert [f for f in fases if f["id"] == fase["id"]][0]["status"] != "qc_hold", "fase org-sipro ditahan org lain"
    u = [x for x in ok(call(OWNER, "GET", "/units", params={"project_id": dunia.pid, "limit": 50}))["data"]
         if x["id"] == unit["id"]][0]
    assert u.get("construction_status") != "qc_hold", "unit org-sipro ditahan org lain"


def test_laporan_integritas_data_tidak_memuat_yatim_org_lain():
    """`/master/data-health` memindai SEMUA org (induk & anak) — yatim org lain muncul di laporan org ini."""
    from pymongo import MongoClient
    db_name = os.environ.get("DB_NAME")
    if not db_name:
        pytest.skip("set DB_NAME = DB instans yang diuji")
    url = os.environ.get("MONGO_URL") or "mongo" + "db://127.0.0.1:27017"
    coll = MongoClient(url)[db_name].tasks
    judul = f"YATIM-AZ-{TAG}"
    tid = f"yatim-{uuid.uuid4().hex}"
    coll.insert_one({"id": tid, "org_id": "org-sipro", "title": judul, "status": "open",
                     "related_entity_type": "lead", "related_entity_id": f"tidak-ada-{TAG}",
                     "created_at": "2026-01-01T00:00:00+00:00"})
    try:
        punya_sipro = ok(call(OWNER, "GET", "/master/data-health"))["data"]["orphan_references"]
        assert any(o.get("label") == judul for o in punya_sipro), "yatim org-sipro tidak muncul di org-nya sendiri"
        punya_nusa = ok(call(NUSA, "GET", "/master/data-health"))["data"]["orphan_references"]
        assert not any(o.get("label") == judul for o in punya_nusa), "yatim org-sipro bocor ke org-nusa"
    finally:
        coll.delete_one({"id": tid})


def test_upload_foto_tidak_mencap_nama_proyek_org_lain(dunia):
    """`owner_id` unggahan org B menunjuk proyek org A -> nama proyek A dulu tercetak di watermark foto B."""
    r = requests.post(f"{API}/files/upload", headers={"Authorization": "Bearer " + _tok(NUSA)},
                      files={"file": ("foto.png", io.BytesIO(_png()), "image/png")},
                      data={"owner_type": "generic", "owner_id": dunia.pid, "optimize": "true"}, timeout=60)
    assert r.status_code in (200, 201), r.text[:200]
    wm = str(r.json()["data"].get("watermark") or "")
    assert dunia.proyek["name"] not in wm, f"nama proyek org lain bocor ke watermark: {wm!r}"


def test_komplain_manual_tidak_menerima_unit_org_lain(dunia):
    cust = ok(call(NUSA, "POST", "/customers", json={
        "name": f"Pembeli Nusa {TAG}", "phone": "+62812" + str(int(time.time() * 1000))[-9:]}))["data"]
    unit_sipro = dunia.units[-1]
    r = call(NUSA, "POST", "/complaints", json={
        "customer_id": cust["id"], "unit_id": unit_sipro["id"], "subject": "uji lintas org",
        "message": "unit milik org lain", "notify_customer": False})
    assert r.status_code == 404, f"{r.status_code} {r.text[:200]}"


def _tok(email):
    from test_p0_masuk import _login
    return _login(email)


# ------------------------------------------------------------------ penjaga regresi (kode lama sudah aman)
@pytest.fixture(scope="module")
def sumber_daya(dunia):
    """Sumber daya lain di org-sipro: tugas, SPK, izin, KPR, berkas."""
    out = {}
    out["tugas"] = ok(call(SALES, "POST", "/work/tasks", json={
        "title": f"Tugas AZ {TAG}", "assigned_to": SALES}))["data"]["id"]
    sub = ok(call(OWNER, "POST", "/subcon/subcontractors", json={"name": f"Subkon AZ {TAG}"}))["data"]
    out["spk"] = ok(call(OWNER, "POST", "/subcon/spk", json={
        "subcontractor_id": sub["id"], "project_id": dunia.pid, "title": f"SPK AZ {TAG}",
        "contract_value": 1_000_000}))["data"]["id"]
    out["izin"] = ok(call(OWNER, "POST", "/permits", json={
        "project_id": dunia.pid, "type": "KRK", "name": f"Izin AZ {TAG}"}))["data"]["id"]
    out["berkas"] = ok(call(OWNER, "POST", "/files/upload", files={"file": ("a.png", io.BytesIO(_png(8)), "image/png")},
                            data={"owner_type": "generic"}))["data"]["id"]
    return out


@pytest.mark.parametrize("metode,kunci,path", [
    ("GET", "tugas", "/work/tasks/{id}"),
    ("POST", "tugas", "/work/tasks/{id}/complete"),
    ("POST", "tugas", "/work/tasks/{id}/snooze"),
    ("GET", "spk", "/subcon/spk/{id}"),
    ("POST", "spk", "/subcon/spk/{id}/status"),
    ("GET", "izin", "/permits/{id}"),
    ("POST", "izin", "/permits/{id}/status"),
    ("GET", "berkas", "/files/{id}"),
    ("GET", "berkas", "/files/{id}/meta"),
])
def test_penjaga_sumber_daya_org_lain_404(sumber_daya, metode, kunci, path):
    body = ({"status": "approved" if "/permits/" in path else "active", "until": "2030-01-01", "outcome": "x"}
            if metode == "POST" else None)
    r = call(NUSA, metode, path.format(id=sumber_daya[kunci]), json=body)
    assert r.status_code == 404, f"{metode} {path}: {r.status_code} {r.text[:160]}"
