"""Probe runtime sesi 13: CAS encode/retire tag & advance (balapan → satu 200), riwayat pindai roll
(roll_scans + last_scan + timeline), antrean label QR (kind=qr_label) tampil di device-jobs printer.
Jalankan: python scripts/probe_sesi13.py"""
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
    tag = "PROBE13-" + uuid.uuid4().hex[:4]

    # ── encode tag: roll sintetis tanpa tag → 2× bersamaan = satu 200, satu tag aktif ──
    base = db.inventory_rolls.find_one({"owner_entity_id": "ent_ksc", "status": "available", "length_remaining": {"$gt": 0}}, {"_id": 0})
    fx = {**base, "id": "roll_probe13_" + uuid.uuid4().hex[:6], "roll_no": tag, "rfid_tag_id": None, "tracking_mode": "barcode"}
    db.inventory_rolls.insert_one(dict(fx))
    rs = await asyncio.gather(*[admin.post("/rfid/tags/encode", json={"roll_id": fx["id"]}) for _ in range(2)])
    codes = sorted(x.status_code for x in rs)
    active = db.rfid_tags.count_documents({"roll_id": fx["id"], "status": "active"})
    check("encode 2× bersamaan → satu 200 + satu 4xx; tepat 1 tag aktif", codes[0] == 200 and codes[1] in (400, 409) and active == 1, f"{codes} aktif={active}")
    tag_id = db.rfid_tags.find_one({"roll_id": fx["id"], "status": "active"}, {"_id": 0, "id": 1})["id"]
    # retire 2× bersamaan → satu 200, satu 409; roll rfid_tag_id kosong
    rs = await asyncio.gather(*[admin.delete(f"/rfid/tags/{tag_id}") for _ in range(2)])
    codes = sorted(x.status_code for x in rs)
    roll_after = db.inventory_rolls.find_one({"id": fx["id"]}, {"_id": 0, "rfid_tag_id": 1})
    check("retire 2× bersamaan → [200, 409]; roll dilepas dari tag", codes == [200, 409] and not roll_after.get("rfid_tag_id"), f"{codes} {roll_after}")

    # ── riwayat pindai: lookup mencatat roll_scans + last_scan; timeline memuat kind scan ──
    r1 = await admin.get("/rfid/lookup", params={"code": tag, "warehouse_id": "wh_probe"})
    r2 = await admin.get("/rfid/lookup", params={"code": tag})
    scans = list(db.roll_scans.find({"roll_id": fx["id"]}, {"_id": 0}))
    roll_after = db.inventory_rolls.find_one({"id": fx["id"]}, {"_id": 0, "last_scan": 1})
    check("2× lookup → 2 roll_scans (via label, by admin, warehouse wh_probe pada yang pertama)",
          r1.status_code == 200 and len(scans) == 2 and scans[0]["via"] == "label" and any(s["warehouse_id"] == "wh_probe" for s in scans) and all(s.get("by") for s in scans), f"{r1.status_code} {len(scans)}")
    check("roll.last_scan terisi & respons lookup ke-2 memuat last_scan pindai pertama",
          bool(roll_after.get("last_scan")) and (r2.json().get("last_scan") or {}).get("at") == roll_after["last_scan"]["at"], str(roll_after.get("last_scan")))
    r3 = await admin.get("/rfid/lookup", params={"code": tag, "record": "false"})
    check("lookup record=false tidak menambah jejak", r3.status_code == 200 and db.roll_scans.count_documents({"roll_id": fx["id"]}) == 2)
    hist = await admin.get(f"/rfid/roll-scans/{fx['id']}")
    check("GET /rfid/roll-scans/{id} → 2 baris terbaru dulu", hist.status_code == 200 and hist.json()["count"] == 2 and hist.json()["scans"][0]["at"] >= hist.json()["scans"][1]["at"])
    tl = await admin.get(f"/inventory/rolls/{fx['id']}/journey-timeline")
    kinds = [e["kind"] for e in tl.json().get("events", [])] if tl.status_code == 200 else []
    check("timeline roll memuat event kind=scan + roll.last_scan", tl.status_code == 200 and kinds.count("scan") == 2 and tl.json()["roll"].get("last_scan"), f"{tl.status_code} {kinds}")

    # ── antrean label QR: POST print-jobs kind=qr_label → job kind qr_label, ZPL ^BQN, muncul di device-jobs printer ──
    r = await admin.post("/rfid/print-jobs", json={"roll_ids": [fx["id"]], "kind": "qr_label", "source": "probe"})
    ok = r.status_code == 200 and r.json().get("kind") == "qr_label" and r.json().get("item_count") == 1
    check("POST /rfid/print-jobs kind=qr_label → job qr_label 1 item, tanpa encode (tag aktif tetap 0)", ok and db.rfid_tags.count_documents({"roll_id": fx["id"], "status": "active"}) == 0, f"{r.status_code} {r.text[:120]}")
    job_id = r.json().get("id") if ok else None
    if job_id:
        z = await admin.get(f"/rfid/print-jobs/{job_id}/zpl")
        check("ZPL job QR memuat ^BQN + nomor roll, tanpa ^RFW", z.status_code == 200 and "^BQN" in z.text and tag in z.text and "^RFW" not in z.text)
        dev = db.rfid_devices.find_one({"type": "printer", "warehouse_id": fx["warehouse_id"]}, {"_id": 0})
        if not dev:
            dev = {"id": "dev_probe13", "code": "PRN-PROBE", "name": "Printer Probe", "type": "printer", "warehouse_id": fx["warehouse_id"], "api_key": "probe13-key", "status": "online"}
            db.rfid_devices.insert_one(dict(dev))
        key = dev.get("api_key")
        anon = httpx.AsyncClient(base_url=API, timeout=60)
        pend = await anon.get("/rfid/device-jobs/pending", headers={"X-Device-Key": key or ""})
        ids = [j["id"] for j in pend.json().get("jobs", [])] if pend.status_code == 200 else []
        check("printer pull device-jobs/pending memuat job QR (antrean bersama RFID)", pend.status_code == 200 and job_id in ids, f"{pend.status_code} {pend.text[:100]}")
        if pend.status_code == 200 and job_id in ids:
            ack = await anon.post(f"/rfid/device-jobs/{job_id}/ack", headers={"X-Device-Key": key})
            check("ack printer → job printed", ack.status_code == 200 and db.rfid_print_jobs.find_one({"id": job_id}, {"_id": 0, "status": 1})["status"] == "printed")
        lst = await admin.get("/rfid/print-jobs", params={"warehouse_id": fx["warehouse_id"]})
        check("daftar print-jobs memuat kind pada job", any(j.get("id") == job_id and j.get("kind") == "qr_label" for j in lst.json().get("jobs", [])))
        db.rfid_print_jobs.delete_one({"id": job_id})
        db.rfid_devices.delete_one({"id": "dev_probe13"})

    # ── advance: tugas sintetis created → 2× bersamaan = [200, 409] ──
    tb = db.wms_tasks.find_one({"flow_type": "inbound", "status": "created"}, {"_id": 0}) or db.wms_tasks.find_one({"flow_type": "inbound"}, {"_id": 0})
    t = {**tb, "id": "wms_probe13_" + uuid.uuid4().hex[:6], "status": "created", "stages": ["created", "receiving", "qc_check", "put_away", "completed"], "entity_id": "ent_ksc", "lot": tag, "refs": []}
    db.wms_tasks.insert_one(dict(t))
    rs = await asyncio.gather(*[admin.post(f"/wms/tasks/{t['id']}/advance", params={"expected_status": "created"}) for _ in range(2)])
    codes = sorted(x.status_code for x in rs)
    st = db.wms_tasks.find_one({"id": t["id"]}, {"_id": 0, "status": 1})["status"]
    check("advance 2× bersamaan (expected_status=created) → [200, 409]; status maju TEPAT satu tahap (receiving)", codes == [200, 409] and st == "receiving", f"{codes} {st}")
    r = await admin.post(f"/wms/tasks/{t['id']}/advance", params={"expected_status": "created"})
    check("advance ulang dgn expected_status basi → 409 STATE_CHANGED", r.status_code == 409 and "STATE_CHANGED" in r.text, f"{r.status_code}")

    # bersih-bersih
    db.wms_tasks.delete_one({"id": t["id"]})
    db.rfid_tags.delete_many({"roll_id": fx["id"]})
    db.roll_scans.delete_many({"roll_id": fx["id"]})
    db.inventory_rolls.delete_one({"id": fx["id"]})
    check("jejak probe bersih", db.inventory_rolls.count_documents({"roll_no": tag}) == 0 and db.roll_scans.count_documents({"roll_no": tag}) == 0)

    print(f"\n{'SEMUA PASS' if not FAILS else str(len(FAILS)) + ' FAIL: ' + ', '.join(FAILS)}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
