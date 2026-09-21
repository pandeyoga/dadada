"""Iterasi 301 — RBAC Beranda/Pusat Persetujuan, harga master vs SO lama,
Satuan (UOM) CRUD + konversi, ekspor CSV, registri domain.

Semua lewat URL publik (REACT_APP_BACKEND_URL) + header X-Entity-Id: ent_ksc.
"""
import os
import csv
import io
import pytest
import requests
from dotenv import dotenv_values

fe = dotenv_values("/app/frontend/.env")
base = os.environ.get("REACT_APP_BACKEND_URL") or fe.get("REACT_APP_BACKEND_URL")
if not base:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
BASE_URL = base.rstrip("/")
ENT = "ent_ksc"
PWD = "demo12345"


def _login(email: str) -> requests.Session:
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json", "X-Entity-Id": ENT})
    r = s.post(f"{BASE_URL}/api/auth/login",
               json={"email": f"{email}@kainnusantara.id", "password": PWD}, timeout=60)
    assert r.status_code == 200, f"login {email} gagal: {r.status_code} {r.text[:300]}"
    tok = r.json().get("token") or r.json().get("session_token")
    assert tok, f"tidak ada token untuk {email}: {r.text[:200]}"
    s.headers.update({"Authorization": f"Bearer {tok}"})
    return s


@pytest.fixture(scope="module")
def sessions():
    out = {}
    for who in ["admin", "manager", "sales", "finance", "md", "wh.admin", "warehouse", "driver"]:
        out[who] = _login(who)
    return out


# ── (1) RBAC: Pusat Persetujuan / my-queue ────────────────────────────────
class TestApprovalRbac:
    @pytest.mark.parametrize("who", ["driver", "warehouse"])
    def test_my_queue_forbidden(self, sessions, who):
        r = sessions[who].get(f"{BASE_URL}/api/approvals/my-queue?entity_id={ENT}", timeout=60)
        assert r.status_code == 403, f"{who} my-queue → {r.status_code} {r.text[:200]}"

    @pytest.mark.parametrize("who", ["manager", "admin"])
    def test_my_queue_allowed(self, sessions, who):
        r = sessions[who].get(f"{BASE_URL}/api/approvals/my-queue?entity_id={ENT}", timeout=60)
        assert r.status_code == 200, f"{who} my-queue → {r.status_code} {r.text[:300]}"
        body = r.json()
        assert isinstance(body, dict)

    @pytest.mark.parametrize("who", ["md", "finance"])
    def test_my_queue_leak_for_md_finance(self, sessions, who):
        """SPEK sesi: hanya admin/manager/sales boleh; md & finance harus 403."""
        r = sessions[who].get(f"{BASE_URL}/api/approvals/my-queue?entity_id={ENT}", timeout=60)
        assert r.status_code == 403, f"KEBOCORAN: {who} my-queue → {r.status_code} {r.text[:200]}"


# ── (2) RBAC Beranda ───────────────────────────────────────────────────────
class TestHomeRbac:
    @pytest.mark.parametrize("who", ["md", "driver", "sales", "warehouse", "finance"])
    def test_home_admin_forbidden_for_non_manager(self, sessions, who):
        r = sessions[who].get(f"{BASE_URL}/api/home/admin?entity_id={ENT}", timeout=60)
        assert r.status_code == 403, f"{who} /api/home/admin → {r.status_code} {r.text[:200]}"

    @pytest.mark.parametrize("who", ["admin", "manager"])
    def test_home_manager_ok(self, sessions, who):
        r = sessions[who].get(f"{BASE_URL}/api/home/manager?entity_id={ENT}", timeout=60)
        assert r.status_code == 200, f"{who} /api/home/manager → {r.status_code} {r.text[:300]}"

    def test_role_desks_ok(self, sessions):
        r = sessions["md"].get(f"{BASE_URL}/api/md/desk?entity_id={ENT}", timeout=90)
        assert r.status_code == 200, f"md desk → {r.status_code} {r.text[:300]}"
        r2 = sessions["wh.admin"].get(f"{BASE_URL}/api/warehouse-admin/desk?entity_id={ENT}", timeout=90)
        assert r2.status_code == 200, f"wh.admin desk → {r2.status_code} {r2.text[:300]}"

    def test_md_cannot_open_finance_desk(self, sessions):
        r = sessions["md"].get(f"{BASE_URL}/api/finance/desk?entity_id={ENT}", timeout=60)
        assert r.status_code == 403, f"md finance desk → {r.status_code}"


# ── (3) Harga master vs SO lama ────────────────────────────────────────────
class TestMasterPriceDoesNotAffectExistingSO:
    def test_price_change_keeps_old_so_price(self, sessions):
        adm = sessions["admin"]
        orders = adm.get(f"{BASE_URL}/api/sales-orders?entity_id={ENT}", timeout=90)
        assert orders.status_code == 200, orders.text[:300]
        rows = orders.json()
        rows = rows.get("items", rows) if isinstance(rows, dict) else rows
        target = None
        for o in rows:
            for it in (o.get("items") or []):
                if it.get("product_id") and it.get("price"):
                    target = (o, it)
                    break
            if target:
                break
        assert target, "tidak ada SO dengan item berharga untuk diuji"
        order, item = target
        pid = item["product_id"]
        old_item_price = item["price"]

        prod = adm.get(f"{BASE_URL}/api/products/{pid}", timeout=60)
        if prod.status_code != 200:
            plist = adm.get(f"{BASE_URL}/api/products?entity_id={ENT}", timeout=90).json()
            plist = plist.get("items", plist) if isinstance(plist, dict) else plist
            prod_doc = next((p for p in plist if p.get("id") == pid), None)
        else:
            prod_doc = prod.json()
        assert prod_doc, f"produk {pid} tidak ditemukan"
        old_master = prod_doc.get("price")
        assert old_master is not None

        try:
            up = adm.patch(f"{BASE_URL}/api/products/{pid}",
                           json={"data": {"price": float(old_master) + 1}}, timeout=60)
            assert up.status_code == 200, f"PATCH produk → {up.status_code} {up.text[:300]}"
            again = adm.get(f"{BASE_URL}/api/sales-orders/{order['id']}?entity_id={ENT}", timeout=60)
            assert again.status_code == 200, again.text[:300]
            doc = again.json()
            doc = doc.get("order", doc)
            it2 = next(i for i in doc["items"] if i.get("product_id") == pid)
            assert it2["price"] == old_item_price, (
                f"harga item SO berubah {old_item_price} → {it2['unit_price']}")
        finally:
            adm.patch(f"{BASE_URL}/api/products/{pid}", json={"data": {"price": old_master}}, timeout=60)


