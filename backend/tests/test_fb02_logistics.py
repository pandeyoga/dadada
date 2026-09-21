"""FB-02 — Modul Logistik (pengiriman) + komentar ilustrasi AI galeri desain."""
import io
import os

import pytest
import requests
from dotenv import dotenv_values

frontend_env = dotenv_values("/app/frontend/.env")
base = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not base:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
BASE_URL = base.rstrip("/")
ENT = "ent_ksc"
PWD = "demo12345"

JPG = bytes.fromhex(
    "ffd8ffe000104a46494600010100000100010000ffdb004300ffffffffffffffffffffffffffffffff"
    "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
    "ffffffffffffffffffffffffffffffffffc00011080001000103012200021101031101ffc400"
    "1f0000010501010101010100000000000000000102030405060708090a0bffc400b510000201030302"
    "0403050504040000017d01020300041105122131410613516107227114328191a1082342b1c1551552"
    "6274f1a3a2b2c2091a161718191a25262728292a3435363738393a434445464748494a535455565758"
    "595a636465666768696a737475767778797a838485868788898a92939495969798999aa2a3a4a5a6a7"
    "a8a9aab2b3b4b5b6b7b8b9bac2c3c4c5c6c7c8c9cad2d3d4d5d6d7d8d9dae1e2e3e4e5e6e7e8e9eaf1"
    "f2f3f4f5f6f7f8f9faffda0008010100003f00fbfeffd9"
)


def _login(email):
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": PWD}, timeout=30)
    if r.status_code != 200:
        pytest.fail(f"login {email} -> {r.status_code} {r.text[:200]}")
    return r.json()["token"]


def _sess(email):
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {_login(email)}", "X-Entity-Id": ENT})
    return s


@pytest.fixture(scope="module")
def admin():
    return _sess("admin@kainnusantara.id")


@pytest.fixture(scope="module")
def driver():
    return _sess("driver@kainnusantara.id")


@pytest.fixture(scope="module")
def sales():
    return _sess("sales@kainnusantara.id")


@pytest.fixture(scope="module")
def designer():
    return _sess("designer@kainnusantara.id")


# ---------- meta / summary / unassigned ----------
class TestLogisticsRead:
    def test_meta(self, admin):
        r = admin.get(f"{BASE_URL}/api/logistics/meta")
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert set(d["modes"]) == {"expedition", "own_fleet"}
        assert d["statuses"] == ["prepared", "loaded", "in_transit", "delivered", "completed", "failed"]
        assert d["transitions"]["prepared"] == ["loaded"]
        assert d["transitions"]["completed"] == []
        assert d["status_label"]["delivered"] == "Terkirim"

    def test_summary(self, admin):
        r = admin.get(f"{BASE_URL}/api/logistics/summary", params={"entity_id": ENT})
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert isinstance(d["counts"], dict) and "prepared" in d["counts"]
        assert d["total"] == sum(d["counts"].values())
        assert isinstance(d["late"], int)

    def test_unassigned(self, admin):
        r = admin.get(f"{BASE_URL}/api/logistics/shipments/unassigned", params={"entity_id": ENT})
        assert r.status_code == 200, r.text[:300]
        rows = r.json()
        ids = [x["id"] for x in rows]
        assert "shp_b723675b50f0" not in ids, "shipment already used must not be listed"
        for x in rows:
            assert not x.get("logistics_id")
            assert isinstance(x.get("shipping_address"), str)
            assert "_id" not in x

    def test_list_deliveries(self, admin):
        r = admin.get(f"{BASE_URL}/api/logistics/deliveries", params={"entity_id": ENT})
        assert r.status_code == 200, r.text[:300]
        rows = r.json()
        assert any(x["number"] == "KSC/LG-00002" for x in rows), [x["number"] for x in rows]


# ---------- create + full happy flow ----------
@pytest.fixture(scope="module")
def created(admin):
    r = admin.get(f"{BASE_URL}/api/logistics/shipments/unassigned", params={"entity_id": ENT})
    rows = r.json()
    if not rows:
        pytest.skip("no unassigned shipment available")
    ship = rows[0]
    res = admin.post(f"{BASE_URL}/api/logistics/deliveries", json={
        "shipment_ids": [ship["id"]], "mode": "expedition",
        "courier_name": "JNE", "eta": "2026-09-05"})
    assert res.status_code == 200, res.text[:400]
    doc = res.json()
    return {"ship": ship, "doc": doc}


