"""Penutupan TURUNAN deal saat penjualan dibatalkan — SATU fungsi untuk kedua jalur batal (audit PK3-08).

Jalur batal ada dua: `deal_cancel.cancel` (reservasi/booking satu klik) dan `cancellation_engine.decide`
(pembatalan kontrak formal). Dulu hanya jalur pertama yang menutup tugas & melepas kupon; jalur formal
meninggalkan tugas aktif (PPJB, KYC, komponen biaya), komisi `pending`, fee marketing `submitted`, pengajuan
KPR `draft`, kuota kupon terpakai, dan catatan pajak `pending` yang masih bisa disetor.

Aturan (idempoten — aman dipanggil dua kali):
  * tugas aktif milik deal/kontrak (dan tugas KYC pembeli / tugas lead bila tidak ada deal hidup lain) → `cancelled`;
  * komisi & fee marketing yang BELUM disetujui → `cancelled`;
  * yang sudah DISETUJUI-belum-dibayar atau sudah DIBAYAR TIDAK disentuh dan TIDAK dijurnal balik (belum ada
    helper pembalikan akrual yang aman, dan perlakuannya keputusan Keuangan/pemilik) → hanya diberi tanda
    `cancel_followup` + notifikasi + satu tugas ke Keuangan  [⚖ butuh keputusan];
  * pengajuan KPR yang masih berjalan → `status=cancelled`, tahap `batal`;
  * kupon dilepas, kuota dikembalikan;
  * catatan pajak `pending` → `cancelled` (laporan pajak mengecualikannya); yang sudah dilaporkan/disetor
    hanya ditandai butuh tindak lanjut;
  * janji temu MENDATANG milik lead deal ini (`scheduled`) → `cancelled` bila lead tak punya deal hidup lain —
    yang `done`/`no_show`/sudah lewat TIDAK disentuh (sejarah), tugas survei yang menempel ikut ditutup;
  * dokumen `draft` terikat deal/kontrak ini → `cancelled` dengan penanda (`cancelled_at/by`, `cancel_reason`,
    `status_before_cancel`); dokumen final/ditandatangani dan BAP pembatalan TIDAK disentuh (tidak ada yang dihapus).

DIPAKAI TIGA JALUR: batal satu-klik (`deal_cancel.cancel`), batal formal (`cancellation_engine.decide`), dan
kedaluwarsa reservasi (`deal_cancel.expire` ← sweeper) — sisa PK3-08.
"""
import logging
from datetime import datetime, timedelta, timezone

from core_utils import WIB, now, now_iso
from db import db

logger = logging.getLogger("sipro.deal_cancel_cleanup")

OPEN_TASK = {"$nin": ["done", "cancelled"]}
FOLLOWUP_SRC = "deal.cancel_followup:"   # tugas tindak lanjut Keuangan — TIDAK ikut ditutup oleh penutupan ini


def _rp(v) -> str:
    return f"Rp {int(v or 0):,}".replace(",", ".")


async def _close_tasks(org: str, deal: dict, contract_ids: list, lead_closing: bool, ts: str,
                       outcome: str) -> int:
    did = deal["id"]
    ors = [{"related_entity_type": "deal", "related_entity_id": did}]
    if contract_ids:
        ors.append({"related_entity_type": "contract", "related_entity_id": {"$in": contract_ids}})
    cust = deal.get("customer_id") or (await db.contracts.find_one(
        {"org_id": org, "deal_id": did}, {"_id": 0, "customer_id": 1}) or {}).get("customer_id")
    if cust:
        # KYC pembeli hanya ditutup bila pembeli ini tidak punya penjualan hidup lain.
        other = await db.contracts.count_documents({"org_id": org, "customer_id": cust, "deal_id": {"$ne": did},
                                                    "state": {"$nin": ["cancelled", "draft"]}})
        if not other:
            ors.append({"related_entity_type": "customer", "related_entity_id": cust,
                        "source_event": {"$regex": "^customer\\.kyc:"}})
    lead_id = deal.get("lead_id")
    if lead_closing and lead_id and not await db.deals.count_documents({
            "org_id": org, "lead_id": lead_id, "id": {"$ne": did}, "status": {"$in": ["reserved", "booked", "completed"]}}):
        ors.append({"related_entity_type": "lead", "related_entity_id": lead_id})
    res = await db.tasks.update_many(
        {"org_id": org, "status": OPEN_TASK, "$or": ors,
         "source_event": {"$not": {"$regex": "^" + FOLLOWUP_SRC.replace(".", "\\.")}}},
        {"$set": {"status": "cancelled", "outcome": outcome, "updated_at": ts}})
    return res.modified_count


LIVE_DEAL = ["draft", "reserved", "booked", "completed"]


