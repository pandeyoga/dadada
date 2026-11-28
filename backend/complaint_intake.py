"""Jalur pembuatan komplain pembeli (diekstrak dari `routers/portal_router.py`, batas 800 baris).

Dipakai dua pintu dengan perilaku yang sama: `POST /api/portal/complaints` (pembeli sendiri, termasuk
kartu konfirmasi Tanya Estora) dan tiket serah-ke-CS dari chat portal (`ai.portal_handoff`) yang
menimpa tenggat/penugasan dan tidak mengirim WA ke pembeli.
"""
from core_utils import due_in, new_id, now_iso
from db import db, ORG_ID
from engine import auto_create_task, create_notification
from notifications import send_whatsapp

CHAT_KIND = "pertanyaan_chat"  # tiket dari chat portal: dipisah dari statistik & eskalasi komplain
_FROM_DEAL = object()  # penanda default: penanggung jawab = sales pemegang unit (deal.assigned_to)


async def buyer_customer(pu: dict) -> dict:
    """Pelanggan milik akun portal — atau LEAD pemegang reservasi (booking fee, Fase 69B)."""
    cust = await db.customers.find_one({"id": pu.get("customer_id")}, {"_id": 0}) if pu.get("customer_id") else None
    if cust: return cust  # noqa: E701
    lead = await db.leads.find_one({"id": pu.get("lead_id")}, {"_id": 0}) if pu.get("lead_id") else None
    return ({"id": lead["id"], "lead_id": lead["id"], "name": lead.get("name"), "is_lead": True,
             "phone": lead.get("phone"), "email": lead.get("email")} if lead else {})


async def buyer_deals(pu: dict, customer: dict) -> list:
    org = pu.get("org_id", ORG_ID)
    lead_id = customer.get("lead_id") or pu.get("lead_id")
    if not lead_id:
        return []
    return await db.deals.find({"org_id": org, "lead_id": lead_id}, {"_id": 0}).sort("created_at", -1).to_list(50)


async def create_complaint(*, org_id: str, portal_user: dict, deal: dict = None, category: str, subject: str,
                           message: str, priority: str = "medium", sla_hours: int = 48, assigned_to=_FROM_DEAL,
                           extra: dict = None, notify_buyer_wa: bool = True) -> dict:
    """Buat dokumen komplain + tugas SM-09 + notifikasi staf + (opsional) WA konfirmasi ke pembeli."""
    pu = portal_user
    unit_code, unit_id = None, None
    if deal:
        unit = await db.units.find_one({"id": deal.get("unit_id")}, {"_id": 0}) or {}
        unit_code = unit.get("code")
        # Fase 50A: komplain dulu hanya menyimpan KODE unit, bukan id-nya. Akibatnya tidak
        # ada satu pun jalan otomatis dari keluhan pembeli ke rumahnya (dan ke masa
        # garansinya) — CS harus mencari sendiri kavlingnya. Sekarang id-nya ikut disimpan.
        unit_id = unit.get("id") or deal.get("unit_id")
    ts = now_iso()
    cid = new_id()
    sla = due_in(hours=sla_hours)
    assignee = (deal or {}).get("assigned_to") if assigned_to is _FROM_DEAL else assigned_to
    doc = {
        "id": cid, "org_id": org_id, "customer_id": pu.get("customer_id"),
        "customer_name": pu.get("name"), "deal_id": deal["id"] if deal else None,
        "unit_code": unit_code, "unit_id": unit_id,
        "category": category or "umum",
        "subject": subject, "message": message,
        "status": "open", "priority": priority or "medium",
        "assigned_to": assignee,
        "sla_due_at": sla, "responses": [], "created_at": ts, "updated_at": ts,
    }
    doc.update({k: v for k, v in (extra or {}).items() if k not in doc})
    await db.complaints.insert_one(dict(doc))
    chat = doc.get("kind") == CHAT_KIND
    # SLA task for the responsible sales/CS + notification.
    task = await auto_create_task(
        source_event=f"complaint:{cid}",
        title=f"{'Pertanyaan pembeli dari chat' if chat else 'Komplain pembeli'}: {subject}",
        jobdesk_code="SM-09",
        type="complaint", related_entity_type="complaint", related_entity_id=cid,
        assigned_to=assignee, sla_due_at=sla, priority=doc["priority"],
        description=f"{pu.get('name')} ({unit_code or '-'}): {message}", org_id=org_id)
    if task and doc.get("kind"):  # eskalasi SLA tugas (engine_sweepers) mengecualikan tiket chat
        await db.tasks.update_one({"id": task["id"]}, {"$set": {"complaint_kind": doc["kind"]}})
    if assignee:
        await create_notification(user_email=assignee,
                                  title="Pertanyaan pembeli dari chat" if chat else "Komplain pembeli baru",
                                  body=f"{pu.get('name')}: {subject}", type="complaint", org_id=org_id,
                                  **({"related_entity_type": "complaint", "related_entity_id": cid} if chat else {}))
    if notify_buyer_wa:
        sla_txt = "2x24 jam" if sla_hours == 48 else f"{sla_hours} jam"
        await send_whatsapp(pu.get("phone"),
                            f"Terima kasih. Komplain Anda '{subject}' telah kami terima dan akan ditindaklanjuti (SLA {sla_txt}).")
    doc.pop("_id", None)
    return doc
