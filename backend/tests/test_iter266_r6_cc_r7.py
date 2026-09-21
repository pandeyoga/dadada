"""ITERATION 266 — FASE R6 (insiden gate merah, shrinkage, device health)
· CYCLE COUNT RFID · R7 FULFILLMENT WIZARD.

JALANKAN DENGAN `-n 0` (kelas saling bergantung lewat dict STATE).
"""
import os
from typing import Any, Dict, List

import pytest
import requests
from dotenv import dotenv_values
from pymongo import MongoClient

FE = dotenv_values("/app/frontend/.env")
BASE = (os.environ.get("REACT_APP_BACKEND_URL") or FE.get("REACT_APP_BACKEND_URL", "")).rstrip("/")
if not BASE:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
BE = dotenv_values("/app/backend/.env")
MDB = MongoClient(BE["MONGO_URL"])[BE["DB_NAME"]]

ENT = "ent_ksc"
GATE_BDG_OUT = "rdev_b1bc75a4db04"
WH_BDG = "wh_bandung"
WH_JKT = "wh_jakarta"
SO_KSC = "so_007"
SO_OTHER = "so_002"          # milik ent_kanda

STATE: Dict[str, Any] = {}


@pytest.fixture(scope="session")
def api():
    s = requests.Session()
    r = s.post(f"{BASE}/api/auth/login",
               json={"email": "admin@kainnusantara.id", "password": "demo12345"}, timeout=60)
    if r.status_code != 200:
        pytest.fail(f"login gagal {r.status_code}: {r.text[:300]}")
    s.headers.update({"Authorization": f"Bearer {r.json()['token']}", "X-Entity-Id": ENT})
    return s


def _epcs_of(warehouse_id: str, status: str = "available", limit: int = 50) -> List[Dict[str, Any]]:
    rolls = list(MDB.inventory_rolls.find(
        {"warehouse_id": warehouse_id, "owner_entity_id": ENT, "status": status,
         "length_remaining": {"$gt": 0}, "rfid_tag_id": {"$nin": [None, ""]}},
        {"_id": 0, "id": 1, "roll_no": 1, "rfid_tag_id": 1}).limit(limit))
    out = []
    for r in rolls:
        t = MDB.rfid_tags.find_one({"id": r["rfid_tag_id"], "status": "active"},
                                   {"_id": 0, "epc": 1})
        if t:
            out.append({"roll_id": r["id"], "roll_no": r.get("roll_no"), "epc": t["epc"]})
    return out


def _device_key(api, device_id: str) -> str:
    r = api.post(f"{BASE}/api/rfid/devices/{device_id}/api-key", timeout=60)
    assert r.status_code == 200, f"api-key: {r.status_code} {r.text[:300]}"
    return r.json()["api_key"]


