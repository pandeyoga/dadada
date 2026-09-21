"""Sesi #090 / iterasi 299 — PRO-RATA per surat jalan + Laporan Uang Muka Pelanggan.

Alur (HTTP publik, X-Entity-Id: ent_ksc):
  A. SO baru (20 yard) → verify → confirm → kwitansi uang muka 50% (Cr 2-1400)
  B. pick penuh → dispatch PARSIAL 8 yard → JE shipment_revenue/shipment_cogs pro-rata,
     advance_reclass = min(uang muka, AR 40%), journey pct ≈ 40
  C. dispatch sisa (penutup) → Σ = grand total TEPAT, reklas penuh, pct = 100, idempotent
  D. void kwitansi uang muka → advance_reclass_reversal; netto 2-1400 = 0
  E. SO kedua + uang muka TANPA dispatch → GET /api/ar/advance-report (admin & finance),
     ?q= menyaring, sales@ → 403, pesanan shipped penuh tidak muncul
  F. trial balance seimbang; pesanan legacy ber-JE sales_order tidak dapat shipment_revenue

Jalankan: cd /app && python -m pytest backend/tests/test_iter299_prorata_advance_report.py -q -n0 -s
"""
import os

import pytest
import requests
from dotenv import dotenv_values
from pymongo import MongoClient

fe = dotenv_values("/app/frontend/.env")
BASE = (os.environ.get("REACT_APP_BACKEND_URL") or fe.get("REACT_APP_BACKEND_URL")).rstrip("/") + "/api"
be = dotenv_values("/app/backend/.env")
db = MongoClient(be.get("MONGO_URL"))[be.get("DB_NAME")]

ENT = "ent_ksc"
KAS = "1-1100"
PIUTANG = "1-1200"
PPN_OUT = "2-1200"
UANG_MUKA = "2-1400"
PENDAPATAN = "4-1000"
HPP = "5-1000"
CUST = "cust_butik_bali"
ADDR = "addr_002"
PRODUCT = "prod_endek_bali"
TAG = "TEST PRORATA 299"
QTY = 20.0
PART = 8.0

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


@pytest.fixture(scope="module")
def sales_hdr():
    return _hdr("sales@kainnusantara.id")


def _je(source_type, order_id):
    return list(db.journal_entries.find(
        {"source_type": source_type, "status": {"$ne": "void"},
         "$or": [{"source_id": order_id}, {"ref.order_id": order_id},
                 {"source_id": {"$regex": f"^{order_id}:"}}]},
        {"_id": 0}).sort("created_at", 1))


def _sum(jes, account, side):
    return round(sum(float(l.get(side) or 0) for je in jes for l in je["lines"]
                     if l["account_code"] == account), 2)


def _lines(je):
    return [(l["account_code"], round(float(l.get("debit") or 0), 2),
             round(float(l.get("credit") or 0), 2)) for l in je["lines"]]


def _create_order(hdr, qty=QTY):
    payload = {"customer_id": CUST, "shipping_address_id": ADDR, "entity_id": ENT,
               "sales_name": "Ayu Permatasari",
               "items": [{"product_id": PRODUCT, "quantity": qty, "unit": "yard",
                          "base_quantity": qty}]}
    r = requests.post(f"{BASE}/sales-orders", headers=hdr, json=payload, timeout=120)
    assert r.status_code in (200, 201), f"create SO -> {r.status_code}: {r.text[:600]}"
    o = r.json()
    oid = o.get("id") or o.get("order", {}).get("id")
    assert oid, o
    db.sales_orders.update_one({"id": oid}, {"$set": {"notes": TAG, "_test_iter299": True}})
    for path in (f"/sales-orders/{oid}/verify", f"/sales-orders/{oid}/confirm"):
        rr = requests.post(f"{BASE}{path}", headers=hdr, json={}, timeout=120)
        assert rr.status_code in (200, 201), f"{path} -> {rr.status_code}: {rr.text[:400]}"
    fresh = db.sales_orders.find_one({"id": oid}, {"_id": 0})
    print(f"SO {fresh['number']} id={oid} grand={fresh.get('grand_total')} ppn={fresh.get('ppn_amount')}")
    return fresh


