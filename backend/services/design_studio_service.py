"""Design Studio — pengembangan master desain (`design_gallery`) menjadi siklus hidup utuh.

Menambah: kategori per jenis, kode otomatis terkonfigurasi, tag tersimpan, palet warna
dari Pustaka Warna (wajib master), alternatif warna (colorway), rekomendasi produk,
foto referensi & mockup, nilai 0–2 kelipatan 0,25 per versi, timeline & umpan balik dua arah.
"""
import re
from typing import Any, Dict, List, Optional

from db import db
from core_utils import new_id, now_iso, safe_doc
from services.config_resolver import value_of


class DesignError(ValueError):
    pass


# ═══ LIFECYCLE ═══════════════════════════════════════════════════════════════
STATUSES = ("draft", "pending_approval", "in_review", "revision", "approved",
            "final_submitted", "active", "archived", "retired")
STATUS_LABEL = {
    "draft": "Draf", "pending_approval": "Diajukan", "in_review": "Dalam Review",
    "revision": "Perlu Revisi", "approved": "ACC — Menunggu Berkas Final",
    "final_submitted": "Final Diserahkan", "active": "Aktif / Produksi",
    "archived": "Diarsipkan", "retired": "Diarsipkan",
}
TRANSITIONS = {
    "submit": ({"draft", "revision"}, "pending_approval"),
    "start_review": ({"pending_approval"}, "in_review"),
    "request_revision": ({"pending_approval", "in_review"}, "revision"),
    "approve": ({"pending_approval", "in_review"}, "approved"),
    "submit_final": ({"approved"}, "final_submitted"),
    "return_final": ({"final_submitted"}, "approved"),
    "activate": ({"final_submitted"}, "active"),
    "archive": ({"draft", "revision", "approved", "final_submitted", "active", "pending_approval", "in_review"}, "archived"),
    "reopen": ({"archived", "retired"}, "draft"),
}

FILE_KINDS = ("artwork", "reference", "mockup", "colorway", "source", "ai_illustration")
DEFAULT_FINAL_COLOR_COUNT = 4
# HOLD — hanya desain yang sudah ACC; saat hold desain tidak bisa dipakai proofing R&D.
HOLDABLE = {"approved", "final_submitted", "active"}
SAMPLE_STATUS_LABEL = {"draft": "Draf", "sent": "Terkirim ke supplier", "in_progress": "Dikerjakan",
                       "assessed": "Ada yang ACC", "decided": "Pemenang dipilih", "cancelled": "Dibatalkan"}
PROOFING_STATE_LABEL = {"none": "Belum proofing", "in_progress": "Proofing berjalan",
                        "finished": "Proofing selesai", "master": "Sudah jadi master produk"}


def round_label(version: int) -> str:
    v = int(version or 1)
    return "Pengajuan awal" if v <= 1 else f"Revisi {v - 1}"


# ═══ KATEGORI — dua sumbu: `pattern` (Kategori Pattern) & `design` (Kategori Design) ═══
CATEGORY_AXES = ("pattern", "design")
DEFAULT_CATEGORIES = [
    ("pattern", "SLR", "Salur"), ("pattern", "BTK", "Batik"), ("pattern", "BGA", "Bunga"),
    ("pattern", "PLD", "Polkadot"), ("pattern", "ABS", "Abstrak"), ("pattern", "CSMR", "Cashmere"),
    ("design", "AO", "Allover"), ("design", "PG", "Pinggiran"),
]
_LEGACY_AXES = ("motif", "artwork")


async def ensure_categories() -> None:
    """Idempoten: kategori wajib klien selalu ada; sumbu lama (motif/artwork) dinonaktifkan."""
    marker = await db.design_categories.find_one({"design_type": "design"}, {"_id": 1})
    if marker:
        return
    for t, c, n in DEFAULT_CATEGORIES:
        await db.design_categories.update_one(
            {"design_type": t, "code": c},
            {"$setOnInsert": {"id": new_id("dcat"), "design_type": t, "code": c, "name": n,
                              "created_at": now_iso()},
             "$set": {"status": "active", "updated_at": now_iso()}}, upsert=True)
    await db.design_categories.update_many({"design_type": {"$in": list(_LEGACY_AXES)}},
                                           {"$set": {"status": "inactive", "updated_at": now_iso()}})


async def list_categories(design_type: str = "", status: str = "active") -> List[Dict[str, Any]]:
    await ensure_categories()
    q: Dict[str, Any] = {}
    if design_type:
        q["design_type"] = design_type
    if status and status != "all":
        q["status"] = status
    rows = await db.design_categories.find(q, {"_id": 0}).sort([("design_type", 1), ("name", 1)]).to_list(500)
    return [safe_doc(r) for r in rows]


