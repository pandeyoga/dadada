"""§3-C Jual Sampel — master harga sampel per induk, quote untuk POS, dan aksi potong gudang.

Permintaan sampel TIDAK lagi dokumen terpisah: ia baris SO ber-`is_sample` (lihat
`services/sample_sale_service.py`). Router ini hanya menyisakan master harga, quote,
dan aksi potong atas tugas outbound bersubtipe `sample_cut`.
"""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from core_utils import now_iso
from db import db
from dependencies import audit, require_permission
from entity_scope import assert_entity_access, entity_ctx, resolve_scope_ids
from services import sample_sale_service as svc

router = APIRouter(prefix="/api")


class SamplePriceIn(BaseModel):
    price_per_unit: float = Field(..., ge=0)


class SampleCutIn(BaseModel):
    roll_id: str = ""
    epc: str = ""
    actual_length: Optional[float] = Field(None, gt=0)
    reason: str = ""


@router.get("/sample-prices")
async def list_sample_prices(request: Request) -> List[Dict[str, Any]]:
    await require_permission(request, "product", "view")
    tpls = await db.product_templates.find({}, {"_id": 0, "id": 1, "name": 1, "base_unit": 1, "base_price": 1}).to_list(2000)
    masters = {m["template_id"]: m for m in await db.sample_price_master.find({}, {"_id": 0}).to_list(2000)}
    return [{"template_id": t["id"], "template_name": t.get("name"), "unit": t.get("base_unit") or "yard",
             "list_price": float(t.get("base_price") or 0),
             "price_per_unit": float((masters.get(t["id"]) or {}).get("price_per_unit") or 0),
             "updated_at": (masters.get(t["id"]) or {}).get("updated_at")} for t in tpls]


@router.put("/sample-prices/{template_id}")
async def put_sample_price(template_id: str, payload: SamplePriceIn, request: Request) -> Dict[str, Any]:
    actor = await require_permission(request, "product", "update")
    if not await db.product_templates.find_one({"id": template_id}, {"_id": 0, "id": 1}):
        raise HTTPException(status_code=404, detail="Induk produk tidak ditemukan")
    doc = {"template_id": template_id, "price_per_unit": float(payload.price_per_unit),
           "updated_at": now_iso(), "updated_by": actor.get("name", "")}
    await db.sample_price_master.update_one({"template_id": template_id}, {"$set": doc}, upsert=True)
    await audit(actor.get("name", ""), "sample_price_set", "sample_price_master", template_id, doc)
    return doc


@router.get("/sample-quote")
async def sample_quote(request: Request, product_id: str, length: float) -> Dict[str, Any]:
    """POS: harga sampel per satuan + saran roll FIFO untuk baris 'Jual sebagai sampel'."""
    await require_permission(request, "order", "view")
    ctx = await entity_ctx(request)
    product = await db.products.find_one({"id": product_id}, {"_id": 0})
    if not product:
        raise HTTPException(status_code=404, detail="Produk tidak ditemukan")
    price = await svc.sample_price_for(product)
    sug = await svc.suggest_roll(product_id, float(length), resolve_scope_ids(ctx, None)) if length > 0 else None
    return {**price, "length": length, "amount": round(float(length) * price["price_per_unit"], 2),
            "suggested_roll": {k: sug.get(k) for k in ("id", "roll_no", "warehouse_id", "length_remaining", "rfid_tag_id")} if sug else None}


@router.post("/outbound/tasks/{task_id}/cut-sample")
async def cut_sample(task_id: str, payload: SampleCutIn, request: Request) -> Dict[str, Any]:
    """Gudang: pindai roll induk (EPC/QR/nomor roll), potong, catat panjang aktual → roll anak
    ter-reservasi untuk SO; tugas lanjut ke packing seperti baris roll biasa."""
    actor = await require_permission(request, "wms", "scan")
    task = await db.wms_tasks.find_one({"id": task_id}, {"_id": 0, "entity_id": 1})
    if not task:
        raise HTTPException(status_code=404, detail="Tugas tidak ditemukan")
    assert_entity_access(task, "wms_tasks", await entity_ctx(request))
    res = await svc.cut_sample_task(task_id, payload.model_dump(), actor)
    await audit(actor.get("name", ""), "sample_cut", "wms_task", task_id,
                {"roll": res["cut"].get("cut_roll_no"), "child": res["cut"].get("child_roll_no"),
                 "length": res["cut"].get("length"), "so": res["cut"].get("sales_order_number")})
    return res
