"""Webhooks (SIMULATION-first) for omnichannel lead capture.

Public endpoints (no auth) that accept sample payloads from multiple providers:
Meta Lead Ads, WhatsApp, Google Lead Form, TikTok Lead, a generic Web form, dan — sejak
Fase 43 — MITRA (token per mitra). Ads attribution (campaign/campaign_id/adset/ad/creative/
form + utm/fbclid/gclid) dibawa sampai ke lead + lead_capture_event. Saat kredensial nyata
tersedia, cukup set `channel_accounts.mode='live'` — kontrak capture-nya tidak berubah.

Fase 30c — TIDAK ADA LEAD YANG HILANG LAGI. Dulu payload cacat (JSON rusak, nomor HP
kosong, field salah nama) dibalas 422 dan menguap: uang iklan terbayar tetapi lead tidak
pernah masuk CRM dan tidak ada jejaknya. Sekarang setiap kegagalan disimpan di antrean
`lead_capture_failures`, memicu event `capture.failed` (tugas DM-02 + notifikasi
supervisor), dan bisa diperbaiki lalu diulang dari halaman Automasi & Channel.

Fase 43 — webhook MITRA (`docs/v2/25_PARTNER_SPEC.md` §4). Dua hal yang membuatnya berbeda
dari kanal lain dan karena itu ditulis eksplisit:
  1. Nomor telepon lead UNIK per organisasi (index `uq_leads_phone`). Jadi mitra kedua yang
     mengklaim nomor yang sudah ada TIDAK boleh membuat lead kedua — klaimnya dicatat lewat
     mesin atribusi mitra (`partner_engine.attribute`) yang memutuskan pemenangnya sesuai
     model (first/last touch) dan menyimpan SENGKETA bila perlu. Dulu tidak ada pintu masuk
     resmi untuk lead mitra sama sekali; atribusi bergantung pada ingatan orang.
  2. Mitra yang kontraknya habis / ditangguhkan DITOLAK dengan alasan — bukan diterima
     diam-diam lalu memunculkan tagihan fee yang tidak boleh ada.

KEAMANAN (`webhook_security.py`): Meta/WhatsApp (X-Hub-Signature-256 atas BADAN MENTAH), Google
(`google_key`) dan TikTok (TikTok-Signature / rahasia bersama) diverifikasi bila rahasianya sudah
dikonfigurasi — salah/tidak ada = 401/403 seragam tanpa merinci penyebab dan tanpa masuk antrean
gagal-masuk. Belum dikonfigurasi = tetap diterima (simulasi) + peringatan di `GET /webhooks/status`.
Badan dibatasi 1 MB (413); JSON patologis dijawab 400 bersih (bukan 500); id peristiwa dikunci
atomik (replay/pengiriman ulang = 200 `duplicate`).
"""
import asyncio
import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, ValidationError

import capture_failures as cf
import partner_engine as pengine
import rate_limit
import wa_gateway as gw
import wa_inbound as wi
import webhook_security as ws
from core_utils import new_id, now_iso, today_iso_date
from db import db, ORG_ID
from engine import process_lead_capture
from models import WebhookLead
from rbac import audit_log, require_permission

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


class SecretsIn(BaseModel):
    secret: Optional[str] = None         # app secret (Meta) / google_key / rahasia TikTok; "__clear__" = hapus
    verify_token: Optional[str] = None   # hanya Meta; "__clear__" = hapus


def _failed(provider: str, failure: dict, reason: str) -> JSONResponse:
    """202: kami MENERIMA panggilan provider, tetapi leadnya tertahan (bukan hilang)."""
    return JSONResponse(status_code=202, content={"data": {
        "captured": False, "lead_id": None, "duplicate": False,
        "failure_id": failure["id"], "reason": reason,
        "queued": "Antrean lead gagal masuk (Automasi & Channel → Gagal Masuk)",
        "mode": "simulation", "provider": provider}})


def _replayed(provider: str) -> dict:
    """200 untuk pengiriman ulang/replay: sudah diterima sebelumnya, tidak diproses lagi (idempoten)."""
    return {"data": {"lead_id": None, "duplicate": True, "captured": False, "replay": True,
                     "mode": "simulation", "provider": provider}}


