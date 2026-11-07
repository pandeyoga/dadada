"""ctwa — atribusi iklan Click-to-WhatsApp (CTWA): tangkap `referral` dari pesan pertama.

Latar (audit 09 §4 celah 5): iklan CTWA mengirim objek `referral` (`ctwa_clid`, `source_id`, `source_url`,
`headline`, ...) HANYA pada pesan pertama setelah klik iklan. Dulu webhook membuangnya, sehingga biaya
iklan CTWA tidak pernah bisa dihubungkan ke penjualan dan Meta tidak diberi sinyal konversi.

Aturan di modul ini:
  * Disimpan di `conversations.attribution.ctwa` DAN `leads.attribution.ctwa` (bentuk yang sama).
  * PERTAMA MENANG, atomik: filter `attribution.ctwa $exists:false` — pesan/webhook ulang tidak menimpa
    dan tidak menggandakan (idempoten); klik iklan kedua tidak menggeser asal-usul lead.
  * Terikat pada (org, nomor telepon): referral dari nomor A tidak pernah menempel ke lead nomor B.
  * `ctwa_clid` divalidasi bentuknya (base64url-ish) — nilai sampah tidak disimpan/dikirim ke Meta.
  * Lead yang baru lahir SETELAH percakapan (auto-capture / "Kontak WA -> Lead") mewarisinya lewat
    `sync_to_lead`; `resolve` (dipakai CAPI) juga menelusuri percakapan sebagai cadangan.
"""
import logging
import re

from pymongo.errors import WriteError

from core_utils import now_iso
from db import db

logger = logging.getLogger("sipro.ctwa")

CLID_RE = re.compile(r"^[A-Za-z0-9_\-]{8,512}$")
TEXT_FIELDS = {"source_id": 128, "source_type": 32, "headline": 300, "body": 600, "media_type": 32}
URL_FIELDS = {"source_url": 2000}
MEDIA_KEYS = ("media_url", "image_url", "video_url", "thumbnail_url")


def _clip(v, n: int):
    return str(v).strip()[:n] if isinstance(v, (str, int)) and str(v).strip() else None


def normalize(referral) -> dict:
    """Objek `referral` Meta -> dict bersih (field dipetakan & dipotong), atau None bila tak berguna."""
    if not isinstance(referral, dict):
        return None
    clid = _clip(referral.get("ctwa_clid"), 512)
    out = {"ctwa_clid": clid if clid and CLID_RE.match(clid) else None}
    for k, n in TEXT_FIELDS.items():
        out[k] = _clip(referral.get(k), n)
    for k, n in URL_FIELDS.items():
        v = _clip(referral.get(k), n)
        out[k] = v if v and v.lower().startswith(("http://", "https://")) else None
    media = next((_clip(referral.get(k), 2000) for k in MEDIA_KEYS if referral.get(k)), None)
    out["media_url"] = media if media and media.lower().startswith(("http://", "https://")) else None
    wm = referral.get("welcome_message")
    out["welcome_text"] = _clip(wm.get("text"), 600) if isinstance(wm, dict) else None
    if not (out["ctwa_clid"] or out["source_id"] or out["source_url"]):
        return None
    return out


def build(referral: dict, *, waba_id: str = None, phone_number_id: str = None, wamid: str = None,
          at: str = None) -> dict:
    ref = normalize(referral)
    if not ref:
        return None
    ref.update({"waba_id": _clip(waba_id, 64), "phone_number_id": _clip(phone_number_id, 64),
                "wamid": _clip(wamid, 200), "captured_at": at or now_iso(), "received_at": now_iso()})
    return ref


async def _first_wins(coll: str, filt: dict, doc: dict) -> bool:
    """Set `attribution.ctwa` bila BELUM ada. True = baris ini yang menulis."""
    cond = {**filt, "attribution.ctwa": {"$exists": False}}
    try:
        res = await db[coll].update_one(cond, {"$set": {"attribution.ctwa": doc}})
    except WriteError:
        # `attribution` ada tetapi null/bukan objek (data lama): ganti dengan objek berisi ctwa saja.
        res = await db[coll].update_one({**filt, "attribution": None}, {"$set": {"attribution": {"ctwa": doc}}})
    return res.modified_count == 1


async def attach(org_id: str, *, conv_id: str, lead_id: str, doc: dict) -> dict:
    """Simpan atribusi pada percakapan + lead (bila ada). -> {conversation: bool, lead: bool} (True = baru ditulis)."""
    out = {"conversation": False, "lead": False}
    if not doc:
        return out
    if conv_id:
        out["conversation"] = await _first_wins("conversations", {"id": conv_id, "org_id": org_id}, doc)
    if lead_id:
        out["lead"] = await _first_wins("leads", {"id": lead_id, "org_id": org_id}, doc)
    return out


async def from_conversation(org_id: str, phone: str = None, lead_id: str = None) -> dict:
    """`attribution.ctwa` TERTUA dari percakapan WA milik nomor/lead ini (org yang sama), atau None."""
    q = {"org_id": org_id, "attribution.ctwa": {"$exists": True}}
    ors = []
    if phone:
        ors.append({"channel": "whatsapp", "contact_phone": phone})
    if lead_id:
        ors.append({"lead_id": lead_id})
    if not ors:
        return None
    conv = await db.conversations.find_one({**q, "$or": ors}, {"_id": 0, "attribution.ctwa": 1},
                                           sort=[("created_at", 1)])
    return ((conv or {}).get("attribution") or {}).get("ctwa")


async def sync_to_lead(org_id: str, lead_id: str, phone: str) -> bool:
    """Lead dibuat/ditautkan SESUDAH percakapan: warisi atribusi CTWA-nya (pertama menang). True = baru ditulis."""
    if not (lead_id and phone):
        return False
    doc = await from_conversation(org_id, phone=phone)
    if not doc:
        return False
    wrote = await _first_wins("leads", {"id": lead_id, "org_id": org_id}, doc)
    if wrote:
        from engine import add_activity
        await add_activity(entity_type="lead", entity_id=lead_id, type="system", org_id=org_id, actor="system",
                           body="Atribusi iklan Click-to-WhatsApp diwarisi dari percakapan "
                                f"(ad {doc.get('source_id') or '-'}).",
                           meta={"ctwa_source_id": doc.get("source_id")})
    return wrote


async def resolve(lead: dict, org_id: str) -> dict:
    """Atribusi CTWA untuk lead ini: `lead.attribution.ctwa`, kalau tidak ada -> percakapannya. Hanya yang
    punya `ctwa_clid` valid yang berguna bagi CAPI; selain itu None."""
    ctwa = ((lead or {}).get("attribution") or {}).get("ctwa")
    if not (ctwa or {}).get("ctwa_clid"):
        ctwa = await from_conversation(org_id, phone=(lead or {}).get("phone"), lead_id=(lead or {}).get("id"))
    return ctwa if (ctwa or {}).get("ctwa_clid") else None
