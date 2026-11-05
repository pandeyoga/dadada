"""Regresi audit WA-02/03/07/09 + IN-10 (Inbox & OTP portal).

Jalankan terhadap server hidup:  REACT_APP_BACKEND_URL=http://localhost:8001 pytest backend/tests/p0/test_p0_inbox.py
(atau API_BASE=http://host:port/api)
"""
import os
import time
import uuid

import pytest
import requests

BASE = (os.environ.get("API_BASE") or (os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001").rstrip("/") + "/api")).rstrip("/")


@pytest.fixture(scope="module")
def sa():
    r = requests.post(f"{BASE}/auth/login", json={"email": "superadmin@estora.id", "password": "test1234"}, timeout=30)
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["access_token"]}


@pytest.fixture(scope="module")
def long_conv(sa):
    """Percakapan dengan 130 pesan masuk (dibuat lewat jalur webhook simulasi yang sama dengan Meta)."""
    phone = "+62812" + str(uuid.uuid4().int)[:8]
    for i in range(130):
        r = requests.post(f"{BASE}/wa/simulate/inbound", headers=sa, timeout=30, json={
            "phone": phone, "name": "AUDIT P0 Thread", "message": f"p0-msg-{i+1:03d}", "mtype": "text"})
        assert r.status_code == 200, r.text
    rows = requests.get(f"{BASE}/inbox", headers=sa, params={"q": phone[-8:]}, timeout=30).json()["data"]
    assert rows, "percakapan uji tidak ditemukan lewat pencarian nomor"
    return rows[0]["id"]


def _page(sa, cid, **params):
    r = requests.get(f"{BASE}/inbox/{cid}", headers=sa, params={"mark_read": "false", **params}, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["data"]


def test_latest_messages_shown_not_oldest(sa, long_conv):
    """WA-03: halaman pertama = pesan TERBARU, bukan N pesan tertua."""
    d = _page(sa, long_conv, limit=50)
    bodies = [m["body"] for m in d["messages"]]
    assert bodies[-1] == "p0-msg-130" and bodies[0] == "p0-msg-081" and d["has_more"]


def test_pagination_is_lossless_and_ordered(sa, long_conv):
    """Kursor majemuk: created_at hanya presisi detik, banyak pesan sedetik tidak boleh hilang."""
    seen, before = [], None
    for _ in range(20):
        p = {"limit": 40}
        if before:
            p["before"] = before
        d = _page(sa, long_conv, **p)
        seen = [m["body"] for m in d["messages"]] + seen
        before = d["next_before"]
        if not d["has_more"]:
            break
    assert seen == [f"p0-msg-{i:03d}" for i in range(1, 131)]


def test_search_by_name_and_local_phone(sa, long_conv):
    assert any(c["id"] == long_conv for c in requests.get(f"{BASE}/inbox", headers=sa, params={"q": "AUDIT P0 Thread"}).json()["data"])
    rows = requests.get(f"{BASE}/inbox", headers=sa, params={"q": "zzz-tidak-ada-zzz"}).json()
    assert rows["total"] == 0 and rows["data"] == []


def test_mark_read_only_when_asked(sa, long_conv):
    """WA-07: membuka tanpa mark_read tidak menghapus penanda belum-dibaca."""
    before = [c for c in requests.get(f"{BASE}/inbox", headers=sa, params={"q": "AUDIT P0 Thread"}).json()["data"] if c["id"] == long_conv][0]["unread"]
    assert before > 0
    _page(sa, long_conv, limit=5)  # mark_read=false
    mid = [c for c in requests.get(f"{BASE}/inbox", headers=sa, params={"q": "AUDIT P0 Thread"}).json()["data"] if c["id"] == long_conv][0]["unread"]
    assert mid == before
    requests.get(f"{BASE}/inbox/{long_conv}", headers=sa, params={"limit": 5, "mark_read": "true"})
    after = [c for c in requests.get(f"{BASE}/inbox", headers=sa, params={"q": "AUDIT P0 Thread"}).json()["data"] if c["id"] == long_conv][0]["unread"]
    assert after == 0


def test_unknown_conversation_is_404(sa):
    assert requests.get(f"{BASE}/inbox/{uuid.uuid4()}", headers=sa).status_code == 404


def test_portal_empty_otp_rejected():
    """IN-10: kode kosong tidak pernah diterima (master OTP kosong tidak lagi mencocokkan '')."""
    r = requests.post(f"{BASE}/portal/auth/verify-otp", json={"identifier": "+628121111111", "code": ""}, timeout=30)
    assert r.status_code == 400


def test_automation_template_reply_has_cooldown(sa):
    """Temuan sampingan: pesan masuk beruntun yang cocok kata kunci tidak boleh memicu balasan template yang sama berkali-kali."""
    phone = "+62812" + str(uuid.uuid4().int)[:8]
    for msg in ("Berapa DP-nya ya?", "Cicilan 15 tahun berapa?", "Boleh minta harga lagi"):
        r = requests.post(f"{BASE}/wa/simulate/inbound", headers=sa, timeout=30,
                          json={"phone": phone, "name": "AUDIT P0 Cooldown", "message": msg, "mtype": "text"})
        assert r.status_code == 200, r.text
        time.sleep(1)
    time.sleep(2)
    cid = requests.get(f"{BASE}/inbox", headers=sa, params={"q": phone[-8:]}).json()["data"][0]["id"]
    msgs = _page(sa, cid, limit=50)["messages"]
    outs = [m for m in msgs if m["direction"] == "out"]
    if not outs:
        pytest.skip("aturan otomasi demo tidak aktif pada instance ini")
    assert len(outs) == 1, f"balasan otomatis ganda: {len(outs)}"
