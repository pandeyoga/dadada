"""Iter 323 retest — simulate-payment race via precondition claim atomik.

Skenario:
- 3 ronde, tiap ronde 2× POST /api/sales-orders/{id}/simulate-payment via
  asyncio.gather dengan amount=800+ronde (800, 801, 802), method='transfer'.
- Tiap ronde harus TEPAT satu 200 + satu 409 (kode STATE_CHANGED/
  DUPLICATE_PAYMENT/SAGA_IN_PROGRESS), tidak ada 5xx.
- Total paid_total naik tepat 800+801+802=2403; invoices bertambah tepat 3;
  dokumen tanpa saga_lock.
- Tunggu 11 detik → POST amount 802 lagi harus 200 (pembayaran identik setelah
  jendela 10 dtk sah).
"""
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


def extract_code(resp):
    try:
        j = resp.json()
    except Exception:
        return ""
    d = j.get("detail") if isinstance(j, dict) else None
    if isinstance(d, dict):
        return d.get("code") or ""
    return ""


async def main():
    from pymongo import MongoClient
    db = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))[
        os.environ.get("DB_NAME", "test_database")]
    admin = await login("admin@kainnusantara.id")

    # Cari SO KSC yang belum lunas dan cukup outstanding untuk 3×~802 + 1×802 = ~3207
    needed = 800 + 801 + 802 + 802 + 5
    so = None
    for cand in db.sales_orders.find({
        "entity_id": "ent_ksc",
        "status": {"$in": ["confirmed", "shipped", "done", "delivered"]},
        "payment_status": {"$ne": "paid"},
        "saga_lock": {"$exists": False},
        "order_type": {"$ne": "sample"},
    }, {"_id": 0}):
        gt = float(cand.get("grand_total") or 0)
        paid0 = float(cand.get("paid_total") or 0)
        if gt - paid0 >= needed:
            so = cand
            break
    check("ada SO KSC belum lunas cukup untuk 3+1 ronde", bool(so),
          f"needed_outstanding={needed}")
    if not so:
        print("\nGAGAL:", FAILS)
        return 1

    paid0 = float(so.get("paid_total") or 0)
    n_inv0 = db.invoices.count_documents({"order_id": so["id"]})
    print(f"SO {so['number']} id={so['id']} gt={so.get('grand_total')} paid0={paid0} n_inv0={n_inv0}")

    winners_sum = 0.0
    for r_idx in range(3):
        amt = 800.0 + r_idx  # 800, 801, 802
        rs = await asyncio.gather(*[
            admin.post(f"/sales-orders/{so['id']}/simulate-payment",
                       json={"amount": amt, "method": "transfer", "created_by": "qa"})
            for _ in range(2)
        ])
        codes = sorted(x.status_code for x in rs)
        code_reasons = [extract_code(x) for x in rs]
        no_5xx = all(x.status_code < 500 for x in rs)
        one_200 = codes.count(200) == 1
        one_409 = codes.count(409) == 1
        r409 = next((x for x in rs if x.status_code == 409), None)
        reason = extract_code(r409) if r409 else ""
        check(f"ronde{r_idx+1} amt={amt}: tidak ada 5xx", no_5xx, f"codes={codes}")
        check(f"ronde{r_idx+1} amt={amt}: TEPAT satu 200 + satu 409",
              one_200 and one_409,
              f"codes={codes} reasons={code_reasons} bodies={[x.text[:120] for x in rs]}")
        check(f"ronde{r_idx+1}: kode 409 ∈ STATE_CHANGED/DUPLICATE_PAYMENT/SAGA_IN_PROGRESS",
              reason in ("STATE_CHANGED", "DUPLICATE_PAYMENT", "SAGA_IN_PROGRESS"),
              f"reason={reason!r}")
        if one_200:
            winners_sum += amt

    after = db.sales_orders.find_one({"id": so["id"]}, {"_id": 0})
    n_inv1 = db.invoices.count_documents({"order_id": so["id"]})
    paid_delta = round(float(after["paid_total"]) - paid0, 2)
    check("paid_total naik tepat 2403 (800+801+802)", paid_delta == 2403.0,
          f"delta={paid_delta} winners_sum={winners_sum}")
    check("invoices bertambah tepat 3", n_inv1 - n_inv0 == 3, f"{n_inv0}→{n_inv1}")
    check("dokumen tanpa saga_lock", "saga_lock" not in after,
          f"lock={after.get('saga_lock')}")

    # Tunggu >10 dtk → pembayaran identik ke amount 802 harus 200
    print("… menunggu 11 detik untuk uji pembayaran identik setelah jendela 10s …")
    await asyncio.sleep(11)
    r2 = await admin.post(f"/sales-orders/{so['id']}/simulate-payment",
                          json={"amount": 802.0, "method": "transfer", "created_by": "qa"})
    check("setelah 11 dtk POST amount=802 identik → 200",
          r2.status_code == 200, f"{r2.status_code} {r2.text[:200]}")
    n_inv2 = db.invoices.count_documents({"order_id": so["id"]})
    check("invoices bertambah lagi tepat 1", n_inv2 - n_inv1 == 1, f"{n_inv1}→{n_inv2}")

    print("\nGAGAL:" if FAILS else "\nSEMUA PASS", FAILS)
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
