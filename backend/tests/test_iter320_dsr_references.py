"""Iter320 — Galeri Referensi Brief pada Permintaan Desain.

Menguji end-to-end alur unggah gambar referensi ke Permintaan Desain lalu
verifikasi propagasi otomatis ke desain Studio saat create/link, plus RBAC
(desainer 403 upload/delete), validasi tipe file, dan idempotensi.
"""
import io
import os
import struct
import uuid
import zlib

import pytest
import requests

def _load_base_url():
    v = os.environ.get("REACT_APP_BACKEND_URL", "").strip()
    if v:
        return v.rstrip("/")
    try:
        with open("/app/frontend/.env") as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL="):
                    return line.split("=", 1)[1].strip().rstrip("/")
    except Exception:
        pass
    return ""


BASE_URL = _load_base_url()
ENTITY = "ent_ksc"
ADMIN = ("admin@kainnusantara.id", "demo12345")
DESIGNER = ("designer@kainnusantara.id", "demo12345")
DESIGNER_ID = "user_designer_01"


def _tiny_png() -> bytes:
    """Return a valid 1x1 PNG."""
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = b"IHDR" + struct.pack(">II", 1, 1) + b"\x08\x02\x00\x00\x00"
    ihdr_c = struct.pack(">I", 13) + ihdr + struct.pack(">I", zlib.crc32(ihdr) & 0xFFFFFFFF)
    raw = b"\x00\xff\x00\x00"
    comp = zlib.compress(raw)
    idat = b"IDAT" + comp
    idat_c = struct.pack(">I", len(comp)) + idat + struct.pack(">I", zlib.crc32(idat) & 0xFFFFFFFF)
    iend = b"IEND"
    iend_c = struct.pack(">I", 0) + iend + struct.pack(">I", zlib.crc32(iend) & 0xFFFFFFFF)
    return sig + ihdr_c + idat_c + iend_c


def _login(email, pwd):
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": email, "password": pwd}, timeout=30)
    r.raise_for_status()
    return r.json()["token"]


def _h(token, multipart=False):
    h = {"Authorization": f"Bearer {token}", "X-Entity-Id": ENTITY}
    if not multipart:
        h["Content-Type"] = "application/json"
    return h


@pytest.fixture(scope="module")
def admin_token():
    return _login(*ADMIN)


@pytest.fixture(scope="module")
def designer_token():
    return _login(*DESIGNER)


@pytest.fixture(scope="module")
def tag():
    return uuid.uuid4().hex[:8]


def _create_request(admin_token, tag, brief_suffix=""):
    payload = {
        "source": "internal",
        "category_code": "BGA",
        "design_category_code": "PG",
        "brief": f"TEST_QA2 referensi {tag} {brief_suffix}".strip(),
        "assigned_to": DESIGNER_ID,
        "submit_now": True,
    }
    r = requests.post(f"{BASE_URL}/api/design-requests", json=payload,
                      headers=_h(admin_token), timeout=30)
    assert r.status_code == 200, r.text
    return r.json()


# ── BACKEND CASE 1 ────────────────────────────────────────────────────────
def test_admin_upload_references_and_get(admin_token, tag):
    req = _create_request(admin_token, tag)
    rid = req["id"]
    png = _tiny_png()

    files = {"file": ("ref1.png", png, "image/png")}
    r = requests.post(f"{BASE_URL}/api/design-requests/{rid}/references",
                      headers=_h(admin_token, multipart=True), files=files, timeout=30)
    assert r.status_code == 200, r.text
    j = r.json()
    assert "id" in j
    assert j["content_type"] == "image/png"

    # second upload with caption
    files = {"file": ("ref2.png", png, "image/png")}
    r = requests.post(f"{BASE_URL}/api/design-requests/{rid}/references?caption=acuan",
                      headers=_h(admin_token, multipart=True), files=files, timeout=30)
    assert r.status_code == 200, r.text
    assert r.json().get("caption") == "acuan"

    # verify GET detail returns 2 refs
    r = requests.get(f"{BASE_URL}/api/design-requests/{rid}",
                     headers=_h(admin_token), timeout=30)
    assert r.status_code == 200
    refs = r.json().get("references") or []
    assert len(refs) == 2, f"expected 2 refs got {len(refs)}"
    pytest.shared_rid = rid  # type: ignore
    pytest.shared_refs = refs  # type: ignore


