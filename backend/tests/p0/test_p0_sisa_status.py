"""Regresi H-B (1/2) — sisa mesin status: pasangan aksi pemutus yang belum dijaga (pola P1/P7, audit 11 §9 "belum dikerjakan").

    API_BASE=http://localhost:8072/api DB_NAME=sipro_hb MONGO_URL=... python -m pytest backend/tests/p0/test_p0_sisa_status.py -n 0 -q --noconftest

Yang diuji (semuanya ditembakkan SERENTAK lewat API sungguhan; tiap tes membuat datanya sendiri):
  PA  `POST /deals/{id}/pricing-approval` — setuju ‖ tolak ‖ setuju ×N → satu pemenang, keputusan tidak saling menimpa
  PC  kas bon: setuju ×N, setuju ‖ tolak, batal ×N, cairkan ‖ tolak → status akhir konsisten dengan jurnalnya
  SC  termin subkon: opname ×N, tolak ×N, tolak ‖ setuju → tidak ada termin "disetujui" yang pekerjaannya sudah dilepas
  QT  penawaran: putusan diskon ×N, kirim ×N (WA sekali), konversi ×N (satu reservasi), konversi ‖ kirim
  AM  amandemen all-in: ajukan ×N (satu pending), putus ×N (riwayat biaya satu entri)
  PO  `to-po` ×N → tepat satu PO per kekurangan (nomor PO tidak hangus)
  KB  kas/bank: set-default ×N → tepat satu default; nonaktifkan default ‖ jadikan default
  FA  aset tetap: penyusutan ×N satu periode, lepas aset ×N
  BF  booking fee: batal ‖ bayar (tidak menimpa tagihan yang baru dibayar)
  PD  giro: kliring ‖ tolak ‖ batal → satu keputusan
  LF  denda: tagih ×N → satu item denda
"""
import os
import uuid
from datetime import date, timedelta

import pytest

import aio
from test_p0_masuk import FINANCE, MANAGER, OWNER, SALES, World, ar, call, codes, convert, ok, pay, race

FINLEAD = "finlead@sipro.co.id"
PM = "pm@sipro.co.id"
ROUNDS = 2


def _uid(p="H"):
    return f"{p}{uuid.uuid4().hex[:6].upper()}"


def _mongo():
    from pymongo import MongoClient
    url = os.environ.get("MONGO_URL") or ("mongo" + "db://127.0.0.1:27017")
    return MongoClient(url)[os.environ.get("DB_NAME", "sipro_hb")]


@pytest.fixture(scope="module")
def world():
    return World()


@pytest.fixture(scope="module")
def mdb():
    return _mongo()


def _shown(rs):
    return [(r.status_code, r.text[:110]) for r in rs]


def _bank(opening=10_000_000, kind="bank"):
    body = {"kind": kind, "name": f"Rek HB {_uid('R')}", "bank_name": "Bank Uji HB",
            "account_no": _uid("NO"), "opening_balance": opening}
    return ok(call(FINANCE, "POST", "/cash-bank/accounts", json=body))["data"]


def _balance(acc_id):
    rows = ok(call(FINANCE, "GET", "/cash-bank/accounts"))["data"]
    return int([a for a in rows if a["id"] == acc_id][0]["balance"])


# ================================================================== PA — persetujuan potongan reservasi
def _pa_deal(world, mdb):
    d = world.new_deal(book=False)
    mdb.deals.update_one({"id": d["deal_id"]}, {"$set": {"pricing_approval": {
        "state": "pending", "requested_by": SALES, "requested_at": "2026-11-01T00:00:00+00:00"}}})
    return d["deal_id"]


def _pa(mdb, deal_id):
    return mdb.deals.find_one({"id": deal_id}, {"_id": 0, "pricing_approval": 1})["pricing_approval"]


def test_pricing_approval_setuju_tolak_serentak_satu_pemenang(world, mdb):
    for _ in range(ROUNDS):
        deal = _pa_deal(world, mdb)
        jobs = [lambda: call(MANAGER, "POST", f"/deals/{deal}/pricing-approval", json={"approve": True, "reason": "setuju uji HB"}),
                lambda: call(OWNER, "POST", f"/deals/{deal}/pricing-approval", json={"approve": False, "reason": "tolak uji HB"}),
                lambda: call(MANAGER, "POST", f"/deals/{deal}/pricing-approval", json={"approve": True, "reason": "setuju lagi HB"}),
                lambda: call(OWNER, "POST", f"/deals/{deal}/pricing-approval", json={"approve": False, "reason": "tolak lagi HB"})]
        rs = race(jobs)
        assert codes(rs).count(200) == 1, _shown(rs)
        assert set(codes(rs)) <= {200, 400, 409}, _shown(rs)
        win = [r for r in rs if r.status_code == 200][0].json()["data"]["pricing_approval"]
        pa = _pa(mdb, deal)
        assert pa["state"] == win["state"] and pa["decided_by"] == win["decided_by"], (pa, win)


