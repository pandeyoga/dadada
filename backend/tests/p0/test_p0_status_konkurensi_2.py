"""Regresi G-B (2/3) — pasangan aksi eksklusif & mesin status: klaim garansi, jadwal bangun, komplain, janji temu,
rekap upah, change order (audit PK3-10, PK3-18, PK3-23).

    API_BASE=http://localhost:8072/api python -m pytest backend/tests/p0/test_p0_status_konkurensi_2.py -n 0 -q --noconftest
"""
import time
import uuid
from datetime import date, timedelta

import pytest

from test_p0_masuk import FINANCE, OWNER, SUPER, World, call, codes, ok, race, upload_proof

ROUNDS = 3


def _uid(p="G"):
    return f"{p}{uuid.uuid4().hex[:6].upper()}"


@pytest.fixture(scope="module")
def world():
    return World()


_unit_cursor = [20]


def _next_unit(world):
    u = world.units[_unit_cursor[0]]
    _unit_cursor[0] += 1
    return u


# ================================================================== klaim garansi (PK3-18)
def _claim(world):
    unit = _next_unit(world)
    ok(call(OWNER, "POST", "/handover/issue", json={
        "unit_id": unit["id"], "override": True, "override_reason": "uji G-B garansi", "received_by": "Uji"}))
    c = ok(call(OWNER, "POST", "/handover/claims", json={
        "unit_id": unit["id"], "category": "struktur", "title": f"Retak dinding uji {_uid()}",
        "description": "uji G-B"}))["data"]
    return unit, c


def _punches(unit, claim_id):
    rows = ok(call(OWNER, "GET", "/field/punchlist", params={"unit_id": unit["id"]}))["data"]
    return [p for p in rows if p.get("warranty_claim_id") == claim_id]


def test_klaim_garansi_terima_serentak_satu_punch(world):
    for _ in range(ROUNDS):
        unit, c = _claim(world)
        body = {"accept": True, "reason": "diterima untuk diperbaiki"}
        rs = race([lambda: call(OWNER, "POST", f"/handover/claims/{c['id']}/decide", json=body) for _ in range(3)])
        assert codes(rs).count(200) == 1, [(r.status_code, r.text[:120]) for r in rs]
        assert 500 not in codes(rs)
        assert len(_punches(unit, c["id"])) == 1, "terima ×3 dulu melahirkan 3 punch item"


def test_klaim_garansi_terima_vs_tolak_eksklusif(world):
    for _ in range(ROUNDS):
        unit, c = _claim(world)
        rs = race([
            lambda: call(OWNER, "POST", f"/handover/claims/{c['id']}/decide",
                         json={"accept": True, "reason": "diterima untuk diperbaiki"}),
            lambda: call(OWNER, "POST", f"/handover/claims/{c['id']}/decide",
                         json={"accept": False, "reason": "bukan cacat bangunan, kerusakan penghuni",
                               "reject_reason": "di_luar_lingkup"})])
        assert codes(rs).count(200) == 1, [(r.status_code, r.text[:140]) for r in rs]
        cl = ok(call(OWNER, "GET", f"/handover/claims/{c['id']}"))["data"]
        if cl["state"] == "dikerjakan":
            assert not cl.get("reject_reason") and len(_punches(unit, c["id"])) == 1
        else:
            assert cl["state"] == "ditolak" and not _punches(unit, c["id"])


def test_klaim_garansi_selesai_ganda_dan_periksa_ganda(world):
    unit, c = _claim(world)
    ok(call(OWNER, "POST", f"/handover/claims/{c['id']}/decide", json={"accept": True, "reason": "diterima untuk diperbaiki"}))
    photo = upload_proof(OWNER)
    body = {"photo_file_ids": [photo], "note": "diperbaiki"}
    rs = race([lambda: call(OWNER, "POST", f"/handover/claims/{c['id']}/complete", json=body) for _ in range(3)])
    assert codes(rs).count(200) == 1, [(r.status_code, r.text[:120]) for r in rs]
    # periksa lulus ‖ kembalikan → satu pemenang
    rs = race([lambda: call(SUPER, "POST", f"/handover/claims/{c['id']}/verify", json={"passed": True}),
               lambda: call(SUPER, "POST", f"/handover/claims/{c['id']}/verify",
                            json={"passed": False, "reason": "perbaikan belum rapi, ulangi"})])
    assert codes(rs).count(200) == 1, [(r.status_code, r.text[:120]) for r in rs]


