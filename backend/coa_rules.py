"""Aturan Bagan Akun (CoA) yang MENGIKAT posting (audit GL-13) + daftar akun kendali (audit GL-21).

Sebelumnya Bagan Akun hanya "daftar nama": kode bebas ("ABC", "2-1400 " dengan spasi), akun dinonaktifkan
tetapi jurnal otomatis tetap memakainya, sub-akun kas dimatikan padahal rekeningnya masih aktif, dan akun
kendali piutang/utang bisa diisi jurnal manual tanpa persetujuan siapa pun.
"""
import re

CODE_RE = re.compile(r"^[1-9]-\d{4}$")
# Digit pertama kode → tipe akun yang sah (7–9 dicadangkan untuk pendapatan/beban lain).
PREFIX_TYPES = {"1": ("asset",), "2": ("liability",), "3": ("equity",), "4": ("revenue",),
                "5": ("expense",), "6": ("expense",), "7": ("revenue", "expense"),
                "8": ("revenue", "expense"), "9": ("revenue", "expense")}
CASH_HEADERS = ("1-1100", "1-1200")
# Akun yang DIPAKAI jurnal otomatis: tidak boleh dinonaktifkan / diubah tipenya (posting akan gagal).
UNLOCKED_STANDARD = ("1-1700", "3-1100")
# Akun kendali: saldonya dijaga tie-out terhadap subledger (finance_audit / closing_engine). Jurnal manual
# langsung ke sini mengubah saldo tanpa subledger → butuh izin khusus + alasan (GL-21).
CONTROL_ACCOUNTS = {
    "1-1300": "Piutang Usaha", "1-1500": "Uang Muka Karyawan (Kas Bon)", "2-1100": "Utang Usaha",
    "2-1200": "Utang Retensi", "2-1400": "Uang Muka Penjualan (Kewajiban Kontrak)",
    "2-1450": "Titipan Pelanggan", "2-1600": "Utang Komisi",
}


def system_codes() -> set:
    import gl_engine
    return {c for c, _n, _t in gl_engine.STANDARD_COA} - set(UNLOCKED_STANDARD)


def check_new_account(code: str, type_: str, parent_code: str = None) -> str:
    """Validasi pembuatan akun baru; kembalikan kode bersih. ValueError (Indonesia) bila tidak sah."""
    raw = code or ""
    code = raw.strip()
    if code != raw or not CODE_RE.match(code):
        raise ValueError(f"Kode akun '{raw}' tidak valid — gunakan format angka-tanda hubung-empat angka "
                         "tanpa spasi, mis. 6-1900.")
    allowed = PREFIX_TYPES[code[0]]
    if type_ not in allowed:
        raise ValueError(f"Kode {code} berawalan {code[0]}, yang berarti akun bertipe {' / '.join(allowed)}; "
                         f"tipe '{type_}' tidak cocok. Pakai kode yang sesuai tipenya.")
    if parent_code and parent_code in CASH_HEADERS:
        raise ValueError("Sub-akun Kas/Bank dibuat otomatis lewat menu Kas & Bank (daftarkan rekening/kas), "
                         "bukan lewat Bagan Akun — supaya saldo kas di layar sama dengan neraca.")
    return code
