"""Iteration 40 tests: Design gallery final source files, RND sample spec consolidation & decide flow."""
import os
import uuid
import time
import json
import requests
import pytest

def _read_env():
    try:
        for line in open("/app/frontend/.env"):
            if line.startswith("REACT_APP_BACKEND_URL"):
                return line.split("=", 1)[1].strip()
    except Exception:
        return ""
    return ""


BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or _read_env()).rstrip("/")
ENTITY = "ent_ksc"
DESIGN_ID = "dsgn_544db49b7e6c"
SUPPLIER_ID = "sup_a05908473e52"
COLOR_ID = "col_kn_blu_01"


def _login(email, password="demo12345"):
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, f"login failed for {email}: {r.status_code} {r.text[:200]}"
    return r.json()["token"]


@pytest.fixture(scope="module")
def admin_token():
    return _login("admin@kainnusantara.id")


@pytest.fixture(scope="module")
def manager_token():
    return _login("manager@kainnusantara.id")


def _headers(token, upload=False):
    h = {"Authorization": f"Bearer {token}", "X-Entity-Id": ENTITY}
    if not upload:
        h["Content-Type"] = "application/json"
    return h


# --- Design gallery final requirement -----------------------------------
class TestDesignGallery:
    def test_final_requirement_no_colorway(self, admin_token):
        r = requests.get(f"{BASE_URL}/api/design-gallery/{DESIGN_ID}", headers=_headers(admin_token))
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        final = data.get("final")
        assert final is not None, "final missing"
        assert final.get("mockup_required") == 1
        assert final.get("source_required") == 1
        assert "mockup_files" in final and "source_files" in final
        assert "complete" in final
        assert data.get("colorway_required", 0) == 0, f"colorway_required={data.get('colorway_required')}"

    def test_upload_source_file_and_download_and_delete(self, admin_token):
        # upload a non-image .zip-like bytes as source
        content = b"PK\x03\x04TEST_SOURCE_FILE_ZIP_BYTES_" + uuid.uuid4().hex.encode()
        files = {"file": (f"TEST_source_{uuid.uuid4().hex[:6]}.zip", content, "application/zip")}
        r = requests.post(
            f"{BASE_URL}/api/design-gallery/{DESIGN_ID}/files-kind/source",
            headers=_headers(admin_token, upload=True),
            files=files,
        )
        assert r.status_code in (200, 201), f"upload source failed {r.status_code} {r.text[:300]}"
        fmeta = r.json()
        assert fmeta.get("kind") == "source", f"kind not source: {fmeta}"
        fid = fmeta.get("id")
        assert fid

        # download with Content-Disposition attachment
        r2 = requests.get(
            f"{BASE_URL}/api/design-gallery/{DESIGN_ID}/files/{fid}?download=1",
            headers=_headers(admin_token),
        )
        assert r2.status_code == 200, r2.text[:200]
        cd = r2.headers.get("Content-Disposition", "")
        assert "attachment" in cd.lower(), f"Content-Disposition missing attachment: {cd}"

        # cleanup
        r3 = requests.delete(
            f"{BASE_URL}/api/design-gallery/{DESIGN_ID}/files/{fid}",
            headers=_headers(admin_token),
        )
        assert r3.status_code in (200, 204), r3.text[:200]

    def test_colorway_kind_still_accepted(self, admin_token):
        # tiny PNG
        png = bytes.fromhex(
            "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000"
            "000d4944415478da63f8ffff3f0300050001019cd7b3f30000000049454e44ae426082"
        )
        files = {"file": (f"TEST_cw_{uuid.uuid4().hex[:6]}.png", png, "image/png")}
        r = requests.post(
            f"{BASE_URL}/api/design-gallery/{DESIGN_ID}/files-kind/colorway",
            headers=_headers(admin_token, upload=True),
            files=files,
        )
        assert r.status_code in (200, 201), f"colorway upload failed {r.status_code} {r.text[:300]}"
        fmeta = r.json()
        if fmeta.get("id"):
            requests.delete(
                f"{BASE_URL}/api/design-gallery/{DESIGN_ID}/files/{fmeta['id']}",
                headers=_headers(admin_token),
            )

    def test_invalid_kind_rejected(self, admin_token):
        files = {"file": ("x.png", b"x", "image/png")}
        r = requests.post(
            f"{BASE_URL}/api/design-gallery/{DESIGN_ID}/files-kind/invalid",
            headers=_headers(admin_token, upload=True),
            files=files,
        )
        assert r.status_code == 400, f"expected 400 for invalid kind, got {r.status_code}"


