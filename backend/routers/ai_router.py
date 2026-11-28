"""ai_router — `/api/ai`: Copilot (percakapan, SSE, aksi, artefak), pengaturan & penggunaan."""
import asyncio
import json
import re
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel

import settings_store as ss
import storage
from ai import actions, api_views, attachments, budget, config, conversations
from ai.agent import EXEMPT_ROLES, run_turn
from ai.client import ClaudeError, get_claude
from ai.tools.registry import ToolContext
from db import db, ORG_ID
from rbac import audit_log, require_permission

router = APIRouter(prefix="/ai", tags=["ai"])
_use = require_permission("ai_copilot", "use")
_manage = require_permission("ai_settings", "manage")
ROLES = ("copilot", "sales", "cs")
MAX_UPLOAD = 8 * 1024 * 1024
SETTING_KEYS = tuple(k for k in config._SIMPLE if k != "category_modes")
MODES = ("off", "simulation", "live")
EFFORTS = ("low", "medium", "high", "xhigh", "max")


def _org(u: dict) -> str:
    return u.get("org_id", ORG_ID)


def _token(request: Request) -> str:
    h = request.headers.get("authorization", "")
    return h[7:] if h.lower().startswith("bearer ") else request.cookies.get("access_token", "")


async def _own_conv(conv_id: str, user: dict) -> dict:
    try:
        return await conversations.get(conv_id, user["id"])
    except LookupError:
        raise HTTPException(404, "Percakapan tidak ditemukan.")


# ---------------------------------------------------------------- status & percakapan
@router.get("/status")
async def status(user: dict = Depends(_use)):
    org = _org(user)
    s = await config.get_ai_settings(org)
    b = await budget.budget_state(org)
    b["exempt"] = user.get("role") in EXEMPT_ROLES
    return {"data": {"effective_mode": s["effective_mode"], "budget": b,
                     "web_research_enabled": bool(s.get("web_research_enabled"))}}


class ConvIn(BaseModel):
    role: Optional[str] = "copilot"


class TitleIn(BaseModel):
    title: str


@router.get("/conversations")
async def list_conversations(q: Optional[str] = None, user: dict = Depends(_use)):
    rows = await conversations.list_for(user["id"], q)
    return {"data": [{k: r.get(k) for k in ("id", "title", "role", "channel", "created_at", "updated_at")}
                     for r in rows if r.get("channel", "web") == "web"]}


@router.post("/conversations")
async def create_conversation(body: ConvIn, user: dict = Depends(_use)):
    role = body.role or "copilot"
    if role not in ROLES:
        raise HTTPException(400, "Peran percakapan tidak valid.")
    return {"data": await conversations.create(_org(user), user["id"], role=role)}


@router.patch("/conversations/{conv_id}")
async def rename_conversation(conv_id: str, body: TitleIn, user: dict = Depends(_use)):
    await _own_conv(conv_id, user)
    title = body.title.strip()[:120]
    if not title:
        raise HTTPException(400, "Judul tidak boleh kosong.")
    await db.ai_conversations.update_one({"id": conv_id, "owner_id": user["id"]}, {"$set": {"title": title}})
    return {"data": {"id": conv_id, "title": title}}


@router.delete("/conversations/{conv_id}")
async def delete_conversation(conv_id: str, user: dict = Depends(_use)):
    await _own_conv(conv_id, user)
    await db.ai_messages.delete_many({"conversation_id": conv_id})
    await db.ai_conversations.delete_one({"id": conv_id, "owner_id": user["id"]})
    return {"data": {"deleted": True}}


@router.get("/conversations/{conv_id}")
async def get_conversation(conv_id: str, user: dict = Depends(_use)):
    c = await _own_conv(conv_id, user)
    raw = c.pop("messages")
    c["messages"] = await api_views.ui_messages(raw)
    return {"data": c}


# ---------------------------------------------------------------- berkas & pesan (SSE)
@router.post("/files")
async def upload_file(file: UploadFile = File(...), user: dict = Depends(_use)):
    data = await file.read(MAX_UPLOAD + 1)
    if not data:
        raise HTTPException(400, "Berkas kosong.")
    if len(data) > MAX_UPLOAD:
        raise HTTPException(413, "Berkas terlalu besar (maksimal 8 MB).")
    rec = await storage.save_file(data=data, filename=file.filename or "lampiran", content_type=file.content_type,
                                  org_id=_org(user), owner_type="ai_attachment", owner_id=user["id"],
                                  uploaded_by=user["id"], tag="ai_attachment", optimize=False)
    return {"data": {"id": rec["id"], "name": rec["original_filename"], "content_type": rec["content_type"],
                     "size": rec["size"]}}


