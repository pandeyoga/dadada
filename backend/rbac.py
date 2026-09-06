"""RBAC + tenant scope. Enforced from Fase 0 (fix #1 of old SIPRO).

- permission_settings.matrix is the SSOT (admin-overridable); DEFAULT_PERMISSIONS is fallback.
- require_permission(resource, action) is a FastAPI dependency.
- scope_query applies org_id + row-level scope (sales = own; pm/site = assigned project).
"""
from fastapi import Depends, HTTPException

from db import db, ORG_ID
from core_utils import new_id, now_iso
from security import get_current_user

# Roles that see everything within their org.
FULL_ACCESS_ROLES = {"super_admin", "owner"}
# Roles limited to their own assigned rows.
SALES_SCOPED_ROLES = {"sales"}
# Roles limited to their assigned projects.
PROJECT_SCOPED_ROLES = {"project_manager", "site_engineer"}

ALL_ROLES = [
    "super_admin", "owner", "sales_manager", "marketing_admin",
    "sales", "finance", "project_manager", "site_engineer",
    # Fase 29 — divisi Digital Marketing (baru) & supervisor Keuangan
    "dm_supervisor", "dm_staff", "finance_manager",
    # Legal & kepatuhan: halaman legal publik, permintaan penghapusan data (UU PDP / Meta).
    "legal_admin",
]

# Fase 29: peran baru MEWARISI matriks peran yang paling dekat supaya tidak perlu
# menulis ulang seluruh matriks (dan supaya izin lama tidak berubah diam-diam).
ROLE_INHERITS = {
    "dm_supervisor": "marketing_admin",
    "dm_staff": "marketing_admin",
    "finance_manager": "finance",
}
# Aksi yang DICABUT dari peran turunan (staf digital marketing tidak boleh menghapus
# atau membagi ulang lead milik sales, dan tidak boleh menyetujui apa pun).
ROLE_DENY = {
    "dm_staff": {"delete", "assign", "approve", "sign", "manage"},
}
# Tambahan izin khusus peran baru (supervisor keuangan boleh menyetujui, supervisor
# digital marketing mengelola otomasi/template/showroom).
ROLE_GRANTS = {
    # Fase 39b: verifikasi dokumen syarat. Ditulis sebagai grant eksplisit (bukan hanya di
    # DEFAULT_PERMISSIONS) karena matriks RBAC organisasi yang sudah tersimpan di DB
    # MENIMPA daftar izin per peran — tanpa ini, aksi `verify` tidak akan pernah aktif pada
    # organisasi yang matriksnya dibuat sebelum fase ini, dan tombol Verifikasi jadi 403.
    # Fase 99: override harga add-on Rp 0 saat reservasi (Fase 77E) = `pricing:approve`, satu
    # definisi untuk backend (deals_router) dan layar (ReserveDialog) — bukan daftar peran disalin.
    "sales_manager": {"documents": ["verify"], "pricing": ["approve"]},
    "marketing_admin": {"documents": ["verify"]},
    "finance": {"documents": ["verify"]},
    # Fase 31: Manajer Proyek adalah VERIFIKATOR pekerjaan unit (approve pada
    # `construction`). Ditulis sebagai grant eksplisit, bukan hanya di
    # DEFAULT_PERMISSIONS, supaya izin baru tetap berlaku pada organisasi yang
    # dokumen matriks RBAC-nya sudah tersimpan sebelum fase ini.
    "project_manager": {
        "construction": ["approve"],
    },
    "finance_manager": {
        "finance": ["approve", "manage"], "commissions": ["approve"], "marketing_fee": ["approve"],
        "pricing": ["approve"],
        "petty_cash": ["approve"], "gl": ["manage"], "coa": ["manage"], "work_tasks": ["view_all", "create", "update"],
        "documents": ["verify"],   # Fase 39b — supervisor keuangan ikut memverifikasi berkas
        # Fase 47: supervisor keuangan adalah satu-satunya yang boleh MEMBATALKAN
        # pencocokan bank (membalik pembukuan) dan menyetujui/membayar upah harian.
        "bank": ["view_all", "create", "update", "approve"],
        "labor": ["view_all", "approve"],
        # Fase 50A: MENEROBOS daftar periksa serah terima & MEMBATALKAN BAST yang salah
        # terbit adalah keputusan manajerial (kunci diserahkan walau ada yang belum beres,
        # atau dokumen resmi ditarik kembali). Tim proyek/keuangan tetap yang menerbitkan.
        "handover": ["view_all", "create", "override", "cancel"],
        "warranty": ["view_all"],
        # Fase 56C: keputusan pembatalan & pengabaian penahanan refund adalah wewenang
        # Manajer Keuangan. Ditulis sebagai grant eksplisit (bukan hanya di
        # DEFAULT_PERMISSIONS) karena matriks RBAC yang sudah tersimpan di DB MENIMPA
        # daftar izin per peran \u2014 tanpa ini aksinya 403 pada organisasi lama.
        "cancellation": ["view_all", "create", "update", "approve", "override"],
        # Fase 57A: menyusun skema pembayaran & menetapkannya pada kontrak (jadwal kewajiban
        # pembeli) adalah wewenang manajerial — alasan sama dengan di atas: matriks RBAC di
        # DB menimpa daftar izin per peran.
        "payment_scheme": ["view_all", "create", "update", "assign"],
        # Fase 58: KERINGANAN denda (`late_fee:override`) = wewenang Manajer Keuangan, bukan
        # penagihnya. Eksplisit karena matriks RBAC di DB menimpa izin bawaan peran.
        "late_fee": ["view_all", "create", "override"],
    },
    "dm_supervisor": {
        "automation_rules": ["manage"], "wa_templates": ["manage"], "channels": ["manage"],
        "broadcasts": ["manage"], "showroom": ["view_all", "update"],
        "work_tasks": ["view_all", "create", "update"],
        # Fase 43: supervisor DM adalah pemilik anggaran iklan \u2014 hanya dia yang boleh
        # MENARIK data dari platform & MENGIRIM ULANG event konversi ke sistem luar.
        "ads": ["manage"],
    },
    "dm_staff": {
        "automation_rules": ["view_all"], "wa_templates": ["view_all", "create", "update"],
        "broadcasts": ["view_all", "create"], "inbox": ["view_all", "create"],
        "work_tasks": ["view_own", "create", "update"],
    },
    # Admin Legal & Kepatuhan: mengelola halaman legal publik + menangani permintaan
    # penghapusan data; boleh MELIHAT pembeli/dokumen/jejak audit untuk verifikasi identitas.
    "legal_admin": {
        "legal": ["manage"], "settings": ["view_all"], "customers": ["view_all"],
        "leads": ["view_all"], "documents": ["view_all"], "audit_logs": ["view_all"],
        "work_tasks": ["view_own", "create", "update"],
    },
}

