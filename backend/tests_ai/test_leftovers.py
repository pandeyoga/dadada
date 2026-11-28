"""Sisa tahap 1: biaya riset web & fallback, ringkasan WA, lampiran sebagai rujukan."""
import json

import pytest

from ai import budget, conversations, summarize
from ai.client import LiveClaude, get_claude, set_override
from ai.fake import FakeClaude
from db import db, ORG_ID

OWNER = "owner@sipro.co.id"


@pytest.fixture(autouse=True)
def _reset():
    yield
    set_override(None)


def test_web_search_cost_counted():
    base = {"input_tokens": 1000, "output_tokens": 500}
    with_web = {**base, "server_tool_use": {"web_search_requests": 3}}
    assert budget.cost_usd("claude-opus-5-5", with_web) - budget.cost_usd("claude-opus-5-5", base) == pytest.approx(0.03)


async def test_fallback_model_priced(app, monkeypatch):
    assert budget.PRICES["claude-sonnet-5-5"] == (2.0, 10.0, 0.10)
    assert budget.cost_usd("claude-sonnet-5-5", {"input_tokens": 1_000_000}) == pytest.approx(2.0)
    seen = {}

    async def rec(org_id, **kw):
        seen.update(kw)
        return {}
    monkeypatch.setattr(budget, "record_usage", rec)

    class _U:
        def model_dump(self, **kw):
            return {"input_tokens": 10, "output_tokens": 5}

    class _Msg:
        model, stop_reason, stop_details, usage, content = "claude-sonnet-5-5", "end_turn", None, _U(), []

    class _Msgs:
        async def create(self, **kw):
            return _Msg()

    class _Beta:
        messages = _Msgs()

    class _C:
        beta = _Beta()
    out = await LiveClaude("o", client=_C()).turn(model="claude-opus-5-5", system=[], messages=[], tools=[], effort="low",
                                                  max_tokens=10, on_text=None, context={})
    assert seen["model"] == "claude-sonnet-5-5" and out["model"] == "claude-sonnet-5-5"


async def test_wa_summary_written(app):
    conv = await conversations.create(ORG_ID, "svc", role="sales", channel="wa", contact={"phone": "+628100000001"})
    for i in range(45):
        await conversations.append(conv["id"], {"role": "user" if i % 2 == 0 else "assistant",
                                                "content": [{"type": "text", "text": f"pesan {i}"}]})
    set_override(FakeClaude([{"content": [{"type": "text", "text": "Pelanggan menanyakan tipe 36."}]}]))
    assert await summarize.update_wa_summary(conv["id"]) == "Pelanggan menanyakan tipe 36."
    c = await db.ai_conversations.find_one({"id": conv["id"]})
    # jendela 30 dimulai dari giliran pengguna (seq 17): asisten seq 16 di tepinya ikut diringkas, bukan hilang
    assert c["summary"] and c["summary_upto_seq"] == 16
    assert await summarize.update_wa_summary(conv["id"]) is None  # tidak ada pesan baru di luar jendela
    hist = await conversations.history_for_api(conv["id"])
    assert hist[0]["role"] == "user" and "Ringkasan percakapan sebelumnya" in hist[0]["content"][0]["text"]


async def test_attachment_stored_as_ref(client, login, auth):
    tok = await login(OWNER)
    r = await client.post("/api/ai/conversations", headers=auth(tok), json={"role": "copilot"})
    cid = r.json()["data"]["id"]
    png = b"\x89PNG\r\n\x1a\n" + b"0" * 64
    up = await client.post("/api/ai/files", headers=auth(tok), files={"file": ("foto.png", png, "image/png")})
    fid = up.json()["data"]["id"]
    fake = FakeClaude([{"content": [{"type": "text", "text": "ok"}]}, {"content": [{"type": "text", "text": "ok2"}]}])
    set_override(fake)
    r = await client.post(f"/api/ai/conversations/{cid}/messages", headers=auth(tok),
                          json={"text": "lihat", "attachments": [fid]})
    assert r.status_code == 200
    raw = await db.ai_messages.find({"conversation_id": cid}).to_list(10)
    assert "base64" not in json.dumps(raw, default=str)
    user = [m for m in raw if m["role"] == "user"][0]
    assert user["attachment_ids"] == [fid] and "[Lampiran: foto.png]" in json.dumps(user["content"])
    r = await client.post(f"/api/ai/conversations/{cid}/messages", headers=auth(tok), json={"text": "lanjut"})
    assert r.status_code == 200
    first = fake.calls[1]["messages"][0]["content"]
    assert any(b.get("type") == "image" and b["source"]["type"] == "base64" for b in first)
