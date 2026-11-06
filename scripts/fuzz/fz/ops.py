"""Operasi acak. Tiap operasi = (gen, run). gen(w, rng, focus) → args (JSON, hanya label simbolik + angka acak) atau None bila
tak berlaku; run(w, args) → {ok, code, note}. Args disimpan → urutan operasi bisa DIPUTAR ULANG (shrink/reproduksi)."""
import datetime
import random

OPS = {}


def reg(name, weight, gen, run, tags=()):
    OPS[name] = {"name": name, "w": weight, "gen": gen, "run": run, "tags": tags}


def res(code, j, ok=None, note=""):
    ok = (code == 200) if ok is None else ok
    d = (j or {}).get("detail") if isinstance(j, dict) else None
    return {"ok": ok, "code": code, "note": ((note + ": " if note and d else note) + (str(d)[:160] if d else ""))}


def skip(why):
    return {"ok": False, "code": -1, "note": "SKIP " + why}


def pick(w, rng, kind, pred=None, focus=None, prefer_new=0.5):
    if focus and focus.get(kind) and w.get(focus[kind]):
        return focus[kind]
    labs = w.of_kind(kind)
    if pred:
        labs = [x for x in labs if pred(w.get(x))]
    if not labs:
        return None
    if prefer_new and rng.random() < prefer_new:
        return labs[-1]
    return rng.choice(labs)


def pref(w, rng, kind, pred, focus=None, p=0.85, base=None):
    """Pilih entitas yang memenuhi `pred` (keadaan 'siap') dengan peluang p; selain itu entitas apa pun (uji transisi tak sah)."""
    if focus and focus.get(kind) and w.get(focus[kind]):
        return focus[kind]
    ok = pick(w, rng, kind, (lambda e: pred(e) and (base is None or base(e))), None, 0.5)
    if ok and rng.random() < p:
        return ok
    return pick(w, rng, kind, base, None, 0.4)


def ent(w, lab, kind=None):
    e = w.get(lab) if lab else None
    return e if e and (kind is None or e["kind"] == kind) else None


def pic_role(w, lead_id=None, deal_id=None):
    """Peran sales yang sedang jadi PIC lead/deal (setelah reassign, sales lain ditolak 'bukan lead Anda')."""
    em = None
    if deal_id:
        d = w.one("deals", {"id": deal_id})
        em = (d or {}).get("assigned_to")
    if not em and lead_id:
        l = w.one("leads", {"id": lead_id})
        em = (l or {}).get("assigned_to")
    r = (em or "sales@").split("@")[0]
    return r if r in ("sales", "sales2", "marketing") else "sales"


def amt(rng, lo=1_000_000, hi=250_000_000, step=500_000):
    return rng.randrange(lo, hi, step)


# ====================================================================== LEAD
def lead_new_gen(w, rng, f=None):
    return {"src": rng.choice(["walk_in", "manual", "instagram", "referral"])}


def lead_new_run(w, a):
    n = w.cnt.get("lead", 0) + 1
    code, j = w.call("sales", "POST", "/leads", {"name": f"AUDIT-FZ Lead {w.tag} {n}", "phone": w.phone(), "source": a["src"]})
    if code != 200:
        return res(code, j)
    d = j["data"]
    w.new("lead", id=d["id"], name=d["name"], phone=d["phone"], pic="sales@sipro.co.id")
    return res(code, j)


def lead_contact_gen(w, rng, f=None):
    l = pick(w, rng, "lead", focus=f)
    return {"lead": l} if l else None


def lead_contact_run(w, a):
    e = ent(w, a["lead"])
    if not e:
        return skip("lead")
    return res(*w.call(pic_role(w, e["id"]), "POST", f"/leads/{e['id']}/first-contact"))


def appt_gen(w, rng, f=None):
    l = pick(w, rng, "lead", focus=f)
    return {"lead": l, "d": rng.randrange(3, 60)} if l else None


def appt_run(w, a):
    e = ent(w, a["lead"])
    if not e:
        return skip("lead")
    when = (datetime.datetime.now() + datetime.timedelta(days=a["d"])).strftime("%Y-%m-%dT10:00:00")
    return res(*w.call(pic_role(w, e["id"]), "POST", "/appointments", {"lead_id": e["id"], "title": "AUDIT-FZ survei", "scheduled_at": when, "type": "survey"}))


def edit_lead_gen(w, rng, f=None):
    l = pick(w, rng, "lead", focus=f)
    return {"lead": l, "name": f"AUDIT-FZ Lead Ubah {rng.randrange(1000, 9999)}", "ph": rng.random() < 0.5} if l else None


def edit_lead_run(w, a):
    e = ent(w, a["lead"])
    if not e:
        return skip("lead")
    body = {"name": a["name"]}
    if a["ph"]:
        body["phone"] = w.phone()
    return res(*w.call(pic_role(w, e["id"]), "PUT", f"/leads/{e['id']}", body))


def reassign_gen(w, rng, f=None):
    l = pick(w, rng, "lead", focus=f)
    return {"lead": l, "to": rng.choice(["sales@sipro.co.id", "sales2@sipro.co.id", "marketing@sipro.co.id"])} if l else None


def reassign_run(w, a):
    e = ent(w, a["lead"])
    if not e:
        return skip("lead")
    return res(*w.call("manager", "POST", f"/leads/{e['id']}/assign", {"assigned_to": a["to"]}))


def lead_stage_gen(w, rng, f=None):
    l = pick(w, rng, "lead", focus=f)
    return {"lead": l, "stage": rng.choice(["nurturing", "appointment", "recycle", "lost", "acquisition"])} if l else None


def lead_stage_run(w, a):
    e = ent(w, a["lead"])
    if not e:
        return skip("lead")
    return res(*w.call("manager", "POST", f"/leads/{e['id']}/stage/override", {"stage": a["stage"], "reason": "AUDIT-FZ override tahap uji"}))


# ====================================================================== DEAL
SCHEMES = ["cash_bertahap_3x", "cash_bertahap", "cash_keras", "kpr", "kpr_dp20", "telat", "telat", "kpr", "kpr_dp20"]


