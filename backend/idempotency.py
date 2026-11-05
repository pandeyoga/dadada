"""Penjaga permintaan uang: kunci idempotensi + compare-and-swap (CAS).

Latar belakang (audit IN-01, IN-04, PK-02, GL-22, KT-02/KT-08): hampir semua jalur yang
menggerakkan uang bekerja dengan pola "baca status → hitung → tulis". Dua permintaan yang
datang bersamaan (klik ganda di dua tab, dua staf, retry jaringan) sama-sama membaca keadaan
LAMA, sama-sama lolos pengecekan, lalu sama-sama menulis — uang keluar/masuk dua kali sementara
subledger hanya mencatat satu kali.

Dua alat kecil di sini, dipakai ulang oleh semua jalur:

1. `once(key)` — kunci idempotensi. Permintaan identik (kunci sama) yang kedua DITOLAK dengan
   `Conflict` selama jendela waktunya. Atomik karena memakai index unik MongoDB, bukan
   find-lalu-insert. Bila operasi gagal (exception), kunci dilepas supaya pemakai bisa
   mencoba lagi setelah memperbaiki masukannya. Dengan `client_ref` dari klien, kunci bertahan
   lebih lama (retry jaringan yang sama tidak membayar dua kali).
2. `cas(...)` / `transition(...)` — pembaruan bersyarat: hanya berhasil bila dokumen masih
   berada pada keadaan yang tadi dibaca. Yang kalah balapan mendapat `Conflict`, bukan
   menimpa hasil pemenang.

`Conflict` adalah subclass `ValueError` supaya router lama yang menangkap ValueError tetap
menampilkan pesan yang jelas (bukan HTTP 500); handler di server.py memetakannya ke HTTP 409.
"""
import hashlib
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from pymongo.errors import DuplicateKeyError

from db import db

logger = logging.getLogger("sipro.idempotency")

# Jendela bawaan untuk permintaan identik tanpa client_ref (klik ganda / dua tab / retry cepat).
DEFAULT_WINDOW_SECONDS = 15
# Jendela bila klien mengirim `client_ref` eksplisit.
CLIENT_REF_WINDOW_SECONDS = 24 * 3600

_ttl_ready = False


class Conflict(ValueError):
    """Permintaan bentrok dengan permintaan lain yang sama (HTTP 409)."""


async def _ensure_ttl() -> None:
    global _ttl_ready
    if _ttl_ready:
        return
    try:
        await db.idempotency_keys.create_index("expires_at", expireAfterSeconds=0,
                                               name="ttl_idempotency_expires")
        _ttl_ready = True
    except Exception as e:  # noqa: BLE001 — TTL hanya pembersih; jangan gagalkan transaksi
        logger.warning("Index TTL idempotency_keys gagal dibuat: %s", str(e)[:120])


def make_key(op: str, *parts) -> str:
    """Kunci deterministik: op + sidik jari bagian-bagian yang menentukan 'permintaan yang sama'."""
    raw = "|".join("" if p is None else str(p) for p in parts)
    return f"{op}:{hashlib.sha1(raw.encode('utf-8')).hexdigest()}"


async def claim(key: str, ttl_seconds: int = DEFAULT_WINDOW_SECONDS,
                what: str = "Permintaan yang sama") -> None:
    """Klaim kunci secara atomik. Raise Conflict bila sudah diklaim dan belum kedaluwarsa."""
    await _ensure_ttl()
    now = datetime.now(timezone.utc)
    try:
        await db.idempotency_keys.insert_one({
            "key": key, "created_at": now.isoformat(),
            "expires_at": now + timedelta(seconds=ttl_seconds)})
    except DuplicateKeyError:
        # Dokumen TTL baru dihapus oleh monitor MongoDB tiap ±60 dtk, jadi kunci yang sudah
        # lewat masa berlakunya bisa masih ada; ambil alih secara atomik bila memang sudah lewat.
        res = await db.idempotency_keys.find_one_and_update(
            {"key": key, "expires_at": {"$lte": now}},
            {"$set": {"created_at": now.isoformat(),
                      "expires_at": now + timedelta(seconds=ttl_seconds)}})
        if res is None:
            raise Conflict(f"{what} sedang atau baru saja diproses. Tunggu beberapa detik dan "
                           f"periksa daftar sebelum mengulang, agar tidak tercatat dua kali.")


