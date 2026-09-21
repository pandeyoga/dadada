"""Iteration 263 — FASE R0+R1+R2 revamp WMS/RFID.

R0: warehouse_sites CRUD + profil gudang (site_id, roles, storage_rules, gate_config)
R1: print job RFID (ZPL ^RFW,H) + sesi verifikasi expected-vs-scanned + routing
R2: Putaway Order (rules enforcement, dispatch, confirm-arrival + BTG, exception)
Regresi: inventory balances / putaway queue / rfid summary & tags
"""
import os

import pytest
import requests
from dotenv import dotenv_values

fe = dotenv_values("/app/frontend/.env")
BASE = (os.environ.get("REACT_APP_BACKEND_URL") or fe.get("REACT_APP_BACKEND_URL")).rstrip("/")
PWD = "demo12345"
ENT = "ent_ksc"


def login(email):
    r = requests.post(f"{BASE}/api/auth/login", json={"email": email, "password": PWD}, timeout=90)
    if r.status_code != 200:
        pytest.fail(f"login {email} -> {r.status_code} {r.text[:300]}")
    return r.json()["token"]


@pytest.fixture(scope="session")
def admin():
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {login('admin@kainnusantara.id')}",
                      "X-Entity-Id": ENT})
    return s


@pytest.fixture(scope="session")
def warehouses(admin):
    r = admin.get(f"{BASE}/api/warehouses?scope=all", timeout=90)
    assert r.status_code == 200, r.text[:300]
    rows = r.json()
    rows = rows.get("warehouses", rows) if isinstance(rows, dict) else rows
    return {w["code"]: w for w in rows}


# ─────────────────────────── R0: SITES ───────────────────────────
class TestR0Sites:
    def test_list_sites_seeded(self, admin):
        r = admin.get(f"{BASE}/api/warehouse-sites", timeout=90)
        assert r.status_code == 200, r.text[:300]
        sites = r.json()["sites"]
        names = {s["name"] for s in sites}
        for expected in ("Rancamalang", "Soreang", "Jakarta"):
            assert expected in names, f"site {expected} missing; got {names}"
        rcm = next(s for s in sites if s["name"] == "Rancamalang")
        assert "warehouse_count" in rcm and isinstance(rcm["warehouse_count"], int)
        assert rcm["warehouse_count"] >= 5, f"Rancamalang gedung count={rcm['warehouse_count']}"
        assert all("_id" not in s for s in sites)

    def test_create_and_delete_empty_site(self, admin):
        r = admin.post(f"{BASE}/api/warehouse-sites",
                       json={"name": "TEST_Site_QA263", "city": "QA City"}, timeout=90)
        assert r.status_code == 200, r.text[:300]
        site = r.json()
        assert site["name"] == "TEST_Site_QA263" and site["city"] == "QA City"
        sid = site["id"]

        # persisted?
        listed = admin.get(f"{BASE}/api/warehouse-sites", timeout=90).json()["sites"]
        got = next((s for s in listed if s["id"] == sid), None)
        assert got is not None and got["warehouse_count"] == 0

        # duplicate name → 409
        dup = admin.post(f"{BASE}/api/warehouse-sites",
                         json={"name": "TEST_Site_QA263"}, timeout=90)
        assert dup.status_code == 409, f"dup site -> {dup.status_code}"

        # empty name → 400
        bad = admin.post(f"{BASE}/api/warehouse-sites", json={"name": "  "}, timeout=90)
        assert bad.status_code == 400, f"empty name -> {bad.status_code}"

        d = admin.delete(f"{BASE}/api/warehouse-sites/{sid}", timeout=90)
        assert d.status_code == 200, d.text[:300]
        listed2 = admin.get(f"{BASE}/api/warehouse-sites", timeout=90).json()["sites"]
        assert all(s["id"] != sid for s in listed2)

    def test_delete_used_site_rejected(self, admin):
        sites = admin.get(f"{BASE}/api/warehouse-sites", timeout=90).json()["sites"]
        used = next(s for s in sites if s["warehouse_count"] > 0)
        d = admin.delete(f"{BASE}/api/warehouse-sites/{used['id']}", timeout=90)
        assert d.status_code == 409, f"delete used site -> {d.status_code} {d.text[:200]}"
        assert "dipakai" in d.text.lower()

    def test_delete_unknown_site_404(self, admin):
        d = admin.delete(f"{BASE}/api/warehouse-sites/site_does_not_exist", timeout=90)
        assert d.status_code == 404, f"-> {d.status_code}"


