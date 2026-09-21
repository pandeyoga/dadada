"""Sesi 15 — label tertahan: antrean label menunggu > N menit tanpa printer online di gudang itu.

Kepala gudang (warehouse_admin) + manager entitas diberi tahu; satu notifikasi per gudang
selama antrean belum bersih (dedupe ref `printer_stuck:<wh>` scope unread).
"""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from db import db
from core_utils import now_iso
from services.notification_service import create_notification

STUCK_MINUTES = 30
HEARTBEAT_MINUTES = 5


async def scan(stuck_minutes: int = STUCK_MINUTES) -> Dict[str, Any]:
    now = datetime.now(timezone.utc)
    hb_cutoff = (now - timedelta(minutes=HEARTBEAT_MINUTES)).isoformat()
    age_cutoff = (now - timedelta(minutes=stuck_minutes)).isoformat()
    online_wh = {d["warehouse_id"] for d in await db.rfid_devices.find(
        {"type": "printer", "last_heartbeat": {"$gte": hb_cutoff}}, {"_id": 0, "warehouse_id": 1}).to_list(500)}
    pipeline = [
        {"$match": {"status": "queued", "created_at": {"$lte": age_cutoff}}},
        {"$group": {"_id": "$warehouse_id", "labels": {"$sum": "$item_count"}, "jobs": {"$sum": 1},
                    "oldest": {"$min": "$created_at"}, "entity_id": {"$first": "$owner_entity_id"},
                    "warehouse_name": {"$first": "$warehouse_name"}}},
    ]
    rows = await db.rfid_print_jobs.aggregate(pipeline).to_list(500)
    notified = 0
    stuck = []
    for r in rows:
        wh = r["_id"]
        if wh in online_wh:
            continue
        age_min = int((now - datetime.fromisoformat(r["oldest"])).total_seconds() // 60)
        stuck.append({"warehouse_id": wh, "labels": r["labels"], "jobs": r["jobs"], "age_minutes": age_min})
        n = await create_notification(
            notif_type="printer_stuck", ref=f"printer_stuck:{wh}",
            title=f"Label tertahan di {r.get('warehouse_name') or wh}",
            body=(f"{r['labels']} label ({r['jobs']} job) menunggu {age_min} menit tanpa printer online. "
                  f"Nyalakan/cek printer label gudang atau cetak lewat browser."),
            severity="warning", link="operations", entity_id=r.get("entity_id"),
            recipient_role="warehouse_admin", dedupe=True, dedupe_scope="unread")
        if n:
            notified += 1
            await create_notification(
                notif_type="printer_stuck", ref=f"printer_stuck:{wh}:manager",
                title=f"Label tertahan di {r.get('warehouse_name') or wh}",
                body=f"{r['labels']} label menunggu {age_min} menit; printer gudang offline.",
                severity="warning", link="operations", entity_id=r.get("entity_id"),
                recipient_role="manager", dedupe=True, dedupe_scope="unread")
    return {"checked_at": now_iso(), "stuck": stuck, "notified": notified, "threshold_minutes": stuck_minutes}


async def job_printer_stuck_watch() -> Dict[str, Any]:
    res = await scan()
    detail = (f"{len(res['stuck'])} gudang label tertahan > {res['threshold_minutes']} menit"
              if res["stuck"] else "tidak ada label tertahan")
    return {"ok": True, "detail": detail, **res}
