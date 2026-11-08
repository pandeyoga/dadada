"""`money_op` — SATU PINTU uang KELUAR (pagar G1, audit `11_POLA_BUG_DAN_SAPUAN` §5/§7).

Latar belakang: tiap jalur uang keluar (aset tetap, fee marketing, upah, pengajuan dana, kas bon, komisi, ...) merakit
sendiri gabungan "anti klik-ganda → kunci per-deal → kunci rekening + cek saldo", dan masing-masing memilih himpunan
bagian yang berbeda (PK-06 dipasang di 17 jalur tetapi transfer internal lupa; PL-03: 9 jalur mengecek tanpa kunci).
Selama gabungan itu dirakit tangan, perbaikan per-jalur terus bocor di jalur berikutnya.

Pintu ini selalu menyusunnya dengan URUTAN TETAP (dari luar ke dalam):

    1. `once(op, *key, client_ref=...)`   anti klik-ganda / retry jaringan (dilepas bila blok gagal)
    2. `deal_money(org, deal_id)`          mutex per-deal (bila `deal_id`): sejalan dengan terima/void/batal/hapus deal
    3. `cash_bank.funds_guard(...)`        kunci per rekening → cek dana (bila `amount > 0` dan ada kas); kunci DIPEGANG
                                           sampai blok pemanggil selesai (jurnal sudah tampak di buku)
    4. blok pemanggil                       tulis subledger + posting jurnal

Pemakaian:

    async with money_op(org, op="asset.create", key=(org, name, cost, date, actor), amount=cost,
                        cash_code=FUNDING_BANK, kind=f"perolehan aset {name}", what="Pencatatan aset ini") as m:
        ...                                 # m.cash_code = sub-akun kas/bank yang terkunci

Semua parameter selain `org` bersifat keyword. `op=None` = tanpa anti klik-ganda (jalur yang sudah mengklaim dokumennya
sendiri lewat `idempotency.reserved`); `amount<=0` atau tanpa kas = tanpa kunci rekening (mis. perolehan aset secara utang,
rekonsiliasi bank yang uangnya SUDAH keluar). Aturan sapuan statis `P3b_assert_funds_langsung` (scripts/pattern_sweep.py)
menandai fungsi di luar `cash_bank.py`/`money_op.py` yang memanggil `assert_funds` langsung — jalur baru wajib lewat sini.
"""
from contextlib import AsyncExitStack, asynccontextmanager
from dataclasses import dataclass

import cash_bank as cb
from deal_money import deal_money
from idempotency import DEFAULT_WINDOW_SECONDS, once


@dataclass
class MoneyCtx:
    """Apa yang diketahui blok pemanggil: sub-akun kas/bank yang terkunci (None bila tanpa kas) dan kunci idempotensi."""
    cash_code: str = None
    once_key: str = None


@asynccontextmanager
async def money_op(org: str, *, op: str = None, key=None, client_ref: str = None, amount=0,
                   cash_account_id: str = None, cash_code: str = None, kind: str = "Pembayaran",
                   deal_id: str = None, flush_events: bool = False,
                   window: int = DEFAULT_WINDOW_SECONDS, what: str = "Permintaan yang sama"):
    """Lihat docstring modul. `key` = bagian-bagian sidik jari permintaan (tuple/list atau satu nilai)."""
    parts = tuple(key) if isinstance(key, (list, tuple)) else (() if key is None else (key,))
    ctx = MoneyCtx()
    async with AsyncExitStack() as stack:
        if op:
            ctx.once_key = await stack.enter_async_context(
                once(op, *parts, client_ref=client_ref, window=window, what=what))
        if deal_id:
            await stack.enter_async_context(deal_money(org, deal_id))
        if int(amount or 0) > 0 and (cash_account_id or cash_code):
            ctx.cash_code = await stack.enter_async_context(
                cb.funds_guard(org, amount, cash_account_id=cash_account_id, code=cash_code,
                               kind=kind, flush_events=flush_events))
        yield ctx
