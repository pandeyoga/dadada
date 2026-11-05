"""Penjaga reservasi: lead tertutup & batas unit aktif per lead (audit KT-18, KT-20).

Dua celah di jalur reservasi:

* KT-18 — `reservation.max_active_per_lead` hanya diperiksa di router `/deals/reserve` dengan pola
  "hitung lalu reservasi" tanpa kunci. Dua permintaan serentak untuk satu lead (unit berbeda)
  sama-sama menghitung 0 lalu sama-sama lolos; konversi PENAWARAN tidak memeriksa batas sama
  sekali (docstring-nya mengklaim aturan ada di router, padahal `sales_reserve.reserve` tidak
  memeriksa). Sekarang pemeriksaan ada di `sales_reserve.reserve` — SATU jalur reservasi — di
  dalam kunci per-lead, sehingga hitungan dan penulisan deal tidak bisa disela permintaan lain.
* KT-20 — lead berstatus `lost`/`recycle` bisa memesan unit: deal hidup tertinggal pada lead yang
  sudah ditutup, tahap lead tidak ikut maju (`advance_on_deal` diam), dan konversi kemudian
  menulis `lost → won` tanpa jejak sah. Lead tertutup harus dihidupkan lebih dulu (daur ulang).
"""
from contextlib import asynccontextmanager

import reference as ref
import settings_store as cfg
from db import db
from idempotency import Conflict, mutex

ACTIVE_STATUSES = ["reserved", "booked"]
CLOSED_STAGES = ("lost", "recycle")


def closed_reason(lead: dict) -> str:
    """Alasan lead TIDAK boleh memesan unit (atau None)."""
    stage = (lead or {}).get("stage")
    if stage in CLOSED_STAGES:
        return (f"Lead {lead.get('name') or 'ini'} berstatus "
                f"'{ref.label_of('lead_stage', stage)}' — tidak bisa memesan unit. Hidupkan lagi "
                "lead-nya lebih dulu (daur ulang → tahap Nurturing) bila pembeli ini memang kembali.")
    return None


async def active_count(org: str, lead_id: str) -> int:
    return await db.deals.count_documents(
        {"org_id": org, "lead_id": lead_id, "status": {"$in": ACTIVE_STATUSES}})


@asynccontextmanager
async def slot(org: str, lead: dict, *, allow_over: bool = False):
    """Kunci reservasi per lead: pemeriksaan lead terbuka + batas unit aktif + penulisan deal
    terjadi di bawah satu kunci. `allow_over` = pemanggil SUDAH memverifikasi override batas
    (peran pengecualian + alasan) — hanya batas unit yang dilewati, status lead tetap diperiksa."""
    async with mutex(f"reserve:lead:{lead['id']}", wait=15, ttl=45,
                     what="Reservasi untuk lead ini"):
        fresh = await db.leads.find_one({"id": lead["id"], "org_id": org},
                                        {"_id": 0, "id": 1, "name": 1, "stage": 1}) or lead
        alasan = closed_reason(fresh)
        if alasan:
            raise ValueError(alasan)
        if not allow_over:
            max_active = int(await cfg.get("reservation.max_active_per_lead", org_id=org) or 1)
            n = await active_count(org, lead["id"])
            if n >= max_active:
                override_roles = list(await cfg.get("reservation.override_roles", org_id=org) or [])
                raise Conflict(
                    f"Lead ini sudah memegang {n} unit aktif (batas {max_active}). "
                    "Hanya peran " + ", ".join(override_roles or ["-"])
                    + " yang boleh melewati batas, dengan alasan (≥10 karakter) lewat Buat Reservasi.")
        yield
