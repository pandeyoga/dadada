"""Probe runtime sesi 12: CAS scan-pick (balapan → satu 200), klaim dispatch & qc-decision (409 saat terkunci,
kunci tak tertinggal sesudah 400), lookup roll saran FIFO → tugas potong sampel, GET /rfid/labels?po_id.
Jalankan: python scripts/probe_sesi12.py"""
import asyncio
import os
import pathlib
import uuid

import httpx

ROOT = pathlib.Path(__file__).resolve().parent.parent
for line in (ROOT / "frontend/.env").read_text().splitlines():
    if line.startswith("REACT_APP_BACKEND_URL=") and not os.environ.get("REACT_APP_BACKEND_URL"):
        os.environ["REACT_APP_BACKEND_URL"] = line.split("=", 1)[1].strip().strip('"')
for line in (ROOT / "backend/.env").read_text().splitlines():
    k, _, v = line.partition("=")
    if k in ("MONGO_URL", "DB_NAME") and not os.environ.get(k):
        os.environ[k] = v.strip().strip('"')
API = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") + "/api"
FAILS = []
LOCK = {"action": "probe", "by": "probe", "started_at": "2026-09-05T00:00:00+00:00"}


def check(name, ok, info=""):
    print(("PASS " if ok else "FAIL ") + name + (f" — {info}" if info else ""))
    if not ok:
        FAILS.append(name)


async def login(email, pw="demo12345"):
    c = httpx.AsyncClient(base_url=API, timeout=60)
    r = await c.post("/auth/login", json={"email": email, "password": pw})
    assert r.status_code == 200, r.text
    c.headers["X-Entity-Id"] = "ent_ksc"
    return c


