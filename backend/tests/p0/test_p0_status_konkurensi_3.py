"""Regresi G-B (3/3) — siklus tugas Work Hub, perizinan, fee marketing ganda, impor massal, status unit saat booking
(audit PK3-16, PK3-17, PK3-20, PK3-21, FZ-05).

    API_BASE=http://localhost:8072/api python -m pytest backend/tests/p0/test_p0_status_konkurensi_3.py -n 0 -q --noconftest
"""
import io
import uuid
from datetime import date, timedelta

import pytest
import requests

from test_p0_masuk import API, FINANCE, OWNER, SALES, SUPER, World, _login, call, codes, ok, race, upload_proof

ROUNDS = 3


def _uid(p="G"):
    return f"{p}{uuid.uuid4().hex[:6].upper()}"


@pytest.fixture(scope="module")
def world():
    return World()


# ================================================================== PK3-16 — siklus tugas Work Hub
def _task(jobdesk=None):
    """Tugas dengan jobdesk (bukti+verifikasi dari katalog)."""
    return ok(call(OWNER, "POST", "/work/tasks", json={
        "title": f"Tugas uji G-B {_uid()}", "assigned_to": OWNER, "jobdesk_code": jobdesk}))["data"]


def _simple_task(world=None):
    """Tugas SEDERHANA (tanpa bukti & verifikasi) — lahir dari janji temu (auto_create_task tanpa jobdesk)."""
    name = f"Lead GB {_uid()}"
    lead = ok(call(OWNER, "POST", "/leads", json={
        "name": name, "phone": "+62814" + str(uuid.uuid4().int)[:9], "source": "manual"}))["data"]["id"]
    at = (date.today() + timedelta(days=7)).isoformat() + "T09:00:00+07:00"
    ok(call(OWNER, "POST", "/appointments", json={"lead_id": lead, "title": "Survey G-B", "scheduled_at": at}))
    rows = ok(call(OWNER, "GET", "/work/tasks", params={"scope": "all", "q": name, "limit": 5}))["data"]
    t = [r for r in rows if name in r["title"] and "Survey" in r["title"]][0]
    assert t["proof_kind"] == "none" and t["verify_mode"] == "none"
    return t


def _t(tid):
    return ok(call(OWNER, "GET", f"/work/tasks/{tid}"))["data"]["task"]


def test_tugas_put_status_done_tidak_melewati_bukti():
    t = _task("TK-06")       # bukti catatan + verifikasi supervisor
    assert t["proof_kind"] != "none" and t["verify_mode"] != "none"
    assert call(OWNER, "POST", f"/work/tasks/{t['id']}/complete", json={}).status_code == 400
    r = call(OWNER, "PUT", f"/work/tasks/{t['id']}", json={"status": "done"})
    assert r.status_code == 400, (r.status_code, r.text[:200])
    assert _t(t["id"])["status"] == "open"
    assert call(OWNER, "PUT", f"/work/tasks/{t['id']}", json={"status": "submitted"}).status_code == 400


def test_tugas_batal_tidak_bisa_diselesaikan_dan_selesai_tidak_bisa_ditunda():
    t = _simple_task()
    ok(call(OWNER, "PUT", f"/work/tasks/{t['id']}", json={"status": "cancelled"}))
    r = call(OWNER, "POST", f"/work/tasks/{t['id']}/complete", json={})
    assert r.status_code == 400, (r.status_code, r.text[:160])
    assert _t(t["id"])["status"] == "cancelled"
    t2 = _simple_task()
    ok(call(OWNER, "POST", f"/work/tasks/{t2['id']}/complete", json={"outcome": "selesai"}))
    r = call(OWNER, "POST", f"/work/tasks/{t2['id']}/snooze", json={"until": "2030-01-01"})
    assert r.status_code == 400, (r.status_code, r.text[:160])
    assert _t(t2["id"])["status"] == "done"
    assert call(OWNER, "PUT", f"/work/tasks/{t2['id']}", json={"status": "open"}).status_code == 400


