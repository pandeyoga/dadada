"""Bentuk respons UI untuk Copilot: pesan mentah (blok Claude) -> pesan tampilan, lampiran jadi blok."""
import base64
import json

from ai import actions
from ai.report_tool import artifact_view
from ai.tools import registry
from db import db
import storage

MAX_ATTACH_BYTES = 8 * 1024 * 1024
MAX_TEXT_CHARS = 20000
TEXT_TYPES = ("text/", "application/json", "application/csv")


def action_view(a: dict) -> dict:
    if not a:
        return a
    prev = dict(a.get("preview") or {})
    prev.setdefault("on_behalf_of", a.get("on_behalf_of"))
    return {**a, "preview": prev, "editable": list(actions.EDITABLE.get(a.get("tool"), ()))}


async def _result_data(content):
    try:
        return json.loads(content) if isinstance(content, str) else None
    except ValueError:
        return None


async def ui_messages(raw: list) -> list:
    """Gabungkan pesan model berurutan menjadi satu pesan asisten per giliran (teks + langkah + aksi + artefak)."""
    out, cur, steps = [], None, {}
    for m in raw:
        blocks = m.get("content")
        if isinstance(blocks, str):
            blocks = [{"type": "text", "text": blocks}]
        blocks = blocks or []
        is_results = m["role"] == "user" and blocks and all(b.get("type") == "tool_result" for b in blocks)
        if m["role"] == "user" and not is_results:
            for b in blocks:  # tool_result sintetis yang diperbaiki ke depan pesan pengguna (langkah dibatalkan)
                st = steps.get(b.get("tool_use_id")) if b.get("type") == "tool_result" else None
                if st and b.get("is_error"):
                    st.update(ok=False, status="failed", summary=str(b.get("content"))[:200])
            cur = None
            text = "\n".join(b.get("text", "") for b in blocks if b.get("type") == "text")
            out.append({"id": m["id"], "role": "user", "text": text, "created_at": m.get("created_at")})
            continue
        if cur is None:
            cur = {"id": m["id"], "role": "assistant", "text": "", "steps": [], "actions": [], "artifacts": [],
                   "created_at": m.get("created_at")}
            out.append(cur)
        if m["role"] == "assistant":
            cur["id"] = m["id"]
            for b in blocks:
                if b.get("type") == "text" and b.get("text"):
                    cur["text"] += ("\n\n" if cur["text"] else "") + b["text"]
                elif b.get("type") == "tool_use":
                    t = registry.get(b["name"])
                    st = {"id": b["id"], "tool": b["name"], "label": t.label if t else b["name"],
                          "status": "done", "ok": True, "summary": ""}
                    steps[b["id"]] = st
                    cur["steps"].append(st)
        else:
            for b in blocks:
                st = steps.get(b.get("tool_use_id"))
                if not st:
                    continue
                if b.get("is_error"):
                    st.update(ok=False, status="failed", summary=str(b.get("content"))[:200])
                    continue
                d = await _result_data(b.get("content"))
                if isinstance(d, dict) and d.get("action_id"):
                    try:
                        cur["actions"].append(action_view(await actions.get(d["action_id"])))
                    except actions.ActionError:  # aksi terhapus: lewati, jangan jatuhkan tampilan percakapan
                        pass
                if isinstance(d, dict) and d.get("artifact_id"):
                    art = await db.ai_artifacts.find_one({"id": d["artifact_id"]}, {"_id": 0})
                    if art:
                        cur["artifacts"].append(artifact_view(art))
    return out


async def attachment_blocks(file_ids: list, user: dict) -> list:
    """Lampiran (id dari POST /ai/files) -> blok konten. Gambar/PDF sebagai blok base64, teks disisipkan."""
    blocks = []
    for fid in (file_ids or [])[:5]:
        rec = await db.files.find_one({"id": fid, "org_id": user.get("org_id"), "owner_type": "ai_attachment",
                                       "owner_id": user["id"]}, {"_id": 0})
        if not rec:
            continue
        name, ct = rec.get("original_filename") or "berkas", rec.get("content_type") or ""
        if (rec.get("size") or 0) > MAX_ATTACH_BYTES:
            blocks.append({"type": "text", "text": f"[Lampiran '{name}' terlalu besar dan tidak dibaca.]"})
            continue
        data, _ = await storage.get_file_bytes(rec["storage_path"], rec.get("provider"))
        b64 = base64.b64encode(data).decode()
        if ct in ("image/jpeg", "image/png", "image/gif", "image/webp"):
            blocks.append({"type": "image", "source": {"type": "base64", "media_type": ct, "data": b64}})
        elif ct == "application/pdf":
            blocks.append({"type": "document", "source": {"type": "base64", "media_type": ct, "data": b64}})
        elif ct.startswith(TEXT_TYPES):
            txt = data.decode("utf-8", "replace")[:MAX_TEXT_CHARS]
            blocks.append({"type": "text", "text": f"[Lampiran '{name}']\n{txt}"})
        else:
            blocks.append({"type": "text", "text": f"[Lampiran '{name}' ({ct}) diterima tetapi formatnya belum bisa dibaca.]"})
    return blocks
