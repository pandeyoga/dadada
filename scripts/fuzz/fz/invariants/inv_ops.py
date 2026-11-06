"""Invarian OPERASIONAL: status unit↔deal↔kontrak↔lead, salinan nama, PIC, nomor dokumen, yatim, progres."""
import re
from collections import defaultdict

from ..core import V, i, invariant

ACTIVE = ("reserved", "booked")            # menahan unit sebelum BAST
LIVE = ("reserved", "booked", "completed")
DEAD = ("cancelled", "canceled", "expired", "failed")


def _live_deals_by_unit(s):
    g = defaultdict(list)
    for d in s.rows("deals"):
        if d.get("status") in LIVE:
            g[d.get("unit_id")].append(d)
    return g


# ============================================================ unit ↔ deal
@invariant("O01", "Unit", "status unit konsisten dua arah dengan deal (reserved/booked/sold ⇒ deal sesuai; deal hidup ⇒ unit menunjuk balik)", known="KT-25")
def o01(s):
    out = []
    deals = s.idx("deals")
    for u in s.rows("units"):
        st, rid, bid = u.get("status"), u.get("reserved_by_deal"), u.get("booked_by_deal")
        tag = f"unit {u.get('code')}"
        if st == "available" and (rid or bid):
            out.append(V("O01", f"{u['id']}/avail", f"{tag} available tetapi masih menunjuk deal (reserved={rid} booked={bid})"))
        if st == "reserved":
            d = deals.get(rid)
            if not d or d.get("status") != "reserved":
                out.append(V("O01", f"{u['id']}/res", f"{tag} reserved tetapi reserved_by_deal → {'tidak ada' if not d else d.get('status')} (hold hantu)"))
        if st == "booked":
            d = deals.get(bid)
            if not d or d.get("status") not in ("booked", "completed"):
                out.append(V("O01", f"{u['id']}/book", f"{tag} booked tetapi booked_by_deal → {'tidak ada' if not d else d.get('status')}"))
        if st in ("sold", "handed_over"):
            d = deals.get(bid) or deals.get(u.get("sold_by_deal")) or deals.get(rid)
            if not d or (d.get("status") != "completed" and d.get("legal_stage") != "ajb"):
                out.append(V("O01", f"{u['id']}/sold", f"{tag} sold tetapi deal {'tidak ada' if not d else d.get('status') + '/' + str(d.get('legal_stage'))} (bukan completed/AJB)"))
    units = s.idx("units")
    for d in s.rows("deals"):
        u = units.get(d.get("unit_id"))
        if not u:
            out.append(V("O01", f"{d['id']}/nounit", f"deal {d['id'][:6]} unit_id tidak valid"))
            continue
        if d.get("status") == "reserved" and u.get("reserved_by_deal") != d["id"]:
            out.append(V("O01", f"{d['id']}/rback", f"deal reserved {d['id'][:6]} tetapi unit {u.get('code')} tidak menunjuk balik"))
        if d.get("status") in ("booked", "completed") and d["id"] not in (u.get("booked_by_deal"), u.get("sold_by_deal")):
            out.append(V("O01", f"{d['id']}/bback", f"deal {d.get('status')} {d['id'][:6]} tetapi unit {u.get('code')} tidak menunjuk balik (booked_by={u.get('booked_by_deal')})"))
    return out


@invariant("O02", "Unit", "satu unit hanya boleh punya satu deal hidup (reserved/booked/completed)", known="KT-18")
def o02(s):
    out = []
    for uid, ds in _live_deals_by_unit(s).items():
        if len(ds) > 1:
            out.append(V("O02", uid, f"unit {ds[0].get('unit_code')} punya {len(ds)} deal hidup: " + ", ".join(f"{d['id'][:6]}:{d['status']}" for d in ds)))
    return out


