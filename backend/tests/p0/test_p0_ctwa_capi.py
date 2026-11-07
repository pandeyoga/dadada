"""Regresi G-D (2) — ATRIBUSI Click-to-WhatsApp (`ctwa_clid`) + CAPI for Business Messaging.

Temuan audit 09 §4 celah 5: webhook WhatsApp membuang `referral` (ctwa_clid, source_id, ...) dari pesan pertama
setelah klik iklan, dan `capi.py` mengirim konversi ke Pixel dengan `action_source: system_generated` — format yang
salah untuk percakapan WhatsApp. Tes ini membuktikan: (1) referral disimpan idempoten (pertama menang, tak bocor ke lead
lain, tampil sebagai `attribution.ctwa` pada lead & percakapan), (2) peristiwa konversi lead ber-ctwa dikirim sebagai
Business Messaging (`business_messaging` + `whatsapp` + `user_data{whatsapp_business_account_id, ctwa_clid}` + event_id
deterministik), simulasi/dry-run mencatat payload TANPA panggilan jaringan, dan jalur live diuji dengan pengirim PALSU.

    API_BASE=http://localhost:8074/api DB_NAME=<db> MONGO_URL=<url> python -m pytest \
        backend/tests/p0/test_p0_ctwa_capi.py -n 0 --noconftest -q -p no:cacheprovider
"""
import asyncio
import hashlib
import os
import sys
import time
import uuid

import pytest
import requests

API = os.environ.get("API_BASE", "http://localhost:8074/api").rstrip("/")
PW = "Sipro#2026"
OWNER = "owner@sipro.co.id"
TAG = uuid.uuid4().hex[:6]
WABA = "WABA-GD-CTWA"
_tokens = {}


# ------------------------------------------------------------------ pembantu HTTP
def _login(email):
    if email not in _tokens:
        r = requests.post(f"{API}/auth/login", json={"email": email, "password": PW}, timeout=30)
        assert r.status_code == 200, f"login {email}: {r.status_code}"
        _tokens[email] = r.json()["access_token"]
    return _tokens[email]


def call(method, path, **kw):
    return requests.request(method, f"{API}{path}", headers={"Authorization": f"Bearer {_login(OWNER)}"},
                            timeout=60, **kw)


def phone():
    return "+62816" + str(uuid.uuid4().int)[:8]


def new_clid():
    return "AR" + uuid.uuid4().hex + uuid.uuid4().hex[:10]


def referral(clid, **kw):
    r = {"source_url": f"https://fb.me/{TAG}", "source_id": "120200000000" + TAG[:3].upper().replace("-", "0"),
         "source_type": "ad", "headline": f"Rumah Subsidi {TAG}", "body": "Cicilan ringan DP 0%",
         "media_type": "image", "image_url": f"https://cdn.example.com/{TAG}.jpg", "ctwa_clid": clid}
    r.update(kw)
    return r


def wa_payload(ph, text, ref=None, wamid=None, waba=WABA):
    msg = {"from": ph.lstrip("+"), "id": wamid or f"wamid.CT{uuid.uuid4().hex[:24]}",
           "timestamp": str(int(time.time())), "type": "text", "text": {"body": text}}
    if ref is not None:
        msg["referral"] = ref
    return {"object": "whatsapp_business_account", "entry": [{"id": waba, "changes": [{"field": "messages", "value": {
        "messaging_product": "whatsapp", "metadata": {"phone_number_id": "PN-GD"},
        "contacts": [{"profile": {"name": f"Ctwa {TAG}"}, "wa_id": ph.lstrip("+")}], "messages": [msg]}}]}]}


def send(ph, text="Halo, saya lihat iklannya", ref=None, wamid=None):
    r = requests.post(f"{API}/webhooks/wa", json=wa_payload(ph, text, ref, wamid), timeout=60)
    assert r.status_code == 200, f"{r.status_code} {r.text[:200]}"
    return r.json()["data"]


def conv_of(ph):
    rows = call("GET", "/inbox", params={"q": ph.lstrip("+"), "limit": 20}).json()["data"]
    return next((c for c in rows if c["contact_phone"] == ph), None)


def contact_id(ph):
    rows = call("GET", "/wa/contacts", params={"q": ph}).json()["data"]
    return next(c["id"] for c in rows if c["phone"] == ph)


def capture(ph):
    r = call("POST", "/wa/contacts/capture", json={"ids": [contact_id(ph)]})
    assert r.status_code == 200 and r.json()["data"]["created"] == 1, r.text[:300]
    return r.json()["data"]["lead_ids"][0]


