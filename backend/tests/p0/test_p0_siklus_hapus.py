"""Regresi G-A (2/2) — SIKLUS HIDUP DEAL: hapus-paksa, yatim, mutasi bank, hapus master (audit PK3-09/11/12/13/14, FZ-04, FZ-07).

    API_BASE=http://localhost:8071/api DB_NAME=sipro_ga MONGO_URL=<uri> \
      python -m pytest backend/tests/p0/test_p0_siklus_hapus.py -n 0 --noconftest -q -p no:cacheprovider

`orphans_of()` memindai SEMUA koleksi di DB (bukan daftar tetap) — koleksi anak baru yang lupa dimasukkan ke kaskade
hapus-paksa akan menggagalkan tes ini.
"""
import datetime
import time
import uuid

import pytest

from test_p0_masuk import FINANCE, MANAGER, OWNER, SALES, World, ar, call, cl_balance, codes, ok, pay, race, upload_proof  # noqa: F401
from test_p0_masuk_2 import _bank_account, _import_txn, _pay_bf, convert
from test_p0_siklus_deal import mdb, now

FINLEAD = "finlead@sipro.co.id"


@pytest.fixture(scope="module")
def world():
    return World()


def _rid(resp):
    return (resp.get("data") or resp)["receipt"]["id"]


def wait_until(cond, timeout=30.0, step=0.5):
    end = time.time() + timeout
    while time.time() < end:
        if cond():
            return True
        time.sleep(step)
    return cond()


def events_idle():
    return mdb().events.count_documents({"status": {"$in": ["pending", "processing"]}}) == 0


def orphans_of(did: str, src_ids=()) -> dict:
    """Baris yang masih menunjuk deal `did` (atau dokumen turunannya `src_ids`) di koleksi mana pun."""
    db, out = mdb(), {}
    for name in db.list_collection_names():
        if name == "audit_logs" or name.startswith("system."):
            continue
        n = db[name].count_documents({"$or": [{"deal_id": did}, {"source_deal_id": did}, {"converted_deal_id": did}]})
        if n:
            out[name] = n
    for name, field in (("tasks", "related_entity_id"), ("notifications", "related_entity_id"),
                        ("activities", "entity_id"), ("events", "entity_id")):
        n = db[name].count_documents({field: did})
        if n:
            out[name + "*"] = n
    if src_ids:
        ids = list(src_ids)
        for name, q in (("journal_entries", {"source_id": {"$in": ids}}), ("cash_vouchers", {"source_id": {"$in": ids}}),
                        ("payments_out", {"marketing_fee_id": {"$in": ids}})):
            n = db[name].count_documents(q)
            if n:
                out[name] = n
    return out


# ------------------------------------------------------------------ deal "lengkap"
def rich_deal(world):
    """Deal + kontrak + kuitansi (jurnal + BKM) + giro + fee marketing (disetujui & diajukan) + komplain +
    klaim garansi + faktur pajak + peristiwa konversi."""
    d = world.new_deal()
    did = d["deal_id"]
    d["contract_id"] = convert(d)
    d["receipt_id"] = _rid(ok(pay(did, 20_000_000)))
    giro = ok(call(FINANCE, "POST", "/pdc", json={
        "kind": "bg", "bank_name": "BCA", "instrument_no": f"BG-{uuid.uuid4().hex[:8]}", "amount": 10_000_000,
        "due_date": (datetime.date.today() + datetime.timedelta(days=30)).isoformat(), "deal_id": did}))["data"]
    agent = ok(call(OWNER, "POST", "/marketing/agents", json={
        "name": f"Agen Siklus {uuid.uuid4().hex[:6]}", "agent_type": "agen_properti"}))["data"]
    fee_body = {"agent_id": agent["id"], "deal_id": did, "basis": "fixed", "value": 6_000_000}
    fee_ok = ok(call(OWNER, "POST", "/marketing/fees", json={**fee_body, "trigger": "booking"}))["data"]
    ok(call(OWNER, "POST", f"/marketing/fees/{fee_ok['id']}/approve", json={}))
    fee_sub = ok(call(OWNER, "POST", "/marketing/fees", json={**fee_body, "trigger": "ppjb"}))["data"]
    org, ts = mdb().deals.find_one({"id": did})["org_id"], now()
    base = {"org_id": org, "deal_id": did, "created_at": ts}
    for coll in ("complaints", "warranty_claims", "faktur_pajak", "conversion_events"):
        mdb()[coll].insert_one({**base, "id": str(uuid.uuid4()), "status": "open", "state": "diajukan"})
    d.update(giro_id=giro["id"], fee_ok=fee_ok["id"], fee_sub=fee_sub["id"])
    d["src"] = [d["receipt_id"], giro["id"], fee_ok["id"]]
    # tunggu jurnal penerimaan, giro, fee terbit (+ bukti kasnya) supaya keadaan awal sama di kode lama & baru
    assert wait_until(lambda: mdb().journal_entries.count_documents({"source_id": {"$in": d["src"]}}) >= 3
                      and mdb().cash_vouchers.count_documents({"source_id": d["receipt_id"]}) >= 1, 25), \
        "jurnal/bukti kas awal tidak terbit"
    return d


