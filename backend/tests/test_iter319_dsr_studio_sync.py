"""Iter319 — Permintaan Desain ↔ Design Studio sync tests.

Covers:
- /design-requests/meta returns categories.pattern/design
- POST /design-requests with new category/design_category (invalid → 400, valid → assigned)
- POST /design-requests/{id}/create-design (designer only for own request; response shape)
- Sync flow via design_gallery lifecycle (submit → delivered, request-revision → revision, approve → approved)
- Approve/reject on studio-linked request → 400
- Link-design guardrails and happy path
- List includes designs[] + studio_linked
"""
import io
import os
import uuid
import pytest
import requests

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
ENT = "ent_ksc"
HDR_ENT = {"X-Entity-Id": ENT}


def _token(email: str) -> str:
    r = requests.post(f"{BASE}/api/auth/login",
                      json={"email": email, "password": "demo12345"}, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def admin_h():
    return {**HDR_ENT, "Authorization": f"Bearer {_token('admin@kainnusantara.id')}"}


@pytest.fixture(scope="module")
def designer_h():
    return {**HDR_ENT, "Authorization": f"Bearer {_token('designer@kainnusantara.id')}"}


@pytest.fixture(scope="module")
def manager_h():
    return {**HDR_ENT, "Authorization": f"Bearer {_token('manager@kainnusantara.id')}"}


def _small_png() -> bytes:
    # 1x1 PNG
    return (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
            b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8"
            b"\xcf\xc0\x00\x00\x00\x03\x00\x01\x92\xa4l\xfd\x00\x00\x00\x00IEND\xaeB`\x82")


# ---------- meta ----------
def test_meta_categories(admin_h):
    r = requests.get(f"{BASE}/api/design-requests/meta", headers=admin_h, timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "categories" in data
    codes_pat = {c["code"] for c in data["categories"]["pattern"]}
    codes_des = {c["code"] for c in data["categories"]["design"]}
    assert {"SLR", "BTK"}.issubset(codes_pat), f"pattern codes missing: {codes_pat}"
    assert len(data["categories"]["pattern"]) >= 6
    assert {"AO", "PG"}.issubset(codes_des), f"design codes missing: {codes_des}"


# ---------- create request ----------
def _create_req(admin_h, brief_tag: str, cat="SLR", dcat="AO", submit_now=True):
    payload = {
        "source": "internal",
        "category_code": cat,
        "design_category_code": dcat,
        "brief": f"TEST_QA {brief_tag} " + uuid.uuid4().hex[:6],
        "assigned_to": "user_designer_01",
        "due_date": "2026-09-30",
        "submit_now": submit_now,
    }
    r = requests.post(f"{BASE}/api/design-requests", json=payload, headers=admin_h, timeout=15)
    return r


def test_create_with_new_categories(admin_h):
    r = _create_req(admin_h, "salur category")
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["status"] == "assigned"
    # target_label may be composed differently; check fields present
    assert "Salur" in (d.get("target_label", "") or "") or d.get("category_code") == "SLR"


def test_create_with_invalid_category(admin_h):
    payload = {
        "source": "internal",
        "category_code": "XXX",
        "design_category_code": "AO",
        "brief": "TEST_QA invalid",
        "assigned_to": "user_designer_01",
        "due_date": "2026-09-30",
        "submit_now": True,
    }
    r = requests.post(f"{BASE}/api/design-requests", json=payload, headers=admin_h, timeout=15)
    assert r.status_code == 400, r.text


# ---------- create-design authorization ----------
def test_create_design_forbidden_for_other_designer(admin_h, designer_h):
    # request assigned to designer -> then flip assignee elsewhere via different creation
    r = _create_req(admin_h, "auth-test-not-mine")
    assert r.status_code == 200
    req = r.json()
    # reassign to a non-designer user via /assign (admin) — pick user_admin_01 as bogus designer? Use assign endpoint
    # If assign fails (not a designer), we cannot reassign; alternative: create with different assignee
    # Try a request assigned to another id (fallback: only user_designer_01 exists — assert that our designer test still passes)
    # For forbidden test we use manager creating one for a fake user id
    payload = {
        "source": "internal",
        "category_code": "BTK",
        "design_category_code": "PG",
        "brief": "TEST_QA foreign " + uuid.uuid4().hex[:6],
        "assigned_to": "user_designer_99_nonexistent",
        "due_date": "2026-09-30",
        "submit_now": True,
    }
    rc = requests.post(f"{BASE}/api/design-requests", json=payload, headers=admin_h, timeout=15)
    if rc.status_code != 200:
        pytest.skip("Cannot fabricate foreign-designer request; skipping forbidden case")
    rid = rc.json()["id"]
    r2 = requests.post(f"{BASE}/api/design-requests/{rid}/create-design",
                       json={"title": "TEST_QA denied"}, headers=designer_h, timeout=15)
    assert r2.status_code == 403, r2.text


@pytest.fixture(scope="module")
def sync_req(admin_h, designer_h):
    """Create request + designer creates design → returns (req_id, gallery_id, req_number)."""
    r = _create_req(admin_h, "sync-flow")
    assert r.status_code == 200, r.text
    req = r.json()
    rid = req["id"]

    r2 = requests.post(f"{BASE}/api/design-requests/{rid}/create-design",
                       json={"title": "TEST_QA Salur Sync"}, headers=designer_h, timeout=20)
    assert r2.status_code == 200, r2.text
    body = r2.json()
    assert body["status"] == "in_progress"
    assert body["studio_linked"] is True
    designs = body.get("designs") or []
    assert designs, "designs[] should not be empty"
    code = designs[0]["code"]
    assert code.startswith("SRI-SLR-AO-"), f"unexpected code: {code}"
    design = body.get("design") or {}
    assert design.get("id")
    return rid, design["id"], req["number"]


def test_upload_and_submit_triggers_delivered(admin_h, designer_h, sync_req):
    rid, gid, _num = sync_req
    files = {"file": ("test.png", _small_png(), "image/png")}
    ru = requests.post(f"{BASE}/api/design-gallery/{gid}/files-kind/artwork",
                       files=files, headers=designer_h, timeout=20)
    assert ru.status_code in (200, 201), ru.text

    rs = requests.post(f"{BASE}/api/design-gallery/{gid}/lifecycle/submit",
                       json={}, headers=designer_h, timeout=20)
    assert rs.status_code == 200, rs.text

    rg = requests.get(f"{BASE}/api/design-requests/{rid}", headers=admin_h, timeout=15)
    assert rg.status_code == 200
    d = rg.json()
    assert d["status"] == "delivered", d
    assert d["studio_linked"] is True
    hist = d.get("history") or []
    assert any("Hasil diserahkan" in (h.get("label", "") or "") for h in hist[-3:]), hist[-3:]


def test_admin_approve_reject_blocked_when_studio_linked(admin_h, sync_req):
    rid, _gid, _num = sync_req
    ra = requests.post(f"{BASE}/api/design-requests/{rid}/approve",
                       json={"note": "x"}, headers=admin_h, timeout=15)
    assert ra.status_code == 400, ra.text
    assert "studio" in ra.text.lower() or "desain" in ra.text.lower()

    rj = requests.post(f"{BASE}/api/design-requests/{rid}/reject",
                       json={"reason": "some reason"}, headers=admin_h, timeout=15)
    assert rj.status_code == 400, rj.text


def test_sync_revision_then_approve(admin_h, designer_h, sync_req):
    rid, gid, _num = sync_req
    # request revision from studio side
    rr = requests.post(f"{BASE}/api/design-gallery/{gid}/lifecycle/request-revision",
                       json={"note": "warna terlalu gelap", "score": 1.0},
                       headers=admin_h, timeout=20)
    assert rr.status_code == 200, rr.text
    rg = requests.get(f"{BASE}/api/design-requests/{rid}", headers=admin_h, timeout=15)
    d = rg.json()
    assert d["status"] == "revision", d
    assert d.get("revision_count", 0) >= 1
    assert (d.get("reject_reason") or "").startswith("warna terlalu gelap")

    # designer submits again
    files = {"file": ("v2.png", _small_png(), "image/png")}
    requests.post(f"{BASE}/api/design-gallery/{gid}/files-kind/artwork",
                  files=files, headers=designer_h, timeout=20)
    rs = requests.post(f"{BASE}/api/design-gallery/{gid}/lifecycle/submit",
                       json={}, headers=designer_h, timeout=20)
    assert rs.status_code == 200, rs.text
    d2 = requests.get(f"{BASE}/api/design-requests/{rid}", headers=admin_h).json()
    assert d2["status"] == "delivered"

    ra = requests.post(f"{BASE}/api/design-gallery/{gid}/lifecycle/approve",
                       json={"note": "ok", "score": 1.75, "final_color_count": 4},
                       headers=admin_h, timeout=20)
    assert ra.status_code == 200, ra.text
    d3 = requests.get(f"{BASE}/api/design-requests/{rid}", headers=admin_h).json()
    assert d3["status"] == "approved", d3
    assert d3.get("decided_by")


# ---------- link-design guardrails ----------
def _new_design(designer_h, cat="SLR", dcat="AO", title=None):
    body = {"title": title or f"TEST_QA Draft {uuid.uuid4().hex[:6]}",
            "category_code": cat, "design_category_code": dcat}
    r = requests.post(f"{BASE}/api/design-gallery", json=body, headers=designer_h, timeout=15)
    assert r.status_code in (200, 201), r.text
    return r.json()


def test_link_design_happy_path(admin_h, designer_h):
    d = _new_design(designer_h)
    r = _create_req(admin_h, "link-happy")
    rid = r.json()["id"]
    rl = requests.post(f"{BASE}/api/design-requests/{rid}/link-design",
                       json={"gallery_id": d["id"]}, headers=designer_h, timeout=15)
    assert rl.status_code == 200, rl.text
    body = rl.json()
    assert body["status"] == "in_progress"
    assert any(x.get("id") == d["id"] for x in body.get("designs", []))


def test_link_design_already_linked(admin_h, designer_h):
    d = _new_design(designer_h)
    r1 = _create_req(admin_h, "link-first")
    r2 = _create_req(admin_h, "link-second")
    rl = requests.post(f"{BASE}/api/design-requests/{r1.json()['id']}/link-design",
                       json={"gallery_id": d["id"]}, headers=designer_h, timeout=15)
    assert rl.status_code == 200
    rl2 = requests.post(f"{BASE}/api/design-requests/{r2.json()['id']}/link-design",
                        json={"gallery_id": d["id"]}, headers=designer_h, timeout=15)
    assert rl2.status_code == 400, rl2.text


# ---------- list endpoint shape ----------
def test_list_has_designs_and_studio_linked(admin_h):
    r = requests.get(f"{BASE}/api/design-requests?page_size=50", headers=admin_h, timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()
    items = data.get("items") or data.get("data") or []
    assert items, "list empty"
    sample = items[0]
    assert "designs" in sample
    assert "studio_linked" in sample
