"""AP (utang subcon) tipis: bills manual + retensi + approval + pembayaran + aging.

Fase 49F menambah satu pintu: pembayaran yang MEMOTONG PPh (vendor terima neto, potongan
menjadi utang pajak + bukti potong bernomor terbit otomatis).
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from db import db, ORG_ID
from org_scope import exists_in_org
from core_utils import serialize_doc, parse_pagination
from rbac import require_permission, audit_log
import finance_ap as fap
import finance_engine as fe
import withholding_engine as wh
from models import ApBillCreate, ApPay
from models_p49 import BillPayWithholding
from idempotency import Conflict
from sod import assert_separate

router = APIRouter(prefix="/finance/ap", tags=["finance-ap"])


class ApPayDated(ApPay):
    """`ApPay` + tanggal bayar nyata (GL-15). Dipisah dari models.py yang sudah melewati batas ukuran."""
    value_date: Optional[str] = None


async def _value_date(org: str, value, cash_account_id: str = None):
    """Validasi tanggal bayar (tidak masa depan / periode tertutup / rekening terkunci) → HTTP 400 bila tidak sah."""
    import cash_bank as _cb
    import value_date as vd
    try:
        code = await _cb.resolve_code(org, cash_account_id, "1-1200") if value else None
        return await vd.check(org, value, cash_code=code)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/bills")
async def list_bills(status: str = None, po_cancelled: bool = None, skip: int = 0, limit: int = 50,
                     user: dict = Depends(require_permission("finance", "view"))):
    """Daftar tagihan AP. Tiap baris ber-PO diberi `po_cancelled` (PG-06 sisa: tagihan atas PO yang sudah batal tidak boleh
    disetujui/dibayar); `po_cancelled=true|false` menyaring."""
    org = user.get("org_id", ORG_ID)
    skip, limit = parse_pagination(skip, limit)
    q = {"org_id": org}
    if status:
        q["status"] = status
    if po_cancelled is not None:
        ids = await fap.cancelled_po_ids(org)
        q["po_id"] = {"$in": ids} if po_cancelled else {"$nin": ids}
    total = await db.ap_invoices.count_documents(q)
    rows = await db.ap_invoices.find(q, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    await fap.annotate_po_cancelled(org, rows)
    return {"data": serialize_doc(rows), "total": total}


@router.get("/aging")
async def ap_aging(user: dict = Depends(require_permission("finance", "view"))):
    return {"data": await fe.ap_aging(user.get("org_id", ORG_ID))}


@router.post("/bills")
async def create_bill(payload: ApBillCreate,
                      user: dict = Depends(require_permission("finance", "create"))):
    if payload.project_id:
        await exists_in_org(db.projects, payload.project_id, user, name="Proyek")
    if payload.claimed <= 0:
        raise HTTPException(status_code=400, detail="Nilai klaim harus lebih dari 0")
    try:
        bill = await fe.create_ap_bill(payload.vendor, payload.project_id, payload.claimed,
                                       payload.retention_pct, payload.due_date, payload.note,
                                       user.get("email"), user.get("org_id", ORG_ID),
                                       vendor_invoice_no=payload.vendor_invoice_no)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"data": serialize_doc(bill)}


@router.get("/bills/{bill_id}")
async def bill_detail(bill_id: str, user: dict = Depends(require_permission("finance", "view"))):
    """Satu tagihan AP utuh: pembayaran, retensi, jurnal, dan dokumen sumbernya."""
    org = user.get("org_id", ORG_ID)
    bill = await db.ap_invoices.find_one({"id": bill_id, "org_id": org}, {"_id": 0})
    if not bill:
        raise HTTPException(status_code=404, detail="Tagihan AP tidak ditemukan.")
    payments = await db.payments_out.find({"org_id": org, "bill_id": bill_id}, {"_id": 0}).sort("created_at", 1).to_list(500)
    retention = await db.subcon_retentions.find_one({"org_id": org, "ap_bill_id": bill_id}, {"_id": 0})
    source_retention = (await db.subcon_retentions.find_one({"org_id": org, "id": bill.get("retention_id")}, {"_id": 0})
                        if bill.get("retention_id") else None)
    release_bill = (await db.ap_invoices.find_one({"org_id": org, "id": retention.get("release_bill_id")}, {"_id": 0})
                    if retention and retention.get("release_bill_id") else None)
    claim = await db.progress_claims.find_one({"org_id": org, "ap_bill_id": bill_id}, {"_id": 0})
    spk = (await db.spk.find_one({"org_id": org, "id": (claim or bill).get("spk_id")}, {"_id": 0, "id": 1, "spk_number": 1, "title": 1,
                                                                                           "contract_value": 1, "progress_pct": 1, "status": 1})
           if (claim or bill).get("spk_id") else None)
    po = (await db.purchase_orders.find_one({"org_id": org, "id": bill["po_id"]}, {"_id": 0, "id": 1, "po_number": 1, "po_type": 1, "vendor": 1, "total": 1, "status": 1})
          if bill.get("po_id") else None)
    await fap.annotate_po_cancelled(org, [bill])   # PG-06: tanda PO induk batal
    fund_reqs = await db.fund_requests.find({"org_id": org, "ap_bill_id": bill_id}, {"_id": 0, "id": 1, "no": 1, "status": 1, "amount": 1,
                                                                                     "disbursed_amount": 1, "requested_by": 1, "created_at": 1}).to_list(50)
    withholding = await db.withholding_docs.find({"org_id": org, "bill_id": bill_id}, {"_id": 0}).to_list(50)
    src_ids = [bill_id] + ([retention["id"]] if retention else []) + ([source_retention["id"]] if source_retention else [])
    journals = await db.journal_entries.find({"org_id": org, "source_id": {"$in": src_ids}}, {"_id": 0}).sort([("date", 1), ("created_at", 1)]).to_list(200)
    project = (await db.projects.find_one({"org_id": org, "id": bill["project_id"]}, {"_id": 0, "id": 1, "name": 1}) if bill.get("project_id") else None)
    paid = sum(int(p.get("amount", 0)) for p in payments if p.get("status") != "void")  # PK-09: yang dibatalkan tak dihitung
    return {"data": serialize_doc({
        "bill": bill, "project": project, "payments": payments, "withholding": withholding,
        "retention": retention, "source_retention": source_retention, "release_bill": release_bill,
        "claim": claim, "spk": spk, "po": po, "fund_requests": fund_reqs, "journals": journals,
        "summary": {"claimed": int(bill.get("claimed", 0)), "retention_held": int(bill.get("retention_held", 0)),
                    "deduction_total": int(bill.get("deduction_total", 0) or 0), "net": int(bill.get("net", 0)),
                    "paid": paid, "paid_recorded": int(bill.get("paid", 0)), "outstanding": int(bill.get("net", 0)) - int(bill.get("paid", 0)),
                    "withheld_total": int(bill.get("withheld_total", 0) or 0),
                    "paid_consistent": paid == int(bill.get("paid", 0)),
                    "journal_debit": sum(int(j.get("total_debit", 0)) for j in journals)},
    })}


async def _assert_payer_separate(user: dict, bill_id: str, org: str) -> None:
    """PK-07: yang MENYETUJUI tagihan tidak boleh sekaligus membayarnya.

    Tagihan yang disetujui otomatis oleh dokumen sumber yang sudah ber-SoD sendiri (termin subkon,
    pelepasan retensi: pembuat = penyetuju) tidak terkena aturan ini — pemisahan tugasnya sudah
    ditegakkan di dokumen sumber (pengaju ≠ verifikator ≠ penyetuju).
    """
    cur = await db.ap_invoices.find_one({"id": bill_id, "org_id": org},
                                        {"_id": 0, "created_by": 1, "approved_by": 1})
    if not cur or cur.get("approved_by") == cur.get("created_by"):
        return
    assert_separate(user, cur.get("approved_by"),
                    "Pemisahan tugas: yang menyetujui tagihan tidak boleh sekaligus membayarnya "
                    "— minta Keuangan lain yang melakukan pembayaran.")


@router.post("/bills/{bill_id}/approve")
async def approve_bill(bill_id: str,
                       user: dict = Depends(require_permission("finance", "approve"))):
    org = user.get("org_id", ORG_ID)
    await exists_in_org(db.ap_invoices, bill_id, user, name="Tagihan AP")
    try:
        cur = await db.ap_invoices.find_one({"id": bill_id, "org_id": org}, {"_id": 0, "created_by": 1})
        # PK-07: pembuat tagihan tidak boleh menyetujui tagihannya sendiri (maker-checker di API).
        assert_separate(user, (cur or {}).get("created_by"),
                        "Pemisahan tugas: pembuat tagihan tidak boleh menyetujui tagihannya sendiri "
                        "— minta orang lain (mis. Owner/Manajer Keuangan) yang menyetujui.")
        bill = await fe.approve_ap_bill(bill_id, user.get("email"), org)
    except Conflict:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"data": serialize_doc(bill)}


@router.post("/bills/{bill_id}/pay")
async def pay_bill(bill_id: str, payload: ApPayDated,
                   user: dict = Depends(require_permission("finance", "approve"))):
    if payload.amount <= 0:
        raise HTTPException(status_code=400, detail="Jumlah bayar harus lebih dari 0")
    await exists_in_org(db.ap_invoices, bill_id, user, name="Tagihan AP")
    org = user.get("org_id", ORG_ID)
    value_date = await _value_date(org, payload.value_date, payload.cash_account_id)
    try:
        await _assert_payer_separate(user, bill_id, org)
        bill = await fe.pay_ap_bill(bill_id, payload.amount, payload.note,
                                    user.get("email"), org,
                                    cash_account_id=payload.cash_account_id,
                                    client_ref=payload.client_ref, value_date=value_date)
    except Conflict:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"data": serialize_doc(bill)}


@router.post("/bills/{bill_id}/pay-withholding")
async def pay_bill_with_withholding(bill_id: str, payload: BillPayWithholding,
                                    user: dict = Depends(require_permission("finance", "approve"))):
    """Bayar tagihan DENGAN MEMOTONG PPh (Fase 49F): vendor menerima NET, potongan menjadi
    utang pajak, dan bukti potong bernomor terbit otomatis.

    Cacat yang ditutup: sebelum ini pembayaran selalu bruto. Kalau perusahaan sebenarnya
    memotong PPh jasa konstruksi/PPh 23, angka di sistem berbeda dengan uang yang benar-benar
    keluar dari bank, dan potongan yang menjadi kewajiban setor tidak pernah tercatat —
    bukti potong pun tidak bisa diterbitkan karena tidak ada pasangannya di pembukuan.

    Jurnalnya: `Dr 2-1100 Utang Usaha (bruto) / Cr 1-1200 Bank (neto) / Cr 2-1300 Utang Pajak`.
    Nilai potongan dihitung DI SINI (tarif × dasar) supaya angkanya terbaca sebelum uang keluar.
    """
    org = user.get("org_id", ORG_ID)
    bill = await db.ap_invoices.find_one({"id": bill_id, "org_id": org}, {"_id": 0})
    if not bill:
        raise HTTPException(status_code=404, detail="Tagihan AP tidak ditemukan.")
    base = int(payload.base or payload.amount)
    withheld = wh.tax_of(base, payload.rate)
    if withheld <= 0:
        raise HTTPException(status_code=400, detail=(
            f"Potongan hasil hitungan Rp 0 (dasar Rp {base:,} × {payload.rate}%). "
            "Pakai pembayaran biasa bila memang tidak ada potongan PPh."))
    memo = (f"PPh {payload.kind} {payload.rate}% atas "
            f"{bill.get('vendor')} (dasar Rp {base:,})")
    value_date = await _value_date(org, payload.value_date, payload.cash_account_id)
    try:
        await _assert_payer_separate(user, bill_id, org)
        updated, payment = await fe.pay_ap_bill(
            bill_id, payload.amount, payload.note, user.get("email"), org,
            withhold={"kind": payload.kind, "base": base, "rate": payload.rate,
                      "amount": withheld, "memo": memo},
            return_payment=True, cash_account_id=payload.cash_account_id,
            client_ref=payload.client_ref, value_date=value_date)
        doc = await wh.issue_for_bill_payment(
            org, user.get("email"), bill=bill, payment=payment, kind=payload.kind,
            base=base, rate=payload.rate, object_code=payload.object_code,
            note=payload.note)
    except Conflict:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await audit_log(user, "pay_withholding", "ap_invoices", bill_id,
                    {"amount": payload.amount, "withheld": withheld,
                     "bupot": doc.get("number")})
    return {"data": {"bill": serialize_doc(updated), "payment": serialize_doc(payment),
                     "withholding": serialize_doc(doc),
                     "cash_out": int(payload.amount) - withheld, "withheld": withheld,
                     "detail": (f"Kas keluar Rp {int(payload.amount) - withheld:,} ke "
                                f"{bill.get('vendor')}; PPh Rp {withheld:,} menjadi utang pajak "
                                f"dan dibuktikan bukti potong {doc.get('number')}.")}}


@router.get("/payments")
async def list_payments(bill_id: str = None, skip: int = 0, limit: int = 50,
                        user: dict = Depends(require_permission("finance", "view"))):
    """Riwayat pembayaran keluar. Sebelum audit koleksi `payments_out` DITULIS tapi tidak
    punya endpoint baca sama sekali, jadi bukti pembayaran tidak bisa ditelusuri."""
    skip, limit = parse_pagination(skip, limit)
    q = {"org_id": user.get("org_id", ORG_ID)}
    if bill_id:
        q["bill_id"] = bill_id
    total = await db.payments_out.count_documents(q)
    rows = await db.payments_out.find(q, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    paid_total = 0
    async for r in db.payments_out.aggregate([{"$match": {**q, "status": {"$ne": "void"}}},
                                              {"$group": {"_id": None, "s": {"$sum": "$amount"}}}]):
        paid_total = int(r.get("s") or 0)
    return {"data": serialize_doc(rows), "total": total, "summary": {"paid_total": paid_total}}


class ApPaymentVoidIn(BaseModel):
    reason: str = Field(min_length=10, max_length=500)


@router.post("/payments/{payment_id}/void")
async def void_payment(payment_id: str, payload: ApPaymentVoidIn,
                       user: dict = Depends(require_permission("finance", "approve"))):
    """BATALKAN satu pembayaran tagihan AP secara resmi (audit PK-09): jurnal pembalik terbit, subledger tagihan
    dikembalikan, bukti potong dibatalkan, pembayaran asli tetap tersimpan sebagai jejak. Pemisahan tugas:
    yang membayar tidak boleh membatalkan pembayarannya sendiri (kecuali Super Admin)."""
    import ap_void
    org = user.get("org_id", ORG_ID)
    pay = await db.payments_out.find_one({"id": payment_id, "org_id": org}, {"_id": 0})
    if not pay:
        raise HTTPException(status_code=404, detail="Pembayaran tidak ditemukan.")
    try:
        assert_separate(user, pay.get("actor"),
                        "Pemisahan tugas: pembayaran yang Anda catat sendiri tidak boleh Anda batalkan "
                        "— minta Keuangan lain / Direksi.")
        out = await ap_void.void_payment(org, payment_id, user.get("email"), payload.reason)
    except Conflict:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await audit_log(user, "void", "payments_out", payment_id,
                    {"reason": payload.reason.strip(), "bill_id": pay.get("bill_id"), "amount": pay.get("amount")})
    return {"data": out}