from rbac_matrix import DEFAULT_PERMISSIONS  # noqa: E402  (matriks izin bawaan)



def _permitted(perms, action) -> bool:
    if "all" in perms or "manage" in perms:
        return True
    if action in perms:
        return True
    if action == "view" and any(a in perms for a in ("view", "view_all", "view_own")):
        return True
    # view_all mencakup view_own (peran yang boleh melihat semua otomatis boleh melihat miliknya)
    if action == "view_own" and any(a in perms for a in ("view", "view_all")):
        return True
    return False


async def get_matrix() -> dict:
    """Matriks efektif = DEFAULT_PERMISSIONS + override tersimpan di DB.

    Digabung (bukan diganti) supaya resource/peran BARU dari kode langsung berlaku
    walau dokumen matriks di DB dibuat sebelum fase ini (dulu: matriks DB menang total,
    sehingga resource baru tak pernah aktif sampai admin menyimpan ulang).
    """
    merged = {res: dict(roles) for res, roles in DEFAULT_PERMISSIONS.items()}
    doc = await db.permission_settings.find_one({"key": "rbac_matrix"}, {"_id": 0})
    for res, roles in ((doc or {}).get("matrix") or {}).items():
        merged.setdefault(res, {}).update(roles or {})
    return merged


def _role_perms(matrix: dict, resource: str, role: str) -> list:
    """Izin efektif satu peran: matriks langsung → warisan peran → tambahan khusus."""
    return _role_perms_detail(matrix, resource, role)["perms"]


# Aksi yang dikenal mesin RBAC. Dipakai layar Hak Akses untuk menawarkan pilihan yang
# BENAR-BENAR berarti (bukan kotak centang karangan) dan untuk menolak aksi asing.
KNOWN_ACTIONS = ["view", "view_all", "view_own", "create", "update", "delete", "assign",
                 "approve", "verify", "sign", "override", "cancel", "manage", "all"]


