"""Periksa ISI berkas bukti transfer, bukan hanya header Content-Type (audit IN-16).

Portal dulu mempercayai `Content-Type` yang dikirim klien: HTML/skrip berkedok `image/png` diterima dan
tersimpan sebagai "bukti transfer". Di sini tanda tangan (magic bytes) isi berkas dicocokkan dengan jenis
yang diklaim; yang tidak cocok ditolak.
"""

_HEIC_BRANDS = (b"heic", b"heix", b"hevc", b"hevx", b"heim", b"heis", b"mif1", b"msf1")


def detect(data: bytes):
    """Jenis berkas dari isinya: image/png | image/jpeg | image/webp | image/heic | application/pdf | None."""
    head = bytes(data[:16])
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if head.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if head.startswith(b"%PDF-"):
        return "application/pdf"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image/webp"
    if head[4:8] == b"ftyp" and head[8:12] in _HEIC_BRANDS:
        return "image/heic"
    return None


def problem(ctype: str, data: bytes):
    """Pesan galat (Indonesia) bila isi berkas tidak sesuai jenis yang diklaim; None bila sah."""
    real = detect(data)
    claimed = (ctype or "").lower().replace("image/jpg", "image/jpeg").replace("image/heif", "image/heic")
    if real is None:
        return ("Isi berkas bukan foto (JPG/PNG/WEBP/HEIC) atau PDF yang sah — kemungkinan berkas rusak atau "
                "bukan bukti transfer. Unggah ulang fotonya.")
    if real != claimed:
        return f"Jenis berkas yang dikirim ({claimed or 'tidak dikenali'}) tidak sesuai isinya ({real}). Unggah ulang."
    return None
