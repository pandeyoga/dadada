"""FASE R7 — FULFILLMENT WIZARD: matriks skenario S1–S8 menjadi aksi terpandu.

Analisis satu SO: per item cek stok milik entitas SO (per gudang), stok entitas
lain (kandidat interco + kontrak internal), lalu beri rekomendasi skenario +
langkah terpandu. Aksi 1-klik: buat DRAFT Interco (entitas lain) atau DRAFT PR
(pengadaan). Wizard TIDAK memotong stok — hanya merangkai dokumen resmi existing.
"""
from typing import Any, Dict, List, Optional

from fastapi import HTTPException

from db import db
from core_utils import safe_doc


async def _available_by_owner(product_id: str) -> Dict[str, List[Dict[str, Any]]]:
    out: Dict[str, List[Dict[str, Any]]] = {}
    wh_names = {w["id"]: w.get("name", w["id"]) async for w in
                db.warehouses.find({}, {"_id": 0, "id": 1, "name": 1})}
    async for b in db.inventory_balances.find(
            {"product_id": product_id, "available_qty": {"$gt": 0}}, {"_id": 0}):
        out.setdefault(b["owner_entity_id"], []).append({
            "warehouse_id": b["warehouse_id"],
            "warehouse_name": wh_names.get(b["warehouse_id"], b["warehouse_id"]),
            "available_qty": b["available_qty"]})
    return out


async def analyze(so_id: str, scope_ids: List[str]) -> Dict[str, Any]:
    so = await db.sales_orders.find_one({"id": so_id}, {"_id": 0})
    if not so:
        raise HTTPException(status_code=404, detail="SO tidak ditemukan")
    if so.get("entity_id") and so["entity_id"] not in scope_ids:
        raise HTTPException(status_code=403, detail="SO di luar entitas Anda")
    buyer = so.get("entity_id")
    ent_names = {e["id"]: (e.get("short_name") or e.get("legal_name") or e.get("name") or e["id"])
                 async for e in db.business_entities.find(
                     {}, {"_id": 0, "id": 1, "legal_name": 1, "short_name": 1, "name": 1})}

    items_out: List[Dict[str, Any]] = []
    needs_interco: Dict[str, List[Dict[str, Any]]] = {}
    needs_procurement: List[Dict[str, Any]] = []
    for it in so.get("items") or []:
        pid = it.get("product_id")
        qty = float(it.get("quantity") or 0)
        avail = await _available_by_owner(pid)
        own_rows = avail.get(buyer, [])
        own_total = sum(r["available_qty"] for r in own_rows)
        others = []
        for ent, rows in avail.items():
            if ent == buyer:
                continue
            total = sum(r["available_qty"] for r in rows)
            # Kontrak internal HARUS spesifik pasangan (penjual=ent, pembeli=buyer) +
            # masa berlaku — pakai resolusi yang sama dengan penegakan interco.
            from services.interco_service import _find_active_internal_contract
            contract = await _find_active_internal_contract(ent, buyer, pid)
            if contract:
                contract = {k: contract.get(k) for k in ("id", "contract_number", "tariff_rate")}
            others.append({"entity_id": ent, "entity_name": ent_names.get(ent, ent),
                           "available_qty": total, "warehouses": rows,
                           "contract": safe_doc(contract) if contract else None})
        others.sort(key=lambda x: -x["available_qty"])

        if own_total >= qty:
            rec, scen = "alokasi_stok", "S4a"
            label = "Stok sendiri CUKUP — alokasikan langsung dari gudang."
            steps = ["Alokasikan roll ke SO (layar Alokasi/Pegging)",
                     "Picking per gudang → gate-out → staging transit",
                     "Final Loading Check → dispatch + Surat Jalan"]
        elif others and others[0]["available_qty"] >= qty - own_total:
            rec, scen = "interco", "S4"
            src = others[0]
            label = (f"Stok kurang {qty - own_total:g} — beli antar-PT dari "
                     f"{src['entity_name']} ({src['available_qty']:g} tersedia"
                     f"{', ada kontrak internal' if src['contract'] else ', TANPA kontrak internal — harga perlu override'}).")
            steps = [f"Buat DRAFT Interco: {src['entity_name']} → {ent_names.get(buyer, buyer)}",
                     "Konfirmasi → ship → receive (kepemilikan pindah, jurnal kembar otomatis)",
                     "Alokasikan ke SO → picking → loading check → kirim"]
            needs_interco.setdefault(src["entity_id"], []).append(
                {"product_id": pid, "quantity": qty - own_total})
        else:
            rec, scen = "pengadaan", "S5" if not others else "S1"
            label = ("Stok tidak ada di entitas mana pun — buat PR/PO baru. "
                     "Karena PO lahir dari SO ini, sarankan routing CROSS-DOCK "
                     "(barang tiba di transit langsung disiapkan kirim, tidak di-putaway).")
            steps = ["Buat DRAFT PR (1-klik di bawah) → approve → PO",
                     "Terima barang di Gudang Transit → print tag → verifikasi",
                     "Set routing CROSS-DOCK → staging → loading check → kirim"]
            needs_procurement.append({"product_id": pid, "sku": it.get("sku", ""),
                                      "product_name": it.get("product_name", ""),
                                      "quantity": qty - own_total, "unit": it.get("unit", "")})
        items_out.append({
            "product_id": pid, "sku": it.get("sku", ""), "product_name": it.get("product_name", ""),
            "qty_needed": qty, "unit": it.get("unit", ""),
            "own_available": own_total, "own_warehouses": own_rows,
            "other_entities": others,
            "recommendation": rec, "scenario": scen, "label": label, "steps": steps,
        })

    recs = {i["recommendation"] for i in items_out}
    overall = ("tidak_ada_item" if not items_out else
               "alokasi_stok" if recs == {"alokasi_stok"} else
               "campuran" if len(recs) > 1 else recs.pop())
    return {
        "so": {"id": so["id"], "number": so.get("number", ""), "entity_id": buyer,
               "entity_name": ent_names.get(buyer, buyer), "status": so.get("status", "")},
        "items": items_out,
        "overall": overall,
        "interco_drafts": [{"seller_entity_id": k, "seller_entity_name": ent_names.get(k, k),
                            "items": v} for k, v in needs_interco.items()],
        "procurement_items": needs_procurement,
    }


