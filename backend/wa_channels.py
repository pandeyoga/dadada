"""wa_channels — pemilihan kanal WhatsApp: resmi (Cloud / Coexistence) + gateway TIDAK resmi.

Aturan pemilik (Estora AI tahap 1):
- 1 nomor resmi (`cloud` ATAU `coexistence`, satu mode aktif) + opsional 1 nomor `unofficial`.
- Gateway tidak resmi: tanpa AI auto-send, tanpa broadcast/playbook, batas default 20 pesan/jam,
  hanya kontak ber-opt-in `unofficial`, dan ada kill switch. Token dienkripsi, tidak pernah
  dikembalikan lewat API.
- Coexistence memakai jalur Graph API yang sama dengan Cloud; bedanya hanya penanda kanal dan
  penanganan `smb_message_echoes` (pesan dari aplikasi WhatsApp Business di HP sales).
"""
import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone

import httpx

import wa_gateway as gw
from core_utils import new_id, now_iso
from db import db, ORG_ID

logger = logging.getLogger("sipro.wa_channels")

UNOFFICIAL_CODE = "wa_unofficial"
OFFICIAL_MODES = ("cloud", "coexistence")
DEFAULT_HOURLY_LIMIT = 20
DEFAULT_TEMPLATE = '{"to": "{to}", "text": "{text}", "media_url": "{media_url}"}'
BLOCKED_KINDS = ("broadcast", "playbook")
COUNTED_STATUS = ("sent", "simulated", "failed")
TRANSPORT = None  # httpx.MockTransport untuk pengujian


# ------------------------------------------------------------------ resmi
class CoexistenceAdapter(gw.MetaCloudAdapter):
    """Coexistence: nomor yang sama dipakai API dan aplikasi WhatsApp Business. Jalur kirim = Graph API."""
    channel = "coexistence"


def channel_mode(cfg: dict) -> str:
    m = cfg.get("channel_mode")
    return m if m in OFFICIAL_MODES else "cloud"


def official_channel_name(cfg: dict) -> str:
    """Nilai `messages.channel` untuk kanal resmi: cloud|coexistence|simulation."""
    if cfg.get("effective_mode") != "live":
        return "simulation"
    return channel_mode(cfg)


async def official_adapter(org_id: str = ORG_ID):
    cfg = await gw.get_config(org_id)
    if cfg["effective_mode"] == "live":
        cls = CoexistenceAdapter if channel_mode(cfg) == "coexistence" else gw.MetaCloudAdapter
        return cls(cfg["creds"]), cfg
    return gw.SimulationAdapter(), cfg


async def set_official_mode(org_id: str, mode: str, actor: str = "") -> None:
    if mode not in OFFICIAL_MODES:
        raise ValueError("Mode kanal resmi harus 'cloud' atau 'coexistence'.")
    ch = await gw._channel(org_id)
    await db.channel_accounts.update_one({"id": ch["id"]}, {"$set": {
        "channel_mode": mode, "updated_at": now_iso(), "updated_by": actor}})


# ------------------------------------------------------------------ tidak resmi: konfigurasi
async def _unofficial_row(org_id: str) -> dict:
    row = await db.channel_accounts.find_one({"org_id": org_id, "code": UNOFFICIAL_CODE}, {"_id": 0})
    if row:
        return row
    row = {"id": new_id(), "org_id": org_id, "code": UNOFFICIAL_CODE, "channel": "whatsapp",
           "name": "WhatsApp Gateway (tidak resmi)", "mode": "unofficial", "enabled": False,
           "is_active": True, "base_url": "", "send_path": "/send", "payload_template": DEFAULT_TEMPLATE,
           "hourly_limit": DEFAULT_HOURLY_LIMIT, "phone": "", "created_by": "system", "created_at": now_iso()}
    await db.channel_accounts.insert_one(dict(row))
    return row


def _secret_hash(secret: str) -> str:
    return hashlib.sha256(secret.encode()).hexdigest()


