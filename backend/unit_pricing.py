"""Harga unit per JENIS skema pembayaran (cash_keras / cash_bertahap / kpr).

`units.scheme_prices = {kind: harga}` opsional; jenis yang tidak diisi memakai `units.price`
(harga dasar). Satu fungsi dipakai penawaran, reservasi, dan rincian kontrak supaya angka
tidak berbeda antar layar.
"""
import reference as ref

SCHEME_KINDS = ("cash_keras", "cash_bertahap", "kpr")


def clean_scheme_prices(raw) -> dict:
    """Validasi input `{kind: harga}` → hanya kind yang dikenal, harga int ≥ 0 (0/None = hapus)."""
    out = {}
    for k, v in (raw or {}).items():
        if k not in SCHEME_KINDS:
            raise ValueError(f"Jenis skema '{k}' tidak dikenal (cash_keras/cash_bertahap/kpr).")
        if v in (None, "", 0, "0"):
            continue
        n = int(v)
        if n < 0:
            raise ValueError("Harga per skema tidak boleh negatif.")
        out[k] = n
    return out


def price_for(unit: dict, kind: str | None) -> int:
    """Harga unit untuk jenis skema; jatuh ke `price` bila jenis itu tidak punya harga khusus."""
    sp = unit.get("scheme_prices") or {}
    v = sp.get(kind) if kind else None
    return int(v) if v else int(unit.get("price") or 0)


def price_source(unit: dict, kind: str | None) -> str:
    return "skema" if kind and (unit.get("scheme_prices") or {}).get(kind) else "dasar"


def price_table(unit: dict) -> list:
    """Daftar harga per jenis skema untuk layar (pricelist/unit detail)."""
    return [{"kind": k, "label": ref.label_of("payment_scheme_kind", k),
             "price": price_for(unit, k), "source": price_source(unit, k)}
            for k in SCHEME_KINDS]
