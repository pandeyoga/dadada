"""Iter 50 — Marketing & Sosial Media (kalender konten, kampanye, post, lampiran, analitik).

Coverage:
  - GET /api/marketing/meta (admin) + role warehouse 403
  - Campaigns CRUD + validasi tanggal + rename → post.campaign_name ikut
  - Post lifecycle: hashtags dedup, transisi idea→review 400, draft→review tanpa caption 400,
    approve oleh sales 400, approve oleh manager OK, scheduled tanpa PIC 400,
    approved→draft tanpa note 400, scheduled→published + published_url, metrics guards,
    edit caption pada published 400, delete published 400, delete draft OK
  - Attachments PNG (POST/GET/DELETE)
  - GET /posts?month + platform/status filter
  - GET /assets?q=OD keys designs/products/special_orders
  - GET /analytics?month=2026-09 (data uji ada), campaign_id filter
"""
import io
import os
import struct
import zlib

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
def sales_h():
    return _h("sales@kainnusantara.id")


@pytest.fixture(scope="module")
def warehouse_h():
    return _h("warehouse@kainnusantara.id")


# ─── META & RBAC ─────────────────────────────────────────────────────────────
def test_meta_admin_shape(admin_h):
    r = requests.get(f"{BASE}/api/marketing/meta", headers=admin_h, timeout=30)
    assert r.status_code == 200, r.text
    j = r.json()
    assert len(j["platforms"]) == 6
    codes = {p["code"] for p in j["platforms"]}
    assert {"instagram", "tiktok", "facebook", "whatsapp", "shopee", "youtube"}.issubset(codes)
    assert len(j["statuses"]) == 7
    assert len(j["pic_options"]) >= 1


def test_meta_warehouse_forbidden(warehouse_h):
    r = requests.get(f"{BASE}/api/marketing/meta", headers=warehouse_h, timeout=30)
    assert r.status_code == 403, r.text


