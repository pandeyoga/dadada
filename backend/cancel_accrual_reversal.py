"""Pembalikan AKRUAL komisi / fee marketing / pajak yang sudah disetujui pada DEAL BATAL (keputusan #11, docs/audit/12).

Sebelumnya (`deal_cancel_cleanup`) akrual yang sudah disetujui/dibayar hanya DITANDAI + tugas & notifikasi Keuangan; jurnal tidak
dibalik. Kini perlakuannya mengikuti tiga kunci kebijakan (level organisasi + proyek, bawaan `manual_keuangan` = perilaku lama):

  cancel.accrual_reversal.commission | .marketing_fee | .tax
    manual_keuangan                      ditandai + tugas Keuangan, TANPA jurnal balik            (bawaan, tidak berubah)
    balik_otomatis_yang_belum_dibayar    yang DISETUJUI tetapi belum dibayar sama sekali dibalik otomatis
    balik_otomatis_semua                 BELUM TERSEDIA (butuh akun piutang ke penerima — tidak ada di Bagan Akun)

Yang dikerjakan untuk komisi & fee marketing pada mode otomatis (idempoten, aman dipanggil dua kali):
  1. status dokumen diklaim atomik `approved → cancelled` (`idempotency.reserved`; yang kalah balapan dengan pembayaran dibiarkan
     — ia tetap `approved/paid` dan jatuh ke tanda tindak lanjut manual, tidak pernah ada uang hilang/ganda);
  2. jurnal koreksi = CERMIN jurnal akrual aslinya (komisi: Dr 2-1600 / Cr 6-1100; fee: Dr 2-1500 [+ Dr 2-1300 PPh] / Cr 6-1200),
     `source_event` unik per dokumen, sehingga subledger (komisi `approved`, fee `approved`) DAN buku besar (2-1600, 2-1500) turun
     bersama dan rekonsiliasi tetap hijau;
  3. bila jurnal akrual asli belum terbit (event pembukuan antre/gagal) atau jurnal koreksi gagal, status dikembalikan dan dokumen
     dibiarkan untuk tindak lanjut manual Keuangan — pembatalan tidak pernah macet karenanya.
Fee yang sudah dibayar (sebagian/penuh) dan komisi yang sudah dibayar TIDAK disentuh: itu "tagihan balik ke penerima" milik Keuangan.

PAJAK: catatan pajak baru dijurnal setelah DILAPORKAN/DISETOR; yang berstatus `pending` tidak berjurnal dan sudah dibatalkan
penutup. Yang sudah dilaporkan/disetor ke negara TIDAK PERNAH dibalik otomatis (pembetulan SPT / restitusi) apa pun pengaturannya.

`apply()` membaca kebijakan SAAT pembatalan dan mengembalikan `policy_snapshot` (nilai + asal tiap kunci) untuk disimpan pada hasil
penutupan/dokumen pembatalan — mengganti pengaturan berlaku ke depan saja.
"""
import logging

import gl_engine as gl
import policy
from core_utils import now_iso
from db import db
from idempotency import Conflict, reserved

logger = logging.getLogger("sipro.cancel_accrual")

KEYS = {"commission": "cancel.accrual_reversal.commission",
        "marketing_fee": "cancel.accrual_reversal.marketing_fee",
        "tax": "cancel.accrual_reversal.tax"}
MANUAL = "manual_keuangan"
UNPAID = "balik_otomatis_yang_belum_dibayar"
ALL_ = "balik_otomatis_semua"
AUTO_MODES = (UNPAID, ALL_)   # ALL_ belum tersedia; bila nilai usang terbaca, perilakunya SAMA dengan UNPAID (yang dibayar tetap manual)


async def read_policy(org: str, project_id: str = None) -> dict:
    snap = await policy.snapshot(list(KEYS.values()), org_id=org, project_id=project_id)
    return {"snapshot": snap, "modes": {k: snap[key]["value"] for k, key in KEYS.items()}}