async def create_interco_draft(so_id: str, seller_entity_id: str,
                               items: List[Dict[str, Any]], scope_ids: List[str],
                               actor: Dict[str, Any]) -> Dict[str, Any]:
    from services import interco_service
    so = await db.sales_orders.find_one({"id": so_id}, {"_id": 0, "entity_id": 1, "number": 1})
    if not so:
        raise HTTPException(status_code=404, detail="SO tidak ditemukan")
    if so.get("entity_id") not in scope_ids:
        raise HTTPException(status_code=403, detail="SO di luar entitas Anda")
    try:
        doc = await interco_service.create({
            "seller_entity_id": seller_entity_id,
            "buyer_entity_id": so["entity_id"],
            "items": items,
            "notes": f"[Wizard] Pemenuhan SO {so.get('number', so_id)}",
        }, actor=actor.get("name", ""), actor_user=actor)
    except Exception as exc:  # IntercoError → 400 dengan pesan aslinya
        raise HTTPException(status_code=400, detail=str(exc))
    return safe_doc(doc)


async def create_pr_draft(so_id: str, items: List[Dict[str, Any]], scope_ids: List[str],
                          actor: Dict[str, Any]) -> Dict[str, Any]:
    from services import purchase_requisition_service as prs
    so = await db.sales_orders.find_one({"id": so_id}, {"_id": 0, "entity_id": 1, "number": 1})
    if not so:
        raise HTTPException(status_code=404, detail="SO tidak ditemukan")
    if so.get("entity_id") not in scope_ids:
        raise HTTPException(status_code=403, detail="SO di luar entitas Anda")
    from types import SimpleNamespace
    payload = SimpleNamespace(
        entity_id=so["entity_id"], warehouse_id="",
        items=[SimpleNamespace(product_id=i["product_id"], quantity=float(i["quantity"]),
                               est_price=0, unit="", notes="")
               for i in items],
        source="wizard", source_ref_id=so_id,
        reason=f"Pemenuhan SO {so.get('number', so_id)}",
        notes=f"[Wizard] Pengadaan untuk SO {so.get('number', so_id)} — saran routing CROSS-DOCK",
        submit_now=False,
    )
    try:
        doc = await prs.create_requisition(payload, created_by=actor.get("name", ""),
                                           created_by_id=actor.get("id", ""))
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return safe_doc(doc)
