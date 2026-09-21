"""ITERATION 265 — FASE R3 (Device Ingest API + printer pull) · R4 (Final Loading Check)
· JEJAK BARANG (roll journey timeline) · R5 (roll retur masuk pipeline fisik).

JALANKAN DENGAN `-n 0` (kelas saling bergantung lewat dict STATE).
"""
import os
import time
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
SO_ID = "so_d5287a3ace1e"          # KSC/SO-00010
TASK_ID = "wms_1bcfd8b53506"
GATE_JKT_IN = "rdev_dbc0cd6c6494"
GATE_JKT_OUT = "rdev_4e70218361df"
GATE_BDG_IN = "rdev_d5fcc540429d"

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


def _key(api, device_id: str, regenerate: bool = False) -> str:
    url = f"{BASE}/api/rfid/devices/{device_id}/api-key" + ("?regenerate=true" if regenerate else "")
    r = api.post(url, timeout=60)
    assert r.status_code == 200, f"api-key {device_id}: {r.status_code} {r.text[:300]}"
    body = r.json()
    assert body["device_id"] == device_id
    assert body["api_key"].startswith("dk_"), body
    return body["api_key"]


def _ingest(key: str, epcs: List[str]):
    return requests.post(f"{BASE}/api/rfid/ingest", json={"epcs": epcs},
                         headers={"X-Device-Key": key} if key else {}, timeout=60)


def _epc_of_roll(roll_id: str) -> str:
    roll = MDB.inventory_rolls.find_one({"id": roll_id}, {"_id": 0, "rfid_tag_id": 1})
    tag = MDB.rfid_tags.find_one({"id": (roll or {}).get("rfid_tag_id"), "status": "active"},
                                 {"_id": 0, "epc": 1})
    assert tag, f"roll {roll_id} tidak punya tag aktif"
    return tag["epc"]


