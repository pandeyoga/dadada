"""MODUL PENGAJUAN KEUANGAN (fund requests) — satu pintu untuk semua permintaan dana.

Jenis: biaya operasional, reimbursement, pembelian, pembayaran vendor, kas bon (uang muka).
Alur satu tahap: submitted → approved → disbursed (→ settled khusus kas bon) | rejected | cancelled.

Jurnal (idempoten via `source_event`):
  * Pencairan non-kas-bon  : Dr beban/WIP per kategori (CASHBON_ACCOUNT) / Cr kas|bank
  * Pencairan kas bon      : Dr 1-1500 Uang Muka Karyawan / Cr kas|bank
  * Pertanggungjawaban     : memakai aturan kas bon (petty_cash._settle_lines)
"""
import gl_engine as gl
import reference_p27 as r27
import sequences as seq
from core_utils import new_id, now_iso
from db import ORG_ID, db
from engine import add_activity, create_notification, emit
from finance_engine import notify_finance
from p27_utils import cash_account, rp
from petty_cash import ADVANCE_ACCOUNT, _settle_lines

COLL = "fund_requests"


async def _get(rid: str, org: str) -> dict:
    doc = await db[COLL].find_one({"id": rid, "org_id": org}, {"_id": 0})
    if not doc:
        raise ValueError("Pengajuan tidak ditemukan.")
    return doc


async def _files(org: str, ids: list) -> list:
    if not ids:
        return []
    return await db.files.find({"id": {"$in": ids}, "org_id": org, "is_deleted": False},
                               {"_id": 0, "id": 1, "filename": 1, "content_type": 1, "size": 1}
                               ).to_list(len(ids))


async def _bind_ap_bill(org: str, payload) -> dict:
    """vendor_payment yang menunjuk tagihan AP: cek tagihan sah & belum diajukan orang lain."""
    if payload.type != "vendor_payment":
        raise ValueError("Hanya pengajuan jenis pembayaran vendor yang boleh menunjuk tagihan AP.")
    bill = await db.ap_invoices.find_one({"id": payload.ap_bill_id, "org_id": org}, {"_id": 0})
    if not bill:
        raise ValueError("Tagihan AP tidak ditemukan.")
    if bill.get("status") not in ("approved", "partial"):
        raise ValueError("Tagihan AP harus sudah DISETUJUI dan belum lunas untuk diajukan pembayarannya.")
    outstanding = int(bill.get("net", 0)) - int(bill.get("paid", 0))
    if int(payload.amount) > outstanding:
        raise ValueError(f"Nominal {rp(payload.amount)} melebihi sisa tagihan {rp(outstanding)} "
                         f"({bill.get('vendor')}).")
    dup = await db[COLL].find_one({"org_id": org, "ap_bill_id": bill["id"],
                                   "status": {"$in": ["submitted", "approved"]}}, {"_id": 0, "no": 1})
    if dup:
        raise ValueError(f"Tagihan ini sudah diajukan pembayarannya lewat {dup['no']} — "
                         "satu tagihan tidak boleh diajukan dua kali.")
    return bill


