"""Percakapan AI: koleksi `ai_conversations` + `ai_messages`.

Blok konten disimpan apa adanya. Saat dikirim ulang, giliran lama tanpa thinking (lihat `history_for_api`)."""
from typing import Optional

from ai import attachments, pii
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


def _blocks(m: dict) -> list:
    c = m.get("content")
    return c if isinstance(c, list) else [{"type": "text", "text": c or ""}]


def _starts_clean(m: dict) -> bool:
    """Giliran pengguna sungguhan (bukan pesan yang hanya berisi tool_result)."""
    return m["role"] == "user" and any(b.get("type") != "tool_result" for b in _blocks(m))


# ---------------------------------------------------------------- perbaikan tool_use yatim (I1)
CANCELLED = "Langkah dibatalkan (dihentikan pengguna atau proses terputus); hasilnya tidak tersedia."


def _orphans(msgs: list) -> list:
    """[(indeks pesan asisten, [tool_use_id tanpa tool_result di pesan berikutnya])]."""
    out = []
    for i, m in enumerate(msgs):
        if m["role"] != "assistant":
            continue
        ids = [b["id"] for b in _blocks(m) if b.get("type") == "tool_use" and b.get("id")]
        if not ids:
            continue
        nxt = msgs[i + 1] if i + 1 < len(msgs) else None
        answered = {b.get("tool_use_id") for b in _blocks(nxt)} if nxt and nxt["role"] == "user" else set()
        missing = [x for x in ids if x not in answered]
        if missing:
            out.append((i, missing))
    return out


async def _repair_orphans(conv_id: str, msgs: list) -> list:
    """Tambahkan tool_result sintetis (is_error) untuk setiap tool_use tanpa jawaban, DAN simpan perbaikannya,
    supaya riwayat yang dikirim ulang deterministik (sama persis di giliran berikutnya)."""
    for i, missing in reversed(_orphans(msgs)):
        results = [{"type": "tool_result", "tool_use_id": x, "content": CANCELLED, "is_error": True} for x in missing]
        nxt = msgs[i + 1] if i + 1 < len(msgs) else None
        if nxt is not None and nxt["role"] == "user":
            content = results + _blocks(nxt)  # tool_result wajib di depan isi pesan pengguna
            await db.ai_messages.update_one({"id": nxt["id"]}, {"$set": {"content": content, "repaired": True}})
            msgs[i + 1] = {**nxt, "content": content}
        else:  # sisipkan pesan tool_result tepat setelah tool_use (seq pecahan: urutan tetap, tanpa menomori ulang)
            doc = {"id": new_id(), "conversation_id": conv_id, "seq": msgs[i]["seq"] + 0.5, "created_at": now_iso(),
                   "role": "user", "content": results, "repaired": True}
            await db.ai_messages.insert_one(dict(doc))
            msgs.insert(i + 1, doc)
    return msgs


# ---------------------------------------------------------------- giliran lama tanpa thinking (C3)
_THINKING = ("thinking", "redacted_thinking")
_WEB_RESULTS = ("web_search_tool_result", "web_fetch_tool_result")


def _web_note(b: dict) -> dict:
    inp = b.get("input") or {}
    what = pii.mask(str(inp.get("query") or inp.get("url") or "")[:200], mask_phone=True)
    return {"type": "text", "text": f"[Riset web sebelumnya: {what}]"}


def _strip_old_turn(content: list) -> list:
    """Giliran SEBELUM pesan pengguna terakhir: buang thinking (pembuangan deterministik & tercatat di sini),
    ganti blok riset web server dengan teks pendek, dan buang sitasinya. Hasilnya sah walau `system`/`tools`
    berubah di giliran baru (tanggal, verifikasi, riset web dimatikan), karena tidak ada thinking lama yang dikirim ulang."""
    out = []
    for b in content:
        t = b.get("type")
        if t in _THINKING or t in _WEB_RESULTS:
            continue
        if t == "server_tool_use":
            out.append(_web_note(b))
        elif t == "text" and "citations" in b:
            out.append({k: v for k, v in b.items() if k != "citations"})
        else:
            out.append(b)
    return out or [{"type": "text", "text": "(tanpa teks)"}]


async def history_for_api(conv_id: str) -> list:
    """Riwayat untuk API, dipanggil sekali di awal giliran (setelah pesan pengguna baru disimpan).

    - tool_use yatim diperbaiki & disimpan (I1);
    - thinking/blok riset web hanya dipertahankan untuk giliran SAAT INI (jendela utuh di ekor); giliran lama
      dibuang thinking-nya secara deterministik, sehingga jendela 30 pesan WA dan prompt sistem yang berganti
      tanggal tidak pernah membatalkan thinking yang dikirim ulang. Dalam satu giliran, agen memakai daftar pesan
      di memori sehingga blok putaran alat dikirim ulang apa adanya.
    """
    conv = await db.ai_conversations.find_one({"id": conv_id}, {"_id": 0})
    if not conv:
        raise LookupError("Percakapan tidak ditemukan.")
    msgs = await db.ai_messages.find({"conversation_id": conv_id}, {"_id": 0}).sort("seq", 1).to_list(5000)
    msgs = await _repair_orphans(conv_id, msgs)
    if conv.get("channel") == "wa":
        msgs = msgs[-WA_WINDOW:]
        while msgs and not _starts_clean(msgs[0]):  # jangan mulai dari tool_result yatim / pesan asisten
            msgs = msgs[1:]
        if msgs and any(b.get("type") == "tool_result" for b in _blocks(msgs[0])):  # hasil perbaikan yatim di tepi jendela
            msgs[0] = {**msgs[0], "content": [b for b in _blocks(msgs[0]) if b.get("type") != "tool_result"]}
    msgs = await attachments.expand(msgs, conv["org_id"], conv["owner_id"])
    last_user = max((i for i, m in enumerate(msgs) if _starts_clean(m)), default=len(msgs))
    out = [{"role": m["role"], "content": _strip_old_turn(_blocks(m))} if m["role"] == "assistant" and i < last_user
           else _api_msg(m) for i, m in enumerate(msgs)]
    if conv.get("channel") == "wa" and conv.get("summary"):
        note = {"type": "text", "text": f"[Ringkasan percakapan sebelumnya] {conv['summary']}"}
        if out and out[0]["role"] == "user":
            first = out[0]["content"]
            out[0] = {"role": "user", "content": [note] + (first if isinstance(first, list) else [{"type": "text", "text": first}])}
        else:
            out.insert(0, {"role": "user", "content": [note]})
    return out