# ══════════════════════ R3 — API KEY · HEARTBEAT · INGEST ══════════════════════
class TestR3DeviceIngest:

    def test_01_api_key_issue_and_idempotent(self, api):
        k1 = _key(api, GATE_JKT_OUT)
        k2 = _key(api, GATE_JKT_OUT)
        assert k1 == k2, "api-key tanpa regenerate harus idempotent"
        k3 = _key(api, GATE_JKT_OUT, regenerate=True)
        assert k3 != k1, "regenerate=true wajib mengganti key"
        STATE["key_out"] = k3
        STATE["key_in_jkt"] = _key(api, GATE_JKT_IN)
        STATE["key_in_bdg"] = _key(api, GATE_BDG_IN)
        # key lama tidak berlaku lagi
        assert _ingest(k1, ["E2FF-FFFF-FFFF-FFFF-FFFF-FFFF"]).status_code == 401

    def test_02_api_key_404_unknown_device(self, api):
        r = api.post(f"{BASE}/api/rfid/devices/rdev_bogus/api-key", timeout=60)
        assert r.status_code == 404, r.text[:200]

    def test_03_heartbeat_sets_online(self, api):
        r = requests.post(f"{BASE}/api/rfid/heartbeat",
                          headers={"X-Device-Key": STATE["key_out"]}, timeout=60)
        assert r.status_code == 200, r.text[:300]
        assert r.json()["device_id"] == GATE_JKT_OUT
        dev = MDB.rfid_devices.find_one({"id": GATE_JKT_OUT}, {"_id": 0, "status": 1, "last_heartbeat": 1})
        assert dev["status"] == "online" and dev["last_heartbeat"]

    def test_04_no_key_and_bad_key_401(self):
        assert requests.post(f"{BASE}/api/rfid/heartbeat", timeout=60).status_code == 401
        assert _ingest(None, ["E2AA"]).status_code == 401
        assert _ingest("dk_tidakada", ["E2AA"]).status_code == 401

    def test_05_ingest_unknown_epc_red(self):
        bogus = "E2BOGUS-0000-0000-0000-0001"
        r = _ingest(STATE["key_out"], [bogus])
        assert r.status_code == 200, r.text[:300]
        b = r.json()
        assert b["count"] == 1 and b["red"] == 1
        res = b["results"][0]
        assert res["result"] == "red" and "tidak dikenal" in res["reason"].lower(), res
        STATE["bogus_epc"] = bogus.upper()

    def test_06_ingest_available_roll_gate_out_red(self):
        roll = MDB.inventory_rolls.find_one(
            {"status": "available", "rfid_tag_id": {"$nin": [None, ""]}, "owner_entity_id": ENT},
            {"_id": 0, "id": 1})
        assert roll, "tidak ada roll available ber-tag untuk uji"
        epc = _epc_of_roll(roll["id"])
        r = _ingest(STATE["key_out"], [epc])
        assert r.status_code == 200, r.text[:300]
        res = r.json()["results"][0]
        assert res["result"] == "red", res
        assert "AVAILABLE" in res["reason"] and "dokumen keluar" in res["reason"], res
        STATE["avail_epc"] = epc

    def test_07_ingest_committed_so_roll_gate_out_green_with_so_number(self):
        epc = _epc_of_roll("roll_964850514327")
        STATE["so_epc"] = epc
        r = _ingest(STATE["key_out"], [epc])
        assert r.status_code == 200, r.text[:300]
        res = r.json()["results"][0]
        assert res["result"] == "green", res
        assert "KSC/SO-00010" in res["reason"], res

    def test_08_gate_in_pa_destination_green_and_wrong_warehouse_red(self):
        """Setup: satu PA lama dijadikan open + roll-nya ditandai journey.putaway_order_id.
        Nilai asli DIPULIHKAN di akhir test."""
        pa = MDB.putaway_orders.find_one({"to_warehouse_id": "wh_jakarta"}, {"_id": 0})
        if not pa:
            pa = MDB.putaway_orders.find_one({}, {"_id": 0})
        assert pa, "tidak ada putaway order di data demo"
        roll_id = next((i["roll_id"] for i in pa.get("items", []) if i.get("roll_id")), None)
        assert roll_id, "PA tanpa item roll"
        roll = MDB.inventory_rolls.find_one({"id": roll_id}, {"_id": 0, "journey": 1, "rfid_tag_id": 1})
        assert roll.get("rfid_tag_id"), "roll PA belum ber-tag"
        epc = _epc_of_roll(roll_id)
        orig_pa_status = pa.get("status")
        orig_journey = roll.get("journey")
        dest_wh = pa.get("to_warehouse_id")
        try:
            MDB.putaway_orders.update_one({"id": pa["id"]}, {"$set": {"status": "in_transit"}})
            MDB.inventory_rolls.update_one({"id": roll_id}, {"$set": {
                "journey": {**(orig_journey or {}), "putaway_order_id": pa["id"],
                            "stage": "putaway_in_transit"}}})
            key_dest = STATE["key_in_jkt"] if dest_wh == "wh_jakarta" else _key_for_wh(dest_wh)
            r = _ingest(key_dest, [epc])
            assert r.status_code == 200, r.text[:300]
            res = r.json()["results"][0]
            assert res["result"] == "green", res
            assert pa["pa_number"] in res["reason"], res
            # gate IN gudang LAIN → SALAH GUDANG
            other = STATE["key_in_bdg"] if dest_wh != "wh_bandung" else STATE["key_in_jkt"]
            r2 = _ingest(other, [epc])
            res2 = r2.json()["results"][0]
            assert res2["result"] == "red", res2
            assert "SALAH GUDANG" in res2["reason"], res2
        finally:
            MDB.putaway_orders.update_one({"id": pa["id"]}, {"$set": {"status": orig_pa_status}})
            if orig_journey is None:
                MDB.inventory_rolls.update_one({"id": roll_id}, {"$unset": {"journey": ""}})
            else:
                MDB.inventory_rolls.update_one({"id": roll_id}, {"$set": {"journey": orig_journey}})

    def test_09_reads_recorded(self, api):
        r = api.get(f"{BASE}/api/rfid/reads?device_id={GATE_JKT_OUT}&limit=50", timeout=60)
        assert r.status_code == 200, r.text[:300]
        reads = r.json()["reads"]
        epcs = {x.get("epc") for x in reads}
        assert STATE["bogus_epc"] in epcs, "EPC bogus tidak tercatat di rfid_reads"
        assert STATE["so_epc"] in epcs, "EPC SO tidak tercatat di rfid_reads"
        by_epc = {x["epc"]: x for x in reads}
        assert by_epc[STATE["so_epc"]]["result"] == "green"
        assert by_epc[STATE["bogus_epc"]]["result"] == "red"
        assert by_epc[STATE["so_epc"]]["read_type"] == "gate_out"


