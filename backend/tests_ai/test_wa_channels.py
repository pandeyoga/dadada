"""Kanal WhatsApp: gateway tidak resmi + Coexistence (Estora AI tahap 1, Task 9)."""
import json
import time

import httpx
import pytest

import wa_channels as wch
import wa_inbound as wi
from db import db

ORG = "org_estora"
PHONE = "+6281234560001"
SECRET = "rahasia-webhook-gateway-0123456789"
CALLS = []


def _handler(request: httpx.Request) -> httpx.Response:
    CALLS.append(json.loads(request.content))
    return httpx.Response(200, json={"id": f"gw-{len(CALLS)}"})


@pytest.fixture(autouse=True)
def _transport():
    CALLS.clear()
    wch.TRANSPORT = httpx.MockTransport(_handler)
    yield
    wch.TRANSPORT = None


async def _setup(org, **extra):
    cfg = {"enabled": True, "base_url": "https://gw.example.test", "token": "tok-rahasia",
           "send_path": "/send", "webhook_secret": SECRET, "hourly_limit": 20,
           "payload_template": '{"number": "{to}", "message": "{text}"}', **extra}
    await wch.save_unofficial_config(org, cfg, actor="test")


async def _org(client, login, auth):
    tok = await login("superadmin@estora.id")
    me = (await client.get("/api/auth/me", headers=auth(tok))).json()
    return tok, (me.get("data") or me).get("org_id", ORG)


async def _optin(org, phone=PHONE):
    await db.ai_consents.update_one({"org_id": org, "phone": phone}, {"$set": {"optins": {"unofficial": True}}}, upsert=True)


async def test_unofficial_blocks_ai_auto(client, login, auth):
    _, org = await _org(client, login, auth)
    await _setup(org)
    await _optin(org)
    r = await wch.send_unofficial(org, PHONE, "halo", actor="ai-auto", ai_generated=True)
    assert r["status"] == "blocked" and r["error_code"] == "ai_auto_blocked" and not CALLS
    r = await wch.send_unofficial(org, PHONE, "halo", actor="sales@estora.id", ai_generated=False, kind="broadcast")
    assert r["error_code"] == "unofficial_kind_blocked" and not CALLS


async def test_unofficial_requires_optin(client, login, auth):
    _, org = await _org(client, login, auth)
    await _setup(org)
    other = "+6281234560002"
    r = await wch.send_unofficial(org, other, "halo", actor="sales@estora.id", ai_generated=False)
    assert r["error_code"] == "no_optin" and not CALLS
    await _optin(org, other)
    r = await wch.send_unofficial(org, other, "halo", actor="sales@estora.id", ai_generated=False)
    assert r["status"] == "sent" and r["channel"] == "unofficial"
    assert CALLS[0] == {"number": other.lstrip("+"), "message": "halo"}  # templat payload


async def test_unofficial_hourly_limit(client, login, auth):
    _, org = await _org(client, login, auth)
    await _setup(org, hourly_limit=20)
    await _optin(org)
    await db.messages.delete_many({"org_id": org, "channel": "unofficial"})
    for i in range(20):
        r = await wch.send_unofficial(org, PHONE, f"m{i}", actor="sales@estora.id", ai_generated=False)
        assert r["status"] == "sent"
    r = await wch.send_unofficial(org, PHONE, "ke-21", actor="sales@estora.id", ai_generated=False)
    assert r["status"] == "rate_limited" and len(CALLS) == 20


async def test_unofficial_kill_switch(client, login, auth):
    tok, org = await _org(client, login, auth)
    await _setup(org)
    await _optin(org)
    await db.messages.delete_many({"org_id": org, "channel": "unofficial"})
    r = await client.post("/api/ai/channels/unofficial/disable", headers=auth(tok))
    assert r.status_code == 200 and r.json()["data"]["unofficial"]["enabled"] is False
    r = await wch.send_unofficial(org, PHONE, "halo", actor="sales@estora.id", ai_generated=False)
    assert r["error_code"] == "channel_disabled" and not CALLS
    g = (await client.get("/api/ai/channels", headers=auth(tok))).json()["data"]
    assert g["unofficial"]["token_set"] is True and "tok-rahasia" not in json.dumps(g)


async def test_gateway_webhook_secret_required(client, login, auth):
    _, org = await _org(client, login, auth)
    await _setup(org)
    body = {"from": "6281234560009", "text": "tanya harga", "id": "gwmsg-1"}
    r = await client.post("/api/webhooks/wa-gateway/salah-secret", json=body)
    assert r.status_code == 403
    r = await client.post(f"/api/webhooks/wa-gateway/{SECRET}", json=body)
    assert r.status_code == 200 and r.json()["data"]["messages"] == 1
    m = await db.messages.find_one({"provider_message_id": "gwmsg-1"})
    assert m["channel"] == "unofficial" and m["direction"] == "in"


async def test_smb_echo_recorded_as_outbound(client, login, auth):
    _, org = await _org(client, login, auth)
    raw = {"object": "whatsapp_business_account", "entry": [{"id": "W", "changes": [{
        "field": "smb_message_echoes", "value": {"messaging_product": "whatsapp", "message_echoes": [{
            "from": "6281100000000", "to": "6281234560077", "id": "wamid.ECHO1",
            "timestamp": str(int(time.time())), "type": "text", "text": {"body": "Siap Pak, saya kirim brosurnya"}}]}}]}]}
    res = await wi.process_meta_payload(raw, org)
    assert res["echoes"] == 1
    m = await db.messages.find_one({"provider_message_id": "wamid.ECHO1"})
    assert m["direction"] == "out" and m["sender"] == "sales-phone" and m["channel"] == "coexistence"
    assert m["to"] == "+6281234560077"
