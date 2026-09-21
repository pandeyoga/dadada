"""HRD H5 router — Design Gallery (motif kain) + upload gambar + AI auto-tag.

Koleksi kanonik (entity-scoped): design_gallery (dsgn_). Keputusan owner 3a.
RBAC: read list/detail/file = hr.view; create/update/delete/upload/autotag = hr.manage_attendance.
Auto-tag AI (Claude) GRACEFUL: bila key kosong → 200 {enabled:false} (BUKAN error).

Path aksi pakai segmen literal (/files, /autotag) agar verify_api_contract 0 ERROR.
"""
import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Request, Query, UploadFile, File
from fastapi.responses import Response

from dependencies import require_permission, audit
from entity_scope import entity_ctx, resolve_list_scope, assert_entity_access
from schemas_design_gallery import (DesignAiIllustrateIn, DesignApproveIn, DesignRatingIn,
                                    DesignRejectIn, DesignVersionIn, GalleryInput, GalleryUpdate,
                                    IllustrationCommentIn)
from services import design_gallery_service as gallery
logger = logging.getLogger(__name__)


router = APIRouter(prefix="/api")


async def _perm_view(request: Request) -> Dict[str, Any]:
    """RBAC DUA DIVISI (FASE F): HRD (`hr.view`) **atau** R&D (`rnd.view`).

    Master desain dipakai dua divisi sekaligus — HRD (galeri motif/cerita) dan R&D
    (pattern untuk proofing). Memaksa satu izin akan mematikan salah satu alur,
    karena itu keduanya diterima. Tidak ada wewenang lama yang dicabut.
    """
    try:
        return await require_permission(request, "rnd", "view")
    except HTTPException:
        return await require_permission(request, "hr", "view")


async def _perm_manage(request: Request) -> Dict[str, Any]:
    """Tulis master desain: `rnd.manage` **atau** `hr.manage_attendance` (admin/manager)
    **atau** `design_request.deliver` (FASE D — peran `designer`).

    Kenapa izin ketiga ditambahkan: sejak FASE D desainer punya AKUN dan alur
    resminya adalah *ia sendiri* yang mengunggah karyanya lalu menyerahkannya
    (`POST /design-requests/{id}/deliver`). Tanpa pintu ini, satu-satunya cara
    mengunggah artwork adalah lewat admin — dan rapor desainer akan mencatat
    pekerjaan orang lain. Wewenang lama TIDAK berkurang.
    """
    try:
        return await require_permission(request, "rnd", "manage")
    except HTTPException as exc:
        logger.warning("[_perm_manage] efek samping gagal diabaikan: %s", exc)  # KN-C10
    try:
        return await require_permission(request, "hr", "manage_attendance")
    except HTTPException:
        return await require_permission(request, "design_request", "deliver")