def _role_perms_detail(matrix: dict, resource: str, role: str) -> dict:
    """Izin efektif + ASAL-USULNYA, supaya layar Hak Akses bisa jujur.

    Asal-usul (`sources`) penting karena tiga lapis aturan bertumpuk:
      * `matrix`    — matriks tersimpan/bawaan (bisa diubah admin),
      * `inherited` — peran baru mewarisi peran terdekat (`ROLE_INHERITS`),
      * `granted`   — tambahan yang dipasang di kode (`ROLE_GRANTS`).

    Tanpa ini layar Hak Akses menampilkan sel KOSONG untuk peran turunan (dm_staff,
    dm_supervisor, finance_manager) padahal API-nya menjawab 200 — layar keamanan yang
    berbohong, tepatnya jenis kebohongan yang paling berbahaya.

    **Daftar KOSONG yang tertulis eksplisit = PENCABUTAN.** Sebelum ini `[]` dianggap
    "belum diatur" sehingga warisan peran dan grant kode menghidupkannya kembali: admin
    mencabut izin di layar, sistem menjawab "tersimpan", dan aksesnya tetap ada. Sekarang
    kunci yang ADA tetapi kosong berarti tidak boleh — warisan & grant tidak dipakai.
    """
    res_map = matrix.get(resource) or {}
    sources, inherited_from = [], None
    if role in res_map:
        perms = list(res_map[role] or [])
        if not perms:
            return {"perms": [], "sources": ["revoked"], "inherited_from": None,
                    "revoked": True}
        sources.append("matrix")
    elif role in ROLE_INHERITS:
        inherited_from = ROLE_INHERITS[role]
        perms = list(res_map.get(inherited_from) or [])
        if perms:
            sources.append("inherited")
        else:
            inherited_from = None
    else:
        perms = []
    grants = list((ROLE_GRANTS.get(role) or {}).get(resource) or [])
    if grants:
        perms += grants
        sources.append("granted")
    deny = ROLE_DENY.get(role)
    dicabut_kode = []
    if deny:
        dicabut_kode = sorted({p for p in perms if p in deny})
        perms = [p for p in perms if p not in deny]
    return {"perms": sorted(set(perms)), "sources": sources,
            "inherited_from": inherited_from, "revoked": False,
            "denied_by_code": dicabut_kode}


def effective_matrix(matrix: dict) -> dict:
    """Matriks EFEKTIF untuk semua peran × resource (dengan asal-usulnya).

    Inilah yang harus dilihat admin: hasil akhir yang ditegakkan `require_permission`,
    bukan hanya baris yang kebetulan tertulis di dokumen matriks.
    """
    out = {}
    for resource in matrix:
        out[resource] = {}
        for role in ALL_ROLES:
            if role in FULL_ACCESS_ROLES:
                out[resource][role] = {"perms": ["all"], "sources": ["full_access"],
                                       "inherited_from": None, "revoked": False,
                                       "denied_by_code": []}
                continue
            out[resource][role] = _role_perms_detail(matrix, resource, role)
    return out


def validate_matrix(candidate: dict) -> list:
    """Periksa matriks kiriman admin. Mengembalikan daftar galat berbahasa manusia.

    Menolak lebih baik daripada menyimpan diam-diam sesuatu yang tidak akan pernah
    berlaku: resource/peran/aksi yang tidak dikenal mesin RBAC hanya akan jadi baris mati
    di database dan membuat layar Hak Akses menjanjikan hal yang tidak ditegakkan.
    """
    errors = []
    if not isinstance(candidate, dict) or not candidate:
        return ["Matriks izin kosong atau bukan objek."]
    for resource, roles in candidate.items():
        if resource not in DEFAULT_PERMISSIONS:
            errors.append(f"Resource '{resource}' tidak dikenal mesin RBAC.")
            continue
        if not isinstance(roles, dict):
            errors.append(f"Isi resource '{resource}' harus objek peran → daftar aksi.")
            continue
        for role, perms in roles.items():
            if role not in ALL_ROLES:
                errors.append(f"Peran '{role}' (resource '{resource}') tidak dikenal.")
                continue
            if role in FULL_ACCESS_ROLES:
                # Baris bawaan yang dikirim balik apa adanya (mis. organizations.owner) bukan
                # pembatasan — GET dan PUT harus saling menerima.
                if perms == (DEFAULT_PERMISSIONS.get(resource) or {}).get(role):
                    continue
                errors.append(
                    f"Peran '{role}' selalu berakses penuh dan tidak bisa dibatasi dari "
                    "layar ini — mencabutnya akan mengunci semua orang keluar.")
                continue
            if perms is None:
                continue
            if not isinstance(perms, list):
                errors.append(f"Aksi untuk '{role}' pada '{resource}' harus berupa daftar.")
                continue
            asing = [p for p in perms if p not in KNOWN_ACTIONS]
            if asing:
                errors.append(f"Aksi tidak dikenal pada '{resource}' → '{role}': "
                              + ", ".join(map(str, asing)))
    return errors



