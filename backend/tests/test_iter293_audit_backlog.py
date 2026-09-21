"""Iterasi 293 — verifikasi backlog audit 2026-09-02 (P1-1, P1-3, L-1..L-9, G-3/G-6/G-8, X-5).

Satu kelas berurutan (pytest.ini memakai --dist loadscope sehingga satu kelas = satu worker).
Membuat 2 pengiriman logistik uji (dibiarkan sebagai data demo, sesuai permintaan main agent);
notifikasi & ilustrasi AI uji dibersihkan.
"""
import io
import os

import pytest
import requests
from dotenv import dotenv_values
from pymongo import MongoClient

frontend_env = dotenv_values("/app/frontend/.env")
base_url = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not base_url:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
API = base_url.rstrip("/") + "/api"
DB = MongoClient("mongodb://localhost:27017")["test_database"]
PW = "demo12345"


def _login(email, entity="ent_ksc"):
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": email, "password": PW}, timeout=60)
    if r.status_code != 200:
        pytest.fail(f"login {email} gagal {r.status_code}: {r.text[:200]}")
    s.headers.update({"Authorization": f"Bearer {r.json()['token']}", "X-Entity-Id": entity})
    return s


def _png():
    from PIL import Image
    b = io.BytesIO()
    Image.new("RGB", (40, 40), (10, 120, 200)).save(b, format="PNG")
    return b.getvalue()


@pytest.fixture(scope="module")
def admin():
    return _login("admin@kainnusantara.id")


@pytest.fixture(scope="module")
def driver():
    return _login("driver@kainnusantara.id")


@pytest.fixture(scope="module")
def state():
    return {}


