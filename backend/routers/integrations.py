"""H5 router — Integrasi AI (Anthropic Claude) config.

Scope `integrations` di system_settings. RBAC: admin only via hr.manage_settings
(manager TIDAK memilikinya). Key API TIDAK pernah dikembalikan plaintext — GET
hanya mengembalikan `has_key`. Lihat memory/PLAN_HRD.md §10b HR-Q5.
"""
from typing import Any, Dict
from fastapi import APIRouter, HTTPException, Request

from dependencies import require_permission, audit
from schemas_integrations import IntegrationsUpdate
from services import integrations_service as integ

router = APIRouter(prefix="/api")


@router.get("/admin/integrations")
async def get_integrations(request: Request) -> Dict[str, Any]:
    """Config integrasi ter-MASK (api_key → has_key). Admin only."""
    await require_permission(request, "hr", "manage_settings")
    return await integ.get_integrations_public()


@router.put("/admin/integrations")
async def update_integrations(payload: IntegrationsUpdate, request: Request) -> Dict[str, Any]:
    """Set/clear key + model + enabled. Admin only. Return config ter-mask."""
    actor = await require_permission(request, "hr", "manage_settings")
    patch = payload.model_dump(exclude_unset=True)
    if not patch:
        raise HTTPException(status_code=400, detail="Tidak ada perubahan dikirim.")
    res = await integ.update_integrations(patch)
    # Audit TANPA membocorkan key (catat hanya status perubahan).
    await audit(actor["name"], "integrations_update", "system_settings", "integrations",
                {"key_changed": bool(patch.get("anthropic_api_key") or patch.get("anthropic_clear_key")
                                     or patch.get("gemini_api_key") or patch.get("gemini_clear_key")),
                 "model": res["anthropic"]["model"], "enabled": res["anthropic"]["enabled"],
                 "gemini_model": res["gemini"]["model"], "gemini_enabled": res["gemini"]["enabled"]})
    return res


@router.post("/admin/integrations/gemini/test")
async def test_gemini(request: Request) -> Dict[str, Any]:
    """G-3 — uji koneksi key Gemini (panggilan ringan). Lulus → `verified_at` diisi → status LIVE."""
    actor = await require_permission(request, "hr", "manage_settings")
    from services import gemini_image_service as gem
    from core_utils import now_iso
    cfg = await gem.resolve_config()
    if not cfg["api_key"]:
        raise HTTPException(status_code=400, detail="API key Gemini belum diisi.")
    try:
        res = await gem.test_connection(cfg["api_key"])
    except ValueError as e:
        await integ.update_integrations({"gemini_verified_at": ""})
        await audit(actor["name"], "integrations_gemini_test", "system_settings", "integrations",
                    {"ok": False, "error": str(e)[:200]})
        raise HTTPException(status_code=400, detail=str(e))
    ts = now_iso()
    await integ.update_integrations({"gemini_verified_at": ts})
    await audit(actor["name"], "integrations_gemini_test", "system_settings", "integrations",
                {"ok": True, "models_seen": res.get("models_seen")})
    return {"ok": True, "verified_at": ts, "model": cfg["model"], **res}
