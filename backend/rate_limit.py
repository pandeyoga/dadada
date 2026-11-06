"""Pembatas laju sederhana (jendela geser, di memori proses) — pola yang sama dengan `_rate_ok`
di `routers/public_router.py`, dijadikan satu berkas agar bisa dipakai router lain
(OTP portal, formulir web publik) tanpa menyalin kode.

Catatan jujur: hitungan hidup di memori PROSES — dengan beberapa worker batas efektifnya
dikali jumlah worker, dan hilang saat restart. Cukup untuk menahan penyalahgunaan massal;
penjagaan yang HARUS tahan banting (mis. kunci percobaan OTP) disimpan di database.
"""
import time

_HITS: dict = {}


def hit_ok(bucket: str, key: str, max_hits: int, window_s: float) -> bool:
    """Catat satu kejadian untuk (bucket, key); False bila batas `max_hits` per `window_s` terlewati."""
    now = time.time()
    k = f"{bucket}:{key}"
    hits = [t for t in _HITS.get(k, []) if now - t < window_s]
    if len(hits) >= max_hits:
        _HITS[k] = hits
        return False
    hits.append(now)
    _HITS[k] = hits
    if len(_HITS) > 20000:  # jaga memori: buang kunci yang sudah kedaluwarsa
        for old in [x for x, v in _HITS.items() if not v or now - v[-1] >= window_s]:
            _HITS.pop(old, None)
    return True


def reset(bucket: str = None) -> None:
    """Kosongkan hitungan (dipakai tes / saat konfigurasi berubah)."""
    for k in [k for k in _HITS if bucket is None or k.startswith(f"{bucket}:")]:
        _HITS.pop(k, None)
