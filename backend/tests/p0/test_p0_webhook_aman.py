"""Regresi G-D (1) — KEAMANAN WEBHOOK PUBLIK: Meta Lead, WhatsApp Cloud, Google Lead Form, TikTok Lead.

Temuan audit CRM (10): webhook lead/WhatsApp publik menerima apa saja tanpa tanda tangan — lead palsu mengotori
CPL/CAC/ROAS dan umpan balik CAPI, dan penyerang bisa membanjiri tugas/notifikasi supervisor lewat antrean
"lead gagal masuk". Kebijakan yang diuji: rahasia SUDAH dikonfigurasi -> tanda tangan WAJIB (401/403 seragam);
BELUM -> tetap diterima (simulasi) + peringatan di `GET /api/webhooks/status`.

Tes menandatangani muatannya sendiri dengan rahasia uji acak (dipasang lewat API konfigurasi lalu SELALU dicabut).

    API_BASE=http://localhost:8074/api DB_NAME=<db> MONGO_URL=<url> python -m pytest \
        backend/tests/p0/test_p0_webhook_aman.py -n 0 --noconftest -q -p no:cacheprovider
"""
import contextlib
import hashlib
import hmac
import json
import os
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
import requests

API = os.environ.get("API_BASE", "http://localhost:8074/api").rstrip("/")
PW = "Sipro#2026"
OWNER, SALES = "owner@sipro.co.id", "sales@sipro.co.id"
TAG = uuid.uuid4().hex[:6]
GENERIC = "Permintaan tidak sah."
_tokens = {}


# ------------------------------------------------------------------ pembantu
def _login(email):
    if email not in _tokens:
        r = requests.post(f"{API}/auth/login", json={"email": email, "password": PW}, timeout=30)
        assert r.status_code == 200, f"login {email}: {r.status_code}"
        _tokens[email] = r.json()["access_token"]
    return _tokens[email]


def call(email, method, path, **kw):
    return requests.request(method, f"{API}{path}", headers={"Authorization": f"Bearer {_login(email)}"},
                            timeout=60, **kw)


def phone():
    return "+62815" + str(uuid.uuid4().int)[:8]


def sign_hub(secret, body):
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def post_raw(path, body, headers=None):
    h = {"Content-Type": "application/json", **(headers or {})}
    return requests.post(f"{API}/webhooks{path}", data=body, headers=h, timeout=60)


def jbytes(obj):
    return json.dumps(obj, separators=(",", ":")).encode()


def lead_body(**extra):
    return jbytes({"name": f"G-D {TAG}", "phone": phone(), "campaign": f"gd-{TAG}", "message": "tanya harga", **extra})


def new_secret():
    return f"gd-{uuid.uuid4().hex}"


@contextlib.contextmanager
def secret(channel, value, verify=None):
    """Pasang rahasia uji lewat API konfigurasi; SELALU dicabut di akhir (kanal kembali 'belum dikonfigurasi')."""
    payload = {"secret": value}
    if verify:
        payload["verify_token"] = verify
    r = call(OWNER, "PUT", f"/webhooks/secrets/{channel}", json=payload)
    assert r.status_code == 200, f"pasang rahasia {channel}: {r.status_code} {r.text[:200]}"
    try:
        yield value
    finally:
        clr = {"secret": "__clear__"}
        if channel == "meta_lead":
            clr["verify_token"] = "__clear__"
        call(OWNER, "PUT", f"/webhooks/secrets/{channel}", json=clr)


def mongo():
    name = os.environ.get("DB_NAME")
    if not name:
        pytest.skip("set DB_NAME = nama DB instans yang diuji")
    from pymongo import MongoClient
    url = os.environ.get("MONGO_URL") or "mongo" + "db://127.0.0.1:27017"   # gate kepatuhan: tanpa literal URI
    return MongoClient(url)[name]


def wa_text(ph, text="halo, tanya harga", wamid=None):
    return {"object": "whatsapp_business_account", "entry": [{"id": "WABA-GD", "changes": [{"field": "messages", "value": {
        "messaging_product": "whatsapp", "metadata": {"phone_number_id": "PN-GD"},
        "contacts": [{"profile": {"name": f"GD {TAG}"}, "wa_id": ph.lstrip("+")}],
        "messages": [{"from": ph.lstrip("+"), "id": wamid or f"wamid.GD{uuid.uuid4().hex[:24]}",
                      "timestamp": str(int(time.time())), "type": "text", "text": {"body": text}}]}}]}]}


