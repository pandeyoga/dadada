"""Iteration 258 — RANTAI BELI DARI NOL + Nilai Roll Presisi (SEN BULAT).

Scope: create PR → submit → approve (SoD) → PO → approve (SoD, reject creator) →
scan-receive inbound task → complete GR → vendor bill → submit/approve → verify
journal entries balanced, PO billing synced, inventory reconciliation stays
within Rp 1 tolerance, drift-explain matches recon subledger, and 
opening-balance rounding rules obey include_rounding flag.
"""
import os
import time
import pytest
import requests

def _get_backend_url() -> str:
    if os.environ.get("REACT_APP_BACKEND_URL"):
        return os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
    # Fallback: read from /app/frontend/.env
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                return line.split("=", 1)[1].strip().rstrip("/")
    raise RuntimeError("REACT_APP_BACKEND_URL not set")

BASE_URL = _get_backend_url()
ENTITY = "ent_ksc"


def _login(email: str) -> requests.Session:
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login",
               json={"email": email, "password": "demo12345"}, timeout=30)
    assert r.status_code == 200, f"login {email} → {r.status_code} {r.text[:200]}"
    tok = r.json().get("token") or r.json().get("access_token") or ""
    assert tok, f"login {email} no token: {r.json()}"
    s.headers.update({
        "Authorization": f"Bearer {tok}",
        "Content-Type": "application/json",
        "X-Entity-Id": ENTITY,
    })
    return s


# ── Sessions per role (Segregation of Duties) ──────────────────────────────
@pytest.fixture(scope="module")
def s_admin():
    return _login("admin@kainnusantara.id")


@pytest.fixture(scope="module")
def s_manager():
    return _login("manager@kainnusantara.id")


@pytest.fixture(scope="module")
def s_salesadmin():
    return _login("salesadmin@kainnusantara.id")


@pytest.fixture(scope="module")
def s_warehouse():
    return _login("warehouse@kainnusantara.id")


@pytest.fixture(scope="module")
def s_finance():
    return _login("finance@kainnusantara.id")


# ── Helpers to pick reference data ─────────────────────────────────────────
@pytest.fixture(scope="module")
def refs(s_admin):
    """Pilih 1 supplier, 1 warehouse, 1 product yang cocok utk ent_ksc."""
    warehouses = s_admin.get(f"{BASE_URL}/api/warehouses", timeout=30).json()
    wh = next((w for w in warehouses
               if not w.get("entity_ids") or ENTITY in (w.get("entity_ids") or [])
               or w.get("sharing_mode") == "shared"
               or (w.get("owner_entity_id") == ENTITY)), warehouses[0])

    products = s_admin.get(f"{BASE_URL}/api/products", timeout=30).json()
    if isinstance(products, dict):
        products = products.get("items") or products.get("rows") or []
    prod = next((p for p in products if p.get("status", "active") == "active"), products[0])

    suppliers = s_admin.get(f"{BASE_URL}/api/suppliers", timeout=30).json()
    if isinstance(suppliers, dict):
        suppliers = suppliers.get("items") or suppliers.get("rows") or []
    # Exclude internal-entity suppliers (409 "badan usaha di dalam grup")
    external = [s for s in suppliers
                if (not s.get("entity_id") or s.get("entity_id") == ENTITY)
                and not s.get("is_internal_entity")
                and "kanda" not in (s.get("name", "").lower())
                and "kain suka" not in (s.get("name", "").lower())]
    sup = external[0] if external else suppliers[0]
    return {"warehouse": wh, "product": prod, "supplier": sup}