@invariant("O03", "Unit", "unit available bersih: tanpa deal hidup & tanpa tautan basi (deal_id/lead_id/customer_id/lead_name/payment_status)", known="KT-25")
def o03(s):
    out = []
    live = _live_deals_by_unit(s)
    for u in s.rows("units"):
        if u.get("status") != "available":
            continue
        if live.get(u["id"]):
            out.append(V("O03", f"{u['id']}/live", f"unit {u.get('code')} available padahal ada deal hidup {live[u['id']][0]['id'][:6]}:{live[u['id']][0]['status']}"))
        stale = {k: u.get(k) for k in ("deal_id", "lead_id", "customer_id", "lead_name", "contract_id") if u.get(k)}
        if stale or u.get("payment_status") not in (None, "none"):
            out.append(V("O03", f"{u['id']}/stale", f"unit {u.get('code')} available tetapi menyimpan tautan basi {stale} payment_status={u.get('payment_status')}"))
    return out


@invariant("O04", "Unit", "payment_status unit = fungsi status AR deal hidupnya (none/booking_fee/partial/paid_off)")
def o04(s):
    out = []
    invs = s.idx("ar_invoices", "deal_id")
    deals = s.idx("deals")
    for u in s.rows("units"):
        if u.get("status") not in ("booked", "sold", "reserved", "handed_over"):
            continue
        did = u.get("booked_by_deal") or u.get("sold_by_deal") or u.get("reserved_by_deal")
        d = deals.get(did)
        inv = invs.get(did)
        if not d or not inv or inv.get("status") == "cancelled":
            continue
        if u.get("status") in ("sold", "handed_over"):
            exp = "paid_off"
        else:
            exp = "paid_off" if inv.get("status") == "paid" else ("partial" if i(inv.get("paid")) > 0 else "booking_fee")
        if u.get("payment_status") != exp and not (exp == "booking_fee" and u.get("payment_status") == "none" and i(inv.get("paid")) == 0):
            out.append(V("O04", u["id"], f"unit {u.get('code')} payment_status={u.get('payment_status')} seharusnya {exp} (AR {inv.get('status')} paid={i(inv.get('paid')):,})"))
    return out


@invariant("O05", "Deal", "deal hidup punya tepat satu AR (kecuali draft/sebelum booking) dan satu kontrak aktif paling banyak", known="KT-02")
def o05(s):
    out = []
    ar = s.grp("ar_invoices", "deal_id")
    ct = s.grp("contracts", "deal_id")
    for d in s.rows("deals"):
        if len(ar.get(d["id"], [])) > 1:
            out.append(V("O05", f"{d['id']}/ar", f"deal {d['id'][:6]} punya {len(ar[d['id']])} AR"))
        live_ct = [c for c in ct.get(d["id"], []) if c.get("state") not in ("cancelled", "void", "canceled")]
        if len(live_ct) > 1:
            out.append(V("O05", f"{d['id']}/ct", f"deal {d['id'][:6]} punya {len(live_ct)} kontrak hidup ({', '.join(c.get('number', '?') for c in live_ct)})"))
        if d.get("status") in ("booked", "completed") and not ar.get(d["id"]):
            out.append(V("O05", f"{d['id']}/noar", f"deal {d.get('status')} {d['id'][:6]} tanpa AR"))
    return out


