"""Iter33 — Notifications relevance/audience sync with roles & permissions."""
import os
import uuid
import subprocess
import pytest
import requests
from pymongo import MongoClient

_MONGO_URL = subprocess.check_output(
    "grep ^MONGO_URL /app/backend/.env | cut -d= -f2- | tr -d '\"'", shell=True
).decode().strip()
_DB_NAME = subprocess.check_output(
    "grep ^DB_NAME /app/backend/.env | cut -d= -f2- | tr -d '\"'", shell=True
).decode().strip()
_mongo = MongoClient(_MONGO_URL)[_DB_NAME]

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/") or \
    subprocess.check_output("grep REACT_APP_BACKEND_URL /app/frontend/.env | cut -d= -f2",
                            shell=True).decode().strip()
API = f"{BASE_URL}/api"
ENTITY = "ent_ksc"


def _login(email, pw="demo12345"):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": pw})
    assert r.status_code == 200, f"login {email}: {r.status_code} {r.text}"
    return r.json()["token"]


def _hdr(token):
    return {"Authorization": f"Bearer {token}", "X-Entity-Id": ENTITY, "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def tokens():
    admin = _login("admin@kainnusantara.id")
    penag = _login("penagihan@kainnusantara.id")
    sales = _login("sales@kainnusantara.id")
    # penagihan user id
    me = requests.get(f"{API}/auth/me", headers=_hdr(penag)).json()
    return {"admin": admin, "penag": penag, "sales": sales, "penag_id": me.get("id")}


def _iso():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@pytest.fixture(scope="module")
def seed_notifs(tokens):
    """Insert 5 QA notifications directly into Mongo via a python one-liner."""
    penag_id = tokens["penag_id"]
    ids = {k: f"qa_{uuid.uuid4().hex[:10]}" for k in "ABCDE"}
    docs = [
        {"id": ids["A"], "recipient_role": "manager", "recipient_user": None, "link": "reorder"},
        {"id": ids["B"], "recipient_role": "finance", "recipient_user": None, "link": "ar-aging"},
        {"id": ids["C"], "recipient_role": "all", "recipient_user": None, "link": "fixed-assets"},
        {"id": ids["D"], "recipient_role": "all", "recipient_user": None, "link": ""},
        {"id": ids["E"], "recipient_role": "", "recipient_user": penag_id, "link": "closing"},
    ]
    common = {"type": "qa", "entity_id": ENTITY, "read": False, "created_at": _iso(),
              "title": "QA", "body": "iter33", "severity": "info"}
    full = [{**d, **common} for d in docs]
    _mongo.notifications.insert_many(full)
    yield ids
    _mongo.notifications.delete_many({"type": "qa"})


def _list_ids(token):
    r = requests.get(f"{API}/notifications", headers=_hdr(token))
    assert r.status_code == 200, r.text
    return {n["id"] for n in r.json()}


# --- 1. Audience & relevance filter ---
def test_penagihan_sees_BCDE_not_A(tokens, seed_notifs):
    ids = seed_notifs
    got = _list_ids(tokens["penag"])
    for k in "BCDE":
        assert ids[k] in got, f"penagihan should see {k}"
    assert ids["A"] not in got, "penagihan should NOT see A (manager reorder)"


def test_sales_sees_only_D(tokens, seed_notifs):
    ids = seed_notifs
    got = _list_ids(tokens["sales"])
    assert ids["D"] in got
    for k in "ABCE":
        assert ids[k] not in got, f"sales should NOT see {k}"


def test_admin_sees_ABCD_not_E(tokens, seed_notifs):
    ids = seed_notifs
    got = _list_ids(tokens["admin"])
    for k in "ABCD":
        assert ids[k] in got, f"admin should see {k}"
    assert ids["E"] not in got, "admin recipient_user is penag not admin"


def test_unread_count_consistent(tokens, seed_notifs):
    r = requests.get(f"{API}/notifications/unread-count", headers=_hdr(tokens["penag"]))
    assert r.status_code == 200
    count = r.json()["count"]
    got = _list_ids(tokens["penag"])
    # unread-count counts unread across matching scope; our seed is all unread
    # ensure our 4 seed unread all counted (count >= 4)
    seen_seed = sum(1 for k in "BCDE" if seed_notifs[k] in got)
    assert count >= seen_seed


# --- 2. Sync with role changes ---
def test_role_level_change_gates_notifications(tokens):
    # PATCH accounting=none for cr_staf_penagihan
    r = requests.patch(f"{API}/access/roles/cr_staf_penagihan",
                       json={"levels": {"accounting": "none"}}, headers=_hdr(tokens["admin"]))
    assert r.status_code == 200, r.text
    try:
        nid = f"qa_{uuid.uuid4().hex[:10]}"
        doc = {"id": nid, "type": "qa_gl", "entity_id": ENTITY, "read": False,
               "created_at": _iso(), "recipient_role": "all", "recipient_user": None,
               "link": "general-ledger", "title": "QA-GL", "body": "gl", "severity": "info"}
        _mongo.notifications.insert_one(doc)

        got = _list_ids(tokens["penag"])
        assert nid not in got, "penagihan with accounting=none should NOT see GL notif"

        r2 = requests.patch(f"{API}/access/roles/cr_staf_penagihan",
                            json={"levels": {"accounting": "view"}}, headers=_hdr(tokens["admin"]))
        assert r2.status_code == 200
        got2 = _list_ids(tokens["penag"])
        assert nid in got2, "after accounting=view, penagihan should see GL notif"
    finally:
        requests.patch(f"{API}/access/roles/cr_staf_penagihan",
                       json={"levels": {"accounting": "view"}}, headers=_hdr(tokens["admin"]))
        _mongo.notifications.delete_many({"type": "qa_gl"})


# --- 3. Turn map / turn_alerts ---
def test_turn_alerts_finance(tokens):
    r = requests.get(f"{API}/access/roles/finance", headers=_hdr(tokens["admin"]))
    assert r.status_code == 200
    ta = r.json().get("turn_alerts") or []
    titles = [t.get("title") if isinstance(t, dict) else t for t in ta]
    assert any("Terbitkan faktur" in str(t) for t in titles), f"finance turn_alerts={titles}"


def test_turn_alerts_warehouse(tokens):
    r = requests.get(f"{API}/access/roles/warehouse", headers=_hdr(tokens["admin"]))
    assert r.status_code == 200
    ta = r.json().get("turn_alerts") or []
    titles = [t.get("title") if isinstance(t, dict) else t for t in ta]
    assert any("picking" in str(t).lower() or "siapkan barang" in str(t).lower() for t in titles), titles


def test_turn_alerts_cr_staf_penagihan(tokens):
    r = requests.get(f"{API}/access/roles/cr_staf_penagihan", headers=_hdr(tokens["admin"]))
    assert r.status_code == 200
    ta = r.json().get("turn_alerts") or []
    titles = [t.get("title") if isinstance(t, dict) else t for t in ta]
    assert any("Terbitkan faktur" in str(t) for t in titles), f"cr_staf_penagihan turn_alerts={titles}"


def test_turn_roles_python():
    """turn_roles(TURN_MAP['sales_orders']['shipped']) contains finance & cr_staf_penagihan, no admin/manager."""
    script = (
        "import asyncio, json\n"
        "from services.turn_notification_service import TURN_MAP, turn_roles\n"
        "async def run():\n"
        "    a = await turn_roles(TURN_MAP['sales_orders']['shipped'])\n"
        "    b = await turn_roles(TURN_MAP['sales_orders']['waiting_approval'])\n"
        "    print(json.dumps({'shipped': list(a), 'waiting_approval': list(b)}))\n"
        "asyncio.run(run())\n"
    )
    r = subprocess.run(["python3", "-c", script], cwd="/app/backend", capture_output=True)
    assert r.returncode == 0, r.stderr.decode()
    import json as _json
    out = _json.loads(r.stdout.decode().strip().splitlines()[-1])
    shipped = out["shipped"]
    wa = out["waiting_approval"]
    assert "finance" in shipped, shipped
    assert "cr_staf_penagihan" in shipped, shipped
    assert "admin" not in shipped and "manager" not in shipped, shipped
    assert wa == ["manager"], wa


# --- 4. Regression: read endpoints ---
def test_read_endpoints_regression(tokens, seed_notifs):
    ids = seed_notifs
    # unread-count 200
    r = requests.get(f"{API}/notifications/unread-count", headers=_hdr(tokens["penag"]))
    assert r.status_code == 200
    # /read for a visible one (D) → 200
    r = requests.post(f"{API}/notifications/{ids['D']}/read", headers=_hdr(tokens["penag"]))
    assert r.status_code == 200, r.text
    # /read for a not-relevant one (A for penag) → 404
    r = requests.post(f"{API}/notifications/{ids['A']}/read", headers=_hdr(tokens["penag"]))
    assert r.status_code == 404, r.text
    # read-all 200
    r = requests.post(f"{API}/notifications/read-all", headers=_hdr(tokens["penag"]))
    assert r.status_code == 200
