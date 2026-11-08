"""ROUTER REKONSILIASI BANK (Fase 47A) — prefix `/bank`.

Pemisahan tugas yang dipaksakan di sini:
  * `view`   — melihat mutasi & ringkasan rekonsiliasi (keuangan + direksi).
  * `create` — mendaftarkan rekening & mengimpor mutasi.
  * `update` — MENCOCOKKAN mutasi ke dokumen (kasir/finance).
  * `approve` — MEMBATALKAN pencocokan (membalik uang) — hanya supervisor keuangan/direksi.
    Sengaja lebih ketat daripada mencocokkan: membalik penerimaan mengubah pembukuan yang
    sudah dilaporkan.
Sales & peran lapangan tidak punya akses sama sekali (mutasi rekening = data sensitif).
"""
import re

from fastapi import APIRouter, Body, Depends, HTTPException, Query

import bank_import as bimp
import bank_match as bmatch
from core_utils import new_id, now_iso, parse_pagination, serialize_doc
from db import ORG_ID, db
from org_scope import exists_in_org
from idempotency import Conflict, mutex
from models_p47 import BankAccountIn, BankIgnoreIn, BankImportIn, BankMatchIn, BankUnmatchIn
from rbac import audit_log, require_permission
from reference_p47 import DIRECTION_LABEL, MATCH_STATE_LABEL

router = APIRouter(prefix="/bank", tags=["bank"])


def _org(user: dict) -> str:
    return user.get("org_id", ORG_ID)


# ------------------------------------------------------------------ rekening
@router.get("/accounts")
async def list_accounts(user: dict = Depends(require_permission("bank", "view"))):
    # Fase 82/83: koleksi `bank_accounts` juga memuat kas (kind=cash); rekonsiliasi bank hanya
    # untuk rekening bank — kas tidak punya mutasi rekening untuk dibandingkan.
    rows = await db.bank_accounts.find({"org_id": _org(user), "kind": {"$ne": "cash"}}, {"_id": 0}) \
        .sort([("is_default", -1), ("name", 1)]).to_list(100)
    return {"data": serialize_doc(rows), "total": len(rows)}


@router.get("/accounts/gl-options")
async def gl_options(user: dict = Depends(require_permission("bank", "view"))):
    """Pilihan akun GL yang SAH untuk rekening bank baru (GL-08): induk 1-1200 = buat sub-akun otomatis,
    atau sub-akun Bank yang belum dipakai rekening mana pun. Dialog "+ Rekening" hanya memuat ini."""
    import cash_bank as _cb
    rows = await _cb.bank_gl_options(_org(user))
    return {"data": rows, "total": len(rows)}


@router.post("/accounts")
async def create_account(payload: BankAccountIn,
                         user: dict = Depends(require_permission("bank", "create"))):
    import cash_bank as _cb
    org = _org(user)
    gl_code = payload.gl_account_code.strip()
    # GL-08: hanya sub-akun Bank sah & belum dipakai rekening lain (dulu akun GL APA PUN: Piutang,
    # WIP, induk, atau sub-akun rekening lain → saldo kas di layar ≠ neraca). Diserialkan per akun
    # supaya dua pendaftaran bersamaan tidak sama-sama lolos cek "belum dipakai".
    async with mutex(f"bank.gl:{org}:{gl_code}", what="Pendaftaran rekening untuk akun GL ini"):
        try:
            await _cb.assert_valid_bank_gl(org, gl_code)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        acct = await db.accounts.find_one({"org_id": org, "code": gl_code}, {"_id": 0, "code": 1, "name": 1})
        if await db.bank_accounts.find_one({"org_id": org, "account_no": payload.account_no},
                                           {"_id": 0, "id": 1}):
            raise HTTPException(status_code=409,
                                detail="Nomor rekening ini sudah terdaftar.")
        ts = now_iso()
        doc = {"id": new_id(), "org_id": org, **payload.model_dump(),
               "gl_account_name": acct.get("name"),
               "created_by": user.get("email"), "created_at": ts, "updated_at": ts}
        await db.bank_accounts.insert_one(dict(doc))
        doc.pop("_id", None)
        # Fase 82: setiap rekening langsung mendapat sub-akun GL sendiri (bukan menumpang 1-1200).
        doc["gl_account_code"] = await _cb._ensure_sub_account(org, {**doc, "kind": "bank"})
        await db.bank_accounts.update_one({"id": doc["id"], "org_id": org}, {"$set": {"kind": "bank"}})
    await _cb._post_opening(org, doc)
    await audit_log(user, "create", "bank_accounts", doc["id"], {"name": doc["name"]})
    return {"data": serialize_doc(doc)}


