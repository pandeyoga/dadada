"""Titipan biaya (2-1470) & invoice biaya terbuka pada DEAL BATAL — kebijakan terkonfigurasi (keputusan #12, docs/audit/12, W1-C).

Sebelumnya pembatalan hanya DIBLOK sampai titipan/invoice biaya diakui + catatan (`cancellation_costs.assert_ack`), tanpa jurnal.
Kini nasib uang itu mengikuti tiga kunci (level organisasi + proyek):

  cancel.cost_deposit.policy
    refund_dan_batalkan_invoice  (BAWAAN) saldo titipan biaya menjadi UTANG REFUND pembeli (2-1460) dan invoice biaya terbuka
                                 dibatalkan; pembatalan tidak lagi diblok gerbang pengakuan
    manual_dengan_pengakuan      perilaku lama persis: pembatalan diblok sampai diakui + catatan, tanpa jurnal
    hangus_sebagian              `forfeit_pct` dari saldo titipan ditahan developer (Pendapatan Lain-lain 4-1200 — akun yang sama
                                 dengan booking fee hangus & potongan pembatalan), sisanya menjadi utang refund
  cancel.cost_deposit.forfeit_pct         0–100, hanya dibaca `hangus_sebagian`
  cancel.cost_deposit.requires_approval   bool (bawaan true): ya → pembatalan hanya melahirkan PERMOHONAN (`cost_deposit_settlements`)
                                          yang harus disetujui Keuangan — penyetuju HARUS orang lain dari pemohon (maker-checker);
                                          tidak → permohonan langsung dijalankan saat pembatalan.

"Saldo titipan" = Σ kuitansi biaya − Σ penyaluran (`allin_engine.ledger`), jadi biaya yang SUDAH benar-benar disalurkan ke notaris/BPN
otomatis tidak ikut direfund. Dibaca ULANG di bawah kunci saat eksekusi (uang bisa bergerak antara pembatalan dan persetujuan).

Eksekusi (di bawah `deal_money` + mutex titipan kontrak — kunci yang sama dengan bayar-invoice-biaya & salurkan-titipan, jadi tak ada celah):
  * subledger: baris `cost_disbursements` (`kind` = refund_pembatalan | hangus_pembatalan) → saldo titipan turun, dan rekonsiliasi 2-1470
    (Σ kuitansi − Σ penyaluran) TETAP sama dengan buku besar tanpa perubahan rumus;
  * jurnal tunggal `source_event=costsettle:<id>:approve`: Dr 2-1470 saldo / Cr 2-1460 refund [/ Cr 4-1200 hangus];
  * invoice biaya: `unpaid` → `void`; `partial` → `cancelled` (outstanding 0, `paid` TIDAK diubah — uang yang sudah masuk tetap tercatat
    dan ikut direfund lewat saldo titipan); `paid` tidak disentuh. Kalah balapan → dilewati + dicatat, tidak merusak.
Pembayaran refund memakai `money_op` (once → deal_money → funds_guard): Dr 2-1460 / Cr kas|bank, bertahap, idempoten.
Deal batal tidak bisa menerbitkan invoice biaya baru (`allin_engine.issue_cost_invoice`).
"""
import logging

from pymongo.errors import DuplicateKeyError

import allin_engine as allin
import cancellation_costs as cc
import cancellation_engine as cx
import gl_engine as gl
import policy
import reference as ref
import sequences as seq
from core_utils import new_id, now_iso
from db import db
from deal_money import deal_money
from idempotency import Conflict, mutex, reserved, transition
from money_op import money_op

logger = logging.getLogger("sipro.cancel_cost_settlement")

KEY_POLICY, KEY_PCT, KEY_APPROVAL = cc.KEY_POLICY, "cancel.cost_deposit.forfeit_pct", "cancel.cost_deposit.requires_approval"
FORFEIT_POLICY = "hangus_sebagian"
AKUN_TITIPAN = allin.GL_TITIPAN_BIAYA          # 2-1470 Titipan Biaya Customer
AKUN_UTANG_REFUND = cx.AKUN_UTANG_REFUND       # 2-1460 Utang Refund Pembatalan (SSOT pembatalan)
AKUN_HANGUS = cx.AKUN_POTONGAN                 # 4-1200 Pendapatan Lain-lain (sama dengan potongan pembatalan & booking fee hangus)
IN_FLIGHT = ("diajukan", "disetujui", "refund_sebagian")
FOLLOWUP_PREFIX = "deal.cancel_followup:"      # tugas dengan awalan ini TIDAK ikut ditutup oleh penutup deal batal
SYSTEM_APPROVER = "sistem:kebijakan"
MIN_NOTE = 10
COLL = "cost_deposit_settlements"


