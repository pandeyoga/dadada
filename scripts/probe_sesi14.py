"""Probe runtime sesi 14: Idempotency-Key (replay → balasan sama, efek 1×; concurrent → 1 proses + 409/replay),
klaim verify/cycle-count complete, kompensasi transfer antar-PT, POST /rfid/roll-scans (offline replay, bin, last_scan
hanya maju), GET /rfid/printer-status. Jalankan: python scripts/probe_sesi14.py"""
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
    tag = "PROBE14-" + uuid.uuid4().hex[:4]

    # ── Idempotency: scan-pick tugas sintetis dgn kunci sama 3× → picked_qty 4 (bukan 12), balasan replay ──
    base = db.wms_tasks.find_one({"flow_type": "outbound", "status": "created", "entity_id": "ent_ksc"}, {"_id": 0})
    t = {**base, "id": "wms_probe14_" + uuid.uuid4().hex[:6], "order_id": None, "quantity": 10.0, "picked_qty": 0.0, "scan_log": [], "refs": [], "lot": tag}
    db.wms_tasks.insert_one(dict(t))
    key = "idem-" + uuid.uuid4().hex
    r1 = await admin.post(f"/outbound/tasks/{t['id']}/scan-pick", params={"actual_qty": 4}, headers={"Idempotency-Key": key})
    r2 = await admin.post(f"/outbound/tasks/{t['id']}/scan-pick", params={"actual_qty": 4}, headers={"Idempotency-Key": key})
    r3 = await admin.post(f"/outbound/tasks/{t['id']}/scan-pick", params={"actual_qty": 4}, headers={"Idempotency-Key": key})
    picked = db.wms_tasks.find_one({"id": t["id"]}, {"_id": 0, "picked_qty": 1})["picked_qty"]
    check("Idempotency-Key sama 3× berurutan → efek 1× (picked 4), replay 200 + header X-Idempotent-Replay",
          r1.status_code == 200 and r2.status_code == 200 and r3.status_code == 200 and picked == 4.0
          and r2.headers.get("x-idempotent-replay") == "true" and r2.json() == r1.json(), f"{r1.status_code}/{r2.status_code}/{r3.status_code} picked={picked}")
    key2 = "idem-" + uuid.uuid4().hex
    rs = await asyncio.gather(*[admin.post(f"/outbound/tasks/{t['id']}/scan-pick", params={"actual_qty": 2}, headers={"Idempotency-Key": key2}) for _ in range(4)])
    codes = sorted(x.status_code for x in rs)
    picked = db.wms_tasks.find_one({"id": t["id"]}, {"_id": 0, "picked_qty": 1})["picked_qty"]
    check("Idempotency-Key sama 4× BERSAMAAN → efek 1× (picked 6); lainnya 409 IDEMPOTENT_IN_PROGRESS atau replay 200",
          picked == 6.0 and all(c in (200, 409) for c in codes) and codes.count(200) >= 1, f"{codes} picked={picked}")
    key3 = "idem-" + uuid.uuid4().hex
    r = await admin.post(f"/outbound/tasks/{t['id']}/scan-pick", params={"actual_qty": 99}, headers={"Idempotency-Key": key3})
    r_again = await admin.post(f"/outbound/tasks/{t['id']}/scan-pick", params={"actual_qty": 99}, headers={"Idempotency-Key": key3})
    check("balasan 4xx juga di-replay apa adanya (400 → 400 replay)", r.status_code == 400 and r_again.status_code == 400 and r_again.headers.get("x-idempotent-replay") == "true", f"{r.status_code}/{r_again.status_code}")
    r_nokey = await admin.post(f"/outbound/tasks/{t['id']}/scan-pick", params={"actual_qty": 1})
    check("tanpa header → perilaku biasa (200, picked 7)", r_nokey.status_code == 200 and db.wms_tasks.find_one({"id": t["id"]}, {"_id": 0, "picked_qty": 1})["picked_qty"] == 7.0)
    db.wms_tasks.delete_one({"id": t["id"]})
    db.idempotency_keys.delete_many({"key": {"$in": [key, key2, key3]}})

    # ── roll-scans offline replay + bin + last_scan hanya maju ──
    roll = db.inventory_rolls.find_one({"owner_entity_id": "ent_ksc", "status": "available"}, {"_id": 0})
    fx = {**roll, "id": "roll_probe14_" + uuid.uuid4().hex[:6], "roll_no": tag, "rfid_tag_id": None, "last_scan": None}
    db.inventory_rolls.insert_one(dict(fx))
    k = "idem-" + uuid.uuid4().hex
    body = {"code": tag, "bin_id": "A-01-03", "scanned_at": "2026-09-06T01:00:00+00:00"}
    a = await admin.post("/rfid/roll-scans", json=body, headers={"Idempotency-Key": k})
    b = await admin.post("/rfid/roll-scans", json=body, headers={"Idempotency-Key": k})
    n = db.roll_scans.count_documents({"roll_id": fx["id"]})
    ls = db.inventory_rolls.find_one({"id": fx["id"]}, {"_id": 0, "last_scan": 1})["last_scan"]
    check("POST /rfid/roll-scans (offline replay) 2× kunci sama → 1 jejak, bin tercatat, offline=true, last_scan terisi",
          a.status_code == 200 and b.status_code == 200 and n == 1 and ls and ls.get("bin_id") == "A-01-03" and db.roll_scans.find_one({"roll_id": fx["id"]})["offline"] is True, f"{a.status_code}/{b.status_code} n={n} {ls}")
    now_scan = await admin.get("/rfid/lookup", params={"code": tag, "bin_id": "B-07"})
    ls2 = db.inventory_rolls.find_one({"id": fx["id"]}, {"_id": 0, "last_scan": 1})["last_scan"]
    old = await admin.post("/rfid/roll-scans", json={"code": tag, "bin_id": "LAMA", "scanned_at": "2026-09-01T00:00:00+00:00"})
    ls3 = db.inventory_rolls.find_one({"id": fx["id"]}, {"_id": 0, "last_scan": 1})["last_scan"]
    check("lookup online mencatat bin B-07 sebagai last_scan; pindai offline LAMA tersimpan tapi TIDAK menimpa last_scan",
          now_scan.status_code == 200 and ls2.get("bin_id") == "B-07" and old.status_code == 200 and ls3.get("bin_id") == "B-07"
          and db.roll_scans.count_documents({"roll_id": fx["id"]}) == 3, f"{ls2} → {ls3}")
    tl = await admin.get(f"/inventory/rolls/{fx['id']}/journey-timeline")
    check("timeline memuat 'bin A-01-03' pada event scan", tl.status_code == 200 and any("bin A-01-03" in e.get("label", "") for e in tl.json().get("events", [])))
    bad = await admin.post("/rfid/roll-scans", json={"code": "TIDAK-ADA-XYZ"})
    check("roll-scans kode tak dikenal → 404 CODE_UNKNOWN", bad.status_code == 404 and "CODE_UNKNOWN" in bad.text)
    db.roll_scans.delete_many({"roll_id": fx["id"]}); db.inventory_rolls.delete_one({"id": fx["id"]}); db.idempotency_keys.delete_many({"key": k})

    # ── klaim verify-sessions complete & cycle-count complete ──
    for kind, path in (("verify", "/rfid/verify-sessions/{}/complete"), ("cycle_count", "/rfid/cycle-count/{}/complete")):
        sess = db.rfid_verify_sessions.find_one({"kind": kind, "status": "open"} if kind == "cycle_count" else {"status": "open", "kind": {"$ne": "cycle_count"}}, {"_id": 0, "id": 1})
        if not sess:
            print(f"SKIP  tidak ada sesi {kind} open"); continue
        db.rfid_verify_sessions.update_one({"id": sess["id"]}, {"$set": {"saga_lock": LOCK}})
        r = await admin.post(path.format(sess["id"]))
        check(f"{kind} complete saat terkunci → 409 SAGA_IN_PROGRESS", r.status_code == 409 and "SAGA_IN_PROGRESS" in r.text, f"{r.status_code} {r.text[:100]}")
        db.rfid_verify_sessions.update_one({"id": sess["id"]}, {"$unset": {"saga_lock": ""}})
    # sesi cycle count sintetis: complete 2× bersamaan → satu 200, satu 4xx, satu CC
    wh = db.warehouses.find_one({}, {"_id": 0, "id": 1})["id"]
    cs = {"id": "vs_probe14_" + uuid.uuid4().hex[:6], "kind": "cycle_count", "status": "open", "warehouse_id": wh, "owner_entity_id": "ent_ksc",
          "expected": [], "scanned_epcs": [], "created_at": "2026-09-06T00:00:00+00:00", "lot": tag}
    db.rfid_verify_sessions.insert_one(dict(cs))
    rs = await asyncio.gather(*[admin.post(f"/rfid/cycle-count/{cs['id']}/complete") for _ in range(2)])
    codes = sorted(x.status_code for x in rs)
    ccs = db.rfid_cycle_counts.count_documents({"session_id": cs["id"]})
    st = db.rfid_verify_sessions.find_one({"id": cs["id"]}, {"_id": 0, "status": 1, "saga_lock": 1})
    check("cycle-count complete 2× bersamaan → satu 200 + satu 4xx; tepat 1 CC; sesi completed tanpa kunci", codes[0] == 200 and codes[1] in (400, 409) and ccs == 1 and st["status"] == "completed" and "saga_lock" not in st, f"{codes} cc={ccs} {st}")
    db.rfid_cycle_counts.delete_many({"session_id": cs["id"]}); db.rfid_verify_sessions.delete_one({"id": cs["id"]})

    # ── transfer antar-PT: item palsu → 4xx dan reservasi item pertama dilepas ──
    src_roll = db.inventory_rolls.find_one({"owner_entity_id": "ent_ksc", "status": "available", "length_remaining": {"$gt": 1}}, {"_id": 0})
    dest = db.business_entities.find_one({"id": {"$ne": "ent_ksc"}}, {"_id": 0, "id": 1})["id"]
    before = db.inventory_rolls.count_documents({"owner_entity_id": "ent_ksc", "status": "reserved", "reserved_ref.type": "transfer"})
    r = await admin.post("/transfers/inter-company", json={"source_entity_id": "ent_ksc", "dest_entity_id": dest, "items": [
        {"product_id": src_roll["product_id"], "quantity": 1, "unit": src_roll.get("unit", "yard")}, {"product_id": "prod_palsu_" + uuid.uuid4().hex[:5], "quantity": 1, "unit": "yard"}]})
    after = db.inventory_rolls.count_documents({"owner_entity_id": "ent_ksc", "status": "reserved", "reserved_ref.type": "transfer"})
    check("transfer antar-PT item palsu → 4xx dan reservasi dilepas (kompensasi)", r.status_code in (400, 404, 422) and after == before, f"{r.status_code} reserved {before}→{after}")

    # ── printer-status ──
    ps = await admin.get("/rfid/printer-status")
    ok = ps.status_code == 200 and "warehouses" in ps.json() and "total_queued_labels" in ps.json()
    check("GET /rfid/printer-status → per gudang: printers(online), queued_labels, stuck", ok and all({"printers", "queued_labels", "stuck", "online_printers"} <= set(w) for w in ps.json()["warehouses"]), f"{ps.status_code} {ps.text[:120]}")
    # job QR tanpa printer online → gudang tsb stuck
    jr = await admin.post("/rfid/print-jobs", json={"roll_ids": [src_roll["id"]], "kind": "qr_label", "source": "probe14"})
    ps2 = await admin.get("/rfid/printer-status", params={"warehouse_id": src_roll["warehouse_id"]})
    w = next((x for x in ps2.json()["warehouses"] if x["warehouse_id"] == src_roll["warehouse_id"]), None)
    check("gudang dengan label menunggu terlihat: queued_labels ≥ 1 dan stuck = (tak ada printer online)",
          jr.status_code == 200 and w and w["queued_labels"] >= 1 and w["stuck"] == (w["online_printers"] == 0), f"{w}")
    if jr.status_code == 200:
        db.rfid_print_jobs.delete_one({"id": jr.json()["id"]})

    check("jejak probe bersih", db.wms_tasks.count_documents({"lot": tag}) == 0 and db.inventory_rolls.count_documents({"roll_no": tag}) == 0)
    print(f"\n{'SEMUA PASS' if not FAILS else str(len(FAILS)) + ' FAIL: ' + ', '.join(FAILS)}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
