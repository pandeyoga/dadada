"""Kain dasar — rujukan induk master data (mis. kain polos woven yang menjadi bahan printing)."""
from typing import Any, Dict

from db import db

FIELDS = ("base_fabric_template_id", "base_fabric_name", "base_fabric_sku_prefix")
EMPTY: Dict[str, Any] = {k: "" for k in FIELDS}


async def snapshot(template_id: Any, *, exclude_id: str = "") -> Dict[str, Any]:
    tid = str(template_id or "").strip()
    if not tid:
        return dict(EMPTY)
    if exclude_id and tid == exclude_id:
        raise ValueError("Kain dasar tidak boleh merujuk induk itu sendiri.")
    row = await db.product_templates.find_one({"id": tid}, {"_id": 0, "name": 1, "sku_prefix": 1, "status": 1})
    if not row or row.get("status") == "archived":
        raise ValueError("Kain dasar tidak ditemukan di master data atau sudah diarsipkan.")
    return {"base_fabric_template_id": tid, "base_fabric_name": row.get("name", ""),
            "base_fabric_sku_prefix": row.get("sku_prefix", "")}


def inherit(product: Dict[str, Any], parent: Dict[str, Any]) -> None:
    if not product.get("base_fabric_template_id") and parent.get("base_fabric_template_id"):
        for k in FIELDS:
            product[k] = parent.get(k, "")
