"""Ringkasan AI per lead (`ai_lead_insights`): yang diketahui, niat, keberatan, langkah berikutnya, saran skor.

Skor resmi tetap milik `lead_scoring`; di sini hanya SARAN (`suggested_score_delta`)."""
from core_utils import now_iso
from db import db

NEXT_STEP = {
    "stok_harga": ("Kirim daftar unit dan harga yang cocok, lalu tawarkan jadwal survei.", 5),
    "simulasi_kpr": ("Kirim simulasi KPR (perkiraan) dan tanyakan penghasilan serta rencana DP.", 5),
    "lokasi_fasilitas": ("Kirim lokasi dan fasilitas sekitar, ajak survei langsung.", 3),
    "jadwal_survei": ("Konfirmasi tanggal survei dan buat janji.", 10),
    "berkas_kpr": ("Kirim daftar berkas KPR dan bantu pengumpulannya.", 8),
    "tagihan_pembayaran": ("Verifikasi pembeli, lalu bantu informasi tagihan.", 0),
    "progres_serah_terima": ("Verifikasi pembeli, lalu kirim progres pembangunan.", 0),
    "komplain": ("Catat komplain dan teruskan ke tim layanan pelanggan.", -5),
    "sapaan_umum": ("Sapa dan gali kebutuhan: tipe unit, anggaran, rencana pembelian.", 1),
    "diskon_nego": ("Sales perlu menghubungi langsung untuk pembahasan harga.", 5),
    "janji_komitmen": ("Sales perlu menghubungi langsung; jangan menjanjikan lewat AI.", 3),
    "pembatalan_refund": ("Eskalasi ke manajer sales/keuangan.", -10),
    "lainnya_tidak_yakin": ("Sales perlu membaca pesan dan membalas langsung.", 0),
}
MAX_LIST = 8


def _merge(old: list, new: list) -> list:
    out = list(old or [])
    for x in new or []:
        if x and x not in out:
            out.append(x)
    return out[-MAX_LIST:]


async def update(org_id: str, lead_id: str, triage: dict, conversation: dict = None, *, simulated: bool = False) -> dict:
    """-> dokumen insight (tanpa _id); {} bila percakapan belum terkait lead.
    `simulated`: dibuat dari pemilah simulasi -> ditandai (UI menyebutnya data simulasi) dan tidak diwarisi giliran live."""
    if not lead_id:
        return {}
    lead = await db.leads.find_one({"id": lead_id, "org_id": org_id}, {"_id": 0}) or {}
    prev = await db.ai_lead_insights.find_one({"org_id": org_id, "lead_id": lead_id}, {"_id": 0}) or {}
    if prev.get("simulated") and not simulated:
        prev = {}  # niat/keberatan hasil simulasi tidak dibawa ke ringkasan live
    known = []
    if lead.get("interest_unit_type"):
        known.append(f"Minat tipe unit: {lead['interest_unit_type']}")
    if lead.get("source"):
        known.append(f"Sumber: {lead['source']}")
    cat = triage.get("category", "lainnya_tidak_yakin")
    step, delta = NEXT_STEP.get(cat, NEXT_STEP["lainnya_tidak_yakin"])
    if triage.get("sentiment") == "negatif":
        delta -= 3
    doc = {"org_id": org_id, "lead_id": lead_id, "conversation_id": (conversation or {}).get("id"),
           "known": _merge(prev.get("known"), known), "intent": triage.get("intent") or prev.get("intent") or "",
           "objections": _merge(prev.get("objections"), triage.get("objections")), "category": cat,
           "sentiment": triage.get("sentiment"), "next_step": step, "suggested_score_delta": delta,
           "simulated": simulated, "updated_at": now_iso()}
    await db.ai_lead_insights.update_one({"org_id": org_id, "lead_id": lead_id}, {"$set": doc}, upsert=True)
    return doc
