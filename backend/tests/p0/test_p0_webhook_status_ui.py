"""H-C — bentuk `GET /api/webhooks/status` yang dibutuhkan layar "Keamanan Webhook" (Pusat Konfigurasi).

Layar perlu tahu (a) variabel lingkungan alternatif tiap kanal (NAMA saja, bukan nilainya), (b) dari mana verify
token berasal (db/env/none), dan (c) di mana rahasia diatur (WhatsApp tetap lewat konfigurasi WA). Tes ini
memastikan bidang itu ada, benar isinya, dan nilai rahasia/verify token TIDAK PERNAH ikut keluar.

    API_BASE=http://localhost:8073/api python -m pytest backend/tests/p0/test_p0_webhook_status_ui.py \
        -n 0 --noconftest -q -p no:cacheprovider
"""
import os
import uuid

import requests

API = os.environ.get("API_BASE", "http://localhost:8073/api").rstrip("/")
PW = "Sipro#2026"
OWNER, SALES = "owner@sipro.co.id", "sales@sipro.co.id"
_tokens = {}


def _login(email):
    if email not in _tokens:
        r = requests.post(f"{API}/auth/login", json={"email": email, "password": PW}, timeout=30)
        assert r.status_code == 200, f"login {email}: {r.status_code}"
        _tokens[email] = r.json()["access_token"]
    return _tokens[email]


def call(email, method, path, **kw):
    return requests.request(method, f"{API}{path}", headers={"Authorization": f"Bearer {_login(email)}"},
                            timeout=60, **kw)


def _status(email=OWNER):
    r = call(email, "GET", "/webhooks/status")
    assert r.status_code == 200, r.text[:200]
    return r


def test_status_memuat_nama_env_sumber_dan_tempat_pengaturan():
    d = _status().json()["data"]
    kanal = {c["channel"]: c for c in d["channels"]}
    assert kanal["meta_lead"]["env_secret"] == ["META_LEAD_APP_SECRET", "META_APP_SECRET"]
    assert kanal["meta_lead"]["env_verify"] == ["META_LEAD_VERIFY_TOKEN", "META_VERIFY_TOKEN"]
    assert kanal["google_lead"]["env_secret"] == ["GOOGLE_LEAD_WEBHOOK_KEY"] and kanal["google_lead"]["env_verify"] == []
    assert kanal["tiktok_lead"]["env_secret"] == ["TIKTOK_LEAD_WEBHOOK_SECRET"]
    assert kanal["whatsapp"]["managed_via"] == "wa_config"
    for ch in ("meta_lead", "google_lead", "tiktok_lead"):
        assert kanal[ch]["managed_via"] == "webhook_secrets"
    # verify token hanya bermakna untuk kanal yang memakainya
    assert kanal["google_lead"]["verify_token_source"] is None and kanal["tiktok_lead"]["verify_token_source"] is None
    assert kanal["meta_lead"]["verify_token_source"] in ("db", "env", "none")


def test_sumber_verify_token_berubah_dan_nilainya_tak_bocor():
    sec, ver = f"hc-{uuid.uuid4().hex}", f"hcv-{uuid.uuid4().hex}"
    r = call(OWNER, "PUT", "/webhooks/secrets/meta_lead", json={"secret": sec, "verify_token": ver})
    assert r.status_code == 200, r.text[:200]
    try:
        txt = _status().text
        assert sec not in txt and ver not in txt, "nilai rahasia/verify token tidak boleh keluar di status"
        txt_sales = _status(SALES).text                       # settings:view dimiliki semua peran bawaan
        assert sec not in txt_sales and ver not in txt_sales
        m = next(c for c in _status().json()["data"]["channels"] if c["channel"] == "meta_lead")
        assert m["secret_configured"] is True and m["secret_source"] == "db"
        assert m["verify_token_configured"] is True and m["verify_token_source"] == "db"
    finally:
        call(OWNER, "PUT", "/webhooks/secrets/meta_lead", json={"secret": "__clear__", "verify_token": "__clear__"})
    m = next(c for c in _status().json()["data"]["channels"] if c["channel"] == "meta_lead")
    assert m["secret_configured"] is False and m["verify_token_configured"] is False
    assert m["secret_source"] in ("none", "env")