async def _guard(gallery_id: str, ctx) -> Dict[str, Any]:
    doc = await gallery.get_gallery(gallery_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Entri galeri tidak ditemukan.")
    assert_entity_access(doc, "design_gallery", ctx)
    return doc


@router.get("/design-gallery")
async def list_gallery(request: Request, entity_id: Optional[str] = Query(None),
                       tag: Optional[str] = Query(None),
                       q: Optional[str] = Query(None),
                       status: str = Query(""), design_type: str = Query(""),
                       category_code: str = Query(""), created_by: str = Query(""),
                       product_id: str = Query(""), color_id: str = Query(""),
                       on_hold: str = Query("", description="yes|no — saring desain HOLD"),
                       line: str = Query("", description="FASE L — penyaring lini")) -> List[Dict[str, Any]]:
    viewer = await _perm_view(request)
    ctx = await entity_ctx(request)
    scope = resolve_list_scope("design_gallery", {}, ctx, entity_id)
    # FASE L — galeri desain ikut berpagar lini (artwork printing bukan urusan staf woven).
    from services import line_scope as _lines
    scope = _lines.narrow(scope, viewer, line)
    return await gallery.list_gallery(scope, tag, q, viewer_id=viewer.get("id"),
                                      filters={"status": status, "design_type": design_type,
                                               "category_code": category_code, "created_by": created_by,
                                               "product_id": product_id, "color_id": color_id,
                                               "on_hold": on_hold})


@router.post("/design-gallery")
async def create_gallery(payload: GalleryInput, request: Request) -> Dict[str, Any]:
    actor = await _perm_manage(request)
    ctx = await entity_ctx(request)
    try:
        doc = await gallery.create_gallery(payload.model_dump(), actor["name"], ctx.active_entity_id,
                                           actor=actor)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await audit(actor["name"], "design_gallery_create", "design_gallery", doc["id"],
                {"title": doc["title"]})
    return doc


@router.get("/design-gallery/{gallery_id}")
async def get_gallery(gallery_id: str, request: Request) -> Dict[str, Any]:
    viewer = await _perm_view(request)
    ctx = await entity_ctx(request)
    await _guard(gallery_id, ctx)
    return await gallery.get_gallery(gallery_id, viewer_id=viewer.get("id"))


@router.put("/design-gallery/{gallery_id}")
async def update_gallery(gallery_id: str, payload: GalleryUpdate, request: Request) -> Dict[str, Any]:
    actor = await _perm_manage(request)
    ctx = await entity_ctx(request)
    await _guard(gallery_id, ctx)
    patch = payload.model_dump(exclude_unset=True)
    try:
        doc = await gallery.update_gallery(gallery_id, patch, actor=actor)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await audit(actor["name"], "design_gallery_update", "design_gallery", gallery_id, patch)
    return doc


@router.delete("/design-gallery/{gallery_id}")
async def delete_gallery(gallery_id: str, request: Request) -> Dict[str, Any]:
    actor = await _perm_manage(request)
    ctx = await entity_ctx(request)
    await _guard(gallery_id, ctx)
    try:
        res = await gallery.delete_gallery(gallery_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await audit(actor["name"], "design_gallery_delete", "design_gallery", gallery_id, {})
    return res


# ─── Files (upload / serve / delete) ──────────────────────────────────
@router.post("/design-gallery/{gallery_id}/files")
async def upload_gallery_file(gallery_id: str, request: Request,
                              file: UploadFile = File(...)) -> Dict[str, Any]:
    actor = await _perm_manage(request)
    ctx = await entity_ctx(request)
    await _guard(gallery_id, ctx)
    data = await file.read()
    try:
        fmeta = await gallery.add_file(gallery_id, file.filename or "motif",
                                       file.content_type or "", data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await audit(actor["name"], "design_gallery_upload", "design_gallery", gallery_id,
                {"file": fmeta.get("filename")})
    return fmeta


@router.get("/design-gallery/{gallery_id}/files/{file_id}")
async def get_gallery_file(gallery_id: str, file_id: str, request: Request):
    await _perm_view(request)
    ctx = await entity_ctx(request)
    await _guard(gallery_id, ctx)
    try:
        data, ctype = await gallery.get_file_bytes(gallery_id, file_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File fisik tidak ditemukan.")
    headers = {"Cache-Control": "private, max-age=300"}
    if request.query_params.get("download") == "1" or not str(ctype or "").startswith("image/"):
        fname = await gallery.file_name_of(gallery_id, file_id)
        headers["Content-Disposition"] = f'attachment; filename="{fname}"'
    return Response(content=data, media_type=ctype, headers=headers)


@router.delete("/design-gallery/{gallery_id}/files/{file_id}")
async def delete_gallery_file(gallery_id: str, file_id: str, request: Request) -> Dict[str, Any]:
    actor = await _perm_manage(request)
    ctx = await entity_ctx(request)
    await _guard(gallery_id, ctx)
    try:
        res = await gallery.delete_file(gallery_id, file_id, actor=actor)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    await audit(actor["name"], "design_gallery_delete_file", "design_gallery", gallery_id,
                {"file_id": file_id})
    return res


# ─── AI auto-tag (graceful) ─────────────────────────────────────
@router.post("/design-gallery/{gallery_id}/autotag")
async def autotag_gallery(gallery_id: str, request: Request) -> Dict[str, Any]:
    """Trigger AI auto-tag. Bila AI nonaktif → 200 {enabled:false} (BUKAN error)."""
    actor = await _perm_manage(request)
    ctx = await entity_ctx(request)
    await _guard(gallery_id, ctx)
    try:
        res = await gallery.autotag(gallery_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await audit(actor["name"], "design_gallery_autotag", "design_gallery", gallery_id,
                {"enabled": res.get("enabled"), "error": res.get("error", "")})
    return res


# ─── FB-01 — Ilustrasi AI (Gemini Nano Banana Pro; demo lokal bila key kosong) ──────
@router.post("/design-gallery/{gallery_id}/ai-illustrate")
async def ai_illustrate_gallery(gallery_id: str, payload: DesignAiIllustrateIn,
                                request: Request) -> Dict[str, Any]:
    """Buat ilustrasi ARAHAN (mockup/modifikasi) — tersimpan sebagai berkas `ai_illustration`
    pada desain yang sama; bukan versi baru dan tidak mengubah status."""
    actor = await _perm_manage(request)
    ctx = await entity_ctx(request)
    await _guard(gallery_id, ctx)
    try:
        fmeta = await gallery.add_ai_illustration(gallery_id, payload.model_dump(), actor["name"])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await audit(actor["name"], "design_gallery_ai_illustrate", "design_gallery", gallery_id,
                {"file_id": fmeta["id"], "mode": payload.mode, "model": fmeta["ai"]["model"],
                 "demo": fmeta["ai"]["demo"]}, reason=payload.prompt[:200])
    return fmeta


@router.post("/design-gallery/{gallery_id}/files/{file_id}/comments")
async def comment_illustration(gallery_id: str, file_id: str, payload: IllustrationCommentIn,
                               request: Request) -> Dict[str, Any]:
    """Komentar pada ilustrasi AI — desainer, admin, manajer (diskusi arahan tercatat di desain)."""
    actor = await _perm_manage(request)
    ctx = await entity_ctx(request)
    await _guard(gallery_id, ctx)
    try:
        c = await gallery.add_illustration_comment(gallery_id, file_id, actor, payload.text)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await audit(actor["name"], "design_gallery_ai_comment", "design_gallery", gallery_id,
                {"file_id": file_id, "comment_id": c["id"]}, reason=payload.text[:200])
    return c


@router.delete("/design-gallery/{gallery_id}/files/{file_id}/comments/{comment_id}")
async def delete_illustration_comment(gallery_id: str, file_id: str, comment_id: str,
                                      request: Request) -> Dict[str, Any]:
    """G-6 — hapus komentar sendiri pada ilustrasi AI (admin: siapa pun)."""
    actor = await _perm_manage(request)
    ctx = await entity_ctx(request)
    await _guard(gallery_id, ctx)
    try:
        res = await gallery.delete_illustration_comment(gallery_id, file_id, comment_id, actor)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await audit(actor["name"], "design_gallery_ai_comment_delete", "design_gallery", gallery_id,
                {"file_id": file_id, "comment_id": comment_id})
    return res


@router.get("/design-gallery-ai/status")
async def ai_illustrate_status(request: Request) -> Dict[str, Any]:
    """Status layanan ilustrasi AI untuk UI: {enabled, demo, verified, model, daily_limit, cost}."""
    await _perm_view(request)
    from services import gemini_image_service as gem
    cfg = await gem.resolve_config()
    return {"enabled": cfg["enabled"], "demo": cfg["demo"], "verified": cfg["verified"],
            "model": cfg["model"], "daily_limit": cfg["daily_limit"],
            "cost_per_image_usd": cfg["cost_per_image_usd"], "configured": cfg['configured'], "disabled_reason": cfg['disabled_reason']}


# ─── FASE F (PS-14) — Master desain: versi & pengesahan ──────────────────────
@router.post("/design-gallery/{gallery_id}/version")
async def bump_design_version(gallery_id: str, payload: DesignVersionIn,
                              request: Request) -> Dict[str, Any]:
    """Naikkan versi desain (artwork direvisi). Versi lama tetap terarsip di `versions[]`."""
    actor = await _perm_manage(request)
    ctx = await entity_ctx(request)
    await _guard(gallery_id, ctx)
    try:
        doc = await gallery.bump_version(gallery_id, payload.model_dump(exclude_unset=True),
                                        actor["name"])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await audit(actor["name"], "design_version_bumped", "design_gallery", gallery_id,
                {"version": doc.get("version")}, reason=payload.note or "")
    return doc


@router.post("/design-gallery/{gallery_id}/submit")
async def submit_design(gallery_id: str, request: Request) -> Dict[str, Any]:
    """UTANG ALUR F-6.7 — draf desain DIAJUKAN dulu, baru bisa disahkan."""
    actor = await _perm_manage(request)
    ctx = await entity_ctx(request)
    await _guard(gallery_id, ctx)
    try:
        doc = await gallery.submit_design(gallery_id, actor["name"])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await audit(actor["name"], "design_submitted", "design_gallery", gallery_id,
                {"code": doc.get("code"), "version": doc.get("version")})
    return doc


@router.post("/design-gallery/{gallery_id}/reject")
async def reject_design(gallery_id: str, payload: DesignRejectIn,
                        request: Request) -> Dict[str, Any]:
    """Kembalikan desain yang diajukan ke draf — ALASAN wajib & tersimpan."""
    actor = await _perm_manage(request)
    ctx = await entity_ctx(request)
    await _guard(gallery_id, ctx)
    try:
        doc = await gallery.reject_design(gallery_id, actor["name"], payload.reason)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await audit(actor["name"], "design_rejected", "design_gallery", gallery_id,
                {"code": doc.get("code")}, reason=payload.reason)
    return doc


@router.post("/design-gallery/{gallery_id}/approve")
async def approve_design(gallery_id: str, payload: DesignApproveIn,
                         request: Request) -> Dict[str, Any]:
    """Sahkan desain agar boleh dipakai proofing & produk printing (wajib kode + berkas)."""
    actor = await _perm_manage(request)
    ctx = await entity_ctx(request)
    await _guard(gallery_id, ctx)
    try:
        doc = await gallery.approve_design(gallery_id, actor["name"], payload.note)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await audit(actor["name"], "design_approved", "design_gallery", gallery_id,
                {"code": doc.get("code"), "version": doc.get("version")},
                reason=payload.note or "")
    return doc


# ─── Rating desain (bintang 1–5, 1 nilai per penilai; admin/manager) ─────────────
@router.post("/design-gallery/{gallery_id}/rating")
async def rate_design(gallery_id: str, payload: DesignRatingIn,
                      request: Request) -> Dict[str, Any]:
    """Set/ubah rating bintang 1–5 milik penilai (admin/manager). Upsert 1 nilai/orang."""
    actor = await _perm_manage(request)
    ctx = await entity_ctx(request)
    await _guard(gallery_id, ctx)
    try:
        doc = await gallery.set_rating(gallery_id, actor.get("id"), actor.get("name", ""),
                                       payload.stars, payload.note)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await audit(actor["name"], "design_rated", "design_gallery", gallery_id,
                {"stars": payload.stars, "rating_avg": doc.get("rating_avg"),
                 "rating_count": doc.get("rating_count")}, reason=payload.note or "")
    return doc


@router.delete("/design-gallery/{gallery_id}/rating")
async def unrate_design(gallery_id: str, request: Request) -> Dict[str, Any]:
    """Hapus rating milik penilai yang sedang login."""
    actor = await _perm_manage(request)
    ctx = await entity_ctx(request)
    await _guard(gallery_id, ctx)
    try:
        doc = await gallery.clear_rating(gallery_id, actor.get("id"))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await audit(actor["name"], "design_unrated", "design_gallery", gallery_id,
                {"rating_avg": doc.get("rating_avg"), "rating_count": doc.get("rating_count")})
    return doc