async def _mirror(org: str, orig: dict, *, memo: str, source_type: str, source_id: str, source_event: str,
                  actor: str, deal_id: str) -> dict:
    """Jurnal koreksi = cermin jurnal akrual asli (debit ↔ kredit pada akun yang sama)."""
    lines = [{"account_code": ln["account_code"], "debit": int(ln.get("credit") or 0),
              "credit": int(ln.get("debit") or 0), "memo": f"Balik akrual {orig.get('entry_no')}"}
             for ln in orig["lines"]]
    return await gl.post_journal(org, memo, lines, source_type=source_type, source_id=source_id,
                                 source_event=source_event, posted_by=actor, auto=True, source_deal_id=deal_id)


def _outcome(kind: str, mode: str) -> dict:
    return {"kind": kind, "mode": mode, "auto": mode in AUTO_MODES, "reversed": [], "skipped": [], "amount_reversed": 0}


# ------------------------------------------------------------------ komisi sales
async def _commission_accrual(org: str, com: dict):
    return await db.journal_entries.find_one(
        {"org_id": org, "source_type": "commission", "source_id": com["id"],
         "lines": {"$elemMatch": {"account_code": "2-1600", "credit": {"$gt": 0}}}},
        {"_id": 0}, sort=[("created_at", 1)])


async def _reverse_commission(org: str, deal: dict, com: dict, mode: str, actor: str, why: str) -> dict:
    cid = com["id"]
    orig = await _commission_accrual(org, com)
    if not orig:
        return {"id": cid, "ok": False, "reason": "jurnal akrual belum terbit (event pembukuan antre/gagal)"}
    ts = now_iso()
    try:
        async with reserved(
                "commissions", {"id": cid, "org_id": org}, {"status": "approved"},
                {"$set": {"status": "cancelled", "cancelled_at": ts, "cancelled_by": actor, "cancel_reason": why,
                          "updated_at": ts, "accrual_reversal": {"at": ts, "by": actor, "mode": mode,
                                                                  "orig_journal_id": orig["id"]}}},
                undo={"$set": {"status": "approved"},
                      "$unset": {"cancelled_at": "", "cancelled_by": "", "cancel_reason": "", "accrual_reversal": ""}},
                what="Komisi"):
            je = await _mirror(org, orig, memo=f"Balik akrual komisi (deal batal) — {com.get('assigned_to') or ''}",
                               source_type="commission_reversal", source_id=cid,
                               source_event=f"cancel.reverse:commission:{cid}", actor=actor, deal_id=deal["id"])
            await db.commissions.update_one({"id": cid}, {"$set": {
                "accrual_reversal.journal_id": je["id"], "accrual_reversal.journal_no": je.get("entry_no")}})
    except Conflict:
        return {"id": cid, "ok": False, "reason": "status komisi baru berubah (mis. baru dibayar) — ditangani manual"}
    except Exception as e:  # noqa: BLE001  — pembatalan tidak boleh macet; komisi tetap `approved` → tanda manual
        logger.exception("Pembalikan akrual komisi %s gagal", cid)
        return {"id": cid, "ok": False, "reason": f"jurnal koreksi gagal: {str(e)[:160]}"}
    return {"id": cid, "ok": True, "amount": int(com.get("amount") or 0), "journal_id": je["id"],
            "journal_no": je.get("entry_no")}


async def reverse_commissions(org: str, deal: dict, mode: str, actor: str, why: str) -> dict:
    out = _outcome("commission", mode)
    if mode not in AUTO_MODES:
        return out
    rows = await db.commissions.find({"org_id": org, "deal_id": deal["id"], "status": "approved"}, {"_id": 0}).to_list(200)
    if rows:
        from engine import dispatch_pending
        await dispatch_pending()   # jurnal akrual lahir dari event; kosongkan antrean dulu (pola ap_void)
    for com in rows:
        r = await _reverse_commission(org, deal, com, mode, actor, why)
        (out["reversed"] if r["ok"] else out["skipped"]).append(r)
        out["amount_reversed"] += r.get("amount", 0) if r["ok"] else 0
    return out


