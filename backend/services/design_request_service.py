"""FASE D — **PERMINTAAN DESAIN** (`<ENT>/DSR-#####`) + rapor desainer.

## Lubang nyata yang ditutup
Galeri desain (`design_gallery`) menyimpan **artwork**-nya, dan KPI Desainer menilai
putaran sample. Yang tidak pernah ada: **penugasannya**. Praktiknya MD meminta desain
lewat WhatsApp, jadi tidak ada satu pun angka yang bisa menjawab pertanyaan pemilik:

  * desain ini diminta siapa, untuk pesanan mana, kapan tenggatnya?
  * berapa lama desainer menyelesaikan satu permintaan?
  * berapa yang harus direvisi — dan revisi karena apa?

Karena itu dokumen ini SENGAJA hanya mengurus **pekerjaan**: siapa mengerjakan, kapan
selesai, dan keputusan atasannya. Artwork tetap hidup di `design_gallery`
(satu permintaan boleh punya beberapa versi), angka teknis tetap di `md_specs`.
Melanggar batas itu berarti membuat dokumen ke-4 yang saling menimpa.

## Aturan yang dijaga di sini (bukan di layar)
1. **Alasan revisi/tolak WAJIB.** Revisi tanpa alasan adalah cara paling murah untuk
   membuat desainer mengulang pekerjaan tanpa tahu apa yang salah.
2. **Serah hasil (`deliver`) harus menunjuk artwork yang NYATA** di galeri badan usaha
   yang sama — bukan catatan bebas "sudah dikirim lewat email".
3. **Rapor dihitung dari dokumen**, bukan diketik: `report_by_designer()` membaca
   koleksi ini + nilai bintang di `design_gallery`, sehingga angka rapor tidak bisa
   berbeda dengan isi layar (POC memeriksanya dengan hitung-ulang mandiri).
4. **Papan tidak boleh bocor antar badan usaha** — semua daftar lewat
   `resolve_list_scope` di router, dan setiap tulisan menstempel `entity_id`.
5. **Pagar lini** (`line_scope`): permintaan desain lini printing bukan urusan staf
   woven; kode lini disnapshot di dokumen supaya riwayat tidak bergeser saat master
   produk diubah.
"""
from typing import Any, Dict, List, Optional, Tuple

from db import db
from core_utils import new_id, next_doc_number, now_iso, safe_doc, timeline_entry
from services import line_scope

COLL = "design_requests"

# ─── Status (mesin keadaan yang sengaja pendek) ───────────────────────────────
STATUS_DRAFT = "draft"
STATUS_SUBMITTED = "submitted"
STATUS_ASSIGNED = "assigned"
STATUS_IN_PROGRESS = "in_progress"
STATUS_DELIVERED = "delivered"
STATUS_APPROVED = "approved"
STATUS_REVISION = "revision"
STATUS_CANCELLED = "cancelled"

STATUS_LABEL: Dict[str, str] = {
    STATUS_DRAFT: "Draf",
    STATUS_SUBMITTED: "Menunggu penugasan",
    STATUS_ASSIGNED: "Ditugaskan",
    STATUS_IN_PROGRESS: "Dikerjakan",
    STATUS_DELIVERED: "Menunggu keputusan",
    STATUS_APPROVED: "Disetujui (ACC)",
    STATUS_REVISION: "Minta revisi",
    STATUS_CANCELLED: "Dibatalkan",
}
#: Urutan kolom papan (kanban) — dipakai layar & POC supaya keduanya tidak bercabang.
BOARD_ORDER: Tuple[str, ...] = (
    STATUS_DRAFT, STATUS_SUBMITTED, STATUS_ASSIGNED, STATUS_IN_PROGRESS,
    STATUS_DELIVERED, STATUS_REVISION, STATUS_APPROVED,
)
OPEN_STATUSES: Tuple[str, ...] = (
    STATUS_DRAFT, STATUS_SUBMITTED, STATUS_ASSIGNED, STATUS_IN_PROGRESS,
    STATUS_DELIVERED, STATUS_REVISION,
)
TERMINAL_STATUSES: Tuple[str, ...] = (STATUS_APPROVED, STATUS_CANCELLED)

TARGET_TYPES: Dict[str, str] = {
    "motif": "Motif",
    "pattern": "Pattern / Pola",
    "artwork": "Artwork Printing",
}
SOURCES: Dict[str, str] = {
    "so": "Dari pesanan pelanggan",
    "customer": "Permintaan pelanggan",
    "internal": "Inisiatif internal",
}


class DesignRequestError(ValueError):
    """Kesalahan ber-kalimat siap tampil (Bahasa Indonesia)."""


# ─── Util kecil ──────────────────────────────────────────────────────────────
def _today() -> str:
    return now_iso()[:10]


