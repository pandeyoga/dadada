"""TAHAP LEGAL KONTRAK (PPJB, akad kredit, pelunasan, BAST, AJB, sertifikat) — atomik per kontrak.

Dipisah dari `contracts_engine.py` (batas ukuran berkas) dan diperbaiki untuk audit KT-24.

## Cacat yang ditutup

`legal_advance` bekerja "cek lalu tulis": dua permintaan PPJB serentak sama-sama membaca
`legal.ppjb` kosong, sama-sama lolos gerbang, sama-sama mengambil NOMOR (PPJB/2026/0002 dan 0003),
sama-sama `$push` riwayat legal, dan sama-sama membuat tugas "Jadwalkan AJB". Sekarang:

  * seluruh pemajuan tahap untuk SATU kontrak diserialkan oleh `mutex` — yang datang kedua
    menunggu, membaca ulang kontrak, lalu ditolak "sudah tercatat" (tanpa mengambil nomor);
  * penulisan tahap itu sendiri memakai syarat `legal.<tahap>` belum ada (CAS), sebagai pagar
    kedua bila kunci mutex sempat kedaluwarsa.
"""
import logging

import reference as ref
import sequences as seq
import stage_clock as clock
from core_utils import due_in, now_iso, today_wib
from db import db
from engine import add_activity, auto_create_task, dispatch_pending, emit
from idempotency import Conflict, mutex

logger = logging.getLogger("sipro.contracts")


def _ce():
    """Impor malas `contracts_engine` — memutus siklus impor."""
    import contracts_engine as ce
    return ce


async def legal_advance(org: str, contract_id: str, stage: str, payload: dict,
                        actor: str) -> dict:
    """Majukan satu tahap legal setelah gerbang buktinya lulus. Menulis jejak + cermin deal."""
    if stage not in _ce().LEGAL_ORDER:
        raise ValueError(f"Tahap legal '{stage}' tidak dikenal.")
    async with mutex(f"legal:{contract_id}", wait=20, ttl=90, what="Tahap legal kontrak ini"):
        return await _advance_locked(org, contract_id, stage, payload, actor)


