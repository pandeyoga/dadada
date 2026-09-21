"""Marketing — Sosial Media & Konten: kampanye, kalender post, lampiran, performa, analitik."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel

from db import db
from dependencies import audit, require_permission
from entity_scope import assert_entity_access, entity_ctx, resolve_list_scope
from services import marketing_service as mkt
from services import marketing_ext as ext
from datetime import datetime

router = APIRouter(prefix="/api", tags=["marketing"])
COLL = "mkt_posts"


class CampaignBody(BaseModel):
    name: str = ""
    theme: str = ""
    goal: str = ""
    start_date: str = ""
    end_date: str = ""
    platforms: List[str] = []
    budget: float = 0
    color: str = ""
    status: str = ""
    notes: str = ""


class PostBody(BaseModel):
    title: Optional[str] = None
    caption: Optional[str] = None
    hashtags: Optional[Any] = None
    platforms: Optional[List[str]] = None
    content_type: Optional[str] = None
    publish_at: Optional[str] = None
    campaign_id: Optional[str] = None
    pic_user_id: Optional[str] = None
    pic_name: Optional[str] = None
    cta: Optional[str] = None
    notes: Optional[str] = None
    assets: Optional[List[Dict[str, Any]]] = None
    account_ids: Optional[List[str]] = None
    status: Optional[str] = None
    published_url: Optional[str] = None


class TransitionBody(BaseModel):
    to: str
    note: str = ""
    published_url: str = ""


class MetricsBody(BaseModel):
    metrics: Dict[str, Any]
    note: str = ""


def _err(exc: Exception) -> HTTPException:
    return HTTPException(status_code=400, detail=str(exc))


async def _post_or_404(pid: str, request: Request) -> Dict[str, Any]:
    ctx = await entity_ctx(request)
    doc = await db.mkt_posts.find_one({"id": pid}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Post tidak ditemukan")
    assert_entity_access(doc, COLL, ctx)
    return await _with_entity(doc)


async def _with_entity(doc: Dict[str, Any]) -> Dict[str, Any]:
    names = await ext.entity_names()
    doc["entity_name"] = names.get(doc.get("entity_id"), doc.get("entity_id", ""))
    return doc


@router.get("/marketing/meta")
async def marketing_meta(request: Request) -> Dict[str, Any]:
    await require_permission(request, "marketing", "view")
    users = await db.users.find({"active": {"$ne": False}, "role": {"$in": ["admin", "manager", "designer", "sales", "sales_admin"]}},
                                {"_id": 0, "id": 1, "name": 1, "role": 1}).sort("name", 1).to_list(200)
    ctx = await entity_ctx(request)
    names = await ext.entity_names()
    return {**mkt.meta(), "pic_options": users, "active_entity_id": ctx.active_entity_id,
            "active_entity_name": names.get(ctx.active_entity_id, ctx.active_entity_id), "entity_names": names}


# ─── Kampanye ────────────────────────────────────────────────────────────────
@router.get("/marketing/campaigns")
async def list_campaigns(request: Request, entity_id: Optional[str] = None) -> List[Dict[str, Any]]:
    await require_permission(request, "marketing", "view")
    ctx = await entity_ctx(request)
    return await mkt.list_campaigns(resolve_list_scope("mkt_campaigns", {}, ctx, entity_id))


@router.post("/marketing/campaigns")
async def create_campaign(payload: CampaignBody, request: Request) -> Dict[str, Any]:
    user = await require_permission(request, "marketing", "create")
    ctx = await entity_ctx(request)
    try:
        doc = await mkt.create_campaign(payload.model_dump(), entity_id=ctx.active_entity_id, actor=user)
    except mkt.MarketingError as exc:
        raise _err(exc) from exc
    await audit(user.get("name", ""), "mkt_campaign_create", "mkt_campaign", doc["id"], {"name": doc["name"]})
    return doc


@router.patch("/marketing/campaigns/{cid}")
async def update_campaign(cid: str, payload: CampaignBody, request: Request) -> Dict[str, Any]:
    await require_permission(request, "marketing", "update")
    ctx = await entity_ctx(request)
    cur = await db.mkt_campaigns.find_one({"id": cid}, {"_id": 0})
    if not cur:
        raise HTTPException(status_code=404, detail="Kampanye tidak ditemukan")
    assert_entity_access(cur, "mkt_campaigns", ctx)
    try:
        return await mkt.update_campaign(cid, payload.model_dump(exclude_unset=True))
    except mkt.MarketingError as exc:
        raise _err(exc) from exc


# ─── Post ────────────────────────────────────────────────────────────────────
@router.get("/marketing/posts")
async def list_posts(request: Request, entity_id: Optional[str] = None, month: str = "", from_date: str = "", to_date: str = "",
                     platform: str = "", status: str = "", campaign_id: str = "", pic_user_id: str = "", q: str = "") -> List[Dict[str, Any]]:
    await require_permission(request, "marketing", "view")
    ctx = await entity_ctx(request)
    query: Dict[str, Any] = {}
    if month:
        query["$or"] = [{"publish_at": {"$gte": f"{month}-01", "$lt": mkt._next_month(month)}}, {"publish_at": "", "created_at": {"$gte": f"{month}-01"}}]  # noqa: SLF001
    if from_date or to_date:
        rng: Dict[str, Any] = {}
        if from_date:
            rng["$gte"] = from_date
        if to_date:
            rng["$lte"] = to_date + "T23:59"
        query["publish_at"] = rng
    if platform:
        query["platforms"] = platform
    if status:
        query["status"] = status
    if campaign_id:
        query["campaign_id"] = campaign_id
    if pic_user_id:
        query["pic_user_id"] = pic_user_id
    if q:
        query["title"] = {"$regex": q, "$options": "i"}
    query = resolve_list_scope(COLL, query, ctx, entity_id)
    rows = await db.mkt_posts.find(query, {"_id": 0, "metrics_history": 0, "history": 0}).sort([("publish_at", 1), ("created_at", -1)]).to_list(1000)
    names = await ext.entity_names()
    for r in rows:
        r["entity_name"] = names.get(r.get("entity_id"), r.get("entity_id", ""))
    return rows


# ─── Akun sosmed (per badan usaha, boleh banyak) ─────────────────────────────
class AccountBody(BaseModel):
    platform: Optional[str] = None
    handle: Optional[str] = None
    url: Optional[str] = None
    label: Optional[str] = None
    followers: Optional[float] = None
    active: Optional[bool] = None
    notes: Optional[str] = None


@router.get("/marketing/accounts")
async def list_accounts(request: Request, entity_id: Optional[str] = None) -> List[Dict[str, Any]]:
    await require_permission(request, "marketing", "view")
    ctx = await entity_ctx(request)
    return await ext.list_accounts(resolve_list_scope("mkt_accounts", {}, ctx, entity_id))


@router.post("/marketing/accounts")
async def create_account(payload: AccountBody, request: Request) -> Dict[str, Any]:
    user = await require_permission(request, "marketing", "create")
    ctx = await entity_ctx(request)
    try:
        return await ext.create_account(payload.model_dump(exclude_none=True), entity_id=ctx.active_entity_id, actor=user.get("name", ""))
    except mkt.MarketingError as exc:
        raise _err(exc) from exc


@router.patch("/marketing/accounts/{aid}")
async def update_account(aid: str, payload: AccountBody, request: Request) -> Dict[str, Any]:
    await require_permission(request, "marketing", "update")
    ctx = await entity_ctx(request)
    cur = await db.mkt_accounts.find_one({"id": aid}, {"_id": 0})
    if not cur:
        raise HTTPException(status_code=404, detail="Akun tidak ditemukan")
    assert_entity_access(cur, "mkt_accounts", ctx)
    try:
        return await ext.update_account(aid, payload.model_dump(exclude_unset=True))
    except mkt.MarketingError as exc:
        raise _err(exc) from exc


@router.get("/marketing/dashboard")
async def marketing_dashboard(request: Request, entity_id: Optional[str] = None, month: str = "") -> Dict[str, Any]:
    await require_permission(request, "marketing", "view")
    ctx = await entity_ctx(request)
    month = month or datetime.now(ext.WIB).strftime("%Y-%m")
    return await ext.dashboard(resolve_list_scope(COLL, {}, ctx, entity_id), month)


@router.get("/marketing/calendar.pdf")
async def calendar_pdf(request: Request, entity_id: Optional[str] = None, month: str = ""):
    await require_permission(request, "marketing", "view")
    ctx = await entity_ctx(request)
    month = month or datetime.now(ext.WIB).strftime("%Y-%m")
    scope = resolve_list_scope(COLL, {}, ctx, entity_id)
    names = await ext.entity_names()
    ids = ctx.allowed_entity_ids if (entity_id == "all" or getattr(ctx, "view_all", False)) and not (entity_id and entity_id != "all") else [entity_id or ctx.active_entity_id]
    scope_label = "Semua badan usaha" if len(ids) > 1 else names.get(ids[0], ids[0])
    from services import pdf_service as pdfsvc
    from services.pdf_engine import render_pdf
    branding = await pdfsvc.get_branding(ids[0] if len(ids) == 1 else ctx.active_entity_id)
    if len(ids) > 1:
        branding = {**branding, "company_name": "Grup Kain Nusantara"}
    html_doc = await ext.calendar_pdf_html(scope, month, branding, scope_label)
    pdf, _engine = render_pdf(html_doc)
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="kalender-konten-{month}.pdf"'})


@router.get("/marketing/posts/{pid}")
async def get_post(pid: str, request: Request) -> Dict[str, Any]:
    await require_permission(request, "marketing", "view")
    return await _post_or_404(pid, request)


@router.post("/marketing/posts")
async def create_post(payload: PostBody, request: Request) -> Dict[str, Any]:
    user = await require_permission(request, "marketing", "create")
    ctx = await entity_ctx(request)
    try:
        doc = await mkt.create_post(payload.model_dump(exclude_none=True), entity_id=ctx.active_entity_id, actor=user)
    except mkt.MarketingError as exc:
        raise _err(exc) from exc
    await audit(user.get("name", ""), "mkt_post_create", "mkt_post", doc["id"], {"title": doc["title"]})
    return await _with_entity(doc)


@router.patch("/marketing/posts/{pid}")
async def update_post(pid: str, payload: PostBody, request: Request) -> Dict[str, Any]:
    user = await require_permission(request, "marketing", "update")
    await _post_or_404(pid, request)
    try:
        return await _with_entity(await mkt.update_post(pid, payload.model_dump(exclude_unset=True), user))
    except mkt.MarketingError as exc:
        raise _err(exc) from exc


@router.post("/marketing/posts/{pid}/transition")
async def transition_post(pid: str, payload: TransitionBody, request: Request) -> Dict[str, Any]:
    user = await require_permission(request, "marketing", "update")
    cur = await _post_or_404(pid, request)
    try:
        doc = await _with_entity(await mkt.transition(pid, payload.to, user, payload.note, payload.published_url))
    except mkt.MarketingError as exc:
        raise _err(exc) from exc
    await audit(user.get("name", ""), f"mkt_post_{payload.to}", "mkt_post", pid, {"from": cur.get("status"), "title": cur.get("title")}, reason=payload.note)
    return doc


@router.post("/marketing/posts/{pid}/metrics")
async def post_metrics(pid: str, payload: MetricsBody, request: Request) -> Dict[str, Any]:
    user = await require_permission(request, "marketing", "update")
    await _post_or_404(pid, request)
    try:
        return await _with_entity(await mkt.record_metrics(pid, payload.metrics, user, payload.note))
    except mkt.MarketingError as exc:
        raise _err(exc) from exc


@router.delete("/marketing/posts/{pid}")
async def delete_post(pid: str, request: Request) -> Dict[str, Any]:
    user = await require_permission(request, "marketing", "delete")
    cur = await _post_or_404(pid, request)
    if cur.get("status") == "published":
        raise HTTPException(status_code=400, detail="Post yang sudah tayang tidak bisa dihapus — batalkan lewat riwayat atau biarkan sebagai arsip.")
    await db.mkt_posts.delete_one({"id": pid})
    await audit(user.get("name", ""), "mkt_post_delete", "mkt_post", pid, {"title": cur.get("title")})
    return {"ok": True}


@router.post("/marketing/posts/{pid}/attachments")
async def upload_attachment(pid: str, request: Request, file: UploadFile = File(...), caption: str = Form("")) -> Dict[str, Any]:
    user = await require_permission(request, "marketing", "update")
    await _post_or_404(pid, request)
    data = await file.read()
    try:
        meta_ = await mkt.add_attachment(pid, user.get("name", ""), file.filename or "lampiran", file.content_type or "", data, caption)
    except (mkt.MarketingError, ValueError) as exc:
        raise _err(exc) from exc
    return {"attachment": meta_, "post": await db.mkt_posts.find_one({"id": pid}, {"_id": 0})}


@router.get("/marketing/posts/{pid}/attachments/{fid}")
async def attachment_file(pid: str, fid: str, request: Request):
    await require_permission(request, "marketing", "view")
    post = await _post_or_404(pid, request)
    try:
        data, ctype = await mkt.attachment_bytes(post, fid)
    except (mkt.MarketingError, FileNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(content=data, media_type=ctype, headers={"Cache-Control": "private, max-age=300"})


@router.delete("/marketing/posts/{pid}/attachments/{fid}")
async def delete_attachment(pid: str, fid: str, request: Request) -> Dict[str, Any]:
    await require_permission(request, "marketing", "update")
    await _post_or_404(pid, request)
    await mkt.remove_attachment(pid, fid)
    return await db.mkt_posts.find_one({"id": pid}, {"_id": 0})


@router.get("/marketing/assets")
async def assets(request: Request, q: str = "") -> Dict[str, Any]:
    await require_permission(request, "marketing", "view")
    ctx = await entity_ctx(request)
    return await mkt.search_assets(q.strip(), ctx.active_entity_id)


@router.get("/marketing/analytics")
async def marketing_analytics(request: Request, entity_id: Optional[str] = None, month: str = "", campaign_id: str = "") -> Dict[str, Any]:
    await require_permission(request, "marketing", "view")
    ctx = await entity_ctx(request)
    return await mkt.analytics(resolve_list_scope(COLL, {}, ctx, entity_id), month, campaign_id)
