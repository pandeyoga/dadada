"""Akurasi draf/balasan AI per kategori: pintu mode `auto`, sampel audit, dan penurunan otomatis ke `draft`.

Benar = draf terkirim dengan kemiripan >= 0,9 terhadap teks akhir (atau sampel audit dinilai "benar").
Salah = draf ditulis ulang/dibuang/diedit berat (atau sampel dinilai "salah"). Jendela bergulir, nilai dari setelan `ai.*`.
"""
import hashlib
import logging
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher

import settings_store as ss
from ai import config, triage
from core_utils import now_iso
from db import db, ORG_ID

logger = logging.getLogger("estora.ai.accuracy")
SIMILAR = 0.9
LOCKED_REASON = "Kategori ini selalu diserahkan ke sales."


def similarity(a: str, b: str) -> float:
    a, b = (a or "").strip(), (b or "").strip()
    if a == b:
        return 1.0
    return round(SequenceMatcher(None, a, b).ratio(), 4)


async def record_outcome(draft_id: str, final_text, *, status: str = None) -> dict:
    """Catat hasil draf. `final_text=None` = dibuang. Draf yang sudah ditulis ulang tetap dihitung salah."""
    d = await db.ai_drafts.find_one({"id": draft_id}, {"_id": 0})
    if not d:
        raise LookupError("Draf tidak ditemukan.")
    if final_text is None:
        sim, correct, st = 0.0, False, status or "discarded"
    else:
        sim = similarity(d.get("original_text") or d["text"], final_text)
        correct = sim >= SIMILAR
        st = status or ("sent" if sim == 1.0 else "edited")
        if d["status"] == "rewritten" or d.get("correct") is False:
            correct = False  # sudah dinilai salah saat ditulis ulang
    upd = {"status": st, "final_text": final_text, "similarity": sim, "correct": correct, "outcome_at": now_iso()}
    await db.ai_drafts.update_one({"id": draft_id}, {"$set": upd})
    return {**d, **upd}


async def stats(org_id: str, category: str) -> dict:
    days = int(await ss.get("ai.accuracy_window_days", org_id=org_id))
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    rows = await db.ai_drafts.aggregate([
        {"$match": {"org_id": org_id, "category": category, "correct": {"$in": [True, False]}, "outcome_at": {"$gte": since}}},
        {"$group": {"_id": "$correct", "n": {"$sum": 1}}}]).to_list(2)
    n = {bool(r["_id"]): r["n"] for r in rows}
    total = n.get(True, 0) + n.get(False, 0)
    return {"accuracy": (n.get(True, 0) / total) if total else None, "samples": total}


async def can_enable_auto(org_id: str, category: str):
    """-> (boleh, alasan)."""
    if category in triage.LOCKED:
        return False, LOCKED_REASON
    if category not in triage.CATEGORIES:
        return False, "Kategori tidak dikenal."
    st = await stats(org_id, category)
    need = int(await ss.get("ai.accuracy_min_samples", org_id=org_id))
    thr = float(await ss.get("ai.accuracy_threshold", org_id=org_id))
    if st["samples"] < need:
        return False, f"Sampel kurang: {st['samples']} dari minimal {need} sampel."
    if st["accuracy"] < thr:
        return False, f"Akurasi {st['accuracy'] * 100:.1f}% masih di bawah ambang {thr * 100:.0f}%."
    return True, "Memenuhi syarat."


async def auto_gate(org_id: str, category: str) -> bool:
    """Bentuk yang dipakai `ai.config.set_auto_validator` (hanya bool)."""
    return (await can_enable_auto(org_id, category))[0]


config.set_auto_validator(auto_gate)


async def maybe_sample(draft: dict, rate: float = None) -> bool:
    """Pilih balasan otomatis untuk ditinjau manusia; deterministik per id draf."""
    if rate is None:
        rate = float(await ss.get("ai.auto_sample_rate", org_id=draft.get("org_id", ORG_ID)))
    h = int(hashlib.sha256(str(draft["id"]).encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
    return h < rate


async def review_sample(draft_id: str, verdict: str, user: dict) -> dict:
    if verdict not in ("correct", "wrong"):
        raise ValueError("Penilaian harus 'correct' atau 'wrong'.")
    d = await db.ai_drafts.find_one({"id": draft_id, "org_id": user.get("org_id", ORG_ID)}, {"_id": 0})
    if not d:
        raise LookupError("Sampel tidak ditemukan.")
    if d["status"] != "auto_sent" or not d.get("sampled"):
        raise ValueError("Draf ini bukan sampel untuk ditinjau.")
    if d.get("sample_review"):
        raise ValueError("Sampel ini sudah ditinjau.")
    upd = {"sample_review": verdict, "correct": verdict == "correct", "outcome_at": now_iso(),
           "reviewed_by": user.get("email")}
    await db.ai_drafts.update_one({"id": draft_id}, {"$set": upd})
    await check_demote(d["org_id"], d["category"])
    return {**d, **upd}


async def _notify_demote(org_id: str, category: str, reason: str) -> None:
    from engine import create_notification
    label = triage.CATEGORY_INFO.get(category, (category,))[0]
    async for u in db.users.find({"org_id": org_id, "role": {"$in": ["super_admin", "owner"]}, "is_active": {"$ne": False}},
                                 {"_id": 0, "email": 1}):
        await create_notification(user_email=u["email"], title=f"Estora AI: '{label}' diturunkan ke Draf",
                                  body=reason, type="warning", related_entity_type="ai_category",
                                  related_entity_id=category, org_id=org_id)


async def check_demote(org_id: str, category: str, *, negative_signal: bool = False) -> bool:
    """Turunkan kategori `auto` ke `draft` + notifikasi admin bila akurasi < ambang atau ada sinyal negatif."""
    modes = await ss.get("ai.category_modes", org_id=org_id)
    if (modes or {}).get(category) != "auto":
        return False
    thr = float(await ss.get("ai.accuracy_threshold", org_id=org_id))
    st = await stats(org_id, category)
    if negative_signal:
        reason = "Pelanggan bereaksi negatif setelah balasan otomatis."
    elif st["accuracy"] is not None and st["accuracy"] < thr:
        reason = f"Akurasi {st['accuracy'] * 100:.1f}% ({st['samples']} sampel) di bawah ambang {thr * 100:.0f}%."
    else:
        return False
    await config.set_category_mode(org_id, category, "draft", actor="ai-accuracy")
    await _notify_demote(org_id, category, reason + " Mode diubah ke Draf; tinjau sebelum mengaktifkan Otomatis lagi.")
    logger.warning("Kategori %s diturunkan ke draft: %s", category, reason)
    return True