# ================================================================== PK3-09 / FZ-04 — hapus-paksa deal tanpa yatim
def test_pk309_hapus_paksa_deal_lengkap_tidak_menyisakan_yatim(world):
    d = rich_deal(world)
    did = d["deal_id"]
    assert orphans_of(did, d["src"]), "sanity: deal lengkap memang punya turunan"
    r = call(OWNER, "DELETE", f"/deals/{did}", params={"reason": "uji siklus hapus paksa deal lengkap"})
    assert r.status_code == 200, r.text[:300]
    left = orphans_of(did, d["src"])
    assert not left, f"yatim setelah hapus-paksa: {left}"
    # fee yang belum disetujui TIDAK bisa disetujui untuk deal yang sudah dihapus (dulu 200 + akrual utang fiktif)
    r = call(OWNER, "POST", f"/marketing/fees/{d['fee_sub']}/approve", json={})
    assert r.status_code in (400, 404, 409), f"fee yatim masih bisa disetujui: {r.status_code} {r.text[:200]}"
    giro = call(FINANCE, "GET", "/pdc", params={"deal_id": did}).json()["data"]
    assert not giro, "giro deal yang dihapus harus ikut hilang"


def test_pk309_fee_untuk_deal_yang_tidak_ada_tidak_bisa_disetujui(world):
    db = mdb()
    org = db.deals.find_one({})["org_id"]
    ts = now()
    fid = str(uuid.uuid4())
    db.marketing_fees.insert_one({
        "id": fid, "org_id": org, "no": f"MF-HANTU-{fid[:6]}", "status": "submitted", "agent_id": "x", "agent_name": "Agen Hantu",
        "deal_id": "deal-yang-tidak-ada", "amount_gross": 6_000_000, "amount_net": 6_000_000, "paid_amount": 0,
        "created_at": ts, "updated_at": ts})
    r = call(OWNER, "POST", f"/marketing/fees/{fid}/approve", json={})
    assert r.status_code == 400 and "tidak ada" in r.text, (r.status_code, r.text[:200])
    assert db.journal_entries.count_documents({"source_id": fid}) == 0
    assert db.marketing_fees.find_one({"id": fid})["status"] == "submitted"


def test_pk309_hapus_paksa_melepas_customer_dan_tidak_menyisakan_bukti_kas(world):
    d = rich_deal(world)
    did = d["deal_id"]
    cust = mdb().customers.find_one({"deal_id": did})
    ok(call(OWNER, "DELETE", f"/deals/{did}", params={"reason": "uji siklus hapus paksa bukti kas"}))
    assert mdb().cash_vouchers.count_documents({"source_id": {"$in": d["src"]}}) == 0, "BKM/BKK yatim"
    if cust:
        assert not mdb().customers.find_one({"id": cust["id"]}).get("deal_id"), "customer menunjuk deal yang hilang"


