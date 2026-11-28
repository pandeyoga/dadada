"""Agen CS pembeli di portal (Tanya Estora, tahap 2a): isolasi pembeli, konfirmasi tepat sekali, serah ke CS,
kuota & anggaran, saklar mati, dan pemisahan tiket chat dari statistik komplain."""
import asyncio
import json
import uuid
from datetime import datetime

import pytest

import complaint_intake
import settings_store as ss
from ai import actions, conversations, portal_handoff
from ai.agent import BUDGET_MSG
from ai.client import set_override
from ai.fake import FakeClaude
from ai.tools import catalog, registry  # noqa: F401
from ai.tools.registry import ToolContext
from core_utils import new_id, now, now_iso
from db import db, ORG_ID
from portal_security import create_portal_token

OWNER = "owner@sipro.co.id"


@pytest.fixture(autouse=True)
async def _reset():
    yield
    set_override(None)
    await ss.set_value("ai.portal_enabled", False, actor="test", reason="reset", org_id=ORG_ID)
    await ss.set_value("ai.portal_daily_limit", 30, actor="test", reason="reset", org_id=ORG_ID)


async def _enable(on: bool = True):
    await ss.set_value("ai.portal_enabled", on, actor="test", reason="uji agen portal", org_id=ORG_ID)


async def _buyer(tag: str, *, deals: int = 1, assigned_to: str = "sales@sipro.co.id"):
    """Pembeli portal dengan customer/lead, `deals` transaksi (unit, tagihan, satu komplain). -> (pu, token, [deal_id])."""
    phone = f"+62813{uuid.uuid4().int % 10**8:08d}"
    lead_id, cust_id, ts = new_id(), new_id(), now_iso()
    await db.leads.insert_one({"id": lead_id, "org_id": ORG_ID, "name": f"Pembeli {tag}", "phone": phone, "created_at": ts})
    await db.customers.insert_one({"id": cust_id, "org_id": ORG_ID, "name": f"Pembeli {tag}", "phone": phone,
                                   "lead_id": lead_id, "created_at": ts})
    ids = []
    for i in range(deals):
        unit_id, deal_id = new_id(), new_id()
        await db.units.insert_one({"id": unit_id, "org_id": ORG_ID, "code": f"PT-{tag}-{i}", "type": "36",
                                   "project_id": "proj-portal-uji", "status": "sold", "price": 500_000_000})
        await db.deals.insert_one({"id": deal_id, "org_id": ORG_ID, "lead_id": lead_id, "customer_id": cust_id,
                                   "unit_id": unit_id, "project_id": "proj-portal-uji", "status": "booked",
                                   "price": 500_000_000, "assigned_to": assigned_to, "created_at": f"2026-0{i + 1}-01T00:00:00+00:00"})
        await db.ar_invoices.insert_one({"id": new_id(), "org_id": ORG_ID, "deal_id": deal_id, "unit_code": f"PT-{tag}-{i}",
                                         "total": 500_000_000, "paid": 0, "outstanding": 500_000_000, "status": "open",
                                         "items": [{"label": f"Angsuran {tag}", "due_date": "2026-12-10",
                                                    "amount": 10_000_000, "status": "unpaid"}]})
        await db.complaints.insert_one({"id": new_id(), "org_id": ORG_ID, "customer_id": cust_id, "deal_id": deal_id,
                                        "subject": f"Rahasia {tag}", "message": "isi", "category": "lainnya",
                                        "status": "open", "created_at": ts})
        ids.append(deal_id)
    pu = {"id": new_id(), "org_id": ORG_ID, "is_active": True, "customer_id": cust_id, "lead_id": None,
          "name": f"Pembeli {tag}", "phone": phone, "email": None, "created_at": ts}
    await db.portal_users.insert_one(dict(pu))
    return pu, create_portal_token(pu), ids


async def _ctx(pu, tok) -> ToolContext:
    conv = await conversations.create(ORG_ID, pu["id"], role="buyer_cs", channel="portal")
    return ToolContext(org_id=ORG_ID, user=pu, token=tok, channel="portal", conversation_id=conv["id"],
                       verified=True, role="buyer_cs")