async def release(key: str) -> None:
    try:
        await db.idempotency_keys.delete_one({"key": key})
    except Exception:  # noqa: BLE001
        pass


@asynccontextmanager
async def once(op: str, *parts, client_ref: str = None, window: int = DEFAULT_WINDOW_SECONDS,
               what: str = "Permintaan yang sama"):
    """`async with once("ap.pay", bill_id, amount, actor): ...` — satu kali per jendela waktu.

    Dengan `client_ref`, kunci = (op + client_ref) saja dan berlaku 24 jam: pengiriman ulang
    dengan referensi yang sama tidak pernah menjadi transaksi kedua.
    """
    if client_ref:
        key = make_key(op, "ref", client_ref)
        ttl = CLIENT_REF_WINDOW_SECONDS
    else:
        key = make_key(op, *parts)
        ttl = window
    await claim(key, ttl, what)
    try:
        yield key
    except BaseException:
        await release(key)  # gagal → boleh dicoba lagi; hanya yang SUKSES menahan pengulangan
        raise


async def cas(coll: str, filt: dict, expect: dict, update: dict,
              what: str = "Data") -> None:
    """update_one bersyarat. `expect` = keadaan yang tadi dibaca (mis. {"status": "approved", "paid": 0})."""
    res = await db[coll].update_one({**filt, **expect}, update)
    if res.matched_count != 1:
        raise Conflict(f"{what} baru saja diubah oleh proses lain. Muat ulang lalu coba lagi.")


async def transition(coll: str, filt: dict, expect: dict, update: dict,
                     what: str = "Data") -> dict:
    """find_one_and_update bersyarat; kembalikan dokumen SESUDAH diubah, atau raise Conflict."""
    from pymongo import ReturnDocument
    doc = await db[coll].find_one_and_update(
        {**filt, **expect}, update, projection={"_id": 0},
        return_document=ReturnDocument.AFTER)
    if doc is None:
        raise Conflict(f"{what} baru saja diubah oleh proses lain atau tidak lagi berstatus yang "
                       f"diharapkan. Muat ulang lalu coba lagi.")
    return doc


def expect_of(doc: dict, *fields) -> dict:
    """Syarat CAS dari nilai yang tadi dibaca: {field: nilai} (atau {$exists: False} bila belum ada)."""
    return {f: (doc[f] if f in doc else {"$exists": False}) for f in fields}


def _landed(update: dict) -> dict:
    """Nilai skalar yang di-`$set` oleh `update` — dipakai untuk mengenali dokumen hasil klaim kita."""
    out = {}
    for k, v in (update.get("$set") or {}).items():
        if v is None or isinstance(v, (str, int, float, bool)):
            out[k] = v
    return out


@asynccontextmanager
async def reserved(coll: str, filt: dict, expect: dict, update: dict, *, undo: dict,
                   what: str = "Data"):
    """Klaim dokumen secara atomik SEBELUM efek samping (jurnal/emit/pembayaran), lalu kembalikan
    bila efek samping gagal.

    `async with reserved("ap_invoices", {"id": x}, {"paid": 0, "status": "approved"}, {"$set": ...}, undo={...}):`
    1. `cas()` — hanya SATU dari dua permintaan bersamaan yang lolos; yang kalah → `Conflict` (409).
    2. Blok dijalankan (post jurnal, emit, insert pembayaran, ...).
    3. Bila blok melempar exception, `undo` diterapkan dengan syarat dokumen masih berada pada
       keadaan hasil klaim kita (tidak menimpa perubahan proses lain).
    """
    await cas(coll, filt, expect, update, what)
    try:
        yield
    except BaseException:
        try:
            await db[coll].update_one({**filt, **_landed(update)}, undo)
        except Exception:  # noqa: BLE001 — pengembalian best-effort; jangan menutupi galat asli
            logger.exception("Gagal mengembalikan klaim %s %s", coll, filt)
        raise
