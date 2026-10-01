"""Panel profil pelanggan yang dirangkai SERVER — prefix `/customers/{cid}/...`.

  * `contract-pricing`  → tab "Kontrak & Harga": per transaksi (deal) → skema yang DIPILIH
    saat reservasi, rincian harga (dasar/add-on/diskon/neto), termin, kontrak (komponen
    biaya + tahap legal), dan ringkasan AR — plus pemeriksaan SINKRON skema deal ↔ kontrak ↔ AR.
  * `units-construction` → tab "Unit & Konstruksi": jadwal bangun per tahap, milestone,
    bukti foto terakhir, status serah terima, dan tautan ke modul Pembangunan.
"""
from fastapi import APIRouter, Depends, HTTPException

import contracts_engine as ce
import reference as ref
from core_utils import serialize_doc
from db import ORG_ID, db
from rbac import require_permission

router = APIRouter(prefix="/customers", tags=["customer-hub"])


def _org(user: dict) -> str:
    return user.get("org_id", ORG_ID)


async def _customer(org: str, cid: str) -> dict:
    cust = await db.customers.find_one({"id": cid, "org_id": org}, {"_id": 0})
    if not cust:
        raise HTTPException(status_code=404, detail="Pelanggan tidak ditemukan")
    return cust


async def _deals_of(org: str, cust: dict) -> list:
    ors = [{"customer_id": cust["id"]}]
    if cust.get("lead_id"):
        ors.append({"lead_id": cust["lead_id"]})
    return await db.deals.find({"org_id": org, "$or": ors}, {"_id": 0}).sort(
        "created_at", -1).to_list(50)


def _scheme_view(doc: dict) -> dict:
    if not doc:
        return None
    kind = doc.get("kind") or doc.get("type")
    return {"id": doc.get("id"), "name": doc.get("name"), "kind": kind,
            "kind_label": ref.label_of("payment_scheme_kind", kind or "") if kind else None,
            "items": [{"label": i.get("label"), "basis": i.get("basis"), "value": i.get("value"),
                       "due_rule": i.get("due_rule"), "due_offset_days": i.get("due_offset_days")}
                      for i in (doc.get("items") or [])]}