def _admin_session() -> requests.Session:
    s = requests.Session()
    r = s.post(f"{BASE}/api/auth/login",
               json={"email": "admin@kainnusantara.id", "password": "demo12345"}, timeout=60)
    s.headers.update({"Authorization": f"Bearer {r.json()['token']}", "X-Entity-Id": ENT})
    return s


def _key_for_wh(wh_id: str) -> str:
    """Key gate-in gudang tujuan; bila gudang itu belum punya gate-in, buat device TEST
    sementara (dihapus di cleanup)."""
    s = _admin_session()
    dev = MDB.rfid_devices.find_one({"warehouse_id": wh_id, "type": "gate", "direction": "in"},
                                    {"_id": 0, "id": 1})
    if not dev:
        r = s.post(f"{BASE}/api/rfid/devices", json={
            "code": f"TEST-GATE-IN-{int(time.time())}", "name": "TEST Gate In",
            "type": "gate", "direction": "in", "warehouse_id": wh_id,
            "location": "TEST"}, timeout=60)
        assert r.status_code == 200, f"buat gate-in gagal: {r.status_code} {r.text[:200]}"
        dev = {"id": r.json()["id"]}
        STATE.setdefault("temp_devices", []).append(dev["id"])
    return _key(s, dev["id"])


# ══════════════════════ R3 — PRINTER PULL (ZPL) ══════════════════════
class TestR3Printer:

    def test_01_create_print_job_and_printer_device(self, api):
        rolls = api.get(f"{BASE}/api/rfid/untagged-rolls", timeout=60).json()["rolls"]
        if not rolls:
            # self-seeding: retire 1 tag aktif agar ada kandidat
            tag = MDB.rfid_tags.find_one({"status": "active"}, {"_id": 0, "id": 1})
            assert tag, "tidak ada tag untuk di-retire"
            api.delete(f"{BASE}/api/rfid/tags/{tag['id']}", timeout=60)
            rolls = api.get(f"{BASE}/api/rfid/untagged-rolls", timeout=60).json()["rolls"]
        assert rolls, "tidak ada roll untagged untuk membuat print job"
        wh = rolls[0]["warehouse_id"]
        picked = [r["id"] for r in rolls if r["warehouse_id"] == wh][:2]
        r = api.post(f"{BASE}/api/rfid/print-jobs", json={"roll_ids": picked}, timeout=60)
        assert r.status_code == 200, r.text[:300]
        job = r.json()
        assert job["status"] == "queued", job
        STATE["job_id"] = job["id"]
        STATE["job_wh"] = job.get("warehouse_id") or wh

        r = api.post(f"{BASE}/api/rfid/devices", json={
            "code": f"TEST-PRN-{int(time.time())}", "name": "TEST Printer RFID",
            "type": "printer", "warehouse_id": STATE["job_wh"], "location": "Ruang Cetak"}, timeout=60)
        assert r.status_code == 200, f"buat device printer gagal: {r.status_code} {r.text[:300]}"
        STATE["printer_id"] = r.json()["id"]
        STATE["printer_key"] = _key(api, STATE["printer_id"])

        other_wh = next(w for w in ["wh_bandung", "wh_jakarta", "wh_surabaya"] if w != STATE["job_wh"])
        r = api.post(f"{BASE}/api/rfid/devices", json={
            "code": f"TEST-PRN2-{int(time.time())}", "name": "TEST Printer Lain",
            "type": "printer", "warehouse_id": other_wh, "location": "Lain"}, timeout=60)
        assert r.status_code == 200, r.text[:300]
        STATE["printer2_id"] = r.json()["id"]
        STATE["printer2_key"] = _key(api, STATE["printer2_id"])

    def test_02_pending_jobs_contains_zpl(self):
        r = requests.get(f"{BASE}/api/rfid/device-jobs/pending",
                         headers={"X-Device-Key": STATE["printer_key"]}, timeout=60)
        assert r.status_code == 200, r.text[:300]
        jobs = r.json()["jobs"]
        ids = [j["id"] for j in jobs]
        assert STATE["job_id"] in ids, f"job {STATE['job_id']} tidak muncul di antrean printer: {ids}"
        job = next(j for j in jobs if j["id"] == STATE["job_id"])
        zpls = [i.get("zpl", "") for i in job.get("items", [])]
        assert zpls and all(z.startswith("^XA") for z in zpls), zpls[:1]
        assert any("^RFW" in z for z in zpls), "ZPL tanpa perintah encode RFID ^RFW"

    def test_03_printer_lain_tidak_melihat_job(self):
        r = requests.get(f"{BASE}/api/rfid/device-jobs/pending",
                         headers={"X-Device-Key": STATE["printer2_key"]}, timeout=60)
        assert r.status_code == 200, r.text[:300]
        assert STATE["job_id"] not in [j["id"] for j in r.json()["jobs"]]

    def test_04_ack_403_dari_printer_gudang_lain(self):
        r = requests.post(f"{BASE}/api/rfid/device-jobs/{STATE['job_id']}/ack",
                          headers={"X-Device-Key": STATE["printer2_key"]}, timeout=60)
        assert r.status_code == 403, f"harus 403, dapat {r.status_code} {r.text[:200]}"

    def test_05_ack_printed(self, api):
        r = requests.post(f"{BASE}/api/rfid/device-jobs/{STATE['job_id']}/ack",
                          headers={"X-Device-Key": STATE["printer_key"]}, timeout=60)
        assert r.status_code == 200, r.text[:300]
        assert r.json()["status"] == "printed"
        job = api.get(f"{BASE}/api/rfid/print-jobs/{STATE['job_id']}", timeout=60).json()
        assert job["status"] == "printed", job.get("status")
        assert job.get("printed_by_device") == STATE["printer_id"]

    def test_06_guard_tipe_device(self):
        # printer tidak boleh kirim EPC
        r = _ingest(STATE["printer_key"], ["E2AA"])
        assert r.status_code == 400, r.text[:200]
        # gate tidak boleh menarik antrean printer
        r = requests.get(f"{BASE}/api/rfid/device-jobs/pending",
                         headers={"X-Device-Key": STATE["key_out"]}, timeout=60)
        assert r.status_code == 400, r.text[:200]
        r = requests.post(f"{BASE}/api/rfid/device-jobs/rprj_bogus/ack",
                          headers={"X-Device-Key": STATE["printer_key"]}, timeout=60)
        assert r.status_code == 404, r.text[:200]

    def test_99_cleanup_devices(self, api):
        for k in ("printer_id", "printer2_id"):
            if STATE.get(k):
                api.delete(f"{BASE}/api/rfid/devices/{STATE[k]}", timeout=60)
        for did in STATE.get("temp_devices", []):
            api.delete(f"{BASE}/api/rfid/devices/{did}", timeout=60)