@invariant("O06", "Kontrak", "status kontrak selaras deal: deal batal ⇒ kontrak batal & AR batal; kontrak aktif ⇒ deal booked/completed", known="KT-19")
def o06(s):
    out = []
    deals = s.idx("deals")
    invs = s.idx("ar_invoices", "deal_id")
    for c in s.rows("contracts"):
        d = deals.get(c.get("deal_id"))
        if not d:
            out.append(V("O06", f"{c['id']}/orph", f"kontrak {c.get('number')} → deal tidak ada (yatim)"))
            continue
        if d.get("status") in DEAD and c.get("state") not in ("cancelled", "void", "canceled"):
            out.append(V("O06", f"{c['id']}/dead", f"kontrak {c.get('number')} state={c.get('state')} padahal deal {d.get('status')}"))
        if c.get("state") == "active" and d.get("status") not in ("booked", "completed"):
            out.append(V("O06", f"{c['id']}/act", f"kontrak {c.get('number')} aktif padahal deal {d.get('status')}"))
        if c.get("unit_id") != d.get("unit_id") or c.get("lead_id") != d.get("lead_id"):
            out.append(V("O06", f"{c['id']}/link", f"kontrak {c.get('number')} unit/lead tidak sama dengan deal"))
        inv = invs.get(d["id"])
        if c.get("state") == "active" and inv and inv.get("status") == "cancelled":
            out.append(V("O06", f"{c['id']}/arx", f"kontrak {c.get('number')} aktif padahal AR batal"))
    return out


@invariant("O07", "Lead", "satu pembeli per lead; pembeli menunjuk lead yang ada; kontrak menunjuk pembeli milik lead yang sama", known="KT-02")
def o07(s):
    out = []
    cust = s.grp("customers", "lead_id")
    leads = s.idx("leads")
    for lid, cs in cust.items():
        if lid and len(cs) > 1:
            out.append(V("O07", f"{lid}/dup", f"lead {str(lid)[:6]} punya {len(cs)} pembeli"))
        if lid and lid not in leads:
            out.append(V("O07", f"{lid}/orph", f"pembeli {cs[0].get('name')} → lead {str(lid)[:6]} tidak ada"))
    custs = s.idx("customers")
    for c in s.rows("contracts"):
        cu = custs.get(c.get("customer_id"))
        if c.get("customer_id") and not cu:
            out.append(V("O07", f"{c['id']}/nocust", f"kontrak {c.get('number')} → customer tidak ada"))
        elif cu and c.get("lead_id") and cu.get("lead_id") and cu["lead_id"] != c["lead_id"]:
            out.append(V("O07", f"{c['id']}/lead", f"kontrak {c.get('number')} lead ≠ lead pembelinya"))
    return out


@invariant("O08", "Lead", "tahap lead selaras deal: lead dgn deal hidup ⇒ booking/won; lead 'booking' tanpa deal hidup = basi", known="KT-13/KT-19/KT-25")
def o08(s):
    out = []
    live = defaultdict(list)
    alld = defaultdict(list)
    for d in s.rows("deals"):
        alld[d.get("lead_id")].append(d)
        if d.get("status") in LIVE:
            live[d.get("lead_id")].append(d)
    for l in s.rows("leads"):
        st = l.get("stage")
        if live.get(l["id"]) and st not in ("booking", "won"):
            out.append(V("O08", f"{l['id']}/live", f"lead {l.get('name')} tahap '{st}' padahal punya deal hidup {live[l['id']][0]['status']}"))
        if st == "booking" and not live.get(l["id"]) and not any(d.get("status") in ("draft",) for d in alld.get(l["id"], [])) and alld.get(l["id"]):
            out.append(V("O08", f"{l['id']}/stale", f"lead {l.get('name')} masih 'booking' padahal semua deal-nya {sorted({d.get('status') for d in alld[l['id']]})}"))
        if st == "won" and not live.get(l["id"]):
            out.append(V("O08", f"{l['id']}/won", f"lead {l.get('name')} 'won' tanpa deal hidup (deal: {sorted({d.get('status') for d in alld.get(l['id'], [])}) or 'tidak ada'})"))
    return out


# ============================================================ salinan nama / PIC
MASTER = {"lead": ("leads", "name"), "unit": ("units", "code"), "customer": ("customers", "name"),
          "project": ("projects", "name"), "contract": ("contracts", "number"), "po": ("purchase_orders", "po_number"),
          "spk": ("spk", "spk_number"), "vendor": ("vendors", "name")}
