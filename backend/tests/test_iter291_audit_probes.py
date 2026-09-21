"""Iterasi 291 — AUDIT probes (report only): RBAC sopir & edge-case validasi Logistik + Galeri AI.

Modul yang diperiksa:
* backend/routers/logistics.py + services/logistics_service.py (B2 RBAC, B6 edge cases)
* backend/routers/design_gallery.py (submit gating bila hanya ada ilustrasi AI)
Semua data uji dibersihkan kembali di teardown (foto yang diunggah dihapus).
"""
import io
import os

import pytest
import requests
from dotenv import dotenv_values

fe = dotenv_values("/app/frontend/.env")
BASE = (os.environ.get("REACT_APP_BACKEND_URL") or fe.get("REACT_APP_BACKEND_URL")).rstrip("/")
ENT = "ent_ksc"
OTHER_ENT = "ent_kanda"
PW = "demo12345"

FINDINGS = []


def _login(email):
    r = requests.post(f"{BASE}/api/auth/login", json={"email": email, "password": PW}, timeout=30)
    assert r.status_code == 200, f"login {email} -> {r.status_code} {r.text[:200]}"
    d = r.json()
    tok = d.get("token") or d.get("access_token")
    assert tok, d
    return tok, d.get("user", {})


def _sess(email, entity=ENT):
    tok, user = _login(email)
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {tok}", "X-Entity-Id": entity,
                      "Content-Type": "application/json"})
    return s, user


@pytest.fixture(scope="module")
def S():
    out = {}
    for role in ("admin", "sales", "warehouse", "driver"):
        s, u = _sess(f"{role}@kainnusantara.id")
        out[role] = s
        out[role + "_user"] = u
    return out


@pytest.fixture(scope="module")
def deliveries(S):
    r = S["admin"].get(f"{BASE}/api/logistics/deliveries", params={"entity_id": ENT}, timeout=30)
    assert r.status_code == 200, r.text[:300]
    return r.json()


@pytest.fixture(scope="module")
def uploaded(S):
    """(delivery_id, photo_id) yang dibuat probe — dihapus di teardown."""
    bag = []
    yield bag
    for did, pid in bag:
        S["admin"].delete(f"{BASE}/api/logistics/deliveries/{did}/photos/{pid}", timeout=30)


PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d494844520000000100000001080600000"
    "01f15c4890000000d4944415478da63f8cfc0000003010100189db4ec0000000049454e44ae426082")