# ================================================================== FZ-07 / FZ-07b — hapus-paksa ‖ kuitansi / void
def _settle(timeout=40):
    assert wait_until(events_idle, timeout), "antrean event tidak kosong"


def _check_runs(runs):
    db, bad = mdb(), []
    for did, rids in runs:
        exists = bool(db.deals.find_one({"id": did}))
        if not exists:
            for coll in ("receipts", "contract_liabilities", "ar_invoices", "customer_deposits"):
                if db[coll].count_documents({"deal_id": did}):
                    bad.append(("yatim tanpa deal", coll, did))
            if db.journal_entries.count_documents({"source_deal_id": did}):
                bad.append(("jurnal deal hilang", did))
        for rid in rids:
            has_rc = bool(db.receipts.find_one({"id": rid}))
            n_j = db.journal_entries.count_documents({"source_id": rid})
            if not has_rc and n_j:
                bad.append(("jurnal yatim", rid))
            if has_rc and not exists:
                bad.append(("kuitansi tanpa deal", rid))
    return bad


def test_fz07_penerimaan_void_dan_hapus_paksa_menunggu_kunci_deal_yang_sama(world):
    """Deterministik: selama kunci per-deal dipegang, penerimaan baru, void kuitansi, dan hapus-paksa TIDAK jalan
    (dulu ketiganya jalan serentak tanpa kunci bersama → uang tanpa jurnal / jurnal yatim)."""
    import threading
    d = world.new_deal()
    did = d["deal_id"]
    org = mdb().deals.find_one({"id": did})["org_id"]
    rid = _rid(ok(pay(did, 1_000_000)))
    body = {"deal_id": did, "amount": 1_300_000, "method": "transfer", "proof_file_ids": [upload_proof()]}
    mdb().idempotency_keys.insert_one({
        "key": f"mutex:deal.money:{org}:{did}", "created_at": now(),
        "expires_at": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=25)})
    jobs = {"terima": lambda: call(FINANCE, "POST", "/finance/ar/receipts", json=body),
            "void": lambda: call(FINLEAD, "POST", f"/finance/ar/receipts/{rid}/void", json={"reason": "uji siklus void menunggu kunci"}),
            "hapus": lambda: call(OWNER, "DELETE", f"/deals/{did}", params={"reason": "uji siklus hapus menunggu kunci"})}
    done, out = {}, {}

    def run(name, fn):
        out[name] = fn()
        done[name] = time.time()
    t0 = time.time()
    ths = [threading.Thread(target=run, args=(n, f)) for n, f in jobs.items()]
    [t.start() for t in ths]
    time.sleep(2.0)
    selesai_dini = sorted(done)
    mdb().idempotency_keys.delete_one({"key": f"mutex:deal.money:{org}:{did}"})
    [t.join(60) for t in ths]
    assert not selesai_dini, f"jalan padahal kunci deal dipegang: {selesai_dini}"
    assert all(done[n] - t0 >= 2.0 for n in done)
    assert all(r.status_code in (200, 400, 404, 409) for r in out.values()), {n: r.status_code for n, r in out.items()}
    assert not mdb().deals.find_one({"id": did}) and not mdb().receipts.count_documents({"deal_id": did})


def test_fz07_hapus_paksa_serentak_dengan_penerimaan_tidak_menyisakan_yatim(world):
    """Penghapusan dimulai pada selisih waktu ACAK (0–150 ms) dari tiga penerimaan: menyapu jendela balapan."""
    import random
    runs = []
    for i in range(16):
        d = world.new_deal()
        did = d["deal_id"]
        bodies = [{"deal_id": did, "amount": a, "method": "transfer", "proof_file_ids": [upload_proof()]}
                  for a in (1_000_000, 1_100_000, 1_200_000)]
        lag = random.uniform(0.0, 0.15)

        def hapus(lag=lag, did=did):
            time.sleep(lag)
            return call(OWNER, "DELETE", f"/deals/{did}", params={"reason": "uji siklus hapus paksa serentak"})
        rs = race([hapus] + [lambda b=b: call(FINANCE, "POST", "/finance/ar/receipts", json=b) for b in bodies])
        assert all(r.status_code in (200, 400, 404, 409) for r in rs), [(r.status_code, r.text[:100]) for r in rs]
        runs.append((did, [_rid(r.json()) for r in rs[1:] if r.status_code == 200]))
    _settle()
    bad = _check_runs(runs)
    assert not bad, bad


