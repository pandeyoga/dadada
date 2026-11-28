"""Aksi usulan AI (`ai_actions`): AI hanya mengusulkan; manusia menyetujui; eksekusi lewat API internal dengan token PENYETUJU."""
import logging

from core_utils import new_id, now_iso
from db import db
from rbac import audit_log, can

from ai.tools import internal_api

logger = logging.getLogger("estora.ai.actions")
# Bidang payload yang boleh diubah penyetuju per alat ("Ubah" di kartu persetujuan). Bidang lain (id lead, pelanggan,
# tujuan) tidak bisa diubah agar persetujuan tidak dapat diarahkan ke data lain.
EDITABLE = {"kirim_pesan_wa": ("body",), "catat_catatan_lead": ("body",), "jadwalkan_survei": ("scheduled_at", "notes"),
            "ubah_tahap_lead": ("note",), "buat_komplain_atau_balasan": ("message",)}


class ActionError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status, self.message = status, message


async def create_pending(ctx, *, tool: str, resource: str, permission: str, method: str, path: str, json: dict,
                         preview: dict, entity_id: str = None) -> dict:
    ts = now_iso()
    doc = {"id": new_id(), "org_id": ctx.org_id, "conversation_id": ctx.conversation_id, "tool": tool,
           "status": "pending", "resource": resource, "permission": permission, "entity_id": entity_id,
           "payload": {"method": method, "path": path, "json": json}, "preview": preview,
           "proposed_by": "ai", "on_behalf_of": (ctx.user or {}).get("email"), "channel": ctx.channel,
           "created_at": ts, "updated_at": ts, "result": None, "error": None}
    if ctx.channel == "portal":  # aksi pembeli: hanya pemiliknya (akun portal) yang bisa mengonfirmasi
        doc["owner_id"] = (ctx.user or {}).get("id")
    await db.ai_actions.insert_one(dict(doc))
    return doc


async def get(action_id: str) -> dict:
    a = await db.ai_actions.find_one({"id": action_id}, {"_id": 0})
    if not a:
        raise ActionError(404, "Aksi tidak ditemukan.")
    return a


async def list_for(org_id: str, *, status: str = None, conversation_id: str = None) -> list:
    q = {"org_id": org_id}
    if status:
        q["status"] = status
    if conversation_id:
        q["conversation_id"] = conversation_id
    return await db.ai_actions.find(q, {"_id": 0}).sort("created_at", -1).to_list(200)


async def approve(action_id: str, approver: dict, token: str, *, edits: dict = None) -> dict:
    a = await get(action_id)
    if a["org_id"] != approver.get("org_id") or a.get("channel") == "portal":  # aksi portal: hanya pembelinya
        raise ActionError(404, "Aksi tidak ditemukan.")
    if not await can(approver.get("role"), a["resource"], a["permission"]):
        raise ActionError(403, f"Anda tidak punya izin '{a['permission']}' pada '{a['resource']}' untuk menyetujui aksi ini.")
    setter = {"status": "executing", "approved_by": approver.get("email"), "approved_at": now_iso(),
              "updated_at": now_iso()}
    if edits:
        allowed = EDITABLE.get(a["tool"], ())
        bad = [k for k in edits if k not in allowed or not isinstance(edits[k], str)]
        if bad:
            raise ActionError(400, f"Bidang tidak dapat diubah: {', '.join(bad)}.")
        for k, v in edits.items():
            setter[f"payload.json.{k}"] = v
        setter["edited"] = True
    claimed = await db.ai_actions.find_one_and_update(
        {"id": action_id, "status": "pending"}, {"$set": setter}, projection={"_id": 0}, return_document=True)
    if claimed is None:
        raise ActionError(409, "Aksi ini sudah diproses.")
    p = claimed["payload"]
    meta = {"actor_type": "ai", "on_behalf_of": claimed.get("on_behalf_of"), "approved_by": approver.get("email"),
            "action_id": action_id, "tool": claimed["tool"], "conversation_id": claimed.get("conversation_id")}
    try:
        status, data = await internal_api.call(token, p["method"], p["path"], json=p.get("json"))
    except Exception as e:  # noqa: BLE001
        status, data = 599, {"detail": f"{type(e).__name__}: {e}"}
    ok = 200 <= status < 300
    fin = {"status": "executed" if ok else "failed", "updated_at": now_iso(), "executed_at": now_iso(),
           "result": data if ok else None, "error": None if ok else internal_api.error_detail(data)}
    await db.ai_actions.update_one({"id": action_id}, {"$set": fin})
    await audit_log(approver, "ai_action_executed" if ok else "ai_action_failed", claimed["resource"],
                    claimed.get("entity_id"), {**meta, "http_status": status})
    return await get(action_id)