async def _deal_block(org: str, deal: dict) -> dict:
    pricing = deal.get("pricing") or {}
    scheme_doc = (await db.payment_schemes.find_one({"id": deal.get("scheme_id"), "org_id": org},
                                                    {"_id": 0}) if deal.get("scheme_id") else None)
    contract = await db.contracts.find_one({"org_id": org, "deal_id": deal["id"]}, {"_id": 0})
    inv = await db.ar_invoices.find_one({"org_id": org, "deal_id": deal["id"]}, {"_id": 0})
    quotation = await db.quotations.find_one(
        {"org_id": org, "$or": [{"deal_id": deal["id"]},
                                {"id": (contract or {}).get("quotation_id") or "-"}]},
        {"_id": 0, "id": 1, "no": 1, "number": 1, "version": 1, "state": 1})

    contract_view = None
    if contract:
        bd = await ce.build_breakdown(org, contract)
        contract_view = {
            "id": contract["id"], "number": contract.get("number"), "state": contract.get("state"),
            "legal_stage": contract.get("legal_stage"), "scheme": contract.get("scheme"),
            "scheme_label": contract.get("scheme_label"),
            "payment_scheme_id": contract.get("payment_scheme_id"),
            "payment_scheme_name": contract.get("payment_scheme_name"),
            "activated_at": contract.get("activated_at"),
            "costs": contract.get("costs") or {},
            "breakdown": bd,
        }

    ar_view = None
    if inv:
        items = inv.get("items") or []
        nxt = next((i for i in sorted(items, key=lambda x: str(x.get("due_date") or ""))
                    if i.get("status") not in ("paid", "waived", "cancelled")), None)
        overdue = [i for i in items if i.get("status") in ("unpaid", "partial", "overdue")
                   and str(i.get("due_date") or "") < inv.get("updated_at", "")[:10]]
        ar_view = {"id": inv["id"], "status": inv.get("status"), "total": inv.get("total"),
                   "paid": inv.get("paid"), "outstanding": inv.get("outstanding"),
                   "scheme_id": inv.get("scheme_id"), "scheme_name": inv.get("scheme_name"),
                   "items": items, "next_due": nxt, "overdue_count": len(overdue)}

    # --- pemeriksaan sinkron skema: deal (pilihan sales) ↔ kontrak ↔ AR
    deal_kind = (scheme_doc or {}).get("kind") or (scheme_doc or {}).get("type")
    issues = []
    if contract and deal_kind and contract.get("scheme") != deal_kind:
        issues.append(f"Kontrak berskema {contract.get('scheme_label')} sedangkan reservasi "
                      f"memilih {ref.label_of('payment_scheme_kind', deal_kind)}.")
    if contract and scheme_doc and contract.get("payment_scheme_id") \
            and contract["payment_scheme_id"] != scheme_doc["id"]:
        issues.append(f"Kontrak memakai skema '{contract.get('payment_scheme_name')}' — "
                      f"berbeda dari pilihan saat reservasi '{scheme_doc.get('name')}'.")
    if inv and scheme_doc and inv.get("scheme_id") and inv["scheme_id"] != scheme_doc["id"]:
        issues.append(f"Tagihan AR memakai skema '{inv.get('scheme_name')}' — berbeda dari "
                      f"pilihan saat reservasi '{scheme_doc.get('name')}'.")
    if inv and contract and contract.get("payment_scheme_id") \
            and inv.get("scheme_id") != contract["payment_scheme_id"]:
        issues.append("Tagihan AR belum mengikuti skema kontrak (aktifkan ulang / perbarui termin).")
    if scheme_doc and scheme_doc.get("name") and deal_kind:
        nm = scheme_doc["name"].lower()
        if "kpr" in nm and deal_kind != "kpr":
            issues.append(f"Nama skema '{scheme_doc['name']}' menyebut KPR tetapi jenisnya "
                          f"{ref.label_of('payment_scheme_kind', deal_kind)} — perbaiki di "
                          "Pusat Konfigurasi › Skema Pembayaran.")

    return {
        "deal": {k: deal.get(k) for k in ("id", "unit_id", "unit_code", "project_id", "status",
                                           "price", "booking_fee", "reserved_at", "booked_at",
                                           "scheme_id", "scheme_explicit", "assigned_to")},
        "scheme": _scheme_view(scheme_doc),
        "pricing": {
            "base_price": pricing.get("base_price", deal.get("price")),
            "addon_total": pricing.get("addon_total"),
            "addon_lines": deal.get("addons") or pricing.get("addons") or [],
            "discount_amount": pricing.get("discount_amount"),
            "discount_lines": pricing.get("discount_lines") or [],
            "cost_discount_amount": pricing.get("cost_discount_amount"),
            "net_price": pricing.get("net_price", deal.get("price")),
            "buyer_total": pricing.get("buyer_total"),
            "terms": pricing.get("terms") or [],
            "taxes": pricing.get("taxes"),
            "payment_breakdown": pricing.get("payment_breakdown"),
            "kpr": pricing.get("kpr"),
        },
        "quotation": quotation,
        "contract": contract_view,
        "ar": ar_view,
        "sync": {"ok": not issues, "issues": issues},
    }


@router.get("/{cid}/contract-pricing")
async def contract_pricing(cid: str,
                           user: dict = Depends(require_permission("customers", "view"))):
    org = _org(user)
    cust = await _customer(org, cid)
    deals = await _deals_of(org, cust)
    blocks = [await _deal_block(org, d) for d in deals]
    return {"data": serialize_doc(blocks), "total": len(blocks),
            "customer": {"id": cust["id"], "name": cust.get("name"), "lead_id": cust.get("lead_id")}}


