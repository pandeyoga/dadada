"""Riset web terkendali: server tool hanya bila diizinkan, pencatatan kueri, deteksi PII -> insiden + matikan."""
import re

import settings_store as ss
from core_utils import new_id, now_iso
from db import db

SERVER_TOOLS = [{"type": "web_search_20260209", "name": "web_search", "max_uses": 5},
                {"type": "web_fetch_20260209", "name": "web_fetch", "max_uses": 5}]
WEB_NAMES = ("web_search", "web_fetch")
_PII = re.compile(r"\b\d{16}\b|(?<!\d)(?:\+?62|0)8[\d\s.-]{8,13}\d|[\w.+-]+@[\w-]+\.[\w.-]+")


def has_pii(text: str) -> bool:
    return bool(_PII.search(text or ""))


async def enabled_for(ctx, conv_id: str) -> bool:
    if not ctx.web_research or not await ss.get("ai.web_research_enabled", org_id=ctx.org_id):
        return False
    c = await db.ai_conversations.find_one({"id": conv_id}, {"_id": 0, "web_disabled": 1})
    return not (c or {}).get("web_disabled")


async def extra_tools(ctx, conv_id: str) -> list:
    return [dict(t) for t in SERVER_TOOLS] if await enabled_for(ctx, conv_id) else []


async def record(ctx, conv_id: str, content: list) -> bool:
    """Catat setiap server_tool_use web; True bila riset dimatikan karena PII."""
    tripped = False
    for b in content or []:
        if b.get("type") != "server_tool_use" or b.get("name") not in WEB_NAMES:
            continue
        inp = b.get("input") or {}
        q = str(inp.get("query") or inp.get("url") or "")
        pii = has_pii(q)
        await db.ai_web_queries.insert_one({
            "id": new_id(), "org_id": ctx.org_id, "conversation_id": conv_id, "tool": b["name"],
            "query": "[DIMASKER: berisi data pribadi]" if pii else q[:500], "pii_blocked": pii, "created_at": now_iso()})
        if pii:
            tripped = True
            await db.ai_incidents.insert_one({
                "id": new_id(), "org_id": ctx.org_id, "conversation_id": conv_id, "kind": "web_query_pii",
                "detail": "Kueri riset web memuat pola NIK/telepon/email; riset web dimatikan untuk percakapan ini.",
                "created_at": now_iso()})
    if tripped:
        await db.ai_conversations.update_one({"id": conv_id}, {"$set": {"web_disabled": True}})
    return tripped
