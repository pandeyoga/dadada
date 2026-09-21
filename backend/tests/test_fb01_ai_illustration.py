"""FB-01 — AI Galeri Desain (Gemini Nano Banana Pro, MODE DEMO) backend tests."""
import os

import pytest
import requests
from dotenv import dotenv_values

frontend_env = dotenv_values("/app/frontend/.env")
base_url = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not base_url:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
BASE_URL = base_url.rstrip("/")
ENT = "ent_ksc"
PWD = "demo12345"
DSG_PARANG = "dsgn_cf2ccad1866f"   # has 1 artwork
DSG_TENUN = "dsgn_1e14c842fa9b"    # no artwork


def _login(email):
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": PWD}, timeout=60)
    assert r.status_code == 200, f"login {email} -> {r.status_code} {r.text[:300]}"
    tok = r.json().get("token") or r.json().get("access_token")
    assert tok, f"no token in {r.json().keys()}"
    return tok


def _h(token, write=True):
    h = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    if write:
        h["X-Entity-Id"] = ENT
    return h


@pytest.fixture(scope="module")
def admin():
    return _login("admin@kainnusantara.id")


@pytest.fixture(scope="module")
def designer():
    return _login("designer@kainnusantara.id")


@pytest.fixture(scope="module")
def sales():
    return _login("sales@kainnusantara.id")


@pytest.fixture(scope="module", autouse=True)
def restore_integrations(admin):
    yield
    requests.put(f"{BASE_URL}/api/admin/integrations",
                 json={"gemini_enabled": True, "gemini_clear_key": True},
                 headers=_h(admin), timeout=60)


# ── status endpoint ────────────────────────────────────────────────
class TestStatus:
    def test_status_demo_mode(self, admin):
        r = requests.get(f"{BASE_URL}/api/design-gallery-ai/status", headers=_h(admin, False), timeout=60)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert d["enabled"] is True
        assert d["demo"] is True
        assert d["model"] == "gemini-3-pro-image-preview", d


# ── mockup happy path ──────────────────────────────────────────────
class TestIllustrateMockup:
    def test_mockup_creates_ai_illustration_file(self, admin):
        before = requests.get(f"{BASE_URL}/api/design-gallery/{DSG_PARANG}",
                              headers=_h(admin, False), timeout=60).json()
        n_art_before = len([f for f in before.get("files", [])
                            if (f.get("kind") or "artwork") != "ai_illustration"])
        r = requests.post(f"{BASE_URL}/api/design-gallery/{DSG_PARANG}/ai-illustrate",
                          json={"mode": "mockup", "prompt": "TEST_ mockup kemeja batik parang studio"},
                          headers=_h(admin), timeout=180)
        assert r.status_code == 200, r.text[:400]
        f = r.json()
        assert f["kind"] == "ai_illustration"
        assert f["ai"]["demo"] is True
        assert f["ai"]["model"] == "demo-local"
        assert f["ai"]["mode"] == "mockup"
        assert f["ai"]["source_file_id"], "source_file_id must be set (design has artwork)"
        assert f["content_type"] == "image/png"
        assert f["size"] > 1000
        assert "_id" not in f
        fid = f["id"]

        # file bytes served as png
        rf = requests.get(f"{BASE_URL}/api/design-gallery/{DSG_PARANG}/files/{fid}",
                          headers={"Authorization": _h(admin, False)["Authorization"]}, timeout=60)
        assert rf.status_code == 200
        assert rf.headers.get("content-type", "").startswith("image/png")
        assert rf.content[:4] == b"\x89PNG"

        # design doc reflects the file; version/status unchanged
        after = requests.get(f"{BASE_URL}/api/design-gallery/{DSG_PARANG}",
                             headers=_h(admin, False), timeout=60).json()
        ai_files = [x for x in after["files"] if x.get("kind") == "ai_illustration"]
        assert fid in [x["id"] for x in ai_files]
        n_art_after = len([x for x in after["files"] if (x.get("kind") or "artwork") != "ai_illustration"])
        assert n_art_after == n_art_before, "artwork count must be unaffected"
        assert after.get("version") == before.get("version")
        assert after.get("status") == before.get("status")

        # cleanup: delete file
        rd = requests.delete(f"{BASE_URL}/api/design-gallery/{DSG_PARANG}/files/{fid}",
                             headers=_h(admin), timeout=60)
        assert rd.status_code == 200, rd.text[:300]
        assert rd.json().get("deleted") is True
        final = requests.get(f"{BASE_URL}/api/design-gallery/{DSG_PARANG}",
                             headers=_h(admin, False), timeout=60).json()
        assert fid not in [x["id"] for x in final["files"]]


