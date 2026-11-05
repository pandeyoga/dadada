"""Regresi audit GL-06 (tanggal jurnal manual) — jalankan terhadap server hidup:
REACT_APP_BACKEND_URL=http://localhost:8001 pytest backend/tests/p0/test_p0_gl.py
(GL-03 tutup-tahun-ulang memutasi status periode, jadi diverifikasi manual di instance uji, bukan di sini.)
"""
import os

import pytest
import requests

BASE = (os.environ.get("API_BASE") or (os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001").rstrip("/") + "/api")).rstrip("/")


@pytest.fixture(scope="module")
def sa():
    r = requests.post(f"{BASE}/auth/login", json={"email": "superadmin@estora.id", "password": "test1234"}, timeout=30)
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["access_token"]}


def _manual(sa, date):
    return requests.post(f"{BASE}/gl/journals", headers=sa, timeout=30, json={
        "memo": "AUDIT-P0 uji tanggal", "date": date,
        "lines": [{"account_code": "6-1300", "debit": 1000, "credit": 0},
                  {"account_code": "2-1100", "debit": 0, "credit": 1000}]})


@pytest.mark.parametrize("bad", ["bukan-tanggal", "2026-13-40", "xx", "2099-01-01"])
def test_invalid_or_future_manual_date_rejected(sa, bad):
    r = _manual(sa, bad)
    assert r.status_code == 400, (bad, r.status_code, r.text)
    assert "tanggal" in r.json()["detail"].lower()


def test_period_screens_survive(sa):
    for path in ("/gl/periods", "/gl/year", "/gl/reports/closing-history"):
        assert requests.get(f"{BASE}{path}", headers=sa, timeout=30).status_code == 200, path
