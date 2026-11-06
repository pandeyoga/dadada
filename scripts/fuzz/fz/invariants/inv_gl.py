"""Invarian BUKU BESAR: tie-out akun kendali ↔ subledger, keseimbangan jurnal, pasangan dokumen↔jurnal, kas/bank.
`settled=True` = baru dicek setelah antrean event GL kosong (dispatcher menerbitkan jurnal secara asinkron)."""
from collections import defaultdict

from ..core import V, i, invariant


def _live_receipts(s):
    return [r for r in s.rows("receipts") if r.get("status") != "void"]


def _tie(s, inv, code, label, gl_val, sub, known=None):
    if gl_val != sub:
        return [V(inv, code, f"GL {code} {label}: GL={gl_val:,} ≠ subledger={sub:,} (selisih {gl_val - sub:,})", gl_val - sub)]
    return []


# ============================================================ tie-out akun kendali
@invariant("G01", "GL", "GL 2-1400 Uang Muka Penjualan = Σ contract_liabilities.balance (belum BAST)", settled=True, known="GL-01/GL-20")
def g01(s):
    sub = sum(i(c.get("balance")) for c in s.rows("contract_liabilities") if not c.get("recognized"))
    return _tie(s, "G01", "2-1400", "Uang Muka", s.gl_cr("2-1400"), sub)


@invariant("G02", "GL", "GL 2-1450 Titipan Pelanggan = Σ customer_deposits.balance", settled=True)
def g02(s):
    return _tie(s, "G02", "2-1450", "Titipan", s.gl_cr("2-1450"), sum(i(d.get("balance")) for d in s.rows("customer_deposits")))


@invariant("G03", "GL", "GL 2-1100 Utang Usaha = Σ (net − paid) tagihan disetujui", settled=True)
def g03(s):
    sub = sum(i(b.get("net")) - i(b.get("paid")) for b in s.rows("ap_invoices") if b.get("status") in ("approved", "partial", "paid"))
    return _tie(s, "G03", "2-1100", "Utang Usaha", s.gl_cr("2-1100"), sub)


@invariant("G04", "GL", "GL 2-1200 Utang Retensi = Σ retensi ditahan (belum dicairkan)", settled=True)
def g04(s):
    sub = sum(i(b.get("retention_held")) for b in s.rows("ap_invoices")
              if b.get("status") in ("approved", "partial", "paid") and not b.get("retention_released"))
    return _tie(s, "G04", "2-1200", "Utang Retensi", s.gl_cr("2-1200"), sub)


@invariant("G05", "GL", "GL 2-1600 Utang Komisi = Σ komisi approved belum dibayar", settled=True)
def g05(s):
    sub = sum(i(c.get("amount")) for c in s.rows("commissions") if c.get("status") == "approved")
    return _tie(s, "G05", "2-1600", "Utang Komisi", s.gl_cr("2-1600"), sub)


@invariant("G06", "GL", "GL 1-1500 Kas Bon = Σ kas bon + pengajuan dana jenis advance yang cair & belum dipertanggungjawabkan", settled=True)
def g06(s):
    a = sum(i(r.get("disbursed_amount")) for r in s.rows("cash_advances") if r.get("status") == "disbursed")
    b = sum(i(r.get("disbursed_amount")) for r in s.rows("fund_requests") if r.get("type") == "advance" and r.get("status") == "disbursed")
    return _tie(s, "G06", "1-1500", "Kas Bon", s.gl_dr("1-1500"), a + b)


