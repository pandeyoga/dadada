"""Cross-cutting utilities: ids, time (UTC ISO-8601), serialization, pagination."""
import uuid
from datetime import datetime, timezone, timedelta


def new_id() -> str:
    return str(uuid.uuid4())


def now() -> datetime:
    return datetime.now(timezone.utc)


def now_iso() -> str:
    return now().isoformat()


def iso(dt: datetime) -> str:
    return dt.isoformat()


def due_in(hours: int = 0, days: int = 0, minutes: int = 0) -> str:
    return (now() + timedelta(hours=hours, days=days, minutes=minutes)).isoformat()


def serialize_doc(doc):
    """Recursively strip Mongo _id and make everything JSON-safe."""
    if doc is None:
        return None
    if isinstance(doc, list):
        return [serialize_doc(d) for d in doc]
    if isinstance(doc, dict):
        out = {}
        for k, v in doc.items():
            if k == "_id":
                continue
            out[k] = serialize_doc(v)
        return out
    if isinstance(doc, datetime):
        return doc.isoformat()
    return doc


def parse_pagination(skip: int = 0, limit: int = 50):
    limit = max(1, min(int(limit or 50), 200))
    skip = max(0, int(skip or 0))
    return skip, limit


def today_iso_date() -> str:
    return now().date().isoformat()


WIB = timezone(timedelta(hours=7))


def period_of(value) -> str:
    """Periode akuntansi 'YYYY-MM' dari tanggal/ISO datetime — SATU definisi (CFG-01).

    Tanggal polos ('2026-08-31') dibaca apa adanya; stempel waktu dikonversi ke WIB dulu
    ('2026-08-31T18:00:00+00:00' → 2026-09). Nilai kosong/tidak terbaca → None, bukan potongan
    string yang kebetulan tujuh huruf."""
    s = str(value or "").strip()
    if not s:
        return None
    if len(s) <= 10:
        return s[:7] if len(s) >= 7 and s[4] == "-" else None
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return s[:7] if len(s) >= 7 and s[4] == "-" else None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(WIB).strftime("%Y-%m")


def to_wib_iso(value):
    """Bentuk KANONIK tanggal jurnal (GL-15): tanggal polos tetap; stempel waktu diubah ke WIB (+07:00).

    Dulu jurnal bertanggal UTC ('2026-10-31T20:00:00+00:00' = 1 Nov WIB). Pemeriksaan periode tertutup memakai
    `period_of` (WIB) sedangkan laporan memotong string (UTC), jadi jurnal itu lolos periode Oktober yang sudah
    ditutup lalu masuk Laba Rugi Oktober. Menyimpan dalam WIB membuat potongan string, `period_of`, dan filter
    rentang tanggal memandang jurnal yang SAMA berada di bulan yang sama."""
    s = str(value or "").strip()
    if len(s) <= 10:
        return s
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return s
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(WIB).isoformat()


def today_wib() -> str:
    """Hari ini (YYYY-MM-DD) menurut zona waktu bisnis (WIB) — pasangan `to_wib_iso` untuk 'per hari ini'."""
    return datetime.now(WIB).strftime("%Y-%m-%d")


_PERIOD_RE = None


def valid_period(m) -> bool:
    """True bila `m` berbentuk 'YYYY-MM' dengan bulan 01..12 (tahan terhadap data jurnal lama yang rusak)."""
    global _PERIOD_RE
    if _PERIOD_RE is None:
        import re
        _PERIOD_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
    return bool(_PERIOD_RE.match(str(m or "")))


def parse_journal_date(value):
    """Validasi tanggal jurnal MANUAL (audit GL-06). Kembalikan `value` bila sah; ValueError bila tidak.

    Sah: 'YYYY-MM-DD' atau ISO datetime yang terbaca, bukan hari di masa depan (zona WIB).
    Dulu tanggal bebas: 'bukan-tanggal' diterima lalu memutus layar Tutup Buku (HTTP 500), tanggal
    rusak menembus kunci periode, dan tanggal masa depan hilang dari laporan 'per tanggal'.
    """
    s = str(value or "").strip()
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00")) if len(s) > 10 else datetime.strptime(s, "%Y-%m-%d")
    except ValueError:
        raise ValueError(f"Tanggal jurnal tidak valid: '{s}'. Gunakan format TTTT-BB-HH, mis. 2026-11-05.")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc) if len(s) > 10 else dt.replace(tzinfo=WIB)
    if dt.astimezone(WIB).date() > datetime.now(WIB).date():
        raise ValueError(f"Tanggal jurnal {s[:10]} berada di masa depan. Jurnal hanya boleh bertanggal hari ini atau sebelumnya.")
    return s


def normalize_phone_e164(phone: str) -> str:
    """Best-effort E.164 normalization for Indonesian numbers (idempotent).

    '08123' -> '+628123', '628123' -> '+628123', '+62 812-3' -> '+628123'.
    Non-ID inputs starting with '+' are kept (digits only after '+').
    """
    if not phone:
        return phone
    s = "".join(ch for ch in str(phone) if ch.isdigit() or ch == "+")
    if s.startswith("+"):
        return "+" + "".join(ch for ch in s[1:] if ch.isdigit())
    digits = "".join(ch for ch in s if ch.isdigit())
    if digits.startswith("0"):
        digits = "62" + digits[1:]
    elif not digits.startswith("62"):
        digits = "62" + digits
    return "+" + digits


def normalize_nik(nik: str) -> str:
    """Strip non-digits from an Indonesian NIK (16 digits). Idempotent."""
    if not nik:
        return nik
    return "".join(ch for ch in str(nik) if ch.isdigit())
