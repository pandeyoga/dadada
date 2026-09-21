"""Regresi audit KN 2026-09-21 — penjaga entitas jalur TULIS & isolasi sampel (R-3a).

Menggantikan uji R-3a lama yang memukul `/api/sample-requests` (rute sudah dihapus; KN-A08).
Semua uji memakai data demo `seed_realistic.py` (admin@kainnusantara.id / demo12345, entitas
ent_ksc & ent_kanda). Dijalankan lewat `bash scripts/gate.sh` (blok runtime).
"""
import os
import pytest
import requests

API = [l.split("=", 1)[1].strip() for l in open("/app/frontend/.env")
       if l.startswith("REACT_APP_BACKEND_URL=")][0].rstrip("/") + "/api"
PW = os.environ.get("KN_TEST_PASSWORD", "demo12345")
ENTS = ("ent_ksc", "ent_kanda")


def _sess(email="admin@kainnusantara.id", entity="ent_ksc"):
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": email, "password": PW}, timeout=20)
    if r.status_code != 200:
        pytest.skip(f"login gagal ({r.status_code}) — backend/seed belum siap")
    s.headers.update({"Authorization": "Bearer " + r.json()["token"], "X-Entity-Id": entity})
    return s


def _other(ent):
    return "ent_kanda" if ent == "ent_ksc" else "ent_ksc"


def _first_doc(sess, path, params=None):
    r = sess.get(f"{API}/{path}", params=params or {}, headers={"X-Entity-Id": "all"}, timeout=30)
    if r.status_code != 200:
        return None
    data = r.json()
    items = data.get("items") if isinstance(data, dict) else data
    for d in items or []:
        if d.get("entity_id") in ENTS:
            return d
    return None


# ── KN-A07 / R-3a — pesanan sampel: detail & aksi mengikuti badan usaha AKTIF ────
def test_sample_order_isolated_by_active_entity():
    admin = _sess()
    doc = _first_doc(admin, "sample-orders")
    if not doc:
        pytest.skip("tidak ada pesanan sampel demo")
    ent = doc["entity_id"]
    same = admin.get(f"{API}/sample-orders/{doc['id']}", headers={"X-Entity-Id": ent}, timeout=20)
    cross = admin.get(f"{API}/sample-orders/{doc['id']}", headers={"X-Entity-Id": _other(ent)}, timeout=20)
    assert same.status_code in (200, 404, 405), same.text[:200]   # GET detail bisa tak tersedia; yang penting aksi
    # aksi tulis lintas entitas WAJIB ditolak (404 penjaga / 403), bukan 200/400 logika bisnis
    act = admin.post(f"{API}/sample-orders/{doc['id']}/cancel", json={"reason": "TEST lintas entitas"},
                     headers={"X-Entity-Id": _other(ent)}, timeout=20)
    assert act.status_code in (403, 404), f"cancel lintas entitas lolos: {act.status_code} {act.text[:200]}"
    assert cross.status_code in (403, 404, 405)


# ── KN-A01 — void jurnal lintas entitas ditolak ──────────────────────────────────
def test_gl_void_cross_entity_denied():
    admin = _sess()
    je = _first_doc(admin, "gl/journal", {"entity_id": "all"})
    if not je:
        pytest.skip("tidak ada jurnal demo")
    r = admin.post(f"{API}/gl/journal/{je['id']}/void", headers={"X-Entity-Id": _other(je["entity_id"])}, timeout=20)
    assert r.status_code in (403, 404), f"void jurnal lintas entitas lolos: {r.status_code} {r.text[:200]}"


# ── KN-A03 — void kas lintas entitas ditolak ─────────────────────────────────────
def test_cash_void_cross_entity_denied():
    admin = _sess()
    txn = _first_doc(admin, "cash-transactions", {"entity_id": "all"})
    if not txn:
        pytest.skip("tidak ada transaksi kas demo")
    r = admin.post(f"{API}/cash-transactions/{txn['id']}/void",
                   headers={"X-Entity-Id": _other(txn["entity_id"])}, timeout=20)
    assert r.status_code in (403, 404), f"void kas lintas entitas lolos: {r.status_code} {r.text[:200]}"


# ── KN-A04 — bayar vendor bill lintas entitas ditolak ────────────────────────────
def test_vendor_bill_pay_cross_entity_denied():
    admin = _sess()
    bill = _first_doc(admin, "vendor-bills", {"entity_id": "all"})
    if not bill:
        pytest.skip("tidak ada vendor bill demo")
    r = admin.post(f"{API}/vendor-bills/{bill['id']}/pay",
                   json={"amount": 1, "method": "transfer", "cash_type": "kas_besar"},
                   headers={"X-Entity-Id": _other(bill["entity_id"])}, timeout=20)
    assert r.status_code in (403, 404), f"pay bill lintas entitas lolos: {r.status_code} {r.text[:200]}"


# ── KN-A06 — daftar retur beli tanpa parameter = entitas AKTIF saja ──────────────
def test_purchase_return_list_scoped():
    admin = _sess(entity="ent_ksc")
    r = admin.get(f"{API}/purchase-returns", timeout=30)
    assert r.status_code == 200, r.text[:200]
    rows = r.json().get("items", [])
    leaked = [d["number"] for d in rows if d.get("entity_id") and d["entity_id"] != "ent_ksc"]
    assert not leaked, f"retur beli PT lain bocor ke konteks KSC: {leaked[:5]}"


# ── KN-C03 — satu daftar GREEN gate RFID untuk ingest & monitor ──────────────────
def test_rfid_green_lists_identical():
    import sys
    sys.path.insert(0, "/app/backend")
    from services import rfid_service, rfid_ingest_service
    assert rfid_service.GREEN_OUT is rfid_ingest_service.GREEN_OUT_STATUSES
    assert {"committed", "picked", "packed"} <= rfid_service.GREEN_OUT


# ── KN-C05 / KN-A11 — konstanta bersama benar-benar satu sumber ──────────────────
def test_shared_status_constants():
    import sys
    sys.path.insert(0, "/app/backend")
    from services import roll_service, gl_service, costing_service, fulfillment_service, stock_bucket_service
    assert gl_service.PHYSICAL_ROLL_STATUSES is roll_service.PHYSICAL_ROLL_STATUSES
    assert costing_service.LIVE_ROLL_STATUSES == set(roll_service.PHYSICAL_ROLL_STATUSES)
    assert fulfillment_service.OPEN_PO_STATUSES is roll_service.OPEN_PO_STATUSES
    assert stock_bucket_service.OPEN_PO_STATUSES is roll_service.OPEN_PO_STATUSES
