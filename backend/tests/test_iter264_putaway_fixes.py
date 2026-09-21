"""Iteration 264 — RETEST TERFOKUS perbaikan bug iteration_263 (WMS/RFID R2).

BE-1 GET /api/putaway-orders/suggest → grade-aware (field `grade` per grup,
      kandidat dihitung per grade: grade B/C/BS mendapat 'Gedung Retur', grade A tidak)
BE-2 POST /api/putaway-orders/{id}/resolve-exception aksi tidak valid → 400
      SEBELUM mutasi apa pun (item exception tetap exception)
BE-3 Regresi confirm-arrival (kini bulk_write): PA kecil → dispatch → confirm semua EPC
      → BTG terbit, roll pindah gudang, balance konsisten
"""
import os

import pytest
import requests
from dotenv import dotenv_values
from pymongo import MongoClient

fe = dotenv_values("/app/frontend/.env")
be = dotenv_values("/app/backend/.env")
BASE = (os.environ.get("REACT_APP_BACKEND_URL") or fe.get("REACT_APP_BACKEND_URL")).rstrip("/")
MONGO_URL = os.environ.get("MONGO_URL") or be.get("MONGO_URL")
DB_NAME = os.environ.get("DB_NAME") or be.get("DB_NAME")
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
def mongo():
    cli = MongoClient(MONGO_URL)
    yield cli[DB_NAME]
    cli.close()


@pytest.fixture(scope="session")
def warehouses(admin):
    r = admin.get(f"{BASE}/api/warehouses?scope=all", timeout=90)
    assert r.status_code == 200, r.text[:300]
    rows = r.json()
    rows = rows.get("warehouses", rows) if isinstance(rows, dict) else rows
    return rows


def _find_ready(admin, warehouses):
    for w in warehouses:
        r = admin.get(f"{BASE}/api/putaway-orders/suggest",
                      params={"from_warehouse_id": w["id"]}, timeout=90)
        if r.status_code == 200 and r.json().get("ready_count", 0) > 0:
            return w
    return None


def _seed_ready_rolls(admin):
    """SEED: cetak tag untuk roll untagged lalu verifikasi → stage tag_verified."""
    def untagged_by_wh():
        r = admin.get(f"{BASE}/api/rfid/untagged-rolls", timeout=90)
        out = {}
        for roll in (r.json().get("rolls") if r.status_code == 200 else []):
            out.setdefault(roll.get("warehouse_id"), []).append(roll)
        return out

    by_wh = untagged_by_wh()
    if not by_wh or max((len(v) for v in by_wh.values()), default=0) < 2:
        tags = admin.get(f"{BASE}/api/rfid/tags", params={"status": "active"},
                         timeout=90).json()["tags"]
        per_wh = {}
        for t in tags:
            if t.get("roll_id"):
                per_wh.setdefault(t.get("warehouse_id"), []).append(t)
        group = max(per_wh.values(), key=len, default=[])
        for t in group[:3]:
            admin.delete(f"{BASE}/api/rfid/tags/{t['id']}", timeout=90)
        by_wh = untagged_by_wh()
    if not by_wh:
        return None
    wid, rolls = max(by_wh.items(), key=lambda kv: len(kv[1]))
    job = admin.post(f"{BASE}/api/rfid/print-jobs",
                     json={"roll_ids": [x["id"] for x in rolls[:3]]}, timeout=120)
    if job.status_code != 200:
        return None
    job = job.json()
    epcs = [i["epc"] for i in job["items"]]
    admin.post(f"{BASE}/api/rfid/print-jobs/{job['id']}/mark-printed", timeout=90)
    sess = admin.post(f"{BASE}/api/rfid/print-jobs/{job['id']}/verify/start", timeout=90).json()
    admin.post(f"{BASE}/api/rfid/verify-sessions/{sess['id']}/scan",
               json={"epcs": epcs}, timeout=90)
    admin.post(f"{BASE}/api/rfid/verify-sessions/{sess['id']}/complete", timeout=90)
    return wid


@pytest.fixture(scope="session")
def transit_wh(admin, warehouses):
    """Gudang asal yang punya roll siap-putaway (ready_count > 0); self-seeding."""
    w = _find_ready(admin, warehouses)
    if w:
        return w
    seeded = _seed_ready_rolls(admin)
    w = _find_ready(admin, warehouses)
    if w:
        return w
    pytest.fail(f"gagal menyiapkan roll siap-putaway (seed wh={seeded})")