def lead(lead_id):
    r = call("GET", f"/leads/{lead_id}")
    assert r.status_code == 200, r.text[:200]
    return r.json()["data"]


def ctwa_of(doc):
    return ((doc or {}).get("attribution") or {}).get("ctwa")


def capi_rows(lead_id):
    rows = call("GET", "/ads/capi/events", params={"platform": "meta", "limit": 100}).json()["data"]
    return [x for x in rows if x.get("lead_id") == lead_id]


# ================================================================== 1. penangkapan referral
def test_referral_pesan_pertama_disimpan_pada_percakapan_dan_diwarisi_lead():
    ph, clid = phone(), new_clid()
    d = send(ph, ref=referral(clid))
    assert d["messages"] == 1
    c = ctwa_of(conv_of(ph))
    assert c, "percakapan harus memuat attribution.ctwa"
    assert c["ctwa_clid"] == clid and c["source_type"] == "ad" and c["headline"].startswith("Rumah Subsidi")
    assert c["source_url"].startswith("https://fb.me/") and c["media_url"].endswith(".jpg")
    assert c["body"] == "Cicilan ringan DP 0%" and c["media_type"] == "image"
    assert c["waba_id"] == WABA and c["phone_number_id"] == "PN-GD" and c["wamid"] and c["captured_at"]
    lid = capture(ph)
    got = ctwa_of(lead(lid))
    assert got and got["ctwa_clid"] == clid and got["source_id"] == c["source_id"], "lead lahir sesudah percakapan harus mewarisi"


def test_lead_yang_sudah_ada_menerima_atribusi_dari_pesan_berreferral():
    ph, clid = phone(), new_clid()
    r = call("POST", "/leads", json={"name": f"Lead Lebih Dulu {TAG}", "phone": ph, "source": "manual"})
    assert r.status_code == 200, r.text[:200]
    lid = r.json()["data"]["id"]
    assert ctwa_of(lead(lid)) is None
    send(ph, ref=referral(clid))
    assert ctwa_of(lead(lid))["ctwa_clid"] == clid
    assert ctwa_of(conv_of(ph))["ctwa_clid"] == clid


def test_pertama_menang_idempoten_dan_tidak_menimpa():
    ph, clid1, clid2 = phone(), new_clid(), new_clid()
    wamid = f"wamid.CT1{uuid.uuid4().hex[:20]}"
    send(ph, ref=referral(clid1, headline="IKLAN PERTAMA"), wamid=wamid)
    lid = capture(ph)
    again = send(ph, ref=referral(clid1, headline="IKLAN PERTAMA"), wamid=wamid)       # webhook yang sama diulang
    assert again["duplicates"] == 1 and again["messages"] == 0
    send(ph, text="klik iklan lagi", ref=referral(clid2, headline="IKLAN KEDUA"))      # klik iklan lain
    for doc in (conv_of(ph), lead(lid)):
        c = ctwa_of(doc)
        assert c["ctwa_clid"] == clid1 and c["headline"] == "IKLAN PERTAMA", "atribusi pertama tidak boleh tertimpa"


def test_atribusi_tidak_bocor_ke_lead_lain():
    a, b, c_ph = phone(), phone(), phone()
    clid_a, clid_c = new_clid(), new_clid()
    send(a, ref=referral(clid_a))
    send(b, text="saya tanya langsung tanpa iklan")
    send(c_ph, ref=referral(clid_c))
    la, lb, lc = capture(a), capture(b), capture(c_ph)
    assert ctwa_of(lead(la))["ctwa_clid"] == clid_a
    assert ctwa_of(lead(lc))["ctwa_clid"] == clid_c
    assert ctwa_of(lead(lb)) is None, "lead tanpa klik iklan tidak boleh mewarisi atribusi nomor lain"
    assert ctwa_of(conv_of(b)) is None


def test_clid_tidak_valid_tidak_disimpan_dan_referral_kosong_diabaikan():
    ph = phone()
    send(ph, ref=referral("<script>alert(1)</script>", source_id="SRC-1"))
    c = ctwa_of(conv_of(ph))
    assert c and c["ctwa_clid"] is None and c["source_id"] == "SRC-1"
    ph2 = phone()
    send(ph2, ref={"foo": "bar", "headline": "tanpa id"})
    assert ctwa_of(conv_of(ph2)) is None