# ── BACKEND CASE 2 ────────────────────────────────────────────────────────
def test_designer_rbac_and_bad_type(admin_token, designer_token):
    rid = pytest.shared_rid  # type: ignore
    png = _tiny_png()

    # designer upload → 403
    files = {"file": ("bad.png", png, "image/png")}
    r = requests.post(f"{BASE_URL}/api/design-requests/{rid}/references",
                      headers=_h(designer_token, multipart=True), files=files, timeout=30)
    assert r.status_code == 403, r.text

    # admin upload .txt → 400
    files = {"file": ("bad.txt", b"hello", "text/plain")}
    r = requests.post(f"{BASE_URL}/api/design-requests/{rid}/references",
                      headers=_h(admin_token, multipart=True), files=files, timeout=30)
    assert r.status_code == 400, r.text

    # designer GET reference on assigned request → 200 image/png
    fid = pytest.shared_refs[0]["id"]  # type: ignore
    r = requests.get(f"{BASE_URL}/api/design-requests/{rid}/references/{fid}",
                     headers=_h(designer_token), timeout=30)
    assert r.status_code == 200, r.text
    assert r.headers.get("content-type", "").startswith("image/")


def test_designer_get_reference_foreign_request_403(admin_token, designer_token, tag):
    # create request assigned to a DIFFERENT user (admin's own id via seed) so designer
    # has no access. Fallback: assign to nobody→admin cannot; use admin_id via /auth/me.
    me = requests.get(f"{BASE_URL}/api/auth/me", headers=_h(admin_token), timeout=15).json()
    admin_id = me.get("id") or me.get("user", {}).get("id")
    if not admin_id:
        pytest.skip("cannot resolve admin id")
    # Try to create req assigned to admin (may fail if only designers allowed);
    # else create unassigned request (skip if not allowed).
    payload = {"source": "internal", "category_code": "BGA", "design_category_code": "PG",
               "brief": f"TEST_QA2 foreign {tag}", "assigned_to": admin_id, "submit_now": False}
    r = requests.post(f"{BASE_URL}/api/design-requests", json=payload,
                      headers=_h(admin_token), timeout=30)
    if r.status_code != 200:
        pytest.skip(f"cannot create foreign request: {r.status_code} {r.text[:120]}")
    rid2 = r.json()["id"]
    png = _tiny_png()
    files = {"file": ("f.png", png, "image/png")}
    up = requests.post(f"{BASE_URL}/api/design-requests/{rid2}/references",
                       headers=_h(admin_token, multipart=True), files=files, timeout=30)
    if up.status_code != 200:
        pytest.skip(f"cannot upload to foreign req: {up.text[:120]}")
    fid = up.json()["id"]
    r = requests.get(f"{BASE_URL}/api/design-requests/{rid2}/references/{fid}",
                     headers=_h(designer_token), timeout=30)
    assert r.status_code == 403


# ── BACKEND CASE 3 ────────────────────────────────────────────────────────
def test_designer_create_design_copies_refs(designer_token, tag):
    rid = pytest.shared_rid  # type: ignore
    payload = {"title": f"TEST_QA2 Bunga {tag}"}
    r = requests.post(f"{BASE_URL}/api/design-requests/{rid}/create-design",
                      json=payload, headers=_h(designer_token), timeout=30)
    assert r.status_code == 200, r.text
    body = r.json()
    design = body.get("design") or {}
    gid = design.get("id")
    assert gid, "design.id missing"

    # history last note contains '2 referensi ikut'
    history = body.get("history") or []
    assert history, "no history"
    last = history[-1]
    assert "2 referensi ikut" in (last.get("note") or ""), f"history note: {last}"

    # GET design → files contain 2 reference-kind with source_reference_id set
    r = requests.get(f"{BASE_URL}/api/design-gallery/{gid}",
                     headers=_h(designer_token), timeout=30)
    assert r.status_code == 200, r.text
    d = r.json()
    ref_files = [f for f in (d.get("files") or []) if f.get("kind") == "reference"]
    assert len(ref_files) == 2, f"expected 2 ref files got {len(ref_files)}"
    for f in ref_files:
        assert f.get("source_reference_id"), f"missing source_reference_id in {f}"
    assert d.get("reference_count") == 2

    # GET file bytes
    file_id = ref_files[0]["id"]
    r = requests.get(f"{BASE_URL}/api/design-gallery/{gid}/files/{file_id}",
                     headers=_h(designer_token), timeout=30)
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("image/")

    pytest.shared_gid = gid  # type: ignore


