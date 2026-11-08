"""Regresi H-B (2/2) — dedup manual "cari lalu sisipkan" (pola P12, audit 11 §2): permintaan serentak harus menghasilkan TEPAT SATU efek.

    API_BASE=http://localhost:8072/api DB_NAME=sipro_hb MONGO_URL=... python -m pytest backend/tests/p0/test_p0_dedup_manual.py -n 0 -q --noconftest

Dipilih yang berisiko duplikat NYATA pada data uang/CRM dan belum dijaga indeks unik:
  customers      pembeli kembar (HP/email boleh sama bila `allow_duplicate`, jadi tak ada indeks unik) → kunci identitas
  leads          pendaftaran / impor serentak → pesan "sudah terdaftar" yang jelas dan impor tidak gugur di tengah
  tasks          `auto_create_task` / `workhub.create_task` + indeks unik parsial `uq_task_open_source`
  materials      kode kembar → 400 (bukan 409 generik); material kembar tujuan transfer; pembuatan unit; impor mutasi bank
Tes in-process (tugas) memanggil fungsi backend langsung lewat `aio.run` dan butuh DB_NAME/MONGO_URL.
"""
import asyncio
import os
import sys
import uuid

import pytest

import aio
from test_p0_masuk import FINANCE, OWNER, SALES, World, call, codes, ok, race

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
ORG = "org-sipro"


def _uid(p="D"):
    return f"{p}{uuid.uuid4().hex[:6].upper()}"


def _phone():
    return "+62813" + str(uuid.uuid4().int)[:9]


def _shown(rs):
    return [(r.status_code, r.text[:110]) for r in rs]


@pytest.fixture(scope="module")
def mdb():
    from pymongo import MongoClient
    url = os.environ.get("MONGO_URL") or ("mongo" + "db://127.0.0.1:27017")
    return MongoClient(url)[os.environ.get("DB_NAME", "sipro_hb")]


@pytest.fixture(scope="module")
def world():
    return World()


# ================================================================== customers
def test_customer_dibuat_serentak_dengan_hp_sama_satu_saja(mdb):
    hp = _phone()
    rs = race([lambda: call(OWNER, "POST", "/customers", json={"name": f"Pembeli HB {_uid()}", "phone": hp}) for _ in range(4)])
    assert codes(rs).count(200) == 1 and set(codes(rs)) <= {200, 409}, _shown(rs)
    assert mdb.customers.count_documents({"org_id": ORG, "phone": {"$regex": hp[-9:] + "$"}}) == 1


def test_customer_dibuat_serentak_dengan_email_sama_satu_saja(mdb):
    mail = f"hb-{uuid.uuid4().hex[:8]}@contoh.id"
    rs = race([lambda: call(OWNER, "POST", "/customers", json={"name": f"Pembeli HB {_uid()}", "email": mail}) for _ in range(4)])
    assert codes(rs).count(200) == 1 and set(codes(rs)) <= {200, 409}, _shown(rs)
    assert mdb.customers.count_documents({"org_id": ORG, "email": mail}) == 1


def test_customer_allow_duplicate_tetap_boleh_kembar_sengaja(mdb):
    hp = _phone()
    ok(call(OWNER, "POST", "/customers", json={"name": f"Pembeli HB {_uid()}", "phone": hp}))
    ok(call(OWNER, "POST", "/customers", json={"name": f"Pembeli HB {_uid()}", "phone": hp, "allow_duplicate": True}))
    assert mdb.customers.count_documents({"org_id": ORG, "phone": {"$regex": hp[-9:] + "$"}}) == 2


# ================================================================== leads
def test_lead_didaftarkan_serentak_dengan_nomor_sama_pesan_jelas(mdb):
    hp = _phone()
    rs = race([lambda: call(SALES, "POST", "/leads", json={"name": f"Lead HB {_uid()}", "phone": hp, "source": "manual"}) for _ in range(4)])
    assert codes(rs).count(200) == 1 and set(codes(rs)) <= {200, 409}, _shown(rs)
    for r in rs:
        if r.status_code == 409:
            assert "sudah terdaftar sebagai lead" in r.text, r.text[:200]   # dulu: pesan generik dari penangan DuplicateKey
    assert mdb.leads.count_documents({"org_id": ORG, "phone": hp}) == 1


