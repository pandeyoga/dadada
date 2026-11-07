"""webhook_security — keamanan webhook PUBLIK (lead Meta/Google/TikTok + WhatsApp Cloud).

Masalah yang ditutup (audit CRM 10 §"Kesiapan integrasi", temuan #1): endpoint webhook publik
menerima apa saja. Siapa pun yang tahu URL-nya bisa menyuntik lead palsu (mengotori CPL, CAC, ROAS,
dan umpan balik CAPI), memicu notifikasi/tugas ke supervisor lewat antrean "lead gagal masuk",
atau memutar ulang (replay) permintaan asli yang sudah pernah ditangkap.

KEBIJAKAN (satu kebenaran, dipakai semua kanal):
  * Rahasia kanal SUDAH dikonfigurasi  -> tanda tangan/rahasia WAJIB. Salah/tidak ada -> 401/403
    dengan pesan SERAGAM (tidak membocorkan apa yang salah) dan TIDAK masuk antrean gagal-masuk.
  * Rahasia BELUM dikonfigurasi        -> permintaan tetap diterima supaya mode simulasi/uji lama
    jalan, tetapi `GET /api/webhooks/status` mencantumkan kanal itu sebagai TIDAK AMAN.

SPESIFIKASI per kanal (ASUMSI dicatat jujur di bawah):
  meta_lead / whatsapp : `X-Hub-Signature-256: sha256=HMAC_SHA256(app_secret, BADAN MENTAH)`;
                         handshake GET `hub.mode=subscribe` + `hub.verify_token` -> balas `hub.challenge`.
                         Spesifikasi resmi Meta. Cap waktu pesan TIDAK ikut ditandatangani Meta.
  google_lead          : kolom `google_key` di badan JSON dibandingkan konstan-waktu dengan kunci
                         yang kita isi di Google Ads (spesifikasi resmi Lead Form webhook).
  tiktok_lead          : ASUMSI — dokumen webhook TikTok untuk lead tidak mengikat satu skema.
                         Didukung dua bentuk, keduanya konstan-waktu:
                           (a) `TikTok-Signature: t=<unix>,s=<hex>` dengan s = HMAC_SHA256(secret,
                               "<t>.<badan mentah>") dan toleransi cap waktu 5 menit (skema webhook
                               TikTok for Developers);
                           (b) rahasia bersama di header `X-TikTok-Secret` / `X-Webhook-Secret`.
                         Rahasia lewat query string SENGAJA tidak didukung: access log uvicorn
                         mencetak query string, jadi rahasia akan bocor ke log.

PERLINDUNGAN REPLAY: (1) dedup atomik id peristiwa (`leadgen_id`/`lead_id`/`event_id`/`wamid`) lewat
`idempotency.claim`; (2) cap waktu hanya ditegakkan di tempat ia ikut ditandatangani (TikTok `t=`).
Cap waktu pesan Meta adalah waktu KEJADIAN, bukan waktu kirim: Meta mengulang pengiriman sampai 7 hari
saat server mati, jadi menolak pesan >5 menit akan membuang pesan pelanggan yang sah. Pembatas opsional:
env `WEBHOOK_META_MAX_AGE_SECONDS` (bawaan 0 = mati).

Rahasia disimpan TERENKRIPSI (Fernet dari JWT_SECRET, sama dengan kredensial WhatsApp) di koleksi
`webhook_secrets`, atau dibaca dari env; tidak pernah ditulis ke log maupun dikembalikan oleh API.
"""
import hashlib
import hmac
import json
import logging
import os
import time
from dataclasses import dataclass
from typing import Optional

from fastapi.responses import JSONResponse

import idempotency
import rate_limit
import wa_gateway as gw
from core_utils import new_id, now_iso
from db import db, ORG_ID

logger = logging.getLogger("sipro.webhook_security")

MAX_BODY = int(os.environ.get("WEBHOOK_MAX_BODY_BYTES", str(1024 * 1024)))   # 1 MB
REPLAY_TOLERANCE = 300                      # detik; cap waktu yang ikut ditandatangani
EVENT_TTL = 7 * 24 * 3600                   # Meta mengulang pengiriman sampai 7 hari
BAD_ATTEMPTS_PER_MIN = 30                   # percobaan GAGAL per IP; yang sah tidak pernah dibatasi
MIN_SECRET_LEN = 8
CLEAR = "__clear__"
COLL = "webhook_secrets"
GENERIC_DENY = "Permintaan tidak sah."