# ══════════════════════ R4 — FINAL LOADING CHECK ══════════════════════
EXP_ST = ["reserved", "committed", "picked", "packed", "allocated"]


def _resolve_lc_target() -> dict:
    """Pilih task outbound yang masih bisa di-dispatch DAN SO-nya punya roll ber-tag
    (self-seeding agar suite bisa dijalankan ulang; SO KSC/SO-00010 diprioritaskan)."""
    def tagged(order_id, statuses=None):
        return MDB.inventory_rolls.count_documents({
            "reserved_ref.type": "sales_order", "reserved_ref.id": order_id,
            "status": {"$in": statuses or EXP_ST}, "rfid_tag_id": {"$nin": [None, ""]},
            "length_remaining": {"$gt": 0}})
    prio = MDB.wms_tasks.find_one({"id": TASK_ID, "status": {"$nin": ["dispatched", "cancelled"]}},
                                  {"_id": 0})
    cands = [prio] if (prio and tagged(prio["order_id"])) else []
    if not cands:
        fallback = None
        for t in MDB.wms_tasks.find({"flow_type": "outbound",
                                     "status": {"$nin": ["dispatched", "cancelled"]}}, {"_id": 0}):
            if not tagged(t.get("order_id", "")):
                continue
            # utamakan SO yang punya roll COMMITTED (satu-satunya yang bisa benar-benar
            # dikirim oleh ship_order_rolls) agar test_06 tidak tersandung data demo.
            if tagged(t["order_id"], ["committed", "picked", "packed"]):
                cands.append(t)
                break
            fallback = fallback or t
        if not cands and fallback:
            cands.append(fallback)
    if not cands:
        pytest.skip("tidak ada task outbound + roll ber-tag untuk uji loading check")
    return cands[0]


