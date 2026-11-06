"""Regresi F1/F2 — otorisasi & lingkup organisasi (audit AZ-11, AZ-12, AZ-01, AZ-02, AZ-04).

    API_BASE=http://localhost:8054/api python -m pytest backend/tests/p0/test_p0_otorisasi.py -n 0 -q --noconftest

Pengguna uji dibuat berawalan `pat.` lalu dinonaktifkan di akhir; tidak ada data lain yang diubah.
"""
import uuid

import pytest
import requests

from test_p0_masuk import API, OWNER, PW, SUPER, call, ok

NUSA_OWNER = "owner@nusaproperti.co.id"
TAG = uuid.uuid4().hex[:6]


def _login_raw(email, pw):
    return requests.post(f"{API}/auth/login", json={"email": email, "password": pw}, timeout=30)


def _new_user(role="sales", actor=OWNER):
    email = f"pat.{TAG}.{uuid.uuid4().hex[:4]}@sipro.co.id"
    r = call(actor, "POST", "/admin/users", json={"name": f"PAT {TAG}", "email": email,
                                                   "password": "PatUji#2026x", "role": role})
    return email, r


@pytest.fixture(scope="module", autouse=True)
def _cleanup():
    made = []
    yield made
    for uid in made:
        call(OWNER, "PUT", f"/admin/users/{uid}", json={"is_active": False})


# ------------------------------------------------------------------ AZ-11
def test_owner_tidak_boleh_membuat_super_admin():
    email, r = _new_user(role="super_admin")
    assert r.status_code == 403, f"owner berhasil membuat super_admin: {r.status_code} {r.text[:200]}"
    assert _login_raw(email, "PatUji#2026x").status_code != 200, "akun super_admin ternyata ada"


def test_owner_tidak_boleh_menaikkan_pengguna_menjadi_super_admin(_cleanup):
    email, r = _new_user(role="sales")
    uid = ok(r)["data"]["id"]
    _cleanup.append(uid)
    r2 = call(OWNER, "PUT", f"/admin/users/{uid}", json={"role": "super_admin"})
    assert r2.status_code == 403, r2.text[:200]
    rows = ok(call(OWNER, "GET", "/admin/users", params={"limit": 200}))["data"]
    assert [u for u in rows if u["id"] == uid][0]["role"] == "sales"


def test_super_admin_tetap_boleh_memberi_peran_super_admin(_cleanup):
    email, r = _new_user(role="super_admin", actor=SUPER)
    body = ok(r)["data"]
    _cleanup.append(body["id"])
    assert body["role"] == "super_admin"
    # SUPER bertindak pada org asalnya; nonaktifkan lagi supaya tidak menyisakan akun lintas-tenant
    ok(call(SUPER, "PUT", f"/admin/users/{body['id']}", json={"is_active": False}))


def test_owner_tidak_boleh_mengubah_akun_super_admin():
    j = ok(call(SUPER, "GET", "/auth/me"))
    me = j.get("data", j)
    r = call(OWNER, "PUT", f"/admin/users/{me['id']}", json={"password": "Dibajak#2026x"})
    assert r.status_code in (403, 404), r.text[:200]
    assert _login_raw(SUPER, "test1234").status_code == 200, "sandi super_admin berubah!"


# ------------------------------------------------------------------ AZ-12
def test_owner_org_lain_tidak_bisa_mengganti_sandi_pengguna_org_ini(_cleanup):
    email, r = _new_user(role="sales")
    uid = ok(r)["data"]["id"]
    _cleanup.append(uid)
    r2 = call(NUSA_OWNER, "PUT", f"/admin/users/{uid}", json={"name": "DIUBAH ORG LAIN", "password": "Dibajak#2026x"})
    assert r2.status_code == 404, f"lintas-org seharusnya 404, dapat {r2.status_code} {r2.text[:160]}"
    assert _login_raw(email, "Dibajak#2026x").status_code != 200, "akun terambil alih"
    assert _login_raw(email, "PatUji#2026x").status_code == 200, "sandi lama harus tetap berlaku"


def test_owner_tetap_boleh_mengelola_pengguna_di_orgnya_sendiri(_cleanup):
    email, r = _new_user(role="sales")
    uid = ok(r)["data"]["id"]
    _cleanup.append(uid)
    out = ok(call(OWNER, "PUT", f"/admin/users/{uid}", json={"name": "PAT Diubah Sah", "role": "finance"}))
    assert out["data"]["name"] == "PAT Diubah Sah" and out["data"]["role"] == "finance"
