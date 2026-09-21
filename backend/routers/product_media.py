"""Product media API. File reads use the same SKU scope as catalogue reads."""
from typing import Optional
from fastapi import APIRouter, Request, UploadFile, File, Form, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from db import db
from dependencies import require_permission, permission_matrix, audit
from entity_scope import entity_ctx, assert_active_entity_access
from services import catalog_access as access, product_media_service as media, storage_service as storage, gemini_image_service as gem

router = APIRouter(prefix='/api')


async def capabilities(actor):
    matrix = await permission_matrix()
    perms = matrix.get(actor.get('role'), {})
    allowed = lambda module, action: action in perms.get(module, []) or '*' in perms.get(module, [])
    return {'create': allowed('product', 'create'), 'update': allowed('product', 'update'),
            'delete': allowed('product', 'delete'), 'review': allowed('rnd', 'assess'),
            'rnd_create': allowed('rnd', 'create'), 'rnd_view': allowed('rnd', 'view')}


class MediaPatch(BaseModel):
    status: Optional[str] = None
    kind: Optional[str] = None
    cover: bool = False
    sort_order: Optional[int] = Field(None, ge=0, le=30)


class MockupInput(BaseModel):
    source_media_id: str
    prompt: str = Field(..., min_length=3, max_length=1500)


class DesignImport(BaseModel):
    design_id: str
    file_id: str
    version: Optional[int] = None


@router.get('/product-catalog/meta')
async def meta(request: Request):
    actor = await require_permission(request, 'product', 'view')
    cfg = await gem.resolve_config()
    from services import variant_axes
    try:
        eid = (await entity_ctx(request)).active_entity_id or ''
    except Exception:  # noqa: BLE001 — tanpa konteks entitas = konfigurasi global
        eid = ''
    return {'permissions': await capabilities(actor), 'max_media': media.MAX_MEDIA,
            'variant_axes': await variant_axes.axis_config(eid),
            'ai': {'enabled': cfg['enabled'], 'configured': bool(cfg['api_key']), 'model': cfg['model'], 'reason': cfg.get('disabled_reason', '')}}


@router.get('/products/{product_id}/media')
async def list_media(product_id: str, request: Request):
    actor = await require_permission(request, 'product', 'view')
    p = await access.product_for(actor, product_id)
    caps = await capabilities(actor)
    return {'items': access.public_product(p, actor, manage=caps['update'] or caps['review'])['media'], 'cover_media_id': p.get('cover_media_id', ''), 'revision': p.get('media_revision', 0)}


@router.post('/products/{product_id}/media')
async def upload(product_id: str, request: Request, file: UploadFile = File(...), kind: str = Form('photo')):
    actor = await require_permission(request, 'product', 'update')
    p = await access.product_for(actor, product_id)
    data = await file.read(media.MAX_BYTES + 1)
    result = await media.store(p, data, file.filename or 'foto.jpg', kind, actor)
    await audit(actor['name'], 'product_media_uploaded', 'product', product_id, {'media_id': result['id']})
    return result


@router.get('/products/{product_id}/media/{media_id}/content')
async def content(product_id: str, media_id: str, request: Request):
    actor = await require_permission(request, 'product', 'view')
    p = await access.product_for(actor, product_id)
    caps = await capabilities(actor)
    m = next((m for m in p.get('media', []) if m['id'] == media_id and not m.get('deleted')), None)
    if not m or (m.get('status') != 'approved' and not (caps['update'] or caps['review'])):
        raise HTTPException(404, 'Foto tidak ditemukan.')
    try:
        data, mime = await storage.get_object(m['path'])
    except FileNotFoundError as exc:
        raise HTTPException(404, 'Berkas foto tidak tersedia.') from exc
    return Response(data, media_type=mime, headers={'Cache-Control': 'private, no-store', 'X-Content-Type-Options': 'nosniff'})


@router.patch('/products/{product_id}/media/{media_id}')
async def update(product_id: str, media_id: str, payload: MediaPatch, request: Request):
    actor = await require_permission(request, 'product', 'view')
    caps = await capabilities(actor)
    patch = payload.model_dump(exclude_none=True, exclude_unset=True)
    if not patch:
        raise HTTPException(400, 'Tidak ada perubahan foto yang dikirim.')
    if ('status' in patch and not caps['review']) or (set(patch) - {'status'} and not caps['update']):
        raise HTTPException(403, 'Tidak berwenang mengubah foto.')
    p = await access.product_for(actor, product_id)
    result = await media.mutate(p, media_id, patch, actor, review=caps['review'])
    await audit(actor['name'], 'product_media_updated', 'product', product_id, {'media_id': media_id, **patch})
    return result


