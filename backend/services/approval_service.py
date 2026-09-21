"""services/approval_service.py — **ATURAN AMBANG PERSETUJUAN** (`approval_rules`).

Cakupan modul ini SEKARANG hanya CRUD **aturan** (`approval_rules`) yang dipakai
layar Pengaturan → "Aturan Persetujuan" (`routers/approval_rules.py`).

YANG DIPENSIUNKAN DI FASE F-6 (2026-08-17) — DAN KENAPA
=======================================================
Modul ini dulu juga memuat **mesin persetujuan generik**: `create_approval_request()`,
`get_approval_requests()`, `approve_request()`, `reject_request()`,
`get_pending_approvals_count()`, `check_approval_required()` + `_evaluate_threshold()`.
Seluruhnya dicabut setelah diukur, bukan ditebak:

1. **Nol produsen.** `create_approval_request()` tidak pernah dipanggil siapa pun di
   seluruh backend, sehingga koleksi `approval_requests` selalu kosong (terukur: 0 dok).
   Endpoint `POST /api/approval-requests/{id}/approve|reject` ADA dan izin
   `approval.approve` diberikan ke admin & manajer — wewenang di kertas tanpa satu pun
   dokumen yang bisa diputuskan. Itulah satu-satunya "izin yatim" yang jujur di audit
   peran F-2, dan KPI beranda yang berbohong (0 padahal 17) lahir dari koleksi mati ini.
2. **Nol pemakai di layar.** Tidak ada satu pun berkas frontend yang memanggil
   `/approval-requests` (dicari di seluruh `frontend/src`).
3. **Menghidupkannya akan MELANGGAR arsitektur.** Setiap persetujuan nyata di sistem ini
   diputuskan di endpoint dokumennya sendiri (PO, SO, PR, retur, kontrabon, cuti, …) —
   "Pusat Persetujuan" sengaja read-only supaya *tidak ada dua jalur penulisan status*
   (lihat `routers/approvals_matrix.py`). Mesin generik yang menulis status sendiri
   akan menjadi jalur penulisan kedua untuk dokumen yang sama.
4. **Permukaan yang tak berscope.** Endpoint generik itu membaca `approval_requests`
   TANPA saringan badan usaha (`list` tanpa filter entitas; pada `get` bahkan
   `resolve_scope_ids()` dihitung lalu tidak dipakai) — pagar multi-PT bocor pada
   fitur yang tak pernah dipakai.
5. **Penilai ambang KEMBAR.** `check_approval_required()` menilai ambang dari
   `approval_rules`, padahal jalur yang HIDUP adalah
   `services/config_service.evaluate_approval()` / `build_approval_chain()` — itulah
   yang dipanggil `routers/sales_orders.py` & `routers/purchase_orders.py`. Dua penilai
   untuk satu pertanyaan = dua pendapat yang kelak berbeda.

GANTINYA (bukan sekadar dicabut): 14 antrean keputusan NYATA yang selama ini tak
terhitung didaftarkan ke `services/approval_backlog_service.QUEUES`, dan gate baru
**INV-APPR-01** (`scripts/guardrails/verify_approval_queues.py`) membuat pintu
keputusan baru mustahil ditambahkan tanpa antrean yang menghitungnya.

Aturan ambang (`approval_rules`) TETAP hidup & bisa diatur pemilik dari layar.
"""
from typing import Any, Dict, List, Optional

from core_utils import new_id, now_iso
from db import db

# ─── Approval Rules Management ────────────────────────────────────────────────


async def create_approval_rule(
    doc_type: str,
    min_amount: float = 0,
    max_amount: float | None = None,
    required_role: str = "",
    sort: int = 1,
    active: bool = True,
    description: str = "",
    created_by: str = "system",
    entity_id: str = "all",
    is_percent: bool = False,
) -> Dict[str, Any]:
    """Buat aturan ambang persetujuan — SKEMA MESIN (`config_service.evaluate_approval`).

    Rentang [min_amount, max_amount) menentukan `required_role`; role kosong =
    dokumen lolos tanpa persetujuan. `is_percent` untuk doc_type='discount'.
    """
    rule = {
        "id": new_id("aprule"),
        "entity_id": entity_id or "all",   # FASE E-0 — aturan per entitas ('all' = warisan grup)
        "doc_type": doc_type,
        "min_amount": round(float(min_amount or 0), 2),
        "max_amount": round(float(max_amount), 2) if max_amount is not None else None,
        "required_role": required_role or "",
        "sort": int(sort or 1),
        "active": bool(active),
        "is_percent": bool(is_percent),
        "description": description,
        "created_at": now_iso(),
        "created_by": created_by,
        "updated_at": now_iso(),
    }

    await db.approval_rules.insert_one(rule)
    rule.pop("_id", None)
    return rule


async def get_approval_rules(
    doc_type: Optional[str] = None,
    active: Optional[bool] = None,
    entity_ids: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Daftar aturan ambang, dengan saringan opsional.

    FASE E-0 (L15/L17) — `approval_rules` terdaftar SCOPED. `entity_ids` menyaring
    aturan milik entitas tersebut **plus** aturan bawaan grup (`entity_id="all"`/kosong)
    yang berlaku sebagai warisan.
    """
    query: Dict[str, Any] = {}
    if doc_type:
        query["doc_type"] = doc_type
    if active is not None:
        query["active"] = active
    if entity_ids:
        query["$or"] = [{"entity_id": {"$in": list(entity_ids)}},
                        {"entity_id": "all"}, {"entity_id": None},
                        {"entity_id": {"$exists": False}}]

    return await db.approval_rules.find(query, {"_id": 0}).sort(
        [("doc_type", 1), ("sort", 1)]).to_list(1000)


async def update_approval_rule(rule_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    """Ubah aturan ambang."""
    updates["updated_at"] = now_iso()

    result = await db.approval_rules.find_one_and_update(
        {"id": rule_id},
        {"$set": updates},
        return_document=True,
    )

    if not result:
        raise ValueError(f"Approval rule {rule_id} not found")

    result.pop("_id", None)
    return result


async def delete_approval_rule(rule_id: str) -> bool:
    """Nonaktifkan aturan (soft delete) — jejak aturan lama tetap bisa dibaca dokumen."""
    result = await db.approval_rules.update_one(
        {"id": rule_id},
        {"$set": {"active": False, "updated_at": now_iso()}},
    )

    return result.modified_count > 0