def _rp(v) -> str:
    return f"Rp {int(v or 0):,}".replace(",", ".")


async def read_policy(org: str, project_id: str = None) -> dict:
    snap = await policy.snapshot([KEY_POLICY, KEY_PCT, KEY_APPROVAL], org_id=org, project_id=project_id)
    return {"policy": snap[KEY_POLICY]["value"], "forfeit_pct": float(snap[KEY_PCT]["value"] or 0),
            "requires_approval": bool(snap[KEY_APPROVAL]["value"]), "snapshot": snap}


# ------------------------------------------------------------------ dipanggil penutup deal batal
async def apply_policy(org: str, deal: dict, *, actor: str, source: str, reason: str, deal_lock_held: bool = True) -> dict:
    """Terapkan kebijakan titipan biaya untuk `deal` yang BARU batal. Idempoten: satu permohonan aktif per deal."""
    pol = await read_policy(org, deal.get("project_id"))
    out = {"mode": pol["policy"], "forfeit_pct": pol["forfeit_pct"], "requires_approval": pol["requires_approval"],
           "policy_snapshot": pol["snapshot"], "handled": False}
    if pol["policy"] not in cc.POLICY_HANDLING:
        return out        # manual_dengan_pengakuan: gerbang pengakuan + tugas Keuangan (perilaku lama)
    live = await db[COLL].find_one({"org_id": org, "deal_id": deal["id"], "state": {"$in": list(IN_FLIGHT)}}, {"_id": 0})
    if live:
        return {**out, "handled": True, "idempotent": True, "settlement_id": live["id"], "number": live["number"],
                "state": live["state"]}
    holds = await cc.holds_of_deal(org, deal)
    if not holds["has_holds"]:
        return {**out, "handled": True, "nothing_to_do": True}
    ts = now_iso()
    sid = new_id()
    doc = {
        "id": sid, "org_id": org,
        "number": await seq.next_number("cost_settlement", org, prefix="RTB", context={
            "project_id": deal.get("project_id"), "unit_id": deal.get("unit_id")}),
        "deal_id": deal["id"], "contract_id": deal.get("contract_id"), "project_id": deal.get("project_id"),
        "unit_id": deal.get("unit_id"), "unit_code": deal.get("unit_code"), "customer_name": deal.get("lead_name"),
        "assigned_to": deal.get("assigned_to"), "source": source, "cancel_reason": reason,
        "policy": pol["policy"], "forfeit_pct": pol["forfeit_pct"] if pol["policy"] == FORFEIT_POLICY else 0,
        "requires_approval": pol["requires_approval"], "policy_snapshot": pol["snapshot"],
        "state": "diajukan", "requested_by": actor, "requested_at": ts,
        "snapshot": {"titipan_balance": holds["titipan_balance"], "open_invoices": holds["open_invoices"],
                     "open_invoice_total": holds["open_invoice_total"]},
        "decision": None, "settlement": None, "refund_paid_total": 0, "refund_payments": [],
        "created_at": ts, "updated_at": ts}
    try:
        await db[COLL].insert_one(dict(doc))
    except DuplicateKeyError:   # dua penutup bersamaan: indeks unik `uq_costsettle_inflight` memenangkan satu
        live = await db[COLL].find_one({"org_id": org, "deal_id": deal["id"], "state": {"$in": list(IN_FLIGHT)}}, {"_id": 0})
        return {**out, "handled": True, "idempotent": True, "settlement_id": (live or {}).get("id"),
                "number": (live or {}).get("number"), "state": (live or {}).get("state")}
    out.update({"handled": True, "settlement_id": sid, "number": doc["number"], "state": "diajukan"})
    from engine import add_activity, auto_create_task
    from finance_engine import notify_finance
    body = (f"Deal unit {deal.get('unit_code') or '-'} dibatalkan ({source}). Titipan biaya {_rp(holds['titipan_balance'])} (2-1470) "
            f"dan invoice biaya terbuka {_rp(holds['open_invoice_total'])} diajukan "
            + ("refund + pembatalan invoice" if pol["policy"] != FORFEIT_POLICY
               else f"refund (hangus {pol['forfeit_pct']:g}%) + pembatalan invoice")
            + (f" — permohonan {doc['number']} menunggu persetujuan Keuangan (penyetuju harus orang lain dari pemohon)."
               if pol["requires_approval"] else f" — {doc['number']} dijalankan otomatis oleh kebijakan."))
    await add_activity(entity_type="lead", entity_id=deal.get("lead_id"), type="system", actor=actor, org_id=org, body=body)
    if pol["requires_approval"]:
        await notify_finance(org, "Permohonan refund titipan biaya menunggu persetujuan", body, "finance", COLL, sid)
        await auto_create_task(source_event=f"{FOLLOWUP_PREFIX}costsettle:{sid}",
                               title=f"Setujui refund titipan biaya {doc['number']} — unit {deal.get('unit_code') or '-'}",
                               type="todo", related_entity_type="deal", related_entity_id=deal["id"], assigned_to=None,
                               description=body, priority="high", org_id=org)
    else:
        try:
            res = await execute(org, sid, SYSTEM_APPROVER, "Dijalankan otomatis (requires_approval=false)", auto=True,
                                deal_lock_held=deal_lock_held)
            out["state"] = res["state"]
        except Exception as e:  # noqa: BLE001  — gagal otomatis → tetap permohonan `diajukan` untuk Keuangan
            logger.exception("Eksekusi otomatis refund titipan biaya %s gagal", sid)
            await db[COLL].update_one({"id": sid, "state": "diajukan"}, {"$set": {"auto_error": str(e)[:300]}})
            await notify_finance(org, "Refund titipan biaya gagal dijalankan otomatis",
                                 f"{doc['number']}: {str(e)[:200]}. Setujui manual dari daftar Pembatalan & Refund.",
                                 "finance", COLL, sid)
    return out