# ─── KAMPANYE ────────────────────────────────────────────────────────────────
@pytest.fixture(scope="module")
def campaign_id(admin_h):
    body = {"name": "Uji Kampanye Iter50", "start_date": "2026-10-01",
            "end_date": "2026-10-31", "platforms": ["instagram"]}
    r = requests.post(f"{BASE}/api/marketing/campaigns", headers=admin_h, json=body, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["id"]


def test_campaign_created_ok(campaign_id):
    assert campaign_id.startswith("mkc_")


def test_campaign_end_before_start_400(admin_h):
    body = {"name": "Bad", "start_date": "2026-10-10", "end_date": "2026-10-05", "platforms": ["instagram"]}
    r = requests.post(f"{BASE}/api/marketing/campaigns", headers=admin_h, json=body, timeout=30)
    assert r.status_code == 400


def test_campaign_empty_name_400(admin_h):
    body = {"name": "  ", "start_date": "2026-10-01", "end_date": "2026-10-31", "platforms": ["instagram"]}
    r = requests.post(f"{BASE}/api/marketing/campaigns", headers=admin_h, json=body, timeout=30)
    assert r.status_code == 400


def test_campaign_list_has_counts(admin_h, campaign_id):
    r = requests.get(f"{BASE}/api/marketing/campaigns", headers=admin_h, timeout=30)
    assert r.status_code == 200
    found = [c for c in r.json() if c["id"] == campaign_id]
    assert found and "post_counts" in found[0] and "posts_total" in found[0]


# ─── POSTS ───────────────────────────────────────────────────────────────────
def test_post_missing_platforms_400(admin_h):
    r = requests.post(f"{BASE}/api/marketing/posts", headers=admin_h,
                      json={"title": "No platforms", "caption": "hi"}, timeout=30)
    assert r.status_code == 400


@pytest.fixture(scope="module")
def post_id(admin_h, campaign_id):
    body = {"title": "Post Uji Iter50", "platforms": ["tiktok", "instagram"],
            "hashtags": "#a #b #a", "caption": "x", "publish_at": "2026-10-05T09:30",
            "campaign_id": campaign_id}
    r = requests.post(f"{BASE}/api/marketing/posts", headers=admin_h, json=body, timeout=30)
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["status"] == "idea"
    assert j["hashtags"] == ["a", "b"]
    return j["id"]


def test_campaign_rename_propagates(admin_h, campaign_id, post_id):
    r = requests.patch(f"{BASE}/api/marketing/campaigns/{campaign_id}", headers=admin_h,
                       json={"name": "Uji Kampanye Iter50 v2"}, timeout=30)
    assert r.status_code == 200
    p = requests.get(f"{BASE}/api/marketing/posts/{post_id}", headers=admin_h, timeout=30).json()
    assert p["campaign_name"] == "Uji Kampanye Iter50 v2"


def test_transition_idea_to_review_400(admin_h, post_id):
    r = requests.post(f"{BASE}/api/marketing/posts/{post_id}/transition", headers=admin_h,
                      json={"to": "review"}, timeout=30)
    assert r.status_code == 400
    assert "Tidak bisa" in r.json().get("detail", "")


def test_transition_idea_draft(admin_h, post_id):
    r = requests.post(f"{BASE}/api/marketing/posts/{post_id}/transition", headers=admin_h,
                      json={"to": "draft"}, timeout=30)
    assert r.status_code == 200


def test_transition_draft_review_no_caption_400(admin_h, post_id):
    # kosongkan caption dulu
    requests.patch(f"{BASE}/api/marketing/posts/{post_id}", headers=admin_h,
                   json={"caption": ""}, timeout=30)
    r = requests.post(f"{BASE}/api/marketing/posts/{post_id}/transition", headers=admin_h,
                      json={"to": "review"}, timeout=30)
    assert r.status_code == 400


def test_transition_draft_review_ok(admin_h, post_id):
    requests.patch(f"{BASE}/api/marketing/posts/{post_id}", headers=admin_h,
                   json={"caption": "caption oke"}, timeout=30)
    r = requests.post(f"{BASE}/api/marketing/posts/{post_id}/transition", headers=admin_h,
                      json={"to": "review"}, timeout=30)
    assert r.status_code == 200


def test_approve_by_sales_forbidden(sales_h, post_id):
    r = requests.post(f"{BASE}/api/marketing/posts/{post_id}/transition", headers=sales_h,
                      json={"to": "approved"}, timeout=30)
    assert r.status_code == 400
    assert "manager" in r.json().get("detail", "").lower()


def test_approve_by_manager_ok(manager_h, post_id):
    r = requests.post(f"{BASE}/api/marketing/posts/{post_id}/transition", headers=manager_h,
                      json={"to": "approved"}, timeout=30)
    assert r.status_code == 200
    assert r.json()["status"] == "approved"


def test_scheduled_without_pic_400(admin_h, post_id):
    r = requests.post(f"{BASE}/api/marketing/posts/{post_id}/transition", headers=admin_h,
                      json={"to": "scheduled"}, timeout=30)
    assert r.status_code == 400


def test_approved_to_draft_without_note_400(admin_h, post_id):
    r = requests.post(f"{BASE}/api/marketing/posts/{post_id}/transition", headers=admin_h,
                      json={"to": "draft"}, timeout=30)
    assert r.status_code == 400


def test_set_pic_then_scheduled(admin_h, post_id):
    # find a pic
    meta = requests.get(f"{BASE}/api/marketing/meta", headers=admin_h, timeout=30).json()
    pic = meta["pic_options"][0]
    r = requests.patch(f"{BASE}/api/marketing/posts/{post_id}", headers=admin_h,
                      json={"pic_user_id": pic["id"]}, timeout=30)
    assert r.status_code == 200
    r = requests.post(f"{BASE}/api/marketing/posts/{post_id}/transition", headers=admin_h,
                      json={"to": "scheduled"}, timeout=30)
    assert r.status_code == 200
    assert r.json()["status"] == "scheduled"


def test_scheduled_to_published(admin_h, post_id):
    r = requests.post(f"{BASE}/api/marketing/posts/{post_id}/transition", headers=admin_h,
                      json={"to": "published", "published_url": "https://ig.example.com/p/xyz"}, timeout=30)
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["status"] == "published"
    assert j["published_at"]
    assert j["published_url"] == "https://ig.example.com/p/xyz"


def test_metrics_negative_400(admin_h, post_id):
    r = requests.post(f"{BASE}/api/marketing/posts/{post_id}/metrics", headers=admin_h,
                      json={"metrics": {"likes": -1}}, timeout=30)
    assert r.status_code == 400


def test_metrics_ok(admin_h, post_id):
    r = requests.post(f"{BASE}/api/marketing/posts/{post_id}/metrics", headers=admin_h,
                      json={"metrics": {"likes": 10, "reach": 100}}, timeout=30)
    assert r.status_code == 200
    j = r.json()
    assert j["metrics"]["likes"] == 10
    assert j["metrics"]["reach"] == 100
    assert len(j["metrics_history"]) >= 1


def test_edit_caption_on_published_400(admin_h, post_id):
    r = requests.patch(f"{BASE}/api/marketing/posts/{post_id}", headers=admin_h,
                      json={"caption": "ubah"}, timeout=30)
    assert r.status_code == 400


def test_delete_published_400(admin_h, post_id):
    r = requests.delete(f"{BASE}/api/marketing/posts/{post_id}", headers=admin_h, timeout=30)
    assert r.status_code == 400


def test_metrics_on_non_published_400(admin_h, campaign_id):
    r = requests.post(f"{BASE}/api/marketing/posts", headers=admin_h,
                      json={"title": "Draft only", "platforms": ["instagram"], "caption": "c",
                            "campaign_id": campaign_id}, timeout=30)
    pid = r.json()["id"]
    r = requests.post(f"{BASE}/api/marketing/posts/{pid}/metrics", headers=admin_h,
                      json={"metrics": {"likes": 1}}, timeout=30)
    assert r.status_code == 400
    # cleanup
    requests.delete(f"{BASE}/api/marketing/posts/{pid}", headers=admin_h, timeout=30)


def test_delete_draft_ok(admin_h):
    r = requests.post(f"{BASE}/api/marketing/posts", headers=admin_h,
                      json={"title": "Delete Me", "platforms": ["facebook"], "caption": ""}, timeout=30)
    pid = r.json()["id"]
    r = requests.delete(f"{BASE}/api/marketing/posts/{pid}", headers=admin_h, timeout=30)
    assert r.status_code == 200


# ─── LAMPIRAN ────────────────────────────────────────────────────────────────
def _tiny_png() -> bytes:
    # 1x1 red PNG
    def _chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    idat = zlib.compress(b"\x00\xff\x00\x00")
    return sig + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", idat) + _chunk(b"IEND", b"")


def test_attachment_lifecycle(admin_h, campaign_id):
    r = requests.post(f"{BASE}/api/marketing/posts", headers=admin_h,
                      json={"title": "Attach Me", "platforms": ["instagram"], "caption": "c",
                            "campaign_id": campaign_id}, timeout=30)
    pid = r.json()["id"]
    files = {"file": ("uji.png", _tiny_png(), "image/png")}
    r = requests.post(f"{BASE}/api/marketing/posts/{pid}/attachments", headers=admin_h,
                     files=files, data={"caption": "c"}, timeout=30)
    assert r.status_code == 200, r.text
    fid = r.json()["attachment"]["id"]
    # fetch bytes
    r = requests.get(f"{BASE}/api/marketing/posts/{pid}/attachments/{fid}", headers=admin_h, timeout=30)
    assert r.status_code == 200
    assert "image/png" in r.headers.get("Content-Type", "")
    # delete
    r = requests.delete(f"{BASE}/api/marketing/posts/{pid}/attachments/{fid}", headers=admin_h, timeout=30)
    assert r.status_code == 200
    assert all(a["id"] != fid for a in r.json().get("attachments", []))
    requests.delete(f"{BASE}/api/marketing/posts/{pid}", headers=admin_h, timeout=30)


# ─── LIST/FILTER/ASSETS/ANALYTICS ────────────────────────────────────────────
def test_list_posts_month_includes_uji(admin_h, post_id):
    r = requests.get(f"{BASE}/api/marketing/posts?month=2026-10", headers=admin_h, timeout=30)
    assert r.status_code == 200
    ids = {p["id"] for p in r.json()}
    assert post_id in ids


def test_list_filter_platform_status(admin_h):
    r = requests.get(f"{BASE}/api/marketing/posts?platform=tiktok&status=published", headers=admin_h, timeout=30)
    assert r.status_code == 200
    for p in r.json():
        assert "tiktok" in p.get("platforms", [])
        assert p["status"] == "published"


def test_assets_keys(admin_h):
    r = requests.get(f"{BASE}/api/marketing/assets?q=OD", headers=admin_h, timeout=30)
    assert r.status_code == 200
    j = r.json()
    for k in ("designs", "products", "special_orders"):
        assert k in j


def test_analytics_sep_2026(admin_h):
    r = requests.get(f"{BASE}/api/marketing/analytics?month=2026-09", headers=admin_h, timeout=30)
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["published"] >= 1
    ig = j["by_platform"].get("instagram") or {}
    assert ig.get("reach", 0) >= 3400
    assert isinstance(j["engagement_rate_pct"], (int, float))


def test_analytics_campaign_filter(admin_h, campaign_id):
    r = requests.get(f"{BASE}/api/marketing/analytics?campaign_id={campaign_id}", headers=admin_h, timeout=30)
    assert r.status_code == 200
    j = r.json()
    assert j["posts_total"] >= 1
