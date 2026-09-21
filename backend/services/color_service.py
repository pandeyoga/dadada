"""M0 — Color Library service (Pantone-style master warna).

Koleksi `color_library` (prefix `col_`) = master warna internal bergaya Pantone
(code/name/hex/system/family). SHARED lintas-entitas (seperti products).
Dipakai lintas menu (Master Produk, Template Varian, POS, Special Order, Makloon).

Backward-compat: produk lama pakai `color` teks bebas; color_code opsional.
"""
import re
from typing import Any, Dict, List, Optional

from db import db
from core_utils import new_id, now_iso, safe_doc

PREFIX = "col"
VALID_SYSTEMS = {"TPX", "TCX", "C", "U", "KN"}

_HEX_RE = re.compile(r"^#?([0-9a-fA-F]{6})$")


def normalize_hex(value: str) -> Optional[str]:
    """Normalisasi '#rrggbb' → 'RRGGBB' (uppercase, tanpa #). None bila invalid."""
    if not value:
        return None
    m = _HEX_RE.match(str(value).strip())
    if not m:
        return None
    return m.group(1).upper()


def hex_to_rgb(value: str) -> Optional[tuple]:
    h = normalize_hex(value)
    if not h:
        return None
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def color_distance(rgb1: tuple, rgb2: tuple) -> float:
    """Jarak warna 'redmean' (aproksimasi perseptual sederhana, tanpa dependency).

    Lebih baik dari Euclidean RGB polos untuk mendekati persepsi mata manusia.
    """
    r1, g1, b1 = rgb1
    r2, g2, b2 = rgb2
    rmean = (r1 + r2) / 2.0
    dr, dg, db_ = r1 - r2, g1 - g2, b1 - b2
    return (
        (2 + rmean / 256) * dr * dr
        + 4 * dg * dg
        + (2 + (255 - rmean) / 256) * db_ * db_
    ) ** 0.5


# ─── CRUD ────────────────────────────────────────────────────────────────────

async def list_colors(q: str = "", family: str = "", system: str = "",
                      status: str = "active") -> List[Dict[str, Any]]:
    query: Dict[str, Any] = {}
    if status and status != "all":
        query["status"] = status
    if family:
        query["family"] = family
    if system:
        query["system"] = system
    rows = await db.color_library.find(query, {"_id": 0}).sort("code", 1).to_list(2000)
    if q:
        s = q.lower()
        rows = [r for r in rows
                if s in f"{r.get('code','')}{r.get('name','')}{r.get('factory_name','')}{r.get('family','')}".lower()]
    # MD-06 lanjutan — putaran labdip yang LEWAT tanggal butuh per warna (lencana merah di kartu).
    today = now_iso()[:10]
    overdue: Dict[str, int] = {}
    async for smp in db.md_samples.find(
            {"color_target.color_id": {"$in": [r["id"] for r in rows]},
             "status": {"$nin": ["decided", "cancelled"]},
             "rounds": {"$elemMatch": {"result": {"$in": ["", None]}, "due_date": {"$gt": "", "$lt": today}}}},
            {"_id": 0, "color_target.color_id": 1, "rounds.result": 1, "rounds.due_date": 1}):
        cid = (smp.get("color_target") or {}).get("color_id", "")
        n = sum(1 for rd in smp.get("rounds") or []
                if not rd.get("result") and rd.get("due_date") and rd["due_date"] < today)
        if n:
            overdue[cid] = overdue.get(cid, 0) + n
    for r in rows:
        r["labdip_overdue_count"] = overdue.get(r["id"], 0)
    return [safe_doc(r) for r in rows]