async def _parse(provider: str, raw: bytes, defaults: dict = None, parsed: tuple = None):
    """-> (payload bersih, JSONResponse kegagalan). Satu pintu validasi semua provider. `raw` = BADAN
    MENTAH yang sudah dibaca/diautentikasi (tidak dibaca ulang dari request); `parsed` = hasil
    `ws.parse_json(raw)` bila pemanggil sudah mem-parse-nya."""
    data_raw, parse_err, fatal = parsed or ws.parse_json(raw)
    if fatal:
        return None, JSONResponse(status_code=400, content={"detail": parse_err})
    if parse_err:
        failure = await cf.record(provider, data_raw or {}, parse_err, kind=cf.KIND_DATA,
                                  org_id=ORG_ID)
        return None, _failed(provider, failure, parse_err)
    data_raw.pop("google_key", None)   # rahasia kiriman provider: tidak boleh sampai lead/antrean/log
    try:
        data = WebhookLead(**data_raw).model_dump()
    except ValidationError as e:
        first = (e.errors() or [{}])[0]
        loc = ".".join(str(x) for x in (first.get("loc") or []))
        reason = f"Payload tidak sesuai kontrak pada '{loc or 'payload'}': {first.get('msg')}"
        failure = await cf.record(provider, data_raw, reason, kind=cf.KIND_DATA, org_id=ORG_ID)
        return None, _failed(provider, failure, reason)
    data.setdefault("source", provider)
    for key, value in (defaults or {}).items():
        data[key] = value
    clean, err = cf.validate(data)
    if err:
        failure = await cf.record(provider, data, err, kind=cf.KIND_DATA, org_id=ORG_ID)
        return None, _failed(provider, failure, err)
    return clean, None


async def _is_replay(provider: str, obj, verdict) -> bool:
    """Klaim atomik id peristiwa (leadgen_id/lead_id/event_id) + tanda tangan bercap waktu (TikTok).
    True = SUDAH pernah diterima -> jangan diproses lagi."""
    ids = ws.event_ids_for(obj)
    fresh = [i for i in ids if await ws.claim_event(provider, i)]
    if ids and not fresh:
        return True
    if verdict.replay_key and not await ws.claim_event(provider + "_sig", verdict.replay_key,
                                                       ttl=2 * ws.REPLAY_TOLERANCE):
        return True
    return False


async def _capture(provider: str, request: Request, defaults: dict = None, channel: str = None):
    """Satu pintu untuk semua provider: baca (batas ukuran) -> autentikasi -> dedup id -> parse -> validasi
    -> proses (atau antrekan). `channel` = kunci kebijakan di `webhook_security.CHANNELS`
    (None = kanal publik tanpa tanda tangan: formulir web)."""
    raw, too_big = await ws.read_body(request)   # badan mentah dibaca SEKALI (setara `await request.body()`)
    if too_big:
        return too_big
    parsed = ws.parse_json(raw)
    if channel:
        verdict = await ws.authorize(channel, request, raw, parsed[0])
        if not verdict.ok:
            return ws.rejection(channel, request)
        if await _is_replay(provider, parsed[0], verdict):
            return _replayed(provider)
    clean, failed = await _parse(provider, raw, defaults, parsed)
    if failed:
        return failed
    try:
        lead_id, duplicate = await process_lead_capture(provider, clean, org_id=ORG_ID)
    except Exception as e:  # noqa: BLE001 - gangguan sementara: layak dicoba ulang otomatis
        reason = f"Gangguan saat memproses lead: {e}"
        failure = await cf.record(provider, clean, reason, kind=cf.KIND_TRANSIENT,
                                  org_id=ORG_ID)
        return _failed(provider, failure, reason)
    return {"data": {"lead_id": lead_id, "duplicate": duplicate, "captured": True,
                     "mode": "simulation", "provider": provider}}


@router.get("/status")
async def webhook_status(user: dict = Depends(require_permission("settings", "view"))):
    """Kanal webhook mana yang sudah/belum aman (tanda tangan wajib) + peringatan. Nilai rahasia tak pernah keluar."""
    return {"data": await ws.status(user.get("org_id", ORG_ID))}