@router.put("/accounts/{account_id}")
async def update_account(account_id: str, payload: BankAccountIn,
                         user: dict = Depends(require_permission("bank", "update"))):
    """Ubah data rekening. Akun GL TIDAK bisa dipindah (GL-08): jurnal lama tetap di sub-akun asal,
    sehingga mengarahkan ulang rekening ke akun lain memecah saldo atau menunjuk akun non-kas."""
    import cash_bank as _cb
    org = _org(user)
    acc = await db.bank_accounts.find_one({"id": account_id, "org_id": org}, {"_id": 0})
    if not acc:
        raise HTTPException(status_code=404, detail="Rekening tidak ditemukan")
    if _cb.kind_of(acc) == "cash":
        raise HTTPException(status_code=400, detail="Kas tunai diubah dari menu Kas & Bank, bukan dari Rekonsiliasi Bank.")
    want = (payload.gl_account_code or "").strip()
    if want and want not in (acc.get("gl_account_code"), _cb.HEADER["bank"]):
        raise HTTPException(status_code=400, detail=(
            f"Akun GL rekening ini ({acc.get('gl_account_code')}) tidak bisa dipindah ke {want}: jurnal "
            "yang sudah ada tetap di akun asal. Buat rekening baru bila memang berbeda."))
    try:
        doc = await _cb.update_account(org, account_id, payload.model_dump(exclude={"gl_account_code"}),
                                       user.get("email"))
    except Conflict:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await audit_log(user, "update", "bank_accounts", account_id, {"name": payload.name})
    return {"data": serialize_doc(doc)}


# ------------------------------------------------------------------ impor mutasi
@router.post("/statements/import")
async def import_statement(payload: BankImportIn,
                           user: dict = Depends(require_permission("bank", "create"))):
    """Impor CSV mutasi. `dry_run=true` (bawaan) HANYA memberi pratinjau, tanpa menulis."""
    await exists_in_org(db.bank_accounts, payload.account_id, user, name="Rekening")
    try:
        out = await bimp.import_csv(_org(user), payload.account_id, payload.filename,
                                    payload.csv_text, user.get("email"),
                                    dry_run=payload.dry_run)
    except Conflict:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not payload.dry_run:
        await audit_log(user, "import", "bank_transactions", payload.account_id,
                        {"file": payload.filename, "counts": out["counts"]})
    return {"data": serialize_doc(out), "message": out["message"]}


@router.get("/statements")
async def list_statements(account_id: str = None, skip: int = 0, limit: int = 25,
                          user: dict = Depends(require_permission("bank", "view"))):
    skip, limit = parse_pagination(skip, limit)
    q = {"org_id": _org(user)}
    if account_id:
        q["account_id"] = account_id
    total = await db.bank_statements.count_documents(q)
    rows = await db.bank_statements.find(q, {"_id": 0}).sort("created_at", -1) \
        .skip(skip).limit(limit).to_list(limit)
    return {"data": serialize_doc(rows), "total": total}


# ------------------------------------------------------------------ mutasi & pencocokan
@router.get("/transactions")
async def list_transactions(account_id: str = None, match_state: str = None,
                            direction: str = None, date_from: str = None,
                            date_to: str = None, q: str = None, skip: int = 0,
                            limit: int = Query(25, ge=1, le=200),
                            user: dict = Depends(require_permission("bank", "view"))):
    org = _org(user)
    skip, limit = parse_pagination(skip, limit)
    query = {"org_id": org}
    if account_id:
        query["account_id"] = account_id
    if match_state:
        query["match_state"] = {"$in": [s for s in match_state.split(",") if s]}
    if direction:
        query["direction"] = direction
    if date_from or date_to:
        query["date"] = {k: v for k, v in (("$gte", date_from), ("$lte", date_to)) if v}
    if q:
        qre = re.escape(q)  # AZ-08
        query["$or"] = [{"description": {"$regex": qre, "$options": "i"}},
                        {"ref": {"$regex": qre, "$options": "i"}}]
    total = await db.bank_transactions.count_documents(query)
    rows = await db.bank_transactions.find(query, {"_id": 0}) \
        .sort([("date", -1), ("created_at", -1)]).skip(skip).limit(limit).to_list(limit)
    for r in rows:
        r["direction_label"] = DIRECTION_LABEL.get(r.get("direction"))
        r["match_state_label"] = MATCH_STATE_LABEL.get(r.get("match_state"))
    base = {"org_id": org, **({"account_id": account_id} if account_id else {})}
    summary = {s: await db.bank_transactions.count_documents({**base, "match_state": s})
               for s in MATCH_STATE_LABEL}
    return {"data": serialize_doc(rows), "total": total, "summary": summary}


@router.get("/transactions/{txn_id}/suggest")
async def suggest_match(txn_id: str,
                        user: dict = Depends(require_permission("bank", "view"))):
    """Kandidat pencocokan + SKOR & ALASANNYA. Sistem mengusulkan, manusia memutuskan."""
    try:
        return {"data": serialize_doc(await bmatch.suggest(_org(user), txn_id))}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# jenis pencocokan -> (koleksi dokumen tujuan, nama untuk pesan galat)
_MATCH_TARGET = {"ar_deal": ("deals", "Deal"), "payment_intake": ("payment_intakes", "Bukti pelanggan"),
                 "ap_bill": ("ap_invoices", "Tagihan AP"), "labor_payroll": ("labor_payrolls", "Rekap upah")}


