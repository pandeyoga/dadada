"""Tes regresi P0 — kontrak & konversi lead→customer (audit 04_KONTRAK_DAN_KONVERSI_LEAD).

Menembak SERVER HIDUP lewat HTTP (tanpa mengimpor kode aplikasi):

    API_BASE=http://localhost:8015/api python -m pytest backend/tests/p0/test_p0_kontrak.py -n 0 -q --noconftest

(`--noconftest` karena conftest induk `backend/tests/conftest.py` mewajibkan variabel env
URL pratinjau lama; tes ini mandiri.)

Setiap tes membuat data sendiri (lead/unit/deal berawalan `P0KT`) dan membersihkannya lewat
hapus-paksa deal oleh owner di akhir, sehingga unit demo kembali tersedia dan suite aman
dijalankan berulang.

Cakupan:
  KT-01  jalur legal lama /deals/{id}/ppjb|ajb tidak lagi menjual unit tanpa gerbang kontrak
  KT-02  konversi paralel -> 1 customer, 1 kontrak, tanpa HTTP 500, tanpa lubang nomor
  KT-07  jadwal AR pada deal batal ditolak
  KT-08  kupon kuota 1 paralel -> hanya satu terpakai, tidak ada deal berdiskon yatim
  KT-09  sales tidak boleh membaca pembeli milik sales lain
"""
import os
import random
import re
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
import requests

API = os.environ.get("API_BASE", "http://localhost:8015/api").rstrip("/")
PASSWORD = "Sipro#2026"
ACCOUNTS = {
    "owner": ("owner@sipro.co.id", PASSWORD),
    "manager": ("manager@sipro.co.id", PASSWORD),
    "sales": ("sales@sipro.co.id", PASSWORD),
    "sales2": ("sales2@sipro.co.id", PASSWORD),
    "finance": ("finance@sipro.co.id", PASSWORD),
}
PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000d49444154789c6360f8cfc0f01f0005000201a5f645400000000049454e44ae426082")

_tokens: dict = {}
_lock = threading.Lock()


# ----------------------------------------------------------------------------- HTTP
def _token(who: str) -> str:
    with _lock:
        if who not in _tokens:
            email, pw = ACCOUNTS[who]
            r = requests.post(f"{API}/auth/login", json={"email": email, "password": pw}, timeout=30)
            if r.status_code != 200:
                pytest.skip(f"login {email} gagal: {r.status_code} {r.text[:120]}")
            _tokens[who] = r.json()["access_token"]
        return _tokens[who]


def call(who: str, method: str, path: str, body=None, params=None):
    r = requests.request(method, f"{API}{path}", json=body, params=params, timeout=120,
                         headers={"Authorization": f"Bearer {_token(who)}"})
    try:
        data = r.json()
    except ValueError:
        data = r.text
    return r.status_code, data


def ok(resp, expect=200):
    code, data = resp
    assert code == expect, f"HTTP {code} (harap {expect}): {str(data)[:400]}"
    return data["data"] if isinstance(data, dict) and "data" in data else data


# ----------------------------------------------------------------------------- fixture data
_lead_names: list = []


@pytest.fixture
def cleanup():
    """Kumpulkan deal uji; akhir tes: hapus paksa (owner) supaya unit demo tersedia lagi,
    lalu hapus pembeli hasil konversi uji (nama lead berawalan `P0KT`)."""
    deals: list = []
    _lead_names.clear()
    yield deals
    for did in deals:
        call("owner", "DELETE", f"/deals/{did}", params={"reason": "bersihkan data uji P0 kontrak"})
    for name in _lead_names:
        code, body = call("owner", "GET", "/customers", params={"q": name, "limit": 20})
        for c in (body.get("data") or []) if code == 200 else []:
            call("owner", "DELETE", f"/customers/{c['id']}")


def _phone() -> str:
    return "0812" + "".join(random.choice("0123456789") for _ in range(8))


def available_units(n: int, exclude=()) -> list:
    rows = ok(call("manager", "GET", "/units", params={"status": "available", "limit": 200}))
    got = [u for u in rows if u["code"] not in exclude]
    if len(got) < n:
        pytest.skip(f"butuh {n} unit tersedia, hanya {len(got)}")
    return got[:n]


_scheme_cache: dict = {}


def scheme_id(code: str) -> str:
    if not _scheme_cache:
        for s in ok(call("manager", "GET", "/payment-schemes")):
            _scheme_cache[s["code"]] = s["id"]
    return _scheme_cache[code]