# ─────────────────────── R0: PROFIL GUDANG ───────────────────────
class TestR0WarehouseProfile:
    def test_patch_profile_persists(self, admin, warehouses):
        wh = warehouses.get("SRG-01")
        assert wh, f"SRG-01 not found; codes={list(warehouses)[:20]}"
        sites = admin.get(f"{BASE}/api/warehouse-sites", timeout=90).json()["sites"]
        site = next(s for s in sites if s["name"] == "Soreang")
        payload = {"data": {
            "roles": ["storage"],
            "storage_rules": {"mode": "category", "categories": ["Batik"], "grades": []},
            "gate_config": {"physical_gate": True},
            "site_id": site["id"],
        }}
        r = admin.patch(f"{BASE}/api/warehouses/{wh['id']}", json=payload, timeout=90)
        assert r.status_code == 200, r.text[:300]

        rows = admin.get(f"{BASE}/api/warehouses?scope=all", timeout=90).json()
        rows = rows.get("warehouses", rows) if isinstance(rows, dict) else rows
        got = next(w for w in rows if w["id"] == wh["id"])
        assert got["roles"] == ["storage"]
        assert got["storage_rules"]["mode"] == "category"
        assert got["storage_rules"]["categories"] == ["Batik"]
        assert got["gate_config"]["physical_gate"] is True
        assert got["site_id"] == site["id"]

        # restore permissive rules so PA tests aren't affected
        admin.patch(f"{BASE}/api/warehouses/{wh['id']}", json={"data": {
            "storage_rules": {"mode": "none", "categories": [], "grades": []}}}, timeout=90)

    def test_invalid_role_rejected(self, admin, warehouses):
        wh = warehouses["SRG-01"]
        r = admin.patch(f"{BASE}/api/warehouses/{wh['id']}",
                        json={"data": {"roles": ["bukan_peran"]}}, timeout=90)
        assert r.status_code == 400, f"-> {r.status_code} {r.text[:200]}"

    def test_invalid_rule_mode_rejected(self, admin, warehouses):
        wh = warehouses["SRG-01"]
        r = admin.patch(f"{BASE}/api/warehouses/{wh['id']}", json={"data": {
            "storage_rules": {"mode": "warna"}}}, timeout=90)
        assert r.status_code == 400, f"-> {r.status_code} {r.text[:200]}"

    def test_invalid_site_rejected(self, admin, warehouses):
        wh = warehouses["SRG-01"]
        r = admin.patch(f"{BASE}/api/warehouses/{wh['id']}",
                        json={"data": {"site_id": "site_nope"}}, timeout=90)
        assert r.status_code == 400, f"-> {r.status_code} {r.text[:200]}"


# ────────────────── R1: PRINT JOB + VERIFIKASI ──────────────────
STATE = {}


