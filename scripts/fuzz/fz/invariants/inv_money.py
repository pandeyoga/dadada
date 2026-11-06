"""Invarian UANG: AR/kuitansi/kewajiban kontrak/titipan/AP/komisi/KPR (subledger ↔ subledger)."""
from collections import defaultdict

from ..core import V, i, invariant

LIVE_DEAL = ("reserved", "booked", "completed")


def _live_receipts(s, deal_id=None):
    for r in s.rows("receipts"):
        if r.get("status") == "void":
            continue
        if deal_id is None or r.get("deal_id") == deal_id:
            yield r


def _inv_tag(inv):
    return f"AR {inv.get('unit_code') or inv['id'][:6]}/{inv['deal_id'][:6]}"


# ============================================================ AR (piutang termin)
@invariant("M01", "AR", "ar_invoices.paid = Σ items.paid_amount")
def m01(s):
    out = []
    for inv in s.rows("ar_invoices"):
        sp = sum(i(x.get("paid_amount")) for x in inv.get("items") or [])
        if i(inv.get("paid")) != sp:
            out.append(V("M01", inv["deal_id"], f"{_inv_tag(inv)} paid={i(inv.get('paid')):,} ≠ Σ item.paid_amount={sp:,}", i(inv.get('paid')) - sp))
    return out


@invariant("M02", "AR", "outstanding = total − paid (AR batal: outstanding = 0)")
def m02(s):
    out = []
    for inv in s.rows("ar_invoices"):
        o, t, p = i(inv.get("outstanding")), i(inv.get("total")), i(inv.get("paid"))
        if inv.get("status") == "cancelled":
            if o != 0:
                out.append(V("M02", inv["deal_id"], f"{_inv_tag(inv)} AR batal tapi outstanding={o:,}", o))
        elif o != t - p:
            out.append(V("M02", inv["deal_id"], f"{_inv_tag(inv)} outstanding={o:,} ≠ total−paid={t - p:,}", o - (t - p)))
    return out


@invariant("M03", "AR", "Σ items.amount = total (AR tidak batal)")
def m03(s):
    out = []
    for inv in s.rows("ar_invoices"):
        if inv.get("status") == "cancelled":
            continue
        sa = sum(i(x.get("amount")) for x in inv.get("items") or [])
        if sa != i(inv.get("total")):
            out.append(V("M03", inv["deal_id"], f"{_inv_tag(inv)} Σ item.amount={sa:,} ≠ total={i(inv.get('total')):,}", sa - i(inv.get('total'))))
    return out


@invariant("M04", "AR", "status & batas tiap termin: 0 ≤ paid_amount ≤ amount, status sesuai")
def m04(s):
    out = []
    for inv in s.rows("ar_invoices"):
        if inv.get("status") == "cancelled":
            continue
        for it in inv.get("items") or []:
            amt, pd = i(it.get("amount")), i(it.get("paid_amount"))
            if pd < 0 or pd > amt:
                out.append(V("M04", f"{inv['deal_id']}/{it['id']}", f"{_inv_tag(inv)} termin '{it.get('label')}' paid={pd:,} di luar [0,{amt:,}]", pd))
                continue
            exp = "cancelled" if it.get("waived") else ("paid" if pd >= amt and amt > 0 else ("partial" if pd > 0 else "unpaid"))
            if it.get("status") != exp:
                out.append(V("M04", f"{inv['deal_id']}/{it['id']}", f"{_inv_tag(inv)} termin '{it.get('label')}' status={it.get('status')} seharusnya {exp}"))
    return out


@invariant("M05", "AR", "status invoice sesuai paid/outstanding")
def m05(s):
    out = []
    for inv in s.rows("ar_invoices"):
        if inv.get("status") == "cancelled":
            continue
        o, p = i(inv.get("outstanding")), i(inv.get("paid"))
        exp = "paid" if o <= 0 else ("partial" if p > 0 else "unpaid")
        if inv.get("status") != exp:
            out.append(V("M05", inv["deal_id"], f"{_inv_tag(inv)} status={inv.get('status')} seharusnya {exp}"))
    return out


