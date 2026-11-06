"""Keadaan deal/kontrak yang dibaca BERSAMA oleh semua jalur uang (satu sumber kebenaran).

Latar belakang (audit PK3-05, FZ-01/02/03/08, PK3-06, PK-12): BAST/pengakuan pendapatan, void kuitansi, tahap KPR,
setoran pajak, komisi dan fee marketing masing-masing memeriksa — atau tidak memeriksa — status deal dengan caranya
sendiri. Akibatnya deal yang sudah DIBATALKAN bisa hidup kembali: diakui pendapatan Rp 600 jt, AR batal muncul
lagi, pajak Rp 113 jt keluar dari bank. Predikat "batal" ada di SATU tempat ini.
"""
from db import ORG_ID, db


def is_cancelled(deal: dict) -> bool:
    """Deal dianggap batal bila statusnya `cancelled` ATAU sudah tertaut pengajuan pembatalan yang disetujui."""
    d = deal or {}
    return d.get("status") == "cancelled" or bool(d.get("cancellation_id"))


def assert_not_cancelled(deal: dict, what: str = "Tindakan ini") -> None:
    if is_cancelled(deal):
        raise ValueError(f"Deal ini sudah DIBATALKAN — {what} tidak boleh dilakukan untuk penjualan yang batal.")


async def deal_of(org: str, deal_id: str, projection: dict = None) -> dict:
    return await db.deals.find_one({"id": deal_id, "org_id": org or ORG_ID}, projection or {"_id": 0}) or {}


async def assert_deal_not_cancelled(org: str, deal_id: str, what: str = "Tindakan ini") -> dict:
    deal = await deal_of(org, deal_id)
    assert_not_cancelled(deal, what)
    return deal


def assert_can_recognize_revenue(deal: dict) -> None:
    """Pengakuan pendapatan (BAST) hanya untuk deal yang BOOKED dan tidak batal.

    Deal `reserved` belum punya kesepakatan/AR (FN-23); deal `cancelled` tidak boleh hidup lagi (PK3-05/FZ-03);
    deal `completed` yang sudah punya pengakuan ditangani idempoten oleh pemanggil; yang `completed` TANPA
    pengakuan (data cacat) tetap boleh diakui supaya bisa dibereskan.
    """
    if not deal:
        raise ValueError("Deal tidak ditemukan.")
    assert_not_cancelled(deal, "pengakuan pendapatan (BAST)")
    if deal.get("status") not in ("booked", "completed"):
        raise ValueError(f"Pengakuan pendapatan (BAST) hanya untuk deal berstatus 'booked' — deal ini "
                         f"'{deal.get('status')}'. Selesaikan booking terlebih dahulu.")