async def create_category(data: Dict[str, Any]) -> Dict[str, Any]:
    code = re.sub(r"[^A-Z0-9]", "", (data.get("code") or "").upper())[:6]
    name = (data.get("name") or "").strip()
    dtype = (data.get("design_type") or "").strip().lower()
    if dtype not in CATEGORY_AXES:
        raise DesignError("Sumbu kategori harus 'pattern' (Kategori Pattern) atau 'design' (Kategori Design).")
    if len(code) < 2 or not name:
        raise DesignError("Kode kategori (2–6 huruf/angka) dan nama wajib diisi.")
    if await db.design_categories.find_one({"design_type": dtype, "code": code}, {"_id": 1}):
        raise DesignError(f"Kode kategori '{code}' sudah ada untuk jenis {dtype}.")
    doc = {"id": new_id("dcat"), "design_type": dtype, "code": code, "name": name,
           "status": "active", "created_at": now_iso(), "updated_at": now_iso()}
    await db.design_categories.insert_one(doc)
    return safe_doc(doc)


async def update_category(cat_id: str, patch: Dict[str, Any]) -> Dict[str, Any]:
    upd: Dict[str, Any] = {}
    if patch.get("name") is not None:
        upd["name"] = str(patch["name"]).strip()
    if patch.get("status") in ("active", "inactive"):
        upd["status"] = patch["status"]
    if not upd:
        raise DesignError("Tidak ada perubahan.")
    upd["updated_at"] = now_iso()
    res = await db.design_categories.find_one_and_update({"id": cat_id}, {"$set": upd},
                                                         projection={"_id": 0}, return_document=True)
    if not res:
        raise DesignError("Kategori tidak ditemukan.")
    return safe_doc(res)


async def category_of(design_type: str, code: str) -> Optional[Dict[str, Any]]:
    if not code:
        return None
    await ensure_categories()
    return safe_doc(await db.design_categories.find_one(
        {"design_type": design_type, "code": code.upper(), "status": "active"}, {"_id": 0}))


# ═══ KODE OTOMATIS ═══════════════════════════════════════════════════════════
def designer_prefix(name: str) -> str:
    """'Budi Santoso' → 'BDI' : huruf pertama + konsonan berikutnya, dilengkapi huruf terakhir."""
    first = re.sub(r"[^A-Za-z]", "", (name or "").strip().split(" ")[0]).upper()
    if not first:
        return "DSG"
    out = first[0] + "".join(ch for ch in first[1:] if ch not in "AEIOU")
    if len(out) < 3:
        out = (out + first[::-1])[:3] if len(first) >= 3 else (out + "X" * 3)[:3]
    return out[:3]


async def code_config(entity_id: str) -> Dict[str, Any]:
    ctx = {"entity_id": entity_id or ""}
    return {
        "pattern": await value_of("rnd.design_code_pattern", ctx),
        "seq_digits": int(await value_of("rnd.design_code_seq_digits", ctx) or 3),
        "type_prefix": {
            "motif": await value_of("rnd.design_prefix_motif", ctx),
            "pattern": await value_of("rnd.design_prefix_pattern", ctx),
            "artwork": await value_of("rnd.design_prefix_artwork", ctx),
        },
        "acc_min_score": float(await value_of("rnd.design_acc_min_score", ctx) or 0),
    }


async def next_code(entity_id: str, actor: Dict[str, Any], design_type: str,
                    category_code: str, design_category_code: str = "") -> Dict[str, Any]:
    cfg = await code_config(entity_id)
    dtype = (design_type or "").lower()
    dprefix = (actor.get("designer_code") or designer_prefix(actor.get("name", ""))).upper()
    parts = {"DESIGNER": dprefix, "TYPE": cfg["type_prefix"].get(dtype, dtype[:3].upper()) if dtype else "",
             "CAT": (category_code or "GEN").upper(), "DCAT": (design_category_code or "").upper(), "ENTITY": ""}
    ent = await db.business_entities.find_one({"id": entity_id}, {"_id": 0, "doc_prefix": 1}) or {}
    parts["ENTITY"] = ent.get("doc_prefix", "")
    pattern = cfg["pattern"] or "{DESIGNER}-{CAT}-{DCAT}-{SEQ}"
    base = pattern
    for k, v in parts.items():
        base = base.replace("{" + k + "}", v or "")
    base = re.sub(r"-{2,}", "-", base).lstrip("-")
    prefix = base.split("{SEQ}")[0]
    highest = 0
    async for row in db.design_gallery.find(
            {"entity_id": entity_id, "code": {"$regex": f"^{re.escape(prefix)}\\d+$"}},
            {"_id": 0, "code": 1}):
        try:
            highest = max(highest, int(re.findall(r"\d+$", row["code"])[0]))
        except (IndexError, ValueError):
            continue
    code = base.replace("{SEQ}", f"{highest + 1:0{cfg['seq_digits']}d}")
    return {"code": code, "designer_code": dprefix, "pattern": pattern, "parts": parts}