# ================================================================== PC — kas bon
def _advance(amount=1_000_000, approve=False):
    r = call(PM, "POST", "/petty-cash/advances", json={"purpose": _uid("Kas bon HB "), "amount": amount, "category": "transport"})
    aid = ok(r)["data"]["id"]
    if approve:
        ok(call(FINANCE, "POST", f"/petty-cash/advances/{aid}/approve", json={}))
    return aid


def _adv(aid):
    return ok(call(FINANCE, "GET", f"/petty-cash/advances/{aid}"))["data"]


def test_kas_bon_setuju_serentak_satu_efek():
    for _ in range(ROUNDS):
        aid = _advance()
        rs = race([lambda: call(FINANCE, "POST", f"/petty-cash/advances/{aid}/approve", json={"note": "uji HB"}) for _ in range(4)])
        assert codes(rs).count(200) == 1 and set(codes(rs)) <= {200, 400, 409}, _shown(rs)
        assert _adv(aid)["status"] == "approved"


def test_kas_bon_setuju_vs_tolak_tidak_menghasilkan_status_campur():
    for _ in range(ROUNDS * 3):
        aid = _advance()
        rs = race([lambda: call(FINANCE, "POST", f"/petty-cash/advances/{aid}/approve", json={}),
                   lambda: call(FINLEAD, "POST", f"/petty-cash/advances/{aid}/reject", json={"note": "tolak uji HB"})])
        # setuju → tolak berurutan SAH (kas bon yang disetujui masih bisa ditolak); yang tidak sah: tolak lalu "disetujui",
        # atau status "approved" padahal sudah ada penolakan (dulu terjadi karena kedua aksi menulis tanpa syarat status).
        assert set(codes(rs)) <= {200, 400, 409} and 200 in codes(rs), _shown(rs)
        a = _adv(aid)
        assert not (a["status"] == "approved" and a.get("rejected_by")), (a["status"], a.get("rejected_by"))
        if codes(rs) == [200, 200]:
            assert a["status"] == "rejected", a["status"]


def test_kas_bon_batal_serentak_satu_efek():
    aid = _advance()
    rs = race([lambda: call(PM, "POST", f"/petty-cash/advances/{aid}/cancel") for _ in range(4)])
    assert codes(rs).count(200) == 1 and set(codes(rs)) <= {200, 400, 409}, _shown(rs)
    assert _adv(aid)["status"] == "cancelled"


def test_kas_bon_cairkan_vs_tolak_status_sesuai_jurnal():
    """Dulu: tolak menimpa `disbursing`, lalu pencairan menulis `disbursed` — pemohon diberi tahu 'ditolak' padahal uang sudah keluar."""
    for _ in range(ROUNDS * 2):
        acc = _bank(10_000_000)
        aid = _advance(2_000_000, approve=True)
        rs = race([lambda: call(FINANCE, "POST", f"/petty-cash/advances/{aid}/disburse",
                                json={"source": "bank", "cash_account_id": acc["id"]}),
                   lambda: call(FINLEAD, "POST", f"/petty-cash/advances/{aid}/reject", json={"note": "tolak uji HB"})])
        assert codes(rs).count(200) == 1, _shown(rs)
        a = _adv(aid)
        if a["status"] == "disbursed":
            assert not a.get("rejected_by") and _balance(acc["id"]) == 8_000_000
        else:
            assert a["status"] == "rejected" and _balance(acc["id"]) == 10_000_000


# ================================================================== SC — termin subkon
def _claim(world, pct=50):
    sub = ok(call(OWNER, "POST", "/subcon/subcontractors", json={"name": f"Subkon HB {_uid()}"}))["data"]
    spk = ok(call(OWNER, "POST", "/subcon/spk", json={
        "subcontractor_id": sub["id"], "project_id": world.project_id, "title": f"SPK HB {_uid()}",
        "contract_value": 100_000_000}))["data"]
    return ok(call(OWNER, "POST", "/subcon/claims", json={"spk_id": spk["id"], "progress_pct": pct}))["data"]["id"], spk["id"]


