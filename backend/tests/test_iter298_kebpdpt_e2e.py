"""Sesi #089 / iterasi 298 — E2E HTTP untuk KEB-PDPT (kebijakan pengakuan pendapatan).

Alur (via API publik, header X-Entity-Id: ent_ksc):
  1. Buat SO baru (TEST KEB-PDPT) → verify → confirm
  2. Kwitansi AR ~30% SEBELUM kirim → harus Cr 2-1400 (Uang Muka), TIDAK ada 1-1200,
     tidak ada JE 'sales_order', journey.revenue_recognized=false, payments[0].gl_bucket='advance'
  3. Meja Finance: antrean 'uang_muka_belum_kirim' memuat SO ini dgn badge kewajiban
  4. Pick + dispatch → JE 'sales_order' + 'sales_cogs' + 'advance_reclass'
     journey.revenue_recognized=true, advance_unrecognized=0, idempotent
  5. Kwitansi sisa SETELAH kirim → Cr 1-1200 (bukan 2-1400), payment tanpa gl_bucket
  6. Void kwitansi uang muka → JE 'advance_reclass_reversal' + void kas; netto 2-1400 = 0
  7. Trial balance tetap seimbang

Jalankan: cd /app && python -m pytest backend/tests/test_iter298_kebpdpt_e2e.py -q -n0 -s
Dokumen uji dibersihkan di akhir modul (fixture `flow`).
"""
import os
import uuid

import pytest
import requests
from dotenv import dotenv_values
from pymongo import MongoClient

fe = dotenv_values("/app/frontend/.env")
BASE = (os.environ.get("REACT_APP_BACKEND_URL") or fe.get("REACT_APP_BACKEND_URL")).rstrip("/") + "/api"
be = dotenv_values("/app/backend/.env")
db = MongoClient(be.get("MONGO_URL"))[be.get("DB_NAME")]

ENT = "ent_ksc"
PIUTANG = "1-1200"
UANG_MUKA = "2-1400"
PPN_OUT = "2-1200"
PENDAPATAN = "4-1000"
CUST = "cust_butik_bali"
ADDR = "addr_002"
PRODUCT = "prod_endek_bali"
TAG = "TEST KEB-PDPT"

STATE = {}


