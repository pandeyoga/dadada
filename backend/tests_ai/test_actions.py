import asyncio

import pytest

import rbac
from ai import actions, agent, conversations
from ai.client import set_override
from ai.fake import FakeClaude
from db import db
from tests_ai.helpers import ctx_for, make_lead, user_of


@pytest.fixture(autouse=True)
def _reset():
    yield
    set_override(None)


async def _propose(ctx, tool, inp):
    conv = await conversations.create(ctx.org_id, ctx.user["id"], role="copilot")
    ctx.conversation_id = conv["id"]
    set_override(FakeClaude([
        {"content": [{"type": "tool_use", "id": "toolu_p", "name": tool, "input": inp}], "stop_reason": "tool_use"},
        {"content": [{"type": "text", "text": "Usulan dibuat."}]}]))
    ev = [e async for e in agent.run_turn(ctx, conv["id"], [{"type": "text", "text": "usulkan"}])]
    prop = [e for e in ev if e["type"] == "action_proposed"]
    assert len(prop) == 1, ev
    return prop[0]["action"]


async def test_propose_creates_pending_not_executed(client, login, auth):
    tok = await login("owner@sipro.co.id")
    lead = await make_lead(client, auth, tok, "Lead Usulan")
    ctx = await ctx_for("owner@sipro.co.id", tok)
    a = await _propose(ctx, "ubah_tahap_lead", {"lead_id": lead["id"], "tahap_baru": "nurturing", "alasan": "sudah dihubungi"})
    assert a["status"] == "pending" and a["preview"]["changes"] and "checks" in a["preview"]
    cur = (await client.get(f"/api/leads/{lead['id']}", headers=auth(tok))).json()["data"]
    assert cur["stage"] == "acquisition"


async def test_approve_executes_once_concurrently(client, login, auth):
    tok = await login("owner@sipro.co.id")
    lead = await make_lead(client, auth, tok, "Lead Catatan")
    ctx = await ctx_for("owner@sipro.co.id", tok)
    a = await _propose(ctx, "catat_catatan_lead", {"lead_id": lead["id"], "catatan": "Minat tipe 45"})
    owner = await user_of("owner@sipro.co.id")
    res = await asyncio.gather(actions.approve(a["id"], owner, tok), actions.approve(a["id"], owner, tok),
                               return_exceptions=True)
    ok = [r for r in res if isinstance(r, dict)]
    bad = [r for r in res if isinstance(r, actions.ActionError)]
    assert len(ok) == 1 and ok[0]["status"] == "executed" and len(bad) == 1 and "sudah diproses" in bad[0].message
    acts = (await client.get("/api/activities", headers=auth(tok), params={"entity_type": "lead", "entity_id": lead["id"]})).json()["data"]
    assert sum(1 for x in acts if x["body"] == "Minat tipe 45") == 1
    log = await db.audit_logs.find_one({"action": "ai_action_executed", "meta.action_id": a["id"]})
    assert log and log["meta"]["actor_type"] == "ai" and log["meta"]["approved_by"] == "owner@sipro.co.id"


async def test_approve_uses_approver_permissions(client, login, auth):
    tok = await login("owner@sipro.co.id")
    lead = await make_lead(client, auth, tok, "Lead Izin")
    ctx = await ctx_for("owner@sipro.co.id", tok)
    a = await _propose(ctx, "ubah_tahap_lead", {"lead_id": lead["id"], "tahap_baru": "nurturing", "alasan": "x"})
    email = None
    for e in ("site@sipro.co.id", "pm@sipro.co.id", "finance@sipro.co.id"):
        if not await rbac.can((await user_of(e))["role"], "leads", "update"):
            email = e
            break
    assert email
    low = await user_of(email)
    with pytest.raises(actions.ActionError) as ei:
        await actions.approve(a["id"], low, await login(email))
    assert ei.value.status == 403
    assert (await actions.get(a["id"]))["status"] == "pending"
