"""Regresi P0 — perbaikan PEMBAYARAN MASUK (audit IN-01, IN-02, IN-04, IN-08, IN-11, IN-12, IN-13, IN-15).

Pengujian END-TO-END ke server hidup (bukan mock): seluruh skenario "dua permintaan bersamaan"
ditembakkan paralel lewat `ThreadPoolExecutor` + `threading.Barrier` supaya benar-benar berbarengan.

Menjalankan:
    API_BASE=http://localhost:8012/api python -m pytest backend/tests/p0/test_p0_masuk.py \
        --confcutdir=backend/tests/p0 -p no:cacheprovider -q

Tiap tes membuat DATA SENDIRI (proyek + unit + lead khusus tes ini), jadi aman dijalankan ulang di
database yang sama dan tidak bergantung pada data seed selain peran demo & skema pembayaran bawaan.
Peran: finance@sipro.co.id / sales@sipro.co.id / manager@sipro.co.id / owner@sipro.co.id (Sipro#2026),
superadmin@estora.id (test1234).
"""
import io
import os
import struct
import threading
import time
import uuid
import zlib
from concurrent.futures import ThreadPoolExecutor

import pytest
import requests

API = os.environ.get("API_BASE", "http://localhost:8012/api").rstrip("/")
PW = "Sipro#2026"
FINANCE, SALES, MANAGER, OWNER = ("finance@sipro.co.id", "sales@sipro.co.id",
                                  "manager@sipro.co.id", "owner@sipro.co.id")
SUPER = "superadmin@estora.id"
TAG = uuid.uuid4().hex[:5].upper()

_tokens = {}


# ------------------------------------------------------------------ pembantu HTTP
def _login(email):
    if email not in _tokens:
        pw = "test1234" if email == SUPER else PW
        r = requests.post(f"{API}/auth/login", json={"email": email, "password": pw}, timeout=30)
        assert r.status_code == 200, f"login {email}: {r.status_code} {r.text[:200]}"
        _tokens[email] = r.json()["access_token"]
    return _tokens[email]


def call(email, method, path, json=None, params=None, files=None, data=None, timeout=90):
    return requests.request(method, f"{API}{path}", headers={"Authorization": f"Bearer {_login(email)}"},
                            json=json, params=params, files=files, data=data, timeout=timeout)


def ok(r, code=200):
    assert r.status_code == code, f"HTTP {r.status_code}: {r.text[:600]}"
    return r.json()


def race(jobs):
    """Jalankan beberapa panggilan (lambda tanpa argumen) BERSAMAAN; kembalikan daftar respons."""
    n = len(jobs)
    bar = threading.Barrier(n)

    def run(job):
        bar.wait()
        return job()

    with ThreadPoolExecutor(max_workers=n) as ex:
        return list(ex.map(run, jobs))


def codes(rs):
    return sorted(r.status_code for r in rs)


def rp_png(seed):
    def chunk(t, d):
        c = struct.pack(">I", len(d)) + t + d
        return c + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    raw = b"".join(b"\x00" + bytes([(seed * 7 + x) % 256, (seed * 13 + x) % 256, (seed * 31 + x) % 256]) * 4
                   for x in range(4))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 4, 4, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


_seed = [int(time.time()) % 100000]


def upload_proof(email=FINANCE):
    """Unggah berkas bukti bayar sungguhan (unik per panggilan) dan kembalikan id-nya."""
    _seed[0] += 1
    r = call(email, "POST", "/files/upload", files={"file": ("bukti.png", io.BytesIO(rp_png(_seed[0])), "image/png")},
             data={"owner_type": "generic"})
    return ok(r)["data"]["id"]


