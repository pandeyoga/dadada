"""Alat usulan (kind="propose"): TIDAK mengubah data; hanya membuat `ai_actions` berstatus pending untuk disetujui manusia."""
import re

from ai import actions
from ai.tools import internal_api as api
from ai.tools.registry import Tool, ToolContext, ToolError, register
from ai.tools.read_tools import _get, _obj

S = {"type": "string"}
_PHONE_OK = re.compile(r"^(?:\+?62|0)8\d{8,12}$")
STAGE_LABEL = {"acquisition": "Akuisisi", "nurturing": "Nurturing", "appointment": "Janji temu",
               "booking": "Booking", "won": "Menang", "lost": "Hilang", "recycle": "Daur ulang"}


def _result(a: dict, summary: str) -> dict:
    return {"action_id": a["id"], "status": "pending", "pesan": f"Menunggu persetujuan pengguna (id {a['id']}).",
            "summary": summary}


async def _lead(ctx, lead_id):
    return (await _get(ctx, f"/leads/{lead_id}")).get("data") or {}


def _lead_id(ctx: ToolContext, inp: dict) -> str:
    """WA: id dari model DIABAIKAN — usulan hanya untuk lead milik kontak ini."""
    if ctx.channel == "wa":
        own = (ctx.contact or {}).get("lead_id")
        if not own:
            raise ToolError("Nomor ini belum terhubung ke lead. Serahkan ke sales untuk ditindaklanjuti.")
        return own
    return inp["lead_id"]


def _wa_customer(ctx: ToolContext) -> str:
    own = (ctx.contact or {}).get("buyer_customer_id")
    if not (ctx.verified and own):
        raise ToolError("Komplain hanya bisa diusulkan untuk pembeli yang nomornya sudah terverifikasi.")
    return own


async def ubah_tahap_lead(ctx: ToolContext, inp: dict) -> dict:
    lead = await _lead(ctx, inp["lead_id"])
    cur, new = lead.get("stage"), inp["tahap_baru"]
    checks = []
    try:
        lc = (await _get(ctx, f"/leads/{inp['lead_id']}/lifecycle")).get("data") or {}
        if new not in (lc.get("manual_targets") or []) and new != lc.get("next_stage"):
            checks.append({"ok": False, "label": f"Transisi {cur} → {new} tidak lazim; aturan tahap akan memeriksa saat dijalankan"})
        if new == lc.get("next_stage"):
            checks.append({"ok": bool(lc.get("can_advance")), "label": "Bukti lengkap" if lc.get("can_advance")
                           else f"Bukti belum lengkap: {lc.get('blocked_reason')}"})
    except ToolError:
        pass
    if new in ("lost", "recycle") and not (inp.get("alasan") or "").strip():
        raise ToolError("Alasan wajib diisi untuk tahap Hilang/Daur ulang.")
    prev = {"title": f"Ubah tahap lead {lead.get('name')}",
            "changes": [f"Tahap: {STAGE_LABEL.get(cur, cur)} → {STAGE_LABEL.get(new, new)}", f"Alasan: {inp['alasan']}"],
            "checks": checks}
    a = await actions.create_pending(ctx, tool="ubah_tahap_lead", resource="leads", permission="update", method="POST",
                                     path=f"/leads/{inp['lead_id']}/stage", json={"stage": new, "note": inp["alasan"]},
                                     preview=prev, entity_id=inp["lead_id"])
    return _result(a, "Mengusulkan perubahan tahap lead")


async def jadwalkan_survei(ctx, inp):
    lead_id = _lead_id(ctx, inp)
    lead = await _lead(ctx, lead_id)
    body = {"lead_id": lead_id, "title": f"Survei: {lead.get('name')}", "scheduled_at": inp["waktu"],
            "type": "survey", "notes": inp.get("catatan")}
    checks = []
    if inp.get("petugas_id"):
        from db import db
        u = await db.users.find_one({"id": inp["petugas_id"], "org_id": ctx.org_id}, {"_id": 0, "email": 1, "name": 1})
        if not u:
            raise ToolError("Petugas tidak ditemukan.")
        body["participants"] = [u["email"]]
    checks.append({"ok": bool(re.match(r"^\d{4}-\d{2}-\d{2}", inp["waktu"])), "label": "Format waktu ISO valid"})
    prev = {"title": f"Jadwalkan survei untuk {lead.get('name')}",
            "changes": [f"Waktu: {inp['waktu']}"] + ([f"Petugas: {u['name']}"] if inp.get("petugas_id") else [])
            + ([f"Catatan: {inp['catatan']}"] if inp.get("catatan") else []), "checks": checks}
    a = await actions.create_pending(ctx, tool="jadwalkan_survei", resource="appointments", permission="create",
                                     method="POST", path="/appointments", json=body, preview=prev, entity_id=lead_id)
    return _result(a, "Mengusulkan jadwal survei")


async def catat_catatan_lead(ctx, inp):
    lead_id = _lead_id(ctx, inp)
    lead = await _lead(ctx, lead_id)
    prev = {"title": f"Catatan untuk {lead.get('name')}", "changes": [inp["catatan"]], "checks": []}
    a = await actions.create_pending(ctx, tool="catat_catatan_lead", resource="activities", permission="create",
                                     method="POST", path="/activities",
                                     json={"entity_type": "lead", "entity_id": lead_id, "body": inp["catatan"], "type": "comment"},
                                     preview=prev, entity_id=lead_id)
    return _result(a, "Mengusulkan catatan lead")


