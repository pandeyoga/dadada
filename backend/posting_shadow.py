"""Resolver BAYANGAN posting profile (Fase 2): bandingkan jurnal yang BENAR-BENAR terbit dengan profil v0.

Dipanggil dari `gl_engine.post_journal` (pintu tunggal) SESUDAH jurnal tersimpan. Aturan keras:
  * tidak pernah mengubah jurnal / mengembalikan galat ke pemanggil (semua galat dicatat lewat logger);
  * bawaan MATI — hanya hidup bila env `POSTING_SHADOW=1`; mati = nol kueri dan nol pekerjaan tambahan;
  * biaya hidup: profil v0 ada di kode (0 kueri); satu `update_one` ($inc) statistik per jurnal peristiwa yang dicakup,
    ditambah satu upsert hanya bila ada SELISIH — tidak ada baca-tulis lain di jalur posting.
Masukan profil dari: (1) `hint` eksplisit dari pemanggil bila ada (gl_engine mengisinya dari dokumen sumber), lalu
(2) diturunkan dari baris jurnal itu sendiri (`derive` pada katalog) — jalur kedua dipakai untuk modul lain yang tidak
mengirim petunjuk; ia memeriksa akun/sisi/rumus tetapi tidak bisa menguji kondisi yang hanya ada di dokumen sumber.
"""
import logging
import os

import coa_rules
import posting_profile as pp
from core_utils import new_id, now_iso
from db import db

logger = logging.getLogger("sipro.posting_shadow")
ENV_FLAG = "POSTING_SHADOW"
KIND_OF_HEADER = dict(zip(coa_rules.CASH_HEADERS, ("cash", "bank")))   # urutan CASH_HEADERS = (kas, bank)


def enabled() -> bool:
    return os.environ.get(ENV_FLAG) == "1"


# ---------------------------------------------------------------------------------- peristiwa dari sumber
_INDEX: dict = {}


def _index() -> dict:
    if not _INDEX:
        for e in pp.EVENTS.values():
            for st, prefix in e["sources"]:
                _INDEX.setdefault(st, []).append((prefix or "", e["key"]))
    return _INDEX


def event_key_of(source_type, source_event, hint_key=None):
    """Kunci peristiwa katalog: petunjuk eksplisit, atau (source_type, awalan source_event) yang TUNGGAL."""
    if hint_key and hint_key in pp.EVENTS:
        return hint_key
    cands = [(len(p), k) for p, k in _index().get(source_type or "", ()) if (source_event or "").startswith(p)]
    if not cands:
        return None
    best = max(n for n, _k in cands)
    keys = {k for n, k in cands if n == best}
    return next(iter(keys)) if len(keys) == 1 else None


# --------------------------------------------------------------------------------------- tampilan jurnal
def _key_of(code: str, acct_map: dict) -> str:
    a = acct_map.get(code) or {}
    head = code if code in KIND_OF_HEADER else a.get("parent_code")
    return f"@{KIND_OF_HEADER[head]}" if head in KIND_OF_HEADER else code


def posted_view(lines: list, acct_map: dict) -> tuple:
    """Baris jurnal terbit → (agregat {(sisi, kunci): nilai}, lingkungan turunan D_*/K_*)."""
    agg = {}
    env = {f"{s}_{n}": 0 for s in "DK" for n in (*pp.ROLES, "CASH", "BANK")}
    for ln in lines:
        code = ln["account_code"]
        key = _key_of(code, acct_map)
        name = key[1:].upper() if key.startswith("@") else pp.CODE_TO_ROLE.get(code)
        for side, amt in (("D", int(ln.get("debit") or 0)), ("K", int(ln.get("credit") or 0))):
            if amt:
                agg[(side, key)] = agg.get((side, key), 0) + amt
                if name:
                    env[f"{side}_{name}"] += amt
    return agg, env


def derive_inputs(ev: dict, env: dict) -> dict:
    out = {name: pp.run_expr(expr, env) for name, expr in ev["derive"].items()}
    if ev.get("cash_rule") is not None:
        cash = env["D_CASH"] + env["K_CASH"]
        bank = env["D_BANK"] + env["K_BANK"]
        if cash or bank:
            out["cash_kind"] = "cash" if cash >= bank else "bank"
    return out