def reserve_gen(w, rng, f=None):
    l = pick(w, rng, "lead", focus=f, prefer_new=0.7)
    if not l:
        return None
    if f and f.get("unit"):
        u = f["unit"]
    else:
        used = {e.get("unit") for e in w.ent.values() if e["kind"] == "deal" and not e.get("dead")}
        free = [k for k in w.of_kind("unit") if k not in used]
        u = rng.choice(free) if free and rng.random() < 0.9 else rng.choice(w.of_kind("unit"))
    return {"lead": l, "unit": u, "bf": rng.choice([0, 5_000_000, 5_000_000, 10_000_000, 25_000_000]),
            "scheme": f.get("scheme") if f and f.get("scheme") else rng.choice(SCHEMES)}


def reserve_run(w, a):
    le, un = ent(w, a["lead"]), ent(w, a["unit"])
    if not le or not un:
        return skip("lead/unit")
    code, j = w.call(pic_role(w, le["id"]), "POST", "/deals/reserve", {"unit_id": un["id"], "lead_id": le["id"], "booking_fee": a["bf"],
                                                         "scheme_id": w.schemes.get(a["scheme"]), "notes": "AUDIT-FZ"})
    if code == 200:
        w.new("deal", id=j["data"]["id"], lead=a["lead"], unit=a["unit"], scheme=a["scheme"], bf=a["bf"])
    return res(code, j)


