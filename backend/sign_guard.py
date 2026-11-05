"""Penjaga tanda tangan dokumen (audit KT-24).

Dulu `POST /documents/{id}/sign` "cek lalu tulis" tanpa kunci: dua permintaan serentak oleh peran &
nama yang sama menghasilkan dua entri tanda tangan identik, dan dua SPR untuk satu kontrak bisa
sama-sama `signed` (dua dokumen "sah" dengan angka berbeda). Sekarang:

  * penandatanganan diserialkan (mutex) per kontrak/deal untuk SPR, per dokumen untuk lainnya;
  * peran + nama yang sama tidak boleh menandatangani dokumen yang sama dua kali;
  * SPR kedua untuk deal yang sudah punya SPR bertanda tangan DITOLAK — perubahan setelah tanda
    tangan lewat adendum (spr_compare.ensure_addendum), bukan SPR kedua.
"""
from db import db
from docgen import SPR_CODES
from idempotency import mutex


def lock(doc: dict):
    """Kunci penandatanganan: satu per kontrak/deal untuk SPR, satu per dokumen untuk lainnya."""
    if doc.get("template_code") in SPR_CODES:
        return mutex(f"sign:spr:{doc.get('deal_id') or doc['id']}", wait=10, ttl=30,
                     what="Penandatanganan SPR kontrak ini")
    return mutex(f"sign:{doc['id']}", wait=10, ttl=30, what="Penandatanganan dokumen ini")


async def duplicate_reason(doc: dict, role: str, name: str) -> str:
    """Alasan penolakan (atau None): penanda tangan ganda / SPR lain sudah bertanda tangan."""
    for s in doc.get("signatures") or []:
        if s.get("role") == role and (s.get("name") or "").strip().lower() == (name or "").strip().lower():
            return (f"{name} ({role}) sudah menandatangani dokumen {doc.get('doc_number')}. "
                    "Tanda tangan yang sama tidak dicatat dua kali.")
    if doc.get("template_code") in SPR_CODES:
        lain = await db.documents.find_one(
            {"org_id": doc.get("org_id"), "deal_id": doc.get("deal_id"), "status": "signed",
             "template_code": {"$in": list(SPR_CODES)}, "id": {"$ne": doc["id"]}},
            {"_id": 0, "doc_number": 1})
        if lain:
            return (f"SPR {lain.get('doc_number')} untuk kontrak ini sudah ditandatangani. Dua SPR "
                    "bertanda tangan untuk satu kontrak tidak diperbolehkan — perubahan setelah "
                    "tanda tangan dibuat sebagai adendum, bukan SPR kedua.")
    return None
