"""General Ledger router (Phase 13 — EPIC 3.4).

Endpoints (RBAC resource `gl` — finance + owner/super_admin only):
  GET  /gl/accounts            — Chart of Accounts + balances
  POST /gl/accounts            — add account (manual)
  GET  /gl/journals            — journal list (filters)
  POST /gl/journals            — manual (adjusting) journal, must balance
  GET  /gl/journals/{id}       — journal detail
  GET  /gl/ledger?account_code — general ledger per account (running balance)
  GET  /gl/trial-balance       — neraca saldo (must balance)
  GET  /gl/income-statement    — laba rugi
  GET  /gl/balance-sheet       — neraca
  GET  /gl/summary             — dashboard KPIs
All GET endpoints keep query params optional (owner endpoint sweep must return 200).
"""
import re

from fastapi import APIRouter, Depends, HTTPException

from db import db, ORG_ID
from core_utils import new_id, now_iso, parse_journal_date, serialize_doc, parse_pagination
from rbac import audit_log, can, require_permission
from models import AccountCreate, JournalCreate
from models_master import AccountUpdate
import coa_rules
import gl_engine as gl

router = APIRouter(prefix="/gl", tags=["gl"])


@router.get("/accounts")
async def list_accounts(type: str = None, user: dict = Depends(require_permission("coa", "view"))):
    org = user.get("org_id", ORG_ID)
    await gl.ensure_coa(org)
    bal = await gl.account_balances(org)
    rows = sorted(bal.values(), key=lambda x: x["code"])
    if type:
        rows = [r for r in rows if r["type"] == type]
    # GL-13/GL-21: penanda untuk layar — nonaktif, induk kas, akun kendali (jurnal manual butuh izin + alasan).
    flags = {a["code"]: a for a in await db.accounts.find({"org_id": org}, {"_id": 0, "code": 1, "is_active": 1,
                                                                            "parent_code": 1}).to_list(1000)}
    for r in rows:
        r["is_active"] = (flags.get(r["code"]) or {}).get("is_active", True) is not False
        r["parent_code"] = (flags.get(r["code"]) or {}).get("parent_code")
        r["is_header"] = r["code"] in coa_rules.CASH_HEADERS
        r["is_control"] = r["code"] in coa_rules.CONTROL_ACCOUNTS
    return {"data": rows, "total": len(rows)}


@router.post("/accounts")
async def create_account(payload: AccountCreate, user: dict = Depends(require_permission("coa", "create"))):
    org = user.get("org_id", ORG_ID)
    if payload.type not in gl.VALID_TYPES:
        raise HTTPException(status_code=400, detail=f"Tipe akun tidak valid. Pilih: {', '.join(gl.VALID_TYPES)}.")
    await gl.ensure_coa(org)
    # GL-13: format kode, kecocokan prefiks-tipe, dan larangan membuat sub-akun kas/bank manual.
    try:
        code = coa_rules.check_new_account(payload.code, payload.type, payload.parent_code)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if await db.accounts.find_one({"org_id": org, "code": code}):
        raise HTTPException(status_code=400, detail="Kode akun sudah dipakai.")
    if payload.parent_code:
        parent = await db.accounts.find_one({"org_id": org, "code": payload.parent_code}, {"_id": 0, "type": 1})
        if not parent or parent.get("type") != payload.type:
            raise HTTPException(status_code=400, detail=(
                f"Akun induk {payload.parent_code} tidak ada atau tipenya berbeda dari akun baru."))
    ts = now_iso()
    doc = {"id": new_id(), "org_id": org, "code": code, "name": payload.name,
           "type": payload.type, "parent_code": payload.parent_code, "is_active": True, "created_at": ts}
    await db.accounts.insert_one(dict(doc))
    doc.pop("_id", None)
    return {"data": serialize_doc(doc)}


@router.get("/journals")
async def list_journals(source_type: str = None, source_id: str = None, auto: str = None,
                        q: str = None, skip: int = 0, limit: int = 50,
                        user: dict = Depends(require_permission("gl", "view"))):
    org = user.get("org_id", ORG_ID)
    skip, limit = parse_pagination(skip, limit)
    fq = {"org_id": org}
    if source_type:
        fq["source_type"] = source_type
    if source_id:
        fq["$or"] = [{"source_id": source_id}, {"source_deal_id": source_id}]
    if auto in ("true", "false"):
        fq["auto"] = auto == "true"
    if q:
        qre = re.escape(q)  # AZ-08
        fq["$or"] = [{"memo": {"$regex": qre, "$options": "i"}}, {"entry_no": {"$regex": qre, "$options": "i"}}]
    total = await db.journal_entries.count_documents(fq)
    rows = await db.journal_entries.find(fq, {"_id": 0}).sort([("date", -1), ("created_at", -1)]).skip(skip).limit(limit).to_list(limit)
    return {"data": serialize_doc(rows), "total": total}