def _c(cid):
    return ok(call(OWNER, "GET", f"/subcon/claims/{cid}"))["data"]


def test_termin_opname_serentak_satu_pemenang(world):
    cid, _ = _claim(world)
    rs = race([lambda p=p: call(OWNER, "POST", f"/subcon/claims/{cid}/verify", json={"verified_pct": p}) for p in (50, 40, 30, 20)])
    assert codes(rs).count(200) == 1 and set(codes(rs)) <= {200, 400, 409}, _shown(rs)
    win = [r for r in rs if r.status_code == 200][0].json()["data"]
    assert _c(cid)["verified_pct"] == win["verified_pct"]


def test_termin_tolak_serentak_satu_efek(world):
    cid, _ = _claim(world)
    rs = race([lambda: call(OWNER, "POST", f"/subcon/claims/{cid}/reject", json={"note": "tolak uji HB"}) for _ in range(4)])
    assert codes(rs).count(200) == 1 and set(codes(rs)) <= {200, 400, 409}, _shown(rs)
    assert _c(cid)["status"] == "rejected"


def test_termin_tolak_vs_setuju_tidak_menyisakan_tagihan_tanpa_termin(world):
    for _ in range(ROUNDS * 2):
        cid, _spk = _claim(world)
        ok(call(OWNER, "POST", f"/subcon/claims/{cid}/verify", json={"verified_pct": 50}))
        rs = race([lambda: call(OWNER, "POST", f"/subcon/claims/{cid}/approve"),
                   lambda: call(OWNER, "POST", f"/subcon/claims/{cid}/reject", json={"note": "tolak uji HB"})])
        assert codes(rs).count(200) == 1, _shown(rs)
        c = _c(cid)
        assert (c["status"] == "approved") == bool(c.get("ap_bill_id")), (c["status"], c.get("ap_bill_id"))
        assert not (c["status"] == "approved" and c.get("rejected_by")), "disetujui sekaligus ditolak"


# ================================================================== QT — penawaran
def _quote(world, approval=False):
    """Penawaran baru (unit + lead baru). `approval=True` → promo `approval_mode=always` buatan tes sehingga
    penawaran berstatus `awaiting_approval` (diskon manual tidak diizinkan, harus lewat skema/promo)."""
    d = world.new_deal(book=False)   # ambil lead + unit baru; deal-nya dibatalkan agar unit kembali tersedia
    call(MANAGER, "POST", f"/deals/{d['deal_id']}/cancel", json={"reason": "uji HB — lepas unit", "refund_mode": "forfeit"})
    body = {"lead_id": d["lead_id"], "unit_id": d["unit_id"], "booking_fee": 0}
    if approval:
        promo = ok(call(MANAGER, "POST", "/pricing/promos", json={
            "code": _uid("PH"), "name": f"Promo HB {_uid()}", "kind": "percent", "value": 1,
            "approval_mode": "always", "applies_project_ids": [world.project_id]}))["data"]
        body.update({"promo_id": promo["id"], "discount_reason": "Pembeli pameran, dasar uji HB"})
    return ok(call(SALES, "POST", "/quotations", json=body))["data"], d


def test_penawaran_putusan_diskon_serentak_satu_pemenang(world):
    q, _ = _quote(world, approval=True)
    assert q["state"] == "awaiting_approval", q["state"]
    rs = race([lambda: call(MANAGER, "POST", f"/quotations/{q['id']}/decision", json={"approve": True, "reason": "setuju uji HB"}),
               lambda: call(OWNER, "POST", f"/quotations/{q['id']}/decision", json={"approve": False, "reason": "tolak uji HB"}),
               lambda: call(MANAGER, "POST", f"/quotations/{q['id']}/decision", json={"approve": True, "reason": "setuju lagi HB"}),
               lambda: call(OWNER, "POST", f"/quotations/{q['id']}/decision", json={"approve": False, "reason": "tolak lagi HB"})])
    assert codes(rs).count(200) == 1 and set(codes(rs)) <= {200, 400, 409}, _shown(rs)
    got = ok(call(MANAGER, "GET", f"/quotations/{q['id']}"))["data"]
    acts = [h["action"] for h in got["history"] if h["action"] in ("approve_discount", "reject_discount")]
    assert len(acts) == 1, acts