# ------------------------------------------------------------------ data uji
class World:
    """Satu proyek khusus tes ini + penyedia deal baru (tiap deal = satu unit & satu lead)."""

    def __init__(self):
        r = ok(call(OWNER, "POST", "/projects", json={"name": f"P0 Masuk {TAG}", "location": "uji"}))
        self.project_id = r["data"]["id"]
        ok(call(OWNER, "POST", f"/projects/{self.project_id}/units",
                json={"prefix": f"P{TAG}", "count": 80, "type": "Tipe 45/90", "price": 500_000_000,
                      "start_index": 1}))
        units = ok(call(OWNER, "GET", "/units", params={"project_id": self.project_id, "limit": 200}))["data"]
        self.units = sorted(units, key=lambda u: u["code"])
        self.next_unit = 0
        schemes = ok(call(FINANCE, "GET", "/finance/config/payment-schemes"))["data"]
        self.scheme = {s["name"]: s["id"] for s in schemes}

    def new_deal(self, scheme="Cash Bertahap (3x)", booking_fee=0, book=True):
        unit = self.units[self.next_unit]
        self.next_unit += 1
        phone = "+62812" + str(int(time.time() * 1000))[-9:]
        lead = ok(call(SALES, "POST", "/leads", json={"name": f"Uji P0 {TAG} {self.next_unit}",
                                                      "phone": phone, "source": "manual"}))["data"]
        deal = ok(call(SALES, "POST", "/deals/reserve", json={
            "unit_id": unit["id"], "lead_id": lead["id"], "booking_fee": booking_fee,
            "scheme_id": self.scheme[scheme]}))["data"]
        if book:
            ok(call(SALES, "POST", f"/deals/{deal['id']}/book", json={}))
        return {"deal_id": deal["id"], "unit_id": unit["id"], "lead_id": lead["id"],
                "phone": phone, "unit_code": unit["code"]}


@pytest.fixture(scope="module")
def world():
    return World()


def ar(deal_id, email=FINANCE):
    return ok(call(email, "GET", f"/finance/ar/{deal_id}"))


def live_receipts(deal_id):
    return [r for r in ar(deal_id)["receipts"] if r.get("status") != "void"]


def cl_balance(deal_id):
    return int((ar(deal_id).get("contract_liability") or {}).get("balance") or 0)


def deposit_balance(deal_id):
    return int((ar(deal_id).get("deposit") or {}).get("balance") or 0)


def pay(deal_id, amount, email=FINANCE, **extra):
    body = {"deal_id": deal_id, "amount": amount, "method": "transfer",
            "proof_file_ids": [upload_proof(email)], **extra}
    return call(email, "POST", "/finance/ar/receipts", json=body)


# ================================================================== IN-01 — kuitansi manual
def test_in01_kuitansi_paralel_identik_hanya_satu(world):
    d = world.new_deal()["deal_id"]
    proof = upload_proof()
    body = {"deal_id": d, "amount": 100_000_000, "method": "transfer", "proof_file_ids": [proof]}
    rs = race([lambda: call(FINANCE, "POST", "/finance/ar/receipts", json=body) for _ in range(2)])
    assert codes(rs) == [200, 409], [(r.status_code, r.text[:200]) for r in rs]
    a = ar(d)
    assert a["data"]["paid"] == 100_000_000
    assert len(live_receipts(d)) == 1
    assert cl_balance(d) == 100_000_000     # kewajiban kontrak naik SEKALI (sebelumnya 200 jt)


def test_in01_kuitansi_paralel_dua_staf_hanya_satu(world):
    """Dua staf berbeda (kunci idempotensi berbeda) — yang menjaga adalah CAS pada AR."""
    d = world.new_deal()["deal_id"]
    pf, po = upload_proof(FINANCE), upload_proof(OWNER)
    rs = race([
        lambda: call(FINANCE, "POST", "/finance/ar/receipts",
                     json={"deal_id": d, "amount": 500_000_000, "method": "transfer", "proof_file_ids": [pf]}),
        lambda: call(OWNER, "POST", "/finance/ar/receipts",
                     json={"deal_id": d, "amount": 500_000_000, "method": "transfer", "proof_file_ids": [po]}),
    ])
    # pelunasan penuh oleh dua orang: yang kedua ditolak (CAS bentrok = 409, atau sisa tagihan sudah 0 = 400)
    assert codes(rs).count(200) == 1 and all(c in (200, 400, 409) for c in codes(rs)), \
        [(r.status_code, r.text[:200]) for r in rs]
    assert ar(d)["data"]["paid"] == 500_000_000
    assert len(live_receipts(d)) == 1 and cl_balance(d) == 500_000_000