# ============================================================ unit & konstruksi
async def _unit_block(org: str, unit: dict, deal: dict) -> dict:
    sched = await db.build_schedules.find_one({"org_id": org, "unit_id": unit["id"]}, {"_id": 0})
    items, photos, milestones = [], [], []
    if sched:
        rows = await db.build_items.find({"org_id": org, "schedule_id": sched["id"]},
                                         {"_id": 0}).sort("order", 1).to_list(500)
        for it in rows:
            items.append({k: it.get(k) for k in (
                "id", "step_code", "name", "week", "weight", "status", "planned_start",
                "planned_finish", "started_at", "submitted_at", "verified_at", "completed_at",
                "hold_point", "handover_gate", "late_days", "assigned_to", "min_photos")}
                | {"evidence_count": len(it.get("evidence") or [])})
            if it.get("hold_point") or it.get("handover_gate"):
                milestones.append({"code": it.get("step_code"), "name": it.get("name"),
                                   "status": it.get("status"), "planned_finish": it.get("planned_finish"),
                                   "completed_at": it.get("completed_at"),
                                   "kind": "serah_terima" if it.get("handover_gate") else "hold_point"})
            for ev in (it.get("evidence") or []):
                photos.append({"file_id": ev.get("file_id"), "filename": ev.get("filename"),
                               "uploaded_at": ev.get("uploaded_at") or ev.get("attached_at"),
                               "step": it.get("name"), "step_code": it.get("step_code")})
        photos.sort(key=lambda p: str(p.get("uploaded_at") or ""), reverse=True)
    handover = await db.unit_handovers.find_one({"org_id": org, "unit_id": unit["id"]},
                                                {"_id": 0, "id": 1, "number": 1, "state": 1,
                                                 "state_label": 1, "handed_over_at": 1,
                                                 "received_by": 1, "keys_handed": 1, "warranties": 1})
    contract = await db.contracts.find_one({"org_id": org, "unit_id": unit["id"],
                                            "state": {"$ne": "cancelled"}},
                                           {"_id": 0, "id": 1, "legal_stage": 1, "number": 1})
    done = sum(1 for i in items if i["status"] == "done")
    return {
        "unit": {k: unit.get(k) for k in ("id", "code", "type", "block", "project_id",
                                           "project_name", "price", "status",
                                           "construction_status", "construction_progress",
                                           "land_area", "building_area")}
        | {"construction_label": ref.label_of("construction_status",
                                              unit.get("construction_status") or "") or None},
        "deal": {k: (deal or {}).get(k) for k in ("id", "status", "booked_at")} if deal else None,
        "schedule": ({k: sched.get(k) for k in ("id", "status", "progress", "planned_progress",
                                                "deviation", "planned_start", "planned_finish",
                                                "started_at", "finished_at", "template_code")}
                     if sched else None),
        "items": items, "items_done": done, "items_total": len(items),
        "milestones": milestones, "photos": photos[:8],
        "handover": handover, "contract": contract,
        "links": {"unit": f"/units/{unit['id']}", "build": f"/units/{unit['id']}?tab=build",
                  "construction": f"/construction?project_id={unit.get('project_id')}"},
    }


@router.get("/{cid}/units-construction")
async def units_construction(cid: str,
                             user: dict = Depends(require_permission("customers", "view"))):
    org = _org(user)
    cust = await _customer(org, cid)
    deals = await _deals_of(org, cust)
    unit_ids = {d.get("unit_id") for d in deals if d.get("unit_id")
                and d.get("status") not in ("cancelled", "expired")}
    for u in await db.units.find({"org_id": org, "customer_id": cid}, {"_id": 0, "id": 1}).to_list(50):
        unit_ids.add(u["id"])
    units = await db.units.find({"org_id": org, "id": {"$in": list(unit_ids)}},
                                {"_id": 0}).sort("code", 1).to_list(50)
    deal_by_unit = {d.get("unit_id"): d for d in reversed(deals)}
    blocks = [await _unit_block(org, u, deal_by_unit.get(u["id"])) for u in units]
    return {"data": serialize_doc(blocks), "total": len(blocks)}