CHANNELS = {
    "meta_lead": {
        "label": "Meta Lead Ads", "path": "/api/webhooks/meta-lead", "method": "hub", "deny": 403,
        "method_label": "Meta: header X-Hub-Signature-256 (HMAC-SHA256 atas badan mentah) + handshake hub.verify_token",
        "env_secret": ("META_LEAD_APP_SECRET", "META_APP_SECRET"), "env_verify": ("META_LEAD_VERIFY_TOKEN", "META_VERIFY_TOKEN"),
        "hint": "Isi App Secret aplikasi Meta (Settings > Basic) dan Verify Token lewat PUT /api/webhooks/secrets/meta_lead, "
                "atau env META_APP_SECRET / META_VERIFY_TOKEN.",
    },
    "whatsapp": {
        "label": "WhatsApp Cloud API", "path": "/api/webhooks/wa", "method": "hub", "deny": 403,
        "method_label": "Meta: header X-Hub-Signature-256 (HMAC-SHA256 atas badan mentah) + handshake hub.verify_token",
        "env_secret": ("WHATSAPP_APP_SECRET",), "env_verify": ("WHATSAPP_VERIFY_TOKEN",),
        "hint": "Isi App Secret dan Verify Token di Pengaturan > WhatsApp (PUT /api/wa/config).",
    },
    "google_lead": {
        "label": "Google Ads Lead Form", "path": "/api/webhooks/google-lead", "method": "google_key", "deny": 401,
        "method_label": "Google: kolom google_key di badan JSON (dibandingkan konstan-waktu)",
        "env_secret": ("GOOGLE_LEAD_WEBHOOK_KEY",), "env_verify": (),
        "hint": "Isi 'Key' yang sama dengan yang dimasukkan di pengaturan webhook Lead Form Google Ads lewat "
                "PUT /api/webhooks/secrets/google_lead, atau env GOOGLE_LEAD_WEBHOOK_KEY.",
    },
    "tiktok_lead": {
        "label": "TikTok Lead", "path": "/api/webhooks/tiktok-lead", "method": "tiktok", "deny": 401,
        "method_label": "TikTok: header TikTok-Signature (t=,s= HMAC-SHA256, toleransi 5 menit) atau rahasia bersama di header X-TikTok-Secret",
        "env_secret": ("TIKTOK_LEAD_WEBHOOK_SECRET",), "env_verify": (),
        "hint": "Isi rahasia lewat PUT /api/webhooks/secrets/tiktok_lead, atau env TIKTOK_LEAD_WEBHOOK_SECRET.",
    },
}


@dataclass
class Verdict:
    ok: bool
    enforced: bool                      # rahasia terkonfigurasi (tanda tangan WAJIB)
    signature_ok: Optional[bool]        # None = tidak bisa diverifikasi (belum ada rahasia)
    reason: str = ""                    # HANYA untuk log internal, tidak pernah dikirim ke penelepon
    replay_key: Optional[str] = None    # tanda tangan bercap waktu: ingat selama jendela toleransi


# ------------------------------------------------------------------ primitif kriptografi
def safe_equals(a, b) -> bool:
    """Perbandingan konstan-waktu untuk str/bytes APA PUN (termasuk non-ASCII; tidak melempar)."""
    if a is None or b is None:
        return False
    a = a.encode() if isinstance(a, str) else bytes(a)
    b = b.encode() if isinstance(b, str) else bytes(b)
    return hmac.compare_digest(a, b)


def hmac_hex(secret: str, data: bytes) -> str:
    return hmac.new(secret.encode(), data, hashlib.sha256).hexdigest()


def verify_hub_signature(secret: str, body: bytes, header: str):
    """Skema Meta. None = tidak ada rahasia (tak bisa diverifikasi); False = salah/hilang; True = sah."""
    if not secret:
        return None
    if not header or not header.startswith("sha256="):
        return False
    return safe_equals(hmac_hex(secret, body), header.split("=", 1)[1].strip().lower())


def verify_tiktok(secret: str, sig_header: str, shared_header: str, body: bytes,
                  now: float = None, tolerance: int = REPLAY_TOLERANCE) -> tuple:
    """-> (ok, alasan_internal, replay_key)."""
    if sig_header:
        parts = dict(p.strip().split("=", 1) for p in sig_header.split(",") if "=" in p)
        t, s = parts.get("t", ""), parts.get("s", "")
        if not (t.isdigit() and s):
            return False, "bad_signature", None
        if abs((now if now is not None else time.time()) - int(t)) > tolerance:
            return False, "stale_timestamp", None
        ok = safe_equals(hmac_hex(secret, f"{t}.".encode() + body), s.lower())
        return ok, "bad_signature", (f"{t}.{s.lower()}" if ok else None)
    if shared_header:
        return safe_equals(shared_header, secret), "bad_secret", None
    return False, "no_credential", None


