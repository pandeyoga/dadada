"""
marketing_ext.py — Marketing lanjutan: master Akun Sosmed per badan usaha, dashboard analitik
(bulan ini vs lalu, tren 6 bulan, per platform/akun/PT, tepat waktu), dan ekspor PDF kalender bulanan.
"""
from __future__ import annotations

import html
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from db import db
from core_utils import new_id, now_iso
from services.marketing_service import METRIC_FIELDS, PLATFORMS, MarketingError, _next_month

WIB = timezone(timedelta(hours=7))
ON_TIME_GRACE_MIN = 60
MONTHS_ID = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]


async def entity_names() -> Dict[str, str]:
    rows = await db.business_entities.find({}, {"_id": 0, "id": 1, "short_name": 1, "legal_name": 1, "code": 1}).to_list(100)
    return {r["id"]: (r.get("short_name") or r.get("code") or r.get("legal_name") or r["id"]) for r in rows}


# ─── Akun sosmed ─────────────────────────────────────────────────────────────
async def create_account(payload: Dict[str, Any], *, entity_id: str, actor: str) -> Dict[str, Any]:
    platform = (payload.get("platform") or "").strip()
    handle = (payload.get("handle") or "").strip().lstrip("@")
    if platform not in {p["code"] for p in PLATFORMS}:
        raise MarketingError("Platform tidak dikenal.")
    if not handle:
        raise MarketingError("Nama akun / handle wajib diisi.")
    dup = await db.mkt_accounts.find_one({"entity_id": entity_id, "platform": platform, "handle": {"$regex": f"^{handle}$", "$options": "i"}}, {"_id": 1})
    if dup:
        raise MarketingError(f"Akun @{handle} di {platform} sudah terdaftar untuk badan usaha ini.")
    doc = {"id": new_id("mka"), "entity_id": entity_id, "platform": platform, "handle": handle, "url": (payload.get("url") or "").strip(),
           "label": (payload.get("label") or "").strip(), "followers": float(payload.get("followers") or 0), "active": True,
           "notes": (payload.get("notes") or "").strip(), "created_by": actor, "created_at": now_iso(), "updated_at": now_iso()}
    await db.mkt_accounts.insert_one(dict(doc))
    return doc


