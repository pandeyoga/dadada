"""KN-D16 (audit 2026-09-21) — SATU ambang toleransi 3-way match (PO ↔ terima ↔ faktur).

Sebelumnya tiga sisi memakai angka berbeda: vendor bill (qty% dari `purchasing.bill_qty_
tolerance_percent`, harga 5% dari `bill_price_tolerance_percent`, tanpa ambang rupiah) vs
kontrabon (qty% & harga dari `contra_bon.qty_tolerance_percent`=1%, ditambah ambang rupiah).
Kini keduanya membaca fungsi ini:
  • qty_pct   : purchasing.bill_qty_tolerance_percent
  • price_pct : purchasing.bill_price_tolerance_percent
  • value_rp  : contra_bon.value_tolerance_rupiah  (ambang rupiah — selisih kecil diabaikan
                oleh KEDUA layar; 0 = tanpa ambang rupiah)
Sebuah selisih adalah pengecualian bila melewati ambang persen DAN ambang rupiah.
"""
from typing import Any, Dict

from services.config_service import get_effective_settings
from services.config_resolver import value_of


async def tolerances(entity_id: str = "") -> Dict[str, float]:
    s = await get_effective_settings(entity_id or "")
    pur = s.get("purchasing", {}) or {}
    value_rp = await value_of("contra_bon.value_tolerance_rupiah", {"entity_id": entity_id or ""})
    return {
        "qty_pct": float(pur.get("bill_qty_tolerance_percent", 0.0) or 0.0),
        "price_pct": float(pur.get("bill_price_tolerance_percent", 5.0) or 0.0),
        "value_rp": float(value_rp or 0),
    }


def exceeds(pct: float, tol_pct: float, value: float, value_rp: float) -> bool:
    """Pengecualian bila persen DAN rupiah sama-sama melewati ambang."""
    return abs(pct) > tol_pct + 1e-6 and abs(value) > value_rp + 0.01
