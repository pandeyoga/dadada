"""Probe runtime sesi 11: klaim transfer-ownership retur (409 saat terkunci, kunci lepas sesudah 400),
kompensasi POST /transfers (item gagal → reservasi dilepas), POST /wms/tasks inbound (roll + tugas utuh),
GET /rfid/lookup mengembalikan open_tasks (pindai → aksi). Jalankan: python scripts/probe_sesi11.py"""
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

    # ── transfer-ownership retur: kunci → 409; validasi gagal → kunci TIDAK tertinggal ──
    ret = db.sales_returns.find_one({"entity_id": "ent_ksc", "saga_lock": {"$exists": False}}, {"_id": 0, "id": 1})
    check("ada retur jual KSC untuk uji", bool(ret))
    if ret:
        db.sales_returns.update_one({"id": ret["id"]}, {"$set": {"saga_lock": LOCK}})
        r = await admin.post(f"/sales-returns/{ret['id']}/rolls/roll_x/transfer-ownership", json={"dest_entity_id": "ent_other"})
        # roll_x tidak ada → validasi (400) terjadi SEBELUM klaim → 400, bukan 409
        check("transfer-ownership roll tak dikenal saat terkunci → 400 (validasi sebelum klaim)", r.status_code == 400, f"{r.status_code} {r.text[:100]}")
        await admin.post(f"/saga-locks/sales_returns/{ret['id']}/release")
        # cari roll retur available yang BUKAN asal antar-PT (E9.3 menolak sebelum klaim) di retur mana pun
        hit = None
        for cand in db.inventory_rolls.find({"origin_type": "return", "status": "available", "return_id": {"$ne": None}}, {"_id": 0}).limit(25):
            rid = cand["return_id"]
            dest = db.business_entities.find_one({"id": {"$ne": cand.get("owner_entity_id")}}, {"_id": 0, "id": 1})
            db.sales_returns.update_one({"id": rid}, {"$set": {"saga_lock": LOCK}})
            r = await admin.post(f"/sales-returns/{rid}/rolls/{cand['id']}/transfer-ownership", json={"dest_entity_id": dest["id"]})
            await admin.post(f"/saga-locks/sales_returns/{rid}/release")
            if r.status_code == 400 and "pembelian internal" in r.text:
                continue
            hit = (cand, r)
            break
        if hit:
            cand, r = hit
            check("transfer-ownership roll sah saat terkunci → 409 SAGA_IN_PROGRESS", r.status_code == 409 and "SAGA_IN_PROGRESS" in r.text, f"{r.status_code} {r.text[:120]}")
            still = db.inventory_rolls.find_one({"id": cand["id"]}, {"_id": 0, "status": 1})
            check("roll tetap available (tak direservasi saat klaim kalah)", still["status"] == "available", still["status"])
        else:
            # fixture sintetis: salin roll retur available, cabut penanda antar-PT → jalur klaim benar-benar diuji
            src = db.inventory_rolls.find_one({"origin_type": "return", "status": "available", "return_id": {"$ne": None}}, {"_id": 0})
            check("ada roll retur untuk fixture sintetis", bool(src))
            if src:
                fx = {**src, "id": "roll_probe11_" + uuid.uuid4().hex[:6], "roll_no": "PROBE11-" + uuid.uuid4().hex[:4].upper(),
                      "origin_interco_pair_id": "", "origin_interco_number": "", "cost_basis": {}, "rfid_tag_id": None}
                db.inventory_rolls.insert_one(fx)
                rid = fx["return_id"]
                dest = db.business_entities.find_one({"id": {"$ne": fx.get("owner_entity_id")}}, {"_id": 0, "id": 1})
                db.sales_returns.update_one({"id": rid}, {"$set": {"saga_lock": LOCK}})
                r = await admin.post(f"/sales-returns/{rid}/rolls/{fx['id']}/transfer-ownership", json={"dest_entity_id": dest["id"]})
                await admin.post(f"/saga-locks/sales_returns/{rid}/release")
                check("transfer-ownership roll sah saat terkunci → 409 SAGA_IN_PROGRESS", r.status_code == 409 and "SAGA_IN_PROGRESS" in r.text, f"{r.status_code} {r.text[:120]}")
                still = db.inventory_rolls.find_one({"id": fx["id"]}, {"_id": 0, "status": 1})
                check("roll tetap available (tak direservasi saat klaim kalah)", still["status"] == "available", still["status"])
                db.inventory_rolls.delete_one({"id": fx["id"]})
    check("tidak ada saga_lock tertinggal di sales_returns", db.sales_returns.count_documents({"saga_lock": {"$exists": True}}) == 0)

    # ── POST /transfers: item ke-2 produk palsu → 404 + reservasi item ke-1 dilepas ──
    roll = db.inventory_rolls.find_one({"owner_entity_id": "ent_ksc", "status": "available", "length_remaining": {"$gt": 1}}, {"_id": 0})
    whs = [w["id"] for w in db.warehouses.find({}, {"_id": 0, "id": 1})]
    if roll:
        dest = next((w for w in whs if w != roll["warehouse_id"]), None)
        before = db.inventory_rolls.count_documents({"product_id": roll["product_id"], "warehouse_id": roll["warehouse_id"], "status": "reserved", "reserved_ref.type": "transfer"})
        r = await admin.post("/transfers", json={"source_warehouse_id": roll["warehouse_id"], "dest_warehouse_id": dest, "requested_by": "probe",
                                                 "items": [{"product_id": roll["product_id"], "qty": 1, "unit": roll.get("unit", "yard")},
                                                           {"product_id": "prod_palsu_" + uuid.uuid4().hex[:6], "qty": 1, "unit": "yard"}]})
        after = db.inventory_rolls.count_documents({"product_id": roll["product_id"], "warehouse_id": roll["warehouse_id"], "status": "reserved", "reserved_ref.type": "transfer"})
        check("POST /transfers item palsu → 4xx dan reservasi item pertama dilepas (kompensasi)", r.status_code in (400, 404, 422) and after == before, f"{r.status_code} reserved {before}→{after}")
        r = await admin.post("/transfers", json={"source_warehouse_id": roll["warehouse_id"], "dest_warehouse_id": dest, "requested_by": "probe",
                                                 "items": [{"product_id": roll["product_id"], "qty": 1, "unit": roll.get("unit", "yard")}]})
        ok = r.status_code == 200
        check("POST /transfers sah → 200 + dokumen tersimpan", ok and db.warehouse_transfers.find_one({"id": r.json()["id"]}) is not None, f"{r.status_code} {r.text[:100]}")
        if ok:
            await admin.delete(f"/transfers/{r.json()['id']}")

    # ── POST /wms/tasks inbound → tugas + roll, dan /rfid/lookup memuat open_tasks ──
    prod = db.products.find_one({"id": roll["product_id"]}, {"_id": 0}) if roll else db.products.find_one({}, {"_id": 0})
    r = await admin.post("/wms/tasks", json={"flow_type": "inbound", "source_type": "manual", "product_id": prod["id"], "quantity": 5, "unit": prod.get("unit", "yard"),
                                             "warehouse_id": roll["warehouse_id"] if roll else whs[0], "bin_id": "", "batch": "", "lot": "PROBE11", "roll_id": ""})
    check("POST /wms/tasks inbound → 200", r.status_code == 200, f"{r.status_code} {r.text[:120]}")
    if r.status_code == 200:
        t = r.json()
        rl = db.inventory_rolls.find_one({"id": t.get("roll_id")}, {"_id": 0})
        check("tugas inbound punya roll nyata", bool(rl), str(t.get("roll_id")))
        if rl:
            lk = await admin.get("/rfid/lookup", params={"code": rl["roll_no"]})
            ids = [x["id"] for x in lk.json().get("open_tasks", [])] if lk.status_code == 200 else []
            check("GET /rfid/lookup (nomor roll) memuat open_tasks berisi tugas inbound ini", lk.status_code == 200 and t["id"] in ids, f"{lk.status_code} {ids}")
            lk2 = await admin.get("/rfid/lookup", params={"code": rl["id"]})
            check("GET /rfid/lookup (id roll) juga menemukan tugas", lk2.status_code == 200 and t["id"] in [x["id"] for x in lk2.json().get("open_tasks", [])])
        # roll yang dicadangkan untuk SO → tugas ambil (outbound) SO itu ikut muncul
        ob = db.wms_tasks.find_one({"flow_type": "outbound", "status": {"$in": ["created", "picking", "packing", "pending"]}, "order_id": {"$ne": None}}, {"_id": 0, "id": 1, "order_id": 1, "product_id": 1})
        rr = db.inventory_rolls.find_one({"reserved_ref.id": ob["order_id"], "product_id": ob["product_id"]}, {"_id": 0, "roll_no": 1}) if ob else None
        if rr:
            lk3 = await admin.get("/rfid/lookup", params={"code": rr["roll_no"]})
            check("GET /rfid/lookup roll reserved SO → open_tasks memuat tugas ambil SO itu", lk3.status_code == 200 and ob["id"] in [x["id"] for x in lk3.json().get("open_tasks", [])], f"{lk3.status_code} {[x['id'] for x in lk3.json().get('open_tasks', [])]}")
        # bersihkan jejak probe
        db.wms_tasks.delete_one({"id": t["id"]})
        if rl:
            db.inventory_rolls.delete_one({"id": rl["id"]})
            db.inventory_movements.delete_many({"roll_id": rl["id"]})
    check("tugas tanpa roll (cangkang) tidak tertinggal", db.wms_tasks.count_documents({"flow_type": "inbound", "lot": "PROBE11"}) == 0)

    print(f"\n{'SEMUA PASS' if not FAILS else str(len(FAILS)) + ' FAIL: ' + ', '.join(FAILS)}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