def test_auto_capture_lead_lahir_sudah_beratribusi_dan_event_capi_percakapan_tercatat():
    ph, clid = phone(), new_clid()
    r = call("PUT", "/settings/wa.auto_capture_lead", json={"value": True, "reason": "uji G-D CTWA"})
    assert r.status_code == 200, r.text[:200]
    try:
        d = send(ph, ref=referral(clid))
        assert d["captured"] == 1, d
    finally:
        call("POST", "/settings/wa.auto_capture_lead/reset")
    lid = next(x["id"] for x in call("GET", "/leads", params={"q": ph}).json()["data"] if x["phone"] == ph)
    assert ctwa_of(lead(lid))["ctwa_clid"] == clid
    rows = _await_rows(lid)
    assert rows and rows[0]["event_name"] == "Lead"


def _await_rows(lid, tries=20):
    for _ in range(tries):
        rows = capi_rows(lid)
        if rows:
            return rows
        time.sleep(0.5)
    return []


# ================================================================== 2. CAPI Business Messaging (HTTP, simulasi)
def test_event_lead_ctwa_dikirim_sebagai_business_messaging_dalam_simulasi():
    ph, clid = phone(), new_clid()
    send(ph, ref=referral(clid))
    lid = capture(ph)
    rows = _await_rows(lid)
    assert len(rows) == 1, rows
    ev = rows[0]
    assert ev["action_source"] == "business_messaging" and ev["messaging_channel"] == "whatsapp"
    assert ev["status"] == "simulated" and ev["transport"] == "simulation", "tanpa token: simulasi, bukan 'sent'"
    assert ev["ctwa_clid"] == clid and ev["platform"] == "meta" and ev["event_name"] == "Lead"
    data = ev["payload"]["data"][0]
    assert data["action_source"] == "business_messaging" and data["messaging_channel"] == "whatsapp"
    assert data["user_data"] == {"whatsapp_business_account_id": WABA, "ctwa_clid": clid}
    assert data["event_name"] == "Lead" and data["event_id"] == ev["event_id"] and len(ev["event_id"]) == 32
    assert isinstance(data["event_time"], int)
    assert "dry-run" in ev["message"].lower() or "simulasi" in ev["message"].lower()
    res = call("POST", f"/ads/capi/events/{ev['id']}/resend")
    assert res.status_code == 400, "simulasi tidak punya apa pun untuk dikirim ulang"
    assert len(capi_rows(lid)) == 1


def test_lead_whatsapp_tanpa_ctwa_tetap_event_klasik_bukan_business_messaging():
    ph = phone()
    send(ph)                                   # tanpa referral
    lid = capture(ph)
    rows = _await_rows(lid)
    assert rows and all(r.get("action_source") != "business_messaging" for r in rows)
    assert all("ctwa_clid" not in r or not r.get("ctwa_clid") for r in rows)


# ================================================================== 3. unit/in-process (pengirim palsu, tanpa jaringan)
_LOOP = None


def _run(coro):
    global _LOOP
    if _LOOP is None:
        _LOOP = asyncio.new_event_loop()
    return _LOOP.run_until_complete(coro)


@pytest.fixture
def be(monkeypatch):
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
    pytest.importorskip("motor")
    if not os.environ.get("DB_NAME"):
        pytest.skip("set DB_NAME/MONGO_URL")
    import capi
    import capi_hooks
    import ctwa
    from db import db, ORG_ID

    for n in ("META_CAPI_TOKEN", "META_CAPI_DATASET_ID", "META_PIXEL_ID"):
        monkeypatch.delenv(n, raising=False)
    calls = []

    async def forbidden(url, payload, token):
        raise AssertionError("TIDAK boleh ada panggilan jaringan di mode simulasi")

    monkeypatch.setattr(capi, "_post_json", forbidden)
    created = []

    class B:
        pass
    b = B()
    b.capi, b.hooks, b.ctwa, b.db, b.org, b.calls, b.mp = capi, capi_hooks, ctwa, db, ORG_ID, calls, monkeypatch
    b.created = created

    def live(status=200, body=None):
        monkeypatch.setenv("META_CAPI_TOKEN", "tok-uji-bukan-rahasia")
        monkeypatch.setenv("META_CAPI_DATASET_ID", "DS-UJI-1")

        async def fake(url, payload, token):
            calls.append({"url": url, "payload": payload, "token": token})
            return status, (body if body is not None else {"events_received": 1})
        monkeypatch.setattr(capi, "_post_json", fake)
    b.live = live
    yield b
    from pymongo import MongoClient
    sync = MongoClient(os.environ.get("MONGO_URL") or "mongo" + "db://127.0.0.1:27017")[os.environ["DB_NAME"]]
    for lid in created:
        sync.conversion_events.delete_many({"lead_id": lid})
        sync.deals.delete_many({"lead_id": lid})
        sync.leads.delete_many({"id": lid})