async def main():
    from pymongo import MongoClient
    db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    admin = await login("admin@kainnusantara.id")
    tag = "PROBE12-" + uuid.uuid4().hex[:4]

    # ── scan-pick: tugas sintetis (tanpa roll nyata) → 2× bersamaan = [200, 409]; picked_qty tepat 1× ──
    base = db.wms_tasks.find_one({"flow_type": "outbound", "status": "created", "entity_id": "ent_ksc"}, {"_id": 0})
    check("ada tugas outbound created untuk cetakan", bool(base))
    if base:
        t = {**base, "id": "wms_probe12_" + uuid.uuid4().hex[:6], "order_id": None, "quantity": 10.0, "picked_qty": 0.0, "scan_log": [], "refs": [], "lot": tag}
        db.wms_tasks.insert_one(dict(t))
        rs = await asyncio.gather(*[admin.post(f"/outbound/tasks/{t['id']}/scan-pick", params={"actual_qty": 4}) for _ in range(6)])
        codes = sorted(x.status_code for x in rs)
        ok200 = codes.count(200)
        after = db.wms_tasks.find_one({"id": t["id"]}, {"_id": 0, "picked_qty": 1, "status": 1, "scan_log": 1})
        check("scan-pick 6× bersamaan (qty 10): picked_qty == 4×jumlah 200, ≤ 10, scan_log sepadan (tak ada tulisan hilang/ganda)",
              after["picked_qty"] == 4.0 * ok200 and after["picked_qty"] <= 10 and len(after.get("scan_log", [])) == ok200 and all(c in (200, 400, 409) for c in codes),
              f"{codes} picked {after['picked_qty']} log {len(after.get('scan_log', []))}")
        db.wms_tasks.update_one({"id": t["id"]}, {"$set": {"picked_qty": 4.0, "status": "picking"}})
        r = await admin.post(f"/outbound/tasks/{t['id']}/scan-pick", params={"actual_qty": 6})
        check("scan-pick berikutnya (basis picked_qty baru) → 200, status packing", r.status_code == 200 and r.json().get("status") == "packing", f"{r.status_code} {r.text[:80]}")
        # dispatch: kunci → 409; validasi 400 (task bukan outbound) tak meninggalkan kunci
        db.wms_tasks.update_one({"id": t["id"]}, {"$set": {"saga_lock": LOCK}})
        r = await admin.post(f"/outbound/tasks/{t['id']}/dispatch")
        check("dispatch saat terkunci → 409 SAGA_IN_PROGRESS", r.status_code == 409 and "SAGA_IN_PROGRESS" in r.text, f"{r.status_code} {r.text[:100]}")
        db.wms_tasks.update_one({"id": t["id"]}, {"$unset": {"saga_lock": ""}, "$set": {"picked_qty": 0.0, "shipped_qty": 0.0}})
        r = await admin.post(f"/outbound/tasks/{t['id']}/dispatch")
        cur = db.wms_tasks.find_one({"id": t["id"]}, {"_id": 0, "saga_lock": 1})
        check("dispatch tanpa qty ter-pick → 400 dan TIDAK ada kunci tertinggal", r.status_code == 400 and "saga_lock" not in cur, f"{r.status_code}")
        db.wms_tasks.delete_one({"id": t["id"]})

    # ── qc-decision: kunci → 409; validasi 400 (qty 0) tak meninggalkan kunci ──
    qc = db.wms_tasks.find_one({"flow_type": "inbound", "status": "qc_pending"}, {"_id": 0, "id": 1, "entity_id": 1})
    if qc:
        admin.headers["X-Entity-Id"] = qc.get("entity_id") or "ent_ksc"
        db.wms_tasks.update_one({"id": qc["id"]}, {"$set": {"saga_lock": LOCK}})
        r = await admin.post(f"/inbound/tasks/{qc['id']}/qc-decision", json={"accept_qty": 1, "reject_qty": 0, "reject_disposition": "damaged", "reason": "probe"})
        check("qc-decision saat terkunci → 409 SAGA_IN_PROGRESS", r.status_code == 409 and "SAGA_IN_PROGRESS" in r.text, f"{r.status_code} {r.text[:100]}")
        db.wms_tasks.update_one({"id": qc["id"]}, {"$unset": {"saga_lock": ""}})
        r = await admin.post(f"/inbound/tasks/{qc['id']}/qc-decision", json={"accept_qty": 0, "reject_qty": 0, "reject_disposition": "damaged", "reason": "probe"})
        cur = db.wms_tasks.find_one({"id": qc["id"]}, {"_id": 0, "saga_lock": 1, "status": 1})
        check("qc-decision qty 0 → 400 dan TIDAK ada kunci tertinggal, status tetap qc_pending", r.status_code == 400 and "saga_lock" not in cur and cur["status"] == "qc_pending", f"{r.status_code} {cur}")
        admin.headers["X-Entity-Id"] = "ent_ksc"
    else:
        print("SKIP  tidak ada tugas qc_pending")

    # ── lookup roll saran FIFO → tugas potong sampel (cetakan sintetis) ──
    roll = db.inventory_rolls.find_one({"owner_entity_id": "ent_ksc", "status": "available", "rfid_tag_id": None}, {"_id": 0}) or \
        db.inventory_rolls.find_one({"owner_entity_id": "ent_ksc", "status": "available"}, {"_id": 0})
    st = {"id": "wms_probe12s_" + uuid.uuid4().hex[:6], "flow_type": "sample_cut", "task_subtype": "sample_cut", "status": "pending", "entity_id": "ent_ksc",
          "sample_request_id": "smp_probe", "sample_number": "SMP-PROBE", "product_id": roll["product_id"], "product_name": "Probe", "quantity": 2, "unit": roll.get("unit", "yard"),
          "customer_name": "Pelanggan Probe", "warehouse_id": roll["warehouse_id"], "suggested_roll_id": roll["id"], "suggested_roll_no": roll["roll_no"], "lot": tag,
          "created_at": "2026-09-06T00:00:00+00:00"}
    db.wms_tasks.insert_one(dict(st))
    lk = await admin.get("/rfid/lookup", params={"code": roll["roll_no"]})
    hit = next((x for x in lk.json().get("open_tasks", []) if x["id"] == st["id"]), None) if lk.status_code == 200 else None
    check("lookup roll saran FIFO → open_tasks memuat tugas potong sampel + customer_name", bool(hit) and hit.get("customer_name") == "Pelanggan Probe", f"{lk.status_code} {hit}")
    db.wms_tasks.delete_one({"id": st["id"]})

    # ── GET /rfid/labels?po_id ──
    pr = db.inventory_rolls.find_one({"po_id": {"$nin": [None, ""]}, "owner_entity_id": "ent_ksc"}, {"_id": 0, "po_id": 1})
    if pr:
        r = await admin.get("/rfid/labels", params={"po_id": pr["po_id"]})
        ok = r.status_code == 200 and r.json()["count"] >= 1 and all(x.get("roll_no") and x.get("product_name") for x in r.json()["rolls"])
        check("GET /rfid/labels?po_id → roll lengkap (roll_no + product_name) + po_number", ok and r.json().get("po_number"), f"{r.status_code} count={r.json().get('count')} po={r.json().get('po_number')}")
    else:
        print("SKIP  tidak ada roll ber-po_id")
    r = await admin.get("/rfid/labels")
    check("GET /rfid/labels tanpa filter → 400", r.status_code == 400)
    check("tidak ada jejak probe tertinggal", db.wms_tasks.count_documents({"lot": tag}) == 0)

    print(f"\n{'SEMUA PASS' if not FAILS else str(len(FAILS)) + ' FAIL: ' + ', '.join(FAILS)}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