def new_lead(who="sales", tag="Lead") -> dict:
    name = f"P0KT {tag} {uuid.uuid4().hex[:6]}"
    _lead_names.append(name)
    lead = ok(call(who, "POST", "/leads", {"name": name, "phone": _phone(), "source": "walk_in"}))
    call(who, "POST", f"/leads/{lead['id']}/first-contact")
    call(who, "POST", "/appointments", {"lead_id": lead["id"], "title": "P0KT survei",
                                        "scheduled_at": "2026-12-10T10:00:00", "type": "survey"})
    return lead


def reserve(lead_id: str, unit: dict, who="sales", scheme="cash_keras", **extra):
    body = {"unit_id": unit["id"], "lead_id": lead_id, "booking_fee": 5_000_000,
            "scheme_id": scheme_id(scheme) if scheme else None, "notes": "P0KT", **extra}
    return call(who, "POST", "/deals/reserve", body)


def upload_proof(deal_id: str) -> str:
    r = requests.post(f"{API}/files/upload", timeout=60,
                      headers={"Authorization": f"Bearer {_token('finance')}"},
                      files={"file": ("bukti.png", PNG, "image/png")},
                      data={"owner_type": "deal", "owner_id": deal_id})
    assert r.status_code == 200, r.text[:200]
    return r.json()["data"]["id"]


def pay_booking_fee_and_book(deal_id: str, who="sales"):
    fid = upload_proof(deal_id)
    ok(call("finance", "POST", f"/booking-fee/deals/{deal_id}/pay",
            {"amount": 5_000_000, "method": "transfer", "note": "P0KT bf", "proof_file_ids": [fid]}))
    return ok(call(who, "POST", f"/deals/{deal_id}/book", {}))


def booked_deal(cleanup, who="sales", unit=None, scheme="cash_keras", tag="Deal"):
    unit = unit or available_units(1)[0]
    lead = new_lead(who, tag)
    deal = ok(reserve(lead["id"], unit, who, scheme))
    cleanup.append(deal["id"])
    pay_booking_fee_and_book(deal["id"], who)
    return lead, deal, unit


def unit_status(code: str) -> dict:
    rows = ok(call("manager", "GET", "/units", params={"q": code, "limit": 20}))
    return next(u for u in rows if u["code"] == code)


def contract_seq(number: str) -> int:
    m = re.search(r"(\d+)$", number or "")
    return int(m.group(1)) if m else -1


# ============================================================================ KT-02
def test_kt02_convert_paralel_satu_customer_satu_kontrak(cleanup):
    """4 permintaan /convert serentak -> semuanya sukses, kontrak & customer SAMA, tanpa 500."""
    lead, deal, _ = booked_deal(cleanup, tag="Race")
    for who in ("sales", "manager"):  # tembakan ke-3/4 dari peran lain pun harus aman
        _token(who)
    with ThreadPoolExecutor(max_workers=4) as pool:
        futs = [pool.submit(call, w, "POST", f"/deals/{deal['id']}/convert", {})
                for w in ("sales", "sales", "manager", "sales")]
        res = [f.result() for f in futs]
    codes = [c for c, _ in res]
    assert all(c == 200 for c in codes), f"kode respons {codes}: {[str(d)[:120] for c, d in res if c != 200]}"
    contracts = {r["data"]["contract"]["id"] for _, r in res}
    customers = {r["data"]["customer"]["id"] for _, r in res}
    assert len(contracts) == 1, f"kontrak ganda: {contracts}"
    assert len(customers) == 1, f"customer ganda: {customers}"
    assert sum(1 for _, r in res if r["data"]["created"]) == 1, "tepat satu permintaan yang membuat"
    # Sisi data: satu kontrak untuk deal, satu customer untuk lead.
    rows = ok(call("manager", "GET", "/contracts", params={"deal_id": deal["id"]}))
    assert len(rows) == 1
    custs = ok(call("manager", "GET", "/customers", params={"q": lead["name"], "limit": 50}))
    assert len([c for c in custs if c.get("lead_id") == lead["id"]]) == 1, "customer ganda untuk satu lead"


