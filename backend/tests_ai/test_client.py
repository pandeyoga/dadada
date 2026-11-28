import json

import anthropic
import httpx2 as httpx
import pytest

from ai.client import ClaudeError, LiveClaude

pytestmark = pytest.mark.asyncio

OK = {"id": "msg_1", "type": "message", "role": "assistant", "model": "claude-opus-5-5",
      "content": [{"type": "text", "text": "halo"}], "stop_reason": "end_turn", "stop_sequence": None,
      "usage": {"input_tokens": 10, "output_tokens": 5}}


def _live(handler):
    return LiveClaude("org-x", "sk-ant-fake", http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
                      max_retries=0)


async def _turn(c):
    return await c.turn(model="claude-opus-5-5", system=[{"type": "text", "text": "s"}],
                        messages=[{"role": "user", "content": "hi"}],
                        tools=[{"name": "t", "description": "d", "input_schema": {"type": "object", "properties": {}}}],
                        effort="high", max_tokens=1000, on_text=None, context={"u": 1})


async def test_live_request_shape(app, monkeypatch):
    from ai import budget
    seen = {}

    async def fake_record(org_id, **kw):
        seen["usage"] = kw
        return {}
    monkeypatch.setattr(budget, "record_usage", fake_record)

    def handler(req: httpx.Request):
        seen["body"] = json.loads(req.content)
        seen["headers"] = req.headers
        return httpx.Response(200, json=OK)
    res = await _turn(_live(handler))
    b = seen["body"]
    assert b["model"] == "claude-opus-5-5"
    assert b["thinking"]["type"] == "adaptive"
    assert b["output_config"]["effort"] == "high"
    assert (b.get("tool_choice") or {}).get("type") not in ("any", "tool")
    assert "server-side-fallback-2026-07-01" in seen["headers"]["anthropic-beta"]
    assert b["fallbacks"] == "default"
    assert b["system"][-1]["cache_control"] and b["tools"][-1]["cache_control"]
    assert res["stop_reason"] == "end_turn" and res["content"][0]["text"] == "halo"
    assert seen["usage"]["usage"]["input_tokens"] == 10


async def test_error_mapping_429_and_overloaded(app):
    def h429(req):
        return httpx.Response(429, headers={"retry-after": "7"},
                              json={"type": "error", "error": {"type": "rate_limit_error", "message": "slow"}})

    def h529(req):
        return httpx.Response(529, json={"type": "error", "error": {"type": "overloaded_error", "message": "busy"}})
    with pytest.raises(ClaudeError) as e1:
        await _turn(_live(h429))
    assert e1.value.kind == "rate_limit" and e1.value.retry_after == 7.0
    with pytest.raises(ClaudeError) as e2:
        await _turn(_live(h529))
    assert e2.value.kind == "overloaded"