@invariant("G07", "GL", "GL 1-1300 Piutang = piutang BAST belum tertagih + denda belum tertagih (turunan dari AR)", settled=True, level="soft")
def g07(s):
    """Indikator turunan: piutang pasca-BAST (revenue − kewajiban dibersihkan) + denda tak-dibatalkan
    − bagian kuitansi aktif yang mengkredit 1-1300 (split.ar + split.penalty)."""
    canc_deals = {c.get("deal_id") for c in s.rows("cancellations") if c.get("state") in ("disetujui", "refund_sebagian", "selesai")}
    deals = s.idx("deals")
    ar_bast = 0
    for rr in s.rows("revenue_recognitions"):
        if rr.get("deal_id") in canc_deals or rr.get("deal_id") not in deals:
            continue
        ar_bast += max(0, i(rr.get("revenue")) - i(rr.get("contract_liability_cleared")))
    pen = 0
    for inv in s.rows("ar_invoices"):
        if inv["deal_id"] in canc_deals or inv.get("status") == "cancelled":
            continue
        pen += sum(i(x.get("amount")) for x in inv.get("items") or [] if x.get("is_penalty") and not x.get("waived"))
    cr = 0
    for r in _live_receipts(s):
        if r.get("deal_id") in canc_deals:
            continue
        sp = r.get("gl_split") or {}
        cr += i(sp.get("ar")) + i(sp.get("penalty"))
    return _tie(s, "G07", "1-1300", "Piutang", s.gl_dr("1-1300"), ar_bast + pen - cr)


@invariant("G08", "GL", "GL 1-2100/1-2200 = Σ perolehan / akumulasi aset tetap aktif; akumulasi = Σ jurnal susut", settled=True)
def g08(s):
    out = []
    live = [a for a in s.rows("fixed_assets") if a.get("status") != "disposed"]
    out += _tie(s, "G08", "1-2100", "Aset Tetap", s.gl_dr("1-2100"), sum(i(a.get("cost")) for a in live))
    out += _tie(s, "G08", "1-2200", "Akumulasi Susut", s.gl_cr("1-2200"), sum(i(a.get("accumulated_depreciation")) for a in live))
    dep = defaultdict(int)
    for d in s.rows("asset_depreciations"):
        dep[d.get("asset_id")] += i(d.get("amount"))
    for a in s.rows("fixed_assets"):
        if i(a.get("accumulated_depreciation")) != dep.get(a["id"], 0):
            out.append(V("G08", f"{a['id']}/acc", f"aset {a.get('code')} akumulasi={i(a.get('accumulated_depreciation')):,} ≠ Σ penyusutan={dep.get(a['id'], 0):,}"))
    return out


@invariant("G09", "GL", "GL 2-2100 Utang Bank = Σ sisa pokok fasilitas aktif; 2-1500 Utang Fee = Σ fee disetujui belum dibayar", settled=True)
def g09(s):
    out = []
    out += _tie(s, "G09", "2-2100", "Utang Bank", s.gl_cr("2-2100"), sum(i(l.get("outstanding_principal")) for l in s.rows("loans") if l.get("status") == "active"))
    pay = sum(i(f.get("amount_net")) - i(f.get("paid_amount")) for f in s.rows("marketing_fees") if f.get("status") in ("approved", "paid"))
    out += _tie(s, "G09", "2-1500", "Utang Marketing Fee", s.gl_cr("2-1500"), pay)
    return out


# ============================================================ kualitas jurnal
@invariant("G10", "Jurnal", "tiap jurnal seimbang (Σ debit = Σ kredit = total_*), baris valid (satu sisi, ≥0), minimal 2 baris")
def g10(s):
    out = []
    for je in s.rows("journal_entries"):
        ls = je.get("lines") or []
        d, c = sum(i(l.get("debit")) for l in ls), sum(i(l.get("credit")) for l in ls)
        tag = f"{je.get('entry_no')} ({je.get('source_type')})"
        if d != c or d != i(je.get("total_debit")) or c != i(je.get("total_credit")):
            out.append(V("G10", je["id"], f"jurnal {tag} tidak seimbang: Σdr={d:,} Σcr={c:,} total_dr={i(je.get('total_debit')):,} total_cr={i(je.get('total_credit')):,}", d - c))
        for l in ls:
            if i(l.get("debit")) < 0 or i(l.get("credit")) < 0 or (i(l.get("debit")) and i(l.get("credit"))):
                out.append(V("G10", f"{je['id']}/line", f"jurnal {tag} baris {l.get('account_code')} tidak valid dr={l.get('debit')} cr={l.get('credit')}"))
        if len(ls) < 2:
            out.append(V("G10", f"{je['id']}/n", f"jurnal {tag} hanya {len(ls)} baris"))
    return out


