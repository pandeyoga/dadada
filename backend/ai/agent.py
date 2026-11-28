"""Putaran agen: model ↔ alat, aliran peristiwa untuk UI/WA. Konten model disimpan & dikirim ulang apa adanya."""
import asyncio
import json
import logging
import time
from typing import AsyncIterator

from ai import actions, api_views, budget, config, conversations, prompts, web_research
from ai.client import ClaudeError, get_claude
from ai.tools import catalog, registry
from ai.tools.registry import ToolContext, wrap_untrusted

import secrets

catalog.load()
logger = logging.getLogger("estora.ai.agent")

MAX_ROUNDS = 12
MAX_TOKENS = 8192
REFUSAL_MSG = "Permintaan ini tidak bisa saya bantu."
EXEMPT_ROLES = ("owner", "super_admin")
ERR_MSG = {"rate_limit": "Layanan AI sedang sibuk (batas laju). Coba lagi sebentar lagi.",
           "overloaded": "Layanan AI sedang padat. Coba lagi sebentar lagi.",
           "auth": "Kunci API AI tidak valid. Hubungi admin.",
           "network": "Koneksi ke layanan AI terganggu. Coba lagi.",
           "bad_request": "Permintaan ke layanan AI ditolak. Hubungi admin bila terus terjadi."}


def _add_usage(total: dict, u: dict) -> None:
    for k, v in (u or {}).items():
        if isinstance(v, (int, float)):
            total[k] = total.get(k, 0) + v


def _result_block(tu: dict, res: dict) -> dict:
    if res["ok"]:
        data = res["data"]
        if isinstance(data, dict) and "artifact" in data:
            data = {**{k: v for k, v in data.items() if k != "artifact"}, "artifact_id": (data["artifact"] or {}).get("id")}
        return {"type": "tool_result", "tool_use_id": tu["id"], "content": json.dumps(data, ensure_ascii=False, default=str)}
    return {"type": "tool_result", "tool_use_id": tu["id"], "content": res["error"] or "Gagal.", "is_error": True}


BUDGET_MSG = "Anggaran AI bulan ini habis. Hubungi pemilik/admin untuk menambah anggaran."


async def _budget_stopped(ctx: ToolContext) -> bool:
    """Batas anggaran berlaku untuk SEMUA permukaan (web apa pun perannya, WA) kecuali pemilik/super admin."""
    if (ctx.user or {}).get("role") in EXEMPT_ROLES:
        return False
    return (await budget.budget_state(ctx.org_id))["state"] == "stop"