@router.post("/journals")
async def create_journal(payload: JournalCreate, user: dict = Depends(require_permission("gl", "create"))):
    org = user.get("org_id", ORG_ID)
    if not payload.lines:
        raise HTTPException(status_code=400, detail="Jurnal harus memiliki minimal 1 baris.")
    lines = [{"account_code": ln.account_code.strip(), "debit": int(ln.debit or 0),
              "credit": int(ln.credit or 0), "memo": ln.memo} for ln in payload.lines]
    memo = payload.memo
    try:
        if payload.date:   # tanggal diperiksa PERTAMA (GL-06): pesan galatnya tidak boleh tertutup aturan lain
            parse_journal_date(payload.date)
        memo = await _manual_journal_guard(user, payload, lines)
        doc = await gl.post_journal(org, memo, lines, date=payload.date,
                                    source_type="manual", posted_by=user.get("email"), auto=False)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if memo != payload.memo:
        await audit_log(user, "control_post", "journal_entries", doc["id"],
                        {"reason": (payload.control_reason or "").strip(), "entry_no": doc["entry_no"]})
    return {"data": serialize_doc(doc)}


async def _manual_journal_guard(user: dict, payload, lines: list) -> str:
    """Aturan jurnal MANUAL (audit GL-21) — kembalikan memo final. PermissionError → 403, ValueError → 400.

    * memo wajib bermakna; satu baris tidak boleh debit DAN kredit sekaligus (dulu Dr 1000/Cr 1000 pada akun
      yang sama menghasilkan baris netto nol yang tak bisa diaudit);
    * induk kas (1-1100/1-1200) dulu dialihkan DIAM-DIAM ke rekening default → harus menyebut sub-akun rekening;
    * akun kendali (piutang/utang/kewajiban kontrak/titipan/retensi/komisi/kas bon) dijaga tie-out terhadap
      subledger: jurnal manual langsung ke sana hanya untuk peran berizin `gl:control_post` + alasan tertulis,
      karena mengubah saldo tanpa dokumen sumber (pakai fitur resmi: penerimaan, void, pembayaran, dst.).
    """
    if len((payload.memo or "").strip()) < 3:
        raise ValueError("Keterangan (memo) jurnal wajib diisi.")
    if any(ln["debit"] and ln["credit"] for ln in lines):
        raise ValueError("Satu baris jurnal tidak boleh berisi debit DAN kredit sekaligus — pisahkan menjadi dua baris.")
    heads = sorted({ln["account_code"] for ln in lines} & set(coa_rules.CASH_HEADERS))
    if heads:
        raise ValueError(f"Akun induk {', '.join(heads)} tidak boleh diposting langsung — pilih sub-akun rekening/kas "
                         "(mis. 1-1201 / 1-1101) agar saldo per rekening benar.")
    control = sorted({ln["account_code"] for ln in lines} & set(coa_rules.CONTROL_ACCOUNTS))
    if not control:
        return payload.memo
    names = ", ".join(f"{c} {coa_rules.CONTROL_ACCOUNTS[c]}" for c in control)
    if not await can(user.get("role"), "gl", "control_post"):
        raise PermissionError(f"Jurnal manual ke akun kendali ({names}) hanya untuk Manajer Keuangan/Direksi. "
                              "Gunakan fitur resmi (penerimaan, pembatalan, pembayaran) atau minta persetujuan mereka.")
    reason = (payload.control_reason or "").strip()
    if len(reason) < 10:
        raise ValueError(f"Alasan wajib diisi (minimal 10 huruf) untuk jurnal manual ke akun kendali ({names}) — "
                         "isi 'control_reason'.")
    return f"{payload.memo} · [akun kendali: {reason[:120]}]"