class TestCreate:
    def test_create_ok(self, admin, created):
        d = created["doc"]
        assert d["number"].endswith("LG-") is False and "LG-" in d["number"]
        assert d["status"] == "prepared"
        assert d["mode"] == "expedition" and d["courier_name"] == "JNE"
        assert isinstance(d["destination"], str) and d["destination"]
        assert d["entity_id"] == ENT
        assert "_id" not in d
        g = admin.get(f"{BASE_URL}/api/logistics/deliveries/{d['id']}")
        assert g.status_code == 200
        assert g.json()["number"] == d["number"]
        assert g.json()["status_label"] == "Disiapkan"

    def test_reuse_shipment_400(self, admin, created):
        r = admin.post(f"{BASE_URL}/api/logistics/deliveries", json={
            "shipment_ids": [created["ship"]["id"]], "mode": "expedition"})
        assert r.status_code == 400, r.text[:300]
        assert "sudah diangkut" in r.json()["detail"]

    def test_empty_shipments(self, admin):
        r = admin.post(f"{BASE_URL}/api/logistics/deliveries", json={"shipment_ids": [], "mode": "expedition"})
        assert r.status_code in (400, 422), r.text[:300]

    def test_invalid_mode(self, admin, created):
        r = admin.post(f"{BASE_URL}/api/logistics/deliveries", json={
            "shipment_ids": [created["ship"]["id"]], "mode": "teleport"})
        assert r.status_code == 400, r.text[:300]

    def test_unknown_shipment(self, admin):
        r = admin.post(f"{BASE_URL}/api/logistics/deliveries", json={"shipment_ids": ["shp_nope"]})
        assert r.status_code == 400 and "tidak ditemukan" in r.json()["detail"]


class TestFlowGates:
    def test_position_before_loaded_400(self, admin, created):
        did = created["doc"]["id"]
        r = admin.post(f"{BASE_URL}/api/logistics/deliveries/{did}/positions", json={"location": "Bekasi"})
        assert r.status_code == 400, r.text[:300]

    def test_loaded_requires_load_photo(self, admin, created):
        did = created["doc"]["id"]
        r = admin.post(f"{BASE_URL}/api/logistics/deliveries/{did}/transition", json={"to": "loaded"})
        assert r.status_code == 400 and "FOTO MUAT" in r.json()["detail"]

    def test_upload_load_photo_then_loaded(self, admin, created):
        did = created["doc"]["id"]
        up = admin.post(f"{BASE_URL}/api/logistics/deliveries/{did}/photos",
                        data={"kind": "load", "note": "TEST_muat"},
                        files={"file": ("muat.jpg", io.BytesIO(JPG), "image/jpeg")})
        assert up.status_code == 200, up.text[:400]
        photo = up.json()
        assert photo["kind"] == "load" and photo["size"] == len(JPG)
        created["load_photo_id"] = photo["id"]
        # photo bytes
        pb = admin.get(f"{BASE_URL}/api/logistics/deliveries/{did}/photos/{photo['id']}")
        assert pb.status_code == 200 and pb.content == JPG
        assert pb.headers["content-type"].startswith("image/")

        t = admin.post(f"{BASE_URL}/api/logistics/deliveries/{did}/transition", json={"to": "loaded"})
        assert t.status_code == 200, t.text[:400]
        assert t.json()["status"] == "loaded"

    def test_in_transit_requires_tracking_no(self, admin, created):
        did = created["doc"]["id"]
        r = admin.post(f"{BASE_URL}/api/logistics/deliveries/{did}/transition", json={"to": "in_transit"})
        assert r.status_code == 400 and "NOMOR RESI" in r.json()["detail"]
        p = admin.patch(f"{BASE_URL}/api/logistics/deliveries/{did}", json={"tracking_no": "JNE123"})
        assert p.status_code == 200 and p.json()["tracking_no"] == "JNE123"
        t = admin.post(f"{BASE_URL}/api/logistics/deliveries/{did}/transition", json={"to": "in_transit"})
        assert t.status_code == 200 and t.json()["status"] == "in_transit"

    def test_position(self, admin, created):
        did = created["doc"]["id"]
        r = admin.post(f"{BASE_URL}/api/logistics/deliveries/{did}/positions",
                       json={"location": "Bandung", "note": "TEST_pos"})
        assert r.status_code == 200, r.text[:300]
        assert r.json()["last_position"]["location"] == "Bandung"

    def test_invalid_transition_skip(self, admin, created):
        did = created["doc"]["id"]
        r = admin.post(f"{BASE_URL}/api/logistics/deliveries/{did}/transition", json={"to": "completed"})
        assert r.status_code == 400, r.text[:300]

    def test_delivered_gates(self, admin, created):
        did = created["doc"]["id"]
        r = admin.post(f"{BASE_URL}/api/logistics/deliveries/{did}/transition",
                       json={"to": "delivered", "receiver_name": "Pak Uji"})
        assert r.status_code == 400 and "POD" in r.json()["detail"]
        up = admin.post(f"{BASE_URL}/api/logistics/deliveries/{did}/photos",
                        data={"kind": "pod"},
                        files={"file": ("pod.jpg", io.BytesIO(JPG), "image/jpeg")})
        assert up.status_code == 200, up.text[:300]
        r2 = admin.post(f"{BASE_URL}/api/logistics/deliveries/{did}/transition", json={"to": "delivered"})
        assert r2.status_code == 400 and "penerima" in r2.json()["detail"].lower()
        r3 = admin.post(f"{BASE_URL}/api/logistics/deliveries/{did}/transition",
                        json={"to": "delivered", "receiver_name": "Pak Uji"})
        assert r3.status_code == 200, r3.text[:400]
        assert r3.json()["pod"]["receiver_name"] == "Pak Uji"

    def test_locked_after_delivered(self, admin, created):
        did = created["doc"]["id"]
        p = admin.patch(f"{BASE_URL}/api/logistics/deliveries/{did}", json={"notes": "x"})
        assert p.status_code == 400, p.text[:300]
        pid = created.get("load_photo_id")
        d = admin.delete(f"{BASE_URL}/api/logistics/deliveries/{did}/photos/{pid}")
        assert d.status_code == 400, d.text[:300]

    def test_completed_then_no_further(self, admin, created):
        did = created["doc"]["id"]
        t = admin.post(f"{BASE_URL}/api/logistics/deliveries/{did}/transition", json={"to": "completed"})
        assert t.status_code == 200 and t.json()["status"] == "completed"
        bad = admin.post(f"{BASE_URL}/api/logistics/deliveries/{did}/transition", json={"to": "loaded"})
        assert bad.status_code == 400, bad.text[:300]
        # shipments mirror status
        sj = admin.get(f"{BASE_URL}/api/shipments/{created['ship']['id']}")
        if sj.status_code == 200:
            assert sj.json().get("logistics_status") == "completed"


