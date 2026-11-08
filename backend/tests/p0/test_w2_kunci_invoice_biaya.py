"""Regresi — kunci penerbitan invoice biaya harus SAMA untuk jalur `deal.booked` (kontrak semu, id kosong) dan `ensure_contract`
(id kontrak): temuan sampingan W2-B (dua invoice biaya untuk satu deal, selisih 2 md, 'system' + 'sales').

    API_BASE=http://localhost:8062/api python -m pytest backend/tests/p0/test_w2_kunci_invoice_biaya.py -n 0 -q --noconftest

Deterministik (tanpa balapan): merekam kunci yang diambil `issue_cost_invoice`. Balapan asli bersifat probabilistik dan tidak pernah merah terukur.
"""
import os
import sys

import aio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def test_kunci_invoice_biaya_sama_untuk_kontrak_semu_dan_kontrak_asli(monkeypatch):
    import allin_engine as ae
    keys = []

    class _Rekam:
        def __init__(self, *a, **kw):
            keys.append(a[:2])

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

    async def _noop(org, contract, actor):
        return {"ok": True}

    monkeypatch.setattr(ae, "locked", _Rekam)
    monkeypatch.setattr(ae, "_issue_cost_invoice_locked", _noop)
    semu = {"id": None, "deal_id": "deal-xyz"}        # deal_as_contract (handler deal.booked)
    asli = {"id": "kontrak-abc", "deal_id": "deal-xyz"}   # ensure_contract
    aio.run(ae.issue_cost_invoice("org", semu, "system"))
    aio.run(ae.issue_cost_invoice("org", asli, "sales"))
    assert keys[0] == keys[1] == ("allin.issue", "deal-xyz"), keys
