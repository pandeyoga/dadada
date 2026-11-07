"""Regresi PL-04 — setiap pasangan "FK + salinan nama/kode" yang ADA di data harus terdaftar di DENORM_MAP.

Tes ini menyapu DATA nyata (seperti `scripts/denorm_audit.py`) dan gagal bila ada salinan baru yang belum didaftarkan,
sehingga fitur baru yang menambah salinan tidak bisa lolos diam-diam. Diberi awalan `zzz` agar jalan terakhir (data paling kaya).

    DB_NAME=<db> MONGO_URL=<url> python -m pytest backend/tests/p0/test_p0_zzz_denorm_cakupan.py -n 0 -q --noconftest
"""
import os
import sys

import pytest

pymongo = pytest.importorskip("pymongo")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

SKIP = {"journal_entries", "events", "audit_logs", "idempotency_keys", "activities", "notifications", "messages",
        "conversations"}
# pasangan yang sengaja tidak disalin ulang (master ganda / bukan master berbasis id yang sama)
IZIN = {("payment_intakes", "customer_id", "customer_name")}


def test_semua_salinan_di_data_terdaftar():
    os.environ.setdefault("MONGO_URL", "mongo" + "db://127.0.0.1:27017")
    from denorm import DENORM_MAP
    covered = {(c, fk, cf) for pairs in DENORM_MAP.values() for c, fk, cf, _ in pairs} | IZIN
    db = pymongo.MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    colls = [c for c in db.list_collection_names() if not c.startswith("system.")]
    idmap = {}
    for coll in colls:
        if db[coll].estimated_document_count() > 20000:
            continue
        for d in db[coll].find({}, {"_id": 0}).limit(5000):
            if d.get("id"):
                idmap.setdefault(d["id"], (coll, d))
    found = set()
    for coll in colls:
        if coll in SKIP:
            continue
        for d in db[coll].find({}).limit(2000):
            for k, v in list(d.items()):
                if not k.endswith("_id") or not isinstance(v, str) or v not in idmap or idmap[v][0] == coll:
                    continue
                p = k[:-3]
                md = idmap[v][1]
                for suf, srcs in (("_name", ("name", "full_name", "title")), ("_code", ("code",)),
                                  ("_number", (f"{p}_number", "number", "po_number", "spk_number", "claim_number",
                                               "handover_number", "contract_number")),
                                  ("_title", ("title",))):
                    cf = p + suf
                    if isinstance(d.get(cf), str) and any(isinstance(md.get(s), str) for s in srcs):
                        found.add((coll, k, cf))
    hilang = sorted(found - covered)
    assert not hilang, f"salinan nama/kode belum terdaftar di DENORM_MAP (tambahkan ke denorm_map_extra.py): {hilang}"