FIELD = {"lead": "lead_name", "unit": "unit_code", "customer": "customer_name", "project": "project_name",
         "contract": "contract_number", "po": "po_number", "spk": "spk_number", "vendor": "vendor_name"}
# koleksi 'tampilan hidup' (harus selalu mengikuti master). Selain ini = dokumen/foto-saat-itu → hanya indikator.
LIVE_VIEW = {"deals", "units", "ar_invoices", "contracts", "commissions", "financing_apps", "customers", "tasks",
             "build_schedules", "materials", "purchase_orders", "material_requisitions", "unit_handovers"}


@invariant("O09", "Salinan", "salinan nama/kode (lead_name, unit_code, customer_name, project_name, …) pada tampilan hidup sama dengan master", known="KT-15")
def o09(s):
    out = []
    for coll in s.db.list_collection_names():
        if coll in ("journal_entries", "events", "audit_logs", "activities", "notifications", "file_blobs", "files",
                    "messages", "conversations", "documents"):
            continue
        rows = s.rows(coll)
        if not rows:
            continue
        sample = rows[0]
        for ent, fname in FIELD.items():
            idf = f"{ent}_id"
            if fname == "po_number" and coll in ("purchase_orders",):
                continue
            mcoll, mfield = MASTER[ent]
            if mcoll == coll:
                continue
            if not any(fname in r and idf in r for r in rows[:50]):
                continue
            m = s.idx(mcoll)
            for r in rows:
                mid, copy = r.get(idf), r.get(fname)
                if not mid or copy in (None, ""):
                    continue
                mrow = m.get(mid)
                if not mrow:
                    continue    # yatim — dicek O13
                if str(mrow.get(mfield)) != str(copy):
                    lvl = "live" if coll in LIVE_VIEW else "snapshot"
                    out.append(V("O09", f"{coll}/{r.get('id')}/{fname}",
                                 f"[{lvl}] {coll}.{fname}='{copy}' ≠ master {mcoll}.{mfield}='{mrow.get(mfield)}'" +
                                 ("" if lvl == "live" else " (dokumen/foto-saat-itu: indikator saja)")))
    return out


@invariant("O10", "Salinan", "pembeli ↔ lead: nama & telepon pembeli sama dengan lead asalnya (indikator: pembeli yang diedit sendiri sah berbeda — aturan aman KT-15)", known="KT-15", level="soft")
def o10(s):
    out = []
    leads = s.idx("leads")
    for c in s.rows("customers"):
        l = leads.get(c.get("lead_id"))
        if not l:
            continue
        for f in ("name", "phone"):
            if (c.get(f) or "") != (l.get(f) or ""):
                out.append(V("O10", f"{c['id']}/{f}", f"pembeli {c.get('name')}: {f}='{c.get(f)}' ≠ lead {f}='{l.get(f)}'"))
    return out


@invariant("O11", "PIC", "PIC (assigned_to) lead = PIC deal hidup/kontrak/AR/komisi turunan lead itu", known="KT-16")
def o11(s):
    out = []
    leads = s.idx("leads")
    deals = s.idx("deals")
    for coll in ("deals", "contracts", "ar_invoices"):
        for r in s.rows(coll):
            l = leads.get(r.get("lead_id"))
            d = deals.get(r.get("deal_id")) if coll != "deals" else r
            if not l or (d and d.get("status") in DEAD):
                continue
            if r.get("assigned_to") and l.get("assigned_to") and r["assigned_to"] != l["assigned_to"]:
                out.append(V("O11", f"{coll}/{r['id']}", f"{coll} {str(r['id'])[:6]} assigned_to={r['assigned_to']} ≠ PIC lead {l['assigned_to']}"))
    return out


