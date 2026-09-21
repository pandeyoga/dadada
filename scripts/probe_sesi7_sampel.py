"""Probe runtime sesi 7: §3-C Jual Sampel (master harga, quote FIFO, potong dengan klaim atomik,
alasan bila bukan saran, SO sampel + kwitansi, P-1 potongan tanpa tag), §D warna tunggal, aksi tugas gudang.
Jalankan: python scripts/probe_sesi7_sampel.py"""
import asyncio
import os
import pathlib
import sys

import httpx

ROOT = pathlib.Path(__file__).resolve().parent.parent
for line in (ROOT / "frontend/.env").read_text().splitlines():
    if line.startswith("REACT_APP_BACKEND_URL=") and not os.environ.get("REACT_APP_BACKEND_URL"):
        os.environ["REACT_APP_BACKEND_URL"] = line.split("=", 1)[1].strip().strip('"')
API = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") + "/api"
FAILS = []


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
    db = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))[os.environ.get("DB_NAME", "test_database")]
    admin = await login("admin@kainnusantara.id")
    sales = await login("sales@kainnusantara.id")
    wh = await login("wh.admin@kainnusantara.id")

    # roll available bertag milik KSC dengan sisa cukup
    roll = db.inventory_rolls.find_one({"status": "available", "owner_entity_id": "ent_ksc", "length_remaining": {"$gte": 6}, "rfid_tag_id": {"$nin": [None, ""]}}, {"_id": 0}, sort=[("created_at", 1)])
    check("ada roll available bertag KSC", bool(roll))
    prod = db.products.find_one({"id": roll["product_id"]}, {"_id": 0})
    cust = db.customers.find_one({"entity_id": "ent_ksc"}, {"_id": 0}) or db.customers.find_one({}, {"_id": 0})

    # master harga sampel per induk
    r = await admin.get("/sample-prices"); check("GET /sample-prices → daftar induk", r.status_code == 200 and any(x["template_id"] == prod["template_id"] for x in r.json()), f"{r.status_code}")
    r = await admin.put(f"/sample-prices/{prod['template_id']}", json={"price_per_unit": 12345})
    check("PUT /sample-prices → 200", r.status_code == 200, r.text[:100])
    r = await sales.put(f"/sample-prices/{prod['template_id']}", json={"price_per_unit": 1})
    check("sales tidak boleh ubah master harga (403)", r.status_code == 403, str(r.status_code))

    # quote: harga master × panjang + saran FIFO
    r = await sales.get("/sample-requests/quote", params={"product_id": prod["id"], "length": 2})
    q = r.json(); check("quote pakai master sampel 12345 × 2", r.status_code == 200 and q.get("source") == "master_sampel" and q.get("amount") == 24690, str(q)[:140])
    fifo = db.inventory_rolls.find_one({"product_id": prod["id"], "status": "available", "owner_entity_id": "ent_ksc", "length_remaining": {"$gte": 2}}, {"_id": 0, "id": 1}, sort=[("created_at", 1)])
    check("saran roll = FIFO (tertua)", (q.get("suggested_roll") or {}).get("id") == fifo["id"], f"{(q.get('suggested_roll') or {}).get('id')} vs {fifo['id']}")

    # permintaan oleh sales → tugas WMS sample_cut
    r = await sales.post("/sample-requests", json={"customer_id": cust["id"], "product_id": prod["id"], "length": 2, "payment_method": "cash", "notes": "probe"})
    req = r.json(); check("POST /sample-requests → 200 status requested + tugas WMS", r.status_code == 200 and req.get("status") == "requested" and db.wms_tasks.find_one({"id": req.get("wms_task_id"), "flow_type": "sample_cut"}) is not None, r.text[:120])
    tasks = (await wh.get("/wms/tasks")).json()
    tl = tasks if isinstance(tasks, list) else tasks.get("items", tasks.get("tasks", []))
    check("tugas sample_cut tampil di /wms/tasks gudang", any(t.get("id") == req.get("wms_task_id") for t in tl))

    # potong roll lain tanpa alasan → 400 REASON_REQUIRED
    other = db.inventory_rolls.find_one({"product_id": prod["id"], "status": "available", "owner_entity_id": "ent_ksc", "length_remaining": {"$gte": 2}, "id": {"$ne": req["suggested_roll_id"]}}, {"_id": 0})
    if other:
        r = await wh.post(f"/sample-requests/{req['id']}/cut", json={"roll_id": other["id"]})
        check("roll bukan saran tanpa alasan → 400 REASON_REQUIRED", r.status_code == 400 and "REASON_REQUIRED" in r.text, f"{r.status_code} {r.text[:100]}")
    r = await wh.post(f"/sample-requests/{req['id']}/cut", json={"epc": "EPC-TIDAK-ADA"})
    check("EPC tak dikenal → 404 TAG_UNKNOWN", r.status_code == 404 and "TAG_UNKNOWN" in r.text, f"{r.status_code}")
    before_len = db.inventory_rolls.find_one({"id": req["suggested_roll_id"]}, {"_id": 0, "length_remaining": 1})["length_remaining"]
    # balapan: 2× potong roll saran bersamaan → tepat satu 200
    rs = await asyncio.gather(*[wh.post(f"/sample-requests/{req['id']}/cut", json={"roll_id": req["suggested_roll_id"]}) for _ in range(2)])
    codes = sorted(x.status_code for x in rs)
    check("2× potong bersamaan → satu 200 + satu 409 (klaim atomik)", codes == [200, 409], f"{codes} {[x.text[:80] for x in rs]}")
    done = next((x.json() for x in rs if x.status_code == 200), {})
    after = db.sample_requests.find_one({"id": req["id"]}, {"_id": 0})
    check("permintaan → done tanpa saga_lock", after.get("status") == "done" and "saga_lock" not in after)
    parent = db.inventory_rolls.find_one({"id": req["suggested_roll_id"]}, {"_id": 0})
    child = db.inventory_rolls.find_one({"id": done.get("child_roll_id")}, {"_id": 0})
    check("induk berkurang 2 & tetap bertag", round(before_len - parent["length_remaining"], 2) == 2 and parent.get("rfid_tag_id"), f"{before_len}→{parent['length_remaining']}")
    check("potongan status sold, TANPA tag (P-1)", child and child.get("status") == "sold" and child.get("rfid_tag_id") is None, str({k: (child or {}).get(k) for k in ("status", "rfid_tag_id", "roll_no")}))
    so = db.sales_orders.find_one({"id": done.get("sales_order_id")}, {"_id": 0})
    check("SO jenis sample status done, nilai 24690", so and so.get("order_type") == "sample" and so.get("status") == "done" and so.get("grand_total") == 24690, str({k: (so or {}).get(k) for k in ("order_type", "status", "grand_total", "paid_total")}))
    rc = db.ar_receipts.find_one({"id": done.get("receipt_id")}, {"_id": 0}) if done.get("receipt_id") else None
    check("kwitansi kas terbit & SO lunas", rc is not None and round(float(so.get("paid_total") or 0), 2) == 24690, f"receipt={bool(rc)} paid={so.get('paid_total')} err={done.get('receipt_error')}")
    mov = db.inventory_movements.count_documents({"movement_type": "sample_sale", "reference_id": req["id"]})
    check("mutasi sample_sale tepat 1", mov == 1, str(mov))
    check("tugas WMS completed", db.wms_tasks.find_one({"id": req["wms_task_id"]}, {"_id": 0, "status": 1})["status"] == "completed")
    r = await wh.post(f"/sample-requests/{req['id']}/cut", json={"roll_id": req["suggested_roll_id"]})
    check("potong ulang permintaan selesai → 409", r.status_code == 409, str(r.status_code))
    # batal permintaan lain
    r = await sales.post("/sample-requests", json={"customer_id": cust["id"], "product_id": prod["id"], "length": 1, "payment_method": "transfer"})
    r2 = await sales.post(f"/sample-requests/{r.json()['id']}/cancel", json={"reason": "probe"})
    check("cancel permintaan requested → 200 cancelled + tugas cancelled", r2.status_code == 200 and r2.json().get("status") == "cancelled" and db.wms_tasks.find_one({"id": r.json()["wms_task_id"]})["status"] == "cancelled")
    db.sample_requests.delete_one({"id": r.json()["id"]}); db.wms_tasks.delete_one({"id": r.json()["wms_task_id"]})

    # §D warna tunggal
    bad = [p["sku"] for p in db.products.find({}, {"_id": 0, "sku": 1, "color": 1, "color_name": 1, "variant_attrs": 1}) if not (p.get("color") == p.get("color_name") == (p.get("variant_attrs") or {}).get("color"))]
    check("semua produk: color == color_name == variant_attrs.color (sumber tunggal)", not bad, str(bad[:5]))
    sys.path.insert(0, str(ROOT / "backend"))
    from services.product_variant_service import color_code_for, variant_sku
    check("kode warna: 'Biru Tua'→BIT, 'Merah'→MER", color_code_for("Biru Tua") == "BIT" and color_code_for("Merah") == "MER")
    check("SKU varian = prefix induk + kode warna", variant_sku({"sku_prefix": "BTK"}, "Biru Tua", "A") == "BTK-BIT" and variant_sku({"sku_prefix": "BTK"}, "Merah", "B") == "BTK-MER-B")

    # bersih-bersih master harga probe
    db.sample_price_master.delete_one({"template_id": prod["template_id"]})
    print("\nGAGAL:" if FAILS else "\nSEMUA PASS", FAILS)
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
