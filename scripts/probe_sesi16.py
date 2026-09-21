"""Probe runtime sesi 16: CAS archive entity (2× → [200/409]), klaim impact-apply (409 saat terkunci, kunci lepas
sesudah 400), endpoint yang dipakai layar HP sales baru (360, open-orders, ar-receipts idempoten, customer-prices,
sales-returns, special-orders). Jalankan: python scripts/probe_sesi16.py"""
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
    tag = "PROBE16-" + uuid.uuid4().hex[:4]

    # ── archive entity CAS: entitas sintetis tanpa pengguna/dokumen → 2× bersamaan = satu 200, satu 409 ──
    ent = {"id": "ent_probe16_" + uuid.uuid4().hex[:5], "code": tag, "name": f"PT Probe {tag}", "status": "active", "created_at": "2026-09-06T00:00:00+00:00"}
    db.business_entities.insert_one(dict(ent))
    rs = await asyncio.gather(*[admin.post(f"/entities/{ent['id']}/archive", json={"reason": "probe", "force": True}) for _ in range(2)])
    codes = sorted(x.status_code for x in rs)
    st = db.business_entities.find_one({"id": ent["id"]}, {"_id": 0, "status": 1})["status"]
    check("archive entitas 2× bersamaan → [200, 409]; status archived", codes == [200, 409] and st == "archived", f"{codes} {st} {[x.text[:80] for x in rs]}")
    db.business_entities.delete_one({"id": ent["id"]})

    # ── impact-apply klaim: kunci products → 409; alasan kosong → 400 tanpa kunci ──
    prod = db.products.find_one({"price": {"$gt": 1000}}, {"_id": 0, "id": 1, "price": 1})
    db.products.update_one({"id": prod["id"]}, {"$set": {"saga_lock": LOCK}})
    r = await admin.post("/config/impact-apply", json={"product_id": prod["id"], "new_price": prod["price"], "doc_ids": [], "reason": "probe", "update_master": False})
    db.products.update_one({"id": prod["id"]}, {"$unset": {"saga_lock": ""}})
    check("impact-apply saat produk terkunci → 409 SAGA_IN_PROGRESS", r.status_code == 409 and "SAGA_IN_PROGRESS" in r.text, f"{r.status_code} {r.text[:100]}")
    r = await admin.post("/config/impact-apply", json={"product_id": prod["id"], "new_price": prod["price"], "doc_ids": [], "reason": "", "update_master": False})
    check("impact-apply alasan kosong → 400 tanpa kunci tertinggal", r.status_code == 400 and "saga_lock" not in db.products.find_one({"id": prod["id"]}, {"_id": 0, "saga_lock": 1}), f"{r.status_code}")
    r = await admin.post("/config/impact-apply", json={"product_id": prod["id"], "new_price": prod["price"], "doc_ids": [], "reason": "probe tanpa perubahan", "update_master": False})
    check("impact-apply sah → 200 dan kunci dilepas (release di finally)", r.status_code == 200 and "saga_lock" not in db.products.find_one({"id": prod["id"]}, {"_id": 0, "saga_lock": 1}), f"{r.status_code} {r.text[:100]}")

    # ── layar HP sales: endpoint yang dipakai ──
    sales = await login("sales@kainnusantara.id")
    cust = db.customers.find_one({"entity_id": "ent_ksc"}, {"_id": 0})
    c360 = await sales.get(f"/customers/{cust['id']}/360")
    check("GET /customers/{id}/360 (detail pelanggan HP) → order_history/payments/sample_history", c360.status_code == 200 and all(k in c360.json() for k in ("order_history", "payments", "sample_history")), f"{c360.status_code} {c360.text[:80]}")
    oo = await sales.get("/ar-receipts/open-orders", params={"customer_id": cust["id"]})
    check("GET /ar-receipts/open-orders (alokasi kwitansi HP) → daftar outstanding", oo.status_code == 200 and isinstance(oo.json(), list), f"{oo.status_code} {oo.text[:80]}")
    if oo.status_code == 200 and oo.json():
        o = oo.json()[0]
        amt = min(1000.0, float(o["outstanding"]))
        k = "idem16-" + uuid.uuid4().hex
        body = {"customer_id": cust["id"], "amount": amt, "method": "cash", "notes": tag, "allocations": [{"order_id": o["order_id"], "amount": amt}]}
        a = await sales.post("/ar-receipts", json=body, headers={"Idempotency-Key": k})
        b = await sales.post("/ar-receipts", json=body, headers={"Idempotency-Key": k})
        n = db.ar_receipts.count_documents({"notes": tag})
        check("POST /ar-receipts dari sales 2× kunci sama → 1 kwitansi (replay)", a.status_code == 200 and b.status_code == 200 and b.headers.get("x-idempotent-replay") == "true" and n == 1, f"{a.status_code}/{b.status_code} n={n} {a.text[:100]}")
        if a.status_code == 200:
            await admin.post(f"/ar-receipts/{a.json()['id']}/void", json={"reason": "probe"})
    else:
        print("SKIP  tidak ada tagihan terbuka untuk uji kwitansi")
    cp = await sales.get("/customer-prices", params={"customer_id": cust["id"], "entity_id": "ent_ksc"})
    rows = cp.json().get("rows") or cp.json().get("items") or []
    check("GET /customer-prices (daftar harga HP) → baris dgn global_price/customer_price/special_price", cp.status_code == 200 and rows and "global_price" in rows[0], f"{cp.status_code} {len(rows)}")
    for path in ("/sales-returns", "/special-orders", "/sales-returns/meta/complaint-reasons"):
        r = await sales.get(path)
        check(f"GET {path} (HP sales) → 200", r.status_code == 200, f"{r.status_code} {r.text[:80]}")
    db.idempotency_keys.delete_many({"key": {"$regex": "^idem16"}})
    print(f"\n{'SEMUA PASS' if not FAILS else str(len(FAILS)) + ' FAIL: ' + ', '.join(FAILS)}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
