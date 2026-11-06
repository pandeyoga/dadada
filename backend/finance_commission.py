"""Komisi sales: persetujuan & pembayaran — dipisah dari finance_engine.py demi batas NFR 800 baris.
Tetap diekspos lewat `finance_engine.approve_commission/pay_commission` (pemanggil lama tidak berubah).

PK-03: komisi hanya bisa maju (pending → approved → paid); `approve` pada komisi `paid` ditolak.
PK-02: setiap transisi diklaim atomik SEBELUM event terbit (approve/bayar bersamaan = satu akrual / satu kas keluar).
PK-12: komisi untuk deal yang dibatalkan tidak disetujui/dibayar.
"""
from db import db, ORG_ID
from core_utils import now_iso
from engine import emit


async def notify_finance(*a, **kw):  # impor tertunda (finance_engine mengimpor modul ini di akhir berkas)
    from finance_engine import notify_finance as _nf
    return await _nf(*a, **kw)


async def _assert_deal_not_cancelled(com: dict, org_id: str) -> None:
    """PK-12: komisi tidak disetujui/dibayar untuk penjualan yang sudah dibatalkan."""
    from deal_state import deal_of, is_cancelled
    deal = await deal_of(org_id, com.get("deal_id"), {"_id": 0, "status": 1, "cancellation_id": 1})
    if deal and is_cancelled(deal):
        raise ValueError("Deal komisi ini sudah DIBATALKAN — komisi tidak boleh disetujui atau dibayar "
                         "untuk penjualan yang batal.")


async def approve_commission(commission_id, approver, org_id=ORG_ID) -> dict:
    from idempotency import reserved
    com = await db.commissions.find_one({"id": commission_id, "org_id": org_id}, {"_id": 0})
    if not com:
        raise ValueError("Komisi tidak ditemukan.")
    if com.get("status") == "approved":
        return com
    if com.get("status") != "pending":
        # PK-03: dulu komisi berstatus `paid` jatuh ke sini, dimundurkan ke `approved` dan menerbitkan
        # akrual baru → dibayar ulang. Transisi mundur ditolak.
        raise ValueError(f"Komisi berstatus '{com.get('status')}' tidak dapat disetujui lagi "
                         "(hanya komisi menunggu persetujuan).")
    await _assert_deal_not_cancelled(com, org_id)
    ts = now_iso()
    # PK-02/03: klaim atomik pending → approved SEBELUM emit (approve bersamaan = satu akrual).
    async with reserved("commissions", {"id": commission_id, "org_id": org_id}, {"status": "pending"},
                        {"$set": {"status": "approved", "approved_by": approver, "approved_at": ts,
                                  "updated_at": ts}},
                        undo={"$set": {"status": "pending", "approved_by": None, "approved_at": None}},
                        what="Komisi"):
        await emit("commission.approved", "deal", com.get("deal_id"),
                   {"commission_id": commission_id}, org_id=org_id)
    await notify_finance(org_id, "Komisi disetujui",
                         f"Komisi Rp {com.get('amount', 0):,} disetujui.", "finance",
                         "deal", com.get("deal_id"), extra_emails=[com.get("assigned_to")])
    return await db.commissions.find_one({"id": commission_id, "org_id": org_id}, {"_id": 0})


async def pay_commission(commission_id, payer, org_id=ORG_ID, cash_account_id=None) -> dict:
    """Bayarkan komisi yang sudah disetujui (approved -> paid). Idempotent; dibayar SEKALI saja."""
    from idempotency import reserved
    com = await db.commissions.find_one({"id": commission_id, "org_id": org_id}, {"_id": 0})
    if not com:
        raise ValueError("Komisi tidak ditemukan.")
    if com.get("status") == "paid":
        return com
    if com.get("status") != "approved":
        raise ValueError("Komisi harus disetujui terlebih dahulu sebelum dibayar.")
    await _assert_deal_not_cancelled(com, org_id)
    import cash_bank as _cb
    cash_code = await _cb.resolve_code(org_id, cash_account_id, "1-1200")
    cash_acc = await _cb.account_by_code(org_id, cash_code)
    cash_account_id = (cash_acc or {}).get("id")
    ts = now_iso()
    # PL-03: kunci rekening + cek dana; jurnal komisi diposting lewat event, jadi antrean event dikosongkan
    # sebelum kunci dilepas (flush_events) — kalau tidak, pembayaran berikutnya masih membaca saldo lama.
    async with _cb.funds_guard(org_id, int(com.get("amount", 0)), cash_account_id=cash_account_id,
                               code=cash_code, kind="pembayaran komisi", flush_events=True):
        # PK-02/03: klaim atomik approved → paid SEBELUM emit commission.paid.
        async with reserved("commissions", {"id": commission_id, "org_id": org_id}, {"status": "approved"},
                            {"$set": {"status": "paid", "paid_by": payer, "paid_at": ts, "updated_at": ts,
                                      "cash_account_id": cash_account_id,
                                      "cash_account_name": (cash_acc or {}).get("name")}},
                            undo={"$set": {"status": "approved"}}, what="Komisi"):
            await emit("commission.paid", "commission", commission_id,
                       {"amount": int(com.get("amount", 0)), "cash_account_id": cash_account_id},
                       org_id=org_id)
    await notify_finance(org_id, "Komisi dibayar",
                         f"Komisi Rp {com.get('amount', 0):,} telah dibayarkan.", "finance",
                         "deal", com.get("deal_id"), extra_emails=[com.get("assigned_to")])
    return await db.commissions.find_one({"id": commission_id, "org_id": org_id}, {"_id": 0})