async def create_color(data: Dict[str, Any], actor_name: str = "") -> Dict[str, Any]:
    code = (data.get("code") or "").strip().upper()
    name = (data.get("name") or "").strip()
    if not code:
        raise ValueError("Kode warna wajib diisi")
    if not name:
        raise ValueError("Nama warna wajib diisi")
    hex_norm = normalize_hex(data.get("hex") or "")
    if not hex_norm:
        raise ValueError("Hex warna tidak valid (harus 6 digit, mis. #1A2B3C)")
    if await db.color_library.find_one({"code": code}, {"_id": 0}):
        raise ValueError(f"Kode warna '{code}' sudah digunakan")
    system = (data.get("system") or "KN").strip().upper()
    if system not in VALID_SYSTEMS:
        system = "KN"
    doc = {
        "id": new_id(PREFIX),
        "code": code,
        "name": name,
        "factory_name": (data.get("factory_name") or "").strip(),
        "hex": f"#{hex_norm}",
        "system": system,
        "family": (data.get("family") or "").strip() or "Lainnya",
        "status": "active",
        "created_by": actor_name,
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    await db.color_library.insert_one(doc)
    return safe_doc(doc)


async def update_color(color_id: str, patch: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    upd: Dict[str, Any] = {}
    if patch.get("name") is not None:
        upd["name"] = str(patch["name"]).strip()
    if patch.get("factory_name") is not None:
        upd["factory_name"] = str(patch["factory_name"]).strip()
    if patch.get("hex") is not None:
        hex_norm = normalize_hex(patch["hex"])
        if not hex_norm:
            raise ValueError("Hex warna tidak valid")
        upd["hex"] = f"#{hex_norm}"
    if patch.get("family") is not None:
        upd["family"] = str(patch["family"]).strip() or "Lainnya"
    if patch.get("system") is not None:
        sysv = str(patch["system"]).strip().upper()
        upd["system"] = sysv if sysv in VALID_SYSTEMS else "KN"
    if patch.get("status") is not None:
        upd["status"] = str(patch["status"]).strip() or "active"
    if not upd:
        return safe_doc(await db.color_library.find_one({"id": color_id}, {"_id": 0}))
    upd["updated_at"] = now_iso()
    await db.color_library.update_one({"id": color_id}, {"$set": upd})
    return safe_doc(await db.color_library.find_one({"id": color_id}, {"_id": 0}))


async def delete_color(color_id: str) -> Dict[str, Any]:
    res = await db.color_library.update_one(
        {"id": color_id}, {"$set": {"status": "inactive", "updated_at": now_iso()}})
    if res.matched_count == 0:
        raise ValueError("Warna tidak ditemukan")
    return {"deleted": True, "id": color_id}


async def nearest(hex_value: str, limit: int = 8) -> Dict[str, Any]:
    """Cari warna terdekat by hex (ΔE redmean sederhana)."""
    target = hex_to_rgb(hex_value)
    if target is None:
        raise ValueError("Hex tidak valid (mis. #1A2B3C)")
    rows = await db.color_library.find(
        {"status": "active"}, {"_id": 0}).to_list(5000)
    scored = []
    for r in rows:
        rgb = hex_to_rgb(r.get("hex", ""))
        if rgb is None:
            continue
        d = color_distance(target, rgb)
        scored.append({**safe_doc(r), "distance": round(d, 2)})
    scored.sort(key=lambda x: x["distance"])
    top = scored[: max(1, min(limit, 24))]
    return {
        "query_hex": f"#{normalize_hex(hex_value)}",
        "nearest_id": top[0]["id"] if top else None,
        "results": top,
    }


# ── Keterkaitan warna internal ↔ versi supplier ↔ master produk ↔ sample R&D ────────────────
_COLOR_PROJ = {"_id": 0, "id": 1, "code": 1, "name": 1, "hex": 1, "family": 1, "system": 1, "status": 1,
               "factory_name": 1, "supplier_variants": 1}


async def _products_of_color(color_id: str) -> List[Dict[str, Any]]:
    """Produk master yang lahir dari spesifikasi ber-warna target ini (jalur utama R&D → produk)."""
    specs = await db.md_specs.find({"color_target.color_id": color_id, "product_id": {"$nin": ["", None]}},
                                   {"_id": 0, "id": 1, "number": 1, "product_id": 1, "status": 1}).to_list(500)
    by_pid = {s["product_id"]: s for s in specs}
    if not by_pid:
        return []
    prods = await db.products.find({"id": {"$in": list(by_pid)}},
                                   {"_id": 0, "id": 1, "sku": 1, "name": 1, "lifecycle": 1, "template_id": 1,
                                    "variant_attrs": 1, "is_active": 1}).to_list(500)
    tpl_ids = [p.get("template_id") for p in prods if p.get("template_id")]
    tpls = {t["id"]: t for t in await db.product_templates.find({"id": {"$in": tpl_ids}}, {"_id": 0, "id": 1, "name": 1}).to_list(200)} if tpl_ids else {}
    out = []
    for p in prods:
        s = by_pid.get(p["id"], {})
        out.append({"id": p["id"], "sku": p.get("sku", ""), "name": p.get("name", ""), "lifecycle": p.get("lifecycle", ""),
                    "variant_attrs": p.get("variant_attrs") or {}, "template_name": (tpls.get(p.get("template_id")) or {}).get("name", ""),
                    "spec_id": s.get("id", ""), "spec_number": s.get("number", ""), "via": "spesifikasi"})
    return out


async def _samples_of_color(color_id: str) -> List[Dict[str, Any]]:
    rows = await db.md_samples.find({"color_target.color_id": color_id},
                                     {"_id": 0, "id": 1, "number": 1, "title": 1, "status": 1, "sample_types": 1,
                                      "decision.supplier_id": 1, "decision.supplier_name": 1, "decision.supplier_color_name": 1,
                                      "decision.supplier_color_code": 1, "decision.decided_at": 1, "decision.product_sku": 1,
                                      "created_at": 1}).sort("created_at", -1).to_list(200)
    return [{"id": r["id"], "number": r.get("number", ""), "title": r.get("title", ""), "status": r.get("status", ""),
             "sample_types": r.get("sample_types") or [], "decision": r.get("decision") or {}, "created_at": r.get("created_at", "")}
            for r in rows]


async def color_links(color_id: str) -> Dict[str, Any]:
    color = await db.color_library.find_one({"id": color_id}, _COLOR_PROJ)
    if not color:
        raise ValueError("Warna tidak ditemukan.")
    products = await _products_of_color(color_id)
    samples = await _samples_of_color(color_id)
    # produk yang lahir dari sample pemenang supplier X → dilekatkan ke versi supplier X
    variants = []
    for v in color.get("supplier_variants") or []:
        smp = next((s for s in samples if s["id"] == v.get("sample_id")), None)
        prod_sku = ((smp or {}).get("decision") or {}).get("product_sku", "")
        variants.append({**v, "sample_status": (smp or {}).get("status", ""),
                         "products": [p for p in products if prod_sku and p["sku"] == prod_sku]})
    return {"color": {k: v for k, v in color.items() if k != "supplier_variants"}, "supplier_variants": variants,
            "products": products, "samples": samples}


async def list_supplier_variants() -> List[Dict[str, Any]]:
    """Daftar rata semua versi warna supplier — satu baris per (warna internal × supplier)."""
    cols = await db.color_library.find({"supplier_variants.0": {"$exists": True}}, _COLOR_PROJ).to_list(2000)
    out: List[Dict[str, Any]] = []
    for c in cols:
        prods = await _products_of_color(c["id"])
        smp_ids = [v.get("sample_id") for v in c.get("supplier_variants") or [] if v.get("sample_id")]
        smps = {s["id"]: s for s in await db.md_samples.find({"id": {"$in": smp_ids}}, {"_id": 0, "id": 1, "status": 1, "decision.product_sku": 1}).to_list(500)} if smp_ids else {}
        for v in c.get("supplier_variants") or []:
            smp = smps.get(v.get("sample_id"), {})
            sku = (smp.get("decision") or {}).get("product_sku", "")
            out.append({**v, "color_id": c["id"], "color_code": c.get("code", ""), "color_name": c.get("name", ""),
                        "hex": c.get("hex", ""), "family": c.get("family", ""), "color_status": c.get("status", ""),
                        "sample_status": smp.get("status", ""),
                        "products": [{"id": p["id"], "sku": p["sku"], "name": p["name"], "lifecycle": p["lifecycle"]} for p in prods if sku and p["sku"] == sku],
                        "color_products_count": len(prods)})
    out.sort(key=lambda r: r.get("at", ""), reverse=True)
    return out


async def sync_product_colors(product_id: str) -> Optional[Dict[str, Any]]:
    """Denormalisasi 'dua warna' ke master produk: warna internal (color_ref), versi warna supplier
    (supplier_colors, dilabeli supplier) & supplier pemenang R&D (rnd_supplier) — dibaca semua menu
    (MD, Pembelian RFQ/PO, pemilih produk, katalog) tanpa join."""
    prod = await db.products.find_one({"id": product_id}, {"_id": 0, "id": 1, "sku": 1})
    if not prod:
        return None
    spec = await db.md_specs.find_one({"product_id": product_id}, {"_id": 0, "id": 1, "number": 1, "color_target": 1, "sample_ids": 1})
    color_id = ((spec or {}).get("color_target") or {}).get("color_id") or ""
    patch: Dict[str, Any] = {"color_ref": None, "supplier_colors": [], "rnd_supplier": None,
                             "rnd_spec_number": (spec or {}).get("number", "")}
    if color_id:
        col = await db.color_library.find_one({"id": color_id}, _COLOR_PROJ)
        if col:
            patch["color_ref"] = {"id": col["id"], "code": col.get("code", ""), "name": col.get("name", ""),
                                  "hex": col.get("hex", ""), "factory_name": col.get("factory_name", "")}
            patch["supplier_colors"] = [{"supplier_id": v.get("supplier_id", ""), "supplier_name": v.get("supplier_name", ""),
                                         "supplier_color_name": v.get("supplier_color_name", ""),
                                         "supplier_color_code": v.get("supplier_color_code", ""),
                                         "sample_number": v.get("sample_number", ""), "at": v.get("at", "")}
                                        for v in (col.get("supplier_variants") or [])]
    smp = await db.md_samples.find_one({"$or": [{"decision.product_id": product_id}, {"decision.product_sku": prod.get("sku", "")},
                                                 {"spec_id": (spec or {}).get("id", "-"), "status": "decided"}]},
                                       {"_id": 0, "number": 1, "decision": 1}, sort=[("decision.decided_at", -1)])
    dec = (smp or {}).get("decision") or {}
    if dec.get("supplier_id"):
        patch["rnd_supplier"] = {"id": dec["supplier_id"], "name": dec.get("supplier_name", ""), "sample_number": (smp or {}).get("number", ""),
                                 "supplier_color_name": dec.get("supplier_color_name", ""), "supplier_color_code": dec.get("supplier_color_code", ""),
                                 "contract_number": dec.get("contract_number", ""), "price": dec.get("price")}
        # versi warna pemenang ditaruh paling depan
        patch["supplier_colors"].sort(key=lambda v: 0 if v["supplier_id"] == dec["supplier_id"] else 1)
    await db.products.update_one({"id": product_id}, {"$set": patch})
    return patch


async def backfill_product_colors() -> int:
    ids = {s["product_id"] async for s in db.md_specs.find({"product_id": {"$nin": ["", None]}}, {"_id": 0, "product_id": 1})}
    n = 0
    for pid in ids:
        if await sync_product_colors(pid):
            n += 1
    return n
