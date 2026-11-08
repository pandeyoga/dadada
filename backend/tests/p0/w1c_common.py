"""Pembantu bersama tes W1-C (deal batal: akrual komisi/fee/pajak #11, titipan biaya & invoice biaya #12).

Semua penimpaan kebijakan dipasang di TINGKAT PROYEK milik `World` tes itu (bukan organisasi) lalu dikembalikan di `finally`
— suite penuh memakai organisasi yang sama dan tes lain tidak boleh melihat kebijakan kita (pelajaran 7).
"""
import contextlib
import time
import uuid

from test_p0_masuk import FINANCE, OWNER, call, ok
from test_p0_siklus_deal import mdb

FINLEAD = "finlead@sipro.co.id"          # finance_manager: boleh memutuskan permohonan (cancellation:approve)
K_COM, K_FEE, K_TAX = ("cancel.accrual_reversal.commission", "cancel.accrual_reversal.marketing_fee",
                       "cancel.accrual_reversal.tax")
K_POL, K_PCT, K_APR = ("cancel.cost_deposit.policy", "cancel.cost_deposit.forfeit_pct", "cancel.cost_deposit.requires_approval")
UNPAID, MANUAL = "balik_otomatis_yang_belum_dibayar", "manual_keuangan"
REFUND, MANUAL_COST, HANGUS = "refund_dan_batalkan_invoice", "manual_dengan_pengakuan", "hangus_sebagian"


def put_policy(key, value, project_id=None, who=OWNER):
    body = {"value": value, "reason": "uji W1-C kebijakan pembatalan", "scope": "project" if project_id else "org"}
    if project_id:
        body["scope_id"] = project_id
    return call(who, "PUT", f"/settings/{key}", json=body)


def reset_policy(key, project_id=None):
    params = {"scope": "project", "scope_id": project_id} if project_id else {"scope": "org"}
    call(OWNER, "POST", f"/settings/{key}/reset", params=params)


@contextlib.contextmanager
def policies(project_id, **kv):
    """`with policies(pid, **{K_COM: UNPAID}):` — pasang di proyek, kembalikan di akhir."""
    keys = list(kv.items())
    try:
        for k, v in keys:
            ok(put_policy(k, v, project_id))
        yield
    finally:
        for k, _ in keys:
            reset_policy(k, project_id)


def reconcile_ok(timeout=40):
    """Rekonsiliasi hijau SETELAH antrean event kosong (jurnal lahir dari event; dispatcher ±8 dtk)."""
    end = time.time() + timeout
    while True:
        d = ok(call(FINANCE, "GET", "/finance/reconcile"))["data"]
        if d["ok"] or time.time() > end:
            return d["ok"], [c for c in d["checks"] if not c["ok"] and not c.get("indicator")]
        time.sleep(1.5)


def check(code):
    rows = ok(call(FINANCE, "GET", "/finance/reconcile"))["data"]["checks"]
    return [c for c in rows if c["code"] == code][0]


def wait_until(fn, timeout=40, every=1.0):
    end = time.time() + timeout
    while True:
        v = fn()
        if v or time.time() > end:
            return v
        time.sleep(every)


def bank(opening=5_000_000_000):
    body = {"kind": "bank", "name": f"Rek W1C {uuid.uuid4().hex[:6].upper()}", "bank_name": "Bank Uji W1C",
            "account_no": uuid.uuid4().hex[:10].upper(), "opening_balance": opening}
    return ok(call(FINANCE, "POST", "/cash-bank/accounts", json=body))["data"]


def journals(source_type=None, source_id=None, event_re=None):
    q = {}
    if source_type:
        q["source_type"] = source_type
    if source_id:
        q["source_id"] = source_id
    if event_re:
        q["source_event"] = {"$regex": event_re}
    return list(mdb().journal_entries.find(q))


def lines_of(je):
    """{kode_akun: (debit, kredit)} dijumlahkan."""
    out = {}
    for ln in je["lines"]:
        d, c = out.get(ln["account_code"], (0, 0))
        out[ln["account_code"]] = (d + int(ln["debit"]), c + int(ln["credit"]))
    return out


def commission_of(deal_id):
    return mdb().commissions.find_one({"deal_id": deal_id})


def approve_commission(deal_id, who=FINANCE):
    """Setujui komisi deal ini lewat API lalu tunggu jurnal akrualnya terbit (dispatcher ±8 dtk)."""
    com = commission_of(deal_id)
    ok(call(who, "POST", f"/finance/commissions/{com['id']}/approve"))
    assert wait_until(lambda: journals("commission", com["id"])), "jurnal akrual komisi tidak terbit"
    return mdb().commissions.find_one({"id": com["id"]})


def new_agent():
    return ok(call(OWNER, "POST", "/marketing/agents", json={
        "name": f"Agen W1C {uuid.uuid4().hex[:6].upper()}", "agent_type": "agen_properti"}))["data"]["id"]


def approved_fee(deal_id, gross_pct=2.0, pph_pct=5.0, trigger="booking"):
    """Fee marketing disetujui (jurnal akrual sinkron). Mengembalikan dokumen fee dari DB."""
    fee = ok(call(OWNER, "POST", "/marketing/fees", json={
        "agent_id": new_agent(), "deal_id": deal_id, "basis": "percent", "value": gross_pct,
        "trigger": trigger, "pph_pct": pph_pct}))["data"]
    ok(call(FINANCE, "POST", f"/marketing/fees/{fee['id']}/approve", json={"note": "uji W1-C"}))
    return mdb().marketing_fees.find_one({"id": fee["id"]})