# ---------- RBAC ----------
class TestRBAC:
    def test_driver_can_view(self, driver):
        r = driver.get(f"{BASE_URL}/api/logistics/deliveries", params={"entity_id": ENT})
        assert r.status_code == 200, r.text[:300]

    def test_driver_cannot_create(self, driver, admin):
        u = admin.get(f"{BASE_URL}/api/logistics/shipments/unassigned", params={"entity_id": ENT}).json()
        sid = u[0]["id"] if u else "shp_x"
        r = driver.post(f"{BASE_URL}/api/logistics/deliveries", json={"shipment_ids": [sid]})
        assert r.status_code == 403, r.text[:300]

    def test_driver_cannot_list_unassigned(self, driver):
        r = driver.get(f"{BASE_URL}/api/logistics/shipments/unassigned", params={"entity_id": ENT})
        assert r.status_code == 403, r.text[:300]

    def test_driver_update_allowed(self, driver, admin):
        """driver bisa unggah foto & catat posisi pada pengiriman yang belum selesai."""
        u = admin.get(f"{BASE_URL}/api/logistics/shipments/unassigned", params={"entity_id": ENT}).json()
        if not u:
            pytest.skip("no unassigned shipment left for driver flow")
        c = admin.post(f"{BASE_URL}/api/logistics/deliveries", json={
            "shipment_ids": [u[0]["id"]], "mode": "own_fleet",
            "vehicle_plate": "b1234xy", "driver_name": "Joko Susilo"})
        assert c.status_code == 200, c.text[:400]
        d = c.json()
        assert d["vehicle_plate"] == "B1234XY"
        did = d["id"]
        up = driver.post(f"{BASE_URL}/api/logistics/deliveries/{did}/photos", data={"kind": "load"},
                         files={"file": ("m.jpg", io.BytesIO(JPG), "image/jpeg")})
        assert up.status_code == 200, up.text[:300]
        t = driver.post(f"{BASE_URL}/api/logistics/deliveries/{did}/transition", json={"to": "loaded"})
        assert t.status_code == 200, t.text[:300]
        pos = driver.post(f"{BASE_URL}/api/logistics/deliveries/{did}/positions", json={"location": "Cikampek"})
        assert pos.status_code == 200, pos.text[:300]
        # failed path
        f1 = driver.post(f"{BASE_URL}/api/logistics/deliveries/{did}/transition", json={"to": "failed"})
        assert f1.status_code == 400 and "Alasan" in f1.json()["detail"]
        f2 = driver.post(f"{BASE_URL}/api/logistics/deliveries/{did}/transition",
                         json={"to": "failed", "reason": "Alamat tidak ditemukan"})
        assert f2.status_code == 200 and f2.json()["status"] == "failed"
        assert f2.json()["fail_reason"] == "Alamat tidak ditemukan"
        back = driver.post(f"{BASE_URL}/api/logistics/deliveries/{did}/transition", json={"to": "prepared"})
        assert back.status_code == 200 and back.json()["status"] == "prepared"
        assert back.json()["fail_reason"] == ""

    def test_sales_view_only(self, sales, created):
        r = sales.get(f"{BASE_URL}/api/logistics/deliveries", params={"entity_id": ENT})
        assert r.status_code == 200, r.text[:300]
        did = created["doc"]["id"]
        p = sales.post(f"{BASE_URL}/api/logistics/deliveries/{did}/photos", data={"kind": "load"},
                       files={"file": ("m.jpg", io.BytesIO(JPG), "image/jpeg")})
        assert p.status_code == 403, p.text[:300]


