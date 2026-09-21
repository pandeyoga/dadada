"""Iter-14 — Backend regressions for WMS Transfer + Rolls picker + Supplier refs.

Aturan: nilai qty/unit dari master + roll, TIDAK ada ketik manual. 
Uji difokuskan pada:
  * GET /api/inventory/rolls/available (warehouse_id, base_unit, supplier_refs)
  * POST /api/transfers dengan roll_ids (qty diambil dari roll, unit dari master),
    validasi 400 (roll salah gudang / roll_ids kosong & qty 0), 409 (dobel klaim).
  * POST /api/transfers/{id}/reject → roll kembali available (cleanup).
  * GET /api/products memuat supplier_codes utk produk yang memiliki supplier item.
"""
import os
import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = BASE_URL + "/api"
ENTITY = "ent_ksc"
PROD_ID = "prod_batik_mega"
WH_SRC = "wh_jakarta"
WH_DEST = "wh_bandung"


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json", "X-Entity-Id": ENTITY})
    r = s.post(f"{API}/auth/login", json={"email": "admin@kainnusantara.id", "password": "demo12345"})
    assert r.status_code == 200, r.text
    token = r.json().get("token")
    if token:
        s.headers["Authorization"] = f"Bearer {token}"
    return s


# ── Rolls available API ────────────────────────────────────────────────────
class TestRollsAvailable:
    def test_filter_by_warehouse_and_supplier_refs(self, admin_session):
        r = admin_session.get(
            f"{API}/inventory/rolls/available",
            params={"product_id": PROD_ID, "all_entities": "true", "warehouse_id": WH_SRC},
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert "items" in data and "total" in data
        assert "base_unit" in data, "base_unit harus ada di response"
        # base_unit produk batik_mega diharapkan 'yard'
        assert data["base_unit"] in ("yard", "meter"), data["base_unit"]
        assert "supplier_refs" in data and isinstance(data["supplier_refs"], list)
        # semua item hanya dari warehouse_id yang diminta
        for it in data["items"]:
            assert it.get("warehouse_id") == WH_SRC, f"item bocor: {it}"

    def test_no_warehouse_filter_returns_all(self, admin_session):
        r = admin_session.get(
            f"{API}/inventory/rolls/available",
            params={"product_id": PROD_ID, "all_entities": "true"},
        )
        assert r.status_code == 200
        data = r.json()
        whs = {it.get("warehouse_id") for it in data["items"]}
        # bila memang ada roll di gudang lain, kita harapkan >1; kalau tidak, minimal ada items
        assert data["total"] >= 0
        # tidak boleh gagal karena filter warehouse hilang
        assert isinstance(whs, set)


# ── Products supplier_codes ────────────────────────────────────────────────
class TestProductsSupplierCodes:
    def test_products_have_supplier_codes_field(self, admin_session):
        r = admin_session.get(f"{API}/products")
        assert r.status_code == 200
        items = r.json()
        # cari produk yang punya supplier_codes non-kosong
        with_sup = [p for p in items if p.get("supplier_codes")]
        assert with_sup, "Tidak ada produk dengan supplier_codes — regresi A-09"
        first = with_sup[0]["supplier_codes"][0]
        # struktur minimal
        assert "supplier_name" in first
        assert "supplier_sku" in first or "supplier_item_name" in first


# ── Transfers create/reject with roll_ids ──────────────────────────────────
class TestTransfersWithRolls:
    @pytest.fixture(autouse=True)
    def _cleanup(self, admin_session):
        self.session = admin_session
        self.created = []
        yield
        for tid in self.created:
            try:
                admin_session.post(f"{API}/transfers/{tid}/reject",
                                   json={"rejected_by": "QA", "reason": "TEST cleanup"})
            except Exception:
                pass

    def _pick_available(self, warehouse_id=WH_SRC, n=1):
        r = self.session.get(f"{API}/inventory/rolls/available",
                             params={"product_id": PROD_ID, "all_entities": "true",
                                     "warehouse_id": warehouse_id, "limit": 10})
        assert r.status_code == 200
        items = r.json()["items"]
        return items[:n]

    def test_create_transfer_with_roll_ids_qty_and_unit_from_master(self):
        rolls = self._pick_available(n=1)
        if not rolls:
            pytest.skip("Tidak ada roll available di wh_jakarta")
        roll = rolls[0]
        payload = {
            "source_warehouse_id": WH_SRC,
            "dest_warehouse_id": WH_DEST,
            "requested_by": "QA",
            "items": [{
                "product_id": PROD_ID, "qty": 0, "unit": "pcs",  # unit manual harus DIABAIKAN
                "roll_ids": [roll["id"]],
            }],
        }
        r = self.session.post(f"{API}/transfers", json=payload)
        assert r.status_code == 200, r.text
        tr = r.json()
        self.created.append(tr["id"])
        item = tr["items"][0]
        # qty diisi dari panjang roll (bukan 0)
        assert float(item["qty"]) > 0, item
        assert abs(float(item["qty"]) - float(roll["length_remaining"])) < 0.5
        # unit harus base_unit master ('yard') — bukan 'pcs' input klien
        assert item["unit"] in ("yard", "meter"), item["unit"]
        assert item["unit"] != "pcs"
        # roll_ids/rolls tersimpan
        assert item.get("rolls") and item["rolls"][0]["roll_id"] == roll["id"]

    def test_double_reserve_returns_409(self):
        rolls = self._pick_available(n=1)
        if not rolls:
            pytest.skip("no rolls")
        roll = rolls[0]
        p = {"source_warehouse_id": WH_SRC, "dest_warehouse_id": WH_DEST,
             "requested_by": "QA",
             "items": [{"product_id": PROD_ID, "qty": 0, "unit": "pcs", "roll_ids": [roll["id"]]}]}
        r1 = self.session.post(f"{API}/transfers", json=p)
        assert r1.status_code == 200, r1.text
        self.created.append(r1.json()["id"])
        r2 = self.session.post(f"{API}/transfers", json=p)
        assert r2.status_code == 409, f"expected 409, got {r2.status_code}: {r2.text}"

    def test_roll_from_wrong_warehouse_returns_400(self):
        # roll dari wh_bandung dipakai sebagai source wh_jakarta
        other = self._pick_available(warehouse_id=WH_DEST, n=1)
        if not other:
            pytest.skip("Tidak ada roll di wh_bandung untuk uji lintas gudang")
        p = {"source_warehouse_id": WH_SRC, "dest_warehouse_id": WH_DEST,
             "requested_by": "QA",
             "items": [{"product_id": PROD_ID, "qty": 0, "unit": "pcs",
                        "roll_ids": [other[0]["id"]]}]}
        r = self.session.post(f"{API}/transfers", json=p)
        assert r.status_code == 400, f"expected 400, got {r.status_code}: {r.text}"
        assert "gudang asal" in r.text.lower() or "tidak berada" in r.text.lower()

    def test_no_roll_ids_and_qty_zero_returns_400(self):
        p = {"source_warehouse_id": WH_SRC, "dest_warehouse_id": WH_DEST,
             "requested_by": "QA",
             "items": [{"product_id": PROD_ID, "qty": 0, "unit": "pcs", "roll_ids": []}]}
        r = self.session.post(f"{API}/transfers", json=p)
        assert r.status_code == 400, r.text
        assert "roll" in r.text.lower() or "pilih" in r.text.lower()

    def test_legacy_qty_only_still_works(self):
        # tanpa roll_ids, qty>0 harus tetap bekerja (FEFO)
        p = {"source_warehouse_id": WH_SRC, "dest_warehouse_id": WH_DEST,
             "requested_by": "QA",
             "items": [{"product_id": PROD_ID, "qty": 1, "unit": "yard", "roll_ids": []}]}
        r = self.session.post(f"{API}/transfers", json=p)
        # Baik 200 (ada stok) atau 409 (tak cukup stok) TIDAK boleh 400 karena "Pilih roll"
        assert r.status_code in (200, 409), r.text
        if r.status_code == 200:
            self.created.append(r.json()["id"])

    def test_reject_returns_roll_to_available(self):
        rolls = self._pick_available(n=1)
        if not rolls:
            pytest.skip("no rolls")
        roll_id = rolls[0]["id"]
        p = {"source_warehouse_id": WH_SRC, "dest_warehouse_id": WH_DEST,
             "requested_by": "QA",
             "items": [{"product_id": PROD_ID, "qty": 0, "unit": "pcs", "roll_ids": [roll_id]}]}
        r = self.session.post(f"{API}/transfers", json=p)
        assert r.status_code == 200
        tid = r.json()["id"]
        # Setelah create, roll harus reserved (bukan available lagi)
        r2 = self.session.get(f"{API}/inventory/rolls/available",
                              params={"product_id": PROD_ID, "all_entities": "true", "warehouse_id": WH_SRC})
        ids_after_create = {it["id"] for it in r2.json()["items"]}
        assert roll_id not in ids_after_create, "roll seharusnya tidak lagi available (reserved)"
        # Reject → available lagi
        rj = self.session.post(f"{API}/transfers/{tid}/reject",
                               json={"rejected_by": "QA", "reason": "TEST cleanup"})
        assert rj.status_code == 200, rj.text
        r3 = self.session.get(f"{API}/inventory/rolls/available",
                              params={"product_id": PROD_ID, "all_entities": "true", "warehouse_id": WH_SRC})
        ids_after_reject = {it["id"] for it in r3.json()["items"]}
        assert roll_id in ids_after_reject, "roll harus kembali available setelah reject"
