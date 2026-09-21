"""Validate source relations before saving any R&D specification."""
from fastapi import HTTPException
from db import db
from entity_scope import assert_active_entity_access
from services import catalog_access, catalog_rules, line_scope, rnd_gate


async def validate_spec_catalog(data, actor, ctx):
    line_scope.assert_can_touch(actor, data)
    for coll, field in (('customers', 'customer_id'), ('sales_orders', 'so_id')):
        if data.get(field):
            linked = await db[coll].find_one({'id': data[field]}, {'_id': 0})
            if not linked:
                raise HTTPException(404, 'Dokumen referensi R&D tidak ditemukan.')
            assert_active_entity_access(linked, coll, ctx)
    if data.get('design_id'):
        design = await db.design_gallery.find_one({'id': data['design_id']}, {'_id': 0})
        if not design:
            raise HTTPException(404, 'Desain tidak ditemukan.')
        assert_active_entity_access(design, 'design_gallery', ctx)
        line_scope.assert_can_touch(actor, design)
    if data.get('target_product_id') and not data.get('template_id'):
        raise HTTPException(400, 'Pilih induk sebelum SKU target.')
    if not data.get('template_id'):
        if data.get('variant_attrs') or data.get('variant_options'):
            raise HTTPException(400, 'Pilih induk yang mendefinisikan kombinasi atribut ini.')
        return
    parent = await catalog_access.template_for(actor, data['template_id'], manage=True)
    if parent.get('status') != 'active':
        raise HTTPException(409, 'Induk produk sudah diarsipkan.')
    probe = {**(data.get('target') or {}), 'variant_attrs': data.get('variant_attrs') or {}, 'variant_options': data.get('variant_options') or {}}
    try:
        catalog_rules.combination(parent, probe)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    if data.get('color_target') and probe.get('color_code'):
        color = data['color_target']
        source = await db.color_library.find_one({'id': color['color_id']} if color.get('color_id') else {'code': color.get('code', '')}, {'_id': 0})
        if source and source.get('code') != probe['color_code']:
            raise HTTPException(400, 'Warna target R&D tidak sama dengan kombinasi varian.')
    for field in ('stage', 'fabric_type'):
        if parent.get(field) and probe.get(field) != parent[field]:
            raise HTTPException(400, f'{field} target harus sesuai induk.')
    if data.get('base_unit') and parent.get('base_unit') != data['base_unit']:
        raise HTTPException(400, 'Satuan spesifikasi harus sama dengan induk.')
    if data.get('target_product_id'):
        product = await catalog_access.product_for(actor, data['target_product_id'])
        if product.get('template_id') != parent['id']:
            raise HTTPException(400, 'SKU target bukan anggota induk ini.')
        if product.get('spec_id') or rnd_gate.is_orderable(product):
            raise HTTPException(409, 'Pilih SKU konsep yang belum terhubung spesifikasi.')
        old = dict(product)
        catalog_rules.combination(parent, old)
        if old['variant_key'] != probe['variant_key']:
            raise HTTPException(400, 'Kombinasi spesifikasi tidak sesuai SKU target.')