# ── validation ─────────────────────────────────────────────────────
class TestValidation:
    def test_modify_without_artwork_400(self, admin):
        r = requests.post(f"{BASE_URL}/api/design-gallery/{DSG_TENUN}/ai-illustrate",
                          json={"mode": "modify", "prompt": "TEST_ ubah warna jadi indigo"},
                          headers=_h(admin), timeout=180)
        assert r.status_code == 400, r.text[:300]
        assert "artwork acuan" in r.json().get("detail", "").lower() or \
               "minimal 1 artwork" in r.json().get("detail", "")

    def test_mockup_without_artwork_ok_text_only(self, admin):
        r = requests.post(f"{BASE_URL}/api/design-gallery/{DSG_TENUN}/ai-illustrate",
                          json={"mode": "mockup", "prompt": "TEST_ mockup kain tenun tanpa acuan"},
                          headers=_h(admin), timeout=180)
        assert r.status_code == 200, r.text[:400]
        f = r.json()
        assert f["kind"] == "ai_illustration"
        assert f["ai"]["source_file_id"] == ""
        requests.delete(f"{BASE_URL}/api/design-gallery/{DSG_TENUN}/files/{f['id']}",
                        headers=_h(admin), timeout=60)

    def test_invalid_mode_400(self, admin):
        r = requests.post(f"{BASE_URL}/api/design-gallery/{DSG_PARANG}/ai-illustrate",
                          json={"mode": "aneh", "prompt": "TEST_ mode salah"},
                          headers=_h(admin), timeout=120)
        assert r.status_code == 400, r.text[:300]

    def test_short_prompt_422(self, admin):
        r = requests.post(f"{BASE_URL}/api/design-gallery/{DSG_PARANG}/ai-illustrate",
                          json={"mode": "mockup", "prompt": "ab"},
                          headers=_h(admin), timeout=120)
        assert r.status_code == 422, r.text[:300]

    def test_invalid_source_file_400(self, admin):
        r = requests.post(f"{BASE_URL}/api/design-gallery/{DSG_PARANG}/ai-illustrate",
                          json={"mode": "mockup", "prompt": "TEST_ acuan tidak ada",
                                "source_file_id": "file_zzzzzzzz"},
                          headers=_h(admin), timeout=120)
        assert r.status_code == 400, r.text[:300]


# ── submit gate: ai_illustration is not artwork ────────────────────
class TestSubmitGate:
    def test_submit_with_only_ai_illustration_fails(self, admin):
        c = requests.post(f"{BASE_URL}/api/design-gallery",
                          json={"title": "TEST_Uji AI FB01"}, headers=_h(admin), timeout=60)
        assert c.status_code == 200, c.text[:300]
        gid = c.json()["id"]
        try:
            r = requests.post(f"{BASE_URL}/api/design-gallery/{gid}/ai-illustrate",
                              json={"mode": "mockup", "prompt": "TEST_ ilustrasi arahan saja"},
                              headers=_h(admin), timeout=180)
            assert r.status_code == 200, r.text[:400]
            s = requests.post(f"{BASE_URL}/api/design-gallery/{gid}/submit",
                              headers=_h(admin), timeout=60)
            assert s.status_code == 400, f"expected 400, got {s.status_code} {s.text[:300]}"
            assert "artwork" in s.json().get("detail", "").lower()
        finally:
            d = requests.delete(f"{BASE_URL}/api/design-gallery/{gid}", headers=_h(admin), timeout=60)
            assert d.status_code == 200, d.text[:200]