def verify_google_key(secret: str, payload) -> bool:
    key = payload.get("google_key") if isinstance(payload, dict) else None
    return isinstance(key, str) and safe_equals(key, secret)


def too_old(ts, max_age: int = None, now: float = None) -> bool:
    """Pembatas usia peristiwa OPSIONAL (bawaan mati). ts = epoch detik (int/str)."""
    if max_age is None:
        max_age = int(os.environ.get("WEBHOOK_META_MAX_AGE_SECONDS", "0") or 0)
    if max_age <= 0:
        return False
    try:
        return (now if now is not None else time.time()) - int(ts) > max_age
    except (TypeError, ValueError):
        return False


# ------------------------------------------------------------------ badan permintaan
def _deny(status: int, detail: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"detail": detail})


async def read_body(request, limit: int = None) -> tuple:
    """-> (bytes, None) atau (None, JSONResponse). Batas ukuran ditegakkan SAAT MEMBACA (stream),
    bukan sesudah seluruh badan masuk memori. Badan mentah inilah yang ditandatangani provider, jadi
    dibaca SEKALI sebagai bytes (setara `await request.body()`) lalu dipakai ulang oleh semua pemeriksa."""
    limit = limit or MAX_BODY
    too_big = _deny(413, f"Badan permintaan terlalu besar (maksimum {limit // 1024} KB).")
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > limit:
        return None, too_big
    chunks, total = [], 0
    try:
        async for chunk in request.stream():
            total += len(chunk)
            if total > limit:
                return None, too_big
            chunks.append(chunk)
    except Exception as exc:  # noqa: BLE001 — klien memutus koneksi di tengah kiriman
        logger.warning("Webhook: badan permintaan tidak terbaca (%s)", type(exc).__name__)
        return None, _deny(400, "Badan permintaan tidak bisa dibaca.")
    return b"".join(chunks), None


def parse_json(raw: bytes) -> tuple:
    """-> (dict|None, galat|None, fatal). fatal=True: badan patologis (bersarang terlalu dalam, angka
    di luar batas) -> 400 bersih, TIDAK diantrekan. Selain itu galat biasa diantrekan (Fase 30c)."""
    if not raw:
        return None, "Body kosong: provider tidak mengirim data apa pun.", False
    try:
        data = json.loads(raw)
    except RecursionError:
        return None, "JSON bersarang terlalu dalam.", True
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        return {"_raw_text": raw[:2000].decode("utf-8", "replace")}, f"JSON tidak valid: {e}", False
    except (ValueError, MemoryError):
        return None, "Struktur/angka JSON di luar batas yang didukung.", True
    if not isinstance(data, dict):
        return {"_raw_text": str(data)[:2000]}, "Payload harus berupa objek JSON.", False
    return data, None, False


# ------------------------------------------------------------------ rahasia (terenkripsi / env)
_index_ready = False


async def _ensure_index() -> None:
    global _index_ready
    if _index_ready:
        return
    try:
        await db[COLL].create_index([("org_id", 1), ("channel", 1)], unique=True, name="uq_webhook_secrets")
        _index_ready = True
    except Exception as e:  # noqa: BLE001 — indeks hanya pengaman; jangan gagalkan webhook
        logger.warning("Indeks webhook_secrets gagal dibuat: %s", str(e)[:120])


def _env(names: tuple) -> str:
    for n in names:
        if os.environ.get(n):
            return os.environ[n]
    return ""


async def get_secrets(channel: str, org_id: str = ORG_ID) -> dict:
    """{secret, verify_token, secret_source, verify_source} — source: db|env|none."""
    spec = CHANNELS[channel]
    if channel == "whatsapp":
        cfg = await gw.get_config(org_id)
        return {"secret": cfg["creds"].get("app_secret") or "", "verify_token": cfg["creds"].get("verify_token") or "",
                "secret_source": cfg["sources"].get("app_secret", "none"),
                "verify_source": cfg["sources"].get("verify_token", "none")}
    doc = await db[COLL].find_one({"org_id": org_id, "channel": channel}, {"_id": 0}) or {}
    out = {}
    for field, enc_key, env_names in (("secret", "secret_enc", spec["env_secret"]),
                                      ("verify", "verify_enc", spec["env_verify"])):
        val = gw.decrypt(doc[enc_key]) if doc.get(enc_key) else ""
        src = "db" if val else "none"
        if not val and env_names and _env(env_names):
            val, src = _env(env_names), "env"
        out[field], out[f"{field}_source"] = val, src
    return {"secret": out["secret"], "verify_token": out["verify"],
            "secret_source": out["secret_source"], "verify_source": out["verify_source"]}