def _fmt(agg: dict) -> list:
    return [{"side": s, "key": k, "amount": v} for (s, k), v in sorted(agg.items())]


def compare(event_key: str, lines: list, acct_map: dict, hint_inputs: dict = None) -> dict:
    """Bandingkan jurnal terbit dengan profil v0. `equal` bila agregat (sisi, akun) sama persis."""
    ev = pp.EVENTS[event_key]
    posted, env = posted_view(lines, acct_map)
    derived = derive_inputs(ev, env)
    inputs = {**derived, **(hint_inputs or {})}   # petunjuk eksplisit (termasuk None = "tidak ada") menang
    base = {"event": event_key, "mode": "hint" if hint_inputs else "derived", "inputs": inputs,
            "posted": _fmt(posted)}
    try:
        res = pp.evaluate(event_key, inputs)
    except pp.ProfileError as e:
        return {**base, "equal": False, "error": str(e), "expected": [], "diff": []}
    expected = pp.aggregate(res["lines"])
    keys = sorted(set(expected) | set(posted))
    diff = [{"side": s, "key": k, "expected": expected.get((s, k), 0), "posted": posted.get((s, k), 0)}
            for s, k in keys if expected.get((s, k), 0) != posted.get((s, k), 0)]
    return {**base, "equal": not diff, "error": None, "expected": _fmt(expected), "diff": diff}


# ------------------------------------------------------------------------------------------ jalur posting
def stamp(doc: dict, hint=None) -> None:
    """Cap jejak pada dokumen jurnal baru (`profile_event`, `profile_version`) — metadata saja, tak pernah melempar.
    Dilakukan SELALU (bukan hanya saat bayangan hidup): murni komputasi, tanpa kueri."""
    try:
        key = event_key_of(doc.get("source_type"), doc.get("source_event"), hint[0] if hint else None)
        if key:
            doc["profile_event"] = key
            if pp.EVENTS[key]["covered"]:
                doc["profile_version"] = pp.VERSION
    except Exception:  # noqa: BLE001 — cap jejak tidak boleh menggagalkan posting
        logger.exception("posting_shadow: gagal mencap jejak jurnal %s", (doc or {}).get("source_event"))


async def observe(org_id: str, doc: dict, acct_map: dict, hint=None) -> None:
    """Bandingkan satu jurnal yang baru terbit. TIDAK PERNAH melempar galat. Mati ⇒ langsung kembali."""
    if not enabled():
        return
    try:
        hint_key, hint_inputs = hint if hint else (None, None)
        key = event_key_of(doc.get("source_type"), doc.get("source_event"), hint_key)
        if not key or not pp.EVENTS[key]["covered"]:
            return
        r = compare(key, doc["lines"], acct_map, hint_inputs)
        ts = now_iso()
        await db.posting_shadow_stats.update_one(
            {"org_id": org_id, "event_key": key},
            {"$inc": {"checked": 1, "ok" if r["equal"] else "diff": 1}, "$set": {"last_at": ts}}, upsert=True)
        if not r["equal"]:
            logger.warning("posting_shadow: SELISIH %s pada jurnal %s: %s", key, doc.get("entry_no"),
                           r["error"] or r["diff"])
            await db.posting_shadow_diffs.update_one(
                {"org_id": org_id, "journal_id": doc["id"]},
                {"$setOnInsert": {
                    "id": new_id(), "org_id": org_id, "journal_id": doc["id"], "entry_no": doc.get("entry_no"),
                    "source_type": doc.get("source_type"), "source_id": doc.get("source_id"),
                    "source_event": doc.get("source_event"), "event_key": key, "profile_version": pp.VERSION,
                    "mode": r["mode"], "inputs": r["inputs"], "error": r["error"], "diff": r["diff"],
                    "expected": r["expected"], "posted": r["posted"], "created_at": ts}}, upsert=True)
    except Exception:  # noqa: BLE001 — bayangan tidak boleh menggagalkan posting; galat dicatat
        logger.exception("posting_shadow: gagal membandingkan jurnal %s", (doc or {}).get("entry_no"))