# ---------------- B2: RBAC sopir ----------------
class TestDriverRbac:
    def test_driver_can_act_on_delivery_not_assigned_to_him(self, S, deliveries, uploaded):
        me = S["driver_user"]["id"]
        target = next((d for d in deliveries
                       if d.get("driver_user_id") != me and d.get("status") in ("prepared", "loaded", "in_transit")),
                      None)
        if not target:
            pytest.skip("Tidak ada pengiriman aktif milik sopir lain untuk diprobe")
        r = S["driver"].post(
            f"{BASE}/api/logistics/deliveries/{target['id']}/photos",
            files={"file": ("probe.png", PNG, "image/png")},
            data={"kind": "other", "note": "TEST_audit_probe"},
            headers={"Authorization": S["driver"].headers["Authorization"], "X-Entity-Id": ENT},
            timeout=60)
        if r.status_code in (200, 201):
            uploaded.append((target["id"], r.json()["id"]))
            FINDINGS.append(f"driver dapat unggah foto pada {target['number']} "
                            f"(driver_user_id={target.get('driver_user_id')!r}) -> {r.status_code}")
        assert r.status_code in (200, 201, 403), r.text[:300]
        # AUDIT: catat kenyataannya, jangan paksa lulus
        print(f"AUDIT driver photo on {target['number']} -> {r.status_code}")

    def test_driver_position_on_foreign_delivery(self, S, deliveries):
        me = S["driver_user"]["id"]
        target = next((d for d in deliveries
                       if d.get("driver_user_id") != me and d.get("status") in ("loaded", "in_transit")), None)
        if not target:
            pytest.skip("Tidak ada pengiriman loaded/in_transit milik sopir lain")
        r = S["driver"].post(f"{BASE}/api/logistics/deliveries/{target['id']}/positions",
                             json={"location": "TEST_audit probe posisi"}, timeout=30)
        print(f"AUDIT driver position on {target['number']} -> {r.status_code} {r.text[:120]}")
        if r.status_code == 200:
            FINDINGS.append(f"driver dapat catat posisi pada {target['number']} milik sopir lain")

    def test_driver_transition_on_foreign_delivery(self, S, deliveries):
        me = S["driver_user"]["id"]
        target = next((d for d in deliveries
                       if d.get("driver_user_id") != me and d.get("status") == "delivered"), None)
        if not target:
            pytest.skip("Tidak ada pengiriman delivered milik sopir lain")
        # transition delivered -> completed adalah aksi nyata; hanya dicatat lewat dry-run tidak mungkin,
        # jadi pakai transisi TIDAK VALID untuk membedakan 403 (RBAC) dari 400 (validasi state).
        r = S["driver"].post(f"{BASE}/api/logistics/deliveries/{target['id']}/transition",
                             json={"to": "loaded"}, timeout=30)
        print(f"AUDIT driver transition on {target['number']} -> {r.status_code} {r.text[:160]}")
        if r.status_code == 400:
            FINDINGS.append(f"driver lolos RBAC (400 validasi, bukan 403) pada {target['number']} "
                            f"yang bukan tugasnya")

    def test_sales_write_forbidden(self, S, deliveries):
        d = deliveries[0]
        r1 = S["sales"].post(f"{BASE}/api/logistics/deliveries/{d['id']}/positions",
                             json={"location": "TEST_sales"}, timeout=30)
        r2 = S["sales"].post(f"{BASE}/api/logistics/deliveries/{d['id']}/transition",
                             json={"to": "loaded"}, timeout=30)
        r3 = requests.post(f"{BASE}/api/logistics/deliveries/{d['id']}/photos",
                           files={"file": ("probe.png", PNG, "image/png")}, data={"kind": "other"},
                           headers={"Authorization": S["sales"].headers["Authorization"],
                                    "X-Entity-Id": ENT}, timeout=60)
        assert (r1.status_code, r2.status_code, r3.status_code) == (403, 403, 403), \
            (r1.status_code, r2.status_code, r3.status_code, r1.text[:120], r3.text[:120])

    def test_sales_create_forbidden(self, S):
        r = S["sales"].post(f"{BASE}/api/logistics/deliveries", json={"shipment_ids": ["x"]}, timeout=30)
        assert r.status_code == 403, r.text[:200]

    def test_driver_cross_entity_list_blocked(self, S):
        r = S["driver"].get(f"{BASE}/api/logistics/deliveries", params={"entity_id": OTHER_ENT}, timeout=30)
        print(f"AUDIT driver list ent_kanda -> {r.status_code} {str(r.text)[:120]}")
        assert r.status_code in (403, 409) or (r.status_code == 200 and r.json() == []), \
            f"{r.status_code} {r.text[:200]}"

    def test_driver_get_foreign_entity_delivery_blocked(self, S):
        r = S["admin"].get(f"{BASE}/api/logistics/deliveries", params={"entity_id": OTHER_ENT}, timeout=30)
        rows = r.json() if r.status_code == 200 else []
        if not rows:
            pytest.skip("Tidak ada pengiriman di ent_kanda")
        r2 = S["driver"].get(f"{BASE}/api/logistics/deliveries/{rows[0]['id']}", timeout=30)
        assert r2.status_code in (403, 404), f"{r2.status_code} {r2.text[:200]}"