def test_in01_client_ref_sama_tidak_pernah_dua_kali(world):
    d = world.new_deal()["deal_id"]
    proof = upload_proof()
    body = {"deal_id": d, "amount": 10_000_000, "method": "transfer", "proof_file_ids": [proof],
            "client_ref": f"p0-{TAG}-{uuid.uuid4().hex[:6]}"}
    assert call(FINANCE, "POST", "/finance/ar/receipts", json=body).status_code == 200
    time.sleep(16)   # lewat jendela 15 dtk klik-ganda: HANYA client_ref yang masih menahan
    r2 = call(FINANCE, "POST", "/finance/ar/receipts", json=body)
    assert r2.status_code == 409
    assert len(live_receipts(d)) == 1 and ar(d)["data"]["paid"] == 10_000_000


def test_in01_sekuensial_normal_tetap_berhasil(world):
    """Satu klik satu permintaan; nominal berbeda berurutan; kelebihan bayar tetap ditolak."""
    d = world.new_deal()["deal_id"]
    ok(pay(d, 50_000_000))
    ok(pay(d, 20_000_000))
    ok(pay(d, 5_000_000))
    a = ar(d)
    assert a["data"]["paid"] == 75_000_000 and len(live_receipts(d)) == 3
    assert cl_balance(d) == 75_000_000
    r = pay(d, 900_000_000)       # melebihi sisa tagihan tanpa allow_overpay
    assert r.status_code == 400 and "melebihi sisa tagihan" in r.text
    assert ar(d)["data"]["paid"] == 75_000_000


def test_in01_kuitansi_butuh_bukti_dan_nominal_valid(world):
    d = world.new_deal()["deal_id"]
    assert call(FINANCE, "POST", "/finance/ar/receipts",
                json={"deal_id": d, "amount": 0, "method": "transfer", "proof_file_ids": ["x"]}).status_code in (400, 422)
    assert call(SALES, "POST", "/finance/ar/receipts",
                json={"deal_id": d, "amount": 1000, "method": "transfer", "proof_file_ids": ["x"]}).status_code == 403


# ================================================================== IN-15 — method kpr
def test_in15_method_kpr_di_kuitansi_manual_ditolak(world):
    d = world.new_deal(scheme="Standar KPR (DP 20%)")["deal_id"]
    r = pay(d, 10_000_000, method="kpr")
    assert r.status_code == 400 and "Pencairan KPR" in r.text, r.text
    assert ar(d)["data"]["paid"] == 0 and not live_receipts(d)
    # jalur sah (setoran pembeli) tetap berhasil
    ok(pay(d, 10_000_000, method="transfer"))
    assert ar(d)["data"]["paid"] == 10_000_000


# ================================================================== IN-13 — deal dibatalkan
def test_in13_tolak_penerimaan_pada_deal_dibatalkan(world):
    d = world.new_deal()["deal_id"]
    ok(call(SALES, "POST", f"/deals/{d}/cancel", json={"reason": "uji P0 pembatalan IN-13"}))
    before = ar(d)["data"]
    assert before["status"] == "cancelled"
    r = pay(d, 20_000_000)
    assert r.status_code == 400 and "DIBATALKAN" in r.text, r.text
    after = ar(d)["data"]
    assert after["status"] == "cancelled" and after["paid"] == 0
    assert not live_receipts(d)
    # unit tidak boleh tertandai "sebagian dibayar"
    unit = [u for u in ok(call(OWNER, "GET", "/units", params={"project_id": world.project_id, "limit": 200}))["data"]
            if u["id"] == before["unit_id"]][0]
    assert unit["status"] == "available" and unit.get("payment_status") in (None, "none")


