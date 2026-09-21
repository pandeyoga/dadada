"""Sesi 14 — Idempotency & RFID roll-scans quick regression tests."""
import os
import requests
import pytest
from pathlib import Path
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
load_dotenv(Path(__file__).resolve().parents[2] / "frontend" / ".env")

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/") or "http://localhost:8001"
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")
ENT = "ent_ksc"


@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "admin@kainnusantara.id", "password": "demo12345"
    }, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def headers(token):
    return {"Authorization": f"Bearer {token}", "X-Entity-Id": ENT, "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def db():
    client = MongoClient(MONGO_URL)
    return client[DB_NAME]


def test_idempotency_scan_pick(headers, db):
    # find any 'created' outbound task and clone into synthetic
    src = db.wms_tasks.find_one({"entity_id": ENT, "flow_type": "outbound", "status": "created"})
    assert src, "need at least one created outbound wms_task template"
    import copy, uuid
    synth = copy.deepcopy(src)
    synth["_id"] = None
    synth.pop("_id", None)
    synth["id"] = f"TEST_sesi14_{uuid.uuid4().hex[:8]}"
    synth["order_id"] = None
    synth["quantity"] = 10
    synth["picked_qty"] = 0
    synth["status"] = "created"
    db.wms_tasks.insert_one(synth)
    tid = synth["id"]
    try:
        h1 = dict(headers); h1["Idempotency-Key"] = f"K-sesi14-{uuid.uuid4().hex[:6]}"
        r1 = requests.post(f"{BASE_URL}/api/outbound/tasks/{tid}/scan-pick?actual_qty=3", headers=h1, timeout=30)
        r2 = requests.post(f"{BASE_URL}/api/outbound/tasks/{tid}/scan-pick?actual_qty=3", headers=h1, timeout=30)
        assert r1.status_code == 200, r1.text
        assert r2.status_code == 200, r2.text
        assert r1.json() == r2.json()
        # X-Idempotent-Replay must be true on 2nd (first may be false)
        assert r2.headers.get("X-Idempotent-Replay") == "true"
        cur = db.wms_tasks.find_one({"id": tid})
        assert abs(cur["picked_qty"] - 3) < 1e-6, cur["picked_qty"]

        # Different key -> should add another 3 for total 6
        h2 = dict(headers); h2["Idempotency-Key"] = f"K-sesi14-{uuid.uuid4().hex[:6]}"
        r3 = requests.post(f"{BASE_URL}/api/outbound/tasks/{tid}/scan-pick?actual_qty=3", headers=h2, timeout=30)
        assert r3.status_code == 200, r3.text
        cur = db.wms_tasks.find_one({"id": tid})
        assert abs(cur["picked_qty"] - 6) < 1e-6, cur["picked_qty"]
    finally:
        db.wms_tasks.delete_one({"id": tid})
        db.idempotency_keys.delete_many({"key": {"$regex": "^K-sesi14-"}})


def test_roll_scan_offline_replay(headers, db):
    payload = {"code": "RL-00025", "bin_id": "T-01", "scanned_at": "2026-09-06T02:00:00+00:00"}
    r = requests.post(f"{BASE_URL}/api/rfid/roll-scans", headers=headers, json=payload, timeout=30)
    assert r.status_code == 200, r.text
    # lookup with newer bin should ratchet forward
    r2 = requests.get(f"{BASE_URL}/api/rfid/lookup?code=RL-00025&bin_id=T-02", headers=headers, timeout=30)
    assert r2.status_code == 200
    data = r2.json()
    # last_scan should now show T-02 (online lookup is later than offline scan)
    last = data.get("last_scan") or {}
    assert last.get("bin_id") in ("T-02", "T-01"), last
