"""Validasi berkas BUKTI di API (audit PK-13).

Sebelumnya kewajiban "foto bukti pencairan / nota reimbursement / bukti kas kecil" hanya dipaksa
di UI. API menerima daftar kosong, id palsu (`FAKE-FILE-ID`), berkas milik pengguna lain (mis.
KTP lead sebagai nota) dan satu berkas yang sama sebagai bukti dua transaksi berbeda.

`validate()` memeriksa di server: berkas ADA, milik organisasi ini, belum dihapus, jenisnya sesuai
(`owner_type`), belum terikat ke dokumen lain (`owner_id`), diunggah oleh aktor yang sama, dan belum
dipakai sebagai bukti pada pengajuan/pengeluaran lain.
"""
from db import db


async def _used_elsewhere(org: str, ids: list, *, exclude_fund_request: str = None,
                          exclude_expense: str = None):
    """Pertama yang ketemu: (nomor_dokumen, id_berkas) yang sudah memakai salah satu `ids`."""
    q = {"org_id": org, "$or": [{"attachments.id": {"$in": ids}}, {"payment_proofs.id": {"$in": ids}},
                                {"settle_attachments.id": {"$in": ids}}]}
    if exclude_fund_request:
        q["id"] = {"$ne": exclude_fund_request}
    row = await db.fund_requests.find_one(q, {"_id": 0, "no": 1, "attachments": 1, "payment_proofs": 1,
                                              "settle_attachments": 1})
    if row:
        used = {f.get("id") for k in ("attachments", "payment_proofs", "settle_attachments")
                for f in (row.get(k) or [])}
        return row.get("no"), next(i for i in ids if i in used)
    q2 = {"org_id": org, "file_ids": {"$in": ids}}
    if exclude_expense:
        q2["id"] = {"$ne": exclude_expense}
    row = await db.petty_expenses.find_one(q2, {"_id": 0, "no": 1, "file_ids": 1})
    if row:
        return row.get("no"), next(i for i in ids if i in (row.get("file_ids") or []))
    # IN-17: berkas yang sudah menjadi bukti KUITANSI (termasuk yang sudah dibatalkan) tidak dipakai ulang.
    row = await db.receipts.find_one({"org_id": org, "proof_file_ids": {"$in": ids}},
                                     {"_id": 0, "receipt_no": 1, "proof_file_ids": 1})
    if row:
        return row.get("receipt_no"), next(i for i in ids if i in (row.get("proof_file_ids") or []))
    return None


async def validate(org: str, ids, *, actor: str, owner_types: tuple, owner_id: str = None,
                   minimum: int = 0, label: str = "bukti", exclude_fund_request: str = None,
                   exclude_expense: str = None) -> list:
    """Kembalikan metadata berkas yang sah (urutan sesuai `ids`) atau raise ValueError (Indonesia)."""
    ids = [str(i) for i in dict.fromkeys(i for i in (ids or []) if i)]
    if len(ids) < minimum:
        raise ValueError(f"Berkas {label} wajib dilampirkan (minimal {minimum}).")
    if not ids:
        return []
    rows = await db.files.find({"id": {"$in": ids}, "org_id": org, "is_deleted": False},
                               {"_id": 0, "data_b64": 0}).to_list(len(ids))
    by_id = {r["id"]: r for r in rows}
    for fid in ids:
        f = by_id.get(fid)
        if not f:
            raise ValueError(f"Berkas {label} tidak ditemukan atau bukan milik organisasi ini: {fid}. "
                             "Unggah ulang berkasnya.")
        nm = f.get("original_filename") or fid
        if owner_types and (f.get("owner_type") or "generic") not in owner_types:
            raise ValueError(f"Berkas '{nm}' bukan berkas {label} (jenis '{f.get('owner_type')}'). "
                             "Unggah berkas yang benar dari layar ini.")
        if f.get("owner_id") and f.get("owner_id") != owner_id:
            raise ValueError(f"Berkas '{nm}' sudah terikat ke dokumen lain dan tidak boleh dipakai ulang "
                             f"sebagai {label}.")
        if f.get("uploaded_by") and actor and f["uploaded_by"] != actor:
            raise ValueError(f"Berkas '{nm}' diunggah oleh pengguna lain — unggah sendiri berkas {label} Anda.")
    used = await _used_elsewhere(org, ids, exclude_fund_request=exclude_fund_request,
                                 exclude_expense=exclude_expense)
    if used:
        no, fid = used
        raise ValueError(f"Berkas '{(by_id.get(fid) or {}).get('original_filename') or fid}' sudah dipakai "
                         f"sebagai bukti pada {no or 'dokumen lain'} — satu berkas tidak boleh menjadi bukti "
                         "dua transaksi.")
    return [{"id": r["id"], "filename": r.get("original_filename"), "content_type": r.get("content_type"),
             "size": r.get("size")} for r in (by_id[i] for i in ids)]


async def validate_proof(org: str, ids, *, actor: str, deal_id: str = None) -> list:
    """Bukti BAYAR pembeli yang dicatat staf (kuitansi manual, booking fee, titipan) — audit IN-17.

    Dulu `proof_file_ids:["x"]` atau satu berkas nyata yang sama untuk tiga kuitansi pada tiga deal diterima,
    sehingga "bukti bayar wajib" tampil terpenuhi di semua laporan padahal kosong/ganda. Berkas harus ada,
    milik organisasi ini, diunggah pencatat sendiri, tidak terikat ke dokumen LAIN (mis. KTP lead; berkas yang
    terikat ke deal ini boleh), dan belum menjadi bukti kuitansi/pengajuan lain. Jenis berkas (`owner_type`)
    sengaja tidak dibatasi: UI memakai `receipt_proof`, sedangkan alur lain mengunggah dengan jenis `deal`/umum.
    """
    return await validate(org, ids, actor=actor, owner_types=(), owner_id=deal_id, minimum=1, label="bukti bayar")
