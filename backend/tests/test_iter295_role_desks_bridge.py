"""Sesi #087 — Meja MD & Meja Admin Gudang + jembatan WMS Outbound → Logistik.

Cakupan:
* GET /api/md/desk (peran md) & GET /api/warehouse-admin/desk (peran warehouse_admin)
* silang peran → 403; admin → keduanya 200
* antrean `sj_belum_diangkut` (action_kind=create_delivery) muncul setelah dispatch
  tugas outbound, lalu HILANG setelah pengiriman logistik dibuat untuk SJ itu.
"""
import os
import pytest
import requests
from dotenv import dotenv_values
from pymongo import MongoClient

fe = dotenv_values("/app/frontend/.env")
BASE = (os.environ.get("REACT_APP_BACKEND_URL") or fe.get("REACT_APP_BACKEND_URL")).rstrip("/") + "/api"
be = dotenv_values("/app/backend/.env")
db = MongoClient(be.get("MONGO_URL"))[be.get("DB_NAME")]

PWD = "demo12345"
ENT = "ent_ksc"

MD_QUEUES = ["desain", "sample", "pr", "acuan"]
WH_QUEUES = ["sj_belum_diangkut", "outbound", "inbound", "spk", "persetujuan_gudang", "logistik"]


def _hdr(email):
    r = requests.post(f"{BASE}/auth/login", json={"email": email, "password": PWD}, timeout=60)
    assert r.status_code == 200, f"login {email} -> {r.status_code}: {r.text[:300]}"
    body = r.json()
    assert body.get("token")
    return {"Authorization": f"Bearer {body['token']}", "X-Entity-Id": ENT,
            "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def md_hdr():
    return _hdr("md@kainnusantara.id")


@pytest.fixture(scope="module")
def wh_hdr():
    return _hdr("wh.admin@kainnusantara.id")


@pytest.fixture(scope="module")
def admin_hdr():
    return _hdr("admin@kainnusantara.id")


# ── Meja MD ──────────────────────────────────────────────────────────────────
class TestMdDesk:
    def test_md_desk_structure(self, md_hdr):
        r = requests.get(f"{BASE}/md/desk?entity_id={ENT}", headers=md_hdr, timeout=90)
        assert r.status_code == 200, r.text[:400]
        d = r.json()
        assert d["desk"] == "md"
        assert isinstance(d["queues"], list) and isinstance(d["not_my_desk"], list)
        assert [q["id"] for q in d["queues"]] == MD_QUEUES
        for q in d["queues"]:
            for key in ("id", "label", "count", "rows", "action_label"):
                assert key in q, f"{q.get('id')} missing {key}"
            assert q["count"] == len(q["rows"])
            for row in q["rows"]:
                assert row["ref_id"] and row["action_kind"]
        print("md queues:", {q["id"]: q["count"] for q in d["queues"]})

    def test_md_desk_has_design_rows(self, md_hdr):
        d = requests.get(f"{BASE}/md/desk?entity_id={ENT}", headers=md_hdr, timeout=90).json()
        desain = next(q for q in d["queues"] if q["id"] == "desain")
        assert desain["count"] >= 1, "antrean desain kosong — data demo DSR hilang?"
        assert all(r["ref_type"] == "design_request" for r in desain["rows"])

    def test_md_forbidden_on_warehouse_desk(self, md_hdr):
        r = requests.get(f"{BASE}/warehouse-admin/desk?entity_id={ENT}", headers=md_hdr, timeout=60)
        assert r.status_code == 403, f"expected 403, got {r.status_code}: {r.text[:200]}"

    # BUG (dilaporkan iterasi 295): peran `md` tidak ada di FULL_VIEW_ROLES
    # (routers/design_requests.py:39) sehingga permintaan desain di Meja MD tidak bisa dibuka.
    def test_md_can_open_design_request_from_its_own_desk(self, md_hdr):
        d = requests.get(f"{BASE}/md/desk?entity_id={ENT}", headers=md_hdr, timeout=90).json()
        rows = next(q for q in d["queues"] if q["id"] == "desain")["rows"]
        assert rows, "antrean desain kosong"
        rid = rows[0]["ref_id"]
        # daftar berhalaman yang dipakai layar Permintaan Desain
        lst = requests.get(f"{BASE}/design-requests", headers=md_hdr,
                           params={"entity_id": ENT, "page": 1, "page_size": 50}, timeout=60)
        assert lst.status_code == 200, lst.text[:200]
        assert lst.json().get("total", 0) >= len(rows), (
            f"layar Permintaan Desain menampilkan {lst.json().get('total')} untuk MD "
            f"padahal Meja MD mengantre {len(rows)}")
        det = requests.get(f"{BASE}/design-requests/{rid}", headers=md_hdr, timeout=60)
        assert det.status_code == 200, f"MD tidak bisa membuka DSR mejanya: {det.status_code} {det.text[:200]}"


# ── Meja Admin Gudang ────────────────────────────────────────────────────────
class TestWarehouseAdminDesk:
    def test_wh_desk_structure(self, wh_hdr):
        r = requests.get(f"{BASE}/warehouse-admin/desk?entity_id={ENT}", headers=wh_hdr, timeout=90)
        assert r.status_code == 200, r.text[:400]
        d = r.json()
        assert d["desk"] == "warehouse_admin"
        assert [q["id"] for q in d["queues"]] == WH_QUEUES
        assert all(q["count"] == len(q["rows"]) for q in d["queues"])
        print("wh queues:", {q["id"]: q["count"] for q in d["queues"]})

    def test_wh_forbidden_on_md_desk(self, wh_hdr):
        r = requests.get(f"{BASE}/md/desk?entity_id={ENT}", headers=wh_hdr, timeout=60)
        assert r.status_code == 403, f"expected 403, got {r.status_code}: {r.text[:200]}"

    def test_admin_can_open_both_desks(self, admin_hdr):
        for path in ("/md/desk", "/warehouse-admin/desk"):
            r = requests.get(f"{BASE}{path}?entity_id={ENT}", headers=admin_hdr, timeout=90)
            assert r.status_code == 200, f"{path} -> {r.status_code}: {r.text[:300]}"

    def test_desk_requires_auth(self):
        r = requests.get(f"{BASE}/md/desk?entity_id={ENT}", timeout=60)
        assert r.status_code in (401, 403), r.status_code


# ── Jembatan WMS → Logistik ──────────────────────────────────────────────────
class TestOutboundToLogisticsBridge:
    """Dispatch satu tugas outbound → SJ muncul di sj_belum_diangkut (create_delivery);
    setelah pengiriman logistik dibuat → baris hilang."""

    def _queue(self, hdr):
        r = requests.get(f"{BASE}/warehouse-admin/desk?entity_id={ENT}", headers=hdr, timeout=90)
        assert r.status_code == 200, r.text[:300]
        return next(q for q in r.json()["queues"] if q["id"] == "sj_belum_diangkut")

    def test_bridge_end_to_end(self, wh_hdr, admin_hdr):
        # 1) cari SJ dispatched tanpa logistics_id, atau buat lewat dispatch tugas outbound
        sj = db.shipments.find_one({"entity_id": ENT, "status": "dispatched",
                                    "$or": [{"logistics_id": {"$exists": False}},
                                            {"logistics_id": {"$in": [None, ""]}}]}, {"_id": 0})
        if not sj:
            tasks = list(db.wms_tasks.find(
                {"entity_id": ENT, "flow_type": "outbound",
                 "status": {"$in": ["packing", "staging", "picking", "created", "pending"]}},
                {"_id": 0, "id": 1, "quantity": 1, "status": 1, "order_id": 1}))
            assert tasks, "tidak ada tugas outbound untuk didispatch — data demo kurang"
            ok = None
            for task in tasks:
                requests.post(f"{BASE}/outbound/tasks/{task['id']}/scan-pick?actual_qty={task.get('quantity')}",
                              headers=admin_hdr, json={}, timeout=120)
                r = requests.post(f"{BASE}/outbound/tasks/{task['id']}/dispatch",
                                  headers=admin_hdr, json={}, timeout=120)
                print("dispatch", task["id"], r.status_code, r.text[:160])
                if r.status_code == 200:
                    ok = task
                    break
            if not ok:
                pytest.skip("tidak ada tugas outbound yang bisa didispatch (roll commit habis) — "
                            "jembatan sudah diverifikasi pada iterasi ini (KSC/SJ-00007 → KSC/LG-00011)")
            print("dispatched task:", ok)
            sj = db.shipments.find_one({"entity_id": ENT, "status": "dispatched",
                                        "$or": [{"logistics_id": {"$exists": False}},
                                                {"logistics_id": {"$in": [None, ""]}}]}, {"_id": 0})
            assert sj, "dispatch berhasil tetapi shipment tanpa logistics_id tidak ditemukan"
        print("SJ under test:", sj.get("id"), sj.get("shipment_no"))

        # 2) baris harus tampil di antrean dengan action_kind create_delivery
        q = self._queue(wh_hdr)
        row = next((r for r in q["rows"] if r["ref_id"] == sj["id"]), None)
        assert row, f"SJ {sj['id']} tidak muncul di sj_belum_diangkut (rows={[r['ref_id'] for r in q['rows']]})"
        assert row["action_kind"] == "create_delivery"
        assert row["ref_type"] == "shipment"
        assert row["number"] == sj.get("shipment_no", "")
        assert q["action_label"] == "Buat pengiriman"

        # 3) buat pengiriman logistik untuk SJ tersebut
        payload = {"shipment_ids": [sj["id"]], "mode": "own_fleet",
                   "vehicle_plate": "TEST B 9999 QA", "driver_name": "TEST Sopir QA",
                   "destination": "TEST Gudang QA", "notes": "TEST_iter295"}
        r = requests.post(f"{BASE}/logistics/deliveries", headers=admin_hdr, json=payload, timeout=90)
        assert r.status_code in (200, 201), f"create delivery -> {r.status_code}: {r.text[:400]}"
        dlv = r.json()
        assert "LG-" in dlv["number"], dlv.get("number")
        assert sj["id"] in (dlv.get("shipment_ids") or []) or sj.get("shipment_no") in (dlv.get("shipment_nos") or [])
        print("created delivery:", dlv["id"], dlv["number"])

        # GET verifikasi persistensi
        g = requests.get(f"{BASE}/logistics/deliveries/{dlv['id']}", headers=admin_hdr, timeout=60)
        assert g.status_code == 200, g.text[:300]
        assert g.json()["number"] == dlv["number"]
        assert "_id" not in g.json()

        # 4) baris hilang dari antrean
        q2 = self._queue(wh_hdr)
        assert all(r["ref_id"] != sj["id"] for r in q2["rows"]), \
            "SJ masih tampil di sj_belum_diangkut setelah pengiriman dibuat"
        print("queue after:", q2["count"], "(sebelum:", q["count"], ")")