# ══════════════════ R6 — INSIDEN GATE MERAH ══════════════════
class TestR6Incidents:
    def test_01_ingest_red_creates_incident(self, api):
        key = _device_key(api, GATE_BDG_OUT)
        STATE["gate_key"] = key
        rolls = _epcs_of(WH_BDG, "available", 5)
        assert rolls, "tidak ada roll available ber-tag di wh_bandung untuk uji gate merah"
        epc = rolls[0]["epc"]
        STATE["red_epc"] = epc
        # idempotensi uji: buang sisa insiden open dari eksekusi uji sebelumnya
        MDB.rfid_incidents.delete_many({"epc": epc, "device_id": GATE_BDG_OUT, "status": "open"})
        before = api.get(f"{BASE}/api/rfid/incidents?status=open", timeout=60).json()
        ids_before = {i["id"] for i in before["incidents"]}

        r = requests.post(f"{BASE}/api/rfid/ingest", json={"epcs": [epc]},
                          headers={"X-Device-Key": key}, timeout=60)
        assert r.status_code == 200, f"ingest: {r.status_code} {r.text[:300]}"
        body = r.json()
        res = body.get("results") or []
        assert res, body
        assert res[0]["result"] == "red", f"harus merah (roll available keluar gate): {res[0]}"

        after = api.get(f"{BASE}/api/rfid/incidents?status=open", timeout=60)
        assert after.status_code == 200, after.text[:300]
        new = [i for i in after.json()["incidents"] if i["id"] not in ids_before]
        assert len(new) == 1, f"harus tepat 1 insiden baru, dapat {len(new)}"
        inc = new[0]
        assert inc["epc"] == epc
        assert inc["device_id"] == GATE_BDG_OUT
        assert inc["status"] == "open"
        assert inc["hits"] == 1
        assert inc["reason"], "alasan insiden kosong"
        assert inc["warehouse_id"] == WH_BDG
        assert inc.get("roll_no")
        STATE["inc_id"] = inc["id"]

    def test_02_dedupe_10_minutes(self, api):
        r = requests.post(f"{BASE}/api/rfid/ingest", json={"epcs": [STATE["red_epc"]]},
                          headers={"X-Device-Key": STATE["gate_key"]}, timeout=60)
        assert r.status_code == 200, r.text[:300]
        rows = api.get(f"{BASE}/api/rfid/incidents?status=open", timeout=60).json()["incidents"]
        same = [i for i in rows if i["epc"] == STATE["red_epc"] and i["device_id"] == GATE_BDG_OUT]
        assert len(same) == 1, f"duplikasi insiden: {len(same)}"
        assert same[0]["id"] == STATE["inc_id"]
        assert same[0]["hits"] == 2, f"hits harus bertambah, dapat {same[0]['hits']}"

    def test_03_acknowledge(self, api):
        r = api.post(f"{BASE}/api/rfid/incidents/{STATE['inc_id']}/acknowledge",
                     json={"note": "TEST_ dicek petugas gudang"}, timeout=60)
        assert r.status_code == 200, f"{r.status_code} {r.text[:300]}"
        b = r.json()
        assert b["status"] == "acknowledged"
        assert b["ack_by"] and b["ack_at"]
        assert any("TEST_" in (n.get("text") or "") for n in b.get("notes") or []), b.get("notes")
        # persisten
        g = api.get(f"{BASE}/api/rfid/incidents?status=acknowledged", timeout=60).json()
        assert STATE["inc_id"] in {i["id"] for i in g["incidents"]}

    def test_04_ack_twice_is_400(self, api):
        r = api.post(f"{BASE}/api/rfid/incidents/{STATE['inc_id']}/acknowledge",
                     json={"note": ""}, timeout=60)
        assert r.status_code == 400, f"transisi tak sah harus 400, dapat {r.status_code}"

    def test_05_resolve(self, api):
        r = api.post(f"{BASE}/api/rfid/incidents/{STATE['inc_id']}/resolve",
                     json={"note": "TEST_ roll dikembalikan ke rak"}, timeout=60)
        assert r.status_code == 200, f"{r.status_code} {r.text[:300]}"
        b = r.json()
        assert b["status"] == "resolved"
        assert b["resolved_by"] and b["resolved_at"]
        r2 = api.post(f"{BASE}/api/rfid/incidents/{STATE['inc_id']}/resolve",
                      json={"note": ""}, timeout=60)
        assert r2.status_code == 400, f"resolve ulang harus 400, dapat {r2.status_code}"

    def test_06_unknown_incident_404(self, api):
        r = api.post(f"{BASE}/api/rfid/incidents/rinc_tidakada/acknowledge",
                     json={"note": ""}, timeout=60)
        assert r.status_code == 404, r.status_code

    def test_07_gate_simulate_still_creates_incident(self, api):
        rolls = _epcs_of(WH_BDG, "available", 5)
        target = next((x for x in rolls if x["epc"] != STATE["red_epc"]), None)
        assert target, "butuh roll available kedua"
        r = api.post(f"{BASE}/api/rfid/gate/simulate",
                     json={"device_id": GATE_BDG_OUT, "roll_id": target["roll_id"]}, timeout=60)
        assert r.status_code == 200, f"{r.status_code} {r.text[:300]}"
        assert r.json()["result"] == "red", r.json()
        rows = api.get(f"{BASE}/api/rfid/incidents?status=open", timeout=60).json()["incidents"]
        hit = [i for i in rows if i["epc"] == target["epc"]]
        assert hit, "simulasi gate merah tidak membuat insiden"
        STATE["inc_sim_id"] = hit[0]["id"]

    def test_08_filter_by_warehouse(self, api):
        r = api.get(f"{BASE}/api/rfid/incidents?warehouse_id={WH_BDG}", timeout=60)
        assert r.status_code == 200, r.text[:300]
        rows = r.json()["incidents"]
        assert rows and all(i["warehouse_id"] == WH_BDG for i in rows)