def _is_upcoming(value) -> bool:
    """Janji temu masih di depan? Waktu tanpa zona dibaca WIB; tanggal polos = sampai akhir hari itu (WIB).
    Tak terbaca → BUKAN mendatang (tidak disentuh)."""
    s = str(value or "").strip()
    if not s:
        return False
    try:
        if len(s) <= 10:
            dt = datetime.fromisoformat(s).replace(tzinfo=WIB) + timedelta(days=1)
        else:
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=WIB)
    except ValueError:
        return False
    return dt.astimezone(timezone.utc) >= now()


async def _cancel_appointments(org: str, deal: dict, ts: str, actor: str, why: str) -> int:
    """Janji temu MENDATANG milik lead deal yang batal → `cancelled` (tanpa menyentuh `done`/`no_show`/yang lewat).
    Bila lead masih punya deal hidup lain, janji temunya bisa jadi untuk deal itu → dibiarkan."""
    lead_id = deal.get("lead_id")
    if not lead_id or await db.deals.count_documents({"org_id": org, "lead_id": lead_id, "id": {"$ne": deal["id"]},
                                                      "status": {"$in": LIVE_DEAL}}):
        return 0
    rows = await db.appointments.find({"org_id": org, "lead_id": lead_id, "status": "scheduled"},
                                      {"_id": 0, "id": 1, "scheduled_at": 1}).to_list(500)
    ids = [r["id"] for r in rows if _is_upcoming(r.get("scheduled_at"))]
    if not ids:
        return 0
    res = await db.appointments.update_many(
        {"org_id": org, "id": {"$in": ids}, "status": "scheduled"},
        {"$set": {"status": "cancelled", "cancelled_at": ts, "cancelled_by": actor, "cancel_reason": why,
                  "cancelled_by_deal": deal["id"], "updated_at": ts}})
    # tugas survei yang lahir dari janji temu itu (source_event `appointment:<id>`) ikut ditutup
    await db.tasks.update_many(
        {"org_id": org, "source_event": {"$in": [f"appointment:{i}" for i in ids]}, "status": OPEN_TASK},
        {"$set": {"status": "cancelled", "outcome": why, "updated_at": ts}})
    return res.modified_count


async def _cancel_draft_documents(org: str, deal: dict, contract_ids: list, ts: str, actor: str, why: str) -> int:
    """Dokumen `draft` (SPR/PPJB/adendum…) terikat deal/kontrak batal → `cancelled` + penanda. Final/ditandatangani dan
    BAP pembatalan (`cancellation_id`) tidak disentuh; tidak ada dokumen yang dihapus."""
    ors = [{"deal_id": deal["id"]}] + ([{"contract_id": {"$in": contract_ids}}] if contract_ids else [])
    try:
        import stage_clock as clock
        clk = await clock.patch_for("document", "cancelled", org_id=org, at=ts, pol={"cancelled": 0})   # tahap akhir: tanpa SLA
    except Exception as e:  # noqa: BLE001  — jam tahap hanya pelengkap; pembatalan dokumen tetap jalan
        logger.warning("Jam tahap dokumen batal tidak diisi: %s", e)
        clk = {}
    res = await db.documents.update_many(
        {"org_id": org, "status": "draft", "cancellation_id": None, "$or": ors},
        {"$set": {"status": "cancelled", "status_before_cancel": "draft", "cancelled_at": ts, "cancelled_by": actor,
                  "cancel_reason": why, "updated_at": ts, **clk}})
    return res.modified_count


async def _flag(coll: str, q: dict, ts: str, reason: str) -> list:
    """Tandai dokumen yang TIDAK boleh disentuh otomatis (sudah disetujui/dibayar) sebagai butuh tindak lanjut."""
    rows = await db[coll].find({**q, "cancel_followup": {"$exists": False}},
                               {"_id": 0, "id": 1, "status": 1, "amount": 1, "amount_net": 1, "no": 1}).to_list(200)
    for r in rows:
        await db[coll].update_one({"id": r["id"], "cancel_followup": {"$exists": False}}, {"$set": {
            "cancel_followup": {"at": ts, "reason": reason, "status_at_cancel": r.get("status")}}})
    return rows


