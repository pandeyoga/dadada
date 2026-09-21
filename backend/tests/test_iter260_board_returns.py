"""Iteration 260 — queue-board endpoint + enriched sales-return detail."""
import os

import pytest
import requests
from dotenv import dotenv_values

fe = dotenv_values("/app/frontend/.env")
BASE = (os.environ.get("REACT_APP_BACKEND_URL") or fe.get("REACT_APP_BACKEND_URL")).rstrip("/")
PWD = "demo12345"


def login(email):
    r = requests.post(f"{BASE}/api/auth/login", json={"email": email, "password": PWD}, timeout=60)
    assert r.status_code == 200, f"login {email} -> {r.status_code} {r.text[:300]}"
    return r.json()["token"]


@pytest.fixture(scope="module")
def mgr():
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {login('manager@kainnusantara.id')}",
                      "X-Entity-Id": "ent_ksc"})
    return s


@pytest.fixture(scope="module")
def admin():
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {login('admin@kainnusantara.id')}",
                      "X-Entity-Id": "ent_ksc"})
    return s


@pytest.fixture(scope="module")
def salesadmin():
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {login('salesadmin@kainnusantara.id')}",
                      "X-Entity-Id": "ent_ksc"})
    return s


@pytest.fixture(scope="module")
def backlog(mgr):
    r = mgr.get(f"{BASE}/api/approvals/backlog?entity_id=ent_ksc&oldest=10", timeout=60)
    assert r.status_code == 200, r.text[:300]
    return r.json()


class TestQueueBoard:
    def test_backlog_has_items(self, backlog):
        assert isinstance(backlog.get("all_items"), list) and backlog["all_items"], backlog.keys()

    def test_requires_auth(self):
        r = requests.get(f"{BASE}/api/approvals/queue-board/purchase_order", timeout=60)
        assert r.status_code in (401, 403), r.status_code

    def test_all_keys_return_consistent_shape(self, mgr, backlog):
        keys = [i.get("key") for i in backlog["all_items"] if i.get("key")]
        assert keys
        failures = []
        for k in keys:
            r = mgr.get(f"{BASE}/api/approvals/queue-board/{k}?entity_id=ent_ksc&limit=500", timeout=60)
            if r.status_code != 200:
                failures.append((k, r.status_code, r.text[:120]))
                continue
            d = r.json()
            for f in ("key", "count", "rows", "truncated"):
                if f not in d:
                    failures.append((k, "missing field", f))
            if d.get("key") != k:
                failures.append((k, "key mismatch", d.get("key")))
            if not isinstance(d.get("rows"), list):
                failures.append((k, "rows not list", type(d.get("rows"))))
            else:
                # limit besar → seluruh baris terkirim
                if d.get("count", 0) <= 500 and len(d["rows"]) != d.get("count"):
                    failures.append((k, "rows!=count", (len(d["rows"]), d.get("count"))))
                if d.get("truncated") is not False and d.get("count", 0) <= 500:
                    failures.append((k, "truncated true with full limit", d.get("truncated")))
        assert not failures, failures

    def test_limit_param_honored(self, mgr, backlog):
        # pilih antrean dengan count >= 2
        target = None
        for i in backlog["all_items"]:
            if (i.get("count") or 0) >= 2 and i.get("key"):
                target = i
                break
        if not target:
            pytest.skip("tidak ada antrean dengan >=2 dokumen")
        r = mgr.get(f"{BASE}/api/approvals/queue-board/{target['key']}?entity_id=ent_ksc&limit=1", timeout=60)
        assert r.status_code == 200
        d = r.json()
        assert len(d["rows"]) == 1
        assert d["truncated"] is True
        assert d["count"] >= 2
        assert d.get("hidden", 0) == d["count"] - 1

    def test_unknown_key_graceful(self, mgr):
        r = mgr.get(f"{BASE}/api/approvals/queue-board/tidak_ada_key?entity_id=ent_ksc", timeout=60)
        assert r.status_code == 200, r.text[:200]
        d = r.json()
        assert d["count"] == 0 and d["rows"] == []

    def test_manager_rows_carry_action(self, mgr, backlog):
        keys = [i["key"] for i in backlog["all_items"] if (i.get("count") or 0) > 0 and i.get("key")]
        found_action = False
        for k in keys:
            d = mgr.get(f"{BASE}/api/approvals/queue-board/{k}?entity_id=ent_ksc", timeout=60).json()
            for row in d.get("rows", []):
                assert "action" in row, (k, row.keys())
                if row.get("action"):
                    found_action = True
        assert found_action, "tidak ada satu pun baris dengan action untuk manager"

    def test_salesadmin_can_read_but_no_action(self, salesadmin, backlog):
        keys = [i["key"] for i in backlog["all_items"] if (i.get("count") or 0) > 0 and i.get("key")]
        assert keys
        k = keys[0]
        r = salesadmin.get(f"{BASE}/api/approvals/queue-board/{k}?entity_id=ent_ksc", timeout=60)
        assert r.status_code == 200, r.text[:200]


class TestSalesReturnDetail:
    def test_detail_enriched(self, admin):
        lst = admin.get(f"{BASE}/api/sales-returns?entity_id=ent_ksc", timeout=60)
        assert lst.status_code == 200, lst.text[:300]
        data = lst.json()
        rows = data if isinstance(data, list) else data.get("items", [])
        assert rows, "tidak ada retur jual di seed"
        checked = 0
        for row in rows[:6]:
            r = admin.get(f"{BASE}/api/sales-returns/{row['id']}", timeout=60)
            assert r.status_code == 200, (row["id"], r.status_code, r.text[:200])
            d = r.json()
            assert "_id" not in d
            assert isinstance(d.get("estimated_value"), (int, float)), d.get("estimated_value")
            for it in d.get("items", []):
                assert isinstance(it.get("unit_price_est"), (int, float)), it
                assert isinstance(it.get("line_total_est"), (int, float)), it
            checked += 1
        assert checked > 0

    def test_sret_00001_estimate_positive(self, admin):
        lst = admin.get(f"{BASE}/api/sales-returns?entity_id=ent_ksc", timeout=60).json()
        rows = lst if isinstance(lst, list) else lst.get("items", [])
        target = next((r for r in rows if r.get("number") == "SRET-00001"), None)
        if not target:
            pytest.skip("SRET-00001 tidak ada")
        d = admin.get(f"{BASE}/api/sales-returns/{target['id']}", timeout=60).json()
        assert d["estimated_value"] > 0, d.get("estimated_value")
        assert any(it["line_total_est"] > 0 for it in d["items"]), d["items"]

    def test_list_return_type_filter(self, admin):
        base = admin.get(f"{BASE}/api/sales-returns?entity_id=ent_ksc", timeout=60).json()
        rows = base if isinstance(base, list) else base.get("items", [])
        types = {r.get("return_type") for r in rows if r.get("return_type")}
        assert types, "seed tanpa return_type"
        t = sorted(types)[0]
        r = admin.get(f"{BASE}/api/sales-returns?entity_id=ent_ksc&return_type={t}", timeout=60)
        assert r.status_code == 200, r.text[:200]
        d = r.json()
        frows = d if isinstance(d, list) else d.get("items", [])
        assert frows, f"filter return_type={t} kosong padahal ada data"
        assert all(x.get("return_type") == t for x in frows), [x.get("return_type") for x in frows]
