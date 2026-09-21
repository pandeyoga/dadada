"""F1b — Product Templates & Variants (pendekatan ADDITIVE/non-destruktif).

Katalog `products` TETAP unit jual ber-SKU (POS/stok/SO/harga tidak berubah).
`product_templates` = lapisan induk (definisi + atribut bersama + axis varian).
`products.template_id` menautkan varian ke template. SHARED lintas-entitas (D1).

Axis varian fleksibel:
  axis = {"key": "color", "label": "Warna",
          "options": [{"code": "MRH", "label": "Merah", "value": ""}, ...]}
Generate = cartesian product semua axis → buat produk ber-SKU
  SKU  = f"{sku_prefix}-{kode1}-{kode2}..." (uppercase, lewati SKU yang sudah ada)
  Nama = f"{template.name} {label1} {label2}..."
"""
import itertools
import re
from typing import Any, Dict, List, Optional

import domain_registry as dr
from db import db
from core_utils import new_id, now_iso, safe_doc
from services import base_fabric

PREFIX = "ptpl"
DEFAULT_IMAGE = ""


def _slug(text: str, n: int = 8) -> str:
    s = re.sub(r"[^A-Za-z0-9]", "", str(text or "")).upper()
    return s[:n]


def _prefix_from_name(name: str) -> str:
    words = [w for w in re.split(r"\s+", str(name or "").strip()) if w]
    initials = "".join(w[0] for w in words)[:6].upper()
    return initials or _slug(name, 6) or "PRD"


# ─── CRUD Template ───────────────────────────────────────────────────────────

async def create_template(data: Dict[str, Any], actor_name: str) -> Dict[str, Any]:
    name = (data.get("name") or "").strip()
    if not name:
        raise ValueError("Nama template wajib diisi")
    doc = {
        "id": new_id(PREFIX),
        "name": name,
        "category": (data.get("category") or "Kain").strip(),
        "fabric_type": (data.get("fabric_type") or "").strip(),
        "motif": (data.get("motif") or "Polos").strip(),
        "stage": (data.get("stage") or "finished").strip(),
        # Fase A · D-22 — atribut benang (dipakai bila stage=yarn)
        "yarn_count": (data.get("yarn_count") or "").strip(),
        "yarn_count_system": (data.get("yarn_count_system") or "").strip(),
        "description": (data.get("description") or "").strip(),
        "image": (data.get("image") or "").strip() or DEFAULT_IMAGE,
        "base_unit": (data.get("base_unit") or "meter").strip(),
        "base_price": round(float(data.get("base_price") or 0), 2),
        "harga_pokok": round(float(data.get("harga_pokok") or 0), 2),
        "gramasi": float(data.get("gramasi") or 0),
        "lebar": float(data.get("lebar") or 0),
        "supplier": (data.get("supplier") or "Internal").strip(),
        "sku_prefix": (data.get("sku_prefix") or "").strip().upper() or _prefix_from_name(name),
        "axes": _normalize_axes(data.get("axes") or []),
        **(await base_fabric.snapshot(data.get("base_fabric_template_id"))),
        "line_code": data.get("line_code") or "",
        "exclusivity": data.get("exclusivity") or "umum",
        "owner_sales_ids": data.get("owner_sales_ids") or [],
        "status": "active",
        "created_by": actor_name, "created_at": now_iso(), "updated_at": now_iso(),
    }
    # Fase A (PS-01/02/03) — template = induk produk: domain WAJIB sah sejak awal.
    dr.apply_normalization(doc)
    check = dr.validate_product(doc)
    if check["errors"]:
        raise ValueError(" ".join(check["errors"]))
    doc["needs_review"] = check["needs_review"]
    doc["needs_review_reasons"] = check["needs_review_reasons"]
    await db.product_templates.insert_one(doc)
    out = safe_doc(doc)
    out["domain_warnings"] = check["warnings"]
    return out