def _tri(cat):
    return {"content": [{"type": "text", "text": json.dumps({"category": cat, "intent": "tanya", "objections": [],
                                                              "sentiment": "netral", "confidence": 0.9})}]}


def _events(r) -> list:
    return [json.loads(b[6:]) for b in r.text.split("\n\n") if b.startswith("data: ")]


async def _new_conv(client, auth, tok) -> str:
    r = await client.post("/api/portal/ai/conversations", headers=auth(tok))
    assert r.status_code == 200, r.text
    return r.json()["data"]["id"]


async def test_portal_buyer_isolation(client, auth):
    pa, ta, (da,) = await _buyer("Alfa")
    pb, tb, (dbb,) = await _buyer("Bravo")
    ctx = await _ctx(pa, ta)
    names = {t.name for t in registry.tools_for(ctx)}
    assert {"komplain_saya", "tagihan_saya", "buat_komplain", "simulasi_kpr"} <= names
    assert not names & {"api_get", "cari_endpoint", "tagihan_pembeli", "cari_lead"}
    for tool, mine in (("komplain_saya", "Rahasia Alfa"), ("tagihan_saya", "Angsuran Alfa")):
        own = await registry.run(ctx, tool, {})
        assert own["ok"] and mine in json.dumps(own["data"]) and "Bravo" not in json.dumps(own["data"]), tool
        other = await registry.run(ctx, tool, {"deal_id": dbb})
        assert "Bravo" not in json.dumps(other) and not (other["data"] or {}).get("komplain"), tool
    staff = ToolContext(org_id=ORG_ID, user=pa, token=ta)  # alat portal tidak pernah tampil/jalan di kanal staf
    assert "komplain_saya" not in {t.name for t in registry.tools_for(staff)}
    assert (await registry.run(staff, "komplain_saya", {}))["ok"] is False
    bad = await registry.run(ctx, "buat_komplain", {"deal_id": dbb, "kategori": "konstruksi", "subjek": "Atap bocor",
                                                    "pesan": "Atap bocor saat hujan."})
    assert bad["ok"] is False and await db.ai_actions.count_documents({"entity_id": dbb}) == 0
    prop = await registry.run(ctx, "buat_komplain", {"deal_id": da, "kategori": "konstruksi", "subjek": "Atap bocor",
                                                     "pesan": "Atap bocor saat hujan."})
    aid = prop["data"]["action_id"]
    r = await client.post(f"/api/portal/ai/actions/{aid}/confirm", headers=auth(tb))
    assert r.status_code == 404
    assert (await client.post(f"/api/portal/ai/actions/{aid}/cancel", headers=auth(tb))).status_code == 404
    a = await actions.get(aid)
    assert a["status"] == "pending" and a["owner_id"] == pa["id"]


async def test_portal_confirm_once(client, auth):
    pu, tok, (older, newer) = await _buyer("Charlie", deals=2)
    ctx = await _ctx(pu, tok)
    prop = await registry.run(ctx, "buat_komplain", {"deal_id": older, "kategori": "konstruksi", "subjek": "Retak dinding",
                                                     "pesan": "Dinding kamar retak sejak minggu lalu."})
    assert prop["ok"], prop
    aid = prop["data"]["action_id"]
    assert await db.complaints.count_documents({"subject": "Retak dinding", "deal_id": {"$in": [older, newer]}}) == 0
    res = await asyncio.gather(actions.confirm_by_buyer(aid, pu, tok), actions.confirm_by_buyer(aid, pu, tok),
                               return_exceptions=True)
    ok = [x for x in res if isinstance(x, dict)]
    bad = [x for x in res if isinstance(x, actions.ActionError)]
    assert len(ok) == 1 and ok[0]["status"] == "executed" and len(bad) == 1 and bad[0].status == 409, res
    made = await db.complaints.find({"subject": "Retak dinding", "customer_id": pu["customer_id"]}).to_list(10)
    assert len(made) == 1 and made[0]["deal_id"] == older  # deal yang dikirim, bukan fallback deals[0]
    a = await actions.get(aid)
    assert a["executed_by"] == pu["id"] and a["channel"] == "portal"
    r = await client.post(f"/api/portal/ai/actions/{aid}/confirm", headers=auth(tok))
    assert r.status_code == 409
    owner = await db.users.find_one({"email": OWNER}, {"_id": 0})
    with pytest.raises(actions.ActionError):  # staf tidak bisa menyetujui aksi pembeli
        await actions.approve(aid, owner, "x")