@invariant("G11", "Jurnal", "source_event jurnal unik (tak ada jurnal ganda dari satu peristiwa); entry_no unik", known="IN-03/PK-01")
def g11(s):
    out = []
    ev, no = defaultdict(list), defaultdict(list)
    for je in s.rows("journal_entries"):
        if je.get("source_event"):
            ev[je["source_event"]].append(je)
        no[je.get("entry_no")].append(je)
    for k, v in ev.items():
        if len(v) > 1:
            out.append(V("G11", f"ev/{k}", f"{len(v)} jurnal dengan source_event={k} ({', '.join(j['entry_no'] for j in v)})"))
    for k, v in no.items():
        if len(v) > 1:
            out.append(V("G11", f"no/{k}", f"nomor jurnal {k} dipakai {len(v)}×"))
    return out


@invariant("G12", "Jurnal", "kode akun jurnal ada di CoA organisasi", )
def g12(s):
    codes = {a["code"] for a in s.rows("accounts")}
    out, seen = [], set()
    for je in s.rows("journal_entries"):
        for l in je.get("lines") or []:
            c = l.get("account_code")
            if c not in codes and (je["id"], c) not in seen:
                seen.add((je["id"], c))
                out.append(V("G12", f"{je['id']}/{c}", f"jurnal {je.get('entry_no')} memakai akun {c} yang tidak ada di CoA"))
    return out


@invariant("G13", "Jurnal", "tiap kuitansi aktif yang membawa kas punya tepat satu jurnal 'receipt' (debit kas = Σ kas kuitansi)", settled=True, known="IN-03/GL-22")
def g13(s):
    out = []
    js = defaultdict(list)
    for je in s.rows("journal_entries"):
        if je.get("source_type") == "receipt":
            js[je.get("source_id")].append(je)
    for r in s.rows("receipts"):
        if r.get("status") == "void" or (r.get("funding") or "cash") != "cash":
            continue
        want = i(r.get("applied"))
        n = js.get(r["id"], [])
        if want > 0 and len(n) != 1:
            out.append(V("G13", r["id"], f"kuitansi {r.get('receipt_no')} (applied {want:,}) punya {len(n)} jurnal receipt (harus 1)"))
        elif len(n) == 1:
            dr = sum(i(l.get("debit")) for l in n[0]["lines"] if str(l.get("account_code", "")).startswith("1-1"))
            if dr != want and want > 0:
                out.append(V("G13", f"{r['id']}/amt", f"kuitansi {r.get('receipt_no')} applied={want:,} ≠ debit kas jurnal {n[0].get('entry_no')}={dr:,}", dr - want))
    return out


@invariant("G14", "Jurnal", "tiap kuitansi void punya tepat satu jurnal pembalik 'receipt_void'; pembalik hanya untuk kuitansi void", settled=True)
def g14(s):
    out = []
    vj = defaultdict(list)
    for je in s.rows("journal_entries"):
        if je.get("source_type") == "receipt_void":
            vj[je.get("source_id")].append(je)
    recs = s.idx("receipts")
    for r in s.rows("receipts"):
        if r.get("status") != "void" or (r.get("funding") or "cash") != "cash" or i(r.get("applied")) <= 0:
            continue
        if len(vj.get(r["id"], [])) != 1:
            out.append(V("G14", r["id"], f"kuitansi void {r.get('receipt_no')} punya {len(vj.get(r['id'], []))} jurnal pembalik (harus 1)"))
    for rid, js in vj.items():
        r = recs.get(rid)
        if r is None or r.get("status") != "void":
            out.append(V("G14", f"orphan/{rid}", f"jurnal pembalik {js[0].get('entry_no')} menunjuk kuitansi {'yang tidak ada' if r is None else 'yang tidak void'}"))
    return out


