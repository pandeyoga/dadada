"""Deals + Units — atomic booking (anti double-booking). Slice A."""
from fastapi import APIRouter, Depends, HTTPException

import listing as lst
import settings_store as cfg
import stage_clock as clock
from db import db, ORG_ID, BOOKING_HOLD_DAYS
from core_utils import new_id, now_iso, serialize_doc, parse_pagination
from rbac import can, require_permission, scope_query, is_scoped_sales, audit_log, has_role
from org_scope import get_in_org
from idempotency import transition
import lead_lifecycle as lc
from engine import emit, add_activity, dispatch_pending
from models import DealReserve, DealAction, DealCancel, DealPricingDecision, PpjbSign, AjbSign
from models_p56 import DealCancelIn

router = APIRouter(tags=["deals"])


async def _bind_unit(org: str, unit_id: str):
    """Fase 31: simpan ikatan unit → deal → lead → pembeli pada dokumen unit & jadwalnya."""
    import build_engine as be
    try:
        await be.sync_unit_binding(org, unit_id)
    except Exception:  # noqa: BLE001  (ikatan denormalisasi tidak boleh menggagalkan deal)
        pass


# ----------------------------- Units -----------------------------
UNIT_SORTS = {"code": "code", "type": "type", "status": "status", "price": "price",
              "construction_progress": "construction_progress", "block": "block",
              "cluster_code": "cluster_code", "payment_status": "payment_status",
              "created_at": "created_at", "updated_at": "updated_at"}


@router.get("/units")
async def list_units(project_id: str = None, status: str = None, q: str = None,
                     type: str = None, cluster_id: str = None, block_id: str = None,
                     construction_status: str = None, payment_status: str = None,
                     customer_id: str = None, lead_id: str = None,
                     sort: str = None, direction: str = None,
                     skip: int = 0, limit: int = 200,
                     user: dict = Depends(require_permission("units", "view"))):
    """Daftar unit: cari kode + filter multi (status/tipe/cluster/blok) + sort (Fase 40)."""
    skip, limit = parse_pagination(skip, limit)
    org = user.get("org_id", ORG_ID)
    q_base = {"org_id": org}
    if project_id:
        q_base["project_id"] = project_id
    lst.apply_in(q_base, "status", status)
    lst.apply_in(q_base, "type", type)
    lst.apply_in(q_base, "cluster_id", cluster_id)
    lst.apply_in(q_base, "block_id", block_id)
    lst.apply_in(q_base, "construction_status", construction_status)
    lst.apply_in(q_base, "payment_status", payment_status)
    lst.apply_in(q_base, "customer_id", customer_id)
    lst.apply_in(q_base, "lead_id", lead_id)
    lst.apply_search(q_base, q, ("code", "type", "block", "cluster_code", "lead_name"))
    total = await db.units.count_documents(q_base)
    rows = await (db.units.find(q_base, {"_id": 0})
                  .sort(lst.sort_spec(sort, direction, UNIT_SORTS, ("code", 1)))
                  .skip(skip).limit(limit).to_list(limit))
    projects = await db.projects.find({"org_id": org}, {"_id": 0, "id": 1, "name": 1}).to_list(200)
    pmap = {p["id"]: p["name"] for p in projects}
    for u in rows:
        u["project_name"] = pmap.get(u.get("project_id"))
    lst.attach_aging(rows, history_field="status_history")
    # Hitungan status memakai filter yang sama MINUS filter status sendiri, supaya angka pada
    # chip filter tidak berubah menjadi 0 begitu satu status dipilih (dulu membingungkan).
    base_no_status = {k: v for k, v in q_base.items() if k != "status"}
    counts = {}
    for st in ("available", "reserved", "booked", "sold"):
        counts[st] = await db.units.count_documents({**base_no_status, "status": st})
    return {"data": serialize_doc(rows), "total": total, "counts": counts}


# ----------------------------- Deals -----------------------------
DEAL_SORTS = {"unit_code": "unit_code", "status": "status", "price": "price",
              "booking_fee": "booking_fee", "assigned_to": "assigned_to",
              "reserved_at": "reserved_at", "created_at": "created_at",
              "updated_at": "updated_at", **clock.SORTS}


