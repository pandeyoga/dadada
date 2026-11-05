"""Regresi P1-b — void kuitansi resmi & hapus-paksa yang konsisten (audit IN-05, GL-05, GL-10).

    API_BASE=http://localhost:8020/api python -m pytest backend/tests/p0/test_p0_void_receipt.py -n 0 -q --noconftest
"""
import time

import pytest

from test_p0_masuk import FINANCE, OWNER, World, ar, call, cl_balance, ok, pay, race  # noqa: F401

FINLEAD = "finlead@sipro.co.id"


@pytest.fixture(scope="module")
def world():
    return World()


def _rid(resp):
    return (resp.get("data") or resp)["receipt"]["id"]


def _void(email, rid, reason="uji P0 pembatalan kuitansi"):
    return call(email, "POST", f"/finance/ar/receipts/{rid}/void", json={"reason": reason})


def _reversal_count(deal_id, rid, timeout=5):
    time.sleep(0.5)
    rows = ok(call(FINANCE, "GET", "/gl/journals", params={"source_type": "receipt_void", "source_id": rid}))["data"]
    return len([r for r in rows if r["source_id"] == rid])


def test_void_resmi_membalik_alokasi_kewajiban_dan_jurnal(world):
    d = world.new_deal()["deal_id"]
    rid = _rid(ok(pay(d, 100_000_000)))
    assert cl_balance(d) == 100_000_000
    ok(_void(FINLEAD, rid))
    inv = ar(d)["data"]
    assert int(inv["paid"]) == 0, "alokasi termin harus kembali"
    assert cl_balance(d) == 0, "kewajiban kontrak harus turun"
    rc = [r for r in ar(d)["receipts"] if r["id"] == rid][0]
    assert rc["status"] == "void", "kuitansi TETAP ada sebagai jejak, berstatus void"
    assert _reversal_count(d, rid) == 1
    assert ok(call(FINANCE, "GET", "/finance/reconcile"))["data"]["ok"]


def test_void_pencatat_sendiri_ditolak_pemisahan_tugas(world):
    d = world.new_deal()["deal_id"]
    rid = _rid(ok(pay(d, 50_000_000)))
    r = _void(FINANCE, rid)
    assert r.status_code == 400 and "Pemisahan tugas" in r.text, r.text
    assert cl_balance(d) == 50_000_000, "tidak ada efek"


def test_void_paralel_hanya_satu_pembalikan(world):
    d = world.new_deal()["deal_id"]
    rid = _rid(ok(pay(d, 80_000_000)))
    rs = race([lambda: _void(FINLEAD, rid) for _ in range(3)])
    oks = [r for r in rs if r.status_code == 200]
    assert len(oks) == 1, [(r.status_code, r.text[:120]) for r in rs]
    assert cl_balance(d) == 0 and int(ar(d)["data"]["paid"]) == 0
    assert _reversal_count(d, rid) == 1, "jurnal pembalik hanya satu"


def test_void_dua_kali_berurutan_ditolak(world):
    d = world.new_deal()["deal_id"]
    rid = _rid(ok(pay(d, 20_000_000)))
    ok(_void(FINLEAD, rid))
    assert _void(FINLEAD, rid).status_code == 400


def test_void_butuh_alasan_dan_izin(world):
    d = world.new_deal()["deal_id"]
    rid = _rid(ok(pay(d, 10_000_000)))
    assert _void(FINLEAD, rid, reason="x").status_code == 400
    assert _void("sales@sipro.co.id", rid).status_code == 403


def test_hapus_paksa_menurunkan_kewajiban_kontrak(world):
    """Dulu hapus-paksa menghapus jurnal tetapi kewajiban kontrak (subledger) tetap → tie-out 2-1400 merah."""
    d = world.new_deal()["deal_id"]
    rid = _rid(ok(pay(d, 60_000_000)))
    time.sleep(10)  # biarkan jurnal terbit lebih dulu
    ok(call(OWNER, "DELETE", f"/finance/ar/receipts/{rid}", params={"reason": "uji P0 hapus paksa konsisten"}))
    assert cl_balance(d) == 0
    assert ok(call(FINANCE, "GET", "/finance/reconcile"))["data"]["ok"]