# ================================================================== IN-02 — titipan tidak boleh negatif
def _deposit_in(d, amount):
    return ok(call(FINANCE, "POST", f"/finance/ar/{d}/deposit",
                   json={"amount": amount, "proof_file_ids": [upload_proof()]}))


def test_in02_pakai_titipan_paralel_tidak_negatif(world):
    d = world.new_deal()["deal_id"]
    _deposit_in(d, 100_000_000)
    rs = race([lambda: call(FINANCE, "POST", f"/finance/ar/{d}/deposit/apply", json={"amount": 40_000_000})
               for _ in range(4)])
    assert codes(rs).count(200) == 1, [(r.status_code, r.text[:160]) for r in rs]
    assert all(c in (200, 400, 409) for c in codes(rs))
    assert deposit_balance(d) == 60_000_000                      # tidak pernah -60 jt
    assert ar(d)["data"]["paid"] == 40_000_000 and cl_balance(d) == 40_000_000
    assert len([r for r in live_receipts(d) if r["method"] == "deposit"]) == 1


def test_in02_pakai_dan_kembalikan_titipan_bersamaan_tidak_negatif(world):
    d = world.new_deal()["deal_id"]
    _deposit_in(d, 30_000_000)
    rs = race([
        lambda: call(FINANCE, "POST", f"/finance/ar/{d}/deposit/apply", json={"amount": 30_000_000}),
        lambda: call(FINANCE, "POST", f"/finance/ar/{d}/deposit/refund", json={"amount": 30_000_000}),
    ])
    assert codes(rs).count(200) == 1, [(r.status_code, r.text[:160]) for r in rs]
    assert deposit_balance(d) == 0
    a = ar(d)
    dep = a["deposit"]
    assert dep["balance"] == dep["received_total"] - dep["applied_total"] - dep["refunded_total"] == 0


def test_in02_kembalikan_titipan_melebihi_saldo_ditolak(world):
    d = world.new_deal()["deal_id"]
    _deposit_in(d, 5_000_000)
    r = call(FINANCE, "POST", f"/finance/ar/{d}/deposit/refund", json={"amount": 9_000_000})
    assert r.status_code == 400 and "melebihi saldo" in r.text
    ok(call(FINANCE, "POST", f"/finance/ar/{d}/deposit/refund", json={"amount": 5_000_000}))
    assert deposit_balance(d) == 0


def test_in02_terima_titipan_paralel_identik_hanya_satu(world):
    d = world.new_deal()["deal_id"]
    proof = upload_proof()
    rs = race([lambda: call(FINANCE, "POST", f"/finance/ar/{d}/deposit",
                            json={"amount": 7_000_000, "proof_file_ids": [proof]}) for _ in range(2)])
    assert codes(rs) == [200, 409]
    assert deposit_balance(d) == 7_000_000


# ================================================================== pembantu: bukti portal, KPR, bank
import datetime  # noqa: E402


def portal_token(phone):
    r = requests.post(f"{API}/portal/auth/request-otp", json={"identifier": phone}, timeout=30)
    assert r.status_code == 200, r.text[:200]
    code = r.json().get("dev_code")
    assert code, "mode simulasi OTP (dev_code) diperlukan untuk tes ini"
    r = requests.post(f"{API}/portal/auth/verify-otp", json={"identifier": phone, "code": code}, timeout=30)
    assert r.status_code == 200, r.text[:200]
    return r.json()["token"]


def portal_proof(deal, amount, path="/portal/payments/proof"):
    """Pelanggan mengirim bukti transfer lewat portal; kembalikan id bukti (state pending)."""
    _seed[0] += 1
    h = {"Authorization": f"Bearer {portal_token(deal['phone'])}"}
    up = requests.post(f"{API}/portal/payments/proof/upload", headers=h, timeout=60,
                       files={"file": ("b.png", io.BytesIO(rp_png(_seed[0])), "image/png")},
                       data={"deal_id": deal["deal_id"]})
    assert up.status_code == 200, up.text[:300]
    r = requests.post(f"{API}{path}", headers=h, timeout=60, json={
        "deal_id": deal["deal_id"], "amount": amount, "transfer_date": datetime.date.today().isoformat(),
        "file_ids": [up.json()["data"]["id"]]})
    assert r.status_code == 200, r.text[:300]
    return r.json()["data"]["id"]


