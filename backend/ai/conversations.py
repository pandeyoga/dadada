"""Percakapan AI: koleksi `ai_conversations` + `ai_messages` (blok konten disimpan & dikirim ulang apa adanya)."""
from typing import Optional

from core_utils import new_id, now_iso
from db import db

WA_WINDOW = 30


async def create(org_id: str, owner_id: str, *, role: str, channel: str = "web", title: str = None,
                 contact: dict = None) -> dict:
    ts = now_iso()
    doc = {"id": new_id(), "org_id": org_id, "owner_id": owner_id, "role": role, "channel": channel,
           "title": title or "Percakapan baru", "contact": contact, "summary": None,
           "created_at": ts, "updated_at": ts}
    await db.ai_conversations.insert_one(dict(doc))
    return doc


async def list_for(owner_id: str, q: str = None) -> list:
    query = {"owner_id": owner_id}
    if q:
        import re
        query["title"] = {"$regex": re.escape(q), "$options": "i"}
    return await db.ai_conversations.find(query, {"_id": 0}).sort("updated_at", -1).to_list(200)


async def get(conv_id: str, owner_id: Optional[str]) -> dict:
    """Percakapan + pesannya. `owner_id=None` melewati cek pemilik (layanan internal, mis. WA)."""
    c = await db.ai_conversations.find_one({"id": conv_id}, {"_id": 0})
    if not c or (owner_id is not None and c["owner_id"] != owner_id):
        raise LookupError("Percakapan tidak ditemukan.")
    c["messages"] = await db.ai_messages.find({"conversation_id": conv_id}, {"_id": 0}).sort("seq", 1).to_list(2000)
    return c


async def append(conv_id: str, message: dict) -> dict:
    """Tambah pesan {"role","content",...}. `seq` naik atomik per percakapan."""
    conv = await db.ai_conversations.find_one_and_update(
        {"id": conv_id}, {"$inc": {"seq": 1}, "$set": {"updated_at": now_iso()}}, projection={"_id": 0, "seq": 1},
        return_document=True)
    if conv is None:
        raise LookupError("Percakapan tidak ditemukan.")
    doc = {"id": new_id(), "conversation_id": conv_id, "seq": conv["seq"], "created_at": now_iso(), **message}
    await db.ai_messages.insert_one(dict(doc))
    return doc


async def set_title_if_new(conv_id: str, text: str) -> None:
    await db.ai_conversations.update_one({"id": conv_id, "title": "Percakapan baru"},
                                         {"$set": {"title": (text or "").strip()[:60] or "Percakapan baru"}})


def _api_msg(m: dict) -> dict:
    return {"role": m["role"], "content": m["content"]}


def _starts_clean(m: dict) -> bool:
    c = m["content"]
    return m["role"] == "user" and not (isinstance(c, list) and any(b.get("type") == "tool_result" for b in c))


async def history_for_api(conv_id: str) -> list:
    conv = await db.ai_conversations.find_one({"id": conv_id}, {"_id": 0})
    if not conv:
        raise LookupError("Percakapan tidak ditemukan.")
    msgs = await db.ai_messages.find({"conversation_id": conv_id}, {"_id": 0}).sort("seq", 1).to_list(5000)
    if conv.get("channel") == "wa":
        msgs = msgs[-WA_WINDOW:]
        while msgs and not _starts_clean(msgs[0]):  # jangan mulai dari tool_result yatim
            msgs = msgs[1:]
    out = [_api_msg(m) for m in msgs]
    if conv.get("channel") == "wa" and conv.get("summary"):
        note = {"type": "text", "text": f"[Ringkasan percakapan sebelumnya] {conv['summary']}"}
        if out and out[0]["role"] == "user":
            first = out[0]["content"]
            out[0] = {"role": "user", "content": [note] + (first if isinstance(first, list) else [{"type": "text", "text": first}])}
        else:
            out.insert(0, {"role": "user", "content": [note]})
    return out