@invariant("M06", "AR", "ar_invoices.paid = Σ kuitansi tidak-void (applied) per deal")
def m06(s):
    out = []
    recs = defaultdict(int)
    for r in _live_receipts(s):
        recs[r["deal_id"]] += i(r.get("applied"))
    for inv in s.rows("ar_invoices"):
        if inv.get("status") == "cancelled":
            continue   # AR batal: paid dibekukan; kuitansi dikembalikan lewat refund
        if i(inv.get("paid")) != recs.get(inv["deal_id"], 0):
            out.append(V("M06", inv["deal_id"], f"{_inv_tag(inv)} paid={i(inv.get('paid')):,} ≠ Σ kuitansi aktif={recs.get(inv['deal_id'], 0):,}", i(inv.get('paid')) - recs.get(inv['deal_id'], 0)))
    return out


@invariant("M07", "AR", "paid_amount tiap termin = Σ alokasi kuitansi aktif ke termin itu", known="IN-14/FN-25")
def m07(s):
    out = []
    alloc = defaultdict(int)
    for r in _live_receipts(s):
        for a in r.get("allocations") or []:
            if a.get("item_id") is None:     # kuitansi booking fee: alokasi semu ke faktur BF, bukan ke termin
                continue
            alloc[(r["deal_id"], a.get("item_id"))] += i(a.get("amount"))
    for inv in s.rows("ar_invoices"):
        if inv.get("status") == "cancelled":
            continue
        for it in inv.get("items") or []:
            a = alloc.get((inv["deal_id"], it["id"]), 0)
            if i(it.get("paid_amount")) != a:
                out.append(V("M07", f"{inv['deal_id']}/{it['id']}", f"{_inv_tag(inv)} termin '{it.get('label')}' paid_amount={i(it.get('paid_amount')):,} ≠ Σ alokasi kuitansi={a:,}", i(it.get('paid_amount')) - a))
        ids = {it["id"] for it in inv.get("items") or []}
        for (d, iid), v in list(alloc.items()):
            if d == inv["deal_id"] and iid not in ids and v:
                out.append(V("M07", f"{d}/{iid}", f"{_inv_tag(inv)} kuitansi mengalokasikan Rp {v:,} ke termin yang tidak ada lagi (jadwal diganti?)", v))
    return out


@invariant("M08", "Kuitansi", "Σ allocations.amount = applied; kas = applied + titipan; kuitansi dana-titipan: amount = 0")
def m08(s):
    out = []
    for r in s.rows("receipts"):
        sa = sum(i(a.get("amount")) for a in r.get("allocations") or [])
        if sa != i(r.get("applied")) and r.get("kind") != "booking_fee":
            out.append(V("M08", r["id"], f"kuitansi {r.get('receipt_no')} Σ alokasi={sa:,} ≠ applied={i(r.get('applied')):,}", sa - i(r.get('applied'))))
        if (r.get("funding") or "cash") == "cash" and i(r.get("amount")) != i(r.get("applied")) + i(r.get("deposit_amount")):
            out.append(V("M08", r["id"], f"kuitansi {r.get('receipt_no')} kas={i(r.get('amount')):,} ≠ applied+titipan={i(r.get('applied')) + i(r.get('deposit_amount')):,}"))
        if r.get("funding") == "deposit" and i(r.get("amount")) != 0:
            out.append(V("M08", r["id"], f"kuitansi {r.get('receipt_no')} dari titipan tapi amount={i(r.get('amount')):,}≠0"))
    return out


