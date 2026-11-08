"""Regresi H-D — EKUIVALENSI profil posting v0 ≡ kode lama (bagian 2 dari test_p0_posting_profile.py).

    API_BASE=http://localhost:8074/api DB_NAME=<db> MONGO_URL=<url> POSTING_SHADOW=1 (pada SERVER) \
      python -m pytest backend/tests/p0/test_p0_posting_profile_2.py -n 0 -q --noconftest

Dua lapis bukti:
  C. DALAM-PROSES: handler event `gl_engine._gl_*` yang NYATA dijalankan pada org uji sementara (bukan mock), dengan resolver
     bayangan dinyalakan; jurnal terbit dibandingkan dengan profil v0 dari masukan yang ditulis tes sendiri
     (termasuk cabang tepi: tipe PO × retensi × potongan × akrual, split piutang/denda, WIP kurang, kelebihan bayar).
  D. SKENARIO API: alur nyata (deal → bayar → void → denda → titipan → BAST → AP → komisi → fee → pajak → kas bon → aset →
     pembatalan). Tiap jurnal dibandingkan dengan `dry-run` yang masukannya diambil dari DOKUMEN sumber (bukan dari
     jurnal), plus endpoint `verify`. Bila server berjalan dengan POSTING_SHADOW=1, `posting_shadow_diffs` HARUS kosong.
"""
import os
import sys
import time
import uuid

import pytest

import p0_common as pc
from test_p0_masuk import FINANCE, OWNER, World, ar, call, ok, pay
from test_p0_masuk import upload_proof

BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, BACKEND)
pytest.importorskip("motor")

import aio  # noqa: E402

FINLEAD = "finlead@sipro.co.id"
CASH_HEADERS = ("1-1100", "1-1200")


# ============================================================================ C. dalam-proses: handler nyata
class FakeOrg:
    """Org sementara berisi CoA penuh (dibuat `ensure_coa`) + rekening bayangan; dibersihkan sesudah uji."""
    COLLS = ("journal_entries", "accounts", "bank_accounts", "posting_shadow_stats", "posting_shadow_diffs", "ap_invoices",
             "purchase_orders", "revenue_recognitions", "commissions", "cash_vouchers", "receipts", "customer_deposits",
             "deals")

    def __init__(self):
        from db import db
        self.db = db
        self.org = f"org-hd-{uuid.uuid4().hex[:8]}"

    def run(self, coro):
        return aio.run(coro)

    def ev(self, data, entity_id=None):
        return {"id": uuid.uuid4().hex, "org_id": self.org, "entity_id": entity_id or uuid.uuid4().hex, "data": data}

    def seed(self, coll, doc):
        async def _s():
            await self.db[coll].insert_one({"org_id": self.org, **doc})
        self.run(_s())

    def post_manual(self, lines):
        import gl_engine as gl
        return self.run(gl.post_journal(self.org, "saldo uji H-D", lines, source_type="manual", auto=False))

    def one(self, coll, q):
        async def _o():
            return await self.db[coll].find_one({"org_id": self.org, **q}, {"_id": 0})
        return self.run(_o())

    def journal(self, **q):
        return self.one("journal_entries", q)

    def acct_map(self):
        async def _a():
            return await self.db.accounts.find({"org_id": self.org}, {"_id": 0}).to_list(500)
        return {a["code"]: a for a in self.run(_a())}

    def counts(self, coll, q=None):
        async def _c():
            return await self.db[coll].count_documents({"org_id": self.org, **(q or {})})
        return self.run(_c())

    def stat(self, key):
        return self.one("posting_shadow_stats", {"event_key": key}) or {}

    def cleanup(self):
        async def _c():
            for c in self.COLLS:
                await self.db[c].delete_many({"org_id": self.org})
            await self.db.counters.delete_many({"_id": {"$regex": self.org}})
        self.run(_c())

    def assert_equal(self, j, key, inputs):
        """Jurnal terbit == profil v0 dari masukan tes; cap jejak ada; bayangan mencatat cek TANPA selisih."""
        import posting_profile as pp
        import posting_shadow as ps
        assert j is not None, "handler tidak menerbitkan jurnal"
        exp = pp.aggregate(pp.evaluate(key, inputs)["lines"])
        got, _env = ps.posted_view(j["lines"], self.acct_map())
        assert got == exp, f"{key}: jurnal terbit {got} != profil v0 {exp}"
        assert j["profile_event"] == key and j["profile_version"] == "v0"
        assert j["total_debit"] == j["total_credit"]
        assert self.stat(key).get("checked", 0) >= 1 and self.stat(key).get("diff", 0) == 0, self.stat(key)
        assert self.counts("posting_shadow_diffs") == 0, "bayangan mencatat selisih"


@pytest.fixture
def fo(monkeypatch):
    monkeypatch.setenv("POSTING_SHADOW", "1")
    f = FakeOrg()
    try:
        yield f
    finally:
        f.cleanup()


