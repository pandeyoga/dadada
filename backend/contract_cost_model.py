"""MODEL BIAYA KONTRAK (W2-C, keputusan #6 / KT-03): bagaimana komponen biaya kontrak boleh dimasukkan — kunci
`contract.cost_model` (+ `contract.cost_free_input_needs_approval`), tingkat organisasi + proyek.

Jalur "input bebas" (nominal diketik orang, bukan dihitung dari master All-in) dan perilakunya per model:

  jalur                                              input_bebas_invoice            wajib_all_in                persetujuan
  ─────────────────────────────────────────────────  ─────────────────────────────  ──────────────────────────  ─────────────────────────
  POST /contracts/{id}/costs (bphtb, notary_fee,     langsung berlaku bila kunci    DITOLAK 400 (pakai          permohonan → disetujui
    bank_fee, insurance, pph_seller)                 persetujuan = false; bila true skema All-in/amandemen)    Keuangan (pemohon≠penyetuju)
                                                     (BAWAAN) → permohonan
  POST /contracts/{id}/costs (promo_discount,        langsung                       langsung                    permohonan (semua isian)
    plafon_kredit, dp_percent — bukan komponen)
  reservasi: costs_manual / costs bebas (Keuangan)   seperti dulu (finance:manage    DITOLAK 400                 seperti dulu
                                                     + alasan wajib)
  amandemen dengan komponen manual                   seperti dulu (finance:manage;  DITOLAK 400                 seperti dulu (amandemen
                                                     amandemen = persetujuan)                                   SUDAH alur persetujuan)

Persetujuan REUSE: amandemen All-in (`allin_amend`) sudah berupa pengajuan → keputusan pemegang `finance:approve` lain, jadi dipakai ulang
apa adanya untuk komponen manual. Alur baru (`contract_cost_requests`) hanya untuk isian kolom biaya kontrak (`POST /contracts/{id}/costs`)
yang selama ini berlaku seketika tanpa pemeriksa kedua; amandemen tidak cocok karena mengganti SELURUH snapshot dan butuh `finance:manage`.

"Input bebas + invoice": kontrak yang biayanya diketik bebas tidak punya snapshot komponen sehingga invoice biaya tak bisa terbit (KT-03,
dulu baru terbit setelah migrasi saat restart). `ensure_invoiceable` membangun snapshot LEGACY kontrak itu (pemetaan yang sama dengan
`allin_engine.migrate_legacy_contracts`) saat invoice diminta.
"""
import logging

import allin_engine as ae
import policy
from core_utils import new_id, now_iso
from db import db
from engine import add_activity, create_notification
from idempotency import Conflict, mutex, reserved

logger = logging.getLogger("sipro.costmodel")

KEY_MODEL = "contract.cost_model"
KEY_APPROVAL = "contract.cost_free_input_needs_approval"
INPUT_BEBAS, WAJIB_ALLIN, PERSETUJUAN = "input_bebas_invoice", "wajib_all_in", "persetujuan"
FREE_FIELDS = ("bphtb", "notary_fee", "bank_fee", "insurance", "pph_seller")        # komponen biaya yang diketik bebas
OTHER_FIELDS = ("promo_discount", "plafon_kredit", "dp_percent")                   # isian kontrak lain (bukan komponen)
LABEL = {"bphtb": "BPHTB", "notary_fee": "Biaya notaris / akad", "bank_fee": "Biaya bank", "insurance": "Asuransi",
         "pph_seller": "PPh penjual", "promo_discount": "Potongan harga", "plafon_kredit": "Plafon kredit",
         "dp_percent": "Persentase DP"}


def _rp(v) -> str:
    return f"Rp {int(v or 0):,}".replace(",", ".")


async def policy_of(org: str, project_id: str = None) -> dict:
    model = await policy.resolve(KEY_MODEL, org_id=org, project_id=project_id)
    needs = bool(await policy.resolve(KEY_APPROVAL, org_id=org, project_id=project_id))
    return {"model": model, "needs_approval": needs}


async def policy_snapshot(org: str, project_id: str = None) -> dict:
    return await policy.snapshot((KEY_MODEL, KEY_APPROVAL), org_id=org, project_id=project_id)


async def reject_if_all_in_only(org: str, project_id: str, what: str) -> None:
    """Model `wajib_all_in`: jalur input bebas (komponen manual saat reservasi / amandemen) ditolak dengan petunjuk."""
    if (await policy_of(org, project_id))["model"] == WAJIB_ALLIN:
        raise ValueError(f"Model biaya kontrak = 'Wajib skema All-in': {what} ditolak. Pilih skema All-in dari master "
                         "(biaya kontrak yang sudah ada diubah lewat amandemen skema).")


def held_response(doc: dict, message: str):
    """HTTP 202: isian DITAHAN menunggu persetujuan Keuangan (bukan gagal, bukan sudah berlaku)."""
    from fastapi.responses import JSONResponse

    from core_utils import serialize_doc
    return JSONResponse(status_code=202, content=serialize_doc({"held": True, "message": message, "data": doc}))