def test_kt02_convert_paralel_tanpa_lubang_nomor_kontrak(cleanup):
    """Nomor kontrak berurutan walau ada konversi paralel (dulu nomor hangus di request yang gagal)."""
    u1, u2, u3 = available_units(3)
    _, d1, _ = booked_deal(cleanup, unit=u1, tag="Nomor1")
    n1 = contract_seq(ok(call("sales", "POST", f"/deals/{d1['id']}/convert", {}))["contract"]["number"])
    _, d2, _ = booked_deal(cleanup, unit=u2, tag="Nomor2")
    with ThreadPoolExecutor(max_workers=4) as pool:
        res = list(pool.map(lambda _: call("sales", "POST", f"/deals/{d2['id']}/convert", {}), range(4)))
    assert [c for c, _ in res] == [200] * 4, [str(d)[:100] for c, d in res]
    n2 = contract_seq(res[0][1]["data"]["contract"]["number"])
    _, d3, _ = booked_deal(cleanup, unit=u3, tag="Nomor3")
    n3 = contract_seq(ok(call("sales", "POST", f"/deals/{d3['id']}/convert", {}))["contract"]["number"])
    assert (n2, n3) == (n1 + 1, n1 + 2), f"nomor berlubang: {n1}, {n2}, {n3}"


def test_kt02_alur_normal_sekuensial_tetap_idempoten(cleanup):
    """Alur normal: konversi pertama membuat, konversi ulang mengembalikan yang sama."""
    lead, deal, unit = booked_deal(cleanup, tag="Normal")
    first = ok(call("sales", "POST", f"/deals/{deal['id']}/convert", {}))
    assert first["created"] is True and first["contract"]["state"] == "draft"
    again = ok(call("sales", "POST", f"/deals/{deal['id']}/convert", {}))
    assert again["created"] is False
    assert again["contract"]["id"] == first["contract"]["id"]
    assert again["customer"]["id"] == first["customer"]["id"]
    assert first["contract"]["deal_id"] == deal["id"]


# ============================================================================ KT-01
def test_kt01_sales_ppjb_ajb_ditolak_dan_unit_tidak_sold(cleanup):
    """Sales memanggil jalur legal lama -> ditolak (izin kontrak:manage); unit TIDAK sold."""
    lead, deal, unit = booked_deal(cleanup, tag="LegalSales")
    ok(call("sales", "POST", f"/deals/{deal['id']}/convert", {}))
    c1, r1 = call("sales", "POST", f"/deals/{deal['id']}/ppjb", {})
    c2, r2 = call("sales", "POST", f"/deals/{deal['id']}/ajb", {"notary": "Notaris P0KT"})
    assert (c1, c2) == (403, 403), (c1, str(r1)[:200], c2, str(r2)[:200])
    assert unit_status(unit["code"])["status"] == "booked"
    d = ok(call("manager", "GET", f"/deals/{deal['id']}"))
    assert d["status"] == "booked" and not d.get("legal_stage") and not d.get("sold_at")


def test_kt01_manager_ppjb_ajb_lewat_gerbang_kontrak(cleanup):
    """Manajer pun tidak bisa menjual unit hanya dengan booking fee: gerbang DP/pelunasan berlaku."""
    lead, deal, unit = booked_deal(cleanup, tag="LegalMgr")
    contract = ok(call("sales", "POST", f"/deals/{deal['id']}/convert", {}))["contract"]
    c1, r1 = call("manager", "POST", f"/deals/{deal['id']}/ppjb", {})
    assert c1 == 400 and "DP" in str(r1), (c1, str(r1)[:300])
    c2, r2 = call("manager", "POST", f"/deals/{deal['id']}/ajb", {"notary": "Notaris P0KT"})
    assert c2 == 400, (c2, str(r2)[:300])
    assert unit_status(unit["code"])["status"] == "booked"
    k = ok(call("manager", "GET", f"/contracts/{contract['id']}"))
    assert k["legal"] == {} and k["legal_stage"] == "belum" and k["state"] == "draft"
    d = ok(call("manager", "GET", f"/deals/{deal['id']}"))
    assert d["status"] == "booked" and not d.get("legal_stage")


def test_kt01_deal_tanpa_kontrak_diarahkan_ke_jadikan_pembeli(cleanup):
    lead, deal, unit = booked_deal(cleanup, tag="LegalNoContract")
    code, body = call("manager", "POST", f"/deals/{deal['id']}/ppjb", {})
    assert code == 400 and "Jadikan Pembeli" in str(body), (code, str(body)[:300])
    assert unit_status(unit["code"])["status"] == "booked"