# ── integrations settings ──────────────────────────────────────────
class TestIntegrations:
    def test_gemini_section_present(self, admin):
        r = requests.get(f"{BASE_URL}/api/admin/integrations", headers=_h(admin, False), timeout=60)
        assert r.status_code == 200, r.text[:300]
        g = r.json().get("gemini")
        assert g, r.json()
        assert g["has_key"] is False
        assert g["enabled"] is True
        assert g["demo_mode"] is True
        assert g["model"] == "gemini-3-pro-image-preview"
        assert isinstance(g["models_available"], list) and len(g["models_available"]) >= 1

    def test_disable_then_restore(self, admin):
        r = requests.put(f"{BASE_URL}/api/admin/integrations", json={"gemini_enabled": False},
                         headers=_h(admin), timeout=60)
        assert r.status_code == 200, r.text[:300]
        st = requests.get(f"{BASE_URL}/api/design-gallery-ai/status", headers=_h(admin, False), timeout=60)
        assert st.json()["enabled"] is False, st.json()
        bad = requests.post(f"{BASE_URL}/api/design-gallery/{DSG_PARANG}/ai-illustrate",
                            json={"mode": "mockup", "prompt": "TEST_ harus ditolak"},
                            headers=_h(admin), timeout=120)
        assert bad.status_code == 400, bad.text[:300]
        assert "dinonaktifkan" in bad.json().get("detail", "").lower()
        rr = requests.put(f"{BASE_URL}/api/admin/integrations", json={"gemini_enabled": True},
                          headers=_h(admin), timeout=60)
        assert rr.status_code == 200
        assert requests.get(f"{BASE_URL}/api/design-gallery-ai/status",
                            headers=_h(admin, False), timeout=60).json()["enabled"] is True

    def test_set_and_clear_key(self, admin):
        r = requests.put(f"{BASE_URL}/api/admin/integrations", json={"gemini_api_key": "AIzaDUMMY"},
                         headers=_h(admin), timeout=60)
        assert r.status_code == 200, r.text[:300]
        g = requests.get(f"{BASE_URL}/api/admin/integrations",
                         headers=_h(admin, False), timeout=60).json()["gemini"]
        assert g["has_key"] is True and g["demo_mode"] is False, g
        assert requests.get(f"{BASE_URL}/api/design-gallery-ai/status",
                            headers=_h(admin, False), timeout=60).json()["demo"] is False
        r2 = requests.put(f"{BASE_URL}/api/admin/integrations", json={"gemini_clear_key": True},
                          headers=_h(admin), timeout=60)
        assert r2.status_code == 200
        g2 = requests.get(f"{BASE_URL}/api/admin/integrations",
                          headers=_h(admin, False), timeout=60).json()["gemini"]
        assert g2["has_key"] is False and g2["demo_mode"] is True, g2


# ── RBAC ───────────────────────────────────────────────────────────
class TestRBAC:
    def test_designer_can_illustrate(self, designer, admin):
        r = requests.post(f"{BASE_URL}/api/design-gallery/{DSG_PARANG}/ai-illustrate",
                          json={"mode": "modify", "prompt": "TEST_ desainer minta modifikasi warna"},
                          headers=_h(designer), timeout=180)
        assert r.status_code == 200, r.text[:400]
        f = r.json()
        assert f["ai"]["mode"] == "modify"
        requests.delete(f"{BASE_URL}/api/design-gallery/{DSG_PARANG}/files/{f['id']}",
                        headers=_h(admin), timeout=60)

    def test_sales_forbidden(self, sales):
        r = requests.post(f"{BASE_URL}/api/design-gallery/{DSG_PARANG}/ai-illustrate",
                          json={"mode": "mockup", "prompt": "TEST_ sales tidak boleh"},
                          headers=_h(sales), timeout=120)
        assert r.status_code == 403, f"expected 403, got {r.status_code} {r.text[:300]}"
