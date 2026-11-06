"""Regresi F5 — konkurensi sederhana di stok, BAST, rekap upah (audit PK3-01, PK3-02, PK3-03).

    API_BASE=http://localhost:8054/api python -m pytest backend/tests/p0/test_p0_konkurensi3.py -n 0 -q --noconftest
"""
import uuid

import pytest

from test_p0_masuk import OWNER, World, call, ok, race

SITE = "owner@sipro.co.id"  # akses penuh: proyek uji ini dibuat owner, site bukan anggotanya
PM = "pm@sipro.co.id"


@pytest.fixture(scope="module")
def world():
    return World()


def _material(world, name):
    r = ok(call(OWNER, "POST", "/materials", json={"project_id": world.project_id, "name": f"{name} {uuid.uuid4().hex[:5]}",
                                                   "uom": "sak"}))
    mid = r["data"]["id"]
    ok(call(SITE, "POST", "/materials/txn", json={"project_id": world.project_id, "material_id": mid,
                                                  "type": "in", "qty": 100, "note": "F5 masuk"}))
    return mid


def _stock(world, mid):
    r = ok(call(SITE, "POST", "/materials/txn", json={"project_id": world.project_id, "material_id": mid,
                                                      "type": "in", "qty": 0.01, "note": "F5 baca"}))
    return round(float(r["stock"]) - 0.01, 2)


# ------------------------------------------------------------------ PK3-02
def test_stok_keluar_paralel_tidak_membuat_stok_negatif(world):
    mid = _material(world, "F5 Semen")
    rs = race([lambda i=i: call(SITE, "POST", "/materials/txn", json={
        "project_id": world.project_id, "material_id": mid, "type": "out", "qty": 80, "note": f"F5 keluar {i}"})
        for i in range(2)])
    assert sorted(r.status_code for r in rs).count(200) == 1, [(r.status_code, r.text[:100]) for r in rs]
    assert _stock(world, mid) == 20


def test_opname_paralel_tidak_menggeser_stok_dua_kali(world):
    mid = _material(world, "F5 Pasir")
    rs = race([lambda i=i: call(SITE, "POST", "/materials/opname", json={
        "project_id": world.project_id, "material_id": mid, "physical_qty": 60, "note": f"F5 opname {i}"})
        for i in range(2)])
    assert all(r.status_code == 200 for r in rs), [(r.status_code, r.text[:100]) for r in rs]
    assert _stock(world, mid) == 60, "dua opname fisik 60 harus menghasilkan stok 60 (bukan 20)"


# ------------------------------------------------------------------ PK3-03
def test_bast_paralel_hanya_satu_dokumen_aktif(world):
    unit = world.units[70]
    body = {"unit_id": unit["id"], "override": True, "override_reason": "uji F5 paralel BAST", "received_by": "Uji F5"}
    rs = race([lambda: call(OWNER, "POST", "/handover/issue", json=body) for _ in range(4)])
    assert all(r.status_code == 200 for r in rs), [(r.status_code, r.text[:120]) for r in rs]
    numbers = {(r.json().get("data") or r.json()).get("number") for r in rs}
    assert len(numbers) == 1, f"empat permintaan bersamaan melahirkan {len(numbers)} BAST: {numbers}"
