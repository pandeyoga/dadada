"""Demo: lengkapi induk "Endek Bali Rangrang" (ENK-BALI-003) → 4 varian warna + foto,
detail bahan, mockup & artwork (stok foto lokal di scripts/demo_media). Idempoten.
Jalankan: cd /app/backend && python ../scripts/seed_endek_showcase.py
"""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from dotenv import load_dotenv  # noqa: E402

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "backend", ".env"))
from db import db  # noqa: E402
from core_utils import new_id, now_iso  # noqa: E402
from services import catalog_rules  # noqa: E402
from services import product_media_service as media  # noqa: E402

MEDIA = Path(__file__).resolve().parent / "demo_media"
ACTOR = {"id": "system-seed", "name": "System Seed"}
COLORS = [  # (code axis, label, color_library code, hex, harga)
    ("UNGU-EMAS", "Ungu-Emas", "KN-PUR-01", "#5B2A6B", 320000),
    ("MERAH-MARUN", "Merah Marun", "KN-RED-01", "#7B1E22", 320000),
    ("KUNING-EMAS", "Kuning Emas", "KN-YLW-01", "#E4B429", 335000),
    ("HITAM-PEKAT", "Hitam Pekat", "KN-BLK-01", "#1A1A1A", 345000),
]
# per kode warna: [(file, kind, filename tampil)]
SHOTS = {
    "UNGU-EMAS": [("photo-1749367288395-f874bb54bc8a.jpg", "photo", "endek-rangrang-ungu-emas-flatlay.jpg"),
                  ("photo-1784295039401-2225df40ee7c.jpg", "detail", "detail-tenun-rangrang-ungu.jpg"),
                  ("photo-1758169744470-097641049fb7.jpg", "mockup", "mockup-kebaya-endek-ungu.jpg"),
                  ("photo-1762111908757-2444be02131d.jpg", "artwork", "artwork-rangrang-ungu-emas-v3.jpg")],
    "MERAH-MARUN": [("photo-1748141951488-9c9fb9603daf.jpg", "photo", "endek-rangrang-merah-marun.jpg"),
                    ("photo-1774679817333-decf0d988dd5.jpg", "detail", "detail-gulungan-merah.jpg"),
                    ("photo-1768478701502-c6b378f85167.jpg", "mockup", "mockup-kemeja-endek-merah.jpg"),
                    ("photo-1761516126097-98d996214b75.jpg", "artwork", "artwork-rangrang-merah-v2.jpg")],
    "KUNING-EMAS": [("photo-1762111067760-1f0fc2aa2866.jpg", "photo", "endek-rangrang-kuning-emas.jpg"),
                    ("photo-1768478701507-24b1c8de2df0.jpg", "mockup", "mockup-tunik-endek-kuning.jpg")],
    "HITAM-PEKAT": [("photo-1784295039401-2225df40ee7c.jpg", "photo", "endek-rangrang-hitam-pekat.jpg"),
                    ("photo-1762111908757-2444be02131d.jpg", "artwork", "artwork-rangrang-hitam-v1.jpg")],
}


async def main() -> None:
    tpl = await db.product_templates.find_one({"sku_prefix": "ENK-BALI-003"}, {"_id": 0})
    if not tpl:
        print("template ENK-BALI-003 tidak ditemukan — jalankan seed_realistic dulu")
        return
    axes = [{"key": "color", "label": "Warna", "options": [
        {"code": c, "label": lbl, "value": lib, "hex": hx} for c, lbl, lib, hx, _ in COLORS]}]
    await db.product_templates.update_one({"id": tpl["id"]}, {"$set": {
        "axes": axes, "legacy_parent": False, "updated_at": now_iso(),
        "description": tpl.get("description") or "",
        "image": "https://images.unsplash.com/photo-1749367288395-f874bb54bc8a?w=1200&q=80&fm=jpg"}})
    tpl["axes"] = axes
    base = await db.products.find_one({"sku": "ENK-BALI-003"}, {"_id": 0})
    for i, (code, label, lib, hx, price) in enumerate(COLORS):
        sku = "ENK-BALI-003" if i == 0 else f"ENK-BALI-003-{code}"
        prod = await db.products.find_one({"sku": sku}, {"_id": 0})
        if not prod:
            prod = {**base, "id": new_id("prod"), "sku": sku, "price": price, "media": [], "media_revision": 0,
                    "cover_media_id": "", "batch_lot_rolls": [], "uom_conversions": [],
                    "name": f"Endek Bali Rangrang {label}", "variant": label,
                    "created_at": now_iso(), "updated_at": now_iso()}
            prod.pop("legacy_image", None)
        prod["variant_attrs"] = {"color": label}
        prod["variant_options"] = {"color": code}
        catalog_rules.combination(tpl, prod)
        prod["image"] = prod.get("legacy_image") or prod.get("image") or tpl.get("image")
        await db.products.update_one({"id": prod["id"]}, {"$set": prod}, upsert=True)
        prod = await db.products.find_one({"id": prod["id"]}, {"_id": 0})
        if any(not m.get("deleted") for m in prod.get("media") or []):
            continue
        for fname, kind, shown in SHOTS[code]:
            data = (MEDIA / fname).read_bytes()
            await media.store(prod, data, shown, kind, ACTOR, source={"type": "seed_demo"})
            prod = await db.products.find_one({"id": prod["id"]}, {"_id": 0})
        rows = [{**m, "status": "approved", "reviewed_by": ACTOR["id"], "reviewed_at": now_iso()}
                for m in prod["media"]]
        cover = next(m["id"] for m in rows if m["kind"] == "photo")
        await media.save_media(prod, rows, cover_id=cover)
        print(f"{sku}: {len(rows)} media disetujui, cover {cover}")
    n = await db.products.count_documents({"template_id": tpl["id"]})
    print(f"Endek Bali Rangrang: {n} varian siap")


asyncio.run(main())
