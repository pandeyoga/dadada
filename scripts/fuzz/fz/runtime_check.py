"""Evaluasi semua invarian pada satu snapshot → daftar V."""
import time
import traceback

from .core import REGISTRY, Snap
from . import invariants   # noqa: F401  (mendaftarkan semua invarian)


def evaluate(db, org="org-sipro", api=None, settled=True, only=None, skip=None):
    s = Snap(db, org)
    s.api = api
    res, errs = [], []
    for iid, inv in REGISTRY.items():
        if only and iid not in only:
            continue
        if skip and iid in skip:
            continue
        if inv.settled and not settled:
            inv.skipped += 1
            continue
        t0 = time.time()
        try:
            vs = inv.fn(s)
        except Exception as e:   # noqa: BLE001 — galat alat ≠ pelanggaran aplikasi; dicatat terpisah
            errs.append((iid, f"{type(e).__name__}: {e}", traceback.format_exc(limit=3)))
            continue
        inv.runs += 1
        inv.viol += len(vs)
        res.extend(vs)
    return res, errs