@router.get('/products/{product_id}/catalog-relations')
async def relations(product_id: str, request: Request):
    actor = await require_permission(request, 'product', 'view')
    await require_permission(request, 'rnd', 'view')
    await access.product_for(actor, product_id)
    from entity_scope import resolve_list_scope
    from services import line_scope
    ctx = await entity_ctx(request)
    query = resolve_list_scope('md_specs', {'$or': [{'product_id': product_id}, {'target_product_id': product_id}]}, ctx)
    specs = await db.md_specs.find(line_scope.narrow(query, actor), {'_id': 0, 'id': 1, 'number': 1, 'title': 1, 'status': 1, 'lifecycle': 1}).to_list(500)
    sq = resolve_list_scope('md_samples', {'spec_id': {'$in': [s['id'] for s in specs]}}, ctx)
    return {'specs': specs, 'sample_count': await db.md_samples.count_documents(line_scope.narrow(sq, actor))}


@router.delete('/products/{product_id}/media/{media_id}')
async def remove(product_id: str, media_id: str, request: Request):
    actor = await require_permission(request, 'product', 'update')
    p = await access.product_for(actor, product_id)
    result = await media.mutate(p, media_id, {}, actor, delete=True)
    await audit(actor['name'], 'product_media_deleted', 'product', product_id, {'media_id': media_id})
    return result


@router.post('/products/{product_id}/media/from-design')
async def from_design(product_id: str, payload: DesignImport, request: Request):
    actor = await require_permission(request, 'product', 'update')
    await require_permission(request, 'rnd', 'view')
    p = await access.product_for(actor, product_id)
    from services import line_scope
    design = await db.design_gallery.find_one({'id': payload.design_id}, {'_id': 0})
    if not design:
        raise HTTPException(404, 'Desain tidak ditemukan.')
    assert_active_entity_access(design, 'design_gallery', await entity_ctx(request))
    line_scope.assert_can_touch(actor, design)
    if design.get('status') != 'approved':
        raise HTTPException(409, 'Desain harus disetujui sebelum dihubungkan ke galeri produk.')
    version = int(design.get('version') or 1)
    if payload.version is not None and payload.version != version:
        raise HTTPException(409, 'Versi desain berubah. Muat ulang dan pilih kembali berkas sumber.')
    m = next((m for m in design.get('files', []) if m['id'] == payload.file_id), None)
    if not m or (m.get('ai') or {}).get('demo'):
        raise HTTPException(400, 'Pilih berkas desain nyata, bukan gambar demo.')
    source = {'type': 'design', 'design_id': design['id'], 'file_id': m['id'], 'version': version, 'entity_id': design.get('entity_id')}
    if any(m0.get('source') == source and not m0.get('deleted') for m0 in p.get('media', [])):
        raise HTTPException(409, 'Berkas/versi ini sudah ada di galeri varian.')
    data, _ = await storage.get_object(m['path'])
    result = await media.store(p, data, m['filename'], 'mockup' if m.get('kind') == 'ai_illustration' else 'artwork', actor, source=source, ai=m.get('ai'))
    await audit(actor['name'], 'product_media_from_design', 'product', product_id, {'media_id': result['id'], 'source': source})
    return result


@router.post('/products/{product_id}/media/generate-mockup')
async def generate_mockup(product_id: str, payload: MockupInput, request: Request):
    actor = await require_permission(request, 'product', 'update')
    p = await access.product_for(actor, product_id)
    cfg = await gem.resolve_config()
    if not cfg['enabled']:
        raise HTTPException(409, cfg.get('disabled_reason') or 'Gemini belum aktif.')
    src = next((m for m in p.get('media', []) if m['id'] == payload.source_media_id and not m.get('deleted') and not m.get('ai')), None)
    if not src:
        raise HTTPException(400, 'Pilih foto asli/artwork varian sebagai sumber mockup.')
    from services import atomic_claim
    await atomic_claim.claim('products', product_id, 'product_mockup', actor=actor['name'])
    try:
        # Read latest after claiming, preventing concurrent generation/quota races.
        p = await access.product_for(actor, product_id)
        from datetime import datetime
        from zoneinfo import ZoneInfo
        today = datetime.now(ZoneInfo('Asia/Jakarta')).date().isoformat()
        count = sum(1 for m in p.get('media', []) if (m.get('ai') or {}).get('day') == today)
        if count >= cfg['daily_limit'] or len([m for m in p.get('media', []) if not m.get('deleted')]) >= media.MAX_MEDIA:
            raise HTTPException(409, 'Batas gambar per hari atau kapasitas galeri tercapai.')
        data, mime = await storage.get_object(src['path'])
        result = await gem.illustrate(data, mime, 'mockup', payload.prompt,
            context=f"Produk: {p.get('name')}. SKU: {p['sku']}. Atribut: {p.get('variant_attrs')}. Jangan mengubah warna, motif, dan karakter bahan referensi.")
        latest = await access.product_for(actor, product_id)
        saved = await media.store(latest, result['data'], 'mockup-model.jpg', 'mockup', actor,
            source={'type': 'variant', 'media_id': src['id']}, ai={'model': result['model'], 'prompt': payload.prompt, 'demo': False, 'day': today})
        await audit(actor['name'], 'product_mockup_generated', 'product', product_id, {'media_id': saved['id'], 'model': result['model']})
        return saved
    except ValueError as exc:
        raise HTTPException(502, str(exc)) from exc
    finally:
        await atomic_claim.release('products', product_id)