@router.put("/secrets/{channel}")
async def put_webhook_secrets(channel: str, p: SecretsIn,
                              user: dict = Depends(require_permission("settings", "manage"))):
    """Isi/hapus rahasia verifikasi kanal (terenkripsi). WhatsApp tetap di `PUT /api/wa/config`."""
    if channel == "whatsapp":
        raise HTTPException(status_code=400, detail="Rahasia WhatsApp diatur di PUT /api/wa/config.")
    if channel not in ws.CHANNELS:
        raise HTTPException(status_code=404, detail="Kanal webhook tidak dikenal.")
    if p.verify_token is not None and not ws.CHANNELS[channel]["env_verify"]:
        raise HTTPException(status_code=400, detail="Kanal ini tidak memakai verify token.")
    org = user.get("org_id", ORG_ID)
    try:
        changed = await ws.save_secrets(channel, org, secret=p.secret, verify_token=p.verify_token,
                                        actor=user.get("email"))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await audit_log(user, "update", "webhook_secrets", channel, {"fields": changed})   # nama kolom, bukan nilai
    return {"data": await ws.status(org)}


@router.get("/meta-lead")
async def meta_lead_verify(request: Request):
    """Handshake webhook Meta Lead Ads: token cocok -> balas hub.challenge apa adanya (teks polos)."""
    sec = await ws.get_secrets("meta_lead", ORG_ID)
    challenge = ws.verify_handshake(sec["verify_token"], request.query_params)
    if challenge is None:
        return PlainTextResponse(ws.GENERIC_DENY, status_code=403)
    return PlainTextResponse(challenge)


@router.post("/meta-lead")
async def meta_lead(request: Request):
    return await _capture("meta_ads", request, channel="meta_lead")


@router.get("/wa")
async def wa_verify(request: Request):
    """Handshake Meta: hub.mode=subscribe & hub.verify_token cocok → balas hub.challenge."""
    cfg = await gw.get_config(ORG_ID)
    challenge = ws.verify_handshake(cfg["creds"].get("verify_token"), request.query_params)
    if challenge is not None:
        # uji handshake dari SIPRO sendiri (wa_setup) tidak dihitung sebagai webhook Meta yang sungguhan
        if not request.headers.get("X-Sipro-Selfcheck"):
            await gw.note_webhook(ORG_ID, signature_ok=True, kind="verify")
        return PlainTextResponse(challenge)
    await gw.note_webhook(ORG_ID, signature_ok=False, kind="verify_failed")
    return PlainTextResponse(ws.GENERIC_DENY, status_code=403)


async def _wa_legacy(body: bytes, parsed: tuple):
    """Kontrak lama `WebhookLead` di /wa — badan SUDAH diautentikasi oleh pemanggil."""
    clean, failed = await _parse("whatsapp", body, None, parsed)
    if failed:
        return failed
    try:
        lead_id, duplicate = await process_lead_capture("whatsapp", clean, org_id=ORG_ID)
    except Exception as e:  # noqa: BLE001 - gangguan sementara: layak dicoba ulang otomatis
        reason = f"Gangguan saat memproses lead: {e}"
        failure = await cf.record("whatsapp", clean, reason, kind=cf.KIND_TRANSIENT, org_id=ORG_ID)
        return _failed("whatsapp", failure, reason)
    return {"data": {"lead_id": lead_id, "duplicate": duplicate, "captured": True,
                     "mode": "simulation", "provider": "whatsapp"}}


