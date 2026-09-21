"""ITERATION 267 — 3 fitur baru di atas R0-R7:
(1) NOTIFIKASI ALARM gate MERAH → db.notifications rfid_gate_alarm critical/warehouse
(2) DASHBOARD KESEHATAN GUDANG — GET /api/wms/health-dashboard
(3) RETUR MULTI-LEG — POST /api/sales-returns/{id}/relocate + jejak barang
"""
import os
from datetime import datetime, timedelta, timezone

import pytest
import requests
from dotenv import dotenv_values
from pymongo import MongoClient

fe = dotenv_values("/app/frontend/.env")
be = dotenv_values("/app/backend/.env")
BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL")
            or fe.get("REACT_APP_BACKEND_URL")).rstrip("/")
mdb = MongoClient(be["MONGO_URL"])[be["DB_NAME"]]

ADMIN = ("admin@kainnusantara.id", "demo12345")
WAREHOUSE = ("warehouse@kainnusantara.id", "demo12345")
GATE_DEVICE_KEY = "dk_5a0e33d207f8076061a34655ff8ef78a"
GATE_DEVICE_ID = "rdev_b1bc75a4db04"          # Gate Keluar Gudang Bandung Kopo
RETUR_WH = "wh_6baed091f26e"                  # Gedung Retur


def _login(email, password):
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, r.text[:300]
    return r.json()["access_token"] if "access_token" in r.json() else r.json()["token"]


@pytest.fixture(scope="module")
def admin_h():
    t = _login(*ADMIN)
    return {"Authorization": f"Bearer {t}", "X-Entity-Id": "ent_ksc"}


@pytest.fixture(scope="module")
def wh_h():
    t = _login(*WAREHOUSE)
    return {"Authorization": f"Bearer {t}", "X-Entity-Id": "ent_ksc"}


# ─────────── (2) DASHBOARD KESEHATAN GUDANG ───────────
class TestHealthDashboard:
    def test_shape_and_totals(self, admin_h):
        h = dict(admin_h, **{"X-Entity-Id": "all"})
        r = requests.get(f"{BASE_URL}/api/wms/health-dashboard", headers=h, timeout=60)
        assert r.status_code == 200, r.text[:400]
        d = r.json()
        assert set(d.keys()) >= {"totals", "warehouses"}
        for k in ("open_incidents", "red_reads_today", "putaway_ready", "pa_open",
                  "gate_exceptions", "untagged", "devices_stale"):
            assert k in d["totals"], f"missing total {k}"
            assert isinstance(d["totals"][k], int)
        assert len(d["warehouses"]) >= 5
        row = d["warehouses"][0]
        for k in ("warehouse_id", "warehouse_name", "open_incidents", "gate_exceptions",
                  "putaway_ready", "pa_open", "untagged", "last_cc",
                  "devices_total", "devices_stale"):
            assert k in row, f"missing row key {k}"
        # sum(rows) == totals
        for k in ("open_incidents", "red_reads_today", "putaway_ready", "pa_open",
                  "gate_exceptions", "untagged", "devices_stale"):
            assert sum(w[k] for w in d["warehouses"]) == d["totals"][k], k
        # priority ordering
        score = [-(w["open_incidents"] * 100 + w["gate_exceptions"] * 10
                   + w["putaway_ready"]) for w in d["warehouses"]]
        assert score == sorted(score), "warehouses not sorted by priority"

    def test_bandung_last_cc(self, admin_h):
        h = dict(admin_h, **{"X-Entity-Id": "all"})
        d = requests.get(f"{BASE_URL}/api/wms/health-dashboard", headers=h,
                         timeout=60).json()
        bdg = next(w for w in d["warehouses"] if w["warehouse_id"] == "wh_bandung")
        assert bdg["last_cc"], "Bandung Kopo tanpa last_cc"
        assert str(bdg["last_cc"]["cc_number"]).startswith("CC")
        assert bdg["last_cc"]["accuracy_pct"] == 92.3
        assert bdg["last_cc"]["at"]

    def test_open_incidents_consistent_with_source(self, admin_h):
        h = dict(admin_h, **{"X-Entity-Id": "all"})
        d = requests.get(f"{BASE_URL}/api/wms/health-dashboard", headers=h,
                         timeout=60).json()
        inc = requests.get(f"{BASE_URL}/api/rfid/incidents?status=open", headers=h,
                           timeout=60).json()
        items = inc.get("incidents") if isinstance(inc, dict) else inc
        known = {w["warehouse_id"] for w in d["warehouses"]}
        expected = sum(1 for i in items if i.get("warehouse_id") in known)
        assert d["totals"]["open_incidents"] == expected

    def test_devices_total_matches_db(self, admin_h):
        h = dict(admin_h, **{"X-Entity-Id": "all"})
        d = requests.get(f"{BASE_URL}/api/wms/health-dashboard", headers=h,
                         timeout=60).json()
        assert sum(w["devices_total"] for w in d["warehouses"]) == \
            mdb.rfid_devices.count_documents({})

    def test_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/wms/health-dashboard", timeout=30)
        assert r.status_code in (401, 403), r.status_code


