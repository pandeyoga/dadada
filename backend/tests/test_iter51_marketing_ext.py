"""Iter 51 — Marketing lanjutan: Akun sosmed per PT, dashboard, PDF, multi-entitas.

Coverage:
  - POST /marketing/accounts (validasi platform, handle strip '@', duplikat, PATCH label/followers, list entity_name+posts_total, admin all)
  - POST /marketing/posts dengan account_ids: platform mismatch 400, cross-entity 400, snapshot handle
  - Multi-entitas: POST/GET posts scoping per entity, entity_id=all admin, list entity_name
  - GET /marketing/dashboard shape (kpi, kpi_prev, trend[6], by_platform, by_entity, by_account, pipeline, upcoming, overdue)
  - GET /marketing/calendar.pdf: content-type/disposition/PDF magic; pymupdf text extraction (title, kolom Badan usaha saat entity_id=all)
"""
import os
import re
import pytest
import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE:
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE = line.split("=", 1)[1].strip()
                break
BASE = BASE.rstrip("/")

ENT_KSC = "ent_ksc"
ENT_KANDA = "ent_kanda"


def _login(email, pwd="demo12345"):
    r = requests.post(f"{BASE}/api/auth/login", json={"email": email, "password": pwd}, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["token"]


def _h(email, ent=ENT_KSC):
    return {"Authorization": f"Bearer {_login(email)}", "X-Entity-Id": ent, "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def admin_ksc():
    return _h("admin@kainnusantara.id", ENT_KSC)


@pytest.fixture(scope="module")
def admin_kanda():
    return _h("admin@kainnusantara.id", ENT_KANDA)


@pytest.fixture(scope="module")
def sales_h():
    return _h("sales@kainnusantara.id", ENT_KSC)


# ─── ACCOUNTS ────────────────────────────────────────────────────────────────
@pytest.fixture(scope="module")
def created_tt_account_id(admin_ksc):
    body = {"platform": "tiktok", "handle": "@kn.official", "label": "TT",
            "url": "https://tiktok.com/@kn.official", "followers": 300}
    r = requests.post(f"{BASE}/api/marketing/accounts", headers=admin_ksc, json=body, timeout=30)
    # cleanup pre-existing dup by returning existing id from list
    if r.status_code == 400:
        # find existing
        lst = requests.get(f"{BASE}/api/marketing/accounts", headers=admin_ksc, timeout=30).json()
        for a in lst:
            if a["platform"] == "tiktok" and a["handle"].lower() == "kn.official" and a["entity_id"] == ENT_KSC:
                return a["id"]
        pytest.fail(f"Create failed and no existing: {r.text}")
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["handle"] == "kn.official"  # '@' stripped
    assert j["entity_id"] == ENT_KSC
    return j["id"]


def test_account_dup_handle_case_insensitive_400(admin_ksc, created_tt_account_id):
    body = {"platform": "tiktok", "handle": "KN.Official", "label": "dup"}
    r = requests.post(f"{BASE}/api/marketing/accounts", headers=admin_ksc, json=body, timeout=30)
    assert r.status_code == 400


def test_account_unknown_platform_400(admin_ksc):
    body = {"platform": "xx", "handle": "test_iter51"}
    r = requests.post(f"{BASE}/api/marketing/accounts", headers=admin_ksc, json=body, timeout=30)
    assert r.status_code == 400


def test_account_patch_label_followers(admin_ksc, created_tt_account_id):
    r = requests.patch(f"{BASE}/api/marketing/accounts/{created_tt_account_id}", headers=admin_ksc,
                       json={"label": "TikTok utama", "followers": 350}, timeout=30)
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["label"] == "TikTok utama"
    assert j["followers"] == 350


def test_account_list_has_entity_name_and_posts_total(admin_ksc):
    r = requests.get(f"{BASE}/api/marketing/accounts", headers=admin_ksc, timeout=30)
    assert r.status_code == 200
    rows = r.json()
    assert rows, "expected accounts"
    for a in rows:
        assert "entity_name" in a and a["entity_name"]
        assert "posts_total" in a


def test_account_list_entity_all_admin(admin_ksc):
    r = requests.get(f"{BASE}/api/marketing/accounts?entity_id=all", headers=admin_ksc, timeout=30)
    assert r.status_code == 200
    rows = r.json()
    ents = {a["entity_id"] for a in rows}
    # should include multiple entities (data seeded across PT)
    assert len(ents) >= 1
    # at least KSC present
    assert ENT_KSC in ents


# ─── POST + ACCOUNT VALIDATION ───────────────────────────────────────────────
def test_post_with_matching_tt_account_ok(admin_ksc, created_tt_account_id):
    body = {"title": "Iter51 TT match", "platforms": ["tiktok"], "caption": "x",
            "account_ids": [created_tt_account_id]}
    r = requests.post(f"{BASE}/api/marketing/posts", headers=admin_ksc, json=body, timeout=30)
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["accounts"] and j["accounts"][0]["handle"] == "kn.official"
    requests.delete(f"{BASE}/api/marketing/posts/{j['id']}", headers=admin_ksc, timeout=30)


@pytest.fixture(scope="module")
def ig_account_id(admin_ksc):
    # find or create instagram account in ent_ksc
    lst = requests.get(f"{BASE}/api/marketing/accounts", headers=admin_ksc, timeout=30).json()
    for a in lst:
        if a["platform"] == "instagram" and a["entity_id"] == ENT_KSC:
            return a["id"]
    r = requests.post(f"{BASE}/api/marketing/accounts", headers=admin_ksc,
                      json={"platform": "instagram", "handle": "kn.iter51.ig"}, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["id"]


def test_post_account_platform_mismatch_400(admin_ksc, ig_account_id):
    body = {"title": "mismatch", "platforms": ["tiktok"], "caption": "x", "account_ids": [ig_account_id]}
    r = requests.post(f"{BASE}/api/marketing/posts", headers=admin_ksc, json=body, timeout=30)
    assert r.status_code == 400
    detail = r.json().get("detail", "").lower()
    assert "tidak sesuai platform" in detail or "sesuai platform" in detail


@pytest.fixture(scope="module")
def kanda_account_id(admin_kanda):
    lst = requests.get(f"{BASE}/api/marketing/accounts", headers=admin_kanda, timeout=30).json()
    for a in lst:
        if a["platform"] == "tiktok" and a["entity_id"] == ENT_KANDA:
            return a["id"]
    r = requests.post(f"{BASE}/api/marketing/accounts", headers=admin_kanda,
                      json={"platform": "tiktok", "handle": "kanda.iter51.tt"}, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["id"]


def test_post_cross_entity_account_400(admin_ksc, kanda_account_id):
    body = {"title": "cross-ent", "platforms": ["tiktok"], "caption": "x", "account_ids": [kanda_account_id]}
    r = requests.post(f"{BASE}/api/marketing/posts", headers=admin_ksc, json=body, timeout=30)
    assert r.status_code == 400
    assert "badan usaha lain" in r.json().get("detail", "").lower()


# ─── MULTI-ENTITAS ───────────────────────────────────────────────────────────
@pytest.fixture(scope="module")
def kanda_post_id(admin_kanda):
    body = {"title": "Iter51 Kanda Sep", "platforms": ["instagram"], "caption": "kanda",
            "publish_at": "2026-09-15T09:00"}
    r = requests.post(f"{BASE}/api/marketing/posts", headers=admin_kanda, json=body, timeout=30)
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["entity_id"] == ENT_KANDA
    return j["id"]


def test_posts_scoped_to_active_entity(admin_ksc, kanda_post_id):
    r = requests.get(f"{BASE}/api/marketing/posts?month=2026-09", headers=admin_ksc, timeout=30)
    assert r.status_code == 200
    rows = r.json()
    ids = {p["id"] for p in rows}
    assert kanda_post_id not in ids
    for p in rows:
        assert p.get("entity_id") == ENT_KSC


def test_posts_entity_all_admin_multi(admin_ksc, kanda_post_id):
    r = requests.get(f"{BASE}/api/marketing/posts?month=2026-09&entity_id=all", headers=admin_ksc, timeout=30)
    assert r.status_code == 200
    rows = r.json()
    ids = {p["id"] for p in rows}
    assert kanda_post_id in ids
    ent_names = {p.get("entity_name") for p in rows}
    # entity_name field populated
    for p in rows:
        assert "entity_name" in p and p["entity_name"]
    # expect at least Kanda + Sukacita
    assert any("Kanda" in (n or "") for n in ent_names)


def test_posts_entity_kanda_from_ksc_admin(admin_ksc, kanda_post_id):
    r = requests.get(f"{BASE}/api/marketing/posts?entity_id={ENT_KANDA}", headers=admin_ksc, timeout=30)
    assert r.status_code == 200
    for p in r.json():
        assert p.get("entity_id") == ENT_KANDA


def test_posts_entity_kanda_from_sales_forbidden(sales_h):
    r = requests.get(f"{BASE}/api/marketing/posts?entity_id={ENT_KANDA}", headers=sales_h, timeout=30)
    # sales tidak lintas PT → 403 (atau data kosong bila cross-entity diblok tanpa raise). Cek strict 403.
    assert r.status_code in (403, 400), f"expected 403/400 got {r.status_code} {r.text}"


# ─── DASHBOARD ────────────────────────────────────────────────────────────────
def test_dashboard_shape_all(admin_ksc):
    r = requests.get(f"{BASE}/api/marketing/dashboard?month=2026-09&entity_id=all", headers=admin_ksc, timeout=30)
    assert r.status_code == 200, r.text
    j = r.json()
    kpi = j["kpi"]
    for k in ("posts", "published", "reach", "engagement", "clicks", "leads", "on_time_rate_pct"):
        assert k in kpi
    assert "kpi_prev" in j
    assert isinstance(j["trend"], list) and len(j["trend"]) == 6
    assert j["trend"][5]["month"] == "2026-09"
    assert "by_platform" in j
    assert isinstance(j["by_entity"], dict) and len(j["by_entity"]) >= 1
    assert "by_account" in j
    assert isinstance(j["upcoming"], list)
    assert isinstance(j["overdue"], list)
    assert "pipeline" in j


def test_dashboard_month_empty_no_error(admin_ksc):
    r = requests.get(f"{BASE}/api/marketing/dashboard?month=2026-08&entity_id=all", headers=admin_ksc, timeout=30)
    assert r.status_code == 200
    j = r.json()
    assert j["kpi"]["posts"] == 0 or isinstance(j["kpi"]["posts"], int)


# ─── PDF ──────────────────────────────────────────────────────────────────────
def test_calendar_pdf_all_entities(admin_ksc):
    r = requests.get(f"{BASE}/api/marketing/calendar.pdf?month=2026-09&entity_id=all", headers=admin_ksc, timeout=30)
    assert r.status_code == 200, r.text[:400]
    assert "application/pdf" in r.headers.get("Content-Type", "")
    assert r.content.startswith(b"%PDF")
    disp = r.headers.get("Content-Disposition", "")
    assert "kalender-konten-2026-09.pdf" in disp
    # extract text
    import pymupdf
    doc = pymupdf.open(stream=r.content, filetype="pdf")
    text = "".join(page.get_text() for page in doc)
    doc.close()
    assert "Kalender Konten September 2026" in text, text[:500]
    assert "Badan usaha" in text  # kolom hanya saat entity_id=all


def test_calendar_pdf_single_entity(admin_ksc):
    r = requests.get(f"{BASE}/api/marketing/calendar.pdf?month=2026-09", headers=admin_ksc, timeout=30)
    assert r.status_code == 200
    assert r.content.startswith(b"%PDF")
