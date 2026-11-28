"""portal_ai_router — `/api/portal/ai`: chat "Tanya Estora" untuk pembeli (auth portal, bukan JWT staf).

Amplop `{"data": ...}`. Pesan dikirim sebagai SSE (`data: <json>\\n\\n`) dengan peristiwa yang sama dengan Copilot
(`step_started|step_done|text_delta|action_proposed|done|error`) ditambah `handoff {"ticket": {...}}`.
Aksi (komplain / klaim garansi) hanya dieksekusi oleh pembeli pemiliknya lewat `/actions/{id}/confirm`.
"""
import asyncio
import json

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ai import actions, conversations, portal_agent
from db import db, ORG_ID
from portal_security import _candidates, get_portal_user
from security import JWT_ALGORITHM, get_jwt_secret

router = APIRouter(prefix="/portal/ai", tags=["portal-ai"])
MAX_TEXT = 4000
CONV_KEYS = ("id", "title", "created_at", "updated_at")


def _org(pu: dict) -> str:
    return pu.get("org_id", ORG_ID)


def _token(request: Request, pu: dict) -> str:
    """Token portal yang SAMA dengan yang diterima `get_portal_user` (header dulu, lalu cookie, lalu ?auth=)."""
    for tok in _candidates(request):
        try:
            claims = jwt.decode(tok, get_jwt_secret(), algorithms=[JWT_ALGORITHM])
        except jwt.InvalidTokenError:
            continue
        if claims.get("type") == "portal" and claims.get("sub") == pu["id"]:
            return tok
    raise HTTPException(401, "Sesi portal Anda tidak dikenali. Silakan masuk kembali dengan kode OTP.")


async def _own_conv(conv_id: str, pu: dict) -> dict:
    c = await db.ai_conversations.find_one({"id": conv_id}, {"_id": 0})
    if not c or c.get("owner_id") != pu["id"] or c.get("channel") != "portal":
        raise HTTPException(404, "Percakapan tidak ditemukan.")
    return c


async def _require_enabled(pu: dict) -> None:
    on, _s = await portal_agent.enabled(_org(pu))
    if not on:
        raise HTTPException(403, portal_agent.DISABLED_MSG)


async def _drop(conv_ids: list) -> None:
    """Hapus percakapan + pesan; usulan yang masih menunggu dibatalkan (tidak bisa dikonfirmasi lagi)."""
    if not conv_ids:
        return
    await db.ai_actions.update_many({"conversation_id": {"$in": conv_ids}, "status": "pending"},
                                    {"$set": {"status": "cancelled", "summary": "Riwayat chat dihapus pembeli."}})
    await db.ai_messages.delete_many({"conversation_id": {"$in": conv_ids}})
    await db.ai_conversations.delete_many({"id": {"$in": conv_ids}, "channel": "portal"})


# ---------------------------------------------------------------- status & privasi
@router.get("/status")
async def get_status(pu: dict = Depends(get_portal_user)):
    return {"data": await portal_agent.status(pu)}


@router.post("/notice/ack")
async def ack_notice(pu: dict = Depends(get_portal_user)):
    await portal_agent.mark_noticed(pu)
    return {"data": await portal_agent.status(pu)}


@router.post("/stop")
async def stop_assistant(pu: dict = Depends(get_portal_user)):
    await portal_agent.stop(pu)
    return {"data": await portal_agent.status(pu)}


@router.post("/resume")
async def resume_assistant(pu: dict = Depends(get_portal_user)):
    await portal_agent.resume(pu)
    return {"data": await portal_agent.status(pu)}


# ---------------------------------------------------------------- percakapan
@router.get("/conversations")
async def list_conversations(pu: dict = Depends(get_portal_user)):
    rows = await conversations.list_for(pu["id"])
    return {"data": [{k: r.get(k) for k in CONV_KEYS} for r in rows if r.get("channel") == "portal"]}


@router.post("/conversations")
async def create_conversation(pu: dict = Depends(get_portal_user)):
    await _require_enabled(pu)
    c = await conversations.create(_org(pu), pu["id"], role="buyer_cs", channel="portal")
    return {"data": {k: c.get(k) for k in CONV_KEYS}}


@router.delete("/conversations")
async def delete_all_conversations(pu: dict = Depends(get_portal_user)):
    ids = [c["id"] async for c in db.ai_conversations.find({"owner_id": pu["id"], "channel": "portal"}, {"_id": 0, "id": 1})]
    await _drop(ids)
    return {"data": {"deleted": len(ids)}}


@router.get("/conversations/{conv_id}")
async def get_conversation(conv_id: str, pu: dict = Depends(get_portal_user)):
    await _own_conv(conv_id, pu)
    return {"data": await portal_agent.conversation_view(conv_id, pu)}


@router.delete("/conversations/{conv_id}")
async def delete_conversation(conv_id: str, pu: dict = Depends(get_portal_user)):
    await _own_conv(conv_id, pu)
    await _drop([conv_id])
    return {"data": {"deleted": True}}


class MessageIn(BaseModel):
    text: str


def _sse(ev: dict) -> bytes:
    return f"data: {json.dumps(ev, ensure_ascii=False, default=str)}\n\n".encode()


@router.post("/conversations/{conv_id}/messages")
async def send_message(conv_id: str, body: MessageIn, request: Request, pu: dict = Depends(get_portal_user)):
    await _own_conv(conv_id, pu)
    text = (body.text or "").strip()
    if not text:
        raise HTTPException(400, "Pesan tidak boleh kosong.")
    if len(text) > MAX_TEXT:
        raise HTTPException(400, f"Pesan terlalu panjang (maksimal {MAX_TEXT} karakter).")
    await _require_enabled(pu)
    token = _token(request, pu)

    async def stream():
        gen = portal_agent.handle_message(pu, token, conv_id, text)
        partial, finished = [], False
        try:
            async for ev in gen:
                if ev.get("type") == "text_delta" and not ev.get("saved"):
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


# ---------------------------------------------------------------- konfirmasi aksi pembeli
def _action_out(a: dict) -> dict:
    return {"data": {"action": portal_agent.action_view(a)}}


@router.post("/actions/{action_id}/confirm")
async def confirm_action(action_id: str, request: Request, pu: dict = Depends(get_portal_user)):
    try:
        a = await actions.confirm_by_buyer(action_id, pu, _token(request, pu))
    except actions.ActionError as e:
        raise HTTPException(e.status, e.message)
    return _action_out(a)


@router.post("/actions/{action_id}/cancel")
async def cancel_action(action_id: str, pu: dict = Depends(get_portal_user)):
    try:
        a = await actions.cancel_by_buyer(action_id, pu)
    except actions.ActionError as e:
        raise HTTPException(e.status, e.message)
    return _action_out(a)