# ─────────── (1) NOTIFIKASI ALARM GATE MERAH ───────────
def _fresh_epc():
    """EPC roll AVAILABLE ber-tag aktif di Bandung tanpa insiden open ≤10 menit."""
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
    busy = {i["epc"] for i in mdb.rfid_incidents.find(
        {"status": "open", "device_id": GATE_DEVICE_ID,
         "created_at": {"$gte": cutoff}}, {"epc": 1})}
    for t in mdb.rfid_tags.find({"status": "active"}, {"epc": 1, "roll_id": 1}):
        if t["epc"] in busy:
            continue
        roll = mdb.inventory_rolls.find_one(
            {"id": t["roll_id"], "status": "available"},
            {"roll_no": 1, "warehouse_id": 1})
        if roll:
            return t["epc"]
    return None


class TestGateAlarmNotification:
    def test_red_read_creates_critical_notification(self):
        epc = _fresh_epc()
        assert epc, "tak ada EPC roll available untuk uji alarm"
        before = mdb.notifications.count_documents({"type": "rfid_gate_alarm"})
        r = requests.post(f"{BASE_URL}/api/rfid/ingest", json={"epcs": [epc]},
                          headers={"X-Device-Key": GATE_DEVICE_KEY}, timeout=60)
        assert r.status_code == 200, r.text[:400]
        body = r.json()
        assert body["red"] >= 1, body
        inc = mdb.rfid_incidents.find_one({"epc": epc, "device_id": GATE_DEVICE_ID,
                                           "status": "open"})
        assert inc, "insiden open tidak dibuat"
        notif = mdb.notifications.find_one({"type": "rfid_gate_alarm",
                                           "ref": inc["id"]}, {"_id": 0})
        assert notif, "notifikasi rfid_gate_alarm tidak dibuat"
        assert notif["severity"] == "critical"
        assert notif["recipient_role"] == "warehouse"
        assert "ALARM GATE MERAH" in notif["title"]
        assert notif["read"] is False
        assert notif["entity_id"]
        assert mdb.notifications.count_documents({"type": "rfid_gate_alarm"}) == before + 1
        pytest.epc_used = epc
        pytest.inc_used = inc["id"]

    def test_repeat_read_dedupes_incident_and_notification(self):
        epc = getattr(pytest, "epc_used", None) or _fresh_epc()
        inc_before = mdb.rfid_incidents.find_one({"epc": epc,
                                                 "device_id": GATE_DEVICE_ID,
                                                 "status": "open"})
        assert inc_before
        n_before = mdb.notifications.count_documents({"type": "rfid_gate_alarm"})
        r = requests.post(f"{BASE_URL}/api/rfid/ingest", json={"epcs": [epc]},
                          headers={"X-Device-Key": GATE_DEVICE_KEY}, timeout=60)
        assert r.status_code == 200
        inc_after = mdb.rfid_incidents.find_one({"id": inc_before["id"]})
        assert inc_after["hits"] == inc_before["hits"] + 1, "hits tidak bertambah"
        assert mdb.rfid_incidents.count_documents(
            {"epc": epc, "device_id": GATE_DEVICE_ID, "status": "open"}) == 1
        assert mdb.notifications.count_documents({"type": "rfid_gate_alarm"}) == n_before, \
            "notifikasi duplikat dibuat pada pembacaan berulang"

    def test_notification_visible_to_warehouse_user(self, wh_h):
        inc = getattr(pytest, "inc_used", None)
        r = requests.get(f"{BASE_URL}/api/notifications", headers=wh_h, timeout=60)
        assert r.status_code == 200, r.text[:300]
        items = r.json() if isinstance(r.json(), list) else r.json().get("items", [])
        alarms = [n for n in items if n.get("type") == "rfid_gate_alarm"]
        assert alarms, "user gudang tidak melihat notifikasi alarm gate"
        assert alarms[0]["severity"] == "critical"
        if inc:
            assert any(n["ref"] == inc for n in alarms), \
                "notifikasi insiden baru tidak terlihat oleh role warehouse"

    def test_ingest_rejects_bad_device_key(self):
        r = requests.post(f"{BASE_URL}/api/rfid/ingest", json={"epcs": ["X"]},
                          headers={"X-Device-Key": "dk_bogus"}, timeout=30)
        assert r.status_code in (401, 403), r.status_code