async def reject(action_id: str, user: dict, reason: str = None) -> dict:
    a = await get(action_id)
    if a["org_id"] != user.get("org_id") or a.get("channel") == "portal":
        raise ActionError(404, "Aksi tidak ditemukan.")
    if user.get("email") != a.get("on_behalf_of") and not await can(user.get("role"), a["resource"], a["permission"]):
        raise ActionError(403, "Anda tidak berhak menolak aksi ini.")
    res = await db.ai_actions.find_one_and_update(
        {"id": action_id, "status": "pending"},
        {"$set": {"status": "rejected", "rejected_by": user.get("email"), "reject_reason": reason,
                  "updated_at": now_iso()}}, projection={"_id": 0}, return_document=True)
    if res is None:
        raise ActionError(409, "Aksi ini sudah diproses.")
    await audit_log(user, "ai_action_rejected", a["resource"], a.get("entity_id"),
                    {"actor_type": "ai", "on_behalf_of": a.get("on_behalf_of"), "rejected_by": user.get("email"),
                     "action_id": action_id, "reason": reason})
    return await get(action_id)


# ---------------------------------------------------------------- aksi pembeli (kanal portal)
def _buyer_label(pu: dict) -> str:
    return pu.get("email") or pu.get("phone") or f"portal:{pu.get('id')}"


async def _buyer_action(action_id: str, pu: dict) -> dict:
    """Aksi milik pembeli ini. Bukan miliknya / bukan kanal portal -> 404 (tidak membocorkan keberadaan)."""
    a = await db.ai_actions.find_one({"id": action_id}, {"_id": 0})
    if not a or a.get("channel") != "portal" or not pu.get("id") or a.get("owner_id") != pu["id"] \
            or a.get("org_id") != pu.get("org_id", a.get("org_id")):
        raise ActionError(404, "Aksi tidak ditemukan.")
    return a


def _done_summary(a: dict, data) -> str:
    msg = data.get("message") if isinstance(data, dict) else None
    if msg:
        return str(msg)
    title = (a.get("preview") or {}).get("subject") or (a.get("payload") or {}).get("json", {}).get("subject")
    return f"Komplain terkirim: {title}. Tim kami akan menindaklanjuti." if title else "Terkirim."


async def confirm_by_buyer(action_id: str, portal_user: dict, token: str) -> dict:
    """Pembeli menekan "Kirim" pada kartu: klaim atomik pending -> executing (tepat sekali), lalu panggil endpoint
    portal dengan TOKEN PEMBELI itu sendiri. Panggilan sukses tetapi pencatatan gagal -> tetap `executed` + catatan."""
    pu = portal_user
    await _buyer_action(action_id, pu)
    ts = now_iso()
    claimed = await db.ai_actions.find_one_and_update(
        {"id": action_id, "status": "pending", "channel": "portal", "owner_id": pu["id"]},
        {"$set": {"status": "executing", "approved_by": _buyer_label(pu), "approved_at": ts, "updated_at": ts}},
        projection={"_id": 0}, return_document=True)
    if claimed is None:
        raise ActionError(409, "Aksi ini sudah diproses.")
    p = claimed["payload"]
    try:
        status, data = await internal_api.call(token, p["method"], p["path"], json=p.get("json"))
    except Exception as e:  # noqa: BLE001
        status, data = 599, {"detail": f"{type(e).__name__}: {e}"}
    ok = 200 <= status < 300
    fin = {"status": "executed" if ok else "failed", "updated_at": now_iso(), "executed_at": now_iso(),
           "executed_by": pu["id"], "result": data if ok else None,
           "summary": _done_summary(claimed, data) if ok else None,
           "error": None if ok else internal_api.error_detail(data)}
    try:
        await db.ai_actions.update_one({"id": action_id}, {"$set": fin})
    except Exception:  # noqa: BLE001 — jangan pernah mengulang panggilan yang sudah berhasil
        logger.exception("Pencatatan aksi pembeli %s gagal", action_id)
        await db.ai_actions.update_one({"id": action_id}, {"$set": {
            "status": fin["status"], "executed_by": pu["id"], "updated_at": now_iso(),
            "note": "Panggilan selesai tetapi pencatatan hasil gagal; tidak diulang."}})
    actor = {"org_id": claimed["org_id"], "email": _buyer_label(pu), "role": "portal_buyer"}
    await audit_log(actor, "ai_action_executed" if ok else "ai_action_failed", claimed["resource"],
                    claimed.get("entity_id"),
                    {"actor_type": "ai", "on_behalf_of": claimed.get("on_behalf_of"), "approved_by": _buyer_label(pu),
                     "portal_user_id": pu["id"], "action_id": action_id, "tool": claimed["tool"],
                     "conversation_id": claimed.get("conversation_id"), "http_status": status})
    return await get(action_id)


async def cancel_by_buyer(action_id: str, portal_user: dict) -> dict:
    pu = portal_user
    await _buyer_action(action_id, pu)
    res = await db.ai_actions.find_one_and_update(
        {"id": action_id, "status": "pending", "channel": "portal", "owner_id": pu["id"]},
        {"$set": {"status": "cancelled", "rejected_by": _buyer_label(pu), "summary": "Dibatalkan oleh pembeli.",
                  "updated_at": now_iso()}}, projection={"_id": 0}, return_document=True)
    if res is None:
        raise ActionError(409, "Aksi ini sudah diproses.")
    return res