def test_tugas_selesaikan_serentak_sekali():
    t = _simple_task()
    rs = race([lambda: call(OWNER, "POST", f"/work/tasks/{t['id']}/complete", json={"outcome": f"hasil {i}"})
               for i in range(3)])
    assert codes(rs).count(200) == 1, [(r.status_code, r.text[:100]) for r in rs]
    assert 500 not in codes(rs)
    assert _t(t["id"])["status"] == "done"


# ================================================================== PK3-17 — perizinan
def _permit(world, expiry=None):
    body = {"project_id": world.project_id, "type": "IMB", "name": f"Izin uji {_uid()}"}
    if expiry:
        body["expiry_at"] = expiry
    return ok(call(OWNER, "POST", "/permits", json=body))["data"]["id"]


def _set(pid, status):
    return call(OWNER, "POST", f"/permits/{pid}/status", json={"status": status})


def _walk(pid, *path):
    for s in path:
        ok(_set(pid, s))


def test_izin_tidak_bisa_langsung_disetujui_dan_ditolak_tidak_bisa_diperpanjang(world):
    pid = _permit(world)
    r = _set(pid, "approved")
    assert r.status_code == 400, (r.status_code, r.text[:160])
    _walk(pid, "in_progress", "submitted", "rejected")
    assert _set(pid, "approved").status_code == 400, "rejected → approved langsung ditolak"
    r = call(OWNER, "POST", f"/permits/{pid}/renew", json={"expiry_at": "2031-01-01T00:00:00+00:00"})
    assert r.status_code == 400, (r.status_code, r.text[:160])
    got = ok(call(OWNER, "GET", f"/permits/{pid}"))["data"]
    assert got["status"] == "rejected" and not got.get("approved_at")


def test_izin_setuju_vs_tolak_eksklusif(world):
    for _ in range(ROUNDS):
        pid = _permit(world)
        _walk(pid, "in_progress", "submitted")
        rs = race([lambda: _set(pid, "approved"), lambda: _set(pid, "rejected")])
        assert codes(rs).count(200) == 1, [(r.status_code, r.text[:120]) for r in rs]


def test_pindai_peringatan_izin_serentak_tidak_menggandakan_notifikasi(world):
    ok(call(OWNER, "POST", "/permits/alerts/scan"))         # kuras izin lama yang belum diberi tahu hari ini
    soon = (date.today() + timedelta(days=5)).isoformat() + "T00:00:00+00:00"
    pids = [_permit(world, expiry=soon) for _ in range(6)]
    for pid in pids:
        _walk(pid, "in_progress", "submitted", "approved")
    rs = race([lambda: call(OWNER, "POST", "/permits/alerts/scan") for _ in range(3)])
    assert all(r.status_code == 200 for r in rs), [(r.status_code, r.text[:100]) for r in rs]
    made = sum(r.json()["data"]["alerts"] for r in rs)
    assert made == 6, f"6 izin → 6 peringatan, bukan {made} (dulu ×3)"


# ================================================================== PK3-20 — fee marketing ganda
def test_fee_marketing_serentak_hanya_satu(world):
    agent = ok(call(OWNER, "POST", "/marketing/agents", json={
        "name": f"Agen G-B {_uid()}", "agent_type": "agen_properti"}))["data"]
    deal = world.new_deal(book=True)["deal_id"]
    body = {"agent_id": agent["id"], "deal_id": deal, "basis": "percent", "value": 1.0, "trigger": "booking"}
    rs = race([lambda: call(OWNER, "POST", "/marketing/fees", json=body) for _ in range(3)])
    assert codes(rs).count(200) == 1, [(r.status_code, r.text[:120]) for r in rs]
    assert 500 not in codes(rs)
    rows = ok(call(OWNER, "GET", "/marketing/fees", params={"agent_id": agent["id"]}))["data"]
    assert len([f for f in rows if f["deal_id"] == deal and f["status"] == "submitted"]) == 1