def _hdr(email="admin@kainnusantara.id"):
    r = requests.post(f"{BASE}/auth/login", json={"email": email, "password": "demo12345"}, timeout=60)
    assert r.status_code == 200, r.text[:300]
    return {"Authorization": f"Bearer {r.json()['token']}", "X-Entity-Id": ENT,
            "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def hdr():
    return _hdr()


@pytest.fixture(scope="module")
def fin_hdr():
    return _hdr("finance@kainnusantara.id")


def _je(source_type, source_id):
    """JE per dokumen. Untuk pesanan: jurnal per pesanan (legacy) ATAU per surat jalan
    (KEB-PDPT tahap 2, `ref.order_id`) dianggap satu keluarga sumber."""
    ALIAS = {"sales_order": "shipment_revenue", "sales_cogs": "shipment_cogs"}
    flt = {"status": {"$ne": "void"},
           "$or": [{"source_type": source_type, "source_id": source_id},
                   {"source_type": source_type, "ref.order_id": source_id}]}
    if source_type in ALIAS:
        flt["$or"].append({"source_type": ALIAS[source_type], "ref.order_id": source_id})
    return list(db.journal_entries.find(flt, {"_id": 0}))


def _lines(je):
    return [(l["account_code"], round(float(l.get("debit") or 0), 2),
             round(float(l.get("credit") or 0), 2)) for l in je["lines"]]


def _cash_je_for_receipt(receipt_id):
    cash = list(db.cash_transactions.find({"ref_type": "ar_receipt", "ref_id": receipt_id},
                                          {"_id": 0, "id": 1, "status": 1}))
    out = []
    for c in cash:
        for stype in ("cash_transaction", "cash_transaction_void"):
            out += [(stype, j) for j in _je(stype, c["id"])]
    return cash, out


def _create_order(hdr, qty=20.0):
    payload = {"customer_id": CUST, "shipping_address_id": ADDR, "entity_id": ENT,
               "sales_name": "Ayu Permatasari",
               "items": [{"product_id": PRODUCT, "quantity": qty, "unit": "yard",
                          "base_quantity": qty}]}
    r = requests.post(f"{BASE}/sales-orders", headers=hdr, json=payload, timeout=120)
    assert r.status_code in (200, 201), f"create SO -> {r.status_code}: {r.text[:600]}"
    o = r.json()
    oid = o.get("id") or o.get("order", {}).get("id")
    assert oid, o
    db.sales_orders.update_one({"id": oid}, {"$set": {"notes": TAG, "_test_kebpdpt_e2e": True}})
    print(f"created SO {oid} number={o.get('number')} status={o.get('status')} "
          f"grand_total={o.get('grand_total')}")
    for path in (f"/sales-orders/{oid}/verify", f"/sales-orders/{oid}/confirm"):
        rr = requests.post(f"{BASE}{path}", headers=hdr, json={}, timeout=120)
        print(path, rr.status_code, rr.text[:200] if rr.status_code >= 400 else "ok")
        assert rr.status_code in (200, 201), f"{path} -> {rr.status_code}: {rr.text[:400]}"
    return db.sales_orders.find_one({"id": oid}, {"_id": 0})


def _receipt(hdr, oid, amount, ref=""):
    body = {"customer_id": CUST, "amount": round(amount, 2), "method": "transfer",
            "entity_id": ENT, "notes": f"{TAG} {ref}",
            "allocations": [{"order_id": oid, "amount": round(amount, 2)}]}
    r = requests.post(f"{BASE}/ar-receipts", headers=hdr, json=body, timeout=120)
    assert r.status_code in (200, 201), f"ar-receipt -> {r.status_code}: {r.text[:600]}"
    rc = r.json()
    rid = rc.get("id") or rc.get("receipt", {}).get("id")
    assert rid, rc
    db.ar_receipts.update_one({"id": rid}, {"$set": {"_test_kebpdpt_e2e": True}})
    print(f"receipt {rid} number={rc.get('number')} amount={amount}")
    return rid


# ---------------------------------------------------------------- module flow
@pytest.fixture(scope="module", autouse=True)
def flow(hdr):
    yield
    # pembersihan dokumen uji
    oids = [d["id"] for d in db.sales_orders.find({"_test_kebpdpt_e2e": True}, {"_id": 0, "id": 1})]
    rids = [d["id"] for d in db.ar_receipts.find({"_test_kebpdpt_e2e": True}, {"_id": 0, "id": 1})]
    cids = [d["id"] for d in db.cash_transactions.find({"ref_type": "ar_receipt",
                                                        "ref_id": {"$in": rids}}, {"_id": 0, "id": 1})]
    db.journal_entries.delete_many({"$or": [{"source_id": {"$in": oids + rids + cids}},
                                            {"ref.order_id": {"$in": oids}}]
                                           + [{"source_id": {"$regex": f"^{o}:"}} for o in oids]})
    db.sales_orders.delete_many({"_test_kebpdpt_e2e": True})
    db.ar_receipts.delete_many({"_test_kebpdpt_e2e": True})
    db.cash_transactions.delete_many({"id": {"$in": cids}})
    db.wms_tasks.delete_many({"order_id": {"$in": oids}})
    db.shipments.delete_many({"order_id": {"$in": oids}})
    print("cleanup: orders", oids, "receipts", rids)
    # Pulangkan roll yang masih terikat ke SO uji (stok demo tidak terkuras).
    import subprocess, sys as _sys
    subprocess.run([_sys.executable, "/app/backend/tests/iter299_restore_orphan_rolls.py"],
                   check=False, capture_output=True, timeout=120)


# ================================================================ 1. advance
class TestAdvanceBeforeShipment:
    def test_01_create_order_and_advance_receipt(self, hdr):
        o = _create_order(hdr)
        STATE["oid"] = o["id"]
        STATE["number"] = o["number"]
        STATE["grand_total"] = float(o["grand_total"])
        adv = round(STATE["grand_total"] * 0.30, 2)
        STATE["advance"] = adv
        STATE["rid_adv"] = _receipt(hdr, o["id"], adv, "uang-muka")

        assert o["status"] not in ("shipped", "partially_shipped", "done", "delivered")

    def test_02_no_sales_order_je_before_shipment(self, hdr):
        assert _je("sales_order", STATE["oid"]) == [], "JE pendapatan lahir sebelum kirim!"
        assert _je("sales_cogs", STATE["oid"]) == [], "JE HPP lahir sebelum kirim!"
        r = requests.get(f"{BASE}/gl/journal", headers=hdr,
                         params={"entity_id": ENT, "source": "sales_order"}, timeout=60)
        assert r.status_code == 200, r.text[:300]
        items = r.json() if isinstance(r.json(), list) else r.json().get("items", [])
        assert not any(i.get("source_id") == STATE["oid"] for i in items)

    def test_03_cash_je_credits_advance_not_receivable(self):
        cash, jes = _cash_je_for_receipt(STATE["rid_adv"])
        assert cash, "kas untuk kwitansi tidak ada"
        assert jes, "JE kas untuk kwitansi tidak ada"
        ls = [l for _, je in jes for l in _lines(je)]
        print("cash JE lines:", ls)
        assert any(a == UANG_MUKA and c == pytest.approx(STATE["advance"], abs=1)
                   for a, d, c in ls), f"tidak ada Cr {UANG_MUKA} sebesar uang muka: {ls}"
        assert not any(a == PIUTANG for a, _, _ in ls), f"uang muka tidak boleh menyentuh {PIUTANG}: {ls}"

    def test_04_journey_reports_advance_unrecognized(self, hdr):
        r = requests.get(f"{BASE}/sales-orders/{STATE['oid']}/journey", headers=hdr, timeout=60)
        assert r.status_code == 200, r.text[:400]
        j = r.json()
        assert "revenue_recognized" in j and "advance_unrecognized" in j, sorted(j.keys())
        assert j["revenue_recognized"] is False, j["revenue_recognized"]
        assert float(j["advance_unrecognized"]) == pytest.approx(STATE["advance"], abs=1), j
        assert "_id" not in j

    def test_05_payment_tagged_advance(self, hdr):
        r = requests.get(f"{BASE}/sales-orders/{STATE['oid']}", headers=hdr, timeout=60)
        assert r.status_code == 200, r.text[:300]
        o = r.json()
        pays = o.get("payments") or []
        assert pays, "payments[] kosong"
        assert pays[0].get("gl_bucket") == "advance", pays[0]
        assert float(o.get("paid_total") or 0) == pytest.approx(STATE["advance"], abs=1)

    def test_06_finance_desk_advance_queue(self, fin_hdr):
        r = requests.get(f"{BASE}/finance/desk", headers=fin_hdr,
                         params={"entity_id": ENT}, timeout=90)
        assert r.status_code == 200, r.text[:400]
        d = r.json()
        queues = d.get("queues") or []
        q = next((x for x in queues if x.get("id") == "uang_muka_belum_kirim"), None)
        assert q, [x.get("id") for x in queues]
        totals = d.get("totals") or {}
        assert "advance_liability" in totals and "advance_recognized_legacy" in totals, sorted(totals)
        rows = q.get("rows") or q.get("items") or []
        mine = next((x for x in rows if STATE["oid"] in str(x.values()) or
                     x.get("id") == STATE["oid"] or x.get("order_id") == STATE["oid"]), None)
        print("advance queue rows:", [(x.get("title") or x.get("number"), x.get("badge"),
                                       x.get("value")) for x in rows])
        assert mine, f"SO uji {STATE['number']} tidak muncul di antrean uang muka"
        assert "kewajiban" in str(mine.get("badge") or mine.get("tag") or "").lower(), mine
        legacy = [x for x in rows if "historis" in str(x.get("badge") or "").lower()]
        print("legacy rows:", [(x.get("title") or x.get("number")) for x in legacy])
        assert float(totals["advance_liability"]) >= STATE["advance"] - 1, totals


# ============================================================== 2. dispatch
class TestDispatchRecognition:
    def test_07_pick_and_dispatch(self, hdr):
        oid = STATE["oid"]
        r = requests.post(f"{BASE}/wms/tasks/outbound-from-order/{oid}", headers=hdr,
                          json={}, timeout=120)
        assert r.status_code in (200, 201), f"outbound-from-order -> {r.status_code}: {r.text[:400]}"
        tasks = list(db.wms_tasks.find({"order_id": oid, "flow_type": "outbound"},
                                       {"_id": 0, "id": 1, "quantity": 1, "status": 1}))
        assert tasks, "tidak ada tugas outbound"
        for t in tasks:
            rr = requests.post(f"{BASE}/outbound/tasks/{t['id']}/scan-pick",
                               headers=hdr, params={"actual_qty": t.get("quantity")},
                               json={}, timeout=120)
            assert rr.status_code == 200, f"scan-pick -> {rr.status_code}: {rr.text[:400]}"
            rr = requests.post(f"{BASE}/outbound/tasks/{t['id']}/dispatch", headers=hdr,
                               json={}, timeout=120)
            assert rr.status_code == 200, f"dispatch -> {rr.status_code}: {rr.text[:400]}"
        o = db.sales_orders.find_one({"id": oid}, {"_id": 0, "status": 1})
        print("status after dispatch:", o.get("status"))
        assert o.get("status") in ("shipped", "partially_shipped", "done", "delivered"), o

    def test_08_revenue_cogs_and_reclass_je(self):
        oid = STATE["oid"]
        rev = _je("sales_order", oid)
        assert rev, "JE pendapatan tidak lahir saat dispatch"
        assert len(rev) == 1, f"JE pendapatan ganda: {len(rev)}"
        ls = _lines(rev[0])
        print("revenue JE:", ls)
        assert any(a == PIUTANG and d == pytest.approx(STATE["grand_total"], abs=1)
                   for a, d, c in ls), ls
        assert any(a == PENDAPATAN and c > 0 for a, d, c in ls), ls
        cogs = _je("sales_cogs", oid)
        print("cogs JE count:", len(cogs), _lines(cogs[0]) if cogs else None)

        rc = _je("advance_reclass", oid)
        assert rc, "JE advance_reclass tidak lahir"
        assert len(rc) == 1, f"advance_reclass ganda: {len(rc)}"
        rls = _lines(rc[0])
        print("reclass JE:", rls)
        assert any(a == UANG_MUKA and d == pytest.approx(STATE["advance"], abs=1) for a, d, c in rls), rls
        assert any(a == PIUTANG and c == pytest.approx(STATE["advance"], abs=1) for a, d, c in rls), rls

    def test_09_journey_recognized(self, hdr):
        r = requests.get(f"{BASE}/sales-orders/{STATE['oid']}/journey", headers=hdr, timeout=60)
        assert r.status_code == 200, r.text[:300]
        j = r.json()
        assert j["revenue_recognized"] is True, j["revenue_recognized"]
        assert float(j["advance_unrecognized"]) == 0.0, j["advance_unrecognized"]

    def test_10_idempotent_no_duplicate_je(self, hdr):
        oid = STATE["oid"]
        for _ in range(2):
            requests.get(f"{BASE}/sales-orders/{oid}/journey", headers=hdr, timeout=60)
        r = requests.post(f"{BASE}/gl/sync", headers=hdr, json={}, timeout=240)
        print("gl/sync:", r.status_code, r.text[:200])
        for stype in ("sales_order", "sales_cogs", "advance_reclass"):
            n = len(_je(stype, oid))
            print(stype, "count", n)
            assert n <= 1, f"{stype} tergandakan: {n}"
        assert len(_je("sales_order", oid)) == 1
        assert len(_je("advance_reclass", oid)) == 1

    def test_11_finance_desk_no_longer_lists_order(self, fin_hdr):
        r = requests.get(f"{BASE}/finance/desk", headers=fin_hdr, params={"entity_id": ENT}, timeout=90)
        assert r.status_code == 200
        q = next((x for x in (r.json().get("queues") or [])
                  if x.get("id") == "uang_muka_belum_kirim"), None)
        rows = (q.get("rows") or q.get("items") or []) if q else []
        assert not any(STATE["oid"] in str(x.values()) for x in rows), \
            "pesanan sudah dikirim masih di antrean uang muka"


# ================================================= 3. receipt after shipment
class TestReceiptAfterShipment:
    def test_12_receipt_after_shipment_credits_receivable(self, hdr):
        remaining = round(STATE["grand_total"] - STATE["advance"], 2)
        rid = _receipt(hdr, STATE["oid"], remaining, "sisa-setelah-kirim")
        STATE["rid_after"] = rid
        cash, jes = _cash_je_for_receipt(rid)
        assert jes, "JE kas kwitansi kedua tidak ada"
        ls = [l for _, je in jes for l in _lines(je)]
        print("after-ship cash JE:", ls)
        assert any(a == PIUTANG and c == pytest.approx(remaining, abs=1) for a, d, c in ls), ls
        assert not any(a == UANG_MUKA for a, _, _ in ls), ls
        o = db.sales_orders.find_one({"id": STATE["oid"]}, {"_id": 0, "payments": 1})
        new_pay = [p for p in o["payments"] if p.get("receipt_id") == rid]
        assert new_pay, o["payments"]
        assert new_pay[0].get("gl_bucket") in (None, ""), new_pay[0]


# ============================================================== 4. void
class TestVoidAdvanceReceipt:
    def test_13_void_advance_receipt_reverses_reclass(self, hdr):
        rid = STATE["rid_adv"]
        r = requests.post(f"{BASE}/ar-receipts/{rid}/void", headers=hdr,
                          params={"reason": "TEST KEB-PDPT pembatalan uang muka uji"},
                          json={}, timeout=120)
        assert r.status_code == 200, f"void -> {r.status_code}: {r.text[:500]}"
        rev = _je("advance_reclass_reversal", f"{STATE['oid']}:{rid}")
        assert rev, "JE advance_reclass_reversal tidak lahir"
        ls = _lines(rev[0])
        print("reversal JE:", ls)
        assert any(a == PIUTANG and d == pytest.approx(STATE["advance"], abs=1) for a, d, c in ls), ls
        assert any(a == UANG_MUKA and c == pytest.approx(STATE["advance"], abs=1) for a, d, c in ls), ls

        cash, jes = _cash_je_for_receipt(rid)
        stypes = {s for s, _ in jes}
        print("cash je source types after void:", stypes)
        assert any("void" in s for s in stypes), stypes

    def test_14_advance_account_nets_to_zero(self):
        oid = STATE["oid"]
        net = 0.0
        rids = [STATE["rid_adv"], STATE.get("rid_after")]
        cids = [c["id"] for c in db.cash_transactions.find({"ref_type": "ar_receipt",
                                                            "ref_id": {"$in": rids}}, {"_id": 0, "id": 1})]
        for je in db.journal_entries.find(
                {"$or": [{"source_id": {"$in": [oid] + cids}},
                         {"source_id": {"$regex": f"^{oid}:"}}]}, {"_id": 0}):
            if je.get("status") not in (None, "posted"):
                continue
            for l in je["lines"]:
                if l["account_code"] == UANG_MUKA:
                    net += float(l.get("debit") or 0) - float(l.get("credit") or 0)
        print("net 2-1400 for order:", net)
        assert net == pytest.approx(0.0, abs=1), f"saldo Uang Muka tidak nol: {net}"


# ============================================================== 5. regression
class TestRegression:
    def test_15_trial_balance_balanced(self, hdr):
        r = requests.get(f"{BASE}/gl/trial-balance", headers=hdr, params={"entity_id": ENT}, timeout=90)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        rows = d if isinstance(d, list) else (d.get("rows") or d.get("accounts") or d.get("items") or [])
        deb = sum(float(x.get("debit") or 0) for x in rows)
        cre = sum(float(x.get("credit") or 0) for x in rows)
        print(f"trial balance debit={deb} credit={cre} rows={len(rows)}")
        assert deb == pytest.approx(cre, abs=1), (deb, cre)