@router.post("/wa")
async def wa_inbound(request: Request):
    """Dua kontrak: payload Meta asli (object=whatsapp_business_account) atau `WebhookLead` lama.

    Tanda tangan diperiksa atas BADAN MENTAH (`await request.body()` — dibaca sekali oleh `ws.read_body`)
    SEBELUM apa pun di-parse, dan berlaku untuk KEDUA kontrak: kontrak lama dulu lolos tanpa tanda
    tangan walau App Secret sudah terpasang."""
    body, too_big = await ws.read_body(request)
    if too_big:
        return too_big
    cfg = await gw.get_config(ORG_ID)
    verdict = await ws.authorize("whatsapp", request, body)
    if not verdict.ok:
        # App secret terpasang tetapi tanda tangan tidak cocok → tolak (siapa pun bisa menyuntik lead palsu).
        # TIDAK diantrekan ke "gagal masuk": penyerang tak boleh bisa membanjiri tugas/notifikasi supervisor.
        await gw.note_webhook(ORG_ID, signature_ok=False, kind="messages")
        return ws.rejection("whatsapp", request)
    sig_ok = verdict.signature_ok
    parsed = ws.parse_json(body)
    raw = parsed[0]
    if not wi.is_meta_payload(raw):
        return await _wa_legacy(body, parsed)
    await gw.note_webhook(ORG_ID, signature_ok=sig_ok, kind="messages")
    ev = {"id": new_id(), "waba_id": (raw.get("entry") or [{}])[0].get("id"), "org_id": ORG_ID, "received_at": now_iso(), "status": "processing",
          "payload": raw, "signature_ok": sig_ok}
    ev_id = (await db.wa_webhook_events.insert_one(dict(ev))).inserted_id

    async def _run():
        try:
            summary = await wi.process_meta_payload(raw, ORG_ID)
            await db.wa_webhook_events.update_one({"_id": ev_id}, {"$set": {
                "status": "done", "summary": {k: v for k, v in summary.items() if k != "results"}}})
            return summary
        except Exception as e:  # noqa: BLE001 — payload TIDAK dibuang: masuk antrean gagal
            failure = await cf.record("whatsapp", raw, f"Gangguan memproses webhook Meta: {e}",
                                      kind=cf.KIND_TRANSIENT, org_id=ORG_ID)
            await db.wa_webhook_events.update_one({"_id": ev_id}, {"$set": {"status": "failed", "failure_id": failure["id"]}})
            return {"queued": True, "failure_id": failure["id"]}

    # Meta menunggu < 5 detik: proses berjalan sebagai task; bila belum selesai dalam 4 detik, balas
    # 200 lebih dulu dan biarkan task melanjutkan (idempotensi dijaga klaim atomik + indeks unik wamid).
    task = asyncio.create_task(_run())
    done, _pending = await asyncio.wait({task}, timeout=4.0)
    if not done:
        return {"data": {"accepted": True, "deferred": True}, "mode": cfg["effective_mode"], "signature_ok": sig_ok}
    summary = task.result()
    return {"data": {k: v for k, v in summary.items() if k != "results"},
            "mode": cfg["effective_mode"], "signature_ok": sig_ok}


@router.post("/google-lead")
async def google_lead(request: Request):
    return await _capture("google_lead", request, channel="google_lead")


@router.post("/tiktok-lead")
async def tiktok_lead(request: Request):
    return await _capture("tiktok_lead", request, channel="tiktok_lead")


# AZ-09: per IP, `WEB_FORM_RATE_MAX` kiriman / 10 menit (bawaan 60). Di belakang proxy/CDN semua pengunjung berbagi
# satu IP — naikkan lewat env bila lonjakan kampanye yang sah ikut terblokir.
WEB_RATE_MAX, WEB_RATE_WINDOW = int(os.environ.get("WEB_FORM_RATE_MAX", "60")), 600


@router.post("/web")
async def web_form(request: Request):
    """Formulir web publik (tanpa tanda tangan) — dibatasi lajunya per IP supaya tidak bisa
    dipakai membanjiri CRM dengan lead palsu. Webhook provider bertanda tangan TIDAK dibatasi."""
    ip = request.client.host if request.client else "?"
    if not rate_limit.hit_ok("webhook_web", ip, WEB_RATE_MAX, WEB_RATE_WINDOW):
        return JSONResponse(status_code=429, content={"detail": (
            "Terlalu banyak kiriman dari perangkat ini. Coba lagi beberapa menit lagi "
            "atau hubungi kami via WhatsApp.")}, headers={"Retry-After": str(WEB_RATE_WINDOW)})
    return await _capture("website", request)


