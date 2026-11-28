"""wa_gateway_webhook_router — webhook pesan masuk dari gateway WhatsApp TIDAK resmi.

URL membawa secret (`/api/webhooks/wa-gateway/{secret}`); secret salah / kanal mati → 403.
Bentuk badan gateway dinormalisasi ke payload Meta lalu lewat `wa_inbound` (channel `unofficial`).
"""
from fastapi import APIRouter, HTTPException, Request

import wa_channels as wch
import wa_inbound as wi

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def _pick(d: dict, *keys):
    for k in keys:
        v = d.get(k)
        if v not in (None, ""):
            return v
    return None


def normalize(body: dict) -> dict:
    """Badan gateway generik → payload Meta (teks/media). Medan dikenali longgar."""
    phone = str(_pick(body, "from", "phone", "sender", "wa_id") or "")
    if not phone:
        raise ValueError("Nomor pengirim tidak ada pada payload gateway.")
    if not phone.startswith("+"):
        phone = "+" + phone.lstrip("+")
    mtype = str(_pick(body, "type", "message_type") or "text").lower()
    text = _pick(body, "text", "body", "message", "caption")
    if isinstance(text, dict):
        text = text.get("body")
    if mtype not in ("text",) + wi.MEDIA_TYPES:
        mtype = "text"
    return wi.build_meta_payload(phone=phone, name=_pick(body, "name", "push_name"), text=text,
                                 mtype=mtype, wamid=_pick(body, "id", "message_id"),
                                 filename=_pick(body, "filename"))


@router.post("/wa-gateway/{secret}")
async def wa_gateway_webhook(secret: str, request: Request):
    org_id = await wch.org_for_webhook_secret(secret)
    if not org_id:
        raise HTTPException(403, "Secret webhook gateway tidak valid atau kanal tidak aktif.")
    try:
        body = await request.json()
        raw = normalize(body if isinstance(body, dict) else {})
    except ValueError as e:
        raise HTTPException(400, str(e))
    summary = await wi.process_meta_payload(raw, org_id, mode="live", channel="unofficial")
    return {"data": {"received": True, "messages": summary["messages"], "duplicates": summary["duplicates"]}}
