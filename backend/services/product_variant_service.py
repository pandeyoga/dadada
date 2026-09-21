"""Satu induk, SKU tetap: jalur bersama untuk seluruh penulis produk.

Mongo standalone: claims serialize family changes; unique indexes close races.
Never infer a legacy family from a similar name. No transaction ID is replaced.
"""
import hashlib
from contextlib import asynccontextmanager
from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError
from db import db
from core_utils import now_iso, safe_doc, new_id
from services import atomic_claim, catalog_rules, rnd_gate


def family_name(product):
    return str(product.get("name") or product.get("sku") or "Produk").strip()


def canonical_color(product):
    return str((product.get("variant_attrs") or {}).get("color") or product.get("color") or product.get("color_name") or "Natural")


def color_code_for(color):
    words = str(color).split()
    return ((words[0][:2] + words[1][:1]) if len(words) > 1 else (words[0][:3] if words else "STD")).upper()


def variant_sku(parent, color, grade="A"):
    return f"{parent.get('sku_prefix') or 'PRD'}-{color_code_for(color)}" + (f"-{grade.upper()}" if grade != "A" else "")


def variant_attrs(product):
    attrs = dict(product.get("variant_attrs") or {})
    if not attrs:
        attrs = {"color": canonical_color(product), "grade": product.get("grade") or "A"}
        if product.get("lebar"):
            attrs["lebar"] = str(product["lebar"])
    return attrs


def variant_label(attrs):
    return " · ".join(str(v) for v in attrs.values()) or "Standar"


async def ensure_indexes():
    await db.products.create_index("sku", unique=True, name="uniq_sku")
    await db.product_templates.create_index("id", unique=True, name="catalog_parent_id")
    await db.products.create_index([("template_id", 1), ("variant_key", 1)], unique=True,
                                  partialFilterExpression={"catalog_version": 2}, name="catalog_combination_v2")


async def parent_from_product(product, actor="System"):
    """Additive fallback for legacy/single-SKU/import/MTO; stable ID, no name merging."""
    tid = "ptpl_" + hashlib.sha256(product["id"].encode()).hexdigest()[:20]
    fields = ("category", "fabric_type", "motif", "stage", "description", "base_unit", "gramasi", "lebar", "supplier", "yarn_count", "yarn_count_system", "line_code", "exclusivity", "owner_sales_ids")
    doc = {k: product[k] for k in fields if k in product}
    doc.update(id=tid, name=family_name(product), sku_prefix=product.get("sku", ""),
               base_price=product.get("price", 0), image=product.get("image", ""), axes=[],
               status="active", legacy_parent=True, created_by=actor, created_at=now_iso(), updated_at=now_iso())
    await db.product_templates.update_one({"id": tid}, {"$setOnInsert": doc}, upsert=True)
    return await db.product_templates.find_one({"id": tid}, {"_id": 0})


@asynccontextmanager
async def family_lock(template_id, action="catalog_write", actor=""):
    await atomic_claim.claim("product_templates", template_id, action, actor=actor)
    try:
        yield
    finally:
        current = await db.product_templates.find_one({'id': template_id}, {'_id': 0, 'saga_lock': 1}) or {}
        if not (current.get('saga_lock') or {}).get('failed_at'):
            await atomic_claim.release("product_templates", template_id)


async def prepare(product, actor="System", *, allow_orphan_repair=False):
    tid = str(product.get("template_id") or "").strip()
    parent = await db.product_templates.find_one({"id": tid}, {"_id": 0}) if tid else None
    if tid and not parent and not allow_orphan_repair:
        raise HTTPException(400, "Induk produk tidak ditemukan. Pilih induk yang masih aktif.")
    if not parent:
        parent = await parent_from_product(product, actor)
    if parent.get("status") != "active":
        raise HTTPException(409, "Induk produk sudah diarsipkan.")
    for field in ("fabric_type", "base_unit", "stage"):
        if parent.get(field) and product.get(field) and parent[field] != product[field]:
            raise HTTPException(400, f"{field} varian harus sama dengan induknya.")
    product["template_id"] = parent["id"]
    product["template_name"] = parent["name"]
    if parent.get('line_code'):
        if product.get('line_code') and product['line_code'] != parent['line_code']:
            raise HTTPException(400, 'Lini SKU harus sesuai induknya.')
        product['line_code'] = parent['line_code']
    if parent.get('exclusivity') == 'sales_tertentu':
        parent_owners = set(parent.get('owner_sales_ids') or [])
        owners = set(product.get('owner_sales_ids') or []) if product.get('exclusivity') == 'sales_tertentu' else parent_owners
        owners &= parent_owners
        if not owners:
            raise HTTPException(400, 'Pemilik SKU harus termasuk pemilik induk eksklusif.')
        product['exclusivity'] = 'sales_tertentu'
        product['owner_sales_ids'] = sorted(owners)
    from services import base_fabric
    if product.get("base_fabric_template_id"):
        try:
            product.update(await base_fabric.snapshot(product["base_fabric_template_id"], exclude_id=parent["id"]))
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
    else:
        base_fabric.inherit(product, parent)
    if not parent.get("axes"):
        product["variant_attrs"] = variant_attrs(product)
        product["variant_options"] = {}
    try:
        catalog_rules.combination(parent, product)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    product["catalog_version"] = 2
    return parent