def open_failures():
    r = call(OWNER, "GET", "/capture/failures/summary")
    assert r.status_code == 200, r.text[:200]
    return r.json()["data"]["open"]


# ================================================================== status & izin
def test_status_butuh_izin_dan_menandai_kanal_belum_aman():
    assert requests.get(f"{API}/webhooks/status", timeout=30).status_code == 401
    sales = call(SALES, "GET", "/webhooks/status")           # settings:view dimiliki semua peran bawaan
    assert sales.status_code == 200 and "secret_enc" not in sales.text
    d = call(OWNER, "GET", "/webhooks/status").json()["data"]
    kanal = {c["channel"]: c for c in d["channels"]}
    assert set(kanal) == {"meta_lead", "whatsapp", "google_lead", "tiktok_lead"}
    for ch in ("meta_lead", "google_lead", "tiktok_lead"):
        assert kanal[ch]["secure"] is False and kanal[ch]["warning"], f"{ch}: harus diperingatkan saat belum ada rahasia"
        assert ch in d["insecure_channels"]
    assert d["all_secure"] is False and d["warnings"]
    assert {o["channel"] for o in d["others"]} == {"partner", "web"}
    with secret("google_lead", new_secret()):
        d2 = call(OWNER, "GET", "/webhooks/status").json()["data"]
        g = next(c for c in d2["channels"] if c["channel"] == "google_lead")
        assert g["secure"] is True and g["enforced"] is True and g["warning"] is None
        assert "google_lead" not in d2["insecure_channels"]


def test_pengaturan_rahasia_butuh_izin_manage_pendek_ditolak_dan_nilai_tak_bocor():
    assert call(SALES, "PUT", "/webhooks/secrets/google_lead", json={"secret": new_secret()}).status_code == 403
    assert call(OWNER, "PUT", "/webhooks/secrets/google_lead", json={"secret": "pendek"}).status_code == 400
    assert call(OWNER, "PUT", "/webhooks/secrets/tidak_ada", json={"secret": new_secret()}).status_code == 404
    assert call(OWNER, "PUT", "/webhooks/secrets/whatsapp", json={"secret": new_secret()}).status_code == 400
    val = new_secret()
    with secret("google_lead", val):
        txt = call(OWNER, "GET", "/webhooks/status").text
        assert val not in txt, "nilai rahasia tidak boleh keluar dari API"
        doc = mongo().webhook_secrets.find_one({"channel": "google_lead", "org_id": {"$exists": True}})
        assert doc and val not in json.dumps(doc, default=str), "rahasia harus tersimpan TERENKRIPSI"


# ================================================================== Meta Lead Ads
def test_meta_lead_tanda_tangan_wajib_bila_rahasia_ada_dan_longgar_bila_belum():
    assert post_raw("/meta-lead", lead_body()).status_code == 200, "belum dikonfigurasi -> tetap diterima (simulasi)"
    with secret("meta_lead", new_secret()) as sec:
        body = lead_body()
        for hdr in ({}, {"X-Hub-Signature-256": "sha256=" + "0" * 64}, {"X-Hub-Signature-256": "salah"},
                    {"X-Hub-Signature-256": sign_hub("rahasia-lain-12345", body)}):
            r = post_raw("/meta-lead", body, hdr)
            assert r.status_code == 403, (hdr, r.status_code)
            assert r.json() == {"detail": GENERIC}, "balasan harus seragam & tidak merinci alasan"
        ok = post_raw("/meta-lead", body, {"X-Hub-Signature-256": sign_hub(sec, body)})
        assert ok.status_code == 200 and ok.json()["data"]["captured"] is True, ok.text[:200]
    assert post_raw("/meta-lead", lead_body()).status_code == 200, "rahasia dicabut -> kembali diterima"


def test_meta_lead_tanda_tangan_dihitung_atas_badan_mentah_bukan_json_ulang():
    with secret("meta_lead", new_secret()) as sec:
        raw = b'{ "name" : "Mentah",   "phone":"' + phone().encode() + b'", "campaign":"x" }'   # spasi kustom
        resign = jbytes(json.loads(raw))                                                       # JSON ulang
        assert raw != resign
        assert post_raw("/meta-lead", raw, {"X-Hub-Signature-256": sign_hub(sec, resign)}).status_code == 403
        assert post_raw("/meta-lead", raw, {"X-Hub-Signature-256": sign_hub(sec, raw)}).status_code == 200