# ================================================================== jadwal bangun (PK3-18)
def _submitted_item(world):
    unit = _next_unit(world)
    tid = ok(call(OWNER, "GET", "/build/templates"))["data"][1]["id"]
    ok(call(OWNER, "POST", "/build/schedules", json={"unit_id": unit["id"], "template_id": tid,
                                                     "start_date": date.today().isoformat()}))
    items = ok(call(OWNER, "GET", "/build/items", params={"unit_id": unit["id"], "limit": 100}))["data"]
    it = [i for i in items if i["status"] == "ready"][0]
    det = ok(call(OWNER, "GET", f"/build/items/{it['id']}"))["data"]
    cl = [{"code": c["code"], "result": "pass"} for c in (det.get("checklist") or [])]
    photos = [upload_proof(SUPER) for _ in range(int(det.get("min_photos") or 0))]
    ok(call(SUPER, "POST", f"/build/items/{it['id']}/submit", json={
        "note": "Pekerjaan selesai sesuai gambar uji G-B", "photo_file_ids": photos, "checklist": cl}))
    return it["id"]


def test_jadwal_bangun_verifikasi_ganda_dan_kembalikan_eksklusif(world):
    for _ in range(ROUNDS):
        iid = _submitted_item(world)
        rs = race([lambda: call(OWNER, "POST", f"/build/items/{iid}/verify", json={"note": "ok"}),
                   lambda: call(OWNER, "POST", f"/build/items/{iid}/verify", json={"note": "ok"}),
                   lambda: call(OWNER, "POST", f"/build/items/{iid}/reject", json={"reason": "foto kurang jelas, ulangi"})])
        assert codes(rs).count(200) == 1, [(r.status_code, r.text[:120]) for r in rs]
        det = ok(call(OWNER, "GET", f"/build/items/{iid}"))["data"]
        acts = [h["action"] for h in det.get("history", [])]
        assert acts.count("verify") + acts.count("reject") == 1, acts
        assert det["status"] in ("done", "rework")


# ================================================================== komplain (PK3-18, PK3-23)
def _complaint():
    cust = ok(call(OWNER, "GET", "/customers", params={"limit": 1}))["data"][0]
    return ok(call(OWNER, "POST", "/complaints", json={
        "customer_id": cust["id"], "subject": f"Uji G-B {_uid()}", "message": "pesan uji", "channel": "telepon",
        "notify_customer": False}))["data"]["id"]


def _compl(cid):
    return ok(call(OWNER, "GET", f"/complaints/{cid}"))["data"]


def test_komplain_selesaikan_serentak_sekali(world):
    cid = _complaint()
    rs = race([lambda: call(OWNER, "POST", f"/complaints/{cid}/respond",
                            json={"message": "sudah ditangani", "resolve": True}) for _ in range(3)])
    assert codes(rs).count(200) == 1, [(r.status_code, r.text[:120]) for r in rs]
    c = _compl(cid)
    assert c["status"] == "resolved" and len(c["responses"]) == 1, "satu balasan, satu WA (dulu 3)"


def test_komplain_tugaskan_vs_selesaikan_tidak_meninggalkan_in_progress(world):
    for _ in range(ROUNDS * 2):
        cid = _complaint()
        rs = race([lambda: call(OWNER, "POST", f"/complaints/{cid}/respond",
                                json={"message": "sudah selesai", "resolve": True}),
                   lambda: call(OWNER, "POST", f"/complaints/{cid}/assign", json={"assigned_to": OWNER})])
        resolve = rs[0]
        c = _compl(cid)
        if resolve.status_code == 200:
            assert c["status"] == "resolved", "pembeli diberi tahu 'selesai' ⇒ status akhir harus resolved"