# ------------------------------------------------------------------ eksekusi (jurnal + subledger + invoice)
async def _get(org: str, sid: str) -> dict:
    s = await db[COLL].find_one({"id": sid, "org_id": org}, {"_id": 0})
    if not s:
        raise ValueError("Permohonan refund titipan biaya tidak ditemukan.")
    return s


async def execute(org: str, sid: str, approver: str, note: str, *, auto: bool = False, deal_lock_held: bool = False) -> dict:
    """Setujui + jalankan permohonan. `deal_lock_held=True` bila pemanggil (penutup deal batal) sudah memegang `deal_money`."""
    s = await _get(org, sid)
    if s["state"] != "diajukan":
        raise ValueError(f"Permohonan {s['number']} sudah {ref.label_of('cost_settlement_state', s['state']).lower()} — "
                         "tidak bisa diputus dua kali.")
    if s.get("requested_by") == approver and not auto:
        raise ValueError("Pemohon tidak boleh menyetujui permohonannya sendiri (pemisahan tugas) — minta Keuangan lain.")
    if deal_lock_held:
        return await _execute_titipan_locked(org, sid, approver, note, auto)
    async with deal_money(org, s["deal_id"]):
        return await _execute_titipan_locked(org, sid, approver, note, auto)


async def _execute_titipan_locked(org: str, sid: str, approver: str, note: str, auto: bool) -> dict:
    s = await _get(org, sid)
    async with mutex(f"allin.titipan:{org}:{s.get('contract_id')}", what="Titipan biaya kontrak ini"):
        deal = await db.deals.find_one({"id": s["deal_id"], "org_id": org}, {"_id": 0}) or {"id": s["deal_id"]}
        contract = await allin.deal_as_contract(org, {**deal, "id": s["deal_id"]})
        ts = now_iso()
        async with reserved(COLL, {"id": sid, "org_id": org}, {"state": "diajukan"},
                            {"$set": {"state": "disetujui", "updated_at": ts,
                                      "decision": {"approved": True, "by": approver, "at": ts, "note": note, "auto": auto}}},
                            undo={"$set": {"state": "diajukan"}, "$unset": {"decision": ""}},
                            what="Permohonan refund titipan biaya"):
            res = await _post(org, s, contract, approver, ts)
            state = "selesai" if res["refund_amount"] <= 0 else "disetujui"
            await db[COLL].update_one({"id": sid}, {"$set": {"settlement": res, "state": state, "updated_at": ts}})
    await _close_request_task(org, sid)
    from engine import add_activity
    from finance_engine import notify_finance
    msg = (f"Permohonan {s['number']} DISETUJUI ({approver}): titipan biaya {_rp(res['titipan_balance'])} → utang refund "
           f"{_rp(res['refund_amount'])}" + (f", hangus {_rp(res['forfeit_amount'])}" if res["forfeit_amount"] else "")
           + f"; invoice biaya dibatalkan {len(res['invoices_voided']) + len(res['invoices_cancelled_partial'])}.")
    await add_activity(entity_type="lead", entity_id=deal.get("lead_id"), type="system", actor=approver, org_id=org, body=msg)
    if res["refund_amount"] > 0:
        await notify_finance(org, "Refund titipan biaya menunggu pembayaran", msg, "finance", COLL, sid)
    return await _get(org, sid)


