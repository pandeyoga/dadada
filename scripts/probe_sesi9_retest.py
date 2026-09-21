"""Sesi 9 retest — 2 temuan iteration_321.
- simulate-payment: klik-ganda identik ≤10s → 409 DUPLICATE_PAYMENT; setelah >10s → 200.
- closing reopen ∥ reclose: tidak ada 5xx, dokumen akhir tanpa saga_lock, status ∈ {reopened, closed}.
Jalankan: python scripts/probe_sesi9_retest.py"""
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

    # ── simulate-payment: pagar klik-ganda ────────────────────────────────
    so = db.sales_orders.find_one({
        "entity_id": "ent_ksc",
        "status": {"$in": ["confirmed", "shipped", "done", "delivered"]},
        "payment_status": {"$ne": "paid"},
        "saga_lock": {"$exists": False},
        "order_type": {"$ne": "sample"},
    }, {"_id": 0})
    check("ada SO KSC belum lunas untuk uji", bool(so))
    if so:
        gt = float(so.get("grand_total") or 0)
        paid0 = float(so.get("paid_total") or 0)
        n_inv0 = db.invoices.count_documents({"order_id": so["id"]})
        # amount tetap 700 agar konsisten dengan skenario retest
        amt = 700.0
        # butuh outstanding >= 700 * 2 supaya pembayaran ke-2 setelah 11s masih sah
        available = gt - paid0
        if available < amt * 2 + 5:
            # fallback: pakai amt kecil supaya cukup untuk 2× bayar
            amt = round(max(1.0, min(available / 2.5, 700.0)), 2)
        rs = await asyncio.gather(*[
            admin.post(f"/sales-orders/{so['id']}/simulate-payment",
                       json={"amount": amt, "method": "transfer", "created_by": "qa"})
            for _ in range(2)
        ])
        codes = sorted(x.status_code for x in rs)
        bodies = [x.json() if x.headers.get("content-type", "").startswith("application/json") else {} for x in rs]
        one_ok = codes.count(200) == 1
        one_409 = codes.count(409) == 1
        code_reason = ""
        if one_409:
            r409 = next(x for x in rs if x.status_code == 409)
            j = r409.json()
            code_reason = ((j.get("detail") or {}).get("code") if isinstance(j.get("detail"), dict) else j.get("detail", "")) or ""
        after = db.sales_orders.find_one({"id": so["id"]}, {"_id": 0, "paid_total": 1, "saga_lock": 1})
        n_inv1 = db.invoices.count_documents({"order_id": so["id"]})
        paid_delta = round(float(after["paid_total"]) - paid0, 2)
        check(
            "2× simulate-payment bersamaan/berurutan cepat → satu 200 + satu 409",
            one_ok and one_409,
            f"codes={codes} reason={code_reason!r} bodies={[str(b)[:80] for b in bodies]}",
        )
        check(
            "409 memakai kode SAGA_IN_PROGRESS atau DUPLICATE_PAYMENT",
            code_reason in ("SAGA_IN_PROGRESS", "DUPLICATE_PAYMENT"),
            f"code={code_reason!r}",
        )
        check(
            f"paid_total naik tepat {amt}",
            paid_delta == amt,
            f"delta={paid_delta} amt={amt}",
        )
        check("invoices bertambah tepat 1", n_inv1 - n_inv0 == 1, f"{n_inv0}→{n_inv1}")
        check("tanpa saga_lock setelah selesai", "saga_lock" not in after, f"lock={after.get('saga_lock')}")

        # Tunggu 11 detik → pembayaran kedua yang sah harus 200
        print("… menunggu 11 detik untuk uji pembayaran kedua yang sah …")
        await asyncio.sleep(11)
        r2 = await admin.post(f"/sales-orders/{so['id']}/simulate-payment",
                              json={"amount": amt, "method": "transfer", "created_by": "qa"})
        check(">10 detik kemudian pembayaran identik → 200 (sah)", r2.status_code == 200, f"{r2.status_code} {r2.text[:120]}")
        n_inv2 = db.invoices.count_documents({"order_id": so["id"]})
        check("invoices bertambah lagi tepat 1", n_inv2 - n_inv1 == 1, f"{n_inv1}→{n_inv2}")

    # ── closing reopen ∥ reclose: tidak pernah 5xx, akhir tanpa saga_lock ──
    cid = f"cls_retest_{uuid.uuid4().hex[:8]}"
    db.period_closings.insert_one({
        "id": cid, "entity_id": "ent_ksc", "period_type": "month",
        "period_key": "2019-11", "start_date": "2019-11-01", "end_date": "2019-11-30",
        "status": "closed", "journal_entry_id": None, "net_income": 0,
        "created_at": "2026-09-05T00:00:00+00:00",
    })
    rs = await asyncio.gather(
        admin.post(f"/finance/closing/{cid}/reopen"),
        admin.post(f"/finance/closing/{cid}/reclose"),
    )
    codes = [x.status_code for x in rs]
    doc = db.period_closings.find_one({"id": cid}, {"_id": 0})
    check("reopen ∥ reclose: TIDAK ada 5xx", all(c < 500 for c in codes), f"codes={codes} bodies={[x.text[:100] for x in rs]}")
    check("dokumen akhir TANPA saga_lock", doc is not None and "saga_lock" not in doc, f"doc_lock={doc.get('saga_lock') if doc else None}")
    check("status akhir ∈ {reopened, closed}", doc is not None and doc.get("status") in ("reopened", "closed"), f"status={doc.get('status') if doc else None}")

    # cleanup dokumen sintetis
    db.journal_entries.delete_many({"source_id": cid})
    db.period_closings.delete_one({"id": cid})

    print("\nGAGAL:" if FAILS else "\nSEMUA PASS", FAILS)
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