async def save_secrets(channel: str, org_id: str, *, secret: str = None, verify_token: str = None,
                       actor: str = "") -> list:
    """Simpan (terenkripsi) / hapus (`__clear__`). -> daftar field yang diubah. ValueError bila rahasia terlalu pendek."""
    if channel not in CHANNELS or channel == "whatsapp":
        raise ValueError("Kanal tidak dikenal atau dikelola di tempat lain (WhatsApp: PUT /api/wa/config).")
    await _ensure_index()
    sets, unsets, changed = {}, {}, []
    for field, enc_key, value in (("secret", "secret_enc", secret), ("verify_token", "verify_enc", verify_token)):
        if value is None:
            continue
        value = value.strip() if value != CLEAR else value
        if value == CLEAR:
            unsets[enc_key] = ""
        elif value:
            if len(value) < MIN_SECRET_LEN:
                raise ValueError(f"{field} minimal {MIN_SECRET_LEN} karakter.")
            sets[enc_key] = gw.encrypt(value)
        else:
            continue
        changed.append(field)
    if not changed:
        return []
    update = {"$set": {**sets, "updated_at": now_iso(), "updated_by": actor},
              "$setOnInsert": {"id": new_id(), "created_at": now_iso()}}
    if unsets:
        update["$unset"] = unsets
    await db[COLL].update_one({"org_id": org_id, "channel": channel}, update, upsert=True)
    return changed


async def note(channel: str, org_id: str, ok: bool) -> None:
    """Statistik ringan untuk layar status (tanpa isi permintaan)."""
    try:
        await _ensure_index()
        upd = {"$set": {"last_ok_at": now_iso()}} if ok else {
            "$set": {"last_rejected_at": now_iso()}, "$inc": {"rejected_total": 1}}
        upd.setdefault("$setOnInsert", {"id": new_id(), "created_at": now_iso()})
        await db[COLL].update_one({"org_id": org_id, "channel": channel}, upd, upsert=True)
    except Exception:  # noqa: BLE001 — statistik tidak boleh menggagalkan webhook
        logger.warning("Catatan statistik webhook %s gagal", channel)


# ------------------------------------------------------------------ gerbang
def rejection(channel: str, request=None) -> JSONResponse:
    """Balasan SERAGAM untuk semua kegagalan autentikasi (tak membocorkan penyebab). Percobaan GAGAL
    yang berulang dari satu IP dijawab 429; permintaan SAH tidak pernah ikut terhitung."""
    ip = (request.client.host if request is not None and request.client else "?")
    if not rate_limit.hit_ok("webhook_bad", ip, BAD_ATTEMPTS_PER_MIN, 60):
        return _deny(429, "Terlalu banyak percobaan.")
    return _deny(CHANNELS[channel]["deny"], GENERIC_DENY)


async def authorize(channel: str, request, raw: bytes, parsed=None, org_id: str = ORG_ID) -> Verdict:
    """Terapkan kebijakan kanal. `parsed` = objek JSON (dibutuhkan kanal google_key)."""
    sec = await get_secrets(channel, org_id)
    secret = sec["secret"]
    if not secret:
        return Verdict(ok=True, enforced=False, signature_ok=None)
    method, h = CHANNELS[channel]["method"], request.headers
    ok, reason, replay_key = False, "bad_signature", None
    if method == "hub":
        ok = verify_hub_signature(secret, raw, h.get("X-Hub-Signature-256")) is True
        reason = "bad_signature" if h.get("X-Hub-Signature-256") else "no_credential"
    elif method == "google_key":
        ok, reason = verify_google_key(secret, parsed), "bad_key"
    elif method == "tiktok":
        ok, reason, replay_key = verify_tiktok(
            secret, h.get("TikTok-Signature"), h.get("X-TikTok-Secret") or h.get("X-Webhook-Secret"), raw)
    await note(channel, org_id, ok)
    if not ok:
        ip = request.client.host if request.client else "?"
        logger.warning("Webhook %s DITOLAK (ip=%s, alasan=%s)", channel, ip, reason)  # tanpa nilai rahasia
    return Verdict(ok=ok, enforced=True, signature_ok=ok, reason="" if ok else reason, replay_key=replay_key)