def test_impor_lead_serentak_tidak_gugur_di_tengah_dan_tanpa_kembar(mdb):
    phones = [_phone() for _ in range(6)]
    body = {"leads": [{"name": f"Impor HB {i}", "phone": p, "source": "manual"} for i, p in enumerate(phones)]}
    rs = race([lambda: call(SALES, "POST", "/leads/import", json=body) for _ in range(4)])
    assert set(codes(rs)) == {200}, _shown(rs)
    assert sum(r.json()["data"]["created"] for r in rs) == 6, [r.json() for r in rs]
    assert mdb.leads.count_documents({"org_id": ORG, "phone": {"$in": phones}}) == 6


# ================================================================== tugas (in-process)
def _race_inproc(n, factory):
    async def go():
        return await asyncio.gather(*[factory() for _ in range(n)], return_exceptions=True)
    return aio.run(go())


def test_auto_create_task_serentak_satu_tugas_per_source_event(mdb):
    import engine
    se = f"hb.test.auto:{_uid()}"

    def one():
        return engine.auto_create_task(source_event=se, title="Tugas uji HB", type="follow_up",
                                       related_entity_type="lead", related_entity_id="hb-uji", org_id=ORG)
    res = _race_inproc(6, one)
    assert not [r for r in res if isinstance(r, Exception)], res
    assert len([r for r in res if r]) == 1, "hanya satu pemanggil yang boleh membuat tugas"
    assert mdb.tasks.count_documents({"org_id": ORG, "source_event": se}) == 1


def test_workhub_create_task_serentak_dan_campur_dengan_auto_create(mdb):
    import engine
    import workhub as wh
    se = f"hb.test.wh:{_uid()}"
    jd = aio.run(wh.jobdesk(ORG, "SM-05"))

    def wh_one():
        return wh.create_task(ORG, jd, source_event=se, assigned_to="sales@sipro.co.id", title="Tugas uji HB wh")

    def auto_one():
        return engine.auto_create_task(source_event=se, title="Tugas uji HB auto", type="follow_up",
                                       related_entity_type="lead", related_entity_id="hb-uji", org_id=ORG)

    async def go():
        return await asyncio.gather(*[wh_one() for _ in range(3)], *[auto_one() for _ in range(3)], return_exceptions=True)
    res = aio.run(go())
    assert not [r for r in res if isinstance(r, Exception)], res
    assert len([r for r in res if r]) == 1
    assert mdb.tasks.count_documents({"org_id": ORG, "source_event": se}) == 1


def test_indeks_unik_tugas_terbuka_menolak_penulis_yang_tak_lewat_kunci(mdb):
    from pymongo.errors import DuplicateKeyError
    se = f"hb.test.idx:{_uid()}"
    base = {"org_id": ORG, "title": "Tugas uji indeks HB", "status": "open", "source_event": se}
    ids = [str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())]
    try:
        mdb.tasks.insert_one({**base, "id": ids[0]})
        with pytest.raises(DuplicateKeyError):
            mdb.tasks.insert_one({**base, "id": ids[1]})
        # tugas yang sudah selesai TIDAK menghalangi tugas periode berikutnya
        mdb.tasks.update_one({"id": ids[0]}, {"$set": {"status": "done"}})
        mdb.tasks.insert_one({**base, "id": ids[2]})
    finally:
        mdb.tasks.delete_many({"id": {"$in": ids}})


