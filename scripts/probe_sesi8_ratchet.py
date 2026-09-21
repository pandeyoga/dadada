"""Probe runtime sesi 8: klaim saga lead convert · goods-back retur beli · resolve-exception putaway;
paginasi /hr/field-tracks (envelope) untuk peta. Jalankan: python scripts/probe_sesi8_ratchet.py"""
import asyncio
import os
import pathlib
import sys
import uuid

import httpx

ROOT = pathlib.Path(__file__).resolve().parent.parent
for line in (ROOT / "frontend/.env").read_text().splitlines():
    if line.startswith("REACT_APP_BACKEND_URL=") and not os.environ.get("REACT_APP_BACKEND_URL"):
        os.environ["REACT_APP_BACKEND_URL"] = line.split("=", 1)[1].strip().strip('"')
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
    db = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))[os.environ.get("DB_NAME", "test_database")]
    admin = await login("admin@kainnusantara.id")

    # ── lead convert ──
    lead_id = f"lead_probe8_{uuid.uuid4().hex[:8]}"
    db.crm_leads.insert_one({"id": lead_id, "name": "Probe Lead", "company": "PT Probe Delapan", "phone": "0800", "email": "",
                             "stage": "qualified", "entity_id": "ent_ksc", "owner_id": "", "owner_name": "", "created_at": "2026-09-05T00:00:00+00:00"})
    db.crm_leads.update_one({"id": lead_id}, {"$set": {"saga_lock": LOCK}})
    r = await admin.post(f"/crm/leads/{lead_id}/convert", json={})
    check("lead convert saat terkunci → 409 SAGA_IN_PROGRESS", r.status_code == 409 and "SAGA_IN_PROGRESS" in r.text, f"{r.status_code} {r.text[:100]}")
    locks = (await admin.get("/saga-locks")).json()
    check("kunci crm_leads tampil di /saga-locks", any(l["collection"] == "crm_leads" and l["id"] == lead_id for l in locks))
    r = await admin.post(f"/saga-locks/crm_leads/{lead_id}/release"); check("lepas kunci crm_leads → 200", r.status_code == 200)
    rs = await asyncio.gather(*[admin.post(f"/crm/leads/{lead_id}/convert", json={}) for _ in range(2)])
    codes = sorted(x.status_code for x in rs)
    check("2× convert bersamaan → satu 200 + satu 4xx (tanpa 5xx)", codes.count(200) == 1 and all(c < 500 for c in codes), f"{codes} {[x.text[:80] for x in rs]}")
    n_cust = db.customers.count_documents({"source_lead_id": lead_id})
    lead = db.crm_leads.find_one({"id": lead_id}, {"_id": 0})
    check("tepat 1 pelanggan lahir; lead stage won tanpa saga_lock", n_cust == 1 and lead.get("stage") == "won" and "saga_lock" not in lead, f"cust={n_cust} {lead.get('stage')}")
    db.customers.delete_many({"source_lead_id": lead_id}); db.crm_leads.delete_one({"id": lead_id}); db.crm_interactions.delete_many({"lead_id": lead_id})

    # ── goods-back retur beli: kunci → 409 ──
    pret = db.purchase_returns.find_one({"entity_id": "ent_ksc"}, {"_id": 0, "id": 1, "supplier_status": 1}) or db.purchase_returns.find_one({}, {"_id": 0, "id": 1, "supplier_status": 1})
    if pret:
        db.purchase_returns.update_one({"id": pret["id"]}, {"$set": {"saga_lock": LOCK}})
        r = await admin.post(f"/purchase-returns/{pret['id']}/goods-back", json={"notes": "probe", "regrade": []})
        check("goods-back saat terkunci → 409 SAGA_IN_PROGRESS atau 400 transisi-dulu", r.status_code in (400, 409), f"{r.status_code} {r.text[:100]}")
        await admin.post(f"/saga-locks/purchase_returns/{pret['id']}/release")
        db.purchase_returns.update_one({"id": pret["id"]}, {"$unset": {"saga_lock": ""}})
    else:
        check("ada retur beli untuk uji", False)

    # ── putaway resolve-exception: dokumen sintetis dengan 1 item exception ──
    po_id = f"pa_probe8_{uuid.uuid4().hex[:8]}"
    roll = db.inventory_rolls.find_one({"status": "available", "owner_entity_id": "ent_ksc"}, {"_id": 0})
    db.putaway_orders.insert_one({"id": po_id, "status": "completed_with_exception", "owner_entity_id": "ent_ksc", "entity_id": "ent_ksc",
                                  "warehouse_from": roll["warehouse_id"], "warehouse_to": roll["warehouse_id"],
                                  "items": [{"roll_id": roll["id"], "product_id": roll["product_id"], "status": "exception"}],
                                  "created_at": "2026-09-05T00:00:00+00:00", "updated_at": "2026-09-05T00:00:00+00:00"})
    db.putaway_orders.update_one({"id": po_id}, {"$set": {"saga_lock": LOCK}})
    r = await admin.post(f"/putaway-orders/{po_id}/resolve-exception", json={"roll_ids": [roll["id"]], "action": "return_transit"})
    check("resolve-exception saat terkunci → 409 SAGA_IN_PROGRESS", r.status_code == 409 and "SAGA_IN_PROGRESS" in r.text, f"{r.status_code} {r.text[:120]}")
    await admin.post(f"/saga-locks/putaway_orders/{po_id}/release")
    rs = await asyncio.gather(*[admin.post(f"/putaway-orders/{po_id}/resolve-exception", json={"roll_ids": [roll["id"]], "action": "return_transit"}) for _ in range(2)])
    codes = sorted(x.status_code for x in rs)
    check("2× resolve-exception bersamaan → satu 200, sisanya 4xx", codes.count(200) == 1 and all(c < 500 for c in codes), f"{codes} {[x.text[:80] for x in rs]}")
    pa = db.putaway_orders.find_one({"id": po_id}, {"_id": 0})
    check("putaway status completed tanpa saga_lock", pa.get("status") == "completed" and "saga_lock" not in pa, str(pa.get("status")))
    db.putaway_orders.delete_one({"id": po_id})
    db.inventory_rolls.update_one({"id": roll["id"]}, {"$set": {"status": "available", "warehouse_id": roll["warehouse_id"], "updated_at": roll.get("updated_at")}})

    # ── paginasi jejak lapangan (peta) ──
    r = await admin.get("/hr/field-tracks", params={"employee_id": "none", "page": 1, "page_size": 500})
    check("GET /hr/field-tracks?page → envelope {items,total,has_more}", r.status_code == 200 and isinstance(r.json(), dict) and {"items", "total", "has_more"} <= set(r.json()), r.text[:80])

    print("\nGAGAL:" if FAILS else "\nSEMUA PASS", FAILS)
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