# ----------------------------------------------------------------------------------- jalur baca (laporan)
async def verify_journal(org_id: str, journal_id: str) -> dict:
    """Bandingkan SATU jurnal tersimpan dengan profil v0 (read-only; masukan diturunkan dari barisnya)."""
    doc = await db.journal_entries.find_one({"id": journal_id, "org_id": org_id}, {"_id": 0})
    if not doc:
        return {"found": False}
    codes = sorted({ln["account_code"] for ln in doc.get("lines", [])})
    accts = {a["code"]: a for a in await db.accounts.find(
        {"org_id": org_id, "code": {"$in": codes}}, {"_id": 0, "code": 1, "parent_code": 1}).to_list(len(codes) + 1)}
    key = event_key_of(doc.get("source_type"), doc.get("source_event"), doc.get("profile_event"))
    head = {"found": True, "journal_id": journal_id, "entry_no": doc.get("entry_no"),
            "source_type": doc.get("source_type"), "source_event": doc.get("source_event"), "event": key}
    if not key:
        return {**head, "status": "tidak_dikenal", "equal": None,
                "detail": "Jurnal ini tidak cocok dengan peristiwa katalog mana pun."}
    if not pp.EVENTS[key]["covered"]:
        return {**head, "status": "belum_dicakup", "equal": None, "detail": pp.EVENTS[key]["why_not"]}
    r = compare(key, doc["lines"], accts)
    return {**head, "status": "sama" if r["equal"] else "beda", **{k: r[k] for k in (
        "equal", "error", "diff", "expected", "posted", "inputs")}}


async def report(org_id: str, limit: int = 20, days: int = 30) -> dict:
    """Ringkasan selisih bayangan per peristiwa + selisih terbaru + cakupan jurnal 30 hari menurut sumber."""
    stats = {s["event_key"]: s async for s in db.posting_shadow_stats.find({"org_id": org_id}, {"_id": 0})}
    rows = []
    for k, e in pp.EVENTS.items():
        s = stats.get(k) or {}
        rows.append({"event": k, "label": e["label"], "module": e["module"], "covered": e["covered"],
                     "checked": int(s.get("checked", 0)), "ok": int(s.get("ok", 0)), "diff": int(s.get("diff", 0)),
                     "last_at": s.get("last_at")})
    recent = await db.posting_shadow_diffs.find({"org_id": org_id}, {"_id": 0}).sort(
        "created_at", -1).to_list(max(1, min(int(limit), 100)))
    return {"enabled": enabled(), "env_flag": ENV_FLAG, "profile_version": pp.VERSION,
            "diffs_total": await db.posting_shadow_diffs.count_documents({"org_id": org_id}),
            "checked_total": sum(r["checked"] for r in rows), "events": rows, "recent_diffs": recent,
            "journals_by_source": await _journals_by_source(org_id, days)}


async def _journals_by_source(org_id: str, days: int) -> list:
    """Jumlah jurnal `days` hari terakhir per source_type + apakah peristiwa katalognya sudah dicakup. Dibatasi waktu."""
    from datetime import datetime, timedelta, timezone
    since = (datetime.now(timezone.utc) - timedelta(days=max(1, int(days)))).isoformat()
    try:
        rows = await db.journal_entries.aggregate([
            {"$match": {"org_id": org_id, "created_at": {"$gte": since}}},
            {"$group": {"_id": "$source_type", "n": {"$sum": 1}, "stamped": {"$sum": {
                "$cond": [{"$ifNull": ["$profile_event", False]}, 1, 0]}}}}], maxTimeMS=5000).to_list(200)
    except Exception:  # noqa: BLE001 — laporan opsional; tidak boleh menggagalkan endpoint
        logger.exception("posting_shadow: agregasi jurnal per sumber gagal")
        return []
    out = []
    for r in sorted(rows, key=lambda x: -x["n"]):
        st = r["_id"]
        evs = [k for k, e in pp.EVENTS.items() if any(s[0] == st for s in e["sources"])]
        out.append({"source_type": st, "journals": r["n"], "stamped": r["stamped"], "events": evs,
                    "covered": any(pp.EVENTS[k]["covered"] for k in evs), "in_catalog": bool(evs)})
    return out