# ───────────────────── BE-1: suggest grade-aware ─────────────────────
class TestSuggestGradeAware:
    def test_groups_expose_grade_field(self, admin, transit_wh):
        r = admin.get(f"{BASE}/api/putaway-orders/suggest",
                      params={"from_warehouse_id": transit_wh["id"]}, timeout=90)
        assert r.status_code == 200, r.text[:400]
        data = r.json()
        assert data["groups"], "tidak ada grup saran"
        for g in data["groups"]:
            assert "grade" in g, f"grup tanpa field grade: {g.keys()}"
            assert g["grade"] == (g["grade"] or "").upper()
            assert isinstance(g["candidates"], list)
            # semua roll dalam grup harus punya grade sama dengan grup
            for roll in g["rolls"]:
                assert (roll.get("grade") or "A").upper() == g["grade"], (
                    f"roll {roll.get('roll_no')} grade {roll.get('grade')} "
                    f"tercampur di grup grade {g['grade']}")

    def test_grade_a_group_excludes_retur(self, admin, transit_wh):
        r = admin.get(f"{BASE}/api/putaway-orders/suggest",
                      params={"from_warehouse_id": transit_wh["id"]}, timeout=90)
        groups = [g for g in r.json()["groups"] if g["grade"] == "A"]
        if not groups:
            pytest.skip("tidak ada grup grade A")
        for g in groups:
            names = [c["warehouse_name"] for c in g["candidates"]]
            assert not any("Retur" in n for n in names), (
                f"grade A tidak boleh disarankan ke gudang Retur; kandidat={names}")

    def test_grade_b_group_includes_retur(self, admin, mongo, transit_wh):
        """Ubah SEMENTARA grade 1 roll siap-putaway → 'B', lalu KEMBALIKAN."""
        r = admin.get(f"{BASE}/api/putaway-orders/suggest",
                      params={"from_warehouse_id": transit_wh["id"]}, timeout=90)
        groups = r.json()["groups"]
        b_groups = [g for g in groups if g["grade"] in ("B", "C", "BS")]
        temp_roll_id, original_grade = None, None
        if not b_groups:
            roll = groups[0]["rolls"][0]
            doc = mongo.inventory_rolls.find_one({"id": roll["id"]}, {"_id": 0, "grade": 1})
            temp_roll_id, original_grade = roll["id"], doc.get("grade")
            mongo.inventory_rolls.update_one({"id": temp_roll_id}, {"$set": {"grade": "B"}})
        try:
            r2 = admin.get(f"{BASE}/api/putaway-orders/suggest",
                           params={"from_warehouse_id": transit_wh["id"]}, timeout=90)
            assert r2.status_code == 200, r2.text[:300]
            b_groups = [g for g in r2.json()["groups"] if g["grade"] in ("B", "C", "BS")]
            assert b_groups, "grup grade B tidak muncul setelah roll di-set grade B"
            for g in b_groups:
                names = [c["warehouse_name"] for c in g["candidates"]]
                assert any("Retur" in n for n in names), (
                    f"grade {g['grade']} HARUS mendapat kandidat Gedung Retur; kandidat={names}")
        finally:
            if temp_roll_id is not None:
                mongo.inventory_rolls.update_one({"id": temp_roll_id},
                                                 {"$set": {"grade": original_grade}})
                back = mongo.inventory_rolls.find_one({"id": temp_roll_id}, {"_id": 0, "grade": 1})
                assert back.get("grade") == original_grade, "grade tidak berhasil dipulihkan"


# ────────── BE-2: resolve-exception aksi invalid → 400 tanpa mutasi ──────────
class TestResolveExceptionValidation:
    def test_invalid_action_400_no_mutation(self, admin):
        r = admin.get(f"{BASE}/api/putaway-orders", params={"limit": 200}, timeout=90)
        assert r.status_code == 200, r.text[:300]
        orders = r.json()["orders"]
        target = next((o for o in orders
                       if any(i["status"] == "exception" for i in o.get("items", []))), None)
        if not target:
            pytest.skip("tidak ada PA dengan item exception di DB")
        exc_rolls = [i["roll_id"] for i in target["items"] if i["status"] == "exception"]
        before = {i["roll_id"]: i["status"] for i in target["items"]}
        status_before = target["status"]

        bad = admin.post(f"{BASE}/api/putaway-orders/{target['id']}/resolve-exception",
                         json={"roll_ids": exc_rolls, "action": "bogus_action"}, timeout=90)
        assert bad.status_code == 400, f"-> {bad.status_code} {bad.text[:300]}"
        assert "accept" in bad.text and "return_transit" in bad.text

        after = admin.get(f"{BASE}/api/putaway-orders", params={"limit": 200}, timeout=90)
        doc = next(o for o in after.json()["orders"] if o["id"] == target["id"])
        assert doc["status"] == status_before, "status PA berubah padahal aksi invalid"
        for item in doc["items"]:
            assert item["status"] == before[item["roll_id"]], (
                f"item {item['roll_no']} bermutasi: {before[item['roll_id']]} → {item['status']}")
        assert [i["roll_id"] for i in doc["items"] if i["status"] == "exception"] == exc_rolls

    def test_valid_action_but_no_matching_item_404(self, admin):
        r = admin.get(f"{BASE}/api/putaway-orders", params={"limit": 200}, timeout=90)
        orders = r.json()["orders"]
        target = next((o for o in orders
                       if any(i["status"] == "exception" for i in o.get("items", []))), None)
        if not target:
            pytest.skip("tidak ada PA dengan item exception di DB")
        resp = admin.post(f"{BASE}/api/putaway-orders/{target['id']}/resolve-exception",
                          json={"roll_ids": ["roll_does_not_exist"], "action": "accept"}, timeout=90)
        assert resp.status_code == 404, f"-> {resp.status_code} {resp.text[:300]}"


