"""Pindah-PIC lead harus ikut memindahkan transaksi turunannya (audit KT-16).

Cacat nyata: `assign_lead` hanya mengubah `leads.assigned_to`. Deal, kontrak, AR, tagihan booking fee
dan pembeli yang sudah terbit dari lead itu tetap atas nama PIC LAMA. Karena sales hanya boleh
mengakses data yang `assigned_to`-nya dirinya, PIC baru terkunci dari transaksi lead yang baru
diterimanya (403 pada deal/kontrak), sementara PIC lama masih bisa melihat & mengubahnya.

Aturan: hanya baris yang masih dipegang PIC LAMA yang dipindah (baris yang sengaja dipegang orang
lain tidak ditimpa). Komisi TIDAK dipindah — komisi mengikuti siapa yang menjual, bukan siapa yang
memegang lead sekarang.
"""
from db import db


async def reassign_children(org: str, lead_id: str, old: str, new: str, ts: str) -> dict:
    """Pindahkan `assigned_to`/`owner` turunan lead dari `old` ke `new`. Kembalikan jumlah per jenis."""
    if not old or old == new:
        return {}
    out = {}
    s = {"$set": {"assigned_to": new, "updated_at": ts}}
    deal_ids = await db.deals.distinct("id", {"org_id": org, "lead_id": lead_id})
    r = await db.deals.update_many({"org_id": org, "lead_id": lead_id, "assigned_to": old}, s)
    out["deal"] = r.modified_count
    r = await db.contracts.update_many({"org_id": org, "lead_id": lead_id, "assigned_to": old}, s)
    out["kontrak"] = r.modified_count
    r = await db.customers.update_many(
        {"org_id": org, "assigned_to": old, "$or": [{"lead_id": lead_id}, {"lead_ids": lead_id}]}, s)
    out["pembeli"] = r.modified_count
    if deal_ids:
        r = await db.ar_invoices.update_many({"org_id": org, "deal_id": {"$in": deal_ids}, "assigned_to": old}, s)
        out["tagihan AR"] = r.modified_count
        r = await db.booking_fee_invoices.update_many(
            {"org_id": org, "deal_id": {"$in": deal_ids}, "assigned_to": old}, s)
        out["booking fee"] = r.modified_count
    r = await db.conversations.update_many(
        {"org_id": org, "lead_id": lead_id, "owner": old}, {"$set": {"owner": new, "updated_at": ts}})
    out["percakapan WA"] = r.modified_count
    return {k: v for k, v in out.items() if v}
