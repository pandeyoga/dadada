"""Tests for the new /leads/import-template.xlsx and /leads/import-file endpoints.

Covers UI-triggered lead import (super admin + sales scope).
"""
import io
import os
import asyncio
import pytest
import requests
import openpyxl
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import dotenv_values

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
SUPER = ("superadmin@sipro.co.id", "Sipro#2026")
SALES = ("sales@sipro.co.id", "Sipro#2026")

CSV_PATH = "/app/tests/fixtures/leads.csv"
XLSX_PATH = "/app/tests/fixtures/SemuaData_leads.xlsx"

# Unique phone used by the sales-role test only (easy to purge)
SALES_TEST_PHONE = "081277000123"
SALES_TEST_NAME = "TEST_Sales_CSV"


def _login(email, pw):
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": pw}, timeout=30)
    assert r.status_code == 200, r.text
    tok = r.json().get("token") or r.json().get("access_token")
    assert tok
    return {"Authorization": f"Bearer {tok}"}


@pytest.fixture(scope="module")
def super_headers():
    return _login(*SUPER)


@pytest.fixture(scope="module")
def sales_headers():
    return _login(*SALES)


# ------ Template ----------
def test_template_download_ok(super_headers):
    r = requests.get(f"{BASE_URL}/api/leads/import-template.xlsx", headers=super_headers, timeout=30)
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    wb = openpyxl.load_workbook(io.BytesIO(r.content))
    assert "Leads" in wb.sheetnames


# ------ CSV preview + commit (super admin) ----------
def test_csv_preview_then_commit(super_headers):
    with open(CSV_PATH, "rb") as f:
        content = f.read()

    # Dry run
    files = {"file": ("leads.csv", content, "text/csv")}
    r = requests.post(f"{BASE_URL}/api/leads/import-file",
                      files=files, data={"dry_run": "true"},
                      headers=super_headers, timeout=60)
    assert r.status_code == 200, r.text
    d = r.json()["data"]
    assert d["total"] == 2, d
    assert d["insert"] == 1, d
    assert d["error"] == 1, d
    # error row must mention HP
    err_rows = [row for row in d.get("rows", []) if row.get("errors")]
    assert err_rows and any("HP" in " ".join(er["errors"]) or "wajib" in " ".join(er["errors"]).lower()
                            for er in err_rows), err_rows

    # Commit
    files = {"file": ("leads.csv", content, "text/csv")}
    r = requests.post(f"{BASE_URL}/api/leads/import-file",
                      files=files, data={"dry_run": "false"},
                      headers=super_headers, timeout=60)
    assert r.status_code == 200, r.text
    d = r.json()["data"]
    assert d["insert"] == 1, d

    # Verify persistence
    r = requests.get(f"{BASE_URL}/api/leads?q=Tes CSV&limit=10", headers=super_headers, timeout=30)
    assert r.status_code == 200
    items = r.json().get("data") or []
    assert any(i.get("name") == "Tes CSV" for i in items), items


def test_csv_reupload_updates_not_duplicates(super_headers):
    with open(CSV_PATH, "rb") as f:
        content = f.read()
    files = {"file": ("leads.csv", content, "text/csv")}
    r = requests.post(f"{BASE_URL}/api/leads/import-file",
                      files=files, data={"dry_run": "true"},
                      headers=super_headers, timeout=60)
    assert r.status_code == 200, r.text
    d = r.json()["data"]
    assert d["insert"] == 0, d
    assert d["update"] == 1, d


# ------ 77-row XLSX preview only ----------
def test_xlsx_77_rows_preview_only(super_headers):
    with open(XLSX_PATH, "rb") as f:
        content = f.read()
    files = {"file": ("SemuaData_leads.xlsx", content,
                      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    r = requests.post(f"{BASE_URL}/api/leads/import-file",
                      files=files, data={"dry_run": "true"},
                      headers=super_headers, timeout=90)
    assert r.status_code == 200, r.text
    d = r.json()["data"]
    assert d["total"] == 77, d
    assert d["insert"] == 77, d
    assert d["error"] == 0, d


# ------ 400 error handling ----------
def test_bad_extension_returns_400(super_headers):
    files = {"file": ("notes.txt", b"hello", "text/plain")}
    r = requests.post(f"{BASE_URL}/api/leads/import-file",
                      files=files, data={"dry_run": "true"},
                      headers=super_headers, timeout=30)
    assert r.status_code == 400, r.text


def test_missing_columns_returns_400(super_headers):
    # CSV with wrong header
    body = "Other;Column\nfoo;bar\n".encode("utf-8")
    files = {"file": ("wrong.csv", body, "text/csv")}
    r = requests.post(f"{BASE_URL}/api/leads/import-file",
                      files=files, data={"dry_run": "true"},
                      headers=super_headers, timeout=30)
    assert r.status_code == 400, r.text
    detail = r.json().get("detail", "").lower()
    assert "nama" in detail and ("no. hp" in detail or "phone" in detail), detail


# ------ Sales-scoped auto-assign ----------
def test_sales_role_import_auto_assigns_to_self(sales_headers):
    body = f"Nama;No. HP\n{SALES_TEST_NAME};{SALES_TEST_PHONE}\n".encode("utf-8")
    files = {"file": ("sales_lead.csv", body, "text/csv")}
    # Dry run
    r = requests.post(f"{BASE_URL}/api/leads/import-file",
                      files=files, data={"dry_run": "true"},
                      headers=sales_headers, timeout=30)
    assert r.status_code == 200, r.text
    assert r.json()["data"]["insert"] == 1

    # Commit
    files = {"file": ("sales_lead.csv", body, "text/csv")}
    r = requests.post(f"{BASE_URL}/api/leads/import-file",
                      files=files, data={"dry_run": "false"},
                      headers=sales_headers, timeout=30)
    assert r.status_code == 200, r.text
    assert r.json()["data"]["insert"] == 1

    # Sales can see it
    r = requests.get(f"{BASE_URL}/api/leads?q={SALES_TEST_NAME}&limit=10",
                     headers=sales_headers, timeout=30)
    assert r.status_code == 200
    items = r.json().get("data") or []
    match = [i for i in items if i.get("name") == SALES_TEST_NAME]
    assert match, items
    assert match[0].get("assigned_to") == SALES[0], match[0]
    assert (match[0].get("phone") or "").startswith("+62"), match[0]


# ------ Cleanup ----------
def test_zzz_cleanup(super_headers):
    env = dotenv_values("/app/backend/.env")
    mongo_url = env.get("MONGO_URL") or os.environ.get("MONGO_URL")
    db_name = env.get("DB_NAME") or os.environ.get("DB_NAME")

    async def _run():
        cli = AsyncIOMotorClient(mongo_url)
        d = cli[db_name]
        n1 = (await d.leads.delete_many({"name": {"$in": ["Tes CSV", SALES_TEST_NAME]}})).deleted_count
        # by phone too (in case name got normalised)
        n2 = (await d.leads.delete_many({
            "phone": {"$in": ["+6281234567890", "+62" + SALES_TEST_PHONE[1:]]}
        })).deleted_count
        cli.close()
        return n1, n2

    n1, n2 = asyncio.new_event_loop().run_until_complete(_run())
    print(f"cleanup: name={n1} phone={n2}")