def _h(name):
    import gl_engine
    return getattr(gl_engine, name)


@pytest.mark.parametrize("amount,split,inp", [
    (100, None, {"amount": 100}),
    (100, {"liability": 60, "ar": 30, "penalty": 10}, {"amount": 100, "split_ar": 30, "split_penalty": 10}),
    (100, {"liability": 0, "ar": 100, "penalty": 0}, {"amount": 100, "split_ar": 100}),
    (100, {"liability": 50, "ar": 0, "penalty": 0}, {"amount": 100}),     # selisih bulat jatuh ke 2-1400
    (100, {"liability": 0, "ar": 0, "penalty": 100}, {"amount": 100, "split_penalty": 100}),
])
def test_payment_received_nyata_sama_dengan_profil(fo, amount, split, inp):
    rid = uuid.uuid4().hex
    fo.seed("receipts", {"id": rid})
    data = {"amount": amount, "receipt_id": rid, "cash_account_id": None, "split": split}
    fo.run(_h("_gl_payment_received")(fo.ev(data)))
    fo.assert_equal(fo.journal(source_type="receipt"), "sales.receipt", inp)


def test_titipan_diterima_dipakai_dikembalikan_nyata_sama_dengan_profil(fo):
    dep = uuid.uuid4().hex
    fo.seed("customer_deposits", {"id": dep})
    fo.run(_h("_gl_deposit_received")(fo.ev({"amount": 40}, dep)))
    fo.assert_equal(fo.journal(source_type="deposit", memo={"$regex": "diterima"}), "sales.deposit_in", {"amount": 40})
    deal = uuid.uuid4().hex
    fo.seed("deals", {"id": deal})
    fo.run(_h("_gl_deposit_applied")(fo.ev({"amount": 25, "deal_id": deal,
                                            "split": {"liability": 20, "ar": 5, "penalty": 0}}, dep)))
    fo.assert_equal(fo.journal(source_type="deposit", memo={"$regex": "dipakai"}), "sales.deposit_apply",
                    {"amount": 25, "split_ar": 5})
    fo.run(_h("_gl_deposit_refunded")(fo.ev({"amount": 15}, dep)))
    fo.assert_equal(fo.journal(source_type="deposit", memo={"$regex": "dikembalikan"}), "sales.deposit_refund",
                    {"amount": 15})


AP_CASES = [   # (po_type di dokumen PO atau None=tanpa PO, saldo akrual 2-1700, retensi, potongan)
    ("material", 0, 50, {}),
    ("general", 0, 0, {"material": 30}),
    ("subcon", 300, 40, {"advance": 100, "penalty": 20}),
    ("subcon", 300, 0, {}),            # klaim (1000) > akrual (300): akrual dilunasi dulu
    ("subcon", 5000, 0, {}),           # akrual > klaim: seluruh klaim melunasi akrual
    (None, 200, 10, {"other": 15, "foo": 5}),           # tanpa PO + jenis potongan tak dikenal → 4-1200
    ("lainnya", 0, 0, {"advance": 10, "material": 10, "penalty": 10, "other": 10}),   # tipe PO tak dikenal → WIP
]


@pytest.mark.parametrize("po_type,accrual,ret,ded", AP_CASES)
def test_ap_approved_nyata_sama_dengan_profil_semua_cabang(fo, po_type, accrual, ret, ded):
    claimed = 1000
    if accrual:
        fo.post_manual([{"account_code": "5-1100", "debit": accrual, "credit": 0},
                        {"account_code": "2-1700", "debit": 0, "credit": accrual}])
    bid, poid = uuid.uuid4().hex, uuid.uuid4().hex
    total_ded = sum(ded.values())
    bill = {"id": bid, "vendor": "Vendor Uji H-D", "claimed": claimed, "retention_held": ret,
            "net": claimed - ret - total_ded,
            "deductions": [{"kind": k, "amount": v, "reason": "uji"} for k, v in ded.items()]}
    if po_type:
        bill["po_id"] = poid
        fo.seed("purchase_orders", {"id": poid, "po_type": po_type})
    fo.seed("ap_invoices", bill)
    fo.run(_h("_gl_ap_approved")(fo.ev({}, bid)))
    known = {"advance", "material", "penalty"}
    fo.assert_equal(fo.journal(source_type="ap_bill"), "ap.approve", {
        "claimed": claimed, "net": claimed - ret - total_ded, "retention": ret, "po_type": po_type,
        "accrual_balance": accrual, "ded_advance": ded.get("advance", 0), "ded_material": ded.get("material", 0),
        "ded_penalty": ded.get("penalty", 0), "ded_other": sum(v for k, v in ded.items() if k not in known)})