@invariant("G15", "Jurnal", "jurnal otomatis tidak yatim: sumber (kuitansi/titipan/tagihan AP/komisi/…) masih ada", settled=True, known="GL-05")
def g15(s):
    m = {"receipt": "receipts", "deposit": "customer_deposits", "commission": "commissions", "ap_bill": "ap_invoices",
         "cash_advance": "cash_advances", "fixed_asset": "fixed_assets", "loan": "loans", "marketing_fee": "marketing_fees",
         "revrec": "revenue_recognitions", "receipt_void": "receipts", "ap_payment_void": "ap_invoices"}
    out = []
    idxs = {k: s.idx(v) for k, v in m.items()}
    for je in s.rows("journal_entries"):
        st = je.get("source_type")
        if st in idxs and je.get("source_id") not in idxs[st]:
            out.append(V("G15", je["id"], f"jurnal {je.get('entry_no')} ({st}) menunjuk sumber {str(je.get('source_id'))[:8]} yang tidak ada (yatim)"))
    return out


@invariant("G16", "AP", "tiap tagihan AP disetujui punya jurnal pengakuan; saldo 2-1100 per tagihan = net − paid", settled=True, known="FN-05/FN-44")
def g16(s):
    out = []
    bal = defaultdict(int)
    cnt = defaultdict(int)
    for je in s.rows("journal_entries"):
        if je.get("source_type") in ("ap_bill", "ap_payment_void"):
            sid = je.get("source_id")
            for l in je.get("lines") or []:
                if l.get("account_code") == "2-1100":
                    bal[sid] += i(l.get("credit")) - i(l.get("debit"))
            cnt[sid] += 1
    for b in s.rows("ap_invoices"):
        if b.get("status") not in ("approved", "partial", "paid"):
            continue
        if cnt.get(b["id"], 0) == 0:
            out.append(V("G16", b["id"], f"tagihan {b.get('vendor')}/{b['id'][:6]} status {b.get('status')} (net {i(b.get('net')):,}) tanpa jurnal sama sekali"))
        elif bal.get(b["id"], 0) != i(b.get("net")) - i(b.get("paid")):
            out.append(V("G16", f"{b['id']}/bal", f"tagihan {b.get('vendor')}/{b['id'][:6]} saldo 2-1100 per-tagihan={bal.get(b['id'], 0):,} ≠ net−paid={i(b.get('net')) - i(b.get('paid')):,}", bal.get(b['id'], 0) - (i(b.get('net')) - i(b.get('paid')))))
    return out


# ============================================================ kas/bank
def _api_cash(s):
    if s.api is None:
        return None
    code, j = s.api("finance", "/cash-bank/position")
    if code != 200:
        return None
    return {a["gl_account_code"]: a for a in j["data"]["accounts"]}


@invariant("G17", "Kas", "saldo rekening kas/bank (API posisi kas) = Σ baris jurnal pada akun GL rekening itu", settled=True)
def g17(s):
    out = []
    api = _api_cash(s)
    if api is None:
        return out
    for code, a in api.items():
        glb = s.gl_dr(code)
        if i(a.get("balance")) != glb:
            out.append(V("G17", code, f"rekening {a.get('name')} ({code}) saldo layar={i(a.get('balance')):,} ≠ Σ jurnal={glb:,}", i(a.get('balance')) - glb))
    return out


@invariant("G18", "Kas", "saldo rekening kas/bank tidak negatif", settled=True, known="PK-06/GL-18", level="soft")
def g18(s):
    out = []
    for a in s.rows("bank_accounts"):
        if not a.get("gl_account_code"):
            continue
        b = s.gl_dr(a["gl_account_code"])
        if b < 0:
            out.append(V("G18", a["gl_account_code"], f"rekening {a.get('name')} saldo negatif {b:,}", b))
    return out


