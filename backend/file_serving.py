"""Tajuk penyajian berkas unggahan yang AMAN (audit AZ-07).

Dulu semua berkas disajikan `Content-Disposition: inline` dengan tipe aslinya, tanpa
`X-Content-Type-Options`. Akibatnya `.html`/`.svg` yang diunggah pemakai dijalankan peramban
pada asal (origin) aplikasi — skrip tersimpan (stored XSS), diperparah token di `?auth=`.

Aturan sekarang:
  * hanya GAMBAR raster dan PDF yang boleh `inline` (tampilan `<img>`/`<iframe>` di UI tetap
    jalan); tipe lain — termasuk `text/html`, `image/svg+xml`, `application/xml` — dipaksa
    `attachment` (diunduh, tidak dirender);
  * `X-Content-Type-Options: nosniff` SELALU dikirim, supaya peramban tidak menebak tipe lain;
  * nama berkas dibersihkan (tanda kutip / kendali) dan nama non-ASCII dikirim lewat `filename*`
    (RFC 5987), bukan dilempar mentah ke tajuk (dulu bisa membuat tajuk tidak valid).
"""
from urllib.parse import quote

INLINE_TYPES = frozenset({
    "image/png", "image/jpeg", "image/jpg", "image/gif", "image/webp", "image/bmp",
    "application/pdf",
})


def is_inline_safe(content_type: str) -> bool:
    return (content_type or "").split(";")[0].strip().lower() in INLINE_TYPES


def _clean_name(name: str, fallback: str) -> str:
    name = "".join(ch for ch in str(name or "") if ch >= " " and ch not in '"\\/\x7f').strip()
    return name or fallback


def headers(filename: str, content_type: str, fallback: str = "berkas") -> dict:
    """Tajuk `Content-Disposition` + `X-Content-Type-Options` untuk penyajian berkas unggahan."""
    name = _clean_name(filename, fallback)
    disp = "inline" if is_inline_safe(content_type) else "attachment"
    try:
        name.encode("ascii")
        spec = f'filename="{name}"'
    except UnicodeEncodeError:
        ascii_name = name.encode("ascii", "replace").decode().replace("?", "_")
        spec = f"filename=\"{ascii_name}\"; filename*=UTF-8''{quote(name)}"
    return {"Content-Disposition": f"{disp}; {spec}", "X-Content-Type-Options": "nosniff"}
