"""HPP saat BAST — dari RAB (bukan tebakan 70% harga).

Sebelum ini `recognize_revenue` selalu memakai `cogs = 70% × harga` dan mengkredit WIP
sebesar itu, padahal WIP yang benar-benar dikapitalisasi (tagihan subkon/material yang
disetujui) bisa jauh lebih kecil → 1-1600 negatif dan laba kotor fiktif.

Aturan sekarang:
  * HPP unit = HPP RAB per unit (`rab_engine.project_summary().per_unit[].hpp` = RAB tipe +
    alokasi biaya bersama) bila RAB tipe unit ada; bila tidak, estimasi 70% dipertahankan
    tetapi DITANDAI `cogs_source = "estimate_70pct"`.
  * Kredit 1-1600 WIP hanya sebesar saldo WIP yang tersedia; sisanya diakui sebagai
    2-1700 Utang Biaya Konstruksi Ditaksir (akrual biaya yang belum ditagih subkon).
    Tagihan subkon/WIP berikutnya melunasi akrual itu lebih dulu (`gl_engine._gl_ap_approved`).
"""
from db import db

ACCRUAL_ACCOUNT = "2-1700"
WIP_ACCOUNT = "1-1600"
ESTIMATE_PCT = 0.7


async def unit_cogs(org_id: str, deal: dict) -> dict:
    price = int(deal.get("price") or 0)
    est = round(price * ESTIMATE_PCT)
    unit_id, project_id = deal.get("unit_id"), deal.get("project_id")
    if not (unit_id and project_id):
        return {"cogs": est, "cogs_source": "estimate_70pct", "rab_hpp": None}
    import rab_engine as re_
    try:
        summary = await re_.project_summary(org_id, project_id)
    except Exception:  # noqa: BLE001 — RAB rusak tidak boleh menggagalkan BAST
        return {"cogs": est, "cogs_source": "estimate_70pct", "rab_hpp": None}
    row = next((u for u in summary.get("per_unit") or [] if u.get("unit_id") == unit_id), None)
    hpp = int((row or {}).get("hpp") or 0)
    if hpp > 0 and int((row or {}).get("rab_type") or 0) > 0:
        return {"cogs": hpp, "cogs_source": "rab", "rab_hpp": hpp,
                "rab_type": int(row.get("rab_type") or 0), "rab_shared": int(row.get("shared") or 0)}
    return {"cogs": est, "cogs_source": "estimate_70pct", "rab_hpp": hpp or None}


async def account_balance(org_id: str, code: str) -> int:
    """Saldo sisi normal-debit (debit − kredit) sebuah akun dari jurnal."""
    dr = cr = 0
    async for je in db.journal_entries.find({"org_id": org_id, "lines.account_code": code},
                                            {"_id": 0, "lines": 1}):
        for ln in je.get("lines", []):
            if ln.get("account_code") == code:
                dr += int(ln.get("debit", 0) or 0)
                cr += int(ln.get("credit", 0) or 0)
    return dr - cr


async def cogs_credit_lines(org_id: str, cogs: int) -> list:
    """Kredit WIP sebatas saldonya; sisanya akrual 2-1700."""
    if cogs <= 0:
        return []
    wip = max(0, await account_balance(org_id, WIP_ACCOUNT))
    from_wip = min(cogs, wip)
    lines = []
    if from_wip > 0:
        lines.append({"account_code": WIP_ACCOUNT, "debit": 0, "credit": from_wip})
    if cogs - from_wip > 0:
        lines.append({"account_code": ACCRUAL_ACCOUNT, "debit": 0, "credit": cogs - from_wip,
                      "memo": "HPP diakui melebihi WIP terkapitalisasi — biaya belum ditagih"})
    return lines


async def accrual_debit_lines(org_id: str, amount: int) -> list:
    """Tagihan WIP baru melunasi akrual HPP lebih dulu, sisanya dikapitalisasi ke WIP."""
    accrual = max(0, -(await account_balance(org_id, ACCRUAL_ACCOUNT)))
    to_accrual = min(amount, accrual)
    lines = []
    if to_accrual > 0:
        lines.append({"account_code": ACCRUAL_ACCOUNT, "debit": to_accrual, "credit": 0,
                      "memo": "Realisasi biaya atas HPP yang sudah diakui saat BAST"})
    if amount - to_accrual > 0:
        lines.append({"account_code": WIP_ACCOUNT, "debit": amount - to_accrual, "credit": 0})
    return lines
