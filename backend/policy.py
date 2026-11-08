"""Resolver kebijakan — SATU pintu baca untuk semua perilaku yang bisa dikonfigurasi (docs/audit/12).

Urutan nilai efektif (paling spesifik menang):  kontrak → klaster → proyek → organisasi → bawaan kode.
`settings_store` memegang tiga tingkat terakhir/tengah; tingkat KONTRAK disimpan di dokumen kontrak
(`policy_overrides: {key: {value, by, at, reason}}`) dan hanya berlaku bagi kunci yang `levels`-nya memuat "contract".

Prinsip yang dijaga di sini:
  * modul bisnis TIDAK membaca `settings` langsung untuk kebijakan akuntansi/pembatalan — selalu lewat `resolve`;
  * `snapshot` merekam nilai + asal yang berlaku PADA SAAT transaksi, supaya audit bisa menjelaskan dua transaksi yang
    diperlakukan berbeda; mengganti pengaturan berlaku ke depan dan tidak menjurnal ulang transaksi lama.
"""
import settings_store as cfg
from db import ORG_ID


def _contract_layer(spec: dict, key: str, contract: dict):
    """Lapisan tingkat kontrak bila diizinkan untuk kunci ini dan nilainya masih sah; selain itu None.
    Urutan di dalam lapisan: penimpaan eksplisit (`policy_overrides`, asal "contract") → nilai yang DIBEKUKAN saat kontrak lahir
    (`policy_snapshot`, asal "snapshot"; W2-B) — supaya mengganti bawaan organisasi/proyek tidak mengubah kontrak yang sudah ada diam-diam."""
    if not contract or "contract" not in (spec.get("levels") or ()):
        return None
    for field, origin in (("policy_overrides", "contract"), ("policy_snapshot", "snapshot")):
        ov = (contract.get(field) or {}).get(key)
        if not isinstance(ov, dict) or "value" not in ov:
            continue
        try:
            return {"value": cfg.coerce(spec, ov["value"]), "origin": origin}   # nilai usang (opsi dicabut/belum tersedia) → abaikan, jatuh ke atas
        except ValueError:
            continue
    return None


async def resolve_with_origin(key: str, *, org_id: str = ORG_ID, project_id: str = None,
                              cluster_id: str = None, contract: dict = None):
    """(nilai, asal) dengan asal ∈ contract|snapshot|cluster|project|org|default."""
    spec = cfg.DEFAULTS.get(key)
    if not spec:
        raise KeyError(f"Kebijakan tidak dikenal: {key}")
    layer = _contract_layer(spec, key, contract)
    if layer is not None:
        return layer["value"], layer["origin"]
    return await cfg.get_with_origin(key, org_id=org_id, project_id=project_id, cluster_id=cluster_id)


async def resolve(key: str, **kw):
    return (await resolve_with_origin(key, **kw))[0]


async def snapshot(keys, *, org_id: str = ORG_ID, project_id: str = None, cluster_id: str = None,
                   contract: dict = None) -> dict:
    """{key: {"value", "origin"}} — disimpan di dokumen transaksi sebagai `policy_snapshot`."""
    out = {}
    for k in keys:
        v, o = await resolve_with_origin(k, org_id=org_id, project_id=project_id, cluster_id=cluster_id,
                                         contract=contract)
        out[k] = {"value": v, "origin": o}
    return out
