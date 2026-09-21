"""Iter 52 — Verify entity_name populated in marketing post GET/POST/transition."""
import os
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")


@pytest.fixture(scope="module")
def admin_headers():
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": "admin@kainnusantara.id", "password": "demo12345"})
    assert r.status_code == 200, r.text
    token = r.json()["token"]
    return {"Authorization": f"Bearer {token}", "X-Entity-Id": "ent_ksc",
            "Content-Type": "application/json"}


def test_get_existing_post_has_entity_name(admin_headers):
    r = requests.get(f"{BASE_URL}/api/marketing/posts/mkp_75d2888905d9", headers=admin_headers)
    # If post exists, ent should be Sukacita; otherwise create fresh
    if r.status_code == 404:
        pytest.skip("seed post mkp_75d2888905d9 tidak ditemukan")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("entity_name") == "Sukacita", data


def test_create_post_returns_entity_name(admin_headers):
    body = {"title": "TEST_Retest entity iter52", "platforms": ["instagram"]}
    r = requests.post(f"{BASE_URL}/api/marketing/posts", json=body, headers=admin_headers)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("entity_id") == "ent_ksc"
    assert data.get("entity_name") == "Sukacita", data
    pid = data["id"]

    # GET must also include entity_name
    r2 = requests.get(f"{BASE_URL}/api/marketing/posts/{pid}", headers=admin_headers)
    assert r2.status_code == 200
    assert r2.json().get("entity_name") == "Sukacita"

    # Transition to draft
    r3 = requests.post(f"{BASE_URL}/api/marketing/posts/{pid}/transition",
                       json={"to": "draft"}, headers=admin_headers)
    assert r3.status_code == 200, r3.text
    assert r3.json().get("entity_name") == "Sukacita"

    # cleanup
    requests.delete(f"{BASE_URL}/api/marketing/posts/{pid}", headers=admin_headers)
