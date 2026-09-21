"""Iteration 253 — session 2026-06b verification: drift suspects.ref, notifications pagination, finance home boards."""
import os, requests, pytest

BASE = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")

def _login(email, password="demo12345"):
    r = requests.post(f"{BASE}/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["token"]

@pytest.fixture(scope="module")
def admin_token():
    return _login("admin@kainnusantara.id")

@pytest.fixture(scope="module")
def finance_token():
    return _login("finance@kainnusantara.id")

@pytest.fixture(scope="module")
def sales3_token():
    return _login("sales3@kainnusantara.id")


# (b) BACKEND — drift-explain suspects[].ref required
@pytest.mark.parametrize("entity", ["ent_ksc", "ent_kanda"])
def test_drift_explain_has_ref(admin_token, entity):
    r = requests.get(
        f"{BASE}/api/gl/inventory-drift-explain",
        params={"entity_id": entity},
        headers={"Authorization": f"Bearer {admin_token}", "X-Entity-Id": entity},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    suspects = body.get("suspects", [])
    assert isinstance(suspects, list) and len(suspects) > 0, f"{entity}: no suspects"
    for s in suspects:
        # 'pembulatan' (rounding-only drift < Rp 1) legitimately has no doc to link
        if s.get("kind") == "pembulatan":
            continue
        ref = s.get("ref")
        assert isinstance(ref, dict), f"{entity}: suspect missing ref {s}"
        assert ref.get("kind") in ("roll", "journal", "account"), f"bad kind: {ref}"
        assert ref.get("id") or ref.get("number"), f"ref missing id/number: {ref}"
        assert "q" in ref, f"ref missing q: {ref}"


# (c) BACKEND — notifications pagination envelope
def test_notifications_pagination_envelope(admin_token):
    r = requests.get(
        f"{BASE}/api/notifications",
        params={"page": 1, "page_size": 2},
        headers={"Authorization": f"Bearer {admin_token}", "X-Entity-Id": "ent_ksc"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert isinstance(body, dict), "paginated should be envelope"
    for k in ("items", "total", "page", "page_size", "has_more"):
        assert k in body, f"missing {k}"
    assert len(body["items"]) <= 2
    assert body["page"] == 1
    total = body["total"]

    # page 2 differs
    if total > 2:
        r2 = requests.get(
            f"{BASE}/api/notifications",
            params={"page": 2, "page_size": 2},
            headers={"Authorization": f"Bearer {admin_token}", "X-Entity-Id": "ent_ksc"},
        )
        assert r2.status_code == 200
        ids1 = {i["id"] for i in body["items"]}
        ids2 = {i["id"] for i in r2.json()["items"]}
        assert ids1.isdisjoint(ids2), "page2 must contain different rows"

    # unread-count <= total
    rc = requests.get(
        f"{BASE}/api/notifications/unread-count",
        headers={"Authorization": f"Bearer {admin_token}", "X-Entity-Id": "ent_ksc"},
    )
    assert rc.status_code == 200
    unread = rc.json().get("count", rc.json().get("unread", 0))
    assert unread <= total, f"unread {unread} > total {total}"


def test_notifications_no_params_returns_bare_array(admin_token):
    r = requests.get(
        f"{BASE}/api/notifications",
        headers={"Authorization": f"Bearer {admin_token}", "X-Entity-Id": "ent_ksc"},
    )
    assert r.status_code == 200
    assert isinstance(r.json(), list), "no-params must be bare array (backward compat)"


def test_notifications_isolation_sales3(sales3_token):
    # sales3 (Kanda) should not see non-critical KSC notifications via pagination
    r = requests.get(
        f"{BASE}/api/notifications",
        params={"page": 1, "page_size": 100},
        headers={"Authorization": f"Bearer {sales3_token}", "X-Entity-Id": "ent_kanda"},
    )
    assert r.status_code == 200
    items = r.json().get("items", [])
    for it in items:
        if it.get("entity_id") == "ent_ksc":
            assert it.get("severity") == "critical", f"non-critical KSC leaked to sales3: {it}"


# (d) BACKEND — Finance home boards
def test_finance_home_boards(finance_token):
    r = requests.get(
        f"{BASE}/api/home/finance",
        headers={"Authorization": f"Bearer {finance_token}", "X-Entity-Id": "ent_ksc"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    wb = body.get("waiting_boards", [])
    expected_keys = ["contra_bon_approve", "contra_bon_verify", "contra_bon_dispute", "vendor_bill"]
    assert isinstance(wb, list), f"waiting_boards should be list, got {type(wb)}"
    actual_keys = [b.get("key") for b in wb]
    assert actual_keys == expected_keys, f"waiting_boards keys mismatch: {actual_keys}"
    wb_by_key = {b["key"]: b for b in wb}
    for k, v in wb_by_key.items():
        for f in ("count", "shown", "truncated", "rows"):
            assert f in v, f"{k} missing {f}"

    # Compare with approvals backlog
    rb = requests.get(
        f"{BASE}/api/approvals/backlog",
        headers={"Authorization": f"Bearer {finance_token}", "X-Entity-Id": "ent_ksc"},
    )
    assert rb.status_code == 200
    backlog = rb.json()
    if isinstance(backlog, dict):
        for k in expected_keys:
            if k in backlog:
                bcount = backlog[k] if isinstance(backlog[k], int) else backlog[k].get("count", backlog[k].get("total"))
                assert wb_by_key[k]["count"] == bcount, f"{k}: home {wb_by_key[k]['count']} != backlog {bcount}"


def test_finance_home_forbidden_other_entity(finance_token):
    r = requests.get(
        f"{BASE}/api/home/finance",
        headers={"Authorization": f"Bearer {finance_token}", "X-Entity-Id": "ent_kanda"},
    )
    assert r.status_code == 403, f"expected 403 for other entity, got {r.status_code}"