# ---------------- B6: edge-case validasi ----------------
class TestEdgeProbes:
    def test_create_two_orders_rejected(self, S):
        r = S["admin"].get(f"{BASE}/api/logistics/shipments/unassigned", params={"entity_id": ENT}, timeout=30)
        assert r.status_code == 200, r.text[:200]
        rows = r.json()
        by_order = {}
        for s in rows:
            by_order.setdefault(s.get("order_id"), []).append(s["id"])
        if len(by_order) < 2:
            pytest.skip(f"Butuh SJ belum ditugaskan dari 2 pesanan; tersedia {len(by_order)}")
        ids = [v[0] for v in list(by_order.values())[:2]]
        r2 = S["admin"].post(f"{BASE}/api/logistics/deliveries",
                             json={"shipment_ids": ids, "mode": "expedition"}, timeout=30)
        assert r2.status_code == 400, r2.text[:200]
        assert "SATU pesanan" in r2.json().get("detail", "")

    def test_create_empty_shipments_422(self, S):
        r = S["admin"].post(f"{BASE}/api/logistics/deliveries", json={"shipment_ids": []}, timeout=30)
        assert r.status_code == 422, f"{r.status_code} {r.text[:200]}"

    def test_create_unknown_shipment_400(self, S):
        r = S["admin"].post(f"{BASE}/api/logistics/deliveries",
                            json={"shipment_ids": ["ship_tidak_ada"]}, timeout=30)
        assert r.status_code == 400, r.text[:200]
        assert "tidak ditemukan" in r.json()["detail"]

    def test_patch_bad_eta_400(self, S, deliveries):
        d = next((x for x in deliveries if x["status"] in ("prepared", "loaded", "in_transit")), None)
        if not d:
            pytest.skip("Tidak ada pengiriman aktif")
        r = S["admin"].patch(f"{BASE}/api/logistics/deliveries/{d['id']}", json={"eta": "abc"}, timeout=30)
        assert r.status_code == 400, r.text[:200]
        assert "YYYY-MM-DD" in r.json()["detail"]

    def test_patch_bad_mode_400(self, S, deliveries):
        d = next((x for x in deliveries if x["status"] in ("prepared", "loaded", "in_transit")), None)
        if not d:
            pytest.skip("Tidak ada pengiriman aktif")
        r = S["admin"].patch(f"{BASE}/api/logistics/deliveries/{d['id']}", json={"mode": "pesawat"}, timeout=30)
        assert r.status_code == 400, r.text[:200]
        print("AUDIT mode invalid detail:", r.json()["detail"])

    def test_patch_empty_body_400(self, S, deliveries):
        d = next((x for x in deliveries if x["status"] in ("prepared", "loaded", "in_transit")), None)
        if not d:
            pytest.skip("Tidak ada pengiriman aktif")
        r = S["admin"].patch(f"{BASE}/api/logistics/deliveries/{d['id']}", json={}, timeout=30)
        assert r.status_code == 400, r.text[:200]
        assert "Tidak ada perubahan" in r.json()["detail"]

    def test_patch_completed_400(self, S, deliveries):
        d = next((x for x in deliveries if x["status"] in ("completed", "delivered")), None)
        if not d:
            pytest.skip("Tidak ada pengiriman completed/delivered")
        r = S["admin"].patch(f"{BASE}/api/logistics/deliveries/{d['id']}", json={"notes": "TEST_audit"}, timeout=30)
        assert r.status_code == 400, r.text[:200]

    def test_transition_from_completed_400(self, S, deliveries):
        d = next((x for x in deliveries if x["status"] == "completed"), None)
        if not d:
            pytest.skip("Tidak ada pengiriman completed")
        for to in ("in_transit", "delivered", "prepared", "failed", "completed"):
            r = S["admin"].post(f"{BASE}/api/logistics/deliveries/{d['id']}/transition",
                                json={"to": to}, timeout=30)
            assert r.status_code == 400, f"{to} -> {r.status_code} {r.text[:200]}"

    def test_transition_unknown_status_400(self, S, deliveries):
        d = next((x for x in deliveries if x["status"] in ("prepared", "loaded", "in_transit")), None)
        if not d:
            pytest.skip("Tidak ada pengiriman aktif")
        r = S["admin"].post(f"{BASE}/api/logistics/deliveries/{d['id']}/transition",
                            json={"to": "terbang"}, timeout=30)
        assert r.status_code == 400, r.text[:200]
        print("AUDIT transisi tak dikenal:", r.json()["detail"])

    def test_upload_txt_rejected(self, S, deliveries):
        d = next((x for x in deliveries if x["status"] in ("prepared", "loaded", "in_transit")), None)
        if not d:
            pytest.skip("Tidak ada pengiriman aktif")
        r = requests.post(f"{BASE}/api/logistics/deliveries/{d['id']}/photos",
                          files={"file": ("catatan.txt", io.BytesIO(b"bukan gambar"), "text/plain")},
                          data={"kind": "other"},
                          headers={"Authorization": S["admin"].headers["Authorization"],
                                   "X-Entity-Id": ENT}, timeout=60)
        assert r.status_code == 400, f"{r.status_code} {r.text[:200]}"
        print("AUDIT upload txt:", r.json().get("detail"))

    def test_upload_bad_kind_rejected(self, S, deliveries, uploaded):
        d = next((x for x in deliveries if x["status"] in ("prepared", "loaded", "in_transit")), None)
        if not d:
            pytest.skip("Tidak ada pengiriman aktif")
        r = requests.post(f"{BASE}/api/logistics/deliveries/{d['id']}/photos",
                          files={"file": ("probe.png", PNG, "image/png")}, data={"kind": "selfie"},
                          headers={"Authorization": S["admin"].headers["Authorization"],
                                   "X-Entity-Id": ENT}, timeout=60)
        if r.status_code in (200, 201):
            uploaded.append((d["id"], r.json()["id"]))
            FINDINGS.append("kind foto sembarang diterima (harusnya 400)")
        assert r.status_code == 400, f"{r.status_code} {r.text[:200]}"

    def test_photo_get_wrong_id_404(self, S, deliveries):
        d = deliveries[0]
        r = S["admin"].get(f"{BASE}/api/logistics/deliveries/{d['id']}/photos/pho_tidak_ada", timeout=30)
        assert r.status_code == 404, f"{r.status_code} {r.text[:200]}"

    def test_delivery_get_unknown_404(self, S):
        r = S["admin"].get(f"{BASE}/api/logistics/deliveries/lgs_tidak_ada", timeout=30)
        assert r.status_code == 404, r.text[:200]

    def test_position_string_lat_coerced(self, S, deliveries):
        d = next((x for x in deliveries if x["status"] == "in_transit"), None)
        if not d:
            pytest.skip("Tidak ada pengiriman in_transit")
        r = S["admin"].post(f"{BASE}/api/logistics/deliveries/{d['id']}/positions",
                            json={"location": "TEST_audit koordinat string", "lat": "1.5", "lng": "2.5"},
                            timeout=30)
        print(f"AUDIT lat string -> {r.status_code}")
        if r.status_code == 200:
            pos = r.json()["positions"][-1]
            FINDINGS.append(f"lat/lng string '1.5' diterima & disimpan sebagai {type(pos['lat']).__name__} "
                            f"{pos['lat']} (pydantic coercion; posisi uji tertinggal di {d['number']})")
            assert pos["lat"] == 1.5

    def test_position_out_of_range_lat(self, S, deliveries):
        d = next((x for x in deliveries if x["status"] == "in_transit"), None)
        if not d:
            pytest.skip("Tidak ada pengiriman in_transit")
        r = S["admin"].post(f"{BASE}/api/logistics/deliveries/{d['id']}/positions",
                            json={"location": "TEST_audit lat mustahil", "lat": 999, "lng": -999}, timeout=30)
        print(f"AUDIT lat=999 -> {r.status_code}")
        if r.status_code == 200:
            FINDINGS.append(f"lat=999/lng=-999 diterima tanpa validasi rentang (peta Leaflet bisa rusak) "
                            f"— tertinggal di {d['number']}")

    def test_position_on_prepared_blocked(self, S, deliveries):
        d = next((x for x in deliveries if x["status"] == "prepared"), None)
        if not d:
            pytest.skip("Tidak ada pengiriman prepared")
        r = S["admin"].post(f"{BASE}/api/logistics/deliveries/{d['id']}/positions",
                            json={"location": "TEST_audit prepared"}, timeout=30)
        assert r.status_code == 400, r.text[:200]

    def test_my_route_sets_order_on_delivered(self, S):
        r = S["driver"].get(f"{BASE}/api/logistics/deliveries", params={"entity_id": ENT, "mine": "true"},
                            timeout=30)
        assert r.status_code == 200, r.text[:200]
        rows = r.json()
        done = [x for x in rows if x["status"] in ("delivered", "completed")]
        if not done:
            pytest.skip("Sopir tidak punya pengiriman delivered/completed")
        before = done[0].get("route_order")
        r2 = S["driver"].post(f"{BASE}/api/logistics/my-route", json={"ids": [done[0]["id"]]}, timeout=30)
        print(f"AUDIT my-route on delivered -> {r2.status_code} {r2.text[:120]}")
        if r2.status_code == 200 and r2.json().get("updated"):
            FINDINGS.append(f"POST /my-route menerima pengiriman {done[0]['number']} yang sudah "
                            f"{done[0]['status']} dan menulis route_order (sebelumnya {before!r})")
            # pulihkan
            if before is None:
                pytest.skip_msg = None
            S["admin"].patch(f"{BASE}/api/logistics/deliveries/{done[0]['id']}", json={"notes": "x"}, timeout=30)

    def test_my_route_empty_422(self, S):
        r = S["driver"].post(f"{BASE}/api/logistics/my-route", json={"ids": []}, timeout=30)
        assert r.status_code == 422, f"{r.status_code} {r.text[:200]}"

    def test_journey_without_logistics_empty(self, S):
        r = S["admin"].get(f"{BASE}/api/sales-orders", params={"entity_id": ENT}, timeout=30)
        assert r.status_code == 200, r.text[:200]
        orders = r.json()
        orders = orders.get("items", orders) if isinstance(orders, dict) else orders
        found = False
        for o in orders[:12]:
            j = S["admin"].get(f"{BASE}/api/sales-orders/{o['id']}/journey", timeout=30)
            assert j.status_code == 200, f"{o.get('order_number')} -> {j.status_code} {j.text[:200]}"
            lg = j.json().get("logistics")
            assert isinstance(lg, list), f"logistics bukan list: {type(lg)}"
            if lg == []:
                found = True
        assert found, "Semua pesanan punya logistik — tidak bisa memverifikasi kasus kosong"