async def can(role: str, resource: str, action: str) -> bool:
    if role in FULL_ACCESS_ROLES:
        return True
    matrix = await get_matrix()
    return _permitted(_role_perms(matrix, resource, role), action)


async def effective_permissions(role: str) -> dict:
    """Izin efektif satu peran untuk SELURUH resource — dipakai `GET /auth/me`.

    Tujuannya agar frontend bisa menyembunyikan aksi yang pasti ditolak backend tanpa
    menyalin aturan RBAC (dulu satu-satunya cara adalah menebak dari nama peran, yang
    membuat aturan punya dua versi). Peran FULL_ACCESS ditandai `"*": ["*"]`.
    """
    if role in FULL_ACCESS_ROLES:
        return {"*": ["*"]}
    matrix = await get_matrix()
    out = {}
    for resource in matrix:
        perms = _role_perms(matrix, resource, role)
        if perms:
            out[resource] = sorted(set(perms))
    return out


def require_permission(resource: str, action: str):
    async def dep(user: dict = Depends(get_current_user)):
        if not await can(user.get("role"), resource, action):
            raise HTTPException(
                status_code=403,
                detail=f"Akses ditolak: tidak memiliki izin '{action}' pada '{resource}'",
            )
        return user
    return dep


def require_super_admin():
    """Cross-tenant operations (org management/onboarding/switch) are super_admin-only.
    Note: owner is FULL_ACCESS *within its own tenant* but must NOT manage other tenants."""
    async def dep(user: dict = Depends(get_current_user)):
        if user.get("role") != "super_admin":
            raise HTTPException(status_code=403, detail="Akses ditolak: khusus super admin.")
        return user
    return dep


def is_scoped_sales(user: dict) -> bool:
    return user.get("role") in SALES_SCOPED_ROLES


def is_project_scoped(user: dict) -> bool:
    return user.get("role") in PROJECT_SCOPED_ROLES


def project_query(user: dict, query: dict = None) -> dict:
    """org_id + project membership scope (pm/site_engineer -> assigned projects)."""
    q = dict(query or {})
    q["org_id"] = user.get("org_id", ORG_ID)
    if user.get("role") in PROJECT_SCOPED_ROLES:
        q["members"] = user.get("email")
    return q


async def assert_project_access(project_id: str, user: dict):
    """Raise 404/403 if project missing or not accessible to a project-scoped user."""
    proj = await db.projects.find_one({"id": project_id, "org_id": user.get("org_id", ORG_ID)}, {"_id": 0})
    if not proj:
        raise HTTPException(status_code=404, detail="Proyek tidak ditemukan")
    if user.get("role") in PROJECT_SCOPED_ROLES and user.get("email") not in (proj.get("members") or []):
        raise HTTPException(status_code=403, detail="Akses ditolak: bukan anggota proyek ini")
    return proj


def scope_query(user: dict, query: dict = None, own_field: str = "assigned_to") -> dict:
    """Add org_id + row-level scope to a Mongo query."""
    q = dict(query or {})
    q["org_id"] = user.get("org_id", ORG_ID)
    if user.get("role") in SALES_SCOPED_ROLES:
        q[own_field] = user.get("email")
    return q


async def audit_log(user: dict, action: str, resource: str, entity_id: str = None, meta: dict = None):
    await db.audit_logs.insert_one({
        "id": new_id(), "org_id": user.get("org_id", ORG_ID),
        "actor": user.get("email"), "actor_role": user.get("role"),
        "action": action, "resource": resource, "entity_id": entity_id,
        "meta": meta or {}, "created_at": now_iso(),
    })