def _normalize_axes(axes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    from services.catalog_rules import normalize_axes
    return normalize_axes(axes)


async def update_template(template_id: str, patch: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    tpl = await db.product_templates.find_one({"id": template_id}, {"_id": 0})
    if not tpl:
        return None
    allowed = ["name", "category", "fabric_type", "motif", "description", "image", "line_code", "exclusivity", "owner_sales_ids",
               "base_unit", "base_price", "harga_pokok", "gramasi", "lebar",
               "supplier", "sku_prefix", "status", "stage",
               "yarn_count", "yarn_count_system"]   # Fase A · D-22
    upd: Dict[str, Any] = {}
    for k in allowed:
        if k in patch and patch[k] is not None:
            upd[k] = patch[k]
    if "axes" in patch and patch["axes"] is not None:
        upd["axes"] = _normalize_axes(patch["axes"])
    if patch.get("base_fabric_template_id") is not None:
        upd.update(await base_fabric.snapshot(patch["base_fabric_template_id"], exclude_id=template_id))
    if "sku_prefix" in upd:
        upd["sku_prefix"] = (str(upd["sku_prefix"]).strip().upper() or tpl.get("sku_prefix"))
    # Fase A — normalisasi + validasi domain terhadap dokumen gabungan (patch parsial).
    dr.apply_normalization(upd)
    check = dr.validate_product(upd, tpl)
    if check["errors"]:
        raise ValueError(" ".join(check["errors"]))
    upd["needs_review"] = check["needs_review"]
    upd["needs_review_reasons"] = check["needs_review_reasons"]
    upd["updated_at"] = now_iso()
    from services.product_variant_service import family_lock
    async with family_lock(template_id, "template_update"):
        children = await db.products.find({"template_id": template_id}, {"_id": 0}).to_list(10000)
        if children:
            if 'status' in upd and upd['status'] != 'active':
                raise ValueError('Induk yang masih memiliki SKU tidak boleh diarsipkan melalui perubahan status.')
            for key in ("fabric_type", "stage", "base_unit", "line_code", "exclusivity", "owner_sales_ids"):
                if key in upd and upd[key] != tpl.get(key, "umum" if key == "exclusivity" else [] if key == "owner_sales_ids" else ""):
                    raise ValueError(f"{key} induk yang sudah memiliki SKU tidak dapat diubah massal. Kelola varian tanpa memutus riwayat.")
            if "axes" in upd:
                old = {a['key']: a for a in tpl.get('axes', [])}
                new = {a['key']: a for a in upd['axes']}
                if set(old) != set(new):
                    raise ValueError("Jenis atribut tidak dapat ditambah/dihapus setelah SKU terbentuk. Buat induk baru untuk struktur berbeda.")
                for key, axis in old.items():
                    for opt in axis.get('options', []):
                        if not any(all(n.get(k, '') == opt.get(k, '') for k in ('code', 'label', 'value')) for n in new[key]['options']):
                            raise ValueError("Pilihan yang sudah dipakai tidak boleh dihapus atau diganti. Tambah pilihan baru.")
        await db.product_templates.update_one({"id": template_id}, {"$set": upd})
    return safe_doc(await db.product_templates.find_one({"id": template_id}, {"_id": 0}))


async def delete_template(template_id: str) -> Dict[str, Any]:
    tpl = await db.product_templates.find_one({"id": template_id}, {"_id": 0})
    if not tpl:
        raise ValueError("Template tidak ditemukan")
    from services.product_variant_service import family_lock
    async with family_lock(template_id, "template_archive"):
        if await db.products.count_documents({"template_id": template_id}):
            from fastapi import HTTPException
            raise HTTPException(409, "Induk masih memiliki SKU. Hapus induk dilarang agar stok dan riwayat tetap terhubung; nonaktifkan SKU yang tidak dijual.")
        if await db.md_specs.count_documents({"template_id": template_id}):
            from fastapi import HTTPException
            raise HTTPException(409, "Induk masih dirujuk spesifikasi R&D.")
        await db.product_templates.update_one({"id": template_id}, {"$set": {"status": "archived", "updated_at": now_iso()}})
    return {"deleted": False, "archived": True, "id": template_id, "detached_variants": 0}


# ─── List / detail (dengan jumlah varian) ────────────────────────────────────

async def _variant_counts() -> Dict[str, int]:
    rows = await db.products.aggregate([
        {"$match": {"template_id": {"$exists": True, "$nin": ["", None]}}},
        {"$group": {"_id": "$template_id", "count": {"$sum": 1}}},
    ]).to_list(2000)
    return {r["_id"]: r["count"] for r in rows}


async def list_templates(search: str = "", *, actor, manage=False, offset=0, limit=500, paginate=False):
    from services.catalog_access import visible_query, template_for
    from fastapi import HTTPException
    q = visible_query(actor, {"status": {"$ne": "archived"}})
    if search:
        rx = {"$regex": re.escape(search.strip()), "$options": "i"}
        q = {"$and": [q, {"$or": [{"name": rx}, {"category": rx}, {"sku_prefix": rx}]}]}
    visible = []
    async for t in db.product_templates.find(q, {"_id": 0}).sort("created_at", -1):
        try:
            out = await template_for(actor, t['id'], manage=manage)
        except HTTPException as exc:
            if exc.status_code == 404:
                continue
            raise
        variants = out.pop('variants')
        prices = [float(v.get('price') or 0) for v in variants]
        out['price_min'] = min(prices) if prices else out.get('base_price', 0)
        out['price_max'] = max(prices) if prices else out.get('base_price', 0)
        cover = next((v for v in variants if any(m.get('status') == 'approved' for m in v.get('media', []))), None)
        out['cover_product'] = cover or next((v for v in variants if v.get('image')), None)
        out['media_count'] = sum(len(v.get('media', [])) for v in variants)
        visible.append(out)
    result = visible[offset:offset+limit]
    return {"items": result, "total": len(visible), "offset": offset, "limit": limit} if paginate else result


async def get_template(template_id: str, *, actor, manage=False):
    from services.catalog_access import template_for
    return await template_for(actor, template_id, manage=manage)


# ─── Generate varian massal (cartesian) ──────────────────────────────────────

async def generate_variants(template_id: str, data: Dict[str, Any], *, actor, entity_id="") -> Dict[str, Any]:
    tpl = await db.product_templates.find_one({"id": template_id}, {"_id": 0})
    if not tpl:
        raise ValueError("Template tidak ditemukan")
    from services import catalog_rules, rnd_gate
    tpl['axes'] = catalog_rules.normalize_axes(tpl.get('axes') or [])
    from services.catalog_access import template_for
    from services.product_variant_service import family_lock, check_duplicate
    await template_for(actor, template_id, manage=True)
    if tpl.get('status') != 'active':
        raise ValueError("Induk sudah diarsipkan.")
    axes = _normalize_axes(data.get("axes") if data.get("axes") is not None else tpl.get("axes") or [])
    if {a['key'] for a in axes} != {a['key'] for a in tpl.get('axes', [])}:
        raise ValueError("Pilih semua jenis atribut yang didefinisikan induk.")
    allowed_axes = {a['key']: a for a in tpl.get('axes', [])}
    for a in axes:
        if any(o not in allowed_axes[a['key']]['options'] for o in a['options']):
            raise ValueError("Pilihan generator harus berasal dari induk yang tersimpan.")
    axis_lists = [(ax, ax["options"]) for ax in axes if ax.get("options")]
    if not axis_lists:
        raise ValueError("Minimal satu axis dengan opsi diperlukan untuk generate varian")
    base_price = catalog_rules.finite_number(data.get("base_price") if data.get("base_price") is not None
                       else tpl.get("base_price", 0) or 0, 'Harga dasar')
    prefix = (data.get("sku_prefix") or tpl.get("sku_prefix") or _prefix_from_name(tpl["name"])).strip().upper()
    combos = catalog_rules.combinations(axes)
    # INV-PERF-01 — hanya SKU kandidat yang dibaca, bukan seluruh katalog.
    candidate_skus = [(f"{prefix}-" + "-".join(o["code"] for o in combo)).upper() for combo in combos]
    existing = {p["sku"]: p for p in await db.products.find(
        {"sku": {"$in": candidate_skus}}, {"_id": 0, "sku": 1, "template_id": 1, "variant_options": 1}).to_list(len(candidate_skus))}
    lifecycle = await rnd_gate.default_new_lifecycle(entity_id)
    created: List[Dict[str, Any]] = []
    skipped: List[str] = []
    for combo in combos:
        codes, labels, attrs = [], [], {}
        color = tpl.get("color", "Natural")
        grade = tpl.get("grade", "A")
        color_code = ""
        color_hex = ""
        lebar = float(tpl.get("lebar", 0) or 0)
        for (ax, _), opt in zip(axis_lists, combo):
            codes.append(opt["code"])
            labels.append(opt["label"])
            key = ax["key"]
            attrs[key] = opt["label"]
            if key == "color":
                color = opt["label"]
                color_code = str(opt.get("value") or "").strip()   # M0 — axis color option.value = color_library.code
                color_hex = str(opt.get("hex") or "").strip()
            elif key == "grade":
                grade = opt["label"]
            elif key == "lebar":
                try:
                    lebar = float(opt.get("value") or opt["label"])
                except (TypeError, ValueError):
                    pass
        sku = (f"{prefix}-" + "-".join(codes)).upper()
        if sku in existing:
            old = existing[sku]
            expected = {a['key']: o['code'] for (a, _), o in zip(axis_lists, combo)}
            if old.get('template_id') == template_id and old.get('variant_options') == expected:
                skipped.append(sku)
                continue
            raise ValueError(f"SKU {sku} sudah digunakan. Ganti prefix/kode pilihan; tidak dilewati diam-diam.")
        prod = {
            "id": new_id("prod"), "sku": sku,
            "name": f"{tpl['name']} " + " ".join(labels),
            "category": tpl.get("category", "Kain"),
            "variant": " ".join(labels) or "Regular",
            "color": color, "motif": tpl.get("motif", "Polos"), "grade": grade,
            "color_code": color_code, "color_name": color if color_code else "", "color_hex": color_hex,
            "stage": tpl.get("stage", "finished"),
            # Fase A · PS-02/D-02 — varian WAJIB mewarisi jenis kain & atribut benang induk.
            "fabric_type": tpl.get("fabric_type", ""),
            "yarn_count": tpl.get("yarn_count", ""),
            "yarn_count_system": tpl.get("yarn_count_system", ""),
            "supplier": tpl.get("supplier", "Internal"),
            "base_unit": tpl.get("base_unit", "meter"),
            "price": round(base_price, 2), "harga_pokok": float(tpl.get("harga_pokok", 0) or 0),
            "gramasi": float(tpl.get("gramasi", 0) or 0), "lebar": lebar, "kg_per_meter": 0,
            "reorder_point": 0, "reorder_qty": 0,
            "image": tpl.get("image") or DEFAULT_IMAGE,
            "description": tpl.get("description") or "",
            "media": [], "media_revision": 0,
            "lifecycle": lifecycle,
            "line_code": tpl.get("line_code") or "",
            "exclusivity": tpl.get("exclusivity") or "umum",
            "owner_sales_ids": tpl.get("owner_sales_ids") or [],
            **{k: tpl.get(k, "") for k in base_fabric.FIELDS},
            "status": "active", "uom_conversions": [],
            "template_id": template_id, "variant_attrs": attrs,
            "template_name": tpl['name'], "catalog_version": 2,
            "variant_options": {a['key']: o['code'] for (a, _), o in zip(axis_lists, combo)},
            "batch_lot_rolls": [], "created_at": now_iso(), "updated_at": now_iso(),
        }
        # Fase A — varian yang dihasilkan WAJIB lulus validasi domain (tanpa ini,
        # generator bisa menyisipkan produk cacat yang menembus validasi router).
        catalog_rules.combination(tpl, prod)
        dr.apply_normalization(prod)
        vcheck = dr.validate_product(prod)
        if vcheck["errors"]:
            raise ValueError(f"Varian {sku} tidak sah: " + " ".join(vcheck["errors"]))
        prod["needs_review"] = vcheck["needs_review"]
        prod["needs_review_reasons"] = vcheck["needs_review_reasons"]
        existing[sku] = prod
        created.append(safe_doc(prod))
    # Validate the WHOLE batch before the first write. Family claim + compensation.
    from pymongo.errors import DuplicateKeyError
    from fastapi import HTTPException
    async with family_lock(template_id, 'generate_variants', actor.get('name', '')):
        current = await db.product_templates.find_one({'id': template_id}, {'_id': 0})
        if current.get('updated_at') != tpl.get('updated_at') or current.get('status') != 'active':
            raise HTTPException(409, 'Induk berubah. Muat ulang sebelum membuat varian.')
        for p in created:
            await check_duplicate(p)
        try:
            if created:
                await db.products.insert_many([dict(p) for p in created], ordered=True)
        except Exception as exc:
            try:
                await db.products.delete_many({'id': {'$in': [p['id'] for p in created]}})
            except Exception as rollback_error:
                from services import atomic_claim
                await atomic_claim.mark_failed('product_templates', template_id, str(rollback_error))
                raise
            if isinstance(exc, DuplicateKeyError):
                raise HTTPException(409, 'SKU/kombinasi sudah dibuat oleh proses lain. Muat ulang.') from exc
            raise
    return {"created": len(created), "skipped": len(skipped),
            "skipped_skus": skipped, "variants": created,
            "total_combinations": len(combos)}


# ─── Assign / detach produk existing ─────────────────────────────────────────

async def assign_products(template_id: str, product_ids: List[str]) -> Dict[str, Any]:
    tpl = await db.product_templates.find_one({"id": template_id}, {"_id": 0})
    if not tpl:
        raise ValueError("Template tidak ditemukan")
    from fastapi import HTTPException
    raise HTTPException(409, "Pemindahan massal tanpa pemetaan atribut dilarang. Gunakan Tautkan SKU lama pada induk tujuan dan pilih seluruh atribut.")


async def detach_products(product_ids: List[str]) -> Dict[str, Any]:
    from fastapi import HTTPException
    raise HTTPException(409, "Setiap SKU wajib memiliki induk. Pelepasan tanpa induk pengganti tidak diizinkan.")
