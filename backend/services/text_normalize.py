"""K-1/K-2 (feedback klien 2026-09) — normalisasi penulisan (EYD) & nomor telepon/WhatsApp.

Aturan berlaku untuk dokumen BARU / suntingan baru; data lama tidak diubah diam-diam.
"""
import re
from typing import Annotated

from pydantic import BeforeValidator

# Bentuk badan hukum / singkatan yang selalu KAPITAL.
_LEGAL_FORMS = {"PT", "CV", "UD", "PD", "TB", "TBK", "FA", "NV", "BUMN", "BUMD", "UMKM", "PS", "PP"}
# Kata sambung yang ditulis kecil di tengah nama usaha.
_LOWER_WORDS = {"dan", "atau", "of", "and", "di", "ke", "dari", "the", "de", "van", "der", "bin", "binti", "al"}

_PHONE_RE = re.compile(r"^62[2-9]\d{7,11}$")
PHONE_HINT = "Nomor telepon/WhatsApp tidak valid. Tulis 08xxxxxxxxxx atau +62xxxxxxxxxxx (10–13 angka, tanpa huruf)."


def _cap(word: str) -> str:
    # Pertahankan tanda hubung/apostrof: "nur'aini-putri" → "Nur'aini-Putri"
    return re.sub(r"(^|[-/])([a-z])", lambda m: m.group(1) + m.group(2).upper(), word.lower())


def nama_orang(raw: str) -> str:
    """'BUDI santoso, s.e.' → 'Budi Santoso, S.E.' — gelar berpetik titik dikapitalkan penuh."""
    s = re.sub(r"\s+", " ", (raw or "").strip())
    if not s:
        return ""
    out = []
    for i, w in enumerate(s.split(" ")):
        if re.fullmatch(r"(?:[A-Za-z]\.)+,?", w):      # gelar berhuruf tunggal: S.E., M.M., H.
            out.append(w.upper())
        elif i > 0 and w.lower() in _LOWER_WORDS:
            out.append(w.lower())
        else:
            out.append(_cap(w))
    return " ".join(out)


def nama_usaha(raw: str) -> str:
    """'pt kain suka cita tbk' → 'PT Kain Suka Cita Tbk' ; 'toko ABC & rekan' → 'Toko ABC & Rekan'."""
    s = re.sub(r"\s+", " ", (raw or "").strip().strip(".,"))
    if not s:
        return ""
    out = []
    for i, w in enumerate(s.split(" ")):
        core = re.sub(r"[^A-Za-z]", "", w)
        up = core.upper()
        if up in _LEGAL_FORMS:
            out.append("Tbk" if up == "TBK" else w.upper())
        elif core and core.isupper() and len(core) <= 4 and i > 0:
            out.append(w)                            # singkatan/akronim yang memang ditulis kapital (KSC, ABC)
        elif i > 0 and w.lower() in _LOWER_WORDS:
            out.append(w.lower())
        else:
            out.append(_cap(w))
    return " ".join(out)


def normalize_name(raw: str, kind: str = "usaha") -> str:
    return nama_orang(raw) if kind == "orang" else nama_usaha(raw)


def phone_id(raw: str) -> str:
    """Normalisasi nomor Indonesia ke bentuk WhatsApp `62xxxxxxxxxx`. Kosong → ''. Tidak valid → ValueError."""
    s = (raw or "").strip()
    if not s:
        return ""
    if re.search(r"[A-Za-z]", s):
        raise ValueError(PHONE_HINT)
    digits = re.sub(r"\D", "", s)
    if digits.startswith("0"):
        digits = "62" + digits[1:]
    elif digits.startswith("620"):
        digits = "62" + digits[3:]
    if not _PHONE_RE.match(digits):
        raise ValueError(PHONE_HINT)
    return digits


def _phone_validator(v):
    if v is None:
        return ""
    return phone_id(str(v))


# Tipe field Pydantic: dipakai di schemas untuk semua kolom telepon/WhatsApp.
PhoneStr = Annotated[str, BeforeValidator(_phone_validator)]