def test_penawaran_kirim_serentak_sekali(world):
    q, _ = _quote(world)
    rs = race([lambda: call(SALES, "POST", f"/quotations/{q['id']}/send", json={"channel": "whatsapp"}) for _ in range(4)])
    assert codes(rs).count(200) == 1 and set(codes(rs)) <= {200, 400, 409}, _shown(rs)
    got = ok(call(MANAGER, "GET", f"/quotations/{q['id']}"))["data"]
    assert len([h for h in got["history"] if h["action"] == "send"]) == 1, got["history"]


def test_penawaran_konversi_serentak_satu_reservasi(world, mdb):
    q, d = _quote(world)
    rs = race([lambda: call(SALES, "POST", f"/quotations/{q['id']}/convert") for _ in range(4)])
    assert codes(rs).count(200) == 1 and set(codes(rs)) <= {200, 400, 409}, _shown(rs)
    assert mdb.deals.count_documents({"unit_id": d["unit_id"], "status": {"$in": ["reserved", "booked"]}}) == 1
    got = ok(call(MANAGER, "GET", f"/quotations/{q['id']}"))["data"]
    assert got["state"] == "converted" and got.get("converted_deal_id")


def test_penawaran_konversi_vs_kirim_tidak_menimpa_status(world):
    """Dulu: kirim menulis `sent` di atas `converted` (penawaran yang sudah jadi reservasi tampil 'terkirim')."""
    for _ in range(ROUNDS * 2):
        q, _d = _quote(world)
        rs = race([lambda: call(SALES, "POST", f"/quotations/{q['id']}/convert"),
                   lambda: call(SALES, "POST", f"/quotations/{q['id']}/send", json={"channel": "whatsapp"})])
        got = ok(call(MANAGER, "GET", f"/quotations/{q['id']}"))["data"]
        if rs[0].status_code == 200:
            assert got["state"] == "converted", (got["state"], _shown(rs))


# ================================================================== AM — amandemen all-in
def _contract(world):
    return convert(world.new_deal())


def _scheme_other(cid):
    schemes = ok(call(FINANCE, "GET", "/allin-schemes"))["data"]
    cur = (ok(call(FINANCE, "GET", f"/contracts/{cid}"))["data"].get("costs") or {}).get("scheme_name")
    return [s for s in schemes if s["name"] != cur and s.get("is_active", True)][0]["id"]


def test_amandemen_ajukan_serentak_satu_pending(world, mdb):
    cid = _contract(world)
    sid = _scheme_other(cid)
    rs = race([lambda: call(FINANCE, "POST", f"/contracts/{cid}/allin-amendments",
                            json={"scheme_id": sid, "reason": "amandemen serentak uji HB"}) for _ in range(4)])
    assert codes(rs).count(200) == 1 and set(codes(rs)) <= {200, 400, 409}, _shown(rs)
    assert mdb.allin_amendments.count_documents({"contract_id": cid, "status": "pending"}) == 1


def test_amandemen_putus_serentak_riwayat_biaya_satu_entri(world, mdb):
    cid = _contract(world)
    sid = _scheme_other(cid)
    aid = ok(call(FINANCE, "POST", f"/contracts/{cid}/allin-amendments",
                  json={"scheme_id": sid, "reason": "amandemen putus uji HB"}))["data"]["id"]
    rs = race([lambda: call(FINLEAD, "POST", f"/allin-amendments/{aid}/decide", json={"approve": True, "note": "setuju HB"}),
               lambda: call(OWNER, "POST", f"/allin-amendments/{aid}/decide", json={"approve": False, "note": "tolak HB"}),
               lambda: call(FINLEAD, "POST", f"/allin-amendments/{aid}/decide", json={"approve": True, "note": "setuju lagi HB"}),
               lambda: call(OWNER, "POST", f"/allin-amendments/{aid}/decide", json={"approve": False, "note": "tolak lagi HB"})])
    assert codes(rs).count(200) == 1 and set(codes(rs)) <= {200, 400, 409}, _shown(rs)
    win = [r for r in rs if r.status_code == 200][0].json()["data"]["status"]
    am = mdb.allin_amendments.find_one({"id": aid})
    contract = mdb.contracts.find_one({"id": cid})
    assert am["status"] == win
    assert len(contract.get("costs_history") or []) == (1 if win == "approved" else 0)