async def kirim_pesan_wa(ctx, inp):
    lead_id = inp.get("lead_id")
    if not lead_id and inp.get("telepon"):
        d = await _get(ctx, "/leads", {"q": inp["telepon"], "limit": 2})
        rows = d.get("data") or []
        if len(rows) != 1:
            raise ToolError("Lead dengan nomor itu tidak ditemukan atau ambigu; sebutkan lead_id.")
        lead_id = rows[0]["id"]
    if not lead_id:
        raise ToolError("lead_id atau telepon wajib diisi.")
    if not (inp.get("teks") or inp.get("template")):
        raise ToolError("Isi teks atau template.")
    lead = await _lead(ctx, lead_id)
    wa = (await _get(ctx, f"/leads/{lead_id}/wa")).get("data") or {}
    checks = [{"ok": bool(_PHONE_OK.match(re.sub(r"[\s-]", "", lead.get("phone") or ""))),
               "label": "No. HP valid" if _PHONE_OK.match(re.sub(r"[\s-]", "", lead.get("phone") or "")) else "No. HP belum valid"},
              {"ok": bool(wa.get("window_open") or inp.get("template")),
               "label": "Sesi 24 jam terbuka" if wa.get("window_open") else
               ("Memakai template (sesi 24 jam tertutup)" if inp.get("template") else "Sesi 24 jam tertutup: perlu template")}]
    body = {"body": inp.get("teks") or "", "template_code": inp.get("template")}
    prev = {"title": f"Kirim WhatsApp ke {lead.get('name')}",
            "changes": [f"Isi: {inp.get('teks') or '(template ' + inp['template'] + ')'}"], "checks": checks}
    # Dijalankan lewat gateway WA RESMI atas nama penyetuju (bukan endpoint simulasi `/leads/{id}/wa`).
    a = await actions.create_pending(ctx, tool="kirim_pesan_wa", resource="leads", permission="update", method="POST",
                                     path=f"/ai/inbox/leads/{lead_id}/wa", json=body, preview=prev, entity_id=lead_id)
    return _result(a, "Mengusulkan pesan WhatsApp")


async def buat_komplain_atau_balasan(ctx, inp):
    own = _wa_customer(ctx) if ctx.channel == "wa" else None
    if inp["mode"] == "balas":
        if not (inp.get("komplain_id") and inp.get("pesan")):
            raise ToolError("komplain_id dan pesan wajib untuk membalas.")
        c = (await _get(ctx, f"/complaints/{inp['komplain_id']}")).get("data") or {}
        if own and c.get("customer_id") != own:
            raise ToolError("Komplain ini bukan milik nomor yang terverifikasi.")
        body = {"message": inp["pesan"], "resolve": bool(inp.get("selesai"))}
        prev = {"title": f"Balas komplain: {c.get('subject')}",
                "changes": [f"Balasan: {inp['pesan']}"] + (["Tandai selesai"] if inp.get("selesai") else []), "checks": []}
        a = await actions.create_pending(ctx, tool="buat_komplain_atau_balasan", resource="complaints", permission="update",
                                         method="POST", path=f"/complaints/{inp['komplain_id']}/respond", json=body,
                                         preview=prev, entity_id=inp["komplain_id"])
    else:
        customer_id = own or inp.get("customer_id")
        if not (customer_id and inp.get("subjek") and inp.get("pesan")):
            raise ToolError("customer_id, subjek, dan pesan wajib untuk membuat komplain.")
        body = {"customer_id": customer_id, "subject": inp["subjek"], "message": inp["pesan"],
                "channel": "whatsapp"}
        prev = {"title": f"Catat komplain: {inp['subjek']}", "changes": [inp["pesan"]], "checks": []}
        a = await actions.create_pending(ctx, tool="buat_komplain_atau_balasan", resource="complaints", permission="create",
                                         method="POST", path="/complaints", json=body, preview=prev,
                                         entity_id=customer_id)
    return _result(a, "Mengusulkan komplain/balasan")


def register_all():
    R = register
    R(Tool("ubah_tahap_lead", "Usulkan perubahan tahap lead (aturan bukti tahap tetap berlaku saat dijalankan). Tidak langsung mengubah data; menunggu persetujuan pengguna.",
           _obj({"lead_id": S, "tahap_baru": S, "alasan": S}, ["lead_id", "tahap_baru", "alasan"]),
           "propose", "staff", ubah_tahap_lead, "Menyusun usulan tahap lead"))
    R(Tool("jadwalkan_survei", "Usulkan jadwal survei untuk lead. Menunggu persetujuan pengguna.",
           _obj({"lead_id": S, "waktu": S, "petugas_id": S, "catatan": S}, ["lead_id", "waktu"]),
           "propose", "any", jadwalkan_survei, "Menyusun usulan jadwal survei"))
    R(Tool("catat_catatan_lead", "Usulkan catatan pada lead. Menunggu persetujuan pengguna.",
           _obj({"lead_id": S, "catatan": S}, ["lead_id", "catatan"]),
           "propose", "any", catat_catatan_lead, "Menyusun usulan catatan"))
    R(Tool("kirim_pesan_wa", "Usulkan pesan WhatsApp ke lead (teks atau kode template). Menunggu persetujuan pengguna.",
           _obj({"lead_id": S, "telepon": S, "teks": S, "template": S}), "propose", "staff", kirim_pesan_wa, "Menyusun usulan pesan WA"))
    R(Tool("buat_komplain_atau_balasan", "Usulkan pencatatan komplain baru (mode 'buat') atau balasan komplain (mode 'balas'). Menunggu persetujuan pengguna.",
           _obj({"mode": {"type": "string", "enum": ["buat", "balas"]}, "customer_id": S, "subjek": S, "komplain_id": S,
                 "pesan": S, "selesai": {"type": "boolean"}}, ["mode"]),
           "propose", "any", buat_komplain_atau_balasan, "Menyusun usulan komplain"))
