"""Sumbu varian yang dapat dikonfigurasi pemilik (rnd.variant_axes_default / _optional).

Katalog sumbu tetap hidup di kode (size/material/lebar tidak dihapus), tetapi
yang DITAWARKAN ke MD & dipasang otomatis pada induk baru dibaca dari konfigurasi.
"""
from typing import Any, Dict, List

import domain_registry as dr
from services.config_resolver import value_of

AXIS_CATALOG: Dict[str, Dict[str, Any]] = {
    "color": {"label": "Warna", "options": [], "source": "color_library"},
    "grade": {"label": "Grade", "options": [
        {"code": g["value"], "label": g["value"], "value": g["value"], "hex": ""} for g in dr.GRADES]},
    "origin": {"label": "Asal", "options": [
        {"code": "IMP", "label": "Impor", "value": "impor", "hex": ""},
        {"code": "LOK", "label": "Lokal", "value": "lokal", "hex": ""}]},
    "size": {"label": "Ukuran", "options": []},
    "material": {"label": "Material", "options": []},
    "lebar": {"label": "Lebar", "options": [], "unit": "cm"},
}
DEFAULT_AXES = ["color", "grade", "origin"]


def _clean(values: Any, fallback: List[str]) -> List[str]:
    if not isinstance(values, list):
        return list(fallback)
    out: List[str] = []
    for v in values:
        k = str(v or "").strip().lower()
        if k in AXIS_CATALOG and k not in out:
            out.append(k)
    return out


async def axis_config(entity_id: str = "") -> Dict[str, Any]:
    ctx = {"entity_id": entity_id or ""}
    default = _clean(await value_of("rnd.variant_axes_default", ctx), DEFAULT_AXES)
    optional = [k for k in _clean(await value_of("rnd.variant_axes_optional", ctx), []) if k not in default]
    return {"default": default, "optional": optional,
            "catalog": [{"key": k, **AXIS_CATALOG[k], "preset": k in default} for k in default + optional]}