async def _post(org: str, s: dict, contract: dict, approver: str, ts: str) -> dict:
    """Subledger + jurnal + invoice. Gagal sebelum jurnal → baris subledger ditarik kembali; setelah jurnal tak ada lagi yang bisa melempar."""
    led = await allin.ledger(org, contract)
    balance = max(0, int(led["titipan_balance"]))
    pct = float(s.get("forfeit_pct") or 0) if s["policy"] == FORFEIT_POLICY else 0.0
    forfeit = min(balance, int(round(balance * pct / 100)))
    refund = balance - forfeit
    unit = s.get("unit_code") or "-"
    movements = ([("refund_pembatalan", "REFUND_BATAL", refund, s.get("customer_name") or "Pembeli (refund pembatalan)")]
                 if refund else []) + ([("hangus_pembatalan", "HANGUS_BATAL", forfeit, "Developer (titipan hangus)")] if forfeit else [])
    disb_ids, je = [], None
    try:
        for kind, code, amt, payee in movements:
            row = {"id": new_id(), "org_id": org, "contract_id": contract.get("id"), "deal_id": s["deal_id"],
                   "component_code": code, "amount": amt, "payee": payee, "kind": kind, "settlement_id": s["id"],
                   "note": f"{s['number']} · pembatalan unit {unit}", "actor": approver, "created_at": ts}
            await db.cost_disbursements.insert_one(dict(row))
            disb_ids.append(row["id"])
        if balance > 0:
            lines = [{"account_code": AKUN_TITIPAN, "debit": balance, "credit": 0,
                      "memo": f"Titipan biaya dilepas (deal batal) {s['number']}"}]
            if refund:
                lines.append({"account_code": AKUN_UTANG_REFUND, "debit": 0, "credit": refund,
                              "memo": f"Utang refund titipan biaya kepada {s.get('customer_name') or 'pembeli'}"})
            if forfeit:
                lines.append({"account_code": AKUN_HANGUS, "debit": 0, "credit": forfeit,
                              "memo": f"Titipan biaya hangus {pct:g}% (kebijakan pembatalan)"})
            je = await gl.post_journal(org, f"Titipan biaya deal batal {unit} → utang refund {s['number']}", lines,
                                       source_type="cost_settlement", source_id=s["id"],
                                       source_event=f"costsettle:{s['id']}:approve", posted_by=approver, auto=True,
                                       source_deal_id=s["deal_id"])
    except BaseException:
        if disb_ids:
            await db.cost_disbursements.delete_many({"id": {"$in": disb_ids}})
        raise
    voided, partial, skipped = [], [], []
    why = f"Deal dibatalkan — {s['number']}"
    invs = await db.cost_invoices.find({"org_id": org, **allin._scope(contract),   # noqa: SLF001
                                        "status": {"$in": ["unpaid", "partial"]}}, {"_id": 0}).to_list(50)
    for inv in invs:
        paid, left = int(inv.get("paid") or 0), int(inv.get("outstanding") or 0)
        row = {"id": inv["id"], "number": inv.get("number"), "paid": paid, "outstanding": left}
        try:
            if paid == 0:
                await transition("cost_invoices", {"id": inv["id"], "org_id": org}, {"status": "unpaid", "paid": 0},
                                 {"$set": {"status": "void", "outstanding": 0, "void_reason": why, "voided_at": ts,
                                           "voided_by": approver, "settlement_id": s["id"], "updated_at": ts}},
                                 what="Invoice biaya")
                voided.append(row)
            else:   # sebagian terbayar: uang yang masuk tetap tercatat; hanya sisa tagihan yang gugur
                await transition("cost_invoices", {"id": inv["id"], "org_id": org}, {"status": "partial", "paid": paid},
                                 {"$set": {"status": "cancelled", "outstanding": 0, "cancelled_outstanding": left,
                                           "cancelled_at": ts, "cancelled_by": approver, "cancel_reason": why,
                                           "settlement_id": s["id"], "updated_at": ts}}, what="Invoice biaya")
                partial.append(row)
        except Conflict as e:
            skipped.append({**row, "reason": str(e)})
    return {"titipan_balance": balance, "refund_amount": refund, "forfeit_amount": forfeit, "forfeit_pct": pct,
            "journal_id": (je or {}).get("id"), "journal_no": (je or {}).get("entry_no"), "disbursement_ids": disb_ids,
            "invoices_voided": voided, "invoices_cancelled_partial": partial, "invoices_skipped": skipped}