@router.get("/deals")
async def list_deals(status: str = None, q: str = None, assigned_to: str = None,
                     project_id: str = None, lead_id: str = None, unit_id: str = None,
                     sort: str = None, direction: str = None, sla: str = None,
                     created_from: str = None, created_to: str = None,
                     skip: int = 0, limit: int = 50,
                     user: dict = Depends(require_permission("deals", "view"))):
    """Daftar deal: cari + filter multi + sort server-side + umur status (Fase 40) +
    filter umur status/SLA dari Pusat Konfigurasi (Fase 41)."""
    skip, limit = parse_pagination(skip, limit)
    base = {}
    lst.apply_in(base, "status", status)
    lst.apply_in(base, "assigned_to", assigned_to)
    lst.apply_in(base, "project_id", project_id)
    lst.apply_in(base, "lead_id", lead_id)
    lst.apply_in(base, "unit_id", unit_id)
    clock.apply_sla_filter(base, "deal", sla)
    lst.apply_range(base, "created_at", created_from, created_to)
    lst.apply_search(base, q, ("unit_code", "notes"))
    query = scope_query(user, base)
    total = await db.deals.count_documents(query)
    rows = await (db.deals.find(query, {"_id": 0})
                  .sort(lst.sort_spec(sort, direction, DEAL_SORTS, ("created_at", -1)))
                  .skip(skip).limit(limit).to_list(limit))
    await clock.attach(rows, "deal", org_id=user.get("org_id", ORG_ID))
    counts = {}
    for st in ("reserved", "booked", "cancelled", "closed"):
        counts[st] = await db.deals.count_documents({**scope_query(user, {}), "status": st})
    # enrich
    org_id = user.get("org_id", ORG_ID)
    for d in rows:
        unit = await db.units.find_one({"id": d.get("unit_id"), "org_id": org_id}, {"_id": 0, "code": 1, "type": 1})
        lead = await db.leads.find_one({"id": d.get("lead_id"), "org_id": org_id}, {"_id": 0, "name": 1})
        d["unit_code"] = unit.get("code") if unit else None
        d["unit_type"] = unit.get("type") if unit else None
        d["lead_name"] = lead.get("name") if lead else None
    return {"data": serialize_doc(rows), "total": total, "counts": counts}


@router.get("/deals/{deal_id}")
async def get_deal(deal_id: str, user: dict = Depends(require_permission("deals", "view"))):
    # AZ-01: wajib dalam organisasi pemakai (lintas-org = 404).
    d = await get_in_org(db.deals, deal_id, user, name="Deal")
    if is_scoped_sales(user) and d.get("assigned_to") != user.get("email"):
        raise HTTPException(status_code=403, detail="Akses ditolak: bukan deal Anda")
    return {"data": serialize_doc(d)}


_COST_KEYS = ("bphtb", "notary_fee", "bank_fee", "insurance", "pph_seller", "promo_discount")


def _clean_costs(costs) -> dict:
    """Hanya angka ≥0 yang diisi manusia + penanda all-in; kosong = belum diketahui."""
    out = {}
    for k in _COST_KEYS:
        v = (costs or {}).get(k)
        if v not in (None, "") and int(v) >= 0:
            out[k] = int(v)
    if (costs or {}).get("all_in_by_developer"):
        out["all_in_by_developer"] = True
    return out


