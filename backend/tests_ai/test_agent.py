import pytest

from ai import agent, budget, conversations
from ai.client import set_override
from ai.fake import FakeClaude
from tests_ai.helpers import ctx_for


@pytest.fixture(autouse=True)
def _reset():
    yield
    set_override(None)


def _tu(i, name, inp=None):
    return {"type": "tool_use", "id": f"toolu_{i}", "name": name, "input": inp or {}}


async def _run(ctx, text="halo"):
    conv = await conversations.create(ctx.org_id, ctx.user["id"], role="copilot")
    ctx.conversation_id = conv["id"]
    return conv, [e async for e in agent.run_turn(ctx, conv["id"], [{"type": "text", "text": text}])]


async def test_parallel_tool_results_single_message(login):
    ctx = await ctx_for("owner@sipro.co.id", await login("owner@sipro.co.id"))
    fake = FakeClaude([
        {"content": [_tu(1, "cari_unit"), _tu(2, "daftar_harga"), _tu(3, "tidak_ada")], "stop_reason": "tool_use"},
        {"content": [{"type": "text", "text": "Selesai."}]}])
    set_override(fake)
    _, ev = await _run(ctx)
    last = fake.calls[1]["messages"][-1]
    assert last["role"] == "user" and [b["tool_use_id"] for b in last["content"]] == ["toolu_1", "toolu_2", "toolu_3"]
    assert last["content"][2].get("is_error") is True and not last["content"][0].get("is_error")
    kinds = [e["type"] for e in ev]
    assert kinds.count("step_started") == 3 and kinds.count("step_done") == 3 and kinds[-1] == "done"
    assert all(t.get("strict") for t in fake.calls[0]["tools"])


async def test_thinking_blocks_round_trip_unchanged(login):
    ctx = await ctx_for("owner@sipro.co.id", await login("owner@sipro.co.id"))
    content = [{"type": "thinking", "thinking": "mikir", "signature": "sig=="}, _tu(1, "cari_unit")]
    fake = FakeClaude([{"content": content, "stop_reason": "tool_use"}, {"content": [{"type": "text", "text": "ok"}]}])
    set_override(fake)
    conv, _ = await _run(ctx)
    assert fake.calls[1]["messages"][1] == {"role": "assistant", "content": content}
    again = await conversations.history_for_api(conv["id"])
    assert again[1]["content"] == content  # tersimpan utuh


async def test_refusal_message(login):
    ctx = await ctx_for("owner@sipro.co.id", await login("owner@sipro.co.id"))
    set_override(FakeClaude([{"content": [], "stop_reason": "refusal"}]))
    _, ev = await _run(ctx)
    assert ev[0] == {"type": "text_delta", "text": "Permintaan ini tidak bisa saya bantu."} and ev[-1]["type"] == "done"


async def test_budget_stop_blocks_non_owner(login, monkeypatch):
    async def stop(org_id=None):
        return {"state": "stop", "spent_idr": 1, "limit_idr": 1, "pct": 100}
    monkeypatch.setattr(budget, "budget_state", stop)
    fake = FakeClaude([{"content": [{"type": "text", "text": "ok"}]}])
    set_override(fake)
    mgr = await ctx_for("manager@sipro.co.id", await login("manager@sipro.co.id"))
    _, ev = await _run(mgr)
    assert [e["type"] for e in ev] == ["error"] and "anggaran" in ev[0]["message"].lower() and not fake.calls
    owner = await ctx_for("owner@sipro.co.id", await login("owner@sipro.co.id"))
    _, ev = await _run(owner)
    assert ev[-1]["type"] == "done"
