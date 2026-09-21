"""FB-01 — Ilustrasi AI Galeri Desain via Google Gemini "Nano Banana Pro" (SDK google-genai LANGSUNG).

Dua mode: `mockup` (artwork diterapkan ke produk/kain) dan `modify` (modifikasi artwork
sesuai arahan). Hasil = ILUSTRASI ARAHAN (bukan artwork/versi baru) — desainer me-rework.

GRACEFUL/DEMO: bila key Gemini kosong (settings & env) → gambar demo dirender lokal (Pillow)
dengan cap "MODE DEMO", supaya alur bisa dicoba sebelum API key tersedia.
"""
import asyncio
import io
import logging
import os
import textwrap
from typing import Any, Dict, Optional, Tuple

from services import integrations_service as integ

logger = logging.getLogger("gemini_image_service")

MODES = {
    "mockup": ("Buat MOCKUP produk tekstil yang realistis memakai motif/artwork pada gambar ini "
               "sebagai bahan kain (drape kain, tekstur tenun/printing terlihat, pencahayaan studio). "
               "Jaga warna & pola tetap setia pada artwork."),
    "modify": ("MODIFIKASI artwork motif kain pada gambar ini sesuai arahan berikut, "
               "pertahankan karakter utama motif, hasil rapi dan siap dijadikan referensi desainer."),
}


MAX_SIDE = 2048          # G-7: susutkan gambar sumber sebelum dikirim (artwork bisa 10 MB)
CALL_TIMEOUT_S = 60      # G-7: batas waktu panggilan Gemini
JPEG_QUALITY = 90


async def resolve_config() -> Dict[str, Any]:
    cfg = (await integ.get_integrations()).get("gemini", {})
    key = (cfg.get("api_key") or os.environ.get("GEMINI_API_KEY") or "").strip()
    return {"api_key": key, "model": cfg.get("model") or integ.GEMINI_DEFAULT_MODEL,
            "enabled": bool(cfg.get("enabled", True)) and bool(key), "demo": False,
            "configured": bool(key),
            "disabled_reason": "Gemini belum dikonfigurasi. Unggahan foto tetap tersedia." if not key else ("Ilustrasi AI dinonaktifkan admin." if not cfg.get('enabled', True) else ""),
            "verified": bool(cfg.get("verified_at")),
            "daily_limit": int(cfg.get("daily_limit") or integ.GEMINI_DEFAULT_DAILY_LIMIT),
            "cost_per_image_usd": float(cfg.get("cost_per_image_usd") or integ.GEMINI_DEFAULT_COST_USD)}


def _test_key_sync(api_key: str) -> Dict[str, Any]:
    """G-3 — uji koneksi ringan: daftar model (tidak menghasilkan gambar, tanpa biaya berarti)."""
    from google import genai
    client = genai.Client(api_key=api_key)
    names = []
    for m in client.models.list():
        names.append(getattr(m, "name", "") or "")
        if len(names) >= 50:
            break
    return {"ok": True, "models_seen": len(names)}


async def test_connection(api_key: str) -> Dict[str, Any]:
    try:
        return await asyncio.wait_for(asyncio.to_thread(_test_key_sync, api_key), timeout=30)
    except asyncio.TimeoutError:
        raise ValueError("Uji koneksi Gemini melewati batas waktu 30 detik.")
    except Exception as e:  # noqa: BLE001
        raise ValueError(f"Gemini menolak key / gagal terhubung: {e}")


def _shrink(image: bytes, mime: str) -> Tuple[bytes, str]:
    """G-7 — sisi terpanjang ≤ MAX_SIDE; simpan JPEG bila tidak transparan."""
    from PIL import Image
    try:
        im = Image.open(io.BytesIO(image))
    except Exception:  # noqa: BLE001
        return image, mime
    if max(im.size) <= MAX_SIDE and len(image) < 4 * 1024 * 1024:
        return image, mime
    im.thumbnail((MAX_SIDE, MAX_SIDE))
    out = io.BytesIO()
    if im.mode in ("RGBA", "LA", "P"):
        im.save(out, format="PNG", optimize=True)
        return out.getvalue(), "image/png"
    im.convert("RGB").save(out, format="JPEG", quality=JPEG_QUALITY, optimize=True)
    return out.getvalue(), "image/jpeg"


def _compact_output(data: bytes, mime: str) -> Tuple[bytes, str]:
    """G-7 — hasil AI disimpan JPEG kecuali ada transparansi."""
    from PIL import Image
    try:
        im = Image.open(io.BytesIO(data))
    except Exception:  # noqa: BLE001
        return data, mime
    if im.mode in ("RGBA", "LA", "P") or "png" not in (mime or "").lower():
        return data, mime
    out = io.BytesIO()
    im.convert("RGB").save(out, format="JPEG", quality=JPEG_QUALITY, optimize=True)
    return out.getvalue(), "image/jpeg"