async def get_unofficial_config(org_id: str = ORG_ID) -> dict:
    """Konfigurasi tanpa rahasia: token & secret hanya muncul sebagai penanda `*_set`."""
    row = await _unofficial_row(org_id)
    return {"enabled": bool(row.get("enabled")), "base_url": row.get("base_url") or "",
            "send_path": row.get("send_path") or "/send",
            "payload_template": row.get("payload_template") or DEFAULT_TEMPLATE,
            "hourly_limit": int(row.get("hourly_limit") or DEFAULT_HOURLY_LIMIT),
            "phone": row.get("phone") or "", "token_set": bool(row.get("token_enc")),
            "webhook_secret_set": bool(row.get("webhook_secret_hash")),
            "webhook_path": "/api/webhooks/wa-gateway/{secret}",
            "disabled_at": row.get("disabled_at"), "disabled_by": row.get("disabled_by")}


async def save_unofficial_config(org_id: str, data: dict, actor: str = "") -> dict:
    row = await _unofficial_row(org_id)
    upd = {"updated_at": now_iso(), "updated_by": actor}
    for k in ("base_url", "send_path", "phone"):
        if data.get(k) is not None:
            upd[k] = str(data[k]).strip()
    if upd.get("base_url") and not upd["base_url"].lower().startswith(("https://", "http://")):
        raise ValueError("Base URL gateway harus diawali http:// atau https://.")
    if data.get("payload_template") is not None:
        tpl = data["payload_template"]
        tpl = tpl if isinstance(tpl, str) else json.dumps(tpl)
        try:
            json.loads(tpl)
        except ValueError:
            raise ValueError("Templat payload bukan JSON yang valid.")
        upd["payload_template"] = tpl
    if data.get("hourly_limit") is not None:
        lim = int(data["hourly_limit"])
        if lim < 1 or lim > 1000:
            raise ValueError("Batas per jam harus antara 1 dan 1000.")
        upd["hourly_limit"] = lim
    if data.get("token"):
        upd["token_enc"] = gw.encrypt(data["token"].strip())
    if data.get("webhook_secret"):
        sec = data["webhook_secret"].strip()
        if len(sec) < 16:
            raise ValueError("Secret webhook minimal 16 karakter.")
        upd["webhook_secret_hash"] = _secret_hash(sec)
        upd["webhook_secret_enc"] = gw.encrypt(sec)
    if data.get("enabled") is not None:
        want = bool(data["enabled"])
        merged = {**row, **upd}
        if want and not (merged.get("base_url") and merged.get("token_enc")):
            raise ValueError("Isi Base URL dan token gateway sebelum mengaktifkan kanal tidak resmi.")
        upd["enabled"] = want
        if want:
            upd.update({"disabled_at": None, "disabled_by": None})
    await db.channel_accounts.update_one({"id": row["id"]}, {"$set": upd})
    return await get_unofficial_config(org_id)


async def disable_unofficial(org_id: str, actor: str = "") -> dict:
    """Kill switch: matikan seketika."""
    row = await _unofficial_row(org_id)
    await db.channel_accounts.update_one({"id": row["id"]}, {"$set": {
        "enabled": False, "disabled_at": now_iso(), "disabled_by": actor}})
    return await get_unofficial_config(org_id)


async def org_for_webhook_secret(secret: str):
    """-> org_id bila secret cocok dan kanal aktif, selain itu None."""
    if not secret:
        return None
    row = await db.channel_accounts.find_one(
        {"code": UNOFFICIAL_CODE, "webhook_secret_hash": _secret_hash(secret)}, {"_id": 0, "org_id": 1, "enabled": 1})
    return row["org_id"] if row and row.get("enabled") else None


# ------------------------------------------------------------------ tidak resmi: adapter
def _fill(node, vals: dict):
    if isinstance(node, str):
        for k, v in vals.items():
            node = node.replace("{" + k + "}", v)
        return node
    if isinstance(node, list):
        return [_fill(x, vals) for x in node]
    if isinstance(node, dict):
        return {k: _fill(v, vals) for k, v in node.items()}
    return node


def render_payload(template: str, *, to: str, text: str, media_url: str = "") -> dict:
    return _fill(json.loads(template), {"to": to, "text": text or "", "media_url": media_url or ""})