@pytest.mark.parametrize("withheld", [0, 1_500])
def test_ap_paid_dan_komisi_nyata_sama_dengan_profil(fo, withheld):
    fo.run(_h("_gl_ap_paid")(fo.ev({"amount": 100_000, "withheld": withheld, "cash_account_id": None})))
    fo.assert_equal(fo.journal(source_type="ap_bill"), "ap.pay", {"amount": 100_000, "withheld": withheld})
    cid = uuid.uuid4().hex
    fo.seed("commissions", {"id": cid, "deal_id": "d-uji", "amount": 7_000, "assigned_to": "sales@x"})
    fo.run(_h("_gl_commission_approved")(fo.ev({"commission_id": cid}, "d-uji")))
    fo.assert_equal(fo.journal(source_type="commission", memo={"$regex": "Akrual"}), "commission.approve", {"amount": 7_000})
    fo.run(_h("_gl_commission_paid")(fo.ev({"amount": 7_000}, cid)))
    fo.assert_equal(fo.journal(source_type="commission", memo={"$regex": "Pembayaran"}), "commission.pay", {"amount": 7_000})


@pytest.mark.parametrize("revenue,cogs,cleared,wip", [
    (500, 350, 400, 1000),    # sebagian piutang, HPP penuh dari WIP
    (500, 350, 500, 100),     # WIP kurang → sisa HPP jadi akrual 2-1700
    (500, 350, 0, 0),         # tanpa WIP sama sekali, seluruh pendapatan jadi piutang
    (500, 0, 650, 0),         # uang diterima > pendapatan → kelebihan jadi titipan 2-1450
    (500, 350, 500, 350),     # WIP persis
])
def test_revrec_nyata_sama_dengan_profil_semua_cabang(fo, revenue, cogs, cleared, wip):
    if wip:
        fo.post_manual([{"account_code": "1-1600", "debit": wip, "credit": 0},
                        {"account_code": "2-1100", "debit": 0, "credit": wip}])
    deal = uuid.uuid4().hex
    fo.seed("revenue_recognitions", {"id": uuid.uuid4().hex, "deal_id": deal, "revenue": revenue, "cogs": cogs,
                                     "contract_liability_cleared": cleared})
    fo.run(_h("_gl_revenue_recognized")(fo.ev({}, deal)))
    fo.assert_equal(fo.journal(source_type="revrec"), "sales.revrec",
                    {"revenue": revenue, "cogs": cogs, "cleared": cleared, "wip_balance": wip})


def test_pajak_akrual_dan_setor_nyata_sama_dengan_profil(fo):
    import gl_engine as gl
    rec = {"id": uuid.uuid4().hex, "amount": 55_000, "type": "ppn", "unit_code": "U1", "created_at": "2026-11-01T00:00:00+00:00"}
    fo.run(gl.post_tax_payment(fo.org, rec))    # memastikan akrual lebih dulu, lalu setor
    fo.assert_equal(fo.journal(source_type="tax_accrual"), "tax.accrue", {"amount": 55_000})
    fo.assert_equal(fo.journal(source_type="tax_setor"), "tax.deposit", {"amount": 55_000})


def test_bayangan_mati_tidak_mencatat_apa_pun_dan_posting_tetap_jalan(fo, monkeypatch):
    monkeypatch.delenv("POSTING_SHADOW", raising=False)
    fo.run(_h("_gl_ap_paid")(fo.ev({"amount": 500, "withheld": 0})))
    j = fo.journal(source_type="ap_bill")
    assert j and j["total_debit"] == 500 and j["profile_event"] == "ap.pay"   # cap jejak tetap (tanpa kueri)
    assert fo.counts("posting_shadow_stats") == 0 and fo.counts("posting_shadow_diffs") == 0


def test_selisih_nyata_tercatat_dan_posting_tetap_utuh(fo):
    """Profil sengaja 'salah' lewat petunjuk palsu: jurnal TETAP terbit apa adanya, selisih tercatat di posting_shadow_diffs."""
    import gl_engine as gl
    j = fo.run(gl.post_journal(fo.org, "uji selisih", [
        {"account_code": "6-1100", "debit": 900, "credit": 0}, {"account_code": "2-1600", "debit": 0, "credit": 900}],
        source_type="commission", source_id="c1", source_event="ev:uji-selisih",
        profile=("commission.approve", {"amount": 1_000})))
    assert j["total_debit"] == 900 and [ln["debit"] for ln in j["lines"]] == [900, 0]   # jurnal tidak diubah
    d = fo.one("posting_shadow_diffs", {})
    assert d and d["event_key"] == "commission.approve" and d["source_event"] == "ev:uji-selisih"
    assert {(x["side"], x["key"], x["expected"], x["posted"]) for x in d["diff"]} == {
        ("D", "6-1100", 1_000, 900), ("K", "2-1600", 1_000, 900)}
    assert d["journal_id"] == j["id"] and d["created_at"] and d["mode"] == "hint"
    assert fo.stat("commission.approve")["diff"] == 1