@router.post("/deals/reserve")
async def reserve_unit(payload: DealReserve,
                       user: dict = Depends(require_permission("deals", "create"))):
    """Reservasi unit — memakai SATU jalur reservasi bersama (`sales_reserve.reserve`).

    Fase 53: isi fungsi ini dipindah ke `sales_reserve.py` supaya jalur dari PENAWARAN
    (`quotation_engine.convert`) tidak lagi membuat deal berbentuk lain. Dulu deal hasil
    penawaran ditulis `{"stage": "reserved", "status": "active"}` sehingga `POST
    /deals/{id}/book` menolaknya, tahap lead tidak maju, unit tidak terikat pembeli, dan
    masa keep unit tidak pernah diset.
    """
    import sales_reserve as sr
    org = user.get("org_id", ORG_ID)
    unit = await db.units.find_one({"id": payload.unit_id, "org_id": org}, {"_id": 0})
    if not unit:
        raise HTTPException(status_code=404, detail="Unit tidak ditemukan")
    lead = await db.leads.find_one({"id": payload.lead_id, "org_id": org}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead tidak ditemukan")
    if is_scoped_sales(user) and lead.get("assigned_to") != user.get("email"):
        raise HTTPException(status_code=403, detail="Akses ditolak: bukan lead Anda")
    # KT-20: lead yang sudah ditutup (lost/recycle) tidak bisa memesan unit.
    import reserve_guard as rg
    if rg.closed_reason(lead):
        raise HTTPException(status_code=409, detail=rg.closed_reason(lead))
    # `reservation.max_active_per_lead` + `reservation.override_roles` (Pusat Konfigurasi).
    # Pemeriksaan AUTORITATIF ada di `sales_reserve.reserve` (di bawah kunci per-lead, KT-18);
    # di sini hanya memberi pesan awal + menangani pengecualian peran/alasan.
    max_active = int(await cfg.get("reservation.max_active_per_lead", org_id=org) or 1)
    active_cnt = await rg.active_count(org, lead["id"])
    limit_override = False
    if active_cnt >= max_active:
        override_roles = list(await cfg.get("reservation.override_roles", org_id=org) or [])
        reason = (payload.limit_override_reason or "").strip()
        if not has_role(user, *override_roles) or len(reason) < 10:
            raise HTTPException(status_code=409, detail=(
                f"Lead ini sudah memegang {active_cnt} unit aktif (batas {max_active}). "
                "Hanya peran " + ", ".join(override_roles or ["-"])
                + " yang boleh melewati batas, dengan alasan (≥10 karakter)."))
        await audit_log(user, "override", "deals", None,
                        {"limit_override": True, "reason": reason, "active": active_cnt})
        limit_override = True
    # Fase 69: reservasi langsung memakai MESIN HARGA yang sama dengan penawaran — rincian
    # (harga dasar, add-on, skema diskon/promo/kupon, termin) tersimpan pada deal.
    import quotation_engine as qe
    import pricing_engine as pe
    try:
        calc = await qe.simulate(org, unit_id=unit["id"], addons=payload.addons,
                                 scheme_id=payload.scheme_id, kpr=payload.kpr,
                                 discount_scheme_id=payload.discount_scheme_id,
                                 promo_id=payload.promo_id, coupon_code=payload.coupon_code,
                                 lead_id=lead["id"], booking_fee=payload.booking_fee,
                                 allin_scheme_id=payload.allin_scheme_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    # Persetujuan potongan dievaluasi SETELAH biaya all-in menempel (lihat bawah) — jalur
    # SPR berbeda dari penawaran: reservasi tetap dibuat, tetapi MENUNGGU persetujuan
    # (booking & SPR tertahan) kecuali pembuatnya sendiri memegang `pricing:approve`.
    # Fase 77E: add-on berharga master 0 memblokir reservasi. Override sales_manager+ dengan
    # alasan → dicatat sebagai add-on HARGA + DISKON 100% (pendapatan & piutang tetap utuh).
    zero = [a for a in calc.get("addons") or [] if not int(a.get("unit_price") or 0)
            and (a.get("finance_treatment") or "revenue") != "info"]
    if zero:
        ov = payload.addon_zero_override or {}
        prices = {k: int(v) for k, v in (ov.get("prices") or {}).items() if int(v or 0) > 0}
        if (not await can(user.get("role"), "pricing", "approve")
                or len((ov.get("reason") or "").strip()) < 10
                or any(a["code"] not in prices for a in zero)):
            raise HTTPException(status_code=409, detail=(
                "Add-on berharga Rp 0 di master: " + ", ".join(a["code"] for a in zero)
                + ". Isi harganya di master, atau sales manager mengisi harga + alasan (dicatat "
                "sebagai diskon 100%, bukan harga nol)."))
        for a in zero:
            a["unit_price"] = prices[a["code"]]
            a["amount"] = prices[a["code"]]
            a["formula"] = "harga override manajer"
            # Potongan bersasaran ADD-ON: tidak menyentuh harga unit / termin / KPR.
            calc["discount_lines"].append({
                "source": "override", "source_label": "Override add-on", "rule_id": a["code"],
                "code": a["code"], "name": f"Gratis {a.get('name') or a['code']}", "amount": a["amount"],
                "target": "addon", "target_component": a["code"], "target_label": "add-on",
                "formula": "diskon 100%", "requires_approval": False, "reason": ov["reason"].strip(),
                "by": user.get("email")})
            calc["addon_total"] = int(calc.get("addon_total") or 0) + a["amount"]
        await audit_log(user, "override", "deals", None,
                        {"addon_zero": [a["code"] for a in zero], "reason": ov["reason"].strip()})
    # Fase 76: biaya dari SKEMA all-in (snapshot komponen — SUDAH dihitung `simulate` dengan
    # potongan bersasaran komponen), atau manual oleh finance + alasan.
    import allin_engine as ae
    costs = _clean_costs(payload.costs)
    try:
        if payload.allin_scheme_id:
            snap = dict(calc["costs"] or {})
            costs = {k: v for k, v in costs.items() if k in ("pph_seller", "promo_discount")}
            costs.update(snap)
        elif payload.costs_manual is not None:
            if not await ae.may_manual(user):  # MANUAL_ROLES = pemegang finance:manage
                raise HTTPException(status_code=403, detail=(
                    "Input biaya manual hanya untuk finance_manager/superadmin — pilih skema all-in."))
            costs.update(ae.manual_components(payload.costs_manual, payload.costs_manual_reason,
                                              user.get("email")))
            await audit_log(user, "override", "deal_costs", None,
                            {"reason": payload.costs_manual_reason, "items": payload.costs_manual})
            qe.attach_costs(calc, costs)
        elif any(k in costs for k in ("bphtb", "notary_fee", "bank_fee", "insurance")):
            if not await ae.may_manual(user):
                raise HTTPException(status_code=403, detail=(
                    "Input biaya bebas sudah ditutup — pilih skema all-in dari master."))
            costs["components"] = ae.legacy_components(costs)
            costs["scheme_code"], costs["scheme_name"] = "LEGACY", "Legacy (input bebas)"
            qe.attach_costs(calc, costs)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    # Fase 88C: potongan bersasaran komponen biaya yang tidak menemukan komponennya = pending.
    pending = [x for x in calc["discount_lines"] if x.get("pending")]
    if pending:
        raise HTTPException(status_code=400, detail=(
            "Potongan " + ", ".join(x["code"] for x in pending)
            + " menyasar komponen biaya yang tidak ada pada transaksi ini — pilih skema all-in "
            "yang memuat komponennya, atau pilih promo lain."))
    # Booking fee bersih setelah promo bersasaran booking fee.
    booking_fee_net = int(calc.get("booking_fee_net") if calc.get("booking_fee_net") is not None
                          else (payload.booking_fee or 0))
    qe.refresh_totals(calc)
    approval = None
    if calc["needs_discount_approval"]:
        reason = (payload.discount_reason or "").strip()
        if len(reason) < 5:
            raise HTTPException(status_code=400, detail=(
                "Potongan ini memerlukan persetujuan manajer — tulis alasan/dasar potongan (≥5 huruf) "
                "agar manajer bisa memutuskan. Reservasi akan menunggu persetujuan."))
        ts = now_iso()
        # W1-B (#8): kebijakan persetujuan (mode + tabel tingkat) yang berlaku SAAT permohonan lahir direkam di
        # permohonan itu; mengganti pengaturan kemudian tidak mengubah permohonan yang sedang menunggu.
        import discount_approval as da
        snap = await da.snapshot(org, unit.get("project_id"), int(calc.get("total_discount_amount") or 0))
        if await can(user.get("role"), "pricing", "approve") and da.covers(snap, user.get("role")):
            approval = {"state": "approved", "reasons": calc["approval_reasons"], "reason": reason,
                        "requested_by": user.get("email"), "requested_at": ts,
                        "decided_by": user.get("email"), "decided_at": ts, "self_approved": True,
                        "decision_reason": "Dibuat langsung oleh pemegang izin pricing:approve.",
                        "policy_snapshot": snap}
        else:
            approval = {"state": "pending", "reasons": calc["approval_reasons"], "reason": reason,
                        "requested_by": user.get("email"), "requested_at": ts,
                        "decided_by": None, "decided_at": None, "decision_reason": None,
                        "policy_snapshot": snap}
    # KT-08: kuota kupon dipakai SECARA ATOMIK lebih dulu (deal_id dibuat di sini), baru unit
    # ditahan. Dulu kupon ditebus SESUDAH deal ada: dua reservasi serentak pada kupon kuota 1
    # sama-sama berdiskon (deal kedua tertinggal dengan HTTP 500 dan unit terkunci).
    deal_id = new_id()
    redeemed = False
    if calc.get("coupon_code"):
        try:
            await pe.redeem_coupon(org, calc["coupon_code"], unit=unit, lead=lead,
                                   ref_type="deal", ref_id=deal_id,
                                   amount=int((calc.get("coupon") or {}).get("amount") or 0),
                                   actor=user.get("email"))
        except ValueError as e:
            raise HTTPException(status_code=409, detail=str(e))
        redeemed = True
    try:
        deal = await sr.reserve(org, lead=lead, unit=unit, actor=user.get("email"),
                                booking_fee=booking_fee_net, notes=payload.notes,
                                deal_id=deal_id, limit_override=limit_override,
                                extra={"price": int(calc["net_price"]),
                                       "discount": int(calc["discount_amount"] or 0),
                                       "addons": calc["addons"],
                                       "scheme_id": (calc.get("scheme") or {}).get("id"),
                                       # Jalur 1: skema yang DIPILIH sales mengunci jenis kontrak;
                                       # skema bawaan (tidak dipilih) boleh diganti saat konversi.
                                       "scheme_explicit": bool(payload.scheme_id),
                                       "pricing": qe.pricing_snapshot(calc),
                                       "pricing_approval": approval,
                                       "costs": costs})
    except BaseException as e:
        if redeemed:  # reservasi gagal → kuota kupon dikembalikan (tebusan ditandai released)
            await pe.release_coupon(org, ref_type="deal", ref_id=deal_id, actor=user.get("email"))
        if isinstance(e, ValueError):
            raise HTTPException(status_code=409, detail=str(e))
        raise
    if approval and approval["state"] == "pending":
        await _notify_pricing_approvers(org, deal, calc, approval.get("policy_snapshot"))
        await audit_log(user, "request_approval", "deals", deal["id"],
                        {"reasons": calc["approval_reasons"], "reason": approval["reason"]})
    elif approval:
        await audit_log(user, "approve", "deals", deal["id"],
                        {"self_approved": True, "reasons": calc["approval_reasons"]})
    return {"data": serialize_doc(deal)}


def pricing_approval_block(deal: dict) -> str:
    """Alasan booking/SPR DITAHAN karena potongan belum disetujui manajer (atau None)."""
    pa = deal.get("pricing_approval") or {}
    if pa.get("state") == "pending":
        return ("Potongan pada reservasi ini masih MENUNGGU persetujuan manajer — booking dan SPR "
                "belum boleh dilanjutkan.")
    if pa.get("state") == "rejected":
        return (f"Potongan pada reservasi ini DITOLAK manajer ({pa.get('decision_reason') or '-'}) — "
                "batalkan reservasi lalu buat ulang tanpa potongan tersebut.")
    return None


async def _notify_pricing_approvers(org: str, deal: dict, calc: dict, snap: dict = None) -> None:
    import quotation_engine as qe
    from engine import create_notification
    reasons = "; ".join(r.get("label") or "" for r in calc.get("approval_reasons") or [])
    # Mode bertingkat: hanya penyetuju yang rank-nya mencukupi tingkat ini yang diberi tahu.
    for email in await qe.approver_emails(org, min_rank=int((snap or {}).get("required_rank") or 0)):
        await create_notification(
            user_email=email, org_id=org, type="sales", title="Persetujuan potongan reservasi (SPR)",
            body=(f"Unit {deal.get('unit_code')} · {deal.get('lead_name')}: potongan Rp "
                  f"{int(calc.get('total_discount_amount') or 0):,} — {reasons}").replace(",", "."),
            related_entity_type="deal", related_entity_id=deal["id"])


@router.post("/deals/{deal_id}/pricing-approval")
async def decide_pricing(deal_id: str, payload: DealPricingDecision,
                         user: dict = Depends(require_permission("pricing", "approve"))):
    """Manajer menyetujui/menolak potongan reservasi langsung (jalur SPR, bukan penawaran)."""
    from engine import create_notification
    d = await db.deals.find_one({"id": deal_id, "org_id": user.get("org_id", ORG_ID)}, {"_id": 0})
    if not d:
        raise HTTPException(status_code=404, detail="Deal tidak ditemukan")
    pa = d.get("pricing_approval") or {}
    if pa.get("state") != "pending":
        raise HTTPException(status_code=400, detail="Reservasi ini tidak sedang menunggu persetujuan potongan.")
    import discount_approval as da
    snap = pa.get("policy_snapshot")
    if da.is_tiered(snap):   # W1-B (#8): mode bertingkat — tanpa pengecualian pemohon + peran minimal tingkat
        try:
            da.check_decider(snap, role=user.get("role"), email=user.get("email"), requester=pa.get("requested_by"))
        except da.Forbidden as e:
            raise HTTPException(status_code=403, detail=str(e))
    elif pa.get("requested_by") == user.get("email") and user.get("role") not in ("owner", "super_admin"):
        raise HTTPException(status_code=403, detail="Pemohon tidak boleh menyetujui potongannya sendiri.")
    ts = now_iso()
    state = "approved" if payload.approve else "rejected"
    new_pa = {**pa, "state": state, "decided_by": user.get("email"), "decided_at": ts,
              "decision_reason": payload.reason.strip()}
    # H-B (P7): keputusan diambil SEKALI — setuju ‖ tolak / setuju ×2 dulu sama-sama 200 dan yang terakhir
    # menimpa; sekarang status "pending" yang tadi dibaca masuk ke filter, yang kalah mendapat 409.
    await transition("deals", {"id": deal_id, "org_id": d["org_id"]}, {"pricing_approval.state": "pending"},
                     {"$set": {"pricing_approval": new_pa, "updated_at": ts}},
                     what="Persetujuan potongan reservasi ini")
    await audit_log(user, "approve" if payload.approve else "reject", "deals", deal_id,
                    {"pricing_approval": state, "reason": payload.reason.strip()})
    await add_activity(entity_type="lead", entity_id=d["lead_id"], type="sales", actor=user.get("email"),
                       org_id=user.get("org_id", ORG_ID),
                       body=(f"Potongan reservasi unit {d.get('unit_code')} "
                             f"{'DISETUJUI' if payload.approve else 'DITOLAK'} — {payload.reason.strip()}"))
    if pa.get("requested_by"):
        await create_notification(
            user_email=pa["requested_by"], org_id=user.get("org_id", ORG_ID), type="sales",
            title=f"Potongan reservasi unit {d.get('unit_code')} {'disetujui' if payload.approve else 'ditolak'}",
            body=payload.reason.strip(), related_entity_type="deal", related_entity_id=deal_id)
    fresh = await db.deals.find_one({"id": deal_id, "org_id": d["org_id"]}, {"_id": 0})
    return {"data": serialize_doc(fresh),
            "message": f"Potongan {'disetujui' if payload.approve else 'ditolak'}."}


@router.get("/deals/{deal_id}/delete-check")
async def deal_delete_check(deal_id: str, user: dict = Depends(require_permission("deals", "view"))):
    import force_delete as fd
    d = await _get_deal_editable(deal_id, user)
    org = user.get("org_id", ORG_ID)
    fp = await fd.footprint(org, deal_id)
    can_force = fd.may_force(user)
    return {"data": {"can_delete": can_force, "can_force": can_force, "blockers": fp,
                     "note": "Hapus deal menghapus SELURUH transaksinya (AR, kuitansi, jurnal, booking fee, "
                             "biaya all-in, kontrak, komisi). Unit kembali tersedia." if can_force
                     else "Hanya Direksi/Super Admin yang boleh menghapus deal beserta transaksinya."}}


@router.delete("/deals/{deal_id}")
async def delete_deal(deal_id: str, reason: str = None,
                      user: dict = Depends(require_permission("deals", "update"))):
    """HAPUS PAKSA deal + seluruh turunannya (akses penuh + alasan). Unit kembali `available`."""
    import force_delete as fd
    d = await _get_deal_editable(deal_id, user)
    org = user.get("org_id", ORG_ID)
    if not fd.may_force(user):
        raise HTTPException(status_code=403, detail="Hapus deal beserta transaksinya hanya untuk Direksi/Super Admin.")
    if len((reason or "").strip()) < 10:
        raise HTTPException(status_code=400, detail="Hapus deal wajib alasan (minimal 10 huruf).")
    out = await fd.delete_deal_cascade(org, d, user.get("email"))
    await _bind_unit(org, d["unit_id"])
    await audit_log(user, "force_delete", "deals", deal_id,
                    {"reason": reason.strip(), "unit_code": d.get("unit_code"), "removed": out["removed"]})
    return {"data": out}


async def _get_deal_editable(deal_id: str, user: dict) -> dict:
    # AZ-01: lintas-organisasi = 404; baru sesudahnya cek kepemilikan sales.
    d = await get_in_org(db.deals, deal_id, user, name="Deal")
    if is_scoped_sales(user) and d.get("assigned_to") != user.get("email"):
        raise HTTPException(status_code=403, detail="Akses ditolak: bukan deal Anda")
    return d


@router.post("/deals/{deal_id}/book")
async def book_deal(deal_id: str, payload: DealAction,
                    user: dict = Depends(require_permission("deals", "update"))):
    d = await _get_deal_editable(deal_id, user)
    if d.get("status") != "reserved":
        raise HTTPException(status_code=400, detail=(
            f"Deal harus berstatus 'reserved' untuk di-booking — saat ini '{d.get('status')}'"
            + (" (sudah dikonfirmasi sebelumnya; muat ulang halaman)." if d.get("status") == "booked"
               else ". Muat ulang halaman untuk melihat status terbaru.")))
    org = user.get("org_id", ORG_ID)
    blocked_pa = pricing_approval_block(d)
    if blocked_pa:
        raise HTTPException(status_code=400, detail=blocked_pa)
    import booking_fee as bf
    blocked = await bf.block_booking_reason(org, d)
    if blocked:
        raise HTTPException(status_code=400, detail=blocked)
    ts = now_iso()
    # CAS: dua klik "Konfirmasi Booking" serentak hanya menghasilkan satu booking (satu event
    # deal.booked, satu jadwal AR, satu komisi); yang kedua mendapat 409.
    klaim = await db.deals.update_one({"id": deal_id, "org_id": org, "status": "reserved"}, {"$set": {
        "status": "booked", "booked_at": ts, "updated_at": ts,
        **await clock.patch_for("deal", "booked", org_id=org, at=ts)}})
    if klaim.matched_count != 1:
        from idempotency import Conflict
        raise Conflict("Reservasi ini baru saja dikonfirmasi/diubah oleh proses lain. Muat ulang halaman.")
    # FZ-05: `payment_status` unit = fungsi status AR yang SEBENARNYA (rumus sama dengan `_recalc_invoice`) —
    # dulu selalu "booking_fee" walau piutang sudah terbayar sebagian/penuh sebelum booking.
    inv = await db.ar_invoices.find_one({"org_id": org, "deal_id": deal_id, "status": {"$ne": "cancelled"}},
                                        {"_id": 0, "status": 1, "paid": 1})
    pay_status = "booking_fee"
    if inv:
        pay_status = ("paid_off" if inv.get("status") == "paid"
                      else ("partial" if int(inv.get("paid") or 0) > 0 else "booking_fee"))
    await db.units.update_one({"id": d["unit_id"], "org_id": org}, {"$set": {
        "status": "booked", "booked_by_deal": deal_id, "payment_status": pay_status, "updated_at": ts}})
    # Fase 31 (perbaikan cacat): ikatan unit → deal → lead → pembeli disimpan pada unit,
    # supaya progres pembangunan, portal pembeli, dan laporan tidak bergantung pencarian
    # berlapis yang mudah putus.
    await _bind_unit(org, d["unit_id"])
    # KT-29: tugas "Konfirmasi booking fee" selesai dengan sendirinya begitu booking dikonfirmasi.
    await db.tasks.update_many(
        {"org_id": org, "related_entity_type": "deal", "related_entity_id": deal_id,
         "source_event": f"deal.bookingfee:{deal_id}", "status": {"$in": ["open", "in_progress", "snoozed"]}},
        {"$set": {"status": "done", "completed_at": ts, "completed_by": user.get("email"),
                  "outcome": "Booking dikonfirmasi", "updated_at": ts}})
    await emit("deal.booked", "deal", deal_id, {"unit_id": d["unit_id"]}, org_id=org)
    await add_activity(entity_type="lead", entity_id=d["lead_id"], type="system",
                       body="Deal dikonfirmasi (booked).", actor=user.get("email"), org_id=org)
    await dispatch_pending()  # process deal.booked now -> generate AR schedule + commission (Finance)
    fresh = await db.deals.find_one({"id": deal_id, "org_id": org}, {"_id": 0})
    return {"data": serialize_doc(fresh)}


@router.get("/deals/{deal_id}/cancel-preview")
async def cancel_preview(deal_id: str, user: dict = Depends(require_permission("deals", "view"))):
    """Apa yang terjadi bila reservasi ini dibatalkan + siapa yang boleh (sales vs admin)."""
    import deal_cancel as dc
    d = await _get_deal_editable(deal_id, user)
    return {"data": await dc.preview(user.get("org_id", ORG_ID), d, user)}


@router.post("/deals/{deal_id}/cancel")
async def cancel_deal(deal_id: str, payload: DealCancelIn,
                      user: dict = Depends(require_permission("deals", "update"))):
    """Batalkan reservasi/booking SATU langkah (unit dilepas, tagihan ditutup, refund/hangus).
    Titipan biaya / invoice biaya terbuka wajib diakui (`acknowledge_costs` + `cost_note`) — FN-03."""
    import deal_cancel as dc
    from idempotency import Conflict
    d = await _get_deal_editable(deal_id, user)
    org = user.get("org_id", ORG_ID)
    try:
        out = await dc.cancel(org, d, user, reason=payload.reason.strip(),
                              refund_mode=payload.refund_mode, refund_amount=payload.refund_amount,
                              method=payload.method, note=payload.note,
                              acknowledge_costs=payload.acknowledge_costs, cost_note=payload.cost_note)
    except Conflict:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await audit_log(user, "cancel", "deals", deal_id,
                    {"reason": payload.reason.strip(), "refund_mode": out["refund_mode"],
                     "refund_deferred": out.get("refund_deferred"), "unit_code": d.get("unit_code"),
                     **({"cost_ack": out["cost_ack"]} if out.get("cost_ack") else {})})
    return {"data": serialize_doc(out["deal"]), "refund": serialize_doc(out["refund"]),
            "message": ("Reservasi dibatalkan — unit kembali tersedia. Refund booking fee menunggu "
                        "eksekusi Keuangan (kas keluar harus oleh pemegang izin Keuangan)."
                        if out.get("refund_deferred") else
                        "Reservasi dibatalkan — unit kembali tersedia.")}


# ----------------------------- Legal chain (EPIC 1.4): PPJB -> AJB -> sold -----------------------------
async def _deal_payment_summary(deal_id: str, org: str, price: int) -> dict:
    inv = await db.ar_invoices.find_one({"org_id": org, "deal_id": deal_id}, {"_id": 0})
    total = int(inv.get("total", price)) if inv else int(price or 0)
    paid = int(inv.get("paid", 0)) if inv else 0
    outstanding = int(inv.get("outstanding", total - paid)) if inv else total
    pct = round(paid / total * 100) if total > 0 else 0
    return {"price": int(price or 0), "total": total, "paid": paid,
            "outstanding": outstanding, "paid_pct": pct, "ar_status": (inv or {}).get("status")}


@router.get("/deals/{deal_id}/legal")
async def deal_legal(deal_id: str, user: dict = Depends(require_permission("deals", "view"))):
    d = await _get_deal_editable(deal_id, user)
    org = user.get("org_id", ORG_ID)
    unit = await db.units.find_one({"id": d.get("unit_id"), "org_id": org}, {"_id": 0, "code": 1, "status": 1}) or {}
    lead = await db.leads.find_one({"id": d.get("lead_id"), "org_id": org}, {"_id": 0, "name": 1}) or {}
    fin = await db.financing_apps.find_one({"org_id": org, "deal_id": deal_id}, {"_id": 0})
    payment = await _deal_payment_summary(deal_id, org, d.get("price", 0))
    return {"data": {
        "deal_id": deal_id, "status": d.get("status"), "legal_stage": d.get("legal_stage"),
        # Tahap legal DICATAT di kontrak pembeli (Kontrak & Legal); layar Deal hanya membaca.
        "contract_id": d.get("contract_id"), "customer_id": d.get("customer_id"),
        "unit_code": unit.get("code"), "unit_status": unit.get("status"), "lead_name": lead.get("name"),
        "reserved_at": d.get("reserved_at"), "booked_at": d.get("booked_at"),
        "ppjb": d.get("ppjb"), "ajb": d.get("ajb"), "sold_at": d.get("sold_at"),
        "payment": payment,
        "financing": ({"bank": fin.get("bank_name"), "status": fin.get("status"),
                       "plafon": fin.get("plafon"), "tenor": fin.get("tenor_months")} if fin else None),
    }}


async def _legal_via_contract(deal_id: str, stage: str, entry: dict, user: dict) -> dict:
    """PPJB/AJB lewat endpoint deal LAMA = PEMBUNGKUS TIPIS atas `contracts_engine.legal_advance`.

    Audit KT-01 (kritis): dulu `POST /deals/{id}/ppjb|ajb` cukup izin `deals:update`, menulis
    `deals.legal_stage` sendiri dan menjadikan unit SOLD hanya dengan booking fee — melewati
    gerbang DP/pelunasan/BAST/akad dan pemisahan tugas manajer jalur kontrak. Sekarang tidak
    ada lagi jalur legal kedua: izin = `contracts:manage` (sama dengan jalur kontrak), gerbang
    bukti = `legal_gates` yang sama, dan `deals.legal_stage/ppjb/ajb` hanyalah CERMIN yang
    ditulis `legal_advance` (satu sumber kebenaran: `contracts.legal`).
    """
    import contracts_engine as ce
    d = await _get_deal_editable(deal_id, user)
    org = user.get("org_id", ORG_ID)
    contract = await db.contracts.find_one({"org_id": org, "deal_id": deal_id}, {"_id": 0})
    if not contract:
        raise HTTPException(status_code=400, detail=(
            f"Deal ini belum menjadi pembeli, jadi belum ada kontrak untuk mencatat "
            f"{stage.upper()}. Klik 'Jadikan Pembeli' lebih dulu, lalu catat tahap legal di "
            "Kontrak & Legal pembeli (gerbang DP/pelunasan/BAST berlaku di sana)."))
    if contract.get("state") == "cancelled":
        raise HTTPException(status_code=400, detail="Kontrak deal ini sudah dibatalkan.")
    legal = contract.get("legal") or {}
    if stage == "ppjb" and (legal.get("ppjb") or d.get("legal_stage") in ("ppjb", "ajb")):
        raise HTTPException(status_code=400, detail="PPJB sudah ditandatangani untuk deal ini.")
    if stage == "ajb":
        if legal.get("ajb") or d.get("legal_stage") == "ajb":
            raise HTTPException(status_code=400, detail="AJB sudah ditandatangani untuk deal ini.")
        if not legal.get("ppjb"):
            raise HTTPException(status_code=400,
                                detail="AJB memerlukan PPJB yang sudah ditandatangani.")
    try:
        await ce.legal_advance(org, contract["id"], stage, entry, user.get("email"))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await audit_log(user, "update", "contract", contract["id"],
                    {"legal_stage": stage, "via": "deals_legacy_endpoint"})
    fresh = await db.deals.find_one({"id": deal_id, "org_id": org}, {"_id": 0})
    return {"data": serialize_doc(fresh)}


@router.post("/deals/{deal_id}/ppjb")
async def sign_ppjb(deal_id: str, payload: PpjbSign,
                    user: dict = Depends(require_permission("contracts", "manage"))):
    """PPJB — pembungkus jalur kontrak (`/contracts/{id}/legal/ppjb`): gerbang DP berlaku."""
    return await _legal_via_contract(deal_id, "ppjb", {
        k: v for k, v in {"number": payload.number, "date": payload.signed_date,
                          "note": payload.note}.items() if v}, user)


@router.post("/deals/{deal_id}/ajb")
async def sign_ajb(deal_id: str, payload: AjbSign,
                   user: dict = Depends(require_permission("contracts", "manage"))):
    """AJB — pembungkus jalur kontrak (`/contracts/{id}/legal/ajb`): pelunasan + BAST (tunai)
    atau akad kredit (KPR) wajib; hanya dengan itu unit menjadi SOLD."""
    return await _legal_via_contract(deal_id, "ajb", {
        k: v for k, v in {"number": payload.number, "date": payload.signed_date,
                          "notary": payload.notary, "note": payload.note}.items() if v}, user)
