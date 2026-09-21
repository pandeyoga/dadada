"""Iter-285 — Customer Feedback (per SO), Ekspor Katalog Benang CSV, Meja Finance queue hutang_jatuh_tempo."""
import os
import pytest
import requests


def _base():
    v = os.environ.get("REACT_APP_BACKEND_URL")
    if not v:
        try:
            with open("/app/frontend/.env") as f:
                for line in f:
                    if line.startswith("REACT_APP_BACKEND_URL="):
                        return line.split("=", 1)[1].strip().rstrip("/")
        except Exception:
            pass
    return (v or "").rstrip("/")


BASE = _base()
ENT = "ent_ksc"


def _login(email, password="demo12345", entity=ENT):
    s = requests.Session()
    r = s.post(f"{BASE}/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, f"login {email}: {r.status_code} {r.text}"
    tok = r.json()["token"]
    s.headers.update({"Authorization": f"Bearer {tok}", "X-Entity-Id": entity, "Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def admin():
    return _login("admin@kainnusantara.id")


@pytest.fixture(scope="module")
def sales():
    return _login("sales@kainnusantara.id")


@pytest.fixture(scope="module")
def warehouse():
    return _login("warehouse@kainnusantara.id")


@pytest.fixture(scope="module")
def finance():
    return _login("finance@kainnusantara.id")


@pytest.fixture(scope="module")
def salesadmin():
    return _login("salesadmin@kainnusantara.id")


@pytest.fixture(scope="module")
def created_ids():
    return {"feedbacks": []}


# ---------------- FEEDBACK BACKEND ----------------

def test_feedback_meta_admin(admin):
    r = admin.get(f"{BASE}/api/customer-feedback/meta")
    assert r.status_code == 200, r.text
    d = r.json()
    assert {"categories", "severities", "statuses"} <= set(d.keys())
    cats = [c["value"] for c in d["categories"]]
    assert "kualitas" in cats and "pengiriman" in cats
    sevs = [s["value"] for s in d["severities"]]
    assert set(sevs) == {"rendah", "sedang", "tinggi"}
    sts = [s["value"] for s in d["statuses"]]
    assert set(sts) == {"open", "in_progress", "resolved", "closed"}


@pytest.fixture(scope="module")
def target_so(admin):
    r = admin.get(f"{BASE}/api/sales-orders", params={"entity_id": ENT})
    assert r.status_code == 200, r.text
    data = r.json()
    if isinstance(data, list):
        items = data
    else:
        items = data.get("items") or data.get("orders") or []
    # pick first SO with entity ent_ksc
    for so in items:
        if so.get("entity_id") == ENT:
            return so
    assert items, "no SOs found"
    return items[0]


def test_feedback_create_with_assignee_becomes_in_progress(admin, target_so, created_ids):
    payload = {
        "order_id": target_so["id"],
        "title": "QA Warna roll ke-2 lebih gelap dari sampel",
        "category": "kualitas",
        "severity": "tinggi",
        "description": "Perbedaan warna terlihat pada roll ke-2 dibanding sampel awal.",
        "assignee_name": "Rina Kartika",
        "due_date": "2026-09-05",
    }
    r = admin.post(f"{BASE}/api/customer-feedback", json=payload)
    assert r.status_code == 200, r.text
    doc = r.json()
    assert doc["status"] == "in_progress"
    assert doc["number"].startswith("KSC/CF-"), doc["number"]
    assert doc["assignee_name"] == "Rina Kartika"
    created_ids["feedbacks"].append(doc["id"])
    created_ids["assignee_fb"] = doc["id"]


def test_feedback_create_without_assignee_open(admin, target_so, created_ids):
    payload = {
        "order_id": target_so["id"],
        "title": "QA Keluhan pengiriman terlambat",
        "category": "pengiriman",
        "severity": "sedang",
        "description": "pengiriman terlambat dua hari",
    }
    r = admin.post(f"{BASE}/api/customer-feedback", json=payload)
    assert r.status_code == 200, r.text
    doc = r.json()
    assert doc["status"] == "open"
    created_ids["feedbacks"].append(doc["id"])
    created_ids["no_assignee_fb"] = doc["id"]


def test_feedback_title_too_short_422(admin, target_so):
    payload = {"order_id": target_so["id"], "title": "abc"}
    r = admin.post(f"{BASE}/api/customer-feedback", json=payload)
    assert r.status_code == 422, r.text


def test_feedback_patch_resolved_without_resolution_400(admin, created_ids):
    fb = created_ids["assignee_fb"]
    r = admin.patch(f"{BASE}/api/customer-feedback/{fb}", json={"status": "resolved"})
    assert r.status_code == 400, r.text


def test_feedback_patch_resolved_with_resolution_ok(admin, created_ids):
    fb = created_ids["assignee_fb"]
    r = admin.patch(f"{BASE}/api/customer-feedback/{fb}",
                    json={"status": "resolved", "resolution": "Roll ulang produksi & QC dobel"})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["status"] == "resolved"
    tl_labels = " ".join((e.get("title") or e.get("label") or e.get("event") or "") for e in d.get("timeline", []))
    # Expect "Ditindak → Selesai" transition entry
    assert "Selesai" in tl_labels or any("Ditindak" in (e.get("title") or e.get("label") or "") and "Selesai" in (e.get("title") or e.get("label") or "") for e in d.get("timeline", []))


def test_feedback_patch_closed_then_open_400(admin, created_ids):
    fb = created_ids["assignee_fb"]
    # resolved -> closed
    r1 = admin.patch(f"{BASE}/api/customer-feedback/{fb}", json={"status": "closed"})
    assert r1.status_code == 200, r1.text
    assert r1.json()["status"] == "closed"
    # closed -> open must be 400 "tidak bisa langsung"
    r2 = admin.patch(f"{BASE}/api/customer-feedback/{fb}", json={"status": "open"})
    assert r2.status_code == 400, r2.text
    assert "tidak bisa langsung" in r2.text.lower() or "closed" in r2.text.lower()


def test_feedback_list_by_order_id(admin, target_so, created_ids):
    r = admin.get(f"{BASE}/api/customer-feedback", params={"order_id": target_so["id"]})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["count"] >= 2
    ids = [it["id"] for it in d["items"]]
    for fb in created_ids["feedbacks"]:
        assert fb in ids


def test_feedback_summary(admin):
    r = admin.get(f"{BASE}/api/customer-feedback/summary")
    assert r.status_code == 200, r.text
    d = r.json()
    assert "total" in d and "open" in d and "resolved" in d
    assert d["total"] >= 2


def test_feedback_sales_can_list_and_create(sales, target_so, created_ids):
    r = sales.get(f"{BASE}/api/customer-feedback", params={"order_id": target_so["id"]})
    assert r.status_code == 200, r.text
    r2 = sales.post(f"{BASE}/api/customer-feedback", json={
        "order_id": target_so["id"], "title": "QA Sales cek komplain",
        "category": "layanan", "severity": "rendah", "description": "test perms sales"
    })
    assert r2.status_code == 200, r2.text
    created_ids["feedbacks"].append(r2.json()["id"])


def test_feedback_warehouse_post_403(warehouse, target_so):
    r = warehouse.post(f"{BASE}/api/customer-feedback", json={
        "order_id": target_so["id"], "title": "QA Warehouse tak boleh",
        "category": "kualitas", "severity": "sedang"
    })
    assert r.status_code == 403, r.text


def test_feedback_entity_scoping(admin):
    """X-Entity-Id ent_kanda tidak melihat feedback ent_ksc."""
    s = requests.Session()
    r = s.post(f"{BASE}/api/auth/login", json={"email": "admin@kainnusantara.id", "password": "demo12345"})
    tok = r.json()["token"]
    s.headers.update({"Authorization": f"Bearer {tok}", "X-Entity-Id": "ent_kanda", "Content-Type": "application/json"})
    r = s.get(f"{BASE}/api/customer-feedback")
    assert r.status_code == 200, r.text
    d = r.json()
    # None of items should be ent_ksc scoped
    for it in d.get("items", []):
        assert it.get("entity_id") != ENT, f"leaked: {it}"


# ---------------- EKSPOR KATALOG BENANG ----------------

def test_export_yarn_admin(admin):
    r = admin.get(f"{BASE}/api/master-data/export-yarn")
    assert r.status_code == 200, r.text
    assert "text/csv" in r.headers.get("content-type", "")
    body = r.text
    header = body.splitlines()[0]
    for col in ["sku", "name", "yarn_count", "yarn_count_system", "yarn_material",
                "yarn_ply", "yarn_twist", "yarn_dye_status",
                "supplier_skus", "supplier_item_names", "supplier_names"]:
        assert col in header, f"missing col {col} in {header}"
    # Baris BNG-KTN-001 punya supplier_skus SLW-YARN-30S
    found = False
    for line in body.splitlines():
        if line.startswith("BNG-KTN-001,") or ",BNG-KTN-001," in line:
            assert "SLW-YARN-30S" in line, line
            found = True
            break
    assert found, "BNG-KTN-001 row not found in export"


def test_export_yarn_sales_403(sales):
    r = sales.get(f"{BASE}/api/master-data/export-yarn")
    assert r.status_code == 403, r.text


# ---------------- MEJA FINANCE — HUTANG JATUH TEMPO ----------------

def test_finance_desk_hutang_jatuh_tempo(finance):
    r = finance.get(f"{BASE}/api/finance/desk", params={"entity_id": ENT})
    assert r.status_code == 200, r.text
    d = r.json()
    queues = {q["id"]: q for q in d.get("queues", [])}
    assert "hutang_jatuh_tempo" in queues, list(queues.keys())
    hq = queues["hutang_jatuh_tempo"]
    assert hq["count"] >= 2, f"expected >=2, got {hq['count']}: {hq}"
    numbers = [row.get("number") for row in hq.get("rows", [])]
    # PO-00001 & PO-00002 expected
    assert any("PO-00001" in (n or "") for n in numbers), numbers
    assert any("PO-00002" in (n or "") for n in numbers), numbers
    # PO-00001 subtitle mentions NET30 & 'lewat'
    for row in hq["rows"]:
        if "PO-00001" in (row.get("number") or ""):
            assert row.get("badge") == "lewat", row
            assert "NET30" in (row.get("subtitle") or ""), row
    assert d["totals"].get("ap_overdue", 0) >= 2, d["totals"]
    # regression: old queues still exist
    for q_id in ("siap_faktur_pajak", "uang_masuk", "jatuh_tempo"):
        assert q_id in queues, f"missing {q_id}"
    # paid/cancelled must not appear
    for row in hq["rows"]:
        assert row.get("badge") in ("lewat", "segera"), row


def test_finance_hutang_excludes_paid_cancelled(admin):
    """Direct DB-style probe: query as admin, then ensure no cancelled/paid PO shows up in queue rows."""
    r = admin.get(f"{BASE}/api/finance/desk", params={"entity_id": ENT})
    if r.status_code != 200:
        pytest.skip("admin cannot access finance desk")
    d = r.json()
    for q in d.get("queues", []):
        if q["id"] != "hutang_jatuh_tempo":
            continue
        for row in q.get("rows", []):
            # they should be non-cancelled non-paid: just structurally have outstanding value > 0
            assert (row.get("value") or 0) > 0, row


# ---------------- CLEANUP ----------------

def test_zzz_cleanup(admin, created_ids):
    """Attempt cleanup: use direct mongo via API is not available; leave marked 'QA' feedbacks in DB.
    We just try setting status closed on any still-open."""
    for fb_id in created_ids.get("feedbacks", []):
        try:
            admin.patch(f"{BASE}/api/customer-feedback/{fb_id}",
                        json={"status": "resolved", "resolution": "QA autotest cleanup"})
            admin.patch(f"{BASE}/api/customer-feedback/{fb_id}", json={"status": "closed"})
        except Exception:
            pass