def test_biaya_bayangan_tidak_menambah_kueri_di_luar_satu_tulis_per_jurnal(fo):
    import gl_engine as gl
    import posting_shadow as ps
    calls = []

    class Rec:
        def __init__(self, coll):
            self.coll = coll

        def __getattr__(self, m):
            async def f(*a, **k):
                calls.append((self.coll, m))
                return await getattr(real[self.coll], m)(*a, **k)
            return f

    class RecDB:
        def __getattr__(self, coll):
            return Rec(coll)
    real = {"posting_shadow_stats": fo.db.posting_shadow_stats, "posting_shadow_diffs": fo.db.posting_shadow_diffs}
    orig = ps.db
    ps.db = RecDB()
    try:
        fo.run(gl.post_journal(fo.org, "uji biaya", [
            {"account_code": "6-1100", "debit": 10, "credit": 0}, {"account_code": "2-1600", "debit": 0, "credit": 10}],
            source_type="commission", source_event="ev:uji-biaya", profile=("commission.approve", {"amount": 10})))
    finally:
        ps.db = orig
    assert calls == [("posting_shadow_stats", "update_one")], calls   # profil di kode: 0 baca; sama: 1 tulis statistik saja


def test_dimensi_jurnal_deal_dan_rekening_terisi_tanpa_mengubah_nilai(fo):
    """Fase 3 (opsional): `dimensions` ditambahkan pada jurnal BARU — deal dari source_deal_id, rekening dari sub-akun kas/bank.
    Hanya metadata: baris & total identik dengan profil v0; jurnal tanpa deal/kas tidak mendapat kunci yang tidak relevan."""
    rid, deal = uuid.uuid4().hex, uuid.uuid4().hex
    fo.seed("receipts", {"id": rid})
    fo.run(_h("_gl_payment_received")(fo.ev({"amount": 100, "receipt_id": rid, "split": None}, deal)))
    j = fo.journal(source_type="receipt")
    bank = fo.one("bank_accounts", {"kind": "bank", "is_default": True})
    assert j["dimensions"] == {"deal_id": deal, "cash_account_id": bank["id"], "cash_account_ids": [bank["id"]]}
    assert j["source_deal_id"] == deal and "project_id" not in j["dimensions"], "project/unit sengaja belum diisi"
    fo.assert_equal(j, "sales.receipt", {"amount": 100})
    fo.run(_h("_gl_commission_paid")(fo.ev({"amount": 5}, "c1")))     # kas keluar, tanpa deal
    c = fo.journal(source_type="commission")
    assert c["dimensions"] == {"cash_account_id": bank["id"], "cash_account_ids": [bank["id"]]}
    fo.post_manual([{"account_code": "6-1300", "debit": 7, "credit": 0}, {"account_code": "2-1100", "debit": 0, "credit": 7}])
    assert "dimensions" not in fo.journal(source_type="manual"), "tanpa deal & kas: tidak ada kunci dimensi"


# ============================================================================ D. skenario API
TAG = uuid.uuid4().hex[:5].upper()
SEEN = {}          # peristiwa -> jumlah jurnal yang dibandingkan
JIDS = []


@pytest.fixture(scope="module")
def world():
    return World()


@pytest.fixture(scope="module", autouse=True)
def baseline():
    """Cacah bayangan SEBELUM skenario D (dipakai tes penutup). Toleran: bila endpoint belum ada (kode lama) → None,
    sehingga tes C (dalam-proses) tidak ikut gagal karena server."""
    r = call(FINANCE, "GET", "/gl/posting-profile/shadow-report")
    if r.status_code != 200:
        return None
    rep = r.json()["data"]
    return {"enabled": rep["enabled"], "ev": {e["event"]: (e["checked"], e["diff"]) for e in rep["events"]}}


def journals(**params):
    return ok(call(FINANCE, "GET", "/gl/journals", params={"limit": 100, **params}))["data"]


def wait_journal(event, timeout=40, **params):
    """Tunggu jurnal bercap `profile_event == event` (event outbox diposting dispatcher tiap ≤ 8 dtk)."""
    end, rows = time.time() + timeout, []
    while time.time() < end:
        rows = [j for j in journals(**params) if j.get("profile_event") == event]
        if rows:
            return rows[0]
        time.sleep(1)
    pytest.fail(f"jurnal {event} {params} tidak terbit dalam {timeout} dtk")


def agg(lines):
    out = {}
    for ln in lines:
        for side, v in (("D", ln.get("debit") or 0), ("K", ln.get("credit") or 0)):
            if v:
                out[(side, ln["account_code"])] = out.get((side, ln["account_code"]), 0) + v
    return out


