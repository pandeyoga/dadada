"""Gerbang BERSAMA penggantian skema pembayaran (docs/audit/12 keputusan #9 dan #14).

Semua jalur yang bisa mengganti skema sebuah deal/kontrak melewati fungsi gerbang di sini:
  * `POST /finance/ar/{deal}/schedule`            → `gate_schedule`
  * `POST /payment-schemes/contracts/{kontrak}`   → `payment_scheme_engine.set_for_contract` → `gate_money`
  * `POST /contracts/{kontrak}/scheme` (jenis)    → `contract_ops.set_scheme` → `gate_kind_change`

## #14 — ganti skema KE KPR sesudah kontrak dibuat (`contract.scheme_change_to_kpr`)
Skema KPR membawa komponen KPR-only (biaya bank/BANK_FEE, asuransi) dan porsi bank yang TIDAK ikut terbawa saat skema diganti.
`tolak_buat_baru` (bawaan) menolak dengan 400; `izinkan_manual` = perilaku lama; `hitung_ulang_dengan_persetujuan` membuat
AMANDEMEN skema all-in (selisih komponen ditampilkan) yang bila disetujui Keuangan menjalankan penggantian jenis.

## #9 — ganti skema SETELAH ada pembayaran nyata (`payment.scheme_change.allocation`)
Uang yang sudah masuk (kuitansi kas/KPR; booking fee/titipan tetap dialihkan sistem ke DP baru) tidak boleh diam-diam
terpasang ke termin yang salah. Penerapan skema baru DITAHAN (HTTP 202 + dokumen `scheme_change_requests`) sampai Keuangan
(`finance:approve`, alasan wajib, tercatat) memetakan tiap kuitansi ke termin baru (`manual_keuangan`) atau mengonfirmasi hasil
hitung sistem (`urut_termin_tertua`, `proporsional`). Ubah alokasi TIDAK mengubah kas/jurnal; kuitansi tetap utuh, alokasi lama
disimpan di `allocation_history`. Kebijakan yang berlaku direkam di permintaan saat ia lahir.
"""
import logging

import finance_engine as fin
import policy
import scheme_change_alloc as sca
from core_utils import new_id, now_iso
from db import db
from deal_money import deal_money
from deal_state import is_cancelled
from idempotency import mutex

logger = logging.getLogger("sipro.scheme_change")

KEY_ALLOC = "payment.scheme_change.allocation"
KEY_KPR = "contract.scheme_change_to_kpr"
MANUAL = "manual_keuangan"
OPEN = ("menunggu_pemetaan", "menunggu_konfirmasi")
MIN_ALASAN = 10


class Held(Exception):
    """Penerapan skema baru DITAHAN — `request` = dokumen permintaan (HTTP 202 di pemanggil)."""

    def __init__(self, request: dict, message: str = None):
        self.request = request
        self.message = message or held_message(request)
        super().__init__(self.message)


def _rp(v) -> str:
    return f"Rp {int(v or 0):,}".replace(",", ".")


def held_response(h: "Held"):
    """HTTP 202: perubahan DITAHAN (bukan gagal, bukan selesai) — badan memuat dokumen permintaan & petunjuk."""
    from fastapi.responses import JSONResponse

    from core_utils import serialize_doc
    return JSONResponse(status_code=202, content=serialize_doc({"held": True, "message": h.message, "data": h.request}))


def held_message(req: dict) -> str:
    if req.get("kind") == "amandemen_kpr":
        return ("Penggantian ke skema KPR DITAHAN: komponen KPR dihitung ulang dan menunggu persetujuan Keuangan "
                f"(amandemen skema biaya {req.get('amendment_id')}). Skema kontrak baru berubah setelah disetujui.")
    cara = ("Keuangan harus menyerahkan pemetaan alokasi tiap kuitansi ke termin baru"
            if req.get("mode") == MANUAL else "Sistem sudah menghitung pemetaan; Keuangan harus mengonfirmasinya")
    return (f"Sudah ada pembayaran {_rp(req.get('paid_total'))} pada deal ini, jadi skema baru TIDAK diterapkan dulu. {cara} "
            f"(permintaan {req.get('id')}). Jadwal dan kuitansi lama tetap berlaku sampai itu selesai.")


async def real_money(org: str, deal_id: str) -> int:
    """Uang NYATA yang sudah dialokasikan ke AR (kuitansi kas/KPR; pemakaian titipan/booking fee TIDAK dihitung)."""
    n = 0
    async for r in db.receipts.find({"org_id": org, "deal_id": deal_id, "funding": {"$ne": "deposit"},
                                     "status": {"$ne": "void"}, "applied": {"$gt": 0}}, {"_id": 0, "applied": 1}):
        n += int(r.get("applied") or 0)
    return n


