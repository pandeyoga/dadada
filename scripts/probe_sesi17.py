"""Probe runtime sesi 17: klaim categories PATCH (rename kaskade, 409 saat terkunci, kunci lepas),
klaim convert-to-so (409 saat terkunci), klaim outbound-from-order (2× bersamaan → satu set tugas),
endpoint layar HP baru (leads CRUD+convert, inbox persetujuan manajer). Jalankan: python scripts/probe_sesi17.py"""
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
    sales = await login("sales@kainnusantara.id")
    manager = await login("manager@kainnusantara.id")
    tag = "PROBE17-" + uuid.uuid4().hex[:4]

    # ── categories PATCH: rename kaskade + kunci ──
    r = await admin.post("/product-categories", json={"name": f"Kat {tag}", "code": tag})
    check("buat kategori probe", r.status_code == 200, r.text[:100])
    cat = r.json()
    pid = "prd_probe17_" + uuid.uuid4().hex[:5]
    db.products.insert_one({"id": pid, "name": f"Produk {tag}", "sku": tag, "category": cat["name"], "price": 1000, "status": "active"})
    r = await admin.patch(f"/product-categories/{cat['id']}", json={"data": {"name": f"Kat {tag} B"}})
    prod_cat = db.products.find_one({"id": pid}, {"_id": 0, "category": 1})["category"]
    cat_doc = db.product_categories.find_one({"id": cat["id"]}, {"_id": 0})
    check("rename kategori → produk ikut, kunci lepas", r.status_code == 200 and prod_cat == f"Kat {tag} B" and "saga_lock" not in cat_doc, f"{r.status_code} {prod_cat}")
    db.product_categories.update_one({"id": cat["id"]}, {"$set": {"saga_lock": LOCK}})
    r = await admin.patch(f"/product-categories/{cat['id']}", json={"data": {"description": "x"}})
    check("PATCH kategori saat terkunci → 409 SAGA_IN_PROGRESS", r.status_code == 409 and "SAGA_IN_PROGRESS" in r.text, f"{r.status_code}")
    db.product_categories.update_one({"id": cat["id"]}, {"$unset": {"saga_lock": ""}})
    r = await admin.patch(f"/product-categories/{cat['id']}", json={"data": {"name": ""}})
    check("PATCH nama kosong → 400 tanpa kunci tertinggal", r.status_code == 400 and "saga_lock" not in db.product_categories.find_one({"id": cat["id"]}, {"_id": 0}), f"{r.status_code}")
    db.products.delete_one({"id": pid})
    db.product_categories.delete_one({"id": cat["id"]})

    # ── convert-to-so: special order terkunci → 409; sudah tertaut → 400 ──
    so = db.special_orders.find_one({"status": {"$in": ["confirmed", "in_production", "ready"]}}, {"_id": 0, "id": 1, "linked_sales_order_id": 1})
    if so and not so.get("linked_sales_order_id"):
        db.special_orders.update_one({"id": so["id"]}, {"$set": {"saga_lock": LOCK}})
        r = await admin.post(f"/special-orders/{so['id']}/convert-to-so")
        db.special_orders.update_one({"id": so["id"]}, {"$unset": {"saga_lock": ""}})
        check("convert-to-so saat terkunci → 409 SAGA_IN_PROGRESS", r.status_code == 409 and "SAGA_IN_PROGRESS" in r.text, f"{r.status_code} {r.text[:80]}")
    else:
        print("SKIP convert-to-so (tidak ada special order confirmed tanpa SO)")

    # ── outbound-from-order: SO confirmed tanpa tugas → 2× bersamaan hanya satu set tugas ──
    order = db.sales_orders.find_one({"status": "confirmed", "allocations.0": {"$exists": True}}, {"_id": 0, "id": 1})
    if order:
        oid = order["id"]
        backup = list(db.wms_tasks.find({"order_id": oid, "flow_type": "outbound"}))
        db.wms_tasks.delete_many({"order_id": oid, "flow_type": "outbound"})
        n_alloc = len(db.sales_orders.find_one({"id": oid}, {"_id": 0, "allocations": 1})["allocations"])
        rs = await asyncio.gather(*[admin.post(f"/wms/tasks/outbound-from-order/{oid}") for _ in range(2)])
        codes = sorted(x.status_code for x in rs)
        n_tasks = db.wms_tasks.count_documents({"order_id": oid, "flow_type": "outbound"})
        locked = "saga_lock" in (db.sales_orders.find_one({"id": oid}, {"_id": 0, "saga_lock": 1}) or {})
        check("outbound-from-order 2× bersamaan → tugas = alokasi (tak ganda), kunci lepas", n_tasks == n_alloc and not locked and 409 in codes or (n_tasks == n_alloc and not locked), f"{codes} tasks={n_tasks} alloc={n_alloc}")
        db.wms_tasks.delete_many({"order_id": oid, "flow_type": "outbound"})
        if backup:
            db.wms_tasks.insert_many(backup)
    else:
        print("SKIP outbound-from-order (tidak ada SO confirmed)")

    # ── leads HP: buat, geser tahap, konversi ──
    r = await sales.post("/crm/leads", json={"name": f"Lead {tag}", "company": f"Toko {tag}", "phone": "0812", "source": "whatsapp", "stage": "new", "est_value": 5000000, "notes": "probe"})
    check("sales buat lead", r.status_code == 200, r.text[:100])
    lead = r.json()
    r = await sales.patch(f"/crm/leads/{lead['id']}", json={"stage": "qualified"})
    check("sales geser tahap lead", r.status_code == 200 and r.json().get("stage") == "qualified", r.text[:80])
    r = await sales.post(f"/crm/leads/{lead['id']}/convert", json={})
    check("sales konversi lead → customer_id", r.status_code == 200 and r.json().get("customer_id"), r.text[:100])
    cid = r.json().get("customer_id") if r.status_code == 200 else None
    r = await sales.post(f"/crm/leads/{lead['id']}/convert", json={})
    check("konversi ulang → ditolak", r.status_code in (400, 409), f"{r.status_code}")
    r = await sales.get("/crm/leads")
    rows = r.json() if isinstance(r.json(), list) else r.json().get("items", [])
    check("lead terkonversi tidak muncul sebagai aktif di HP", not any(l["id"] == lead["id"] and l.get("stage") not in ("won", "lost", "converted") for l in rows))
    db.crm_leads.delete_one({"id": lead["id"]})
    if cid:
        db.customers.delete_one({"id": cid})
        db.crm_interactions.delete_many({"customer_id": cid})

    # ── inbox persetujuan HP (manajer): daftar pending & putuskan ──
    r = await manager.get("/price-approvals", params={"status": "pending"})
    check("manajer lihat antrean harga khusus", r.status_code == 200, f"{r.status_code}")
    r = await manager.get("/special-orders")
    check("manajer lihat pesanan khusus", r.status_code == 200, f"{r.status_code}")
    cust = db.customers.find_one({"entity_id": "ent_ksc", "status": "active"}, {"_id": 0, "id": 1})
    prod = db.products.find_one({"price": {"$gt": 1000}}, {"_id": 0, "id": 1, "price": 1})
    r = await sales.post("/price-approvals", json={"customer_id": cust["id"], "product_id": prod["id"], "requested_price": round(prod["price"] * 0.95, 2), "min_quantity": 10, "reason": f"probe {tag}", "scope": "standing"})
    if r.status_code == 200:
        pa = r.json()
        if pa.get("status") == "draft":
            db.price_approvals.update_one({"id": pa["id"]}, {"$set": {"status": "pending"}})  # bukti chat wajib → lewati di probe
        r = await manager.post(f"/price-approvals/{pa['id']}/reject", json={"decision_notes": "probe HP"})
        check("manajer tolak harga khusus dari HP", r.status_code == 200 and r.json().get("status") == "rejected", f"{r.status_code} {r.text[:100]}")
        db.price_approvals.delete_one({"id": pa["id"]})
    else:
        print("SKIP price approval fixture:", r.status_code, r.text[:120])

    print("\n" + ("ALL PASS" if not FAILS else f"{len(FAILS)} FAIL: {FAILS}"))
    for c in (admin, sales, manager):
        await c.aclose()


asyncio.run(main())
