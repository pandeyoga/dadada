"""F1b — Product Templates & Variants router (ADDITIVE/non-destruktif).

Katalog SHARED lintas-entitas (D1). Akses: permission module "product"
(create/update/delete = admin; view = semua). Kontrak respons OBJEK/ARRAY telanjang.
"""
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Request, Query

from dependencies import require_permission, audit, permission_matrix
from entity_scope import entity_ctx
from services import catalog_access, line_scope, product_exclusivity
from db import db
from schemas import ProductTemplateCreate, ProductTemplatePatch, VariantGenerateIn, AssignProductsIn
from services import product_template_service as svc

router = APIRouter(prefix="/api")


@router.get("/product-templates")
async def list_templates(request: Request, search: str = Query(""), offset: int = Query(0, ge=0), limit: int = Query(500, ge=1, le=500), paginate: bool = False):
    actor = await require_permission(request, "product", "view")
    matrix = await permission_matrix()
    manage = 'update' in matrix.get(actor.get('role'), {}).get('product', [])
    return await svc.list_templates(search=search, actor=actor, manage=manage, offset=offset, limit=limit, paginate=paginate)


@router.get("/product-templates/{template_id}/summary")
async def template_summary(template_id: str, request: Request) -> Dict[str, Any]:
    """Induk = katalog & agregasi: varian + stok tersedia/dipesan + roll (bertag) per varian."""
    actor = await require_permission(request, "product", "view")
    from services import product_variant_service as pvs
    matrix = await permission_matrix()
    manage = 'update' in matrix.get(actor.get('role'), {}).get('product', [])
    out = await pvs.family_summary(template_id, actor, await entity_ctx(request), manage=manage)
    if not out:
        raise HTTPException(status_code=404, detail="Template tidak ditemukan")
    return out


@router.post("/product-templates/resolve-orphans")
async def resolve_orphans(request: Request, dry_run: bool = True) -> Dict[str, Any]:
    """Migrasi idempoten: setiap produk (varian) mendapat induk hidup (tak ada `template_id` yatim)."""
    actor = await require_permission(request, "product", "delete")
    from services import product_variant_service as pvs
    res = await pvs.resolve_orphans(actor.get("name", "System"), dry_run=dry_run)
    await audit(actor.get("name", ""), "product_variants_reparented", "product_template", "all", res)
    return res


@router.get("/product-templates/{template_id}")
async def get_template(template_id: str, request: Request) -> Dict[str, Any]:
    actor = await require_permission(request, "product", "view")
    matrix = await permission_matrix()
    tpl = await svc.get_template(template_id, actor=actor, manage='update' in matrix.get(actor.get('role'), {}).get('product', []))
    if not tpl:
        raise HTTPException(status_code=404, detail="Template tidak ditemukan")
    # FASE SL — alias supplier (kode & nama versi pabrik) per varian untuk katalog MD.
    from services.supplier_item_service import attach_supplier_codes
    await attach_supplier_codes(tpl.get("variants") or [])
    return tpl


@router.post("/product-templates")
async def create_template(payload: ProductTemplateCreate, request: Request) -> Dict[str, Any]:
    actor = await require_permission(request, "product", "create")
    data = payload.model_dump()
    ctx = await entity_ctx(request)
    await line_scope.normalize_product(data, entity_id=ctx.active_entity_id)
    line_scope.assert_can_order(actor, data)
    await product_exclusivity.normalize(db, data)
    try:
        tpl = await svc.create_template(data, actor.get("name", ""))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await audit(actor.get("name", ""), "product_template_created", "product_template", tpl["id"],
                {"name": tpl["name"], "axes": len(tpl.get("axes", []))})
    return tpl


@router.patch("/product-templates/{template_id}")
async def patch_template(template_id: str, payload: ProductTemplatePatch, request: Request) -> Dict[str, Any]:
    actor = await require_permission(request, "product", "update")
    existing = await catalog_access.template_for(actor, template_id, manage=True)
    data = payload.model_dump(exclude_none=True)
    await line_scope.normalize_product(data, existing, (await entity_ctx(request)).active_entity_id)
    await product_exclusivity.normalize(db, data)
    try:
        tpl = await svc.update_template(template_id, data)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    if tpl is None:
        raise HTTPException(status_code=404, detail="Template tidak ditemukan")
    await audit(actor.get("name", ""), "product_template_updated", "product_template", template_id, {})
    return tpl


@router.delete("/product-templates/{template_id}")
async def delete_template(template_id: str, request: Request) -> Dict[str, Any]:
    actor = await require_permission(request, "product", "delete")
    await catalog_access.template_for(actor, template_id, manage=True)
    try:
        res = await svc.delete_template(template_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    await audit(actor.get("name", ""), "product_template_deleted", "product_template", template_id, res)
    return res


@router.post("/product-templates/{template_id}/generate-variants")
async def generate_variants(template_id: str, payload: VariantGenerateIn, request: Request) -> Dict[str, Any]:
    actor = await require_permission(request, "product", "create")
    try:
        res = await svc.generate_variants(template_id, payload.model_dump(), actor=actor, entity_id=(await entity_ctx(request)).active_entity_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await audit(actor.get("name", ""), "variants_generated", "product_template", template_id,
                {"created": res["created"], "skipped": res["skipped"]})
    return res


@router.post("/product-templates/{template_id}/assign")
async def assign_products(template_id: str, payload: AssignProductsIn, request: Request) -> Dict[str, Any]:
    actor = await require_permission(request, "product", "update")
    try:
        res = await svc.assign_products(template_id, payload.product_ids)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    await audit(actor.get("name", ""), "variants_assigned", "product_template", template_id, res)
    return res


@router.post("/product-templates/detach")
async def detach_products(payload: AssignProductsIn, request: Request) -> Dict[str, Any]:
    actor = await require_permission(request, "product", "update")
    res = await svc.detach_products(payload.product_ids)
    await audit(actor.get("name", ""), "variants_detached", "product", "batch", res)
    return res
