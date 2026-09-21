"""Iter 49 — Special Order FASE 4 (pengiriman OD otomatis + kartu Meja Admin Sales).

Coverage:
  (A) GET /api/sales-admin/desk desk queues od_acc_pelanggan (SORD-260919-0023)
      & od_kunci_harga (SORD-260919-0024).
  (B) Existing baseline sord_ea3ce1b8387d already at status 'done', KSC/SJ-00005,
      chain.so.status 'done', outbound_task_ids populated.
  (C) Full new flow: create OD labdip → approve → sample decide → customer ACC
      → lock-price(auto_po) → SO auto-born → receive PO (scan-receive+complete
      + optional qc-decision) → OD ready + outbound task 60 → scan-pick+dispatch
      → OD shipped + SJ created → mark-delivered SO → OD done.
  (D) prepare-shipment idempotency and 400 when no SO.
"""
import os
import uuid

import pytest
import requests


def _read_backend_url():
    env = os.environ.get("REACT_APP_BACKEND_URL")
    if env:
        return env
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                return line.split("=", 1)[1].strip()
    return ""


BASE = _read_backend_url().rstrip("/")
ENTITY = "ent_ksc"
SUPPLIER = "sup_343fce6af69e"
CUSTOMER = "cust_textile_medan"
PRICE = 40000
QTY = 60
MARGIN = 20


