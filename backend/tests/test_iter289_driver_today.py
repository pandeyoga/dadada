"""Iterasi 289 — Tugas Sopir Hari Ini (GET /drivers, GET /deliveries?mine, POST /my-route)."""
import os
import pytest
import requests
from dotenv import dotenv_values

fe = dotenv_values("/app/frontend/.env")
BASE = (os.environ.get("REACT_APP_BACKEND_URL") or fe.get("REACT_APP_BACKEND_URL")).rstrip("/")
ENT = "ent_ksc"
PW = "demo12345"


def _login(email):
    r = requests.post(f"{BASE}/api/auth/login", json={"email": email, "password": PW}, timeout=30)
    assert r.status_code == 200, f"login {email} -> {r.status_code} {r.text[:200]}"
    d = r.json()
    tok = d.get("token") or d.get("access_token")
    assert tok
    return tok, d.get("user", {})


@pytest.fixture(scope="module")
def sessions():
    out = {}
    for role in ("admin", "warehouse", "sales", "driver"):
        tok, user = _login(f"{role}@kainnusantara.id")
        s = requests.Session()
        s.headers.update({"Authorization": f"Bearer {tok}", "X-Entity-Id": ENT,
                          "Content-Type": "application/json"})
        out[role] = {"s": s, "user": user}
    return out


# ---- GET /api/logistics/drivers ----
class TestDrivers:
    def test_admin_sees_driver_joko(self, sessions):
        r = sessions["admin"]["s"].get(f"{BASE}/api/logistics/drivers", params={"entity_id": ENT}, timeout=30)
        assert r.status_code == 200, r.text[:300]
        rows = r.json()
        assert isinstance(rows, list) and rows
        ids = [x["id"] for x in rows]
        assert "user_driver_01" in ids, ids
        joko = next(x for x in rows if x["id"] == "user_driver_01")
        assert joko["name"] == "Joko Susilo"
        assert all("_id" not in x for x in rows)

    def test_warehouse_allowed(self, sessions):
        r = sessions["warehouse"]["s"].get(f"{BASE}/api/logistics/drivers", params={"entity_id": ENT}, timeout=30)
        assert r.status_code == 200, r.text[:300]
        assert "user_driver_01" in [x["id"] for x in r.json()]

    def test_sales_forbidden(self, sessions):
        r = sessions["sales"]["s"].get(f"{BASE}/api/logistics/drivers", params={"entity_id": ENT}, timeout=30)
        assert r.status_code == 403, f"{r.status_code} {r.text[:200]}"

    def test_driver_forbidden(self, sessions):
        r = sessions["driver"]["s"].get(f"{BASE}/api/logistics/drivers", params={"entity_id": ENT}, timeout=30)
        assert r.status_code == 403, f"{r.status_code} {r.text[:200]}"


# ---- GET /api/logistics/deliveries?mine=true ----
def _mine(sess):
    r = sess.get(f"{BASE}/api/logistics/deliveries", params={"entity_id": ENT, "mine": "true"}, timeout=30)
    assert r.status_code == 200, r.text[:300]
    return r.json()


class TestMine:
    def test_driver_only_own(self, sessions):
        rows = _mine(sessions["driver"]["s"])
        assert rows, "driver should have deliveries"
        assert all(d["driver_user_id"] == "user_driver_01" for d in rows), [d.get("driver_user_id") for d in rows]
        nums = [d["number"] for d in rows]
        assert any("LG-00005" in n for n in nums), nums

    def test_sorted_route_then_eta_then_created(self, sessions):
        rows = _mine(sessions["driver"]["s"])
        keys = [(d.get("route_order") or 9999, d.get("eta") or "9999-12-31", d.get("created_at") or "") for d in rows]
        assert keys == sorted(keys), keys

    def test_admin_mine_scoped_to_admin(self, sessions):
        rows = _mine(sessions["admin"]["s"])
        aid = sessions["admin"]["user"].get("id")
        assert all(d.get("driver_user_id") == aid for d in rows), rows[:2]

    def test_all_without_mine_superset(self, sessions):
        r = sessions["admin"]["s"].get(f"{BASE}/api/logistics/deliveries", params={"entity_id": ENT}, timeout=30)
        assert r.status_code == 200
        allrows = r.json()
        assert len(allrows) >= len(_mine(sessions["driver"]["s"]))