async def _close_request_task(org: str, sid: str) -> None:
    """Tugas "setujui permohonan" selesai begitu permohonan diputus (disetujui/ditolak)."""
    await db.tasks.update_many({"org_id": org, "source_event": f"{FOLLOWUP_PREFIX}costsettle:{sid}",
                                "status": {"$in": ["open", "in_progress", "snoozed", "submitted"]}},
                               {"$set": {"status": "done", "updated_at": now_iso()}})


async def decide(org: str, sid: str, actor: str, approved: bool, note: str) -> dict:
    """Putusan Keuangan atas permohonan: setujui (jalankan) atau tolak (titipan/invoice ditangani manual)."""
    s = await _get(org, sid)
    note = (note or "").strip()
    if approved:
        return await execute(org, sid, actor, note, auto=False)
    if s["state"] != "diajukan":
        raise ValueError(f"Permohonan {s['number']} sudah {ref.label_of('cost_settlement_state', s['state']).lower()} — "
                         "tidak bisa diputus dua kali.")
    if len(note) < MIN_NOTE:
        raise ValueError(f"Alasan penolakan wajib diisi (minimal {MIN_NOTE} huruf) — titipan/invoice biaya lalu ditangani manual.")
    ts = now_iso()
    fresh = await transition(COLL, {"id": sid, "org_id": org}, {"state": "diajukan"},   # CAS: hanya satu putusan menang
                             {"$set": {"state": "ditolak", "updated_at": ts,
                                       "decision": {"approved": False, "by": actor, "at": ts, "note": note}}},
                             what="Permohonan refund titipan biaya")
    await _close_request_task(org, sid)
    from engine import auto_create_task
    from finance_engine import notify_finance
    body = (f"Permohonan {s['number']} ditolak ({actor}): {note}. Titipan biaya & invoice biaya deal unit "
            f"{s.get('unit_code') or '-'} ditangani manual oleh Keuangan.")
    await notify_finance(org, "Refund titipan biaya ditolak — tangani manual", body, "finance", COLL, sid)
    await auto_create_task(source_event=f"deal.cancel_followup:costsettle-ditolak:{sid}",
                           title=f"Tangani manual titipan biaya deal batal {s.get('unit_code') or '-'} ({s['number']})",
                           type="todo", related_entity_type="deal", related_entity_id=s["deal_id"], assigned_to=None,
                           description=body, priority="high", org_id=org)
    return fresh