@invariant("M09", "Kuitansi", "kuitansi menunjuk deal & AR yang ada (tanpa kuitansi yatim)")
def m09(s):
    out = []
    deals, invs = s.idx("deals"), s.idx("ar_invoices", "deal_id")
    for r in s.rows("receipts"):
        if r.get("deal_id") not in deals:
            out.append(V("M09", r["id"], f"kuitansi {r.get('receipt_no')} → deal {str(r.get('deal_id'))[:8]} tidak ada"))
        elif r.get("deal_id") not in invs and not (r.get("kind") == "booking_fee" and deals[r["deal_id"]].get("status") in ("reserved", "draft")):
            out.append(V("M09", r["id"], f"kuitansi {r.get('receipt_no')} → deal ada tetapi AR tidak ada"))
    return out


@invariant("M10", "Kuitansi", "nilai kuitansi aktif tidak melebihi total tagihan + titipan (tidak ada kelebihan alokasi)")
def m10(s):
    out = []
    for inv in s.rows("ar_invoices"):
        if inv.get("status") == "cancelled":
            continue
        a = sum(i(r.get("applied")) for r in _live_receipts(s, inv["deal_id"]))
        if a > i(inv.get("total")):
            out.append(V("M10", inv["deal_id"], f"{_inv_tag(inv)} Σ applied={a:,} > total tagihan={i(inv.get('total')):,}", a - i(inv.get('total'))))
    return out


# ============================================================ kewajiban kontrak & titipan
def _liab_part(r):
    sp = r.get("gl_split")
    return i(sp.get("liability")) if sp else i(r.get("applied"))


@invariant("M11", "KewajibanKontrak", "contract_liability.balance = Σ bagian liability kuitansi aktif (deal belum BAST, tidak batal)", known="GL-01/GL-20")
def m11(s):
    out = []
    deals = s.idx("deals")
    canc_deals = {c.get("deal_id") for c in s.rows("cancellations") if c.get("state") in ("disetujui", "refund_sebagian", "selesai")}
    for cl in s.rows("contract_liabilities"):
        d = deals.get(cl.get("deal_id"))
        if not d or d.get("status") in ("cancelled", "expired") or cl.get("deal_id") in canc_deals:
            continue
        if cl.get("recognized"):
            if i(cl.get("balance")) != 0:
                out.append(V("M11", cl["deal_id"], f"kewajiban kontrak sudah diakui (BAST) tapi balance={i(cl.get('balance')):,}≠0", i(cl.get('balance'))))
            continue
        exp = sum(_liab_part(r) for r in _live_receipts(s, cl["deal_id"]))
        if i(cl.get("balance")) != exp:
            out.append(V("M11", cl["deal_id"], f"deal {cl['deal_id'][:6]} kewajiban kontrak={i(cl.get('balance')):,} ≠ Σ bagian liability kuitansi aktif={exp:,}", i(cl.get('balance')) - exp))
    return out


@invariant("M12", "KewajibanKontrak", "balance ≥ 0 dan tepat satu baris kewajiban per deal")
def m12(s):
    out = []
    cnt = defaultdict(int)
    for cl in s.rows("contract_liabilities"):
        cnt[cl.get("deal_id")] += 1
        if i(cl.get("balance")) < 0:
            out.append(V("M12", cl.get("deal_id"), f"kewajiban kontrak negatif {i(cl.get('balance')):,}", i(cl.get('balance'))))
    for d, n in cnt.items():
        if n > 1:
            out.append(V("M12", d, f"{n} baris contract_liabilities untuk satu deal"))
    return out


