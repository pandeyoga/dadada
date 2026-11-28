import json

import pytest

from ai.client import set_override
from ai.fake import FakeClaude

OWNER, SALES = "owner@sipro.co.id", "sales@sipro.co.id"


@pytest.fixture(autouse=True)
def _reset():
    yield
    set_override(None)


async def _new_conv(client, auth, tok):
    r = await client.post("/api/ai/conversations", headers=auth(tok), json={"role": "copilot"})
    assert r.status_code == 200, r.text
    return r.json()["data"]["id"]


async def test_sse_stream_events_order(client, login, auth):
    tok = await login(OWNER)
    set_override(FakeClaude([
        {"content": [{"type": "tool_use", "id": "toolu_1", "name": "cari_unit", "input": {}}], "stop_reason": "tool_use"},
        {"content": [{"type": "text", "text": "Ini hasilnya."}]}]))
    cid = await _new_conv(client, auth, tok)
    r = await client.post(f"/api/ai/conversations/{cid}/messages", headers=auth(tok), json={"text": "cari unit"})
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/event-stream")
    evs = [json.loads(b[6:]) for b in r.text.split("\n\n") if b.startswith("data: ")]
    kinds = [e["type"] for e in evs]
    assert kinds.index("step_started") < kinds.index("step_done") < kinds.index("text_delta") < kinds.index("done")
    assert kinds[-1] == "done"
    c = (await client.get(f"/api/ai/conversations/{cid}", headers=auth(tok))).json()["data"]
    assert [m["role"] for m in c["messages"]] == ["user", "assistant"]
    assert c["messages"][1]["text"] == "Ini hasilnya." and c["messages"][1]["steps"][0]["tool"] == "cari_unit"


async def test_api_key_never_returned(client, login, auth):
    tok = await login(OWNER)
    secret = "sk-ant-rahasia-1234567890abcd"
    r = await client.put("/api/ai/settings/api-key", headers=auth(tok), json={"key": secret})
    assert r.status_code == 200 and secret not in r.text
    r = await client.get("/api/ai/settings", headers=auth(tok))
    d = r.json()["data"]
    assert d["has_key"] is True and d["key_last4"] == secret[-4:] and secret not in r.text
    r = await client.put("/api/ai/settings", headers=auth(tok), json={"category_modes": {"x": "auto"}})
    assert r.status_code == 400


async def test_conversations_are_private_per_owner(client, login, auth):
    a, b = await login(OWNER), await login(SALES)
    cid = await _new_conv(client, auth, a)
    assert (await client.get(f"/api/ai/conversations/{cid}", headers=auth(b))).status_code == 404
    assert (await client.delete(f"/api/ai/conversations/{cid}", headers=auth(b))).status_code == 404
    ids = [c["id"] for c in (await client.get("/api/ai/conversations", headers=auth(b))).json()["data"]]
    assert cid not in ids
    assert (await client.get(f"/api/ai/conversations/{cid}", headers=auth(a))).status_code == 200


async def test_settings_requires_manage(client, login, auth):
    tok = await login(SALES)
    for method, path in (("get", "/api/ai/settings"), ("put", "/api/ai/settings"), ("get", "/api/ai/usage")):
        r = await getattr(client, method)(path, headers=auth(tok), **({"json": {}} if method == "put" else {}))
        assert r.status_code == 403, path
