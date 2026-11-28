"""Klien Claude (Messages API). Live → anthropic.AsyncAnthropic; tanpa kunci → SimulatedClaude."""
import logging
from typing import Awaitable, Callable, Optional, Protocol

import anthropic

from ai import budget, config
from db import ORG_ID

logger = logging.getLogger("estora.ai.client")

FALLBACK_BETA = "server-side-fallback-2026-07-01"


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
    def __init__(self, org_id: str, api_key: str, *, http_client=None, max_retries: int = 2):
        self.org_id = org_id
        self.client = anthropic.AsyncAnthropic(api_key=api_key, http_client=http_client, max_retries=max_retries)

    def build_request(self, *, model, system, messages, tools, effort, max_tokens, streaming, output_format=None) -> dict:
        tools = _with_cache(tools or [])
        if streaming:
            tools = [{**t, "eager_input_streaming": True} if "input_schema" in t else t for t in tools]
        oc = {"effort": effort}
        if output_format:
            oc["format"] = output_format
        req = {"model": model, "max_tokens": max_tokens, "system": _with_cache(system or []),
               "messages": messages, "thinking": {"type": "adaptive"}, "output_config": oc,
               "betas": [FALLBACK_BETA], "fallbacks": "default"}
        if tools:
            req["tools"] = tools
        return req

    async def turn(self, *, model, system, messages, tools, effort, max_tokens, on_text, context,
                   output_format=None) -> dict:
        req = self.build_request(model=model, system=system, messages=messages, tools=tools, effort=effort,
                                 max_tokens=max_tokens, streaming=on_text is not None, output_format=output_format)
        try:
            if on_text is not None:
                async with self.client.beta.messages.stream(**req) as s:
                    async for t in s.text_stream:
                        await on_text(t)
                    msg = await s.get_final_message()
            else:
                msg = await self.client.beta.messages.create(**req)
        except anthropic.AnthropicError as e:
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


def set_override(obj) -> None:
    global _override
    _override = obj


async def get_claude(org_id: str = ORG_ID) -> ClaudeLike:
    if _override is not None:
        return _override
    s = await config.get_ai_settings(org_id)
    key = await config.get_api_key(org_id) if s["effective_mode"] == "live" else None
    if key:
        return LiveClaude(org_id, key)
    from ai.simulated import SimulatedClaude
    return SimulatedClaude(org_id)
