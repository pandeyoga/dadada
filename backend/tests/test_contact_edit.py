"""Backend tests for Contact Edit feature across:
Lead, Customer, WA Contact (wa_contacts), Inbox Conversation.
RBAC: leads:update required for lead/wa/inbox; customers:update for customer.
"""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"
PWD = "Sipro#2026"


def _login(email):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": PWD}, timeout=30)
    assert r.status_code == 200, f"Login {email} failed: {r.status_code} {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def admin_h():
    return {"Authorization": f"Bearer {_login('superadmin@sipro.co.id')}"}


@pytest.fixture(scope="module")
def sales_h():
    return {"Authorization": f"Bearer {_login('sales@sipro.co.id')}"}


@pytest.fixture(scope="module")
def site_h():
    # site engineer: no leads:update
    return {"Authorization": f"Bearer {_login('site@sipro.co.id')}"}


# -------------------- lead edit --------------------
@pytest.fixture
def test_lead(admin_h):
    phone = f"0812{int(time.time()) % 100000000:08d}"
    r = requests.post(f"{API}/leads", json={
        "name": "TEST_LeadEdit", "phone": phone, "source": "manual"
    }, headers=admin_h, timeout=30)
    assert r.status_code in (200, 201), r.text
    lid = r.json().get("id") or r.json().get("data", {}).get("id")
    yield lid, phone
    try:
        requests.delete(f"{API}/leads/{lid}", headers=admin_h, timeout=10)
    except Exception:
        pass


def test_lead_update_fields(admin_h, test_lead):
    lid, phone = test_lead
    r = requests.put(f"{API}/leads/{lid}", json={
        "name": "TEST_LeadRenamed", "email": "test_lead@example.com",
        "source": "website", "notes": "edited by test"
    }, headers=admin_h, timeout=30)
    assert r.status_code == 200, r.text
    g = requests.get(f"{API}/leads/{lid}", headers=admin_h, timeout=10).json()
    data = g.get("data", g)
    assert data["name"] == "TEST_LeadRenamed"
    assert data.get("email") == "test_lead@example.com"


def test_lead_duplicate_phone(admin_h, test_lead):
    lid, phone = test_lead
    # create another lead
    phone2 = f"0813{int(time.time()) % 100000000:08d}"
    r = requests.post(f"{API}/leads", json={"name": "TEST_LeadOther", "phone": phone2, "source": "manual"},
                      headers=admin_h, timeout=30)
    assert r.status_code in (200, 201)
    other_id = r.json().get("id") or r.json().get("data", {}).get("id")
    try:
        # try to set the first lead's phone to phone2 -> expect 409
        r2 = requests.put(f"{API}/leads/{lid}", json={"phone": phone2}, headers=admin_h, timeout=30)
        assert r2.status_code in (400, 409), f"Expected conflict, got {r2.status_code}: {r2.text}"
    finally:
        requests.delete(f"{API}/leads/{other_id}", headers=admin_h, timeout=10)


def test_lead_rbac_site_cannot_update(site_h, admin_h, test_lead):
    lid, _ = test_lead
    r = requests.put(f"{API}/leads/{lid}", json={"name": "nope"}, headers=site_h, timeout=10)
    assert r.status_code == 403, f"Expected 403, got {r.status_code}"


# -------------------- customer edit --------------------
def test_customer_update(admin_h):
    phone = f"0817{int(time.time()) % 100000000:08d}"
    r = requests.post(f"{API}/customers", json={"name": "TEST_Cust", "phone": phone,
                                                "email": "cust@test.com"}, headers=admin_h, timeout=30)
    if r.status_code not in (200, 201):
        pytest.skip(f"Customer create not supported: {r.status_code} {r.text}")
    cid = r.json().get("id") or r.json().get("data", {}).get("id")
    try:
        r2 = requests.put(f"{API}/customers/{cid}",
                          json={"name": "TEST_CustRenamed", "email": "cust2@test.com"},
                          headers=admin_h, timeout=30)
        assert r2.status_code == 200, r2.text
        g = requests.get(f"{API}/customers/{cid}", headers=admin_h, timeout=10).json()
        data = g.get("data", g)
        assert data["name"] == "TEST_CustRenamed"
    finally:
        requests.delete(f"{API}/customers/{cid}", headers=admin_h, timeout=10)


# -------------------- wa_contacts edit --------------------
@pytest.fixture
def wa_contact(admin_h):
    phone = f"0856{int(time.time()) % 100000000:08d}"
    name = "Budi"
    r = requests.post(f"{API}/wa/contacts/import", json={"text": f"{name} {phone}"},
                      headers=admin_h, timeout=30)
    assert r.status_code == 200, r.text
    lr = requests.get(f"{API}/wa/contacts?q={phone[-8:]}", headers=admin_h, timeout=10).json()
    rows = lr.get("data", [])
    assert rows, f"No contact imported: {lr}"
    cid = rows[0]["id"]
    yield cid, phone
    try:
        requests.delete(f"{API}/wa/contacts/{cid}", headers=admin_h, timeout=10)
    except Exception:
        pass