class MessageIn(BaseModel):
    text: str
    role: Optional[str] = None
    web_research: bool = False
    attachments: list[str] = []


def _sse(ev: dict) -> bytes:
    return f"data: {json.dumps(ev, ensure_ascii=False, default=str)}\n\n".encode()


@router.post("/conversations/{conv_id}/messages")
async def send_message(conv_id: str, body: MessageIn, request: Request, user: dict = Depends(_use)):
    conv = await _own_conv(conv_id, user)
    text = (body.text or "").strip()
    if not text:
        raise HTTPException(400, "Pesan tidak boleh kosong.")
    role = body.role or conv.get("role") or "copilot"
    if role not in ROLES:
        raise HTTPException(400, "Peran percakapan tidak valid.")
    org = _org(user)
    web = bool(body.web_research) and bool((await config.get_ai_settings(org)).get("web_research_enabled"))
    ctx = ToolContext(org_id=org, user=user, token=_token(request), conversation_id=conv_id,
                      web_research=web, role=role)
    recs = await attachments.resolve(body.attachments, org, user["id"])
    if sum(r.get("size") or 0 for r in recs) > attachments.MAX_ATTACH_BYTES:
        raise HTTPException(413, "Total lampiran terlalu besar (maksimal 8 MB per pesan).")
    content = [{"type": "text", "text": text}] + [attachments.marker(r) for r in recs]
    att_ids = [r["id"] for r in recs]

    async def stream():
        gen = run_turn(ctx, conv_id, content, att_ids)
        partial, finished = [], False
        try:
            async for ev in gen:
                if ev.get("type") == "text_delta":
                    partial.append(ev.get("text", ""))
                elif ev.get("type") == "step_started":
                    partial.clear()  # teks putaran ini sudah tersimpan bersama tool_use-nya
                elif ev.get("type") in ("done", "error"):
                    finished = True
                yield _sse(ev)
        except (asyncio.CancelledError, GeneratorExit):
            raise
        except Exception:  # noqa: BLE001
            finished = True
            yield _sse({"type": "error", "message": "Terjadi kesalahan pada layanan AI. Coba lagi."})
        finally:
            if not finished and partial:  # klien putus: simpan jawaban parsial (tugas terpisah, kebal pembatalan)
                asyncio.ensure_future(conversations.append(conv_id, {
                    "role": "assistant", "content": [{"type": "text", "text": "".join(partial)}], "partial": True}))
            asyncio.ensure_future(gen.aclose())

    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ---------------------------------------------------------------- aksi & artefak
class ApproveIn(BaseModel):
    edits: Optional[dict] = None


class RejectIn(BaseModel):
    reason: Optional[str] = ""


def _action_error(e: actions.ActionError):
    raise HTTPException(e.status, e.message)


@router.post("/actions/{action_id}/approve")
async def approve_action(action_id: str, request: Request, body: ApproveIn = ApproveIn(),
                         user: dict = Depends(_use)):
    try:
        a = await actions.approve(action_id, user, _token(request), edits=body.edits)
    except actions.ActionError as e:
        _action_error(e)
    return {"data": api_views.action_view(a)}


@router.post("/actions/{action_id}/reject")
async def reject_action(action_id: str, body: RejectIn = RejectIn(), user: dict = Depends(_use)):
    try:
        a = await actions.reject(action_id, user, body.reason or "")
    except actions.ActionError as e:
        _action_error(e)
    return {"data": api_views.action_view(a)}


@router.get("/artifacts/{artifact_id}/{kind}")
async def download_artifact(artifact_id: str, kind: str, user: dict = Depends(_use)):
    from ai import reports
    art = await db.ai_artifacts.find_one({"id": artifact_id}, {"_id": 0, "created_by": 1})
    if not art or (art.get("created_by") != user["id"] and user.get("role") not in EXEMPT_ROLES):
        raise HTTPException(404, "Laporan tidak ditemukan.")
    try:
        data, ct, name = await reports.artifact_file(artifact_id, kind)
    except (ValueError, FileNotFoundError):
        raise HTTPException(404, "Berkas laporan tidak ditemukan.")
    safe = re.sub(r"[^\w.\- ]+", "", name) or f"laporan.{kind}"
    return Response(data, media_type=ct, headers={"Content-Disposition": f'attachment; filename="{safe}"'})