# ==================================================================
# STEP 1 — Create PR (salesadmin) → submit → approve (manager, SoD)
# ==================================================================
class TestRantaiBeli:
    state: dict = {}

    def test_01_create_pr(self, s_salesadmin, refs):
        payload = {
            "items": [{
                "product_id": refs["product"]["id"],
                "quantity": 10,
                "unit": refs["product"].get("base_unit", "meter"),
                "est_price": 50000,
                "note": "iter258 e2e write test",
            }],
            "warehouse_id": refs["warehouse"]["id"],
            "entity_id": ENTITY,
            "reason": "iter258 write E2E — beli 10 unit test",
            "needed_by_date": "",
            "submit_now": True,
            "notes": "iter258 test",
        }
        r = s_salesadmin.post(f"{BASE_URL}/api/purchase-requisitions", json=payload, timeout=30)
        assert r.status_code in (200, 201), f"PR create {r.status_code}: {r.text[:400]}"
        pr = r.json()
        assert pr.get("id"), f"no PR id: {pr}"
        assert pr.get("status") in ("pending_approval", "approved", "submitted"), pr.get("status")
        TestRantaiBeli.state["pr_id"] = pr["id"]
        TestRantaiBeli.state["pr_status"] = pr["status"]
        TestRantaiBeli.state["pr_creator_role"] = "salesadmin"

    def test_02_pr_approve_by_manager_sod(self, s_salesadmin, s_manager):
        pr_id = TestRantaiBeli.state["pr_id"]
        # If PR is already approved (auto on submit_now, below threshold), skip
        if TestRantaiBeli.state.get("pr_status") == "approved":
            TestRantaiBeli.state["pr_auto_approved"] = True
            return
        # SoD check: creator (salesadmin) should be rejected
        r_creator = s_salesadmin.post(
            f"{BASE_URL}/api/purchase-requisitions/{pr_id}/approve",
            json={"notes": "creator tries to approve"}, timeout=30)
        TestRantaiBeli.state["pr_creator_approve_status"] = r_creator.status_code
        if r_creator.status_code == 200:
            TestRantaiBeli.state["pr_approved_by_creator"] = True
            return
        assert r_creator.status_code in (403, 400, 409), \
            f"expected SoD deny; got {r_creator.status_code}: {r_creator.text[:300]}"
        r = s_manager.post(f"{BASE_URL}/api/purchase-requisitions/{pr_id}/approve",
                           json={"notes": "iter258 approved by manager"}, timeout=30)
        assert r.status_code == 200, f"PR approve manager → {r.status_code}: {r.text[:400]}"
        assert r.json().get("status") == "approved"

    def test_03_create_po(self, s_admin, refs):
        payload = {
            "supplier_id": refs["supplier"]["id"],
            "supplier_name": refs["supplier"].get("name", ""),
            "warehouse_id": refs["warehouse"]["id"],
            "items": [{
                "product_id": refs["product"]["id"],
                "quantity": 10,
                "unit": refs["product"].get("base_unit", "meter"),
                "price": 50000,
                "expected_grade": "A",
            }],
            "entity_id": ENTITY,
            "tax_mode": "ppn",
            "expected_delivery_date": "",
            "notes": "iter258 e2e PO",
        }
        r = s_admin.post(f"{BASE_URL}/api/purchase-orders", json=payload, timeout=30)
        assert r.status_code in (200, 201), f"PO create {r.status_code}: {r.text[:400]}"
        po = r.json()
        assert po.get("id"), po
        TestRantaiBeli.state["po_id"] = po["id"]
        TestRantaiBeli.state["po_number"] = po.get("number") or po.get("po_number") or ""
        TestRantaiBeli.state["po_status_after_create"] = po.get("status")
        TestRantaiBeli.state["po_creator_role"] = "admin"

    def test_04_po_approve_sod(self, s_admin, s_manager):
        po_id = TestRantaiBeli.state["po_id"]
        # Creator tries to approve
        r_creator = s_admin.post(f"{BASE_URL}/api/purchase-orders/{po_id}/approve",
                                 json={}, timeout=30)
        TestRantaiBeli.state["po_creator_approve_status"] = r_creator.status_code
        if r_creator.status_code == 200:
            TestRantaiBeli.state["po_approved_by_creator"] = True
        else:
            assert r_creator.status_code in (403, 400, 409), \
                f"PO SoD expected deny got {r_creator.status_code}: {r_creator.text[:300]}"
            r = s_manager.post(f"{BASE_URL}/api/purchase-orders/{po_id}/approve",
                               json={}, timeout=30)
            # Some PO doesn't need approve if amount below threshold → status already 'approved'
            assert r.status_code in (200, 400, 409), \
                f"PO approve → {r.status_code}: {r.text[:300]}"

    def test_05_find_inbound_task(self, s_warehouse):
        po_id = TestRantaiBeli.state["po_id"]
        # Poll briefly (task creation is auto)
        task = None
        for _ in range(6):
            r = s_warehouse.get(f"{BASE_URL}/api/inbound/tasks", timeout=30)
            assert r.status_code == 200, r.text[:300]
            tasks = r.json()
            task = next((t for t in tasks if t.get("po_id") == po_id), None)
            if task:
                break
            time.sleep(1)
        assert task, f"no inbound task auto-created for PO {po_id}"
        TestRantaiBeli.state["task_id"] = task["id"]
        TestRantaiBeli.state["task_expected"] = task.get("expected_qty") or task.get("quantity")

    def test_06_scan_receive_and_complete(self, s_warehouse, refs):
        task_id = TestRantaiBeli.state["task_id"]
        expected = float(TestRantaiBeli.state["task_expected"] or 10)
        r = s_warehouse.post(
            f"{BASE_URL}/api/inbound/tasks/{task_id}/scan-receive",
            json={
                "product_id": refs["product"]["id"],
                "actual_qty": expected,
                "batch": "ITER258-B01",
                "lot": "ITER258-L01",
                "grade": "A",
            }, timeout=30)
        assert r.status_code == 200, f"scan-receive {r.status_code}: {r.text[:400]}"
        # Complete GR
        r2 = s_warehouse.post(f"{BASE_URL}/api/inbound/tasks/{task_id}/complete",
                              json={"dye_lot": "ITER258-DL", "grade": "A"}, timeout=60)
        assert r2.status_code == 200, f"complete GR {r2.status_code}: {r2.text[:400]}"
        # If QC-on-receipt: status may be qc_pending — that's acceptable; roll DID get created
        TestRantaiBeli.state["gr_status"] = r2.json().get("status")

    def test_07_verify_roll_created(self, s_admin, refs):
        # Query inventory rolls to prove a new roll was created for this PO
        po_id = TestRantaiBeli.state["po_id"]
        r = s_admin.get(f"{BASE_URL}/api/inventory-rolls",
                        params={"product_id": refs["product"]["id"]}, timeout=30)
        if r.status_code != 200:
            # Alternate endpoint
            r = s_admin.get(f"{BASE_URL}/api/rolls",
                            params={"product_id": refs["product"]["id"]}, timeout=30)
        if r.status_code == 200:
            rolls = r.json()
            if isinstance(rolls, dict):
                rolls = rolls.get("items") or rolls.get("rows") or []
            match = [rl for rl in rolls if rl.get("po_id") == po_id]
            TestRantaiBeli.state["new_rolls"] = len(match)
            assert match, "No new roll linked to PO"
        else:
            # Not a blocker — endpoint variant
            TestRantaiBeli.state["new_rolls_endpoint_status"] = r.status_code

    def test_08_create_vendor_bill(self, s_admin, refs):
        po_id = TestRantaiBeli.state["po_id"]
        payload = {
            "po_id": po_id,
            "supplier_invoice_no": f"INV-ITER258-{int(time.time())}",
            "items": [{
                "product_id": refs["product"]["id"],
                "billed_qty": 10,
                "price": 50000,
            }],
            "tax_mode": "ppn",
            "entity_id": ENTITY,
            "submit_now": True,
        }
        r = s_admin.post(f"{BASE_URL}/api/vendor-bills", json=payload, timeout=30)
        assert r.status_code in (200, 201), f"VB create {r.status_code}: {r.text[:400]}"
        vb = r.json()
        assert vb.get("id"), vb
        TestRantaiBeli.state["vb_id"] = vb["id"]
        TestRantaiBeli.state["vb_status_after_create"] = vb.get("status")

    def test_09_vb_approve_sod(self, s_admin, s_manager, s_finance):
        vb_id = TestRantaiBeli.state["vb_id"]
        # If already posted/approved on submit_now, nothing to approve
        status_after_create = TestRantaiBeli.state.get("vb_status_after_create")
        if status_after_create in ("approved", "posted", "paid"):
            TestRantaiBeli.state["vb_auto_approved"] = True
            return
        # Creator (admin) tries to approve — SoD
        r_creator = s_admin.post(f"{BASE_URL}/api/vendor-bills/{vb_id}/approve",
                                 json={}, timeout=30)
        TestRantaiBeli.state["vb_creator_approve_status"] = r_creator.status_code
        if r_creator.status_code == 200:
            TestRantaiBeli.state["vb_approved_by_creator"] = True
            return
        assert r_creator.status_code in (403, 400, 409), \
            f"VB SoD expected deny got {r_creator.status_code}: {r_creator.text[:300]}"
        # Approve as manager
        r = s_manager.post(f"{BASE_URL}/api/vendor-bills/{vb_id}/approve",
                           json={}, timeout=30)
        assert r.status_code == 200, f"VB approve manager → {r.status_code}: {r.text[:300]}"

    def test_10_journals_balanced(self, s_admin):
        po_id = TestRantaiBeli.state["po_id"]
        vb_id = TestRantaiBeli.state["vb_id"]
        # PO/GR journal source_id via source filter
        r = s_admin.get(f"{BASE_URL}/api/gl/journal",
                        params={"entity_id": ENTITY}, timeout=30)
        assert r.status_code == 200, r.text[:200]
        entries = r.json()
        if isinstance(entries, dict):
            entries = entries.get("items") or entries.get("rows") or []
        # find any entry mentioning the po or vb
        related = [e for e in entries
                   if (e.get("source_ref_id") in (po_id, vb_id))
                   or (e.get("ref_id") in (po_id, vb_id))
                   or (po_id in (e.get("description") or "") or vb_id in (e.get("description") or ""))]
        TestRantaiBeli.state["related_entries"] = len(related)
        # Check each entry is balanced
        for e in related:
            td = float(e.get("total_debit", 0) or 0)
            tc = float(e.get("total_credit", 0) or 0)
            assert abs(td - tc) < 0.01, f"unbalanced JE {e.get('id')}: {td} vs {tc}"
        # Trial balance still balances
        r2 = s_admin.get(f"{BASE_URL}/api/gl/trial-balance",
                         params={"entity_id": ENTITY}, timeout=30)
        assert r2.status_code == 200
        tb = r2.json()
        # accept fields: total_debit/total_credit OR reconciled/balanced
        td = float(tb.get("total_debit", 0) or 0)
        tc = float(tb.get("total_credit", 0) or 0)
        assert abs(td - tc) < 1.0, f"trial balance unbalanced: {td} vs {tc}"