# ═══ TAG TERSIMPAN ═══════════════════════════════════════════════════════════
async def remember_tags(tags: List[str]) -> None:
    for t in tags or []:
        s = str(t).strip()
        if not s:
            continue
        await db.design_tags.update_one(
            {"name_lc": s.lower()},
            {"$setOnInsert": {"id": new_id("dtag"), "name": s, "name_lc": s.lower(),
                              "created_at": now_iso()},
             "$inc": {"uses": 1}, "$set": {"last_used_at": now_iso()}},
            upsert=True)


async def suggest_tags(q: str = "", limit: int = 20) -> List[Dict[str, Any]]:
    query: Dict[str, Any] = {}
    if q.strip():
        query["name_lc"] = {"$regex": re.escape(q.strip().lower())}
    rows = await db.design_tags.find(query, {"_id": 0, "name": 1, "uses": 1}).sort(
        [("uses", -1), ("name_lc", 1)]).to_list(limit)
    if not rows and not q:
        seen = set()
        async for d in db.design_gallery.find({}, {"_id": 0, "tags": 1}):
            for t in d.get("tags") or []:
                if t.lower() not in seen:
                    seen.add(t.lower())
                    rows.append({"name": t, "uses": 1})
    return rows[:limit]


# ═══ WARNA (wajib dari master) ═══════════════════════════════════════════════
async def resolve_colors(items: List[Any]) -> List[Dict[str, Any]]:
    """Setiap warna WAJIB merujuk `color_library` aktif; detail (kode/nama/hex) disalin dari master."""
    out: List[Dict[str, Any]] = []
    for it in items or []:
        cid = it.get("color_id") if isinstance(it, dict) else str(it)
        if not cid:
            continue
        c = await db.color_library.find_one({"id": cid, "status": "active"}, {"_id": 0})
        if not c:
            raise DesignError(f"Warna '{cid}' tidak ada di Pustaka Warna aktif — pilih dari master, "
                              "tidak boleh diketik bebas.")
        out.append({"color_id": c["id"], "code": c.get("code", ""), "name": c.get("name", ""),
                    "hex": c.get("hex", ""), "system": c.get("system", ""),
                    "role": (it.get("role") if isinstance(it, dict) else "") or ""})
    return out


async def resolve_products(ids: List[str]) -> List[Dict[str, Any]]:
    out = []
    for pid in ids or []:
        p = await db.products.find_one({"id": pid}, {"_id": 0, "id": 1, "sku": 1, "name": 1})
        if not p:
            raise DesignError(f"Produk '{pid}' tidak ditemukan.")
        out.append(p)
    return out


# ═══ TIMELINE & VERSI ════════════════════════════════════════════════════════
def event(actor: Dict[str, Any], kind: str, note: str = "", **extra) -> Dict[str, Any]:
    return {"id": new_id("evt"), "at": now_iso(), "by": actor.get("name", ""),
            "user_id": actor.get("id", ""), "role": actor.get("role", ""),
            "event": kind, "note": (note or "").strip(), **extra}


async def _doc(gallery_id: str) -> Dict[str, Any]:
    cur = await db.design_gallery.find_one({"id": gallery_id}, {"_id": 0})
    if not cur:
        raise DesignError("Desain tidak ditemukan.")
    return cur


def current_version(doc: Dict[str, Any]) -> Dict[str, Any]:
    v = int(doc.get("version") or 1)
    for row in doc.get("versions") or []:
        if int(row.get("version") or 0) == v:
            return row
    return {"version": v}


def _artworks_current(doc: Dict[str, Any]) -> List[Dict[str, Any]]:
    v = int(doc.get("version") or 1)
    return [f for f in doc.get("files") or []
            if (f.get("kind") or "artwork") == "artwork" and int(f.get("version") or 1) == v]


def validate_score(value: Any) -> float:
    try:
        s = float(value)
    except (TypeError, ValueError):
        raise DesignError("Nilai harus angka 0 – 2.")
    if s < 0 or s > 2 or abs(s * 4 - round(s * 4)) > 1e-6:
        raise DesignError("Nilai harus di antara 0 dan 2 dengan kelipatan 0,25 (mis. 1,25).")
    return round(s, 2)


def _files_of_kind(doc: Dict[str, Any], kind: str) -> List[Dict[str, Any]]:
    return [f for f in doc.get("files") or [] if (f.get("kind") or "artwork") == kind]


