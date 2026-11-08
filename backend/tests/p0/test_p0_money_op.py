"""Regresi H-B — `money_op` (G1, satu pintu uang keluar): urutan once → deal_money → funds_guard → blok, dan ekuivalensi jalur yang dipindahkan.

    API_BASE=http://localhost:8072/api DB_NAME=sipro_hb MONGO_URL=... python -m pytest backend/tests/p0/test_p0_money_op.py -n 0 -q --noconftest

Jujur soal merah/hijau:
  * tes in-process (kelas `TestMoneyOp*`) MERAH di kode lama karena modul `money_op` belum ada (ImportError);
  * tes EKUIVALENSI (kelas `TestEkuivalensi*`) lewat API sungguhan HARUS hijau di kode lama DAN baru — jalur yang dipindahkan
    (aset tetap, fee marketing, upah, pengajuan dana, kas bon) tidak boleh berubah perilakunya.
"""
import asyncio
import os
import sys
import uuid
from contextlib import asynccontextmanager

import pytest

import aio
from test_p0_masuk import FINANCE, OWNER, call, codes, ok, race

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
ORG = "org-sipro"
PM = "pm@sipro.co.id"


def _uid(p="M"):
    return f"{p}{uuid.uuid4().hex[:6].upper()}"


def _bank(opening):
    body = {"kind": "bank", "name": f"Rek MO {_uid('R')}", "bank_name": "Bank Uji MO",
            "account_no": _uid("NO"), "opening_balance": opening}
    return ok(call(FINANCE, "POST", "/cash-bank/accounts", json=body))["data"]


def _balance(acc_id):
    rows = ok(call(FINANCE, "GET", "/cash-bank/accounts"))["data"]
    return int([a for a in rows if a["id"] == acc_id][0]["balance"])


# ====================================================================== urutan & aturan lewati (in-process, tanpa DB)
class TestMoneyOpUrutan:
    def _patched(self, monkeypatch, log):
        import money_op as mo

        def rec(name):
            @asynccontextmanager
            async def cm(*a, **kw):
                log.append((name, "masuk", a, kw))
                yield f"{name}-hasil"
                log.append((name, "keluar"))
            return cm
        monkeypatch.setattr(mo, "once", rec("once"))
        monkeypatch.setattr(mo, "deal_money", rec("deal"))
        monkeypatch.setattr(mo.cb, "funds_guard", rec("funds"))
        return mo

    def test_urutan_masuk_dan_keluar_berkebalikan(self, monkeypatch):
        log = []
        mo = self._patched(monkeypatch, log)

        async def go():
            async with mo.money_op(ORG, op="uji.bayar", key=("a", 1), client_ref="ref-1", amount=500, cash_account_id="acc",
                                   cash_code="1-1200", kind="pembayaran uji", deal_id="deal-1", flush_events=True) as m:
                log.append(("blok",))
                return m
        m = aio.run(go())
        assert [e[:2] if len(e) > 1 else e for e in log] == [
            ("once", "masuk"), ("deal", "masuk"), ("funds", "masuk"), ("blok",),
            ("funds", "keluar"), ("deal", "keluar"), ("once", "keluar")], log
        assert m.cash_code == "funds-hasil" and m.once_key == "once-hasil"
        # argumen diteruskan apa adanya
        once_call = next(e for e in log if e[0] == "once" and e[1] == "masuk")
        assert once_call[2] == ("uji.bayar", "a", 1) and once_call[3]["client_ref"] == "ref-1"
        funds_call = next(e for e in log if e[0] == "funds" and e[1] == "masuk")
        assert funds_call[2] == (ORG, 500) and funds_call[3]["cash_account_id"] == "acc" \
            and funds_call[3]["code"] == "1-1200" and funds_call[3]["flush_events"] is True \
            and funds_call[3]["kind"] == "pembayaran uji"
        deal_call = next(e for e in log if e[0] == "deal" and e[1] == "masuk")
        assert deal_call[2] == (ORG, "deal-1")

    def test_tanpa_op_deal_atau_kas_tidak_ada_penjaga_yang_dipasang(self, monkeypatch):
        log = []
        mo = self._patched(monkeypatch, log)

        async def go():
            async with mo.money_op(ORG, amount=0, cash_code="1-1200") as a:       # nominal 0 → tanpa kunci rekening
                pass
            async with mo.money_op(ORG, amount=100) as b:                          # nominal tanpa kas → tanpa kunci rekening
                pass
            return a, b
        a, b = aio.run(go())
        assert log == [] and a.cash_code is None and b.once_key is None

    def test_kegagalan_blok_melepas_semua_penjaga_dan_meneruskan_galat(self, monkeypatch):
        log = []
        mo = self._patched(monkeypatch, log)

        async def go():
            async with mo.money_op(ORG, op="x", key="k", amount=1, cash_code="1-1200", deal_id="d"):
                raise RuntimeError("blok gagal")
        with pytest.raises(RuntimeError):
            aio.run(go())
        assert [e[:2] for e in log if len(e) > 1] == [("once", "masuk"), ("deal", "masuk"), ("funds", "masuk"),
                                                      ("funds", "keluar"), ("deal", "keluar"), ("once", "keluar")]