# ============================================================ nomor dokumen
NUMBERED = [("contracts", "number"), ("receipts", "receipt_no"), ("journal_entries", "entry_no"),
            ("purchase_orders", "po_number"), ("grns", "grn_number"), ("cash_vouchers", "no"),
            ("cancellations", "number"), ("material_requisitions", "req_number"), ("fund_requests", "no"),
            ("cash_advances", "no"), ("unit_handovers", "number"), ("marketing_fees", "no"),
            ("pdc_instruments", "no"), ("progress_claims", "claim_number"), ("spk", "number"), ("loans", "no"),
            ("faktur_pajak", "number")]


@invariant("O12", "Nomor", "nomor dokumen unik per koleksi", known="KT-24")
def o12(s):
    out = []
    for coll, f in NUMBERED:
        g = defaultdict(list)
        for r in s.rows(coll):
            if r.get(f):
                g[r[f]].append(r)
        for n, rs in g.items():
            if len(rs) > 1:
                out.append(V("O12", f"{coll}/{n}", f"{coll}.{f}='{n}' dipakai {len(rs)} dokumen"))
    return out


@invariant("O13", "Nomor", "nomor dokumen berurutan tanpa lubang per (awalan, tahun) dan counter ≥ nomor terbesar", known="KT-02", level="soft")
def o13(s):
    out = []
    pat = re.compile(r"^(.*?)/(\d{4})/(\d+)$")
    for coll, f in NUMBERED:
        if coll in ("journal_entries",):
            continue
        g = defaultdict(list)
        for r in s.rows(coll):
            m = pat.match(str(r.get(f) or ""))
            if m:
                g[(m.group(1), m.group(2))].append(int(m.group(3)))
        for (pre, yr), nums in g.items():
            nums = sorted(set(nums))
            miss = [n for n in range(nums[0], nums[-1] + 1) if n not in nums]
            if miss and len(miss) <= 50:
                out.append(V("O13", f"{coll}/{pre}/{yr}", f"{coll} {pre}/{yr}: lubang nomor {miss[:6]} (rentang {nums[0]}–{nums[-1]})", len(miss)))
    return out


# ============================================================ yatim (FK)
FK = [("deals", "lead_id", "leads"), ("deals", "unit_id", "units"), ("receipts", "deal_id", "deals"),
      ("ar_invoices", "deal_id", "deals"), ("contracts", "deal_id", "deals"), ("contract_liabilities", "deal_id", "deals"),
      ("customer_deposits", "deal_id", "deals"), ("commissions", "deal_id", "deals"), ("financing_apps", "deal_id", "deals"),
      ("cancellations", "contract_id", "contracts"), ("customers", "lead_id", "leads"), ("grns", "po_id", "purchase_orders"),
      ("material_txns", "material_id", "materials"), ("materials", "project_id", "projects"),
      ("payments_out", "bill_id", "ap_invoices"), ("appointments", "lead_id", "leads"), ("unit_handovers", "deal_id", "deals"),
      ("tax_records", "deal_id", "deals"), ("faktur_pajak", "deal_id", "deals"), ("marketing_fees", "deal_id", "deals"),
      ("revenue_recognitions", "deal_id", "deals"), ("units", "booked_by_deal", "deals"), ("units", "reserved_by_deal", "deals"),
      ("units", "project_id", "projects"), ("build_schedules", "unit_id", "units"), ("build_items", "schedule_id", "build_schedules"),
      ("pdc_instruments", "deal_id", "deals"), ("bank_transactions", "account_id", "bank_accounts"),
      ("cash_vouchers", "cash_account_id", "bank_accounts"), ("commissions", "unit_id", "units")]


@invariant("O14", "Yatim", "tidak ada baris anak yang induknya tidak ada (FK logis)", known="GL-05/KT-02")
def o14(s):
    out = []
    for coll, f, mcoll in FK:
        m = s.idx(mcoll)
        for r in s.rows(coll):
            v = r.get(f)
            if v and v not in m:
                out.append(V("O14", f"{coll}.{f}/{r.get('id')}", f"{coll} {str(r.get('id'))[:8]}: {f}={str(v)[:8]} → {mcoll} tidak ada (yatim)"))
    return out