# ══════════════════ R6 — SHRINKAGE + DEVICE HEALTH ══════════════════
class TestR6Reports:
    def test_01_shrinkage_report(self, api):
        r = api.get(f"{BASE}/api/rfid/shrinkage-report?days=30", timeout=60)
        assert r.status_code == 200, f"{r.status_code} {r.text[:300]}"
        b = r.json()
        assert b["days"] == 30
        for k in ("red_reads", "incidents_open", "gate_exception_rolls"):
            assert k in b["totals"], b["totals"]
            assert isinstance(b["totals"][k], int)
        assert b["totals"]["red_reads"] >= 3, b["totals"]
        assert b["totals"]["incidents_open"] >= 1, b["totals"]
        assert isinstance(b["per_warehouse"], list) and b["per_warehouse"]
        bdg = next((w for w in b["per_warehouse"] if w["warehouse_id"] == WH_BDG), None)
        assert bdg, b["per_warehouse"]
        assert bdg["warehouse_name"] and bdg["red_reads"] >= 3
        assert isinstance(b["recent_cycle_counts"], list)
        assert all("_id" not in c for c in b["recent_cycle_counts"])

    def test_02_shrinkage_days_1(self, api):
        r = api.get(f"{BASE}/api/rfid/shrinkage-report?days=1", timeout=60)
        assert r.status_code == 200, r.text[:300]
        assert r.json()["days"] == 1

    def test_03_device_health(self, api):
        hb = requests.post(f"{BASE}/api/rfid/heartbeat", headers={"X-Device-Key": STATE["gate_key"]},
                           timeout=60)
        assert hb.status_code == 200, f"heartbeat: {hb.status_code} {hb.text[:300]}"
        r = api.get(f"{BASE}/api/rfid/device-health", timeout=60)
        assert r.status_code == 200, f"{r.status_code} {r.text[:300]}"
        b = r.json()
        assert b["count"] == len(b["devices"]) and b["count"] >= 12
        dev = next((d for d in b["devices"] if d["id"] == GATE_BDG_OUT), None)
        assert dev, "device gate BDG OUT tidak ada di device-health"
        assert dev["heartbeat_age_sec"] is not None and dev["heartbeat_age_sec"] < 120, dev
        assert dev["effective_status"] == "online", dev
        for d in b["devices"]:
            assert d["effective_status"] in ("online", "stale", "offline"), d
            assert "api_key" not in d, "api_key device BOCOR di device-health"
            assert "_id" not in d
        assert isinstance(b["stale_count"], int)


