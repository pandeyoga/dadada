"""JEJAK BARANG (Item Passport) — timeline satu roll lintas SEMUA dokumen.

Menyatukan jejak yang sudah tersebar: acquired (PO/GR/retur), tag RFID, print job,
sesi verifikasi, Putaway Order + BTG, mutasi stok, pembacaan gate, loading check.
Read-only — tidak menambah sumber data baru (anti duplikasi SSOT).
"""
from typing import Any, Dict, List

from fastapi import HTTPException

from db import db
from core_utils import safe_doc

STAGE_LABEL = {
    "received_transit": "Diterima di Transit", "tag_printed": "Tag RFID Dicetak",
    "tag_verified": "Tag Terverifikasi", "cross_dock_ready": "Cross-Dock — Langsung Kirim",
    "putaway_assigned": "Masuk Putaway Order", "putaway_in_transit": "Menuju Gudang Simpan",
    "stored": "Tersimpan di Gudang", "gate_exception": "Exception di Gate",
}
MOV_LABEL = {
    "putaway": "Penempatan ke bin", "putaway_transfer_out": "Keluar gudang (putaway)",
    "putaway_transfer_in": "Masuk gudang (putaway)",
}


async def roll_timeline(roll_id: str, scope_ids: List[str]) -> Dict[str, Any]:
    roll = await db.inventory_rolls.find_one({"id": roll_id}, {"_id": 0})
    if not roll:
        raise HTTPException(status_code=404, detail="Roll tidak ditemukan")
    if roll.get("owner_entity_id") not in scope_ids:
        raise HTTPException(status_code=403, detail="Roll di luar entitas Anda")
    ev: List[Dict[str, Any]] = []

    acq = roll.get("acquired") or {}
    if acq:
        via = acq.get("via", "")
        label = {"inbound": f"Diterima dari pembelian (PO {roll.get('po_number') or acq.get('ref_id', '')})",
                 "return": "Masuk kembali dari RETUR penjualan",
                 "initial": "Stok awal"}.get(via, f"Perolehan via {via}")
        ev.append({"at": acq.get("date"), "kind": "acquired", "label": label,
                   "ref": roll.get("po_number") or acq.get("ref_id", "")})

    tag = None
    if roll.get("rfid_tag_id"):
        tag = await db.rfid_tags.find_one({"id": roll["rfid_tag_id"]}, {"_id": 0})
    if tag:
        ev.append({"at": tag.get("encoded_at"), "kind": "tag",
                   "label": f"Tag RFID di-encode — EPC {tag.get('epc')}", "ref": tag.get("epc")})

    async for pj in db.rfid_print_jobs.find({"items.roll_id": roll_id},
                                            {"_id": 0, "job_number": 1, "created_at": 1,
                                             "printed_at": 1, "verified_at": 1, "status": 1}):
        ev.append({"at": pj.get("created_at"), "kind": "print",
                   "label": f"Masuk print job {pj['job_number']}", "ref": pj["job_number"]})
        if pj.get("printed_at"):
            ev.append({"at": pj["printed_at"], "kind": "print",
                       "label": f"Tag dicetak ({pj['job_number']})", "ref": pj["job_number"]})
        if pj.get("verified_at"):
            ev.append({"at": pj["verified_at"], "kind": "verify",
                       "label": f"Verifikasi handheld selesai ({pj['job_number']} — {pj.get('status')})",
                       "ref": pj["job_number"]})

    async for pa in db.putaway_orders.find({"items.roll_id": roll_id},
                                           {"_id": 0, "pa_number": 1, "btg_number": 1,
                                            "to_warehouse_name": 1, "created_at": 1,
                                            "dispatched_at": 1, "confirmed_at": 1, "items": 1}):
        ev.append({"at": pa.get("created_at"), "kind": "putaway",
                   "label": f"Masuk {pa['pa_number']} → {pa.get('to_warehouse_name', '')}",
                   "ref": pa["pa_number"]})
        if pa.get("dispatched_at"):
            ev.append({"at": pa["dispatched_at"], "kind": "putaway",
                       "label": f"Berangkat menuju {pa.get('to_warehouse_name', '')} ({pa['pa_number']})",
                       "ref": pa["pa_number"]})
        if pa.get("confirmed_at"):
            item = next((i for i in pa.get("items", []) if i.get("roll_id") == roll_id), {})
            st = item.get("status", "")
            lbl = (f"Tiba & tervalidasi di {pa.get('to_warehouse_name', '')}"
                   + (f" — BTG {pa['btg_number']}" if pa.get("btg_number") else "")) \
                if st == "arrived" else f"EXCEPTION saat tiba ({pa['pa_number']}) — status item: {st}"
            ev.append({"at": pa["confirmed_at"], "kind": "putaway", "label": lbl,
                       "ref": pa.get("btg_number") or pa["pa_number"]})

    async for m in db.inventory_movements.find({"roll_id": roll_id}, {"_id": 0}).sort("timestamp", 1):
        mt = m.get("movement_type") or m.get("type") or ""
        if mt in ("putaway_transfer_out",):  # pasangannya (in) sudah cukup mewakili
            continue
        label = MOV_LABEL.get(mt) or f"Mutasi: {mt}"
        src = m.get("source_document") or ""
        ev.append({"at": m.get("timestamp"), "kind": "movement",
                   "label": f"{label}{f' ({src})' if src else ''}", "ref": src})

    if tag:
        async for r in db.rfid_reads.find({"tag_id": tag["id"]}, {"_id": 0}).sort("timestamp", -1).limit(15):
            ev.append({"at": r.get("timestamp"), "kind": "gate",
                       "label": f"{'🟢' if r.get('result') == 'green' else '🔴' if r.get('result') == 'red' else '·'} "
                                f"{r.get('device_name', 'Reader')}: {r.get('reason', '')}",
                       "ref": r.get("device_name", ""), "result": r.get("result")})
    # Sesi 13 — jejak pindai HP gudang (QR label / EPC via /rfid/lookup)
    async for s in db.roll_scans.find({"roll_id": roll_id}, {"_id": 0}).sort("at", -1).limit(15):
        ev.append({"at": s.get("at"), "kind": "scan",
                   "label": f"Dipindai {'QR label' if s.get('via') == 'label' else 'tag RFID'} oleh {s.get('by') or 'HP gudang'}"
                            f"{' · ' + s['warehouse_id'] if s.get('warehouse_id') else ''}{' · bin ' + s['bin_id'] if s.get('bin_id') else ''}",
                   "ref": s.get("warehouse_id", "")})

    ref = roll.get("reserved_ref") or {}
    if isinstance(ref, dict) and ref.get("type") == "sales_order" and ref.get("id"):
        so = await db.sales_orders.find_one({"id": ref["id"]},
                                            {"_id": 0, "number": 1, "loading_check": 1})
        if so:
            ev.append({"at": roll.get("updated_at"), "kind": "so",
                       "label": f"Ter-alokasi untuk SO {so.get('number', '')} (status roll: {roll.get('status')})",
                       "ref": so.get("number", "")})
            lc = so.get("loading_check")
            if lc:
                ev.append({"at": lc.get("checked_at"), "kind": "loading",
                           "label": f"Final Loading Check: {'BERSIH' if lc.get('result') == 'clean' else 'ADA SELISIH'} "
                                    f"({lc.get('matched')}/{lc.get('expected')})",
                           "ref": so.get("number", "")})

    ev = [e for e in ev if e.get("at")]
    ev.sort(key=lambda e: e["at"])
    journey = roll.get("journey") or {}
    wh = await db.warehouses.find_one({"id": roll.get("warehouse_id")}, {"_id": 0, "name": 1}) or {}
    return {
        "roll": {"id": roll["id"], "roll_no": roll.get("roll_no"), "status": roll.get("status"),
                 "grade": roll.get("grade"), "warehouse_name": wh.get("name", ""),
                 "qty": roll.get("length_remaining"), "unit": roll.get("unit"),
                 "epc": (tag or {}).get("epc"), "last_scan": roll.get("last_scan"),
                 "journey_stage": journey.get("stage"),
                 "journey_stage_label": STAGE_LABEL.get(journey.get("stage"), journey.get("stage") or "—"),
                 "routing": journey.get("routing")},
        "events": [safe_doc(e) for e in ev],
    }