def _call_gemini_sync(api_key: str, model: str, prompt: str,
                      image: Optional[bytes], mime: str) -> Tuple[bytes, str]:
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=api_key)
    contents = []
    if image:
        contents.append(types.Part.from_bytes(data=image, mime_type=mime))
    contents.append(prompt)
    resp = client.models.generate_content(
        model=model, contents=contents,
        config=types.GenerateContentConfig(response_modalities=["IMAGE", "TEXT"]))
    for cand in (resp.candidates or []):
        for part in (cand.content.parts or []):
            data = getattr(getattr(part, "inline_data", None), "data", None)
            if data:
                return bytes(data), part.inline_data.mime_type or "image/png"
    raise RuntimeError("Gemini tidak mengembalikan gambar (kemungkinan diblokir filter keamanan).")


def _font(size: int):
    from PIL import ImageFont
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
              "/usr/share/fonts/truetype/freefont/FreeSans.ttf"):
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _demo_render(image: Optional[bytes], mode: str, prompt: str) -> Tuple[bytes, str]:
    from PIL import Image, ImageDraw, ImageOps
    W, H = 1024, 768
    canvas = Image.new("RGB", (W, H), (244, 241, 234))
    draw = ImageDraw.Draw(canvas)
    src = None
    if image:
        try:
            src = Image.open(io.BytesIO(image)).convert("RGB")
        except Exception:  # noqa: BLE001
            src = None
    if src is None:
        src = Image.new("RGB", (400, 300), (200, 190, 170))
    if mode == "mockup":
        # "kain digantung": 3 panel motif dengan gelap-terang berbeda + bayangan
        tile = ImageOps.fit(src, (280, 520))
        for i, shade in enumerate((0.85, 1.0, 0.9)):
            panel = Image.eval(tile, lambda p, s=shade: int(min(255, p * s)))
            x = 60 + i * 300
            draw.rectangle([x + 10, 120 + 10, x + 290, 640 + 10], fill=(210, 205, 195))
            canvas.paste(panel, (x, 120))
    else:
        left = ImageOps.fit(src, (440, 440))
        right = ImageOps.posterize(ImageOps.autocontrast(left), 3)
        right = ImageOps.colorize(ImageOps.grayscale(right), (40, 60, 120), (245, 220, 170))
        canvas.paste(left, (50, 150))
        canvas.paste(right, (534, 150))
        draw.text((50, 605), "ASLI", fill=(90, 90, 90), font=_font(18))
        draw.text((534, 605), "USULAN AI (DEMO)", fill=(90, 90, 90), font=_font(18))
    # G-4 — banner demo lebih besar & terbaca pada pratinjau kecil.
    draw.rectangle([0, 0, W, 96], fill=(0, 88, 204))
    draw.text((24, 14), "ILUSTRASI AI - MODE DEMO", fill="white", font=_font(40))
    draw.text((24, 62), f"Nano Banana Pro belum terhubung · Mode: {mode}", fill=(200, 220, 255), font=_font(22))
    draw.rectangle([0, H - 70, W, H], fill=(255, 255, 255))
    draw.text((24, H - 60), "\n".join(textwrap.wrap(f"Arahan: {prompt}", 90)[:2]), fill=(60, 60, 60), font=_font(18))
    out = io.BytesIO()
    canvas.save(out, format="PNG")
    return out.getvalue(), "image/png"


async def illustrate(image: Optional[bytes], mime: str, mode: str,
                     prompt: str, context: str = "") -> Dict[str, Any]:
    """Hasilkan ilustrasi arahan. Return {data, content_type, model, demo}. Raise ValueError bila nonaktif."""
    if mode not in MODES:
        raise ValueError(f"Mode harus salah satu: {', '.join(MODES)}.")
    cfg = await resolve_config()
    if not cfg["enabled"]:
        raise ValueError(cfg['disabled_reason'] or "Ilustrasi AI dinonaktifkan admin (Pengaturan → Integrasi AI).")
    full_prompt = f"{MODES[mode]}\n\nArahan: {prompt.strip()}\n{context}".strip()
    # Tidak pernah menghasilkan gambar demo bila kredensial kosong.
    if image:
        image, mime = await asyncio.to_thread(_shrink, image, mime)
    try:
        data, ct = await asyncio.wait_for(asyncio.to_thread(
            _call_gemini_sync, cfg["api_key"], cfg["model"], full_prompt, image, mime),
            timeout=CALL_TIMEOUT_S)
    except asyncio.TimeoutError:
        raise ValueError(f"Gemini tidak merespons dalam {CALL_TIMEOUT_S} detik — coba lagi.")
    except Exception as e:  # noqa: BLE001
        logger.warning("[gemini_image] provider gagal: %s", type(e).__name__)
        raise ValueError("Gemini gagal membuat ilustrasi. Periksa konfigurasi atau coba kembali; tidak ada gambar pengganti yang dibuat.")
    data, ct = await asyncio.to_thread(_compact_output, data, ct)
    return {"data": data, "content_type": ct, "model": cfg["model"], "demo": False}
