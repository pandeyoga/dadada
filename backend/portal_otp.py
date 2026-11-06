"""OTP portal pembeli — penjagaan percobaan (audit AZ-10).

Dulu kolom `attempts` hanya diisi 0 saat OTP dibuat dan tidak pernah dihitung: 800 tebakan
beruntun tidak ditolak (ruang 10^6 kombinasi, masa berlaku 10 menit). Sekarang:

  * tiap percobaan verifikasi menaikkan `attempts` SECARA ATOMIK (`find_one_and_update`), jadi
    tebakan paralel pun tidak melewati batas;
  * paling banyak `MAX_ATTEMPTS` percobaan per OTP; percobaan gagal terakhir MENGHAPUS OTP itu
    (kode yang benar pun tak lagi berlaku) dan dijawab 429;
  * permintaan OTP baru memulai hitungan dari nol, tetapi dibatasi per pembeli
    (`REQUEST_MAX` kali per `REQUEST_WINDOW_S` detik) supaya batas di atas tidak bisa dicuci
    dengan meminta kode baru berulang kali (sekaligus mencegah banjir pesan WhatsApp).
"""
import hmac

from fastapi import HTTPException
from pymongo import ReturnDocument

import rate_limit
from core_utils import now_iso
from db import db

MAX_ATTEMPTS = 5
REQUEST_MAX = 5
REQUEST_WINDOW_S = 600


def throttle_request(portal_user_id: str) -> None:
    """Dipanggil sebelum membuat OTP baru; 429 bila pembeli ini terlalu sering meminta kode."""
    if not rate_limit.hit_ok("portal_otp_req", portal_user_id, REQUEST_MAX, REQUEST_WINDOW_S):
        raise HTTPException(status_code=429, detail=(
            "Terlalu sering meminta kode OTP. Tunggu beberapa menit lalu coba lagi."))


async def check_code(portal_user_id: str, code: str) -> None:
    """Periksa kode OTP; melempar 400/429 bila salah, kedaluwarsa, atau percobaan habis."""
    rec = await db.portal_otps.find_one_and_update(
        {"portal_user_id": portal_user_id}, {"$inc": {"attempts": 1}},
        projection={"_id": 0}, return_document=ReturnDocument.AFTER)
    if not rec:
        raise HTTPException(status_code=400, detail="Kode OTP tidak berlaku. Minta kode baru.")
    used = int(rec.get("attempts") or 0)
    if used > MAX_ATTEMPTS:
        await db.portal_otps.delete_one({"portal_user_id": portal_user_id})
        raise HTTPException(status_code=429, detail="Terlalu banyak percobaan. Minta kode OTP baru.")
    if not hmac.compare_digest(str(rec.get("code") or ""), code):
        if used >= MAX_ATTEMPTS:
            await db.portal_otps.delete_one({"portal_user_id": portal_user_id})
            raise HTTPException(status_code=429, detail=(
                "Terlalu banyak kode salah. Kode OTP ini dikunci — minta kode baru."))
        raise HTTPException(status_code=400, detail=(
            f"Kode OTP salah. Sisa percobaan: {MAX_ATTEMPTS - used}."))
    if rec.get("expires_at") and rec["expires_at"] < now_iso():
        raise HTTPException(status_code=400, detail="Kode OTP kedaluwarsa. Minta kode baru.")
