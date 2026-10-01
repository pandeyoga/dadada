"""PLAFON SP3K vs PORSI BANK pada piutang (AR).

Saat bank menyetujui plafon yang BERBEDA dari porsi bank yang direncanakan pada skema pembayaran:
  * plafon < porsi bank  → selisih menjadi KEWAJIBAN PEMBELI: termin baru "Selisih Plafon KPR"
    (payer=buyer, jatuh tempo wajib diisi) dan porsi bank dikurangi sebesar itu;
  * plafon > porsi bank  → porsi bank dinaikkan, termin pembeli (yang belum dibayar) dikurangi.
Total piutang TIDAK berubah — hanya berpindah payer, jadi GL/kas tidak tersentuh; alokasi setoran
pembeli & pencairan bank (`finance_engine._allocate`) otomatis mengikuti tanda `payer`.
"""
import logging

import finance_engine as fe
from core_utils import new_id, now_iso
from db import db
from engine import add_activity
from finance_engine import notify_finance

logger = logging.getLogger("sipro.kpr_plafon")
SHORTFALL_KIND = "kpr_shortfall"
SHORTFALL_LABEL = "Selisih Plafon KPR (kewajiban pembeli)"


def _rp(v) -> str:
    return "Rp " + f"{int(v or 0):,}".replace(",", ".")


def _movable(it: dict) -> bool:
    """Termin pembeli unit yang boleh dialihkan ke porsi bank (bukan add-on / selisih plafon)."""
    return (not fe.is_bank_item(it) and not it.get("kpr_excluded")
            and it.get("basis") != "addon" and it.get("kind") != SHORTFALL_KIND)


def _unpaid(it: dict) -> int:
    return max(0, int(it.get("amount") or 0) - int(it.get("paid_amount") or 0))


def _fold_back_shortfall(items: list) -> list:
    """Selisih plafon lama yang belum dibayar dikembalikan ke porsi bank sebelum dihitung ulang."""
    bank = [i for i in items if fe.is_bank_item(i)]
    out = []
    for it in items:
        if it.get("kind") == SHORTFALL_KIND and bank:
            back = _unpaid(it)
            bank[-1]["amount"] = int(bank[-1]["amount"]) + back
            if int(it.get("paid_amount") or 0) <= 0:
                continue
            it = {**it, "amount": int(it["paid_amount"]), "value": int(it["paid_amount"]), "status": "paid"}
        out.append(it)
    return out


def preview(inv: dict, plafon: int) -> dict:
    """Bandingkan plafon dengan porsi bank AR tanpa mengubah apa pun."""
    items = _fold_back_shortfall([dict(i) for i in (inv or {}).get("items") or []])
    bank = [i for i in items if fe.is_bank_item(i)]
    bank_total = sum(int(i.get("amount") or 0) for i in bank)
    buyer_reducible = sum(_unpaid(i) for i in items if _movable(i))
    bank_reducible = sum(_unpaid(i) for i in bank)
    diff = int(plafon or 0) - bank_total
    if not bank:
        kind = "no_bank_items"
    elif diff == 0:
        kind = "match"
    elif diff < 0:
        kind = "shortfall"
    else:
        kind = "excess"
    return {"has_bank_items": bool(bank), "bank_portion": bank_total, "plafon": int(plafon or 0),
            "diff": diff, "shortfall": max(0, -diff), "excess": max(0, diff), "kind": kind,
            "buyer_reducible": buyer_reducible, "bank_reducible": bank_reducible,
            "requires_due_date": kind == "shortfall",
            "excess_ok": kind != "excess" or diff <= buyer_reducible,
            "shortfall_ok": kind != "shortfall" or -diff <= bank_reducible}