# ================================================================== PK3-21 — impor semua data
def _import_session():
    exp = call(SUPER, "GET", "/data-mgmt/full/export.xlsx", params={"collections": "activities"})
    assert exp.status_code == 200
    r = requests.post(f"{API}/data-mgmt/full/sessions", headers={"Authorization": f"Bearer {_login(SUPER)}"},
                      files={"file": ("g-b.xlsx", io.BytesIO(exp.content),
                                      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                      timeout=90)
    assert r.status_code == 200, r.text[:200]
    sid = r.json()["id"]
    new_id = str(uuid.uuid4())
    edits = [{"sheet": "activities", "row": 9000, "col": c, "value": v} for c, v in (
        ("id", new_id), ("org_id", "org-sipro"), ("entity_type", "gb_uji"), ("entity_id", _uid("E")),
        ("type", "system"), ("body", "baris impor uji G-B"), ("actor", "superadmin@estora.id"),
        ("created_at", "2026-11-07T00:00:00+00:00"))]
    ok(call(SUPER, "PATCH", f"/data-mgmt/full/sessions/{sid}/cells", json={"edits": edits}))
    return sid, new_id, edits[3]["value"]


def test_impor_commit_serentak_hanya_satu_dan_tidak_bisa_diulang():
    sid, new_id, eid = _import_session()
    body = {"mode": "update", "sheets": ["activities"], "skip_errors": True, "confirm": "IMPOR"}
    rs = race([lambda: call(SUPER, "POST", f"/data-mgmt/full/sessions/{sid}/commit", json=body) for _ in range(3)])
    assert codes(rs).count(200) == 1, [(r.status_code, r.text[:140]) for r in rs]
    assert 500 not in codes(rs)
    acts = ok(call(OWNER, "GET", "/activities", params={"entity_type": "gb_uji", "entity_id": eid}))
    assert acts["total"] == 1, f"dokumen ber-id sama muncul {acts['total']}× (dulu 3×)"
    again = call(SUPER, "POST", f"/data-mgmt/full/sessions/{sid}/commit", json=body)
    assert again.status_code == 400, "sesi yang sudah committed tidak boleh di-commit lagi"


# ================================================================== PK3-21 — impor biaya iklan
def test_impor_biaya_iklan_commit_serentak_satu_pemenang():
    name = f"Kampanye GB {_uid()}"
    ok(call(OWNER, "POST", "/ads/campaigns", json={"name": name, "platform": "meta"}))
    day = (date.today() - timedelta(days=1)).isoformat()
    csv = f"date,platform,campaign_name,spend\n{day},meta,{name},150000\n"
    prev = ok(call(OWNER, "POST", "/ads/spend/import", json={"csv_text": csv, "filename": "gb.csv", "dry_run": True}))
    iid = prev["data"]["id"]
    rs = race([lambda: call(OWNER, "POST", f"/ads/spend/import/{iid}/commit") for _ in range(3)])
    assert 500 not in codes(rs), [(r.status_code, r.text[:120]) for r in rs]
    fresh = [r for r in rs if r.status_code == 200 and not r.json().get("already_committed")]
    assert len(fresh) == 1, [(r.status_code, r.text[:100]) for r in rs]


# ================================================================== FZ-05 — status bayar unit saat booking
def test_booking_menurunkan_payment_status_unit_dari_ar_sebenarnya(world):
    d = world.new_deal(book=False)
    did = d["deal_id"]
    ok(call(FINANCE, "POST", f"/finance/ar/{did}/deposit", json={
        "amount": 54_000_000, "proof_file_ids": [upload_proof(FINANCE)], "note": "uji FZ-05"}))
    ok(call(FINANCE, "POST", f"/finance/ar/{did}/schedule", json={"scheme_id": world.scheme["Cash Bertahap (3x)"]}))
    assert ok(call(FINANCE, "GET", f"/finance/ar/{did}"))["data"]["status"] == "partial"
    ok(call(SALES, "POST", f"/deals/{did}/book", json={}))
    units = ok(call(OWNER, "GET", "/units", params={"project_id": world.project_id, "limit": 200}))["data"]
    unit = [u for u in units if u["id"] == d["unit_id"]][0]
    assert unit["status"] == "booked"
    assert unit["payment_status"] == "partial", f"AR sudah terbayar sebagian, bukan {unit['payment_status']}"
