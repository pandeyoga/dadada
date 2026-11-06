"""Regresi PL-05 — tanggal bisnis memakai WIB, bukan UTC (dini hari WIB "hari ini" ditolak sebagai "masa depan").

Tidak butuh server: fungsi dipanggil langsung dengan jam disimulasikan 05:00 WIB 7 Nov (= 22:00 UTC 6 Nov).
Butuh env DB_NAME/MONGO_URL (modul memuat koneksi; tidak ada yang ditulis ke database).

    DB_NAME=<db> MONGO_URL=<url> python -m pytest backend/tests/p0/test_p0_waktu.py -n 0 -q --noconftest
"""
import asyncio
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
pytest.importorskip("motor")

FAKE_UTC = "2026-11-06T22:00:00+00:00"   # = 07 Nov 2026 05:00 WIB
WIB_TODAY = "2026-11-07"


def test_today_wib_dini_hari_adalah_hari_berikutnya_dari_tanggal_utc():
    import core_utils
    from datetime import datetime, timezone
    real = core_utils.datetime

    class Fake(real):
        @classmethod
        def now(cls, tz=None):
            base = datetime.fromisoformat(FAKE_UTC)
            return base.astimezone(tz) if tz else base

    core_utils.datetime = Fake
    try:
        assert core_utils.today_wib() == WIB_TODAY
        assert FAKE_UTC[:10] != WIB_TODAY, "uji ini hanya berarti bila tanggal UTC berbeda dari WIB"
    finally:
        core_utils.datetime = real


def test_giro_diterima_hari_ini_wib_tidak_ditolak_sebagai_masa_depan():
    import pdc_engine
    pdc_engine.now_iso = lambda: FAKE_UTC
    pdc_engine.today_wib = lambda: WIB_TODAY
    with pytest.raises(Exception) as e:
        asyncio.run(pdc_engine._receive_locked("org-sipro", {
            "kind": "cek", "amount": 1_000_000, "due_date": "2026-11-20", "received_date": WIB_TODAY,
            "deal_id": "tidak-ada-uji-waktu"}, "uji@x"))
    assert "masa depan" not in str(e.value), f"tanggal hari ini (WIB) ditolak: {e.value}"
