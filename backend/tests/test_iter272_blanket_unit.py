"""ITER-272 — FIX-4 backend: unit kontrak Blanket PO wajib dari master UOM.

Cakupan:
  * POST /api/purchase-orders/blanket dengan unit ngawur ('karung') -> 400 + pesan jelas
  * POST /api/purchase-orders/blanket dengan unit master (base_unit) -> 200/201
  * call-off dengan unit != unit kontrak -> 400
"""
import os
import re
from pathlib import Path

import pytest
import requests
from dotenv import dotenv_values

frontend_env = dotenv_values("/app/frontend/.env")
base_url = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not base_url:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
BASE_URL = base_url.rstrip("/")
ENTITY = "ent_ksc"


@pytest.fixture(scope="module")
def creds():
    content = Path("/app/memory/test_credentials.md").read_text(encoding="utf-8")
    m = re.search(r"`(admin@[^`]+)`", content)
    return {"email": m.group(1) if m else "admin@kainnusantara.id", "password": "demo12345"}


@pytest.fixture(scope="module")
def client(creds):
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json", "X-Entity-Id": ENTITY})
    r = s.post(f"{BASE_URL}/api/auth/login", json=creds, timeout=60)
    if r.status_code != 200:
        pytest.fail(f"login failed {r.status_code}: {r.text[:300]}")
    token = r.json().get("token") or r.json().get("access_token")
    assert token, f"no token in {r.json().keys()}"
    s.headers.update({"Authorization": f"Bearer {token}"})
    return s


@pytest.fixture(scope="module")
def ctx(client):
    prods = client.get(f"{BASE_URL}/api/products?limit=50", timeout=60)
    assert prods.status_code == 200, prods.text[:300]
    plist = prods.json()
    plist = plist.get("items", plist) if isinstance(plist, dict) else plist
    prod = next((p for p in plist if p.get("base_unit")), plist[0])
    whs = client.get(f"{BASE_URL}/api/warehouses", timeout=60)
    assert whs.status_code == 200
    wlist = whs.json()
    wlist = wlist.get("items", wlist) if isinstance(wlist, dict) else wlist
    sups = client.get(f"{BASE_URL}/api/suppliers", timeout=60)
    slist = sups.json()
    slist = slist.get("items", slist) if isinstance(slist, dict) else slist
    # hindari pemasok yang sebenarnya badan usaha grup (ditolak 409 by design)
    banned = ("kanda", "kain suka", "ksc")
    sup = next((s for s in slist if not any(b in (s.get("name", "").lower()) for b in banned)), None)
    assert sup, "no external supplier available in seed data"
    return {"product": prod, "warehouse": wlist[0], "supplier": sup}


def _payload(ctx, unit, qty=100.0):
    return {
        "supplier_id": ctx["supplier"]["id"],
        "warehouse_id": ctx["warehouse"]["id"],
        "valid_from": "2026-01-01",
        "valid_until": "2026-12-31",
        "notes": "TEST_ITER272",
        "items": [{
            "product_id": ctx["product"]["id"],
            "contract_qty": qty,
            "contract_price": 50000,
            "unit": unit,
        }],
    }


class TestBlanketUnitValidation:
    created = []

    def test_bogus_unit_rejected(self, client, ctx):
        r = client.post(f"{BASE_URL}/api/purchase-orders/blanket", json=_payload(ctx, "karung"), timeout=60)
        assert r.status_code == 400, f"expected 400, got {r.status_code}: {r.text[:400]}"
        detail = str(r.json().get("detail", ""))
        assert "karung" in detail.lower(), detail
        assert "satuan" in detail.lower(), detail

    def test_master_unit_accepted_and_persisted(self, client, ctx):
        base_unit = ctx["product"].get("base_unit") or "meter"
        r = client.post(f"{BASE_URL}/api/purchase-orders/blanket", json=_payload(ctx, base_unit), timeout=60)
        assert r.status_code in (200, 201), f"{r.status_code}: {r.text[:500]}"
        doc = r.json()
        doc = doc.get("purchase_order", doc) if isinstance(doc, dict) else doc
        assert doc.get("po_type") == "blanket", doc.get("po_type")
        assert doc["contract_items"][0]["unit"] == base_unit
        assert "_id" not in doc
        TestBlanketUnitValidation.created.append((doc["id"], doc.get("po_number")))
        got = client.get(f"{BASE_URL}/api/purchase-orders/{doc['id']}", timeout=60)
        assert got.status_code == 200, got.text[:300]
        g = got.json()
        g = g.get("purchase_order", g)
        assert g["contract_items"][0]["unit"] == base_unit
        assert float(g["contract_items"][0]["remaining_qty"]) == 100.0

    def test_call_off_unit_mismatch_rejected(self, client, ctx):
        assert TestBlanketUnitValidation.created, "needs blanket from previous test"
        po_id = TestBlanketUnitValidation.created[0][0]
        body = {
            "items": [{
                "product_id": ctx["product"]["id"],
                "quantity": 10,
                "unit": "karung",
            }],
            "warehouse_id": ctx["warehouse"]["id"],
        }
        r = client.post(f"{BASE_URL}/api/purchase-orders/{po_id}/call-off", json=body, timeout=60)
        assert r.status_code == 400, f"expected 400, got {r.status_code}: {r.text[:500]}"
        detail = str(r.json().get("detail", "")).lower()
        assert "satuan" in detail or "unit" in detail, detail
