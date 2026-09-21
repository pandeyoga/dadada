"""Tests for uniform revision-count indicators across MD/R&D/Meja MD (iter 24)."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://sample-tracker-25.preview.emergentagent.com").rstrip("/")
ENTITY = "ent_ksc"


@pytest.fixture(scope="module")
def token():
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "admin@kainnusantara.id", "password": "demo12345"},
        timeout=15,
    )
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def headers(token):
    return {"Authorization": f"Bearer {token}", "X-Entity-Id": ENTITY, "Content-Type": "application/json"}


# ---------- Design Requests ----------
def test_design_requests_expose_revision_count(headers):
    r = requests.get(f"{BASE_URL}/api/design-requests", params={"entity_id": ENTITY}, headers=headers, timeout=20)
    assert r.status_code == 200, r.text
    data = r.json()
    items = data.get("items") if isinstance(data, dict) else data
    assert isinstance(items, list) and items, "expected non-empty design-requests items"
    # Every item must expose revision_count as int (>=0)
    for it in items:
        assert "revision_count" in it, f"missing revision_count in {it.get('id')}"
        assert isinstance(it["revision_count"], int), f"revision_count not int: {it['revision_count']!r}"
        assert it["revision_count"] >= 0
    by_id = {it["id"]: it for it in items}
    # KSC/DSR-00004 (dsr_a623af63e8e1) must be revision_count>=1
    assert "dsr_a623af63e8e1" in by_id, "seed dsr_a623af63e8e1 missing"
    assert by_id["dsr_a623af63e8e1"]["revision_count"] >= 1


def test_design_request_detail_has_history(headers):
    r = requests.get(f"{BASE_URL}/api/design-requests/dsr_a623af63e8e1", headers=headers, timeout=20)
    assert r.status_code == 200, r.text
    doc = r.json()
    assert isinstance(doc.get("history"), list) and doc["history"]
    delivered = [h for h in doc["history"] if h.get("event") == "delivered"]
    assert delivered, "expected at least one delivered event for revised doc"


# ---------- R&D Samples ----------
def test_rnd_samples_list_ok(headers):
    # Try a few endpoint variants
    tried = []
    for path in ("/api/rnd/samples", "/api/samples", "/api/rnd-samples"):
        r = requests.get(f"{BASE_URL}{path}", params={"entity_id": ENTITY}, headers=headers, timeout=20)
        tried.append((path, r.status_code))
        if r.status_code == 200:
            data = r.json()
            items = data.get("items") if isinstance(data, dict) else data
            assert isinstance(items, list)
            return
    pytest.fail(f"no rnd samples endpoint responded 200: {tried}")


# ---------- Meja MD ----------
def test_md_desk_revision_count_only_for_desain_and_sample(headers):
    r = requests.get(f"{BASE_URL}/api/md/desk", params={"entity_id": ENTITY}, headers=headers, timeout=20)
    assert r.status_code == 200, r.text
    data = r.json()
    queues = data.get("queues", data)
    if isinstance(queues, list):
        q_by_id = {q.get("id"): q for q in queues}
    else:
        q_by_id = queues
    def rows(name):
        q = q_by_id.get(name) or {}
        return q.get("rows") or q.get("items") or []

    for qname in ("desain", "sample"):
        rr = rows(qname)
        assert isinstance(rr, list), f"queue {qname} not list"
        # allow empty but if present, must have revision_count int
        for row in rr:
            assert "revision_count" in row, f"queue {qname} row missing revision_count: {row}"
            assert isinstance(row["revision_count"], int)

    for qname in ("pr", "acuan"):
        rr = rows(qname)
        for row in rr:
            assert "revision_count" not in row, f"queue {qname} row must NOT have revision_count: {row}"