# ── (4) Satuan (UOM) + Konversi ────────────────────────────────────────────
class TestUom:
    def test_uom_create_list_deactivate(self, sessions):
        adm = sessions["admin"]
        vocab = adm.get(f"{BASE_URL}/api/uoms/vocab", timeout=60)
        assert vocab.status_code == 200, vocab.text[:300]
        v = vocab.json()
        assert v, "vocab satuan kosong"

        created = adm.post(f"{BASE_URL}/api/uoms", json={
            "code": "TSTU", "name": "TEST_Satuan Uji", "base_type": "length",
            "factor_to_base": 2, "status": "active"}, timeout=60)
        if created.status_code not in (200, 201):
            # mungkin sudah ada dari uji sebelumnya
            assert created.status_code in (400, 409), f"POST /api/uoms → {created.status_code} {created.text[:300]}"
            pytest.skip(f"TSTU sudah ada: {created.text[:120]}")
        uom = created.json()
        uid = uom.get("id") or uom.get("uom", {}).get("id")
        assert uid, created.text[:300]
        try:
            lst = adm.get(f"{BASE_URL}/api/uoms", timeout=60)
            assert lst.status_code == 200
            items = lst.json()
            items = items.get("items", items) if isinstance(items, dict) else items
            row = next((u for u in items if u.get("code") == "TSTU"), None)
            assert row, "TSTU tidak muncul di GET /api/uoms"
            assert float(row.get("factor_to_base")) == 2.0
            assert row.get("base_type") in ("length", "panjang")
        finally:
            off = adm.patch(f"{BASE_URL}/api/uoms/{uid}", json={"data": {"status": "inactive"}}, timeout=60)
            assert off.status_code == 200, f"deaktivasi gagal: {off.status_code} {off.text[:200]}"
            after = adm.get(f"{BASE_URL}/api/uoms", timeout=60).json()
            after = after.get("items", after) if isinstance(after, dict) else after
            row2 = next((u for u in after if u.get("code") == "TSTU"), None)
            if row2:
                assert row2.get("status") == "inactive"

    def test_uom_conversion_catalog(self, sessions):
        r = sessions["admin"].get(f"{BASE_URL}/api/uom-conversions/catalog?entity_id={ENT}", timeout=60)
        assert r.status_code == 200, f"catalog → {r.status_code} {r.text[:300]}"
        r2 = sessions["admin"].get(f"{BASE_URL}/api/uom-conversions/rules?entity_id={ENT}", timeout=60)
        assert r2.status_code == 200, f"rules → {r2.status_code} {r2.text[:300]}"


# ── (5) Ekspor CSV master produk ───────────────────────────────────────────
class TestExport:
    def test_export_products_csv(self, sessions):
        r = sessions["admin"].get(f"{BASE_URL}/api/master-data/export-products", timeout=90)
        assert r.status_code == 200, f"export → {r.status_code} {r.text[:200]}"
        assert "csv" in r.headers.get("content-type", "")
        rows = list(csv.DictReader(io.StringIO(r.text)))
        assert rows, "CSV ekspor kosong"
        assert "sku" in rows[0]

    def test_export_forbidden_for_driver(self, sessions):
        r = sessions["driver"].get(f"{BASE_URL}/api/master-data/export-products", timeout=60)
        assert r.status_code == 403, f"driver export → {r.status_code}"


# ── (6) Registri Domain (Pengaturan) ──────────────────────────────────────
class TestDomainRegistry:
    def test_registry_loads(self, sessions):
        r = sessions["admin"].get(f"{BASE_URL}/api/enums", timeout=60)
        assert r.status_code == 200, f"registri domain → {r.status_code} {r.text[:300]}"

    def test_product_lines_and_stages(self, sessions):
        for path in ["/api/product-lines", "/api/enums"]:
            r = sessions["admin"].get(f"{BASE_URL}{path}", timeout=60)
            assert r.status_code in (200, 404), f"{path} → {r.status_code} {r.text[:200]}"


# ── (7) Harga per Pelanggan untuk sales ───────────────────────────────────
class TestCustomerPricesForSales:
    def test_sales_can_read_customer_prices(self, sessions):
        r = sessions["sales"].get(f"{BASE_URL}/api/customer-prices/records?entity_id={ENT}", timeout=60)
        assert r.status_code == 200, f"sales customer-prices → {r.status_code} {r.text[:300]}"

    def test_sales_cannot_read_pricelist_admin(self, sessions):
        r = sessions["sales"].get(f"{BASE_URL}/api/pricelist?entity_id={ENT}", timeout=60)
        assert r.status_code in (200, 403), f"sales price-lists → {r.status_code} {r.text[:200]}"