def _receipt(hdr, oid, amount, ref=""):
    body = {"customer_id": CUST, "amount": round(amount, 2), "method": "transfer",
            "entity_id": ENT, "notes": f"{TAG} {ref}",
            "allocations": [{"order_id": oid, "amount": round(amount, 2)}]}
    r = requests.post(f"{BASE}/ar-receipts", headers=hdr, json=body, timeout=120)
    assert r.status_code in (200, 201), f"ar-receipt -> {r.status_code}: {r.text[:600]}"
    rc = r.json()
    rid = rc.get("id") or rc.get("receipt", {}).get("id")
    assert rid, rc
    db.ar_receipts.update_one({"id": rid}, {"$set": {"_test_iter299": True}})
    print(f"receipt {rid} number={rc.get('number') or rc.get('receipt', {}).get('number')} amount={amount}")
    return rid


def _pick_full(hdr, oid):
    r = requests.post(f"{BASE}/wms/tasks/outbound-from-order/{oid}", headers=hdr, json={}, timeout=120)
    assert r.status_code in (200, 201), f"outbound-from-order -> {r.status_code}: {r.text[:400]}"
    tasks = list(db.wms_tasks.find({"order_id": oid, "flow_type": "outbound"},
                                   {"_id": 0, "id": 1, "quantity": 1}))
    assert tasks, "tidak ada tugas outbound"
    for t in tasks:
        rr = requests.post(f"{BASE}/outbound/tasks/{t['id']}/scan-pick", headers=hdr,
                           params={"actual_qty": t.get("quantity")}, json={}, timeout=120)
        assert rr.status_code == 200, f"scan-pick -> {rr.status_code}: {rr.text[:400]}"
    return tasks


@pytest.fixture(scope="module", autouse=True)
def cleanup(hdr):
    yield
    oids = [d["id"] for d in db.sales_orders.find({"_test_iter299": True}, {"_id": 0, "id": 1})]
    rids = [d["id"] for d in db.ar_receipts.find({"_test_iter299": True}, {"_id": 0, "id": 1})]
    cids = [d["id"] for d in db.cash_transactions.find({"ref_type": "ar_receipt",
                                                        "ref_id": {"$in": rids}}, {"_id": 0, "id": 1})]
    shids = [d["id"] for d in db.shipments.find({"order_id": {"$in": oids}}, {"_id": 0, "id": 1})]
    db.journal_entries.delete_many({"$or": [{"source_id": {"$in": oids + rids + cids + shids}},
                                            {"ref.order_id": {"$in": oids}}]
                                    + [{"source_id": {"$regex": f"^{o}:"}} for o in oids]})
    db.sales_orders.delete_many({"_test_iter299": True})
    db.ar_receipts.delete_many({"_test_iter299": True})
    db.cash_transactions.delete_many({"id": {"$in": cids}})
    db.wms_tasks.delete_many({"order_id": {"$in": oids}})
    db.shipments.delete_many({"order_id": {"$in": oids}})
    print("cleanup orders:", oids, "receipts:", rids, "shipments:", shids)
    # Pulangkan roll yang masih terikat ke SO uji (stok demo tidak terkuras).
    import subprocess, sys as _sys
    subprocess.run([_sys.executable, "/app/backend/tests/iter299_restore_orphan_rolls.py"],
                   check=False, capture_output=True, timeout=120)


