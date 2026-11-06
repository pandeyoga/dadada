"""Pencari dokumen BER-LINGKUP ORGANISASI — satu pola untuk seluruh router.

Mengapa ada berkas ini (audit AZ-01/AZ-02, docs/audit/11b): banyak router mencari dokumen
dengan `db.<koleksi>.find_one({"id": x})` TANPA `org_id`, sehingga pengguna organisasi B bisa
membaca/mengubah data organisasi A bila tahu id-nya (id bisa bocor lewat tautan, ekspor, notifikasi).
Pemeriksaan "milik sendiri" untuk sales (`assigned_to`) memang ada, tetapi pemeriksaan ORGANISASI tidak.

Aturan pakai:
  * ID dari URL / payload / query  -> WAJIB lewat `get_in_org` (atau memuat `org_id` pada filter).
  * Update/delete SESUDAH pencarian -> pakai `org_filter(user, id=...)` (atau `"org_id": org`)
    supaya CAS/penulisan juga terkunci pada organisasi yang sama.
  * Lintas organisasi dijawab 404 (bukan 403) agar keberadaan data organisasi lain tidak bocor.

`user["org_id"]` sudah berisi organisasi EFEKTIF: super_admin yang "bertindak sebagai" organisasi
lain disuntikkan oleh `security.apply_org_context`, jadi cukup membaca `user["org_id"]`.
"""
from typing import Optional

from fastapi import HTTPException

from db import ORG_ID


def org_of(user: Optional[dict]) -> str:
    """Organisasi efektif pemakai (jatuh ke organisasi bawaan bila klaim tidak ada)."""
    return (user or {}).get("org_id") or ORG_ID


def org_filter(user: Optional[dict], **extra) -> dict:
    """Filter Mongo `{...extra, "org_id": <org pemakai>}` — `org_id` SELALU menang atas `extra`."""
    q = dict(extra)
    q["org_id"] = org_of(user)
    return q


async def get_in_org(coll, doc_id, user: Optional[dict], *, projection: Optional[dict] = None,
                     name: str = "Data", id_field: str = "id", extra: Optional[dict] = None) -> dict:
    """Ambil SATU dokumen berdasarkan id DI DALAM organisasi pemakai; 404 bila tidak ada di sana.

    `coll`       koleksi Motor (mis. `db.leads`).
    `name`       kata benda untuk pesan galat: "Lead" -> "Lead tidak ditemukan".
    `projection` default `{"_id": 0}`.
    `extra`      syarat tambahan (mis. `{"status": "draft"}`) yang ikut masuk filter.
    """
    q = {**(extra or {}), id_field: doc_id, "org_id": org_of(user)}
    doc = await coll.find_one(q, projection if projection is not None else {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail=f"{name} tidak ditemukan")
    return doc
