"""Iterasi 280 — T7 (SPK makloon hasil kurang → Sebagian sampai klaim diputus),
T8 (klaim makloon tampil di /approvals/my-queue), pagar stok issue bahan."""
import os
import requests
import pytest


def _read_frontend_env():
    p = "/app/frontend/.env"
    if os.path.exists(p):
        for line in open(p):
            if line.startswith("REACT_APP_BACKEND_URL="):
                return line.split("=", 1)[1].strip()
    return ""


BASE = (os.environ.get("REACT_APP_BACKEND_URL") or _read_frontend_env()).rstrip("/")
PWD = "demo12345"


def _hdr(email):
    r = requests.post(f"{BASE}/api/auth/login", json={"email": email, "password": PWD}, timeout=30)
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}", "X-Entity-Id": "ent_ksc"}


@pytest.fixture(scope="module")
def admin():
    return _hdr("admin@kainnusantara.id")


@pytest.fixture(scope="module")
def manager():
    return _hdr("manager@kainnusantara.id")


@pytest.fixture(scope="module")
def target(admin):
    """SPK KSC dengan langkah `pending` beraliran kain (langkah sebelumnya sudah diterima)."""
    rows = requests.get(f"{BASE}/api/makloon-orders", headers=admin, timeout=30).json()
    rows = rows.get("items", rows) if isinstance(rows, dict) else rows
    for o in rows:
        if o.get("entity_id") != "ent_ksc" or o.get("status") in ("completed", "cancelled"):
            continue
        steps = o.get("steps", [])
        for i, s in enumerate(steps):
            prev_ok = i == 0 or steps[i - 1].get("status") == "received"
            if s.get("status") == "pending" and s.get("material_flow", "moves") != "service_only" and prev_ok:
                return {"order": o, "seq": int(s["seq"])}
    pytest.skip("tidak ada SPK dengan langkah pending (jalankan seed_realistic.py)")


def _detail(admin, mko_id):
    return requests.get(f"{BASE}/api/makloon-orders/{mko_id}", headers=admin, timeout=30).json()


def test_01_detail_memuat_source_stock(admin, target):
    d = _detail(admin, target["order"]["id"])
    step = next(s for s in d["steps"] if int(s["seq"]) == target["seq"])
    assert isinstance(step.get("source_stock"), list)
    assert any(r["available_qty"] > 0 for r in step["source_stock"]), step["source_stock"]


def test_02_issue_dari_gudang_kosong_409_menuntun(admin, target):
    d = _detail(admin, target["order"]["id"])
    step = next(s for s in d["steps"] if int(s["seq"]) == target["seq"])
    stocked = {r["warehouse_id"] for r in step["source_stock"] if r["available_qty"] + 0.01 >= float(step["input_qty"])}
    whs = requests.get(f"{BASE}/api/warehouses", headers=admin, timeout=30).json()
    whs = whs.get("items", whs) if isinstance(whs, dict) else whs
    empty = next((w["id"] for w in whs if w["id"] not in stocked), None)
    if not empty:
        pytest.skip("semua gudang punya stok bahan")
    r = requests.post(f"{BASE}/api/makloon-orders/{target['order']['id']}/issue", headers=admin,
                      json={"step_seq": target["seq"], "from_warehouse_id": empty}, timeout=30)
    assert r.status_code == 409, r.text
    assert "tersedia" in r.text.lower() and "butuh" in r.text.lower()


def test_03_issue_mengurangi_available(admin, target):
    d = _detail(admin, target["order"]["id"])
    step = next(s for s in d["steps"] if int(s["seq"]) == target["seq"])
    src = max(step["source_stock"], key=lambda r: r["available_qty"])
    pid, wh, need = step["input_product_id"], src["warehouse_id"], float(step["input_qty"])

    def bal():
        b = requests.get(f"{BASE}/api/inventory/balances", headers=admin, timeout=30).json()
        row = next((x for x in b if x["product_id"] == pid and x["warehouse_id"] == wh and x.get("owner_entity_id") == "ent_ksc"), {})
        return float(row.get("available_qty") or 0), float(row.get("subcon_qty") or 0)

    av0, sc0 = bal()
    r = requests.post(f"{BASE}/api/makloon-orders/{target['order']['id']}/issue", headers=admin,
                      json={"step_seq": target["seq"], "from_warehouse_id": wh}, timeout=30)
    assert r.status_code == 200, r.text
    av1, sc1 = bal()
    assert abs((av0 - av1) - need) < 0.05, (av0, av1, need)
    assert abs((sc1 - sc0) - need) < 0.05, (sc0, sc1, need)


