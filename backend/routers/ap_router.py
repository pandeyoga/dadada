"""AP (utang subcon) tipis: bills manual + retensi + approval + pembayaran + aging.

Fase 49F menambah satu pintu: pembayaran yang MEMOTONG PPh (vendor terima neto, potongan
menjadi utang pajak + bukti potong bernomor terbit otomatis).
"""
from fastapi import APIRouter, Depends, HTTPException

from db import db, ORG_ID
from core_utils import serialize_doc, parse_pagination
from rbac import require_permission, audit_log
import finance_engine as fe
import withholding_engine as wh
from models import ApBillCreate, ApPay
from models_p49 import BillPayWithholding

router = APIRouter(prefix="/finance/ap", tags=["finance-ap"])


@router.get("/bills")
async def list_bills(status: str = None, skip: int = 0, limit: int = 50,
                     user: dict = Depends(require_permission("finance", "view"))):
    org = user.get("org_id", ORG_ID)
    skip, limit = parse_pagination(skip, limit)
    q = {"org_id": org}
    if status:
        q["status"] = status
    total = await db.ap_invoices.count_documents(q)
    rows = await db.ap_invoices.find(q, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    return {"data": serialize_doc(rows), "total": total}


@router.get("/aging")
async def ap_aging(user: dict = Depends(require_permission("finance", "view"))):
    return {"data": await fe.ap_aging(user.get("org_id", ORG_ID))}


@router.post("/bills")
async def create_bill(payload: ApBillCreate,
                      user: dict = Depends(require_permission("finance", "create"))):
    if payload.claimed <= 0:
        raise HTTPException(status_code=400, detail="Nilai klaim harus lebih dari 0")
    bill = await fe.create_ap_bill(payload.vendor, payload.project_id, payload.claimed,
                                   payload.retention_pct, payload.due_date, payload.note,
                                   user.get("email"), user.get("org_id", ORG_ID))
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
    po = (await db.purchase_orders.find_one({"org_id": org, "id": bill["po_id"]}, {"_id": 0, "id": 1, "po_number": 1, "po_type": 1, "vendor": 1, "total": 1})
          if bill.get("po_id") else None)
    fund_reqs = await db.fund_requests.find({"org_id": org, "ap_bill_id": bill_id}, {"_id": 0, "id": 1, "no": 1, "status": 1, "amount": 1,
                                                                                     "disbursed_amount": 1, "requested_by": 1, "created_at": 1}).to_list(50)
    withholding = await db.withholding_docs.find({"org_id": org, "bill_id": bill_id}, {"_id": 0}).to_list(50)
    src_ids = [bill_id] + ([retention["id"]] if retention else []) + ([source_retention["id"]] if source_retention else [])
    journals = await db.journal_entries.find({"org_id": org, "source_id": {"$in": src_ids}}, {"_id": 0}).sort([("date", 1), ("created_at", 1)]).to_list(200)
    project = (await db.projects.find_one({"org_id": org, "id": bill["project_id"]}, {"_id": 0, "id": 1, "name": 1}) if bill.get("project_id") else None)
    paid = sum(int(p.get("amount", 0)) for p in payments)
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


@router.post("/bills/{bill_id}/approve")
async def approve_bill(bill_id: str,
                       user: dict = Depends(require_permission("finance", "approve"))):
    try:
        bill = await fe.approve_ap_bill(bill_id, user.get("email"), user.get("org_id", ORG_ID))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"data": serialize_doc(bill)}


@router.post("/bills/{bill_id}/pay")
async def pay_bill(bill_id: str, payload: ApPay,
                   user: dict = Depends(require_permission("finance", "approve"))):
    if payload.amount <= 0:
        raise HTTPException(status_code=400, detail="Jumlah bayar harus lebih dari 0")
    try:
        bill = await fe.pay_ap_bill(bill_id, payload.amount, payload.note,
                                    user.get("email"), user.get("org_id", ORG_ID),
                                    cash_account_id=payload.cash_account_id)
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
    try:
        updated, payment = await fe.pay_ap_bill(
            bill_id, payload.amount, payload.note, user.get("email"), org,
            withhold={"kind": payload.kind, "base": base, "rate": payload.rate,
                      "amount": withheld, "memo": memo},
            return_payment=True, cash_account_id=payload.cash_account_id)
        doc = await wh.issue_for_bill_payment(
            org, user.get("email"), bill=bill, payment=payment, kind=payload.kind,
            base=base, rate=payload.rate, object_code=payload.object_code,
            note=payload.note)
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
    async for r in db.payments_out.aggregate([{"$match": q}, {"$group": {"_id": None, "s": {"$sum": "$amount"}}}]):
        paid_total = int(r.get("s") or 0)
    return {"data": serialize_doc(rows), "total": total, "summary": {"paid_total": paid_total}}