# ------------------------------------------------------------------ #14 — ke KPR
def _tolak_msg(contract: dict) -> str:
    return (f"Kontrak {contract.get('number') or ''} sudah dibuat dengan skema {contract.get('scheme_label') or contract.get('scheme')}. "
            "Mengganti ke skema KPR TIDAK membawa komponen khusus KPR (biaya bank/BANK_FEE, asuransi, plafon bank) dan tidak "
            "menyusun porsi bank dengan benar, sehingga biaya KPR hilang dari tagihan. Yang harus dilakukan: batalkan "
            "deal/kontrak ini lewat Pembatalan, lalu buat reservasi baru dengan skema KPR dan konversikan menjadi kontrak baru "
            "(uang yang sudah masuk diurus lewat refund/titipan pembatalan). Pemilik dapat mengubah kebijakan ini di Pusat "
            "Konfigurasi › Kebijakan › 'Ganti skema kontrak ke KPR'.")


async def guard_to_kpr(org: str, *, deal: dict, contract: dict, target_kind: str, actor: str, reason: str, op: str) -> None:
    """Tolak/tahan/izinkan penggantian ke skema ber-KPR pada kontrak yang sudah ada (no-op bila bukan perubahan ke KPR)."""
    if target_kind != "kpr" or not contract or contract.get("scheme") == "kpr":
        return
    mode = await policy.resolve(KEY_KPR, org_id=org, project_id=(contract.get("project_id") or (deal or {}).get("project_id")))
    if mode == "izinkan_manual":
        return
    if mode == "tolak_buat_baru":
        raise ValueError(_tolak_msg(contract))
    # hitung_ulang_dengan_persetujuan
    if op != "contract_kind":
        raise ValueError("Kebijakan 'hitung ulang dengan persetujuan' hanya lewat penggantian JENIS skema kontrak "
                         "(POST /contracts/{id}/scheme dengan skema KPR) supaya komponen KPR dihitung ulang dan disetujui "
                         "Keuangan. Jalur ini tidak menghitung ulang komponen KPR.")
    import contract_ops
    await contract_ops.guard_kind_change(org, contract, "kpr")        # legal/SPR/uang nyata → ditolak sebelum amandemen lahir
    sid = (contract.get("costs") or {}).get("scheme_id")
    if not sid:
        raise ValueError("Kontrak ini memakai biaya manual/legacy tanpa skema all-in, jadi komponen KPR tidak bisa dihitung "
                         "ulang otomatis. Minta Keuangan memilih skema all-in lewat amandemen terlebih dulu, atau ubah "
                         "kebijakan ke 'izinkan manual'.")
    import allin_amend
    am = await allin_amend.request_amendment(org, contract, {
        "scheme_id": sid, "scheme_kind": "kpr", "then_scheme": "kpr",
        "reason": (reason or "").strip() or "Ganti skema kontrak ke KPR — komponen KPR dihitung ulang"}, {"email": actor})
    old = {c["code"]: int(c.get("amount") or 0) for c in (am.get("from") or {}).get("components") or []}
    new = {c["code"]: int(c.get("amount") or 0) for c in (am.get("to") or {}).get("components") or []}
    diff = [{"code": k, "dari": old.get(k, 0), "menjadi": new.get(k, 0), "selisih": new.get(k, 0) - old.get(k, 0)}
            for k in sorted(set(old) | set(new)) if old.get(k, 0) != new.get(k, 0)]
    raise Held({"id": am["id"], "kind": "amandemen_kpr", "amendment_id": am["id"], "status": "menunggu_persetujuan",
                "deal_id": contract.get("deal_id"), "diff": diff, "total_selisih": sum(d["selisih"] for d in diff)})


# ------------------------------------------------------------------ #9 — alokasi pembayaran
async def _build_preview(org: str, deal: dict, scheme: dict, contract: dict, op: str) -> list:
    """Jadwal baru persis seperti `create_ar_for_deal` menyusunnya (fungsi yang sama), tanpa menyimpan apa pun."""
    import ar_carry
    import settings_store as cfg
    price = int(deal.get("price", 0))
    base_date = await ar_carry.default_base_date(org, deal)
    comp = ((deal.get("pricing") or {}).get("by_target") or {})
    comp_amt = int(comp.get("dp") or 0) + int(comp.get("booking_fee") or 0)
    items = fin.apply_component_discounts(fin.compute_scheme_items(scheme, price + comp_amt, base_date), comp)
    kind = scheme.get("kind") or scheme.get("type")
    is_kpr = (kind == "kpr") if op == "contract_kind" else (kind == "kpr" or (contract or {}).get("scheme") == "kpr")
    items = fin.infer_bank_items(items, is_kpr)
    return items + fin.addon_items(deal, base_date, int(await cfg.get("addon.due_days", org_id=org) or 30))


