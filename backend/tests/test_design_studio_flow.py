"""Design Studio backend tests — meta, next-code, gallery create, lifecycle,
score validation, colorway, feedback, RBAC (designer forbidden on assess),
categories & tags. Uses only public API via REACT_APP_BACKEND_URL.
"""
import os
import io
import re
import struct
import zlib
import time
import pytest
import requests

def _load_base():
    b = os.environ.get("REACT_APP_BACKEND_URL", "").strip()
    if not b:
        try:
            for line in open("/app/frontend/.env"):
                if line.startswith("REACT_APP_BACKEND_URL="):
                    b = line.split("=", 1)[1].strip()
                    break
        except OSError:
            pass
    return b.rstrip("/")

BASE = _load_base()
ENTITY = "ent_ksc"


def _png_bytes() -> bytes:
    """Minimal valid 1x1 red PNG."""
    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
    idat = chunk(b"IDAT", zlib.compress(b"\x00\xff\x00\x00"))
    iend = chunk(b"IEND", b"")
    return sig + ihdr + idat + iend


def _login(email, password="demo12345"):
    r = requests.post(f"{BASE}/api/auth/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def admin_h():
    return {"Authorization": f"Bearer {_login('admin@kainnusantara.id')}", "X-Entity-Id": ENTITY}


@pytest.fixture(scope="module")
def designer_h():
    return {"Authorization": f"Bearer {_login('designer@kainnusantara.id')}", "X-Entity-Id": ENTITY}


@pytest.fixture(scope="module")
def color_ids(admin_h):
    r = requests.get(f"{BASE}/api/color-library", headers=admin_h, timeout=30)
    assert r.status_code == 200
    ids = [c["id"] for c in r.json() if c.get("status") == "active"][:3]
    assert len(ids) >= 2, "Need at least 2 active colors in library"
    return ids


# ── META & NEXT-CODE ────────────────────────────────────────────────
def test_design_meta(admin_h):
    r = requests.get(f"{BASE}/api/design-studio/meta", headers=admin_h, params={"entity_id": ENTITY}, timeout=30)
    assert r.status_code == 200, r.text
    d = r.json()
    for k in ("statuses", "transitions", "categories", "code", "designer_code"):
        assert k in d, k
    assert d["designer_code"] == "BDI", f"admin designer_code expected BDI, got {d['designer_code']}"
    assert any(c["design_type"] == "pattern" and c["code"] == "SLR" for c in d["categories"])


def test_next_code_pattern(admin_h):
    r = requests.get(f"{BASE}/api/design-studio/next-code", headers=admin_h,
                     params={"category_code": "SLR", "design_category_code": "AO"}, timeout=30)
    assert r.status_code == 200, r.text
    d = r.json()
    assert re.match(r"^BDI-SLR-AO-\d{3}$", d["code"]), d["code"]


def test_designer_prefix_sri(designer_h):
    r = requests.get(f"{BASE}/api/design-studio/meta", headers=designer_h, params={"entity_id": ENTITY}, timeout=30)
    assert r.status_code == 200
    # Sari Melati → SRI (first letter + consonants)
    assert r.json()["designer_code"] == "SRI", r.json()["designer_code"]


# ── CATEGORIES & TAGS ──────────────────────────────────────────────
def test_categories_list(admin_h):
    r = requests.get(f"{BASE}/api/design-studio/categories", headers=admin_h,
                     params={"design_type": "design"}, timeout=30)
    assert r.status_code == 200
    codes = {c["code"] for c in r.json()}
    assert {"AO", "PG"} <= codes, codes
    r = requests.get(f"{BASE}/api/design-studio/categories", headers=admin_h,
                     params={"design_type": "pattern"}, timeout=30)
    codes = {c["code"] for c in r.json()}
    assert {"SLR", "BTK", "BGA", "PLD", "ABS", "CSMR"} <= codes, codes


def test_tags_endpoint(admin_h):
    r = requests.get(f"{BASE}/api/design-studio/tags", headers=admin_h, params={"q": ""}, timeout=30)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


# ── CREATE + FULL LIFECYCLE ────────────────────────────────────────
@pytest.fixture(scope="module")
def created_design(admin_h, color_ids):
    r = requests.get(f"{BASE}/api/design-studio/next-code", headers=admin_h,
                     params={"category_code": "SLR", "design_category_code": "AO"}, timeout=30)
    seq_before = int(re.findall(r"\d+$", r.json()["code"])[0])

    payload = {
        "title": f"TEST_studio_{int(time.time())}",
        "category_code": "SLR",
        "design_category_code": "AO",
        "tags": ["TEST_lebar", "TEST_kotak"],
        "colors": [{"color_id": color_ids[0], "role": "primary"},
                   {"color_id": color_ids[1], "role": "secondary"}],
        "recommended_product_ids": [],
    }
    r = requests.post(f"{BASE}/api/design-gallery", headers=admin_h, json=payload, timeout=30)
    assert r.status_code == 200, r.text
    doc = r.json()
    assert re.match(r"^BDI-SLR-AO-\d{3}$", doc.get("code", "")), doc.get("code")
    assert doc.get("category_name") == "Salur", doc.get("category_name")
    assert doc.get("design_category_name") == "Allover", doc.get("design_category_name")
    assert doc.get("round_label") == "Pengajuan awal" and doc.get("revision_count") == 0
    assert doc["colors"][0].get("hex"), "colors should be resolved with hex from library"

    # next-code should advance
    r2 = requests.get(f"{BASE}/api/design-studio/next-code", headers=admin_h,
                      params={"category_code": "SLR", "design_category_code": "AO"}, timeout=30)
    seq_after = int(re.findall(r"\d+$", r2.json()["code"])[0])
    assert seq_after == seq_before + 1, f"{seq_after} vs {seq_before}"
    return doc


def test_create_bad_color_id(admin_h):
    r = requests.post(f"{BASE}/api/design-gallery", headers=admin_h, json={
        "title": "TEST_badcolor", "category_code": "BTK",
        "colors": [{"color_id": "col_nonexistent_xxx", "role": "primary"}],
    }, timeout=30)
    assert r.status_code == 400, r.text


def test_create_bad_category(admin_h, color_ids):
    r = requests.post(f"{BASE}/api/design-gallery", headers=admin_h, json={
        "title": "TEST_badcat", "category_code": "ZZZ",
        "colors": [{"color_id": color_ids[0]}],
    }, timeout=30)
    assert r.status_code == 400, r.text


def test_lifecycle_full(admin_h, created_design):
    gid = created_design["id"]
    # submit without artwork -> 400
    r = requests.post(f"{BASE}/api/design-gallery/{gid}/lifecycle/submit",
                      headers=admin_h, json={}, timeout=30)
    assert r.status_code == 400, r.text

    # upload artwork
    files = {"file": ("art.png", _png_bytes(), "image/png")}
    r = requests.post(f"{BASE}/api/design-gallery/{gid}/files-kind/artwork",
                      headers=admin_h, files=files, timeout=30)
    assert r.status_code == 200, r.text

    # submit
    r = requests.post(f"{BASE}/api/design-gallery/{gid}/lifecycle/submit",
                      headers=admin_h, json={}, timeout=30)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "pending_approval"

    # start review
    r = requests.post(f"{BASE}/api/design-gallery/{gid}/lifecycle/start-review",
                      headers=admin_h, json={}, timeout=30)
    assert r.status_code == 200 and r.json()["status"] == "in_review", r.text

    # approve without score -> 400
    r = requests.post(f"{BASE}/api/design-gallery/{gid}/lifecycle/approve",
                      headers=admin_h, json={}, timeout=30)
    assert r.status_code == 400

    # invalid score 1.3 -> 400
    r = requests.post(f"{BASE}/api/design-gallery/{gid}/versions/1/score",
                      headers=admin_h, json={"score": 1.3}, timeout=30)
    assert r.status_code == 400, r.text

    # request revision score 1.25
    r = requests.post(f"{BASE}/api/design-gallery/{gid}/lifecycle/request-revision",
                      headers=admin_h, json={"note": "Perbaiki komposisi", "score": 1.25}, timeout=30)
    assert r.status_code == 200 and r.json()["status"] == "revision", r.text
    d = r.json()
    assert d.get("reject_reason") == "Perbaiki komposisi"
    # ronde baru dibuka OTOMATIS (Revisi 1)
    assert d["version"] == 2 and d["round_label"] == "Revisi 1" and d["revision_count"] == 1, d
    assert d["rounds"][0]["result"] == "revision" and d["rounds"][1]["result"] == "revision"
    # new-version manual ditolak saat revisi (ronde sudah dibuka otomatis)
    r = requests.post(f"{BASE}/api/design-gallery/{gid}/new-version",
                      headers=admin_h, json={"note": "Revisi 2"}, timeout=30)
    assert r.status_code == 400, r.text
    # submit tanpa berkas ronde 2 -> 400
    r = requests.post(f"{BASE}/api/design-gallery/{gid}/lifecycle/submit",
                      headers=admin_h, json={}, timeout=30)
    assert r.status_code == 400, r.text

    # upload artwork for v2
    r = requests.post(f"{BASE}/api/design-gallery/{gid}/files-kind/artwork",
                      headers=admin_h, files={"file": ("v2.png", _png_bytes(), "image/png")}, timeout=30)
    assert r.status_code == 200

    # submit v2
    r = requests.post(f"{BASE}/api/design-gallery/{gid}/lifecycle/submit",
                      headers=admin_h, json={}, timeout=30)
    assert r.status_code == 200

    # approve with score 1.0 (below threshold 1.5) -> 400
    r = requests.post(f"{BASE}/api/design-gallery/{gid}/lifecycle/approve",
                      headers=admin_h, json={"score": 1.0}, timeout=30)
    assert r.status_code == 400, r.text

    # approve with 1.75 + penilai menetapkan jumlah varian warna final = 2
    r = requests.post(f"{BASE}/api/design-gallery/{gid}/lifecycle/approve",
                      headers=admin_h, json={"score": 1.75, "final_color_count": 2}, timeout=30)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["status"] == "approved"
    assert d["final_score"] == 1.75
    assert d["final_color_count"] == 2 and d["final"]["complete"] is False
    v2 = next(v for v in d["versions"] if v["version"] == 2)
    assert v2.get("acc") is True

    # activate langsung ditolak (belum ada berkas final)
    r = requests.post(f"{BASE}/api/design-gallery/{gid}/lifecycle/activate",
                      headers=admin_h, json={}, timeout=30)
    assert r.status_code == 400, r.text
    # submit-final tanpa mockup -> 400
    r = requests.post(f"{BASE}/api/design-gallery/{gid}/lifecycle/submit-final",
                      headers=admin_h, json={}, timeout=30)
    assert r.status_code == 400 and "Mockup" in r.text, r.text
    for i in range(2):
        r = requests.post(f"{BASE}/api/design-gallery/{gid}/files-kind/colorway",
                          headers=admin_h, files={"file": (f"cw{i}.png", _png_bytes(), "image/png")}, timeout=30)
        assert r.status_code == 200, r.text
    r = requests.post(f"{BASE}/api/design-gallery/{gid}/files-kind/mockup",
                      headers=admin_h, files={"file": ("mockup.png", _png_bytes(), "image/png")}, timeout=30)
    assert r.status_code == 200, r.text
    r = requests.post(f"{BASE}/api/design-gallery/{gid}/lifecycle/submit-final",
                      headers=admin_h, json={}, timeout=30)
    assert r.status_code == 200 and r.json()["status"] == "final_submitted", r.text
    assert r.json()["final"]["complete"] is True
    # return-final wajib catatan
    r = requests.post(f"{BASE}/api/design-gallery/{gid}/lifecycle/return-final",
                      headers=admin_h, json={}, timeout=30)
    assert r.status_code == 400
    r = requests.post(f"{BASE}/api/design-gallery/{gid}/lifecycle/return-final",
                      headers=admin_h, json={"note": "mockup kurang tajam"}, timeout=30)
    assert r.status_code == 200 and r.json()["status"] == "approved"
    r = requests.post(f"{BASE}/api/design-gallery/{gid}/lifecycle/submit-final",
                      headers=admin_h, json={}, timeout=30)
    assert r.status_code == 200

    # activate
    r = requests.post(f"{BASE}/api/design-gallery/{gid}/lifecycle/activate",
                      headers=admin_h, json={}, timeout=30)
    assert r.status_code == 200 and r.json()["status"] == "active"

    # archive (note required)
    r = requests.post(f"{BASE}/api/design-gallery/{gid}/lifecycle/archive",
                      headers=admin_h, json={}, timeout=30)
    assert r.status_code == 400
    r = requests.post(f"{BASE}/api/design-gallery/{gid}/lifecycle/archive",
                      headers=admin_h, json={"note": "Selesai uji"}, timeout=30)
    assert r.status_code == 200 and r.json()["status"] == "archived"

    # reopen
    r = requests.post(f"{BASE}/api/design-gallery/{gid}/lifecycle/reopen",
                      headers=admin_h, json={}, timeout=30)
    assert r.status_code == 200 and r.json()["status"] == "draft"


# ── COLORWAY ───────────────────────────────────────────────────────
def test_colorway_flow(admin_h, created_design, color_ids):
    gid = created_design["id"]
    # bad color id
    r = requests.post(f"{BASE}/api/design-gallery/{gid}/colorways", headers=admin_h,
                      json={"name": "TEST_bad", "colors": [{"color_id": "col_fake_xxx"}]}, timeout=30)
    assert r.status_code == 400

    r = requests.post(f"{BASE}/api/design-gallery/{gid}/colorways", headers=admin_h,
                      json={"name": "TEST_cw1", "colors": [{"color_id": color_ids[0], "role": "primary"}]},
                      timeout=30)
    assert r.status_code == 200, r.text
    cw = r.json()
    assert re.match(r"^BDI-SLR-AO-\d{3}-CW01$", cw["code"]), cw["code"]


# ── FEEDBACK sides ────────────────────────────────────────────────
def test_feedback_sides(admin_h, designer_h, created_design):
    gid = created_design["id"]
    r = requests.post(f"{BASE}/api/design-gallery/{gid}/feedback", headers=admin_h,
                     json={"text": "TEST_review by admin"}, timeout=30)
    assert r.status_code == 200 and r.json().get("side") == "assessor", r.text

    r = requests.post(f"{BASE}/api/design-gallery/{gid}/feedback", headers=designer_h,
                     json={"text": "TEST_reply by designer"}, timeout=30)
    assert r.status_code == 200 and r.json().get("side") == "designer", r.text

    # detail contains both
    r = requests.get(f"{BASE}/api/design-gallery/{gid}", headers=admin_h, timeout=30)
    assert r.status_code == 200
    sides = {fb.get("side") for fb in r.json().get("feedback") or []}
    assert {"assessor", "designer"}.issubset(sides), sides


# ── RBAC: designer cannot assess ──────────────────────────────────
def test_designer_forbidden_assess(designer_h, color_ids):
    # designer creates own design
    r = requests.post(f"{BASE}/api/design-gallery", headers=designer_h, json={
        "title": f"TEST_designer_{int(time.time())}", "category_code": "BTK", "design_category_code": "PG",
        "colors": [{"color_id": color_ids[0]}]}, timeout=30)
    assert r.status_code == 200, r.text
    gid = r.json()["id"]
    assert r.json()["code"].startswith("SRI-"), r.json()["code"]

    # designer upload artwork
    r = requests.post(f"{BASE}/api/design-gallery/{gid}/files-kind/artwork",
                      headers=designer_h, files={"file": ("d.png", _png_bytes(), "image/png")}, timeout=30)
    assert r.status_code == 200

    # designer submit — ok
    r = requests.post(f"{BASE}/api/design-gallery/{gid}/lifecycle/submit",
                      headers=designer_h, json={}, timeout=30)
    assert r.status_code == 200

    # designer forbidden: start-review, approve, score
    for path, body in [
        (f"/api/design-gallery/{gid}/lifecycle/start-review", {}),
        (f"/api/design-gallery/{gid}/lifecycle/approve", {"score": 1.75}),
        (f"/api/design-gallery/{gid}/versions/1/score", {"score": 1.75}),
    ]:
        r = requests.post(f"{BASE}{path}", headers=designer_h, json=body, timeout=30)
        assert r.status_code == 403, f"{path}: {r.status_code} {r.text}"


# ── LIST FILTER ────────────────────────────────────────────────────
def test_list_filter(admin_h):
    r = requests.get(f"{BASE}/api/design-gallery", headers=admin_h,
                     params={"entity_id": ENTITY, "status": "active", "category_code": "SLR"}, timeout=30)
    assert r.status_code == 200
    for d in r.json():
        assert d.get("status") == "active"
        assert "current_score" in d and "artwork_count" in d and "colorway_count" in d and "feedback_count" in d