# ====================================================================== dengan database sungguhan
class TestMoneyOpDenganDb:
    def test_once_permintaan_identik_kedua_ditolak_gagal_melepas_kunci(self):
        import money_op as mo
        from idempotency import Conflict
        k = _uid("K")

        async def sekali():
            async with mo.money_op(ORG, op="uji.mo", key=(k,)):
                return "ok"

        async def gagal():
            async with mo.money_op(ORG, op="uji.mo.gagal", key=(k,)):
                raise ValueError("gagal sebelum selesai")

        assert aio.run(sekali()) == "ok"
        with pytest.raises(Conflict):
            aio.run(sekali())                    # sukses menahan permintaan identik
        with pytest.raises(ValueError):
            aio.run(gagal())
        with pytest.raises(ValueError):
            aio.run(gagal())                     # gagal melepas kunci → boleh dicoba lagi (bukan Conflict)

    def test_cek_dana_menolak_sebelum_blok_dan_lolos_bila_cukup(self):
        import money_op as mo
        acc = _bank(1_000_000)
        ran = []

        async def go(amount):
            async with mo.money_op(ORG, amount=amount, cash_account_id=acc["id"], kind="uji money_op") as m:
                ran.append(amount)
                return m.cash_code
        with pytest.raises(ValueError) as e:
            aio.run(go(2_000_000))
        assert "Saldo" in str(e.value) and "uji money_op" in str(e.value)
        assert ran == []
        assert aio.run(go(400_000)) == acc["gl_account_code"] and ran == [400_000]

    def test_dua_pengeluaran_bersamaan_dari_rekening_sama_diserialkan(self):
        import money_op as mo
        acc = _bank(1_000_000)
        aktif, tumpang = [], []

        async def keluar(n):
            async with mo.money_op(ORG, amount=100, cash_account_id=acc["id"]):
                aktif.append(n)
                if len(aktif) > 1:
                    tumpang.append(tuple(aktif))
                await asyncio.sleep(0.15)
                aktif.remove(n)

        async def go():
            await asyncio.gather(*[keluar(i) for i in range(3)])
        aio.run(go())
        assert tumpang == [], "blok dua pengeluaran dari rekening yang sama tidak boleh tumpang tindih"

    def test_deal_id_menyerialkan_per_deal(self):
        import money_op as mo
        aktif, tumpang = [], []
        deal = _uid("DEAL")

        async def keluar(n):
            async with mo.money_op(ORG, deal_id=deal):
                aktif.append(n)
                if len(aktif) > 1:
                    tumpang.append(tuple(aktif))
                await asyncio.sleep(0.1)
                aktif.remove(n)

        async def go():
            await asyncio.gather(*[keluar(i) for i in range(3)])
        aio.run(go())
        assert tumpang == []


# ====================================================================== ekuivalensi jalur yang dipindahkan (hijau di kode lama DAN baru)
class TestEkuivalensiJalurYangDipindahkan:
    def test_aset_tetap_klik_ganda_satu_aset(self):
        body = {"name": f"Aset MO {_uid()}", "category": "komputer_it", "tax_group": "kelompok_1", "method": "garis_lurus",
                "cost": 3_000_000, "salvage_value": 0, "useful_life_months": 12, "acquired_date": "2026-01-15", "funding": "bank"}
        rs = race([lambda: call(FINANCE, "POST", "/fixed-assets/assets", json=body) for _ in range(4)])
        assert codes(rs).count(200) == 1 and set(codes(rs)) <= {200, 409}, [(r.status_code, r.text[:100]) for r in rs]

    def test_aset_tetap_utang_usaha_jalur_tanpa_kas_tetap_jalan(self):
        body = {"name": f"Aset Utang MO {_uid()}", "category": "komputer_it", "tax_group": "kelompok_1", "method": "garis_lurus",
                "cost": 2_000_000, "salvage_value": 0, "useful_life_months": 12, "funding": "utang_usaha",
                "vendor": "Vendor MO"}
        r = call(FINANCE, "POST", "/fixed-assets/assets", json=body)
        assert r.status_code == 200, (r.status_code, r.text[:200])

    def test_kas_bon_cairkan_melebihi_saldo_ditolak_dan_saldo_tetap(self):
        acc = _bank(1_000_000)
        aid = ok(call(PM, "POST", "/petty-cash/advances", json={"purpose": _uid("Kas bon MO "), "amount": 3_000_000,
                                                                "category": "transport"}))["data"]["id"]
        ok(call(FINANCE, "POST", f"/petty-cash/advances/{aid}/approve", json={}))
        r = call(FINANCE, "POST", f"/petty-cash/advances/{aid}/disburse", json={"source": "bank", "cash_account_id": acc["id"]})
        assert r.status_code == 400 and "Saldo" in r.text, (r.status_code, r.text[:200])
        assert _balance(acc["id"]) == 1_000_000
        adv = ok(call(FINANCE, "GET", f"/petty-cash/advances/{aid}"))["data"]
        assert adv["status"] == "approved"      # klaim `disbursing` tidak pernah dipasang karena cek dana gagal lebih dulu