def _changes(costs: dict, payload: dict) -> list:
    out = []
    for k in (*FREE_FIELDS, *OTHER_FIELDS):
        if k in payload and payload[k] is not None:
            v = payload[k]
            out.append({"field": k, "label": LABEL[k], "dari": (costs or {}).get(k), "ke": None if v == -1 else v})
    return out


async def screen_set_costs(org: str, contract: dict, payload: dict, user: dict):
    """Penyaring `POST /contracts/{id}/costs` — kembalikan None (lanjut berlaku seperti biasa) atau dokumen permohonan (DITAHAN).
    ValueError → 400; LookupError → 409; Conflict → 409. Validasi isian dijalankan LEBIH DULU (isian tidak sah ditolak sekarang,
    bukan baru saat disetujui)."""
    import contracts_engine as ce
    payload = {k: v for k, v in payload.items() if v is not None}
    touched = [k for k in (*FREE_FIELDS, *OTHER_FIELDS) if k in payload]
    if not touched:
        return None
    pid = await _project_of(org, contract)
    pol = await policy_of(org, pid)
    free = [k for k in touched if k in FREE_FIELDS]
    if pol["model"] == WAJIB_ALLIN and free:
        raise ValueError("Model biaya kontrak = 'Wajib skema All-in': isian bebas "
                         f"({', '.join(LABEL[k] for k in free)}) ditolak. Pilih skema All-in dari master; perubahan biaya kontrak "
                         "yang sudah ada lewat amandemen skema (alasan + persetujuan Keuangan).")
    hold = (pol["model"] == PERSETUJUAN) or (pol["model"] == INPUT_BEBAS and pol["needs_approval"] and bool(free))
    if not hold:
        return None
    await ce.check_costs(org, contract, payload)
    return await _hold(org, contract, payload, user, pid, pol)


async def _project_of(org: str, contract: dict) -> str:
    import cost_limits
    return await cost_limits.project_of_contract(org, contract)


async def _hold(org: str, contract: dict, payload: dict, user: dict, project_id: str, pol: dict) -> dict:
    async with mutex(f"costreq:{org}:{contract['id']}", what="Permohonan biaya kontrak ini"):
        if await db.contract_cost_requests.find_one({"org_id": org, "contract_id": contract["id"], "status": "pending"}):
            raise Conflict("Masih ada permohonan isian biaya untuk kontrak ini yang menunggu keputusan Keuangan — "
                           "selesaikan atau batalkan dulu.")
        ts = now_iso()
        clean = {k: v for k, v in payload.items() if k in (*FREE_FIELDS, *OTHER_FIELDS)}
        doc = {"id": new_id(), "org_id": org, "contract_id": contract["id"], "contract_no": contract.get("number"),
               "deal_id": contract.get("deal_id"), "customer_id": contract.get("customer_id"), "project_id": project_id,
               "payload": clean, "changes": _changes(contract.get("costs"), clean), "note": (payload.get("note") or None),
               "status": "pending", "model": pol["model"], "needs_approval": pol["needs_approval"],
               "policy_snapshot": await policy_snapshot(org, project_id),
               "requested_by": user.get("email"), "requested_at": ts, "created_at": ts}
        await db.contract_cost_requests.insert_one(dict(doc))
    doc.pop("_id", None)
    import finance_engine as fe
    ringkas = ", ".join(f"{c['label']} {'dikosongkan' if c['ke'] is None else _rp(c['ke'])}" for c in doc["changes"])
    await fe.notify_finance(org, f"Isian biaya kontrak {contract.get('number')} menunggu persetujuan", ringkas,
                            ntype="approval", related_entity_type="contract_cost_request", related_entity_id=doc["id"])
    await add_activity(entity_type="customer", entity_id=contract.get("customer_id"), type="finance", actor=user.get("email"),
                       org_id=org, body=f"Isian biaya kontrak {contract.get('number')} diajukan, menunggu persetujuan Keuangan: {ringkas}.")
    return doc


def hold_message(doc: dict) -> str:
    return ("Isian biaya kontrak DITAHAN: belum berlaku sampai disetujui pemegang izin persetujuan Keuangan (orang lain dari "
            f"pemohon) — permohonan {doc['id']}. Angka lama tetap berlaku sementara ini.")


# ------------------------------------------------------------------ keputusan
async def list_for_contract(org: str, contract_id: str) -> list:
    return await db.contract_cost_requests.find({"org_id": org, "contract_id": contract_id}, {"_id": 0}).sort("created_at", -1).to_list(50)


async def list_pending(org: str) -> list:
    return await db.contract_cost_requests.find({"org_id": org, "status": "pending"}, {"_id": 0}).sort("created_at", -1).to_list(200)