# ==================================================== A. uang muka sebelum kirim
class TestPartialDispatchProrata:
    def test_01_order_and_advance(self, hdr):
        o = _create_order(hdr)
        STATE["oid"] = o["id"]
        STATE["number"] = o["number"]
        STATE["grand"] = round(float(o["grand_total"]), 2)
        STATE["ppn"] = round(float(o.get("ppn_amount") or o.get("tax") or 0), 2)
        STATE["advance"] = round(STATE["grand"] * 0.5, 2)
        STATE["rid_adv"] = _receipt(hdr, o["id"], STATE["advance"], "uang-muka-50")
        assert _je("sales_order", o["id"]) == []
        assert _je("shipment_revenue", o["id"]) == []

    def test_02_partial_dispatch(self, hdr):
        oid = STATE["oid"]
        tasks = _pick_full(hdr, oid)
        STATE["task_id"] = tasks[0]["id"]
        r = requests.post(f"{BASE}/outbound/tasks/{tasks[0]['id']}/dispatch", headers=hdr,
                          params={"ship_qty": PART}, json={}, timeout=120)
        assert r.status_code == 200, f"dispatch parsial -> {r.status_code}: {r.text[:400]}"
        o = db.sales_orders.find_one({"id": oid}, {"_id": 0, "status": 1})
        print("status setelah dispatch parsial:", o["status"])
        assert o["status"] == "partially_shipped", o

    def test_03_shipment_revenue_prorata(self):
        oid = STATE["oid"]
        share = PART / QTY
        rev_je = _je("shipment_revenue", oid)
        assert len(rev_je) == 1, [j["source_id"] for j in rev_je]
        print("shipment_revenue lines:", _lines(rev_je[0]), "ref:", rev_je[0].get("ref"))
        assert rev_je[0]["ref"]["order_id"] == oid
        assert _sum(rev_je, PIUTANG, "debit") == pytest.approx(STATE["grand"] * share, abs=1)
        assert _sum(rev_je, PENDAPATAN, "credit") == pytest.approx(
            (STATE["grand"] - STATE["ppn"]) * share, abs=1)
        assert _sum(rev_je, PPN_OUT, "credit") == pytest.approx(STATE["ppn"] * share, abs=1)
        assert _je("sales_order", oid) == [], "JE per pesanan tidak boleh terbit"
        assert _je("sales_cogs", oid) == []

    def test_04_shipment_cogs(self):
        cj = _je("shipment_cogs", STATE["oid"])
        assert len(cj) == 1, [j["source_id"] for j in cj]
        hpp = _sum(cj, HPP, "debit")
        STATE["cogs1"] = hpp
        print("HPP parsial:", hpp, "→ unit cost", round(hpp / PART, 2))
        assert hpp > 0
        assert _sum(cj, "1-1300", "credit") == pytest.approx(hpp, abs=0.01)

    def test_05_advance_reclass_partial(self):
        rj = _je("advance_reclass", STATE["oid"])
        assert len(rj) == 1, [j["source_id"] for j in rj]
        assert rj[0]["source_id"] == STATE["oid"], rj[0]["source_id"]
        ar40 = round(STATE["grand"] * PART / QTY, 2)
        expected = min(STATE["advance"], ar40)
        got = _sum(rj, UANG_MUKA, "debit")
        print("advance_reclass:", got, "expected min(uang muka, AR)", expected)
        assert got == pytest.approx(expected, abs=1)
        assert _sum(rj, PIUTANG, "credit") == pytest.approx(got, abs=0.01)

    def test_06_journey_pct(self, hdr):
        r = requests.get(f"{BASE}/sales-orders/{STATE['oid']}/journey", headers=hdr, timeout=60)
        assert r.status_code == 200, r.text[:300]
        j = r.json()
        print("journey:", {k: j.get(k) for k in ("revenue_recognized", "revenue_recognized_total",
                                                 "revenue_recognized_pct", "advance_unrecognized")})
        assert float(j["revenue_recognized_pct"]) == pytest.approx(40.0, abs=1)
        reclassed = _sum(_je("advance_reclass", STATE["oid"]), UANG_MUKA, "debit")
        assert float(j["advance_unrecognized"]) == pytest.approx(STATE["advance"] - reclassed, abs=1)