async def _advance_locked(org: str, contract_id: str, stage: str, payload: dict,
                          actor: str) -> dict:
    ce = _ce()
    c = await ce.get_raw(org, contract_id)
    if (c.get("legal") or {}).get(stage):
        raise ValueError(f"Tahap {ref.label_of('contract_legal_stage', stage)} sudah "
                         "tercatat untuk kontrak ini.")
    gates = await ce.legal_gates(org, c)
    g = gates.get(stage) or {}
    override = None
    if not g.get("ok"):
        reason = " ".join(str(payload.get("override_reason") or "").split())
        if g.get("overridable") and reason:
            if len(reason) < 5:
                raise ValueError("Alasan pengecualian minimal 5 huruf.")
            file_ids = [str(f) for f in (payload.get("override_file_ids") or []) if f]
            if not file_ids:
                raise ValueError("Surat keterangan / dasar pengecualian wajib diunggah "
                                 "(lampirkan berkasnya).")
            if await db.files.count_documents({"org_id": org, "id": {"$in": file_ids},
                                               "is_deleted": False}) != len(file_ids):
                raise ValueError("Berkas surat keterangan tidak ditemukan — unggah ulang.")
            override = {"reason": reason, "by": actor, "at": now_iso(),
                        "file_ids": file_ids,
                        "blocks": [b["code"] for b in g.get("blocks", [])],
                        "detail": " ".join(b["detail"] for b in g.get("blocks", []))}
        else:
            sebab = " ".join(b["detail"] for b in g.get("blocks", []))
            if g.get("overridable"):
                sebab += (" Manajer dapat mencatat tahap ini dengan PENGECUALIAN "
                          "(alasan tertulis + surat keterangan wajib).")
            raise ValueError(f"Belum bisa dimajukan ke {g.get('label')}. {sebab}".strip())
    ts = now_iso()
    number = payload.get("number")
    if stage in ("ppjb", "ajb") and not number:
        number = await seq.next_number(f"legal:{stage}", org, prefix=stage.upper(), context={
            "stage": stage.upper(), "project_id": c.get("project_id"), "unit_id": c.get("unit_id"),
            "customer_id": c.get("customer_id")})
    entry = {"stage": stage, "label": ref.label_of("contract_legal_stage", stage),
             "number": number, "date": payload.get("date") or today_wib(),
             "notary": payload.get("notary"), "place": payload.get("place"),
             "file_id": payload.get("file_id"), "note": payload.get("note"),
             "override": override,
             "at": ts, "by": actor}
    # Pagar kedua (CAS): tahap hanya boleh ditulis SEKALI, walau kunci mutex sempat kedaluwarsa.
    res = await db.contracts.update_one(
        {"id": contract_id, f"legal.{stage}": {"$exists": False}}, {
            "$set": {f"legal.{stage}": entry, "legal_stage": stage, "updated_at": ts},
            "$push": {"legal_history": entry}})
    if res.matched_count != 1:
        raise Conflict(f"Tahap {entry['label']} baru saja dicatat oleh proses lain untuk kontrak ini. "
                       "Muat ulang untuk melihat hasilnya.")
    # ---- cermin ke `deals` supaya layar & gate lama tetap menyatakan hal yang sama ----
    deal_set = {"updated_at": ts, f"legal_dates.{stage}": entry["date"]}
    if stage == "akad_kredit":
        deal_set["akad_at"] = entry["date"]
        # Cermin ke pengajuan KPR: pencairan bank membaca `financing_apps.akad.date`.
        await db.financing_apps.update_many(
            {"org_id": org, "deal_id": c["deal_id"],
             "$or": [{"akad.date": {"$exists": False}}, {"akad.date": None}, {"akad.date": ""}]},
            {"$set": {"akad": {"date": entry["date"], "number": number, "notary": entry.get("notary"),
                               "file_id": entry.get("file_id"), "at": ts, "by": actor,
                               "note": "Dicatat dari tahap legal kontrak."},
                      "updated_at": ts}})
    await db.customers.update_one({"id": c.get("customer_id")}, {"$set": {
        "contract_legal_stage": stage, f"legal_dates.{stage}": entry["date"],
        "updated_at": ts}})
    if override:
        await add_activity(entity_type="customer", entity_id=c.get("customer_id"),
                           type="system", actor=actor, org_id=org,
                           body=(f"PENGECUALIAN {entry['label']} unit {c.get('unit_code')}: "
                                 f"{override['detail']} Alasan: {override['reason']}"))
    if stage == "ppjb":
        pay = await ce._pay_snapshot(org, c["deal_id"])  # noqa: SLF001
        deal_set.update({"legal_stage": "ppjb", "ppjb": {
            "number": number, "signed_date": entry["date"], "signed_by": c.get("customer_name"),
            # DP/persen terbayar SAAT PPJB: dibaca layar Deal & Unit (dulu hanya diisi jalur lama).
            "dp_paid": pay["paid"], "dp_pct": pay["paid_pct"],
            "note": entry["note"], "created_at": ts}})
        await emit("deal.ppjb", "deal", c["deal_id"],
                   {"unit_id": c.get("unit_id"), "number": number}, org_id=org)
        await auto_create_task(
            source_event=f"contract.ajb:{contract_id}",
            title=f"Jadwalkan AJB / akad: {c.get('customer_name')} · unit {c.get('unit_code')}",
            type="follow_up", related_entity_type="contract", related_entity_id=contract_id,
            assigned_to=c.get("assigned_to"), due_date=due_in(days=14), priority="medium",
            org_id=org)
    if stage == "ajb":
        pay = await ce._pay_snapshot(org, c["deal_id"])  # noqa: SLF001
        deal_set.update({"legal_stage": "ajb", "status": "completed", "sold_at": ts,
                         "ajb": {"number": number, "notary": entry["notary"],
                                 "signed_date": entry["date"],
                                 "buyer": c.get("customer_name"),
                                 "outstanding_at_ajb": pay["outstanding"], "note": entry["note"],
                                 "created_at": ts},
                         **await clock.patch_for("deal", "completed", org_id=org, at=ts)})
        await db.units.update_one({"id": c.get("unit_id"), "org_id": org}, {"$set": {
            "status": "sold", "sold_at": ts, "sold_by_deal": c["deal_id"],
            "updated_at": ts}})
        await db.contracts.update_one({"id": contract_id},
                                      {"$set": {"state": "completed"}})
        await emit("deal.ajb", "deal", c["deal_id"],
                   {"unit_id": c.get("unit_id"), "number": number}, org_id=org)
        await emit("deal.sold", "deal", c["deal_id"], {"unit_id": c.get("unit_id")},
                   org_id=org)
    await db.deals.update_one({"id": c["deal_id"]}, {"$set": deal_set})
    if stage == "ajb":
        # Setelah deal benar-benar `completed` (penangan `deal.sold` membaca deal itu), baru diproses.
        await dispatch_pending()
        try:
            import build_engine as be
            await be.sync_unit_binding(org, c.get("unit_id"))
        except Exception:  # noqa: BLE001 — ikatan denormalisasi tidak boleh menggagalkan AJB
            logger.exception("sync_unit_binding gagal setelah AJB kontrak %s", contract_id)
    await add_activity(entity_type="customer", entity_id=c.get("customer_id"), type="system",
                       actor=actor, org_id=org,
                       body=(f"{entry['label']}" + (f" {number}" if number else "")
                             + f" tercatat untuk unit {c.get('unit_code')}."))
    return await ce.get_raw(org, contract_id)