class TestR1PrintVerify:
    def test_pick_untagged_rolls(self, admin):
        def fetch():
            r = admin.get(f"{BASE}/api/rfid/untagged-rolls", timeout=90)
            assert r.status_code == 200, r.text[:300]
            out = {}
            for roll in r.json()["rolls"]:
                out.setdefault(roll.get("warehouse_id"), []).append(roll)
            return out

        by_wh = fetch()
        best = max(by_wh.values(), key=len, default=[])
        if len(best) < 2:
            # SEED: retire 2 tag aktif di satu gudang → roll-nya jadi untagged lagi
            tags = admin.get(f"{BASE}/api/rfid/tags", params={"status": "active"},
                             timeout=90).json()["tags"]
            per_wh = {}
            for t in tags:
                if t.get("roll_id"):
                    per_wh.setdefault(t.get("warehouse_id"), []).append(t)
            group = max(per_wh.values(), key=len, default=[])
            for t in group[:2]:
                admin.delete(f"{BASE}/api/rfid/tags/{t['id']}", timeout=90)
            by_wh = fetch()
        if not by_wh:
            pytest.skip("tidak ada roll untagged & gagal seed — R1 print flow dilewati")
        wid, group = max(by_wh.items(), key=lambda kv: len(kv[1]))
        STATE["wh_from"] = wid
        STATE["rolls"] = group[:2]
        assert all(x.get("id") for x in STATE["rolls"])
        print(f"\n[info] print job dari {wid} dengan {len(STATE['rolls'])} roll")

    def test_create_print_job(self, admin):
        if "rolls" not in STATE:
            pytest.skip("tidak ada roll untagged")
        roll_ids = [r["id"] for r in STATE["rolls"]]
        r = admin.post(f"{BASE}/api/rfid/print-jobs", json={"roll_ids": roll_ids}, timeout=120)
        assert r.status_code == 200, r.text[:400]
        job = r.json()
        assert job["status"] == "queued"
        assert job["job_number"].startswith("PJ")
        n = len(STATE["rolls"])
        assert job["item_count"] == n and len(job["items"]) == n
        assert all(i["epc"] for i in job["items"]), "EPC kosong pada item"
        assert job["warehouse_id"] == STATE["wh_from"]
        STATE["job"] = job
        STATE["epcs"] = [i["epc"] for i in job["items"]]

        # GET single job persisted
        g = admin.get(f"{BASE}/api/rfid/print-jobs/{job['id']}", timeout=90)
        assert g.status_code == 200 and g.json()["job_number"] == job["job_number"]
        # appears in list
        lst = admin.get(f"{BASE}/api/rfid/print-jobs", timeout=90).json()
        jobs = lst.get("jobs", lst) if isinstance(lst, dict) else lst
        assert any(j["id"] == job["id"] for j in jobs)

    def test_create_print_job_empty_rejected(self, admin):
        r = admin.post(f"{BASE}/api/rfid/print-jobs", json={"roll_ids": []}, timeout=90)
        assert r.status_code == 400, f"-> {r.status_code}"

    def test_zpl_has_rfid_write(self, admin):
        if "job" not in STATE:
            pytest.skip("tidak ada print job")
        r = admin.get(f"{BASE}/api/rfid/print-jobs/{STATE['job']['id']}/zpl", timeout=90)
        assert r.status_code == 200, r.text[:300]
        body = r.text if "^XA" in r.text else str(r.json())
        assert "^RFW,H" in body, f"ZPL tanpa ^RFW,H: {body[:200]}"
        assert body.count("^XA") >= len(STATE["rolls"]), "ZPL harus 1 label per item"

    def test_mark_printed(self, admin):
        if "job" not in STATE:
            pytest.skip("tidak ada print job")
        r = admin.post(f"{BASE}/api/rfid/print-jobs/{STATE['job']['id']}/mark-printed", timeout=90)
        assert r.status_code == 200, r.text[:300]
        assert r.json()["status"] == "printed"
        again = admin.post(f"{BASE}/api/rfid/print-jobs/{STATE['job']['id']}/mark-printed", timeout=90)
        assert again.status_code == 400, f"double mark-printed -> {again.status_code}"

    def test_verify_partial_then_complete(self, admin):
        if "job" not in STATE:
            pytest.skip("tidak ada print job")
        n = len(STATE["epcs"])
        r = admin.post(f"{BASE}/api/rfid/print-jobs/{STATE['job']['id']}/verify/start", timeout=90)
        assert r.status_code == 200, r.text[:300]
        sess = r.json()
        assert sess["status"] == "open" and len(sess["expected"]) == n
        sid = sess["id"]
        STATE["sess"] = sid

        # partial scan (hanya bila job punya >1 item)
        if n > 1:
            p = admin.post(f"{BASE}/api/rfid/verify-sessions/{sid}/scan",
                           json={"epcs": [STATE["epcs"][0]]}, timeout=90)
            assert p.status_code == 200, p.text[:300]
            prog = p.json()
            assert prog["matched_count"] == 1, prog
            assert prog["expected_count"] == n
            assert prog["missing"] == [STATE["epcs"][1].upper()], prog["missing"]
            assert prog["extra"] == []

        # unknown EPC → extra
        e = admin.post(f"{BASE}/api/rfid/verify-sessions/{sid}/scan",
                       json={"epcs": ["DEADBEEFDEADBEEFDEADBEEF"]}, timeout=90).json()
        assert e["extra"] == ["DEADBEEFDEADBEEFDEADBEEF"], e["extra"]

        # scan semua EPC yang diharapkan
        f = admin.post(f"{BASE}/api/rfid/verify-sessions/{sid}/scan",
                       json={"epcs": STATE["epcs"]}, timeout=90).json()
        assert f["missing"] == [] and f["matched_count"] == n

        c = admin.post(f"{BASE}/api/rfid/verify-sessions/{sid}/complete", timeout=90)
        assert c.status_code == 200, c.text[:300]
        res = c.json()
        assert res["status"] == "completed"
        assert res["result"] == "with_issues", "extra EPC harus menandai with_issues"

        job = admin.get(f"{BASE}/api/rfid/print-jobs/{STATE['job']['id']}", timeout=90).json()
        assert job["status"] in ("verified", "verified_with_issues"), job["status"]
        assert job["verified_at"]

        # double complete rejected
        again = admin.post(f"{BASE}/api/rfid/verify-sessions/{sid}/complete", timeout=90)
        assert again.status_code == 400, f"-> {again.status_code}"

    def test_rolls_are_ready_for_putaway(self, admin):
        if "job" not in STATE:
            pytest.skip("tidak ada print job")
        r = admin.get(f"{BASE}/api/putaway-orders/suggest",
                      params={"from_warehouse_id": STATE["wh_from"]}, timeout=90)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        ready_ids = {roll["id"] for g in data["groups"] for roll in g["rolls"]}
        for roll in STATE["rolls"]:
            assert roll["id"] in ready_ids, f"roll {roll['id']} tidak muncul di saran putaway"

    def test_set_routing_cross_dock_then_store(self, admin):
        if "rolls" not in STATE:
            pytest.skip("tidak ada roll uji")
        rid = STATE["rolls"][0]["id"]
        r = admin.post(f"{BASE}/api/rfid/rolls/set-routing",
                       json={"roll_ids": [rid], "routing": "cross_dock"}, timeout=90)
        assert r.status_code == 200, r.text[:300]
        assert r.json()["updated"] == 1

        sug = admin.get(f"{BASE}/api/putaway-orders/suggest",
                        params={"from_warehouse_id": STATE["wh_from"]}, timeout=90).json()
        ids = {roll["id"] for g in sug["groups"] for roll in g["rolls"]}
        assert rid not in ids, "roll cross_dock masih muncul di saran putaway"

        back = admin.post(f"{BASE}/api/rfid/rolls/set-routing",
                          json={"roll_ids": [rid], "routing": "store"}, timeout=90)
        assert back.status_code == 200
        sug2 = admin.get(f"{BASE}/api/putaway-orders/suggest",
                         params={"from_warehouse_id": STATE["wh_from"]}, timeout=90).json()
        ids2 = {roll["id"] for g in sug2["groups"] for roll in g["rolls"]}
        assert rid in ids2, "roll tidak kembali setelah routing store"

    def test_invalid_routing_rejected(self, admin):
        if "rolls" not in STATE:
            pytest.skip("tidak ada roll uji")
        r = admin.post(f"{BASE}/api/rfid/rolls/set-routing",
                       json={"roll_ids": [STATE["rolls"][0]["id"]], "routing": "buang"}, timeout=90)
        assert r.status_code == 400, f"-> {r.status_code}"