class TestR4LoadingCheck:

    def test_00_resolve_target(self, api):
        t = _resolve_lc_target()
        STATE["lc_task"] = t["id"]
        STATE["lc_so"] = t["order_id"]
        r = api.get(f"{BASE}/api/outbound/so/{t['order_id']}/loading-check", timeout=60)
        assert r.status_code == 200, r.text[:300]
        STATE["lc_initial"] = r.json()

    def test_01_dispatch_diblokir_bila_hasil_terakhir_tidak_bersih(self, api):
        lc = (STATE.get("lc_initial") or {}).get("last_result")
        if not lc or lc.get("result") == "clean":
            pytest.skip("hasil terakhir bersih/kosong — blokir diuji di test_04")
        r = api.post(f"{BASE}/api/outbound/tasks/{STATE['lc_task']}/dispatch", timeout=60)
        assert r.status_code == 400, f"harus 400, dapat {r.status_code} {r.text[:300]}"
        assert "Loading Check" in r.json()["detail"], r.json()

    def test_02_start_session(self, api):
        r = api.post(f"{BASE}/api/outbound/so/{STATE['lc_so']}/loading-check/start", timeout=60)
        assert r.status_code == 200, r.text[:300]
        sess = r.json()
        assert sess["status"] == "open" and sess["kind"] == "loading_check"
        assert sess["expected"], "expected EPC kosong"
        STATE["sess_id"] = sess["id"]
        # start ulang = idempotent (sesi yang sama)
        again = api.post(f"{BASE}/api/outbound/so/{STATE['lc_so']}/loading-check/start", timeout=60)
        assert again.status_code == 200 and again.json()["id"] == sess["id"]

    def test_03_dispatch_diblokir_sesi_terbuka(self, api):
        r = api.post(f"{BASE}/api/outbound/tasks/{STATE['lc_task']}/dispatch", timeout=60)
        assert r.status_code == 400, r.text[:300]
        assert "BERJALAN" in r.json()["detail"], r.json()

    def test_04_complete_tanpa_scan_with_issues_dan_dispatch_diblokir(self, api):
        r = api.post(f"{BASE}/api/outbound/loading-check/{STATE['sess_id']}/complete", timeout=60)
        assert r.status_code == 200, r.text[:300]
        sess = r.json()
        assert sess["result"] == "with_issues", sess
        assert sess["missing"], "missing harus terisi"
        d = api.post(f"{BASE}/api/outbound/tasks/{STATE['lc_task']}/dispatch", timeout=60)
        assert d.status_code == 400, d.text[:300]
        assert "TIDAK BERSIH" in d.json()["detail"], d.json()
        r2 = api.post(f"{BASE}/api/outbound/loading-check/{STATE['sess_id']}/complete", timeout=60)
        assert r2.status_code == 400, r2.text[:200]

    def test_05_ulangi_scan_semua_menjadi_clean(self, api):
        r = api.post(f"{BASE}/api/outbound/so/{STATE['lc_so']}/loading-check/start", timeout=60)
        assert r.status_code == 200, r.text[:300]
        sess_id = r.json()["id"]
        epcs = [e["epc"] for e in r.json()["expected"]]
        s = api.post(f"{BASE}/api/outbound/loading-check/{sess_id}/scan",
                     json={"epcs": epcs}, timeout=60)
        assert s.status_code == 200, s.text[:300]
        assert not s.json()["missing"], s.json()
        c = api.post(f"{BASE}/api/outbound/loading-check/{sess_id}/complete", timeout=60)
        assert c.status_code == 200, c.text[:300]
        assert c.json()["result"] == "clean", c.json()
        st = api.get(f"{BASE}/api/outbound/so/{STATE['lc_so']}/loading-check", timeout=60).json()
        assert st["open_session"] is None
        assert st["last_result"]["result"] == "clean", st["last_result"]

    def test_06_dispatch_berhasil_setelah_clean(self, api):
        tid = STATE["lc_task"]
        task = MDB.wms_tasks.find_one({"id": tid}, {"_id": 0})
        qty = float(task.get("quantity", 0) or 0)
        picked = float(task.get("picked_qty", 0) or 0)
        shipped = float(task.get("shipped_qty", 0) or 0)
        if task.get("status") == "scheduled":
            api.post(f"{BASE}/api/outbound/tasks/{tid}/release", timeout=60)
        if picked - shipped <= 0:
            pick_qty = min(1.0, qty - picked) or 1.0
            p = api.post(f"{BASE}/api/outbound/tasks/{tid}/scan-pick",
                         params={"actual_qty": pick_qty}, timeout=60)
            assert p.status_code == 200, f"scan-pick gagal: {p.status_code} {p.text[:300]}"
        d = api.post(f"{BASE}/api/outbound/tasks/{tid}/dispatch", timeout=60)
        if d.status_code == 409 and "Roll commit" in d.text:
            pytest.skip("gerbang loading check TERBUKA (bukan 400 Loading Check) tetapi SO ini "
                        "tidak punya roll committed di data demo — batas SSOT lain, bukan R4: "
                        + d.text[:160])
        assert d.status_code == 200, f"dispatch harus berhasil: {d.status_code} {d.text[:400]}"
        body = d.json()
        assert body["shipment"]["shipment_no"], body
        assert body["shipment"]["qty"] > 0
        STATE["shipment_no"] = body["shipment"]["shipment_no"]

    def test_07_start_untuk_so_bogus_404(self, api):
        r = api.post(f"{BASE}/api/outbound/so/so_bogus999/loading-check/start", timeout=60)
        assert r.status_code == 404, r.text[:200]