# ══════════════════ CYCLE COUNT RFID ══════════════════
class TestCycleCount:
    def test_01_start_session(self, api):
        bal_before = list(MDB.inventory_balances.find(
            {"warehouse_id": WH_BDG}, {"_id": 0, "product_id": 1, "on_hand_qty": 1,
                                       "available_qty": 1, "reserved_qty": 1}))
        STATE["bal_before"] = sorted(bal_before, key=lambda x: x["product_id"])
        r = api.post(f"{BASE}/api/rfid/cycle-count/start", json={"warehouse_id": WH_BDG}, timeout=60)
        assert r.status_code == 200, f"{r.status_code} {r.text[:300]}"
        s = r.json()
        assert s["kind"] == "cycle_count"
        assert s["status"] == "open"
        assert s["warehouse_id"] == WH_BDG and s["warehouse_name"]
        assert s["owner_entity_id"] == ENT
        assert len(s["expected"]) >= 10, f"expected sedikit: {len(s['expected'])}"
        STATE["cc_sess"] = s["id"]
        STATE["cc_expected"] = [e["epc"] for e in s["expected"]]

    def test_02_start_again_returns_same_session(self, api):
        r = api.post(f"{BASE}/api/rfid/cycle-count/start", json={"warehouse_id": WH_BDG}, timeout=60)
        assert r.status_code == 200, r.text[:300]
        assert r.json()["id"] == STATE["cc_sess"], "start kedua harus kembalikan sesi yang sama"

    def test_03_start_unknown_warehouse_404(self, api):
        r = api.post(f"{BASE}/api/rfid/cycle-count/start", json={"warehouse_id": "wh_tidakada"},
                     timeout=60)
        assert r.status_code == 404, r.status_code

    def test_04_scan_partial_plus_misplaced(self, api):
        expected = STATE["cc_expected"]
        missing_epc = expected[-1]
        STATE["cc_missing_epc"] = missing_epc
        jkt = _epcs_of(WH_JKT, "available", 3)
        assert jkt, "butuh roll gudang lain untuk uji extra misplaced"
        STATE["cc_extra_epc"] = jkt[0]["epc"]
        payload = {"epcs": expected[:-1] + [jkt[0]["epc"], "EPC_TEST_ASING_0001"]}
        r = api.post(f"{BASE}/api/rfid/verify-sessions/{STATE['cc_sess']}/scan",
                     json=payload, timeout=60)
        assert r.status_code == 200, f"{r.status_code} {r.text[:300]}"
        b = r.json()
        assert b["expected_count"] == len(expected)
        assert b["matched_count"] == len(expected) - 1, b["matched_count"]
        assert missing_epc in b["missing"]
        assert jkt[0]["epc"] in b["extra"] and "EPC_TEST_ASING_0001" in b["extra"]

    def test_05_complete(self, api):
        r = api.post(f"{BASE}/api/rfid/cycle-count/{STATE['cc_sess']}/complete", timeout=60)
        assert r.status_code == 200, f"{r.status_code} {r.text[:300]}"
        cc = r.json()
        assert cc["cc_number"].startswith("CC"), cc["cc_number"]
        assert cc["warehouse_id"] == WH_BDG
        n = len(STATE["cc_expected"])
        assert cc["expected_count"] == n
        assert cc["found_count"] == n - 1
        assert cc["missing_count"] == 1
        assert cc["extra_count"] == 2
        assert cc["accuracy_pct"] == round((n - 1) / n * 100, 1), cc["accuracy_pct"]
        assert [m["epc"] for m in cc["missing_items"]] == [STATE["cc_missing_epc"]]
        assert cc["missing_items"][0].get("roll_no"), cc["missing_items"][0]
        kinds = {e["kind"] for e in cc["extra_items"]}
        assert kinds == {"misplaced", "unknown"}, cc["extra_items"]
        mis = next(e for e in cc["extra_items"] if e["kind"] == "misplaced")
        assert mis["epc"] == STATE["cc_extra_epc"] and mis.get("roll_no")
        STATE["cc_id"] = cc["id"]
        STATE["cc_number"] = cc["cc_number"]

    def test_06_no_stock_change(self, api):
        after = sorted(list(MDB.inventory_balances.find(
            {"warehouse_id": WH_BDG}, {"_id": 0, "product_id": 1, "on_hand_qty": 1,
                                       "available_qty": 1, "reserved_qty": 1})),
            key=lambda x: x["product_id"])
        assert after == STATE["bal_before"], "cycle count TIDAK boleh mengubah balances"

    def test_07_complete_twice_400(self, api):
        r = api.post(f"{BASE}/api/rfid/cycle-count/{STATE['cc_sess']}/complete", timeout=60)
        assert r.status_code == 400, r.status_code

    def test_08_list_and_detail(self, api):
        r = api.get(f"{BASE}/api/rfid/cycle-counts", timeout=60)
        assert r.status_code == 200, r.text[:300]
        rows = r.json()["counts"]
        assert r.json()["count"] == len(rows)
        nums = {c["cc_number"] for c in rows}
        assert STATE["cc_number"] in nums and "CC00001" in nums, nums
        assert all("_id" not in c for c in rows)
        d = api.get(f"{BASE}/api/rfid/cycle-counts/{STATE['cc_id']}", timeout=60)
        assert d.status_code == 200, d.text[:300]
        assert d.json()["missing_count"] == 1
        nf = api.get(f"{BASE}/api/rfid/cycle-counts/rcc_tidakada", timeout=60)
        assert nf.status_code == 404, nf.status_code

    def test_09_filter_by_warehouse(self, api):
        r = api.get(f"{BASE}/api/rfid/cycle-counts?warehouse_id={WH_BDG}", timeout=60)
        assert r.status_code == 200
        assert all(c["warehouse_id"] == WH_BDG for c in r.json()["counts"])