# ================================================================== PO — permintaan → PO
def _vendor():
    return ok(call(OWNER, "POST", "/vendors", json={"name": f"Vendor HB {_uid()}", "category": "material"}))["data"]["id"]


def test_to_po_serentak_satu_po_per_kekurangan(world, mdb):
    mid = ok(call(OWNER, "POST", "/materials", json={"project_id": world.project_id, "name": f"Semen HB {_uid()}", "uom": "sak"}))["data"]["id"]
    rid = ok(call(OWNER, "POST", "/materials/requisitions", json={
        "project_id": world.project_id, "items": [{"material_id": mid, "qty": 40}], "purpose": "uji HB"}))["data"]["id"]
    ok(call(OWNER, "POST", f"/materials/requisitions/{rid}/approve"))
    vid = _vendor()
    due = (date.today() + timedelta(days=10)).isoformat()
    rs = race([lambda: call(OWNER, "POST", f"/materials/requisitions/{rid}/to-po", json={
        "vendor_id": vid, "due_date": due, "items": [{"material_id": mid, "qty": 40, "unit_price": 50_000}]}) for _ in range(4)])
    assert codes(rs).count(200) == 1 and set(codes(rs)) <= {200, 400, 409}, _shown(rs)
    assert mdb.purchase_orders.count_documents({"requisition_id": rid}) == 1
    req = mdb.material_requisitions.find_one({"id": rid})
    assert len(req.get("po_ids") or []) == 1 and float(req["items"][0]["qty_po"]) == 40.0


# ================================================================== KB — kas & bank
@pytest.fixture()
def keep_default(mdb):
    """Rekening bank default org dipulihkan sesudah tes (keadaan bersama: jurnal otomatis jatuh ke rekening default)."""
    before = mdb.bank_accounts.find_one({"org_id": "org-sipro", "kind": "bank", "is_default": True}, {"id": 1})
    yield
    if before:
        ok(call(FINANCE, "POST", f"/cash-bank/accounts/{before['id']}/set-default"))


def test_set_default_serentak_tepat_satu_default(world, mdb, keep_default):
    accs = [_bank(0) for _ in range(4)]
    rs = race([lambda a=a: call(FINANCE, "POST", f"/cash-bank/accounts/{a['id']}/set-default") for a in accs])
    assert codes(rs).count(200) == 4, _shown(rs)
    n = mdb.bank_accounts.count_documents({"org_id": "org-sipro", "kind": "bank", "is_default": True})
    assert n == 1, f"harus tepat 1 rekening bank default, ada {n}"


def test_nonaktifkan_default_vs_jadikan_default(world, mdb, keep_default):
    for _ in range(ROUNDS * 2):
        a = _bank(0)
        ok(call(FINANCE, "POST", f"/cash-bank/accounts/{a['id']}/set-default"))
        rs = race([lambda: call(FINANCE, "PUT", f"/cash-bank/accounts/{a['id']}", json={"is_active": False}),
                   lambda: call(FINANCE, "POST", f"/cash-bank/accounts/{a['id']}/set-default")])
        doc = mdb.bank_accounts.find_one({"id": a["id"]})
        assert not (doc.get("is_default") and doc.get("is_active") is False), (doc.get("is_default"), doc.get("is_active"), _shown(rs))
        base = mdb.bank_accounts.find_one({"org_id": "org-sipro", "kind": "bank", "name": "Rekening Operasional"}, {"id": 1})
        ok(call(FINANCE, "POST", f"/cash-bank/accounts/{base['id']}/set-default"))   # pulihkan default agar jalur lain tak terganggu


# ================================================================== FA — aset tetap
def _asset(cost=12_000_000, acc=None):
    body = {"name": f"Aset HB {_uid()}", "category": "komputer_it", "tax_group": "kelompok_1", "method": "garis_lurus",
            "cost": cost, "salvage_value": 0, "useful_life_months": 12,
            "acquired_date": "2026-01-15", "funding": "bank"}
    r = call(FINANCE, "POST", "/fixed-assets/assets", json=body)
    return ok(r)["data"]