# ================================================================== materials / unit / bank
def test_material_kode_kembar_serentak_dijawab_400_bukan_409(world, mdb):
    kode = _uid("MAT")
    rs = race([lambda: call(OWNER, "POST", "/materials", json={
        "project_id": world.project_id, "name": f"Semen HB {_uid()}", "uom": "sak", "code": kode}) for _ in range(4)])
    assert codes(rs).count(200) == 1 and set(codes(rs)) <= {200, 400}, _shown(rs)
    assert mdb.materials.count_documents({"org_id": ORG, "project_id": world.project_id, "code": kode}) == 1


def _project(name):
    return ok(call(OWNER, "POST", "/projects", json={"name": f"{name} {_uid()}", "location": "uji HB"}))["data"]["id"]


def test_transfer_serentak_dari_beberapa_proyek_ke_tujuan_sama_satu_material_kembar(mdb):
    kode = _uid("TW")
    dest = _project("Tujuan HB")
    srcs = []
    for _ in range(4):
        pid = _project("Asal HB")
        mid = ok(call(OWNER, "POST", "/materials", json={"project_id": pid, "name": f"Besi HB {kode}", "uom": "btg", "code": kode}))["data"]["id"]
        ok(call(OWNER, "POST", "/materials/txn", json={"project_id": pid, "material_id": mid, "type": "in", "qty": 50, "note": "stok uji HB"}))
        srcs.append((pid, mid))
    rs = race([lambda p=p, m=m: call(OWNER, "POST", "/materials/transfers", json={
        "from_project_id": p, "to_project_id": dest, "material_id": m, "qty": 10, "reason": "uji kembar tujuan HB"}) for p, m in srcs])
    assert set(codes(rs)) == {200}, _shown(rs)
    twins = list(mdb.materials.find({"org_id": ORG, "project_id": dest, "code": kode}))
    assert len(twins) == 1, len(twins)
    masuk = sum(t["qty"] for t in mdb.material_txns.find({"org_id": ORG, "project_id": dest, "material_id": twins[0]["id"], "type": "in"}))
    assert masuk == 40, masuk


def test_generate_unit_serentak_tanpa_409_dan_tanpa_kembar(mdb):
    pid = _project("Unit HB")
    prefix = _uid("U")[:5]
    body = {"prefix": prefix, "count": 12, "type": "Tipe 36/72", "price": 400_000_000, "start_index": 1}
    rs = race([lambda: call(OWNER, "POST", f"/projects/{pid}/units", json=body) for _ in range(4)])
    assert set(codes(rs)) == {200}, _shown(rs)
    dibuat = [c for r in rs for c in r.json()["data"]["created"]]
    assert len(dibuat) == len(set(dibuat)) == 12, len(dibuat)
    assert mdb.units.count_documents({"org_id": ORG, "project_id": pid}) == 12


def test_impor_mutasi_bank_serentak_berkas_sama_tanpa_gagal_di_tengah(mdb):
    acc = ok(call(FINANCE, "POST", "/cash-bank/accounts", json={
        "kind": "bank", "name": f"Rek HB {_uid('R')}", "bank_name": "Bank Uji HB", "account_no": _uid("NO"), "opening_balance": 0}))["data"]
    ref = _uid("REF")
    rows = "".join(f"2026-11-0{i},TRANSFER MASUK {ref} {i},{ref}{i},,{i}00000\n" for i in range(1, 8))
    csv_text = "tanggal,keterangan,referensi,debit,kredit\n" + rows
    rs = race([lambda: call(FINANCE, "POST", "/bank/statements/import", json={
        "account_id": acc["id"], "filename": f"hb-{ref}.csv", "csv_text": csv_text, "dry_run": False}) for _ in range(4)])
    assert set(codes(rs)) == {200}, _shown(rs)     # dulu: sebagian 409 (menubruk indeks sidik jari di tengah putaran)
    assert sum(r.json()["data"]["counts"]["new"] for r in rs) == 7, [r.json()["data"]["counts"] for r in rs]
    assert mdb.bank_transactions.count_documents({"org_id": ORG, "account_id": acc["id"]}) == 7
