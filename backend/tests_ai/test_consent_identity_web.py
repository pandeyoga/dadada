import pytest

import settings_store as ss
from ai import agent, consent, conversations, identity
from ai.client import set_override
from ai.fake import FakeClaude
from ai.tools import registry
from ai.tools.registry import ToolContext
from core_utils import new_id
from db import db, ORG_ID
from tests_ai.helpers import ctx_for

PHONE = "081355500123"


@pytest.fixture(autouse=True)
def _reset():
    yield
    set_override(None)


async def _buyer(nik="3174010101010077", phone=PHONE):
    cid = new_id()
    await db.customers.insert_one({"id": cid, "org_id": ORG_ID, "name": "Budi Uji", "phone": phone, "nik": nik})
    return cid


async def test_stop_keyword_stops_ai():
    p = "081355500901"
    assert (await consent.state(ORG_ID, p))["stopped"] is False
    assert await consent.handle_keyword(ORG_ID, p, "STOP") == "stop"
    assert (await consent.state(ORG_ID, p))["stopped"] is True
    assert await db.wa_optouts.find_one({"org_id": ORG_ID, "phone": p, "active": True})  # opt-out yang sudah ada


async def test_unverified_contact_cannot_get_billing():
    ctx = ToolContext(org_id=ORG_ID, user=None, token="x", channel="wa", contact={"phone": PHONE}, verified=False)
    r = await registry.run(ctx, "tagihan_pembeli", {})
    assert r["ok"] is False
    assert "tagihan_pembeli" not in [t.name for t in registry.tools_for(ctx)]


async def test_verify_lockout_after_3():
    p = "081355500777"
    await _buyer(phone=p)
    assert await identity.check(ORG_ID, "+6281355500777", "0000") is False  # format nomor lain, tetap cocok
    assert await identity.check(ORG_ID, p, "1111") is False
    assert await identity.check(ORG_ID, p, "2222") is False
    assert await identity.is_locked(ORG_ID, p)
    assert await identity.check(ORG_ID, p, "0077") is False  # benar pun ditolak saat terkunci
    assert not await identity.is_verified(ORG_ID, p)
    assert await db.notifications.find_one({"title": "Verifikasi identitas WhatsApp terkunci"})
    q = await identity.start(ORG_ID, "081355500888")
    assert "NIK" in q["question"] and "3174" not in str(q)
    cid = await _buyer(nik="3174010101010177", phone="081355500888")
    assert await identity.check(ORG_ID, "081355500888", "0177")
    assert await identity.verified_customer_id(ORG_ID, "081355500888") == cid


async def _turn(ctx, fake, conv):
    set_override(fake)
    return [e async for e in agent.run_turn(ctx, conv["id"], [{"type": "text", "text": "cari info"}])]


def _web(call):
    return [t for t in call["tools"] if t["name"].startswith("web_")]


async def test_web_tools_added_only_when_enabled(login):
    ctx = await ctx_for("owner@sipro.co.id", await login("owner@sipro.co.id"), web_research=True)
    await ss.set_value("ai.web_research_enabled", False, actor="t", reason="uji", org_id=ORG_ID)
    conv = await conversations.create(ORG_ID, ctx.user["id"], role="copilot")
    f1 = FakeClaude([{"content": [{"type": "text", "text": "ok"}]}])
    await _turn(ctx, f1, conv)
    assert not _web(f1.calls[0])
    await ss.set_value("ai.web_research_enabled", True, actor="t", reason="uji", org_id=ORG_ID)
    f2 = FakeClaude([{"content": [{"type": "text", "text": "ok"}]}])
    await _turn(ctx, f2, conv)
    assert {t["type"] for t in _web(f2.calls[0])} == {"web_search_20260209", "web_fetch_20260209"}
    ctx.web_research = False
    f3 = FakeClaude([{"content": [{"type": "text", "text": "ok"}]}])
    await _turn(ctx, f3, conv)
    assert not _web(f3.calls[0])
    await ss.set_value("ai.web_research_enabled", False, actor="t", reason="uji", org_id=ORG_ID)


async def test_pii_query_incident_disables_research(login):
    ctx = await ctx_for("owner@sipro.co.id", await login("owner@sipro.co.id"), web_research=True)
    await ss.set_value("ai.web_research_enabled", True, actor="t", reason="uji", org_id=ORG_ID)
    conv = await conversations.create(ORG_ID, ctx.user["id"], role="copilot")
    sq = {"type": "server_tool_use", "id": "srvtoolu_1", "name": "web_search", "input": {"query": "KTP 3174010101010077 Budi"}}
    fake = FakeClaude([{"content": [sq], "stop_reason": "pause_turn"}, {"content": [{"type": "text", "text": "ok"}]}])
    await _turn(ctx, fake, conv)
    assert _web(fake.calls[0]) and not _web(fake.calls[1])  # dimatikan setelah insiden
    q = await db.ai_web_queries.find_one({"conversation_id": conv["id"]})
    assert q["pii_blocked"] and "3174" not in q["query"]
    assert await db.ai_incidents.find_one({"conversation_id": conv["id"], "kind": "web_query_pii"})
    await ss.set_value("ai.web_research_enabled", False, actor="t", reason="uji", org_id=ORG_ID)