def same_as_profile(j, event, inputs):
    """Jurnal terbit == dry-run profil v0 (masukan dari dokumen sumber) + endpoint verify menyatakan 'sama'."""
    r = ok(call(FINANCE, "POST", "/gl/posting-profile/dry-run", json={"event": event, "inputs": inputs}))["data"]
    assert r["ok"] and r["balanced"], (event, r["errors"])
    exp = agg(r["lines"])
    assert agg(j["lines"]) == exp, f"{event}: jurnal {j['entry_no']} {agg(j['lines'])} != profil v0 {exp}"
    v = ok(call(FINANCE, "GET", f"/gl/posting-profile/verify/{j['id']}"))["data"]
    assert v["status"] == "sama" and v["event"] == event, v
    SEEN[event] = SEEN.get(event, 0) + 1
    JIDS.append(j["id"])
    return j


def receipt_id(resp):
    return (resp.get("data") or resp)["receipt"]["id"]


def test_d1_penerimaan_dan_pembatalan_penerimaan(world):
    d = world.new_deal()["deal_id"]
    rid = receipt_id(ok(pay(d, 100_000_000)))
    jr = same_as_profile(wait_journal("sales.receipt", source_type="receipt", source_id=rid), "sales.receipt",
                         {"amount": 100_000_000})
    cash_ids = {a["id"] for a in ok(call(FINANCE, "GET", "/cash-bank/accounts"))["data"]}
    assert jr["dimensions"]["deal_id"] == d and jr["dimensions"]["cash_account_id"] in cash_ids   # dimensi Fase 3
    ok(call(FINLEAD, "POST", f"/finance/ar/receipts/{rid}/void", json={"reason": "uji H-D batalkan penerimaan"}))
    same_as_profile(wait_journal("sales.receipt_void", source_type="receipt_void", source_id=rid),
                    "sales.receipt_void", {"amount": 100_000_000})


def test_d2_titipan_masuk_dipakai_dikembalikan(world):
    d = world.new_deal()["deal_id"]
    res = ok(call(FINANCE, "POST", f"/finance/ar/{d}/deposit", json={"amount": 20_000_000,
                                                                      "proof_file_ids": [upload_proof()]}))["data"]
    dep = res["deposit"]["id"]
    same_as_profile(wait_journal("sales.deposit_in", source_type="deposit", source_id=dep), "sales.deposit_in",
                    {"amount": 20_000_000})
    ok(call(FINANCE, "POST", f"/finance/ar/{d}/deposit/apply", json={"amount": 8_000_000}))
    same_as_profile(wait_journal("sales.deposit_apply", source_type="deposit", source_id=dep), "sales.deposit_apply",
                    {"amount": 8_000_000})
    ok(call(FINANCE, "POST", f"/finance/ar/{d}/deposit/refund", json={"amount": 12_000_000}))
    same_as_profile(wait_journal("sales.deposit_refund", source_type="deposit", source_id=dep), "sales.deposit_refund",
                    {"amount": 12_000_000})


def test_d3_denda_ditagihkan_dilunasi_dan_diringankan(world):
    sname = f"HD Terlambat {TAG}"
    r = call(OWNER, "POST", "/payment-schemes", json={
        "name": sname, "kind": "cash_bertahap", "code": f"hd-late-{TAG.lower()}", "active": True,
        "terms": [{"label": "Termin lampau", "basis": "percent", "value": 100, "due_offset_days": -90}]})
    world.scheme[sname] = ok(r)["data"]["id"]
    d1 = world.new_deal(scheme=sname)["deal_id"]
    out = ok(call(OWNER, "POST", f"/finance/late-fees/{d1}/apply", json={}))["created"][0]
    same_as_profile(wait_journal("sales.late_fee", source_type="late_fee", source_id=d1), "sales.late_fee",
                    {"amount": out["amount"]})
    ok(call(FINLEAD, "POST", f"/finance/late-fees/{d1}/waive/{out['id']}", json={"reason": "uji H-D keringanan denda"}))
    same_as_profile(wait_journal("sales.late_fee_waive", source_type="late_fee_waiver", source_id=out["id"]),
                    "sales.late_fee_waive", {"amount": out["amount"]})
    d2 = world.new_deal(scheme=sname)["deal_id"]    # denda dilunasi → bagian denda ke piutang denda (GL-02)
    fee = ok(call(OWNER, "POST", f"/finance/late-fees/{d2}/apply", json={}))["created"][0]["amount"]
    inv = ar(d2)["data"]
    rid = receipt_id(ok(pay(d2, int(inv["outstanding"]))))
    same_as_profile(wait_journal("sales.receipt", source_type="receipt", source_id=rid), "sales.receipt",
                    {"amount": int(inv["outstanding"]), "split_penalty": fee})