def test_fz07b_hapus_paksa_serentak_dengan_void_tidak_menyisakan_jurnal_yatim(world):
    import random
    runs = []
    for _ in range(14):
        d = world.new_deal()
        did = d["deal_id"]
        rid = _rid(ok(pay(did, 1_000_000)))
        lag = random.uniform(0.0, 0.1)

        def hapus(lag=lag, did=did):
            time.sleep(lag)
            return call(OWNER, "DELETE", f"/deals/{did}", params={"reason": "uji siklus hapus paksa vs void"})
        race([hapus, lambda: call(FINLEAD, "POST", f"/finance/ar/receipts/{rid}/void",
                                  json={"reason": "uji siklus void serentak"})])
        runs.append((did, [rid]))
    _settle()
    bad = _check_runs(runs)
    assert not bad, bad


# ================================================================== PK3-11 — hapus kuitansi dua kali
def test_pk311_hapus_kuitansi_dua_kali_bersamaan_tidak_membuat_kewajiban_negatif(world):
    d = world.new_deal()["deal_id"]
    rid = _rid(ok(pay(d, 100_000_000)))
    assert cl_balance(d) == 100_000_000
    rs = race([lambda: call(OWNER, "DELETE", f"/finance/ar/receipts/{rid}",
                            params={"reason": "uji siklus hapus kuitansi ganda"}) for _ in range(2)])
    assert codes(rs).count(200) == 1 and all(c in (200, 404, 409) for c in codes(rs)), \
        [(r.status_code, r.text[:160]) for r in rs]
    assert cl_balance(d) == 0, "kewajiban kontrak tidak boleh dibalik dua kali (dulu −Rp 100 jt)"
    r = call(OWNER, "DELETE", f"/finance/ar/receipts/{rid}", params={"reason": "uji siklus hapus kuitansi ketiga"})
    assert r.status_code == 404
    assert cl_balance(d) == 0


def test_pk311_hapus_kuitansi_void_tidak_membalik_alokasi_lain(world):
    d = world.new_deal()["deal_id"]
    r1 = _rid(ok(pay(d, 30_000_000)))
    r2 = _rid(ok(pay(d, 20_000_000)))
    ok(call(FINLEAD, "POST", f"/finance/ar/receipts/{r1}/void", json={"reason": "uji siklus void sebelum hapus"}))
    paid_before = int(ar(d)["data"]["paid"])
    assert paid_before == 20_000_000
    ok(call(OWNER, "DELETE", f"/finance/ar/receipts/{r1}", params={"reason": "uji siklus hapus kuitansi void"}))
    assert int(ar(d)["data"]["paid"]) == 20_000_000, "kuitansi void sudah dibalik oleh void; hapus tidak boleh membalik lagi"
    assert cl_balance(d) == 20_000_000 and r2


# ================================================================== PK3-12 — mutasi bank & kuitansi yang hilang
def _txn(txn_id):
    return mdb().bank_transactions.find_one({"id": txn_id})


def test_pk312_hapus_kuitansi_melepas_pencocokan_bank(world):
    d = world.new_deal()["deal_id"]
    txn = _import_txn(21_250_000, "AR")
    ok(call(FINANCE, "POST", f"/bank/transactions/{txn}/match", json={"kind": "ar_deal", "target_id": d}))
    assert _txn(txn)["match_state"] == "matched"
    rid = [r for r in ar(d)["receipts"] if r.get("status") != "void"][0]["id"]
    ok(call(OWNER, "DELETE", f"/finance/ar/receipts/{rid}", params={"reason": "uji siklus hapus kuitansi hasil bank"}))
    t = _txn(txn)
    assert t["match_state"] == "unmatched" and not t.get("match_id"), "mutasi tidak boleh matched ke kuitansi hantu"
    d2 = world.new_deal()["deal_id"]
    ok(call(FINANCE, "POST", f"/bank/transactions/{txn}/match", json={"kind": "ar_deal", "target_id": d2}))   # bisa dicocokkan ulang