def test_penyusutan_serentak_satu_jurnal_per_aset_periode(mdb):
    a = _asset()
    period = "2026-02"   # sebulan setelah perolehan (2026-01-15); idempoten per (aset, periode) untuk aset lain juga
    rs = race([lambda: call(OWNER, "POST", "/fixed-assets/depreciation/run", json={"period": period}) for _ in range(4)])
    assert 500 not in codes(rs) and set(codes(rs)) <= {200, 400, 409}, _shown(rs)
    assert mdb.asset_depreciations.count_documents({"asset_id": a["id"], "period": period}) == 1
    got = mdb.fixed_assets.find_one({"id": a["id"]})
    assert int(got["accumulated_depreciation"]) == 1_000_000, got["accumulated_depreciation"]


def test_lepas_aset_serentak_satu_efek(mdb):
    a = _asset(cost=6_000_000)
    rs = race([lambda: call(OWNER, "POST", f"/fixed-assets/assets/{a['id']}/dispose",
                            json={"proceeds": 0, "source": "bank", "note": "uji HB"}) for _ in range(4)])
    assert codes(rs).count(200) == 1 and set(codes(rs)) <= {200, 400, 409}, _shown(rs)
    got = mdb.fixed_assets.find_one({"id": a["id"]})
    assert got["status"] == "disposed" and len(got["journal_ids"]) == 2, got["journal_ids"]


# ================================================================== LF — denda keterlambatan
def _late_deal(world):
    sname = f"HB Terlambat {_uid()}"
    r = call(OWNER, "POST", "/payment-schemes", json={
        "name": sname, "kind": "cash_bertahap", "code": f"hb-late-{_uid().lower()}", "active": True,
        "terms": [{"label": "Termin lampau", "basis": "percent", "value": 100, "due_offset_days": -90}]})
    world.scheme[sname] = ok(r)["data"]["id"]
    return world.new_deal(scheme=sname)["deal_id"]


def test_denda_tagih_serentak_satu_item_dan_satu_respons_membuat(world):
    d = _late_deal(world)
    rs = race([lambda: call(OWNER, "POST", f"/finance/late-fees/{d}/apply", json={}) for _ in range(4)])
    assert set(codes(rs)) <= {200, 400, 409}, _shown(rs)
    made = [r for r in rs if r.status_code == 200 and r.json().get("created")]
    assert len(made) == 1, f"hanya satu permintaan yang boleh menagihkan denda, ada {len(made)}: {_shown(rs)}"
    inv = ar(d)["data"]
    assert len([i for i in inv["items"] if i.get("is_penalty")]) == 1


def test_denda_tagih_vs_bayar_tidak_menghilangkan_pembayaran(world):
    """Dulu `_recalc` menulis ulang `items` dari salinan basi: pembayaran yang masuk di sela-sela hilang dari tagihan."""
    for _ in range(ROUNDS * 2):
        d = _late_deal(world)
        base = int(ar(d)["data"]["outstanding"])
        rs = race([lambda: call(OWNER, "POST", f"/finance/late-fees/{d}/apply", json={}),
                   lambda: pay(d, 10_000_000)])
        assert rs[1].status_code == 200, _shown(rs)
        data = ar(d)
        paid_items = sum(int(i.get("paid_amount") or 0) for i in data["data"]["items"])
        receipts = sum(int(r["amount"]) for r in data["receipts"] if r.get("status") != "void")
        assert paid_items == receipts == 10_000_000, (paid_items, receipts, base)


# ================================================================== BF — batal tagihan booking fee
def test_booking_fee_batal_tidak_menimpa_tagihan_yang_baru_dibayar(world, mdb):
    """Pembayaran masuk di sela-sela baca-tagihan dan tulis-batal (disimulasikan) tidak boleh ditimpa `cancelled`."""
    import booking_fee as bf
    d = world.new_deal(book=False, booking_fee=5_000_000)
    org = "org-sipro"
    orig = bf.get_invoice
    calls = {"n": 0}

    async def stale_after_payment(o, deal_id):
        inv = await orig(o, deal_id)
        calls["n"] += 1
        if calls["n"] == 1:
            await bf._pay_unlocked(o, deal_id, amount=5_000_000, method="transfer", note="uji HB", actor=FINANCE)
        return inv       # salinan BASI: masih "unpaid"

    bf.get_invoice = stale_after_payment
    try:
        aio.run(bf.cancel(org, d["deal_id"], "uji@x"))
    finally:
        bf.get_invoice = orig
    inv = mdb.booking_fee_invoices.find_one({"deal_id": d["deal_id"]})
    assert inv["status"] == "paid" and int(inv["paid"]) == 5_000_000, (inv["status"], inv["paid"])
