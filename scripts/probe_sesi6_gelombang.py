"""Probe runtime sesi 6 (gelombang 2026-09): P-1 potongan tidak mewarisi tag RFID, §3-B bukti wajib +
hint + scope bawaan order, §D induk wajib, klaim quarantine/release, paginasi SDM.
Jalankan: python scripts/probe_sesi6_gelombang.py"""
import asyncio
import io
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

    # ── P-1: potongan roll TIDAK mewarisi tag ──
    sys.path.insert(0, str(ROOT / "backend"))
    from dotenv import load_dotenv
    load_dotenv(ROOT / "backend/.env")
    from services.roll_service import insert_child_roll
    parent = db.inventory_rolls.find_one({"rfid_tag_id": {"$nin": [None, ""]}, "status": "available"}, {"_id": 0})
    check("ada roll bertag untuk uji potong", bool(parent))
    if parent:
        child = dict(parent); child["id"] = "roll_probe6_child"; child["length_initial"] = child["length_remaining"] = 1.0
        doc = await insert_child_roll(child, parent)
        check("insert_child_roll → rfid_tag_id None (tag tidak diwariskan)", doc.get("rfid_tag_id") is None and doc.get("roll_no") != parent.get("roll_no"), str({k: doc.get(k) for k in ("rfid_tag_id", "roll_no")}))
        r = await admin.get("/rfid/untagged-rolls")
        lst = r.json().get("rolls", []) if isinstance(r.json(), dict) else r.json()
        check("potongan muncul di /rfid/untagged-rolls", any(x.get("id") == "roll_probe6_child" for x in lst), f"{r.status_code} n={len(lst)}")
        db.inventory_rolls.delete_one({"id": "roll_probe6_child"})
    dup = list(db.inventory_rolls.aggregate([{"$match": {"rfid_tag_id": {"$nin": [None, ""]}, "status": {"$in": ["available", "reserved", "allocated", "quarantine", "committed", "picked", "packed", "hold"]}}},
                                             {"$group": {"_id": "$rfid_tag_id", "n": {"$sum": 1}}}, {"$match": {"n": {"$gt": 1}}}]))
    check("data demo: 0 tag kembar pada roll aktif", not dup, str(dup[:3]))

    # ── §3-B: bukti wajib, scope bawaan order, hint tanpa HPP ──
    prods = (await admin.get("/products")).json(); plist = prods if isinstance(prods, list) else prods.get("items", [])
    custs = (await admin.get("/customers")).json(); clist = custs if isinstance(custs, list) else custs.get("items", [])
    p = next(x for x in plist if float(x.get("price") or 0) > 0); cust = clist[0]
    r = await admin.get("/price-approvals/hint", params={"product_id": p["id"], "price": round(float(p["price"]) * 0.5)})
    j = r.json() if r.status_code == 200 else {}
    check("hint: gap_pct + verdict, TANPA hpp/floor", r.status_code == 200 and "gap_pct" in j and "verdict" in j and not any(k in j for k in ("hpp", "floor", "harga_pokok")), f"{r.status_code} {str(j)[:120]}")
    body = {"customer_id": cust["id"], "product_id": p["id"], "requested_price": round(float(p["price"]) * 0.9), "min_quantity": 0, "reason": "probe"}
    r = await admin.post("/price-approvals", json={**body, "submit_now": True})
    check("submit_now tanpa bukti → 400 EVIDENCE_REQUIRED", r.status_code == 400 and "EVIDENCE_REQUIRED" in r.text, f"{r.status_code} {r.text[:100]}")
    r = await admin.post("/price-approvals", json={**body, "submit_now": False})
    draft = r.json(); check("draf dibuat; scope bawaan 'order'", r.status_code == 200 and draft.get("scope") == "order", f"{r.status_code} scope={draft.get('scope')}")
    r = await admin.post(f"/price-approvals/{draft['id']}/submit")
    check("submit draf tanpa lampiran → 400", r.status_code == 400, f"{r.status_code}")
    r = await admin.post(f"/price-approvals/{draft['id']}/attachments", files={"file": ("bukti.png", io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"0" * 64), "image/png")})
    check("unggah bukti → 200", r.status_code == 200, r.text[:100])
    r = await admin.post(f"/price-approvals/{draft['id']}/submit")
    check("submit sesudah bukti → 200 pending", r.status_code == 200 and r.json().get("status") == "pending", f"{r.status_code} {r.text[:80]}")
    db.price_approvals.delete_one({"id": draft["id"]})

    # ── §D: induk wajib ──
    live = {t["id"] for t in db.product_templates.find({}, {"id": 1})}
    orph = sum(1 for x in db.products.find({}, {"template_id": 1}) if x.get("template_id") not in live)
    check("semua produk punya induk hidup (0 yatim)", orph == 0 and len(live) > 0, f"templates={len(live)} yatim={orph}")
    r = await admin.post("/products", json={"name": "Kain Probe Sesi 6", "sku": "PRB6-001", "category": "Kain", "price": 50000, "base_unit": "meter", "fabric_type": "woven", "stage": "finished", "color": "Merah", "grade": "A", "harga_pokok": 0, "lebar": 150, "gramasi": 200})
    np_ = r.json() if r.status_code == 200 else {}
    check("POST /products tanpa template_id → induk otomatis (template_id terisi)", r.status_code == 200 and bool(np_.get("template_id")), f"{r.status_code} {r.text[:120]}")
    if np_.get("template_id"):
        r = await admin.get(f"/product-templates/{np_['template_id']}/summary")
        check("summary induk memuat varian baru + totals", r.status_code == 200 and any(v["id"] == np_["id"] for v in r.json().get("variants", [])) and "totals" in r.json(), r.text[:120])
        db.products.delete_one({"id": np_["id"]}); db.product_templates.delete_one({"id": np_["template_id"], "name": "Kain Probe Sesi 6"})

    # ── klaim quarantine/release: kunci → 409 ──
    ret = db.sales_returns.find_one({"entity_id": "ent_ksc"}, {"_id": 0, "id": 1})
    if ret:
        db.sales_returns.update_one({"id": ret["id"]}, {"$set": {"saga_lock": {"action": "probe", "by": "probe", "started_at": "2026-09-05T00:00:00+00:00"}}})
        r = await admin.post(f"/sales-returns/{ret['id']}/quarantine/release", json={"decisions": [], "notes": "probe"})
        check("quarantine/release saat terkunci → 409 SAGA_IN_PROGRESS atau 400 validasi-dulu", r.status_code in (400, 409), f"{r.status_code} {r.text[:100]}")
        await admin.post(f"/saga-locks/sales_returns/{ret['id']}/release")
        db.sales_returns.update_one({"id": ret["id"]}, {"$unset": {"saga_lock": ""}})

    # ── paginasi SDM ──
    r = await admin.get("/hr/attendance", params={"page": 1, "page_size": 5})
    check("GET /hr/attendance?page → envelope", r.status_code == 200 and isinstance(r.json(), dict) and "items" in r.json(), r.text[:80])
    r = await admin.get("/hr/visits", params={"page": 1, "page_size": 5, "date_from": "2020-01-01", "date_to": "2030-12-31"})
    check("GET /hr/visits?page → envelope", r.status_code == 200 and isinstance(r.json(), dict) and "items" in r.json(), r.text[:80])

    print("\nGAGAL:" if FAILS else "\nSEMUA PASS", FAILS)
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
