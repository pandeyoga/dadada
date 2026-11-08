"""Pembantu bersama tes W2-B (BPHTB per kontrak + kebijakan tingkat kontrak).

Penimpaan kebijakan di TINGKAT PROYEK milik `World` tes (bukan organisasi) lalu dikembalikan di `finally` — suite penuh memakai organisasi
yang sama dan tes lain tidak boleh melihat kebijakan kita (pelajaran 7). Satu-satunya yang menyentuh tingkat organisasi mereset di `finally`.
"""
import contextlib
import time
import uuid

from test_p0_masuk import FINANCE, OWNER, SALES, TAG, call, convert, ok, upload_proof
from test_p0_siklus_deal import mdb

FINLEAD = "finlead@sipro.co.id"          # finance_manager: contracts:update + finance:manage
K_BY, K_PCT = "bphtb.borne_by", "bphtb.developer_share_pct"
PEMBELI, DEVELOPER, DIBAGI = "pembeli", "developer", "dibagi"
ALASAN = "uji W2-B kebijakan kontrak BPHTB"
BPHTB_500JT = 21_000_000                 # 5% × (500 jt − NPOPTKP 80 jt) — harga unit World = Rp 500 jt
NOTARIS = 7_500_000


def allin_id(code="EXCLUDE"):
    return next(s["id"] for s in ok(call(OWNER, "GET", "/allin-schemes"))["data"] if s["code"] == code)


def new_contract(world, code="EXCLUDE", scheme="Cash Bertahap (3x)", who=SALES, allin=True):
    """Reservasi → booking → kontrak (otomatis saat booking terverifikasi, atau lewat konversi). Skema biaya all-in `code`."""
    unit = world.units[world.next_unit]
    world.next_unit += 1
    phone = "+62812" + str(int(time.time() * 1000))[-9:]
    lead = ok(call(who, "POST", "/leads", json={"name": f"Uji W2B {TAG} {world.next_unit}", "phone": phone, "source": "manual"}))["data"]
    body = {"unit_id": unit["id"], "lead_id": lead["id"], "booking_fee": 0, "scheme_id": world.scheme[scheme]}
    if allin:
        body["allin_scheme_id"] = allin_id(code)
    deal = ok(call(who, "POST", "/deals/reserve", json=body))["data"]
    ok(call(who, "POST", f"/deals/{deal['id']}/book", json={}))
    d = {"deal_id": deal["id"], "unit_id": unit["id"], "unit_code": unit["code"], "project_id": world.project_id, "reserve_costs": deal.get("costs")}
    d["contract_id"] = convert(d)
    return d


def contract(cid, who=OWNER):
    return ok(call(who, "GET", f"/contracts/{cid}"))["data"]


def comps(cid):
    """{kode: (perlakuan, nilai)} komponen biaya snapshot kontrak."""
    return {c["code"]: (c["treatment"], int(c.get("amount") or 0)) for c in (contract(cid).get("costs") or {}).get("components") or []}


def ledger(cid, who=FINANCE):
    return ok(call(who, "GET", f"/contracts/{cid}/costs-ledger"))["data"]


def live_invoices(cid):
    return [i for i in ledger(cid)["invoices"] if i.get("status") != "void"]


def policy_of(cid, who=FINLEAD):
    return ok(call(who, "GET", f"/contracts/{cid}/policy"))["data"]


def row(cid, key=K_BY, who=FINLEAD):
    return next(r for r in policy_of(cid, who)["keys"] if r["key"] == key)


def put(cid, key, value, reason=ALASAN, who=FINLEAD):
    return call(who, "PUT", f"/contracts/{cid}/policy/{key}", json={"value": value, "reason": reason})


def delete(cid, key, reason=ALASAN, who=FINLEAD):
    params = {"reason": reason} if reason is not None else None
    return call(who, "DELETE", f"/contracts/{cid}/policy/{key}", params=params)


def put_setting(key, value, project_id=None, who=FINLEAD):
    body = {"value": value, "reason": ALASAN, "scope": "project" if project_id else "org"}
    if project_id:
        body["scope_id"] = project_id
    return call(who, "PUT", f"/settings/{key}", json=body)


def reset_setting(key, project_id=None):
    params = {"scope": "project", "scope_id": project_id} if project_id else {"scope": "org"}
    call(OWNER, "POST", f"/settings/{key}/reset", params=params)


@contextlib.contextmanager
def settings(project_id=None, **kv):
    """`with settings(pid, **{K_BY: DEVELOPER}):` — pasang di proyek (atau organisasi bila project_id=None), kembalikan di akhir."""
    keys = list(kv.items())
    try:
        for k, v in keys:
            ok(put_setting(k, v, project_id))
        yield
    finally:
        for k, _ in keys:
            reset_setting(k, project_id)


def bayar_invoice(inv, amount=None, who=FINANCE):
    return call(who, "POST", f"/cost-invoices/{inv['id']}/pay",
                json={"amount": amount or inv["outstanding"], "proof_file_ids": [upload_proof(who)]})


def reconcile_ok(timeout=40):
    """Rekonsiliasi hijau SETELAH antrean event kosong (jurnal lahir dari event; dispatcher ±8 dtk)."""
    end = time.time() + timeout
    while True:
        d = ok(call(FINANCE, "GET", "/finance/reconcile"))["data"]
        if d["ok"] or time.time() > end:
            return d["ok"], [c for c in d["checks"] if not c["ok"] and not c.get("indicator")]
        time.sleep(1.5)


def wait_until(fn, timeout=40, every=1.0):
    end = time.time() + timeout
    while True:
        v = fn()
        if v or time.time() > end:
            return v
        time.sleep(every)


def journals(source_type=None, source_id=None):
    q = {}
    if source_type:
        q["source_type"] = source_type
    if source_id:
        q["source_id"] = source_id
    return list(mdb().journal_entries.find(q))


def lines_of(je):
    """{kode_akun: (debit, kredit)} dijumlahkan."""
    out = {}
    for ln in je["lines"]:
        d, c = out.get(ln["account_code"], (0, 0))
        out[ln["account_code"]] = (d + int(ln["debit"]), c + int(ln["credit"]))
    return out


def uniq(prefix="W2B"):
    return f"{prefix}-{uuid.uuid4().hex[:6].upper()}"