# ─────────────────────── R2: PUTAWAY ORDER ───────────────────────
class TestR2PutawayOrder:
    def test_suggest_excludes_retur_for_grade_a(self, admin, warehouses):
        retur = warehouses.get("RCM-RETUR")
        assert retur, "RCM-RETUR belum ada"
        # cari gudang asal yang punya roll siap putaway
        candidates = [STATE.get("wh_from")] + [w["id"] for w in warehouses.values()]
        sug = None
        for whid in [c for c in candidates if c]:
            d = admin.get(f"{BASE}/api/putaway-orders/suggest",
                          params={"from_warehouse_id": whid}, timeout=90)
            if d.status_code == 200 and d.json()["ready_count"] > 0:
                sug, STATE["wh_from"] = d.json(), whid
                break
        if not sug:
            pytest.skip("tidak ada roll siap putaway di gudang mana pun")
        assert sug["groups"], "ready_count > 0 tapi groups kosong"
        ready = []
        for g in sug["groups"]:
            cand_ids = {c["warehouse_id"] for c in g["candidates"]}
            # iter264 — saran PA kini GRADE-AWARE: Gedung Retur hanya dilarang untuk grup
            # grade A (grup grade B/C/BS memang BOLEH mendapat Gedung Retur).
            if (g.get("grade") or "A").upper() == "A":
                assert retur["id"] not in cand_ids, "Gedung Retur muncul sebagai kandidat grade A"
            assert cand_ids, "grup tanpa kandidat tujuan"
            ready.extend(g["rolls"])
        STATE["ready"] = ready
        grade_a = [r for r in ready if (r.get("grade") or "A").upper() == "A"]
        STATE["grade_a_roll"] = grade_a[0] if grade_a else None
        print(f"\n[info] PA dari {STATE['wh_from']} — {len(ready)} roll siap")

    def test_create_pa_to_retur_rejected(self, admin, warehouses):
        roll = STATE.get("grade_a_roll")
        if not roll:
            pytest.skip("tidak ada roll grade A siap putaway")
        r = admin.post(f"{BASE}/api/putaway-orders", json={
            "from_warehouse_id": STATE["wh_from"],
            "to_warehouse_id": warehouses["RCM-RETUR"]["id"],
            "roll_ids": [roll["id"]]}, timeout=90)
        assert r.status_code == 400, f"-> {r.status_code} {r.text[:200]}"
        assert "grade" in r.text.lower(), r.text[:200]

    def test_create_pa_same_warehouse_rejected(self, admin):
        if not STATE.get("ready"):
            pytest.skip("tidak ada roll siap putaway")
        r = admin.post(f"{BASE}/api/putaway-orders", json={
            "from_warehouse_id": STATE["wh_from"], "to_warehouse_id": STATE["wh_from"],
            "roll_ids": [STATE["ready"][0]["id"]]}, timeout=90)
        assert r.status_code == 400, f"-> {r.status_code}"

    def test_full_pa_flow(self, admin, warehouses):
        if not STATE.get("ready"):
            pytest.skip("tidak ada roll siap putaway")
        dest = warehouses["RCM-WOVEN"]
        # Data bisa lapuk antar-run: roll uji mungkin sudah berada di RCM-WOVEN.
        if STATE.get("wh_from") == dest["id"]:
            dest = warehouses["RCM-KNITTING"]
        rolls = STATE["ready"][:2]
        n = len(rolls)
        r = admin.post(f"{BASE}/api/putaway-orders", json={
            "from_warehouse_id": STATE["wh_from"], "to_warehouse_id": dest["id"],
            "roll_ids": [x["id"] for x in rolls]}, timeout=120)
        assert r.status_code == 200, r.text[:400]
        pa = r.json()
        assert pa["pa_number"].startswith("PA")
        assert pa["status"] == "open" and pa["item_count"] == n
        assert all(i["epc"] for i in pa["items"]), "item PA tanpa EPC"
        assert pa["to_warehouse_id"] == dest["id"]
        STATE["pa"] = pa

        # dispatch
        d = admin.post(f"{BASE}/api/putaway-orders/{pa['id']}/dispatch", timeout=90)
        assert d.status_code == 200, d.text[:300]
        assert d.json()["status"] == "in_transit" and d.json()["dispatched_at"]
        again = admin.post(f"{BASE}/api/putaway-orders/{pa['id']}/dispatch", timeout=90)
        assert again.status_code == 400, f"double dispatch -> {again.status_code}"

        # confirm arrival: hanya EPC item pertama yang "terbaca"
        epc_ok = pa["items"][0]["epc"]
        roll_ok = pa["items"][0]["roll_id"]
        roll_exc = pa["items"][1]["roll_id"] if n > 1 else None
        c = admin.post(f"{BASE}/api/putaway-orders/{pa['id']}/confirm-arrival",
                       json={"scanned_epcs": [epc_ok]}, timeout=120)
        assert c.status_code == 200, c.text[:400]
        conf = c.json()
        assert conf["btg_number"] and conf["btg_number"].startswith("BTG"), conf.get("btg_number")
        statuses = {i["roll_id"]: i["status"] for i in conf["items"]}
        assert statuses[roll_ok] == "arrived"
        if roll_exc:
            assert conf["status"] == "completed_with_exception", conf["status"]
            assert conf["arrived_count"] == 1 and conf["exception_count"] == 1
            assert statuses[roll_exc] == "exception"
        else:
            assert conf["status"] == "completed", conf["status"]

        # roll pindah gudang (arrived) & exception tetap di asal
        tags = admin.get(f"{BASE}/api/rfid/tags", params={"warehouse_id": dest["id"]},
                         timeout=90).json()["tags"]
        moved = {t.get("roll_id") for t in tags}
        assert roll_ok in moved, "tag roll arrived tidak berpindah ke gudang tujuan"

        # inventory balances konsisten di gudang tujuan
        # catatan: GET /api/inventory/balances tidak punya filter warehouse_id → filter di klien
        bal = admin.get(f"{BASE}/api/inventory/balances", timeout=120)
        assert bal.status_code == 200, bal.text[:300]
        rows = bal.json()
        rows = rows.get("balances", rows) if isinstance(rows, dict) else rows
        pid = pa["items"][0]["product_id"]
        row = next((b for b in rows if b.get("product_id") == pid
                    and b.get("warehouse_id") == dest["id"]), None)
        assert row is not None, f"balance produk {pid} tidak ada di gudang tujuan {dest['id']}"
        onhand = float(row.get("on_hand_qty") or row.get("qty_on_hand")
                       or row.get("available_qty") or 0)
        assert onhand > 0, f"balance gudang tujuan kosong: {row}"
        assert int(row.get("on_hand_roll_count") or row.get("roll_count") or 0) >= 1

        # resolve exception → accept
        if not roll_exc:
            return
        rs = admin.post(f"{BASE}/api/putaway-orders/{pa['id']}/resolve-exception",
                        json={"roll_ids": [roll_exc], "action": "accept"}, timeout=120)
        assert rs.status_code == 200, rs.text[:400]
        fin = rs.json()
        assert fin["status"] == "completed", fin["status"]
        assert fin["exception_count"] == 0
        assert {i["status"] for i in fin["items"]} == {"arrived"}

        # tidak ada exception lagi → resolve ulang 404
        rs2 = admin.post(f"{BASE}/api/putaway-orders/{pa['id']}/resolve-exception",
                         json={"roll_ids": [roll_exc], "action": "accept"}, timeout=90)
        assert rs2.status_code == 404, f"-> {rs2.status_code}"

    def test_list_orders_filter(self, admin):
        r = admin.get(f"{BASE}/api/putaway-orders", timeout=90)
        assert r.status_code == 200, r.text[:300]
        orders = r.json()["orders"]
        assert orders, "tidak ada PA sama sekali"
        if STATE.get("pa"):
            assert any(o["id"] == STATE["pa"]["id"] for o in orders)
        assert all("_id" not in o for o in orders)
        f = admin.get(f"{BASE}/api/putaway-orders",
                      params={"status": "completed"}, timeout=90).json()["orders"]
        assert all(o["status"] == "completed" for o in f)

    def test_suggest_unknown_warehouse_404(self, admin):
        r = admin.get(f"{BASE}/api/putaway-orders/suggest",
                      params={"from_warehouse_id": "wh_nope"}, timeout=90)
        assert r.status_code == 404, f"-> {r.status_code}"


