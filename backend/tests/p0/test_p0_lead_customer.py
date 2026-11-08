"""Regresi P1-c — sinkronisasi lead↔customer↔deal & identitas pembeli (audit KT-15, KT-16, KT-17).

    API_BASE=http://localhost:8020/api python -m pytest backend/tests/p0/test_p0_lead_customer.py -n 0 -q --noconftest

Memakai helper tes kontrak (test_p0_kontrak.py): lead/deal berawalan `P0KT`, dibersihkan otomatis.
"""
import random
import uuid

import pytest

from test_p0_kontrak import (  # noqa: F401  (fixture `cleanup` ikut diimpor)
    _lead_names, booked_deal, call, cleanup, ok, pemicu_spr,   # noqa: F401  (fixture ikut diimpor)
)


def _convert(deal_id, who="sales", body=None):
    return ok(call(who, "POST", f"/deals/{deal_id}/convert", body or {}))


# ============================================================================ KT-16
def test_kt16_reassign_pic_memindahkan_deal_dan_kontrak(cleanup):
    lead, deal, _ = booked_deal(cleanup, who="sales", tag="Pic")
    conv = _convert(deal["id"])
    cid = conv["contract"]["id"]
    assert call("sales", "GET", f"/deals/{deal['id']}")[0] == 200
    ok(call("manager", "POST", f"/leads/{lead['id']}/assign", {"assigned_to": "sales2@sipro.co.id"}))
    # PIC baru bisa menangani transaksi lead yang baru diterimanya
    assert call("sales2", "GET", f"/deals/{deal['id']}")[0] == 200
    assert call("sales2", "GET", f"/contracts/{cid}")[0] == 200
    # PIC lama tidak lagi punya akses
    assert call("sales", "GET", f"/deals/{deal['id']}")[0] == 403
    assert call("sales", "GET", f"/contracts/{cid}")[0] == 403


# ============================================================================ KT-15
def test_kt15_edit_nama_lead_pasca_konversi_tersinkron(cleanup):
    lead, deal, _ = booked_deal(cleanup, who="sales", tag="Sync")
    conv = _convert(deal["id"])
    cust_id = conv["customer"]["id"]
    new_name = f"P0KT Nama Baru {uuid.uuid4().hex[:5]}"
    _lead_names.append(new_name)
    ok(call("sales", "PUT", f"/leads/{lead['id']}", {"name": new_name}))
    cust = ok(call("owner", "GET", f"/customers/{cust_id}"))
    assert cust["name"] == new_name, "nama pembeli harus ikut berubah"
    d = ok(call("sales", "GET", f"/deals/{deal['id']}"))
    assert d.get("lead_name") == new_name, "salinan nama lead di deal harus ikut berubah"
    rows = ok(call("manager", "GET", "/contracts", params={"q": new_name}))
    assert any(c["id"] == conv["contract"]["id"] for c in rows), "pencarian kontrak dengan nama baru harus menemukan kontraknya"


# ============================================================================ KT-17
def _uniq_phone():
    return "0812" + "".join(random.choice("0123456789") for _ in range(8))


def _uniq_nik():
    return "31" + "".join(random.choice("0123456789") for _ in range(14))


@pytest.mark.parametrize("bad", [{"nik": "123"}, {"npwp": "abc"}, {"monthly_income": -5000}])
def test_kt17_identitas_tidak_sah_ditolak(cleanup, bad):
    name = f"P0KT Ident {uuid.uuid4().hex[:5]}"
    _lead_names.append(name)
    code, body = call("manager", "POST", "/customers", {"name": name, "phone": _uniq_phone(), **bad})
    assert code == 400, (code, str(body)[:200])


def test_kt17_telepon_dan_email_kembar_ditolak(cleanup):
    name = f"P0KT Dup {uuid.uuid4().hex[:5]}"
    _lead_names.append(name)
    phone, email = _uniq_phone(), f"p0kt{uuid.uuid4().hex[:6]}@example.com"
    ok(call("manager", "POST", "/customers", {"name": name, "phone": phone, "email": email}))
    # nomor sama dengan format berbeda (+62...) → ditolak
    code, body = call("manager", "POST", "/customers", {"name": name + " B", "phone": "+62" + phone[1:]})
    assert code == 409, (code, str(body)[:200])
    code, body = call("manager", "POST", "/customers", {"name": name + " C", "phone": _uniq_phone(), "email": email.upper()})
    assert code == 409, (code, str(body)[:200])
    # orang berbeda yang sengaja berbagi nomor: boleh dengan allow_duplicate
    ok(call("manager", "POST", "/customers", {"name": name + " D", "phone": phone, "allow_duplicate": True}))


def test_kt17_nik_berformat_beda_tetap_terdeteksi_kembar(cleanup):
    name = f"P0KT Nik {uuid.uuid4().hex[:5]}"
    _lead_names.append(name)
    nik = _uniq_nik()
    ok(call("manager", "POST", "/customers", {"name": name, "phone": _uniq_phone(), "nik": nik}))
    dashed = f"{nik[:4]}-{nik[4:8]}-{nik[8:12]}-{nik[12:]}"
    code, _ = call("manager", "POST", "/customers", {"name": name + " X", "phone": _uniq_phone(), "nik": dashed})
    assert code == 409


def test_kt17_konversi_menolak_nik_tak_sah_dan_menormalisasi(cleanup, pemicu_spr):
    lead, deal, _ = booked_deal(cleanup, who="sales", tag="Nik")
    code, body = call("sales", "POST", f"/deals/{deal['id']}/convert", {"nik": "123"})
    assert code == 400, (code, str(body)[:200])
    nik = _uniq_nik()
    dashed = f"{nik[:4]}-{nik[4:8]}-{nik[8:12]}-{nik[12:]}"
    conv = ok(call("sales", "POST", f"/deals/{deal['id']}/convert", {"nik": dashed}))
    assert ok(call("owner", "GET", f"/customers/{conv['customer']['id']}"))["nik"] == nik