def _clean_colors(rows: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for r in rows or []:
        row = dict(r or {})
        code = (row.get("code") or "").strip()
        name = (row.get("name") or "").strip()
        if not (code or name):
            continue
        out.append({"color_id": (row.get("color_id") or "").strip(),
                    "code": code, "name": name,
                    "hex": (row.get("hex") or "").strip()})
    return out


async def get_one(req_id: str) -> Optional[Dict[str, Any]]:
    doc = await db[COLL].find_one({"id": req_id}, {"_id": 0})
    return safe_doc(doc) if doc else None


async def _load(req_id: str) -> Dict[str, Any]:
    doc = await db[COLL].find_one({"id": req_id}, {"_id": 0})
    if not doc:
        raise DesignRequestError("Permintaan desain tidak ditemukan.")
    return doc


async def _save(doc: Dict[str, Any], event: str, label: str, actor: Dict[str, Any],
                note: str = "", **fields: Any) -> Dict[str, Any]:
    """Simpan perubahan + satu baris riwayat. Satu pintu supaya setiap perpindahan
    status selalu meninggalkan jejak (tanpa ini, papan bergerak tanpa cerita)."""
    patch = dict(fields)
    patch["updated_at"] = now_iso()
    entry = timeline_entry(event, label, actor.get("name", ""), note)
    await db[COLL].update_one({"id": doc["id"]},
                              {"$set": patch, "$push": {"history": entry}})
    return await get_one(doc["id"])  # type: ignore[return-value]


def _assert_status(doc: Dict[str, Any], allowed: Tuple[str, ...], aksi: str) -> None:
    if doc.get("status") not in allowed:
        boleh = " / ".join(STATUS_LABEL.get(s, s) for s in allowed)
        raise DesignRequestError(
            f"Permintaan berstatus \u201c{STATUS_LABEL.get(doc.get('status'), doc.get('status'))}\u201d "
            f"tidak bisa {aksi}. Status yang bisa: {boleh}.")


# ─── Kandidat desainer (dari akun ber-peran `designer` + divisi R&D) ─────────
async def designers() -> List[Dict[str, Any]]:
    """Daftar orang yang bisa ditugaskan.

    Sumbernya AKUN ber-peran `designer` (supaya orang yang ditugaskan benar-benar
    bisa masuk & mengunggah karyanya sendiri) ditambah nama pada divisi desain di HR
    yang belum punya akun — nama itu tetap boleh ditugaskan supaya data lapangan yang
    sudah ada tidak hilang, tetapi ditandai `has_account=false` di layar.
    """
    out: List[Dict[str, Any]] = []
    seen = set()
    async for u in db.users.find({"role": "designer"},
                                {"_id": 0, "id": 1, "name": 1, "email": 1, "status": 1}):
        if (u.get("status") or "active") != "active":
            continue
        out.append({"id": u["id"], "name": u.get("name", ""), "email": u.get("email", ""),
                    "division": "design", "has_account": True})
        seen.add((u.get("name") or "").strip().lower())
    async for p in db.rnd_person_divisions.find({}, {"_id": 0, "person": 1, "division": 1}):
        nama = (p.get("person") or "").strip()
        if not nama or nama.lower() in seen:
            continue
        seen.add(nama.lower())
        out.append({"id": f"hr:{nama}", "name": nama, "email": "",
                    "division": p.get("division", ""), "has_account": False})
    return sorted(out, key=lambda r: r["name"].lower())


async def _resolve_assignee(assigned_to: str) -> Tuple[str, str, str]:
    """`assigned_to` → (id, nama, divisi). Menolak orang yang tidak dikenal supaya
    penugasan tidak pernah mendarat di nama yang salah ketik."""
    key = (assigned_to or "").strip()
    if not key:
        raise DesignRequestError("Pilih desainer yang ditugaskan.")
    for row in await designers():
        if row["id"] == key or row["name"].lower() == key.lower():
            return row["id"], row["name"], row.get("division", "")
    raise DesignRequestError(
        "Desainer itu tidak dikenal. Pilih dari daftar desainer (akun ber-peran Desainer "
        "atau nama pada divisi desain di HR).")


# ─── Kategori (master yang SAMA dengan Design Studio) ────────────────────────
async def _resolve_categories(cat_code: Any, dcat_code: Any) -> Dict[str, str]:
    """Kategori Pattern + Kategori Design → snapshot kode & nama. Menolak kode asing
    supaya permintaan dan desain di Studio berbicara dengan kosakata yang sama."""
    from services import design_studio_service as studio
    cat = (cat_code or "").strip().upper()
    dcat = (dcat_code or "").strip().upper()
    out = {"category_code": cat, "category_name": "", "design_category_code": dcat,
           "design_category_name": ""}
    if cat:
        row = await studio.category_of("pattern", cat)
        if not row:
            raise DesignRequestError(f"Kategori Pattern '{cat}' tidak ada / nonaktif.")
        out["category_name"] = row.get("name", "")
    if dcat:
        row = await studio.category_of("design", dcat)
        if not row:
            raise DesignRequestError(f"Kategori Design '{dcat}' tidak ada / nonaktif.")
        out["design_category_name"] = row.get("name", "")
    return out


def _design_summary(g: Dict[str, Any]) -> Dict[str, Any]:
    """Ringkasan satu desain Studio untuk ditampilkan di permintaan (cover, status, nilai)."""
    from services import design_studio_service as studio
    e = studio.enrich(dict(g)) or {}
    files = e.get("files") or []
    cover = next((f for f in files if (f.get("kind") or "artwork") == "artwork"
                  and int(f.get("version") or 1) == int(e.get("version") or 1)), None) \
        or next((f for f in files if (f.get("kind") or "artwork") == "artwork"), None)
    return {"id": e.get("id"), "code": e.get("code", ""), "title": e.get("title", ""),
            "status": e.get("status", "draft"), "status_label": e.get("status_label", ""),
            "version": e.get("version", 1), "round_label": e.get("round_label", ""),
            "revision_count": e.get("revision_count", 0), "current_score": e.get("current_score"),
            "final_score": e.get("final_score"), "artwork_count": e.get("artwork_count", 0),
            "cover_file_id": (cover or {}).get("id", ""), "created_by": e.get("created_by", ""),
            "studio": bool(g.get("versions")),
            "reject_reason": e.get("reject_reason", ""), "updated_at": e.get("updated_at", "")}


async def attach_designs(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Tempelkan `designs[]` (ringkasan desain Studio yang tertaut) ke tiap baris — satu kueri."""
    ids = sorted({gid for r in rows for gid in (r.get("gallery_ids") or [])})
    found: Dict[str, Dict[str, Any]] = {}
    if ids:
        async for g in db.design_gallery.find({"id": {"$in": ids}}, {"_id": 0}):
            found[g["id"]] = _design_summary(g)
    for r in rows:
        r["designs"] = [found[g] for g in (r.get("gallery_ids") or []) if g in found]
        r["studio_linked"] = any(d.get("studio") for d in r["designs"])
    return rows


# ─── Membuat ─────────────────────────────────────────────────────────────────
async def create(payload: Dict[str, Any], actor: Dict[str, Any],
                 entity_id: str) -> Dict[str, Any]:
    if not entity_id or entity_id == "all":
        raise DesignRequestError(
            "Pilih satu badan usaha dulu \u2014 permintaan desain selalu milik satu badan usaha.")
    brief = (payload.get("brief") or "").strip()
    if len(brief) < 5:
        raise DesignRequestError(
            "Tulis brief-nya dulu (minimal satu kalimat) \u2014 desainer tidak bisa mulai "
            "dari permintaan kosong.")
    target = (payload.get("target_type") or "motif").strip().lower()
    if target not in TARGET_TYPES:
        raise DesignRequestError(
            f"Jenis target harus salah satu: {', '.join(TARGET_TYPES)}.")
    source = (payload.get("source") or "internal").strip().lower()
    if source not in SOURCES:
        raise DesignRequestError(f"Sumber permintaan harus salah satu: {', '.join(SOURCES)}.")

    cats = await _resolve_categories(payload.get("category_code"), payload.get("design_category_code"))

    so_id = (payload.get("so_id") or "").strip()
    so_number = customer_id = customer_name = ""
    if source == "so" and not so_id:
        raise DesignRequestError(
            "Sumber \u201cDari pesanan pelanggan\u201d wajib menyebut pesanannya.")
    if so_id:
        so = await db.sales_orders.find_one(
            {"id": so_id}, {"_id": 0, "id": 1, "number": 1, "order_number": 1,
                            "customer_id": 1, "customer_name": 1, "entity_id": 1})
        if not so:
            raise DesignRequestError("Pesanan penjualan tidak ditemukan.")
        if (so.get("entity_id") or "") != entity_id:
            raise DesignRequestError(
                "Pesanan itu milik badan usaha lain \u2014 permintaan desain harus dibuat "
                "dari badan usaha pemilik pesanannya.")
        so_number = so.get("number") or so.get("order_number") or ""
        customer_id = so.get("customer_id") or ""
        customer_name = so.get("customer_name") or ""
    if not customer_id and (payload.get("customer_id") or "").strip():
        customer_id = payload["customer_id"].strip()
        cust = await db.customers.find_one({"id": customer_id}, {"_id": 0, "name": 1})
        customer_name = (cust or {}).get("name", "")

    assigned_id = assigned_name = division = ""
    if (payload.get("assigned_to") or "").strip():
        assigned_id, assigned_name, division = await _resolve_assignee(payload["assigned_to"])

    submit_now = bool(payload.get("submit_now"))
    status = STATUS_DRAFT
    if assigned_id:
        status = STATUS_ASSIGNED
    elif submit_now:
        status = STATUS_SUBMITTED

    now = now_iso()
    doc: Dict[str, Any] = {
        "id": new_id("dsr"),
        "number": await next_doc_number(COLL, "number", "DSR-", entity_id=entity_id),
        "entity_id": entity_id,
        # FASE L — snapshot lini: papan lini printing tidak boleh menampilkan pekerjaan woven.
        "line_code": line_scope.norm(payload.get("line_code")),
        "source": source,
        "so_id": so_id, "so_number": so_number,
        "customer_id": customer_id, "customer_name": customer_name,
        "requested_by": actor.get("name", ""), "requested_by_id": actor.get("id", ""),
        "requested_at": now,
        "assigned_to": assigned_id, "assigned_name": assigned_name, "division": division,
        "assigned_at": now if assigned_id else "",
        "due_date": (payload.get("due_date") or "").strip(),
        "brief": brief, "target_type": target,
        **cats,
        "color_targets": _clean_colors(payload.get("color_targets")),
        "status": status,
        "gallery_ids": [], "references": [], "delivered_at": "",
        "decided_by": "", "decided_at": "",
        "reject_reason": "", "revision_count": 0,
        "cancelled_reason": "",
        "history": [timeline_entry("created", "Permintaan desain dibuat",
                                   actor.get("name", ""), TARGET_TYPES[target])],
        "created_at": now, "updated_at": now,
    }
    if status == STATUS_SUBMITTED:
        doc["history"].append(timeline_entry("submitted", "Diajukan", actor.get("name", "")))
    if status == STATUS_ASSIGNED:
        doc["history"].append(timeline_entry(
            "assigned", f"Ditugaskan ke {assigned_name}", actor.get("name", ""),
            f"tenggat {doc['due_date']}" if doc["due_date"] else ""))
    await db[COLL].insert_one(dict(doc))

    # FASE G-4 — jejak dua arah ke pesanan sumbernya (kalau ada).
    if so_id:
        from services import doc_refs_service as _refs
        await _refs.safe_link(("design_request", doc["id"]), ("sales_order", so_id),
                              "parent", note="permintaan desain untuk pesanan ini")
    return safe_doc(doc)


async def update(req_id: str, payload: Dict[str, Any], actor: Dict[str, Any]) -> Dict[str, Any]:
    doc = await _load(req_id)
    _assert_status(doc, (STATUS_DRAFT, STATUS_SUBMITTED, STATUS_ASSIGNED,
                         STATUS_IN_PROGRESS, STATUS_REVISION), "diubah")
    fields: Dict[str, Any] = {}
    if payload.get("brief") is not None:
        brief = (payload["brief"] or "").strip()
        if len(brief) < 5:
            raise DesignRequestError("Brief tidak boleh dikosongkan.")
        fields["brief"] = brief
    if payload.get("due_date") is not None:
        fields["due_date"] = (payload["due_date"] or "").strip()
    if payload.get("target_type") is not None:
        target = (payload["target_type"] or "").strip().lower()
        if target not in TARGET_TYPES:
            raise DesignRequestError(f"Jenis target harus salah satu: {', '.join(TARGET_TYPES)}.")
        fields["target_type"] = target
    if payload.get("category_code") is not None or payload.get("design_category_code") is not None:
        fields.update(await _resolve_categories(
            payload.get("category_code") if payload.get("category_code") is not None else doc.get("category_code"),
            payload.get("design_category_code") if payload.get("design_category_code") is not None
            else doc.get("design_category_code")))
    if payload.get("line_code") is not None:
        fields["line_code"] = line_scope.norm(payload["line_code"])
    if payload.get("color_targets") is not None:
        fields["color_targets"] = _clean_colors(payload["color_targets"])
    if not fields:
        return safe_doc(doc)
    return await _save(doc, "updated", "Permintaan diperbarui", actor,
                       note=" · ".join(sorted(fields)), **fields)


# ─── Perpindahan status ──────────────────────────────────────────────────────
async def submit(req_id: str, actor: Dict[str, Any]) -> Dict[str, Any]:
    doc = await _load(req_id)
    _assert_status(doc, (STATUS_DRAFT,), "diajukan")
    return await _save(doc, "submitted", "Diajukan", actor, status=STATUS_SUBMITTED)


async def assign(req_id: str, actor: Dict[str, Any], assigned_to: str,
                 due_date: str = "") -> Dict[str, Any]:
    doc = await _load(req_id)
    _assert_status(doc, (STATUS_DRAFT, STATUS_SUBMITTED, STATUS_ASSIGNED,
                         STATUS_IN_PROGRESS, STATUS_REVISION), "ditugaskan")
    aid, aname, division = await _resolve_assignee(assigned_to)
    due = (due_date or doc.get("due_date") or "").strip()
    status = doc.get("status")
    if status in (STATUS_DRAFT, STATUS_SUBMITTED):
        status = STATUS_ASSIGNED
    return await _save(doc, "assigned", f"Ditugaskan ke {aname}", actor,
                       note=f"tenggat {due}" if due else "tanpa tenggat",
                       assigned_to=aid, assigned_name=aname, division=division,
                       assigned_at=now_iso(), due_date=due, status=status)


async def start(req_id: str, actor: Dict[str, Any]) -> Dict[str, Any]:
    doc = await _load(req_id)
    _assert_status(doc, (STATUS_ASSIGNED, STATUS_REVISION), "mulai dikerjakan")
    return await _save(doc, "in_progress", "Mulai dikerjakan", actor,
                       status=STATUS_IN_PROGRESS, started_at=now_iso())


async def deliver(req_id: str, actor: Dict[str, Any], gallery_id: str,
                  note: str = "") -> Dict[str, Any]:
    """Serah hasil: menunjuk **artwork nyata** di galeri desain (bukan catatan bebas)."""
    doc = await _load(req_id)
    _assert_status(doc, (STATUS_ASSIGNED, STATUS_IN_PROGRESS, STATUS_REVISION,
                         STATUS_DELIVERED), "diserahkan")
    gid = (gallery_id or "").strip()
    art = await db.design_gallery.find_one({"id": gid}, {"_id": 0}) if gid else None
    if not art:
        raise DesignRequestError(
            "Artwork tidak ditemukan di Galeri Desain. Unggah dulu karyanya di Galeri, "
            "lalu pilih entrinya di sini.")
    if (art.get("entity_id") or "") != (doc.get("entity_id") or ""):
        raise DesignRequestError("Artwork itu milik badan usaha lain.")
    ids = list(doc.get("gallery_ids") or [])
    if gid not in ids:
        ids.append(gid)
    # Tautan balik di galeri: dari artwork bisa dilacak permintaan yang melahirkannya.
    await db.design_gallery.update_one(
        {"id": gid}, {"$set": {"request_id": doc["id"], "request_number": doc["number"],
                               "updated_at": now_iso()}})
    label = art.get("code") or art.get("title") or gid
    return await _save(doc, "delivered", f"Hasil diserahkan ({label})", actor,
                       note=note, status=STATUS_DELIVERED, delivered_at=now_iso(),
                       gallery_ids=ids)


async def approve(req_id: str, actor: Dict[str, Any], note: str = "") -> Dict[str, Any]:
    doc = await _load(req_id)
    _assert_status(doc, (STATUS_DELIVERED,), "disetujui")
    if await _has_studio_design(doc):
        raise DesignRequestError(
            "Permintaan ini tertaut ke desain di Design Studio \u2014 beri nilai dan putuskan ACC "
            "di halaman desainnya; status permintaan mengikuti otomatis.")
    return await _save(doc, "approved", "Disetujui (ACC)", actor, note=note,
                       status=STATUS_APPROVED, decided_by=actor.get("name", ""),
                       decided_at=now_iso(), reject_reason="")


async def reject(req_id: str, actor: Dict[str, Any], reason: str) -> Dict[str, Any]:
    """Minta revisi. **Alasan wajib** — revisi tanpa alasan membuat desainer menebak."""
    doc = await _load(req_id)
    _assert_status(doc, (STATUS_DELIVERED,), "diminta revisi")
    if await _has_studio_design(doc):
        raise DesignRequestError(
            "Permintaan ini tertaut ke desain di Design Studio \u2014 minta revisi di halaman "
            "desainnya (ronde baru dibuka otomatis); status permintaan mengikuti.")
    why = (reason or "").strip()
    if len(why) < 3:
        raise DesignRequestError(
            "Tulis alasannya \u2014 desainer perlu tahu apa yang harus diubah.")
    return await _save(doc, "revision", "Minta revisi", actor, note=why,
                       status=STATUS_REVISION, reject_reason=why,
                       decided_by=actor.get("name", ""), decided_at=now_iso(),
                       revision_count=int(doc.get("revision_count") or 0) + 1)


# ─── Sinkron dengan Design Studio (`design_gallery`) ─────────────────────────
#: Status desain Studio yang masih boleh ditautkan ke permintaan (belum ACC/aktif/arsip).
LINKABLE_DESIGN_STATUSES: Tuple[str, ...] = ("draft", "revision", "pending_approval", "in_review")
#: Aksi siklus hidup Studio → status permintaan (satu sumber kebenaran: halaman desain).
STUDIO_ACTION_MAP: Dict[str, str] = {
    "submit": STATUS_DELIVERED,
    "request_revision": STATUS_REVISION,
    "approve": STATUS_APPROVED,
}


async def _has_studio_design(doc: Dict[str, Any]) -> bool:
    """Ada desain tertaut yang menjalani siklus hidup Studio (punya `versions`)?"""
    ids = list(doc.get("gallery_ids") or [])
    if not ids:
        return False
    return await db.design_gallery.count_documents(
        {"id": {"$in": ids}, "versions.0": {"$exists": True}}) > 0


async def create_design_from_request(req_id: str, actor: Dict[str, Any], entity_id: str,
                                     title: str = "") -> Dict[str, Any]:
    """Desainer mulai bekerja: desain Studio dibuat dari brief (kategori & lini ikut),
    tertaut dua arah, dan permintaan bergerak ke **Dikerjakan**."""
    from services import design_gallery_service as gallery
    doc = await _load(req_id)
    _assert_status(doc, (STATUS_ASSIGNED, STATUS_IN_PROGRESS, STATUS_REVISION),
                   "dijadikan desain baru")
    judul = (title or "").strip() or (doc.get("brief") or "")[:80].strip()
    if not judul:
        raise DesignRequestError("Judul desain wajib diisi.")
    if not doc.get("category_code") or not doc.get("design_category_code"):
        raise DesignRequestError(
            "Permintaan ini belum punya Kategori Pattern & Kategori Design \u2014 lengkapi dulu "
            "(tombol Ubah) supaya kode desain bisa dibentuk otomatis.")
    try:
        design = await gallery.create_gallery(
            {"title": judul, "story": doc.get("brief", ""), "tags": [],
             "category_code": doc.get("category_code"), "design_category_code": doc.get("design_category_code"),
             "line_code": doc.get("line_code", "")},
            actor.get("name", ""), entity_id or doc.get("entity_id", ""), actor=actor)
    except ValueError as exc:
        raise DesignRequestError(str(exc)) from exc
    await db.design_gallery.update_one(
        {"id": design["id"]},
        {"$set": {"request_id": doc["id"], "request_number": doc["number"], "updated_at": now_iso()}})
    ids = list(doc.get("gallery_ids") or []) + [design["id"]]
    fields: Dict[str, Any] = {"gallery_ids": ids, "status": STATUS_IN_PROGRESS}
    if not doc.get("started_at"):
        fields["started_at"] = now_iso()
    copied = await _propagate_references(doc, actor, [design["id"]])
    fresh = await _save(doc, "design_created", f"Desain {design.get('code')} dibuat dari permintaan",
                        actor, note=judul + (f" · {copied} referensi ikut" if copied else ""), **fields)
    fresh["design"] = design
    return fresh


async def link_design(req_id: str, actor: Dict[str, Any], gallery_id: str) -> Dict[str, Any]:
    """Tautkan desain Studio yang sudah ada. Status permintaan mengikuti status desain."""
    doc = await _load(req_id)
    _assert_status(doc, (STATUS_ASSIGNED, STATUS_IN_PROGRESS, STATUS_REVISION, STATUS_DELIVERED),
                   "ditautkan ke desain")
    gid = (gallery_id or "").strip()
    art = await db.design_gallery.find_one({"id": gid}, {"_id": 0}) if gid else None
    if not art:
        raise DesignRequestError("Desain tidak ditemukan di Design Studio.")
    if (art.get("entity_id") or "") != (doc.get("entity_id") or ""):
        raise DesignRequestError("Desain itu milik badan usaha lain.")
    if art.get("request_id") and art.get("request_id") != doc["id"]:
        raise DesignRequestError(
            f"Desain {art.get('code') or gid} sudah tertaut ke permintaan {art.get('request_number') or 'lain'}.")
    if (art.get("status") or "draft") not in LINKABLE_DESIGN_STATUSES:
        raise DesignRequestError(
            "Hanya desain yang masih berjalan (draf / diajukan / dalam review / revisi) yang bisa ditautkan.")
    await db.design_gallery.update_one(
        {"id": gid}, {"$set": {"request_id": doc["id"], "request_number": doc["number"],
                               "updated_at": now_iso()}})
    ids = list(doc.get("gallery_ids") or [])
    if gid not in ids:
        ids.append(gid)
    status = STATUS_DELIVERED if art.get("status") in ("pending_approval", "in_review") else STATUS_IN_PROGRESS
    fields: Dict[str, Any] = {"gallery_ids": ids, "status": status}
    if status == STATUS_DELIVERED:
        fields["delivered_at"] = now_iso()
    if not doc.get("started_at"):
        fields["started_at"] = now_iso()
    copied = await _propagate_references(doc, actor, [gid])
    return await _save(doc, "design_linked", f"Desain {art.get('code') or art.get('title')} ditautkan",
                       actor, note=f"{copied} referensi ikut" if copied else "", **fields)


async def sync_from_design(design: Dict[str, Any], action: str, actor: Dict[str, Any],
                           note: str = "", score: Any = None) -> None:
    """Dipanggil `design_studio_service.transition` — permintaan mengikuti desain tertaut.
    Tidak melempar galat ke Studio: sinkron gagal tidak boleh membatalkan aksi desain."""
    req_id = (design.get("request_id") or "").strip()
    if not req_id:
        return
    doc = await db[COLL].find_one({"id": req_id}, {"_id": 0})
    if not doc or doc.get("status") == STATUS_CANCELLED:
        return
    label = design.get("code") or design.get("title") or ""
    from services import design_studio_service as studio
    ronde = studio.round_label(design.get("version", 1))
    if action == "submit":
        if doc.get("status") == STATUS_APPROVED:
            return
        await _save(doc, "delivered", f"Hasil diserahkan ({label} · {ronde})", actor, note=note,
                    status=STATUS_DELIVERED, delivered_at=now_iso())
    elif action == "request_revision":
        if doc.get("status") == STATUS_APPROVED:
            return
        skor = f" · nilai {score}" if score is not None else ""
        await _save(doc, "revision", f"Minta revisi ({label}){skor}", actor, note=note,
                    status=STATUS_REVISION, reject_reason=(note or "").strip(),
                    decided_by=actor.get("name", ""), decided_at=now_iso(),
                    revision_count=int(doc.get("revision_count") or 0) + 1)
    elif action == "approve":
        skor = f" · nilai {score}" if score is not None else ""
        await _save(doc, "approved", f"Disetujui (ACC) \u2014 {label}{skor}", actor, note=note,
                    status=STATUS_APPROVED, decided_by=actor.get("name", ""),
                    decided_at=now_iso(), reject_reason="")
    elif action in ("archive", "reopen", "start_review", "submit_final", "activate", "return_final"):
        await _save(doc, f"design_{action}", f"Desain {label}: {studio.STATUS_LABEL.get(design.get('status'), '')}",
                    actor, note=note)


# ─── Gambar referensi brief (ikut otomatis ke tab Referensi desain) ──────────
REFERENCE_EDITABLE: Tuple[str, ...] = (STATUS_DRAFT, STATUS_SUBMITTED, STATUS_ASSIGNED,
                                       STATUS_IN_PROGRESS, STATUS_REVISION, STATUS_DELIVERED)


async def add_reference(req_id: str, actor: Dict[str, Any], filename: str, content_type: str,
                        data: bytes, caption: str = "") -> Dict[str, Any]:
    """Simpan gambar referensi pada permintaan; bila sudah ada desain tertaut yang masih
    berjalan, referensi langsung disalin ke tab Referensi desain itu."""
    from services import storage_service as storage
    doc = await _load(req_id)
    _assert_status(doc, REFERENCE_EDITABLE, "ditambah referensi")
    ct = storage.validate_upload(filename, content_type, len(data))
    if not ct.startswith("image/"):
        raise DesignRequestError("Referensi brief harus berupa gambar (PNG/JPG/WEBP).")
    path = storage.build_path("design_requests", storage.ext_of(filename))
    await storage.put_object(path, data, ct)
    fmeta = {"id": new_id("file"), "filename": filename, "path": path, "content_type": ct,
             "size": len(data), "uploaded_at": now_iso(), "uploaded_by": actor.get("name", ""),
             "caption": (caption or "").strip()}
    await db[COLL].update_one({"id": doc["id"]}, {"$push": {"references": fmeta},
                                                  "$set": {"updated_at": now_iso()}})
    await _propagate_references(await _load(req_id), actor)
    return safe_doc(fmeta)


async def delete_reference(req_id: str, actor: Dict[str, Any], file_id: str) -> Dict[str, Any]:
    doc = await _load(req_id)
    _assert_status(doc, REFERENCE_EDITABLE, "dihapus referensinya")
    if not any(f.get("id") == file_id for f in doc.get("references") or []):
        raise DesignRequestError("Referensi tidak ditemukan.")
    await db[COLL].update_one({"id": doc["id"]}, {"$pull": {"references": {"id": file_id}},
                                                  "$set": {"updated_at": now_iso()}})
    return {"id": file_id, "deleted": True}


async def get_reference_bytes(req_id: str, file_id: str):
    from services import storage_service as storage
    doc = await _load(req_id)
    fmeta = next((f for f in doc.get("references") or [] if f.get("id") == file_id), None)
    if not fmeta:
        raise DesignRequestError("Referensi tidak ditemukan.")
    data, ctype = await storage.get_object(fmeta["path"])
    return data, fmeta.get("content_type") or ctype


async def _propagate_references(doc: Dict[str, Any], actor: Dict[str, Any],
                                gallery_ids: Optional[List[str]] = None) -> int:
    """Salin referensi permintaan ke desain tertaut sebagai berkas `reference` (idempoten:
    penanda `source_reference_id` mencegah salinan ganda)."""
    from services import storage_service as storage
    refs = list(doc.get("references") or [])
    ids = gallery_ids if gallery_ids is not None else list(doc.get("gallery_ids") or [])
    if not refs or not ids:
        return 0
    copied = 0
    async for g in db.design_gallery.find({"id": {"$in": ids}}, {"_id": 0, "id": 1, "files": 1, "status": 1}):
        if g.get("status") in ("archived", "retired"):
            continue
        have = {f.get("source_reference_id") for f in g.get("files") or []}
        for r in refs:
            if r["id"] in have:
                continue
            try:
                data, ct = await storage.get_object(r["path"])
            except Exception:  # noqa: BLE001 — berkas fisik hilang: lewati, jangan gagalkan aksi
                continue
            path = storage.build_path("design_gallery", storage.ext_of(r["filename"]))
            await storage.put_object(path, data, r.get("content_type") or ct)
            fmeta = {"id": new_id("file"), "filename": r["filename"], "path": path,
                     "content_type": r.get("content_type") or ct, "size": len(data), "uploaded_at": now_iso(),
                     "kind": "reference", "caption": r.get("caption") or f"Referensi brief {doc.get('number', '')}",
                     "uploaded_by": r.get("uploaded_by") or actor.get("name", ""), "version": 1,
                     "colorway_id": "", "source_reference_id": r["id"]}
            await db.design_gallery.update_one({"id": g["id"]}, {"$push": {"files": fmeta},
                                                                 "$set": {"updated_at": now_iso()}})
            copied += 1
    return copied


async def cancel(req_id: str, actor: Dict[str, Any], reason: str) -> Dict[str, Any]:
    doc = await _load(req_id)
    if doc.get("status") in TERMINAL_STATUSES:
        raise DesignRequestError("Permintaan ini sudah selesai/dibatalkan.")
    why = (reason or "").strip()
    if len(why) < 3:
        raise DesignRequestError("Sebutkan alasan pembatalan.")
    return await _save(doc, "cancelled", "Dibatalkan", actor, note=why,
                       status=STATUS_CANCELLED, cancelled_reason=why)


# ─── Daftar & ringkasan ──────────────────────────────────────────────────────
def overdue(doc: Dict[str, Any], today: str = "") -> bool:
    """Lewat tenggat = ada tenggat, sudah lewat, dan pekerjaannya belum selesai."""
    due = (doc.get("due_date") or "").strip()
    if not due or doc.get("status") in TERMINAL_STATUSES:
        return False
    return due < (today or _today())


def shape(doc: Dict[str, Any], today: str = "") -> Dict[str, Any]:
    """Bentuk baris untuk layar: field turunan dihitung SERVER (INV-UI-04 — layar
    tidak boleh menghitung sendiri lalu berbeda dengan papan)."""
    out = safe_doc(dict(doc))
    out["status_label"] = STATUS_LABEL.get(doc.get("status"), doc.get("status", ""))
    if doc.get("category_code") or doc.get("design_category_code"):
        out["target_label"] = " · ".join(x for x in (
            doc.get("category_name") or doc.get("category_code"),
            doc.get("design_category_name") or doc.get("design_category_code")) if x)
    else:
        out["target_label"] = TARGET_TYPES.get(doc.get("target_type"), doc.get("target_type", ""))
    out["source_label"] = SOURCES.get(doc.get("source"), doc.get("source", ""))
    out["is_overdue"] = overdue(doc, today)
    out["versions"] = len(doc.get("gallery_ids") or [])
    return out


async def summary(query: Dict[str, Any]) -> Dict[str, Any]:
    """Kartu ringkasan dihitung dari SELURUH hasil filter (bukan dari isi halaman).

    Pelajaran FASE P5: begitu daftar dipaginasi, lencana yang dihitung dari halaman
    aktif diam-diam menyusut (\u201ckartu bilang 12, daftar berisi 3\u201d).
    """
    out: Dict[str, int] = {s: 0 for s in STATUS_LABEL}
    total = 0
    late = 0
    today = _today()
    async for d in db[COLL].find(query, {"_id": 0, "status": 1, "due_date": 1}):
        total += 1
        out[d.get("status", "")] = out.get(d.get("status", ""), 0) + 1
        if overdue(d, today):
            late += 1
    out["total"] = total
    out["overdue"] = late
    out["open"] = sum(out.get(s, 0) for s in OPEN_STATUSES)
    return out


# ─── Rapor desainer (dihitung dari dokumen, bukan diketik) ───────────────────
def _days_between(a: str, b: str) -> Optional[float]:
    from datetime import datetime
    try:
        d1 = datetime.fromisoformat((a or "").replace("Z", "+00:00"))
        d2 = datetime.fromisoformat((b or "").replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return round(abs((d2 - d1).total_seconds()) / 86400.0, 2)


async def report_by_designer(query: Dict[str, Any]) -> Dict[str, Any]:
    """Rapor per desainer: diminta · dikerjakan · diserahkan · ACC · revisi ·
    rata-rata hari kerja · rata-rata bintang · lewat tenggat.

    Bintang dibaca dari `design_gallery.ratings` pada artwork yang diserahkan —
    satu sumber dengan layar Galeri, jadi angkanya tidak bisa berbeda.
    """
    today = _today()
    rows: Dict[str, Dict[str, Any]] = {}
    gallery_needed: List[str] = []
    docs: List[Dict[str, Any]] = []
    async for d in db[COLL].find(query, {"_id": 0}):
        docs.append(d)
        gallery_needed.extend(d.get("gallery_ids") or [])

    stars: Dict[str, List[float]] = {}
    if gallery_needed:
        async for g in db.design_gallery.find({"id": {"$in": list(set(gallery_needed))}},
                                              {"_id": 0, "id": 1, "ratings": 1}):
            vals = [float(r.get("stars") or 0) for r in (g.get("ratings") or [])
                    if float(r.get("stars") or 0) > 0]
            if vals:
                stars[g["id"]] = vals

    for d in docs:
        key = d.get("assigned_to") or "__unassigned__"
        row = rows.setdefault(key, {
            "designer_id": d.get("assigned_to", ""),
            "designer": d.get("assigned_name") or "Belum ditugaskan",
            "division": d.get("division", ""),
            "assigned": 0, "in_progress": 0, "delivered": 0, "approved": 0,
            "revision": 0, "overdue": 0, "_days": [], "_stars": [],
        })
        row["assigned"] += 1
        if d.get("status") == STATUS_IN_PROGRESS:
            row["in_progress"] += 1
        if d.get("delivered_at"):
            row["delivered"] += 1
            hari = _days_between(d.get("assigned_at") or d.get("requested_at", ""),
                                 d.get("delivered_at", ""))
            if hari is not None:
                row["_days"].append(hari)
        if d.get("status") == STATUS_APPROVED:
            row["approved"] += 1
        row["revision"] += int(d.get("revision_count") or 0)
        if overdue(d, today):
            row["overdue"] += 1
        for gid in d.get("gallery_ids") or []:
            row["_stars"].extend(stars.get(gid, []))

    out: List[Dict[str, Any]] = []
    for row in rows.values():
        days = row.pop("_days")
        st = row.pop("_stars")
        row["avg_days"] = round(sum(days) / len(days), 2) if days else None
        row["avg_stars"] = round(sum(st) / len(st), 2) if st else None
        row["acc_rate_pct"] = (round(row["approved"] * 100.0 / row["assigned"], 1)
                               if row["assigned"] else 0.0)
        out.append(row)
    out.sort(key=lambda r: (-r["assigned"], r["designer"].lower()))
    return {"items": out,
            "totals": {
                "requests": len(docs),
                "delivered": sum(r["delivered"] for r in out),
                "approved": sum(r["approved"] for r in out),
                "revision": sum(r["revision"] for r in out),
                "overdue": sum(r["overdue"] for r in out),
            }}


async def report_mine(query: Dict[str, Any], *, user_id: str,
                      display_name: str = "") -> Dict[str, Any]:
    """Rapor **milik satu desainer** — angka dirinya + pembanding tim yang AGREGAT.

    KENAPA ADA (FASE D, keputusan pemilik): rapor lintas desainer
    (`report_by_designer`) menilai ORANG, jadi wewenangnya atasan — desainer yang
    membukanya hanya mendapat 403 yang ditelan `.catch`, yaitu **panel mati**. Tetapi
    "tidak boleh melihat rekan" tidak sama dengan "tidak boleh melihat dirinya".
    Fungsi ini memberi desainer angkanya sendiri **tanpa** membocorkan satu nama rekan
    pun — pola privasi yang sama dengan `rnd_kpi_service.my_kpi` (PS-18).

    `query` WAJIB berupa lingkup badan usaha/lini SAJA — **tanpa** `assigned_to`.
    Kalau ia sudah disaring ke satu orang, `total_designers` selalu 1 dan `rank`
    selalu 1: angka yang terlihat masuk akal tetapi tidak berarti apa-apa. Penyaringan
    ke "punya saya" dilakukan DI SINI (memilih satu baris), dan hanya baris itu yang
    dikirim keluar.
    """
    rep = await report_by_designer(query)
    items = rep["items"]
    me = next((r for r in items if r.get("designer_id") == user_id), None)
    # Peringkat dihitung hanya di antara desainer NYATA (baris "Belum ditugaskan"
    # bukan orang, jadi ia tidak boleh menggeser posisi siapa pun).
    peers = [r for r in items if r.get("designer_id")]
    rank = (peers.index(me) + 1) if me in peers else None

    def _avg(key: str) -> Optional[float]:
        return round(sum(r[key] for r in peers) / len(peers), 2) if peers else None

    return {
        "designer": (me or {}).get("designer") or display_name,
        "me": me,                       # None = belum ada permintaan yang ditugaskan
        "rank": rank,
        "total_designers": len(peers),
        # HANYA angka gabungan — sengaja TANPA daftar/nama rekan (PS-18).
        "team": {
            "designers": len(peers),
            "avg_assigned": _avg("assigned"),
            "avg_delivered": _avg("delivered"),
            "avg_approved": _avg("approved"),
        },
        "totals": {
            "requests": (me or {}).get("assigned", 0),
            "delivered": (me or {}).get("delivered", 0),
            "approved": (me or {}).get("approved", 0),
            "revision": (me or {}).get("revision", 0),
            "overdue": (me or {}).get("overdue", 0),
        },
    }
