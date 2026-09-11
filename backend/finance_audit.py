"""Audit keuangan ringan: tie-out subledger ↔ buku besar dan HPP RAB vs realisasi WIP per unit.

`reconcile()` = versi runtime dari `scripts/verify_business_invariants.py` bagian GL, dipakai
dasbor keuangan untuk menyalakan lampu merah saat saldo akun kendali tidak sama dengan
subledgernya. `hpp_per_unit()` membandingkan HPP RAB per unit (RAB tipe + alokasi biaya
bersama) dengan biaya yang benar-benar sudah dikontrakkan/terverifikasi/ditagih pada unit itu.
"""
from db import db
from revrec_cogs import account_balance, ACCRUAL_ACCOUNT, WIP_ACCOUNT


def _i(v) -> int:
    return int(v or 0)


async def _gl(org: str, code: str) -> int:
    """Saldo sisi normal-kredit (kredit − debit)."""
    return -(await account_balance(org, code))


async def reconcile(org: str) -> dict:
    checks = []

    async def add(code, label, expected, hint):
        gl_bal = await _gl(org, code)
        checks.append({"code": code, "label": label, "gl": gl_bal, "subledger": int(expected),
                       "diff": gl_bal - int(expected), "ok": gl_bal == int(expected), "hint": hint})

    ap = await db.ap_invoices.find({"org_id": org, "status": {"$in": ["approved", "partial", "paid"]}},
                                   {"_id": 0, "net": 1, "paid": 1, "retention_held": 1,
                                    "retention_released": 1}).to_list(5000)
    await add("2-1100", "Utang Usaha vs Σ tagihan AP disetujui belum lunas",
              sum(_i(b.get("net")) - _i(b.get("paid")) for b in ap),
              "Tagihan disetujui tanpa jurnal, atau pembayaran tanpa jurnal.")
    await add("2-1200", "Utang Retensi vs Σ retensi ditahan",
              sum(_i(b.get("retention_held")) for b in ap if not b.get("retention_released")),
              "Retensi dicairkan tanpa jurnal / tagihan asal tidak ditandai.")
    cl = await db.contract_liabilities.find({"org_id": org, "recognized": {"$ne": True}},
                                            {"_id": 0, "balance": 1}).to_list(5000)
    await add("2-1400", "Uang Muka Penjualan vs Σ kewajiban kontrak (belum BAST)",
              sum(_i(c.get("balance")) for c in cl),
              "Penerimaan/pembatalan tanpa jurnal, atau jurnal RevRec yatim.")
    dep = await db.customer_deposits.find({"org_id": org}, {"_id": 0, "balance": 1}).to_list(5000)
    await add("2-1450", "Titipan Pelanggan vs Σ saldo titipan",
              sum(_i(d.get("balance")) for d in dep), "Mutasi titipan tanpa jurnal.")
    com = await db.commissions.find({"org_id": org, "status": "approved"}, {"_id": 0, "amount": 1}).to_list(5000)
    await add("2-1600", "Utang Komisi vs Σ komisi disetujui belum dibayar",
              sum(_i(c.get("amount")) for c in com), "Komisi disetujui/dibayar tanpa jurnal.")
    td = tc = 0
    async for je in db.journal_entries.find({"org_id": org}, {"_id": 0, "total_debit": 1, "total_credit": 1}):
        td += _i(je.get("total_debit"))
        tc += _i(je.get("total_credit"))
    checks.append({"code": "TB", "label": "Neraca saldo seimbang (Σ debit = Σ kredit)", "gl": td,
                   "subledger": tc, "diff": td - tc, "ok": td == tc,
                   "hint": "Ada jurnal tidak seimbang — periksa jurnal manual."})
    failed = [c for c in checks if not c["ok"]]
    pending = await db.events.count_documents({"org_id": org, "status": "pending"})
    failed_ev = await db.events.count_documents({"org_id": org, "status": "failed"})
    return {"ok": not failed and not failed_ev, "checks": checks, "failed": len(failed),
            "events_pending": pending, "events_failed": failed_ev}


async def hpp_per_unit(org: str, project_id: str) -> dict:
    import rab_engine as re_
    summary = await re_.project_summary(org, project_id)
    scope = await db.spk_scope_items.find({"org_id": org, "project_id": project_id},
                                          {"_id": 0, "unit_id": 1, "value": 1, "claim_id": 1,
                                           "build_item_id": 1}).to_list(10000)
    items = {i["id"]: i for i in await db.build_items.find(
        {"org_id": org, "id": {"$in": [s["build_item_id"] for s in scope]}},
        {"_id": 0, "id": 1, "status": 1, "verified_by": 1}).to_list(10000)} if scope else {}
    per = {}
    for s in scope:
        u = per.setdefault(s.get("unit_id"), {"contracted": 0, "verified": 0, "billed": 0})
        v = _i(s.get("value"))
        u["contracted"] += v
        it = items.get(s["build_item_id"]) or {}
        if it.get("status") == "done" and it.get("verified_by"):
            u["verified"] += v
        if s.get("claim_id"):
            u["billed"] += v
    rr = {r["unit_id"]: r for r in await db.revenue_recognitions.find(
        {"org_id": org, "project_id": project_id}, {"_id": 0, "unit_id": 1, "cogs": 1,
                                                    "cogs_source": 1, "revenue": 1}).to_list(5000)}
    rows = []
    for u in summary.get("per_unit") or []:
        p = per.get(u["unit_id"], {"contracted": 0, "verified": 0, "billed": 0})
        rec = rr.get(u["unit_id"])
        rows.append({
            **{k: u.get(k) for k in ("unit_id", "unit_code", "unit_type_code", "type", "status",
                                     "price", "rab_type", "shared", "hpp")},
            **p, "variance": _i(u.get("hpp")) - p["billed"],
            "realized_pct": round(p["billed"] / u["hpp"] * 100, 1) if u.get("hpp") else None,
            "over_rab": bool(u.get("hpp")) and p["contracted"] > _i(u.get("hpp")),
            "recognized": bool(rec), "recognized_cogs": _i((rec or {}).get("cogs")),
            "cogs_source": (rec or {}).get("cogs_source"),
            "revenue": _i((rec or {}).get("revenue")),
        })
    tot = {k: sum(r[k] for r in rows) for k in ("hpp", "rab_type", "shared", "contracted",
                                                  "verified", "billed", "recognized_cogs")}
    tot["variance"] = tot["hpp"] - tot["billed"]
    # Biaya proyek yang tidak melekat pada unit (SPK borongan tanpa lingkup, PO material, fasum).
    bills = await db.ap_invoices.find({"org_id": org, "project_id": project_id,
                                       "status": {"$in": ["approved", "partial", "paid"]},
                                       "bill_kind": {"$ne": "retention_release"}},
                                      {"_id": 0, "claimed": 1}).to_list(5000)
    ap_total = sum(_i(b.get("claimed")) for b in bills)
    return {
        "project_id": project_id, "project_name": summary.get("project_name"),
        "rows": rows, "totals": tot,
        "project_ap_total": ap_total, "project_ap_unallocated": max(0, ap_total - tot["billed"]),
        "gl_wip": await account_balance(org, WIP_ACCOUNT),
        "gl_accrual": -(await account_balance(org, ACCRUAL_ACCOUNT)),
        "units_recognized": sum(1 for r in rows if r["recognized"]),
        "units_over_rab": sum(1 for r in rows if r["over_rab"]),
        "note": ("Saldo WIP (1-1600) dan akrual HPP (2-1700) adalah saldo buku besar organisasi "
                 "— GL tidak berdimensi proyek."),
    }