def bf_gen(w, rng, f=None):
    d = pref(w, rng, "deal", lambda e: not e.get("dead") and not e.get("booked") and e.get("bf"), focus=f, base=lambda e: e.get("bf"))
    if not d:
        return None
    bf = w.get(d)["bf"]
    return {"deal": d, "amount": rng.choice([bf, bf, max(1_000_000, bf // 2), bf + 1_000_000])}


def bf_run(w, a):
    e = ent(w, a["deal"])
    if not e:
        return skip("deal")
    fid = w.proof("deal", e["id"])
    if not fid:
        return skip("upload")
    code, j = w.call("finance", "POST", f"/booking-fee/deals/{e['id']}/pay",
                     {"amount": a["amount"], "method": "transfer", "proof_file_ids": [fid]})
    if code == 200 and a["amount"] >= (e.get("bf") or 0):
        e["bf_paid"] = True
    return res(code, j)


def book_gen(w, rng, f=None):
    d = pref(w, rng, "deal", lambda e: e.get("booked") and not e.get("dead"), focus=f)
    return {"deal": d} if d else None


def book_run(w, a):
    e = ent(w, a["deal"])
    if not e:
        return skip("deal")
    code, j = w.call(pic_role(w, None, e["id"]), "POST", f"/deals/{e['id']}/book", {})
    if code == 200:
        e["booked"] = True
    return res(code, j)


def convert_gen(w, rng, f=None):
    d = pref(w, rng, "deal", lambda e: e.get("booked") and not e.get("dead"), focus=f)
    return {"deal": d} if d else None


def convert_run(w, a):
    e = ent(w, a["deal"])
    if not e:
        return skip("deal")
    code, j = w.call(pic_role(w, None, e["id"]), "POST", f"/deals/{e['id']}/convert", {})
    if code == 200:
        e["booked"] = True
        d = j["data"]
        e["contract_id"] = (d.get("contract") or {}).get("id")
        e["customer_id"] = (d.get("customer") or {}).get("id")
    return res(code, j)


def _contract(w, e):
    if e.get("contract_id"):
        return e["contract_id"]
    c = w.one("contracts", {"deal_id": e["id"]})
    if c:
        e["contract_id"] = c["id"]
    return e.get("contract_id")


def activate_gen(w, rng, f=None):
    d = pref(w, rng, "deal", lambda e: e.get("contract_id") and not e.get("dead"), focus=f)
    return {"deal": d} if d else None


def activate_run(w, a):
    e = ent(w, a["deal"])
    cid = _contract(w, e) if e else None
    if not cid:
        return skip("kontrak")
    return res(*w.call("manager", "POST", f"/contracts/{cid}/activate"))


def cancel_deal_gen(w, rng, f=None):
    d = pick(w, rng, "deal", lambda e: not e.get("dead"), focus=f, prefer_new=0.2)
    return {"deal": d, "refund": rng.choice([None, "full", "none"])} if d else None


def cancel_deal_run(w, a):
    e = ent(w, a["deal"])
    if not e:
        return skip("deal")
    body = {"reason": "AUDIT-FZ pembatalan uji fuzz"}
    if a["refund"]:
        body["refund_mode"] = a["refund"]
    code, j = w.call("manager", "POST", f"/deals/{e['id']}/cancel", body)
    if code == 200:
        e["dead"] = True
    return res(code, j)


def force_delete_gen(w, rng, f=None):
    d = pick(w, rng, "deal", focus=f, prefer_new=0.2)
    return {"deal": d} if d else None


def force_delete_run(w, a):
    e = ent(w, a["deal"])
    if not e:
        return skip("deal")
    code, j = w.call("owner", "DELETE", f"/deals/{e['id']}", params={"reason": "AUDIT-FZ hapus paksa uji fuzz"})
    if code == 200:
        e["dead"] = True
        e["deleted"] = True
    return res(code, j)


def scheme_change_gen(w, rng, f=None):
    d = pref(w, rng, "deal", lambda e: e.get("contract_id") and not e.get("dead"), focus=f)
    return {"deal": d, "scheme": rng.choice(SCHEMES), "mode": rng.choice(["payment-schemes", "scheme"])} if d else None


def scheme_change_run(w, a):
    e = ent(w, a["deal"])
    cid = _contract(w, e) if e else None
    if not cid:
        return skip("kontrak")
    if a["mode"] == "payment-schemes":
        return res(*w.call("manager", "POST", f"/payment-schemes/contracts/{cid}",
                           {"scheme_id": w.schemes[a["scheme"]], "reason": "AUDIT-FZ ganti skema uji fuzz"}))
    code, j = w.call("manager", "POST", f"/contracts/{cid}/scheme", {"scheme": "kpr" if a["scheme"].startswith("kpr") else "cash_bertahap",
                                                                   "reason": "AUDIT-FZ ganti jenis uji fuzz"})
    return res(code, j)


def reschedule_gen(w, rng, f=None):
    d = pick(w, rng, "deal", lambda e: not e.get("dead"), focus=f)
    return {"deal": d, "scheme": rng.choice(SCHEMES)} if d else None


def reschedule_run(w, a):
    e = ent(w, a["deal"])
    if not e:
        return skip("deal")
    return res(*w.call("finance", "POST", f"/finance/ar/{e['id']}/schedule", {"scheme_id": w.schemes[a["scheme"]]}))


def edit_customer_gen(w, rng, f=None):
    d = pref(w, rng, "deal", lambda e: e.get("customer_id") and not e.get("deleted"), focus=f, p=0.95)
    return {"deal": d, "name": f"AUDIT-FZ Pembeli {rng.randrange(1000, 9999)}", "ph": rng.random() < 0.5} if d else None


def edit_customer_run(w, a):
    e = ent(w, a["deal"])
    if not e or not e.get("customer_id"):
        return skip("customer")
    body = {"name": a["name"]}
    if a["ph"]:
        body["phone"] = w.phone()
    return res(*w.call("manager", "PUT", f"/customers/{e['customer_id']}", body))


# ====================================================================== KUITANSI / TITIPAN / DENDA / BAST
def receipt_gen(w, rng, f=None):
    d = pref(w, rng, "deal", lambda e: e.get("booked") and not e.get("dead"), focus=f)
    if not d:
        return None
    return {"deal": d, "amount": rng.choice([amt(rng, 1_000_000, 80_000_000), amt(rng, 1_000_000, 300_000_000), 123_457, 999_999, amt(rng, 100_000_000, 700_000_000)]),
            "over": rng.random() < 0.35, "method": rng.choice(["transfer", "transfer", "cash", "va"]),
            "by": rng.choice(["finance", "finance", "owner"])}


def receipt_run(w, a):
    e = ent(w, a["deal"])
    if not e:
        return skip("deal")
    fid = w.proof("deal", e["id"], role=a["by"])
    if not fid:
        return skip("upload")
    code, j = w.call(a["by"], "POST", "/finance/ar/receipts",
                     {"deal_id": e["id"], "amount": a["amount"], "method": a["method"], "proof_file_ids": [fid], "allow_overpay": a["over"],
                      "allow_bank_portion": True, "note": "AUDIT-FZ"})
    return res(code, j)


def receipt_rest_gen(w, rng, f=None):
    """Bayar SISA tepat (menutup piutang) — jalur 'lunas'."""
    d = pref(w, rng, "deal", lambda e: e.get("booked") and not e.get("dead"), focus=f)
    return {"deal": d} if d else None


def receipt_rest_run(w, a):
    e = ent(w, a["deal"])
    if not e:
        return skip("deal")
    inv = w.one("ar_invoices", {"deal_id": e["id"]})
    if not inv or int(inv.get("outstanding") or 0) <= 0:
        return skip("tak ada sisa")
    fid = w.proof("deal", e["id"])
    return res(*w.call("finance", "POST", "/finance/ar/receipts",
                       {"deal_id": e["id"], "amount": int(inv["outstanding"]), "method": "transfer", "proof_file_ids": [fid], "allow_bank_portion": True}))


def void_receipt_gen(w, rng, f=None):
    d = pref(w, rng, "deal", lambda e: e.get("booked") and not e.get("dead"), focus=f)
    return {"deal": d, "which": rng.random()} if d else None


def void_receipt_run(w, a):
    e = ent(w, a["deal"])
    if not e:
        return skip("deal")
    rs = w.rows("receipts", {"deal_id": e["id"], "status": {"$ne": "void"}})
    if not rs:
        return skip("tak ada kuitansi aktif")
    r = rs[int(a["which"] * len(rs)) % len(rs)]
    return res(*w.call("owner", "POST", f"/finance/ar/receipts/{r['id']}/void", {"reason": "AUDIT-FZ pembatalan kuitansi uji fuzz"}))


def dep_in_gen(w, rng, f=None):
    d = pref(w, rng, "deal", lambda e: e.get("booked") and not e.get("dead"), focus=f)
    return {"deal": d, "amount": amt(rng, 1_000_000, 60_000_000)} if d else None


def dep_in_run(w, a):
    e = ent(w, a["deal"])
    if not e:
        return skip("deal")
    fid = w.proof("deal", e["id"])
    return res(*w.call("finance", "POST", f"/finance/ar/{e['id']}/deposit", {"amount": a["amount"], "proof_file_ids": [fid], "note": "AUDIT-FZ"}))


def dep_apply_gen(w, rng, f=None):
    d = pref(w, rng, "deal", lambda e: e.get("booked") and not e.get("dead"), focus=f)
    return {"deal": d, "amount": rng.choice([None, amt(rng, 500_000, 50_000_000)])} if d else None


def dep_apply_run(w, a):
    e = ent(w, a["deal"])
    if not e:
        return skip("deal")
    body = {"note": "AUDIT-FZ"}
    if a["amount"]:
        body["amount"] = a["amount"]
    return res(*w.call("finance", "POST", f"/finance/ar/{e['id']}/deposit/apply", body))


def dep_refund_gen(w, rng, f=None):
    d = pref(w, rng, "deal", lambda e: e.get("booked") and not e.get("dead"), focus=f)
    return {"deal": d, "amount": rng.choice([None, amt(rng, 500_000, 50_000_000)])} if d else None


def dep_refund_run(w, a):
    e = ent(w, a["deal"])
    if not e:
        return skip("deal")
    body = {"note": "AUDIT-FZ refund titipan"}
    if a["amount"]:
        body["amount"] = a["amount"]
    return res(*w.call("owner", "POST", f"/finance/ar/{e['id']}/deposit/refund", body))


def late_apply_gen(w, rng, f=None):
    d = pref(w, rng, "deal", lambda e: e.get("booked") and not e.get("dead"), focus=f)
    return {"deal": d} if d else None


def late_apply_run(w, a):
    e = ent(w, a["deal"])
    if not e:
        return skip("deal")
    return res(*w.call("finance", "POST", f"/finance/late-fees/{e['id']}/apply", {}))


def late_waive_gen(w, rng, f=None):
    d = pref(w, rng, "deal", lambda e: e.get("booked") and not e.get("dead"), focus=f)
    return {"deal": d} if d else None


def late_waive_run(w, a):
    e = ent(w, a["deal"])
    if not e:
        return skip("deal")
    inv = w.one("ar_invoices", {"deal_id": e["id"]})
    pen = [i for i in (inv or {}).get("items", []) if i.get("is_penalty") and not i.get("waived")]
    if not pen:
        return skip("tak ada denda")
    return res(*w.call("owner", "POST", f"/finance/late-fees/{e['id']}/waive/{pen[0]['id']}", {"reason": "AUDIT-FZ keringanan denda uji fuzz"}))


def bast_gen(w, rng, f=None):
    d = pref(w, rng, "deal", lambda e: e.get("booked") and not e.get("dead"), focus=f)
    return {"deal": d, "force": rng.random() < 0.06} if d else None


def bast_run(w, a):
    """BAST normal = hanya untuk deal yang piutangnya LUNAS. `force` menembak BAST di keadaan lain (GL-07/FN-23 sudah dicatat terbuka)."""
    e = ent(w, a["deal"])
    if not e:
        return skip("deal")
    inv = w.one("ar_invoices", {"deal_id": e["id"]})
    d = w.one("deals", {"id": e["id"]})
    if not a.get("force", True) and (not inv or int(inv.get("outstanding") or 1) > 0 or (d or {}).get("status") not in ("booked", "completed")):
        return skip("BAST normal butuh deal booked + AR lunas")
    code, j = w.call("finance", "POST", f"/finance/ar/{e['id']}/bast")
    if code == 200:
        e["completed"] = True
    return res(code, j)


# ====================================================================== KPR / GIRO / CANCELLATION FORMAL / KOMISI
KPR_STAGES = ["diajukan_ke_bank", "appraisal", "sp3k", "akad_kredit"]


def kpr_stage_gen(w, rng, f=None):
    d = pref(w, rng, "deal", lambda e: e.get("contract_id") and e["scheme"].startswith("kpr") and not e.get("dead"), focus=f, p=0.95)
    return {"deal": d, "plafon": rng.choice([200_000_000, 300_000_000, 480_000_000]), "exact": rng.random() < 0.85} if d else None


def kpr_stage_run(w, a):
    e = ent(w, a["deal"])
    cid = _contract(w, e) if e else None
    if not cid:
        return skip("kontrak")
    st = e.get("kpr_next", 0)
    if st >= len(KPR_STAGES):
        return skip("tahap KPR selesai")
    inv = w.one("ar_invoices", {"deal_id": e["id"]})
    bank = sum(int(x.get("amount") or 0) for x in (inv or {}).get("items", []) if x.get("payer") == "bank")
    if bank > 0 and a.get("exact", True):
        a = {**a, "plafon": bank}
    today = datetime.date.today().isoformat()
    fid = w.proof("deal", e["id"])
    stage = KPR_STAGES[st]
    body = {"diajukan_ke_bank": {"bank": "BTN"},
            "appraisal": {"date": today, "amount": a["plafon"] + 20_000_000, "file_id": fid},
            "sp3k": {"file_id": fid, "plafon": a["plafon"], "number": f"SP3K-FZ-{w.tag}-{st}", "date": today, "tenor_months": 120, "rate": 7.5},
            "akad_kredit": {"date": today, "notary": "Notaris Uji", "file_id": fid}}[stage]
    code, j = w.call("finance", "POST", f"/contracts/{cid}/kpr/stage/{stage}", body)
    if code == 200:
        e["kpr_next"] = st + 1
    return res(code, j, note=stage)


def kpr_disb_gen(w, rng, f=None):
    d = pref(w, rng, "deal", lambda e: e.get("kpr_next", 0) >= 4 and not e.get("dead"), focus=f, p=0.95)
    return {"deal": d, "amount": rng.choice([None, amt(rng, 5_000_000, 200_000_000)])} if d else None


def kpr_disb_run(w, a):
    e = ent(w, a["deal"])
    cid = _contract(w, e) if e else None
    if not cid:
        return skip("kontrak")
    fid = w.proof("deal", e["id"])
    if not e.get("kpr_scheme_set") and w.kpr_scheme:
        c1, j1 = w.call("finance", "POST", f"/contracts/{cid}/kpr/disbursement-scheme", {"scheme_id": w.kpr_scheme})
        if c1 == 200:
            e["kpr_scheme_set"] = True
    body = {"tranche_code": w.kpr_tranche, "date": datetime.date.today().isoformat(), "file_id": fid, "note": "AUDIT-FZ", "allow_deposit": True,
            "reason": "AUDIT-FZ pencairan uji"}
    if a["amount"]:
        body["amount"] = a["amount"]
    return res(*w.call("finance", "POST", f"/contracts/{cid}/kpr/disbursements", body))


def pdc_new_gen(w, rng, f=None):
    d = pref(w, rng, "deal", lambda e: e.get("booked") and not e.get("dead"), focus=f)
    return {"deal": d, "amount": amt(rng, 1_000_000, 100_000_000), "no": f"FZ{rng.randrange(10**6, 10**7)}"} if d else None


def pdc_new_run(w, a):
    e = ent(w, a["deal"])
    if not e:
        return skip("deal")
    due = (datetime.date.today() + datetime.timedelta(days=7)).isoformat()
    code, j = w.call("finance", "POST", "/pdc", {"kind": "cek", "bank_name": "BCA", "instrument_no": a["no"], "issuer_name": "AUDIT-FZ", "amount": a["amount"],
                                                 "due_date": due, "deal_id": e["id"], "note": "AUDIT-FZ"})
    if code == 200:
        w.new("pdc", id=j["data"]["id"], deal=a["deal"])
    return res(code, j)


def pdc_act_gen(w, rng, f=None):
    p = pick(w, rng, "pdc", focus=f, prefer_new=0.4)
    return {"pdc": p, "act": rng.choice(["clear", "clear", "bounce", "cancel"])} if p else None


def pdc_act_run(w, a):
    e = ent(w, a["pdc"])
    if not e or not w.accounts:
        return skip("pdc")
    if a["act"] == "clear":
        return res(*w.call("finance", "POST", f"/pdc/{e['id']}/clear", {"cash_account_id": w.accounts[0]["id"]}))
    return res(*w.call("finance", "POST", f"/pdc/{e['id']}/{a['act']}", {"reason": "AUDIT-FZ giro uji fuzz"}))


def cancellation_gen(w, rng, f=None):
    d = pref(w, rng, "deal", lambda e: e.get("contract_id"), focus=f)
    return {"deal": d, "step": rng.choice(["request", "decide", "refund"]), "approve": rng.random() < 0.8,
            "method": rng.choice(["transfer", "cash"])} if d else None


def cancellation_run(w, a):
    e = ent(w, a["deal"])
    cid = _contract(w, e) if e else None
    if not cid:
        return skip("kontrak")
    c = w.one("cancellations", {"deal_id": e["id"]})
    if a["step"] == "request" or not c:
        code, j = w.call("manager", "POST", "/cancellations", {"contract_id": cid, "reason": "AUDIT-FZ pengajuan pembatalan uji fuzz"})
        return res(code, j)
    if a["step"] == "decide":
        return res(*w.call("owner", "POST", f"/cancellations/{c['id']}/decision", {"approved": a["approve"], "note": "AUDIT-FZ keputusan uji fuzz"}))
    return res(*w.call("finance", "POST", f"/cancellations/{c['id']}/refund", {"method": a["method"], "note": "AUDIT-FZ refund uji fuzz"}))


def commission_gen(w, rng, f=None):
    d = pref(w, rng, "deal", lambda e: e.get("booked") and not e.get("dead"), focus=f)
    return {"deal": d, "act": rng.choice(["compute", "approve", "approve", "pay"])} if d else None


def commission_run(w, a):
    e = ent(w, a["deal"])
    if not e:
        return skip("deal")
    if a["act"] == "compute":
        return res(*w.call("finance", "POST", f"/finance/commissions/{e['id']}/compute", {}))
    cs = w.rows("commissions", {"deal_id": e["id"]})
    if not cs:
        return skip("tak ada komisi")
    c = cs[0]
    if a["act"] == "approve":
        return res(*w.call("owner", "POST", f"/finance/commissions/{c['id']}/approve", {}))
    return res(*w.call("finance", "POST", f"/finance/commissions/{c['id']}/pay", {}))


# ====================================================================== PENGADAAN / AP / STOK
def po_new_gen(w, rng, f=None):
    if not w.mats:
        return None
    n = rng.randrange(1, 3)
    items = [{"mat": rng.choice(w.mats), "qty": rng.choice([10, 20, 50, 100]), "price": rng.choice([50_000, 65_000, 120_000])} for _ in range(n)]
    return {"items": items, "vendor": rng.choice(w.vendors)}


def po_new_run(w, a):
    items = []
    for it in a["items"]:
        m = ent(w, it["mat"])
        if not m:
            continue
        items.append({"description": f"AUDIT-FZ item {it['mat']}", "material_id": m["id"], "uom": "sak", "qty": it["qty"], "unit_price": it["price"]})
    if not items:
        return skip("material")
    code, j = w.call("pm", "POST", "/procurement/pos", {"project_id": w.pid, "po_type": "material", "vendor": a["vendor"], "items": items, "note": "AUDIT-FZ"})
    if code == 200:
        w.new("po", id=j["data"]["id"], n=len(items))
    return res(code, j)


def po_approve_gen(w, rng, f=None):
    p = pick(w, rng, "po", focus=f, prefer_new=0.7)
    return {"po": p} if p else None


def po_approve_run(w, a):
    e = ent(w, a["po"])
    if not e:
        return skip("po")
    return res(*w.call("owner", "POST", f"/procurement/pos/{e['id']}/approve", {"note": "AUDIT-FZ"}))


def po_cancel_gen(w, rng, f=None):
    p = pick(w, rng, "po", focus=f, prefer_new=0.2)
    return {"po": p} if p else None


def po_cancel_run(w, a):
    e = ent(w, a["po"])
    if not e:
        return skip("po")
    return res(*w.call("owner", "POST", f"/procurement/pos/{e['id']}/cancel", {"note": "AUDIT-FZ batal"}))


def grn_gen(w, rng, f=None):
    p = pick(w, rng, "po", focus=f, prefer_new=0.7)
    return {"po": p, "frac": rng.choice([0.25, 0.5, 1.0, 1.0, 1.5])} if p else None


def grn_run(w, a):
    e = ent(w, a["po"])
    if not e:
        return skip("po")
    po = w.one("purchase_orders", {"id": e["id"]})
    if not po:
        return skip("po")
    items = []
    for k, it in enumerate(po["items"]):
        rest = float(it["qty"]) - float(it.get("received_qty") or 0)
        q = round(max(1.0, rest * a["frac"]) if a["frac"] <= 1 else float(it["qty"]) * a["frac"], 2)
        items.append({"po_item_index": k, "qty_received": q})
    code, j = w.call("site", "POST", "/procurement/grns", {"po_id": e["id"], "items": items, "note": "AUDIT-FZ"})
    if code == 200:
        w.new("grn", id=j["data"]["id"], po=a["po"])
    return res(code, j)


def return_gen(w, rng, f=None):
    g = pick(w, rng, "grn", focus=f, prefer_new=0.5)
    return {"grn": g, "frac": rng.choice([0.2, 0.5, 1.0, 1.0]), "kind": rng.choice(["rusak", "salah_kirim", "kelebihan", "mutu"])} if g else None


def return_run(w, a):
    e = ent(w, a["grn"])
    if not e:
        return skip("grn")
    g = w.one("grns", {"id": e["id"]})
    if not g:
        return skip("grn")
    items = []
    for k, it in enumerate(g["items"]):
        q = round(float(it["qty_received"]) * a["frac"] - float(it.get("returned_qty") or 0), 2) if a["frac"] < 1 else round(float(it["qty_received"]) - float(it.get("returned_qty") or 0), 2)
        if q > 0:
            items.append({"grn_item_index": k, "qty_returned": q})
    if not items:
        return skip("tak ada sisa retur")
    return res(*w.call("owner", "POST", "/procurement/returns", {"grn_id": e["id"], "kind": a["kind"], "items": items, "reason": "AUDIT-FZ retur uji fuzz barang"}))


def po_bill_gen(w, rng, f=None):
    p = pick(w, rng, "po", focus=f, prefer_new=0.6)
    return {"po": p, "frac": rng.choice([0.3, 0.6, 1.0, 1.0]), "ret": rng.choice([0, 5, 5, 10])} if p else None


def po_bill_run(w, a):
    e = ent(w, a["po"])
    if not e:
        return skip("po")
    po = w.one("purchase_orders", {"id": e["id"]})
    if not po:
        return skip("po")
    claimed = max(1000, int(int(po.get("received_value") or po.get("total") or 100000) * a["frac"]))
    code, j = w.call("finance", "POST", "/procurement/bills", {"po_id": e["id"], "claimed": claimed, "retention_pct": a["ret"],
                                                              "vendor_invoice_no": f"FZ-{w.tag}-{random.randrange(10**6)}", "note": "AUDIT-FZ"})
    if code == 200:
        bid = (j["data"].get("bill") or j["data"]).get("id")
        w.new("bill", id=bid, po=a["po"])
    return res(code, j)


def bill_manual_gen(w, rng, f=None):
    return {"claimed": amt(rng, 1_000_000, 90_000_000), "ret": rng.choice([0, 5, 10]), "vendor": rng.choice(w.vendors)}


def bill_manual_run(w, a):
    code, j = w.call("finance", "POST", "/finance/ap/bills", {"vendor": a["vendor"], "project_id": w.pid, "claimed": a["claimed"], "retention_pct": a["ret"],
                                                              "vendor_invoice_no": f"FZM-{w.tag}-{random.randrange(10**7)}", "note": "AUDIT-FZ"})
    if code == 200:
        w.new("bill", id=j["data"]["id"], po=None)
    return res(code, j)


def bill_approve_gen(w, rng, f=None):
    b = pick(w, rng, "bill", focus=f, prefer_new=0.7)
    return {"bill": b} if b else None


def bill_approve_run(w, a):
    e = ent(w, a["bill"])
    if not e:
        return skip("bill")
    return res(*w.call("owner", "POST", f"/finance/ap/bills/{e['id']}/approve"))


def bill_pay_gen(w, rng, f=None):
    b = pick(w, rng, "bill", focus=f, prefer_new=0.6)
    return {"bill": b, "frac": rng.choice([0.2, 0.5, 1.0, 1.0, 1.2])} if b else None


def bill_pay_run(w, a):
    e = ent(w, a["bill"])
    if not e:
        return skip("bill")
    b = w.one("ap_invoices", {"id": e["id"]})
    if not b:
        return skip("bill")
    rest = int(b.get("outstanding") or 0)
    amount = max(1000, int(max(rest, 1000) * a["frac"]))
    code, j = w.call("finance", "POST", f"/finance/ap/bills/{e['id']}/pay", {"amount": amount, "note": "AUDIT-FZ"})
    return res(code, j)


def pay_void_gen(w, rng, f=None):
    b = pick(w, rng, "bill", focus=f, prefer_new=0.5)
    return {"bill": b} if b else None


def pay_void_run(w, a):
    e = ent(w, a["bill"])
    if not e:
        return skip("bill")
    ps = w.rows("payments_out", {"bill_id": e["id"], "status": {"$ne": "void"}})
    if not ps:
        return skip("tak ada pembayaran")
    return res(*w.call("owner", "POST", f"/finance/ap/payments/{ps[0]['id']}/void", {"reason": "AUDIT-FZ pembatalan pembayaran uji fuzz"}))


def stock_txn_gen(w, rng, f=None):
    m = pick(w, rng, "mat", focus=f)
    return {"mat": m, "type": rng.choice(["in", "in", "out", "out"]), "qty": rng.choice([5, 10, 25, 100, 400])} if m else None


def stock_txn_run(w, a):
    e = ent(w, a["mat"])
    if not e:
        return skip("mat")
    return res(*w.call("owner", "POST", "/materials/txn", {"project_id": w.pid, "material_id": e["id"], "type": a["type"], "qty": a["qty"], "note": "AUDIT-FZ", "ref": "AUDIT-FZ"}))


def opname_gen(w, rng, f=None):
    m = pick(w, rng, "mat", focus=f)
    return {"mat": m, "phys": rng.choice([0, 3, 40, 120, 500])} if m else None


def opname_run(w, a):
    e = ent(w, a["mat"])
    if not e:
        return skip("mat")
    return res(*w.call("owner", "POST", "/materials/opname", {"project_id": w.pid, "material_id": e["id"], "physical_qty": a["phys"], "note": "AUDIT-FZ"}))


def transfer_gen(w, rng, f=None):
    m = pick(w, rng, "mat", focus=f)
    return {"mat": m, "qty": rng.choice([1, 5, 30, 200])} if m and w.pid2 else None


def transfer_run(w, a):
    e = ent(w, a["mat"])
    if not e:
        return skip("mat")
    return res(*w.call("owner", "POST", "/materials/transfers", {"from_project_id": w.pid, "to_project_id": w.pid2, "material_id": e["id"], "qty": a["qty"],
                                                                 "reason": "AUDIT-FZ transfer uji fuzz stok"}))


def req_gen(w, rng, f=None):
    m = pick(w, rng, "mat", focus=f)
    return {"mat": m, "qty": rng.choice([2, 10, 40]), "step": rng.choice(["new", "approve", "issue"]), "r": w.last.get("req")} if m else None


def req_run(w, a):
    e = ent(w, a["mat"])
    if not e:
        return skip("mat")
    last = a.get("r")
    if a["step"] == "new" or not last or not w.get(last):
        code, j = w.call("site", "POST", "/materials/requisitions", {"project_id": w.pid, "purpose": "AUDIT-FZ permintaan", "items": [{"material_id": e["id"], "qty": a["qty"]}]})
        if code == 200:
            w.new("req", id=j["data"]["id"])
        return res(code, j)
    r = w.get(last)
    if a["step"] == "approve":
        return res(*w.call("pm", "POST", f"/materials/requisitions/{r['id']}/approve", {}))
    return res(*w.call("site", "POST", f"/materials/requisitions/{r['id']}/issue", {}))


def cb_gen(w, rng, f=None):
    return {"step": rng.choice(["new", "approve", "disburse", "disburse", "settle", "cancel"]), "amount": amt(rng, 500_000, 6_000_000),
            "frac": rng.choice([0.4, 1.0, 1.3]), "r": w.last.get("cb")}


def cb_run(w, a):
    last = a.get("r")
    if a["step"] == "new" or not last or not w.get(last):
        code, j = w.call("site", "POST", "/petty-cash/advances", {"purpose": "AUDIT-FZ kas bon uji", "amount": a["amount"], "category": "biaya_proyek"})
        if code == 200:
            w.new("cb", id=j["data"]["id"], amount=a["amount"])
        return res(code, j)
    e = w.get(last)
    if a["step"] == "approve":
        return res(*w.call("finance", "POST", f"/petty-cash/advances/{e['id']}/approve", {"note": "AUDIT-FZ"}))
    if a["step"] == "disburse":
        return res(*w.call("finance", "POST", f"/petty-cash/advances/{e['id']}/disburse", {}))
    if a["step"] == "settle":
        used = max(1000, int(e["amount"] * a["frac"]))
        return res(*w.call("site", "POST", f"/petty-cash/advances/{e['id']}/settle",
                           {"items": [{"category": "biaya_proyek", "description": "AUDIT-FZ belanja", "amount": used, "date": datetime.date.today().isoformat()}]}))
    return res(*w.call("site", "POST", f"/petty-cash/advances/{e['id']}/cancel", {"reason": "AUDIT-FZ batal uji"}))


def bank_stmt_gen(w, rng, f=None):
    d = pref(w, rng, "deal", lambda e: e.get("booked") and not e.get("dead"), focus=f)
    return {"deal": d, "amount": amt(rng, 2_000_000, 120_000_000), "n": rng.randrange(10**5, 10**6)} if d else None


def bank_stmt_run(w, a):
    e = ent(w, a["deal"])
    if not e or not w.accounts:
        return skip("deal")
    today = datetime.date.today().isoformat()
    inv = w.one("ar_invoices", {"deal_id": e["id"]})
    rest = int((inv or {}).get("outstanding") or 0)
    if rest > 0:
        a = {**a, "amount": min(a["amount"], rest)}
    csv_text = f"Tanggal,Keterangan,Referensi,Debit,Kredit,Saldo\n{today},TRANSFER MASUK AUDIT-FZ {a['deal']},FZ{a['n']},0,{a['amount']},{a['amount']}\n"
    code, j = w.call("finance", "POST", "/bank/statements/import", {"account_id": w.accounts[0]["id"], "filename": f"AUDIT-FZ-{a['n']}.csv", "csv_text": csv_text, "dry_run": False})
    if code == 200:
        t = w.one("bank_transactions", {"ref": f"FZ{a['n']}"})
        if t:
            w.new("btx", id=t["id"], deal=a["deal"], amount=a["amount"])
    return res(code, j)


def bank_match_gen(w, rng, f=None):
    b = pick(w, rng, "btx", focus=f, prefer_new=0.5)
    return {"btx": b, "act": rng.choice(["match", "match", "unmatch"])} if b else None


def bank_match_run(w, a):
    b = ent(w, a["btx"])
    d = ent(w, b["deal"]) if b else None
    if not b or not d:
        return skip("btx")
    if a["act"] == "match":
        return res(*w.call("finance", "POST", f"/bank/transactions/{b['id']}/match", {"kind": "ar_deal", "target_id": d["id"], "note": "AUDIT-FZ"}))
    return res(*w.call("owner", "POST", f"/bank/transactions/{b['id']}/unmatch", {"reason": "AUDIT-FZ batal cocok uji fuzz"}))


def tick_gen(w, rng, f=None):
    return {}


def tick_run(w, a):
    """Pemicu dispatcher (membuat lead mengosongkan antrean event) + pembacaan reconcile."""
    return res(*w.call("finance", "GET", "/finance/reconcile"))


W = {  # bobot dasar mode sekuensial
    "lead_new": 6, "lead_contact": 3, "appt": 1, "edit_lead": 3, "reassign": 3, "lead_stage": 1,
    "reserve": 9, "bf_pay": 5, "book": 6, "convert": 6, "activate": 3, "cancel_deal": 2, "force_delete": 1.2,
    "scheme_change": 3, "reschedule": 1.5, "edit_customer": 3,
    "receipt": 14, "receipt_rest": 4, "void_receipt": 4, "dep_in": 3, "dep_apply": 3, "dep_refund": 2,
    "late_apply": 1, "late_waive": 1, "bast": 3,
    "kpr_stage": 5, "kpr_disb": 4, "pdc_new": 1.5, "pdc_act": 1.5, "cancellation": 3, "commission": 3,
    "po_new": 3, "po_approve": 3, "po_cancel": 1, "grn": 4, "return": 2.5, "po_bill": 3, "bill_manual": 1.5, "bill_approve": 3,
    "bill_pay": 4, "pay_void": 1.5, "stock_txn": 4, "opname": 2, "transfer": 2, "req": 2, "cb": 3,
    "bank_stmt": 2, "bank_match": 2, "tick": 0.5,
}
for n, g, r in [
    ("lead_new", lead_new_gen, lead_new_run), ("lead_contact", lead_contact_gen, lead_contact_run), ("appt", appt_gen, appt_run),
    ("edit_lead", edit_lead_gen, edit_lead_run), ("reassign", reassign_gen, reassign_run), ("lead_stage", lead_stage_gen, lead_stage_run),
    ("reserve", reserve_gen, reserve_run), ("bf_pay", bf_gen, bf_run), ("book", book_gen, book_run), ("convert", convert_gen, convert_run),
    ("activate", activate_gen, activate_run), ("cancel_deal", cancel_deal_gen, cancel_deal_run), ("force_delete", force_delete_gen, force_delete_run),
    ("scheme_change", scheme_change_gen, scheme_change_run), ("reschedule", reschedule_gen, reschedule_run),
    ("edit_customer", edit_customer_gen, edit_customer_run), ("receipt", receipt_gen, receipt_run),
    ("receipt_rest", receipt_rest_gen, receipt_rest_run), ("void_receipt", void_receipt_gen, void_receipt_run),
    ("dep_in", dep_in_gen, dep_in_run), ("dep_apply", dep_apply_gen, dep_apply_run), ("dep_refund", dep_refund_gen, dep_refund_run),
    ("late_apply", late_apply_gen, late_apply_run), ("late_waive", late_waive_gen, late_waive_run), ("bast", bast_gen, bast_run),
    ("kpr_stage", kpr_stage_gen, kpr_stage_run), ("kpr_disb", kpr_disb_gen, kpr_disb_run), ("pdc_new", pdc_new_gen, pdc_new_run),
    ("pdc_act", pdc_act_gen, pdc_act_run), ("cancellation", cancellation_gen, cancellation_run), ("commission", commission_gen, commission_run),
    ("po_new", po_new_gen, po_new_run), ("po_approve", po_approve_gen, po_approve_run), ("po_cancel", po_cancel_gen, po_cancel_run),
    ("grn", grn_gen, grn_run), ("return", return_gen, return_run), ("po_bill", po_bill_gen, po_bill_run),
    ("bill_manual", bill_manual_gen, bill_manual_run), ("bill_approve", bill_approve_gen, bill_approve_run), ("bill_pay", bill_pay_gen, bill_pay_run),
    ("pay_void", pay_void_gen, pay_void_run), ("stock_txn", stock_txn_gen, stock_txn_run), ("opname", opname_gen, opname_run),
    ("transfer", transfer_gen, transfer_run), ("req", req_gen, req_run), ("cb", cb_gen, cb_run),
    ("bank_stmt", bank_stmt_gen, bank_stmt_run), ("bank_match", bank_match_gen, bank_match_run), ("tick", tick_gen, tick_run),
]:
    reg(n, W[n], g, r)


# ====================================================================== PERJALANAN (mengarahkan acak agar rantai panjang tercapai)
def advance(w, rng):
    """Pilih satu perjalanan yang belum selesai dan kembalikan LANGKAH LOGIS berikutnya (atau None)."""
    deals = [d for d in w.of_kind("deal") if not w.get(d).get("dead")]
    leads_free = [l for l in w.of_kind("lead") if not any(e["kind"] == "deal" and e["lead"] == l and not e.get("dead") for e in w.ent.values())]
    pool = [("lead", l) for l in leads_free[-3:]] + [("deal", d) for d in deals[-6:]]
    if not pool:
        return {"op": "lead_new", "args": lead_new_gen(w, rng)}
    kind, lab = rng.choice(pool)
    if kind == "lead":
        a = reserve_gen(w, rng, {"lead": lab})
        return {"op": "reserve", "args": a} if a else None
    e = w.get(lab)
    f = {"deal": lab}
    if not e.get("booked"):
        if e.get("bf") and not e.get("bf_paid"):
            a = bf_gen(w, rng, f)
            if a:
                a["amount"] = e["bf"]
                return {"op": "bf_pay", "args": a}
        return {"op": "book", "args": {"deal": lab}}
    if not e.get("contract_id"):
        return {"op": "convert", "args": {"deal": lab}}
    kpr = e["scheme"].startswith("kpr")
    inv = w.one("ar_invoices", {"deal_id": e["id"]})
    if inv and inv.get("status") == "paid" and not e.get("completed") and rng.random() < 0.6:
        return {"op": "bast", "args": {"deal": lab, "force": False}}
    btx = [b for b in w.of_kind("btx") if w.get(b).get("deal") == lab]
    menu = [("receipt", 8), ("receipt_rest", 3), ("void_receipt", 2), ("dep_in", 2), ("dep_apply", 2), ("dep_refund", 1.5), ("bast", 3),
            ("activate", 1.5), ("cancellation", 2), ("scheme_change", 2), ("pdc_new", 1), ("edit_customer", 1.5), ("commission", 1.5),
            ("bank_stmt", 2.5), ("bank_match", 3), ("cancel_deal", 0.7), ("late_apply", 2 if e["scheme"] == "telat" else 0.3), ("late_waive", 1 if e["scheme"] == "telat" else 0.2),
            ("force_delete", 0.5), ("reschedule", 0.7)]
    if kpr:
        menu += [("kpr_stage", 8 if e.get("kpr_next", 0) < 4 else 0.5), ("kpr_disb", 6 if e.get("kpr_next", 0) >= 4 else 0)]
    names = [m[0] for m in menu if m[1] > 0]
    wts = [m[1] for m in menu if m[1] > 0]
    nm = rng.choices(names, wts)[0]
    a = OPS[nm]["gen"](w, rng, f)
    return {"op": nm, "args": a} if a is not None else None