async def gate_money(org: str, deal: dict, *, contract: dict, op: str, params: dict, target_scheme: dict,
                     actor: str, reason: str) -> None:
    """Bila deal punya uang nyata dan skema benar-benar berganti → buat permintaan pemetaan & lempar `Held`. Selain itu no-op."""
    inv = await db.ar_invoices.find_one({"org_id": org, "deal_id": deal["id"]}, {"_id": 0})
    if not inv or not target_scheme or inv.get("scheme_id") == target_scheme.get("id"):
        return
    if await real_money(org, deal["id"]) <= 0:
        return
    await _open_request(org, deal=deal, contract=contract, op=op, params=params, scheme=target_scheme, actor=actor, reason=reason)


async def gate_schedule(org: str, deal: dict, scheme_id: str, actor: str, reason: str = None) -> None:
    """Gerbang `POST /finance/ar/{deal}/schedule` (ValueError → 400, Held → 202)."""
    scheme = await db.payment_schemes.find_one({"id": scheme_id, "org_id": org}, {"_id": 0}) \
        or await fin.get_default_payment_scheme(org)
    if not scheme:
        return
    contract = await db.contracts.find_one({"org_id": org, "deal_id": deal["id"]}, {"_id": 0})
    await guard_to_kpr(org, deal=deal, contract=contract, target_kind=scheme.get("kind") or scheme.get("type"),
                       actor=actor, reason=reason, op="ar_schedule")
    await gate_money(org, deal, contract=contract, op="ar_schedule", params={"scheme_id": scheme["id"]},
                     target_scheme=scheme, actor=actor, reason=reason)


async def gate_kind_change(org: str, contract: dict, scheme: str, actor: str, reason: str = None,
                           to_kpr_ok: bool = False) -> None:
    """Gerbang `contract_ops.set_scheme` (ganti JENIS skema): #14 lebih dulu, lalu #9 bila ada uang nyata.
    `to_kpr_ok` = amandemen KPR sudah disetujui → tidak ada gerbang lagi (uang nyata tetap ditolak `guard_kind_change`)."""
    if to_kpr_ok:
        return
    deal = await db.deals.find_one({"id": contract.get("deal_id"), "org_id": org}, {"_id": 0}) or {}
    await guard_to_kpr(org, deal=deal, contract=contract, target_kind=scheme, actor=actor, reason=reason, op="contract_kind")
    if not deal or await real_money(org, deal["id"]) <= 0:
        return
    import contract_ops
    import payment_scheme_engine as psx
    from builtin_schemes import ensure_payment_scheme
    await contract_ops.guard_kind_change(org, contract, scheme, money_ok=True)   # legal/SPR/KPR berjalan → tetap ditolak
    sch = (await psx.resolve_for_contract(org, {"scheme": scheme, "project_id": contract.get("project_id")})).get("scheme") \
        or await ensure_payment_scheme(org, scheme)
    await gate_money(org, deal, contract=contract, op="contract_kind", params={"scheme": scheme},
                     target_scheme=sch, actor=actor, reason=reason)