class TestAuditBacklog293:
    # ---------- SETUP + L-8 (create_delivery hanya SJ dispatched) ----------
    def test_01_l8_non_dispatched_rejected(self, admin, state):
        # re-runnable: lepaskan pengiriman uji dari jalannya sebelumnya
        old = list(DB.logistics_deliveries.find({"$or": [{"vehicle_plate": "B 1 QA"},
                                                         {"tracking_no": "JNE123"}]}, {"_id": 0, "id": 1}))
        if old:
            ids = [d["id"] for d in old]
            DB.logistics_deliveries.delete_many({"id": {"$in": ids}})
            DB.shipments.update_many({"logistics_id": {"$in": ids}},
                                     {"$set": {"logistics_id": "", "logistics_number": "",
                                               "logistics_status": "", "status": "dispatched"}})
        free = list(DB.shipments.find({"status": "dispatched", "entity_id": "ent_ksc",
                                       "logistics_id": {"$in": [None, ""]}},
                                      {"_id": 0, "id": 1, "shipment_no": 1}).limit(2))
        assert len(free) >= 2, f"butuh 2 SJ dispatched bebas, ada {len(free)}"
        state["ship_a"], state["ship_b"] = free[0], free[1]
        DB.shipments.update_one({"id": free[0]["id"]}, {"$set": {"status": "cancelled_qa"}})
        try:
            r = admin.post(f"{API}/logistics/deliveries",
                           json={"shipment_ids": [free[0]["id"]], "mode": "own_fleet"}, timeout=60)
            assert r.status_code == 400, f"{r.status_code} {r.text[:200]}"
            assert "dispatch" in r.text.lower(), r.text[:200]
        finally:
            DB.shipments.update_one({"id": free[0]["id"]}, {"$set": {"status": "dispatched"}})

    def test_02_create_deliveries(self, admin, state):
        r = admin.post(f"{API}/logistics/deliveries", json={
            "shipment_ids": [state["ship_a"]["id"]], "mode": "own_fleet", "vehicle_plate": "B 1 QA",
            "driver_name": "Joko Susilo", "driver_user_id": "user_driver_01", "eta": "2026-01-01"}, timeout=60)
        assert r.status_code == 200, r.text[:300]
        a = r.json()
        assert a["status"] == "prepared" and a["number"].startswith("KSC/LG-") or a["number"], a
        assert a["driver_user_id"] == "user_driver_01"
        assert "_id" not in a
        state["A"] = a
        r = admin.post(f"{API}/logistics/deliveries", json={
            "shipment_ids": [state["ship_b"]["id"]], "mode": "expedition",
            "courier_name": "JNE", "tracking_no": "JNE123"}, timeout=60)
        assert r.status_code == 200, r.text[:300]
        b = r.json()
        assert not b.get("driver_user_id")
        state["B"] = b
        # GET verify persistence
        g = admin.get(f"{API}/logistics/deliveries/{a['id']}", timeout=60)
        assert g.status_code == 200 and g.json()["vehicle_plate"] == "B 1 QA"

    # ---------- P1-1 ----------
    def test_03_p1_1_driver_write_guard(self, driver, state):
        b = state["B"]["id"]
        r = driver.post(f"{API}/logistics/deliveries/{b}/photos",
                        files={"file": ("a.png", _png(), "image/png")}, data={"kind": "load"}, timeout=60)
        assert r.status_code == 403 and "bukan tugas Anda" in r.text, f"{r.status_code} {r.text[:200]}"
        r = driver.post(f"{API}/logistics/deliveries/{b}/transition", json={"to": "loaded"}, timeout=60)
        assert r.status_code == 403, r.status_code
        r = driver.post(f"{API}/logistics/deliveries/{b}/positions",
                        json={"location": "QA", "lat": -6.2, "lng": 106.8}, timeout=60)
        assert r.status_code == 403, r.status_code

    def test_04_p1_1_driver_read_allowed(self, driver, state):
        r = driver.get(f"{API}/logistics/deliveries/{state['B']['id']}", timeout=60)
        assert r.status_code == 200, r.text[:200]
        r = driver.get(f"{API}/logistics/deliveries", timeout=60)
        assert r.status_code == 200
        ids = [d["id"] for d in r.json()]
        assert state["A"]["id"] in ids and state["B"]["id"] in ids, ids[:5]

    def test_05_driver_write_own_allowed(self, driver, state):
        r = driver.post(f"{API}/logistics/deliveries/{state['A']['id']}/photos",
                        files={"file": ("load.png", _png(), "image/png")},
                        data={"kind": "load"}, timeout=60)
        assert r.status_code == 200, f"{r.status_code} {r.text[:200]}"
        assert r.json()["kind"] == "load"

    # ---------- P1-3 ----------
    def test_06_p1_3_unload(self, admin, driver, state):
        a = state["A"]["id"]
        r = driver.post(f"{API}/logistics/deliveries/{a}/transition", json={"to": "loaded"}, timeout=60)
        assert r.status_code == 200 and r.json()["status"] == "loaded", r.text[:200]
        r = driver.post(f"{API}/logistics/deliveries/{a}/transition",
                        json={"to": "prepared", "reason": "salah"}, timeout=60)
        assert r.status_code == 403, f"{r.status_code} {r.text[:200]}"
        r = admin.post(f"{API}/logistics/deliveries/{a}/transition", json={"to": "prepared"}, timeout=60)
        assert r.status_code == 400 and "Alasan" in r.text, r.text[:200]
        r = admin.post(f"{API}/logistics/deliveries/{a}/transition",
                       json={"to": "prepared", "reason": "salah tekan tombol"}, timeout=60)
        assert r.status_code == 200, r.text[:200]
        doc = r.json()
        assert doc["status"] == "prepared"
        assert doc.get("loaded_at") is None, doc.get("loaded_at")
        assert any("salah tekan tombol" in (t.get("note") or "") for t in doc["timeline"])
        # kembali ke loaded untuk lanjut alur
        r = admin.post(f"{API}/logistics/deliveries/{a}/transition", json={"to": "loaded"}, timeout=60)
        assert r.status_code == 200 and r.json()["status"] == "loaded", r.text[:200]

    # ---------- L-2 ----------
    def test_07_l2_position_validation_and_delete(self, admin, driver, state):
        a = state["A"]["id"]
        r = driver.post(f"{API}/logistics/deliveries/{a}/positions",
                        json={"location": "Cikampek", "lat": 999, "lng": -999}, timeout=60)
        assert r.status_code == 422, f"{r.status_code} {r.text[:200]}"
        r = driver.post(f"{API}/logistics/deliveries/{a}/positions",
                        json={"location": "Cikampek", "lat": -6.4, "lng": 107.4}, timeout=60)
        assert r.status_code == 200, r.text[:200]
        pos = r.json()["positions"][-1]
        assert pos["lat"] == -6.4 and pos["location"] == "Cikampek"
        r = driver.delete(f"{API}/logistics/deliveries/{a}/positions/{pos['id']}", timeout=60)
        assert r.status_code == 403, r.status_code
        r = admin.delete(f"{API}/logistics/deliveries/{a}/positions/{pos['id']}", timeout=60)
        assert r.status_code == 200 and r.json()["deleted"] is True, r.text[:200]
        g = admin.get(f"{API}/logistics/deliveries/{a}", timeout=60)
        assert all(p["id"] != pos["id"] for p in g.json().get("positions") or [])

    # ---------- L-3 (aktif) ----------
    def test_08_l3_my_route_active(self, driver, state):
        r = driver.post(f"{API}/logistics/my-route", json={"ids": [state["A"]["id"]]}, timeout=60)
        assert r.status_code == 200 and r.json()["updated"] == 1, r.text[:200]

    # ---------- L-4 + L-9 ----------
    def test_09_l4_combined_message_and_delivered(self, admin, driver, state):
        a = state["A"]["id"]
        r = admin.post(f"{API}/logistics/deliveries/{a}/transition", json={"to": "in_transit"}, timeout=60)
        assert r.status_code == 200 and r.json()["status"] == "in_transit", r.text[:200]
        r = driver.post(f"{API}/logistics/deliveries/{a}/transition", json={"to": "delivered"}, timeout=60)
        assert r.status_code == 400, r.status_code
        assert "POD" in r.text and "NAMA PENERIMA" in r.text, r.text[:300]
        r = driver.post(f"{API}/logistics/deliveries/{a}/photos",
                        files={"file": ("pod.png", _png(), "image/png")}, data={"kind": "pod"}, timeout=60)
        assert r.status_code == 200, r.text[:200]
        r = driver.post(f"{API}/logistics/deliveries/{a}/transition",
                        json={"to": "delivered", "receiver_name": "Bu Ani"}, timeout=60)
        assert r.status_code == 200, r.text[:300]
        doc = r.json()
        assert doc["status"] == "delivered" and doc["pod"]["receiver_name"] == "Bu Ani"

    def test_10_l9_notification_to_sales(self, state):
        notif = list(DB.notifications.find({"type": "logistics_delivered"}, {"_id": 0}))
        assert notif, "tidak ada notifikasi logistics_delivered"
        recips = {n.get("recipient_user") for n in notif}
        assert any(str(r or "").startswith("user_sales") for r in recips), recips

    def test_11_l3_my_route_inactive_rejected(self, driver, state):
        r = driver.post(f"{API}/logistics/my-route", json={"ids": [state["A"]["id"]]}, timeout=60)
        assert r.status_code == 400, f"{r.status_code} {r.text[:200]}"

    # ---------- L-1 ----------
    def test_12_l1_summary_today_wib(self, admin):
        import re
        from datetime import datetime
        from zoneinfo import ZoneInfo
        r = admin.get(f"{API}/logistics/summary", timeout=60)
        assert r.status_code == 200, r.text[:200]
        today = r.json().get("today")
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(today)), today
        assert today == datetime.now(ZoneInfo("Asia/Jakarta")).strftime("%Y-%m-%d"), today

    # ---------- P1-2 (data pendukung chip) ----------
    def test_13_p1_2_shipment_carries_logistics(self, state):
        sj = DB.shipments.find_one({"id": state["ship_a"]["id"]},
                                   {"_id": 0, "logistics_number": 1, "logistics_status": 1, "logistics_id": 1})
        assert sj.get("logistics_status") == "delivered", sj
        assert sj.get("logistics_number") == state["A"]["number"], sj

    # ---------- G-3 / G-8 ----------
    def test_14_g3_ai_status_keys(self, admin):
        r = admin.get(f"{API}/design-gallery-ai/status", timeout=60)
        assert r.status_code == 200, r.text[:200]
        data = r.json()
        for k in ("enabled", "demo", "verified", "model", "daily_limit", "cost_per_image_usd"):
            assert k in data, f"key {k} hilang: {data}"
        assert data["demo"] is True

    def test_15_g3_gemini_test_without_key(self, admin):
        r = admin.post(f"{API}/admin/integrations/gemini/test", timeout=60)
        assert r.status_code == 400, f"{r.status_code} {r.text[:200]}"

    def test_16_g8_daily_limit(self, admin, state):
        r = admin.put(f"{API}/admin/integrations", json={"gemini_daily_limit": 1}, timeout=60)
        assert r.status_code == 200 and r.json()["gemini"]["daily_limit"] == 1, r.text[:200]
        g = DB.design_gallery.find_one({"entity_id": "ent_ksc"}, {"_id": 0, "id": 1})
        state["gid"] = g["id"]
        r1 = admin.post(f"{API}/design-gallery/{g['id']}/ai-illustrate",
                        json={"mode": "mockup", "prompt": "qa uji batas harian"}, timeout=120)
        r2 = admin.post(f"{API}/design-gallery/{g['id']}/ai-illustrate",
                        json={"mode": "mockup", "prompt": "qa uji batas harian"}, timeout=120)
        assert r1.status_code == 200, r1.text[:200]
        state["fid"] = r1.json()["id"]
        assert r2.status_code == 400 and "Batas" in r2.text, f"{r2.status_code} {r2.text[:200]}"
        rr = admin.put(f"{API}/admin/integrations", json={"gemini_daily_limit": 10}, timeout=60)
        assert rr.status_code == 200 and rr.json()["gemini"]["daily_limit"] == 10

    # ---------- G-6 ----------
    def test_17_g6_comment_notification_and_delete(self, admin, state):
        gid, fid = state["gid"], state["fid"]
        before = DB.notifications.count_documents({"type": "design_ai_comment"})
        r = admin.post(f"{API}/design-gallery/{gid}/files/{fid}/comments",
                       json={"text": "Perbesar motif"}, timeout=60)
        assert r.status_code == 200, r.text[:200]
        cid = r.json()["id"]
        assert DB.notifications.count_documents({"type": "design_ai_comment"}) > before
        designer = _login("designer@kainnusantara.id")
        r = designer.delete(f"{API}/design-gallery/{gid}/files/{fid}/comments/{cid}", timeout=60)
        assert r.status_code == 400, f"{r.status_code} {r.text[:200]}"
        r = admin.delete(f"{API}/design-gallery/{gid}/files/{fid}/comments/{cid}", timeout=60)
        assert r.status_code == 200, r.text[:200]

    # ---------- X-5 ----------
    def test_18_x5_logistics_division(self, admin):
        r = admin.get(f"{API}/rnd/divisions", timeout=60)
        assert r.status_code == 200, r.text[:200]
        data = r.json()
        rows = data if isinstance(data, list) else data.get("divisions") or data.get("items") or []
        row = next((d for d in rows if d.get("id") == "logistics"), None)
        assert row is not None, rows
        assert row.get("name") == "Logistik", row

    # ---------- cleanup ----------
    def test_99_cleanup(self, admin, state):
        if state.get("fid"):
            admin.delete(f"{API}/design-gallery/{state['gid']}/files/{state['fid']}", timeout=60)
        DB.notifications.delete_many({"type": {"$in": ["logistics_delivered", "design_ai_comment"]}})
        assert True
