"""FASE SL - Scan Label Supplier tests.

Backend E2E tests for /api/inbound/tasks/{task}/scan-label and related endpoints,
per review request. Uses task wms_e2e3d9059660 (KSC/PO-00014, prod_batik_mega,
CBN-MEGA-PREM, 250 yard).
"""
import os
import pytest
import requests

def _load_base_url():
    url = os.environ.get("REACT_APP_BACKEND_URL", "").strip()
    if not url:
        try:
            with open("/app/frontend/.env") as f:
                for ln in f:
                    if ln.startswith("REACT_APP_BACKEND_URL="):
                        url = ln.split("=", 1)[1].strip()
                        break
        except Exception:
            pass
    return url.rstrip("/")


BASE_URL = _load_base_url()
ENTITY = "ent_ksc"
TASK = "wms_e2e3d9059660"
WAREHOUSE_LOGIN = {"email": "warehouse@kainnusantara.id", "password": "demo12345"}
ADMIN_LOGIN = {"email": "admin@kainnusantara.id", "password": "demo12345"}


def _login(payload):
    r = requests.post(f"{BASE_URL}/api/auth/login", json=payload, timeout=30)
    assert r.status_code == 200, f"login failed {r.status_code} {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="module")
def wh_headers():
    tok = _login(WAREHOUSE_LOGIN)
    return {"Authorization": f"Bearer {tok}", "X-Entity-Id": ENTITY, "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def admin_headers():
    tok = _login(ADMIN_LOGIN)
    return {"Authorization": f"Bearer {tok}", "X-Entity-Id": ENTITY, "Content-Type": "application/json"}


def _cleanup_task(headers):
    """Delete any existing receiving rolls for the task."""
    r = requests.get(f"{BASE_URL}/api/inbound/tasks/{TASK}/scanned-rolls", headers=headers, timeout=30)
    if r.status_code != 200:
        return
    data = r.json()
    for roll in data.get("rolls", []):
        rid = roll.get("id") or roll.get("_id") or roll.get("roll_id")
        if rid:
            requests.delete(f"{BASE_URL}/api/inbound/rolls/{rid}/scan", headers=headers, timeout=30)


@pytest.fixture(scope="module", autouse=True)
def _pretest_cleanup(wh_headers):
    _cleanup_task(wh_headers)
    yield


# --- Tests ordered as required by scenario (state-dependent) ---

class TestScanLabelFlow:

    def test_01_list_scanned_rolls_initial(self, wh_headers):
        r = requests.get(f"{BASE_URL}/api/inbound/tasks/{TASK}/scanned-rolls", headers=wh_headers, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "rolls" in d and isinstance(d["rolls"], list)
        assert d.get("tolerance_pct") == 2
        assert d.get("label_pattern", {}).get("format") == "auto"
        bins = d.get("bins") or []
        codes = [b.get("code") for b in bins]
        assert "A1-01" in codes, f"A1-01 not found in bins: {codes}"
        assert d.get("supplier_id")
        assert d.get("supplier_name")

    def test_02_scan_json(self, wh_headers):
        raw = '{"sku":"CBN-MEGA-PREM","lot":"DL-TA-01","roll":"TA-R1","yd":120.5,"kg":25.1,"color":"RED-07"}'
        r = requests.post(f"{BASE_URL}/api/inbound/tasks/{TASK}/scan-label",
                          headers=wh_headers, json={"raw": raw}, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        roll = d["roll"]
        assert roll["roll_no"].startswith("RL-")
        assert roll["supplier_roll_no"] == "TA-R1"
        assert roll["supplier_lot"] == "DL-TA-01"
        assert roll["supplier_sku"] == "CBN-MEGA-PREM"
        assert roll["status"] == "receiving"
        assert roll["declared_task_qty"] == 120.5
        assert abs(roll["length_m"] - 110.19) < 0.5
        assert roll["length_yd"] == 120.5
        task = d["task"]
        assert task["received_qty"] == 120.5
        assert task["status"] == "receiving"
        assert task["qty_rolls_scanned"] == 1

    def test_03_scan_delimited(self, wh_headers):
        raw = "CBN-MEGA-PREM|DL-TA-01|TA-R2|100|20.8|RED-07"
        r = requests.post(f"{BASE_URL}/api/inbound/tasks/{TASK}/scan-label",
                          headers=wh_headers, json={"raw": raw}, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["roll"]["declared_task_qty"] == 100
        assert d["task"]["received_qty"] == 220.5

    def test_04_scan_gs1(self, wh_headers):
        raw = "(240)CBN-MEGA-PREM(10)DL-TA-01(21)TA-R3(3230)00000025"
        r = requests.post(f"{BASE_URL}/api/inbound/tasks/{TASK}/scan-label",
                          headers=wh_headers, json={"raw": raw}, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["roll"]["declared_task_qty"] == 25
        assert d["task"]["received_qty"] == 245.5
        assert d["task"]["status"] == "qc_check"

    def test_05_duplicate(self, wh_headers):
        raw = '{"sku":"CBN-MEGA-PREM","lot":"DL-TA-01","roll":"TA-R1","yd":120.5,"kg":25.1,"color":"RED-07"}'
        r = requests.post(f"{BASE_URL}/api/inbound/tasks/{TASK}/scan-label",
                          headers=wh_headers, json={"raw": raw}, timeout=30)
        assert r.status_code == 409, r.text
        d = r.json()
        detail = d.get("detail") or d
        assert isinstance(detail, dict) and detail.get("code") == "DUPLICATE"

    def test_06_unmapped(self, wh_headers):
        r = requests.post(f"{BASE_URL}/api/inbound/tasks/{TASK}/scan-label",
                          headers=wh_headers, json={"raw": "ZZZ-UNKNOWN|DL|R9|100"}, timeout=30)
        assert r.status_code == 400, r.text
        d = r.json().get("detail") or r.json()
        assert d.get("code") == "UNMAPPED"
        assert "tidak ada di PO" in d.get("message", "") or "belum dipetakan" in d.get("message", "")

    def test_07_not_in_task(self, wh_headers):
        r = requests.post(f"{BASE_URL}/api/inbound/tasks/{TASK}/scan-label",
                          headers=wh_headers, json={"raw": "NTT-IKAT-GRD|DL|R9|100"}, timeout=30)
        assert r.status_code == 400, r.text
        d = r.json().get("detail") or r.json()
        assert d.get("code") == "NOT_IN_TASK"

    def test_08_no_roll_no(self, wh_headers):
        r = requests.post(f"{BASE_URL}/api/inbound/tasks/{TASK}/scan-label",
                          headers=wh_headers, json={"raw": '{"sku":"CBN-MEGA-PREM","yd":10}'}, timeout=30)
        assert r.status_code == 400, r.text
        d = r.json().get("detail") or r.json()
        assert d.get("code") == "NO_ROLL_NO"

    def test_09_undecodable(self, wh_headers):
        r = requests.post(f"{BASE_URL}/api/inbound/tasks/{TASK}/scan-label",
                          headers=wh_headers, json={"raw": "abc"}, timeout=30)
        assert r.status_code == 400, r.text
        d = r.json().get("detail") or r.json()
        assert d.get("code") == "UNDECODABLE"

    def test_10_over_po(self, wh_headers):
        r = requests.post(f"{BASE_URL}/api/inbound/tasks/{TASK}/scan-label",
                          headers=wh_headers, json={"raw": "CBN-MEGA-PREM|DL|TA-R99|500"}, timeout=30)
        assert r.status_code == 400, r.text
        d = r.json().get("detail") or r.json()
        assert d.get("code") == "OVER_PO"

    def test_11_manual_fallback(self, wh_headers):
        body = {"manual": {"supplier_roll_no": "TA-M1", "declared_length": 4,
                           "length_unit": "yard", "lot": "DL-TA-01",
                           "reason": "label_damaged", "reason_note": "sobek"}}
        r = requests.post(f"{BASE_URL}/api/inbound/tasks/{TASK}/scan-label",
                          headers=wh_headers, json=body, timeout=30)
        assert r.status_code == 200, r.text
        roll = r.json()["roll"]
        assert roll["manual_override"]["reason"] == "label_damaged"
        assert roll["supplier_sku"] == "CBN-MEGA-PREM"
        assert roll["scan_source"] == "manual"

    def test_12_confirm_measure_variance(self, wh_headers):
        # Find TA-R1 id
        r = requests.get(f"{BASE_URL}/api/inbound/tasks/{TASK}/scanned-rolls", headers=wh_headers, timeout=30)
        rolls = r.json()["rolls"]
        r1 = next(x for x in rolls if x.get("supplier_roll_no") == "TA-R1")
        r1_id = r1.get("id") or r1.get("_id")
        r2 = next(x for x in rolls if x.get("supplier_roll_no") == "TA-R2")
        r2_id = r2.get("id") or r2.get("_id")

        r = requests.post(f"{BASE_URL}/api/inbound/rolls/{r1_id}/confirm-measure",
                          headers=wh_headers, json={"actual_length": 114, "grade": "B"}, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["roll"]["label_variance"]["flagged"] is True
        assert d["roll"]["length_initial"] == 114
        assert d["roll"]["grade"] == "B"
        assert d["roll"]["measure_confirmed"] is True
        assert d["task"]["needs_review"] is True

        r = requests.post(f"{BASE_URL}/api/inbound/rolls/{r2_id}/confirm-measure",
                          headers=wh_headers, json={"actual_length": 100}, timeout=30)
        assert r.status_code == 200, r.text
        assert r.json()["roll"]["label_variance"]["flagged"] is False

    def test_13_putaway(self, wh_headers):
        r = requests.get(f"{BASE_URL}/api/inbound/tasks/{TASK}/scanned-rolls", headers=wh_headers, timeout=30)
        rolls = r.json()["rolls"]
        r1 = next(x for x in rolls if x.get("supplier_roll_no") == "TA-R1")
        r1_id = r1.get("id") or r1.get("_id")

        r = requests.post(f"{BASE_URL}/api/inbound/rolls/{r1_id}/putaway",
                          headers=wh_headers, json={"bin_code": "A1-01"}, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["roll"]["bin_id"] == "bin_jkt_a1_01"
        assert d["roll"]["bin_code"] == "A1-01"

        r = requests.post(f"{BASE_URL}/api/inbound/rolls/{r1_id}/putaway",
                          headers=wh_headers, json={"bin_code": "XX-99"}, timeout=30)
        assert r.status_code == 400, r.text

    def test_14_delete_manual(self, wh_headers):
        r = requests.get(f"{BASE_URL}/api/inbound/tasks/{TASK}/scanned-rolls", headers=wh_headers, timeout=30)
        d = r.json()
        prev_received = None
        prev_count = d.get("count")
        # Get task received
        rt = requests.get(f"{BASE_URL}/api/inbound/tasks/{TASK}", headers=wh_headers, timeout=30)
        if rt.status_code == 200:
            prev_received = rt.json().get("received_qty")
        m1 = next(x for x in d["rolls"] if x.get("supplier_roll_no") == "TA-M1")
        m1_id = m1.get("id") or m1.get("_id")

        r = requests.delete(f"{BASE_URL}/api/inbound/rolls/{m1_id}/scan", headers=wh_headers, timeout=30)
        assert r.status_code == 200, r.text

        r = requests.get(f"{BASE_URL}/api/inbound/tasks/{TASK}/scanned-rolls", headers=wh_headers, timeout=30)
        d2 = r.json()
        assert all(x.get("supplier_roll_no") != "TA-M1" for x in d2["rolls"])
        if prev_received is not None:
            rt2 = requests.get(f"{BASE_URL}/api/inbound/tasks/{TASK}", headers=wh_headers, timeout=30)
            if rt2.status_code == 200:
                assert abs(rt2.json().get("received_qty") - (prev_received - 4)) < 0.001

    def test_15_stats(self, wh_headers):
        r = requests.get(f"{BASE_URL}/api/inbound/scan-label/stats", headers=wh_headers, timeout=30)
        assert r.status_code == 200, r.text
        arr = r.json()
        assert isinstance(arr, list)
        names = [x.get("supplier_name") for x in arr]
        assert any("Cirebon" in (n or "") for n in names), f"Cirebon supplier not present: {names}"

    def test_16_pattern_test_endpoint(self, wh_headers):
        r = requests.post(f"{BASE_URL}/api/suppliers/label-pattern/test",
                          headers=wh_headers,
                          json={"raw": "(240)ABC(10)L1(21)R1(3230)00010000",
                                "pattern": {"format": "gs1"}}, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["ok"] is True
        dec = d["decoded"]
        assert dec["supplier_sku"] == "ABC"
        assert dec["lot"] == "L1"
        assert dec["roll_no"] == "R1"
        assert dec["length"] == 10000

        r = requests.post(f"{BASE_URL}/api/suppliers/label-pattern/test",
                          headers=wh_headers,
                          json={"raw": "abc", "pattern": {"format": "auto"}}, timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert d["ok"] is False
        assert d.get("error")

    def test_17_pattern_get_put_and_scan_meter(self, wh_headers, admin_headers):
        # get supplier id from scanned-rolls
        r = requests.get(f"{BASE_URL}/api/inbound/tasks/{TASK}/scanned-rolls", headers=wh_headers, timeout=30)
        supp_id = r.json().get("supplier_id")
        assert supp_id

        r = requests.get(f"{BASE_URL}/api/suppliers/{supp_id}/label-pattern", headers=wh_headers, timeout=30)
        assert r.status_code == 200, r.text
        assert r.json().get("pattern", {}).get("format") is not None or "format" in r.json()

        new_pat = {"format": "delimited", "delimiter": ";",
                   "fields": ["supplier_sku", "roll_no", "lot", "length"],
                   "length_unit": "meter"}
        r = requests.put(f"{BASE_URL}/api/suppliers/{supp_id}/label-pattern",
                         headers=admin_headers, json=new_pat, timeout=30)
        assert r.status_code == 200, r.text

        r = requests.get(f"{BASE_URL}/api/suppliers/{supp_id}/label-pattern", headers=wh_headers, timeout=30)
        d = r.json()
        pat = d.get("pattern") or d
        assert pat.get("delimiter") == ";"

        r = requests.post(f"{BASE_URL}/api/inbound/tasks/{TASK}/scan-label",
                          headers=wh_headers,
                          json={"raw": "CBN-MEGA-PREM;TA-R5;DL-TA-02;3"}, timeout=30)
        assert r.status_code == 200, r.text
        roll = r.json()["roll"]
        assert roll["length_m"] == 3

        # restore
        restore = {"format": "auto", "delimiter": "|", "length_unit": "yard"}
        r = requests.put(f"{BASE_URL}/api/suppliers/{supp_id}/label-pattern",
                         headers=admin_headers, json=restore, timeout=30)
        assert r.status_code == 200

    def test_18_complete_task(self, wh_headers):
        # Push received_qty above qc_check threshold with a small extra scan.
        rr = requests.post(f"{BASE_URL}/api/inbound/tasks/{TASK}/scan-label",
                           headers=wh_headers,
                           json={"raw": "CBN-MEGA-PREM|DL|TA-R18|4"}, timeout=30)
        # ignore result; status transitions to qc_check when threshold reached
        # Snapshot scan rolls
        r = requests.get(f"{BASE_URL}/api/inbound/tasks/{TASK}/scanned-rolls", headers=wh_headers, timeout=30)
        scanned = r.json()["rolls"]
        scan_roll_nos = set(x.get("roll_no") for x in scanned)

        r = requests.post(f"{BASE_URL}/api/inbound/tasks/{TASK}/complete",
                          headers=wh_headers, json={}, timeout=60)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("status") == "qc_pending"
        created = d.get("created_rolls") or []
        created_nos = set(x.get("roll_no") if isinstance(x, dict) else x for x in created)
        # no new roll numbers introduced
        assert created_nos.issubset(scan_roll_nos) or scan_roll_nos.issubset(created_nos), \
            f"created rolls mismatch: {created_nos} vs {scan_roll_nos}"
        assert "lots" in d
        rv = d.get("receipt_variance") or {}
        note = (rv.get("note") or "").lower()
        assert "selisih label" in note or "label vs aktual" in note or rv

        r = requests.get(f"{BASE_URL}/api/inbound/tasks?status=qc_pending",
                         headers=wh_headers, timeout=30)
        assert r.status_code == 200
        arr = r.json() if isinstance(r.json(), list) else r.json().get("tasks", [])
        ids = [x.get("id") or x.get("task_id") or x.get("_id") for x in arr]
        assert TASK in ids, f"task {TASK} not in qc_pending list"
