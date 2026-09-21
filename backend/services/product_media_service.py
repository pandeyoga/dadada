"""Media per SKU, lokal, ber-versi CAS. Foto nyata/mockup ditinjau sebelum sales melihat."""
import asyncio
import io
from fastapi import HTTPException
from PIL import Image, ImageOps, UnidentifiedImageError
from db import db
from core_utils import new_id, now_iso
from services import storage_service as storage

MAX_MEDIA = 30
MAX_BYTES = 10 * 1024 * 1024
KINDS = {'photo', 'detail', 'artwork', 'mockup'}


def validate_image(data):
    if not data or len(data) > MAX_BYTES:
        raise HTTPException(400, 'Foto wajib berisi data dan maksimal 10 MB.')
    try:
        with Image.open(io.BytesIO(data)) as im:
            if im.format not in ('JPEG', 'PNG', 'WEBP') or im.width * im.height > 25_000_000:
                raise ValueError()
            im.verify()
        with Image.open(io.BytesIO(data)) as im:
            im = ImageOps.exif_transpose(im).convert('RGB')
            im.thumbnail((2048, 2048))
            out = io.BytesIO(); im.save(out, format='JPEG', quality=90)
            return out.getvalue(), 'image/jpeg'
    except (UnidentifiedImageError, ValueError, OSError, Image.DecompressionBombError, SyntaxError) as exc:
        raise HTTPException(400, 'Berkas harus foto JPG, PNG atau WEBP yang valid, maksimal 25 megapiksel.') from exc


def present(media):
    return {k: v for k, v in media.items() if k != 'path'}


async def store(product, data, filename, kind, actor, *, source=None, ai=None):
    if kind not in KINDS:
        raise HTTPException(400, 'Jenis foto tidak dikenal.')
    rows = [dict(m) for m in product.get('media', []) if not m.get('deleted')]
    if len(rows) >= MAX_MEDIA:
        raise HTTPException(400, f'Maksimal {MAX_MEDIA} foto per varian.')
    data, mime = await asyncio.to_thread(validate_image, data)
    path = storage.build_path('product_media', 'jpg')
    await storage.put_object(path, data, mime)
    mid = new_id('media')
    media = {'id': mid, 'product_id': product['id'], 'filename': filename, 'kind': kind,
             'path': path, 'url': f"/api/products/{product['id']}/media/{mid}/content", 'content_type': mime,
             'size': len(data), 'status': 'draft', 'sort_order': len(rows),
             'created_at': now_iso(), 'created_by': actor['id'], 'source': source or {'type': 'upload'}, 'ai': ai}
    rows.append(media)
    try:
        await save_media(product, rows)
    except Exception:
        # No published reference yet; failed CAS must not leave an orphan file.
        try:
            storage._abs_path(path).unlink(missing_ok=True)
        except OSError:
            pass
        raise
    return present(media)


async def save_media(product, media, cover_id=None):
    revision = int(product.get('media_revision') or 0)
    filt = {'id': product['id'], 'media_revision': revision} if 'media_revision' in product else {'id': product['id'], 'media_revision': {'$exists': False}}
    approved = [m for m in media if not m.get('deleted') and m.get('status') == 'approved']
    approved.sort(key=lambda m: (m.get('sort_order', 0), m['id']))
    chosen = cover_id if cover_id is not None else product.get('cover_media_id')
    cover = next((m for m in approved if m['id'] == chosen), approved[0] if approved else None)
    # Retain original legacy image separately; draft/deleted managed images never leak via image.
    legacy = product.get('legacy_image', product.get('image', '') if not product.get('media') else '')
    fields = {'media': media, 'media_revision': revision + 1, 'cover_media_id': cover['id'] if cover else '',
              'legacy_image': legacy, 'image': cover['url'] if cover else legacy, 'updated_at': now_iso()}
    res = await db.products.update_one(filt, {'$set': fields})
    if not res.matched_count:
        raise HTTPException(409, 'Galeri berubah di sesi lain. Muat ulang sebelum mencoba lagi.')
    return fields


async def mutate(product, media_id, patch, actor, *, review=False, delete=False):
    media = [dict(m) for m in product.get('media', [])]
    selected = next((m for m in media if m['id'] == media_id and not m.get('deleted')), None)
    if not selected:
        raise HTTPException(404, 'Foto tidak ditemukan.')
    if delete:
        selected.update(deleted=True, deleted_by=actor['id'], deleted_at=now_iso())
    if 'status' in patch:
        if not review:
            raise HTTPException(403, 'Tidak berwenang menyetujui foto.')
        if patch['status'] not in ('draft', 'approved', 'rejected'):
            raise HTTPException(400, 'Status foto tidak dikenal.')
        if (selected.get('ai') or {}).get('demo') and patch['status'] == 'approved':
            raise HTTPException(400, 'Gambar demo tidak dapat dipublikasikan.')
        selected.update(status=patch['status'], reviewed_by=actor['id'], reviewed_at=now_iso())
    if patch.get('kind'):
        if patch['kind'] not in KINDS or (selected.get('ai') and patch['kind'] != 'mockup'):
            raise HTTPException(400, 'Jenis media tidak sah; ilustrasi AI harus tetap bertanda mockup.')
        selected['kind'] = patch['kind']
    if patch.get('cover') and selected.get('status') != 'approved':
        raise HTTPException(400, 'Foto utama harus disetujui terlebih dahulu.')
    if patch.get('sort_order') is not None:
        current = sorted([m for m in media if not m.get('deleted')], key=lambda m: (m.get('sort_order', 0), m['id']))
        current.remove(selected)
        current.insert(max(0, min(len(current), int(patch['sort_order']))), selected)
        for i, m in enumerate(current):
            m['sort_order'] = i
    await save_media(product, media, media_id if patch.get('cover') else None)
    return present(selected)