"""HRD H5 services — Design Gallery (motif kain) + upload gambar (storage lokal).

Koleksi kanonik (entity-scoped): `design_gallery` (dsgn_). Keputusan owner 3a:
upload gambar (JPG/PNG ≤10MB via storage_service) + judul + cerita + tags +
(opsional) link produk. AI auto-tag GRACEFUL via hr_ai_service (HR-Q5).

CATATAN storage: `storage_service.get_object()` MENGEMBALIKAN TUPLE (data, ctype).
"""
from typing import Any, Dict, List, Optional

from db import db
from core_utils import new_id, now_iso, safe_doc
from services import storage_service as storage
from services import hr_ai_service
from services import line_scope as _lines      # FASE L — satu pintu normalisasi lini


def _clean_tags(tags) -> List[str]:
    out, seen = [], set()
    for t in (tags or []):
        s = str(t).strip()
        k = s.lower()
        if s and k not in seen:
            seen.add(k)
            out.append(s)
    return out[:30]


DESIGN_TYPES = ("motif", "pattern", "artwork")
# UTANG ALUR F-6.7 (dibayar 2026-08-18): `pending_approval` disisipkan antara draf
# dan sah. Tanpa itu pengesahan bekerja dari `draft`, sehingga desain yang masih
# digambar desainer tak bisa dibedakan dari yang siap disahkan — dan antrean
# keputusan tidak mungkin menghitungnya tanpa menyebut pekerjaan orang sebagai
# antrean (alasan pembebasan lama di `verify_approval_queues.DOOR_EXEMPT`).
DESIGN_STATUSES = ("draft", "pending_approval", "in_review", "revision", "approved",
                   "active", "archived", "retired")


async def _next_design_code(title: str, entity_id: str) -> str:
    """Kode desain `DSG-<SLUG>-NN` yang unik per badan usaha (FASE D · DRIFT D4).

    Bukan `next_doc_number`: kode desain bukan nomor dokumen legal, dan yang
    membuatnya berguna justru potongan NAMA-nya ("DSG-PARANG-02" langsung terbaca
    manusia di percakapan). Urutan dihitung dari kode yang sudah ada dengan slug
    sama, jadi aman dipanggil berulang.
    """
    import re as _re
    slug = _re.sub(r"[^A-Z0-9]+", "", (title or "").upper().split(" ")[0])[:10] or "DESAIN"
    prefix = f"DSG-{slug}-"
    tertinggi = 0
    async for row in db.design_gallery.find(
            {"entity_id": entity_id, "code": {"$regex": f"^{_re.escape(prefix)}\\d+$"}},
            {"_id": 0, "code": 1}):
        try:
            tertinggi = max(tertinggi, int(str(row.get("code", "")).rsplit("-", 1)[-1]))
        except ValueError:
            continue
    return f"{prefix}{tertinggi + 1:02d}"