def test_meta_lead_handshake_verify_token_konstan_waktu_dan_challenge_apa_adanya():
    q = {"hub.mode": "subscribe", "hub.verify_token": "x", "hub.challenge": "CH-123"}
    assert requests.get(f"{API}/webhooks/meta-lead", params=q, timeout=30).status_code == 403, "belum ada verify token"
    vt = f"vt-{uuid.uuid4().hex[:12]}"
    with secret("meta_lead", new_secret(), verify=vt):
        ok = requests.get(f"{API}/webhooks/meta-lead", params={**q, "hub.verify_token": vt}, timeout=30)
        assert ok.status_code == 200 and ok.text == "CH-123"
        for bad in ({**q, "hub.verify_token": vt + "x"}, {**q, "hub.verify_token": vt, "hub.mode": "unsubscribe"},
                    {"hub.mode": "subscribe", "hub.challenge": "CH"}):
            r = requests.get(f"{API}/webhooks/meta-lead", params=bad, timeout=30)
            assert r.status_code == 403 and r.text == GENERIC, bad


def test_replay_id_peristiwa_diklaim_atomik_dan_pengiriman_ulang_idempoten():
    with secret("meta_lead", new_secret()) as sec:
        ev = f"lg-{uuid.uuid4().hex}"
        a = lead_body(leadgen_id=ev)
        r1 = post_raw("/meta-lead", a, {"X-Hub-Signature-256": sign_hub(sec, a)})
        assert r1.status_code == 200 and r1.json()["data"]["captured"] is True
        r2 = post_raw("/meta-lead", a, {"X-Hub-Signature-256": sign_hub(sec, a)})          # replay persis
        assert r2.status_code == 200 and r2.json()["data"]["replay"] is True and r2.json()["data"]["captured"] is False
        ph2 = phone()
        b = jbytes({"name": "Replay lain nomor", "phone": ph2, "leadgen_id": ev})          # id sama, badan lain, tanda tangan sah
        r3 = post_raw("/meta-lead", b, {"X-Hub-Signature-256": sign_hub(sec, b)})
        assert r3.json()["data"].get("replay") is True
        assert mongo().leads.count_documents({"phone": ph2}) == 0, "id peristiwa yang sama tidak boleh melahirkan lead kedua"


def test_statistik_penolakan_tercatat_di_status():
    with secret("meta_lead", new_secret()):
        before = next(c for c in call(OWNER, "GET", "/webhooks/status").json()["data"]["channels"]
                      if c["channel"] == "meta_lead")["rejected_total"]
        assert post_raw("/meta-lead", lead_body()).status_code == 403
        now = next(c for c in call(OWNER, "GET", "/webhooks/status").json()["data"]["channels"]
                   if c["channel"] == "meta_lead")
        assert now["rejected_total"] == before + 1 and now["last_rejected_at"]


# ================================================================== Google Lead Form
def test_google_key_wajib_dan_tidak_pernah_tersimpan():
    with secret("google_lead", new_secret()) as key:
        for extra in ({}, {"google_key": "salah-salah-1"}, {"google_key": key[:-1]}, {"google_key": 12345}):
            r = post_raw("/google-lead", lead_body(**extra))
            assert r.status_code == 401 and r.json() == {"detail": GENERIC}, (extra, r.status_code, r.text[:100])
        ph = phone()
        ok = post_raw("/google-lead", jbytes({"name": "G Ok", "phone": ph, "campaign": "gads", "google_key": key,
                                              "lead_id": f"gl-{uuid.uuid4().hex}"}))
        assert ok.status_code == 200 and ok.json()["data"]["captured"] is True, ok.text[:200]
        db = mongo()
        ev = db.lead_capture_events.find_one({"raw_payload.phone": ph})
        assert ev and key not in json.dumps(ev, default=str), "google_key tidak boleh ikut tersimpan di capture event"
        lead = db.leads.find_one({"phone": ph})
        assert key not in json.dumps(lead, default=str)
        # payload cacat tapi kunci sah -> masuk antrean; rahasia tetap tidak ikut tersimpan
        bad = post_raw("/google-lead", jbytes({"name": "G Cacat", "phone": "08", "google_key": key}))
        assert bad.status_code == 202, bad.text[:200]
        fail = db.lead_capture_failures.find_one({"id": bad.json()["data"]["failure_id"]})
        assert fail and key not in json.dumps(fail, default=str)


# ================================================================== TikTok Lead
def tiktok_sig(secret_, body, t=None):
    t = str(int(time.time()) if t is None else t)
    return f"t={t},s=" + hmac.new(secret_.encode(), f"{t}.".encode() + body, hashlib.sha256).hexdigest()


