"""Iterasi 294 — D-01 penomoran atomik + PDF template berlapis (sipro doc_layout) + render."""
import os
import asyncio
import pytest
import requests
from dotenv import dotenv_values

fe = dotenv_values("/app/frontend/.env")
BASE = (os.environ.get("REACT_APP_BACKEND_URL") or fe.get("REACT_APP_BACKEND_URL")).rstrip("/")
API = f"{BASE}/api"
ENT = "ent_ksc"


@pytest.fixture(scope="session")
def admin():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": "admin@kainnusantara.id", "password": "demo12345"}, timeout=60)
    assert r.status_code == 200, r.text[:400]
    tok = r.json().get("access_token") or r.json().get("token")
    assert tok
    s.headers.update({"Authorization": f"Bearer {tok}", "X-Entity-Id": ENT, "Content-Type": "application/json"})
    return s


# ─── D-01: penomoran atomik ─────────────────────────────────────────────
class TestNumberingAtomic:
    def test_shared_mode_40_concurrent_unique(self):
        import sys
        sys.path.insert(0, "/app/backend")
        from dotenv import load_dotenv
        load_dotenv("/app/backend/.env")
        from core_utils import next_doc_number
        from db import db

        async def run():
            nums = await asyncio.gather(*[next_doc_number("qa_docs", "number", "QA-") for _ in range(40)])
            ent_nums = await asyncio.gather(
                *[next_doc_number("sales_orders", "number", "SO-", entity_id=ENT) for _ in range(30)])
            await db.number_sequences.delete_many({"doc_type": {"$regex": "^qa_docs"}})
            return nums, ent_nums

        nums, ent_nums = asyncio.get_event_loop().run_until_complete(run()) \
            if False else asyncio.run(run())
        assert len(set(nums)) == 40, f"duplikat nomor shared: {sorted(nums)}"
        seq = sorted(int(n.split("-")[1]) for n in nums)
        assert seq == list(range(seq[0], seq[0] + 40)), f"tidak berurutan: {seq}"
        assert len(set(ent_nums)) == 30, f"duplikat nomor per-entitas: {sorted(ent_nums)}"
        assert all(n.startswith("KSC/SO-") for n in ent_nums), ent_nums[:3]

    def test_customer_codes_distinct(self, admin):
        ids = []
        codes = []
        users = admin.get(f"{API}/users", timeout=60)
        sales_id = ""
        if users.status_code == 200:
            rows = users.json() if isinstance(users.json(), list) else users.json().get("users", [])
            sales_id = next((u["id"] for u in rows if u.get("role") == "sales"), "")
        for nm in ("QA Cust A", "QA Cust B"):
            r = admin.post(f"{API}/customers", json={
                "name": nm, "pic_name": "QA PIC", "phone": "0800000000", "city": "Bandung",
                "address": "Jl. QA 1", "entity_id": ENT, "assigned_sales_id": sales_id}, timeout=60)
            assert r.status_code in (200, 201), r.text[:400]
            d = r.json()
            ids.append(d.get("id"))
            codes.append(d.get("code"))
        assert len(set(codes)) == 2, codes
        assert all(c and c.startswith("CUST-") for c in codes), codes
        # cleanup langsung di Mongo (pymongo sinkron — hindari loop motor yang sudah tutup)
        from pymongo import MongoClient
        be = dotenv_values("/app/backend/.env")
        cli = MongoClient(be["MONGO_URL"])
        res = cli[be["DB_NAME"]].customers.delete_many({"name": {"$regex": "^QA Cust "}})
        assert res.deleted_count >= 2, f"cleanup gagal (ids={ids})"
        cli.close()