# ══════════════════════ JEJAK BARANG — journey timeline ══════════════════════
class TestJourneyTimeline:

    def test_01_roll_so_timeline(self, api):
        r = api.get(f"{BASE}/api/inventory/rolls/roll_964850514327/journey-timeline", timeout=60)
        assert r.status_code == 200, r.text[:300]
        b = r.json()
        assert b["roll"]["roll_no"] and b["roll"]["epc"]
        assert "journey_stage_label" in b["roll"] and "routing" in b["roll"]
        ev = b["events"]
        assert len(ev) >= 3, ev
        ats = [e["at"] for e in ev]
        assert ats == sorted(ats), "events tidak terurut naik"
        kinds = {e["kind"] for e in ev}
        assert "tag" in kinds and "so" in kinds, kinds
        assert "gate" in kinds, kinds
        assert any("KSC/SO-00010" in (e.get("ref") or "") for e in ev), ev
        assert any(e["kind"] == "loading" for e in ev), "Final Loading Check tidak muncul di timeline"

    def test_02_roll_putaway_timeline(self, api):
        pa = MDB.putaway_orders.find_one({"status": {"$in": ["completed", "confirmed", "closed"]}},
                                         {"_id": 0, "items": 1, "pa_number": 1}) \
            or MDB.putaway_orders.find_one({}, {"_id": 0, "items": 1, "pa_number": 1})
        assert pa, "tidak ada PA"
        roll_id = next(i["roll_id"] for i in pa["items"] if i.get("roll_id"))
        r = api.get(f"{BASE}/api/inventory/rolls/{roll_id}/journey-timeline", timeout=60)
        assert r.status_code == 200, r.text[:300]
        ev = r.json()["events"]
        kinds = {e["kind"] for e in ev}
        assert "putaway" in kinds, kinds
        assert any(pa["pa_number"] in (e.get("ref") or "") for e in ev), ev

    def test_03_roll_bogus_404(self, api):
        r = api.get(f"{BASE}/api/inventory/rolls/roll_bogus999/journey-timeline", timeout=60)
        assert r.status_code == 404, r.text[:200]

    def test_04_roll_entitas_lain_403(self, api):
        other = MDB.inventory_rolls.find_one({"owner_entity_id": {"$nin": [ENT, None]}},
                                             {"_id": 0, "id": 1})
        if not other:
            pytest.skip("tidak ada roll entitas lain")
        r = api.get(f"{BASE}/api/inventory/rolls/{other['id']}/journey-timeline", timeout=60)
        assert r.status_code == 403, f"harus 403, dapat {r.status_code}"