class UnofficialGatewayAdapter:
    mode = "live"
    channel = "unofficial"

    def __init__(self, cfg: dict, token: str, transport=None):
        self.base_url = (cfg.get("base_url") or "").rstrip("/")
        self.send_path = "/" + (cfg.get("send_path") or "/send").lstrip("/")
        self.template = cfg.get("payload_template") or DEFAULT_TEMPLATE
        self.token = token
        self.transport = transport

    async def send(self, payload: dict) -> dict:
        body = render_payload(self.template, to=payload["to"], text=payload.get("text", ""),
                              media_url=payload.get("media_url", ""))
        try:
            async with httpx.AsyncClient(timeout=20, transport=self.transport) as cli:
                resp = await cli.post(self.base_url + self.send_path, json=body,
                                      headers={"Authorization": f"Bearer {self.token}"})
        except httpx.HTTPError as e:
            return gw._fail("network", str(e)[:200])
        if resp.status_code >= 300:
            return gw._fail(str(resp.status_code), resp.text[:200])
        try:
            data = resp.json()
        except ValueError:
            data = {}
        pid = None
        if isinstance(data, dict):
            pid = data.get("id") or data.get("message_id") or (data.get("data") or {}).get("id")
        return {"ok": True, "status": "sent", "provider_message_id": pid or f"gw-{new_id()}",
                "error_code": None, "error_detail": None}

    async def probe(self) -> dict:
        return {"ok": bool(self.base_url), "mode": "unofficial", "detail": "Gateway tidak resmi."}


async def unofficial_adapter(org_id: str = ORG_ID, transport=None):
    """-> adapter bila kanal aktif & kredensial lengkap, selain itu None."""
    row = await _unofficial_row(org_id)
    if not row.get("enabled") or not row.get("base_url") or not row.get("token_enc"):
        return None
    return UnofficialGatewayAdapter(row, gw.decrypt(row["token_enc"]), transport or TRANSPORT)


# ------------------------------------------------------------------ opt-in & kirim
async def has_unofficial_optin(org_id: str, phone: str) -> bool:
    """Sumber kebenaran: `ai.consent.state`."""
    from ai import consent
    return bool((await consent.state(org_id, phone))["optins"]["unofficial"])


async def sent_last_hour(org_id: str) -> int:
    since = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    return await db.messages.count_documents({
        "org_id": org_id, "channel": "unofficial", "direction": "out",
        "status": {"$in": list(COUNTED_STATUS)}, "created_at": {"$gte": since}})


def _block(code: str, detail: str) -> dict:
    return {**gw._fail(code, detail), "status": "blocked"}


async def send_unofficial(org_id: str, to: str, text: str, *, actor: str, ai_generated: bool,
                          kind: str = "inbox", conversation_id: str = None, media_url: str = None,
                          transport=None) -> dict:
    """Kirim lewat gateway tidak resmi dengan semua pengaman. Selalu mencatat `messages`."""
    ts = now_iso()
    dest = gw.valid_phone(to)
    res = None
    row = await _unofficial_row(org_id)
    if kind in BLOCKED_KINDS:
        res = _block("unofficial_kind_blocked", "Broadcast dan playbook tidak boleh lewat nomor tidak resmi.")
    elif not row.get("enabled"):
        res = _block("channel_disabled", "Kanal WhatsApp tidak resmi sedang nonaktif.")
    elif ai_generated or actor == "ai-auto":
        res = _block("ai_auto_blocked", "AI tidak boleh mengirim otomatis lewat nomor tidak resmi.")
    elif not dest:
        res = _block("invalid_phone", f"Nomor tidak valid / bukan +62: {to!r}")
    elif not await has_unofficial_optin(org_id, dest):
        res = _block("no_optin", "Kontak belum memberi persetujuan (opt-in) untuk kanal tidak resmi.")
    elif await sent_last_hour(org_id) >= int(row.get("hourly_limit") or DEFAULT_HOURLY_LIMIT):
        res = {**_block("rate_limited", "Batas pesan per jam untuk nomor tidak resmi tercapai."),
               "status": "rate_limited"}
    if res is None:
        adapter = await unofficial_adapter(org_id, transport)
        if adapter is None:
            res = _block("channel_disabled", "Kredensial gateway tidak lengkap.")
        else:
            res = await adapter.send({"to": dest.lstrip("+"), "text": text, "media_url": media_url or ""})
    msg = {"id": new_id(), "org_id": org_id, "conversation_id": conversation_id, "direction": "out",
           "body": text, "sender": actor, "is_template": False, "kind": kind, "category": "service",
           "to": dest or to, "mode": "live", "channel": "unofficial", "ref": {}, "document": None,
           "created_at": ts, "status_at": ts, "warning": None, "status": res["status"],
           "provider_message_id": res.get("provider_message_id"),
           "error_code": res.get("error_code"), "error_detail": res.get("error_detail")}
    await db.messages.insert_one(dict(msg))
    return msg
