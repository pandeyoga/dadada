"""Sesi 13 retest: POST /api/wms/tasks/{id}/advance dgn expected_status."""
import os
import pathlib
import uuid
import pytest
import requests

ROOT = pathlib.Path(__file__).resolve().parents[2]
for line in (ROOT / "frontend/.env").read_text().splitlines():
    if line.startswith("REACT_APP_BACKEND_URL=") and not os.environ.get("REACT_APP_BACKEND_URL"):
        os.environ["REACT_APP_BACKEND_URL"] = line.split("=", 1)[1].strip().strip('"')
for line in (ROOT / "backend/.env").read_text().splitlines():
    k, _, v = line.partition("=")
    if k in ("MONGO_URL", "DB_NAME") and not os.environ.get(k):
        os.environ[k] = v.strip().strip('"')
BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") + "/api"


@pytest.fixture(scope="module")
def admin():
    s = requests.Session()
    r = s.post(f"{BASE}/auth/login", json={"email": "admin@kainnusantara.id", "password": "demo12345"})
    assert r.status_code == 200, r.text
    s.headers["X-Entity-Id"] = "ent_ksc"
    return s


@pytest.fixture()
def synthetic_task():
    from pymongo import MongoClient
    db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    base = db.wms_tasks.find_one({"flow_type": "inbound"}, {"_id": 0})
    tid = "wms_test_" + uuid.uuid4().hex[:6]
    t = {**base, "id": tid, "status": "created",
         "stages": ["created", "receiving", "qc_check", "put_away", "completed"],
         "entity_id": "ent_ksc", "refs": []}
    db.wms_tasks.insert_one(dict(t))
    yield tid, db
    db.wms_tasks.delete_one({"id": tid})


def test_advance_expected_status_ok_then_409(admin, synthetic_task):
    tid, db = synthetic_task
    r1 = admin.post(f"{BASE}/wms/tasks/{tid}/advance", params={"expected_status": "created"})
    assert r1.status_code == 200, r1.text
    assert r1.json()["status"] == "receiving"
    # second call with STALE expected_status → 409 STATE_CHANGED
    r2 = admin.post(f"{BASE}/wms/tasks/{tid}/advance", params={"expected_status": "created"})
    assert r2.status_code == 409
    body = r2.json()
    assert "STATE_CHANGED" in str(body)
    # DB status stays receiving (no double-jump)
    doc = db.wms_tasks.find_one({"id": tid}, {"_id": 0, "status": 1})
    assert doc["status"] == "receiving"


def test_advance_without_expected_status_still_works(admin, synthetic_task):
    tid, _ = synthetic_task
    r = admin.post(f"{BASE}/wms/tasks/{tid}/advance")
    assert r.status_code == 200
    assert r.json()["status"] == "receiving"