async def close_deal_dependents(org: str, deal: dict, *, actor: str, reason: str, source: str,
                                lead_closing: bool = False, cost_holds: dict = None) -> dict:
    """Tutup turunan `deal` yang batal. `lead_closing=True` bila lead ikut ditandai `lost` (jalur formal).
    `cost_holds` (opsional, dari `cancellation_costs.holds*`) dimasukkan ke tindak lanjut Keuangan — dipakai jalur
    kedaluwarsa, tempat tak ada orang yang bisa mengakui titipan/invoice biaya yang menggantung."""
    did = deal["id"]
    ts = now_iso()
    why = f"Penjualan dibatalkan ({source}): {reason}"[:300]
    out = {}
    contract_ids = [c["id"] async for c in db.contracts.find({"org_id": org, "deal_id": did}, {"_id": 0, "id": 1})]
    out["tasks_closed"] = await _close_tasks(org, deal, contract_ids, lead_closing, ts, why)
    out["appointments_cancelled"] = await _cancel_appointments(org, deal, ts, actor, why)
    out["documents_cancelled"] = await _cancel_draft_documents(org, deal, contract_ids, ts, actor, why)
    cancel_set = {"status": "cancelled", "cancelled_at": ts, "cancelled_by": actor, "cancel_reason": why,
                  "updated_at": ts}

    # --- komisi sales: belum disetujui → batal; disetujui/dibayar → tanda tindak lanjut (tanpa jurnal balik).
    out["commissions_cancelled"] = (await db.commissions.update_many(
        {"org_id": org, "deal_id": did, "status": "pending"}, {"$set": cancel_set})).modified_count
    com_fu = await _flag("commissions", {"org_id": org, "deal_id": did, "status": {"$in": ["approved", "paid"]}},
                         ts, why)
    out["commissions_followup"] = len(com_fu)

    # --- marketing fee mitra: sama.
    out["fees_cancelled"] = (await db.marketing_fees.update_many(
        {"org_id": org, "deal_id": did, "status": {"$in": ["draft", "submitted"]}}, {"$set": cancel_set})).modified_count
    fee_fu = await _flag("marketing_fees", {"org_id": org, "deal_id": did, "status": {"$in": ["approved", "paid"]}},
                         ts, why)
    out["fees_followup"] = len(fee_fu)

    # --- pengajuan KPR yang masih berjalan.
    n_kpr = 0
    async for app in db.financing_apps.find({"org_id": org, "deal_id": did, "status": {"$nin": ["rejected", "cancelled"]},
                                             "kpr_stage": {"$nin": ["ditolak", "batal"]}}, {"_id": 0}):
        live_disb = [d for d in app.get("disbursements") or [] if d.get("status") != "dibatalkan"]
        res = await db.financing_apps.update_one(
            {"id": app["id"], "status": app.get("status")},
            {"$set": {"status": "cancelled", "kpr_stage": "batal", "cancelled_at": ts, "cancel_reason": why,
                      "updated_at": ts,
                      **({"cancel_followup": {"at": ts, "reason": why,
                                              "note": "Pencairan bank sudah tercatat — dana bank ikut diperhitungkan "
                                                      "dalam pembatalan; tindak lanjut Keuangan."}} if live_disb else {})},
             "$push": {"stage_history": {"from": app.get("kpr_stage"), "to": "batal", "at": ts, "actor": actor,
                                         "reason": why, "evidence": []}}})
        n_kpr += res.modified_count
    out["financing_cancelled"] = n_kpr

    # --- kupon dilepas.
    import pricing_engine as pe
    out["coupons_released"] = await pe.release_coupon(org, ref_type="deal", ref_id=did, actor=actor)

    # --- catatan pajak: pending → batal; yang sudah dilapor/disetor → tanda.
    out["tax_cancelled"] = (await db.tax_records.update_many(
        {"org_id": org, "deal_id": did, "status": "pending"}, {"$set": cancel_set})).modified_count
    tax_fu = await _flag("tax_records", {"org_id": org, "deal_id": did, "status": {"$in": ["reported", "paid"]}}, ts, why)
    out["tax_followup"] = len(tax_fu)

    # --- tindak lanjut Keuangan (⚖): hanya untuk hal yang TIDAK diubah otomatis.
    items = []
    if com_fu:
        items.append(f"komisi disetujui/dibayar {len(com_fu)} ({_rp(sum(int(r.get('amount') or 0) for r in com_fu))})")
    if fee_fu:
        items.append(f"fee marketing disetujui/dibayar {len(fee_fu)} ({_rp(sum(int(r.get('amount_net') or 0) for r in fee_fu))})")
    if tax_fu:
        items.append(f"catatan pajak sudah dilapor/disetor {len(tax_fu)} ({_rp(sum(int(r.get('amount') or 0) for r in tax_fu))})")
    if (cost_holds or {}).get("has_holds"):
        items.append(f"uang biaya menggantung: saldo titipan biaya {_rp(cost_holds['titipan_balance'])} (2-1470) dan invoice "
                     f"biaya terbuka {_rp(cost_holds['open_invoice_total'])}")
    if items:
        from engine import auto_create_task
        from finance_engine import notify_finance
        body = ("Penjualan unit " + str(deal.get("unit_code") or "-") + " dibatalkan; perlu keputusan Keuangan "
                "(pembalikan akrual / pemulihan dana) atas: " + "; ".join(items) + ". Sistem TIDAK menjurnal balik otomatis.")
        await notify_finance(org, "Pembatalan: ada akrual/pembayaran yang perlu ditindaklanjuti", body,
                             "finance", "deal", did)
        await auto_create_task(source_event=f"{FOLLOWUP_SRC}{did}",
                               title=f"Tindak lanjut pembatalan unit {deal.get('unit_code') or '-'}: komisi/fee/pajak",
                               type="todo", related_entity_type="deal", related_entity_id=did, assigned_to=None,
                               description=body, priority="high", org_id=org)
        out["finance_followup"] = items
    return out