async def create(payload, actor: str, actor_name: str, org: str = ORG_ID) -> dict:
    ts = now_iso()
    no = await seq.next_number("fund_request", org, prefix="PGJ", width=4,
                               context={"project_id": payload.project_id})
    project = None
    if payload.project_id:
        project = await db.projects.find_one({"id": payload.project_id, "org_id": org},
                                             {"_id": 0, "name": 1})
    items = [{"description": i.description, "qty": int(i.qty), "unit_price": int(i.unit_price),
              "amount": int(i.qty) * int(i.unit_price)} for i in payload.items]
    if payload.type == "reimbursement" and not payload.attachment_ids:
        raise ValueError("Reimbursement wajib melampirkan bukti pembayaran (nota/struk).")
    bill = await _bind_ap_bill(org, payload) if getattr(payload, "ap_bill_id", None) else None
    doc = {
        "id": new_id(), "org_id": org, "no": no, "type": payload.type, "status": "submitted",
        "title": payload.title, "amount": int(payload.amount), "approved_amount": None,
        "category": payload.category, "urgency": payload.urgency,
        "needed_date": payload.needed_date, "project_id": payload.project_id or (bill or {}).get("project_id"),
        "project_name": (project or {}).get("name"),
        "payee_name": payload.payee_name or (bill or {}).get("vendor"), "payee_bank": payload.payee_bank,
        "payee_account": payload.payee_account, "items": items,
        "ap_bill_id": (bill or {}).get("id"), "ap_bill_note": (bill or {}).get("note"),
        "ap_bill_outstanding": (int(bill["net"]) - int(bill.get("paid", 0))) if bill else None,
        "attachments": await _files(org, payload.attachment_ids), "note": payload.note,
        "requested_by": actor, "requester_name": actor_name,
        "approved_by": None, "approved_at": None, "approve_note": None,
        "rejected_by": None, "rejected_at": None, "reject_reason": None,
        "disbursed_amount": 0, "disbursed_at": None, "disbursed_by": None, "source": None,
        "expenses": [], "expense_total": 0, "returned_amount": 0, "reimburse_amount": 0,
        "settled_at": None, "settled_by": None, "journal_ids": [],
        "history": [{"at": ts, "actor": actor, "action": "submitted", "note": None}],
        "created_at": ts, "updated_at": ts,
    }
    await db[COLL].insert_one(dict(doc))
    doc.pop("_id", None)
    await add_activity(entity_type="fund_request", entity_id=doc["id"], type="system",
                       body=f"Pengajuan {no} ({payload.type}) {rp(payload.amount)} — {payload.title}.",
                       actor=actor, org_id=org)
    await notify_finance(org, "Pengajuan keuangan baru",
                         f"{actor_name or actor} mengajukan {no} {rp(payload.amount)}: {payload.title}.",
                         "approval", "fund_request", doc["id"])
    await emit("fund_request.submitted", "fund_request", doc["id"],
               {"amount": int(payload.amount), "type": payload.type}, org_id=org)
    return doc


async def _push(rid: str, sets: dict, actor: str, action: str, note=None, journal_id=None):
    ts = now_iso()
    upd = {"$set": {**sets, "updated_at": ts},
           "$push": {"history": {"at": ts, "actor": actor, "action": action, "note": note}}}
    if journal_id:
        upd["$push"]["journal_ids"] = journal_id
    await db[COLL].update_one({"id": rid}, upd)


async def approve(rid: str, actor: str, note=None, approved_amount=None, org: str = ORG_ID) -> dict:
    r = await _get(rid, org)
    if r["status"] != "submitted":
        raise ValueError("Hanya pengajuan berstatus 'Diajukan' yang dapat disetujui.")
    if r["requested_by"] == actor:
        raise ValueError("Pemisahan tugas: pemohon tidak boleh menyetujui pengajuannya sendiri.")
    amt = int(approved_amount) if approved_amount else int(r["amount"])
    if amt <= 0 or amt > int(r["amount"]):
        raise ValueError(f"Nominal disetujui harus antara Rp 1 dan {rp(r['amount'])}.")
    ts = now_iso()
    await _push(rid, {"status": "approved", "approved_by": actor, "approved_at": ts,
                      "approve_note": note, "approved_amount": amt}, actor, "approved", note)
    await create_notification(user_email=r["requested_by"], title="Pengajuan disetujui",
                              body=f"Pengajuan {r['no']} disetujui {rp(amt)} — menunggu pencairan.",
                              type="approval", related_entity_type="fund_request",
                              related_entity_id=rid, org_id=org)
    return await _get(rid, org)


