"""notification_scope — SATU aturan "notifikasi mana yang relevan untuk pengguna ini".

Dipakai kotak notifikasi (`routers/notifications.py`) dan ringkasan harian (`digest_service`).
Dua lapis, keduanya mengikuti pengaturan Peran & Hak Akses (bukan nama peran yang diketik):

1. AUDIENS — ditujukan ke perannya, ke "all", ke dirinya, atau (untuk peran kustom) ke
   peran ACUANNYA. Notifikasi lama yang masih beralamat `recipient_role="manager"` tetap
   sampai ke peran kustom yang disalin dari Manajer.
2. RELEVANSI — layar tujuan (`link`) harus BOLEH dibuka pemegang peran itu (tingkat ≥ Lihat
   di katalog modul). Notifikasi tanpa `link`, atau yang ditujukan langsung ke orangnya,
   selalu lolos. Admin melihat semuanya.
"""
from typing import Any, Dict, List

from access_modules import LINK_ALIASES, nav_allowed_for_perms


async def audience_roles(user: Dict[str, Any]) -> List[str]:
    import role_registry as reg

    role = str(user.get("role") or "")
    out = [role, "all"]
    base = (reg.ROLES.get(role) or {}).get("base_role") or ""
    if base:
        out.append(base)
    return out


async def allowed_links(user: Dict[str, Any]) -> List[str]:
    from dependencies import permission_matrix

    matrix = await permission_matrix()
    perms = matrix.get(str(user.get("role") or ""), {}) or {}
    allowed = set(nav_allowed_for_perms(perms))
    allowed.update(k for k, v in LINK_ALIASES.items() if v in allowed)
    return sorted(allowed)


async def relevance_filter(user: Dict[str, Any]) -> Dict[str, Any]:
    """Filter Mongo: audiens ∧ relevansi. Admin: semua, kecuali yang ditujukan ke orang lain."""
    uid = user.get("id")
    if user.get("role") == "admin":
        return {"$or": [
            {"recipient_user": {"$in": [None, "", uid]}},
            {"recipient_user": {"$exists": False}},
        ]}
    audience = {"$or": [
        {"recipient_role": {"$in": await audience_roles(user)}},
        {"recipient_user": uid},
    ]}
    links = await allowed_links(user)
    relevance = {"$or": [
        {"recipient_user": uid},
        {"link": {"$in": links}},
        {"link": {"$in": ["", None]}},
        {"link": {"$exists": False}},
    ]}
    return {"$and": [audience, relevance]}