@router.post("/partner/{partner_id}")
async def partner_lead(partner_id: str, request: Request, token: str = None):
    """Lead dari sistem MITRA. Wajib token mitra (header `X-Partner-Token` atau `?token=`)."""
    provided = token or request.headers.get("X-Partner-Token") or ""
    partner = await db.agents.find_one({"id": partner_id, "org_id": ORG_ID}, {"_id": 0})
    # Jawaban SAMA untuk mitra tak dikenal dan token salah: siapa pun yang menebak-nebak
    # tidak boleh bisa memetakan daftar mitra kami dari balasan endpoint publik.
    if not partner or not partner.get("webhook_token") \
            or not ws.safe_equals(provided, partner.get("webhook_token")):
        return JSONResponse(status_code=401, content={"detail": (
            "Token mitra tidak sah. Minta ulang token di halaman profil mitra "
            "(Mitra & Fee → profil mitra → Webhook Lead).")})
    ok, why = pengine.contract_active(partner, today_iso_date())
    if partner.get("status") != "active" or not ok:
        return JSONResponse(status_code=403, content={"detail": (
            f"Mitra {partner.get('name')} tidak sedang aktif ({partner.get('status')}"
            f"{'; ' + why if why else ''}) — lead baru dari mitra ini ditolak supaya tidak "
            "melahirkan hak fee yang tidak boleh ada.")})
    raw, too_big = await ws.read_body(request)
    if too_big:
        return too_big
    clean, failed = await _parse("partner", raw, {"source": "partner", "partner_id": partner_id})
    if failed:
        return failed
    existing = await db.leads.find_one({"org_id": ORG_ID, "phone": clean["phone"]},
                                      {"_id": 0, "id": 1, "partner_id": 1, "name": 1})
    verdict = await pengine.attribute(partner_id=partner_id, phone=clean["phone"],
                                      org_id=ORG_ID,
                                      lead_id=(existing or {}).get("id"))
    if existing:
        # Nomor sudah ada: JANGAN membuat lead kedua (nomor unik per organisasi). Klaim
        # mitra tetap dicatat + pemenangnya ditetapkan mesin atribusi.
        ts = now_iso()
        await db.leads.update_one({"id": existing["id"], "org_id": ORG_ID}, {"$set": {
            "partner_id": verdict["partner_id"],
            "partner_attribution_model": verdict["model"],
            "partner_attributed_at": ts, "updated_at": ts,
            "last_touch": {"at": ts, "provider": "partner", "source": "partner",
                           "campaign": clean.get("campaign"), "partner_id": partner_id},
        }})
        for pid in {partner_id, verdict.get("partner_id")}:
            if pid:
                await pengine.refresh_stats(pid, org_id=ORG_ID)
        return {"data": {
            "lead_id": existing["id"], "duplicate": True, "captured": False,
            "mode": "simulation", "provider": "partner",
            "attributed_to": verdict["partner_id"], "attribution_model": verdict["model"],
            "conflict_id": (verdict.get("conflict") or {}).get("id"),
            "note": ("Nomor ini sudah ada di CRM. Klaim mitra dicatat dan atribusinya "
                     f"diputuskan dengan model {verdict['model']} — tidak ada lead kembar "
                     "yang dibuat.")}}
    clean["partner_id"] = verdict["partner_id"]
    try:
        lead_id, duplicate = await process_lead_capture("partner", clean, org_id=ORG_ID)
    except Exception as e:  # noqa: BLE001
        reason = f"Gangguan saat memproses lead mitra: {e}"
        failure = await cf.record("partner", clean, reason, kind=cf.KIND_TRANSIENT,
                                  org_id=ORG_ID)
        return _failed("partner", failure, reason)
    await pengine.refresh_stats(verdict["partner_id"], org_id=ORG_ID)
    return {"data": {"lead_id": lead_id, "duplicate": duplicate, "captured": True,
                     "mode": "simulation", "provider": "partner",
                     "attributed_to": verdict["partner_id"],
                     "attribution_model": verdict["model"],
                     "conflict_id": (verdict.get("conflict") or {}).get("id")}}