def test_d4_bast_pengakuan_pendapatan_dan_penerimaan_pasca_bast(world):
    d = world.new_deal()["deal_id"]
    ok(pay(d, 200_000_000))
    ok(call(FINANCE, "POST", f"/finance/ar/{d}/bast"))
    rr = ar(d)["revenue_recognition"]
    j = wait_journal("sales.revrec", source_type="revrec", source_id=rr["id"])
    wip_used = sum(ln["credit"] for ln in j["lines"] if ln["account_code"] == "1-1600")
    same_as_profile(j, "sales.revrec", {"revenue": int(rr["revenue"]), "cogs": int(rr["cogs"]),
                                         "cleared": int(rr["contract_liability_cleared"]), "wip_balance": wip_used})
    rid = receipt_id(ok(pay(d, 50_000_000)))      # pasca-BAST → pelunasan piutang (GL-01)
    same_as_profile(wait_journal("sales.receipt", source_type="receipt", source_id=rid), "sales.receipt",
                    {"amount": 50_000_000, "split_ar": 50_000_000})


def test_d5_ap_setuju_bayar_potong_pph_dan_batal_bayar():
    b = pc.approved_bill(claimed=10_000_000, ret=5)
    det = pc.bill_detail(b["id"])["bill"]
    j = wait_journal("ap.approve", source_type="ap_bill", source_id=b["id"])
    accrual = sum(ln["debit"] for ln in j["lines"] if ln["account_code"] == "2-1700")
    same_as_profile(j, "ap.approve", {"claimed": int(det["claimed"]), "net": int(det["net"]),
                                       "retention": int(det["retention_held"]), "accrual_balance": accrual})
    s, jj = pc.call("finance", "POST", f"/finance/ap/bills/{b['id']}/pay", {"amount": 3_000_000})
    assert s == 200, (s, jj)
    same_as_profile(wait_journal("ap.pay", source_type="ap_bill", source_id=b["id"]), "ap.pay",
                    {"amount": 3_000_000, "withheld": 0})
    s, jj = pc.call("finance", "POST", f"/finance/ap/bills/{b['id']}/pay-withholding",
                    {"bill_id": b["id"], "amount": 2_000_000, "kind": "pph23", "rate": 2.0})
    assert s == 200, (s, jj)
    wh = jj["data"]["withheld"]
    assert wh == 40_000
    pays = ok(call(FINANCE, "GET", "/finance/ap/payments", params={"bill_id": b["id"]}))["data"]
    p2 = next(p for p in pays if int(p["amount"]) == 2_000_000)
    deadline = time.time() + 40
    while time.time() < deadline and len([x for x in journals(source_type="ap_bill", source_id=b["id"])
                                          if x.get("profile_event") == "ap.pay"]) < 2:
        time.sleep(1)
    wj = next(x for x in journals(source_type="ap_bill", source_id=b["id"])
              if x.get("profile_event") == "ap.pay" and any(ln["account_code"] == "2-1300" for ln in x["lines"]))
    same_as_profile(wj, "ap.pay", {"amount": 2_000_000, "withheld": wh})
    s, jj = pc.call("owner", "POST", f"/finance/ap/payments/{p2['id']}/void", {"reason": "uji H-D batalkan pembayaran"})
    assert s == 200, (s, jj)
    same_as_profile(wait_journal("ap.pay_void", source_type="ap_payment_void", source_id=b["id"]), "ap.pay_void",
                    {"amount": 2_000_000, "withheld": wh})


def test_d6_komisi_disetujui_dan_dibayar(world):
    d = world.new_deal()["deal_id"]
    # komisi lahir otomatis saat booking (trigger skema); bila belum ada, hitung manual
    rows = ok(call(FINANCE, "GET", "/finance/commissions", params={"limit": 200}))["data"]
    com = next((c for c in rows if c.get("deal_id") == d), None) \
        or ok(call(FINANCE, "POST", f"/finance/commissions/{d}/compute", json={}))["data"]
    ok(call(OWNER, "POST", f"/finance/commissions/{com['id']}/approve"))
    same_as_profile(wait_journal("commission.approve", source_type="commission", source_id=com["id"]),
                    "commission.approve", {"amount": int(com["amount"])})
    ok(call(FINANCE, "POST", f"/finance/commissions/{com['id']}/pay", json={}))
    same_as_profile(wait_journal("commission.pay", source_type="commission", source_id=com["id"]),
                    "commission.pay", {"amount": int(com["amount"])})