def test_kt01_ppjb_lewat_jalur_lama_sukses_bila_dp_terbayar_dan_satu_sumber_kebenaran(cleanup):
    """Pembungkus lama tetap bisa dipakai manajer SETELAH gerbang kontrak terpenuhi; deal & kontrak sinkron."""
    lead, deal, unit = booked_deal(cleanup, tag="LegalOK")
    contract = ok(call("sales", "POST", f"/deals/{deal['id']}/convert", {}))["contract"]
    ar = ok(call("finance", "GET", f"/finance/ar/{deal['id']}"))
    dp = int(ar["items"][0]["amount"])
    kurang = dp - int(ar.get("paid") or 0)
    assert kurang > 0
    fid = upload_proof(deal["id"])
    ok(call("finance", "POST", "/finance/ar/receipts",
            {"deal_id": deal["id"], "amount": kurang, "method": "transfer", "note": "P0KT DP",
             "proof_file_ids": [fid]}))
    d = ok(call("manager", "POST", f"/deals/{deal['id']}/ppjb", {"note": "uji P0"}))
    assert d["legal_stage"] == "ppjb" and d["ppjb"]["number"]
    k = ok(call("manager", "GET", f"/contracts/{contract['id']}"))
    assert k["legal_stage"] == "ppjb" and k["legal"]["ppjb"]["number"] == d["ppjb"]["number"]
    # Ulangi -> ditolak (sudah tercatat), tidak membuat nomor kedua.
    c, body = call("manager", "POST", f"/deals/{deal['id']}/ppjb", {})
    assert c == 400, (c, str(body)[:200])
    # AJB masih tertahan: belum lunas & belum BAST -> unit tetap bukan sold.
    c, body = call("manager", "POST", f"/deals/{deal['id']}/ajb", {"notary": "Notaris P0KT"})
    assert c == 400, (c, str(body)[:200])
    assert unit_status(unit["code"])["status"] == "booked"


# ============================================================================ KT-07
def test_kt07_jadwal_ar_pada_deal_batal_ditolak(cleanup):
    lead = new_lead(tag="Batal")
    unit = available_units(1)[0]
    deal = ok(reserve(lead["id"], unit))
    cleanup.append(deal["id"])
    ok(call("sales", "POST", f"/deals/{deal['id']}/cancel", {"reason": "uji P0 pembatalan"}))
    code, body = call("finance", "POST", f"/finance/ar/{deal['id']}/schedule",
                      {"scheme_id": scheme_id("cash_keras")})
    assert code == 400 and "batal" in str(body).lower(), (code, str(body)[:300])
    c2, ar = call("finance", "GET", f"/finance/ar/{deal['id']}")
    inv = ar.get("data") if isinstance(ar, dict) else None
    assert c2 == 404 or not inv or inv.get("status") == "cancelled", (c2, str(ar)[:200])
    assert unit_status(unit["code"])["status"] == "available"


# ============================================================================ KT-08
def test_kt08_kupon_kuota_satu_paralel_hanya_satu_terpakai(cleanup):
    code = "P0KT" + uuid.uuid4().hex[:6].upper()
    ok(call("manager", "POST", "/pricing/coupons",
            {"code": code, "name": "P0KT kupon sekali pakai", "kind": "amount", "value": 3_000_000,
             "quota_total": 1, "quota_per_customer": 1, "target": "price"}))
    u1, u2 = available_units(2)
    l1, l2 = new_lead(tag="Kupon1"), new_lead(tag="Kupon2")
    with ThreadPoolExecutor(max_workers=2) as pool:
        f1 = pool.submit(reserve, l1["id"], u1, "sales", "cash_keras", coupon_code=code)
        f2 = pool.submit(reserve, l2["id"], u2, "sales", "cash_keras", coupon_code=code)
        res = [f1.result(), f2.result()]
    for c, body in res:
        if c == 200:
            cleanup.append(body["data"]["id"])
    codes = sorted(c for c, _ in res)
    assert codes == [200, 409], f"harap satu 200 & satu 409 (bukan 500): {codes} {[str(b)[:150] for _, b in res]}"
    menang = next(b["data"] for c, b in res if c == 200)
    assert int(menang["discount"]) == 3_000_000
    # Yang kalah: tidak ada deal tertinggal (unit tetap tersedia, tanpa deal berdiskon yatim).
    kalah_unit = u2 if res[0][0] == 200 else u1
    kalah_lead = l2 if res[0][0] == 200 else l1
    assert unit_status(kalah_unit["code"])["status"] == "available"
    assert ok(call("manager", "GET", "/deals", params={"lead_id": kalah_lead["id"]})) == []
    # Kuota: tepat satu pemakaian.
    coupons = ok(call("manager", "GET", "/pricing/coupons"))
    cp = next(c for c in coupons if c["code"] == code)
    assert cp["used_count"] == 1, cp
    rows = ok(call("manager", "GET", f"/pricing/coupons/{cp['id']}/redemptions"))["rows"]
    assert len([r for r in rows if r["state"] == "used"]) == 1


