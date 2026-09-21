"""Iter 25 — Revision filter (min_revision) tests for /api/design-requests.

Covers: N=0/absent (4), N=1 (only KSC/DSR-00004), N=2 (0), N=-1 (422).
"""
import os
import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
ENTITY = "ent_ksc"


@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": "admin@kainnusantara.id",
                            "password": "demo12345"},
                      timeout=30)
    assert r.status_code == 200, r.text
    tok = r.json().get("token")
    assert tok
    return tok


@pytest.fixture(scope="module")
def headers(token):
    return {"Authorization": f"Bearer {token}", "X-Entity-Id": ENTITY,
            "Content-Type": "application/json"}


def _list(headers, params):
    p = {"entity_id": ENTITY, "page": 1, "page_size": 50, **params}
    r = requests.get(f"{BASE_URL}/api/design-requests", params=p,
                     headers=headers, timeout=30)
    return r


class TestRevisionFilter:

    def test_no_min_revision_returns_all_four(self, headers):
        r = _list(headers, {})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["total"] == 4, body
        assert body["summary"]["total"] == 4
        assert len(body["items"]) == 4

    def test_min_revision_zero_returns_all(self, headers):
        r = _list(headers, {"min_revision": 0})
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 4
        assert body["summary"]["total"] == 4

    def test_min_revision_one_returns_only_ksc_dsr_00004(self, headers):
        r = _list(headers, {"min_revision": 1})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["total"] == 1, body
        assert body["summary"]["total"] == 1
        assert len(body["items"]) == 1
        item = body["items"][0]
        assert item["number"] == "KSC/DSR-00004", item
        assert item.get("revision_count", 0) >= 1

    def test_min_revision_two_returns_empty(self, headers):
        r = _list(headers, {"min_revision": 2})
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 0
        assert body["summary"]["total"] == 0
        assert body["items"] == []

    def test_min_revision_negative_returns_422(self, headers):
        r = _list(headers, {"min_revision": -1})
        assert r.status_code == 422, r.text
