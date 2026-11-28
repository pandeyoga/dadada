#!/usr/bin/env python3
"""verify_ai.py — gate invarian Estora AI tahap 1 (in-process, FakeClaude, tanpa jaringan/kunci API).

Lima invarian yang tidak boleh rusak diam-diam:
  1. AI tidak mengubah koleksi bisnis tanpa `ai_actions` berstatus `executed` (usulan hanya pending).
  2. Tidak ada pesan `channel: "unofficial"` dari AI otomatis (`ai-auto` / ai_generated).
  3. Anggaran `stop` -> 0 balasan otomatis (dan 0 panggilan model).
  4. Data `wa_self` tidak pernah lintas kontak (pembeli lain ditolak; tak terverifikasi tak punya alatnya).
  5. Setiap `ai_actions` yang `executed` punya entri audit (`ai_action_executed`, meta.action_id).

Butuh MongoDB lokal: `MONGO_URL=mongodb://127.0.0.1:27017 python3 scripts/verify_ai.py`.
DB `estora_ai_gate` di-drop di awal. Exit 0 = PASSED, 1 = FAILED.
Tanpa MONGO_URL gate DILEWATI (bukan lulus): pesan "SKIPPED" + exit 3; `run_all_gates.sh` menampilkannya
sebagai SKIP (tidak dihitung lulus) supaya tidak ada yang mengira invarian AI sudah diperiksa.
"""
import asyncio
import hashlib
import json
import os
import sys
from pathlib import Path

# Env harus diset SEBELUM `server`/`db` diimpor (sama seperti backend/tests_ai/conftest.py).
SKIP_EXIT = 3
if not os.environ.get("MONGO_URL"):
    print("verify_ai: SKIPPED — MONGO_URL tidak diset, invarian AI TIDAK diperiksa. "
          "Jalankan: MONGO_URL=mongodb://127.0.0.1:27017 python3 scripts/verify_ai.py")
    sys.exit(SKIP_EXIT)
DB_NAME = "estora_ai_gate"
os.environ["DB_NAME"] = DB_NAME
os.environ.setdefault("JWT_SECRET", "gate-secret-estora-ai-0123456789abcdef")
os.environ["SEED_DEMO_USERS"] = "true"
os.environ["AI_WORKER"] = "off"
os.environ.setdefault("STORAGE_PROVIDER", "mongo")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

import logging  # noqa: E402

import httpx  # noqa: E402

logging.disable(logging.INFO)
FAILS: list = []
ALL = ("stok_harga", "simulasi_kpr", "lokasi_fasilitas", "jadwal_survei", "berkas_kpr",
       "tagihan_pembayaran", "progres_serah_terima", "komplain", "sapaan_umum")
BUSINESS = ("leads", "appointments", "complaints", "units", "contracts", "customers", "invoices", "payments")


def check(inv: int, cond: bool, msg: str):
    print(f"  {'ok  ' if cond else 'FAIL'}  [{inv}] {msg}")
    if not cond:
        FAILS.append(f"[{inv}] {msg}")


