"""Kunci kerja pendek untuk operasi uang (audit IN-01).

Beda dengan `idempotency.once()`: kunci `once` SENGAJA bertahan setelah operasi sukses (menolak
permintaan identik yang datang menyusul), sedangkan `locked()` hanya menahan selama operasi
berjalan lalu dilepas — dipakai untuk pola "kunci → baca ulang status → kerjakan", sehingga
pemakai yang sah (mis. verifikasi → batal verifikasi → verifikasi lagi) tidak tertahan 15 detik.

Dibangun di atas `idempotency.claim/release` (index unik MongoDB, atomik). Bila proses mati di
tengah jalan, kunci kedaluwarsa sendiri sesudah `ttl` detik.
"""
from contextlib import asynccontextmanager

import idempotency as idem


@asynccontextmanager
async def locked(op: str, *parts, ttl: int = 60, what: str = "Proses ini"):
    """`async with locked("intake.verify", intake_id): ...` — satu pelaksana pada satu waktu.

    Pelaksana kedua yang datang selagi yang pertama berjalan mendapat `Conflict` (HTTP 409)
    SEBELUM menyentuh subledger apa pun. Selalu dilepas, sukses maupun gagal.
    """
    key = idem.make_key("lock:" + op, *parts)
    await idem.claim(key, ttl, what)
    try:
        yield key
    finally:
        await idem.release(key)