@invariant("M13", "Titipan", "titipan: saldo = Σ masuk − Σ dipakai − Σ dikembalikan ≥ 0; total tersimpan = Σ mutasi")
def m13(s):
    out = []
    for d in s.rows("customer_deposits"):
        e = d.get("entries") or []
        gin = sum(i(x.get("amount")) for x in e if x.get("type") == "in")
        gap = sum(i(x.get("amount")) for x in e if x.get("type") == "apply")
        gre = sum(i(x.get("amount")) for x in e if x.get("type") == "refund")
        gct = sum(i(x.get("amount")) for x in e if x.get("type") == "cancel_transfer")   # dipindah ke utang refund (pembatalan formal)
        bal = i(d.get("balance"))
        tag = f"titipan deal {str(d.get('deal_id'))[:6]}"
        if bal < 0:
            out.append(V("M13", d["deal_id"], f"{tag} saldo negatif {bal:,}", bal))
        if bal != gin - gap - gre - gct:
            out.append(V("M13", d["deal_id"], f"{tag} saldo={bal:,} ≠ in−apply−refund−cancel_transfer={gin - gap - gre - gct:,}", bal - (gin - gap - gre - gct)))
        for f, v in (("received_total", gin), ("applied_total", gap), ("refunded_total", gre)):
            if i(d.get(f)) != v:
                out.append(V("M13", f"{d['deal_id']}/{f}", f"{tag} {f}={i(d.get(f)):,} ≠ Σ mutasi={v:,}", i(d.get(f)) - v))
    return out


@invariant("M14", "Titipan", "titipan dipakai = Σ applied kuitansi berdana-titipan aktif (tak ada pemakaian tanpa kuitansi)")
def m14(s):
    out = []
    ap = defaultdict(int)
    for r in _live_receipts(s):
        if r.get("funding") == "deposit":
            ap[r["deal_id"]] += i(r.get("applied"))
    deps = s.idx("customer_deposits", "deal_id")
    for did in set(ap) | set(deps):
        d = deps.get(did)
        got = i(d.get("applied_total")) if d else 0
        if got != ap.get(did, 0):
            out.append(V("M14", did, f"deal {str(did)[:6]} titipan dipakai={got:,} ≠ Σ kuitansi dana-titipan aktif={ap.get(did, 0):,}", got - ap.get(did, 0)))
    return out


@invariant("M15", "Titipan", "titipan masuk = Σ deposit_amount kuitansi tunai aktif + setoran titipan langsung", level="soft")
def m15(s):
    """Indikator: 'in' pada titipan boleh juga dari setoran langsung (tanpa kuitansi) — tidak dituntut sama."""
    out = []
    dep_rec = defaultdict(int)
    for r in _live_receipts(s):
        dep_rec[r["deal_id"]] += i(r.get("deposit_amount"))
    deps = s.idx("customer_deposits", "deal_id")
    for did, v in dep_rec.items():
        d = deps.get(did)
        gin = sum(i(x.get("amount")) for x in (d or {}).get("entries", []) if x.get("type") == "in")
        if gin < v:
            out.append(V("M15", did, f"deal {str(did)[:6]} kuitansi aktif melahirkan titipan Rp {v:,} tetapi mutasi titipan masuk hanya Rp {gin:,}", gin - v))
    return out


# ============================================================ AP
def _live_pay(s, bill_id):
    return [p for p in s.grp("payments_out", "bill_id").get(bill_id, []) if p.get("status") != "void"]


@invariant("M16", "AP", "ap_invoices.paid = Σ payments_out tidak-void; paid ≤ net; outstanding = net − paid")
def m16(s):
    out = []
    for b in s.rows("ap_invoices"):
        if b.get("status") not in ("approved", "partial", "paid"):
            continue
        ps = sum(i(p.get("amount")) for p in _live_pay(s, b["id"]))
        tag = f"AP {b.get('vendor')}/{b['id'][:6]}"
        if i(b.get("paid")) != ps:
            out.append(V("M16", b["id"], f"{tag} paid={i(b.get('paid')):,} ≠ Σ pembayaran aktif={ps:,}", i(b.get('paid')) - ps))
        if i(b.get("paid")) > i(b.get("net")):
            out.append(V("M16", f"{b['id']}/over", f"{tag} paid {i(b.get('paid')):,} > net {i(b.get('net')):,}", i(b.get('paid')) - i(b.get('net'))))
        if i(b.get("outstanding")) != max(0, i(b.get("net")) - i(b.get("paid"))):
            out.append(V("M16", f"{b['id']}/out", f"{tag} outstanding={i(b.get('outstanding')):,} ≠ net−paid"))
    return out