def test_komplain_status_tidak_mundur(world):
    cid = _complaint()
    ok(call(OWNER, "PUT", f"/complaints/{cid}/status", json={"status": "resolved"}))
    r = call(OWNER, "PUT", f"/complaints/{cid}/status", json={"status": "open"})
    assert r.status_code == 400, (r.status_code, r.text[:160])
    r = call(OWNER, "POST", f"/complaints/{cid}/respond", json={"message": "lagi", "resolve": True})
    assert r.status_code == 400, "selesai dua kali tidak boleh mengirim WA & menimpa resolved_at"
    assert _compl(cid)["status"] == "resolved"


# ================================================================== janji temu (PK3-23)
def _lead():
    r = ok(call(OWNER, "POST", "/leads", json={"name": f"Lead G-B {_uid()}",
                                               "phone": "+62813" + str(int(time.time() * 1000))[-9:],
                                               "source": "manual"}))["data"]
    return r["id"]


def test_janji_temu_identik_tidak_ganda(world):
    lead = _lead()
    at = (date.today() + timedelta(days=3)).isoformat() + "T09:00:00+07:00"
    body = {"lead_id": lead, "title": "Survey uji G-B", "scheduled_at": at, "type": "survey"}
    rs = race([lambda: call(OWNER, "POST", "/appointments", json=body) for _ in range(3)])
    assert codes(rs).count(200) == 1, [(r.status_code, r.text[:120]) for r in rs]
    rows = ok(call(OWNER, "GET", "/appointments", params={"lead_id": lead}))["data"]
    assert len(rows) == 1


def test_janji_temu_status_final_tidak_bisa_mundur(world):
    lead = _lead()
    at = (date.today() + timedelta(days=4)).isoformat() + "T10:00:00+07:00"
    a = ok(call(OWNER, "POST", "/appointments", json={
        "lead_id": lead, "title": "Survey uji G-B 2", "scheduled_at": at, "type": "survey"}))["data"]
    ok(call(OWNER, "POST", f"/appointments/{a['id']}/status", json={"status": "done"}))
    r = call(OWNER, "POST", f"/appointments/{a['id']}/status", json={"status": "scheduled"})
    assert r.status_code == 400, (r.status_code, r.text[:160])
    # selesai ‖ batal → satu pemenang
    b = ok(call(OWNER, "POST", "/appointments", json={
        "lead_id": lead, "title": "Survey uji G-B 3", "scheduled_at": at.replace("10:00", "11:00"),
        "type": "survey"}))["data"]
    rs = race([lambda: call(OWNER, "POST", f"/appointments/{b['id']}/status", json={"status": "done"}),
               lambda: call(OWNER, "POST", f"/appointments/{b['id']}/status", json={"status": "cancelled"})])
    assert codes(rs).count(200) == 1, [(r.status_code, r.text[:120]) for r in rs]


# ================================================================== rekap upah (PK3-18)
def _payroll(world):
    """Proyek baru + 1 pekerja + 1 hari absensi + rekap `draft` (proyek baru → periode tidak bertumpang)."""
    pid = ok(call(OWNER, "POST", "/projects", json={"name": f"G-B Upah {_uid()}", "location": "uji"}))["data"]["id"]
    wk = ok(call(OWNER, "POST", "/labor/workers", json={
        "name": f"Tukang G-B {_uid()}", "role": "tukang", "daily_wage": 200_000, "project_ids": [pid]}))["data"]
    day = (date.today() - timedelta(days=2)).isoformat()
    ok(call(OWNER, "POST", "/labor/attendance", json={
        "project_id": pid, "work_date": day, "entries": [{"worker_id": wk["id"], "status": "full"}]}))
    p = ok(call(OWNER, "POST", "/labor/payrolls", json={"project_id": pid, "period_start": day, "period_end": day}))
    return p["data"]["id"]