# ─────────── (3) RETUR MULTI-LEG ───────────
def _return_with_quarantine(exclude_wh=RETUR_WH):
    for roll in mdb.inventory_rolls.find(
            {"acquired.via": "return", "status": "quarantine",
             "warehouse_id": {"$ne": exclude_wh}},
            {"id": 1, "acquired": 1, "warehouse_id": 1, "owner_entity_id": 1}):
        ret = mdb.sales_returns.find_one({"id": roll["acquired"]["ref_id"]},
                                         {"id": 1, "number": 1, "entity_id": 1,
                                          "owner_entity_id": 1})
        if ret and (ret.get("entity_id") or ret.get("owner_entity_id")) == "ent_ksc":
            return ret, roll
    return None, None


class TestReturnMultiLeg:
    def test_relocate_moves_rolls_and_records_leg(self, admin_h):
        ret, roll = _return_with_quarantine()
        assert ret, "tak ada retur ent_ksc dengan roll karantina di luar Gedung Retur"
        src_wh = roll["warehouse_id"]
        legs_before = len((mdb.sales_returns.find_one({"id": ret["id"]})
                           or {}).get("relocation_legs") or [])
        r = requests.post(f"{BASE_URL}/api/sales-returns/{ret['id']}/relocate",
                          json={"to_warehouse_id": RETUR_WH,
                                "note": "TEST_iter267 multileg"},
                          headers=admin_h, timeout=60)
        assert r.status_code == 200, r.text[:400]
        res = r.json()
        assert res["moved"] >= 1
        leg = res["leg"]
        assert leg["to_warehouse_id"] == RETUR_WH
        assert leg["to_warehouse_name"] == "Gedung Retur"
        assert leg["from_warehouses"] and isinstance(leg["from_warehouses"], list)
        assert leg["roll_count"] == res["moved"]
        assert leg["by"]
        doc = mdb.sales_returns.find_one({"id": ret["id"]})
        assert len(doc["relocation_legs"]) == legs_before + 1
        # roll dipindah + journey
        moved = mdb.inventory_rolls.find_one({"id": roll["id"]})
        assert moved["warehouse_id"] == RETUR_WH
        assert moved["journey"]["stage"] == "received_transit"
        # movements ber-source nomor retur
        movs = list(mdb.inventory_movements.find(
            {"roll_id": roll["id"],
             "movement_type": {"$in": ["return_relocation_in", "return_relocation_out"]}},
            {"_id": 0}))
        assert len(movs) >= 2, movs
        assert all(m["source_document"] == ret["number"] for m in movs), movs
        assert any(m["movement_type"] == "return_relocation_in"
                   and m["warehouse_id"] == RETUR_WH and m["quantity"] > 0 for m in movs)
        assert any(m["movement_type"] == "return_relocation_out"
                   and m["warehouse_id"] == src_wh and m["quantity"] < 0 for m in movs)
        pytest.reloc_ret = ret["id"]
        pytest.reloc_roll = roll["id"]
        pytest.reloc_number = ret["number"]

    def test_second_relocate_rejected(self, admin_h):
        rid = getattr(pytest, "reloc_ret", "sret_958da9c80de0")
        r = requests.post(f"{BASE_URL}/api/sales-returns/{rid}/relocate",
                          json={"to_warehouse_id": RETUR_WH}, headers=admin_h,
                          timeout=60)
        assert r.status_code == 400, f"{r.status_code} {r.text[:300]}"
        assert "karantina" in r.json().get("detail", "").lower()

    def test_relocate_unknown_warehouse(self, admin_h):
        rid = getattr(pytest, "reloc_ret", "sret_958da9c80de0")
        r = requests.post(f"{BASE_URL}/api/sales-returns/{rid}/relocate",
                          json={"to_warehouse_id": "wh_bogus"}, headers=admin_h,
                          timeout=30)
        assert r.status_code == 400, r.status_code
        assert "tujuan" in r.json().get("detail", "").lower()

    def test_relocate_unknown_return_404(self, admin_h):
        r = requests.post(f"{BASE_URL}/api/sales-returns/sret_bogus000/relocate",
                          json={"to_warehouse_id": RETUR_WH}, headers=admin_h,
                          timeout=30)
        assert r.status_code == 404, r.status_code

    def test_relocate_blocked_in_all_entities_scope(self, admin_h):
        rid = getattr(pytest, "reloc_ret", "sret_958da9c80de0")
        h = dict(admin_h, **{"X-Entity-Id": "all"})
        r = requests.post(f"{BASE_URL}/api/sales-returns/{rid}/relocate",
                          json={"to_warehouse_id": RETUR_WH}, headers=h, timeout=30)
        assert r.status_code in (400, 403, 409), f"{r.status_code} {r.text[:200]}"

    def test_relocate_wrong_entity_scope_rejected(self, admin_h):
        other = mdb.sales_returns.find_one(
            {"$or": [{"entity_id": {"$ne": "ent_ksc"}},
                     {"owner_entity_id": {"$ne": "ent_ksc"}}]},
            {"id": 1})
        if not other:
            pytest.skip("tidak ada retur entitas lain")
        r = requests.post(f"{BASE_URL}/api/sales-returns/{other['id']}/relocate",
                          json={"to_warehouse_id": RETUR_WH}, headers=admin_h,
                          timeout=30)
        assert r.status_code in (400, 403, 404), f"{r.status_code} {r.text[:200]}"
        assert r.status_code != 200

    def test_journey_timeline_shows_relocation(self, admin_h):
        roll_id = getattr(pytest, "reloc_roll", None)
        assert roll_id, "test relocate belum jalan"
        r = requests.get(
            f"{BASE_URL}/api/inventory/rolls/{roll_id}/journey-timeline",
            headers=admin_h, timeout=60)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        events = data.get("events") if isinstance(data, dict) else data
        txt = str(events)
        assert "return_relocation_in" in txt, txt[:800]
        assert getattr(pytest, "reloc_number", "SRET") in txt, txt[:800]

    def test_existing_legs_persisted_sret_958(self, admin_h):
        doc = mdb.sales_returns.find_one({"id": "sret_958da9c80de0"})
        assert doc and doc.get("relocation_legs"), "leg utama hilang"
        r = requests.get(f"{BASE_URL}/api/sales-returns/sret_958da9c80de0",
                         headers=admin_h, timeout=30)
        assert r.status_code == 200
        assert r.json().get("relocation_legs"), "API tidak mengembalikan relocation_legs"

    def test_balances_non_negative_after_relocation(self, admin_h):
        roll_id = getattr(pytest, "reloc_roll", None)
        assert roll_id
        roll = mdb.inventory_rolls.find_one({"id": roll_id})
        bal = mdb.inventory_balances.find_one(
            {"product_id": roll["product_id"], "warehouse_id": RETUR_WH,
             "owner_entity_id": roll.get("owner_entity_id")})
        assert bal, "balance gudang tujuan tidak dibangun"
        assert float(bal.get("quantity", bal.get("qty", 0))) >= 0