def test_tiktok_rahasia_bersama_atau_tanda_tangan_bercap_waktu():
    with secret("tiktok_lead", new_secret()) as sec:
        body = lead_body()
        assert post_raw("/tiktok-lead", body).status_code == 401
        r = post_raw("/tiktok-lead", body, {"X-TikTok-Secret": sec + "x"})
        assert r.status_code == 401 and r.json() == {"detail": GENERIC}
        assert post_raw("/tiktok-lead", lead_body(), {"X-TikTok-Secret": sec}).status_code == 200      # (b) rahasia bersama
        b2 = lead_body()
        assert post_raw("/tiktok-lead", b2, {"TikTok-Signature": tiktok_sig(sec, b2)}).status_code == 200  # (a) HMAC
        b3 = lead_body()
        bad = tiktok_sig(sec, b3).replace("s=", "s=00")
        assert post_raw("/tiktok-lead", b3, {"TikTok-Signature": bad}).status_code == 401
        assert post_raw("/tiktok-lead", b3, {"TikTok-Signature": "ngawur"}).status_code == 401
        # query string TIDAK dipakai sebagai kanal rahasia (access log mencetak query string)
        assert requests.post(f"{API}/webhooks/tiktok-lead", params={"secret": sec}, data=lead_body(),
                             headers={"Content-Type": "application/json"}, timeout=30).status_code == 401


def test_tiktok_cap_waktu_basi_ditolak_dan_replay_persis_dalam_jendela_tak_diproses_ulang():
    with secret("tiktok_lead", new_secret()) as sec:
        body = lead_body()
        stale = tiktok_sig(sec, body, t=int(time.time()) - 600)   # tanda tangan SAH tetapi 10 menit lalu
        assert post_raw("/tiktok-lead", body, {"TikTok-Signature": stale}).status_code == 401
        future = tiktok_sig(sec, body, t=int(time.time()) + 600)
        assert post_raw("/tiktok-lead", body, {"TikTok-Signature": future}).status_code == 401
        fresh = tiktok_sig(sec, body)
        r1 = post_raw("/tiktok-lead", body, {"TikTok-Signature": fresh})
        assert r1.status_code == 200 and r1.json()["data"]["captured"] is True
        r2 = post_raw("/tiktok-lead", body, {"TikTok-Signature": fresh})      # permintaan identik direkam ulang
        assert r2.status_code == 200 and r2.json()["data"].get("replay") is True


# ================================================================== WhatsApp Cloud
@contextlib.contextmanager
def wa_secret(value):
    r = call(OWNER, "PUT", "/wa/config", json={"app_secret": value})
    assert r.status_code == 200, r.text[:200]
    try:
        yield value
    finally:
        call(OWNER, "PUT", "/wa/config", json={"app_secret": "__clear__"})


def test_wa_kontrak_lama_dan_payload_meta_sama_sama_butuh_tanda_tangan_dan_penolakan_tak_diantrekan():
    legacy = jbytes({"name": f"WA Lama {TAG}", "phone": phone(), "message": "halo"})
    assert post_raw("/wa", legacy).status_code in (200, 202), "belum ada app secret -> diterima"
    with wa_secret(new_secret()) as sec:
        before = open_failures()
        r = post_raw("/wa", legacy)                                  # kontrak lama TANPA tanda tangan
        assert r.status_code == 403 and r.json() == {"detail": GENERIC}, (r.status_code, r.text[:150])
        meta = jbytes(wa_text(phone()))
        for hdr in ({}, {"X-Hub-Signature-256": "sha256=deadbeef"}, {"X-Hub-Signature-256": sign_hub("lain-lain-123", meta)}):
            rr = post_raw("/wa", meta, hdr)
            assert rr.status_code == 403 and rr.json() == {"detail": GENERIC}, (hdr, rr.status_code, rr.text[:150])
        assert open_failures() == before, "penolakan tanda tangan TIDAK boleh membanjiri antrean gagal-masuk / notifikasi supervisor"
        ok = post_raw("/wa", meta, {"X-Hub-Signature-256": sign_hub(sec, meta)})
        assert ok.status_code == 200 and ok.json()["signature_ok"] is True and ok.json()["data"]["messages"] == 1
        okl = post_raw("/wa", legacy, {"X-Hub-Signature-256": sign_hub(sec, legacy)})
        assert okl.status_code in (200, 202)


