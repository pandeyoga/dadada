"""Mode KONKUREN: tiap putaran = langkah persiapan (sekuensial) + satu 'letusan' 2–4 operasi serentak pada entitas yang sama."""
from . import ops as O


def _mk(runner, w, rng, name, **over):
    focus = dict(w.last)
    args = O.OPS[name]["gen"](w, rng, focus)
    if args is None:
        return None
    args.update(over)
    st = {"op": name, "args": args}
    runner.exec_step(w, st)
    return st


def prep_steps(runner, w, rng, need):
    out = []

    def add(name, **over):
        st = _mk(runner, w, rng, name, **over)
        if st:
            out.append(st)
        return st

    def deal(scheme=None):
        add("lead_new")
        add("reserve", scheme=scheme or rng.choice(["cash_bertahap_3x", "cash_bertahap", "cash_keras"]), bf=5_000_000)
        add("bf_pay", amount=5_000_000)
        add("book")
        add("convert")

    if need == "deal_resv":
        add("lead_new")
        add("reserve", scheme="cash_keras", bf=5_000_000)
    elif need == "lead2":
        add("lead_new")
        add("lead_new")
    elif need == "lead":
        add("lead_new")
    elif need == "deal":
        deal()
    elif need == "deal_paid":
        deal()
        add("receipt", amount=20_000_000, over=False, by="finance", method="transfer")
        add("receipt", amount=12_000_000, over=False, by="finance", method="transfer")
    elif need == "deal_dep":
        deal()
        add("dep_in", amount=30_000_000)
        add("receipt", amount=10_000_000, over=False, by="finance", method="transfer")
    elif need == "deal_over":
        deal()
        add("receipt", amount=900_000_000, over=True, by="finance", method="transfer")
    elif need == "deal_kpr":
        deal("kpr")
        for _ in range(4):
            add("kpr_stage", plafon=300_000_000)
    elif need == "deal_late":
        deal("telat")
    elif need == "deal_late_pen":
        deal("telat")
        add("late_apply")
    elif need == "deal_full":
        deal()
        add("receipt_rest")
    elif need == "deal_pdc":
        deal()
        add("pdc_new")
    elif need == "deal_bank":
        deal()
        add("bank_stmt")
    elif need == "deal_comm":
        deal()
        add("commission", act="compute")
    elif need == "po":
        add("po_new")
        add("po_approve")
    elif need == "po_grn":
        add("po_new")
        add("po_approve")
        add("grn", frac=1.0)
    elif need == "bill":
        add("bill_manual", claimed=40_000_000, ret=5)
        add("bill_approve")
    elif need == "bill_part":
        add("bill_manual", claimed=40_000_000, ret=5)
        add("bill_approve")
        add("bill_pay", frac=0.5)
    elif need == "mat":
        add("stock_txn", type="in", qty=100)
    elif need == "cb":
        add("cb", step="new", amount=3_000_000)
        add("cb", step="approve")
    return out


def last(kind):
    return lambda w: {kind: w.last.get(kind)}


def two_leads_one_unit(w):
    return {}