@invariant("M17", "AP", "status AP sesuai pembayaran; retensi = round(claimed×pct%); net = claimed − retensi")
def m17(s):
    out = []
    for b in s.rows("ap_invoices"):
        tag = f"AP {b.get('vendor')}/{b['id'][:6]}"
        if b.get("kind") and b.get("kind") != "bill":
            pass
        held = i(b.get("retention_held"))
        if b.get("bill_kind") != "retention_release" and held != round(i(b.get("claimed")) * float(b.get("retention_pct") or 0) / 100):
            out.append(V("M17", f"{b['id']}/ret", f"{tag} retensi {held:,} ≠ round(claimed×pct)"))
        if b.get("bill_kind") != "retention_release" and i(b.get("net")) != i(b.get("claimed")) - held:
            out.append(V("M17", f"{b['id']}/net", f"{tag} net {i(b.get('net')):,} ≠ claimed−retensi"))
        st, p, n = b.get("status"), i(b.get("paid")), i(b.get("net"))
        if st == "paid" and p < n:
            out.append(V("M17", f"{b['id']}/st", f"{tag} status paid tetapi paid {p:,} < net {n:,}"))
        if st == "partial" and not (0 < p < n):
            out.append(V("M17", f"{b['id']}/st", f"{tag} status partial tetapi paid={p:,}/net={n:,}"))
        if st == "approved" and p != 0:
            out.append(V("M17", f"{b['id']}/st", f"{tag} status approved tetapi paid={p:,}"))
        if st in ("approved", "partial", "paid") and not b.get("approved_by"):
            out.append(V("M17", f"{b['id']}/ap", f"{tag} status {st} tanpa approved_by"))
    return out


@invariant("M18", "AP", "tiap pembayaran vendor aktif punya tagihan induk yang ada & tidak pending/ditolak")
def m18(s):
    out = []
    bills = s.idx("ap_invoices")
    for p in s.rows("payments_out"):
        if p.get("status") == "void" or not p.get("bill_id"):
            continue
        b = bills.get(p["bill_id"])
        if not b:
            out.append(V("M18", p["id"], f"pembayaran {p['id'][:6]} Rp {i(p.get('amount')):,} → tagihan tidak ada (yatim)"))
        elif b.get("status") in ("pending_approval", "rejected", "cancelled", "void"):
            out.append(V("M18", p["id"], f"pembayaran {p['id'][:6]} aktif pada tagihan berstatus {b.get('status')}"))
    return out


# ============================================================ komisi, KPR, pembatalan
@invariant("M19", "Komisi", "komisi: amount = round(base×rate%) ≤ base; approved/paid punya approver; satu komisi per (deal, penerima)")
def m19(s):
    out = []
    seen = defaultdict(int)
    for c in s.rows("commissions"):
        b, r, a = i(c.get("base")), float(c.get("rate_pct") or 0), i(c.get("amount"))
        tag = f"komisi {c.get('unit_code') or c['id'][:6]}"
        if a != round(b * r / 100) and not c.get("amount_override"):
            out.append(V("M19", f"{c['id']}/calc", f"{tag} amount {a:,} ≠ round({b:,}×{r}%)", a - round(b * r / 100)))
        if a > b:
            out.append(V("M19", f"{c['id']}/gt", f"{tag} amount {a:,} > dasar {b:,}", a - b))
        if c.get("status") in ("approved", "paid") and not c.get("approved_by"):
            out.append(V("M19", f"{c['id']}/ap", f"{tag} status {c.get('status')} tanpa approver"))
        seen[(c.get("deal_id"), c.get("assigned_to"), c.get("scheme_id"))] += 1
    for k, n in seen.items():
        if n > 1:
            out.append(V("M19", f"dup/{k[0]}", f"deal {str(k[0])[:6]} punya {n} komisi identik (penerima+skema)"))
    return out