async def decide(org: str, rid: str, approve: bool, note: str, user: dict) -> dict:
    """Setujui/tolak. Pemohon TIDAK boleh memutuskan permohonannya sendiri (tanpa pengecualian). Setuju → isian diterapkan lewat
    `contracts_engine.set_costs` (pemeriksaan yang sama, sebagai pemohon) dan jejaknya masuk `costs_history` kontrak."""
    import contracts_engine as ce
    req = await db.contract_cost_requests.find_one({"org_id": org, "id": rid}, {"_id": 0})
    if not req:
        raise LookupError("Permohonan tidak ditemukan.")
    if req["status"] != "pending":
        raise ValueError("Permohonan ini sudah diputuskan.")
    if req["requested_by"] == user.get("email"):
        raise PermissionError("Pemohon tidak boleh memutuskan permohonannya sendiri — minta pemegang izin persetujuan Keuangan lain.")
    if not approve and len((note or "").strip()) < 5:
        raise ValueError("Alasan penolakan wajib diisi (minimal 5 huruf).")
    ts = now_iso()
    status = "approved" if approve else "rejected"
    async with reserved("contract_cost_requests", {"id": rid, "org_id": org}, {"status": "pending"},
                        {"$set": {"status": status, "decided_by": user.get("email"), "decided_at": ts, "decision_note": note or ""}},
                        undo={"$set": {"status": "pending", "decided_by": None, "decided_at": None, "decision_note": None}},
                        what="Permohonan ini"):
        if approve:
            before = (await ce.get_raw(org, req["contract_id"])).get("costs") or {}
            try:
                c = await ce.set_costs(org, req["contract_id"], req["payload"], req["requested_by"])
            except LookupError as e:   # snapshot terkunci sejak permohonan diajukan → permohonan tetap pending, galat jelas
                raise ValueError(str(e))
            await db.contracts.update_one({"id": req["contract_id"]}, {"$push": {"costs_history": {
                "cost_request_id": rid, "at": ts, "by": user.get("email"), "requested_by": req["requested_by"],
                "from": {k: before.get(k) for k in req["payload"]}, "to": {k: (c.get("costs") or {}).get(k) for k in req["payload"]},
                "reason": req.get("note") or "isian bebas biaya kontrak disetujui"}}})
    await create_notification(user_email=req["requested_by"], org_id=org, type="finance",
                              title=f"Isian biaya kontrak {req.get('contract_no')} {'DISETUJUI' if approve else 'DITOLAK'}",
                              body=note or "", related_entity_type="contract_cost_request", related_entity_id=rid)
    await add_activity(entity_type="customer", entity_id=req.get("customer_id"), type="finance", actor=user.get("email"), org_id=org,
                       body=f"Isian biaya kontrak {req.get('contract_no')} {'DISETUJUI' if approve else 'DITOLAK'} oleh {user.get('email')}"
                            f"{' — ' + note if note else ''}.")
    return await db.contract_cost_requests.find_one({"id": rid}, {"_id": 0})


async def cancel(org: str, rid: str, user: dict) -> dict:
    req = await db.contract_cost_requests.find_one({"org_id": org, "id": rid}, {"_id": 0})
    if not req:
        raise LookupError("Permohonan tidak ditemukan.")
    if req["requested_by"] != user.get("email"):
        raise PermissionError("Hanya pemohon yang boleh membatalkan permohonannya.")
    async with reserved("contract_cost_requests", {"id": rid, "org_id": org}, {"status": "pending"},
                        {"$set": {"status": "cancelled", "decided_by": user.get("email"), "decided_at": now_iso()}},
                        undo={"$set": {"status": "pending", "decided_by": None, "decided_at": None}}, what="Permohonan ini"):
        pass
    return await db.contract_cost_requests.find_one({"id": rid}, {"_id": 0})


# ------------------------------------------------------------------ invoice untuk input bebas (KT-03)
async def ensure_invoiceable(org: str, contract: dict) -> dict:
    """Kontrak yang biayanya diisi bebas (kolom lama) belum punya `costs.components`, jadi invoice biaya tak bisa terbit. Bangun snapshot
    LEGACY dari kolomnya (pemetaan yang sama dengan `migrate_legacy_contracts`), lalu kembalikan kontrak segar. Model `wajib_all_in` tidak
    melakukannya (biaya bebas bukan sumber tagihan di model itu)."""
    costs = contract.get("costs") or {}
    if costs.get("components") is not None:
        return contract
    comps = ae.legacy_components(costs, contract.get("scheme"))
    if not comps:
        return contract
    if (await policy_of(org, await _project_of(org, contract)))["model"] == WAJIB_ALLIN:
        raise ValueError("Model biaya kontrak = 'Wajib skema All-in': biaya bebas bukan sumber tagihan. Pilih skema All-in lewat "
                         "amandemen skema, lalu terbitkan invoice biaya.")
    ts = now_iso()
    await db.contracts.update_one({"id": contract["id"], "costs.components": {"$exists": False}}, {"$set": {
        "costs.components": comps, "costs.scheme_code": "LEGACY", "costs.scheme_name": "Legacy (input bebas)", "costs.migrated_at": ts}})
    fresh = await db.contracts.find_one({"id": contract["id"]}, {"_id": 0})
    return fresh or contract