def _login(email, pwd="demo12345"):
    r = requests.post(f"{BASE}/api/auth/login", json={"email": email, "password": pwd}, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["token"]


def _h(email):
    return {"Authorization": f"Bearer {_login(email)}", "X-Entity-Id": ENTITY}


@pytest.fixture(scope="module")
def admin_h():
    return _h("admin@kainnusantara.id")


@pytest.fixture(scope="module")
def manager_h():
    return _h("manager@kainnusantara.id")


@pytest.fixture(scope="module")
def salesadmin_h():
    return _h("salesadmin@kainnusantara.id")


@pytest.fixture(scope="module")
def warehouse_h():
    return _h("warehouse@kainnusantara.id")


def _tiny_png():
    return bytes.fromhex(
        "89504E470D0A1A0A0000000D49484452000000010000000108060000001F15C489"
        "0000000A49444154789C6300010000000500010D0A2DB40000000049454E44AE426082"
    )


def _get(url, headers):
    r = requests.get(url, headers=headers, timeout=30)
    assert r.status_code == 200, f"GET {url} → {r.status_code} {r.text}"
    return r.json()


# ═══════════════════════════════════════════════════════════════════════════
# (A) Sales Admin Desk queues
# ═══════════════════════════════════════════════════════════════════════════
class TestSalesAdminDesk:
    def test_desk_has_od_queues(self, salesadmin_h):
        data = _get(f"{BASE}/api/sales-admin/desk?entity_id={ENTITY}", salesadmin_h)
        queues = {q["id"]: q for q in data.get("queues") or []}
        assert "od_acc_pelanggan" in queues, list(queues.keys())
        assert "od_kunci_harga" in queues, list(queues.keys())

        acc = queues["od_acc_pelanggan"]
        assert acc["count"] >= 1, acc
        acc_nums = [r.get("number") for r in acc.get("rows") or []]
        assert "SORD-260919-0023" in acc_nums, acc_nums
        row = next(r for r in acc["rows"] if r.get("number") == "SORD-260919-0023")
        assert row.get("ref_type") == "special_order", row

        klh = queues["od_kunci_harga"]
        assert klh["count"] >= 1, klh
        klh_nums = [r.get("number") for r in klh.get("rows") or []]
        assert "SORD-260919-0024" in klh_nums, klh_nums
        row = next(r for r in klh["rows"] if r.get("number") == "SORD-260919-0024")
        assert "kontrak Rp 39" in (row.get("subtitle") or ""), row

    def test_desk_admin_access(self, admin_h):
        data = _get(f"{BASE}/api/sales-admin/desk?entity_id={ENTITY}", admin_h)
        queues = {q["id"]: q for q in data.get("queues") or []}
        assert "od_acc_pelanggan" in queues and "od_kunci_harga" in queues


# ═══════════════════════════════════════════════════════════════════════════
# (B) Baseline verify sord_ea3ce1b8387d is FASE-4 completed
# ═══════════════════════════════════════════════════════════════════════════
class TestBaselineDone:
    def test_baseline_od_done(self, admin_h):
        od = _get(f"{BASE}/api/special-orders/sord_ea3ce1b8387d", admin_h)
        assert od["status"] == "done", od["status"]
        chain = od.get("chain") or {}
        so = chain.get("so") or {}
        assert so.get("status") == "done", so
        shipments = chain.get("shipments") or []
        nums = [s.get("shipment_no") or s.get("number") or s.get("sj_number") or s.get("shipment_number") for s in shipments]
        assert any("SJ-00005" in (n or "") for n in nums), nums
        assert od.get("outbound_task_ids"), od.get("outbound_task_ids")


# ═══════════════════════════════════════════════════════════════════════════
# (C) Full new FASE-4 flow
# ═══════════════════════════════════════════════════════════════════════════
class TestFullPhase4Flow:
    state = {}

    def test_01_create_and_submit(self, admin_h):
        r = requests.post(f"{BASE}/api/special-orders", headers=admin_h, timeout=30, json={
            "customer_id": CUSTOMER,
            "title": f"Uji F4 {uuid.uuid4().hex[:6]}",
            "request_types": ["labdip"],
            "detail_level": "full",
            "spec": {"fabric_type": "woven", "gramasi": 150, "lebar": 150},
            "custom_item": {"description": "Uji F4", "quantity": QTY, "unit": "meter", "target_price": 50000},
            "expected_delivery": "2026-12-30",
            "submit_for_approval": True,
        })
        assert r.status_code == 200, r.text
        od = r.json()
        assert od["status"] == "pending_approval"
        TestFullPhase4Flow.state["oid"] = od["id"]
        TestFullPhase4Flow.state["number"] = od["number"]

    def test_02_manager_approve(self, manager_h):
        oid = TestFullPhase4Flow.state["oid"]
        r = requests.post(f"{BASE}/api/special-orders/{oid}/approve", headers=manager_h,
                          json={"notes": "ok"}, timeout=30)
        assert r.status_code == 200, r.text
        od = _get(f"{BASE}/api/special-orders/{oid}", manager_h)
        assert od["status"] == "confirmed", od["status"]
        assert od.get("sample_ids"), od
        TestFullPhase4Flow.state["sample_id"] = od["sample_ids"][0]

    def test_03_send_upload_submit_assess(self, manager_h):
        sid = TestFullPhase4Flow.state["sample_id"]
        # send
        r = requests.post(f"{BASE}/api/rnd/samples/{sid}/send", headers=manager_h,
                          json={"supplier_ids": [SUPPLIER], "type_codes": ["labdip"]}, timeout=30)
        assert r.status_code == 200, r.text
        smp = _get(f"{BASE}/api/rnd/samples/{sid}", manager_h)
        rounds = smp.get("rounds") or []
        target = next((rr for rr in rounds if rr.get("supplier_id") == SUPPLIER), rounds[0])
        rid = target["id"]
        TestFullPhase4Flow.state["rid"] = rid
        # attach
        files = {"file": ("swatch.png", _tiny_png(), "image/png")}
        r = requests.post(f"{BASE}/api/rnd/samples/{sid}/rounds/{rid}/attachments",
                          headers={"Authorization": manager_h["Authorization"], "X-Entity-Id": ENTITY},
                          files=files, timeout=30)
        assert r.status_code in (200, 201), r.text
        # submit
        r = requests.post(f"{BASE}/api/rnd/samples/{sid}/rounds/{rid}/submit", headers=manager_h,
                          json={"note": "ok",
                                "measurements": {"delta_e": 0.5, "colorfastness_wash": 4, "colorfastness_rub": 4}},
                          timeout=30)
        assert r.status_code == 200, r.text
        # assess
        r = requests.post(f"{BASE}/api/rnd/samples/{sid}/rounds/{rid}/assess", headers=manager_h,
                          json={"result": "acc", "score": 90}, timeout=30)
        assert r.status_code == 200, r.text

    def test_04_decide_by_admin(self, admin_h):
        sid = TestFullPhase4Flow.state["sample_id"]
        sku = f"OD-F4-{uuid.uuid4().hex[:6].upper()}"
        r = requests.post(f"{BASE}/api/rnd/samples/{sid}/decide", headers=admin_h,
                          json={"supplier_id": SUPPLIER, "reason_code": "warna_paling_dekat",
                                "price": PRICE,
                                "supplier_color_name": "F4", "supplier_color_code": "F4",
                                "approve_spec": True, "product_sku": sku, "product_name": "F4"},
                          timeout=30)
        assert r.status_code == 200, r.text
        smp = _get(f"{BASE}/api/rnd/samples/{sid}", admin_h)
        dec = smp.get("decision") or {}
        assert dec.get("product_id"), dec
        TestFullPhase4Flow.state["product_id"] = dec["product_id"]

    def test_05_customer_acc_and_lock_price(self, admin_h):
        oid = TestFullPhase4Flow.state["oid"]
        r = requests.post(f"{BASE}/api/special-orders/{oid}/customer-decision", headers=admin_h,
                          json={"decision": "acc", "note": "ok"}, timeout=30)
        assert r.status_code == 200, r.text
        r = requests.post(f"{BASE}/api/special-orders/{oid}/lock-price", headers=admin_h,
                          json={"margin_pct": MARGIN, "auto_po": True}, timeout=30)
        assert r.status_code == 200, r.text
        pricing = r.json().get("pricing") or {}
        proc = pricing.get("procurement") or {}
        assert proc.get("po_number"), pricing
        assert not pricing.get("procurement_error"), pricing.get("procurement_error")
        TestFullPhase4Flow.state["po_id"] = proc["po_id"]
        # OD MUST have BOTH linked_po_id AND linked_sales_order_id populated (auto SO on lock-price).
        od = _get(f"{BASE}/api/special-orders/{oid}", admin_h)
        assert od.get("linked_po_id"), od
        assert od.get("linked_sales_order_id"), od
        chain_so = (od.get("chain") or {}).get("so") or {}
        assert chain_so.get("status") == "waiting_stock", chain_so
        TestFullPhase4Flow.state["so_id"] = od["linked_sales_order_id"]

    def test_06_receive_po(self, warehouse_h, admin_h):
        po_id = TestFullPhase4Flow.state["po_id"]
        pid = TestFullPhase4Flow.state["product_id"]
        po = _get(f"{BASE}/api/purchase-orders/{po_id}", admin_h)
        # find inbound task from either PO.inbound_tasks or list endpoint
        tids = [t.get("id") or t.get("task_id") for t in (po.get("inbound_tasks") or [])]
        if not tids:
            # fallback: list inbound tasks scoped to entity, filter po_number
            r = requests.get(f"{BASE}/api/inbound/tasks?entity_id={ENTITY}", headers=warehouse_h, timeout=30)
            assert r.status_code == 200, r.text
            body = r.json()
            rows = body.get("items") or body.get("tasks") or body if isinstance(body, list) else []
            tids = [t["id"] for t in rows if t.get("po_id") == po_id or t.get("po_number") == po.get("po_number")]
        assert tids, f"No inbound task for PO {po_id}"
        tid = tids[0]
        TestFullPhase4Flow.state["inbound_tid"] = tid

        r = requests.post(f"{BASE}/api/inbound/tasks/{tid}/scan-receive", headers=warehouse_h,
                          json={"product_id": pid, "actual_qty": QTY,
                                "batch": "B", "lot": "L", "roll_id": "", "bin_id": ""}, timeout=30)
        assert r.status_code == 200, r.text
        r = requests.post(f"{BASE}/api/inbound/tasks/{tid}/complete", headers=warehouse_h,
                          json={}, timeout=30)
        assert r.status_code == 200, f"complete → {r.status_code} {r.text}"
        # If QC pending, decide accept
        tk = _get(f"{BASE}/api/inbound/tasks/{tid}", warehouse_h) if False else None
        # inspect via db-agnostic list
        r = requests.get(f"{BASE}/api/inbound/tasks?entity_id={ENTITY}", headers=warehouse_h, timeout=30)
        body = r.json() if r.status_code == 200 else {}
        rows = body if isinstance(body, list) else body.get("items") or body.get("tasks") or []
        task = next((t for t in rows if t.get("id") == tid), None)
        if task and task.get("status") == "qc_pending":
            r = requests.post(f"{BASE}/api/inbound/tasks/{tid}/qc-decision", headers=warehouse_h,
                              json={"accept_qty": QTY, "reject_qty": 0, "accept_grade": "A", "reason": "ok"},
                              timeout=30)
            assert r.status_code == 200, r.text

    def test_07_od_ready_with_outbound_task(self, admin_h):
        oid = TestFullPhase4Flow.state["oid"]
        od = _get(f"{BASE}/api/special-orders/{oid}", admin_h)
        assert od["status"] == "ready", f"status={od['status']} shipping_error={od.get('shipping_error')}"
        assert not od.get("shipping_error"), od.get("shipping_error")
        outs = (od.get("chain") or {}).get("outbound_tasks") or []
        assert len(outs) == 1, outs
        t = outs[0]
        assert t.get("status") == "created", t
        assert float(t.get("quantity") or t.get("qty") or 0) == float(QTY), t
        chain_so = (od.get("chain") or {}).get("so") or {}
        assert chain_so.get("status") == "confirmed", chain_so
        TestFullPhase4Flow.state["out_tid"] = t["id"]

    def test_08_pick_and_dispatch(self, warehouse_h, admin_h):
        out_tid = TestFullPhase4Flow.state["out_tid"]
        r = requests.post(f"{BASE}/api/outbound/tasks/{out_tid}/scan-pick?actual_qty={QTY}",
                          headers=warehouse_h, json={}, timeout=30)
        assert r.status_code == 200, r.text
        r = requests.post(f"{BASE}/api/outbound/tasks/{out_tid}/dispatch",
                          headers=warehouse_h, json={}, timeout=30)
        assert r.status_code == 200, r.text
        oid = TestFullPhase4Flow.state["oid"]
        od = _get(f"{BASE}/api/special-orders/{oid}", admin_h)
        assert od["status"] == "shipped", od["status"]
        shipments = (od.get("chain") or {}).get("shipments") or []
        assert len(shipments) >= 1, shipments

    def test_09_mark_delivered_so_od_done(self, admin_h):
        so_id = TestFullPhase4Flow.state["so_id"]
        r = requests.post(f"{BASE}/api/sales-orders/{so_id}/mark-delivered",
                          headers=admin_h, json={}, timeout=30)
        assert r.status_code == 200, r.text
        oid = TestFullPhase4Flow.state["oid"]
        od = _get(f"{BASE}/api/special-orders/{oid}", admin_h)
        assert od["status"] == "done", od["status"]

    def test_10_prepare_shipment_idempotent(self, admin_h):
        """Fase 4 idempotency: prepare-shipment on OD already shipped-out — 200, tasks==0."""
        oid = TestFullPhase4Flow.state["oid"]
        r = requests.post(f"{BASE}/api/special-orders/{oid}/prepare-shipment",
                          headers=admin_h, json={}, timeout=30)
        # OD is 'done' now — the underlying SO also 'done' → skipped
        assert r.status_code == 200, r.text
        res = r.json().get("result") or {}
        # Either 'skipped' (SO status done/shipped) or 'tasks': 0 acceptable idempotent behavior
        assert (res.get("skipped") is not None) or (res.get("tasks", 0) == 0), res


# ═══════════════════════════════════════════════════════════════════════════
# (D) prepare-shipment error path — OD without linked SO
# ═══════════════════════════════════════════════════════════════════════════
class TestPrepareShipmentGuard:
    def test_prepare_shipment_400_no_so(self, admin_h):
        # Create a fresh OD (still in draft/pending, no SO yet) → prepare-shipment must 400.
        r = requests.post(f"{BASE}/api/special-orders", headers=admin_h, timeout=30, json={
            "customer_id": CUSTOMER, "title": "Uji F4 no-SO",
            "request_types": ["labdip"], "detail_level": "reference",
            "custom_item": {"description": "x", "quantity": 10, "unit": "meter", "target_price": 30000},
            "expected_delivery": "2026-12-30",
            "submit_for_approval": False,
        })
        assert r.status_code == 200, r.text
        oid = r.json()["id"]
        r = requests.post(f"{BASE}/api/special-orders/{oid}/prepare-shipment",
                          headers=admin_h, json={}, timeout=30)
        assert r.status_code == 400, f"{r.status_code} {r.text}"
        assert "SO hasil OD belum ada" in (r.text or ""), r.text
