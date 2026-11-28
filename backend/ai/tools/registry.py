"""Registri alat Estora AI: spesifikasi strict, validasi skema, lingkup (staf / WA terverifikasi), masking PII."""
import json
import logging
import re
import secrets
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Optional

import jsonschema

from ai import pii

logger = logging.getLogger("estora.ai.tools")

MAX_RESULT_CHARS = 24000
VERIFY_HINT = ("Data pribadi hanya bisa ditampilkan setelah nomor ini terverifikasi. "
               "Tawarkan verifikasi kepada pembeli (kode OTP ke nomor terdaftar) sebelum melanjutkan.")


@dataclass
class ToolContext:
    org_id: str
    user: dict
    token: str
    channel: str = "web"            # "web" | "wa" | "portal"
    conversation_id: Optional[str] = None
    contact: Optional[dict] = None  # {"phone","lead_id","buyer_customer_id"}
    verified: bool = False
    web_research: bool = False
    role: str = "copilot"           # "copilot" | "sales" | "cs" | "buyer_cs"


@dataclass
class Tool:
    name: str
    description: str
    input_schema: dict
    kind: str                       # "read" | "propose" | "report" | "handoff"
    scope: str                      # "staff" | "any" | "wa_self" | "portal"
    handler: Callable[[ToolContext, dict], Awaitable[dict]]
    label: str = ""
    untrusted: bool = False         # hasil memuat teks pihak luar (mis. pesan WA)


class ToolError(Exception):
    """Kesalahan alat yang pesannya aman ditampilkan ke model (Bahasa Indonesia)."""


_TOOLS: dict = {}


def register(tool: Tool) -> Tool:
    """Daftarkan alat (juga dipakai Task 6 untuk `buat_laporan`). Nama harus unik."""
    if tool.input_schema.get("additionalProperties") is not False:
        raise ValueError(f"Skema {tool.name} wajib additionalProperties: false")
    _TOOLS[tool.name] = tool
    return tool


def get(name: str) -> Optional[Tool]:
    return _TOOLS.get(name)


def all_tools() -> list:
    return list(_TOOLS.values())


PORTAL_SHARED = ("simulasi_kpr",)  # satu-satunya alat non-portal di kanal portal (hitungan murni, tanpa data)


def _visible(ctx: ToolContext, t: Tool) -> bool:
    # Kanal portal: HANYA alat portal (memanggil /api/portal/... dengan token pembeli) + simulasi KPR.
    # Sebaliknya alat portal tidak pernah tampil di kanal staf/WA.
    if ctx.channel == "portal":
        return t.scope == "portal" or t.name in PORTAL_SHARED
    if t.scope == "portal":
        return False
    if ctx.channel == "wa":
        if t.scope == "staff" or t.name in ("api_get", "cari_endpoint"):
            return False
        if t.scope == "wa_self":
            return ctx.verified
    return True


def tools_for(ctx: ToolContext) -> list:
    return [t for t in _TOOLS.values() if _visible(ctx, t)]


def api_specs(tools: list) -> list:
    return [{"name": t.name, "description": t.description, "input_schema": t.input_schema, "strict": True}
            for t in tools]


_TAG = re.compile(r"<\s*(/?)\s*data_tak_tepercaya", re.I)


def wrap_untrusted(text: str, nonce: str = None) -> str:
    """Bungkus teks pihak luar. Tag pembungkus yang ditulis pengirim sendiri dinetralkan (tidak bisa 'menutup' data)."""
    nonce = nonce or secrets.token_hex(4)
    safe = _TAG.sub(lambda m: f"‹{m.group(1)}data_tak_tepercaya", str(text or ""))
    return f'<data_tak_tepercaya id="{nonce}">{safe}</data_tak_tepercaya>'


def _cap(data):
    s = json.dumps(data, ensure_ascii=False, default=str)
    if len(s) <= MAX_RESULT_CHARS:
        return data
    if isinstance(data, dict):
        data = {k: (v[:20] if isinstance(v, list) else v) for k, v in data.items()}
    elif isinstance(data, list):
        data = data[:20]
    s = json.dumps(data, ensure_ascii=False, default=str)
    if len(s) > MAX_RESULT_CHARS:
        return {"terpotong": True, "isi": s[:MAX_RESULT_CHARS]}
    return data


def _fail(msg: str) -> dict:
    return {"ok": False, "data": None, "summary": msg, "error": msg}


async def run(ctx: ToolContext, name: str, inp: dict) -> dict:
    t = _TOOLS.get(name)
    if not t:
        return _fail(f"Alat '{name}' tidak dikenal.")
    if (ctx.channel == "portal" or t.scope == "portal") and not _visible(ctx, t):
        return _fail("Alat ini tidak tersedia di kanal ini.")
    if ctx.channel == "wa" and (t.scope == "staff" or name in ("api_get", "cari_endpoint")):
        return _fail("Alat ini tidak tersedia di WhatsApp.")
    if t.scope == "wa_self" and ctx.channel == "wa" and not (ctx.verified and (ctx.contact or {}).get("buyer_customer_id")):
        return _fail(VERIFY_HINT)
    try:
        jsonschema.validate(inp if inp is not None else {}, t.input_schema)
    except jsonschema.ValidationError as e:
        return _fail(f"Masukan tidak valid: {e.message}")
    try:
        out = await t.handler(ctx, inp or {})
    except ToolError as e:
        return _fail(str(e))
    except Exception as e:  # noqa: BLE001
        logger.exception("Alat %s gagal", name)
        return _fail(f"Alat gagal dijalankan: {type(e).__name__}")
    out = dict(out or {})
    summary = out.pop("summary", None) or (t.label or t.name)
    data = pii.mask(_cap(out), mask_phone=ctx.web_research)
    return {"ok": True, "data": data, "summary": summary, "error": None}
