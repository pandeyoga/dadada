"""Iter 324 — Sesi 10 backend: RFID lookup, sample cut via roll_no, transfer cancel race."""
import os, sys, asyncio, httpx, json, time
from motor.motor_asyncio import AsyncIOMotorClient

BASE = os.environ.get("REACT_APP_BACKEND_URL", "https://vendor-bills-wms.preview.emergentagent.com").rstrip("/")
MONGO = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB = os.environ.get("DB_NAME", "test_database")

ENT = "ent_ksc"


async def login(client, email):
    r = await client.post(f"{BASE}/api/auth/login", json={"email": email, "password": "demo12345"})
    assert r.status_code == 200, r.text
    return r.cookies


async def main():
    results = []
    def rec(name, ok, info=""):
        results.append((name, ok, info))
        print(("PASS" if ok else "FAIL"), name, "-", info)

    mongo = AsyncIOMotorClient(MONGO)
    db = mongo[DB]

    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as wh:
        wh.cookies = await login(wh, "wh.admin@kainnusantara.id")
        wh.headers["X-Entity-Id"] = ENT

        # --- (1) lookup via label (roll_no, no tag) ---
        roll = await db.inventory_rolls.find_one(
            {"owner_entity_id": ENT, "status": "available", "rfid_tag_id": None}, {"_id": 0})
        if not roll:
            roll = await db.inventory_rolls.find_one(
                {"owner_entity_id": ENT, "status": "available",
                 "$or": [{"rfid_tag_id": {"$exists": False}}, {"rfid_tag_id": None}]}, {"_id": 0})
        rec("seed.roll_untagged_available", bool(roll), roll and roll.get("roll_no"))
        assert roll

        r = await wh.get(f"{BASE}/api/rfid/lookup", params={"code": roll["roll_no"]})
        ok = r.status_code == 200 and r.json().get("via") == "label" and r.json().get("roll", {}).get("id") == roll["id"] and r.json().get("tagged") is False
        rec("lookup.via_label", ok, f"HTTP {r.status_code} {r.json() if r.status_code<400 else r.text[:200]}")

        # --- (2) lookup via rfid EPC ---
        tag = await db.rfid_tags.find_one({"status": "active"}, {"_id": 0})
        if tag:
            r = await wh.get(f"{BASE}/api/rfid/lookup", params={"code": tag["epc"]})
            ok = r.status_code == 200 and r.json().get("via") == "rfid"
            rec("lookup.via_rfid", ok, f"HTTP {r.status_code} via={r.json().get('via') if r.status_code<400 else r.text[:200]}")
        else:
            rec("lookup.via_rfid", False, "no active rfid_tag found")

        # --- (3) unknown → 404 CODE_UNKNOWN ---
        r = await wh.get(f"{BASE}/api/rfid/lookup", params={"code": "XYZ"})
        j = {}
        try: j = r.json()
        except Exception: pass
        det = j.get("detail") if isinstance(j.get("detail"), dict) else {}
        ok = r.status_code == 404 and det.get("code") == "CODE_UNKNOWN"
        rec("lookup.unknown_404", ok, f"HTTP {r.status_code} detail={j.get('detail')}")

        # --- (4) sample cut via roll_no ---
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as sales:
            sales.cookies = await login(sales, "sales@kainnusantara.id")
            sales.headers["X-Entity-Id"] = ENT

            # find product with available roll (owner ent_ksc) length_remaining >=1
            avail = await db.inventory_rolls.find_one(
                {"owner_entity_id": ENT, "status": "available", "length_remaining": {"$gte": 1.5}},
                {"_id": 0}, sort=[("created_at", 1)])
            customer = await db.customers.find_one({"entity_id": ENT}, {"_id": 0}) or await db.customers.find_one({}, {"_id": 0})
            rec("seed.sample_prereq", bool(avail and customer), avail and avail.get("roll_no"))
            assert avail and customer

            r = await sales.post(f"{BASE}/api/sample-requests", json={
                "customer_id": customer["id"], "product_id": avail["product_id"],
                "length": 1, "payment_method": "cash"
            })
            ok = r.status_code in (200, 201)
            rec("sample.create", ok, f"HTTP {r.status_code} {r.text[:200] if not ok else r.json().get('number')}")
            req = r.json()
            suggested_no = req.get("suggested_roll_no")

            # cut using roll_no as epc (label QR)
            r = await wh.post(f"{BASE}/api/sample-requests/{req['id']}/cut",
                              json={"epc": suggested_no})
            ok = r.status_code == 200
            rec("sample.cut_via_roll_no", ok, f"HTTP {r.status_code} {r.text[:300] if not ok else 'done'}")

            if ok:
                data = r.json()
                child_id = data.get("child_roll_id")
                child = await db.inventory_rolls.find_one({"id": child_id}, {"_id": 0})
                ok2 = child is not None and child.get("rfid_tag_id") is None
                rec("sample.child_untagged", ok2, f"child rfid_tag_id={child.get('rfid_tag_id') if child else 'missing'}")

        # --- (5) transfer cancel: synthesize, saga lock -> 409, release, race -> 200+4xx ---
        import uuid
        tid = f"trf_test_{uuid.uuid4().hex[:8]}"
        now = time.strftime("%Y-%m-%dT%H:%M:%S")
        await db.warehouse_transfers.insert_one({
            "id": tid, "number": f"TRF-QA-{tid[-6:]}", "status": "pending",
            "transfer_kind": "intra_entity", "entity_id": ENT,
            "source_entity_id": ENT, "dest_entity_id": ENT,
            "from_warehouse_id": "wh_jakarta", "to_warehouse_id": "wh_bandung",
            "items": [], "roll_ids": [], "created_at": now, "updated_at": now,
        })

        # place saga lock manually (as field on doc)
        await db.warehouse_transfers.update_one({"id": tid}, {"$set": {
            "saga_lock": {"action": "qa_test", "by": "qa", "started_at": now}}})

        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as admin:
            admin.cookies = await login(admin, "admin@kainnusantara.id")
            admin.headers["X-Entity-Id"] = ENT

            r = await admin.request("DELETE", f"{BASE}/api/transfers/{tid}", params={"reason": "qa"})
            j = {}
            try: j = r.json()
            except Exception: pass
            det = j.get("detail") if isinstance(j.get("detail"), dict) else {}
            ok = r.status_code == 409 and det.get("code") == "SAGA_IN_PROGRESS"
            rec("transfer.cancel_saga_locked_409", ok, f"HTTP {r.status_code} {j}")

            # release lock
            r = await admin.post(f"{BASE}/api/saga-locks/warehouse_transfers/{tid}/release")
            rec("transfer.release_lock", r.status_code in (200, 204), f"HTTP {r.status_code}")

            # race: two concurrent DELETEs
            async def do_cancel():
                async with httpx.AsyncClient(timeout=30, follow_redirects=True, cookies=admin.cookies,
                                             headers={"X-Entity-Id": ENT}) as c:
                    return await c.request("DELETE", f"{BASE}/api/transfers/{tid}", params={"reason": "race"})
            r1, r2 = await asyncio.gather(do_cancel(), do_cancel())
            codes = sorted([r1.status_code, r2.status_code])
            ok = 200 in codes and any(c >= 400 and c < 500 for c in codes)
            rec("transfer.cancel_race_200_and_4xx", ok, f"codes={codes} bodies=[{r1.text[:120]},{r2.text[:120]}]")

            # verify status cancelled and no saga_lock
            doc = await db.warehouse_transfers.find_one({"id": tid}, {"_id": 0})
            has_lock = bool(doc and doc.get("saga_lock"))
            ok = doc and doc.get("status") == "cancelled" and not has_lock
            rec("transfer.final_state_ok", ok, f"status={doc.get('status') if doc else 'missing'} lock={has_lock}")

        # cleanup synthesized doc
        await db.warehouse_transfers.delete_one({"id": tid})

    passed = sum(1 for _, ok, _ in results if ok)
    print(f"\n=== {passed}/{len(results)} PASSED ===")
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    asyncio.run(main())