def test_d7_marketing_fee_disetujui_dan_dibayar(world):
    d = world.new_deal()["deal_id"]
    s, a = pc.call("marketing", "POST", "/marketing/agents", {"name": pc.uniq("HD Agen"), "agent_type": "referral_pembeli"})
    assert s == 200, (s, a)
    s, f = pc.call("marketing", "POST", "/marketing/fees", {"agent_id": a["data"]["id"], "deal_id": d, "basis": "fixed",
                                                            "value": 8_000_000, "trigger": "booking", "pph_pct": 2.5})
    assert s == 200, (s, f)
    fee = f["data"]
    assert pc.call("owner", "POST", f"/marketing/fees/{fee['id']}/approve", {})[0] == 200
    same_as_profile(wait_journal("mktfee.approve", source_type="marketing_fee", source_id=fee["id"]), "mktfee.approve",
                    {"gross": int(fee["amount_gross"]), "net": int(fee["amount_net"]), "pph": int(fee["pph_amount"])})
    assert fee["pph_amount"] > 0
    s, jj = pc.call("finance", "POST", f"/marketing/fees/{fee['id']}/pay", {"source": "bank"})
    assert s == 200, (s, jj)
    same_as_profile(wait_journal("mktfee.pay", source_type="marketing_fee_payment", q=fee["no"]), "mktfee.pay",
                    {"amount": int(fee["amount_net"]), "source": "bank"})


def test_d8_pajak_akrual_dan_setor(world):
    d = world.new_deal()["deal_id"]
    from pymongo import MongoClient
    url = os.environ.get("MONGO_URL") or "mongo" + "db://127.0.0.1:27017"
    rec = MongoClient(url)[os.environ["DB_NAME"]].tax_records.find_one({"deal_id": d, "type": "ppn"}, {"_id": 0})
    assert rec and rec["amount"] > 0
    ok(call(FINANCE, "PUT", f"/tax/records/{rec['id']}", json={"status": "reported"}))
    same_as_profile(wait_journal("tax.accrue", source_type="tax_accrual", source_id=rec["id"]), "tax.accrue",
                    {"amount": int(rec["amount"])})
    ok(call(FINANCE, "PUT", f"/tax/records/{rec['id']}", json={"status": "paid", "ntpn": pc.uniq("NTPN")}))
    same_as_profile(wait_journal("tax.deposit", source_type="tax_setor", source_id=rec["id"]), "tax.deposit",
                    {"amount": int(rec["amount"])})


def _advance(amount):
    s, j = pc.call("pm", "POST", "/petty-cash/advances", {"purpose": pc.uniq("HD kas bon"), "amount": amount,
                                                          "category": "transport"})
    assert s == 200, (s, j)
    assert pc.call("finance", "POST", f"/petty-cash/advances/{j['data']['id']}/approve", {})[0] == 200
    return j["data"]["id"]


def test_d9_kas_bon_cair_dan_pertanggungjawaban_sisa_dan_kekurangan():
    # (a) realisasi < cair → sisa dikembalikan; kategori campur (umum + WIP + pemasaran)
    a = _advance(5_000_000)
    s, j = pc.call("finance", "POST", f"/petty-cash/advances/{a}/disburse", {"source": "bank"})
    assert s == 200, (s, j)
    same_as_profile(wait_one("cash_advance", a, "cashbon.disburse:"), "staff.advance_disburse", {"amount": 5_000_000})
    items = [{"category": "transport", "description": "ojek", "amount": 1_000_000},
             {"category": "biaya_proyek", "description": "paku", "amount": 1_500_000},
             {"category": "pemasaran_promosi", "description": "spanduk", "amount": 700_000}]
    s, j = pc.call("pm", "POST", f"/petty-cash/advances/{a}/settle", {"items": items})
    assert s == 200, (s, j)
    same_as_profile(wait_one("cash_advance", a, "cashbon.settle:"), "staff.advance_settle",
                    {"disbursed": 5_000_000, "exp_general": 1_000_000, "exp_wip": 1_500_000, "exp_marketing": 700_000})
    # (b) realisasi > cair → penggantian kas keluar tambahan
    b = _advance(2_000_000)
    assert pc.call("finance", "POST", f"/petty-cash/advances/{b}/disburse", {"source": "bank"})[0] == 200
    s, j = pc.call("pm", "POST", f"/petty-cash/advances/{b}/settle",
                   {"items": [{"category": "upah_harian", "description": "tukang", "amount": 2_600_000}]})
    assert s == 200, (s, j)
    same_as_profile(wait_one("cash_advance", b, "cashbon.settle:"), "staff.advance_settle",
                    {"disbursed": 2_000_000, "exp_wip": 2_600_000})


def wait_one(source_type, source_id, prefix):
    """Jurnal langsung (sinkron) — ambil yang source_event-nya berawalan `prefix`."""
    rows = [j for j in journals(source_type=source_type, source_id=source_id) if (j.get("source_event") or "").startswith(prefix)]
    assert rows, (source_type, source_id, prefix)
    return rows[0]