def _pr(pid):
    return ok(call(OWNER, "GET", f"/labor/payrolls/{pid}"))["data"]


def test_rekap_upah_ajukan_serentak_sekali(world):
    pid = _payroll(world)
    rs = race([lambda: call(OWNER, "POST", f"/labor/payrolls/{pid}/submit") for _ in range(3)])
    assert codes(rs).count(200) == 1 and set(codes(rs)) <= {200, 400, 409}, \
        [(r.status_code, r.text[:120]) for r in rs]
    hist = [h["action"] for h in _pr(pid)["history"]]
    assert hist.count("submit") == 1


def test_rekap_upah_setuju_vs_tolak_eksklusif(world):
    for _ in range(ROUNDS):
        pid = _payroll(world)
        ok(call(OWNER, "POST", f"/labor/payrolls/{pid}/submit"))
        rs = race([lambda: call(FINANCE, "POST", f"/labor/payrolls/{pid}/decision", json={"approve": True}),
                   lambda: call(FINANCE, "POST", f"/labor/payrolls/{pid}/decision",
                                json={"approve": False, "reason": "angka tidak cocok absensi"})])
        assert codes(rs).count(200) == 1, [(r.status_code, r.text[:120]) for r in rs]
        p = _pr(pid)
        acts = [h["action"] for h in p["history"]]
        assert acts.count("approve") + acts.count("reject") == 1, acts


# ================================================================== change order paralel (PK3-10)
def _spk(world, value=150_000_000):
    sub = ok(call(OWNER, "POST", "/subcon/subcontractors", json={"name": f"Subkon G-B {_uid()}"}))["data"]
    return ok(call(OWNER, "POST", "/subcon/spk", json={
        "subcontractor_id": sub["id"], "project_id": world.project_id, "title": f"SPK G-B {_uid()}",
        "contract_value": value}))["data"]


def _co(spk_id, delta=10_000_000):
    return ok(call(OWNER, "POST", "/subcon/change-orders", json={
        "spk_id": spk_id, "title": f"CO uji {_uid()}", "value_delta": delta, "reason": "uji G-B"}))["data"]["id"]


def _spk_value(spk_id):
    return int(ok(call(OWNER, "GET", f"/subcon/spk/{spk_id}"))["data"]["contract_value"])


def test_change_order_paralel_nilai_spk_bertambah_semuanya(world):
    spk = _spk(world)
    cos = [_co(spk["id"]) for _ in range(3)]
    rs = race([lambda c=c: call(OWNER, "POST", f"/subcon/change-orders/{c}/approve") for c in cos])
    assert codes(rs) == [200, 200, 200], [(r.status_code, r.text[:140]) for r in rs]
    assert _spk_value(spk["id"]) == 180_000_000, "3 CO × Rp 10 jt harus menambah Rp 30 jt (dulu hanya +Rp 10 jt)"
    new_vals = sorted(r.json()["data"]["new_value"] for r in rs)
    assert new_vals == [160_000_000, 170_000_000, 180_000_000]


def test_change_order_setuju_ganda_dan_setuju_vs_tolak(world):
    spk = _spk(world)
    co = _co(spk["id"])
    rs = race([lambda: call(OWNER, "POST", f"/subcon/change-orders/{co}/approve") for _ in range(2)])
    assert codes(rs).count(200) == 1 and set(codes(rs)) <= {200, 400, 409}, \
        [(r.status_code, r.text[:140]) for r in rs]
    assert _spk_value(spk["id"]) == 160_000_000
    co2 = _co(spk["id"])
    rs = race([lambda: call(OWNER, "POST", f"/subcon/change-orders/{co2}/approve"),
               lambda: call(OWNER, "POST", f"/subcon/change-orders/{co2}/reject", json={"note": "ditolak"})])
    assert codes(rs).count(200) == 1, [(r.status_code, r.text[:140]) for r in rs]
    expected = 170_000_000 if rs[0].status_code == 200 else 160_000_000
    assert _spk_value(spk["id"]) == expected
