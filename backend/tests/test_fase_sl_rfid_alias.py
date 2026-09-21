"""FASE SL - RFID Auto-Tag + Alias Katalog MD backend tests.

Task uji: wms_8abc6bed9e15 (KSC/PO-00014, CBN-MEGA-PREM, 250 yard).
Prefix uji: TB-.
"""
import os
import re
import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')
ENTITY = 'ent_ksc'
TASK_ID = 'wms_8abc6bed9e15'
PTPL_ID = 'ptpl_ec3683557d1bad0da326'

WH_CRED = ('warehouse@kainnusantara.id', 'demo12345')
ADMIN_CRED = ('admin@kainnusantara.id', 'demo12345')
MD_CRED = ('md@kainnusantara.id', 'demo12345')


def _login(email, password):
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, f"login {email} -> {r.status_code}: {r.text}"
    return r.json()["token"]


def _headers(token):
    return {"Authorization": f"Bearer {token}", "X-Entity-Id": ENTITY,
            "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def wh_headers():
    return _headers(_login(*WH_CRED))


@pytest.fixture(scope="module")
def admin_headers():
    return _headers(_login(*ADMIN_CRED))


@pytest.fixture(scope="module")
def md_headers():
    return _headers(_login(*MD_CRED))


def _get_scanned(wh_headers):
    r = requests.get(f"{BASE_URL}/api/inbound/tasks/{TASK_ID}/scanned-rolls",
                     headers=wh_headers, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()


def _find_by_supplier_roll(rolls_payload, sup_roll_no):
    rolls = rolls_payload if isinstance(rolls_payload, list) else rolls_payload.get("rolls", [])
    for r in rolls:
        if r.get("supplier_roll_no") == sup_roll_no:
            return r
    return None


def _cleanup_prefix(wh_headers, prefix="TB-"):
    payload = _get_scanned(wh_headers)
    rolls = payload if isinstance(payload, list) else payload.get("rolls", [])
    for r in rolls:
        if (r.get("supplier_roll_no") or "").startswith(prefix):
            requests.delete(f"{BASE_URL}/api/inbound/rolls/{r['id']}/scan",
                            headers=wh_headers, timeout=30)


# -------- RFID Auto-Tag --------

class TestRfidAutoTag:

    def test_00_cleanup_before(self, wh_headers):
        _cleanup_prefix(wh_headers, "TB-")

    def test_01_scan_label_auto_encodes_rfid(self, wh_headers):
        raw = "CBN-MEGA-PREM|DL-RF-01|TB-R1|20|4.1|RED"
        r = requests.post(
            f"{BASE_URL}/api/inbound/tasks/{TASK_ID}/scan-label",
            headers=wh_headers, json={"raw": raw}, timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        roll = data.get("roll") or data
        # roll must include rfid_epc non-empty
        assert roll.get("rfid_epc"), f"rfid_epc missing: {roll}"
        assert isinstance(roll["rfid_epc"], str) and len(roll["rfid_epc"]) > 0
        # optional format hint XXXX-XXXX-...
        assert re.search(r"[A-Z0-9]{2,}-[A-Z0-9]{2,}", roll["rfid_epc"]), \
            f"epc format unexpected: {roll['rfid_epc']}"
        assert roll.get("tracking_mode") == "rfid", f"tracking_mode={roll.get('tracking_mode')}"
        assert (roll.get("rfid_tag_id") or "").startswith("rtag_"), \
            f"rfid_tag_id={roll.get('rfid_tag_id')}"
        pytest.tb_r1_id = roll["id"]
        pytest.tb_r1_epc = roll["rfid_epc"]
        pytest.tb_r1_tag_id = roll["rfid_tag_id"]

    def test_02_scanned_rolls_lists_epc_and_product(self, wh_headers):
        payload = _get_scanned(wh_headers)
        rolls = payload if isinstance(payload, list) else payload.get("rolls", [])
        assert len(rolls) > 0
        target = _find_by_supplier_roll(rolls, "TB-R1")
        assert target is not None, "TB-R1 not in scanned rolls"
        assert target.get("rfid_epc"), f"TB-R1 rfid_epc missing: {target}"
        # product_name / sku are top-level in the response payload
        assert payload.get("product_name") == "Batik Mega Mendung Premium", \
            f"product_name={payload.get('product_name')}"
        assert payload.get("sku") == "BTK-MEGA-001", f"sku={payload.get('sku')}"

    def test_03_tag_endpoint_rejects_when_already_tagged(self, wh_headers):
        rid = pytest.tb_r1_id
        # Empty EPC on already-tagged roll -> 400
        r = requests.post(f"{BASE_URL}/api/inbound/rolls/{rid}/tag",
                          headers=wh_headers, json={"epc": ""}, timeout=30)
        assert r.status_code == 400, f"{r.status_code}: {r.text}"
        body = r.json()
        detail = body.get("detail") if isinstance(body, dict) else body
        msg = detail.get("message") if isinstance(detail, dict) else str(detail)
        assert "sudah memiliki tag RFID" in msg or "sudah" in (msg or "").lower(), \
            f"unexpected error: {body}"

    def test_04_rfid_tags_list_contains_roll_tag(self, wh_headers):
        r = requests.get(f"{BASE_URL}/api/rfid/tags", headers=wh_headers, timeout=30)
        assert r.status_code == 200, r.text
        body = r.json()
        tags = body if isinstance(body, list) else (body.get("tags") or body.get("items") or [])
        # Match by tag id (rtag_...) captured during scan; epc must equal roll.rfid_epc
        matching = [t for t in tags if t.get("id") == pytest.tb_r1_tag_id]
        assert matching, f"no tag with id {pytest.tb_r1_tag_id} (got {len(tags)} tags)"
        assert matching[0].get("epc") == pytest.tb_r1_epc, \
            f"epc mismatch: tag={matching[0].get('epc')} roll={pytest.tb_r1_epc}"
        assert matching[0].get("roll_id") == pytest.tb_r1_id, matching[0]

    def test_05_manual_tag_flow_delete_and_reassign(self, wh_headers, admin_headers):
        import time
        rid = pytest.tb_r1_id
        manual_epc = f"ABCD-TEST-{int(time.time())%100000:05d}"
        # POST with custom epc on tagged roll -> 400
        r = requests.post(f"{BASE_URL}/api/inbound/rolls/{rid}/tag",
                          headers=wh_headers, json={"epc": manual_epc}, timeout=30)
        assert r.status_code == 400, r.text

        # DELETE tag (try warehouse first, then admin)
        tag_id = pytest.tb_r1_tag_id
        d = requests.delete(f"{BASE_URL}/api/rfid/tags/{tag_id}",
                            headers=wh_headers, timeout=30)
        if d.status_code in (401, 403):
            d = requests.delete(f"{BASE_URL}/api/rfid/tags/{tag_id}",
                                headers=admin_headers, timeout=30)
        assert d.status_code == 200, f"delete tag: {d.status_code} {d.text}"

        # roll should now have empty rfid_epc
        payload = _get_scanned(wh_headers)
        rolls = payload if isinstance(payload, list) else payload.get("rolls", [])
        target = _find_by_supplier_roll(rolls, "TB-R1")
        assert target is not None
        assert not target.get("rfid_epc"), f"rfid_epc not cleared: {target}"

        # POST manual tag epc
        r2 = requests.post(f"{BASE_URL}/api/inbound/rolls/{rid}/tag",
                           headers=wh_headers, json={"epc": manual_epc}, timeout=30)
        assert r2.status_code == 200, r2.text
        body = r2.json()
        tag = body.get("tag") or body
        assert tag.get("epc") == manual_epc, f"tag epc: {tag}"
        # confirm roll now has same epc
        payload = _get_scanned(wh_headers)
        rolls = payload if isinstance(payload, list) else payload.get("rolls", [])
        target = _find_by_supplier_roll(rolls, "TB-R1")
        assert target.get("rfid_epc") == manual_epc, target

    def test_99_cleanup_after(self, wh_headers):
        rid = getattr(pytest, "tb_r1_id", None)
        if rid:
            d = requests.delete(f"{BASE_URL}/api/inbound/rolls/{rid}/scan",
                                headers=wh_headers, timeout=30)
            assert d.status_code == 200, d.text
        _cleanup_prefix(wh_headers, "TB-")


# -------- Alias Katalog MD --------

class TestSupplierAlias:

    def test_inventory_balances_has_supplier_codes(self, wh_headers):
        r = requests.get(f"{BASE_URL}/api/inventory/balances",
                         headers=wh_headers, timeout=30)
        assert r.status_code == 200, r.text
        body = r.json()
        rows = body if isinstance(body, list) else (body.get("items") or body.get("balances") or body.get("rows") or [])
        assert rows, "no balance rows"
        for row in rows:
            assert "supplier_codes" in row, f"row missing supplier_codes: {row.get('sku')}"
            assert isinstance(row["supplier_codes"], list), row
        # find BTK-MEGA-001
        target = next((r for r in rows if r.get("sku") == "BTK-MEGA-001"), None)
        assert target is not None, "BTK-MEGA-001 not in balances"
        codes = target.get("supplier_codes") or []
        assert codes, f"supplier_codes empty for BTK-MEGA-001: {target}"
        assert codes[0].get("supplier_sku") == "CBN-MEGA-PREM", codes
        assert codes[0].get("supplier_item_name"), codes

    def test_product_template_variants_have_supplier_codes(self, md_headers):
        r = requests.get(f"{BASE_URL}/api/product-templates/{PTPL_ID}",
                         headers=md_headers, timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        variants = data.get("variants") or []
        assert variants, "no variants in ptpl"
        target = next((v for v in variants if v.get("sku") == "BNG-KTN-001"), None)
        assert target is not None, f"BNG-KTN-001 variant missing"
        codes = target.get("supplier_codes") or []
        assert any(c.get("supplier_sku") == "SLW-YARN-30S" for c in codes), \
            f"SLW-YARN-30S not found in supplier_codes: {codes}"