# --- RND sample spec consolidation & decide flow -----------------------
class TestRndSampleFlow:
    sample_id = None
    round_id = None

    def test_create_sample_with_spec(self, admin_token):
        sku_hint = f"TST-XYZ-{uuid.uuid4().hex[:6].upper()}"
        body = {
            "sample_types": ["labdip"],
            "title": f"TEST_iter40_labdip {uuid.uuid4().hex[:6]}",
            "color_target": {"color_id": COLOR_ID},
            "qty_requested": 3,
            "unit": "meter",
            "spec": {
                "title": f"TEST_iter40 spec {uuid.uuid4().hex[:6]}",
                "base_unit": "meter",
                "sku_hint": sku_hint,
                "sample_type_hint": "labdip",
                "target": {"fabric_type": "woven", "gramasi": 240, "lebar": 150},
                "color_target": {"color_id": COLOR_ID},
            },
        }
        r = requests.post(f"{BASE_URL}/api/rnd/samples", headers=_headers(admin_token), data=json.dumps(body))
        assert r.status_code in (200, 201), r.text[:400]
        s = r.json()
        assert s.get("spec_id"), f"spec_id missing: {s}"
        assert s.get("spec_number"), f"spec_number missing: {s}"
        TestRndSampleFlow.sample_id = s["id"]

        # GET sample - master_data
        r2 = requests.get(f"{BASE_URL}/api/rnd/samples/{s['id']}", headers=_headers(admin_token))
        assert r2.status_code == 200
        full = r2.json()
        assert "spec" in full, "spec block missing on GET"
        md = full.get("master_data") or {}
        assert "spec" in md and "product" in md and "template" in md and "contract" in md and "supplier_item" in md and "color" in md
        assert md.get("product") is None
        assert md.get("contract") is None
        assert md.get("supplier_item") is None
        assert md.get("decided") is False

    def test_full_flow_send_submit_assess(self, admin_token):
        sid = TestRndSampleFlow.sample_id
        assert sid, "sample_id missing (previous test failed)"

        # send
        r = requests.post(
            f"{BASE_URL}/api/rnd/samples/{sid}/send",
            headers=_headers(admin_token),
            data=json.dumps({"supplier_ids": [SUPPLIER_ID], "type_codes": ["labdip"], "note": "uji"}),
        )
        assert r.status_code == 200, r.text[:300]
        s = r.json()
        assert s.get("rounds"), "rounds missing"
        rid = s["rounds"][0]["id"]
        TestRndSampleFlow.round_id = rid

        # upload attachment
        png = bytes.fromhex(
            "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000"
            "000d4944415478da63f8ffff3f0300050001019cd7b3f30000000049454e44ae426082"
        )
        r = requests.post(
            f"{BASE_URL}/api/rnd/samples/{sid}/rounds/{rid}/attachments",
            headers=_headers(admin_token, upload=True),
            files={"file": ("bukti.png", png, "image/png")},
        )
        assert r.status_code in (200, 201), r.text[:200]

        # meta -> measurement fields
        rmeta = requests.get(f"{BASE_URL}/api/rnd/meta?entity_id={ENTITY}", headers=_headers(admin_token))
        assert rmeta.status_code == 200
        meta = rmeta.json()
        fields = next((t.get("measurement_fields", []) for t in meta.get("sample_types", []) if t["value"] == "labdip"), [])
        meas = {f: 1 for f in fields}

        # submit
        r = requests.post(
            f"{BASE_URL}/api/rnd/samples/{sid}/rounds/{rid}/submit",
            headers=_headers(admin_token),
            data=json.dumps({"note": "warna oke", "measurements": meas, "cost": 100000}),
        )
        assert r.status_code == 200, r.text[:300]

        # assess
        r = requests.post(
            f"{BASE_URL}/api/rnd/samples/{sid}/rounds/{rid}/assess",
            headers=_headers(admin_token),
            data=json.dumps({"result": "acc", "score": 90, "note": "ACC uji"}),
        )
        assert r.status_code == 200, r.text[:300]
        s = r.json()
        assert s["rounds"][0]["result"] == "acc"

    def test_admin_creator_cannot_decide(self, admin_token):
        sid = TestRndSampleFlow.sample_id
        assert sid
        rmeta = requests.get(f"{BASE_URL}/api/rnd/meta?entity_id={ENTITY}", headers=_headers(admin_token))
        reason = rmeta.json()["reasons"][0]["value"]
        body = {
            "supplier_id": SUPPLIER_ID,
            "reason_code": reason,
            "price": 42500,
            "supplier_sku": "TST-SUP-01",
            "supplier_color_name": "Navy 07",
            "supplier_color_code": "NV-07",
            "approve_spec": True,
            "product_sku": f"TST-{uuid.uuid4().hex[:6].upper()}",
            "product_name": "Produk Uji",
        }
        r = requests.post(f"{BASE_URL}/api/rnd/samples/{sid}/decide", headers=_headers(admin_token), data=json.dumps(body))
        assert r.status_code == 403, f"expected 403 for creator-decide, got {r.status_code} {r.text[:200]}"

    def test_manager_decide_and_master_data(self, admin_token, manager_token):
        sid = TestRndSampleFlow.sample_id
        assert sid
        rmeta = requests.get(f"{BASE_URL}/api/rnd/meta?entity_id={ENTITY}", headers=_headers(admin_token))
        reason = rmeta.json()["reasons"][0]["value"]
        product_sku = f"TST-{uuid.uuid4().hex[:8].upper()}"
        body = {
            "supplier_id": SUPPLIER_ID,
            "reason_code": reason,
            "price": 42500,
            "supplier_sku": "TST-SUP-01",
            "supplier_color_name": "Navy 07",
            "supplier_color_code": "NV-07",
            "approve_spec": True,
            "product_sku": product_sku,
            "product_name": "Produk Uji",
        }
        r = requests.post(f"{BASE_URL}/api/rnd/samples/{sid}/decide", headers=_headers(manager_token), data=json.dumps(body))
        assert r.status_code == 200, r.text[:400]
        s = r.json()
        d = s.get("decision") or {}
        assert d.get("supplier_color_name") == "Navy 07"
        assert d.get("color_synced") is True
        assert d.get("product_sku") == product_sku
        assert d.get("master_error") in (None, "", False)
        assert d.get("contract_number"), f"contract_number missing: {d}"

        # verify master_data
        r2 = requests.get(f"{BASE_URL}/api/rnd/samples/{sid}", headers=_headers(admin_token))
        assert r2.status_code == 200
        md = r2.json().get("master_data") or {}
        prod = md.get("product") or {}
        assert prod.get("lifecycle") == "disetujui", f"product.lifecycle={prod.get('lifecycle')}"
        color = md.get("color") or {}
        variants = color.get("supplier_variants") or []
        assert any((v.get("supplier_id") == SUPPLIER_ID) for v in variants), f"supplier_variants missing supplier: {variants}"

        # verify color-library (list endpoint; filter by id)
        r3 = requests.get(f"{BASE_URL}/api/color-library?status=", headers=_headers(admin_token))
        assert r3.status_code == 200, r3.text[:200]
        colors = r3.json() if isinstance(r3.json(), list) else r3.json().get("items", [])
        target = next((c for c in colors if c.get("id") == COLOR_ID), None)
        assert target is not None, f"color {COLOR_ID} not found in library"
        cvs = target.get("supplier_variants") or []
        assert any((v.get("supplier_id") == SUPPLIER_ID) for v in cvs), f"color-library supplier variants missing: {cvs}"