# ══════════════════ R7 — FULFILLMENT WIZARD ══════════════════
class TestR7Wizard:
    def test_01_wizard_analysis(self, api):
        r = api.get(f"{BASE}/api/fulfillment/wizard/{SO_KSC}", timeout=90)
        assert r.status_code == 200, f"{r.status_code} {r.text[:300]}"
        b = r.json()
        assert b["so"]["id"] == SO_KSC and b["so"]["entity_id"] == ENT
        assert b["so"]["number"] and b["so"]["entity_name"]
        assert b["items"], "wizard tanpa item"
        for it in b["items"]:
            assert it["recommendation"] in ("alokasi_stok", "interco", "pengadaan"), it
            assert it["scenario"] and it["label"]
            assert isinstance(it["steps"], list) and it["steps"]
            assert it["qty_needed"] > 0
            assert isinstance(it["own_available"], (int, float))
            assert isinstance(it["own_warehouses"], list)
            assert isinstance(it["other_entities"], list)
            for o in it["other_entities"]:
                assert o["entity_id"] != ENT
                assert "contract" in o
        assert b["overall"] in ("alokasi_stok", "interco", "pengadaan", "campuran")
        assert isinstance(b["procurement_items"], list)
        assert isinstance(b["interco_drafts"], list)
        STATE["wiz"] = b

    def test_02_other_entity_so_403(self, api):
        r = api.get(f"{BASE}/api/fulfillment/wizard/{SO_OTHER}", timeout=60)
        assert r.status_code == 403, f"SO entitas lain harus 403, dapat {r.status_code} {r.text[:200]}"

    def test_03_unknown_so_404(self, api):
        r = api.get(f"{BASE}/api/fulfillment/wizard/so_tidakada", timeout=60)
        assert r.status_code == 404, r.status_code

    def test_04_create_pr_draft(self, api):
        wiz = STATE["wiz"]
        items = [{"product_id": i["product_id"], "quantity": i["quantity"]}
                 for i in wiz["procurement_items"]] or \
                [{"product_id": wiz["items"][0]["product_id"], "quantity": 5}]
        r = api.post(f"{BASE}/api/fulfillment/wizard/{SO_KSC}/create-pr",
                     json={"items": items}, timeout=90)
        assert r.status_code == 200, f"{r.status_code} {r.text[:400]}"
        pr = r.json()
        assert "PR-" in pr["number"], pr["number"]
        assert pr["status"] == "draft", pr["status"]
        assert pr.get("source") == "wizard", pr.get("source")
        assert pr.get("entity_id") == ENT
        assert len(pr["items"]) == len(items)
        STATE["pr_id"] = pr["id"]
        STATE["pr_number"] = pr["number"]
        # persisten via GET
        g = api.get(f"{BASE}/api/purchase-requisitions/{pr['id']}", timeout=60)
        assert g.status_code == 200, f"GET PR: {g.status_code} {g.text[:200]}"
        assert g.json()["number"] == pr["number"]
        assert g.json()["source"] == "wizard"

    def test_05_create_pr_other_entity_403(self, api):
        r = api.post(f"{BASE}/api/fulfillment/wizard/{SO_OTHER}/create-pr",
                     json={"items": [{"product_id": "prod_batik_mega", "quantity": 1}]}, timeout=60)
        assert r.status_code == 403, f"dapat {r.status_code} {r.text[:200]}"

    def test_06_create_interco_without_contract_400(self, api):
        pid = STATE["wiz"]["items"][0]["product_id"]
        STATE["interco_pid"] = pid
        # pastikan memang tidak ada kontrak internal pasangan ini
        MDB.supplier_contracts.delete_many({"entity_id": "ent_kanda", "partner_kind": "entity",
                                            "partner_id": ENT, "product_id": pid,
                                            "contract_number": "TEST_SCT-R7"})
        pre = MDB.supplier_contracts.count_documents(
            {"entity_id": "ent_kanda", "partner_kind": "entity", "partner_id": ENT,
             "product_id": pid, "status": "active"})
        if pre:
            pytest.skip("sudah ada kontrak internal untuk pasangan ini")
        r = api.post(f"{BASE}/api/fulfillment/wizard/{SO_KSC}/create-interco",
                     json={"seller_entity_id": "ent_kanda",
                           "items": [{"product_id": pid, "quantity": 5}]}, timeout=90)
        assert r.status_code == 400, f"dapat {r.status_code} {r.text[:300]}"
        assert "kontrak" in r.text.lower(), r.text[:300]

    def test_07_create_interco_with_contract(self, api):
        pid = STATE["interco_pid"]
        MDB.supplier_contracts.insert_one({
            "id": "sct_test_r7_wizard", "contract_number": "TEST_SCT-R7",
            "entity_id": "ent_kanda", "partner_kind": "entity", "partner_id": ENT,
            "product_id": pid, "status": "active", "tariff_rate": 150000,
            "valid_from": "2026-01-01", "valid_to": "2027-12-31",
            "created_at": "2026-07-01T00:00:00+00:00", "notes": "TEST_ iterasi 266",
        })
        try:
            r = api.post(f"{BASE}/api/fulfillment/wizard/{SO_KSC}/create-interco",
                         json={"seller_entity_id": "ent_kanda",
                               "items": [{"product_id": pid, "quantity": 5}]}, timeout=90)
            assert r.status_code == 200, f"{r.status_code} {r.text[:400]}"
            pair = r.json()
            seller_doc, buyer_doc = pair.get("seller"), pair.get("buyer")
            assert seller_doc and buyer_doc, pair
            assert seller_doc["status"] == "draft", seller_doc["status"]
            assert seller_doc["seller_entity_id"] == "ent_kanda"
            assert seller_doc["buyer_entity_id"] == ENT
            assert seller_doc["items"][0]["unit_price"] == 150000, seller_doc["items"][0]
            assert seller_doc["items"][0]["contract_id"] == "sct_test_r7_wizard"
            pid_pair = pair.get("pair_id")
            assert pid_pair, pair
            twins = list(MDB.interco_transactions.find({"pair_id": pid_pair}, {"_id": 0, "role": 1}))
            assert len(twins) == 2, f"dokumen kembar interco tidak lengkap: {twins}"
            assert {t["role"] for t in twins} == {"seller", "buyer"}
            STATE["interco_pair"] = pid_pair
        finally:
            MDB.supplier_contracts.delete_one({"id": "sct_test_r7_wizard"})

    def test_08_wizard_contract_flag_is_pair_specific(self, api):
        """Flag kontrak di wizard harus untuk pasangan PT + barang, bukan kontrak apa pun."""
        r = api.get(f"{BASE}/api/fulfillment/wizard/{SO_KSC}", timeout=90)
        assert r.status_code == 200
        problems = []
        for it in r.json()["items"]:
            for o in it["other_entities"]:
                if o.get("contract"):
                    real = MDB.supplier_contracts.count_documents({
                        "entity_id": o["entity_id"], "partner_kind": "entity",
                        "partner_id": ENT, "product_id": it["product_id"], "status": "active"})
                    if not real:
                        problems.append((it["product_id"], o["entity_id"],
                                         o["contract"].get("contract_number")))
        assert not problems, ("wizard menandai 'ada kontrak internal' padahal kontrak itu bukan "
                             f"untuk pasangan PT ini: {problems}")


    def test_09_entity_names_resolved_not_raw_ids(self, api):
        """Wizard harus menampilkan NAMA badan usaha, bukan id mentah (ent_ksc)."""
        r = api.get(f"{BASE}/api/fulfillment/wizard/so_008", timeout=90)
        assert r.status_code == 200, r.text[:300]
        b = r.json()
        assert not b["so"]["entity_name"].startswith("ent_"), \
            f"entity_name SO masih id mentah: {b['so']['entity_name']}"
        for it in b["items"]:
            for o in it["other_entities"]:
                assert not o["entity_name"].startswith("ent_"), \
                    f"entity_name entitas lain masih id mentah: {o['entity_name']}"

    def test_10_contract_flag_matches_pt_pair(self, api):
        """so_008 · prod_batik_mega: kontrak yang ditampilkan harus milik pasangan
        penjual=ent_kanda → pembeli=ent_ksc (KANDA/SCT-00001), bukan arah sebaliknya."""
        r = api.get(f"{BASE}/api/fulfillment/wizard/so_008", timeout=90)
        assert r.status_code == 200, r.text[:300]
        for it in r.json()["items"]:
            for o in it["other_entities"]:
                c = o.get("contract")
                if not c:
                    continue
                real = MDB.supplier_contracts.find_one(
                    {"id": c["id"]}, {"_id": 0, "entity_id": 1, "partner_id": 1,
                                      "contract_number": 1})
                assert real["entity_id"] == o["entity_id"] and real["partner_id"] == ENT, (
                    f"kontrak {real['contract_number']} bukan untuk pasangan penjual="
                    f"{o['entity_id']} → pembeli={ENT}")


def test_zz_cleanup_test_artifacts():
    """Bersihkan interco kembar & PR hasil uji; insiden/CC dibiarkan (jejak audit)."""
    pair = STATE.get("interco_pair")
    if pair:
        MDB.interco_transactions.delete_many({"pair_id": pair})
    MDB.supplier_contracts.delete_many({"id": "sct_test_r7_wizard"})
    assert MDB.supplier_contracts.count_documents({"id": "sct_test_r7_wizard"}) == 0
