"""Kunci pemilik baris untuk portal pembeli (dipisah dari `routers/portal_router.py`, batas 800 baris).

Akun portal pemegang reservasi (LEAD, Fase 69B) tidak punya `customer_id`. Saringan lama
`customer_id=pu.get("customer_id")` lalu berubah makna diam-diam: DILEWATI oleh mesin yang hanya
menyaring bila nilainya terisi (= seluruh baris organisasi), atau mencocokkan `customer_id: null`
(= setiap baris tanpa pelanggan, milik orang lain). Di sini kunci pemilik tidak pernah kosong:

- pembeli penuh: `customer_id`-nya — perilaku lama, tidak berubah;
- akun tanpa `customer_id`: deal milik akun itu (reservasinya). `deal_id` adalah kunci yang memang
  dibawa komplain, bukti transfer (termasuk booking fee) dan klaim garansi;
- tanpa keduanya: daftar deal kosong, jadi tidak ada baris yang cocok.
"""
from complaint_intake import buyer_customer, buyer_deals


async def owner(pu: dict) -> dict:
    """Saringan pemilik sebagai argumen mesin (`payment_intake.listing`, `warranty_engine.list_claims`)."""
    if pu.get("customer_id"):
        return {"customer_id": pu["customer_id"]}
    deals = await buyer_deals(pu, await buyer_customer(pu))
    return {"deal_ids": [d["id"] for d in deals]}


async def owner_query(pu: dict) -> dict:
    """Saringan pemilik yang sama sebagai potongan kueri Mongo."""
    own = await owner(pu)
    if own.get("customer_id"):
        return {"customer_id": own["customer_id"]}
    return {"deal_id": {"$in": own["deal_ids"]}}