def test_wa_contact_update_name_email(admin_h, wa_contact):
    cid, _ = wa_contact
    r = requests.put(f"{API}/wa/contacts/{cid}", json={
        "name": "TEST_WaRenamed", "email": "wa@test.com", "notes": "edited"
    }, headers=admin_h, timeout=30)
    assert r.status_code == 200, r.text
    assert r.json()["data"]["name"] == "TEST_WaRenamed"
    assert r.json()["data"]["email"] == "wa@test.com"


def test_wa_contact_update_invalid_phone(admin_h, wa_contact):
    cid, _ = wa_contact
    r = requests.put(f"{API}/wa/contacts/{cid}", json={"phone": "abc123"},
                     headers=admin_h, timeout=30)
    assert r.status_code == 400, f"Got {r.status_code}: {r.text}"


def test_wa_contact_update_duplicate_phone(admin_h):
    phone1 = f"0858{int(time.time()) % 100000000:08d}"
    phone2 = f"0859{(int(time.time()) + 1) % 100000000:08d}"
    r1 = requests.post(f"{API}/wa/contacts/import",
                       json={"text": f"KontakA {phone1}\nKontakB {phone2}"},
                       headers=admin_h, timeout=30)
    assert r1.status_code == 200
    rows = requests.get(f"{API}/wa/contacts?q=Kontak", headers=admin_h, timeout=10).json()["data"]
    try:
        c1 = next(r for r in rows if r.get("name") == "KontakA")
        c2 = next(r for r in rows if r.get("name") == "KontakB")
        # Try set c1.phone to c2.phone -> expect 409
        rr = requests.put(f"{API}/wa/contacts/{c1['id']}", json={"phone": c2["phone"]},
                         headers=admin_h, timeout=30)
        assert rr.status_code == 409, f"Expected 409, got {rr.status_code}: {rr.text}"
    finally:
        for r in rows:
            if r.get("name", "").startswith("Kontak"):
                requests.delete(f"{API}/wa/contacts/{r['id']}", headers=admin_h, timeout=10)


def test_wa_contact_update_rbac(site_h, admin_h, wa_contact):
    cid, _ = wa_contact
    r = requests.put(f"{API}/wa/contacts/{cid}", json={"name": "nope"},
                     headers=site_h, timeout=10)
    assert r.status_code == 403, f"Expected 403, got {r.status_code}"


# -------------------- inbox conversation contact edit --------------------
def _get_or_make_conv(admin_h):
    """Trigger a simulated inbound WA message to create a conversation."""
    phone = f"0821{int(time.time()) % 100000000:08d}"
    r = requests.post(f"{API}/wa/simulate/inbound", json={
        "phone": phone, "name": "TEST_InboxCt", "message": "halo test"
    }, headers=admin_h, timeout=30)
    assert r.status_code == 200, r.text
    # list conversations
    lr = requests.get(f"{API}/inbox?limit=20", headers=admin_h, timeout=10).json()
    for c in lr.get("data", []):
        if c.get("contact_phone", "").endswith(phone[-8:]):
            return c["id"], phone
    pytest.skip("Could not locate created conversation")


def test_inbox_contact_update(admin_h):
    conv_id, phone = _get_or_make_conv(admin_h)
    # fetch original
    orig = requests.get(f"{API}/inbox/{conv_id}", headers=admin_h, timeout=10).json()["data"]["conversation"]
    orig_name = orig.get("contact_name")
    orig_phone = orig.get("contact_phone")
    try:
        r = requests.put(f"{API}/inbox/{conv_id}/contact",
                        json={"contact_name": "TEST_InboxRenamed"},
                        headers=admin_h, timeout=30)
        assert r.status_code == 200, r.text
        assert r.json()["data"]["contact_name"] == "TEST_InboxRenamed"
        # invalid phone
        r2 = requests.put(f"{API}/inbox/{conv_id}/contact",
                         json={"contact_phone": "abc"}, headers=admin_h, timeout=10)
        assert r2.status_code == 400
    finally:
        # Restore
        requests.put(f"{API}/inbox/{conv_id}/contact",
                    json={"contact_name": orig_name, "contact_phone": orig_phone},
                    headers=admin_h, timeout=10)


def test_inbox_contact_update_rbac(site_h, admin_h):
    conv_id, _ = _get_or_make_conv(admin_h)
    r = requests.put(f"{API}/inbox/{conv_id}/contact", json={"contact_name": "nope"},
                    headers=site_h, timeout=10)
    assert r.status_code == 403, f"Expected 403, got {r.status_code}"
