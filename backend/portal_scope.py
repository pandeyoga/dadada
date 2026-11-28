"""Kunci pemilik baris untuk portal pembeli (dipisah dari `routers/portal_router.py`, batas 800 baris).

Akun portal pemegang reservasi (LEAD, Fase 69B) tidak punya `customer_id`. Saringan lama
`customer_id=pu.get("customer_id")` lalu berubah makna diam-diam: DILEWATI oleh mesin yang hanya
menyaring bila nilainya terisi (= seluruh baris organisasi), atau mencocokkan `customer_id: null`
(= setiap baris tanpa pelanggan, milik orang lain). Di sini kunci pemilik tidak pernah kosong:

- pembeli penuh: `customer_id`-nya — perilaku lama, tidak berubah;
- akun tanpa `customer_id`: deal milik akun itu (reservasinya). `deal_id` adalah kunci yang memang
  dibawa komplain, bukti transfer (termasuk booking fee) dan klaim garansi;
- tanpa keduanya: daftar deal kosong, jadi tidak ada baris yang cocok.

"Rumah saya" (garansi, BAST, klaim garansi) hanya diturunkan dari deal yang TIDAK `cancelled`: unit deal
batal sudah dilepas dan bisa dijual ulang, jadi menurunkannya dari deal batal = membaca BAST (nama & nomor
pemilik baru), klaim garansi, dan mengajukan/mengakui klaim di rumah orang lain. Deal batal tetap terbaca
lewat jalurnya sendiri (refund di `/portal/cancellations`, komplain & bukti transfernya).
"""
from complaint_intake import buyer_customer, buyer_deals
from db import db, ORG_ID


async def owner(pu: dict) -> dict:
    """Saringan pemilik sebagai argumen mesin (`payment_intake.listing`, `warranty_engine.list_claims`)."""
    if pu.get("customer_id"):
        return {"customer_id": pu["customer_id"]}
    deals = await buyer_deals(pu, await buyer_customer(pu))
    return {"deal_ids": [d["id"] for d in deals]}


async def owner_query(pu: dict) -> dict:
    """Saringan pemilik komplain sebagai potongan kueri Mongo: kunci di atas, ditambah baris yang dibuat akun
    portal ini sendiri (`portal_user_id`: tiket chat Tanya Estora tanpa deal, mis. pembeli reservasi > 1 unit)."""
    own = await owner(pu)
    key = {"customer_id": own["customer_id"]} if own.get("customer_id") else {"deal_id": {"$in": own["deal_ids"]}}
    return {"$or": [key, {"portal_user_id": pu["id"]}]} if pu.get("id") else key


async def active_deals(pu: dict) -> list:
    """Deal pembeli yang tidak `cancelled` (dasar "rumah saya")."""
    return [d for d in await buyer_deals(pu, await buyer_customer(pu)) if d.get("status") != "cancelled"]


def owns(row: dict, deal_ids, unit_ids) -> bool:
    """BAST/klaim milik pembeli: dibuat untuk deal aktifnya sendiri; baris lama tanpa deal -> lewat unitnya."""
    return row.get("deal_id") in deal_ids if row.get("deal_id") else row.get("unit_id") in unit_ids


async def my_units(pu: dict, deals: list = None) -> list:
    """Rumah milik pembeli ini (dari deal aktifnya) — dipakai layar garansi portal."""
    org, out = pu.get("org_id", ORG_ID), []
    for d in (await active_deals(pu)) if deals is None else deals:
        if not d.get("unit_id"):
            continue
        unit = await db.units.find_one({"id": d["unit_id"], "org_id": org},
                                       {"_id": 0, "id": 1, "code": 1, "type": 1, "project_id": 1, "status": 1})
        if unit:
            out.append({**unit, "deal_id": d["id"]})
    return out


async def my_handovers(pu: dict) -> list:
    """BAST untuk deal aktif pembeli ini (bukan sekadar unit yang sama: unit bisa dijual ulang)."""
    deals = await active_deals(pu)
    unit_ids = [u["id"] for u in await my_units(pu, deals)]
    q = {"org_id": pu.get("org_id", ORG_ID), "$or": [{"deal_id": {"$in": [d["id"] for d in deals]}},
                                                     {"deal_id": None, "unit_id": {"$in": unit_ids}}]}
    return await db.unit_handovers.find(q, {"_id": 0}).sort("handed_over_at", -1).to_list(50)
