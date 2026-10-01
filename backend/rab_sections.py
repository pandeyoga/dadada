"""Akses BAGIAN RAB per peran (Fase lanjutan — hak akses granular).

RAB/BoQ punya beberapa bagian (RAB Unit per tipe, Fasum/Fasos, Umum, Ringkasan & HPP).
`boq:view` tetap gerbang HALAMAN; berkas ini menambah lapisan halus: peran tertentu boleh
melihat SEBAGIAN bagian saja (mis. hanya "Umum", atau "Fasum/Fasos" saja, atau beberapa).

Backward-compatible dengan sengaja:
  * Disimpan terpisah di `permission_settings` (key `rab_section_access`) supaya matriks RBAC
    yang sudah ada di produksi TIDAK berubah.
  * Peran yang TIDAK punya entri = boleh SEMUA bagian (perilaku lama dipertahankan).
  * FULL_ACCESS (owner/super_admin) selalu semua bagian.
Entri berupa daftar KOSONG berarti "tidak boleh bagian apa pun" (pencabutan eksplisit).
"""
from fastapi import Depends, HTTPException

from db import db
from core_utils import now_iso
from security import get_current_user
from rbac import FULL_ACCESS_ROLES, is_known_role

KEY = "rab_section_access"

# kode bagian → (label, penjelasan). Kode dipakai frontend (tab) & endpoint.
SECTIONS = {
    "unit": ("RAB Unit (per tipe)", "Rincian RAB per tipe unit & add-on, template & versinya."),
    "fasum": ("Fasum / Fasos", "RAB fasilitas umum/sosial (jalan, drainase, taman, dll)."),
    "umum": ("Umum", "Biaya umum proyek: perizinan, land clearing, overhead, pemasaran."),
    "summary": ("Ringkasan & HPP", "Ringkasan RAB proyek, HPP per unit, margin & realisasi."),
}
SECTION_CODES = tuple(SECTIONS.keys())


async def get_raw() -> dict:
    """{role: [sections]} sebagaimana tersimpan (tanpa default). Peran tak dikenal dibuang."""
    doc = await db.permission_settings.find_one({"key": KEY}, {"_id": 0})
    out = {}
    for role, secs in ((doc or {}).get("sections") or {}).items():
        if not isinstance(secs, list):
            continue
        out[role] = [s for s in secs if s in SECTION_CODES]
    return out


async def allowed_for(role: str) -> list:
    """Bagian yang boleh dilihat peran ini (list kode). Peran tanpa entri = SEMUA."""
    if role in FULL_ACCESS_ROLES:
        return list(SECTION_CODES)
    raw = await get_raw()
    if role in raw:
        return raw[role]
    return list(SECTION_CODES)


async def can_view(role: str, section: str) -> bool:
    return section in await allowed_for(role)


def validate(sections_map: dict) -> list:
    """Periksa kiriman admin. Kembalikan daftar galat berbahasa manusia."""
    errors = []
    if not isinstance(sections_map, dict):
        return ["Data akses bagian RAB harus berupa objek peran → daftar bagian."]
    for role, secs in sections_map.items():
        if role in FULL_ACCESS_ROLES:
            errors.append(f"Peran '{role}' selalu melihat semua bagian dan tidak bisa dibatasi.")
            continue
        if not is_known_role(role):
            errors.append(f"Peran '{role}' tidak dikenal.")
            continue
        if not isinstance(secs, list):
            errors.append(f"Bagian untuk '{role}' harus berupa daftar.")
            continue
        asing = [s for s in secs if s not in SECTION_CODES]
        if asing:
            errors.append(f"Bagian tidak dikenal pada '{role}': " + ", ".join(map(str, asing)))
    return errors


async def save(sections_map: dict, actor: str) -> dict:
    """Simpan hanya entri yang MEMBATASI. Peran full-access tidak pernah disimpan.

    Peran yang dikirim dengan SEMUA bagian dihapus dari simpanan (kembali ke default
    "boleh semua") supaya dokumen tetap ramping dan tidak menyandera perilaku default.
    """
    clean = {}
    for role, secs in (sections_map or {}).items():
        if role in FULL_ACCESS_ROLES:
            continue
        norm = sorted({s for s in (secs or []) if s in SECTION_CODES})
        # daftar penuh = default → jangan simpan; daftar kosong = pencabutan → simpan.
        if len(norm) == len(SECTION_CODES):
            continue
        clean[role] = norm
    await db.permission_settings.update_one(
        {"key": KEY},
        {"$set": {"key": KEY, "sections": clean, "updated_at": now_iso(), "updated_by": actor}},
        upsert=True)
    return clean


def require_rab_section(section: str):
    """Dependency: tolak 403 bila peran tidak boleh melihat bagian RAB ini."""
    async def dep(user: dict = Depends(get_current_user)):
        if not await can_view(user.get("role"), section):
            label = SECTIONS.get(section, (section,))[0]
            raise HTTPException(
                status_code=403,
                detail=f"Akses ditolak: peran Anda tidak diberi akses bagian RAB '{label}'.")
        return user
    return dep
