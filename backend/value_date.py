"""Tanggal bayar nyata (`value_date`) untuk transaksi uang (audit GL-15 / IN-19).

Kuitansi manual dan pembayaran AP dulu SELALU dibukukan bertanggal "sekarang" (waktu input), sehingga uang
yang sebenarnya masuk/keluar kemarin atau di bulan lalu tidak bisa dibukukan pada tanggal terjadinya
(cut-off bulan/tahun, rekonsiliasi per tanggal).

Aturan `value_date` (opsional; kosong = sekarang, perilaku lama):
  * tanggal ISO sah (YYYY-MM-DD) dan TIDAK di masa depan (WIB);
  * tidak boleh jatuh di periode akuntansi yang sudah DITUTUP (laporan yang sudah dibagikan tidak berubah);
  * tidak boleh jatuh di periode yang sudah DIKUNCI untuk rekening/kas tujuan (rekonsiliasi seimbang).
Ditolak (bukan digeser) — pengguna menyebut tanggal itu dengan sengaja, jadi harus tahu bila tidak bisa.
"""
from datetime import date

import cash_period_lock
import gl_periods
from core_utils import period_of
from p27_utils import clean_cash_date


async def check(org: str, value, *, cash_code: str = None, what: str = "Tanggal bayar"):
    """Kembalikan tanggal bersih 'YYYY-MM-DD' (atau None bila kosong). ValueError (Indonesia) bila tidak sah."""
    if not value:
        return None
    raw = clean_cash_date(str(value).strip(), what)[:10]
    try:
        date.fromisoformat(raw)
    except ValueError:
        raise ValueError(f"{what} '{raw}' tidak valid — gunakan format tahun-bulan-tanggal (YYYY-MM-DD).")
    per = period_of(raw)
    if per in await gl_periods.closed_periods(org):
        raise ValueError(f"{what} {raw} jatuh di periode {per} yang sudah DITUTUP. Pilih tanggal di periode "
                         "terbuka, atau minta Manajer Keuangan membuka periodenya dulu.")
    if cash_code:
        locked = (await cash_period_lock.locked_through(org)).get(cash_code)
        if locked and per <= locked:
            raise ValueError(f"{what} {raw} jatuh di periode {per} yang rekening/kasnya sudah DIKUNCI "
                             f"(rekonsiliasi seimbang s.d. {locked}). Pilih tanggal sesudahnya.")
    return raw