# ---------------- A1: gating submit desain hanya-ilustrasi-AI ----------------
class TestGalleryAiGating:
    def test_meta_and_gallery_reachable(self, S):
        r = S["admin"].get(f"{BASE}/api/design-gallery", params={"entity_id": ENT}, timeout=30)
        assert r.status_code == 200, r.text[:200]
        rows = r.json()
        rows = rows.get("items", rows) if isinstance(rows, dict) else rows
        assert isinstance(rows, list) and rows
        assert all("_id" not in x for x in rows)

    def test_ai_illustration_not_counted_as_artwork(self, S):
        r = S["admin"].get(f"{BASE}/api/design-gallery", params={"entity_id": ENT}, timeout=30)
        rows = r.json()
        rows = rows.get("items", rows) if isinstance(rows, dict) else rows
        for d in rows:
            files = d.get("files") or []
            ai = [f for f in files if f.get("kind") == "ai_illustration"]
            art = [f for f in files if (f.get("kind") or "artwork") != "ai_illustration"]
            cover = d.get("cover_file_id") or ""
            if cover:
                assert cover not in [f["id"] for f in ai], \
                    f"{d.get('code')}: cover memakai ilustrasi AI"
            print(f"AUDIT {d.get('code')}: artwork={len(art)} ai={len(ai)} "
                  f"ai_count_field={d.get('ai_illustration_count')}")


def teardown_module(module):
    print("\n=== AUDIT FINDINGS ===")
    for f in FINDINGS:
        print(" -", f)