async def update_account(aid: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    sets = {k: payload[k] for k in ("handle", "url", "label", "followers", "active", "notes") if k in payload}
    if "handle" in sets:
        sets["handle"] = str(sets["handle"]).strip().lstrip("@")
        if not sets["handle"]:
            raise MarketingError("Nama akun / handle wajib diisi.")
    if "followers" in sets:
        sets["followers"] = float(sets["followers"] or 0)
    sets["updated_at"] = now_iso()
    await db.mkt_accounts.update_one({"id": aid}, {"$set": sets})
    doc = await db.mkt_accounts.find_one({"id": aid}, {"_id": 0})
    await db.mkt_posts.update_many({"accounts.id": aid}, {"$set": {"accounts.$[a].handle": doc["handle"], "accounts.$[a].label": doc.get("label", "")}},
                                   array_filters=[{"a.id": aid}])
    return doc


async def list_accounts(scope: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = await db.mkt_accounts.find(scope, {"_id": 0}).sort([("entity_id", 1), ("platform", 1), ("handle", 1)]).to_list(300)
    names = await entity_names()
    for r in rows:
        r["entity_name"] = names.get(r.get("entity_id"), r.get("entity_id"))
        r["posts_total"] = await db.mkt_posts.count_documents({"accounts.id": r["id"], "status": {"$ne": "cancelled"}})
    return rows


async def snapshot_accounts(account_ids: List[str], entity_id: str, platforms: List[str]) -> List[Dict[str, Any]]:
    """Validasi akun milik badan usaha yang sama & platform-nya termasuk platform post."""
    if not account_ids:
        return []
    rows = await db.mkt_accounts.find({"id": {"$in": account_ids}}, {"_id": 0}).to_list(50)
    out = []
    for a in rows:
        if a.get("entity_id") != entity_id:
            raise MarketingError(f"Akun @{a['handle']} milik badan usaha lain — tidak bisa dipakai untuk konten ini.")
        if platforms and a["platform"] not in platforms:
            raise MarketingError(f"Akun @{a['handle']} ({a['platform']}) tidak sesuai platform yang dipilih.")
        out.append({"id": a["id"], "platform": a["platform"], "handle": a["handle"], "label": a.get("label", ""), "entity_id": a["entity_id"]})
    return out


# ─── Dashboard ───────────────────────────────────────────────────────────────
def _prev_month(month: str) -> str:
    y, m = int(month[:4]), int(month[5:7])
    return f"{y - 1}-12" if m == 1 else f"{y}-{m - 1:02d}"


def _eng(m: Dict[str, Any]) -> float:
    return sum(float((m or {}).get(k) or 0) for k in ("likes", "comments", "shares", "saves"))


def _kpi(rows: List[Dict[str, Any]]) -> Dict[str, float]:
    pub = [r for r in rows if r["status"] == "published"]
    out = {"posts": len(rows), "published": len(pub), "reach": 0.0, "engagement": 0.0, "clicks": 0.0, "leads": 0.0, "on_time": 0, "late": 0}
    for r in pub:
        m = r.get("metrics") or {}
        out["reach"] += float(m.get("reach") or 0); out["engagement"] += _eng(m); out["clicks"] += float(m.get("clicks") or 0); out["leads"] += float(m.get("sales_leads") or 0)
        if r.get("publish_at") and r.get("published_at"):
            try:
                sched = datetime.strptime(r["publish_at"][:16], "%Y-%m-%dT%H:%M").replace(tzinfo=WIB)
                actual = datetime.fromisoformat(r["published_at"].replace("Z", "+00:00"))
                out["on_time" if actual <= sched + timedelta(minutes=ON_TIME_GRACE_MIN) else "late"] += 1
            except ValueError:
                pass
    judged = out["on_time"] + out["late"]
    out["on_time_rate_pct"] = round(out["on_time"] / judged * 100, 1) if judged else 0.0
    out["engagement_rate_pct"] = round(out["engagement"] / out["reach"] * 100, 2) if out["reach"] else 0.0
    return out


def _month_query(scope: Dict[str, Any], month: str) -> Dict[str, Any]:
    return {**scope, "status": {"$ne": "cancelled"}, "publish_at": {"$gte": f"{month}-01", "$lt": _next_month(month)}}


async def dashboard(scope: Dict[str, Any], month: str) -> Dict[str, Any]:
    names = await entity_names()
    cur = await db.mkt_posts.find(_month_query(scope, month), {"_id": 0, "metrics_history": 0, "history": 0}).to_list(3000)
    prev = await db.mkt_posts.find(_month_query(scope, _prev_month(month)), {"_id": 0, "metrics_history": 0, "history": 0}).to_list(3000)
    # tren 6 bulan (termasuk bulan terpilih)
    months: List[str] = []
    m = month
    for _ in range(6):
        months.insert(0, m); m = _prev_month(m)
    start = f"{months[0]}-01"
    six = await db.mkt_posts.find({**scope, "status": {"$ne": "cancelled"}, "publish_at": {"$gte": start, "$lt": _next_month(month)}},
                                  {"_id": 0, "publish_at": 1, "status": 1, "metrics": 1}).to_list(10000)
    trend = []
    for mm in months:
        rows = [r for r in six if (r.get("publish_at") or "")[:7] == mm]
        k = _kpi(rows)
        trend.append({"month": mm, "label": f"{MONTHS_ID[int(mm[5:7]) - 1][:3]} {mm[2:4]}", "posts": k["posts"], "published": k["published"], "reach": k["reach"], "engagement": k["engagement"]})
    by_platform: Dict[str, Dict[str, Any]] = {}
    by_account: Dict[str, Dict[str, Any]] = {}
    by_entity: Dict[str, Dict[str, Any]] = {}
    for r in cur:
        pub = r["status"] == "published"; mt = r.get("metrics") or {}
        for pl in r.get("platforms") or []:
            b = by_platform.setdefault(pl, {"posts": 0, "published": 0, "reach": 0.0, "engagement": 0.0, "clicks": 0.0})
            b["posts"] += 1
            if pub:
                b["published"] += 1; b["reach"] += float(mt.get("reach") or 0); b["engagement"] += _eng(mt); b["clicks"] += float(mt.get("clicks") or 0)
        for a in r.get("accounts") or []:
            b = by_account.setdefault(a["id"], {"handle": a["handle"], "platform": a["platform"], "entity_name": names.get(a.get("entity_id"), ""), "posts": 0, "published": 0, "reach": 0.0, "engagement": 0.0})
            b["posts"] += 1
            if pub:
                b["published"] += 1; b["reach"] += float(mt.get("reach") or 0); b["engagement"] += _eng(mt)
        e = by_entity.setdefault(r.get("entity_id", ""), {"entity_name": names.get(r.get("entity_id"), r.get("entity_id", "")), "posts": 0, "published": 0, "reach": 0.0, "engagement": 0.0})
        e["posts"] += 1
        if pub:
            e["published"] += 1; e["reach"] += float(mt.get("reach") or 0); e["engagement"] += _eng(mt)
    now = datetime.now(WIB); now_s = now.strftime("%Y-%m-%dT%H:%M"); week = (now + timedelta(days=7)).strftime("%Y-%m-%dT%H:%M")
    live = await db.mkt_posts.find({**scope, "status": {"$in": ["approved", "scheduled"]}, "publish_at": {"$ne": ""}},
                                   {"_id": 0, "id": 1, "title": 1, "publish_at": 1, "platforms": 1, "status": 1, "pic_name": 1, "entity_id": 1, "accounts": 1}).sort("publish_at", 1).to_list(500)
    upcoming = [{**r, "entity_name": names.get(r.get("entity_id"), "")} for r in live if now_s <= r["publish_at"] <= week][:20]
    overdue = [{**r, "entity_name": names.get(r.get("entity_id"), "")} for r in live if r["status"] == "scheduled" and r["publish_at"] < now_s][:20]
    top = sorted([r for r in cur if r["status"] == "published"], key=lambda r: _eng(r.get("metrics")), reverse=True)[:5]
    return {"month": month, "prev_month": _prev_month(month), "kpi": _kpi(cur), "kpi_prev": _kpi(prev), "trend": trend,
            "by_platform": by_platform, "by_account": by_account, "by_entity": by_entity,
            "top_posts": [{"id": r["id"], "title": r["title"], "platforms": r.get("platforms"), "metrics": r.get("metrics"), "publish_at": r.get("publish_at"),
                           "entity_name": names.get(r.get("entity_id"), ""), "accounts": r.get("accounts") or []} for r in top],
            "upcoming": upcoming, "overdue": overdue, "pipeline": {s: sum(1 for r in cur if r["status"] == s) for s in ("idea", "draft", "review", "approved", "scheduled", "published")}}


# ─── Ekspor PDF kalender ─────────────────────────────────────────────────────
STATUS_ID = {"idea": "Ide", "draft": "Draft", "review": "Review", "approved": "Disetujui", "scheduled": "Terjadwal", "published": "Tayang", "cancelled": "Batal"}
STATUS_COLOR = {"idea": "#8E8E93", "draft": "#3730A3", "review": "#B45309", "approved": "#0369A1", "scheduled": "#6D28D9", "published": "#1B7F4B", "cancelled": "#C0392B"}
PLAT_SHORT = {"instagram": "IG", "tiktok": "TT", "facebook": "FB", "whatsapp": "WA", "shopee": "SP", "youtube": "YT"}


async def calendar_pdf_html(scope: Dict[str, Any], month: str, branding: Dict[str, Any], scope_label: str) -> str:
    names = await entity_names()
    posts = await db.mkt_posts.find({**scope, "$or": [{"publish_at": {"$gte": f"{month}-01", "$lt": _next_month(month)}}, {"publish_at": "", "created_at": {"$gte": f"{month}-01", "$lt": _next_month(month)}}],
                                     "status": {"$ne": "cancelled"}}, {"_id": 0, "metrics_history": 0, "history": 0}).sort("publish_at", 1).to_list(2000)
    camp_ids = {p.get("campaign_id") for p in posts if p.get("campaign_id")}
    camps = await db.mkt_campaigns.find({"id": {"$in": list(camp_ids)}}, {"_id": 0}).to_list(100) if camp_ids else []
    multi = len({p.get("entity_id") for p in posts}) > 1 or scope_label == "Semua badan usaha"
    y, mo = int(month[:4]), int(month[5:7])
    first = datetime(y, mo, 1); lead = (first.weekday())  # Senin=0
    days = ((first.replace(day=28) + timedelta(days=4)).replace(day=1) - first).days
    by_day: Dict[str, List[Dict[str, Any]]] = {}
    for p in posts:
        by_day.setdefault(p["publish_at"][:10] if p.get("publish_at") else "", []).append(p)
    e = html.escape
    cells = []
    for _ in range(lead):
        cells.append('<td class="empty"></td>')
    for d in range(1, days + 1):
        key = f"{month}-{d:02d}"
        items = "".join(
            f'<div class="chip" style="border-left:3px solid {STATUS_COLOR.get(p["status"], "#999")}"><b>{e(p["publish_at"][11:16])}</b> {e(p["title"][:38])}'
            f'<span class="pl">{"/".join(PLAT_SHORT.get(x, x) for x in p.get("platforms") or [])}{(" · " + e(names.get(p.get("entity_id"), ""))) if multi else ""}</span></div>'
            for p in by_day.get(key, [])[:5])
        more = f'<div class="more">+{len(by_day.get(key, [])) - 5} lagi</div>' if len(by_day.get(key, [])) > 5 else ""
        cells.append(f'<td><div class="dn">{d}</div>{items}{more}</td>')
    while len(cells) % 7:
        cells.append('<td class="empty"></td>')
    rows_html = "".join(f"<tr>{''.join(cells[i:i + 7])}</tr>" for i in range(0, len(cells), 7))
    def _row(p: Dict[str, Any]) -> str:
        cap = (p.get("caption") or "").strip().replace("\n", " ")
        cap = (cap[:120] + "…") if len(cap) > 120 else cap
        acc = ", ".join("@" + a["handle"] for a in p.get("accounts") or [])
        return (f'<tr><td>{e(p["publish_at"][8:10] + "/" + p["publish_at"][5:7] + " " + p["publish_at"][11:16]) if p.get("publish_at") else "—"}</td>'
                f'<td>{e(", ".join(p.get("platforms") or []))}{("<br><small>" + e(acc) + "</small>") if acc else ""}</td>'
                f'<td><b>{e(p["title"])}</b>{("<br><small>" + e(cap) + "</small>") if cap else ""}</td>'
                f'{("<td>" + e(names.get(p.get("entity_id"), "")) + "</td>") if multi else ""}'
                f'<td>{e(p.get("campaign_name") or "—")}</td><td>{e(p.get("pic_name") or "—")}</td>'
                f'<td><span class="st" style="background:{STATUS_COLOR.get(p["status"], "#999")}">{STATUS_ID.get(p["status"], p["status"])}</span></td></tr>')
    list_html = "".join(_row(p) for p in posts if p.get("publish_at")) + "".join(_row(p) for p in posts if not p.get("publish_at"))
    camp_html = "".join(
        f'<tr><td><b>{e(c["name"])}</b><br><small>{e(c.get("theme") or "")}</small></td><td>{e(c.get("start_date") or "")} → {e(c.get("end_date") or "…")}</td>'
        f'<td>{sum(1 for p in posts if p.get("campaign_id") == c["id"])}</td><td>{sum(1 for p in posts if p.get("campaign_id") == c["id"] and p["status"] == "published")}</td></tr>' for c in camps)
    status_counts = {s: sum(1 for p in posts if p["status"] == s) for s in STATUS_ID if s != "cancelled"}
    summary = " · ".join(f"{STATUS_ID[s]} <b>{n}</b>" for s, n in status_counts.items() if n)
    logo = f'<img src="{branding["logo_src"]}" class="logo">' if branding.get("logo_src") else ""
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
@page {{ size: A4 landscape; margin: 12mm; }}
body {{ font-family: Helvetica, Arial, sans-serif; font-size: 9pt; color: #1c1c1e; }}
.kop {{ display:flex; align-items:center; gap:12px; border-bottom: 2px solid #0058CC; padding-bottom:6px; margin-bottom:8px; }}
.logo {{ height: 34px; }} .kop h1 {{ font-size: 14pt; margin:0; }} .kop p {{ margin:0; color:#6B6B73; font-size:8pt; }}
h2 {{ font-size: 11pt; margin: 10px 0 4px; color:#0058CC; }}
table.cal {{ width:100%; border-collapse:collapse; table-layout:fixed; }}
table.cal th {{ background:#F2F2F7; font-size:8pt; padding:3px; border:1px solid #E5E5EA; }}
table.cal td {{ border:1px solid #E5E5EA; vertical-align:top; height:62px; padding:2px; font-size:7pt; }}
td.empty {{ background:#FAFAFB; }} .dn {{ text-align:right; font-weight:bold; color:#6B6B73; }}
.chip {{ background:#F8FAFF; margin:1px 0; padding:1px 3px; border-radius:2px; }} .pl {{ color:#6B6B73; margin-left:3px; }} .more {{ color:#8E8E93; }}
table.list {{ width:100%; border-collapse:collapse; margin-top:4px; }} table.list th {{ text-align:left; background:#F2F2F7; padding:4px; border-bottom:1px solid #D9D9DE; font-size:8pt; }}
table.list td {{ padding:4px; border-bottom:1px solid #EFF0F2; vertical-align:top; }} small {{ color:#6B6B73; }}
.st {{ color:#fff; border-radius:8px; padding:1px 6px; font-size:7.5pt; font-weight:bold; }}
.foot {{ margin-top:6px; color:#8E8E93; font-size:7.5pt; text-align:right; page-break-inside: avoid; }}
h2 {{ page-break-after: avoid; }} table.list tr {{ page-break-inside: avoid; }}
</style></head><body>
<div class="kop">{logo}<div><h1>{e(branding.get("company_name", ""))} — Kalender Konten {MONTHS_ID[mo - 1]} {y}</h1>
<p>{e(scope_label)} · {len(posts)} konten · {summary or "belum ada konten"} · dicetak {datetime.now(WIB).strftime("%d/%m/%Y %H:%M")} WIB · legenda: {" · ".join(f'<span class="st" style="background:{c}">{STATUS_ID[s]}</span>' for s, c in STATUS_COLOR.items() if s != "cancelled")}</p></div></div>
<table class="cal"><thead><tr>{''.join(f'<th>{d}</th>' for d in ("Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"))}</tr></thead><tbody>{rows_html}</tbody></table>
<h2>Daftar rinci konten</h2>
<table class="list"><thead><tr><th style="width:12%">Tanggal · Jam</th><th style="width:14%">Platform · Akun</th><th>Judul · Caption</th>{"<th style='width:10%'>Badan usaha</th>" if multi else ""}<th style="width:12%">Kampanye</th><th style="width:10%">PIC</th><th style="width:8%">Status</th></tr></thead>
<tbody>{list_html or '<tr><td colspan="7"><i>Belum ada konten bulan ini.</i></td></tr>'}</tbody></table>
{('<h2>Ringkasan kampanye</h2><table class="list"><thead><tr><th>Kampanye</th><th>Periode</th><th>Konten bulan ini</th><th>Tayang</th></tr></thead><tbody>' + camp_html + '</tbody></table>') if camps else ''}
<div class="foot">Kain Nusantara ERP · Marketing &amp; Sosial Media</div>
</body></html>"""