async def _open_request(org: str, *, deal: dict, contract: dict, op: str, params: dict, scheme: dict, actor: str,
                        reason: str) -> None:
    """Buat permintaan pemetaan (atau pakai yang sudah terbuka untuk perubahan yang sama) lalu lempar `Held`."""
    if is_cancelled(deal) or deal.get("status") in ("cancelled", "expired"):
        raise ValueError("Deal ini sudah dibatalkan/kedaluwarsa — skema tidak bisa diganti.")
    async with mutex(f"scheme.change:{org}:{deal['id']}", wait=15, ttl=60, what="Penggantian skema deal ini"):
        ada = await db.scheme_change_requests.find_one({"org_id": org, "deal_id": deal["id"], "status": {"$in": list(OPEN)}},
                                                       {"_id": 0})
        if ada:
            if ada["op"] == op and ada.get("target_scheme_id") == scheme["id"]:
                raise Held(ada)
            raise ValueError(f"Sudah ada permintaan penggantian skema untuk deal ini yang menunggu Keuangan ({ada['id']}, ke "
                             f"skema '{ada.get('target_scheme_name')}'). Selesaikan atau batalkan dulu sebelum mengajukan yang lain.")
        inv = await db.ar_invoices.find_one({"org_id": org, "deal_id": deal["id"]}, {"_id": 0})
        liab = await db.contract_liabilities.find_one({"org_id": org, "deal_id": deal["id"]}, {"_id": 0, "recognized": 1})
        if (liab or {}).get("recognized"):
            raise ValueError("Pendapatan deal ini sudah diakui (BAST) — skema pembayaran tidak bisa diganti lagi.")
        receipts = await sca.mappable_receipts(org, deal["id"])
        sca.check_old_ar(inv, receipts)
        items = await _build_preview(org, deal, scheme, contract, op)
        mode = await policy.resolve(KEY_ALLOC, org_id=org, project_id=deal.get("project_id"))
        proposal = None
        if mode != MANUAL:
            proposal = sca.distribute(receipts, items, mode)
        ts = now_iso()
        doc = {
            "id": new_id(), "org_id": org, "deal_id": deal["id"], "contract_id": (contract or {}).get("id"),
            "unit_code": deal.get("unit_code"), "project_id": deal.get("project_id"),
            "op": op, "params": params, "target_scheme_id": scheme["id"], "target_scheme_name": scheme.get("name"),
            "mode": mode, "status": "menunggu_pemetaan" if mode == MANUAL else "menunggu_konfirmasi",
            "reason": (reason or "").strip() or None, "requested_by": actor, "requested_at": ts,
            "old_scheme_id": inv.get("scheme_id"), "old_scheme_name": inv.get("scheme_name"), "paid_total": int(inv.get("paid") or 0),
            "old_items": [{"id": i["id"], "label": i.get("label"), "amount": int(i.get("amount") or 0),
                           "paid_amount": int(i.get("paid_amount") or 0)} for i in inv.get("items") or []],
            "preview": sca.summarize(items), "schedule_hash": sca.schedule_hash(items),
            "receipts": [{"id": r["id"], "receipt_no": r.get("receipt_no"), "applied": int(r.get("applied") or 0),
                          "method": r.get("method"), "funding": r.get("funding"), "payer": sca.payer_of(r),
                          "created_at": r.get("created_at"), "allocations": r.get("allocations") or []} for r in receipts],
            "proposal": sca.to_api(proposal) if proposal is not None else None,
            "policy_snapshot": {"payment_scheme_change_allocation": {"value": mode}},
            "history": [{"at": ts, "by": actor, "action": "diajukan", "reason": (reason or "").strip() or None}],
            "created_at": ts, "updated_at": ts,
        }
        await db.scheme_change_requests.insert_one(dict(doc))
        doc.pop("_id", None)
    await fin.notify_finance(org, "Ganti skema menunggu pemetaan alokasi",
                             f"Unit {deal.get('unit_code') or '-'}: ke skema '{scheme.get('name')}', sudah dibayar {_rp(doc['paid_total'])}. "
                             + ("Serahkan pemetaan alokasi tiap kuitansi." if mode == MANUAL else "Konfirmasi pemetaan hasil hitung sistem."),
                             "approval", "scheme_change_request", doc["id"])
    raise Held(doc)


# ------------------------------------------------------------------ daftar / batal / terapkan
async def list_requests(org: str, deal_id: str = None, status: str = None) -> list:
    q = {"org_id": org}
    if deal_id:
        q["deal_id"] = deal_id
    if status:
        q["status"] = status
    return await db.scheme_change_requests.find(q, {"_id": 0}).sort("created_at", -1).to_list(200)


async def get_request(org: str, rid: str) -> dict:
    doc = await db.scheme_change_requests.find_one({"id": rid, "org_id": org}, {"_id": 0})
    if not doc:
        raise LookupError("Permintaan ganti skema tidak ditemukan.")
    return doc


async def cancel(org: str, rid: str, actor: str, reason: str) -> dict:
    if len((reason or "").strip()) < MIN_ALASAN:
        raise ValueError(f"Alasan pembatalan wajib (minimal {MIN_ALASAN} karakter).")
    req = await get_request(org, rid)
    if req["status"] not in OPEN:
        raise ValueError(f"Permintaan ini sudah berstatus '{req['status']}' — tidak bisa diubah lagi.")
    ts = now_iso()
    from idempotency import transition
    await transition("scheme_change_requests", {"id": rid, "org_id": org}, {"status": req["status"]}, {
        "$set": {"status": "dibatalkan", "updated_at": ts},
        "$push": {"history": {"at": ts, "by": actor, "action": "dibatalkan", "reason": reason.strip()}}},
        what="Permintaan ganti skema ini")
    return await get_request(org, rid)