# ─────────────────────────── REGRESI ───────────────────────────
class TestRegression:
    def test_inventory_balances(self, admin):
        r = admin.get(f"{BASE}/api/inventory/balances", timeout=120)
        assert r.status_code == 200, r.text[:300]

    def test_putaway_queue(self, admin):
        r = admin.get(f"{BASE}/api/inventory/putaway/queue", timeout=120)
        assert r.status_code == 200, r.text[:300]

    def test_rfid_summary(self, admin):
        r = admin.get(f"{BASE}/api/rfid/summary", timeout=120)
        assert r.status_code == 200, r.text[:300]

    def test_rfid_tags(self, admin):
        r = admin.get(f"{BASE}/api/rfid/tags", timeout=120)
        assert r.status_code == 200, r.text[:300]
        assert "tags" in r.json()


# ─────────────────── SCOPE / RBAC GUARDS (R0-R2) ───────────────────
class TestScopeAndRbac:
    """Mode 'Semua Entitas' hanya-lihat; peran sales tidak boleh akses WMS R2."""

    def test_all_entity_mode_write_rejected(self, admin):
        s = requests.Session()
        s.headers.update({"Authorization": admin.headers["Authorization"], "X-Entity-Id": "all"})
        pa = s.post(f"{BASE}/api/putaway-orders", json={
            "from_warehouse_id": "wh_surabaya", "to_warehouse_id": "wh_jakarta",
            "roll_ids": ["roll_dummy"]}, timeout=90)
        assert pa.status_code == 409, f"PA create mode=all -> {pa.status_code}"
        pj = s.post(f"{BASE}/api/rfid/print-jobs", json={"roll_ids": ["roll_dummy"]}, timeout=90)
        assert pj.status_code == 409, f"print-job mode=all -> {pj.status_code}"

    def test_unauthenticated_rejected(self):
        assert requests.get(f"{BASE}/api/warehouse-sites", timeout=90).status_code == 401
        assert requests.get(f"{BASE}/api/putaway-orders", timeout=90).status_code == 401

    def test_sales_role_forbidden(self):
        s = requests.Session()
        s.headers.update({"Authorization": f"Bearer {login('sales@kainnusantara.id')}",
                          "X-Entity-Id": ENT})
        assert s.get(f"{BASE}/api/putaway-orders", timeout=90).status_code == 403
        assert s.post(f"{BASE}/api/putaway-orders", json={
            "from_warehouse_id": "wh_surabaya", "to_warehouse_id": "wh_jakarta",
            "roll_ids": ["roll_dummy"]}, timeout=90).status_code == 403
