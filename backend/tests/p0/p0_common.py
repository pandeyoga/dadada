"""Pembantu bersama regresi P0 pembayaran keluar: klien HTTP, pembaca keadaan, pabrik data."""
import os
import threading
import time
import uuid

import pytest
import requests

API = os.environ.get("API_BASE", "http://localhost:8013/api").rstrip("/")
PW = "Sipro#2026"
LOGINS = {"superadmin": ("superadmin@estora.id", "test1234")}
_TOK = {}


def _email(u):
    return LOGINS.get(u, (f"{u}@sipro.co.id", PW))[0]


def tok(u):
    if u not in _TOK:
        email, pw = LOGINS.get(u, (f"{u}@sipro.co.id", PW))
        r = requests.post(f"{API}/auth/login", json={"email": email, "password": pw}, timeout=30)
        if r.status_code != 200:
            pytest.skip(f"login {email} gagal: {r.status_code}")
        _TOK[u] = r.json()["access_token"]
    return _TOK[u]


def call(u, method, path, body=None, params=None):
    r = requests.request(method, API + path, headers={"Authorization": "Bearer " + tok(u)},
                         json=body, params=params, timeout=120)
    try:
        j = r.json()
    except Exception:  # noqa: BLE001
        j = {"raw": r.text[:300]}
    return r.status_code, j


def par(fns):
    """Jalankan beberapa callable SERENTAK (pagar thread) dan kembalikan hasilnya berurutan."""
    res = [None] * len(fns)
    bar = threading.Barrier(len(fns))

    def w(i, fn):
        bar.wait()
        try:
            res[i] = fn()
        except Exception as e:  # noqa: BLE001
            res[i] = ("EXC", str(e))
    ts = [threading.Thread(target=w, args=(i, f)) for i, f in enumerate(fns)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    return res


def same(n, fn):
    return par([fn] * n)


def codes(results):
    return sorted(r[0] for r in results)


def ok(results):
    return [r for r in results if r[0] == 200]


def detail(r):
    d = r[1]
    return d.get("detail") if isinstance(d, dict) else d


def uniq(prefix="P0"):
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


# ---------------------------------------------------------------- pembaca keadaan
def accounts():
    s, j = call("finance", "GET", "/cash-bank/position")
    assert s == 200, j
    return {a["name"]: a for a in j["data"]["accounts"]}


def bank(name="Rekening Operasional"):
    return accounts()[name]["balance"]


def gl_balance(code):
    s, j = call("finance", "GET", "/gl/trial-balance")
    assert s == 200, j
    for r in j["data"]["rows"]:
        if r["code"] == code:
            return r["balance"]
    return 0


def wait_until(cond, timeout=25.0, step=0.5):
    """Tunggu kondisi benar (jurnal event diposting dispatcher tiap ≤ 8 dtk)."""
    end = time.time() + timeout
    while time.time() < end:
        if cond():
            return True
        time.sleep(step)
    return False


# ---------------------------------------------------------------- pabrik data
def make_bill(claimed=10_000_000, ret=5, vendor=None, creator="finance", **extra):
    body = {"vendor": vendor or uniq("P0-Vendor"), "claimed": claimed, "retention_pct": ret}
    body.update(extra)
    s, j = call(creator, "POST", "/finance/ap/bills", body)
    assert s == 200, (s, j)
    return j["data"]


def approved_bill(claimed=10_000_000, ret=5, **kw):
    b = make_bill(claimed, ret, **kw)
    s, j = call("owner", "POST", f"/finance/ap/bills/{b['id']}/approve")
    assert s == 200, (s, j)
    return j["data"]


def bill_detail(bid):
    s, j = call("finance", "GET", f"/finance/ap/bills/{bid}")
    assert s == 200, j
    return j["data"]




# ---------------------------------------------------------------- pembantu lanjutan
PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d49444154789c6360000002"
    "0001e221bc330000000049454e44ae426082")


def upload(user, owner_type, owner_id=None):
    """Unggah satu berkas bukti (PNG mungil) lewat API sungguhan → id berkas."""
    data = {"owner_type": owner_type, "optimize": "false"}
    if owner_id:
        data["owner_id"] = owner_id
    r = requests.post(f"{API}/files/upload", headers={"Authorization": "Bearer " + tok(user)},
                      files={"file": (f"{uniq('bukti')}.png", PNG, "image/png")}, data=data, timeout=60)
    assert r.status_code in (200, 201), (r.status_code, r.text[:200])
    return r.json()["data"]["id"]


def ensure_finlead():
    """Manajer Keuangan (finance_manager) — tidak ada di akun demo; dibuat lewat API Super Admin."""
    LOGINS["p0finlead"] = ("p0-finlead@sipro.co.id", PW)
    if "p0finlead" not in _TOK:
        call("superadmin", "POST", "/admin/users", {"name": "P0 Finlead", "email": "p0-finlead@sipro.co.id",
                                                    "password": PW, "role": "finance_manager"})
    return "p0finlead"


def project_id():
    """Proyek yang BISA diakses PM/site (anggota) — dipakai PO, SPK, absensi."""
    s, j = call("pm", "GET", "/projects")
    assert j["data"], "PM tidak punya proyek"
    return j["data"][-1]["id"]


def fund(account_name, amount):
    """Isi rekening/kas lewat transfer internal dari Rekening Operasional (dibuat finance, disetujui owner)."""
    accs = accounts()
    s, j = call("finance", "POST", "/cash-bank/transfers",
                {"kind": "transfer", "from_account_id": accs["Rekening Operasional"]["id"],
                 "to_account_id": accs[account_name]["id"], "amount": amount, "fee": 0,
                 "note": "P0 isi kas uji"})
    assert s == 200, (s, j)
    s, j = call("owner", "POST", f"/cash-bank/transfers/{j['data']['id']}/approve")
    assert s == 200, (s, j)


