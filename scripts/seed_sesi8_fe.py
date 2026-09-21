"""Seed data for sesi 8 frontend tests: sample request + synthetic lead with saga_lock."""
import asyncio, os, sys, uuid, pathlib, json
import httpx
ROOT = pathlib.Path(__file__).resolve().parent.parent
for line in (ROOT / "frontend/.env").read_text().splitlines():
    if line.startswith("REACT_APP_BACKEND_URL=") and not os.environ.get("REACT_APP_BACKEND_URL"):
        os.environ["REACT_APP_BACKEND_URL"] = line.split("=", 1)[1].strip().strip('"')
API = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") + "/api"

async def login(email, pw="demo12345"):
    c = httpx.AsyncClient(base_url=API, timeout=60)
    r = await c.post("/auth/login", json={"email": email, "password": pw})
    assert r.status_code == 200, r.text
    c.headers["X-Entity-Id"] = "ent_ksc"
    return c

async def main():
    from pymongo import MongoClient
    db = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))[os.environ.get("DB_NAME", "test_database")]
    # Find a customer + product w/ roll available ent_ksc len>=1
    cust = db.customers.find_one({"entity_id": "ent_ksc"}, {"_id": 0, "id": 1, "name": 1})
    if not cust:
        cust = db.customers.find_one({}, {"_id": 0, "id": 1, "name": 1})
    # Find a roll available ent_ksc
    roll = db.inventory_rolls.find_one({"status": "available", "owner_entity_id": "ent_ksc", "length_remaining": {"$gte": 2}}, {"_id": 0})
    assert roll, "no available roll"
    product_id = roll["product_id"]
    print(f"CUSTOMER={cust['id']} name={cust.get('name')}")
    print(f"PRODUCT={product_id} ROLL={roll['id']} len={roll.get('length_remaining')}")

    sales = await login("sales@kainnusantara.id")
    r = await sales.post("/sample-requests", json={"customer_id": cust["id"], "product_id": product_id, "length": 1, "payment_method": "cash"})
    assert r.status_code in (200, 201), r.text
    sr = r.json()
    print(f"SAMPLE_REQUEST={sr.get('id')} number={sr.get('number')}")
    # Find wms_task
    task = db.wms_tasks.find_one({"sample_request_id": sr["id"]}, {"_id": 0})
    print(f"WMS_TASK={task['id'] if task else None} flow={task.get('flow_type') if task else None} suggested={task.get('suggested_roll_id') if task else None}")

    # Seed synthetic lead with saga_lock
    lead_id = f"lead_fe8_{uuid.uuid4().hex[:8]}"
    db.crm_leads.insert_one({"id": lead_id, "name": "Lead FE Sesi 8", "company": "PT FE Delapan",
                             "phone": "0800", "email": "", "stage": "qualified", "entity_id": "ent_ksc",
                             "owner_id": "", "owner_name": "", "created_at": "2026-09-05T00:00:00+00:00",
                             "saga_lock": {"action": "probe", "by": "fe-probe", "started_at": "2026-09-05T00:00:00+00:00"}})
    print(f"SEEDED_LEAD={lead_id}")

    out = {"customer_id": cust["id"], "customer_name": cust.get("name"), "product_id": product_id,
           "sample_request_id": sr.get("id"), "sample_number": sr.get("number"),
           "wms_task_id": task["id"] if task else None,
           "suggested_roll_id": task.get("suggested_roll_id") if task else None,
           "lead_id": lead_id}
    print("JSON=" + json.dumps(out))

if __name__ == "__main__":
    asyncio.run(main())