def final_requirement(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Berkas final wajib sesudah ACC: minimal 1 mockup + 1 file desain asli (source) yang bisa diunduh kembali."""
    mk = len(_files_of_kind(doc, "mockup"))
    src = len(_files_of_kind(doc, "source"))
    return {"colorway_required": 0, "colorway_files": len(_files_of_kind(doc, "colorway")),
            "mockup_required": 1, "mockup_files": mk, "source_required": 1, "source_files": src,
            "complete": mk >= 1 and src >= 1}


def rounds_of(doc: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Ringkasan tiap ronde (versi) untuk kotak progres: label, jumlah berkas, nilai, hasil."""
    out = []
    status = doc.get("status") or "draft"
    curv = int(doc.get("version") or 1)
    for v in sorted(doc.get("versions") or [], key=lambda r: int(r.get("version") or 0)):
        n = int(v.get("version") or 1)
        files = [f for f in doc.get("files") or []
                 if (f.get("kind") or "artwork") == "artwork" and int(f.get("version") or 1) == n]
        if v.get("acc"):
            result = "acc"
        elif n < curv or (n == curv and status == "revision"):
            result = "revision"
        elif n == curv and status in ("pending_approval", "in_review"):
            result = "review"
        else:
            result = "draft"
        out.append({"version": n, "label": round_label(n), "file_count": len(files),
                    "score": v.get("score"), "result": result, "note": v.get("note") or "",
                    "revision_note": v.get("revision_note") or "", "at": v.get("at")})
    return out


def enrich(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not doc:
        return doc
    out = dict(doc)
    cur = current_version(out)
    out["status_label"] = STATUS_LABEL.get(out.get("status") or "draft", out.get("status"))
    out["on_hold"] = bool(out.get("on_hold"))
    out["hold"] = out.get("hold") or {}
    out["hold_history"] = out.get("hold_history") or []
    out["current_score"] = cur.get("score")
    out["final_score"] = out.get("final_score")
    files = out.get("files") or []
    out["artwork_count"] = sum(1 for f in files if (f.get("kind") or "artwork") == "artwork")
    out["reference_count"] = sum(1 for f in files if f.get("kind") == "reference")
    out["mockup_count"] = sum(1 for f in files if f.get("kind") == "mockup")
    out["colorway_file_count"] = sum(1 for f in files if f.get("kind") == "colorway")
    out["colorway_count"] = len(out.get("colorways") or [])
    out["feedback_count"] = len(out.get("feedback") or [])
    out["revision_count"] = max(0, int(out.get("version") or 1) - 1)
    out["round_label"] = round_label(out.get("version") or 1)
    out["rounds"] = rounds_of(out)
    out["final"] = final_requirement(out)
    return out


async def transition(gallery_id: str, action: str, actor: Dict[str, Any], note: str = "",
                     score: Any = None, entity_id: str = "",
                     extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    extra = extra or {}
    if action not in TRANSITIONS:
        raise DesignError(f"Aksi '{action}' tidak dikenal.")
    cur = await _doc(gallery_id)
    allowed, target = TRANSITIONS[action]
    status = cur.get("status") or "draft"
    if status not in allowed:
        raise DesignError(f"Aksi ini tidak berlaku untuk status '{STATUS_LABEL.get(status, status)}'. "
                          f"Diperbolehkan dari: {', '.join(STATUS_LABEL[s] for s in sorted(allowed))}.")
    updates: Dict[str, Any] = {"status": target, "updated_at": now_iso()}
    push: Dict[str, Any] = {}
    if action == "submit":
        if not (cur.get("code") or "").strip():
            raise DesignError("Desain wajib punya kode sebelum diajukan.")
        if not _artworks_current(cur):
            raise DesignError(f"Ronde '{round_label(cur.get('version', 1))}' belum punya berkas desain — "
                              "unggah dulu hasil kerjanya (boleh beberapa file sekaligus).")
        updates.update({"submitted_by": actor.get("name", ""), "submitted_at": now_iso()})
    if action == "request_revision" and not (note or "").strip():
        raise DesignError("Catatan revisi wajib diisi supaya desainer tahu apa yang harus diperbaiki.")
    if action == "return_final" and not (note or "").strip():
        raise DesignError("Tulis apa yang kurang pada berkas final (mockup / varian warna).")
    if action == "archive" and not (note or "").strip():
        raise DesignError("Alasan pengarsipan wajib diisi.")
    if action == "submit_final":
        req = final_requirement(cur)
        if not req["complete"]:
            raise DesignError(
                f"Berkas final belum lengkap: mockup {req['mockup_files']}/1 dan file desain asli "
                f"{req['source_files']}/1. Keduanya WAJIB diunggah di tab Final sebelum diserahkan.")
        updates.update({"final_submitted_by": actor.get("name", ""), "final_submitted_at": now_iso()})
    if action == "activate" and cur.get("on_hold"):
        raise DesignError("Desain sedang HOLD — lepas hold dulu sebelum diaktifkan untuk produksi.")
    versions = list(cur.get("versions") or [])
    vidx = next((i for i, v in enumerate(versions)
                 if int(v.get("version") or 0) == int(cur.get("version") or 1)), None)
    # NILAI HANYA SAAT ACC (keputusan pemilik 2026-09): revisi tidak membawa nilai.
    if action == "approve" and score is not None and vidx is not None:
        versions[vidx].update({"score": validate_score(score), "score_by": actor.get("name", ""),
                               "score_at": now_iso(), "score_note": (note or "").strip()})
        updates["versions"] = versions
    if action == "approve":
        cfg = await code_config(entity_id or cur.get("entity_id", ""))
        sc = versions[vidx].get("score") if vidx is not None else None
        if sc is None:
            raise DesignError("Beri nilai (0–2) untuk versi ini saat ACC — nilai hanya diberikan sekali di akhir.")
        if float(sc) < cfg["acc_min_score"]:
            raise DesignError(f"Nilai {sc} di bawah ambang ACC {cfg['acc_min_score']} — "
                              "minta revisi atau ubah ambang di Pengaturan.")
        if vidx is not None:
            versions[vidx]["acc"] = True
            versions[vidx]["acc_at"] = now_iso()
            updates["versions"] = versions
        # Peruntukan produk & jumlah varian warna final ditetapkan PENILAI saat ACC (bukan desainer).
        if extra.get("recommended_product_ids") is not None:
            prods = await resolve_products(extra["recommended_product_ids"])
            updates.update({"recommended_products": prods,
                            "recommended_product_ids": [p["id"] for p in prods]})
        try:
            fcc = int(extra.get("final_color_count") or cur.get("final_color_count") or DEFAULT_FINAL_COLOR_COUNT)
        except (TypeError, ValueError):
            raise DesignError("Jumlah varian warna final harus angka.")
        if fcc < 1 or fcc > 20:
            raise DesignError("Jumlah varian warna final harus 1–20.")
        updates.update({"approved_by": actor.get("name", ""), "approved_at": now_iso(),
                        "approve_note": note or "", "final_score": sc,
                        "approved_version": cur.get("version", 1), "final_color_count": fcc})
    if action == "request_revision":
        # Ronde baru dibuka OTOMATIS: desainer cukup unggah hasil revisi lalu ajukan lagi.
        nextv = int(cur.get("version") or 1) + 1
        versions = list(updates.get("versions", versions))
        versions.append({"version": nextv, "note": f"{round_label(nextv)} — {note.strip()}",
                         "revision_note": note.strip(), "at": now_iso(),
                         "by": actor.get("name", ""), "files": [], "score": None})
        updates.update({"versions": versions, "version": nextv, "reject_reason": note.strip(),
                        "rejected_by": actor.get("name", ""), "rejected_at": now_iso()})
    if action == "activate":
        updates.update({"activated_by": actor.get("name", ""), "activated_at": now_iso()})
    if action == "archive":
        updates.update({"archived_by": actor.get("name", ""), "archived_at": now_iso(),
                        "archive_reason": note.strip()})
    if action == "reopen":
        updates.update({"final_score": None, "approved_by": "", "approved_at": ""})
    ev = event(actor, action, note, from_status=status, to_status=target,
               version=cur.get("version", 1), score=updates.get("versions", versions)[vidx].get("score")
               if vidx is not None and action == "approve" else None)
    if action == "request_revision":
        ev["next_version"] = updates["version"]
    push["timeline"] = ev
    await db.design_gallery.update_one({"id": gallery_id}, {"$set": updates, "$push": push})
    # Sinkron ke Permintaan Desain yang melahirkan desain ini (kalau ada).
    if (cur.get("request_id") or "").strip():
        try:
            from services import design_request_service as dsr
            fresh = await _doc(gallery_id)
            await dsr.sync_from_design(fresh if action != "submit" else {**fresh, "version": cur.get("version", 1)},
                                       action, actor, note=note or "",
                                       score=updates.get("versions", versions)[vidx].get("score")
                                       if vidx is not None and action == "approve" else None)
        except Exception as exc:  # noqa: BLE001
            print(f"[design_studio] sinkron permintaan gagal: {exc}")
    if action == "approve":
        # Fase 2 OD — desain dari pesanan khusus printing di-ACC → proofing R&D lahir otomatis.
        try:
            from services import special_order_phase2 as _p2
            await _p2.on_design_approved(await _doc(gallery_id), actor)
        except Exception as exc:  # noqa: BLE001
            print(f"[design_studio] proofing otomatis OD gagal: {exc}")
    label = f"{cur.get('code') or cur.get('title')}"
    if action == "submit":
        title = f"Desain {label} diajukan ({round_label(cur.get('version', 1))}) — menunggu review"
        body = f"{actor.get('name', '')} mengunggah {len(_artworks_current(cur))} berkas. " + (note or "")
    elif action == "submit_final":
        title = f"Berkas final desain {label} diserahkan — siap diaktifkan"
        body = f"{actor.get('name', '')} menyerahkan varian warna + mockup. " + (note or "")
    elif action == "request_revision":
        title = f"Desain {label}: perlu revisi → {round_label(updates['version'])} dibuka"
        body = note
    else:
        title = f"Desain {label}: {STATUS_LABEL[target]}"
        body = note or f"Status diubah oleh {actor.get('name', '')}."
    await _notify(cur, actor, title, body)
    return enrich(safe_doc(await _doc(gallery_id)))


async def set_hold(gallery_id: str, actor: Dict[str, Any], on: bool, reason: str = "") -> Dict[str, Any]:
    """HOLD desain yang sudah ACC: selama hold, desain tidak bisa dipakai proofing R&D / diaktifkan."""
    cur = await _doc(gallery_id)
    reason = (reason or "").strip()
    label = cur.get("code") or cur.get("title")
    if on:
        if (cur.get("status") or "draft") not in HOLDABLE:
            raise DesignError("Hold hanya untuk desain yang sudah ACC (ACC / Final Diserahkan / Aktif).")
        if cur.get("on_hold"):
            raise DesignError("Desain ini sudah dalam status HOLD.")
        if not reason:
            raise DesignError("Alasan hold wajib diisi supaya R&D tahu kenapa desain ditahan.")
        hold = {"by": actor.get("name", ""), "user_id": actor.get("id", ""), "at": now_iso(), "reason": reason}
        updates = {"on_hold": True, "hold": hold, "updated_at": now_iso()}
        ev = event(actor, "hold", reason, version=cur.get("version", 1), status=cur.get("status"))
        title, body = f"Desain {label} di-HOLD", f"{actor.get('name', '')}: {reason}"
    else:
        if not cur.get("on_hold"):
            raise DesignError("Desain ini tidak sedang HOLD.")
        prev = dict(cur.get("hold") or {})
        prev.update({"released_by": actor.get("name", ""), "released_at": now_iso(), "release_note": reason})
        updates = {"on_hold": False, "hold": {}, "updated_at": now_iso()}
        ev = event(actor, "release_hold", reason, version=cur.get("version", 1), status=cur.get("status"),
                   held_since=prev.get("at"), hold_reason=prev.get("reason"))
        title, body = f"Hold desain {label} dilepas", reason or f"Dilepas oleh {actor.get('name', '')}."
    push: Dict[str, Any] = {"timeline": ev}
    if not on:
        push["hold_history"] = prev
    await db.design_gallery.update_one({"id": gallery_id}, {"$set": updates, "$push": push})
    await _notify(cur, actor, title, body)
    return enrich(safe_doc(await _doc(gallery_id)))


async def log_external(design_id: str, actor: Any, kind: str, note: str = "", **extra) -> None:
    """Catat peristiwa dari modul lain (proofing R&D, spesifikasi, master produk) ke timeline desain."""
    if not design_id:
        return
    act = actor if isinstance(actor, dict) else {"name": str(actor or "")}
    try:
        await db.design_gallery.update_one({"id": design_id}, {
            "$push": {"timeline": event(act, kind, note, **extra)}, "$set": {"updated_at": now_iso()}})
    except Exception as exc:  # noqa: BLE001
        print(f"[design_studio] log_external gagal: {exc}")


def _is_proofing(sample: Dict[str, Any]) -> bool:
    types = sample.get("sample_types") or ([sample["sample_type"]] if sample.get("sample_type") else [])
    return "proofing" in [str(t).lower() for t in types]


async def attach_proofing(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Tempelkan ringkasan proofing R&D + master produk ke tiap desain (batch, 3 query)."""
    ids = [r.get("id") for r in rows if r and r.get("id")]
    if not ids:
        return rows
    smp_by: Dict[str, List[Dict[str, Any]]] = {}
    async for s in db.md_samples.find({"design_id": {"$in": ids}},
                                      {"_id": 0, "id": 1, "number": 1, "status": 1, "sample_types": 1,
                                       "sample_type": 1, "design_id": 1, "title": 1, "finished_at": 1,
                                       "delivered_at": 1, "decision": 1, "created_at": 1, "updated_at": 1,
                                       "rounds.result": 1, "rounds.supplier_name": 1, "spec_id": 1}):
        smp_by.setdefault(s["design_id"], []).append(s)
    spec_by: Dict[str, List[Dict[str, Any]]] = {}
    async for sp in db.md_specs.find({"design_id": {"$in": ids}},
                                     {"_id": 0, "id": 1, "number": 1, "status": 1, "lifecycle": 1,
                                      "product_id": 1, "product_sku": 1, "title": 1, "design_id": 1,
                                      "approved_at": 1, "released_at": 1}):
        spec_by.setdefault(sp["design_id"], []).append(sp)
    pids = [sp["product_id"] for L in spec_by.values() for sp in L if sp.get("product_id")]
    pids += [r.get("product_id") for r in rows if r.get("product_id")]
    prods: Dict[str, Dict[str, Any]] = {}
    if pids:
        async for p in db.products.find({"id": {"$in": list(set(pids))}}, {"_id": 0, "id": 1, "sku": 1, "name": 1}):
            prods[p["id"]] = p
    for r in rows:
        samples = []
        for s in smp_by.get(r.get("id"), []):
            if not _is_proofing(s) or s.get("status") == "cancelled":
                continue
            acc = sum(1 for x in (s.get("rounds") or []) if x.get("result") == "acc")
            done = s.get("status") == "decided" or bool(s.get("finished_at"))
            samples.append({"id": s["id"], "number": s.get("number", ""), "title": s.get("title", ""),
                            "status": s.get("status", ""), "status_label": SAMPLE_STATUS_LABEL.get(s.get("status", ""), s.get("status", "")),
                            "finished": done, "finished_at": s.get("finished_at") or "",
                            "delivered_at": s.get("delivered_at") or "", "rounds": len(s.get("rounds") or []),
                            "acc_rounds": acc, "winner": (s.get("decision") or {}).get("supplier_name", ""),
                            "created_at": s.get("created_at"), "updated_at": s.get("updated_at")})
        specs = []
        master = None
        for sp in spec_by.get(r.get("id"), []):
            p = prods.get(sp.get("product_id") or "")
            specs.append({"id": sp["id"], "number": sp.get("number", ""), "title": sp.get("title", ""),
                          "status": sp.get("status", ""), "lifecycle": sp.get("lifecycle", ""),
                          "product_id": sp.get("product_id", ""), "product_sku": (p or {}).get("sku") or sp.get("product_sku", ""),
                          "product_name": (p or {}).get("name", ""), "approved_at": sp.get("approved_at", "")})
            if sp.get("product_id") and not master:
                master = {"product_id": sp["product_id"], "sku": (p or {}).get("sku") or sp.get("product_sku", ""),
                          "name": (p or {}).get("name", ""), "lifecycle": sp.get("lifecycle", ""),
                          "spec_id": sp["id"], "spec_number": sp.get("number", ""), "since": sp.get("approved_at", "")}
        if not master and r.get("product_id") and prods.get(r["product_id"]):
            p = prods[r["product_id"]]
            master = {"product_id": p["id"], "sku": p.get("sku", ""), "name": p.get("name", ""),
                      "lifecycle": "", "spec_id": "", "spec_number": "", "since": ""}
        if master:
            state = "master"
        elif any(s["finished"] for s in samples):
            state = "finished"
        elif samples:
            state = "in_progress"
        else:
            state = "none"
        running = [s for s in samples if not s["finished"]]
        finished = [s for s in samples if s["finished"]]
        if state == "master":
            detail = f"Master produk {master['sku']}" + (f" — {master['name']}" if master.get("name") else "")
        elif state == "finished":
            detail = f"Selesai: {', '.join(s['number'] for s in finished)}" + (f" · {len(running)} masih berjalan" if running else "")
        elif state == "in_progress":
            detail = " · ".join(f"{s['number']} ({s['status_label']})" for s in running)
        else:
            detail = "Belum ada permintaan proofing R&D"
        r["proofing"] = {"state": state, "label": PROOFING_STATE_LABEL[state], "detail": detail,
                         "samples": samples, "specs": specs, "master_product": master,
                         "running_count": len(running), "finished_count": len(finished)}
    return rows


async def add_feedback(gallery_id: str, actor: Dict[str, Any], text: str,
                       version: Optional[int] = None) -> Dict[str, Any]:
    cur = await _doc(gallery_id)
    if not (text or "").strip():
        raise DesignError("Isi umpan balik tidak boleh kosong.")
    fb = {"id": new_id("fb"), "text": text.strip(), "by": actor.get("name", ""),
          "user_id": actor.get("id", ""), "role": actor.get("role", ""), "at": now_iso(),
          "version": int(version or cur.get("version") or 1),
          "side": "designer" if actor.get("role") == "designer" else "assessor"}
    ev = event(actor, "feedback", text.strip()[:200], version=fb["version"])
    await db.design_gallery.update_one({"id": gallery_id}, {
        "$push": {"feedback": fb, "timeline": ev}, "$set": {"updated_at": now_iso()}})
    await _notify(cur, actor, f"Umpan balik desain {cur.get('code') or cur.get('title')}",
                  text.strip()[:160])
    return fb


async def new_version(gallery_id: str, actor: Dict[str, Any], note: str,
                      patch: Dict[str, Any]) -> Dict[str, Any]:
    cur = await _doc(gallery_id)
    if (cur.get("status") or "draft") not in ("draft", "approved", "active"):
        raise DesignError("Versi baru manual hanya dari Draf, ACC, atau Aktif — saat 'Perlu Revisi' "
                          "ronde baru sudah dibuka otomatis, langsung unggah hasil revisinya.")
    if not (note or "").strip():
        raise DesignError("Tulis apa yang berubah pada versi ini.")
    nextv = int(cur.get("version") or 1) + 1
    entry = {"version": nextv, "note": note.strip(), "at": now_iso(), "by": actor.get("name", ""),
             "files": [], "score": None}
    updates: Dict[str, Any] = {"version": nextv, "status": "draft", "updated_at": now_iso()}
    for num, caster in (("repeat_cm", float), ("color_count", int), ("screen_count", int)):
        if patch.get(num) is not None:
            updates[num] = caster(patch[num])
    ev = event(actor, "new_version", note, from_status=cur.get("status"), to_status="draft", version=nextv)
    await db.design_gallery.update_one({"id": gallery_id}, {
        "$set": updates, "$push": {"versions": entry, "timeline": ev}})
    return enrich(safe_doc(await _doc(gallery_id)))


# ═══ COLORWAY (alternatif warna) ════════════════════════════════════════════
async def add_colorway(gallery_id: str, actor: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
    cur = await _doc(gallery_id)
    colors = await resolve_colors(data.get("colors") or [])
    if not colors:
        raise DesignError("Alternatif warna wajib punya minimal 1 warna dari Pustaka Warna.")
    n = len(cur.get("colorways") or []) + 1
    cw = {"id": new_id("cw"), "code": f"{cur.get('code') or 'DSG'}-CW{n:02d}",
          "name": (data.get("name") or f"Alternatif {n}").strip(), "colors": colors,
          "note": (data.get("note") or "").strip(), "file_ids": [],
          "is_default": bool(data.get("is_default")), "created_by": actor.get("name", ""),
          "created_at": now_iso()}
    ev = event(actor, "colorway_added", cw["name"], colorway_id=cw["id"])
    await db.design_gallery.update_one({"id": gallery_id}, {
        "$push": {"colorways": cw, "timeline": ev}, "$set": {"updated_at": now_iso()}})
    return cw


async def update_colorway(gallery_id: str, cw_id: str, data: Dict[str, Any], actor: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    cur = await _doc(gallery_id)
    cws = list(cur.get("colorways") or [])
    idx = next((i for i, c in enumerate(cws) if c.get("id") == cw_id), None)
    if idx is None:
        raise DesignError("Alternatif warna tidak ditemukan.")
    if data.get("colors") is not None:
        cws[idx]["colors"] = await resolve_colors(data["colors"])
    if data.get("name") is not None:
        cws[idx]["name"] = str(data["name"]).strip()
    if data.get("note") is not None:
        cws[idx]["note"] = str(data["note"]).strip()
    if data.get("is_default") is not None:
        for c in cws:
            c["is_default"] = False
        cws[idx]["is_default"] = bool(data["is_default"])
    cws[idx]["updated_at"] = now_iso()
    ev = event(actor or {}, "colorway_updated", cws[idx].get("name", ""), colorway_id=cw_id)
    await db.design_gallery.update_one({"id": gallery_id}, {"$set": {"colorways": cws, "updated_at": now_iso()},
                                                            "$push": {"timeline": ev}})
    return cws[idx]


async def delete_colorway(gallery_id: str, cw_id: str, actor: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    cur = await _doc(gallery_id)
    name = next((c.get("name", "") for c in cur.get("colorways") or [] if c.get("id") == cw_id), "")
    await db.design_gallery.update_one({"id": gallery_id}, {
        "$pull": {"colorways": {"id": cw_id}}, "$set": {"updated_at": now_iso()},
        "$push": {"timeline": event(actor or {}, "colorway_deleted", name, colorway_id=cw_id)}})
    return {"id": cw_id, "deleted": True}


async def _notify(doc: Dict[str, Any], actor: Dict[str, Any], title: str, body: str) -> None:
    try:
        from services import notification_service as notif
        roles = ("designer",) if actor.get("role") != "designer" else ("manager", "admin")
        await notif.create_addressed(roles=roles, entity_id=doc.get("entity_id"),
                                     notif_type="design_lifecycle", title=title, body=body[:200],
                                     severity="info", link="rnd-designs", ref=doc.get("id", ""))
    except Exception as exc:  # noqa: BLE001
        print(f"[design_studio] notifikasi gagal: {exc}")