def test_d10_aset_tetap_perolehan_penyusutan_dan_pelepasan():
    vendor = pc.uniq("HD Vendor")
    ids = {}
    for funding in ("bank", "utang_usaha"):
        body = {"name": pc.uniq(f"HD Aset {funding}"), "category": "komputer_it", "tax_group": "kelompok_1",
                "method": "garis_lurus", "cost": 12_000_000, "salvage_value": 0, "useful_life_months": 12,
                "funding": funding, **({"vendor": vendor} if funding == "utang_usaha" else {})}
        s, j = pc.call("finance", "POST", "/fixed-assets/assets", body)
        assert s == 200, (s, j)
        ids[funding] = j["data"]["id"]
        same_as_profile(wait_one("fixed_asset", ids[funding], "asset.acquire:"), "fixed_asset.acquire",
                        {"cost": 12_000_000, "funding": funding})
    run = ok(call(OWNER, "POST", "/fixed-assets/depreciation/run", json={"period": time.strftime("%Y-%m")}))["data"]
    rows = {r["asset_id"]: r for r in run["rows"]}
    for aid in ids.values():
        assert rows[aid]["amount"] == 1_000_000
        same_as_profile(wait_one("asset_depreciation", aid, "asset.depr:"), "fixed_asset.depreciate", {"amount": 1_000_000})
    # pelepasan: laba (hasil 13 jt > nilai buku 11 jt) dan rugi (hasil 5 jt < 11 jt)
    for aid, proceeds in ((ids["bank"], 13_000_000), (ids["utang_usaha"], 5_000_000)):
        ok(call(OWNER, "POST", f"/fixed-assets/assets/{aid}/dispose", json={"proceeds": proceeds, "source": "bank"}))
        j = next(x for x in journals(source_type="fixed_asset", source_id=aid) if x["source_event"].startswith("asset.dispose:"))
        same_as_profile(j, "fixed_asset.dispose", {"cost": 12_000_000, "accum": 1_000_000, "proceeds": proceeds})


def test_d11_pembatalan_keputusan_dan_refund_bank_serta_tunai(world):
    from test_p0_masuk_2 import approve, cancel_case, _refund_body
    d = cancel_case(world, paid=100_000_000)
    cid = d["cancel_id"]
    doc = approve(cid)
    st = doc.get("settlement") or {}
    same_as_profile(wait_one("cancellation", cid, "cancel:"), "cancel.decision", {
        "received_total": int(st.get("received_total", 100_000_000)), "deposit_balance": int(st.get("deposit_balance", 0)),
        "cut_amount": int(st.get("cut_amount", 35_000_000)), "payable_total": int(st.get("payable_total", 65_000_000))})
    assert int(st.get("payable_total", 65_000_000)) == 65_000_000
    ok(call(OWNER, "POST", f"/cancellations/{cid}/refund", json=_refund_body(30_000_000)))
    pc.fund("Kas Besar", 20_000_000)
    ok(call(OWNER, "POST", f"/cancellations/{cid}/refund", json=_refund_body(5_000_000, method="tunai")))
    pays = [j for j in journals(source_type="cancellation_refund") if j.get("source_deal_id") == d["deal_id"]]
    assert len(pays) == 2
    bank_j = next(j for j in pays if any(ln["credit"] == 30_000_000 for ln in j["lines"]))
    cash_j = next(j for j in pays if any(ln["credit"] == 5_000_000 for ln in j["lines"]))
    same_as_profile(bank_j, "cancel.refund_pay", {"amount": 30_000_000, "method": "transfer"})
    same_as_profile(cash_j, "cancel.refund_pay", {"amount": 5_000_000, "method": "tunai"})


def test_zz_bayangan_tidak_mencatat_selisih_pada_skenario_ini(baseline):
    """Bila server berjalan dengan POSTING_SHADOW=1: setiap peristiwa yang kita jalankan dicek bayangan dan TIDAK ada selisih."""
    assert baseline is not None, "endpoint shadow-report tidak ada"
    assert set(SEEN) >= {"sales.receipt", "sales.revrec", "ap.approve", "ap.pay", "commission.approve",
                         "mktfee.approve", "tax.accrue", "staff.advance_settle", "fixed_asset.dispose", "cancel.decision"}, SEEN
    rep = ok(call(FINANCE, "GET", "/gl/posting-profile/shadow-report", params={"limit": 100}))["data"]
    if not rep["enabled"]:
        pytest.skip("server tidak berjalan dengan POSTING_SHADOW=1 — bukti ekuivalensi tetap dari dry-run+verify di atas")
    now = {e["event"]: (e["checked"], e["diff"]) for e in rep["events"]}
    for ev, n in SEEN.items():
        c0, d0 = baseline["ev"].get(ev, (0, 0))
        assert now[ev][0] - c0 >= n, (ev, "bayangan tidak mengecek jurnal ini", now[ev], c0, n)
        assert now[ev][1] - d0 == 0, (ev, "SELISIH bayangan", now[ev], d0)
    assert not [x for x in rep["recent_diffs"] if x["journal_id"] in set(JIDS)], "jurnal skenario ini punya catatan selisih"
