"""Iter 43 — spesifikasi produk WAJIB pada permintaan sample (labdip/handfeel/proofing).
Cakupan: validasi 400 tanpa spec, validasi per-jenis, create labdip valid, create handfeel valid,
POST /samples/{id}/spec (idempoten & untuk sample lama), attach_spec_summaries pada list.
"""
import os
import uuid
import pytest
import requests
from pathlib import Path


def _load_backend_url():
    v = os.environ.get("REACT_APP_BACKEND_URL")
    if v:
        return v.rstrip("/")
    env = Path("/app/frontend/.env")
    for line in env.read_text().splitlines():
        if line.startswith("REACT_APP_BACKEND_URL="):
            return line.split("=", 1)[1].strip().rstrip("/")
    raise RuntimeError("REACT_APP_BACKEND_URL not set")


BASE = _load_backend_url()
ENT = "ent_ksc"


@pytest.fixture(scope="module")
def admin_headers():
    r = requests.post(f"{BASE}/api/auth/login",
                      json={"email": "admin@kainnusantara.id", "password": "demo12345"})
    assert r.status_code == 200, r.text
    tok = r.json()["token"]
    return {"Authorization": f"Bearer {tok}", "X-Entity-Id": ENT,
            "Content-Type": "application/json"}


def _uniq(prefix): return f"{prefix}-{uuid.uuid4().hex[:6]}"


# -------- Validation errors ----------
class TestSpecRequiredValidation:
    def test_no_spec_returns_400(self, admin_headers):
        r = requests.post(f"{BASE}/api/rnd/samples", headers=admin_headers, json={
            "sample_types": ["handfeel"], "title": "Tanpa spec", "unit": "meter",
            "qty_requested": 2,
        })
        assert r.status_code == 400, r.text
        assert "Spesifikasi produk WAJIB" in r.text

    def test_labdip_missing_color_target_400(self, admin_headers):
        r = requests.post(f"{BASE}/api/rnd/samples", headers=admin_headers, json={
            "sample_types": ["labdip"], "title": "Labdip tanpa warna", "unit": "meter",
            "qty_requested": 2,
            "spec": {"target": {"fabric_type": "woven", "gramasi": 200},
                     "sku_hint": _uniq("TST-LB")},
        })
        assert r.status_code == 400, r.text
        assert "warna target" in r.text.lower()

    def test_proofing_missing_design_400(self, admin_headers):
        r = requests.post(f"{BASE}/api/rnd/samples", headers=admin_headers, json={
            "sample_types": ["proofing"], "title": "Proofing tanpa desain", "unit": "meter",
            "qty_requested": 2,
            "spec": {"target": {"fabric_type": "woven", "gramasi": 200},
                     "sku_hint": _uniq("TST-PR")},
        })
        assert r.status_code == 400, r.text
        assert "desain" in r.text.lower()

    def test_spec_missing_fabric_type_400(self, admin_headers):
        r = requests.post(f"{BASE}/api/rnd/samples", headers=admin_headers, json={
            "sample_types": ["handfeel"], "title": "Handfeel tanpa fabric", "unit": "meter",
            "qty_requested": 2,
            "spec": {"target": {"gramasi": 200}, "sku_hint": _uniq("TST-HF")},
        })
        assert r.status_code == 400, r.text
        assert "jenis kain" in r.text.lower()


# -------- Happy path ----------
class TestCreateWithSpec:
    def test_handfeel_valid_creates_spec_and_persists(self, admin_headers):
        sku = _uniq("TST-HF")
        r = requests.post(f"{BASE}/api/rnd/samples", headers=admin_headers, json={
            "sample_types": ["handfeel"], "title": "Handfeel valid", "unit": "meter",
            "qty_requested": 2,
            "spec": {
                "target": {"fabric_type": "knit", "gramasi": 180, "lebar": 170,
                           "yarn_count": "30s", "yarn_count_system": "Ne"},
                "sku_hint": sku,
            },
        })
        assert r.status_code == 200, r.text
        doc = r.json()
        assert doc.get("spec_id"), doc
        assert doc.get("spec_number"), doc
        sid = doc["id"]

        # GET single
        g = requests.get(f"{BASE}/api/rnd/samples/{sid}", headers=admin_headers)
        assert g.status_code == 200
        gj = g.json()
        assert gj["spec"]["target"]["gramasi"] == 180
        assert gj["spec"]["target"]["yarn_count"] == "30s"
        assert gj.get("master_data", {}).get("spec")

        # LIST → spec_summary
        lst = requests.get(f"{BASE}/api/rnd/samples", headers=admin_headers,
                           params={"entity_id": ENT, "limit": 500})
        assert lst.status_code == 200
        items = lst.json()["items"]
        row = next((it for it in items if it["id"] == sid), None)
        assert row is not None
        ss = row.get("spec_summary") or {}
        assert ss.get("fabric_type") == "knit"
        assert ss.get("gramasi") == 180

    def test_labdip_valid(self, admin_headers):
        sku = _uniq("TST-LB")
        r = requests.post(f"{BASE}/api/rnd/samples", headers=admin_headers, json={
            "sample_types": ["labdip"], "title": "Labdip valid", "unit": "meter",
            "qty_requested": 2,
            "spec": {"target": {"fabric_type": "woven", "gramasi": 200},
                     "color_target": {"color_id": "col_kn_blu_01"},
                     "sku_hint": sku},
        })
        assert r.status_code == 200, r.text
        doc = r.json()
        assert doc.get("spec_id"), doc
        self._sid = doc["id"]  # not used across tests but keep for clarity

    def test_attach_spec_twice_returns_400(self, admin_headers):
        # Create one with spec, then try to attach again.
        sku = _uniq("TST-DUP")
        r = requests.post(f"{BASE}/api/rnd/samples", headers=admin_headers, json={
            "sample_types": ["handfeel"], "title": "Handfeel dup spec", "unit": "meter",
            "qty_requested": 1,
            "spec": {"target": {"fabric_type": "woven", "gramasi": 210},
                     "sku_hint": sku},
        })
        assert r.status_code == 200, r.text
        sid = r.json()["id"]
        r2 = requests.post(f"{BASE}/api/rnd/samples/{sid}/spec", headers=admin_headers,
                          json={"target": {"fabric_type": "woven", "gramasi": 220},
                                "sku_hint": _uniq("TST-DUP2")})
        assert r2.status_code == 400, r2.text
        assert "sudah punya spesifikasi" in r2.text.lower()


# -------- Legacy attach ----------
class TestAttachLegacySpec:
    def test_attach_spec_on_legacy_sample(self, admin_headers):
        lst = requests.get(f"{BASE}/api/rnd/samples", headers=admin_headers,
                           params={"entity_id": ENT, "limit": 500})
        assert lst.status_code == 200
        items = lst.json()["items"]
        legacy = next((it for it in items if not it.get("spec_id")), None)
        if not legacy:
            pytest.skip("Tidak ada sample lama tanpa spec_id")
        sid = legacy["id"]
        r = requests.post(f"{BASE}/api/rnd/samples/{sid}/spec", headers=admin_headers, json={
            "target": {"fabric_type": "woven", "gramasi": 200},
            "color_target": {"color_id": "col_kn_blu_01"},
            "sku_hint": _uniq("TST-LEG"),
        })
        assert r.status_code == 200, r.text
        j = r.json()
        assert j.get("spec_number"), j
        # confirm via GET
        g = requests.get(f"{BASE}/api/rnd/samples/{sid}", headers=admin_headers)
        assert g.status_code == 200
        assert g.json().get("spec")
