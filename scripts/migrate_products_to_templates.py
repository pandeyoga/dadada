"""Migrasi katalog aditif: default dry-run. --apply menyimpan backup dahulu.

python scripts/migrate_products_to_templates.py
python scripts/migrate_products_to_templates.py --apply
Tidak mengubah id, SKU, nilai stok, dokumen transaksi, harga atau lifecycle.
"""
import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from db import db, client
from services import product_variant_service as pvs


async def main(apply):
    before = await db.products.find({}, {'_id': 0}).to_list(100000)
    if apply:
        backup = ROOT / 'memory' / 'catalog_backups'
        backup.mkdir(parents=True, exist_ok=True)
        path = backup / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f') + '.json')
        original_parents = await db.product_templates.find({}, {'_id': 0}).to_list(100000)
        path.write_text(json.dumps({'products': before, 'product_templates': original_parents}, ensure_ascii=False, default=str), encoding='utf8')
        await pvs.ensure_indexes()
    result = await pvs.resolve_orphans('Migrasi katalog v2', dry_run=not apply)
    after = {p['id']: p for p in await db.products.find({}, {'_id': 0}).to_list(100000)}
    immutable = ('id', 'sku', 'price', 'harga_pokok', 'lifecycle', 'base_unit')
    drift = [p['id'] for p in before if p['id'] not in after or any(p.get(k) != after[p['id']].get(k) for k in immutable)]
    result['immutable_field_drift'] = drift
    result['product_count_before'] = len(before)
    result['product_count_after'] = len(after)
    if apply:
        result['backup'] = str(path)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    client.close()
    if drift or result.get('conflicts'):
        sys.exit(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    asyncio.run(main(args.apply))