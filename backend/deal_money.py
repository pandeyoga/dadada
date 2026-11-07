"""Mutex per-DEAL untuk jalur uang yang menyentuh kuitansi/kewajiban kontrak/jurnal sebuah deal (audit FZ-07, PK3-11).

Latar belakang: hapus-paksa deal (`force_delete.delete_deal_cascade`), hapus-paksa kuitansi, void kuitansi, dan
penerimaan baru (`finance_engine.apply_receipt`) masing-masing membaca anak-anak deal lalu menulis — tanpa kunci
bersama. Akibat yang terukur: uang pembeli (HTTP 200) tercatat tanpa jurnal ketika deal dihapus di saat yang sama;
void yang menerbitkan jurnal di tengah penghapusan meninggalkan jurnal yatim; hapus kuitansi 2× membalik kewajiban
kontrak dua kali (−Rp 170 jt).

Satu kunci `deal.money:<org>:<deal>` kini dipegang oleh keempat jalur itu. Kunci ini ANTRE (mutex) bukan gagal-cepat,
jadi penerimaan yang kebetulan bersamaan dengan penghapusan menunggu lalu melihat AR-nya sudah tiada
("Jadwal AR belum dibuat") — bukan lagi tercatat sebagai uang masuk tanpa tuan.

`apply_receipt` di sini membungkus implementasi asli `finance_engine._apply_receipt_unlocked` (finance_engine.py
sudah melewati batas baris, jadi pembungkusnya hidup di modul ini dan diekspor ulang di ujung berkas itu).
"""
from contextlib import asynccontextmanager

from db import ORG_ID
from idempotency import mutex


@asynccontextmanager
async def deal_money(org: str, deal_id: str):
    """`async with deal_money(org, deal_id): ...` — satu pelaksana per deal. `deal_id` kosong = tanpa kunci."""
    if not deal_id:
        yield
        return
    async with mutex(f"deal.money:{org}:{deal_id}", wait=15, ttl=60, what="Transaksi uang deal ini"):
        yield


async def apply_receipt(*args, **kwargs):
    """Terima pembayaran (lihat `finance_engine._apply_receipt_unlocked`) di bawah mutex per-deal."""
    import finance_engine as fe
    deal_id = args[0] if args else kwargs.get("deal_id")
    org = args[5] if len(args) > 5 else kwargs.get("org_id", ORG_ID)
    async with deal_money(org, deal_id):
        return await fe._apply_receipt_unlocked(*args, **kwargs)   # noqa: SLF001