def test_pk312_void_kuitansi_melepas_pencocokan_bank(world):
    d = world.new_deal()["deal_id"]
    txn = _import_txn(12_500_000, "AR")
    ok(call(FINANCE, "POST", f"/bank/transactions/{txn}/match", json={"kind": "ar_deal", "target_id": d}))
    rid = [r for r in ar(d)["receipts"] if r.get("status") != "void"][0]["id"]
    ok(call(FINLEAD, "POST", f"/finance/ar/receipts/{rid}/void", json={"reason": "uji siklus void kuitansi hasil bank"}))
    assert _txn(txn)["match_state"] == "unmatched"


def test_pk312_hapus_paksa_deal_melepas_pencocokan_bank(world):
    d = world.new_deal()["deal_id"]
    txn = _import_txn(9_750_000, "AR")
    ok(call(FINANCE, "POST", f"/bank/transactions/{txn}/match", json={"kind": "ar_deal", "target_id": d}))
    ok(call(OWNER, "DELETE", f"/deals/{d}", params={"reason": "uji siklus hapus paksa deal hasil bank"}))
    assert _txn(txn)["match_state"] == "unmatched"


def test_pk312_unmatch_toleran_bila_kuitansi_sudah_hilang(world):
    """Data lama yang sudah tersangkut (matched ke kuitansi yang dihapus langsung di DB) bisa dilepas."""
    d = world.new_deal()["deal_id"]
    txn = _import_txn(8_250_000, "AR")
    ok(call(FINANCE, "POST", f"/bank/transactions/{txn}/match", json={"kind": "ar_deal", "target_id": d}))
    rid = [r for r in ar(d)["receipts"] if r.get("status") != "void"][0]["id"]
    mdb().receipts.delete_one({"id": rid})   # keadaan tersangkut warisan: kuitansi hilang, mutasi masih matched
    assert _txn(txn)["match_state"] == "matched"
    r = call(OWNER, "POST", f"/bank/transactions/{txn}/unmatch", json={"reason": "uji siklus lepas pencocokan hantu"})
    assert r.status_code == 200, (r.status_code, r.text[:300])
    assert _txn(txn)["match_state"] == "unmatched"
    # bereskan keadaan yatim buatan tes ini (kuitansi dihapus lewat DB, subledger masih membawa uangnya) → rekonsiliasi hijau
    ok(call(OWNER, "DELETE", f"/deals/{d}", params={"reason": "uji siklus bereskan deal uji"}))


# ================================================================== PK3-13 — hapus lead/unit dengan deal batal
def _cancelled_deal(world, money: bool):
    if money:
        d = world.new_deal(booking_fee=5_000_000, book=False)
        _pay_bf(d["deal_id"], 5_000_000)
        ok(call(OWNER, "POST", f"/deals/{d['deal_id']}/cancel", json={"reason": "uji siklus batal hangus", "refund_mode": "forfeit"}))
    else:
        d = world.new_deal(booking_fee=0, book=False)
        ok(call(OWNER, "POST", f"/deals/{d['deal_id']}/cancel", json={"reason": "uji siklus batal tanpa uang"}))
    assert mdb().deals.find_one({"id": d["deal_id"]})["status"] == "cancelled"
    return d


