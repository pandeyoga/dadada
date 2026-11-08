"""Customers (rich KYC): NIK/NPWP/spouse/heir/income + KYC document uploads.

Adopted from SIPROnext Customer model (Dok 10) and wrapped in the new foundation
(org_id scope + RBAC + phone/NIK normalizers). KYC docs go through the storage
abstraction (Emergent managed or mongo fallback).
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pymongo.errors import DuplicateKeyError

import customer_identity
import customer_scope as cs
import listing as lst
import stage_clock as clock
from denorm import cascade_master_change
from db import db, ORG_ID
from core_utils import new_id, now_iso, serialize_doc, parse_pagination, normalize_phone_e164, normalize_nik
from engine import emit, dispatch_pending
from rbac import require_permission
from models import CustomerCreate, CustomerUpdate
import storage

router = APIRouter(prefix="/customers", tags=["customers"])


def _clean(payload: dict) -> dict:
    if payload.get("phone"):
        payload["phone"] = normalize_phone_e164(payload["phone"])
    if payload.get("nik"):
        payload["nik"] = normalize_nik(payload["nik"])
    return payload


async def _attach_files(cust: dict) -> dict:
    ids = [f["file_id"] for f in (cust.get("kyc_files") or [])]
    if ids:
        # AZ-02: berkas KYC hanya dari organisasi pemilik pelanggan (id berasal dari dokumen pelanggan).
        metas = await db.files.find({"id": {"$in": ids}, "org_id": cust.get("org_id"), "is_deleted": False},
                                    {"_id": 0, "data_b64": 0}).to_list(100)
        by_id = {m["id"]: m for m in metas}
        for f in cust.get("kyc_files", []):
            m = by_id.get(f["file_id"]) or {}
            f["original_filename"] = m.get("original_filename")
            f["content_type"] = m.get("content_type")
    return cust


CUSTOMER_SORTS = {"name": "name", "nik": "nik", "phone": "phone",
                  "monthly_income": "monthly_income", "kyc_status": "kyc_status",
                  "created_at": "created_at", "updated_at": "updated_at", **clock.SORTS}

LEGAL_RANK = {"belum": 0, "ppjb": 1, "akad_kredit": 2, "pelunasan": 3, "bast": 4, "ajb": 5,
              "sertifikat": 6}


async def _legal_by_customer(org: str) -> dict:
    """Tahap legal tertinggi per pelanggan dari `contracts` (SSOT tahap legal pembeli) —
    supaya daftar Customer langsung menjawab "siapa yang sudah akad"."""
    rows = await db.contracts.find(
        {"org_id": org, "state": {"$ne": "cancelled"}, "customer_id": {"$ne": None}},
        {"_id": 0, "customer_id": 1, "legal_stage": 1, "legal": 1, "scheme": 1,
         "unit_code": 1, "id": 1}).to_list(10000)
    out = {}
    for c in rows:
        legal = c.get("legal") or {}
        stage = c.get("legal_stage") or "belum"
        akad = legal.get("akad_kredit") or {}
        cur = out.get(c["customer_id"])
        if cur and LEGAL_RANK.get(cur["stage"], 0) >= LEGAL_RANK.get(stage, 0):
            if akad and not cur.get("akad_date"):
                cur["akad_date"] = akad.get("date")
            continue
        out[c["customer_id"]] = {
            "stage": stage, "contract_id": c["id"], "unit_code": c.get("unit_code"),
            "scheme": c.get("scheme"), "akad_date": akad.get("date"),
            "akad_override": bool(akad.get("override")),
            "ajb_date": (legal.get("ajb") or {}).get("date")}
    return out


@router.get("")
async def list_customers(q: str = None, kyc_status: str = None,
                         created_from: str = None, created_to: str = None,
                         sla: str = None, legal_stage: str = None,
                         sort: str = None, direction: str = None,
                         skip: int = 0, limit: int = 50,
                         user: dict = Depends(require_permission("customers", "view"))):
    """Daftar customer: cari + filter multi (KYC) + sort server-side (Fase 40) +
    filter umur/SLA verifikasi berkas dari kebijakan Pusat Konfigurasi (Fase 41) +
    filter tahap legal kontrak (belum/ppjb/akad_kredit/…)."""
    skip, limit = parse_pagination(skip, limit)
    org = user.get("org_id", ORG_ID)
    query = {"org_id": org}
    # KT-09: sales hanya melihat pembeli miliknya (None = peran tanpa batas).
    scope = await cs.scope_filter(user)
    if scope:
        query.update(scope)
    lst.apply_in(query, "kyc_status", kyc_status)
    clock.apply_sla_filter(query, "customer", sla)
    lst.apply_range(query, "created_at", created_from, created_to)
    lst.apply_search(query, q, ("name", "phone", "nik", "email", "npwp"))
    legal_map = await _legal_by_customer(org)
    if scope:
        milik = set(await db.customers.distinct("id", {"org_id": org, **scope}))
        legal_map = {k: v for k, v in legal_map.items() if k in milik}
    wanted = [v for v in lst.multi(legal_stage) if v in LEGAL_RANK]
    if wanted:
        if "belum" in wanted:
            query["id"] = {"$nin": [cid for cid, v in legal_map.items()
                                    if v["stage"] not in wanted]}
        else:
            query["id"] = {"$in": [cid for cid, v in legal_map.items() if v["stage"] in wanted]}
    total = await db.customers.count_documents(query)
    rows = await (db.customers.find(query, {"_id": 0})
                  .sort(lst.sort_spec(sort, direction, CUSTOMER_SORTS, ("created_at", -1)))
                  .skip(skip).limit(limit).to_list(limit))
    await clock.attach(rows, "customer", org_id=org)
    for r in rows:
        r["legal"] = legal_map.get(r["id"]) or {"stage": "belum"}
    counts = {}
    for st in ("pending", "submitted", "verified"):
        counts[st] = await db.customers.count_documents(
            {"org_id": org, **(scope or {}), "kyc_status": st})
    legal_counts = {}
    for v in legal_map.values():
        legal_counts[v["stage"]] = legal_counts.get(v["stage"], 0) + 1
    legal_counts["akad_done"] = sum(1 for v in legal_map.values() if v.get("akad_date"))
    return {"data": serialize_doc(rows), "total": total, "counts": counts,
            "legal_counts": legal_counts}


def _identity_keys(data: dict, allow_dup: bool) -> list:
    """Kunci identitas (NIK, HP, email) yang harus diserialkan agar pemeriksaan duplikat tidak bocor."""
    import re
    keys = []
    if data.get("nik"):
        keys.append("n:" + str(data["nik"]))
    if not allow_dup:
        if data.get("phone"):
            keys.append("p:" + re.sub(r"\D", "", normalize_phone_e164(data["phone"]))[-9:])
        if data.get("email"):
            keys.append("e:" + str(data["email"]).strip().lower())
    return sorted(set(keys))


@router.post("")
async def create_customer(payload: CustomerCreate,
                          user: dict = Depends(require_permission("customers", "create"))):
    org = user.get("org_id", ORG_ID)
    data = _clean(payload.model_dump())
    allow_dup = bool(data.pop("allow_duplicate", False))
    try:
        data = customer_identity.clean_identity(data)  # KT-17: NIK 16 digit, NPWP 15/16, penghasilan >= 0
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    # H-B (P12): "cari duplikat HP/email → insert" tanpa kunci (HP/email tidak punya indeks unik karena
    # `allow_duplicate` sah) — empat permintaan serentak dengan HP yang sama melahirkan empat pembeli kembar.
    # Diserialkan per kunci identitas (urut tetap supaya tidak saling mengunci).
    from contextlib import AsyncExitStack
    from idempotency import mutex
    async with AsyncExitStack() as stack:
        for k in _identity_keys(data, allow_dup):
            await stack.enter_async_context(mutex(f"customer.identity:{org}:{k}", what="Pendaftaran pembeli ini"))
        return await _create_customer_locked(org, data, allow_dup, user)


async def _create_customer_locked(org: str, data: dict, allow_dup: bool, user: dict) -> dict:
    if data.get("nik"):
        dup = await db.customers.find_one({"org_id": org, "nik": data["nik"]}, {"_id": 0})
        if dup:
            raise HTTPException(status_code=409, detail="NIK sudah terdaftar pada customer lain.")
    if not allow_dup:
        dup = await customer_identity.find_duplicate(org, phone=data.get("phone"), email=data.get("email"))
        if dup:
            raise HTTPException(status_code=409, detail=(
                f"Sudah ada pembeli dengan {dup['by']} yang sama: {dup.get('name')}. Buka pembeli itu "
                "dan perbarui datanya, atau pastikan ini orang yang berbeda."))
    ts = now_iso()
    doc = {"id": new_id(), "org_id": org, "kyc_files": [], "kyc_status": "pending",
           "created_by": user.get("email"), "created_at": ts, "updated_at": ts, **data}
    try:
        await db.customers.insert_one(doc)
    except DuplicateKeyError:
        # Index unik: NIK sama atau lead yang sudah punya pembeli (KT-02) — bukan 500.
        raise HTTPException(status_code=409, detail=(
            "Pembeli untuk lead/NIK ini sudah terdaftar. Cari di daftar Pembeli."))
    doc.pop("_id", None)
    # Fase 29: memicu jobdesk SM-07 "Lengkapi KYC pembeli" bila NIK/NPWP belum lengkap.
    if not doc.get("nik"):
        await emit("customer.created", "customer", doc["id"], {"label": doc.get("name")}, org_id=org)
        await dispatch_pending()
    return {"data": serialize_doc(doc)}


async def _get(cid: str, org: str, user: dict = None) -> dict:
    c = await db.customers.find_one({"id": cid, "org_id": org}, {"_id": 0})
    if not c:
        raise HTTPException(status_code=404, detail="Customer tidak ditemukan")
    if user is not None:
        await cs.assert_access(user, cid)   # KT-09: sales hanya boleh membaca/mengubah miliknya
    return c


@router.get("/{cid}")
async def get_customer(cid: str, user: dict = Depends(require_permission("customers", "view"))):
    c = await _get(cid, user.get("org_id", ORG_ID), user)
    return {"data": serialize_doc(await _attach_files(c))}


@router.get("/{cid}/timeline")
async def customer_timeline(cid: str,
                            user: dict = Depends(require_permission("customers", "view"))):
    """Riwayat perjalanan SATU pelanggan, dirangkai dari sumber yang benar-benar mencatatnya.

    ## Cacat yang diperbaiki endpoint ini

    Tab "Timeline" pada profil pelanggan dulu hanya membaca
    `GET /activities?entity_type=customer` — dan koleksi `activities` **tidak pernah**
    menulis baris ber-`entity_type="customer"` (0 baris di database). Akibatnya tab itu
    selalu berbunyi "Belum ada jejak untuk pelanggan ini" bahkan untuk pembeli yang sudah
    memesan rumah, membayar 4 termin, menerima BAST, dan mengajukan 2 klaim garansi.
    Jejaknya ADA, hanya tersimpan di bawah id lead/unit/deal — layar yang berkata "belum
    ada" untuk hal yang ada adalah kebohongan, dan aturan repo melarangnya.

    Jadi jejak dirangkai dari: aktivitas lead & unit miliknya, penerimaan pembayaran
    (kwitansi), berita acara serah terima, klaim garansi, komplain, dan penyerahan dokumen
    syarat. Setiap baris menyebut AKTOR-nya (aturan CR-10) dan `source`-nya supaya bisa
    dilacak. `missing[]` menyebut sumber yang memang belum punya data — bukan disembunyikan.
    """
    org = user.get("org_id", ORG_ID)
    cust = await _get(cid, org, user)
    rows, sources, missing = [], {}, []

    def add(at, kind, title, body, actor, source):
        if at:
            rows.append({"at": at, "kind": kind, "title": title, "body": body,
                         "actor": actor or "sistem", "source": source})

    unit_ids = await db.units.distinct("id", {"org_id": org, "customer_id": cid})
    deal_ids = await db.deals.distinct("id", {"org_id": org, "$or": [
        {"customer_id": cid}, {"lead_id": cust.get("lead_id")} if cust.get("lead_id") else
        {"id": None}]})
    if cust.get("deal_id") and cust["deal_id"] not in deal_ids:
        deal_ids.append(cust["deal_id"])

    ent_ids = [x for x in ([cust.get("lead_id")] + unit_ids + deal_ids + [cid]) if x]
    acts = await db.activities.find(
        {"org_id": org, "entity_id": {"$in": ent_ids}}, {"_id": 0}).to_list(500)
    sources["aktivitas"] = len(acts)
    for a in acts:
        add(a.get("created_at"), "activity",
            "Catatan" if a.get("type") == "comment" else (a.get("title") or "Aktivitas"),
            a.get("body"), a.get("actor") or a.get("created_by"), "activities")

    receipts = await db.receipts.find(
        {"org_id": org, "$or": [{"deal_id": {"$in": deal_ids}},
                                {"unit_id": {"$in": unit_ids}}]}, {"_id": 0}).to_list(300)
    sources["kwitansi"] = len(receipts)
    for r in receipts:
        labels = ", ".join(a.get("label", "") for a in (r.get("allocations") or []))
        add(r.get("created_at"), "document", f"Pembayaran diterima Rp {int(r.get('amount') or 0):,}"
            .replace(",", "."),
            (r.get("note") or "") + (f" · dialokasikan ke {labels}" if labels else ""),
            r.get("actor"), "receipts")

    bast = await db.unit_handovers.find(
        {"org_id": org, "$or": [{"customer_id": cid}, {"deal_id": {"$in": deal_ids}},
                                {"unit_id": {"$in": unit_ids}}]}, {"_id": 0}).to_list(50)
    sources["serah_terima"] = len(bast)
    for h in bast:
        add(h.get("created_at"), "document",
            f"Serah terima rumah — {h.get('number') or 'BAST'}",
            "Berita acara serah terima diterbitkan"
            + (f" (status {h.get('status')})" if h.get("status") else ""),
            h.get("issued_by"), "unit_handovers")

    claims = await db.warranty_claims.find(
        {"org_id": org, "$or": [{"customer_id": cid}, {"unit_id": {"$in": unit_ids}}]},
        {"_id": 0}).to_list(100)
    sources["klaim_garansi"] = len(claims)
    for c in claims:
        add(c.get("created_at"), "message",
            f"Klaim garansi {c.get('number') or ''} — {c.get('title') or ''}".strip(),
            f"Bagian {c.get('category') or '-'}", c.get("created_by") or c.get("reported_by"),
            "warranty_claims")

    comps = await db.complaints.find({"org_id": org, "customer_id": cid},
                                    {"_id": 0}).to_list(100)
    sources["komplain"] = len(comps)
    for c in comps:
        add(c.get("created_at"), "message", f"Komplain: {c.get('subject') or '-'}",
            c.get("description"), c.get("created_by") or c.get("assigned_to"), "complaints")

    subs = await db.doc_submissions.find(
        {"org_id": org, "entity_type": "customer", "entity_id": cid}, {"_id": 0}).to_list(100)
    sources["dokumen_syarat"] = len(subs)
    for s in subs:
        add(s.get("submitted_at") or s.get("created_at"), "upload",
            f"Dokumen “{s.get('requirement_label') or s.get('requirement_code')}” diserahkan",
            {"verified": f"Diverifikasi oleh {s.get('verified_by') or '-'}",
             "rejected": f"Ditolak: {s.get('reject_reason') or '-'}"}.get(
                 s.get("status"), "Menunggu verifikasi"),
            s.get("submitted_by"), "doc_submissions")

    for nama, jumlah in sources.items():
        if not jumlah:
            missing.append(nama)
    rows.sort(key=lambda r: str(r["at"]), reverse=True)
    return {"data": serialize_doc(rows), "sources": sources, "missing": missing}


def _force_or_403(user, force: bool, reason: str):
    """Hapus paksa (beserta transaksi): hanya akses penuh (owner/super_admin) + alasan ≥10 huruf."""
    if not force:
        return
    import force_delete as fd
    if not fd.may_force(user):
        raise HTTPException(status_code=403, detail="Hapus paksa beserta transaksi hanya untuk Direksi/Super Admin.")
    if len((reason or "").strip()) < 10:
        raise HTTPException(status_code=400, detail="Hapus paksa wajib alasan (minimal 10 huruf).")


@router.delete("/{cid}")
async def delete_customer(cid: str, force: bool = False, reason: str = None,
                          user: dict = Depends(require_permission("customers", "delete"))):
    """Hapus customer salah input. Ditolak bila sudah punya deal aktif/kontrak/invoice/pembayaran/unit/KPR —
    kecuali `force=true` (akses penuh + alasan): seluruh transaksinya ikut dihapus."""
    import master_delete as md
    from rbac import audit_log
    org = user.get("org_id", ORG_ID)
    cust = await _get(cid, org, user)
    _force_or_403(user, force, reason)
    if force:
        import force_delete as fd
        ors = [{"customer_id": cid}] + ([{"lead_id": cust["lead_id"]}] if cust.get("lead_id") else [])
        await fd.delete_deals_of(org, {"$or": ors}, user.get("email"))
        for coll in ("contracts", "ar_invoices", "payment_intakes", "financing_apps", "portal_users"):
            await db[coll].delete_many({"org_id": org, "customer_id": cid})
        await db.units.update_many({"org_id": org, "customer_id": cid}, {"$unset": {"customer_id": "", "contract_id": ""}})
        await audit_log(user, "force_delete", "customers", cid, {"reason": reason})
    try:
        out = await md.delete_customer(org, cust)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await audit_log(user, "delete", "customers", cid, {"name": cust.get("name"), "removed": out["removed"]})
    return {"data": out}


@router.get("/{cid}/delete-check")
async def customer_delete_check(cid: str, user: dict = Depends(require_permission("customers", "view"))):
    import master_delete as md
    org = user.get("org_id", ORG_ID)
    cust = await _get(cid, org, user)
    blockers = await md.blockers_of(org, "customer", cust)
    import force_delete as fd
    return {"data": {"can_delete": not blockers, "blockers": blockers, "can_force": fd.may_force(user)}}


@router.put("/{cid}")
async def update_customer(cid: str, payload: CustomerUpdate,
                          user: dict = Depends(require_permission("customers", "update"))):
    org = user.get("org_id", ORG_ID)
    await _get(cid, org, user)
    data = _clean({k: v for k, v in payload.model_dump().items() if v is not None})
    try:
        data = customer_identity.clean_identity(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if data.get("nik") and await db.customers.find_one(
            {"org_id": org, "nik": data["nik"], "id": {"$ne": cid}}, {"_id": 1}):
        raise HTTPException(status_code=409, detail="NIK sudah terdaftar pada customer lain.")
    data["updated_at"] = now_iso()
    try:
        await db.customers.update_one({"id": cid, "org_id": org}, {"$set": data})
    except DuplicateKeyError:
        raise HTTPException(status_code=409, detail="NIK sudah terdaftar pada customer lain.")
    fresh = await db.customers.find_one({"id": cid, "org_id": org}, {"_id": 0})
    await cascade_master_change("customers", cid, fresh)
    return {"data": serialize_doc(await _attach_files(fresh))}


@router.post("/{cid}/kyc")
async def upload_kyc(cid: str, file: UploadFile = File(...), doc_type: str = Form("ktp"),
                     user: dict = Depends(require_permission("customers", "update"))):
    org = user.get("org_id", ORG_ID)
    await _get(cid, org, user)
    data = await file.read()
    try:
        rec = await storage.save_file(
            data=data, filename=file.filename or f"{doc_type}.bin",
            content_type=file.content_type or "application/octet-stream", org_id=org,
            owner_type="customer", owner_id=cid, uploaded_by=user.get("email"),
            doc_type=doc_type, tag="kyc",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    entry = {"file_id": rec["id"], "doc_type": doc_type,
             "original_filename": rec["original_filename"], "uploaded_at": rec["created_at"]}
    await db.customers.update_one({"id": cid, "org_id": org},
                                  {"$push": {"kyc_files": entry},
                                   "$set": {"kyc_status": "submitted", "updated_at": now_iso()}})
    fresh = await db.customers.find_one({"id": cid, "org_id": org}, {"_id": 0})
    return {"data": serialize_doc(await _attach_files(fresh))}