@invariant("M20", "KPR", "KPR: disbursed_total = Σ pencairan ≤ plafon; receipt_id pencairan ada; bukan nominal ≤ 0")
def m20(s):
    out = []
    recs = s.idx("receipts")
    for f in s.rows("financing_apps"):
        ds = [d for d in f.get("disbursements") or [] if d.get("status") not in ("cancelled", "void")]
        tot = sum(i(d.get("amount")) for d in ds)
        tag = f"KPR {f['id'][:6]}"
        if i(f.get("disbursed_total")) != tot:
            out.append(V("M20", f"{f['id']}/tot", f"{tag} disbursed_total={i(f.get('disbursed_total')):,} ≠ Σ pencairan aktif={tot:,}", i(f.get('disbursed_total')) - tot))
        if f.get("plafon") and tot > i(f.get("plafon")):
            out.append(V("M20", f"{f['id']}/plafon", f"{tag} pencairan {tot:,} > plafon {i(f.get('plafon')):,}", tot - i(f.get('plafon'))))
        for d in ds:
            if i(d.get("amount")) <= 0:
                out.append(V("M20", f"{f['id']}/neg", f"{tag} pencairan nominal {i(d.get('amount')):,}"))
            if d.get("receipt_id") and d["receipt_id"] not in recs:
                out.append(V("M20", f"{f['id']}/{d['receipt_id']}", f"{tag} receipt_id pencairan tidak ada"))
            elif d.get("receipt_id") and recs[d["receipt_id"]].get("status") == "void":
                out.append(V("M20", f"{f['id']}/{d['receipt_id']}", f"{tag} pencairan aktif tetapi kuitansinya void"))
    return out


@invariant("M21", "Pembatalan", "deal batal ⇒ AR batal (outstanding 0) dan kewajiban kontrak tak menggantung tanpa kuitansi/pembatalan",
           known="IN-13/FN-21")
def m21(s):
    out = []
    invs = s.idx("ar_invoices", "deal_id")
    cancs = s.grp("cancellations", "deal_id")
    cls = s.idx("contract_liabilities", "deal_id")
    for d in s.rows("deals"):
        if d.get("status") != "cancelled":
            continue
        inv = invs.get(d["id"])
        approved = any(c.get("state") in ("disetujui", "refund_sebagian", "selesai") for c in cancs.get(d["id"], []))
        if inv and inv.get("status") != "cancelled" and not (approved and inv.get("status") == "paid" and i(inv.get("outstanding")) == 0):
            # AR yang SUDAH LUNAS sengaja tidak ditandai 'cancelled' oleh pembatalan formal (cancellation_engine._void_ar) — bukan pelanggaran
            out.append(V("M21", f"{d['id']}/ar", f"deal batal {d['id'][:6]} tetapi AR berstatus {inv.get('status')} outstanding={i(inv.get('outstanding')):,}", i(inv.get('outstanding'))))
        cl = cls.get(d["id"])
        paid_live = sum(i(r.get("applied")) for r in _live_receipts(s, d["id"]))
        if cl and i(cl.get("balance")) > 0 and not cancs.get(d["id"]) and paid_live == 0:
            out.append(V("M21", f"{d['id']}/cl", f"deal batal {d['id'][:6]} kewajiban kontrak masih Rp {i(cl.get('balance')):,} tanpa kuitansi aktif/pembatalan", i(cl.get('balance'))))
    return out


@invariant("M22", "Pembatalan", "refund pembatalan: Σ refund dibayar ≤ Σ kuitansi aktif deal; refund_paid_total = Σ refund_payments")
def m22(s):
    out = []
    for c in s.rows("cancellations"):
        paid = sum(i(p.get("amount")) for p in c.get("refund_payments") or [] if p.get("status") != "void")
        if i(c.get("refund_paid_total")) != paid:
            out.append(V("M22", f"{c['id']}/tot", f"pembatalan {c.get('number')} refund_paid_total={i(c.get('refund_paid_total')):,} ≠ Σ refund_payments={paid:,}", i(c.get('refund_paid_total')) - paid))
        recv = sum(i(r.get("amount")) for r in s.grp("receipts", "deal_id").get(c.get("deal_id"), []))
        if paid > recv and recv >= 0:
            out.append(V("M22", f"{c['id']}/over", f"pembatalan {c.get('number')} refund Rp {paid:,} > Σ uang yang pernah diterima deal Rp {recv:,}", paid - recv))
    return out