# ==================================================== C. surat jalan penutup
class TestClosingShipment:
    def test_07_dispatch_remainder(self, hdr):
        r = requests.post(f"{BASE}/outbound/tasks/{STATE['task_id']}/dispatch", headers=hdr,
                          json={}, timeout=120)
        assert r.status_code == 200, f"dispatch sisa -> {r.status_code}: {r.text[:400]}"
        o = db.sales_orders.find_one({"id": STATE["oid"]}, {"_id": 0, "status": 1})
        print("status setelah penutup:", o["status"])
        assert o["status"] in ("shipped", "done", "delivered"), o

    def test_08_totals_exact(self):
        oid = STATE["oid"]
        rev_je = _je("shipment_revenue", oid)
        assert len(rev_je) == 2, [(j["source_id"], _lines(j)) for j in rev_je]
        print("Σ AR", _sum(rev_je, PIUTANG, "debit"), "grand", STATE["grand"])
        assert _sum(rev_je, PENDAPATAN, "credit") == pytest.approx(
            STATE["grand"] - STATE["ppn"], abs=0.02)
        assert _sum(rev_je, PIUTANG, "debit") == pytest.approx(STATE["grand"], abs=0.02)
        assert _sum(rev_je, PPN_OUT, "credit") == pytest.approx(STATE["ppn"], abs=0.02)

    def test_09_cogs_proportional(self):
        cj = _je("shipment_cogs", STATE["oid"])
        assert len(cj) == 2, [j["source_id"] for j in cj]
        total = _sum(cj, HPP, "debit")
        unit1 = STATE["cogs1"] / PART
        unit2 = (total - STATE["cogs1"]) / (QTY - PART)
        print("HPP total", total, "unit1", round(unit1, 2), "unit2", round(unit2, 2))
        assert unit1 == pytest.approx(unit2, rel=0.02)

    def test_10_advance_reclass_full(self):
        rj = _je("advance_reclass", STATE["oid"])
        assert len(rj) == 2, [j["source_id"] for j in rj]
        assert rj[1]["source_id"] == f"{STATE['oid']}:rc2", rj[1]["source_id"]
        total = _sum(rj, UANG_MUKA, "debit")
        print("Σ reklas", total, "uang muka", STATE["advance"])
        assert total == pytest.approx(STATE["advance"], abs=1)

    def test_11_journey_full_and_idempotent(self, hdr):
        oid = STATE["oid"]
        for i in range(2):
            s = requests.post(f"{BASE}/gl/sync", headers=hdr, json={}, timeout=180)
            assert s.status_code in (200, 201), f"gl/sync -> {s.status_code}: {s.text[:300]}"
            r = requests.get(f"{BASE}/sales-orders/{oid}/journey", headers=hdr, timeout=60)
            assert r.status_code == 200, r.text[:300]
            j = r.json()
            print(f"pass {i}: pct={j.get('revenue_recognized_pct')} adv={j.get('advance_unrecognized')}")
            assert float(j["revenue_recognized_pct"]) == pytest.approx(100.0, abs=0.5), j
            assert float(j["advance_unrecognized"]) == pytest.approx(0, abs=1), j
        # tidak menggandakan
        assert len(_je("shipment_revenue", oid)) == 2
        assert len(_je("shipment_cogs", oid)) == 2
        assert len(_je("advance_reclass", oid)) == 2
        assert _sum(_je("shipment_revenue", oid), PENDAPATAN, "credit") == pytest.approx(
            STATE["grand"] - STATE["ppn"], abs=0.02)

    def test_12_legacy_order_untouched(self, hdr):
        legacy = db.journal_entries.find_one({"source_type": "sales_order", "status": {"$ne": "void"}},
                                             {"_id": 0, "source_id": 1})
        if not legacy:
            pytest.skip("tidak ada pesanan legacy ber-JE sales_order")
        oid = legacy["source_id"]
        extra = list(db.journal_entries.find({"source_type": "shipment_revenue",
                                              "ref.order_id": oid}, {"_id": 0, "id": 1}))
        print("legacy order", oid, "shipment_revenue extra:", extra)
        assert extra == [], f"pesanan legacy {oid} mendapat JE shipment_revenue"


