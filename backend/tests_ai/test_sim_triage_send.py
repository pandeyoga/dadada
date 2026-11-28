"""Mode simulasi (pemilah berbasis kata kunci) dan kirim draf dari Inbox mencatat aktivitas lead."""
import json

from ai import drafts, triage, wa_agent
from ai.client import set_override
from ai.simulated import SimulatedClaude
from db import db, ORG_ID
from tests_ai.helpers import make_lead
from tests_ai.test_wa_agent import _job, _modes


async def test_simulated_triage_keywords():
    set_override(SimulatedClaude(ORG_ID))
    try:
        for text, cat in (("Harga unit tipe 36?", "stok_harga"), ("Bisa cicil KPR gaji 8 juta?", "simulasi_kpr"),
                          ("Mau jadwal survei", "jadwal_survei"), ("bisa nego diskon?", "diskon_nego"),
                          ("atap rumah bocor", "komplain"), ("Halo selamat pagi", "sapaan_umum"), ("???", "lainnya_tidak_yakin")):
            r = await triage.classify(ORG_ID, text, [])
            assert r["category"] == cat and r["confidence"] == 0.8, (text, r)
    finally:
        set_override(None)


async def test_send_draft_logs_lead_activity_and_first_contact(client, login, auth):
    tok = await login("owner@sipro.co.id")
    lead = await make_lead(client, auth, tok, "Lead Draf Simulasi")
    await _modes()
    conv, job = await _job("Harga unit tipe 36 berapa?")
    await db.conversations.update_one({"id": conv["id"]}, {"$set": {"lead_id": lead["id"], "contact_phone": lead["phone"]}})
    job["lead_id"] = lead["id"]
    set_override(SimulatedClaude(ORG_ID))
    try:
        res = await wa_agent.process_job(job)
    finally:
        set_override(None)
    assert res["status"] == "draft"
    d = await db.ai_drafts.find_one({"id": res["draft_id"]})
    assert "Draf simulasi" in d["text"]
    owner = await db.users.find_one({"email": "owner@sipro.co.id"}, {"_id": 0})
    await drafts.send(d["id"], ORG_ID, owner)
    acts = (await client.get("/api/activities", headers=auth(tok), params={"entity_type": "lead", "entity_id": lead["id"]})).json()["data"]
    assert any(a["body"].startswith("WhatsApp terkirim") for a in acts)
    cur = (await client.get(f"/api/leads/{lead['id']}", headers=auth(tok))).json()["data"]
    assert cur.get("first_contact_at")
