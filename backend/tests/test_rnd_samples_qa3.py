"""Backend regression for RND Samples flow (QA iteration 29)."""
import os
import requests
import pytest

def _load_env():
    with open("/app/frontend/.env") as f:
        for ln in f:
            if ln.startswith("REACT_APP_BACKEND_URL="):
                return ln.split("=", 1)[1].strip()
    return None

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or _load_env()).rstrip("/")
ENTITY = "ent_ksc"


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "admin@kainnusantara.id", "password": "demo12345"},
        timeout=30,
    )
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def headers(admin_token):
    return {
        "Authorization": f"Bearer {admin_token}",
        "X-Entity-Id": ENTITY,
        "Content-Type": "application/json",
    }


def test_list_samples_returns_items_and_stats(headers):
    r = requests.get(
        f"{BASE_URL}/api/rnd/samples", params={"entity_id": ENTITY}, headers=headers, timeout=30
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert "items" in data
    assert "stats" in data
    assert isinstance(data["items"], list)
    assert len(data["items"]) >= 1
    print("stats:", data["stats"], "count:", len(data["items"]))


def test_sample_types_meta(headers):
    r = requests.get(f"{BASE_URL}/api/rnd/sample-types", headers=headers, timeout=30)
    assert r.status_code == 200, r.text
    body = r.json()
    if isinstance(body, dict) and "items" in body:
        codes = [t["code"] for t in body["items"]]
    elif isinstance(body, list):
        codes = [t.get("code") or t.get("value") for t in body]
    else:
        codes = []
    for c in ("labdip", "handfeel", "proofing"):
        assert c in codes, f"missing sample type {c}: {codes}"


CREATED_ID = {"id": None}


def test_create_sample_labdip_handfeel(headers):
    payload = {
        "entity_id": ENTITY,
        "sample_types": ["labdip", "handfeel"],
        "title": "TEST_QA3 api",
        "brief": "x",
        "qty_requested": 3,
        "unit": "meter",
    }
    r = requests.post(
        f"{BASE_URL}/api/rnd/samples", json=payload, headers=headers, timeout=30
    )
    assert r.status_code in (200, 201), r.text
    data = r.json()
    assert data.get("number") or data.get("sample_number") or data.get("code"), data
    CREATED_ID["id"] = data.get("id") or data.get("sample_id") or data.get("_id")
    assert CREATED_ID["id"], f"no id in response: {data}"
    print("created:", CREATED_ID["id"], data.get("number") or data.get("sample_number"))


def test_patch_add_proofing_type(headers):
    sid = CREATED_ID["id"]
    assert sid
    r = requests.patch(
        f"{BASE_URL}/api/rnd/samples/{sid}",
        json={"sample_types": ["labdip", "handfeel", "proofing"], "entity_id": ENTITY},
        headers=headers,
        timeout=30,
    )
    # Either accepted or requires design → 400
    assert r.status_code in (200, 400), r.text
    print("patch proofing -> ", r.status_code, r.text[:200])


def test_cancel_cleanup(headers):
    sid = CREATED_ID["id"]
    if not sid:
        pytest.skip("no id")
    r = requests.post(
        f"{BASE_URL}/api/rnd/samples/{sid}/cancel",
        json={"reason": "TEST cleanup", "entity_id": ENTITY},
        headers=headers,
        timeout=30,
    )
    assert r.status_code in (200, 204), r.text