@router.post("/transactions/{txn_id}/match")
async def do_match(txn_id: str, payload: BankMatchIn,
                   user: dict = Depends(require_permission("bank", "update"))):
    await exists_in_org(db.bank_transactions, txn_id, user, name="Mutasi bank")
    # Dokumen tujuan pencocokan juga harus milik organisasi ini (mutasi org B tidak boleh melunasi tagihan org A).
    tujuan = _MATCH_TARGET.get(payload.kind)
    if tujuan and payload.target_id:
        await exists_in_org(db[tujuan[0]], payload.target_id, user, name=tujuan[1])
    try:
        out = await bmatch.match(_org(user), txn_id, payload.kind, payload.target_id,
                                 user.get("email"), payload.note,
                                 allow_duplicate=payload.allow_duplicate)
    except Conflict:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await audit_log(user, "bank.match", "bank_transactions", txn_id,
                    {"kind": payload.kind, "target_id": payload.target_id})
    return {"data": serialize_doc(out), "message": out["message"]}


@router.post("/transactions/{txn_id}/unmatch")
async def do_unmatch(txn_id: str, payload: BankUnmatchIn,
                     user: dict = Depends(require_permission("bank", "approve"))):
    """Batalkan pencocokan + balikkan dampaknya. Wajib beralasan."""
    await exists_in_org(db.bank_transactions, txn_id, user, name="Mutasi bank")
    try:
        out = await bmatch.unmatch(_org(user), txn_id, user.get("email"), payload.reason)
    except Conflict:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await audit_log(user, "bank.unmatch", "bank_transactions", txn_id,
                    {"reason": payload.reason})
    return {"data": serialize_doc(out), "message": out["message"]}


@router.post("/transactions/{txn_id}/ignore")
async def do_ignore(txn_id: str, payload: BankIgnoreIn,
                    user: dict = Depends(require_permission("bank", "update"))):
    await exists_in_org(db.bank_transactions, txn_id, user, name="Mutasi bank")
    try:
        out = await bmatch.ignore(_org(user), txn_id, user.get("email"), payload.reason)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await audit_log(user, "bank.ignore", "bank_transactions", txn_id,
                    {"reason": payload.reason})
    return {"data": serialize_doc(out)}


@router.get("/reconciliation")
async def reconciliation(account_id: str = None, as_of: str = None,
                         user: dict = Depends(require_permission("bank", "view"))):
    """Fase 83: saldo rekening vs saldo SUB-AKUN GL rekening itu pada tanggal yang sama; selisih
    diurai per item (mutasi belum cocok, jurnal tanpa pasangan, saldo awal tersirat, residu)."""
    import bank_recon as brc
    org = _org(user)
    if not account_id:
        acc = await db.bank_accounts.find_one({"org_id": org, "kind": "bank", "is_default": True},
                                              {"_id": 0, "id": 1}) \
            or await db.bank_accounts.find_one({"org_id": org, "kind": "bank"}, {"_id": 0, "id": 1})
        if not acc:
            raise HTTPException(status_code=404, detail="Belum ada rekening bank terdaftar.")
        account_id = acc["id"]
    await exists_in_org(db.bank_accounts, account_id, user, name="Rekening")
    try:
        return {"data": serialize_doc(await brc.reconcile(org, account_id, as_of))}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/reconciliation/overview")
async def reconciliation_overview(user: dict = Depends(require_permission("bank", "view"))):
    import bank_recon as brc
    rows = await brc.overview(_org(user))
    return {"data": serialize_doc(rows), "total": len(rows),
            "summary": {s: sum(1 for r in rows if r["status"] == s)
                        for s in ("seimbang", "dijelaskan", "belum_dijelaskan", "tanpa_data")}}


@router.post("/reconciliation/explain")
async def reconciliation_explain(payload: dict = Body(...),
                                 user: dict = Depends(require_permission("bank", "update"))):
    import bank_recon as brc
    for k in ("account_id", "journal_id", "reason_code"):
        if not payload.get(k):
            raise HTTPException(status_code=400, detail=f"Field '{k}' wajib diisi.")
    await exists_in_org(db.bank_accounts, payload["account_id"], user, name="Rekening")
    await exists_in_org(db.journal_entries, payload["journal_id"], user, name="Jurnal")
    try:
        doc = await brc.explain(_org(user), payload["account_id"], payload["journal_id"],
                                payload["reason_code"], payload.get("note"), user.get("email"))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await audit_log(user, "update", "bank_recon_notes", doc["id"],
                    {"journal_id": payload["journal_id"], "reason_code": payload["reason_code"]})
    return {"data": serialize_doc(doc)}


@router.post("/reconciliation/unexplain")
async def reconciliation_unexplain(payload: dict = Body(...),
                                   user: dict = Depends(require_permission("bank", "update"))):
    import bank_recon as brc
    if payload.get("account_id"):
        await exists_in_org(db.bank_accounts, payload["account_id"], user, name="Rekening")
    ok = await brc.unexplain(_org(user), payload.get("account_id"), payload.get("journal_id"))
    if not ok:
        raise HTTPException(status_code=404, detail="Alasan tidak ditemukan.")
    await audit_log(user, "update", "bank_recon_notes", payload.get("journal_id"), {"removed": True})
    return {"data": {"removed": True}}