def verify_handshake(expected: str, params) -> Optional[str]:
    """GET verifikasi Meta -> hub.challenge bila sah, None bila ditolak. Konstan-waktu."""
    if params.get("hub.mode") != "subscribe" or not expected:
        return None
    if not safe_equals(params.get("hub.verify_token") or "", expected):
        return None
    return (params.get("hub.challenge") or "")[:256]


# ------------------------------------------------------------------ idempotensi peristiwa (anti-replay)
def event_ids_for(obj) -> list:
    """Id peristiwa dari payload lead: `leadgen_id`/`lead_id`/`event_id` (datar) dan amplop Meta
    `entry[].changes[].value.leadgen_id`. Kolom `id` generik sengaja tidak dipakai."""
    ids = []

    def take(src):
        if isinstance(src, dict):
            for k in ("leadgen_id", "lead_id", "event_id"):
                v = src.get(k)
                if isinstance(v, (str, int)) and str(v).strip():
                    ids.append(str(v).strip()[:200])

    take(obj)
    if isinstance(obj, dict) and isinstance(obj.get("entry"), list):
        for entry in obj["entry"]:
            for change in (entry.get("changes") or []) if isinstance(entry, dict) else []:
                take((change or {}).get("value") if isinstance(change, dict) else None)
    return list(dict.fromkeys(ids))


async def claim_event(provider: str, event_id: str, org_id: str = ORG_ID, ttl: int = EVENT_TTL) -> bool:
    """True = baru (diklaim sekarang); False = sudah pernah diterima (replay/pengiriman ulang)."""
    try:
        await idempotency.claim(idempotency.make_key("webhook", provider, org_id, event_id), ttl)
        return True
    except idempotency.Conflict:
        return False


async def release_event(provider: str, event_id: str, org_id: str = ORG_ID) -> None:
    await idempotency.release(idempotency.make_key("webhook", provider, org_id, event_id))


# ------------------------------------------------------------------ layar status
async def status(org_id: str = ORG_ID) -> dict:
    """Kanal mana yang sudah/ belum aman. Hanya 'terisi/tidak' — nilai rahasia TIDAK pernah keluar."""
    channels, warnings = [], []
    for ch, spec in CHANNELS.items():
        sec = await get_secrets(ch, org_id)
        stats = await db[COLL].find_one({"org_id": org_id, "channel": ch},
                                        {"_id": 0, "last_ok_at": 1, "last_rejected_at": 1, "rejected_total": 1}) or {}
        configured = bool(sec["secret"])
        warn = None if configured else (
            f"{spec['label']}: rahasia belum dikonfigurasi, endpoint {spec['path']} menerima permintaan dari SIAPA PUN "
            f"(hanya layak untuk mode simulasi/uji). {spec['hint']}")
        if warn:
            warnings.append(warn)
        channels.append({
            "channel": ch, "label": spec["label"], "path": spec["path"], "method": spec["method_label"],
            "secret_configured": configured, "secret_source": sec["secret_source"],
            "verify_token_configured": bool(sec["verify_token"]) if spec["env_verify"] else None,
            "enforced": configured, "secure": configured, "warning": warn,
            "last_ok_at": stats.get("last_ok_at"), "last_rejected_at": stats.get("last_rejected_at"),
            "rejected_total": stats.get("rejected_total", 0)})
    others = [
        {"channel": "partner", "label": "Webhook Mitra", "path": "/api/webhooks/partner/{id}", "secure": True,
         "method": "Token per mitra (header X-Partner-Token), mitra tak aktif ditolak"},
        {"channel": "web", "label": "Formulir Web", "path": "/api/webhooks/web", "secure": None,
         "method": "Publik oleh desain (dipanggil dari browser pengunjung); dibatasi laju per IP"}]
    insecure = [c["channel"] for c in channels if not c["secure"]]
    return {"channels": channels, "others": others, "insecure_channels": insecure, "warnings": warnings,
            "all_secure": not insecure, "max_body_bytes": MAX_BODY,
            "policy": "Rahasia terkonfigurasi = tanda tangan WAJIB (401/403); belum terkonfigurasi = diterima (simulasi) + peringatan di sini."}