# ─── PDF template berlapis ──────────────────────────────────────────────
class TestPdfTemplateLayering:
    def test_layering_flow(self, admin):
        try:
            r = admin.get(f"{API}/pdf/templates", timeout=60)
            assert r.status_code == 200, r.text[:300]
            data = r.json()["data"]
            assert data[0]["doc_type"] == "__default__"
            assert any(x["doc_type"] == "invoice" for x in data)
            assert "customized" in data[0] and "version" in data[0]

            cfg_def = {"color_primary": "#1F7A45", "table": {"grid": "horizontal", "zebra": True},
                       "intro_text": "Kepada {{pihak}}, {{judul}} No. {{nomor}}."}
            r = admin.put(f"{API}/pdf/templates/__default__", json={"config": cfg_def}, timeout=60)
            assert r.status_code == 200, r.text[:300]
            assert r.json()["meta"]["version"] >= 1

            r = admin.get(f"{API}/pdf/templates/invoice", timeout=60)
            assert r.status_code == 200
            inv = r.json()
            assert inv["config"]["color_primary"] == "#1F7A45"
            assert inv["config"]["table"]["grid"] == "horizontal"
            assert inv["meta"]["customized"] is False

            cfg_inv = dict(inv["config"])
            cfg_inv["color_primary"] = "#C0392B"
            r = admin.put(f"{API}/pdf/templates/invoice", json={"config": cfg_inv}, timeout=60)
            assert r.status_code == 200, r.text[:300]
            assert r.json()["meta"]["override_keys"] == ["color_primary"], r.json()["meta"]

            bad = dict(cfg_inv)
            bad["closing_note"] = "Hai {{tidak_ada}}"
            r = admin.put(f"{API}/pdf/templates/invoice", json={"config": bad}, timeout=60)
            assert r.status_code == 400, r.status_code
            assert "laceholder" in r.json().get("detail", ""), r.text[:200]

            r = admin.post(f"{API}/pdf/templates/validate-script", json={"text": "{{nomor}} {{xx}}"}, timeout=60)
            assert r.status_code == 200
            assert r.json()["unknown"] == ["xx"] and r.json()["ok"] is False

            r = admin.delete(f"{API}/pdf/templates/invoice", timeout=60)
            assert r.status_code == 200
            assert r.json()["meta"]["customized"] is False
            assert r.json()["config"]["color_primary"] == "#1F7A45"
        finally:
            admin.delete(f"{API}/pdf/templates/invoice", timeout=60)
            admin.delete(f"{API}/pdf/templates/__default__", timeout=60)


# ─── PDF render ─────────────────────────────────────────────────────────
class TestPdfRender:
    def test_preview_and_pdf(self, admin):
        r = admin.get(f"{API}/pdf/sample/invoice", params={"entity_id": ENT}, timeout=60)
        assert r.status_code == 200, r.text[:300]
        sid = r.json().get("source_id")
        assert sid, r.json()

        cfg = {"intro_text": "Kepada {{pihak}} No. {{nomor}}", "show_place_date": True, "place": "Bandung",
               "show_materai": True, "show_generated_note": True, "header_mode": "none",
               "table": {"zebra": True, "show_header": False}, "sections": {"notes": False}}
        r = admin.post(f"{API}/pdf/preview",
                       json={"doc_type": "invoice", "source_id": sid, "entity_id": ENT, "config": cfg}, timeout=90)
        assert r.status_code == 200, r.text[:400]
        html = r.text
        assert "Kepada " in html
        intro = html.split('class="intro">')[1].split("</div>")[0] if 'class="intro">' in html else ""
        assert intro and "{{" not in intro, f"intro belum terisi: {intro!r}"
        assert "Bandung," in html
        assert "Bermeterai" in html
        assert "kop-none" in html
        assert "nth-child(even)" in html
        tbl = html.split('table class="items"')[1] if 'table class="items"' in html else html
        assert "<thead>" not in tbl.split("</table>")[0], "thead masih tercetak walau show_header=false"

        r = admin.get(f"{API}/pdf/render/invoice/{sid}", params={"format": "pdf", "entity_id": ENT}, timeout=120)
        assert r.status_code == 200, r.text[:300]
        assert r.content[:4] == b"%PDF", r.content[:20]

    def test_branding_extra_fields(self, admin):
        try:
            r = admin.put(f"{API}/pdf/branding/{ENT}",
                          json={"tagline": "QA Tagline", "email": "qa@kn.id", "website": "kn.id"}, timeout=60)
            assert r.status_code == 200, r.text[:300]
            d = r.json()
            assert d["tagline"] == "QA Tagline" and d["email"] == "qa@kn.id" and d["website"] == "kn.id"

            s = admin.get(f"{API}/pdf/sample/invoice", params={"entity_id": ENT}, timeout=60).json()
            r = admin.post(f"{API}/pdf/preview",
                           json={"doc_type": "invoice", "source_id": s["source_id"], "entity_id": ENT,
                                 "config": {"header_mode": "system"}}, timeout=90)
            assert r.status_code == 200, r.text[:300]
            assert "QA Tagline" in r.text
        finally:
            admin.put(f"{API}/pdf/branding/{ENT}", json={"tagline": "", "email": "", "website": ""}, timeout=60)


# ─── Regresi cepat ──────────────────────────────────────────────────────
class TestRegression:
    def test_endpoints_ok(self, admin):
        r = admin.get(f"{API}/logistics/deliveries", timeout=60)
        assert r.status_code == 200, r.text[:300]
        r2 = admin.get(f"{API}/pdf/doc-types", timeout=60)
        assert r2.status_code == 200, r2.text[:300]
        assert len(r2.json()) > 0
