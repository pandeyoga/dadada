"""Seed demo HOLD & label proofing Design Studio (idempoten).

- SRI-BGA-AO-002 (dsgn_7eec40ef4396) ← spesifikasi KSC/SPEC-00001 (approved, produk lahir) → "Sudah jadi master produk"
- KSC/SMP-00002 (proofing DWI-GEN-002) ditandai JADI → "Proofing selesai"
- SRI-BGA-AO-001 (dsgn_87a63c89bc80) di-HOLD oleh Budi Santoso; SMP-00005 tetap berjalan.
Jalankan: cd /app/backend && python ../scripts/seed_design_hold_proofing_demo.py
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from dotenv import load_dotenv  # noqa: E402

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "backend", ".env"))
from db import db  # noqa: E402
from core_utils import now_iso  # noqa: E402
from services import design_studio_service as studio  # noqa: E402

ADMIN = {"name": "Budi Santoso", "id": "user_admin_01", "role": "admin"}


async def main():
    spec = await db.md_specs.find_one({"number": "KSC/SPEC-00001"}, {"_id": 0})
    master_design = await db.design_gallery.find_one({"code": "SRI-BGA-AO-002"}, {"_id": 0})
    if spec and master_design and spec.get("design_id") != master_design["id"]:
        await db.md_specs.update_one({"id": spec["id"]}, {"$set": {
            "design_id": master_design["id"], "design_code": master_design["code"],
            "design_title": master_design.get("title", ""), "design_version": master_design.get("version", 1)}})
        prod = await db.products.find_one({"id": spec.get("product_id")}, {"_id": 0, "sku": 1, "name": 1}) or {}
        await studio.log_external(master_design["id"], ADMIN, "spec_linked",
                                  f"Spesifikasi {spec['number']} — {spec.get('title', '')} dibuat dengan desain ini",
                                  spec_id=spec["id"], spec_number=spec["number"])
        await studio.log_external(master_design["id"], ADMIN, "master_product_created",
                                  f"Spesifikasi {spec['number']} disetujui → master produk {prod.get('sku', '')} — {prod.get('name', '')} lahir",
                                  spec_id=spec["id"], spec_number=spec["number"], product_id=spec.get("product_id", ""),
                                  product_sku=prod.get("sku", ""), product_name=prod.get("name", ""))
        print("master:", master_design["code"], "←", spec["number"], prod.get("sku"))

    smp = await db.md_samples.find_one({"number": "KSC/SMP-00002"}, {"_id": 0})
    if smp and not smp.get("finished_at"):
        rounds = list(smp.get("rounds") or [])
        if rounds:
            rounds[0]["result"] = "acc"
            rounds[0]["status"] = "assessed"
        await db.md_samples.update_one({"id": smp["id"]}, {"$set": {
            "rounds": rounds, "status": "assessed", "finished_at": now_iso()[:10], "finished_by": ADMIN["name"],
            "finish_note": "Demo: proofing selesai", "updated_at": now_iso()}})
        if smp.get("design_id"):
            await studio.log_external(smp["design_id"], ADMIN, "proofing_finished",
                                      f"{smp['number']} ditandai JADI ({now_iso()[:10]}) — Demo: proofing selesai",
                                      sample_id=smp["id"], sample_number=smp["number"], sample_status="assessed")
        print("finished:", smp["number"])

    hold_design = await db.design_gallery.find_one({"code": "SRI-BGA-AO-001"}, {"_id": 0})
    if hold_design and not hold_design.get("on_hold") and hold_design.get("status") in studio.HOLDABLE:
        await studio.set_hold(hold_design["id"], ADMIN, True, "Demo: menunggu keputusan MD soal bahan dasar")
        print("hold:", hold_design["code"])
    print("selesai.")


asyncio.run(main())