async def test_portal_locked_topic_handoff(client, auth, monkeypatch):
    await _enable()
    pu, tok, (deal_id,) = await _buyer("Delta")
    sent = []

    async def _wa(*a, **k):
        sent.append(a)
        return {"provider": "simulation"}
    monkeypatch.setattr(complaint_intake, "send_whatsapp", _wa)
    fake = FakeClaude([_tri("diskon_nego")])
    set_override(fake)
    cid = await _new_conv(client, auth, tok)
    r = await client.post(f"/api/portal/ai/conversations/{cid}/messages", headers=auth(tok),
                          json={"text": "Bisa diskon kalau saya bayar cash?"})
    evs = _events(r)
    assert [e["type"] for e in evs] == ["handoff", "text_delta", "done"], evs
    assert len(fake.calls) == 1 and fake.calls[0]["output_format"] and fake.calls[0]["model"] == "claude-haiku-5-5"
    ticket = evs[0]["ticket"]
    t = await db.complaints.find_one({"id": ticket["id"]}, {"_id": 0})
    mgr = await db.users.find_one({"org_id": ORG_ID, "role": "sales_manager", "is_active": {"$ne": False}},
                                  {"_id": 0}, sort=[("created_at", 1)])
    assert t["kind"] == "pertanyaan_chat" and t["category"] == "layanan" and t["source"] == "ai_portal"
    assert t["ai_conversation_id"] == cid and t["deal_id"] == deal_id
    assert t["assigned_to"] == mgr["email"] and ticket["assigned_role"] == "sales_manager"
    due = datetime.fromisoformat(t["sla_due_at"])
    assert abs((due - now()).total_seconds() - 24 * 3600) < 120
    assert sent == []
    text = evs[1]["text"]
    assert ticket["number"] in text and "tidak bisa memberi kepastian" in text and "bisa diskon" not in text.lower()
    task = await db.tasks.find_one({"source_event": f"complaint:{t['id']}"}, {"_id": 0})
    assert task["assigned_to"] == mgr["email"] and task["complaint_kind"] == "pertanyaan_chat"
    c = (await client.get(f"/api/portal/ai/conversations/{cid}", headers=auth(tok))).json()["data"]
    assert [m["role"] for m in c["messages"]] == ["user", "assistant"] and c["messages"][1]["ticket"]["id"] == t["id"]


async def test_portal_quota_and_budget(client, auth):
    await _enable()
    await ss.set_value("ai.portal_daily_limit", 2, actor="test", reason="uji kuota", org_id=ORG_ID)
    pu, tok, _ = await _buyer("Echo")
    fake = FakeClaude([_tri("sapaan_umum"), {"content": [{"type": "text", "text": "Halo, ada yang bisa dibantu?"}]},
                       _tri("sapaan_umum"), {"content": [{"type": "text", "text": "Siap."}]}])
    set_override(fake)
    cid = await _new_conv(client, auth, tok)
    for _ in range(2):
        evs = _events(await client.post(f"/api/portal/ai/conversations/{cid}/messages", headers=auth(tok), json={"text": "Halo"}))
        assert evs[-1]["type"] == "done", evs
    evs = _events(await client.post(f"/api/portal/ai/conversations/{cid}/messages", headers=auth(tok), json={"text": "Halo"}))
    assert [e["type"] for e in evs] == ["error"] and "Batas 2 pesan hari ini tercapai" in evs[0]["message"]
    assert len(fake.calls) == 4
    st = (await client.get("/api/portal/ai/status", headers=auth(tok))).json()["data"]
    assert st["quota"] == {"used": 2, "limit": 2}
    await ss.set_value("ai.portal_daily_limit", 30, actor="test", reason="uji anggaran", org_id=ORG_ID)
    limit = await ss.get("ai.budget_idr_month", org_id=ORG_ID)
    await ss.set_value("ai.budget_idr_month", 0, actor="test", reason="uji anggaran habis", org_id=ORG_ID)
    try:
        fake2 = FakeClaude([])
        set_override(fake2)
        evs = _events(await client.post(f"/api/portal/ai/conversations/{cid}/messages", headers=auth(tok),
                                        json={"text": "Tagihan saya berapa?"}))
        assert [e["type"] for e in evs] == ["error"] and evs[0]["message"] == BUDGET_MSG and fake2.calls == []
        st = (await client.get("/api/portal/ai/status", headers=auth(tok))).json()["data"]
        assert st["budget_state"] == "stop" and st["quota"]["used"] == 2  # pesan yang ditolak anggaran tidak memakan kuota
    finally:
        await ss.set_value("ai.budget_idr_month", limit, actor="test", reason="pulihkan", org_id=ORG_ID)


