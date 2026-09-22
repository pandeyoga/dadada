"""
marketing_service.py — Sosial Media & Konten: kampanye, kalender/perencana post, lampiran,
performa manual, dan pengingat tayang ke PIC (in-app + WA lewat pipeline notifikasi).
Alur status post: idea → draft → review → approved → scheduled → published (+ cancelled).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from db import db
from core_utils import new_id, now_iso
from services import storage_service as storage

PLATFORMS = [
    {"code": "instagram", "label": "Instagram", "color": "#C13584"},
    {"code": "tiktok", "label": "TikTok", "color": "#111111"},
    {"code": "facebook", "label": "Facebook", "color": "#1877F2"},
    {"code": "whatsapp", "label": "WhatsApp Status", "color": "#25D366"},
    {"code": "shopee", "label": "Shopee", "color": "#EE4D2D"},
    {"code": "youtube", "label": "YouTube", "color": "#FF0000"},
]
CONTENT_TYPES = ["foto", "carousel", "reels", "video", "story", "live", "artikel"]
STATUSES = [
    {"code": "idea", "label": "Ide"}, {"code": "draft", "label": "Draf"}, {"code": "review", "label": "Tinjauan"},
    {"code": "approved", "label": "Disetujui"}, {"code": "scheduled", "label": "Terjadwal"},
    {"code": "published", "label": "Tayang"}, {"code": "cancelled", "label": "Batal"},
]
TRANSITIONS = {
    "idea": {"draft", "cancelled"}, "draft": {"review", "cancelled", "idea"}, "review": {"approved", "draft", "cancelled"},
    "approved": {"scheduled", "draft", "cancelled"}, "scheduled": {"published", "approved", "cancelled"},
    "published": set(), "cancelled": {"idea"},
}
APPROVE_ROLES = {"admin", "manager"}
METRIC_FIELDS = ["likes", "comments", "shares", "saves", "reach", "impressions", "clicks", "followers_gained", "sales_leads"]
REMINDER_WINDOW_MIN = 60
WIB = timezone(timedelta(hours=7))


class MarketingError(ValueError):
    pass


def meta() -> Dict[str, Any]:
    return {"platforms": PLATFORMS, "content_types": CONTENT_TYPES, "statuses": STATUSES,
            "transitions": {k: sorted(v) for k, v in TRANSITIONS.items()}, "metric_fields": METRIC_FIELDS}


def _hashtags(raw: Any) -> List[str]:
    if isinstance(raw, list):
        items = raw
    else:
        items = str(raw or "").replace(",", " ").split()
    out: List[str] = []
    for t in items:
        t = str(t).strip().lstrip("#")
        if t and t.lower() not in [o.lower() for o in out]:
            out.append(t)
    return out[:30]


async def _campaign_name(campaign_id: str) -> str:
    if not campaign_id:
        return ""
    c = await db.mkt_campaigns.find_one({"id": campaign_id}, {"_id": 0, "name": 1})
    return (c or {}).get("name", "")


# ─── Kampanye ────────────────────────────────────────────────────────────────
async def create_campaign(payload: Dict[str, Any], *, entity_id: str, actor: Dict[str, Any]) -> Dict[str, Any]:
    name = (payload.get("name") or "").strip()
    if not name:
        raise MarketingError("Nama kampanye wajib diisi.")
    doc = {
        "id": new_id("mkc"), "entity_id": entity_id, "name": name, "theme": (payload.get("theme") or "").strip(),
        "goal": (payload.get("goal") or "").strip(), "start_date": (payload.get("start_date") or "")[:10],
        "end_date": (payload.get("end_date") or "")[:10], "platforms": [p for p in (payload.get("platforms") or []) if p],
        "budget": float(payload.get("budget") or 0), "color": payload.get("color") or "#0058CC",
        "status": "active", "notes": (payload.get("notes") or "").strip(),
        "created_by": actor.get("name", ""), "created_at": now_iso(), "updated_at": now_iso(),
    }
    if doc["start_date"] and doc["end_date"] and doc["end_date"] < doc["start_date"]:
        raise MarketingError("Tanggal selesai kampanye tidak boleh sebelum tanggal mulai.")
    await db.mkt_campaigns.insert_one(dict(doc))
    return doc


async def update_campaign(cid: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    allowed = ("name", "theme", "goal", "start_date", "end_date", "platforms", "budget", "color", "status", "notes")
    sets = {k: payload[k] for k in allowed if k in payload}
    if "name" in sets and not str(sets["name"]).strip():
        raise MarketingError("Nama kampanye wajib diisi.")
    if "budget" in sets:
        sets["budget"] = float(sets["budget"] or 0)
    sets["updated_at"] = now_iso()
    await db.mkt_campaigns.update_one({"id": cid}, {"$set": sets})
    if "name" in sets:
        await db.mkt_posts.update_many({"campaign_id": cid}, {"$set": {"campaign_name": sets["name"]}})
    return await db.mkt_campaigns.find_one({"id": cid}, {"_id": 0})


async def list_campaigns(scope: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = await db.mkt_campaigns.find(scope, {"_id": 0}).sort("start_date", -1).to_list(300)
    for c in rows:
        agg = await db.mkt_posts.aggregate([
            {"$match": {"campaign_id": c["id"], "status": {"$ne": "cancelled"}}},
            {"$group": {"_id": "$status", "n": {"$sum": 1},
                        "reach": {"$sum": {"$ifNull": ["$metrics.reach", 0]}},
                        "eng": {"$sum": {"$add": [{"$ifNull": ["$metrics.likes", 0]}, {"$ifNull": ["$metrics.comments", 0]},
                                                  {"$ifNull": ["$metrics.shares", 0]}, {"$ifNull": ["$metrics.saves", 0]}]}}}}]).to_list(20)
        c["post_counts"] = {a["_id"]: a["n"] for a in agg}
        c["posts_total"] = sum(a["n"] for a in agg)
        c["reach_total"] = sum(a["reach"] for a in agg)
        c["engagement_total"] = sum(a["eng"] for a in agg)
    return rows


# ─── Post ────────────────────────────────────────────────────────────────────
def _validate_post(p: Dict[str, Any]) -> None:
    if not (p.get("title") or "").strip():
        raise MarketingError("Judul konten wajib diisi.")
    if not p.get("platforms"):
        raise MarketingError("Pilih minimal satu platform.")
    bad = [x for x in p["platforms"] if x not in {pl["code"] for pl in PLATFORMS}]
    if bad:
        raise MarketingError(f"Platform tidak dikenal: {', '.join(bad)}")
    if p.get("content_type") and p["content_type"] not in CONTENT_TYPES:
        raise MarketingError("Jenis konten tidak dikenal.")


async def create_post(payload: Dict[str, Any], *, entity_id: str, actor: Dict[str, Any]) -> Dict[str, Any]:
    p = {
        "title": (payload.get("title") or "").strip(), "caption": (payload.get("caption") or "").strip(),
        "hashtags": _hashtags(payload.get("hashtags")), "platforms": [x for x in (payload.get("platforms") or []) if x],
        "content_type": payload.get("content_type") or "foto", "publish_at": (payload.get("publish_at") or "").strip(),
        "campaign_id": payload.get("campaign_id") or "", "pic_user_id": payload.get("pic_user_id") or "",
        "pic_name": (payload.get("pic_name") or "").strip(), "cta": (payload.get("cta") or "").strip(),
        "notes": (payload.get("notes") or "").strip(), "assets": _assets(payload.get("assets")),
    }
    _validate_post(p)
    from services import marketing_ext as ext
    p["accounts"] = await ext.snapshot_accounts([a for a in (payload.get("account_ids") or []) if a], entity_id, p["platforms"])
    if p["pic_user_id"] and not p["pic_name"]:
        u = await db.users.find_one({"id": p["pic_user_id"]}, {"_id": 0, "name": 1})
        p["pic_name"] = (u or {}).get("name", "")
    doc = {**p, "id": new_id("mkp"), "entity_id": entity_id, "campaign_name": await _campaign_name(p["campaign_id"]),
           "status": payload.get("status") if payload.get("status") in ("idea", "draft") else "idea",
           "attachments": [], "metrics": {}, "metrics_history": [], "published_url": "", "published_at": "",
           "reminder_sent_at": "", "history": [{"status": "idea", "at": now_iso(), "by": actor.get("name", ""), "note": "dibuat"}],
           "created_by": actor.get("name", ""), "created_by_id": actor.get("id", ""), "created_at": now_iso(), "updated_at": now_iso()}
    await db.mkt_posts.insert_one(dict(doc))
    return doc


def _assets(raw: Any) -> List[Dict[str, Any]]:
    out = []
    for a in raw or []:
        if not isinstance(a, dict) or not a.get("ref_id"):
            continue
        out.append({"ref_type": a.get("ref_type") or "product", "ref_id": a["ref_id"], "label": (a.get("label") or "")[:120],
                    "image_url": a.get("image_url") or ""})
    return out[:12]


async def update_post(pid: str, payload: Dict[str, Any], actor: Dict[str, Any]) -> Dict[str, Any]:
    cur = await db.mkt_posts.find_one({"id": pid}, {"_id": 0})
    if not cur:
        raise MarketingError("Post tidak ditemukan.")
    if cur["status"] == "published" and any(k in payload for k in ("platforms", "publish_at", "caption", "title")):
        raise MarketingError("Post yang sudah tayang tidak bisa diubah isinya — catat performa atau buat post baru.")
    allowed = ("title", "caption", "hashtags", "platforms", "content_type", "publish_at", "campaign_id", "pic_user_id",
               "pic_name", "cta", "notes", "assets", "published_url")
    sets = {k: payload[k] for k in allowed if k in payload}
    if "hashtags" in sets:
        sets["hashtags"] = _hashtags(sets["hashtags"])
    if "assets" in sets:
        sets["assets"] = _assets(sets["assets"])
    merged = {**cur, **sets}
    _validate_post(merged)
    if "account_ids" in payload or "platforms" in sets:
        from services import marketing_ext as ext
        ids = [a for a in (payload.get("account_ids") or []) if a] if "account_ids" in payload else [a["id"] for a in cur.get("accounts") or []]
        sets["accounts"] = await ext.snapshot_accounts(ids, cur.get("entity_id", ""), merged.get("platforms") or [])
    if "campaign_id" in sets:
        sets["campaign_name"] = await _campaign_name(sets["campaign_id"])
    if sets.get("pic_user_id") and not sets.get("pic_name"):
        u = await db.users.find_one({"id": sets["pic_user_id"]}, {"_id": 0, "name": 1})
        sets["pic_name"] = (u or {}).get("name", "")
    if "publish_at" in sets and sets["publish_at"] != cur.get("publish_at"):
        sets["reminder_sent_at"] = ""
    sets["updated_at"] = now_iso()
    await db.mkt_posts.update_one({"id": pid}, {"$set": sets})
    return await db.mkt_posts.find_one({"id": pid}, {"_id": 0})


async def transition(pid: str, to: str, actor: Dict[str, Any], note: str = "", published_url: str = "") -> Dict[str, Any]:
    cur = await db.mkt_posts.find_one({"id": pid}, {"_id": 0})
    if not cur:
        raise MarketingError("Post tidak ditemukan.")
    frm = cur.get("status", "idea")
    if to not in TRANSITIONS.get(frm, set()):
        raise MarketingError(f"Tidak bisa dari '{frm}' ke '{to}'.")
    if to == "approved" and actor.get("role") not in APPROVE_ROLES:
        raise MarketingError("Hanya manager/admin yang boleh menyetujui konten.")
    if to == "review" and not (cur.get("caption") or "").strip():
        raise MarketingError("Isi caption dulu sebelum diajukan review.")
    if to == "scheduled":
        if not cur.get("publish_at"):
            raise MarketingError("Tentukan tanggal & jam tayang sebelum dijadwalkan.")
        if not cur.get("pic_user_id") and not cur.get("pic_name"):
            raise MarketingError("Tentukan PIC yang akan mem-posting.")
    if to in ("draft", "cancelled") and frm in ("review", "approved", "scheduled") and not note.strip():
        raise MarketingError("Alasan wajib diisi saat mengembalikan / membatalkan konten.")
    sets: Dict[str, Any] = {"status": to, "updated_at": now_iso()}
    if to == "published":
        sets["published_at"] = now_iso()
        if published_url:
            sets["published_url"] = published_url.strip()
    if to == "approved":
        sets.update({"approved_by": actor.get("name", ""), "approved_at": now_iso()})
    await db.mkt_posts.update_one({"id": pid}, {"$set": sets, "$push": {"history": {
        "status": to, "from": frm, "at": now_iso(), "by": actor.get("name", ""), "note": note.strip()}}})
    if to == "review":
        await _notify(roles=("manager", "admin"), entity_id=cur.get("entity_id", ""), notif_type="mkt_review",
                      title=f"Konten menunggu review: {cur['title']}", body=f"{', '.join(cur.get('platforms') or [])} · tayang {cur.get('publish_at') or '-'}",
                      ref=pid, severity="info")
    if to == "approved" and cur.get("pic_user_id"):
        await _notify(users=(cur["pic_user_id"],), entity_id=cur.get("entity_id", ""), notif_type="mkt_approved",
                      title=f"Konten disetujui: {cur['title']}", body="Jadwalkan & siapkan materi tayang.", ref=pid, severity="success")
    return await db.mkt_posts.find_one({"id": pid}, {"_id": 0})


async def _notify(*, entity_id: str, notif_type: str, title: str, body: str, ref: str, severity: str,
                  roles: tuple = (), users: tuple = ()) -> None:
    try:
        from services import notification_service as notif
        await notif.create_addressed(roles=roles, also_users=users, entity_id=entity_id, notif_type=notif_type,
                                     title=title, body=body, severity=severity, link="mkt-calendar", ref=ref)
    except Exception as exc:  # noqa: BLE001
        print(f"[marketing] notifikasi gagal: {exc}")


async def record_metrics(pid: str, metrics: Dict[str, Any], actor: Dict[str, Any], note: str = "") -> Dict[str, Any]:
    cur = await db.mkt_posts.find_one({"id": pid}, {"_id": 0, "status": 1})
    if not cur:
        raise MarketingError("Post tidak ditemukan.")
    if cur["status"] != "published":
        raise MarketingError("Performa hanya dicatat untuk post yang sudah tayang.")
    clean: Dict[str, float] = {}
    for k in METRIC_FIELDS:
        if metrics.get(k) not in (None, ""):
            v = float(metrics[k])
            if v < 0:
                raise MarketingError(f"Nilai {k} tidak boleh negatif.")
            clean[k] = v
    if not clean:
        raise MarketingError("Isi minimal satu angka performa.")
    snap = {**clean, "recorded_at": now_iso(), "by": actor.get("name", ""), "note": note.strip()}
    await db.mkt_posts.update_one({"id": pid}, {"$set": {"metrics": {**clean, "recorded_at": snap["recorded_at"]}, "updated_at": now_iso()},
                                                "$push": {"metrics_history": snap}})
    return await db.mkt_posts.find_one({"id": pid}, {"_id": 0})


async def add_attachment(pid: str, actor: str, filename: str, content_type: str, data: bytes, caption: str = "") -> Dict[str, Any]:
    ct = storage.validate_upload(filename, content_type, len(data))
    path = storage.build_path("marketing", storage.ext_of(filename))
    await storage.put_object(path, data, ct)
    meta_ = {"id": new_id("mka"), "filename": filename, "content_type": ct, "size": len(data), "path": path,
             "caption": caption, "uploaded_by": actor, "uploaded_at": now_iso()}
    await db.mkt_posts.update_one({"id": pid}, {"$push": {"attachments": meta_}, "$set": {"updated_at": now_iso()}})
    return meta_


async def attachment_bytes(post: Dict[str, Any], fid: str):
    for f in post.get("attachments") or []:
        if f.get("id") == fid:
            data = await storage.get_object(f["path"])
            if isinstance(data, tuple):
                data = data[0]
            return data, f.get("content_type", "application/octet-stream")
    raise MarketingError("Lampiran tidak ditemukan.")


async def remove_attachment(pid: str, fid: str) -> None:
    await db.mkt_posts.update_one({"id": pid}, {"$pull": {"attachments": {"id": fid}}, "$set": {"updated_at": now_iso()}})


# ─── Bahan konten (aset internal) ────────────────────────────────────────────
async def search_assets(q: str, entity_id: str) -> Dict[str, List[Dict[str, Any]]]:
    rx = {"$regex": q, "$options": "i"} if q else None
    dq: Dict[str, Any] = {"status": {"$in": ["approved", "final_submitted", "active"]}}
    pq: Dict[str, Any] = {"active": {"$ne": False}}
    if rx:
        dq["$or"] = [{"code": rx}, {"title": rx}]
        pq["$or"] = [{"sku": rx}, {"name": rx}]
    designs = await db.design_gallery.find(dq, {"_id": 0, "id": 1, "code": 1, "title": 1, "status": 1, "cover_file_id": 1}).sort("updated_at", -1).to_list(12)
    products = await db.products.find(pq, {"_id": 0, "id": 1, "sku": 1, "name": 1, "image_url": 1, "color_ref": 1}).sort("updated_at", -1).to_list(12)
    ods = await db.special_orders.find({"entity_id": entity_id, "status": {"$in": ["shipped", "done"]}, **({"$or": [{"number": rx}, {"title": rx}]} if rx else {})},
                                       {"_id": 0, "id": 1, "number": 1, "title": 1, "customer_name": 1}).sort("updated_at", -1).to_list(8)
    return {"designs": designs, "products": products, "special_orders": ods}


# ─── Analitik ────────────────────────────────────────────────────────────────
async def analytics(scope: Dict[str, Any], month: str = "", campaign_id: str = "") -> Dict[str, Any]:
    q: Dict[str, Any] = {**scope, "status": {"$ne": "cancelled"}}
    if month:
        q["publish_at"] = {"$gte": f"{month}-01", "$lt": _next_month(month)}
    if campaign_id:
        q["campaign_id"] = campaign_id
    rows = await db.mkt_posts.find(q, {"_id": 0}).to_list(2000)
    by_status: Dict[str, int] = {}
    by_platform: Dict[str, Dict[str, float]] = {}
    totals = {k: 0.0 for k in METRIC_FIELDS}
    published = 0
    for r in rows:
        by_status[r["status"]] = by_status.get(r["status"], 0) + 1
        m = r.get("metrics") or {}
        if r["status"] == "published":
            published += 1
            for k in METRIC_FIELDS:
                totals[k] += float(m.get(k) or 0)
        for pl in r.get("platforms") or []:
            b = by_platform.setdefault(pl, {"posts": 0, "published": 0, "reach": 0.0, "engagement": 0.0, "clicks": 0.0})
            b["posts"] += 1
            if r["status"] == "published":
                b["published"] += 1
                b["reach"] += float(m.get("reach") or 0)
                b["engagement"] += sum(float(m.get(k) or 0) for k in ("likes", "comments", "shares", "saves"))
                b["clicks"] += float(m.get("clicks") or 0)
    eng = sum(totals[k] for k in ("likes", "comments", "shares", "saves"))
    top = sorted([r for r in rows if r["status"] == "published"],
                 key=lambda r: sum(float((r.get("metrics") or {}).get(k) or 0) for k in ("likes", "comments", "shares", "saves")), reverse=True)[:5]
    now = datetime.now(WIB)
    overdue = [r for r in rows if r["status"] == "scheduled" and r.get("publish_at") and r["publish_at"] < now.strftime("%Y-%m-%dT%H:%M")]
    return {"month": month, "posts_total": len(rows), "published": published, "by_status": by_status, "by_platform": by_platform,
            "totals": totals, "engagement_total": eng,
            "engagement_rate_pct": round(eng / totals["reach"] * 100, 2) if totals["reach"] else 0.0,
            "top_posts": [{"id": r["id"], "title": r["title"], "platforms": r.get("platforms"), "metrics": r.get("metrics"), "publish_at": r.get("publish_at")} for r in top],
            "overdue": [{"id": r["id"], "title": r["title"], "publish_at": r.get("publish_at"), "pic_name": r.get("pic_name")} for r in overdue]}


def _next_month(month: str) -> str:
    y, m = int(month[:4]), int(month[5:7])
    return f"{y + 1}-01-01" if m == 12 else f"{y}-{m + 1:02d}-01"


# ─── Pengingat tayang (job scheduler) ────────────────────────────────────────
async def job_content_reminder() -> Dict[str, Any]:
    """Post 'scheduled' yang tayang dalam ≤60 menit (atau sudah lewat & belum ditandai) → ingatkan PIC."""
    now = datetime.now(WIB)
    horizon = (now + timedelta(minutes=REMINDER_WINDOW_MIN)).strftime("%Y-%m-%dT%H:%M")
    rows = await db.mkt_posts.find({"status": "scheduled", "publish_at": {"$ne": "", "$lte": horizon}, "reminder_sent_at": ""}, {"_id": 0}).to_list(200)
    sent = 0
    for r in rows:
        late = r["publish_at"] < now.strftime("%Y-%m-%dT%H:%M")
        title = ("TERLAMBAT tayang: " if late else "Saatnya posting: ") + r["title"]
        body = f"{', '.join(r.get('platforms') or [])} · jadwal {r['publish_at'].replace('T', ' ')} WIB · PIC {r.get('pic_name') or '-'}. Tandai 'Tayang' & tempel tautan setelah posting."
        users = (r["pic_user_id"],) if r.get("pic_user_id") else ()
        await _notify(users=users, roles=() if users else ("manager",), entity_id=r.get("entity_id", ""), notif_type="mkt_publish_due",
                      title=title, body=body, ref=r["id"], severity="warning" if late else "info")
        await db.mkt_posts.update_one({"id": r["id"]}, {"$set": {"reminder_sent_at": now_iso()}})
        sent += 1
    return {"scanned": len(rows), "reminders": sent}
