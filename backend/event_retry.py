"""Percobaan ulang terkendali + pemrosesan ulang event pembukuan yang gagal (audit GL-09).

Sebelumnya dispatcher mencoba sebuah event 3 kali berturut-turut (tiap tick 8 dtk) lalu menandainya
`failed` SELAMANYA: tidak ada jadwal ulang, tidak ada cara memprosesnya lagi selain mengedit database,
dan endpoint yang menerbitkannya tetap menjawab sukses sehingga layar tidak tahu jurnalnya tidak
pernah terbit (tagihan "disetujui" tanpa jurnal 2-1100).

Sekarang:
  * gagal → dicoba lagi dengan jeda yang makin panjang (`BACKOFF`), total `MAX_ATTEMPTS` percobaan —
    gangguan sementara (basis data sibuk, antrean rekening) pulih sendiri;
  * tetap gagal → `failed` TERLIHAT (banner tie-out, /api/health, daftar `GET /finance/events/failed`)
    dan bisa diproses ulang orang berwenang (`finance:approve`) setelah penyebabnya dibetulkan;
  * pemrosesan ulang aman: handler GL idempoten lewat `source_event` yang dijaga indeks unik, jadi
    jurnal yang sudah terbit TIDAK diubah/digandakan; yang diulang hanya langkah yang belum terjadi.

Jeda dapat diatur lewat env `EVENT_RETRY_BACKOFF` (detik, dipisah koma; bawaan "30,120,600,1800").
"""
import os
from datetime import datetime, timedelta, timezone

from core_utils import now_iso


def _backoff() -> tuple:
    raw = os.environ.get("EVENT_RETRY_BACKOFF", "30,120,600,1800")
    try:
        vals = tuple(max(0, int(x)) for x in raw.split(",") if x.strip() != "")
    except ValueError:
        vals = ()
    return vals or (30, 120, 600, 1800)


BACKOFF = _backoff()           # jeda (detik) sebelum percobaan ke-2, ke-3, ...
MAX_ATTEMPTS = len(BACKOFF) + 1  # percobaan pertama langsung (saat emit / tick)


def due_filter(now: str) -> dict:
    """Syarat klaim: event belum dijadwalkan ulang, atau jadwal ulangnya sudah tiba."""
    return {"$or": [{"next_retry_at": None}, {"next_retry_at": {"$lte": now}}]}


def failure_set(ev: dict, error) -> dict:
    """Nilai `$set` untuk event yang barusan gagal (pemanggil juga melakukan `$inc retries`)."""
    retries = int(ev.get("retries", 0) or 0) + 1
    out = {"last_error": str(error)[:500], "last_failed_at": now_iso()}
    if retries >= MAX_ATTEMPTS:
        out.update({"status": "failed", "failed_at": now_iso(), "next_retry_at": None})
    else:
        wait = BACKOFF[min(retries - 1, len(BACKOFF) - 1)]
        out.update({"status": "pending",
                    "next_retry_at": (datetime.now(timezone.utc) + timedelta(seconds=wait)).isoformat()})
    return out


async def health_counts() -> dict:
    """Penanda untuk /api/health: event gagal permanen & event yang menunggu percobaan ulang."""
    from db import db
    return {
        "events_failed": await db.events.count_documents({"status": "failed"}),
        "events_retrying": await db.events.count_documents(
            {"status": "pending", "next_retry_at": {"$ne": None}}),
        "event_retry_backoff": list(BACKOFF),
    }


async def list_problems(org: str, status: str = "failed", limit: int = 100) -> list:
    """Event yang butuh perhatian: `failed` (permanen), `retrying` (menunggu jadwal ulang) atau `all`."""
    from db import db
    q = {"org_id": org}
    retrying = {"status": "pending", "next_retry_at": {"$ne": None}}
    q.update({"failed": {"status": "failed"}, "retrying": retrying}.get(status)
             or {"$or": [{"status": "failed"}, retrying]})
    return await db.events.find(q, {"_id": 0, "id": 1, "type": 1, "entity_type": 1, "entity_id": 1,
                                    "status": 1, "last_error": 1, "retries": 1, "failed_at": 1,
                                    "next_retry_at": 1, "created_at": 1, "requeued_by": 1,
                                    "requeued_at": 1}) \
        .sort("created_at", 1).to_list(max(1, min(int(limit or 100), 500)))


async def requeue(org: str, event_id: str, actor: str) -> dict:
    """Proses ulang SEKARANG satu event `failed` (atau yang menunggu jadwal ulang). CAS atas status:
    dua orang menekan bersamaan = satu pemrosesan ulang. Jurnal yang sudah ada tidak disentuh."""
    from db import db
    ts = now_iso()
    res = await db.events.find_one_and_update(
        {"id": event_id, "org_id": org,
         "$or": [{"status": "failed"}, {"status": "pending", "next_retry_at": {"$ne": None}}]},
        {"$set": {"status": "pending", "retries": 0, "next_retry_at": None, "requeued_by": actor,
                  "requeued_at": ts},
         "$push": {"requeue_log": {"at": ts, "by": actor}}},
        projection={"_id": 0, "id": 1, "type": 1})
    if not res:
        cur = await db.events.find_one({"id": event_id, "org_id": org}, {"_id": 0, "status": 1})
        if not cur:
            raise ValueError("Event tidak ditemukan.")
        raise ValueError(f"Event berstatus '{cur['status']}' — hanya event gagal/menunggu jadwal ulang "
                         "yang bisa diproses ulang.")
    return res