async def test_portal_disabled(client, auth, login):
    await _enable(False)
    pu, tok, _ = await _buyer("Foxtrot")
    st = (await client.get("/api/portal/ai/status", headers=auth(tok))).json()["data"]
    assert st["enabled"] is False and st["noticed"] is False and st["stopped"] is False and st["notice_text"]
    conv = await conversations.create(ORG_ID, pu["id"], role="buyer_cs", channel="portal")
    r = await client.post(f"/api/portal/ai/conversations/{conv['id']}/messages", headers=auth(tok), json={"text": "Halo"})
    assert r.status_code == 403 and "belum tersedia" in r.json()["detail"]
    assert (await client.post("/api/portal/ai/conversations", headers=auth(tok))).status_code == 403
    assert (await client.get("/api/portal/ai/status", headers=auth(await login(OWNER)))).status_code == 401


async def test_complaint_stats_exclude_chat_tickets(client, auth, login):
    pu, tok, (deal_id,) = await _buyer("Golf")
    ctx = await _ctx(pu, tok)
    t = await portal_handoff.create_ticket(ctx, reason="minta_staf", question="Tolong hubungi saya soal akad",
                                           summary="Pembeli minta dihubungi.", sensitive=False, deal_id=deal_id)
    doc = await db.complaints.find_one({"id": t["id"]}, {"_id": 0})
    assert doc["assigned_to"] == "sales@sipro.co.id" and t["assigned_role"] == "sales"
    staff = await login(OWNER)
    non_chat = await db.complaints.count_documents({"org_id": ORG_ID, "kind": {"$ne": "pertanyaan_chat"}})
    chat = await db.complaints.count_documents({"org_id": ORG_ID, "kind": "pertanyaan_chat"})
    assert chat >= 1
    st = (await client.get("/api/complaints/stats", headers=auth(staff))).json()["data"]
    assert st["total"] == non_chat
    full = (await client.get("/api/complaints", headers=auth(staff), params={"limit": 200})).json()
    assert full["counts"]["total"] == non_chat
    only = (await client.get("/api/complaints", headers=auth(staff), params={"kind": "pertanyaan_chat", "limit": 200})).json()
    assert t["id"] in [x["id"] for x in only["data"]] and all(x["kind"] == "pertanyaan_chat" for x in only["data"])
    assert only["total"] == chat and only["counts"]["total"] == chat


async def test_portal_cs_button_text_hands_off_deterministically(client, auth):
    """Tombol "Bicara dengan CS" mengirim teks ini: harus jadi tiket tanpa memanggil model."""
    await _enable()
    pu, tok, _ = await _buyer("Tombol")
    fake = FakeClaude([])
    set_override(fake)
    cid = await _new_conv(client, auth, tok)
    r = await client.post(f"/api/portal/ai/conversations/{cid}/messages", headers=auth(tok),
                          json={"text": "Bicara dengan CS"})
    evs = _events(r)
    assert [e["type"] for e in evs] == ["handoff", "text_delta", "done"], evs
    assert evs[0]["ticket"]["number"] and not fake.calls