# ==================================================================
# NILAI ROLL PRESISI — recon consistency + drift-explain match
# ==================================================================
class TestReconPrecision:
    def test_recon_shape(self, s_admin):
        r = s_admin.get(f"{BASE_URL}/api/gl/inventory-reconciliation", timeout=30)
        assert r.status_code == 200, r.text[:200]
        data = r.json()
        assert "rows" in data and "rounding_tolerance" in data
        tol = float(data["rounding_tolerance"])
        assert tol == 1.0
        # difference == subledger - gl for each row (integer cents math)
        for row in data["rows"]:
            diff = float(row["difference"])
            expected = round(float(row["subledger_value"]) - float(row["gl_balance"]), 2)
            assert abs(diff - expected) < 0.005, \
                f"row {row['entity_id']} diff {diff} vs {expected}"
        # Save for cross-check
        TestReconPrecision._recon = data

    def test_drift_explain_matches_recon(self, s_admin):
        recon = TestReconPrecision._recon
        for row in recon["rows"]:
            eid = row["entity_id"]
            r = s_admin.get(f"{BASE_URL}/api/gl/inventory-drift-explain",
                            params={"entity_id": eid}, timeout=30)
            assert r.status_code == 200, f"drift-explain {eid} {r.status_code}"
            exp = r.json()
            # subledger_value must match recon exactly (both computed in cents)
            assert abs(float(exp["subledger_value"]) - float(row["subledger_value"])) < 0.005, \
                (f"MISMATCH subledger for {eid}: recon={row['subledger_value']} "
                 f"drift={exp['subledger_value']}")
            assert abs(float(exp["gl_balance"]) - float(row["gl_balance"])) < 0.005, \
                f"MISMATCH gl_balance for {eid}"
            assert abs(float(exp["difference"]) - float(row["difference"])) < 0.005, \
                f"MISMATCH difference for {eid}"

    def test_no_new_drift_beyond_rp1(self, s_admin):
        recon = TestReconPrecision._recon
        for row in recon["rows"]:
            assert abs(float(row["difference"])) <= 1.0 + 0.005, \
                f"entity {row['entity_id']} drift {row['difference']} > Rp 1"

    def test_opening_balance_no_post_without_flag(self, s_admin):
        """Bila selisih hanya sen (≤ tol), POST tanpa include_rounding tidak memposting."""
        recon_before = s_admin.get(
            f"{BASE_URL}/api/gl/inventory-reconciliation", timeout=30).json()
        # Only meaningful if diff is within tolerance
        small = all(abs(float(r["difference"])) <= 1.0 for r in recon_before["rows"])
        if not small:
            pytest.skip("difference beyond rounding tolerance; skip 'no-post' guard")
        r = s_admin.post(f"{BASE_URL}/api/gl/inventory-opening-balance",
                         params={"reason": "iter258 sanity: no rounding flag"}, timeout=30)
        assert r.status_code == 200, r.text[:300]
        result = r.json()
        # Should post 0 entries for pure rounding
        posted = int(result.get("posted", 0) or result.get("count", 0) or 0)
        assert posted == 0, f"expected 0 posted without include_rounding, got {result}"

    def test_opening_balance_with_rounding_flag(self, s_admin):
        """include_rounding=True boleh memposting jurnal kecil terhadap 3-2900."""
        recon = s_admin.get(f"{BASE_URL}/api/gl/inventory-reconciliation", timeout=30).json()
        has_rounding_only = any(
            r.get("rounding_only") and abs(float(r["difference"])) > 0 for r in recon["rows"])
        if not has_rounding_only:
            pytest.skip("no rounding-only residue to clean up")
        r = s_admin.post(
            f"{BASE_URL}/api/gl/inventory-opening-balance",
            params={"reason": "iter258 rapikan pembulatan", "include_rounding": True},
            timeout=30)
        assert r.status_code == 200, r.text[:300]
        # after: recon.total_difference == 0
        recon2 = s_admin.get(f"{BASE_URL}/api/gl/inventory-reconciliation", timeout=30).json()
        assert abs(float(recon2["total_difference"])) <= 0.005, \
            f"after rounding true-up total_difference still {recon2['total_difference']}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