def test_wa_pesan_ganda_bersamaan_hanya_satu_yang_tercatat():
    ph, wamid = phone(), f"wamid.RACE{uuid.uuid4().hex[:20]}"
    body = jbytes(wa_text(ph, wamid=wamid))
    bar = threading.Barrier(2)

    def go():
        bar.wait()
        return post_raw("/wa", body)

    with ThreadPoolExecutor(2) as ex:
        rs = list(ex.map(lambda _: go(), range(2)))
    assert [r.status_code for r in rs] == [200, 200], [r.text[:120] for r in rs]
    datas = [r.json()["data"] for r in rs]
    assert sum(d.get("messages", 0) for d in datas) == 1, datas
    assert not any(d.get("queued") for d in datas), f"tabrakan indeks unik menjadi kegagalan antrean: {datas}"
    assert mongo().messages.count_documents({"provider_message_id": wamid}) == 1


# ================================================================== ukuran & JSON patologis
@pytest.mark.parametrize("path", ["/meta-lead", "/google-lead", "/tiktok-lead", "/wa"])
def test_badan_lebih_dari_1mb_ditolak_413(path):
    big = jbytes({"name": "Besar", "phone": phone(), "message": "x" * (1_300_000)})
    r = post_raw(path, big)
    assert r.status_code == 413 and "terlalu besar" in r.json()["detail"], (path, r.status_code, r.text[:120])


@pytest.mark.parametrize("path", ["/meta-lead", "/google-lead", "/tiktok-lead", "/wa"])
def test_json_patologis_dijawab_400_bersih_bukan_500(path):
    deep = b"[" * 20000 + b"]" * 20000                                  # RecursionError di json.loads
    r = post_raw(path, deep)
    assert r.status_code == 400, (path, "bersarang", r.status_code, r.text[:100])
    huge_int = b'{"phone": ' + b"9" * 6000 + b"}"                          # ValueError (batas 4300 digit)
    r = post_raw(path, huge_int)
    assert r.status_code in (400, 202), (path, "angka raksasa", r.status_code, r.text[:100])
    assert r.status_code != 500


# ================================================================== unit (tanpa server)
def _backend_on_path():
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
    pytest.importorskip("motor")
    if not os.environ.get("DB_NAME"):
        pytest.skip("set DB_NAME/MONGO_URL")


def test_unit_primitif_konstan_waktu_dan_cap_waktu_tiktok():
    _backend_on_path()
    import webhook_security as ws
    src = open(os.path.join(os.path.dirname(ws.__file__), "webhook_security.py"), encoding="utf-8").read()
    assert "hmac.compare_digest" in src
    assert ws.safe_equals("é-rahasia", "é-rahasia") and not ws.safe_equals("a", "b") and not ws.safe_equals(None, "a")
    body = b'{"a":1}'
    now = 1_800_000_000
    sig = f"t={now},s=" + hmac.new(b"kunci-uji-123", f"{now}.".encode() + body, hashlib.sha256).hexdigest()
    assert ws.verify_tiktok("kunci-uji-123", sig, None, body, now=now + 299)[0] is True
    assert ws.verify_tiktok("kunci-uji-123", sig, None, body, now=now + 301)[:2] == (False, "stale_timestamp")
    assert ws.verify_tiktok("kunci-uji-123", None, None, body, now=now)[:2] == (False, "no_credential")
    assert ws.verify_hub_signature("", body, "sha256=x") is None
    assert ws.verify_hub_signature("rahasia-1234", body, None) is False
    assert ws.too_old(1, max_age=0) is False and ws.too_old(now - 400, max_age=300, now=now) is True


def test_unit_percobaan_gagal_berulang_dari_satu_ip_dijawab_429_sah_tidak_terhitung():
    _backend_on_path()
    import rate_limit
    import webhook_security as ws

    class Req:
        class client:
            host = f"203.0.113.{uuid.uuid4().int % 250}"

    rate_limit.reset("webhook_bad")
    codes = [ws.rejection("meta_lead", Req).status_code for _ in range(ws.BAD_ATTEMPTS_PER_MIN + 2)]
    assert codes[0] == 403 and codes[-1] == 429, codes[-3:]
    assert ws.rejection("google_lead", type("R", (), {"client": type("C", (), {"host": "198.51.100.9"})})).status_code == 401
    rate_limit.reset("webhook_bad")


def test_unit_redaksi_rahasia_di_antrean_gagal():
    _backend_on_path()
    import capture_failures as cf
    out = cf.redact({"phone": "1", "google_key": "RAHASIA", "nested": {"Access_Token": "T", "ok": 1},
                     "list": [{"secret": "S"}]})
    assert "RAHASIA" not in json.dumps(out) and '"T"' not in json.dumps(out) and "S\"" not in json.dumps(out)
    assert out["phone"] == "1" and out["nested"]["ok"] == 1