@invariant("G19", "Kas", "payments_out aktif tak melebihi tagihan & tiap pembayaran vendor aktif punya jurnal (Σ kredit kas)", settled=True)
def g19(s):
    out = []
    cashcr = defaultdict(int)
    for je in s.rows("journal_entries"):
        if je.get("source_type") == "ap_bill" and "Pembayaran" in (je.get("memo") or ""):
            cashcr[je.get("source_id")] += sum(i(l.get("credit")) for l in je["lines"] if str(l.get("account_code", "")).startswith("1-1"))
    for b in s.rows("ap_invoices"):
        pays = [p for p in s.grp("payments_out", "bill_id").get(b["id"], []) if p.get("status") != "void"]
        want = sum(i(p.get("cash_out", p.get("amount"))) for p in pays)
        if pays and cashcr.get(b["id"], 0) != want and b.get("status") in ("partial", "paid"):
            # pembatalan memakai jurnal terpisah (ap_payment_void) → kas bersih: kurangkan
            voidb = sum(i(l.get("debit")) for je in s.rows("journal_entries") if je.get("source_type") == "ap_payment_void" and je.get("source_id") == b["id"] for l in je["lines"] if str(l.get("account_code", "")).startswith("1-1"))
            if cashcr.get(b["id"], 0) - voidb != want:
                out.append(V("G19", b["id"], f"tagihan {b.get('vendor')}/{b['id'][:6]} kas keluar jurnal bersih={cashcr.get(b['id'], 0) - voidb:,} ≠ Σ cash_out pembayaran aktif={want:,}", cashcr.get(b['id'], 0) - voidb - want))
    return out


@invariant("G20", "Event", "tidak ada event pembukuan gagal permanen / tersangkut (pending >120 dtk, processing >120 dtk)", level="soft")
def g20(s):
    from datetime import datetime, timezone
    out = []
    now = datetime.now(timezone.utc)
    for e in s.rows("events"):
        if e.get("status") == "failed":
            out.append(V("G20", e["id"], f"event {e.get('type')} gagal permanen: {str(e.get('last_error'))[:120]}"))
        elif e.get("status") in ("pending", "processing"):
            try:
                age = (now - datetime.fromisoformat(e["created_at"])).total_seconds()
            except Exception:  # noqa: BLE001
                continue
            if age > 120 and not e.get("next_retry_at"):
                out.append(V("G20", e["id"], f"event {e.get('type')} berstatus {e.get('status')} sudah {int(age)} dtk"))
    return out


@invariant("G21", "Kas", "tiap jurnal yang menyentuh rekening kas/bank punya bukti kas (BKM/BKK) bernilai sama; tak ada bukti kas yatim", settled=True, known="GL-05")
def g21(s):
    out = []
    vouchers = defaultdict(list)
    for v in s.rows("cash_vouchers"):
        vouchers[v.get("journal_id")].append(v)
    jidx = s.idx("journal_entries")
    cashcodes = {a["gl_account_code"] for a in s.rows("bank_accounts") if a.get("gl_account_code")}
    for je in s.rows("journal_entries"):
        d = sum(i(l.get("debit")) for l in je["lines"] if l.get("account_code") in cashcodes)
        c = sum(i(l.get("credit")) for l in je["lines"] if l.get("account_code") in cashcodes)
        if d == 0 and c == 0:
            continue
        vs = vouchers.get(je["id"], [])
        if not vs:
            out.append(V("G21", je["id"], f"jurnal {je.get('entry_no')} ({je.get('source_type')}) menyentuh kas/bank (dr {d:,} cr {c:,}) tanpa bukti kas (BKM/BKK)"))
        else:
            tot = sum(i(v.get("amount")) for v in vs)
            if tot not in (abs(d - c), d + c, max(d, c)):
                out.append(V("G21", f"{je['id']}/amt", f"jurnal {je.get('entry_no')} kas dr {d:,} cr {c:,} ≠ bukti kas Σ {tot:,} ({len(vs)} dok)"))
    for jid, vs in vouchers.items():
        if jid and jid not in jidx:
            out.append(V("G21", f"{jid}/orph", f"bukti kas {vs[0].get('no')} ({vs[0].get('source_type')}) menunjuk jurnal yang tidak ada (yatim)"))
    return out