# ------------------------------------------------------------------ fee marketing mitra
async def _reverse_fee(org: str, deal: dict, fee: dict, mode: str, actor: str, why: str) -> dict:
    fid = fee["id"]
    if int(fee.get("paid_amount") or 0) > 0:
        return {"id": fid, "ok": False, "reason": "sudah dibayar (sebagian/penuh) — tagih balik ke agen oleh Keuangan"}
    orig = await db.journal_entries.find_one({"org_id": org, "source_event": f"mfee.approve:{fid}"}, {"_id": 0})
    if not orig:
        return {"id": fid, "ok": False, "reason": "jurnal akrual fee tidak ditemukan"}
    ts = now_iso()
    try:
        async with reserved(
                "marketing_fees", {"id": fid, "org_id": org}, {"status": "approved", "paid_amount": 0},
                {"$set": {"status": "cancelled", "cancelled_at": ts, "cancelled_by": actor, "cancel_reason": why,
                          "updated_at": ts, "accrual_reversal": {"at": ts, "by": actor, "mode": mode,
                                                                  "orig_journal_id": orig["id"]}}},
                undo={"$set": {"status": "approved"},
                      "$unset": {"cancelled_at": "", "cancelled_by": "", "cancel_reason": "", "accrual_reversal": ""}},
                what="Pengajuan fee"):
            je = await _mirror(org, orig, memo=f"Balik akrual marketing fee {fee.get('no')} (deal batal) — {fee.get('agent_name')}",
                               source_type="marketing_fee_reversal", source_id=fid,
                               source_event=f"cancel.reverse:mfee:{fid}", actor=actor, deal_id=deal["id"])
            await db.marketing_fees.update_one({"id": fid}, {"$set": {
                "accrual_reversal.journal_id": je["id"], "accrual_reversal.journal_no": je.get("entry_no")},
                "$push": {"journal_ids": je["id"]}})
    except Conflict:
        return {"id": fid, "ok": False, "reason": "status fee baru berubah (mis. baru dibayar) — ditangani manual"}
    except Exception as e:  # noqa: BLE001
        logger.exception("Pembalikan akrual fee %s gagal", fid)
        return {"id": fid, "ok": False, "reason": f"jurnal koreksi gagal: {str(e)[:160]}"}
    if fee.get("agent_id"):
        import marketing_fee as mf
        await mf._refresh_agent_totals(fee["agent_id"], org)   # noqa: SLF001  — total agen mengikuti fee `approved/paid`
    return {"id": fid, "ok": True, "amount": int(fee.get("amount_net") or 0), "journal_id": je["id"],
            "journal_no": je.get("entry_no")}


async def reverse_fees(org: str, deal: dict, mode: str, actor: str, why: str) -> dict:
    out = _outcome("marketing_fee", mode)
    if mode not in AUTO_MODES:
        return out
    rows = await db.marketing_fees.find({"org_id": org, "deal_id": deal["id"], "status": "approved"}, {"_id": 0}).to_list(200)
    for fee in rows:
        r = await _reverse_fee(org, deal, fee, mode, actor, why)
        (out["reversed"] if r["ok"] else out["skipped"]).append(r)
        out["amount_reversed"] += r.get("amount", 0) if r["ok"] else 0
    return out


# ------------------------------------------------------------------ pintu masuk penutup deal batal
async def apply(org: str, deal: dict, *, actor: str, why: str) -> dict:
    """Baca kebijakan SAAT pembatalan lalu balik akrual yang diizinkannya. Tidak pernah melempar (kegagalan satu dokumen = tanda manual)."""
    pol = await read_policy(org, deal.get("project_id"))
    modes = pol["modes"]
    res = {"policy_snapshot": pol["snapshot"], "modes": modes,
           # pajak: apa pun nilainya TIDAK dibalik otomatis (yang sudah dilaporkan/disetor ke negara = pembetulan SPT).
           "tax": {"kind": "tax", "mode": modes["tax"], "auto": False, "reversed": [], "skipped": [], "amount_reversed": 0}}
    for kind, fn in (("commission", reverse_commissions), ("marketing_fee", reverse_fees)):
        try:
            res[kind] = await fn(org, deal, modes[kind], actor, why)
        except Exception as e:  # noqa: BLE001
            logger.exception("Pembalikan akrual %s deal %s gagal", kind, deal.get("id"))
            res[kind] = {**_outcome(kind, modes[kind]), "error": str(e)[:200]}
    return res