def test_04_terima_kurang_status_sebagian_bukan_selesai(admin, target):
    d = _detail(admin, target["order"]["id"])
    step = next(s for s in d["steps"] if int(s["seq"]) == target["seq"])
    exp = float(step["expected_output_qty"])
    short = round(exp * 0.8, 2)
    r = requests.post(f"{BASE}/api/makloon-orders/{target['order']['id']}/receive", headers=admin,
                      json={"step_seq": target["seq"], "actual_output_qty": short,
                            "rolls": [{"lot": f"LOT-T7-{target['seq']}", "length": short}]}, timeout=60)
    assert r.status_code == 200, r.text
    o = r.json()
    st = next(s for s in o["steps"] if int(s["seq"]) == target["seq"])
    assert st["claim"]["status"] == "open", st["claim"]
    all_received = all(s["status"] == "received" for s in o["steps"])
    assert all_received, "skenario mengharapkan ini langkah terakhir"
    assert o["status"] == "partially_received", o["status"]
    assert (o.get("completion_hold") or {}).get("reason") == "claim_unsettled"


def test_05_klaim_masuk_my_queue_manajer(admin, manager, target):
    mko = target["order"]["id"]
    r = requests.post(f"{BASE}/api/makloon-orders/{mko}/claim", headers=admin,
                      json={"step_seq": target["seq"], "action": "terima_catatan", "amount": 0,
                            "reason": "TEST_iter280 susut wajar"}, timeout=30)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "partially_received"
    q = requests.get(f"{BASE}/api/approvals/my-queue", headers=manager, timeout=30).json()
    assert "makloon_claim" in [s["stage"] for s in q["stages"]]
    rows = [i for i in q["items"] if i["stage"] == "makloon_claim" and i["id"] == mko and i["step_seq"] == target["seq"]]
    assert rows, q["counts"]
    assert rows[0]["number"] == target["order"]["mko_number"]
    q2 = requests.get(f"{BASE}/api/approvals/my-queue?stage=makloon_claim", headers=manager, timeout=30).json()
    assert all(i["stage"] == "makloon_claim" for i in q2["items"]) and q2["items"]


def test_06_klaim_diputus_spk_selesai(admin, manager, target):
    mko = target["order"]["id"]
    r = requests.post(f"{BASE}/api/makloon-orders/{mko}/claim/approve", headers=manager,
                      json={"step_seq": target["seq"], "note": "TEST_iter280 diterima"}, timeout=30)
    assert r.status_code == 200, r.text
    o = r.json()
    others = [s for s in o["steps"] if int(s["seq"]) != target["seq"]
              and (s.get("claim") or {}).get("status") in ("open", "pending_approval")]
    if others:
        # Langkah lain masih punya klaim terbuka (data seed) → tetap Sebagian, lalu putuskan juga.
        assert o["status"] == "partially_received", o["status"]
        for s in others:
            if s["claim"]["status"] == "open":
                requests.post(f"{BASE}/api/makloon-orders/{mko}/claim", headers=admin,
                              json={"step_seq": int(s["seq"]), "action": "terima_catatan", "amount": 0,
                                    "reason": "TEST_iter280"}, timeout=30)
            r = requests.post(f"{BASE}/api/makloon-orders/{mko}/claim/approve", headers=manager,
                              json={"step_seq": int(s["seq"]), "note": "TEST_iter280"}, timeout=30)
            assert r.status_code == 200, r.text
            o = r.json()
    assert o["status"] == "completed", o["status"]
    assert not o.get("completion_hold")
    q = requests.get(f"{BASE}/api/approvals/my-queue?stage=makloon_claim", headers=manager, timeout=30).json()
    assert not [i for i in q["items"] if i["id"] == mko]