@invariant("M23", "PDC", "giro: giro cair punya kuitansi/jurnal yang ada; giro batal/tolak tidak punya kuitansi aktif", level="soft")
def m23(s):
    out = []
    recs = s.idx("receipts")
    for p in s.rows("pdc"):
        rid = p.get("receipt_id")
        if p.get("status") == "cleared":
            if rid and rid not in recs:
                out.append(V("M23", p["id"], f"giro {p.get('instrument_no')} cair → kuitansi tidak ada"))
        elif p.get("status") in ("bounced", "cancelled") and rid and recs.get(rid, {}).get("status") != "void":
            out.append(V("M23", p["id"], f"giro {p.get('instrument_no')} {p.get('status')} tetapi kuitansi {rid[:6]} masih aktif"))
    return out


@invariant("M24", "Pembatalan", "deal batal tidak menyimpan titipan pelanggan tanpa catatan pembatalan/refund (uang tertahan)", known="IN-13/FN-03", level="soft")
def m24(s):
    out = []
    cancs = s.grp("cancellations", "deal_id")
    deals = s.idx("deals")
    for dep in s.rows("customer_deposits"):
        d = deals.get(dep.get("deal_id"))
        if d and d.get("status") in ("cancelled", "expired") and i(dep.get("balance")) > 0 and not cancs.get(d["id"]):
            out.append(V("M24", d["id"], f"deal {d.get('status')} {d['id'][:6]} menyimpan titipan Rp {i(dep.get('balance')):,} tanpa catatan pembatalan (uang tertahan; harus di-refund manual)", i(dep.get('balance'))))
    return out


@invariant("M25", "BookingFee", "faktur booking fee: paid = Σ kuitansi BF aktif (− refund); refunded_total = Σ refunds; status & nominal selaras deal.booking_fee")
def m25(s):
    out = []
    recs = s.idx("receipts")
    deals = s.idx("deals")
    for b in s.rows("booking_fee_invoices"):
        tag = f"BF {b.get('no')}"
        rs = [recs[r] for r in b.get("receipt_ids") or [] if r in recs]
        live = sum(i(r.get("amount")) for r in rs if r.get("status") != "void")
        refunded = sum(i(x.get("amount")) for x in b.get("refunds") or [])
        if b.get("status") != "cancelled" and i(b.get("paid")) not in (live, live - refunded):
            out.append(V("M25", f"{b['id']}/paid", f"{tag} paid={i(b.get('paid')):,} ≠ Σ kuitansi BF aktif={live:,} (refund {refunded:,})", i(b.get('paid')) - live))
        if i(b.get("refunded_total")) != refunded:
            out.append(V("M25", f"{b['id']}/ref", f"{tag} refunded_total={i(b.get('refunded_total')):,} ≠ Σ refunds={refunded:,}"))
        if b.get("status") == "paid" and i(b.get("paid")) < i(b.get("amount")):
            out.append(V("M25", f"{b['id']}/st", f"{tag} status paid tetapi paid {i(b.get('paid')):,} < amount {i(b.get('amount')):,}"))
        if b.get("status") == "unpaid" and i(b.get("paid")) > 0:
            out.append(V("M25", f"{b['id']}/st2", f"{tag} status unpaid tetapi paid {i(b.get('paid')):,}"))
        d = deals.get(b.get("deal_id"))
        if d and b.get("status") != "cancelled" and i(d.get("booking_fee")) != i(b.get("amount")):
            out.append(V("M25", f"{b['id']}/amt", f"{tag} amount {i(b.get('amount')):,} ≠ deal.booking_fee {i(d.get('booking_fee')):,}"))
    return out