# ───────── BE-3: regresi confirm-arrival (bulk_write) end-to-end ─────────
class TestConfirmArrivalBulk:
    def test_small_pa_full_flow(self, admin, mongo, transit_wh):
        s = admin.get(f"{BASE}/api/putaway-orders/suggest",
                      params={"from_warehouse_id": transit_wh["id"]}, timeout=90)
        assert s.status_code == 200, s.text[:300]
        data = s.json()
        group = next((g for g in data["groups"] if g["candidates"] and g["rolls"]), None)
        if not group:
            pytest.skip("tidak ada grup dengan kandidat gudang tujuan")
        roll = group["rolls"][0]
        to_wh = group["candidates"][0]["warehouse_id"]

        before_roll = mongo.inventory_rolls.find_one({"id": roll["id"]}, {"_id": 0})
        product_id = before_roll["product_id"]
        assert before_roll["warehouse_id"] == transit_wh["id"]

        create = admin.post(f"{BASE}/api/putaway-orders", json={
            "from_warehouse_id": transit_wh["id"], "to_warehouse_id": to_wh,
            "roll_ids": [roll["id"]]}, timeout=120)
        assert create.status_code == 200, create.text[:400]
        order = create.json()
        assert order["status"] == "open" and order["item_count"] == 1
        assert order["pa_number"].startswith("PA")
        epc = order["items"][0]["epc"]
        assert epc, "EPC item PA kosong"

        d = admin.post(f"{BASE}/api/putaway-orders/{order['id']}/dispatch", timeout=90)
        assert d.status_code == 200, d.text[:300]
        assert d.json()["status"] == "in_transit"

        c = admin.post(f"{BASE}/api/putaway-orders/{order['id']}/confirm-arrival",
                       json={"scanned_epcs": [epc]}, timeout=120)
        assert c.status_code == 200, c.text[:400]
        done = c.json()
        assert done["status"] == "completed", done["status"]
        assert done["btg_number"] and done["btg_number"].startswith("BTG")
        assert done["arrived_count"] == 1 and done.get("exception_count", 0) == 0
        assert done["items"][0]["status"] == "arrived"

        # roll pindah gudang + journey stored
        after_roll = mongo.inventory_rolls.find_one({"id": roll["id"]}, {"_id": 0})
        assert after_roll["warehouse_id"] == to_wh, (
            f"roll tidak pindah: {after_roll['warehouse_id']} != {to_wh}")
        assert (after_roll.get("journey") or {}).get("stage") == "stored"
        tag = mongo.rfid_tags.find_one({"roll_id": roll["id"], "status": "active"}, {"_id": 0})
        if tag:
            assert tag.get("warehouse_id") == to_wh, "tag RFID tidak ikut pindah gudang"

        # movement pasangan out/in terbit
        movs = list(mongo.inventory_movements.find(
            {"source_document": done["pa_number"], "roll_id": roll["id"]}, {"_id": 0}))
        assert len(movs) == 2, f"movement tidak sepasang: {len(movs)}"
        assert {m["movement_type"] for m in movs} == {
            "putaway_transfer_out", "putaway_transfer_in"}
        assert round(sum(m["quantity"] for m in movs), 3) == 0.0

        # balance = proyeksi rolls (konsisten kedua sisi)
        for wid in (transit_wh["id"], to_wh):
            rolls = list(mongo.inventory_rolls.find(
                {"product_id": product_id, "warehouse_id": wid,
                 "owner_entity_id": order["owner_entity_id"],
                 "length_remaining": {"$gt": 0}}, {"_id": 0, "length_remaining": 1}))
            expected = round(sum(float(x.get("length_remaining") or 0) for x in rolls), 2)
            bal = mongo.inventory_balances.find_one(
                {"product_id": product_id, "warehouse_id": wid,
                 "owner_entity_id": order["owner_entity_id"]}, {"_id": 0}) or {}
            actual = round(float(bal.get("on_hand_qty") or 0), 2)
            assert abs(actual - expected) < 0.05, (
                f"balance {wid}: {actual} != proyeksi rolls {expected}")
