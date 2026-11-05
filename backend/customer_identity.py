"""Normalisasi & validasi identitas pembeli + deteksi duplikat (audit KT-17).

Cacat nyata: `POST /customers` hanya mengecek NIK; telepon/email kembar lolos jadi dua pembeli.
Konversi lead→pembeli menyimpan NIK/NPWP apa adanya ('3174-0101-0101-0077', 'abc', '123') sehingga NIK
yang sama bisa menjadi dua pembeli (index unik terlewati karena format berbeda) dan penghasilan
negatif diterima. Semua jalur kini lewat fungsi yang sama.
"""
from core_utils import normalize_nik, normalize_phone_e164
from db import db


def clean_identity(data: dict) -> dict:
    """Normalisasi (hanya angka) + validasi NIK/NPWP/NIK pasangan/penghasilan. ValueError bila tidak sah.

    Hanya kolom yang TERISI yang diperiksa; kosong tetap kosong (KYC boleh dilengkapi belakangan).
    """
    for key, label in (("nik", "NIK"), ("spouse_nik", "NIK pasangan")):
        v = data.get(key)
        if v not in (None, ""):
            d = normalize_nik(v)
            if len(d) != 16:
                raise ValueError(f"{label} harus 16 digit angka (terbaca {len(d)} digit).")
            data[key] = d
    v = data.get("npwp")
    if v not in (None, ""):
        d = normalize_nik(v)
        if len(d) not in (15, 16):
            raise ValueError(f"NPWP harus 15 atau 16 digit angka (terbaca {len(d)} digit).")
        data["npwp"] = d
    inc = data.get("monthly_income")
    if inc not in (None, "") and int(inc) < 0:
        raise ValueError("Penghasilan bulanan tidak boleh negatif.")
    return data


async def find_duplicate(org: str, *, phone: str = None, email: str = None, exclude_id: str = None):
    """Pembeli lain dengan telepon (dinormalisasi +62) atau email (tanpa beda huruf besar/kecil) yang sama."""
    import re
    ors = []
    p = normalize_phone_e164(phone) if phone else None
    if p:
        tail = re.sub(r"\D", "", p)[-9:]
        ors.append({"phone": {"$regex": re.escape(tail) + "$"}})
    if email:
        ors.append({"email": {"$regex": f"^{re.escape(email.strip())}$", "$options": "i"}})
    if not ors:
        return None
    q = {"org_id": org, "$or": ors}
    if exclude_id:
        q["id"] = {"$ne": exclude_id}
    for c in await db.customers.find(q, {"_id": 0, "id": 1, "name": 1, "phone": 1, "email": 1}).to_list(10):
        if p and c.get("phone") and normalize_phone_e164(c["phone"]) == p:
            return {**c, "by": "nomor HP"}
        if email and (c.get("email") or "").strip().lower() == email.strip().lower():
            return {**c, "by": "email"}
    return None