# ─── Rating desain (bintang 1–5, 1 nilai per penilai) ──────────────────────────
def _rating_fields(doc: Optional[Dict[str, Any]],
                   viewer_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Perkaya dokumen desain dengan ringkasan rating agar UI cukup baca 3 field:
    `rating_avg` (rata-rata bintang), `rating_count` (jumlah penilai), dan
    `my_rating` (bintang milik penilai yang sedang melihat, bila ada).

    Rating disimpan di `ratings: [{user_id, name, stars, note, at}]` — SATU baris
    per penilai (upsert), sehingga rata-rata selalu mencerminkan penilai unik.
    """
    if not doc:
        return doc
    ratings = doc.get("ratings") or []
    stars = [int(r.get("stars") or 0) for r in ratings if r.get("stars")]
    count = len(stars)
    out = dict(doc)
    out["rating_avg"] = round(sum(stars) / count, 2) if count else 0.0
    out["rating_count"] = count
    out["my_rating"] = None
    if viewer_id:
        for r in ratings:
            if r.get("user_id") == viewer_id:
                out["my_rating"] = int(r.get("stars") or 0)
                break
    return out


async def set_rating(gallery_id: str, user_id: str, name: str, stars: Any,
                     note: str = "") -> Dict[str, Any]:
    """Set/ubah rating bintang 1–5 milik SATU penilai (upsert, tanpa duplikat)."""
    try:
        stars_i = int(stars)
    except (TypeError, ValueError):
        raise ValueError("Nilai bintang harus angka 1–5.")
    if stars_i < 1 or stars_i > 5:
        raise ValueError("Nilai bintang harus di antara 1 sampai 5.")
    cur = await db.design_gallery.find_one({"id": gallery_id}, {"_id": 0})
    if not cur:
        raise ValueError("Entri galeri tidak ditemukan.")
    # buang rating lama milik penilai yang sama → jaga 1 baris per penilai
    ratings = [r for r in (cur.get("ratings") or []) if r.get("user_id") != user_id]
    ratings.append({"user_id": user_id, "name": name or "", "stars": stars_i,
                    "note": (note or "").strip(), "at": now_iso()})
    await db.design_gallery.update_one(
        {"id": gallery_id}, {"$set": {"ratings": ratings, "updated_at": now_iso()}})
    doc = safe_doc(await db.design_gallery.find_one({"id": gallery_id}, {"_id": 0}))
    return _rating_fields(doc, user_id)


async def clear_rating(gallery_id: str, user_id: str) -> Dict[str, Any]:
    """Hapus rating milik penilai (mis. salah beri nilai)."""
    cur = await db.design_gallery.find_one({"id": gallery_id}, {"_id": 0})
    if not cur:
        raise ValueError("Entri galeri tidak ditemukan.")
    ratings = [r for r in (cur.get("ratings") or []) if r.get("user_id") != user_id]
    await db.design_gallery.update_one(
        {"id": gallery_id}, {"$set": {"ratings": ratings, "updated_at": now_iso()}})
    doc = safe_doc(await db.design_gallery.find_one({"id": gallery_id}, {"_id": 0}))
    return _rating_fields(doc, user_id)


async def create_gallery(payload: Dict[str, Any], actor_name: str, entity_id: str,
                         actor: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    from services import design_studio_service as studio
    title = (payload.get("title") or "").strip()
    if not title:
        raise ValueError("Judul motif wajib diisi.")
    dtype = (payload.get("design_type") or "").strip().lower()
    if dtype and dtype not in DESIGN_TYPES:
        raise ValueError(f"Jenis desain harus salah satu: {', '.join(DESIGN_TYPES)}.")
    cat_code = (payload.get("category_code") or "").strip().upper()
    category = await studio.category_of("pattern", cat_code) if cat_code else None
    if cat_code and not category:
        raise ValueError(f"Kategori Pattern '{cat_code}' tidak ada / nonaktif.")
    dcat_code = (payload.get("design_category_code") or "").strip().upper()
    dcategory = await studio.category_of("design", dcat_code) if dcat_code else None
    if dcat_code and not dcategory:
        raise ValueError(f"Kategori Design '{dcat_code}' tidak ada / nonaktif.")
    # Design Studio — kode dibentuk OTOMATIS dari pola terkonfigurasi (bukan ketik bebas).
    code_info = await studio.next_code(entity_id, actor or {"name": actor_name}, dtype, cat_code, dcat_code)
    code = code_info["code"]
    if await db.design_gallery.find_one({"code": code, "entity_id": entity_id}, {"_id": 0, "id": 1}):
        raise ValueError(f"Kode desain '{code}' sudah dipakai pada entitas ini.")
    colors = await studio.resolve_colors(payload.get("colors") or [])
    products = await studio.resolve_products(payload.get("recommended_product_ids") or [])
    tags = _clean_tags(payload.get("tags"))
    await studio.remember_tags(tags)
    actor_doc = actor or {"name": actor_name}
    doc = {
        "id": new_id("dsgn"),
        "title": title, "story": payload.get("story", ""),
        "tags": tags,
        "files": [], "product_id": payload.get("product_id", ""),
        "code": code, "design_type": dtype, "version": 1, "status": "draft",
        "category_code": cat_code, "category_name": (category or {}).get("name", ""),
        "design_category_code": dcat_code, "design_category_name": (dcategory or {}).get("name", ""),
        "final_color_count": studio.DEFAULT_FINAL_COLOR_COUNT,
        "designer_code": code_info["designer_code"],
        "recommended_products": products,
        "recommended_product_ids": [p["id"] for p in products],
        "colors": colors, "colorways": [], "feedback": [],
        # FASE L — lini kerja MD desain (kosong = belum bergolong, tetap terlihat semua).
        "line_code": _lines.norm(payload.get("line_code")),
        "repeat_cm": payload.get("repeat_cm"),
        "color_count": int(payload.get("color_count") or 0) or len(colors),
        "screen_count": int(payload.get("screen_count") or 0),
        "versions": [{"version": 1, "note": "Versi awal", "at": now_iso(),
                      "by": actor_name, "files": [], "score": None}],
        "timeline": [studio.event(actor_doc, "created", "Desain dibuat", to_status="draft", version=1)],
        "approved_by": "", "approved_at": "", "final_score": None,
        "ratings": [],
        "ai_meta": {"enabled": False, "model": "", "tags": [], "summary": "",
                    "attributes": {}, "analyzed_at": ""},
        "entity_id": entity_id,
        "created_by": actor_name, "created_by_id": actor_doc.get("id", ""),
        "created_at": now_iso(), "updated_at": now_iso(),
    }
    await db.design_gallery.insert_one(doc)
    return studio.enrich(safe_doc(doc))


async def list_gallery(scope: Dict[str, Any], tag: Optional[str] = None,
                       q: Optional[str] = None,
                       viewer_id: Optional[str] = None,
                       filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    from services import design_studio_service as studio
    query: Dict[str, Any] = dict(scope or {})
    if tag:
        query["tags"] = tag
    for key in ("status", "design_type", "category_code", "created_by", "line_code"):
        if (filters or {}).get(key):
            query[key] = filters[key]
    if (filters or {}).get("product_id"):
        query["recommended_product_ids"] = filters["product_id"]
    if (filters or {}).get("color_id"):
        query["$or"] = [{"colors.color_id": filters["color_id"]},
                        {"colorways.colors.color_id": filters["color_id"]}]
    if (filters or {}).get("on_hold") in ("yes", "no"):
        query["on_hold"] = filters["on_hold"] == "yes"
    rows = await db.design_gallery.find(query, {"_id": 0}).sort("created_at", -1).to_list(2000)
    rows = [studio.enrich(_rating_fields(safe_doc(r), viewer_id)) for r in rows]
    if q:
        s = q.lower()
        rows = [r for r in rows if s in (r.get("title", "") or "").lower()
                or s in (r.get("code", "") or "").lower()
                or s in (r.get("story", "") or "").lower()
                or any(s in (t or "").lower() for t in (r.get("tags") or []))]
    return await studio.attach_proofing(rows)


async def get_gallery(gallery_id: str,
                      viewer_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    from services import design_studio_service as studio
    doc = studio.enrich(_rating_fields(
        safe_doc(await db.design_gallery.find_one({"id": gallery_id}, {"_id": 0})),
        viewer_id))
    if doc:
        await studio.attach_proofing([doc])
    return doc


# Label field untuk riwayat perubahan (sebelum → sesudah) yang ramah pengguna.
FIELD_LABEL = {
    "title": "Judul", "story": "Cerita / catatan", "tags": "Tag", "product_id": "Tautan produk",
    "line_code": "Lini", "category_code": "Kategori Pattern", "design_category_code": "Kategori Design",
    "final_color_count": "Jumlah varian warna final", "recommended_product_ids": "Peruntukan produk",
    "colors": "Palet warna", "code": "Kode desain", "design_type": "Jenis", "status": "Status",
    "repeat_cm": "Repeat (cm)", "color_count": "Jumlah warna", "screen_count": "Jumlah screen",
}


def _diff_changes(cur: Dict[str, Any], updates: Dict[str, Any]) -> List[Dict[str, Any]]:
    out = []
    for k, v in updates.items():
        if k in ("updated_at", "category_name", "design_category_name", "recommended_products"):
            continue
        before = cur.get(k)
        if k == "recommended_product_ids":
            before = [p.get("sku") for p in cur.get("recommended_products") or []]
            v = [p.get("sku") for p in updates.get("recommended_products") or []]
        if k == "colors":
            before = [c.get("code") or c.get("name") for c in cur.get("colors") or []]
            v = [c.get("code") or c.get("name") for c in updates.get("colors") or []]
        if before == v:
            continue
        out.append({"field": k, "label": FIELD_LABEL.get(k, k), "from": before, "to": v})
    return out


async def update_gallery(gallery_id: str, patch: Dict[str, Any],
                         actor: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    from pymongo import ReturnDocument
    cur = await db.design_gallery.find_one({"id": gallery_id}, {"_id": 0})
    if not cur:
        raise ValueError("Entri galeri tidak ditemukan.")
    updates: Dict[str, Any] = {}
    if patch.get("title") is not None:
        if not str(patch["title"]).strip():
            raise ValueError("Judul motif tidak boleh kosong.")
        updates["title"] = str(patch["title"]).strip()
    if patch.get("story") is not None:
        updates["story"] = patch["story"]
    if patch.get("product_id") is not None:
        updates["product_id"] = patch["product_id"]
    if patch.get("tags") is not None:
        updates["tags"] = _clean_tags(patch["tags"])
        from services import design_studio_service as _studio
        await _studio.remember_tags(updates["tags"])
    if patch.get("line_code") is not None:      # FASE L
        updates["line_code"] = _lines.norm(patch["line_code"])
    # Design Studio — Kategori Pattern + Kategori Design, peruntukan produk (penilai), varian final.
    if patch.get("category_code") is not None:
        from services import design_studio_service as _studio
        cat_code = str(patch["category_code"]).strip().upper()
        cat = await _studio.category_of("pattern", cat_code) if cat_code else None
        if cat_code and not cat:
            raise ValueError(f"Kategori Pattern '{cat_code}' tidak ada / nonaktif.")
        updates["category_code"] = cat_code
        updates["category_name"] = (cat or {}).get("name", "")
    if patch.get("design_category_code") is not None:
        from services import design_studio_service as _studio
        dcat_code = str(patch["design_category_code"]).strip().upper()
        dcat = await _studio.category_of("design", dcat_code) if dcat_code else None
        if dcat_code and not dcat:
            raise ValueError(f"Kategori Design '{dcat_code}' tidak ada / nonaktif.")
        updates["design_category_code"] = dcat_code
        updates["design_category_name"] = (dcat or {}).get("name", "")
    if patch.get("final_color_count") is not None:
        fcc = int(patch["final_color_count"])
        if fcc < 1 or fcc > 20:
            raise ValueError("Jumlah varian warna final harus 1–20.")
        updates["final_color_count"] = fcc
    if patch.get("recommended_product_ids") is not None:
        from services import design_studio_service as _studio
        prods = await _studio.resolve_products(patch["recommended_product_ids"])
        updates["recommended_products"] = prods
        updates["recommended_product_ids"] = [p["id"] for p in prods]
    if patch.get("colors") is not None:
        from services import design_studio_service as _studio
        updates["colors"] = await _studio.resolve_colors(patch["colors"])
        if patch.get("color_count") is None:
            updates["color_count"] = len(updates["colors"])
    # FASE F (PS-14) — atribut master desain.
    if patch.get("code") is not None:
        code = str(patch["code"]).strip().upper()
        if code:
            dup = await db.design_gallery.find_one(
                {"code": code, "entity_id": cur.get("entity_id"), "id": {"$ne": gallery_id}},
                {"_id": 0, "id": 1})
            if dup:
                raise ValueError(f"Kode desain '{code}' sudah dipakai desain lain.")
        updates["code"] = code
    if patch.get("design_type") is not None:
        dtype = str(patch["design_type"]).strip().lower()
        if dtype not in DESIGN_TYPES:
            raise ValueError(f"Jenis desain harus salah satu: {', '.join(DESIGN_TYPES)}.")
        updates["design_type"] = dtype
    if patch.get("status") is not None:
        st = str(patch["status"]).strip().lower()
        if st not in DESIGN_STATUSES:
            raise ValueError(f"Status desain harus salah satu: {', '.join(DESIGN_STATUSES)}.")
        updates["status"] = st
    for num, caster in (("repeat_cm", float), ("color_count", int), ("screen_count", int)):
        if patch.get(num) is not None:
            try:
                updates[num] = caster(patch[num])
            except (TypeError, ValueError):
                raise ValueError(f"Nilai '{num}' harus angka.")
    if not updates:
        raise ValueError("Tidak ada field valid untuk diupdate.")
    updates["updated_at"] = now_iso()
    changes = _diff_changes(cur, updates)
    op: Dict[str, Any] = {"$set": updates}
    if changes:
        from services import design_studio_service as _studio
        op["$push"] = {"timeline": _studio.event(
            actor or {}, "updated", ", ".join(c["label"] for c in changes), changes=changes,
            version=cur.get("version", 1))}
    doc = await db.design_gallery.find_one_and_update(
        {"id": gallery_id}, op,
        projection={"_id": 0}, return_document=ReturnDocument.AFTER)
    return safe_doc(doc)


async def delete_gallery(gallery_id: str) -> Dict[str, Any]:
    cur = await db.design_gallery.find_one({"id": gallery_id}, {"_id": 0})
    if not cur:
        raise ValueError("Entri galeri tidak ditemukan.")
    # FASE F — desain yang sudah dipakai spesifikasi/sample TIDAK boleh dihapus:
    # jejak asal motif harus tetap bisa ditelusuri (aturan repo: append-only).
    used_spec = await db.md_specs.count_documents({"design_id": gallery_id})
    used_smp = await db.md_samples.count_documents({"design_id": gallery_id})
    if used_spec or used_smp:
        raise ValueError(
            f"Desain ini sudah dipakai {used_spec} spesifikasi & {used_smp} permintaan sample — "
            "tidak bisa dihapus. Ubah statusnya menjadi 'retired' bila tidak dipakai lagi.")
    await db.design_gallery.delete_one({"id": gallery_id})
    return {"id": gallery_id, "deleted": True}


async def bump_version(gallery_id: str, payload: Dict[str, Any], actor_name: str) -> Dict[str, Any]:
    """FASE F (PS-14) — naikkan versi desain; berkas versi sebelumnya diarsipkan."""
    cur = await db.design_gallery.find_one({"id": gallery_id}, {"_id": 0})
    if not cur:
        raise ValueError("Entri galeri tidak ditemukan.")
    nextv = int(cur.get("version") or 1) + 1
    entry = {"version": nextv, "note": (payload.get("note") or "").strip(),
             "at": now_iso(), "by": actor_name,
             "files": [f.get("id") for f in (cur.get("files") or [])]}
    updates: Dict[str, Any] = {"version": nextv, "status": "draft",
                               "approved_by": "", "approved_at": "", "updated_at": now_iso()}
    for num, caster in (("repeat_cm", float), ("color_count", int), ("screen_count", int)):
        if payload.get(num) is not None:
            updates[num] = caster(payload[num])
    await db.design_gallery.update_one({"id": gallery_id},
                                      {"$set": updates, "$push": {"versions": entry}})
    return await get_gallery(gallery_id)


async def submit_design(gallery_id: str, actor_name: str) -> Dict[str, Any]:
    """draft → pending_approval (desainer menyatakan desain SIAP disahkan).

    Syarat kelengkapan diperiksa di SINI (kode + minimal 1 berkas), bukan hanya saat
    pengesahan: desain tanpa kode/berkas yang menumpuk di antrean penyetuju hanya
    memindahkan pekerjaan, bukan menyelesaikannya.
    """
    cur = await db.design_gallery.find_one({"id": gallery_id}, {"_id": 0})
    if not cur:
        raise ValueError("Entri galeri tidak ditemukan.")
    if cur.get("status") != "draft":
        raise ValueError(f"Hanya desain draf yang bisa diajukan (status sekarang: "
                         f"'{cur.get('status')}').")
    if not (cur.get("code") or "").strip():
        raise ValueError("Desain wajib punya KODE sebelum diajukan "
                         "(supaya bisa dirujuk spesifikasi & proofing).")
    if not artworks(cur):
        raise ValueError("Desain wajib punya minimal 1 berkas artwork sebelum diajukan "
                         "(ilustrasi AI tidak dihitung — itu arahan, bukan karya).")
    await db.design_gallery.update_one({"id": gallery_id}, {"$set": {
        "status": "pending_approval", "submitted_by": actor_name,
        "submitted_at": now_iso(), "reject_reason": "", "rejected_by": "",
        "rejected_at": "", "updated_at": now_iso()}})
    return await get_gallery(gallery_id)


async def reject_design(gallery_id: str, actor_name: str, reason: str) -> Dict[str, Any]:
    """pending_approval → draft dengan ALASAN yang tersimpan di dokumennya."""
    cur = await db.design_gallery.find_one({"id": gallery_id}, {"_id": 0})
    if not cur:
        raise ValueError("Entri galeri tidak ditemukan.")
    if cur.get("status") != "pending_approval":
        raise ValueError(f"Hanya desain yang sedang diajukan bisa dikembalikan "
                         f"(status sekarang: '{cur.get('status')}').")
    if not (reason or "").strip():
        raise ValueError("Alasan wajib diisi supaya desainer tahu apa yang harus diperbaiki.")
    hist = list(cur.get("decision_history") or [])
    hist.append({"action": "rejected", "by": actor_name, "at": now_iso(),
                 "reason": reason.strip(), "from_status": "pending_approval",
                 "to_status": "draft"})
    await db.design_gallery.update_one({"id": gallery_id}, {"$set": {
        "status": "draft", "reject_reason": reason.strip(), "rejected_by": actor_name,
        "rejected_at": now_iso(), "decision_history": hist, "updated_at": now_iso()}})
    return await get_gallery(gallery_id)


async def approve_design(gallery_id: str, actor_name: str, note: str = "") -> Dict[str, Any]:
    """Sahkan desain agar boleh dipakai proofing/produk (status `approved`)."""
    cur = await db.design_gallery.find_one({"id": gallery_id}, {"_id": 0})
    if not cur:
        raise ValueError("Entri galeri tidak ditemukan.")
    if cur.get("status") != "pending_approval":
        raise ValueError(
            "Desain ini belum diajukan. Desainer perlu menekan “Ajukan” dulu supaya "
            "draf yang masih dikerjakan tidak bercampur dengan yang siap disahkan."
            if cur.get("status") == "draft" else
            f"Desain berstatus '{cur.get('status')}' tidak bisa disahkan.")
    if not (cur.get("code") or "").strip():
        raise ValueError("Desain wajib punya KODE sebelum disahkan "
                         "(supaya bisa dirujuk spesifikasi & proofing).")
    if not artworks(cur):
        raise ValueError("Desain wajib punya minimal 1 berkas artwork sebelum disahkan "
                         "(ilustrasi AI tidak dihitung).")
    await db.design_gallery.update_one({"id": gallery_id}, {"$set": {
        "status": "approved", "approved_by": actor_name, "approved_at": now_iso(),
        "approve_note": note, "updated_at": now_iso()}})
    return await get_gallery(gallery_id)


async def add_file(gallery_id: str, filename: str, content_type: str, data: bytes,
                   kind: str = "artwork", caption: str = "", uploaded_by: str = "",
                   colorway_id: str = "") -> Dict[str, Any]:
    cur = await db.design_gallery.find_one({"id": gallery_id}, {"_id": 0})
    if not cur:
        raise ValueError("Entri galeri tidak ditemukan.")
    if kind == "source":
        # File desain asli (AI/PSD/EPS/PDF/ZIP/TIF…) — tipe bebas, hanya batas ukuran.
        if len(data) <= 0:
            raise ValueError("File kosong.")
        if len(data) > 50 * 1024 * 1024:
            raise ValueError("Ukuran file desain asli melebihi batas 50 MB.")
        ct = (content_type or "").split(";")[0].strip() or "application/octet-stream"
    else:
        ct = storage.validate_upload(filename, content_type, len(data))  # raise ValueError bila invalid
    ext = storage.ext_of(filename)
    path = storage.build_path("design_gallery", ext)
    await storage.put_object(path, data, ct)
    fmeta = {
        "id": new_id("file"), "filename": filename, "path": path,
        "content_type": ct, "size": len(data), "uploaded_at": now_iso(),
        "kind": kind or "artwork", "caption": (caption or "").strip(),
        "uploaded_by": uploaded_by, "version": int(cur.get("version") or 1),
        "colorway_id": colorway_id or "",
    }
    push: Dict[str, Any] = {"files": fmeta}
    if kind in ("reference", "mockup", "artwork", "colorway", "source"):
        from services import design_studio_service as _studio
        push["timeline"] = _studio.event({"name": uploaded_by}, f"{kind}_uploaded", filename,
                                         version=fmeta["version"], file_id=fmeta["id"],
                                         file_kind=kind, size=len(data))
    await db.design_gallery.update_one(
        {"id": gallery_id},
        {"$push": push, "$set": {"updated_at": now_iso()}})
    if colorway_id:
        await db.design_gallery.update_one({"id": gallery_id, "colorways.id": colorway_id},
                                          {"$push": {"colorways.$.file_ids": fmeta["id"]}})
    return safe_doc(fmeta)


def _find_file(doc: Dict[str, Any], file_id: str) -> Optional[Dict[str, Any]]:
    for f in (doc.get("files") or []):
        if f.get("id") == file_id:
            return f
    return None


# FB-01 — berkas galeri punya dua jenis: `artwork` (karya desainer, default untuk berkas
# lama) dan `ai_illustration` (ilustrasi ARAHAN dari AI — bukan artwork, bukan versi baru).
AI_KIND = "ai_illustration"


def is_artwork(f: Dict[str, Any]) -> bool:
    return (f.get("kind") or "artwork") == "artwork"


def artworks(doc: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [f for f in (doc.get("files") or []) if is_artwork(f)]


async def add_ai_illustration(gallery_id: str, payload: Dict[str, Any],
                              actor_name: str) -> Dict[str, Any]:
    """Hasilkan ilustrasi AI (mockup/modifikasi) dan simpan sebagai berkas `ai_illustration`
    pada desain yang sama — versi & status desain TIDAK berubah."""
    from services import gemini_image_service as gem
    doc = await db.design_gallery.find_one({"id": gallery_id}, {"_id": 0})
    if not doc:
        raise ValueError("Entri galeri tidak ditemukan.")
    prompt = (payload.get("prompt") or "").strip()
    if not prompt:
        raise ValueError("Arahan (prompt) wajib diisi.")
    mode = (payload.get("mode") or "mockup").strip().lower()
    src_id = payload.get("source_file_id")
    src = _find_file(doc, src_id) if src_id else (artworks(doc) or [None])[0]
    if src_id and not src:
        raise ValueError("Berkas acuan tidak ditemukan.")
    if mode == "modify" and not src:
        raise ValueError("Modifikasi butuh minimal 1 artwork acuan — unggah artwork dulu.")
    # G-8 — batas ilustrasi per desain per hari (saat LIVE setiap klik = biaya API).
    cfg = await gem.resolve_config()
    from datetime import datetime
    from zoneinfo import ZoneInfo
    today = datetime.now(ZoneInfo("Asia/Jakarta")).strftime("%Y-%m-%d")
    made_today = sum(1 for f in (doc.get("files") or [])
                     if f.get("kind") == AI_KIND and _wib_date((f.get("ai") or {}).get("at", "")) == today)
    if made_today >= cfg["daily_limit"]:
        raise ValueError(f"Batas {cfg['daily_limit']} ilustrasi AI per desain per hari tercapai "
                         f"({made_today} hari ini). Coba lagi besok atau ubah batas di Pengaturan → Integrasi AI.")
    img_bytes, img_ct = (None, "")
    if src:
        img_bytes, ct0 = await storage.get_object(src["path"])
        img_ct = src.get("content_type") or ct0
    res = await gem.illustrate(img_bytes, img_ct, mode, prompt,
                               context=f"Judul desain: {doc.get('title', '')}.")
    ext = "png" if "png" in res["content_type"] else ("webp" if "webp" in res["content_type"] else "jpg")
    path = storage.build_path("design_gallery_ai", ext)
    await storage.put_object(path, res["data"], res["content_type"])
    fmeta = {
        "id": new_id("file"), "filename": f"ai-{mode}-{len(doc.get('files') or []) + 1}.{ext}",
        "path": path, "content_type": res["content_type"], "size": len(res["data"]),
        "uploaded_at": now_iso(), "kind": AI_KIND,
        "ai": {"mode": mode, "prompt": prompt, "model": res["model"], "demo": res["demo"],
               "source_file_id": src.get("id") if src else "", "by": actor_name, "at": now_iso()},
    }
    await db.design_gallery.update_one(
        {"id": gallery_id},
        {"$push": {"files": fmeta}, "$set": {"updated_at": now_iso()}})
    return safe_doc(fmeta)


def _wib_date(iso: str) -> str:
    from datetime import datetime, timezone
    from zoneinfo import ZoneInfo
    try:
        dt = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(ZoneInfo("Asia/Jakarta")).strftime("%Y-%m-%d")
    except Exception:  # noqa: BLE001
        return str(iso)[:10]


async def delete_illustration_comment(gallery_id: str, file_id: str, comment_id: str,
                                      actor: Dict[str, Any]) -> Dict[str, Any]:
    """G-6 — hapus komentar sendiri (admin boleh menghapus siapa pun)."""
    doc = await db.design_gallery.find_one({"id": gallery_id}, {"_id": 0})
    if not doc:
        raise ValueError("Entri galeri tidak ditemukan.")
    f = _find_file(doc, file_id)
    if not f or is_artwork(f):
        raise ValueError("Ilustrasi AI tidak ditemukan.")
    c = next((x for x in (f.get("comments") or []) if x.get("id") == comment_id), None)
    if not c:
        raise ValueError("Komentar tidak ditemukan.")
    if c.get("user_id") != actor.get("id") and actor.get("role") != "admin":
        raise ValueError("Hanya penulis komentar (atau admin) yang boleh menghapusnya.")
    await db.design_gallery.update_one(
        {"id": gallery_id, "files.id": file_id},
        {"$pull": {"files.$.comments": {"id": comment_id}}, "$set": {"updated_at": now_iso()}})
    return {"id": comment_id, "deleted": True}


async def add_illustration_comment(gallery_id: str, file_id: str, actor: Dict[str, Any],
                                   text: str) -> Dict[str, Any]:
    """Komentar berurutan waktu pada satu ilustrasi AI (desainer ↔ atasan)."""
    doc = await db.design_gallery.find_one({"id": gallery_id}, {"_id": 0})
    if not doc:
        raise ValueError("Entri galeri tidak ditemukan.")
    f = _find_file(doc, file_id)
    if not f or is_artwork(f):
        raise ValueError("Ilustrasi AI tidak ditemukan.")
    comment = {"id": new_id("cmt"), "text": text.strip(), "by": actor.get("name", ""),
               "user_id": actor.get("id", ""), "role": actor.get("role", ""), "at": now_iso()}
    await db.design_gallery.update_one(
        {"id": gallery_id, "files.id": file_id},
        {"$push": {"files.$.comments": comment}, "$set": {"updated_at": now_iso()}})
    # G-6 — desainer diberi tahu saat atasan menulis arahan (dan sebaliknya).
    try:
        from services import notification_service as notif
        target_roles = ("designer",) if actor.get("role") != "designer" else ("manager", "admin")
        await notif.create_addressed(
            roles=target_roles, entity_id=doc.get("entity_id"),
            notif_type="design_ai_comment",
            title=f"Arahan ilustrasi AI: {doc.get('title', '')}",
            body=f"{actor.get('name', '')}: {text.strip()[:160]}",
            severity="info", link="design-gallery", ref=f"{file_id}:{comment['id']}")
    except Exception as exc:  # noqa: BLE001
        print(f"[design_gallery] notifikasi komentar gagal: {exc}")
    return comment



async def file_name_of(gallery_id: str, file_id: str) -> str:
    doc = await db.design_gallery.find_one({"id": gallery_id}, {"_id": 0, "files": 1})
    fmeta = _find_file(doc or {}, file_id) or {}
    return str(fmeta.get("filename") or file_id).replace('"', "")


async def get_file_bytes(gallery_id: str, file_id: str):
    """Return (data, content_type) untuk file dalam galeri. Raise ValueError bila tak ada."""
    doc = await db.design_gallery.find_one({"id": gallery_id}, {"_id": 0})
    if not doc:
        raise ValueError("Entri galeri tidak ditemukan.")
    fmeta = _find_file(doc, file_id)
    if not fmeta:
        raise ValueError("File tidak ditemukan.")
    data, ctype = await storage.get_object(fmeta["path"])  # storage MENGEMBALIKAN TUPLE
    return data, fmeta.get("content_type") or ctype


async def delete_file(gallery_id: str, file_id: str, actor: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    doc = await db.design_gallery.find_one({"id": gallery_id}, {"_id": 0})
    if not doc:
        raise ValueError("Entri galeri tidak ditemukan.")
    fmeta = _find_file(doc, file_id)
    if not fmeta:
        raise ValueError("File tidak ditemukan.")
    from services import design_studio_service as _studio
    ev = _studio.event(actor or {}, "file_deleted", fmeta.get("filename", ""), file_id=file_id,
                       file_kind=fmeta.get("kind") or "artwork", version=fmeta.get("version") or 1)
    await db.design_gallery.update_one(
        {"id": gallery_id},
        {"$pull": {"files": {"id": file_id}}, "$set": {"updated_at": now_iso()}, "$push": {"timeline": ev}})
    return {"id": file_id, "deleted": True}


async def autotag(gallery_id: str) -> Dict[str, Any]:
    """Auto-tag motif via AI (Claude). GRACEFUL: bila AI nonaktif → {enabled:False}.
    Bila sukses → simpan ai_meta + gabung tag unik ke tags[]. Return ai_meta-like."""
    doc = await db.design_gallery.find_one({"id": gallery_id}, {"_id": 0})
    if not doc:
        raise ValueError("Entri galeri tidak ditemukan.")
    files = artworks(doc)
    if not files:
        return {"enabled": await hr_ai_service.is_enabled(), "error": "Belum ada gambar untuk dianalisa."}
    fmeta = files[0]
    data, ctype = await storage.get_object(fmeta["path"])
    result = await hr_ai_service.autotag_image(
        data, fmeta.get("content_type") or ctype, context=f"Judul: {doc.get('title', '')}.")
    # Persist ai_meta selalu (transparansi status), gabung tags bila sukses.
    ai_meta = {
        "enabled": bool(result.get("enabled")),
        "model": result.get("model", ""),
        "tags": result.get("tags", []),
        "summary": result.get("summary", ""),
        "attributes": result.get("attributes", {}),
        "analyzed_at": result.get("analyzed_at", now_iso()),
        "error": result.get("error", ""),
    }
    set_doc: Dict[str, Any] = {"ai_meta": ai_meta, "updated_at": now_iso()}
    if result.get("enabled") and result.get("tags") and not result.get("error"):
        merged = _clean_tags(list(doc.get("tags") or []) + list(result.get("tags") or [])) 
        set_doc["tags"] = merged
    await db.design_gallery.update_one({"id": gallery_id}, {"$set": set_doc})
    updated = safe_doc(await db.design_gallery.find_one({"id": gallery_id}, {"_id": 0}))
    return {**result, "gallery": updated}
