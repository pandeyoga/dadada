"""Pembantu uji: konteks alat dari pengguna demo, data lead lewat API."""
import uuid

from ai.tools import internal_api
from ai.tools.registry import ToolContext
from db import db, ORG_ID


async def user_of(email: str) -> dict:
    return await db.users.find_one({"email": email}, {"_id": 0, "password_hash": 0})


async def ctx_for(email: str, token: str, **kw) -> ToolContext:
    u = await user_of(email)
    return ToolContext(org_id=ORG_ID, user=u, token=token, **kw)


async def make_lead(client, auth, token: str, name: str = "Calon Pembeli") -> dict:
    # Nomor unik per panggilan (uuid, bukan hash(name) yang bisa bertabrakan -> lead dedup ke lead lain).
    phone = f"0819{uuid.uuid4().int % 10**8:08d}"
    r = await client.post("/api/leads", headers=auth(token), json={"name": name, "phone": phone, "source": "manual"})
    assert r.status_code == 200, r.text
    return r.json()["data"]