# ==================================================== D. void kwitansi uang muka
class TestVoidAdvance:
    def test_13_void_receipt(self, hdr):
        oid, rid = STATE["oid"], STATE["rid_adv"]
        r = requests.post(f"{BASE}/ar-receipts/{rid}/void", headers=hdr,
                          json={"reason": "uji pembatalan iterasi 299"}, timeout=120)
        assert r.status_code in (200, 201), f"void -> {r.status_code}: {r.text[:400]}"
        rev = _je("advance_reclass_reversal", oid)
        assert rev, "tidak ada JE advance_reclass_reversal"
        amt = _sum(rev, UANG_MUKA, "credit")
        print("reversal:", _lines(rev[0]))
        assert amt == pytest.approx(STATE["advance"], abs=1)

    def test_14_advance_account_net_zero(self):
        oid = STATE["oid"]
        jes = []
        for st in ("advance_reclass", "advance_reclass_reversal"):
            jes += _je(st, oid)
        rids = [STATE["rid_adv"]]
        cids = [c["id"] for c in db.cash_transactions.find({"ref_type": "ar_receipt",
                                                            "ref_id": {"$in": rids}}, {"_id": 0, "id": 1})]
        for cid in cids:
            jes += list(db.journal_entries.find({"source_id": cid, "status": {"$ne": "void"}}, {"_id": 0}))
        net = round(_sum(jes, UANG_MUKA, "credit") - _sum(jes, UANG_MUKA, "debit"), 2)
        print("netto 2-1400:", net)
        assert net == pytest.approx(0, abs=1)


