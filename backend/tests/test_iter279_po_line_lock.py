"""Iterasi 279 — T5 audit training: baris PO yang sudah diterima TERKUNCI dari revisi.

Cakupan: T5-1 qty naik · T5-2 harga · T5-3 diskon · T5-4 satuan · T5-5 qty < diterima ·
T5-6 hapus baris diterima · T5-7 positif (baris utuh + baris baru, lalu amend tanpa items).
Tes positif SENGAJA ditaruh paling akhir (mengubah data PO).
"""
import os
import requests
import pytest


def _read_frontend_env():
    p = "/app/frontend/.env"
    if os.path.exists(p):
        for line in open(p):
            if line.startswith("REACT_APP_BACKEND_URL="):
                return line.split("=", 1)[1].strip()
    return ""


BASE = (os.environ.get("REACT_APP_BACKEND_URL") or _read_frontend_env()).rstrip("/")
PWD = "demo12345"


def _login(email):
    r = requests.post(f"{BASE}/api/auth/login", json={"email": email, "password": PWD}, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def hdr():
    return {"Authorization": f"Bearer {_login('admin@kainnusantara.id')}", "X-Entity-Id": "ent_ksc"}


@pytest.fixture(scope="module")
def po(hdr):
    rows = requests.get(f"{BASE}/api/purchase-orders?limit=200", headers=hdr, timeout=30).json()
    rows = rows.get("items", rows) if isinstance(rows, dict) else rows
    for p in rows:
        if p.get("status") in ("receiving", "partial") and any(
                float(i.get("received_qty") or 0) > 0 for i in p.get("items", [])):
            full = requests.get(f"{BASE}/api/purchase-orders/{p['id']}", headers=hdr, timeout=30).json()
            print(f"PO uji: {full.get('po_number')} id={full.get('id')} status={full.get('status')} "
                  f"v{full.get('version')} baris={len(full.get('items', []))}")
            return full
    pytest.skip("tidak ada PO diterima sebagian")


def _items(po, **patch):
    out = []
    for it in po["items"]:
        row = {"product_id": it["product_id"], "quantity": float(it["quantity"]), "unit": it.get("unit"),
               "price": float(it.get("price") or 0), "discount_percent": float(it.get("discount_percent") or 0)}
        if float(it.get("received_qty") or 0) > 0:
            row.update(patch)
        out.append(row)
    return out


def _amend(hdr, po, items, reason="TEST_iter279 uji T5", **extra):
    body = {"reason": reason}
    if items is not None:
        body["items"] = items
    body.update(extra)
    return requests.post(f"{BASE}/api/purchase-orders/{po['id']}/amend", headers=hdr, json=body, timeout=30)


class TestT5LineLockNegatif:
    """Baris ber-received_qty>0 terkunci — semua percobaan revisi harus 400."""

    def test_T5_1_naikkan_qty_baris_diterima_ditolak(self, hdr, po):
        rcv = next(i for i in po["items"] if float(i.get("received_qty") or 0) > 0)
        r = _amend(hdr, po, _items(po, quantity=float(rcv["quantity"]) + 10))
        assert r.status_code == 400, r.text
        low = r.text.lower()
        assert "terkunci" in low and "diterima" in low, r.text

    def test_T5_2_ubah_harga_baris_diterima_ditolak(self, hdr, po):
        rcv = next(i for i in po["items"] if float(i.get("received_qty") or 0) > 0)
        r = _amend(hdr, po, _items(po, price=float(rcv["price"] or 0) + 1000))
        assert r.status_code == 400, r.text
        low = r.text.lower()
        assert "terkunci" in low and "harga" in low, r.text

    def test_T5_3_ubah_diskon_baris_diterima_ditolak(self, hdr, po):
        r = _amend(hdr, po, _items(po, discount_percent=7.5))
        assert r.status_code == 400, r.text
        low = r.text.lower()
        assert "terkunci" in low and "diskon" in low, r.text

    def test_T5_4_ubah_satuan_baris_diterima_ditolak(self, hdr, po):
        rcv = next(i for i in po["items"] if float(i.get("received_qty") or 0) > 0)
        cur = (rcv.get("unit") or "meter").strip().lower()
        new_unit = "yard" if cur != "yard" else "meter"
        r = _amend(hdr, po, _items(po, unit=new_unit))
        assert r.status_code == 400, r.text
        low = r.text.lower()
        assert "terkunci" in low and "satuan" in low, r.text

    def test_T5_5_turunkan_qty_di_bawah_diterima_ditolak(self, hdr, po):
        rcv = next(i for i in po["items"] if float(i.get("received_qty") or 0) > 0)
        r = _amend(hdr, po, _items(po, quantity=max(float(rcv["received_qty"]) - 1, 0.5)))
        assert r.status_code == 400, r.text
        assert "diterima" in r.text.lower(), r.text

    def test_T5_6_hapus_baris_diterima_ditolak(self, hdr, po):
        items = [row for row, it in zip(_items(po), po["items"])
                 if float(it.get("received_qty") or 0) <= 0]
        r = _amend(hdr, po, items)
        assert r.status_code == 400, r.text
        assert "tidak bisa dihapus" in r.text.lower(), r.text

    def test_T5_6b_po_tidak_berubah_setelah_semua_penolakan(self, hdr, po):
        cur = requests.get(f"{BASE}/api/purchase-orders/{po['id']}", headers=hdr, timeout=30).json()
        assert int(cur.get("version", 1)) == int(po.get("version", 1)), "versi naik padahal semua amend ditolak"
        assert len(cur.get("items", [])) == len(po.get("items", []))
        for a, b in zip(cur["items"], po["items"]):
            assert float(a["quantity"]) == float(b["quantity"])
            assert float(a.get("price") or 0) == float(b.get("price") or 0)


    # --- POSITIF (mengubah data; sengaja satu kelas agar urut & tak paralel) ---

    def test_T5_7a_baris_utuh_plus_baris_baru_diterima(self, hdr, po):
        prods = requests.get(f"{BASE}/api/products?limit=500", headers=hdr, timeout=30).json()
        prods = prods.get("items", prods) if isinstance(prods, dict) else prods
        used = {i["product_id"] for i in po["items"]}
        cand = next((p for p in prods if p["id"] not in used and p.get("status", "active") == "active"
                     and p.get("lifecycle_status", "released") in ("released", "active")), None)
        if not cand:
            pytest.skip("tidak ada produk tambahan")
        items = _items(po) + [{"product_id": cand["id"], "quantity": 5,
                               "unit": cand.get("base_unit") or "meter",
                               "price": float(cand.get("price") or 1000), "discount_percent": 0}]
        before = int(po.get("version", 1) or 1)
        r = _amend(hdr, po, items, reason="TEST_iter279 tambah baris baru, baris diterima utuh")
        assert r.status_code in (200, 201), r.text
        cur = requests.get(f"{BASE}/api/purchase-orders/{po['id']}", headers=hdr, timeout=30).json()
        assert int(cur.get("version", 1)) == before + 1, cur.get("version")
        assert len(cur.get("items", [])) == len(po["items"]) + 1
        rcv_old = {i["product_id"]: float(i.get("received_qty") or 0) for i in po["items"]}
        for it in cur["items"]:
            if rcv_old.get(it["product_id"], 0) > 0:
                assert float(it.get("received_qty") or 0) == rcv_old[it["product_id"]], \
                    "received_qty baris terkunci berubah setelah amend"

    def test_T5_7b_amend_tanpa_items_diterima(self, hdr, po):
        cur = requests.get(f"{BASE}/api/purchase-orders/{po['id']}", headers=hdr, timeout=30).json()
        before = int(cur.get("version", 1) or 1)
        r = _amend(hdr, po, None, reason="TEST_iter279 hanya catatan", notes="TEST_iter279 catatan amandemen")
        assert r.status_code in (200, 201), r.text
        after = requests.get(f"{BASE}/api/purchase-orders/{po['id']}", headers=hdr, timeout=30).json()
        assert int(after.get("version", 1)) == before + 1
        assert "TEST_iter279" in (after.get("notes") or "")


class TestT5Login:
    """Regresi ringan: login semua peran tetap OK."""

    @pytest.mark.parametrize("email", [
        "admin@kainnusantara.id", "manager@kainnusantara.id", "salesadmin@kainnusantara.id",
        "finance@kainnusantara.id", "sales@kainnusantara.id", "warehouse@kainnusantara.id",
        "designer@kainnusantara.id",
    ])
    def test_login(self, email):
        r = requests.post(f"{BASE}/api/auth/login", json={"email": email, "password": PWD}, timeout=30)
        assert r.status_code == 200, r.text
        assert r.json().get("token")