async def reject(rid: str, actor: str, reason=None, org: str = ORG_ID) -> dict:
    r = await _get(rid, org)
    if r["status"] not in ("submitted", "approved"):
        raise ValueError("Pengajuan ini tidak dapat ditolak (sudah dicairkan/selesai).")
    ts = now_iso()
    await _push(rid, {"status": "rejected", "rejected_by": actor, "rejected_at": ts,
                      "reject_reason": reason}, actor, "rejected", reason)
    await create_notification(user_email=r["requested_by"], title="Pengajuan ditolak",
                              body=f"Pengajuan {r['no']} ditolak. {reason or ''}".strip(),
                              type="approval", related_entity_type="fund_request",
                              related_entity_id=rid, org_id=org)
    return await _get(rid, org)


async def cancel(rid: str, actor: str, org: str = ORG_ID) -> dict:
    r = await _get(rid, org)
    if r["status"] not in ("submitted", "approved"):
        raise ValueError("Hanya pengajuan yang belum dicairkan yang dapat dibatalkan.")
    await _push(rid, {"status": "cancelled"}, actor, "cancelled")
    return await _get(rid, org)


async def disburse(rid: str, payload, actor: str, org: str = ORG_ID) -> dict:
    r = await _get(rid, org)
    if r["status"] != "approved":
        raise ValueError("Pengajuan harus disetujui terlebih dahulu sebelum dicairkan.")
    cap = int(r.get("approved_amount") or r["amount"])
    amt = int(payload.amount) if payload.amount else cap
    if amt <= 0 or amt > cap:
        raise ValueError(f"Pencairan {rp(amt)} di luar nominal disetujui {rp(cap)}.")
    import cash_bank as cb
    cash_code = await cb.resolve_code(org, payload.cash_account_id, cash_account(payload.source))
    cash_acc = await cb.account_by_code(org, cash_code)
    if r.get("ap_bill_id"):
        # Pembayaran vendor yang menunjuk tagihan AP: lunasi 2-1100 lewat mesin AP (jurnal
        # Dr Utang Usaha / Cr kas) — beban sudah diakui saat tagihan disetujui.
        import finance_engine as fe
        bill, pay = await fe.pay_ap_bill(r["ap_bill_id"], amt, f"Pengajuan {r['no']} — {r['title']}",
                                         actor, org, return_payment=True,
                                         cash_account_id=(cash_acc or {}).get("id"))
        je = await db.journal_entries.find_one(
            {"org_id": org, "source_type": "ap_bill", "source_id": bill["id"],
             "memo": {"$regex": "^Pembayaran"}}, {"_id": 0, "id": 1, "entry_no": 1},
            sort=[("created_at", -1)]) or {"id": None, "entry_no": "-"}
        extra_set = {"ap_payment_id": pay["id"], "ap_bill_status": bill.get("status")}
    else:
        if r["type"] == "advance":
            debit = ADVANCE_ACCOUNT
            memo = f"Pencairan kas bon {r['no']} — {r.get('requester_name') or r['requested_by']}"
        else:
            debit = r27.CASHBON_ACCOUNT.get(r.get("category"), "6-1300")
            memo = f"Pencairan pengajuan {r['no']} — {r['title']}"
        je = await gl.post_journal(
            org, memo, [{"account_code": debit, "debit": amt, "credit": 0},
                        {"account_code": cash_code, "debit": 0, "credit": amt}],
            source_type="fund_request", source_id=rid,
            source_event=f"fund_request.disburse:{rid}", posted_by=actor)
        extra_set = {}
    ts = now_iso()
    final = "disbursed" if r["type"] == "advance" else "settled"
    await _push(rid, {"status": final, "disbursed_amount": amt, "disbursed_at": ts,
                      "disbursed_by": actor, "source": payload.source,
                      "reference_no": payload.reference_no, "disburse_note": payload.note,
                      "cash_account_id": (cash_acc or {}).get("id"), "cash_account_code": cash_code,
                      "cash_account_name": (cash_acc or {}).get("name"), **extra_set,
                      **({"settled_at": ts, "settled_by": actor, "expense_total": amt}
                         if final == "settled" else {})},
                actor, "disbursed", payload.note, journal_id=je["id"])
    await add_activity(entity_type="fund_request", entity_id=rid, type="system",
                       body=f"Pengajuan {r['no']} dicairkan {rp(amt)} ({payload.source}). "
                            f"Jurnal {je['entry_no']}.", actor=actor, org_id=org)
    await create_notification(user_email=r["requested_by"], title="Pengajuan dicairkan",
                              body=f"Pengajuan {r['no']} cair {rp(amt)}."
                                   + (" Segera isi pertanggungjawaban." if final == "disbursed" else ""),
                              type="finance", related_entity_type="fund_request",
                              related_entity_id=rid, org_id=org)
    await emit("fund_request.disbursed", "fund_request", rid, {"amount": amt}, org_id=org)
    return await _get(rid, org)