# ==================================================== E. laporan uang muka
class TestAdvanceReport:
    def test_15_second_order_with_advance(self, hdr):
        o = _create_order(hdr)
        STATE["oid2"] = o["id"]
        STATE["number2"] = o["number"]
        STATE["grand2"] = round(float(o["grand_total"]), 2)
        STATE["advance2"] = round(STATE["grand2"] * 0.4, 2)
        STATE["rid_adv2"] = _receipt(hdr, o["id"], STATE["advance2"], "uang-muka-so2")
        r = requests.get(f"{BASE}/sales-orders/{o['id']}", headers=hdr, timeout=60)
        assert r.status_code == 200
        num = (r.json().get("payments") or [{}])[0].get("receipt_number")
        STATE["rc_num2"] = num
        print("receipt number so2:", num)

    @pytest.mark.parametrize("who", ["admin@kainnusantara.id", "finance@kainnusantara.id"])
    def test_16_report_contents(self, who):
        h = _hdr(who)
        r = requests.get(f"{BASE}/ar/advance-report", headers=h,
                         params={"entity_id": ENT}, timeout=90)
        assert r.status_code == 200, f"{who} -> {r.status_code}: {r.text[:400]}"
        d = r.json()
        t = d["totals"]
        print(who, "totals:", {k: t[k] for k in ("advance_orders", "deposit_balance", "liability",
                                                 "customers", "orders")}, "buckets:", t["buckets"])
        assert set(t["buckets"]) == {"0_30", "31_60", "61_90", "90_plus"}
        assert t["liability"] == pytest.approx(t["advance_orders"] + t["deposit_balance"], abs=0.02)
        assert t["advance_orders"] >= STATE["advance2"] - 1
        row = next((c for c in d["rows"] if c["customer_id"] == CUST), None)
        assert row, [c["customer_id"] for c in d["rows"]]
        assert row["customer_name"]
        o = next((x for x in row["orders"] if x["order_id"] == STATE["oid2"]), None)
        assert o, [x["order_number"] for x in row["orders"]]
        print("order row:", o)
        assert o["advance_unrecognized"] == pytest.approx(STATE["advance2"], abs=1)
        assert o["bucket"] == "0_30" and o["age_days"] >= 0
        assert float(o["revenue_recognized_pct"]) == pytest.approx(0, abs=0.5)
        assert o["receipts"] and any(rc.get("receipt_number") for rc in o["receipts"]), o["receipts"]
        # pesanan yang sudah dikirim penuh & reklas penuh tidak muncul
        assert not any(x["order_id"] == STATE["oid"] for x in row["orders"]), \
            "pesanan shipped penuh masih muncul di laporan uang muka"
        assert "_id" not in d and "_id" not in row and "_id" not in o

    def test_17_search_filter(self, hdr):
        r = requests.get(f"{BASE}/ar/advance-report", headers=hdr,
                         params={"entity_id": ENT, "q": STATE["number2"]}, timeout=90)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert d["rows"], "pencarian nomor pesanan tidak mengembalikan baris"
        assert any(o["order_id"] == STATE["oid2"] for c in d["rows"] for o in c["orders"])
        r2 = requests.get(f"{BASE}/ar/advance-report", headers=hdr,
                          params={"entity_id": ENT, "q": "ZZZ-TIDAK-ADA"}, timeout=90)
        assert r2.status_code == 200
        print("q kosong → rows", len(r2.json()["rows"]), "totals", r2.json()["totals"])
        assert r2.json()["rows"] == []

    def test_18_sales_role_forbidden(self, sales_hdr):
        r = requests.get(f"{BASE}/ar/advance-report", headers=sales_hdr,
                         params={"entity_id": ENT}, timeout=60)
        print("sales@ ->", r.status_code)
        # CATATAN (temuan iterasi 299): router memberi izin `ar_receipt.view`, dan peran
        # `sales` MEMANG punya izin itu (permissions_config.py baris 131) → 200, bukan 403.
        assert r.status_code == 403, (
            f"spesifikasi menuntut 403 untuk sales@, dapat {r.status_code} — "
            f"router GET /api/ar/advance-report menerima ar_receipt.view yang dimiliki peran sales: "
            f"{r.text[:200]}")


# ==================================================== F. neraca percobaan
class TestTrialBalance:
    def test_19_trial_balance_balanced(self, hdr):
        r = requests.get(f"{BASE}/gl/trial-balance", headers=hdr,
                         params={"entity_id": ENT}, timeout=120)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        td = float(d.get("total_debit") or d.get("totals", {}).get("debit") or 0)
        tc = float(d.get("total_credit") or d.get("totals", {}).get("credit") or 0)
        print("trial balance:", td, tc)
        assert td == pytest.approx(tc, abs=1), d.get("totals") or (td, tc)

    def test_20_finance_desk_partial_advance(self, hdr, fin_hdr):
        """Meja Finance: antrean uang muka memakai advance_unrecognized (bukan paid_total)."""
        r = requests.get(f"{BASE}/finance/desk", headers=fin_hdr, params={"entity_id": ENT}, timeout=120)
        assert r.status_code == 200, r.text[:300]
        q = next((x for x in r.json().get("queues") or [] if x.get("id") == "uang_muka_belum_kirim"), None)
        assert q, [x.get("id") for x in r.json().get("queues") or []]
        rows = q.get("rows") or q.get("items") or []
        mine = next((x for x in rows if x.get("ref_id") == STATE["oid2"] or
                     x.get("order_id") == STATE["oid2"] or x.get("id") == STATE["oid2"]), None)
        print("queue row:", mine)
        assert mine, [(x.get("title"), x.get("value")) for x in rows]
        assert float(mine.get("value") or 0) == pytest.approx(STATE["advance2"], abs=1)
        assert "kewajiban" in str(mine.get("badge") or "").lower(), mine
