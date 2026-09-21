"""services/saga_lock_watch.py — PEMANTAU KUNCI SAGA MENGGANTUNG (T-01 Opsi B).

Klaim atomik (`atomic_claim.claim`) meninggalkan `saga_lock` bila proses mati di tengah.
Kunci itu TERLIHAT di panel Kunci Saga — tetapi hanya kalau admin kebetulan membukanya.
Job ini memindai koleksi induk yang dikunci; kunci yang umurnya melewati ambang
(`saga.stuck_lock_minutes`, bawaan 10 menit) diberitahukan ke admin lewat notifikasi
(`create_addressed(roles=("admin",))`, dedupe per hari per kunci). Job ini TIDAK melepas
kunci — keputusan itu tetap milik admin sesudah memeriksa data hilir.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from db import db
from routers.saga_locks import LOCKED_COLLECTIONS
from services.atomic_claim import LOCK
from services.config_resolver import value_of
from services.notification_service import create_addressed

DEFAULT_MINUTES = 10


async def threshold_minutes() -> float:
    try:
        return max(1.0, float(await value_of("saga.stuck_lock_minutes")))
    except Exception:  # noqa: BLE001 — setelan belum ada → bawaan
        return float(DEFAULT_MINUTES)


def age_minutes(started_at: Optional[str], now: datetime) -> float:
    try:
        t = datetime.fromisoformat(str(started_at).replace("Z", "+00:00"))
        if t.tzinfo is None:
            t = t.replace(tzinfo=timezone.utc)
        return max(0.0, (now - t).total_seconds() / 60)
    except Exception:  # noqa: BLE001 — started_at rusak → anggap sangat tua
        return 1e9


async def stuck_locks(minutes: Optional[float] = None) -> List[Dict[str, Any]]:
    amb = minutes if minutes is not None else await threshold_minutes()
    now = datetime.now(timezone.utc)
    out: List[Dict[str, Any]] = []
    for coll in LOCKED_COLLECTIONS:
        async for d in db[coll].find({LOCK: {"$exists": True}},
                                     {"_id": 0, "id": 1, "status": 1, "entity_id": 1, LOCK: 1}):
            lock = d.get(LOCK) or {}
            age = age_minutes(lock.get("started_at"), now)
            if age < amb:
                continue
            out.append({"collection": coll, "id": d.get("id"), "status": d.get("status"),
                        "entity_id": d.get("entity_id"), "action": lock.get("action"),
                        "by": lock.get("by"), "started_at": lock.get("started_at"),
                        "error": lock.get("error", ""), "age_minutes": round(age, 1)})
    return out


def _body(r: Dict[str, Any], amb: float) -> str:
    baris = [
        f"Dokumen: {r['collection']} / {r['id']} (status '{r.get('status') or '—'}')",
        f"Aksi: '{r.get('action')}' oleh {r.get('by') or '—'}, mulai {r.get('started_at')}",
        f"Umur kunci: {r['age_minutes']:g} menit (ambang {amb:g} menit).",
    ]
    if r.get("error"):
        baris.append(f"Alasan gagal tercatat: {r['error']}")
    else:
        baris.append("Tidak ada alasan gagal tercatat — proses kemungkinan mati di tengah.")
    baris.append("Periksa data hilir (roll, jurnal, tugas) lalu lepas kunci lewat "
                 "Pusat Pengaturan → Kunci Saga. Aksi ulang atas dokumen ini ditolak 409 sampai kunci dilepas.")
    return "\n".join(baris)


async def scan() -> Dict[str, Any]:
    amb = await threshold_minutes()
    rows = await stuck_locks(amb)
    created = 0
    for r in rows:
        notes = await create_addressed(
            roles=("admin",), notif_type="saga_lock_stuck",
            ref=f"saga_lock:{r['collection']}:{r['id']}",
            title=f"Kunci saga menggantung {r['age_minutes']:g} menit — {r['collection']} {r['id']}",
            body=_body(r, amb), severity="critical" if r.get("error") else "warning",
            link="settings-config", entity_id=r.get("entity_id"), dedupe_scope="day")
        r["notified"] = len(notes)
        created += len(notes)
    return {"scanned": len(LOCKED_COLLECTIONS), "stuck": len(rows), "created": created,
            "threshold_minutes": amb, "rows": rows}


async def job_saga_lock_watch() -> Dict[str, Any]:
    res = await scan()
    detail = (f"{res['stuck']} kunci saga menggantung > {res['threshold_minutes']:g} menit"
              if res["stuck"] else "tidak ada kunci saga menggantung")
    return {"scanned": res["scanned"], "created": res["created"], "detail": detail, "rows": res["rows"]}