def convert(deal):
    r = ok(call(SALES, "POST", f"/deals/{deal['deal_id']}/convert", json={}))
    return r["data"]["contract"]["id"]


def kpr_deal(world, plafon=500_000_000):
    """Deal skema KPR 100% porsi bank, sudah konversi + SP3K + akad (siap dicairkan, 1 tahap)."""
    d = world.new_deal(scheme="KPR (DP 0% + pencairan bank)")
    d["contract_id"] = convert(d)
    today = datetime.date.today().isoformat()
    fid = upload_proof()
    for st, body in [("diajukan_ke_bank", {"bank": "BTN"}),
                     ("appraisal", {"date": today, "amount": plafon + 20_000_000, "file_id": fid}),
                     ("sp3k", {"file_id": fid, "plafon": plafon, "number": f"SP3K-{TAG}", "date": today,
                               "tenor_months": 120, "rate": 7.5}),
                     ("akad_kredit", {"date": today, "notary": "Notaris Uji", "file_id": fid})]:
        ok(call(FINANCE, "POST", f"/contracts/{d['contract_id']}/kpr/stage/{st}", json=body))
    app = ok(call(FINANCE, "GET", f"/contracts/{d['contract_id']}/kpr"))["data"]["application"]
    d["fin_id"] = app["id"]
    d["plafon"] = plafon
    return d


def kpr_receipts(deal_id):
    return [r for r in live_receipts(deal_id) if r.get("method") == "kpr"]


def deposit_balance_of(deal_id):
    rows = [x for x in ok(call(FINANCE, "GET", "/finance/ar/deposits"))["data"] if x["deal_id"] == deal_id]
    return int(rows[0]["balance"]) if rows else 0


# ================================================================== IN-01 — verifikasi bukti portal
def test_in01_verifikasi_bukti_paralel_hanya_satu_kuitansi(world):
    d = world.new_deal()
    convert(d)
    iid = portal_proof(d, 12_500_000)
    rs = race([lambda: call(FINANCE, "POST", f"/payment-intakes/{iid}/verify", json={}) for _ in range(2)])
    assert codes(rs).count(200) == 1 and all(c in (200, 400, 409) for c in codes(rs)), \
        [(r.status_code, r.text[:160]) for r in rs]
    assert ar(d["deal_id"])["data"]["paid"] == 12_500_000
    assert len(live_receipts(d["deal_id"])) == 1 and cl_balance(d["deal_id"]) == 12_500_000
    # sekuensial: verifikasi ulang ditolak dengan pesan lama
    r = call(FINANCE, "POST", f"/payment-intakes/{iid}/verify", json={})
    assert r.status_code == 400 and "tidak bisa diverifikasi lagi" in r.text


def test_in01_verifikasi_bukti_sekuensial_normal(world):
    d = world.new_deal()
    convert(d)
    iid = portal_proof(d, 3_000_000)
    out = ok(call(FINANCE, "POST", f"/payment-intakes/{iid}/verify", json={}))
    assert out["data"]["intake"]["state"] == "verified"
    assert ar(d["deal_id"])["data"]["paid"] == 3_000_000


def test_in01_verifikasi_dan_tolak_bersamaan_hanya_satu_menang(world):
    d = world.new_deal()
    convert(d)
    iid = portal_proof(d, 2_000_000)
    rs = race([lambda: call(FINANCE, "POST", f"/payment-intakes/{iid}/verify", json={}),
               lambda: call(FINANCE, "POST", f"/payment-intakes/{iid}/reject",
                            json={"reason": "uji P0 tolak bersamaan verifikasi"})])
    assert codes(rs).count(200) == 1, [(r.status_code, r.text[:160]) for r in rs]
    intake = ok(call(FINANCE, "GET", f"/payment-intakes/{iid}"))["data"]
    paid = ar(d["deal_id"])["data"]["paid"]
    assert (intake["state"] == "verified" and paid == 2_000_000) or (intake["state"] == "rejected" and paid == 0)


