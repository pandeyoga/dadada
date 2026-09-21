"""Demo: tambah versi desain yang DINILAI (0–2) beberapa bulan ke belakang pada
design_gallery hasil seed, supaya Tren Nilai Desain & bobot grade punya data.
Idempoten: hanya menyentuh desain seed yang versinya masih 1 tanpa nilai.
Jalankan: cd /app/backend && python ../scripts/seed_design_scores_demo.py
"""
import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from dotenv import load_dotenv  # noqa: E402

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "backend", ".env"))
from db import db  # noqa: E402

# (created_by, nilai per versi urut dari lama → baru); ACC bila ≥ 1,5
PLAN = {
    "Dewi Lestari": [0.75, 1.25, 1.5, 1.75],
    "Desainer Demo": [1.0, 1.25, 1.75],
    "Bagas Nugroho": [0.5, 1.0, 1.25],
}


def iso(d: datetime) -> str:
    return d.isoformat()


async def main() -> None:
    now = datetime.now(timezone.utc)
    touched = 0
    for who, scores in PLAN.items():
        docs = await db.design_gallery.find({"created_by": who}).to_list(10)
        if not docs:
            # desainer tanpa desain seed → salin satu desain milik seed lain sebagai karyanya
            base = await db.design_gallery.find_one({"created_by": "system-seed"}, {"_id": 0})
            if not base:
                continue
            base = {**base, "id": f"dsgn_demo_{who.split()[0].lower()}", "created_by": who,
                    "code": f"{who[:3].upper()}-MTF-GEN-090", "title": f"{base.get('title', 'Desain')} — {who}",
                    "files": [], "colorways": [], "feedback": []}
            await db.design_gallery.update_one({"id": base["id"]}, {"$setOnInsert": base}, upsert=True)
            docs = [await db.design_gallery.find_one({"id": base["id"]})]
        d = docs[0]
        vers = d.get("versions") or []
        if len(vers) > 1 or (vers and vers[0].get("score") is not None):
            continue
        versions, timeline = [], list(d.get("timeline") or [])
        n = len(scores)
        for i, s in enumerate(scores):
            at = now - timedelta(days=30 * (n - 1 - i) + 3)
            scored_at = at + timedelta(days=2)
            acc = s >= 1.5
            versions.append({"version": i + 1, "note": "Versi awal" if i == 0 else f"Revisi ke-{i}",
                             "at": iso(at), "by": who, "files": [], "score": s,
                             "score_by": "Admin Demo", "score_at": iso(scored_at), "acc": acc,
                             "score_history": [{"score": s, "by": "Admin Demo", "at": iso(scored_at), "note": ""}]})
            timeline.append({"id": f"evt_demo_{d['id']}_{i}", "at": iso(scored_at), "by": "Admin Demo",
                             "user_id": "", "role": "admin", "event": "approve" if acc else "request_revision",
                             "note": f"Nilai {s}", "version": i + 1,
                             "to_status": "approved" if acc else "revision"})
        status = "approved" if scores[-1] >= 1.5 else "revision"
        await db.design_gallery.update_one({"id": d["id"]}, {"$set": {
            "versions": versions, "version": n, "status": status, "timeline": timeline,
            "score": scores[-1], "updated_at": iso(now)}})
        touched += 1
    print(f"design_gallery demo scores: {touched} desain diperbarui")


asyncio.run(main())
