"""ai_channels_router — `/api/ai/channels`: pengaturan kanal WhatsApp (resmi + gateway tidak resmi)."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

import wa_channels as wch
import wa_gateway as gw
from db import ORG_ID
from rbac import audit_log, require_permission

router = APIRouter(prefix="/ai/channels", tags=["ai-channels"])
_manage = require_permission("ai_settings", "manage")


class UnofficialIn(BaseModel):
    enabled: Optional[bool] = None
    base_url: Optional[str] = None
    token: Optional[str] = None
    send_path: Optional[str] = None
    payload_template: Optional[str] = None
    webhook_secret: Optional[str] = None
    hourly_limit: Optional[int] = None
    phone: Optional[str] = None


class ChannelsIn(BaseModel):
    official_mode: Optional[str] = None  # cloud | coexistence
    unofficial: Optional[UnofficialIn] = None


def _org(user: dict) -> str:
    return user.get("org_id", ORG_ID)


async def _view(org_id: str) -> dict:
    cfg = await gw.get_config(org_id)
    un = await wch.get_unofficial_config(org_id)
    un["sent_last_hour"] = await wch.sent_last_hour(org_id)
    return {"official": {"mode": wch.channel_mode(cfg), "effective_mode": cfg["effective_mode"],
                         "live_ready": cfg["live_ready"], "channel": wch.official_channel_name(cfg)},
            "unofficial": un}


@router.get("")
async def get_channels(user: dict = Depends(_manage)):
    return {"data": await _view(_org(user))}


@router.put("")
async def put_channels(body: ChannelsIn, user: dict = Depends(_manage)):
    org = _org(user)
    fields = sorted(body.unofficial.model_dump(exclude_none=True)) if body.unofficial else []
    try:
        if body.official_mode is not None:
            await wch.set_official_mode(org, body.official_mode, actor=user["email"])
        if body.unofficial is not None:
            await wch.save_unofficial_config(org, body.unofficial.model_dump(exclude_none=True), actor=user["email"])
    except ValueError as e:
        raise HTTPException(400, str(e))
    await audit_log(user, "update", "ai_channels", "channels",
                    meta={"official_mode": body.official_mode, "unofficial_fields": fields})
    return {"data": await _view(org)}


@router.post("/unofficial/disable")
async def disable_unofficial(user: dict = Depends(_manage)):
    org = _org(user)
    await wch.disable_unofficial(org, actor=user["email"])
    await audit_log(user, "update", "ai_channels", "unofficial", meta={"kill_switch": True})
    return {"data": await _view(org)}