def test_pk313_hapus_lead_dengan_deal_batal_berjejak_uang_diblokir(world):
    d = _cancelled_deal(world, money=True)
    r = call(OWNER, "DELETE", f"/leads/{d['lead_id']}")
    assert r.status_code == 400 and "catatan keuangan deal batal" in r.text, (r.status_code, r.text[:300])
    assert mdb().deals.find_one({"id": d["deal_id"]}), "deal & jejak uangnya tetap ada"
    chk = ok(call(OWNER, "GET", f"/leads/{d['lead_id']}/delete-check"))["data"]
    assert not chk["can_delete"] and "catatan keuangan deal batal" in chk["blockers"]


def test_pk313_hapus_lead_dengan_deal_batal_tanpa_uang_memakai_kaskade(world):
    d = _cancelled_deal(world, money=False)
    ok(call(OWNER, "DELETE", f"/leads/{d['lead_id']}"))
    assert not orphans_of(d["deal_id"]), f"turunan deal batal tertinggal: {orphans_of(d['deal_id'])}"


def test_pk313_hapus_unit_dengan_deal_batal(world):
    d = _cancelled_deal(world, money=False)
    ok(call(OWNER, "DELETE", f"/projects/{world.project_id}/units/{d['unit_id']}"))
    assert not orphans_of(d["deal_id"]), f"turunan deal batal tertinggal: {orphans_of(d['deal_id'])}"
    d2 = _cancelled_deal(world, money=True)
    r = call(OWNER, "DELETE", f"/projects/{world.project_id}/units/{d2['unit_id']}")
    assert r.status_code == 400, (r.status_code, r.text[:300])
    assert mdb().deals.find_one({"id": d2["deal_id"]})


# ================================================================== PK3-14 — hapus proyek
def _proyek(extra=True):
    p = ok(call(OWNER, "POST", "/projects", json={"name": f"Proyek Siklus {uuid.uuid4().hex[:6]}", "location": "uji"}))["data"]
    db = mdb()
    org, ts, pid = p["org_id"] if p.get("org_id") else db.projects.find_one({"id": p["id"]})["org_id"], now(), p["id"]
    base = {"org_id": org, "project_id": pid, "created_at": ts}
    mat = str(uuid.uuid4())
    db.materials.insert_one({**base, "id": mat, "code": "M-1", "name": "Semen", "uom": "sak"})
    db.boq_items.insert_one({**base, "id": str(uuid.uuid4()), "name": "Pondasi"})
    ids = {"mat": mat}
    if extra:
        db.material_txns.insert_one({**base, "id": str(uuid.uuid4()), "material_id": mat, "type": "in", "qty": 50})
        db.material_requisitions.insert_one({**base, "id": str(uuid.uuid4()), "status": "submitted"})
        db.labor_attendance.insert_one({**base, "id": str(uuid.uuid4()), "worker_id": "w1", "date": "2026-11-01"})
    return pid, ids


def test_pk314_hapus_proyek_diblokir_stok_permintaan_dan_absensi():
    pid, _ = _proyek(extra=True)
    chk = ok(call(OWNER, "GET", f"/projects/{pid}/delete-check"))["data"]
    assert not chk["can_delete"]
    for k in ("mutasi stok material", "permintaan material", "absensi upah"):
        assert k in chk["blockers"], chk["blockers"]
    r = call(OWNER, "DELETE", f"/projects/{pid}")
    assert r.status_code == 400 and "mutasi stok material" in r.text, (r.status_code, r.text[:300])
    r = call(OWNER, "DELETE", f"/projects/{pid}", params={"force": "true", "reason": "uji siklus hapus paksa proyek"})
    assert r.status_code == 400, "hapus-paksa tidak menghapus stok/upah terutang"
    assert mdb().projects.find_one({"id": pid}) and mdb().material_txns.count_documents({"project_id": pid}) == 1


def test_pk314_hapus_proyek_tanpa_catatan_keuangan_membuang_boq_dan_master_material():
    pid, _ = _proyek(extra=False)
    ok(call(OWNER, "DELETE", f"/projects/{pid}"))
    db = mdb()
    assert db.boq_items.count_documents({"project_id": pid}) == 0 and db.materials.count_documents({"project_id": pid}) == 0
    assert db.projects.find_one({"id": pid}) is None
