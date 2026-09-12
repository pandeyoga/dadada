"""Iteration 40 — SIPRO tests for payment scheme sync, customer profile tabs (Kontrak & Harga,
Unit & Konstruksi), manual complaints, lead assignees + PIC assignment, and quotation options."""
import os
import subprocess
import time
import uuid

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"

CID_CONTRACT = "666796c3-9d90-42bf-ab37-2b6696d86583"
CID_UNIT = "c5149a80-0ab0-4d8d-b1d2-3992163058b2"


def _login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, r.text
    tok = r.json().get("access_token")
    assert tok
    return tok


@pytest.fixture(scope="module")
def super_token():
    return _login("superadmin@sipro.co.id", "Sipro#2026")


@pytest.fixture(scope="module")
def sales_token():
    return _login("sales@sipro.co.id", "Sipro#2026")


@pytest.fixture(scope="module")
def s(super_token):
    ses = requests.Session()
    ses.headers.update({"Authorization": f"Bearer {super_token}"})
    return ses


# --- contract-pricing ---
class TestContractPricing:
    def test_contract_pricing(self, s):
        r = s.get(f"{API}/customers/{CID_CONTRACT}/contract-pricing", timeout=30)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["total"] >= 1
        blk = body["data"][0]
        assert blk["scheme"]["name"] == "Cash Bertahap (3x)"
        assert blk["sync"]["ok"] is True
        assert blk["contract"]["number"].startswith("KTR/")
        assert blk["contract"]["breakdown"]["rows"] if isinstance(blk["contract"]["breakdown"], dict) else True
        # terms present
        assert len(blk["pricing"]["terms"]) == 3
        assert blk["ar"]["total"] is not None


# --- units-construction ---
class TestUnitsConstruction:
    def test_units_construction(self, s):
        r = s.get(f"{API}/customers/{CID_UNIT}/units-construction", timeout=30)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["total"] >= 1
        u = body["data"][0]
        assert u["unit"]["code"] == "A-01"
        assert len(u["items"]) == 20
        assert isinstance(u["photos"], list)
        assert "handover" in u
        assert u["links"]["build"].endswith("tab=build")


# --- complaints manual ---
class TestManualComplaint:
    def test_validation_and_create(self, s):
        subj = f"TEST_manual_{uuid.uuid4().hex[:6]}"
        # empty subject
        r = s.post(f"{API}/complaints", json={
            "customer_id": CID_CONTRACT, "subject": "", "message": "x", "channel": "whatsapp"})
        assert r.status_code in (400, 422)
        # invalid channel
        r = s.post(f"{API}/complaints", json={
            "customer_id": CID_CONTRACT, "subject": "x", "message": "y", "channel": "bogus"})
        assert r.status_code in (400, 422)
        # unknown customer
        r = s.post(f"{API}/complaints", json={
            "customer_id": "not-exist", "subject": "x", "message": "y", "channel": "whatsapp"})
        assert r.status_code == 404
        # create ok
        r = s.post(f"{API}/complaints", json={
            "customer_id": CID_CONTRACT, "subject": subj, "message": "keluhan uji manual",
            "channel": "telepon", "category": "umum", "priority": "medium",
            "notify_customer": True})
        assert r.status_code == 200, r.text
        doc = r.json()["data"]
        assert doc["source"] == "manual"
        assert doc["channel"] == "telepon"
        assert doc["sla_due_at"]
        assert doc["assigned_to"]

        # list should contain it
        r = s.get(f"{API}/complaints", params={"customer_id": CID_CONTRACT, "q": subj}, timeout=30)
        assert r.status_code == 200
        rows = r.json()["data"]
        assert any(x["subject"] == subj for x in rows)

        # task auto-created
        r = s.get(f"{API}/work/tasks", params={"filter": "all", "q": subj}, timeout=30)
        assert r.status_code == 200
        titles = [t.get("title", "") for t in r.json().get("data", [])]
        assert any(subj in t for t in titles), f"No task with subject; got {titles[:5]}"


# --- leads assignees ---
class TestLeadsAssignees:
    def test_superadmin_sees_multiple(self, s):
        r = s.get(f"{API}/leads/assignees", timeout=30)
        assert r.status_code == 200
        rows = r.json().get("data") or r.json()
        # accept both shapes
        if isinstance(rows, dict) and "data" in rows:
            rows = rows["data"]
        emails = [x["value"] for x in rows]
        # should have multiple sales/marketing
        assert len(emails) >= 2, rows
        for x in rows:
            assert "value" in x and "label" in x and "role" in x

    def test_sales_sees_self(self, sales_token):
        r = requests.get(f"{API}/leads/assignees",
                         headers={"Authorization": f"Bearer {sales_token}"}, timeout=30)
        assert r.status_code == 200
        rows = r.json().get("data") or r.json()
        if isinstance(rows, dict) and "data" in rows:
            rows = rows["data"]
        emails = [x["value"] for x in rows]
        assert emails == ["sales@sipro.co.id"], emails


# --- create lead assigned_to sales2 ---
class TestCreateLead:
    def test_create_lead_assigned(self, s):
        phone = "812" + str(int(time.time()))[-8:]
        name = f"TEST Lead {uuid.uuid4().hex[:5]}"
        r = s.post(f"{API}/leads", json={
            "name": name, "phone": phone, "source": "whatsapp",
            "assigned_to": "sales2@sipro.co.id"}, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json().get("data") or r.json()
        assert d.get("assigned_to") == "sales2@sipro.co.id", d


# --- quotations options ---
class TestQuotationsOptions:
    def test_options_have_kind_items(self, s):
        r = s.get(f"{API}/quotations/options", timeout=30)
        assert r.status_code == 200
        body = r.json().get("data") or r.json()
        schemes = body.get("schemes") if isinstance(body, dict) else None
        assert schemes and len(schemes) >= 1
        has_items = False
        for sc in schemes:
            assert "kind" in sc and "kind_label" in sc and "items" in sc
            if sc["items"]:
                has_items = True
        assert has_items, "no scheme with non-empty items"


# --- verify_scheme_sync script ---
class TestSchemeSyncScript:
    @pytest.mark.parametrize("scheme_name", [
        "Standar KPR (DP 20%)",
        "Cash keras (DP 80% + pelunasan)",
    ])
    def test_verify_script(self, scheme_name, s):
        r = subprocess.run(
            ["python3", "/app/scripts/verify_scheme_sync.py", scheme_name],
            capture_output=True, text=True, timeout=120)
        assert r.returncode == 0, f"STDOUT:{r.stdout}\nSTDERR:{r.stderr}"
        out = r.stdout
        # extract created customer id line (script prints json summary usually)
        # try to find customer id from output
        import re
        m = re.search(r"^customer\s+([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})",
                      out, re.M | re.I)
        assert m, f"Could not find customer id in script output:\n{out}"
        cid = m.group(1)
        r2 = s.get(f"{API}/customers/{cid}/contract-pricing", timeout=30)
        assert r2.status_code == 200, r2.text
        blocks = r2.json()["data"]
        assert blocks and blocks[0]["sync"]["ok"] is True, blocks[0]["sync"]
