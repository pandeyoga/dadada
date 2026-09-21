"""Pagar bersama template, SKU, media dan relasi R&D. Produk tetap SHARED."""
from fastapi import HTTPException
from db import db
from core_utils import strip_cost_fields
from services import line_scope, product_exclusivity


def visible_query(actor, query=None):
    if not actor:
        raise HTTPException(401, "Sesi diperlukan.")
    return line_scope.narrow(line_scope._merge(query or {}, product_exclusivity.visibility_query(actor)), actor)


async def product_for(actor, product_id):
    row = await db.products.find_one(visible_query(actor, {"id": product_id}), {"_id": 0})
    if not row:
        raise HTTPException(404, "Produk tidak ditemukan.")
    return row


def public_product(product, actor, *, manage=False):
    out = strip_cost_fields(dict(product), actor.get("role"))
    out.pop("saga_lock", None)
    media = [dict(m) for m in out.get("media", []) if not m.get("deleted") and (manage or m.get("status") == "approved")]
    for m in media:
        m.pop("path", None)
        m['is_ai'] = bool(m.get('ai'))
        if not manage:
            for key in ("ai", "source", "created_by", "reviewed_by"):
                m.pop(key, None)
    out["media"] = sorted(media, key=lambda m: (m.get("sort_order", 0), m.get("id", "")))
    if not manage:
        for key in ("owner_sales_ids", "spec_id", "design_id", "design_version", "source_special_order_id"):
            out.pop(key, None)
    return out


async def template_for(actor, template_id, *, manage=False):
    template = await db.product_templates.find_one(visible_query(actor, {"id": template_id}), {"_id": 0})
    if not template:
        raise HTTPException(404, "Induk produk tidak ditemukan.")
    children = await db.products.find(visible_query(actor, {"template_id": template_id}), {"_id": 0}).sort("sku", 1).to_list(10000)
    if not children and not manage:
        raise HTTPException(404, "Induk produk tidak ditemukan.")
    out = public_product(template, actor, manage=manage)
    out['variants'] = [public_product(p, actor, manage=manage) for p in children]
    out['variant_count'] = len(children)
    # Opsi milik SKU yang tidak terlihat tidak boleh bocor melalui metadata induk.
    if not manage:
        out['axes'] = [{**a, 'options': [o for o in a.get('options', []) if any(
            (p.get('variant_options') or {}).get(a['key']) == o['code'] or
            str((p.get('variant_attrs') or {}).get(a['key'], p.get(a['key'], ''))) == str(o['label']) for p in children)]} for a in out.get('axes', [])]
    return out