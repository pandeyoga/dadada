"""Lampiran Copilot disimpan sebagai rujukan (id berkas); isinya dibaca dari penyimpanan saat dikirim ke model."""
import base64

import storage
from db import db

MAX_ATTACH_BYTES = 8 * 1024 * 1024  # total per pesan
MAX_FILES = 5
MAX_TEXT_CHARS = 20000
TEXT_TYPES = ("text/", "application/json", "application/csv")
MARKER = "[Lampiran: "
EXPAND_LAST = 3  # hanya N pesan berlampiran terakhir yang dikembangkan jadi blok; yang lebih lama tetap teks


async def resolve(file_ids: list, org_id: str, owner_id: str) -> list:
    """Catatan berkas milik pengguna (maks 5) yang valid, urutan sesuai permintaan."""
    out = []
    for fid in (file_ids or [])[:MAX_FILES]:
        rec = await db.files.find_one({"id": fid, "org_id": org_id, "owner_type": "ai_attachment", "owner_id": owner_id},
                                      {"_id": 0})
        if rec:
            out.append(rec)
    return out


def marker(rec: dict) -> dict:
    return {"type": "text", "text": f"{MARKER}{rec.get('original_filename') or 'berkas'}]"}


async def blocks_for(file_ids: list, org_id: str, owner_id: str) -> list:
    blocks = []
    for rec in await resolve(file_ids, org_id, owner_id):
        name, ct = rec.get("original_filename") or "berkas", rec.get("content_type") or ""
        if (rec.get("size") or 0) > MAX_ATTACH_BYTES:
            blocks.append({"type": "text", "text": f"[Lampiran '{name}' terlalu besar dan tidak dibaca.]"})
            continue
        try:
            data, _ = await storage.get_file_bytes(rec["storage_path"], rec.get("provider"))
        except Exception:  # noqa: BLE001  (berkas hilang dari penyimpanan: tetap sebagai teks)
            blocks.append({"type": "text", "text": f"[Lampiran '{name}' tidak lagi tersedia.]"})
            continue
        b64 = base64.b64encode(data).decode()
        if ct in ("image/jpeg", "image/png", "image/gif", "image/webp"):
            blocks.append({"type": "image", "source": {"type": "base64", "media_type": ct, "data": b64}})
        elif ct == "application/pdf":
            blocks.append({"type": "document", "source": {"type": "base64", "media_type": ct, "data": b64}})
        elif ct.startswith(TEXT_TYPES):
            blocks.append({"type": "text", "text": f"[Lampiran '{name}']\n{data.decode('utf-8', 'replace')[:MAX_TEXT_CHARS]}"})
        else:
            blocks.append({"type": "text", "text": f"[Lampiran '{name}' ({ct}) diterima tetapi formatnya belum bisa dibaca.]"})
    return blocks


def is_marker(b: dict) -> bool:
    return b.get("type") == "text" and str(b.get("text", "")).startswith(MARKER)


async def expand(msgs: list, org_id: str, owner_id: str) -> list:
    """Kembangkan blok penanda `[Lampiran: ...]` pada EXPAND_LAST pesan berlampiran terakhir menjadi blok isi."""
    idx = [i for i, m in enumerate(msgs) if m.get("attachment_ids")][-EXPAND_LAST:]
    for i in idx:
        m = msgs[i]
        real = await blocks_for(m["attachment_ids"], org_id, owner_id)
        if not real:
            continue
        old = m["content"] if isinstance(m["content"], list) else [{"type": "text", "text": m["content"] or ""}]
        new, put = [], False
        for b in old:
            if is_marker(b):
                if not put:
                    new.extend(real)
                    put = True
            else:
                new.append(b)
        msgs[i] = {**m, "content": new if put else old + real}
    return msgs