def test_kt08_kupon_dikembalikan_bila_unit_gagal_ditahan(cleanup):
    """Dua lead berebut SATU unit dengan kupon kuota 5: pemenang unit memakai 1 kuota; yang kalah
    mengembalikan kuotanya (tidak ada kuota 'bocor' dari reservasi yang gagal)."""
    code = "P0KT" + uuid.uuid4().hex[:6].upper()
    ok(call("manager", "POST", "/pricing/coupons",
            {"code": code, "name": "P0KT kupon rebutan unit", "kind": "amount", "value": 1_000_000,
             "quota_total": 5, "quota_per_customer": 1, "target": "price"}))
    unit = available_units(1)[0]
    l1, l2 = new_lead(tag="Rebut1"), new_lead(tag="Rebut2")
    with ThreadPoolExecutor(max_workers=2) as pool:
        f1 = pool.submit(reserve, l1["id"], unit, "sales", "cash_keras", coupon_code=code)
        f2 = pool.submit(reserve, l2["id"], unit, "sales", "cash_keras", coupon_code=code)
        res = [f1.result(), f2.result()]
    for c, body in res:
        if c == 200:
            cleanup.append(body["data"]["id"])
    codes = sorted(c for c, _ in res)
    assert codes[0] == 200 and codes[1] in (400, 409), (codes, [str(b)[:150] for _, b in res])
    cp = next(c for c in ok(call("manager", "GET", "/pricing/coupons")) if c["code"] == code)
    assert cp["used_count"] == 1, cp


def test_kt08_penawaran_ke_reservasi_dengan_kupon_menebus_satu_kali(cleanup):
    """Jalur penawaran → reservasi memakai urutan yang sama: kupon ditebus sekali, deal berdiskon."""
    code = "P0KT" + uuid.uuid4().hex[:6].upper()
    ok(call("manager", "POST", "/pricing/coupons",
            {"code": code, "name": "P0KT kupon penawaran", "kind": "amount", "value": 2_000_000,
             "quota_total": 3, "quota_per_customer": 1, "target": "price"}))
    unit = available_units(1)[0]
    lead = new_lead(tag="Penawaran")
    q = ok(call("sales", "POST", "/quotations",
                {"lead_id": lead["id"], "unit_id": unit["id"], "coupon_code": code,
                 "scheme_id": scheme_id("cash_keras"), "booking_fee": 5_000_000}))
    out = ok(call("sales", "POST", f"/quotations/{q['id']}/convert", {}))
    cleanup.append(out["deal"]["id"])
    assert int(out["deal"]["discount"]) == 2_000_000
    cp = next(c for c in ok(call("manager", "GET", "/pricing/coupons")) if c["code"] == code)
    assert cp["used_count"] == 1, cp
    rows = ok(call("manager", "GET", f"/pricing/coupons/{cp['id']}/redemptions"))["rows"]
    assert [r["ref_id"] for r in rows if r["state"] == "used"] == [out["deal"]["id"]]


def test_kt08_reservasi_tanpa_kupon_tetap_normal(cleanup):
    lead = new_lead(tag="TanpaKupon")
    deal = ok(reserve(lead["id"], available_units(1)[0]))
    cleanup.append(deal["id"])
    assert deal["status"] == "reserved" and int(deal.get("discount") or 0) == 0


# ============================================================================ KT-09
def test_kt09_sales_lain_tidak_boleh_membaca_pembeli_orang(cleanup):
    lead, deal, _ = booked_deal(cleanup, who="sales", tag="Scope")
    cust = ok(call("sales", "POST", f"/deals/{deal['id']}/convert", {}))["customer"]
    cid = cust["id"]
    # Pemilik (sales) dan manajer tetap bisa membaca.
    for who in ("sales", "manager"):
        for path in (f"/customers/{cid}", f"/customers/{cid}/timeline",
                     f"/customers/{cid}/contract-pricing", f"/customers/{cid}/units-construction"):
            assert call(who, "GET", path)[0] == 200, (who, path)
    # Sales lain: ditolak di semua pintu; daftar tidak memuat pembeli itu.
    for path in (f"/customers/{cid}", f"/customers/{cid}/timeline",
                 f"/customers/{cid}/contract-pricing", f"/customers/{cid}/units-construction"):
        code, body = call("sales2", "GET", path)
        assert code == 403, (path, code, str(body)[:200])
    code, body = call("sales2", "PUT", f"/customers/{cid}", {"name": "Dibajak"})
    assert code == 403, (code, str(body)[:200])
    rows = ok(call("sales2", "GET", "/customers", params={"q": lead["name"], "limit": 50}))
    assert rows == []
    rows_owner = ok(call("sales", "GET", "/customers", params={"q": lead["name"], "limit": 50}))
    assert [r["id"] for r in rows_owner] == [cid]