BURSTS = [
    {"name": "receipt||receipt", "need": "deal", "par": ["receipt", "receipt"]},
    {"name": "receipt||receipt_rest", "need": "deal", "par": ["receipt_rest", "receipt_rest"]},
    {"name": "receipt||void", "need": "deal_paid", "par": ["receipt", "void_receipt"]},
    {"name": "void||void", "need": "deal_paid", "par": ["void_receipt", "void_receipt"]},
    {"name": "dep_apply||dep_refund", "need": "deal_dep", "par": ["dep_apply", "dep_refund"]},
    {"name": "dep_refund||dep_refund", "need": "deal_over", "par": ["dep_refund", "dep_refund", "dep_apply"]},
    {"name": "dep_apply||receipt", "need": "deal_dep", "par": ["dep_apply", "receipt"]},
    {"name": "cancel||receipt", "need": "deal_paid", "par": ["cancel_deal", "receipt"]},
    {"name": "cancel||convert", "need": "deal", "par": ["cancel_deal", "convert"]},
    {"name": "convert||convert", "need": "deal", "par": ["convert", "convert", "convert"]},
    {"name": "scheme||receipt", "need": "deal_paid", "par": ["scheme_change", "receipt"]},
    {"name": "reschedule||receipt", "need": "deal_paid", "par": ["reschedule", "receipt"]},
    {"name": "bast||receipt", "need": "deal_paid", "par": ["bast", "receipt"]},
    {"name": "bast||bast", "need": "deal_full", "par": ["bast", "bast"]},
    {"name": "bast||void", "need": "deal_full", "par": ["bast", "void_receipt"]},
    {"name": "delete||receipt", "need": "deal_paid", "par": ["force_delete", "receipt"]},
    {"name": "delete||void", "need": "deal_paid", "par": ["force_delete", "void_receipt"]},
    {"name": "reserve||reserve(unit sama)", "need": "lead2", "par": [("reserve", lambda w: {"lead": w.of_kind("lead")[-2], "unit": "unit#" + str(w.cnt["unit"])}),
                                                                      ("reserve", lambda w: {"lead": w.of_kind("lead")[-1], "unit": "unit#" + str(w.cnt["unit"])})]},
    {"name": "reserve||reserve(lead sama)", "need": "lead", "par": [("reserve", lambda w: {"unit": "unit#1"}), ("reserve", lambda w: {"unit": "unit#2"})]},
    {"name": "book||cancel", "need": "deal", "par": ["book", "cancel_deal"]},
    {"name": "bf||bf", "need": "lead", "par": []},   # diisi dinamis oleh generator reserve di bawah
    {"name": "edit_lead||edit_lead", "need": "deal", "par": ["edit_lead", "edit_lead", "edit_customer"]},
    {"name": "reassign||edit", "need": "deal", "par": ["reassign", "edit_lead"]},
    {"name": "late||receipt", "need": "deal_paid", "par": ["late_apply", "receipt"]},
    {"name": "kpr_disb||kpr_disb", "need": "deal_kpr", "par": ["kpr_disb", "kpr_disb"]},
    {"name": "kpr_disb||cancel", "need": "deal_kpr", "par": ["kpr_disb", "cancel_deal"]},
    {"name": "pdc_clear||pdc_clear", "need": "deal_pdc", "par": [("pdc_act", lambda w: {}), ("pdc_act", lambda w: {})]},
    {"name": "bank_match||bank_match", "need": "deal_bank", "par": ["bank_match", "bank_match"]},
    {"name": "bank_match||receipt", "need": "deal_bank", "par": ["bank_match", "receipt"]},
    {"name": "commission approve||pay", "need": "deal_comm", "par": ["commission", "commission", "commission"]},
    {"name": "bill_pay||bill_pay", "need": "bill", "par": ["bill_pay", "bill_pay"]},
    {"name": "bill_pay||void", "need": "bill_part", "par": ["bill_pay", "pay_void"]},
    {"name": "bill_approve||bill_approve", "need": "bill", "par": ["bill_approve", "bill_approve"]},
    {"name": "grn||grn", "need": "po", "par": ["grn", "grn"]},
    {"name": "grn||po_cancel", "need": "po", "par": ["grn", "po_cancel"]},
    {"name": "return||return", "need": "po_grn", "par": ["return", "return"]},
    {"name": "return||bill", "need": "po_grn", "par": ["return", "po_bill"]},
    {"name": "stock_out||stock_out", "need": "mat", "par": ["stock_txn", "stock_txn", "stock_txn"]},
    {"name": "transfer||stock_out", "need": "mat", "par": ["transfer", "stock_txn", "opname"]},
    {"name": "cb_disburse||cb_disburse", "need": "cb", "par": ["cb", "cb"]},
]
BURSTS += [
    {"name": "bf||bf", "need": "deal_resv", "par": ["bf_pay", "bf_pay"]},
    {"name": "bf||cancel", "need": "deal_resv", "par": ["bf_pay", "cancel_deal"]},
    {"name": "book||bf", "need": "deal_resv", "par": ["bf_pay", "book"]},
    {"name": "late||late", "need": "deal_late", "par": ["late_apply", "late_apply"]},
    {"name": "late_waive||late_waive", "need": "deal_late_pen", "par": ["late_waive", "late_waive"]},
    {"name": "late_waive||receipt", "need": "deal_late_pen", "par": ["late_waive", "receipt"]},
]
BURSTS = [b for b in BURSTS if b["par"]]