@router.get("/journals/{jid}")
async def get_journal(jid: str, user: dict = Depends(require_permission("gl", "view"))):
    org = user.get("org_id", ORG_ID)
    doc = await db.journal_entries.find_one({"id": jid, "org_id": org}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Jurnal tidak ditemukan.")
    return {"data": serialize_doc(doc)}


@router.get("/ledger")
async def get_ledger(account_code: str = None, user: dict = Depends(require_permission("gl", "view"))):
    org = user.get("org_id", ORG_ID)
    await gl.ensure_coa(org)
    return {"data": serialize_doc(await gl.ledger(org, account_code))}


@router.get("/trial-balance")
async def get_trial_balance(user: dict = Depends(require_permission("gl", "view"))):
    org = user.get("org_id", ORG_ID)
    await gl.ensure_coa(org)
    return {"data": serialize_doc(await gl.trial_balance(org))}


@router.get("/income-statement")
async def get_income_statement(user: dict = Depends(require_permission("gl", "view"))):
    org = user.get("org_id", ORG_ID)
    await gl.ensure_coa(org)
    return {"data": serialize_doc(await gl.income_statement(org))}


@router.get("/balance-sheet")
async def get_balance_sheet(user: dict = Depends(require_permission("gl", "view"))):
    org = user.get("org_id", ORG_ID)
    await gl.ensure_coa(org)
    return {"data": serialize_doc(await gl.balance_sheet(org))}


@router.get("/summary")
async def get_summary(user: dict = Depends(require_permission("gl", "view"))):
    org = user.get("org_id", ORG_ID)
    await gl.ensure_coa(org)
    tb = await gl.trial_balance(org)
    ist = await gl.income_statement(org)
    bs = await gl.balance_sheet(org)
    return {"data": {
        "accounts": await db.accounts.count_documents({"org_id": org}),
        "journals": await db.journal_entries.count_documents({"org_id": org}),
        "total_debit": tb["total_debit"], "total_credit": tb["total_credit"], "balanced": tb["balanced"],
        "revenue": ist["total_revenue"], "expense": ist["total_expense"], "net_income": ist["net_income"],
        "total_assets": bs["total_assets"], "bs_balanced": bs["balanced"],
    }}


@router.put("/accounts/{code}")
async def update_account(code: str, payload: AccountUpdate,
                         user: dict = Depends(require_permission("coa", "update"))):
    """Koreksi/nonaktifkan akun CoA (sebelumnya akun hanya bisa dibuat, tidak bisa diperbaiki).
    Tipe akun dikunci bila sudah ada jurnal agar laporan keuangan tidak berubah retroaktif."""
    org = user.get("org_id", ORG_ID)
    acc = await db.accounts.find_one({"org_id": org, "code": code}, {"_id": 0})
    if not acc:
        raise HTTPException(status_code=404, detail="Akun tidak ditemukan.")
    upd = {k: v for k, v in payload.model_dump(exclude_unset=True).items() if v is not None}
    if "type" in upd and upd["type"] != acc.get("type"):
        used = await db.journal_entries.count_documents({"org_id": org, "lines.account_code": code})
        if used:
            raise HTTPException(status_code=400, detail=(
                f"Tipe akun {code} tidak boleh diubah: sudah dipakai {used} jurnal. "
                "Buat akun baru bila klasifikasinya berbeda."))
    # GL-13: akun yang dipakai jurnal otomatis / sub-akun rekening aktif tidak boleh dilepas dari posting.
    system = code in coa_rules.system_codes() or code in coa_rules.CASH_HEADERS
    if system and "type" in upd and upd["type"] != acc.get("type"):
        raise HTTPException(status_code=400, detail=f"Tipe akun sistem {code} tidak boleh diubah.")
    if upd.get("parent_code") in coa_rules.CASH_HEADERS and upd["parent_code"] != acc.get("parent_code"):
        raise HTTPException(status_code=400, detail=(
            "Sub-akun Kas/Bank dibuat otomatis lewat menu Kas & Bank, bukan dengan memindahkan akun ke induk kas."))
    if upd.get("is_active") is False and acc.get("is_active") is not False:
        if system:
            raise HTTPException(status_code=400, detail=(
                f"Akun {code} {acc.get('name')} dipakai jurnal otomatis sistem — tidak boleh dinonaktifkan "
                "(transaksi berikutnya akan gagal diposting)."))
        master = await db.bank_accounts.find_one(
            {"org_id": org, "gl_account_code": code, "is_active": {"$ne": False}}, {"_id": 0, "name": 1})
        if master:
            raise HTTPException(status_code=400, detail=(
                f"Akun {code} masih dipakai rekening/kas aktif '{master.get('name')}'. Nonaktifkan "
                "rekeningnya dari menu Kas & Bank (saldonya harus nol), bukan dari Bagan Akun."))
    if upd.get("is_active") is False:
        bal = await db.journal_entries.count_documents({"org_id": org, "lines.account_code": code})
        upd["deactivated_at"] = now_iso()
        upd["had_transactions"] = bool(bal)
    if not upd:
        return {"data": serialize_doc(acc)}
    upd["updated_at"] = now_iso()
    await db.accounts.update_one({"org_id": org, "code": code}, {"$set": upd})
    await audit_log(user, "update", "accounts", code, {"fields": sorted(upd)})
    return {"data": serialize_doc(await db.accounts.find_one({"org_id": org, "code": code}, {"_id": 0}))}