def _lead(be, *, clid=None, source="whatsapp", waba="WABA-UJI-9"):
    lid = f"gd-{uuid.uuid4().hex[:12]}"
    doc = {"id": lid, "org_id": be.org, "name": "Uji CTWA", "phone": phone(), "source": source, "campaign": "gd",
           "attribution": {}}
    if clid:
        doc["attribution"]["ctwa"] = {"ctwa_clid": clid, "waba_id": waba, "source_id": "AD-1"}
    be.created.append(lid)
    return doc


def test_unit_normalisasi_referral_dan_event_id_deterministik(be):
    n = be.ctwa.normalize({"ctwa_clid": "ABCDEFGH12345678", "source_id": 12345, "source_url": "javascript:alert(1)",
                           "video_url": "https://cdn/x.mp4", "welcome_message": {"text": "Halo"}, "headline": "H" * 999})
    assert n["ctwa_clid"] == "ABCDEFGH12345678" and n["source_id"] == "12345"
    assert n["source_url"] is None, "skema non-http harus dibuang"
    assert n["media_url"] == "https://cdn/x.mp4" and n["welcome_text"] == "Halo" and len(n["headline"]) == 300
    assert be.ctwa.normalize({"ctwa_clid": "bad clid!"}) is None and be.ctwa.normalize("x") is None
    f = be.capi.bm_event_id
    a = f(org_id="o", platform_event="Lead", ctwa_clid="C1")
    assert a == f(org_id="o", platform_event="Lead", ctwa_clid="C1") and len(a) == 32
    assert a != f(org_id="o", platform_event="Lead", ctwa_clid="C2")
    assert a != f(org_id="o", platform_event="Purchase", ctwa_clid="C1")
    assert f(org_id="o", platform_event="Purchase", ctwa_clid="C1", deal_id="D1") != \
        f(org_id="o", platform_event="Purchase", ctwa_clid="C1", deal_id="D2")


def test_unit_simulasi_mencatat_payload_tanpa_jaringan(be):
    clid = new_clid()
    lead_doc = _lead(be, clid=clid)
    doc = _run(be.capi.record_conversion(event_name="Lead", lead=lead_doc, org_id=be.org))
    assert doc["status"] == "simulated" and doc["transport"] == "simulation"
    d = doc["payload"]["data"][0]
    assert d["action_source"] == "business_messaging" and d["messaging_channel"] == "whatsapp"
    assert d["user_data"] == {"whatsapp_business_account_id": "WABA-UJI-9", "ctwa_clid": clid}
    assert "custom_data" not in d, "Lead tanpa nilai tidak membawa custom_data"
    again = _run(be.capi.record_conversion(event_name="Lead", lead=lead_doc, org_id=be.org))
    assert again["duplicate"] is True and again["event_id"] == doc["event_id"]


def test_unit_live_kirim_format_business_messaging_ke_dataset_dan_dedup_dua_pemicu_bersamaan(be):
    be.live()
    clid = new_clid()
    lead_doc = _lead(be, clid=clid)
    deal = {"id": f"gd-deal-{uuid.uuid4().hex[:8]}", "price": 750_000_000}

    async def both():
        return await asyncio.gather(
            be.capi.record_conversion(event_name="Purchase", lead=lead_doc, deal=deal, value=750_000_000, org_id=be.org),
            be.capi.record_conversion(event_name="Purchase", lead=lead_doc, deal=deal, value=750_000_000, org_id=be.org))
    a, b2 = _run(both())
    assert sorted([bool(a.get("duplicate")), bool(b2.get("duplicate"))]) == [False, True], "satu pemenang, satu duplikat"
    assert len(be.calls) == 1, f"event yang sama dikirim {len(be.calls)}x"
    call_ = be.calls[0]
    assert call_["url"].endswith("/DS-UJI-1/events") and call_["token"] == "tok-uji-bukan-rahasia"
    d = call_["payload"]["data"][0]
    assert d["event_name"] == "Purchase" and d["action_source"] == "business_messaging"
    assert d["messaging_channel"] == "whatsapp"
    assert d["user_data"] == {"whatsapp_business_account_id": "WABA-UJI-9", "ctwa_clid": clid}
    assert d["custom_data"] == {"value": 750_000_000, "currency": "IDR"}
    exp = hashlib.sha256(f"{be.org}|bm|Purchase|{clid}|{deal['id']}".encode()).hexdigest()[:32]
    assert d["event_id"] == exp, "event_id harus deterministik dari (org, event Meta, ctwa_clid, deal)"
    row = _run(be.db.conversion_events.find_one({"event_id": exp, "org_id": be.org}, {"_id": 0}))
    assert row["status"] == "sent" and row["attempts"] == 1 and row["transport"] == "live"