@invariant("O15", "Yatim", "tugas terbuka & agenda mendatang tidak menunjuk entitas yang dibatalkan/dihapus", known="KT-29", level="soft")
def o15(s):
    out = []
    ent = {"lead": ("leads", None), "deal": ("deals", DEAD), "contract": ("contracts", ("cancelled",)), "unit": ("units", None),
           "customer": ("customers", None)}
    for t in s.rows("tasks"):
        if t.get("status") in ("done", "cancelled", "closed", "completed"):
            continue
        et = t.get("related_entity_type")
        if et in ent:
            coll, dead = ent[et]
            r = s.idx(coll).get(t.get("related_entity_id"))
            if r is None:
                out.append(V("O15", t["id"], f"tugas terbuka '{str(t.get('title'))[:50]}' → {et} {str(t.get('related_entity_id'))[:8]} sudah tidak ada"))
            elif dead and (r.get("status") in dead or r.get("state") in dead):
                out.append(V("O15", t["id"], f"tugas terbuka '{str(t.get('title'))[:50]}' → {et} berstatus batal"))
    return out


@invariant("O16", "Komisi", "komisi/marketing fee/pajak tidak aktif untuk deal yang dibatalkan (pending/approved/accrual)", known="PK-12/GL-23")
def o16(s):
    out = []
    deals = s.idx("deals")
    for c in s.rows("commissions"):
        d = deals.get(c.get("deal_id"))
        if d and d.get("status") in DEAD and c.get("status") in ("pending", "approved"):
            out.append(V("O16", f"com/{c['id']}", f"komisi {c.get('unit_code')} {c.get('status')} Rp {i(c.get('amount')):,} untuk deal {d.get('status')}"))
    for f in s.rows("marketing_fees"):
        d = deals.get(f.get("deal_id"))
        if d and d.get("status") in DEAD and f.get("status") in ("draft", "submitted", "approved"):
            out.append(V("O16", f"mf/{f['id']}", f"marketing fee {f.get('no')} {f.get('status')} untuk deal {d.get('status')}"))
    for t in s.rows("tax_records"):
        d = deals.get(t.get("deal_id"))
        if d and d.get("status") in DEAD and t.get("status") in ("pending", "reported"):
            out.append(V("O16", f"tax/{t['id']}", f"catatan pajak {t.get('type')} {t.get('status')} untuk deal {d.get('status')}"))
    return out


@invariant("O17", "Kupon", "coupons.used_count = jumlah deal hidup yang memakai kupon itu; tak melebihi kuota", known="KT-08")
def o17(s):
    out = []
    use = defaultdict(int)
    for d in s.rows("deals"):
        cid = d.get("coupon_id")
        if cid and d.get("status") in LIVE:
            use[cid] += 1
    for c in s.rows("coupons"):
        if i(c.get("used_count")) != use.get(c["id"], 0):
            out.append(V("O17", c["id"], f"kupon {c.get('code')} used_count={i(c.get('used_count'))} ≠ deal hidup pemakai={use.get(c['id'], 0)}", i(c.get('used_count')) - use.get(c['id'], 0)))
        if c.get("quota_total") and i(c.get("used_count")) > i(c.get("quota_total")):
            out.append(V("O17", f"{c['id']}/q", f"kupon {c.get('code')} terpakai {i(c.get('used_count'))} > kuota {i(c.get('quota_total'))}"))
    return out