# ------------------------------------------------------------------ pembayaran refund (uang keluar — jalur `money_op`)
async def pay_refund(org: str, sid: str, actor: str, *, method: str = "transfer", amount: int = None,
                     cash_account_id: str = None, client_ref: str = None, note: str = None) -> dict:
    s = await _get(org, sid)
    _assert_payable(s)
    sisa = int((s.get("settlement") or {}).get("refund_amount") or 0) - int(s.get("refund_paid_total") or 0)
    amt = int(amount or sisa)
    if amt <= 0:
        raise ValueError("Nominal refund harus lebih dari 0.")
    if amt > sisa:
        raise ValueError(f"Nominal melebihi sisa utang refund titipan biaya ({_rp(sisa)}). Refund tidak boleh dibayar dua kali.")
    import cash_bank as cb
    akun_kas = await cb.resolve_code(org, cash_account_id, cx.AKUN_KAS if method == "tunai" else cx.AKUN_BANK)
    async with money_op(org, op="costrefund.pay", key=(sid, amt, method, cash_account_id, actor), client_ref=client_ref,
                        amount=amt, cash_code=akun_kas, deal_id=s["deal_id"],
                        kind=f"refund titipan biaya {s['number']}", what="Pembayaran refund titipan biaya ini"):
        async with mutex(f"costsettle.refund:{sid}", what="Pembayaran refund titipan biaya ini"):
            s = await _get(org, sid)   # dibaca ULANG di bawah kunci
            _assert_payable(s)
            paid = int(s.get("refund_paid_total") or 0)
            total_due = int((s.get("settlement") or {}).get("refund_amount") or 0)
            if amt > total_due - paid:
                raise ValueError(f"Nominal melebihi sisa utang refund titipan biaya ({_rp(total_due - paid)}).")
            pid, ts = new_id(), now_iso()
            state = "selesai" if paid + amt >= total_due else "refund_sebagian"
            payment = {"id": pid, "amount": amt, "method": method, "account_code": akun_kas, "note": note,
                       "client_ref": client_ref, "journal_id": None, "actor": actor, "at": ts}
            async with reserved(COLL, {"id": sid, "org_id": org}, {"state": s["state"], "refund_paid_total": paid},
                                {"$set": {"refund_paid_total": paid + amt, "state": state, "updated_at": ts},
                                 "$push": {"refund_payments": payment}},
                                undo={"$set": {"refund_paid_total": paid, "state": s["state"]},
                                      "$pull": {"refund_payments": {"id": pid}}}, what="Permohonan refund titipan biaya"):
                je = await gl.post_journal(
                    org, f"Pembayaran refund titipan biaya {s['number']}",
                    [{"account_code": AKUN_UTANG_REFUND, "debit": amt, "credit": 0,
                      "memo": f"Utang refund titipan biaya kepada {s.get('customer_name') or 'pembeli'}"},
                     {"account_code": akun_kas, "debit": 0, "credit": amt, "memo": ref.label_of("refund_method", method)}],
                    source_type="cost_settlement_refund", source_id=pid, source_event=f"costsettle:{sid}:refund:{pid}",
                    posted_by=actor, auto=True, source_deal_id=s["deal_id"])
                await db[COLL].update_one({"id": sid, "refund_payments.id": pid},
                                          {"$set": {"refund_payments.$.journal_id": je["id"]}})
    payment["journal_id"] = je["id"]
    return {"settlement": await _get(org, sid), "payment": payment}


def _assert_payable(s: dict) -> None:
    if s["state"] not in ("disetujui", "refund_sebagian"):
        raise ValueError({"diajukan": "Permohonan belum disetujui Keuangan — setujui dulu sebelum membayar refund.",
                          "selesai": "Refund titipan biaya ini sudah dibayar penuh.",
                          "ditolak": "Permohonan ini ditolak — tidak ada refund yang bisa dibayar."}.get(s["state"], "Permohonan tidak dapat dibayar."))


# ------------------------------------------------------------------ pembacaan
def enrich(s: dict) -> dict:
    st = s.get("settlement") or {}
    due = int(st.get("refund_amount") or 0)
    out = max(0, due - int(s.get("refund_paid_total") or 0)) if s["state"] in ("disetujui", "refund_sebagian") else 0
    return {**s, "state_label": ref.label_of("cost_settlement_state", s.get("state") or ""),
            "refund_payable": due, "refund_outstanding": out, "can_pay_refund": out > 0,
            "policy_label": ref.label_of("cancel_cost_deposit_policy", s.get("policy") or "")}


async def listing(org: str, *, state: str = None, deal_id: str = None, limit: int = 100) -> dict:
    q = {"org_id": org}
    if state:
        q["state"] = state
    if deal_id:
        q["deal_id"] = deal_id
    rows = await db[COLL].find(q, {"_id": 0}).sort("created_at", -1).to_list(max(1, min(int(limit), 300)))
    counts = {st: await db[COLL].count_documents({"org_id": org, "state": st}) for st in ref.values("cost_settlement_state")}
    return {"data": [enrich(r) for r in rows], "counts": counts,
            "outstanding": sum(enrich(r)["refund_outstanding"] for r in rows)}


async def get(org: str, sid: str) -> dict:
    return enrich(await _get(org, sid))
