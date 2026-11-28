"""Masking PII untuk keluaran alat: NIK, rekening/VA, email; nomor HP hanya pada riset web."""
import re

_EMAIL = r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
_PHONE = r"(?<!\d)(?:\+?62|0)8\d{8,11}(?!\d)"
_LONG = r"(?<!\d)\d{10,18}(?!\d)"
_RX = re.compile(f"(?P<email>{_EMAIL})|(?P<phone>{_PHONE})|(?P<long>{_LONG})")
_KEY_RX = re.compile(r"nik|rekening|no_rek|account|^va$|va_number|virtual", re.I)


def _mask_digits(d: str) -> str:
    return "*" * (len(d) - 4) + d[-4:]


def _mask_text(s: str, mask_phone: bool) -> str:
    def rep(m):
        if m.group("email"):
            e = m.group("email")
            name, _, dom = e.partition("@")
            return f"{name[:1]}***@{dom}"
        if m.group("phone"):
            return _mask_digits(m.group("phone")) if mask_phone else m.group("phone")
        return _mask_digits(m.group("long"))
    return _RX.sub(rep, s)


def mask(obj, *, keep_names: bool = True, mask_phone: bool = False):
    """Salin `obj` dengan PII dimasker. `keep_names` dicadangkan (nama selalu dipertahankan)."""
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if isinstance(k, str) and _KEY_RX.search(k) and isinstance(v, (str, int)) and not isinstance(v, bool):
                d = re.sub(r"\D", "", str(v))
                out[k] = _mask_digits(d) if len(d) > 4 else v
            else:
                out[k] = mask(v, keep_names=keep_names, mask_phone=mask_phone)
        return out
    if isinstance(obj, (list, tuple)):
        return [mask(v, keep_names=keep_names, mask_phone=mask_phone) for v in obj]
    if isinstance(obj, str):
        return _mask_text(obj, mask_phone)
    return obj