# ---------------------------------------------------------------- pengaturan
async def _settings_view(org: str) -> dict:
    s = await config.get_ai_settings(org)
    row = await db.channel_accounts.find_one({"org_id": org, "code": config.ACCOUNT_CODE}, {"_id": 0, "key_last4": 1})
    has = bool(s.pop("has_api_key", False))
    s["has_key"], s["key_last4"] = has, (row or {}).get("key_last4") if has else None
    return s


@router.get("/settings")
async def get_settings(user: dict = Depends(_manage)):
    return {"data": await _settings_view(_org(user))}


@router.put("/settings")
async def put_settings(body: dict, user: dict = Depends(_manage)):
    if "category_modes" in body:
        raise HTTPException(400, "Mode kategori hanya bisa diubah lewat PUT /api/ai/categories/{kategori}.")
    bad = [k for k in body if k not in SETTING_KEYS]
    if bad:
        raise HTTPException(400, f"Pengaturan tidak dikenal: {', '.join(bad)}.")
    if "mode" in body and body["mode"] not in MODES:
        raise HTTPException(400, "Mode harus off, simulation, atau live.")
    bad_effort = [k for k in body if k.startswith("effort_") and body[k] not in EFFORTS]
    if bad_effort:  # salah ketik effort = 400 di mode live; tolak di sini
        raise HTTPException(400, f"Effort harus salah satu dari {', '.join(EFFORTS)}.")
    if any(k.startswith("model_") and not (isinstance(body[k], str) and body[k].startswith("claude-")) for k in body):
        raise HTTPException(400, "Model harus berupa ID model Claude (claude-...).")
    org = _org(user)
    for k, v in body.items():
        try:
            await ss.set_value(f"ai.{k}", v, actor=user["email"], reason="Pengaturan Estora AI", org_id=org)
        except ValueError as e:
            raise HTTPException(400, str(e))
    await audit_log(user, "ai_settings_updated", "ai_settings", org, {"keys": list(body)})
    return {"data": await _settings_view(org)}


class KeyIn(BaseModel):
    key: str


@router.put("/settings/api-key")
async def put_api_key(body: KeyIn, user: dict = Depends(_manage)):
    try:
        await config.save_api_key(_org(user), body.key, user["email"])
    except ValueError as e:
        raise HTTPException(400, str(e))
    await audit_log(user, "ai_api_key_saved", "ai_settings", _org(user), {})  # kunci tidak dicatat
    v = await _settings_view(_org(user))
    return {"data": {"has_key": v["has_key"], "key_last4": v["key_last4"]}}


@router.post("/settings/test")
async def test_connection(user: dict = Depends(_manage)):
    org = _org(user)
    s = await config.get_ai_settings(org)
    if s["effective_mode"] != "live":
        return {"data": {"ok": False, "simulated": True,
                         "message": "Mode simulasi: belum ada panggilan sungguhan ke Claude. "
                                    "Simpan kunci API dan pilih mode Live untuk menguji koneksi."}}
    try:
        claude = await get_claude(org)
        await claude.turn(model=s["model_triage"], system=[{"type": "text", "text": "Balas singkat."}],
                          messages=[{"role": "user", "content": [{"type": "text", "text": "ping"}]}],
                          tools=[], effort="low", max_tokens=16, on_text=None,
                          context={"purpose": "test_koneksi"})
    except ClaudeError as e:
        return {"data": {"ok": False, "message": f"Koneksi gagal ({e.kind}). Periksa kunci API dan coba lagi."}}
    return {"data": {"ok": True, "message": "Koneksi ke Claude berhasil."}}


@router.get("/usage")
async def usage(month: Optional[str] = None, user: dict = Depends(_manage)):
    org = _org(user)
    if month and not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", month):
        raise HTTPException(400, "Format bulan harus YYYY-MM.")
    b = await budget.budget_state(org)
    if month and month != budget._month():
        rows = await db.ai_usage.aggregate([{"$match": {"org_id": org, "month": month}},
                                            {"$group": {"_id": None, "t": {"$sum": "$cost_idr"}}}]).to_list(1)
        b["spent_idr"] = int(rows[0]["t"]) if rows else 0
        b["pct"] = round(b["spent_idr"] / b["limit_idr"] * 100.0, 2) if b["limit_idr"] > 0 else 100.0
    by = await db.ai_usage.aggregate([{"$match": {"org_id": org, "month": month or budget._month()}},
                                      {"$group": {"_id": "$model", "cost_idr": {"$sum": "$cost_idr"},
                                                  "calls": {"$sum": 1}}}]).to_list(20)
    b["month"] = month or budget._month()
    b["by_model"] = [{"model": r["_id"], "cost_idr": int(r["cost_idr"]), "calls": r["calls"]} for r in by]
    return {"data": b}
