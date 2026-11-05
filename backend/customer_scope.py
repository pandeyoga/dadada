"""CAKUPAN DATA PEMBELI untuk peran bercakupan-sendiri (sales) — audit KT-09.

Cacat nyata: lead, deal, dan kontrak sudah dibatasi ke `assigned_to` pemegangnya
(`rbac.scope_query` / `is_scoped_sales`), tetapi `/customers/{id}` dan seluruh turunannya
(`/timeline`, `/contract-pricing`, `/units-construction`) membaca TANPA batas. Akibatnya sales2
mendapat 403 saat membuka kontrak sales lain, tetapi 200 — lengkap dengan nomor kontrak, harga,
AR, komponen biaya, NIK, alamat, dan timeline — saat membuka pembeli yang sama lewat `/customers`.

Pembeli "milik" sales bila SALAH SATU:
  * `assigned_to` pembeli = sales (diisi dari deal saat konversi);
  * sales yang membuat pembeli manual (`created_by`);
  * lead asal pembeli (`lead_id` / `lead_ids[]`) dipegang sales;
  * ada deal atau kontrak atas pembeli itu yang dipegang sales.
Peran lain (manajer, finance, owner, dst.) tidak dibatasi — `scope_filter` mengembalikan None.
"""
from fastapi import HTTPException

from db import ORG_ID, db
from rbac import is_scoped_sales


async def scope_filter(user: dict):
    """Filter Mongo (kunci `$or`) untuk koleksi `customers`, atau None bila tanpa batas."""
    if not is_scoped_sales(user):
        return None
    org = user.get("org_id", ORG_ID)
    me = user.get("email")
    lead_ids = await db.leads.distinct("id", {"org_id": org, "assigned_to": me})
    cust_ids = set(await db.contracts.distinct("customer_id", {"org_id": org, "assigned_to": me}))
    cust_ids |= set(await db.deals.distinct("customer_id", {"org_id": org, "assigned_to": me}))
    cust_ids.discard(None)
    ors = [{"assigned_to": me}, {"created_by": me}]
    if lead_ids:
        ors += [{"lead_id": {"$in": lead_ids}}, {"lead_ids": {"$in": lead_ids}}]
    if cust_ids:
        ors.append({"id": {"$in": list(cust_ids)}})
    return {"$or": ors}


async def assert_access(user: dict, cid: str) -> None:
    """403 bila pembeli ada tetapi di luar cakupan sales ini (404 tetap urusan pemanggil)."""
    flt = await scope_filter(user)
    if flt is None:
        return
    org = user.get("org_id", ORG_ID)
    if not await db.customers.find_one({"id": cid, "org_id": org, **flt}, {"_id": 1}):
        raise HTTPException(status_code=403, detail="Akses ditolak: bukan pembeli Anda")
