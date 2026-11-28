"""ai_inbox_router — draf AI di Inbox, tinjauan sampel, akurasi & mode per kategori (`/api/ai/...`)."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

import settings_store as ss
from ai import accuracy, config, drafts, triage
from db import db, ORG_ID
from rbac import audit_log, require_permission
from routers.inbox_router import _get_conv_scoped

router = APIRouter(prefix="/ai", tags=["ai-inbox"])
_use = require_permission("ai_inbox", "use")
_manage = require_permission("ai_settings", "manage")


def _org(u: dict) -> str:
    return u.get("org_id", ORG_ID)


async def _guard(draft_id: str, user: dict) -> dict:
    d = await db.ai_drafts.find_one({"id": draft_id, "org_id": _org(user)}, {"_id": 0})
    if not d:
        raise HTTPException(404, "Draf tidak ditemukan.")
    await _get_conv_scoped(d["conversation_id"], user)  # sales hanya percakapannya sendiri
    return d


async def _run(coro):
    try:
        return await coro
    except drafts.DraftError as e:
        raise HTTPException(e.status, e.message)
    except (LookupError, ValueError) as e:
        raise HTTPException(400 if isinstance(e, ValueError) else 404, str(e))


@router.get("/inbox/conversations/{conv_id}")
async def inbox_conversation(conv_id: str, user: dict = Depends(_use)):
    conv = await _get_conv_scoped(conv_id, user)
    return {"data": await drafts.inbox_view(_org(user), conv)}


@router.get("/inbox/labels")
async def inbox_labels(ids: str = "", user: dict = Depends(_use)):
    wanted = [i for i in ids.split(",") if i][:200]
    return {"data": await drafts.labels_for(_org(user), wanted)}


class SendIn(BaseModel):
    text: Optional[str] = None


class RewriteIn(BaseModel):
    instruction: str


class ReviewIn(BaseModel):
    verdict: str


class ModeIn(BaseModel):
    mode: str


@router.post("/inbox/drafts/{draft_id}/send")
async def send_draft(draft_id: str, body: SendIn, user: dict = Depends(_use)):
    await _guard(draft_id, user)
    out = await _run(drafts.send(draft_id, _org(user), user, body.text))
    await audit_log(user, "send", "ai_drafts", draft_id, {"edited": out["status"] == "edited", "similarity": out["similarity"]})
    return {"data": drafts.public(out)}


@router.post("/inbox/drafts/{draft_id}/rewrite")
async def rewrite_draft(draft_id: str, body: RewriteIn, user: dict = Depends(_use)):
    await _guard(draft_id, user)
    if not body.instruction.strip():
        raise HTTPException(400, "Instruksi tulis ulang kosong.")
    out = await _run(drafts.rewrite(draft_id, _org(user), body.instruction.strip()[:500]))
    return {"data": {**drafts.public(out), "draft": drafts.public(out)}}


@router.post("/inbox/drafts/{draft_id}/discard")
async def discard_draft(draft_id: str, user: dict = Depends(_use)):
    await _guard(draft_id, user)
    out = await _run(drafts.discard(draft_id, _org(user)))
    await audit_log(user, "discard", "ai_drafts", draft_id, {})
    return {"data": drafts.public(out)}


@router.post("/inbox/samples/{draft_id}/review")
async def review_sample(draft_id: str, body: ReviewIn, user: dict = Depends(_use)):
    await _guard(draft_id, user)
    out = await _run(accuracy.review_sample(draft_id, body.verdict, user))
    await audit_log(user, "review", "ai_drafts", draft_id, {"verdict": body.verdict})
    return {"data": drafts.public(out)}


# ---------------------------------------------------------------- akurasi & mode kategori
async def _row(org: str, cat: str, modes: dict) -> dict:
    label, desc = triage.CATEGORY_INFO[cat]
    if cat in triage.LOCKED:
        return {"category": cat, "label": label, "description": desc, "accuracy": None, "samples": 0, "mode": "handoff",
                "locked": True, "can_enable_auto": False, "reason": accuracy.LOCKED_REASON}
    st = await accuracy.stats(org, cat)
    ok, why = await accuracy.can_enable_auto(org, cat)
    return {"category": cat, "label": label, "description": desc, "accuracy": st["accuracy"], "samples": st["samples"],
            "mode": (modes or {}).get(cat, "draft"), "locked": False, "can_enable_auto": ok, "reason": why}


@router.get("/accuracy")
async def accuracy_table(user: dict = Depends(_manage)):
    org = _org(user)
    modes = await ss.get("ai.category_modes", org_id=org)
    return {"data": [await _row(org, c, modes) for c in triage.CATEGORY_INFO]}


@router.put("/categories/{cat}")
async def set_category(cat: str, body: ModeIn, user: dict = Depends(_manage)):
    org = _org(user)
    if cat not in triage.CATEGORY_INFO:
        raise HTTPException(404, "Kategori tidak dikenal.")
    if cat in triage.LOCKED:
        raise HTTPException(400, accuracy.LOCKED_REASON)
    if body.mode not in config.CATEGORY_MODES:
        raise HTTPException(400, "Mode harus auto, draft, atau off.")
    if body.mode == "auto":
        ok, why = await accuracy.can_enable_auto(org, cat)
        if not ok:
            raise HTTPException(400, f"Mode Otomatis belum bisa dipilih. {why}")
    try:
        modes = await config.set_category_mode(org, cat, body.mode, user.get("email"))
    except ValueError as e:
        raise HTTPException(400, str(e))
    await audit_log(user, "update", "ai_category_mode", cat, {"mode": body.mode})
    return {"data": await _row(org, cat, modes)}