async def run_turn(ctx: ToolContext, conv_id: str, user_content: list, attachment_ids: list = None) -> AsyncIterator[dict]:
    """Satu giliran. Peristiwa `done` membawa `stop`: "ok" | "refusal" | "truncated" (WA memperlakukan selain ok sebagai gagal)."""
    org = ctx.org_id
    if await _budget_stopped(ctx):
        yield {"type": "error", "message": BUDGET_MSG}
        return
    s = await config.get_ai_settings(org)
    if s.get("effective_mode") == "off":
        yield {"type": "error", "message": "Estora AI sedang dimatikan oleh admin."}
        return
    try:
        claude = await get_claude(org)
    except Exception:  # noqa: BLE001
        yield {"type": "error", "message": "Layanan AI belum siap. Hubungi admin."}
        return
    if ctx.channel == "wa":  # pesan masuk WA = data tak tepercaya
        nonce = secrets.token_hex(4)
        user_content = [{**b, "text": wrap_untrusted(b["text"], nonce)} if b.get("type") == "text" else b for b in user_content]
    await conversations.append(conv_id, {"role": "user", "content": user_content,
                                         **({"attachment_ids": attachment_ids} if attachment_ids else {})})
    first_text = next((b.get("text", "") for b in user_content if b.get("type") == "text"), "")
    await conversations.set_title_if_new(conv_id, first_text)
    messages = await conversations.history_for_api(conv_id)
    # system & tools dihitung SEKALI per giliran dan dipakai ulang persis untuk setiap putaran alat:
    # blok thinking giliran ini terikat pada prefiks yang sama. Perubahan (mis. riset web dimatikan karena PII)
    # baru berlaku pada giliran pengguna berikutnya, ketika thinking giliran lama sudah dibuang dari riwayat.
    turn_tools = registry.api_specs(registry.tools_for(ctx)) + await web_research.extra_tools(ctx, conv_id)
    system = prompts.system_for(ctx.role, ctx)
    model = s["model_main"]
    effort = s["effort_wa"] if ctx.channel == "wa" else s["effort_copilot"]
    usage_total: dict = {}
    last_id = None
    continued = False

    for _round in range(MAX_ROUNDS):
        if _round and await _budget_stopped(ctx):
            msg = "Saya berhenti karena anggaran AI bulan ini habis."
            await conversations.append(conv_id, {"role": "assistant", "content": [{"type": "text", "text": msg}]})
            yield {"type": "error", "message": BUDGET_MSG}
            return
        q: asyncio.Queue = asyncio.Queue()

        async def on_text(t, q=q):
            await q.put(t)

        task = asyncio.create_task(claude.turn(
            model=model, system=system, messages=list(messages), tools=turn_tools, effort=effort, max_tokens=MAX_TOKENS,
            on_text=on_text, context={"conversation_id": conv_id, "role": ctx.role, "channel": ctx.channel}))
        while True:
            getter = asyncio.ensure_future(q.get())
            await asyncio.wait({getter, task}, return_when=asyncio.FIRST_COMPLETED)
            if getter.done():
                yield {"type": "text_delta", "text": getter.result()}
                continue
            getter.cancel()
            break
        while not q.empty():
            yield {"type": "text_delta", "text": q.get_nowait()}
        try:
            resp = task.result()
        except ClaudeError as e:
            yield {"type": "error", "message": ERR_MSG.get(e.kind, "Layanan AI bermasalah. Coba lagi.")}
            return
        except Exception:  # noqa: BLE001
            logger.exception("Giliran agen gagal")
            yield {"type": "error", "message": "Terjadi kesalahan pada layanan AI. Coba lagi."}
            return
        _add_usage(usage_total, resp.get("usage"))
        stop = resp.get("stop_reason")  # periksa SEBELUM membaca konten
        if stop == "refusal":
            m = await conversations.append(conv_id, {"role": "assistant", "content": [{"type": "text", "text": REFUSAL_MSG}]})
            yield {"type": "text_delta", "text": REFUSAL_MSG}
            yield {"type": "done", "message_id": m["id"], "usage": usage_total, "stop": "refusal"}
            return
        content = resp.get("content") or []
        if stop == "max_tokens" and any(b.get("type") == "tool_use" for b in content):
            msg = "Jawaban terpotong sebelum alat selesai dipanggil. Coba pertanyaan yang lebih spesifik."
            m = await conversations.append(conv_id, {"role": "assistant", "content": [{"type": "text", "text": msg}]})
            yield {"type": "text_delta", "text": msg}
            yield {"type": "done", "message_id": m["id"], "usage": usage_total, "stop": "truncated"}
            return
        await web_research.record(ctx, conv_id, content)
        m = await conversations.append(conv_id, {"role": "assistant", "content": content, "model": resp.get("model"),
                                                 "usage": resp.get("usage")})
        last_id = m["id"]
        messages.append({"role": "assistant", "content": content})
        if stop == "pause_turn":
            continue
        if stop == "max_tokens":
            if not continued:
                continued = True
                cont = [{"type": "text", "text": "Lanjutkan."}]
                await conversations.append(conv_id, {"role": "user", "content": cont})
                messages.append({"role": "user", "content": cont})
                continue
            msg = "\n\n(Jawaban dipotong karena terlalu panjang.)"
            await conversations.append(conv_id, {"role": "assistant", "content": [{"type": "text", "text": msg.strip()}]})
            yield {"type": "text_delta", "text": msg}
            yield {"type": "done", "message_id": last_id, "usage": usage_total, "stop": "truncated"}
            return
        uses = [b for b in content if b.get("type") == "tool_use"]
        if stop != "tool_use" or not uses:
            yield {"type": "done", "message_id": last_id, "usage": usage_total, "stop": "ok"}
            return
        # --- alat: jalankan paralel, semua tool_result dalam SATU pesan user
        by_id = {tu["id"]: registry.get(tu["name"]) for tu in uses}
        for tu in uses:
            yield {"type": "step_started", "id": tu["id"], "tool": tu["name"], "label": (by_id[tu["id"]].label if by_id[tu["id"]] else tu["name"])}

        async def one(tu):
            t0 = time.monotonic()
            res = await registry.run(ctx, tu["name"], tu.get("input") or {})
            return tu, res, int((time.monotonic() - t0) * 1000)

        pending = {asyncio.ensure_future(one(tu)) for tu in uses}
        done_res = {}
        while pending:
            fin, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
            for f in fin:
                tu, res, ms = f.result()
                done_res[tu["id"]] = res
                yield {"type": "step_done", "id": tu["id"], "ok": res["ok"], "summary": res["summary"], "ms": ms}
                d = res.get("data") if res["ok"] else None
                if isinstance(d, dict) and d.get("action_id"):
                    yield {"type": "action_proposed", "action": api_views.action_view(await actions.get(d["action_id"]))}
                if isinstance(d, dict) and d.get("artifact"):
                    yield {"type": "artifact", "artifact": d["artifact"]}
        results = [_result_block(tu, done_res[tu["id"]]) for tu in uses]
        await conversations.append(conv_id, {"role": "user", "content": results})
        messages.append({"role": "user", "content": results})

    msg = "Saya berhenti karena terlalu banyak langkah. Mohon persempit permintaan Anda."
    m = await conversations.append(conv_id, {"role": "assistant", "content": [{"type": "text", "text": msg}]})
    yield {"type": "text_delta", "text": msg}
    yield {"type": "error", "message": "Batas langkah tercapai (12 putaran alat)."}