async def settle(rid: str, payload, actor: str, org: str = ORG_ID) -> dict:
    r = await _get(rid, org)
    if r["type"] != "advance" or r["status"] != "disbursed":
        raise ValueError("Pertanggungjawaban hanya untuk kas bon yang sudah dicairkan.")
    rows = [{"id": new_id(), "category": it.category, "description": it.description,
             "amount": int(it.amount), "date": it.date or now_iso()} for it in payload.items]
    lines, total, returned, reimburse = _settle_lines(r, rows)
    if total <= 0:
        raise ValueError("Total realisasi harus lebih dari 0.")
    je = await gl.post_journal(org, f"Pertanggungjawaban kas bon {r['no']}", lines,
                               source_type="fund_request", source_id=rid,
                               source_event=f"fund_request.settle:{rid}", posted_by=actor)
    ts = now_iso()
    await _push(rid, {"status": "settled", "expenses": rows, "expense_total": total,
                      "returned_amount": returned, "reimburse_amount": reimburse,
                      "settle_attachments": await _files(org, payload.attachment_ids),
                      "settled_at": ts, "settled_by": actor, "settle_note": payload.note},
                actor, "settled", payload.note, journal_id=je["id"])
    detail = f"realisasi {rp(total)}"
    if returned:
        detail += f", sisa dikembalikan {rp(returned)}"
    if reimburse:
        detail += f", penggantian {rp(reimburse)}"
    await add_activity(entity_type="fund_request", entity_id=rid, type="system",
                       body=f"Kas bon {r['no']} dipertanggungjawabkan: {detail}. Jurnal {je['entry_no']}.",
                       actor=actor, org_id=org)
    await notify_finance(org, "Kas bon dipertanggungjawabkan", f"{r['no']} — {detail}.",
                         "finance", "fund_request", rid)
    return await _get(rid, org)


async def summary(org: str = ORG_ID, requested_by: str = None) -> dict:
    q = {"org_id": org}
    if requested_by:
        q["requested_by"] = requested_by
    rows = await db[COLL].find(q, {"_id": 0, "status": 1, "amount": 1, "approved_amount": 1,
                                   "disbursed_amount": 1, "type": 1}).to_list(5000)
    def _sum(st, key="amount"):
        return sum(int(r.get(key) or r.get("amount") or 0) for r in rows if r["status"] == st)
    return {
        "count": len(rows),
        "waiting_approval": sum(1 for r in rows if r["status"] == "submitted"),
        "waiting_approval_amount": _sum("submitted"),
        "ready_to_disburse": sum(1 for r in rows if r["status"] == "approved"),
        "ready_to_disburse_amount": _sum("approved", "approved_amount"),
        "advance_outstanding": sum(1 for r in rows if r["status"] == "disbursed"),
        "advance_outstanding_amount": _sum("disbursed", "disbursed_amount"),
        "disbursed_total": sum(int(r.get("disbursed_amount") or 0) for r in rows
                               if r["status"] in ("disbursed", "settled")),
    }