async def apply(org: str, rid: str, user: dict, *, mapping=None, reason: str = None, confirm: bool = False) -> dict:
    """Keuangan menerapkan penggantian skema dengan pemetaan alokasi (manual) atau mengonfirmasi hitungan sistem."""
    actor = user.get("email")
    if len((reason or "").strip()) < MIN_ALASAN:
        raise ValueError(f"Alasan wajib diisi (minimal {MIN_ALASAN} karakter) — alasan dicatat pada permintaan dan kuitansi.")
    req = await get_request(org, rid)
    if req["status"] not in OPEN:
        raise ValueError(f"Permintaan ini sudah berstatus '{req['status']}' — tidak bisa diterapkan lagi.")
    async with mutex(f"scheme.change:{org}:{req['deal_id']}", wait=15, ttl=90, what="Penggantian skema deal ini"):
        req = await get_request(org, rid)
        if req["status"] not in OPEN:
            raise ValueError(f"Permintaan ini sudah berstatus '{req['status']}'.")
        deal = await db.deals.find_one({"id": req["deal_id"], "org_id": org}, {"_id": 0}) or {}
        if is_cancelled(deal) or deal.get("status") in ("cancelled", "expired"):
            raise ValueError("Deal ini sudah dibatalkan/kedaluwarsa — penggantian skema tidak bisa diterapkan.")
        if req["mode"] == MANUAL:
            if not mapping:
                raise ValueError("Mode 'manual oleh Keuangan': sertakan `mapping` (alokasi tiap kuitansi ke termin baru).")
            api_map = mapping
        else:
            if not confirm:
                raise ValueError("Pemetaan dihitung sistem — periksa pratinjau lalu konfirmasi (`confirm: true`).")
            if mapping and mapping != req["proposal"]:
                raise ValueError("Mode ini memakai hasil hitung sistem; mapping buatan sendiri tidak diterima. Ubah kebijakan "
                                 "ke 'manual oleh Keuangan' bila ingin memetakan sendiri.")
            api_map = req["proposal"]
        receipts = await sca.mappable_receipts(org, req["deal_id"])
        probe = [{"label": p["label"], "amount": p["amount"], "payer": p["payer"], "kpr_excluded": p.get("kpr_excluded"),
                  "due_date": p.get("due_date")} for p in req["preview"]]
        alloc = sca.normalize(api_map, receipts, probe)         # pesan galat jelas SEBELUM menyentuh AR
        approved = {"alloc": alloc, "schedule_hash": req["schedule_hash"], "request_id": rid, "by": actor,
                    "reason": reason.strip()}
        async with deal_money(org, req["deal_id"]):
            await _execute(org, req, deal, approved, actor, reason.strip())
        ts = now_iso()
        await db.scheme_change_requests.update_one({"id": rid}, {"$set": {
            "status": "diterapkan", "applied_by": actor, "applied_at": ts, "apply_reason": reason.strip(),
            "applied_mapping": sca.to_api(alloc), "updated_at": ts},
            "$push": {"history": {"at": ts, "by": actor, "action": "diterapkan", "reason": reason.strip()}}})
    return await get_request(org, rid)


async def _execute(org: str, req: dict, deal: dict, approved: dict, actor: str, reason: str) -> None:
    op, p = req["op"], req.get("params") or {}
    if op == "ar_schedule":
        await fin.create_ar_for_deal(deal, scheme_id=p["scheme_id"], org_id=org, replace=True, actor=actor, mapping=approved)
        import spr_compare
        await spr_compare.ensure_addendum(org, deal["id"], actor, "skema pembayaran diganti oleh Finance (alokasi dipetakan)")
    elif op == "contract_scheme_id":
        import payment_scheme_engine as psx
        contract = await db.contracts.find_one({"id": req["contract_id"], "org_id": org}, {"_id": 0})
        await psx.set_for_contract(org, contract, p["scheme_id"], actor, reason, approved=approved)
    elif op == "contract_kind":
        import contract_ops
        await contract_ops.set_scheme(org, req["contract_id"], p["scheme"], actor, reason, approved=approved)
    else:
        raise ValueError(f"Jenis operasi '{op}' tidak dikenal.")