def test_unit_gagal_kirim_dicatat_dan_kirim_ulang_berhasil(be):
    be.live(status=400, body={"error": {"message": "Invalid dataset"}})
    lead_doc = _lead(be, clid=new_clid())
    doc = _run(be.capi.record_conversion(event_name="SubmitApplication", lead=lead_doc, org_id=be.org))
    assert doc["status"] == "failed" and "Invalid dataset" in doc["message"]
    assert doc["payload"]["data"][0]["event_name"] == "QualifiedLead", "SPR ditandatangani = lead berkualitas"
    be.live(status=200)
    res = _run(be.capi.resend_conversion(doc["id"], org_id=be.org, actor="uji"))
    assert res["status"] == "sent" and res["attempts"] == 2
    assert be.calls[-1]["payload"]["data"][0]["event_id"] == doc["event_id"], "kirim ulang memakai event_id yang sama"


def test_unit_tanpa_dataset_atau_waba_event_menunggu_bukan_dikirim_setengah(be):
    be.live()
    be.mp.delenv("META_CAPI_DATASET_ID")
    lead_doc = _lead(be, clid=new_clid())
    doc = _run(be.capi.record_conversion(event_name="Lead", lead=lead_doc, org_id=be.org))
    assert doc["status"] == "pending" and "DATASET" in doc["message"].upper() and not be.calls
    be.live()
    lead2 = _lead(be, clid=new_clid(), waba="SIM-WABA")        # id entri simulasi bukan WABA sungguhan
    doc2 = _run(be.capi.record_conversion(event_name="Lead", lead=lead2, org_id=be.org))
    assert doc2["status"] == "pending" and not be.calls, "tanpa WABA ID nyata tidak boleh ada paket keluar"


def test_unit_pemicu_capi_hooks_yang_ada_dipakai_untuk_booking_dan_won(be):
    lead_doc = _lead(be, clid=new_clid())
    _run(be.db.leads.insert_one(dict(lead_doc)))
    deal = {"id": f"gd-deal-{uuid.uuid4().hex[:8]}", "org_id": be.org, "lead_id": lead_doc["id"], "price": 500_000_000}
    _run(be.db.deals.insert_one(dict(deal)))
    try:
        _run(be.hooks.on_deal_booked({"entity_id": deal["id"], "org_id": be.org}))
        _run(be.hooks.on_deal_sold({"entity_id": deal["id"], "org_id": be.org}))
        rows = _run(be.db.conversion_events.find({"lead_id": lead_doc["id"]}, {"_id": 0}).to_list(10))
    finally:
        _run(be.db.deals.delete_many({"id": deal["id"]}))
    by = {r["event_name"]: r for r in rows}
    assert set(by) == {"InitiateCheckout", "Purchase"}, list(by)
    for r in rows:
        assert r["action_source"] == "business_messaging" and r["messaging_channel"] == "whatsapp"
    assert by["Purchase"]["value"] == 500_000_000
    assert by["Purchase"]["payload"]["data"][0]["custom_data"]["value"] == 500_000_000


def test_unit_lead_lain_tidak_mewarisi_ctwa_nomor_lain(be):
    ph_a, ph_b = phone(), phone()
    conv_id = f"gd-conv-{uuid.uuid4().hex[:8]}"
    _run(be.db.conversations.insert_one({"id": conv_id, "org_id": be.org, "channel": "whatsapp", "contact_phone": ph_a,
                                         "created_at": "2026-01-01T00:00:00+00:00",
                                         "attribution": {"ctwa": {"ctwa_clid": new_clid(), "waba_id": "W"}}}))
    try:
        assert _run(be.ctwa.from_conversation(be.org, phone=ph_a)) is not None
        assert _run(be.ctwa.from_conversation(be.org, phone=ph_b)) is None
        assert _run(be.ctwa.from_conversation("org-lain", phone=ph_a)) is None, "lintas organisasi tidak boleh bocor"
        lead_b = {"id": f"gd-{uuid.uuid4().hex[:8]}", "phone": ph_b, "source": "whatsapp", "attribution": {}}
        assert _run(be.ctwa.resolve(lead_b, be.org)) is None
    finally:
        _run(be.db.conversations.delete_many({"id": conv_id}))
