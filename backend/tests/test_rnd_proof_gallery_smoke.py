"""Backend smoke: attachment download endpoint for SMP-00008 rounds returns image/png."""
import os
import requests
import pytest

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") if os.environ.get("REACT_APP_BACKEND_URL") else "https://kn-erp-dev.preview.emergentagent.com"
HEADERS_ENT = {"X-Entity-Id": "ent_ksc"}


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": "admin@kainnusantara.id", "password": "demo12345"})
    assert r.status_code == 200, r.text
    return r.json()["token"]


def _find_sample_id(token, code):
    h = {"Authorization": f"Bearer {token}", **HEADERS_ENT}
    r = requests.get(f"{BASE_URL}/api/rnd/samples", headers=h, params={"entity_id": "ent_ksc"})
    assert r.status_code == 200, r.text
    data = r.json()
    items = data if isinstance(data, list) else data.get("items", [])
    for s in items:
        if code in (s.get("code") or "") or code in (s.get("number") or ""):
            return s["id"]
    raise AssertionError(f"sample {code} not found; sample list keys={items[0].keys() if items else 'empty'}")


def test_attachment_download_smp_00008(admin_token):
    h = {"Authorization": f"Bearer {admin_token}", **HEADERS_ENT}
    sid = _find_sample_id(admin_token, "SMP-00008")
    r = requests.get(f"{BASE_URL}/api/rnd/samples/{sid}", headers=h)
    assert r.status_code == 200, r.text
    sample = r.json()
    rounds = sample.get("rounds", [])
    assert rounds, "no rounds on SMP-00008"
    # find first attachment
    for rnd in rounds:
        for a in rnd.get("attachments", []):
            url = f"{BASE_URL}/api/rnd/samples/{sid}/rounds/{rnd['id']}/attachments/{a['id']}"
            r2 = requests.get(url, headers=h)
            assert r2.status_code == 200, f"{url} -> {r2.status_code} {r2.text[:200]}"
            ct = r2.headers.get("content-type", "")
            assert ct.startswith("image/"), f"unexpected content-type {ct}"
            assert len(r2.content) > 0
            print(f"OK {a['filename']} ct={ct} size={len(r2.content)}")
            return
    pytest.fail("no attachments to download on SMP-00008")
