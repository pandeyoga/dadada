"""Pemanggil API internal in-process (ASGI) — semua aksi AI melewati RBAC/validasi endpoint yang sama dengan UI."""
import logging
import secrets

import httpx

from core_utils import new_id, now_iso
from db import db, ORG_ID

logger = logging.getLogger("estora.ai.internal_api")


async def call(token: str, method: str, path: str, *, params: dict = None, json=None):
    """Panggil endpoint internal. Mengembalikan (status, data); tidak pernah melempar karena status HTTP."""
    import server  # tertunda: hindari impor melingkar
    if not path.startswith("/api"):
        path = "/api" + (path if path.startswith("/") else "/" + path)
    transport = httpx.ASGITransport(app=server.app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://internal", timeout=60) as c:
        r = await c.request(method.upper(), path, params=params, json=json,
                            headers={"Authorization": f"Bearer {token}"})
    try:
        data = r.json()
    except Exception:
        data = r.text
    return r.status_code, data


def error_detail(data) -> str:
    if isinstance(data, dict):
        d = data.get("detail")
        if isinstance(d, str):
            return d
        if d:
            return str(d)[:300]
    return str(data)[:300]


async def service_user(org_id: str = ORG_ID) -> dict:
    """Pengguna layanan `ai_agent` per organisasi (dibuat bila belum ada; tidak bisa login)."""
    email = f"estora-ai@{org_id}.layanan.estora"
    u = await db.users.find_one({"email": email}, {"_id": 0, "password_hash": 0})
    if not u:
        from security import hash_password
        ts = now_iso()
        await db.users.update_one({"email": email}, {"$setOnInsert": {
            "id": new_id(), "org_id": org_id, "name": "Estora AI", "email": email, "role": "ai_agent",
            "phone": None, "password_hash": hash_password(secrets.token_urlsafe(32)),
            "is_active": True, "created_at": ts, "updated_at": ts}}, upsert=True)
        u = await db.users.find_one({"email": email}, {"_id": 0, "password_hash": 0})
    return u


async def service_token(org_id: str = ORG_ID) -> str:
    from security import create_access_token
    u = await service_user(org_id)
    return create_access_token(u["id"], u["email"], "ai_agent")