# ══════════════════════ R5 — ROLL RETUR MASUK PIPELINE ══════════════════════
class TestR5ReturnPipeline:

    def test_01_buat_retur_dan_settle(self, api):
        so = MDB.sales_orders.find_one(
            {"entity_id": ENT, "status": {"$in": ["shipped", "done", "partially_shipped"]},
             "items.0": {"$exists": True}}, {"_id": 0, "id": 1, "number": 1, "items": 1})
        assert so, "tidak ada SO terkirim untuk membuat retur"
        item = so["items"][0]
        payload = {"order_id": so["id"], "return_type": "retur", "entity_id": ENT,
                   "notes": "TEST_R5 retur otomatis (uji pipeline fisik)",
                   "items": [{"product_id": item["product_id"],
                              "product_name": item.get("product_name", ""),
                              "quantity_returned": 1, "unit": item.get("unit", "meter"),
                              "reason": "TEST_R5 cacat", "condition": "damaged"}]}
        r = api.post(f"{BASE}/api/sales-returns", json=payload, timeout=90)
        assert r.status_code == 200, f"buat retur gagal: {r.status_code} {r.text[:400]}"
        rid = r.json()["id"]
        STATE["ret_id"] = rid
        assert api.post(f"{BASE}/api/sales-returns/{rid}/submit", timeout=60).status_code == 200
        a = api.post(f"{BASE}/api/sales-returns/{rid}/approve", json={"notes": "TEST_R5 setuju"}, timeout=60)
        assert a.status_code == 200, a.text[:300]
        assert api.post(f"{BASE}/api/sales-returns/{rid}/inspect/start", timeout=60).status_code == 200
        ins = api.post(f"{BASE}/api/sales-returns/{rid}/inspect/complete", json={
            "inspections": [{"product_id": item["product_id"], "grade": "B",
                             "condition": "damaged", "disposition": "restock",
                             "accepted_qty": 1}], "notes": "TEST_R5 grade B"}, timeout=90)
        assert ins.status_code == 200, ins.text[:400]
        st = api.post(f"{BASE}/api/sales-returns/{rid}/settle", json={
            "outcome": "store_credit", "notes": "TEST_R5 settle"}, timeout=120)
        assert st.status_code == 200, f"settle gagal: {st.status_code} {st.text[:400]}"

    def test_02_roll_retur_ber_journey_received_transit(self):
        rolls = list(MDB.inventory_rolls.find(
            {"return_id": STATE["ret_id"], "origin_type": "return"}, {"_id": 0}))
        assert rolls, "tidak ada roll dibuat dari retur"
        roll = rolls[0]
        j = roll.get("journey") or {}
        assert j.get("stage") == "received_transit", f"journey.stage salah: {j}"
        assert j.get("routing") == "store", f"journey.routing salah: {j}"
        assert roll.get("rfid_tag_id") in (None, ""), "roll retur seharusnya belum ber-tag"
        STATE["ret_roll_id"] = roll["id"]
        STATE["ret_roll_wh"] = roll.get("warehouse_id")
        STATE["ret_roll_grade"] = roll.get("grade")

    def test_03_roll_retur_muncul_di_untagged_rolls(self, api):
        r = api.get(f"{BASE}/api/rfid/untagged-rolls", timeout=60)
        assert r.status_code == 200, r.text[:300]
        ids = [x["id"] for x in r.json()["rolls"]]
        assert STATE["ret_roll_id"] in ids, "roll retur tidak siap cetak tag (tidak di untagged-rolls)"

    def test_04_print_tag_baru_dan_verifikasi(self, api):
        j = api.post(f"{BASE}/api/rfid/print-jobs",
                     json={"roll_ids": [STATE["ret_roll_id"]]}, timeout=60)
        assert j.status_code == 200, j.text[:300]
        job = j.json()
        assert api.post(f"{BASE}/api/rfid/print-jobs/{job['id']}/mark-printed",
                        timeout=60).status_code == 200
        v = api.post(f"{BASE}/api/rfid/print-jobs/{job['id']}/verify/start", timeout=60)
        assert v.status_code == 200, v.text[:300]
        sess = v.json()
        epcs = [e["epc"] for e in sess["expected"]]
        s = api.post(f"{BASE}/api/rfid/verify-sessions/{sess['id']}/scan",
                     json={"epcs": epcs}, timeout=60)
        assert s.status_code == 200, s.text[:300]
        c = api.post(f"{BASE}/api/rfid/verify-sessions/{sess['id']}/complete", timeout=60)
        assert c.status_code == 200, c.text[:300]
        assert c.json()["result"] == "clean", c.json()
        roll = MDB.inventory_rolls.find_one({"id": STATE["ret_roll_id"]}, {"_id": 0, "journey": 1})
        assert (roll.get("journey") or {}).get("stage") == "tag_verified", roll.get("journey")

    def test_05_suggest_menyarankan_gedung_retur_untuk_grade_bc(self, api):
        wh = STATE["ret_roll_wh"]
        r = api.get(f"{BASE}/api/putaway-orders/suggest?from_warehouse_id={wh}", timeout=60)
        assert r.status_code == 200, r.text[:300]
        groups = r.json().get("groups") or r.json().get("suggestions") or []
        mine = [g for g in groups
                if any(x.get("id") == STATE["ret_roll_id"] or x.get("roll_id") == STATE["ret_roll_id"]
                       for x in (g.get("rolls") or []))]
        assert mine, f"roll retur tidak muncul di saran putaway (grade {STATE['ret_roll_grade']}); groups={str(groups)[:400]}"
        g = mine[0]
        assert g.get("grade") in ("B", "C", "BS"), f"grade grup: {g.get('grade')}"
        names = [c.get("warehouse_name", "") for c in (g.get("candidates") or [])]
        assert any("Retur" in n for n in names), f"Gedung Retur tidak disarankan: {names}"

    def test_06_timeline_roll_retur(self, api):
        r = api.get(f"{BASE}/api/inventory/rolls/{STATE['ret_roll_id']}/journey-timeline", timeout=60)
        assert r.status_code == 200, r.text[:300]
        b = r.json()
        kinds = {e["kind"] for e in b["events"]}
        assert "acquired" in kinds and "tag" in kinds, kinds
        assert any("RETUR" in e["label"].upper() for e in b["events"]), b["events"]