# ---------- journey ----------
class TestJourney:
    def test_journey_logistics(self, admin):
        r = admin.get(f"{BASE_URL}/api/sales-orders/so_003/journey")
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert "logistics" in d, list(d.keys())
        lg = d["logistics"]
        assert isinstance(lg, list) and lg, "expected KSC/LG-00002 in journey"
        row = next((x for x in lg if x["number"] == "KSC/LG-00002"), None)
        assert row, [x["number"] for x in lg]
        assert row["status"] == "delivered"
        assert row["pod"]["receiver_name"] == "Bu Ani"
        assert row.get("last_position")


# ---------- design gallery illustration comments ----------
GID = "dsgn_cf2ccad1866f"
ILLUS = "file_8f1b4f4ece16"
ARTWORK = "file_89727552413a"


class TestIllustrationComments:
    def test_admin_comment(self, admin):
        r = admin.post(f"{BASE_URL}/api/design-gallery/{GID}/files/{ILLUS}/comments",
                       json={"text": "TEST_komentar admin"})
        assert r.status_code == 200, r.text[:400]
        c = r.json()
        assert c["text"] == "TEST_komentar admin"
        assert c["role"] == "admin" and c["by"]
        assert isinstance(c["id"], str)

    def test_designer_comment_and_persist(self, designer, admin):
        r = designer.post(f"{BASE_URL}/api/design-gallery/{GID}/files/{ILLUS}/comments",
                          json={"text": "TEST_komentar desainer"})
        assert r.status_code == 200, r.text[:400]
        assert r.json()["role"] == "designer"
        g = admin.get(f"{BASE_URL}/api/design-gallery/{GID}")
        assert g.status_code == 200
        f = next(x for x in g.json()["files"] if x["id"] == ILLUS)
        texts = [c["text"] for c in f.get("comments", [])]
        assert "TEST_komentar admin" in texts and "TEST_komentar desainer" in texts

    def test_sales_forbidden(self, sales):
        r = sales.post(f"{BASE_URL}/api/design-gallery/{GID}/files/{ILLUS}/comments",
                       json={"text": "TEST_nope"})
        assert r.status_code == 403, r.text[:300]

    def test_artwork_file_rejected(self, admin):
        r = admin.post(f"{BASE_URL}/api/design-gallery/{GID}/files/{ARTWORK}/comments",
                       json={"text": "TEST_artwork"})
        assert r.status_code == 400, r.text[:300]
        assert "Ilustrasi AI tidak ditemukan" in r.json()["detail"]

    def test_empty_text(self, admin):
        r = admin.post(f"{BASE_URL}/api/design-gallery/{GID}/files/{ILLUS}/comments", json={"text": ""})
        assert r.status_code == 422, r.text[:300]