# ── BACKEND CASE 4 ────────────────────────────────────────────────────────
def test_propagation_after_link_and_idempotent(admin_token, designer_token):
    rid = pytest.shared_rid  # type: ignore
    gid = pytest.shared_gid  # type: ignore
    png = _tiny_png()

    # Admin uploads a 3rd reference AFTER linked
    files = {"file": ("ref3.png", png, "image/png")}
    r = requests.post(f"{BASE_URL}/api/design-requests/{rid}/references",
                      headers=_h(admin_token, multipart=True), files=files, timeout=30)
    assert r.status_code == 200, r.text
    third_id = r.json()["id"]

    # design ref_count becomes 3
    d = requests.get(f"{BASE_URL}/api/design-gallery/{gid}",
                     headers=_h(designer_token), timeout=30).json()
    ref_files = [f for f in (d.get("files") or []) if f.get("kind") == "reference"]
    assert len(ref_files) == 3, f"expected 3 got {len(ref_files)}"

    # Idempotent: re-fetch → still 3
    d = requests.get(f"{BASE_URL}/api/design-gallery/{gid}",
                     headers=_h(designer_token), timeout=30).json()
    ref_files = [f for f in (d.get("files") or []) if f.get("kind") == "reference"]
    assert len(ref_files) == 3

    # DELETE reference on request → request references shrink by 1
    r = requests.delete(f"{BASE_URL}/api/design-requests/{rid}/references/{third_id}",
                        headers=_h(admin_token), timeout=30)
    assert r.status_code == 200, r.text
    req = requests.get(f"{BASE_URL}/api/design-requests/{rid}",
                       headers=_h(admin_token), timeout=30).json()
    assert len(req.get("references") or []) == 2

    # Design keeps its copy (expected)
    d = requests.get(f"{BASE_URL}/api/design-gallery/{gid}",
                     headers=_h(designer_token), timeout=30).json()
    ref_files = [f for f in (d.get("files") or []) if f.get("kind") == "reference"]
    assert len(ref_files) == 3, "design should keep the copy after request delete"


# ── BACKEND CASE 5 ────────────────────────────────────────────────────────
def test_link_design_copies_references(admin_token, designer_token, tag):
    # designer creates a new empty design
    payload = {"title": f"TEST_QA2 link {tag}", "category_code": "SLR",
               "design_category_code": "AO"}
    r = requests.post(f"{BASE_URL}/api/design-gallery", json=payload,
                      headers=_h(designer_token), timeout=30)
    assert r.status_code in (200, 201), r.text
    gid = r.json()["id"]

    # admin creates 2nd request with 1 ref, assigned to designer
    req = _create_request(admin_token, tag, brief_suffix="link")
    rid = req["id"]
    files = {"file": ("solo.png", _tiny_png(), "image/png")}
    r = requests.post(f"{BASE_URL}/api/design-requests/{rid}/references",
                      headers=_h(admin_token, multipart=True), files=files, timeout=30)
    assert r.status_code == 200

    # designer links
    r = requests.post(f"{BASE_URL}/api/design-requests/{rid}/link-design",
                      json={"gallery_id": gid}, headers=_h(designer_token), timeout=30)
    assert r.status_code == 200, r.text

    d = requests.get(f"{BASE_URL}/api/design-gallery/{gid}",
                     headers=_h(designer_token), timeout=30).json()
    ref_files = [f for f in (d.get("files") or []) if f.get("kind") == "reference"]
    assert len(ref_files) == 1, f"expected 1 ref file got {len(ref_files)}"