async def check_duplicate(product):
    others = await db.products.find({"template_id": product["template_id"], "id": {"$ne": product["id"]}}, {"_id": 0}).to_list(10000)
    for other in others:
        same = other.get("variant_key") == product["variant_key"]
        if not same and not other.get("variant_key"):
            parent = await db.product_templates.find_one({"id": product["template_id"]}, {"_id": 0})
            try:
                catalog_rules.combination(parent, other)
                same = other.get("variant_key") == product["variant_key"]
            except ValueError:
                same = False
        if same:
            raise HTTPException(409, f"Kombinasi sudah dimiliki SKU {other.get('sku')}. Gunakan SKU tersebut.")


async def save_product(product, *, actor="System", existing=None, entity_id="", strict=True):
    doc = dict(product)
    doc.pop("_id", None); doc.pop("saga_lock", None)
    if not doc.get("id"):
        doc["id"] = new_id("prod")
    if not doc.get("lifecycle"):
        doc["lifecycle"] = await rnd_gate.default_new_lifecycle(entity_id)
    doc["updated_at"] = now_iso()
    if not existing:
        doc["created_at"] = now_iso()
    else:
        doc['created_at'] = existing.get('created_at', doc.get('created_at'))
        if existing.get('saga_lock'):
            raise HTTPException(409, 'SKU sedang diproses. Tunggu sebelum mengubah identitasnya.')
    parent = await prepare(doc, actor)
    async with family_lock(parent["id"], actor=actor):
        # Revalidate after claim: editor/archive cannot change parent between check and write.
        await prepare(doc, actor)
        for field in ('price', 'harga_pokok', 'gramasi', 'lebar', 'kg_per_meter'):
            if doc.get(field) is not None:
                doc[field] = catalog_rules.finite_number(doc[field], field)
        if strict:
            import domain_registry as dr
            dr.apply_normalization(doc)
            checked = dr.validate_product(doc)
            if checked['errors']:
                raise HTTPException(400, ' '.join(checked['errors']))
            doc.update(needs_review=checked['needs_review'], needs_review_reasons=checked['needs_review_reasons'])
        await check_duplicate(doc)
        try:
            if existing:
                # Optimistic concurrency for SKU edits; do not replace concurrent media changes.
                fields = {k: v for k, v in doc.items() if k not in {"media", "media_revision", "saga_lock"}}
                match = {"id": doc["id"], "updated_at": existing.get("updated_at"), 'saga_lock': {'$exists': False}}
                res = await db.products.update_one(match, {"$set": fields})
                if not res.matched_count:
                    raise HTTPException(409, "Produk berubah. Muat ulang sebelum menyimpan.")
            else:
                await db.products.insert_one(dict(doc))
        except DuplicateKeyError as exc:
            raise HTTPException(409, "SKU atau kombinasi varian sudah digunakan.") from exc
    return safe_doc(await db.products.find_one({"id": doc["id"]}, {"_id": 0}))


async def ensure_parent(product, actor="System"):
    doc = dict(product)
    parent = await prepare(doc, actor, allow_orphan_repair=True)
    await check_duplicate(doc)
    fields = {k: doc[k] for k in ("template_id", "template_name", "variant_attrs", "variant_options", "variant_key", "variant_label", "catalog_version")}
    await db.products.update_one({"id": doc["id"]}, {"$set": fields})
    product.update(fields)
    return parent


async def count_orphans():
    live = set(await db.product_templates.distinct("id"))
    return await db.products.count_documents({"template_id": {"$nin": list(live)}})


async def resolve_orphans(actor="System", dry_run=False):
    live = set(await db.product_templates.distinct("id"))
    fixed, conflicts = 0, []
    async for product in db.products.find({}, {"_id": 0}):
        if product.get("template_id") in live and product.get("catalog_version") == 2:
            continue
        if dry_run:
            fixed += 1
            continue
        try:
            await ensure_parent(product, actor)
            fixed += 1
        except (HTTPException, ValueError, DuplicateKeyError) as exc:
            conflicts.append({"sku": product.get("sku"), "reason": str(getattr(exc, "detail", exc))})
    return {"products_linked": fixed, "dry_run": dry_run, "conflicts": conflicts, "orphans_left": await count_orphans()}


async def family_summary(template_id, actor, ctx, manage=False):
    from services.catalog_access import template_for
    from entity_scope import resolve_list_scope
    tpl = await template_for(actor, template_id, manage=manage)
    variants = tpl.pop("variants")
    rows = []
    for v in variants:
        scope = resolve_list_scope("inventory_balances", {"product_id": v["id"]}, ctx)
        balances = await db.inventory_balances.find(scope, {"_id": 0}).to_list(10000)
        v['available'] = round(sum(float(b.get('available', 0) or 0) for b in balances), 2)
        v['reserved'] = round(sum(float(b.get('reserved', 0) or 0) for b in balances), 2)
        rq = resolve_list_scope("inventory_rolls", {"product_id": v['id'], "length_remaining": {"$gt": 0}}, ctx)
        v['rolls'] = await db.inventory_rolls.count_documents(rq)
        rows.append(v)
    # Quantity totals must never add kg and meter. Family base_unit is enforced.
    return {"template": tpl, "variants": rows, "totals": {"variants": len(rows), "available": sum(v['available'] for v in rows), "reserved": sum(v['reserved'] for v in rows), "rolls": sum(v['rolls'] for v in rows)}}