@invariant("O18", "Handover", "unit yang BAST-nya terbit ('issued') ⇒ deal completed & unit sold; unit sold ⇒ ada pengakuan pendapatan", known="KT-01/GL-07")
def o18(s):
    out = []
    deals, units = s.idx("deals"), s.idx("units")
    rr = s.idx("revenue_recognitions", "deal_id")
    for h in s.rows("unit_handovers"):
        if h.get("state") != "issued":
            continue
        d = deals.get(h.get("deal_id"))
        u = units.get(h.get("unit_id"))
        if d and d.get("status") not in ("completed",):
            out.append(V("O18", f"{h['id']}/deal", f"BAST {h.get('number')} terbit tetapi deal {d.get('status')}"))
        if u and u.get("status") not in ("sold", "handed_over"):
            out.append(V("O18", f"{h['id']}/unit", f"BAST {h.get('number')} terbit tetapi unit {u.get('code')} {u.get('status')}"))
    for d in s.rows("deals"):
        if d.get("status") == "completed" and d["id"] not in rr and d.get("legal_stage") != "ajb":
            out.append(V("O18", f"{d['id']}/rr", f"deal completed {d['id'][:6]} tanpa pengakuan pendapatan"))
    return out


@invariant("O19", "Progres", "progres jadwal unit = Σ bobot langkah selesai ÷ Σ bobot; unit.construction_progress = progres jadwal")
def o19(s):
    out = []
    items = s.grp("build_items", "schedule_id")
    units = s.idx("units")
    for sc in s.rows("build_schedules"):
        its = items.get(sc["id"], [])
        if not its:
            continue
        tw = sum(float(x.get("weight") or 0) for x in its) or 1
        dw = sum(float(x.get("weight") or 0) for x in its if x.get("status") == "done")
        exp = round(dw / tw * 100, 1)
        if abs(float(sc.get("progress") or 0) - exp) > 0.11:
            out.append(V("O19", f"{sc['id']}/prog", f"jadwal unit {sc.get('unit_code')} progress={sc.get('progress')} ≠ dari langkah={exp}", exp))
        u = units.get(sc.get("unit_id"))
        if u and int(u.get("construction_progress") or 0) != int(round(float(sc.get("progress") or 0))):
            out.append(V("O19", f"{sc['id']}/unit", f"unit {u.get('code')} construction_progress={u.get('construction_progress')} ≠ jadwal {sc.get('progress')}"))
    return out


# ============================================================ yatim otomatis (FK ditemukan dari nama field)
AUTO_FK = {"deal_id": "deals", "lead_id": "leads", "unit_id": "units", "contract_id": "contracts", "customer_id": "customers",
           "project_id": "projects", "receipt_id": "receipts", "po_id": "purchase_orders", "grn_id": "grns", "bill_id": "ap_invoices",
           "material_id": "materials", "spk_id": "spk", "vendor_id": "vendors", "cancellation_id": "cancellations"}
SKIP_COLL = {"journal_entries", "events", "audit_logs", "activities", "notifications", "file_blobs", "files", "messages",
             "conversations", "documents", "doc_history", "counters", "wa_outbox", "capture_events", "conversion_events", "deleted_archive"}


@invariant("O20", "Yatim", "FK otomatis: setiap kolom *_id (deal/lead/unit/contract/customer/project/receipt/po/…) di koleksi mana pun menunjuk baris yang ada",
           known="GL-05")
def o20(s):
    out = []
    names = set(s.db.list_collection_names())
    for coll in sorted(names):
        if coll in SKIP_COLL or coll.startswith("system."):
            continue
        rows = s.rows(coll)
        if not rows:
            continue
        fields = set()
        for r in rows[:100]:
            fields.update(k for k in r if k in AUTO_FK)
        for f in fields:
            mc = AUTO_FK[f]
            if mc == coll or mc not in names:
                continue
            m = s.idx(mc)
            seen = set()
            for r in rows:
                v = r.get(f)
                if v and isinstance(v, str) and v not in m and v not in seen:
                    seen.add(v)
                    out.append(V("O20", f"{coll}.{f}/{v}", f"{coll}.{f} → {mc} {v[:8]} tidak ada (yatim; {sum(1 for x in rows if x.get(f) == v)} baris)"))
    return out
