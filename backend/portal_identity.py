"""Identitas pembeli portal — pencarian pengguna portal / pelanggan / lead pemegang reservasi.

Dipisah dari `routers/portal_router.py` (audit AZ-02: pencarian by-id tanpa `org_id`).
Masuk ke portal memakai KONTAK (telepon/email) tanpa memilih organisasi, jadi pencarian
awal `kind: val` memang lintas-organisasi — SETELAH pengguna portal ditemukan, organisasi
miliknya (`pu["org_id"]`) mengikat semua pencarian turunan.
"""
from core_utils import new_id, normalize_phone_e164, now_iso
from db import ORG_ID, db


def normalize_ident(ident: str):
    ident = (ident or "").strip()
    if "@" in ident:
        return "email", ident.lower()
    return "phone", normalize_phone_e164(ident)


async def find_portal_user(ident: str):
    """Auto-provision dari customer — atau LEAD pemegang reservasi (booking fee, Fase 69B)."""
    kind, val = normalize_ident(ident)
    pu = await db.portal_users.find_one({kind: val}, {"_id": 0})
    if pu:
        return pu
    cust = await db.customers.find_one({kind: val}, {"_id": 0})
    lead = None
    if not cust:
        lead = await db.leads.find_one({kind: val}, {"_id": 0})
        # Deal pemegang reservasi harus dari organisasi LEAD itu sendiri.
        if not lead or not await db.deals.find_one(
                {"lead_id": lead["id"], "org_id": lead.get("org_id", ORG_ID),
                 "status": {"$in": ["reserved", "booked"]}}, {"_id": 1}):
            return None
    src = cust or lead
    ts = now_iso()
    pu = {"id": new_id(), "org_id": src.get("org_id", ORG_ID), "is_active": True,
          "customer_id": cust["id"] if cust else None, "lead_id": None if cust else lead["id"],
          "name": src.get("name"), "phone": src.get("phone"), "email": src.get("email"),
          "created_at": ts, "last_login_at": None}
    await db.portal_users.insert_one(dict(pu))
    pu.pop("_id", None)
    return pu


async def customer_of(pu: dict) -> dict:
    """Pelanggan (atau lead pemegang reservasi) milik pengguna portal — di organisasi pengguna itu."""
    org = pu.get("org_id", ORG_ID)
    cust = (await db.customers.find_one({"id": pu.get("customer_id"), "org_id": org}, {"_id": 0})
            if pu.get("customer_id") else None)
    if cust:
        return cust
    lead = (await db.leads.find_one({"id": pu.get("lead_id"), "org_id": org}, {"_id": 0})
            if pu.get("lead_id") else None)
    return ({"id": lead["id"], "lead_id": lead["id"], "name": lead.get("name"), "is_lead": True,
             "phone": lead.get("phone"), "email": lead.get("email")} if lead else {})