async def reconcile(org: str, contract: dict, app: dict, plafon: int, due_date: str,
                    actor: str) -> dict:
    """Sesuaikan AR dengan plafon SP3K. Return ringkasan (disimpan ke `financing_apps.plafon_reconcile`)."""
    inv = await db.ar_invoices.find_one({"org_id": org, "deal_id": contract["deal_id"]}, {"_id": 0})
    if not inv:
        return {"applied": False, "kind": "no_ar", "plafon": int(plafon),
                "note": "Jadwal tagihan belum terbit — plafon dicatat, porsi bank belum bisa disesuaikan."}
    items = _fold_back_shortfall([dict(i) for i in inv.get("items") or []])
    pv = preview({"items": items}, plafon)
    ts = now_iso()
    summary = {"applied": False, "at": ts, "by": actor, **pv}
    if pv["kind"] == "no_bank_items":
        summary["note"] = "Skema pembayaran tidak menandai porsi bank — tidak ada yang disesuaikan."
        return summary
    bank = sorted([i for i in items if fe.is_bank_item(i)], key=lambda x: x.get("due_date") or "")
    moved = []
    if pv["kind"] == "shortfall":
        short = pv["shortfall"]
        if not due_date:
            raise ValueError(f"Plafon {_rp(plafon)} lebih kecil dari porsi bank {_rp(pv['bank_portion'])} — "
                             f"selisih {_rp(short)} menjadi kewajiban pembeli. Isi JATUH TEMPO selisih plafon.")
        if short > pv["bank_reducible"]:
            raise ValueError(f"Selisih {_rp(short)} melebihi porsi bank yang belum dicairkan {_rp(pv['bank_reducible'])}.")
        left = short
        for it in reversed(bank):
            take = min(_unpaid(it), left)
            if take <= 0:
                continue
            it["amount"] = int(it["amount"]) - take
            it["value"] = it["amount"] if it.get("basis") != "percent" else it.get("value")
            it["status"] = "paid" if int(it.get("paid_amount") or 0) >= it["amount"] and it["amount"] > 0 else (
                "partial" if int(it.get("paid_amount") or 0) > 0 else "unpaid")
            moved.append({"item_id": it["id"], "label": it["label"], "amount": -take})
            left -= take
            if left <= 0:
                break
        items = [i for i in items if int(i.get("amount") or 0) > 0 or int(i.get("paid_amount") or 0) > 0]
        new_item = {"id": new_id(), "label": SHORTFALL_LABEL, "basis": "amount", "value": short,
                    "amount": short, "due_date": due_date, "grace_days": 0, "due_rule": None,
                    "event_based": False, "payer": "buyer", "kind": SHORTFALL_KIND,
                    "note": f"Plafon SP3K {_rp(plafon)} < porsi bank {_rp(pv['bank_portion'])}",
                    "status": "unpaid", "paid_amount": 0}
        items.append(new_item)
        summary.update({"applied": True, "shortfall_item_id": new_item["id"], "due_date": due_date})
    elif pv["kind"] == "excess":
        extra = pv["excess"]
        if extra > pv["buyer_reducible"]:
            raise ValueError(f"Plafon {_rp(plafon)} melebihi porsi bank {_rp(pv['bank_portion'])} sebesar "
                             f"{_rp(extra)}, tetapi termin pembeli yang masih bisa dialihkan hanya "
                             f"{_rp(pv['buyer_reducible'])}.")
        left = extra
        movable = sorted([i for i in items if _movable(i)], key=lambda x: x.get("due_date") or "")
        for it in reversed(movable):
            take = min(_unpaid(it), left)
            if take <= 0:
                continue
            it["amount"] = int(it["amount"]) - take
            it["status"] = "paid" if int(it.get("paid_amount") or 0) >= it["amount"] and it["amount"] > 0 else (
                "partial" if int(it.get("paid_amount") or 0) > 0 else "unpaid")
            moved.append({"item_id": it["id"], "label": it["label"], "amount": -take})
            left -= take
            if left <= 0:
                break
        items = [i for i in items if int(i.get("amount") or 0) > 0 or int(i.get("paid_amount") or 0) > 0]
        bank[-1]["amount"] = int(bank[-1]["amount"]) + extra
        bank[-1]["status"] = "partial" if int(bank[-1].get("paid_amount") or 0) > 0 else "unpaid"
        moved.append({"item_id": bank[-1]["id"], "label": bank[-1]["label"], "amount": extra})
        summary["applied"] = True
    else:
        summary["applied"] = True
    summary["moved"] = moved
    summary["bank_portion_after"] = sum(int(i.get("amount") or 0) for i in items if fe.is_bank_item(i))
    total_before = int(inv.get("total") or 0)
    total_after = sum(int(i.get("amount") or 0) for i in items)
    if total_after != total_before:
        logger.warning("Total AR berubah saat rekonsiliasi plafon (%s → %s) deal %s", total_before, total_after, inv["deal_id"])
        await db.ar_invoices.update_one({"id": inv["id"]}, {"$set": {"total": total_after}})
        inv["total"] = total_after
    await fe._recalc_invoice(inv, items, ts)
    await db.contracts.update_one({"id": contract["id"]}, {"$set": {"costs.plafon_kredit": int(plafon), "updated_at": ts}})
    if pv["kind"] == "shortfall":
        body = (f"Plafon SP3K {_rp(plafon)} lebih kecil dari porsi bank {_rp(pv['bank_portion'])} — selisih "
                f"{_rp(pv['shortfall'])} menjadi kewajiban pembeli (termin '{SHORTFALL_LABEL}', jatuh tempo {due_date}).")
        await notify_finance(org, "Selisih plafon KPR → tagihan pembeli",
                             f"Unit {contract.get('unit_code') or '-'}: {body}", "finance", "deal",
                             contract["deal_id"], extra_emails=[contract.get("assigned_to")])
    elif pv["kind"] == "excess":
        body = (f"Plafon SP3K {_rp(plafon)} lebih besar dari porsi bank {_rp(pv['bank_portion'])} — porsi bank "
                f"dinaikkan {_rp(pv['excess'])}, termin pembeli berkurang sebesar itu.")
    else:
        body = f"Plafon SP3K {_rp(plafon)} sama dengan porsi bank pada jadwal tagihan."
    await add_activity(entity_type="customer", entity_id=contract.get("customer_id"), type="finance",
                       actor=actor, org_id=org, body=body)
    summary["note"] = body
    return summary
