"""Klien Claude (Messages API). Live → anthropic.AsyncAnthropic; tanpa kunci → SimulatedClaude."""
import hashlib
import logging
from typing import Awaitable, Callable, Optional, Protocol

import anthropic

from ai import budget, config
from db import ORG_ID

logger = logging.getLogger("estora.ai.client")

FALLBACK_BETA = "server-side-fallback-2026-07-01"
# Haiku tidak punya fallback sisi server: `fallbacks` tidak dikirim (bentuk daftar = 400, "default" = tanpa efek).
NO_SERVER_FALLBACK = ("claude-haiku",)


def supports_fallback(model: str) -> bool:
    return not str(model or "").startswith(NO_SERVER_FALLBACK)


class ClaudeError(Exception):
    def __init__(self, kind: str, message: str = "", retry_after: Optional[float] = None, status: Optional[int] = None):
        super().__init__(message or kind)
        self.kind, self.retry_after, self.status = kind, retry_after, status


class ClaudeLike(Protocol):
    async def turn(self, *, model: str, system: list, messages: list, tools: list, effort: str,
                   max_tokens: int, on_text: Optional[Callable[[str], Awaitable]], context: dict,
                   output_format: Optional[dict] = None) -> dict: ...


def map_error(e: Exception) -> ClaudeError:
    if isinstance(e, anthropic.APIStatusError):
        st = e.status_code
        ra = None
        try:
            ra = float(e.response.headers.get("retry-after"))
        except (TypeError, ValueError):
            pass
        if isinstance(e, anthropic.RateLimitError) or st == 429:
            return ClaudeError("rate_limit", str(e), ra, st)
        if isinstance(e, anthropic.OverloadedError) or st in (500, 502, 503, 504, 529):
            return ClaudeError("overloaded", str(e), ra, st)
        if st in (401, 403):
            return ClaudeError("auth", str(e), None, st)
        return ClaudeError("bad_request", str(e), None, st)
    if isinstance(e, anthropic.APIConnectionError):  # termasuk timeout
        return ClaudeError("network", str(e))
    return ClaudeError("network", str(e))


def _with_cache(blocks: list) -> list:
    out = [dict(b) for b in blocks]
    if out:
        out[-1]["cache_control"] = {"type": "ephemeral"}
    return out


class LiveClaude:
    def __init__(self, org_id: str, api_key: str = None, *, http_client=None, max_retries: int = 2, client=None):
        self.org_id = org_id
        self.client = client or anthropic.AsyncAnthropic(api_key=api_key, http_client=http_client, max_retries=max_retries)

    def build_request(self, *, model, system, messages, tools, effort, max_tokens, streaming, output_format=None) -> dict:
        tools = _with_cache(tools or [])
        if streaming:
            tools = [{**t, "eager_input_streaming": True} if "input_schema" in t else t for t in tools]
        oc = {"effort": effort}
        if output_format:
            oc["format"] = output_format
        req = {"model": model, "max_tokens": max_tokens, "system": _with_cache(system or []),
               "messages": messages, "thinking": {"type": "adaptive"}, "output_config": oc}
        if supports_fallback(model):
            req.update({"betas": [FALLBACK_BETA], "fallbacks": "default"})
        if tools:
            req["tools"] = tools
        return req

    async def _record_partial(self, stream, model, context) -> None:
        """Stream gagal di tengah jalan: catat usage yang sudah terkumpul (bila ada) supaya biayanya tidak hilang."""
        try:
            snap = stream.current_message_snapshot if stream is not None else None
            usage = snap.usage.model_dump(exclude_none=True) if snap is not None and snap.usage else {}
            if usage:
                await budget.record_usage(self.org_id, model=str(snap.model or model), usage=usage,
                                          context={**(context or {}), "partial": True})
        except Exception:  # noqa: BLE001  (belum ada snapshot / pencatatan gagal: jangan menutupi error asli)
            logger.debug("Usage stream gagal tak tercatat", exc_info=True)

    async def turn(self, *, model, system, messages, tools, effort, max_tokens, on_text, context,
                   output_format=None) -> dict:
        req = self.build_request(model=model, system=system, messages=messages, tools=tools, effort=effort,
                                 max_tokens=max_tokens, streaming=on_text is not None, output_format=output_format)
        stream = None
        try:
            if on_text is not None:
                async with self.client.beta.messages.stream(**req) as stream:
                    async for t in stream.text_stream:
                        await on_text(t)
                    msg = await stream.get_final_message()
            else:
                msg = await self.client.beta.messages.create(**req)
        except anthropic.AnthropicError as e:
            await self._record_partial(stream, model, context)
            raise map_error(e) from e
        usage = msg.usage.model_dump(exclude_none=True) if msg.usage else {}
        out_model = str(msg.model or model)
        await budget.record_usage(self.org_id, model=out_model, usage=usage, context=context or {})
        # stop_reason diperiksa pemanggil SEBELUM membaca content; blok (termasuk thinking) dibiarkan utuh.
        return {"content": [b.model_dump(exclude_none=True) for b in (msg.content or [])],
                "stop_reason": msg.stop_reason,
                "stop_details": getattr(msg, "stop_details", None) and msg.stop_details.model_dump(exclude_none=True),
                "usage": usage, "model": out_model}


_override = None
_clients: dict = {}  # org_id -> (sha256 kunci, AsyncAnthropic): satu pool koneksi per org, ditutup saat kunci diganti


def set_override(obj) -> None:
    global _override
    _override = obj


async def _client_for(org_id: str, key: str):
    digest = hashlib.sha256(key.encode()).hexdigest()
    cur = _clients.get(org_id)
    if cur and cur[0] == digest:
        return cur[1]
    client = anthropic.AsyncAnthropic(api_key=key, max_retries=2)
    _clients[org_id] = (digest, client)
    if cur:  # kunci diganti: tutup pool lama
        try:
            await cur[1].close()
        except Exception:  # noqa: BLE001
            logger.warning("Gagal menutup klien Anthropic lama", exc_info=True)
    return client


async def get_claude(org_id: str = ORG_ID) -> ClaudeLike:
    if _override is not None:
        return _override
    s = await config.get_ai_settings(org_id)
    key = await config.get_api_key(org_id) if s["effective_mode"] == "live" else None
    if key:
        return LiveClaude(org_id, client=await _client_for(org_id, key))
    from ai.simulated import SimulatedClaude
    return SimulatedClaude(org_id)