# ---- POST /api/logistics/my-route ----
class TestMyRoute:
    def test_reverse_and_persist_then_restore(self, sessions):
        s = sessions["driver"]["s"]
        rows = [d for d in _mine(s) if d["status"] in ("prepared", "loaded", "in_transit")]
        assert len(rows) >= 2, f"need >=2 active deliveries, got {len(rows)}"
        original = [d["id"] for d in rows]
        reversed_ids = list(reversed(original))
        r = s.post(f"{BASE}/api/logistics/my-route", json={"ids": reversed_ids}, timeout=30)
        assert r.status_code == 200, r.text[:300]
        assert r.json()["updated"] == len(reversed_ids)
        after = [d["id"] for d in _mine(s) if d["status"] in ("prepared", "loaded", "in_transit")]
        assert after == reversed_ids, (after, reversed_ids)
        orders = [d.get("route_order") for d in _mine(s) if d["status"] in ("prepared", "loaded", "in_transit")]
        assert orders == list(range(1, len(reversed_ids) + 1)), orders
        # restore
        r2 = s.post(f"{BASE}/api/logistics/my-route", json={"ids": original}, timeout=30)
        assert r2.status_code == 200
        assert [d["id"] for d in _mine(s) if d["status"] in ("prepared", "loaded", "in_transit")] == original

    def test_foreign_ids_ignored(self, sessions):
        s = sessions["driver"]["s"]
        own = [d["id"] for d in _mine(s)][:1]
        r = s.post(f"{BASE}/api/logistics/my-route", json={"ids": own + ["lgs_not_mine_xyz"]}, timeout=30)
        assert r.status_code == 200, r.text[:300]
        assert r.json()["updated"] == 1, r.json()

    def test_all_foreign_400(self, sessions):
        r = sessions["driver"]["s"].post(f"{BASE}/api/logistics/my-route",
                                         json={"ids": ["lgs_zzz1", "lgs_zzz2"]}, timeout=30)
        assert r.status_code == 400, f"{r.status_code} {r.text[:200]}"
        assert "milik Anda" in r.json().get("detail", "")

    def test_empty_ids_422(self, sessions):
        r = sessions["driver"]["s"].post(f"{BASE}/api/logistics/my-route", json={"ids": []}, timeout=30)
        assert r.status_code == 422, f"{r.status_code} {r.text[:200]}"

    def test_sales_forbidden(self, sessions):
        r = sessions["sales"]["s"].post(f"{BASE}/api/logistics/my-route", json={"ids": ["lgs_x"]}, timeout=30)
        assert r.status_code == 403, f"{r.status_code} {r.text[:200]}"


# ---- create/patch driver_user_id ----
class TestAssignDriver:
    created = []

    def test_create_with_driver_user_id_then_patch(self, sessions):
        s = sessions["admin"]["s"]
        r = s.get(f"{BASE}/api/logistics/shipments/unassigned", params={"entity_id": ENT}, timeout=30)
        assert r.status_code == 200, r.text[:300]
        ships = r.json()
        if not ships:
            pytest.skip("no unassigned shipment available to create delivery")
        sid = ships[0]["id"]
        payload = {"shipment_ids": [sid], "mode": "own_fleet", "vehicle_plate": "b 9999 tst",
                   "driver_name": "Joko Susilo", "driver_user_id": "user_driver_01",
                   "eta": "2026-12-31", "notes": "TEST_iter289"}
        c = s.post(f"{BASE}/api/logistics/deliveries", json=payload, timeout=30)
        assert c.status_code == 200, c.text[:400]
        doc = c.json()
        did = doc["id"]
        self.created.append(did)
        assert doc["driver_user_id"] == "user_driver_01"
        assert doc["vehicle_plate"] == "B 9999 TST"
        g = s.get(f"{BASE}/api/logistics/deliveries/{did}", timeout=30)
        assert g.status_code == 200 and g.json()["driver_user_id"] == "user_driver_01"
        # driver mine=true now includes it
        assert did in [d["id"] for d in _mine(sessions["driver"]["s"])]
        # PATCH driver_user_id -> empty (unassign)
        p = s.patch(f"{BASE}/api/logistics/deliveries/{did}", json={"driver_user_id": ""}, timeout=30)
        assert p.status_code == 200, p.text[:300]
        assert p.json()["driver_user_id"] == ""
        assert did not in [d["id"] for d in _mine(sessions["driver"]["s"])]


# ---- PATCH driver_user_id on existing active delivery (revert afterwards) ----
class TestPatchDriverOnExisting:
    def test_patch_unassign_then_reassign(self, sessions):
        s = sessions["admin"]["s"]
        rows = _mine(sessions["driver"]["s"])
        target = next(d for d in rows if d["status"] == "prepared")
        did = target["id"]
        p = s.patch(f"{BASE}/api/logistics/deliveries/{did}", json={"driver_user_id": ""}, timeout=30)
        assert p.status_code == 200, p.text[:300]
        assert p.json()["driver_user_id"] == ""
        assert did not in [d["id"] for d in _mine(sessions["driver"]["s"])]
        p2 = s.patch(f"{BASE}/api/logistics/deliveries/{did}",
                     json={"driver_user_id": "user_driver_01", "driver_name": target.get("driver_name") or "Joko Susilo"},
                     timeout=30)
        assert p2.status_code == 200, p2.text[:300]
        assert p2.json()["driver_user_id"] == "user_driver_01"
        assert did in [d["id"] for d in _mine(sessions["driver"]["s"])]

    def test_patch_delivered_rejected(self, sessions):
        s = sessions["admin"]["s"]
        r = s.get(f"{BASE}/api/logistics/deliveries", params={"entity_id": ENT, "status": "delivered"}, timeout=30)
        assert r.status_code == 200
        rows = r.json()
        if not rows:
            pytest.skip("no delivered delivery")
        p = s.patch(f"{BASE}/api/logistics/deliveries/{rows[0]['id']}",
                    json={"driver_user_id": "user_driver_01"}, timeout=30)
        assert p.status_code == 400, f"{p.status_code} {p.text[:200]}"