async def main():
    import seed
    import server
    import settings_store as ss
    import wa_channels
    from ai import actions, agent, budget, conversations, drafts, wa_agent
    from ai.client import set_override
    from ai.fake import FakeClaude
    from ai.tools import catalog, registry  # noqa: F401
    from ai.tools.registry import ToolContext
    from core_utils import due_in, new_id, now_iso
    from db import client as mongo, db, ORG_ID

    await mongo.drop_database(DB_NAME)
    async with server.app.router.lifespan_context(server.app):
        http = httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app), base_url="http://gate")
        r = await http.post("/api/auth/login", json={"email": "owner@sipro.co.id", "password": seed.TEST_PASSWORD})
        assert r.status_code == 200, r.text
        tok = r.json()["access_token"]
        hdr = {"Authorization": f"Bearer {tok}"}
        owner = await db.users.find_one({"email": "owner@sipro.co.id"}, {"_id": 0, "password_hash": 0})

        async def fingerprint(names):
            out = {}
            for n in names:
                rows = await db[n].find({}, {"_id": 0}).sort("id", 1).to_list(5000)
                out[n] = hashlib.sha256(json.dumps(rows, sort_keys=True, default=str).encode()).hexdigest()
            return out

        def script_tool(name, inp, tid):
            return [{"content": [{"type": "tool_use", "id": tid, "name": name, "input": inp}], "stop_reason": "tool_use"},
                    {"content": [{"type": "text", "text": "Usulan dibuat."}]}]

        # ------------------------------------------------ 1 & 5: aksi hanya lewat ai_actions executed + audit
        print("Invarian 1 & 5 — aksi AI hanya berlaku setelah persetujuan, dan beraudit")
        lead = (await http.post("/api/leads", headers=hdr, json={"name": "Lead Gate", "phone": "081290001234", "source": "manual"})).json()["data"]
        ctx = ToolContext(org_id=ORG_ID, user=owner, token=tok)
        before = await fingerprint(BUSINESS)
        act_before = await db.activities.count_documents({})
        proposals = []
        for tool, inp in (("catat_catatan_lead", {"lead_id": lead["id"], "catatan": "Catatan gate"}),
                          ("ubah_tahap_lead", {"lead_id": lead["id"], "tahap_baru": "nurturing", "alasan": "gate"})):
            conv = await conversations.create(ORG_ID, owner["id"], role="copilot")
            ctx.conversation_id = conv["id"]
            set_override(FakeClaude(script_tool(tool, inp, "toolu_" + new_id()[:8])))
            ev = [e async for e in agent.run_turn(ctx, conv["id"], [{"type": "text", "text": "usulkan"}])]
            proposals += [e["action"] for e in ev if e["type"] == "action_proposed"]
        check(1, len(proposals) == 2 and all(p["status"] == "pending" for p in proposals), "dua usulan lahir berstatus pending")
        after = await fingerprint(BUSINESS)
        check(1, before == after and await db.activities.count_documents({}) == act_before,
              "koleksi bisnis & aktivitas tidak berubah selama usulan belum disetujui")
        res = await actions.approve(proposals[0]["id"], owner, tok)
        check(1, res["status"] == "executed", "usulan yang disetujui berstatus executed")
        notes = await db.activities.count_documents({"entity_id": lead["id"], "body": "Catatan gate"})
        check(1, notes == 1, "perubahan bisnis muncul tepat sekali setelah executed")
        cur = (await http.get(f"/api/leads/{lead['id']}", headers=hdr)).json()["data"]
        check(1, cur["stage"] == "acquisition" and (await actions.get(proposals[1]["id"]))["status"] == "pending",
              "usulan lain yang belum disetujui tidak berefek (tahap lead tetap)")
        executed = await db.ai_actions.find({"status": "executed"}, {"_id": 0}).to_list(500)
        check(5, len(executed) >= 1, "ada aksi executed untuk diperiksa")
        for a in executed:
            log = await db.audit_logs.find_one({"action": "ai_action_executed", "meta.action_id": a["id"]})
            check(5, bool(log) and log["meta"].get("actor_type") == "ai" and bool(log["meta"].get("approved_by")),
                  f"aksi {a['id'][:8]} executed punya audit (aktor AI + penyetuju)")

        # ------------------------------------------------ helper WA
        phone_n = [0]

        async def wa_job(body="Harga unit tipe 36 berapa?", channel="cloud"):
            phone_n[0] += 1
            phone = f"+6281277{phone_n[0]:06d}"
            conv_ = {"id": new_id(), "org_id": ORG_ID, "channel": "whatsapp", "contact_phone": phone, "contact_name": "Gate",
                     "lead_id": None, "owner": None, "status": "new", "mode": "simulation", "unread": 1,
                     "window_expires_at": due_in(hours=24), "created_at": now_iso(), "updated_at": now_iso()}
            await db.conversations.insert_one(dict(conv_))
            m = {"id": new_id(), "org_id": ORG_ID, "conversation_id": conv_["id"], "direction": "in", "body": body,
                 "sender": "contact", "channel": channel, "created_at": now_iso()}
            await db.messages.insert_one(dict(m))
            from ai import consent
            await consent.mark_noticed(ORG_ID, phone)
            return conv_, {"id": new_id(), "org_id": ORG_ID, "conversation_id": conv_["id"], "message_id": m["id"], "phone": phone}

        def tri(cat):
            return {"content": [{"type": "text", "text": json.dumps({"category": cat, "intent": "tanya", "objections": [],
                                                                      "sentiment": "netral", "confidence": 0.9})}]}

        def txt(t):
            return {"content": [{"type": "text", "text": t}]}

        from ai import config as ai_config
        real_settings = ai_config.get_ai_settings

        async def live_settings(org_id=ORG_ID):  # kirim otomatis hanya di mode efektif live (FakeClaude tetap dipakai)
            return {**(await real_settings(org_id)), "effective_mode": "live"}

        async def auto_ready():
            ai_config.get_ai_settings = live_settings
            await ss.set_value("ai.category_modes", {**{c: "draft" for c in ALL}, "stok_harga": "auto"},
                               actor="gate", reason="gate", org_id=ORG_ID)
            await db.ai_drafts.delete_many({"org_id": ORG_ID})
            for _ in range(50):
                await db.ai_drafts.insert_one({"id": new_id(), "org_id": ORG_ID, "category": "stok_harga", "status": "sent", "text": "x",
                                               "correct": True, "outcome_at": now_iso(), "at": now_iso()})

        wa_before = await fingerprint(BUSINESS)
        # ------------------------------------------------ 2: tidak ada auto-send lewat kanal tidak resmi
        print("Invarian 2 — balasan otomatis tidak pernah lewat kanal tidak resmi")
        await auto_ready()
        ai_config.get_ai_settings = real_settings  # mode simulasi: syarat lain terpenuhi tetap hanya draf
        conv0, job0 = await wa_job(channel="cloud")
        set_override(FakeClaude([tri("stok_harga"), txt("Tipe 36 tersedia.")]))
        r0 = await wa_agent.process_job(job0)
        check(2, r0["status"] == "draft" and not await db.messages.count_documents({"conversation_id": conv0["id"], "direction": "out"}),
              "mode simulasi -> tidak pernah kirim otomatis ke pelanggan")
        await auto_ready()
        conv1, job1 = await wa_job(channel="cloud")
        set_override(FakeClaude([tri("stok_harga"), txt("Tipe 36 tersedia.")]))
        r1 = await wa_agent.process_job(job1)
        check(2, r1["status"] == "auto_sent", "kontrol: kanal resmi + syarat terpenuhi -> terkirim otomatis (gate tidak hampa)")
        # Kanal tidak resmi DIAKTIFKAN penuh (kredensial + opt-in) supaya satu-satunya pengaman adalah aturan AI.
        import wa_gateway as gw
        calls = []

        def handler(request):
            calls.append(request)
            return httpx.Response(200, json={"id": f"gw-{len(calls)}"})
        wa_channels.TRANSPORT = httpx.MockTransport(handler)
        await wa_channels.save_unofficial_config(ORG_ID, {"enabled": True, "base_url": "https://gw.example.test", "token": "tok-gate",
                                                          "send_path": "/send", "webhook_secret": "gate-secret-0123456789",
                                                          "hourly_limit": 50,
                                                          "payload_template": '{"number": "{to}", "message": "{text}"}'}, actor="gate")
        conv2, job2 = await wa_job("Harga tipe 45?", channel="unofficial")
        await db.ai_consents.update_one({"org_id": ORG_ID, "phone": gw.valid_phone(job2["phone"])},
                                        {"$set": {"optins": {"unofficial": True}}}, upsert=True)
        set_override(FakeClaude([tri("stok_harga"), txt("Tipe 45 tersedia.")]))
        r2 = await wa_agent.process_job(job2)
        check(2, r2["status"] == "draft", f"kanal tidak resmi -> hanya draf (status={r2['status']})")
        try:
            await drafts.dispatch(ORG_ID, conv2["id"], "tes", actor="ai-auto")
            refused = False
        except drafts.DraftError:
            refused = True
        check(2, refused and not calls, "dispatch(actor=ai-auto) pada kanal tidak resmi ditolak")
        blocked = await wa_channels.send_unofficial(ORG_ID, job2["phone"], "tes", actor="ai-auto", ai_generated=True,
                                                    conversation_id=conv2["id"])
        check(2, not calls, "tidak ada permintaan HTTP ke gateway tidak resmi dari jalur AI otomatis")
        check(2, blocked.get("status") in ("blocked", "rate_limited", "failed"), "send_unofficial(ai_generated) ditolak")
        human = await wa_channels.send_unofficial(ORG_ID, job2["phone"], "halo", actor="sales@sipro.co.id", ai_generated=False,
                                                  conversation_id=conv2["id"])
        check(2, human.get("status") == "sent" and len(calls) == 1, "kontrol: balasan MANUSIA lewat kanal tidak resmi tetap bisa (gate tidak hampa)")
        wa_channels.TRANSPORT = None
        bad = await db.messages.count_documents({"channel": "unofficial", "direction": "out",
                                                 "$or": [{"sender": "ai-auto"}, {"ai_generated": True}],
                                                 "status": {"$nin": ["blocked", "rate_limited", "failed"]}})
        check(2, bad == 0, "tidak ada satu pun pesan keluar unofficial dari AI otomatis yang terkirim")
        # ------------------------------------------------ 3: anggaran stop
        print("Invarian 3 — anggaran stop -> 0 balasan otomatis")
        await auto_ready()
        real = budget.budget_state

        async def stop(org_id=None):
            return {"state": "stop", "spent_idr": 2, "limit_idr": 1, "pct": 200}
        budget.budget_state = stop
        try:
            conv3, job3 = await wa_job()
            fake = FakeClaude([tri("stok_harga"), txt("x")])
            set_override(fake)
            r3 = await wa_agent.process_job(job3)
            ok_allowed, _why = await wa_agent._auto_allowed(ORG_ID, conv3["id"], "stok_harga", "auto", [], [])
        finally:
            budget.budget_state = real
        check(3, r3["status"] == "budget_stop" and not fake.calls, "tugas dihentikan tanpa memanggil model")
        check(3, await db.messages.count_documents({"conversation_id": conv3["id"], "direction": "out"}) == 0, "0 pesan keluar")
        check(3, ok_allowed is False, "pintu auto menolak saat anggaran stop")

        # ------------------------------------------------ 4: wa_self tidak lintas kontak
        print("Invarian 4 — data wa_self hanya milik kontak terverifikasi")
        wa_ctx = ToolContext(org_id=ORG_ID, user={}, token="x", channel="wa", verified=True,
                             contact={"phone": "0811", "lead_id": None, "buyer_customer_id": "cA"})
        for tool in ("tagihan_pembeli", "status_kpr_kontrak", "progres_unit", "daftar_komplain"):
            rr = await registry.run(wa_ctx, tool, {"customer_id": "cB"})
            check(4, rr["ok"] is False, f"{tool}: customer_id pembeli lain ditolak")
        un = ToolContext(org_id=ORG_ID, user={}, token="x", channel="wa", verified=False,
                         contact={"phone": "0811", "buyer_customer_id": "cA"})
        names = {t.name for t in registry.tools_for(un)}
        check(4, not ({"tagihan_pembeli", "progres_unit", "status_kpr_kontrak", "api_get", "cari_endpoint"} & names),
              "kontak tak terverifikasi tidak diberi alat data pribadi/umum")
        rr = await registry.run(un, "tagihan_pembeli", {})
        check(4, rr["ok"] is False, "alat wa_self ditolak saat belum terverifikasi")

        check(1, await fingerprint(BUSINESS) == wa_before, "alur agen WA (draf/otomatis/anggaran) tidak mengubah koleksi bisnis")
        await http.aclose()
    try:
        import engine
        if engine._scheduler:
            engine._scheduler.shutdown(wait=False)
    except Exception:
        pass


asyncio.run(main())
print()
if FAILS:
    print(f"verify_ai: FAILED ({len(FAILS)} pelanggaran)")
    for f in FAILS:
        print("  -", f)
    sys.exit(1)
print("verify_ai: PASSED")