# ================================================================== IN-01 — booking fee
def bf_deal(world, fee=5_000_000):
    return world.new_deal(booking_fee=fee, book=False)


def test_in01_booking_fee_bayar_paralel_hanya_satu(world):
    d = bf_deal(world)["deal_id"]
    proof = upload_proof()
    body = {"amount": 5_000_000, "method": "transfer", "proof_file_ids": [proof]}
    rs = race([lambda: call(FINANCE, "POST", f"/booking-fee/deals/{d}/pay", json=body) for _ in range(2)])
    assert codes(rs) == [200, 409], [(r.status_code, r.text[:160]) for r in rs]
    det = ok(call(FINANCE, "GET", f"/booking-fee/deals/{d}"))["data"]
    assert det["invoice"]["paid"] == 5_000_000 and det["invoice"]["status"] == "paid"
    assert len(det["receipts"]) == 1
    assert deposit_balance_of(d) == 5_000_000     # titipan BF naik SEKALI (sebelumnya 10 jt)


def test_in01_booking_fee_bayar_dua_staf_paralel_hanya_satu(world):
    d = bf_deal(world)["deal_id"]
    pf, po = upload_proof(FINANCE), upload_proof(OWNER)
    rs = race([
        lambda: call(FINANCE, "POST", f"/booking-fee/deals/{d}/pay",
                     json={"amount": 5_000_000, "method": "transfer", "proof_file_ids": [pf]}),
        lambda: call(OWNER, "POST", f"/booking-fee/deals/{d}/pay",
                     json={"amount": 5_000_000, "method": "transfer", "proof_file_ids": [po]}),
    ])
    assert codes(rs).count(200) == 1, [(r.status_code, r.text[:160]) for r in rs]
    det = ok(call(FINANCE, "GET", f"/booking-fee/deals/{d}"))["data"]
    assert det["invoice"]["paid"] == 5_000_000 and len(det["receipts"]) == 1
    assert deposit_balance_of(d) == 5_000_000


def test_in01_booking_fee_bayar_sebagian_lalu_lunas_normal(world):
    d = bf_deal(world)["deal_id"]
    ok(call(FINANCE, "POST", f"/booking-fee/deals/{d}/pay",
            json={"amount": 2_000_000, "proof_file_ids": [upload_proof()]}))
    out = ok(call(FINANCE, "POST", f"/booking-fee/deals/{d}/pay",
                  json={"amount": 3_000_000, "proof_file_ids": [upload_proof()]}))
    assert out["data"]["invoice"]["status"] == "paid" and out["data"]["invoice"]["paid"] == 5_000_000
    r = call(FINANCE, "POST", f"/booking-fee/deals/{d}/pay",
             json={"amount": 1_000_000, "proof_file_ids": [upload_proof()]})
    assert r.status_code == 400 and "LUNAS" in r.text


def test_in01_booking_fee_verifikasi_bukti_paralel_hanya_satu(world):
    d = bf_deal(world)
    iid = portal_proof(d, 5_000_000, path="/portal/booking-fee/proof")
    rs = race([lambda: call(FINANCE, "POST", f"/booking-fee/deals/{d['deal_id']}/proofs/{iid}/verify",
                            json={}) for _ in range(2)])
    assert codes(rs).count(200) == 1 and all(c in (200, 400, 409) for c in codes(rs)), \
        [(r.status_code, r.text[:160]) for r in rs]
    det = ok(call(FINANCE, "GET", f"/booking-fee/deals/{d['deal_id']}"))["data"]
    assert det["invoice"]["paid"] == 5_000_000 and len(det["receipts"]) == 1
    assert deposit_balance_of(d["deal_id"]) == 5_000_000


