"""Reference registry endpoint — SSOT enum untuk frontend.

Frontend TIDAK BOLEH lagi meng-hardcode daftar dropdown. Semua diambil dari sini,
sehingga backend & frontend memakai nilai + label yang sama.
"""
from fastapi import APIRouter, Depends, HTTPException

import reference as ref
import settings_store as cfg
from db import db, ORG_ID
from security import get_current_user

router = APIRouter(prefix="/reference", tags=["reference"])


async def _dynamic_values(org_id: str) -> dict:
    """Lengkapi grup dinamis dengan nilai yang sudah dipakai di DB (agar tak hilang).

    Mendukung `source` tunggal maupun `sources` (beberapa koleksi) — mis. grup `vendor`
    dikumpulkan dari master subkontraktor + vendor yang pernah dipakai di tagihan & PO.
    Grup yang punya `label_field` DILEWATI di sini karena ditangani `_labeled_options`
    (butuh nama manusia, bukan hanya kodenya).
    """
    out = {}
    for name, group in ref.GROUPS.items():
        srcs = group.get("sources") or ([group["source"]] if group.get("source") else [])
        if not (group.get("dynamic") and srcs) or srcs[0].get("label_field"):
            continue
        vals = []
        for src in srcs:
            try:
                vals += await db[src["collection"]].distinct(src["field"], {"org_id": org_id})
            except Exception:  # noqa: BLE001
                continue
        out[name] = sorted({v for v in vals if isinstance(v, str) and v.strip()})
    return out


async def _labeled_options(org_id: str) -> dict:
    """Grup dinamis yang LABEL-nya diambil dari master, bukan sama dengan nilainya.

    Contoh nyata: akun GL. Menampilkan "4-1100" saja memaksa pemakai menghafal bagan akun;
    yang dibutuhkan adalah "4-1100 — Pendapatan Penjualan Unit". Bentuk label diatur di
    registry (`label_format`), jadi tidak ada teks yang perlu ditulis ulang di frontend.
    """
    out = {}
    for name, group in ref.GROUPS.items():
        src = group.get("source") or {}
        if not (group.get("dynamic") and src.get("label_field")):
            continue
        field, lab_field = src["field"], src["label_field"]
        fmt = src.get("label_format", "{value} — {label}")
        try:
            rows = await db[src["collection"]].find(
                {"org_id": org_id}, {"_id": 0, field: 1, lab_field: 1}
            ).sort(field, 1).to_list(500)
        except Exception:  # noqa: BLE001
            continue
        seen, opts = set(), []
        for r in rows:
            val = r.get(field)
            if not isinstance(val, str) or not val.strip() or val in seen:
                continue
            seen.add(val)
            opts.append({"value": val,
                         "label": fmt.format(value=val, label=r.get(lab_field) or val)})
        out[name] = opts
    return out


async def _org_values(org_id: str) -> dict:
    """Nilai dinamis DB + nilai tambahan milik organisasi (setting `custom_setting` per grup,
    mis. `permit.types_custom`, `financing_bank.custom`)."""
    out = await _dynamic_values(org_id)
    for name, group in ref.GROUPS.items():
        key = group.get("custom_setting") or ("permit.types_custom" if name == "permit_type" else None)
        if not key:
            continue
        custom = await cfg.get(key, org_id=org_id) or []
        vals = [str(v).strip() for v in custom if str(v).strip()]
        if vals:
            out[name] = sorted({*out.get(name, []), *vals})
    return out


class NewValueIn(BaseModel):
    value: str


@router.post("/{group}/values")
async def add_reference_value(group: str, payload: NewValueIn,
                              user: dict = Depends(get_current_user)):
    """Simpan nilai baru grup dinamis ke MASTER organisasi (bukan hanya di form yang sedang
    diisi) — bank/jenis izin yang ditambah lewat pemilih tetap ada walau form batal disimpan."""
    g = ref.GROUPS.get(group)
    if not g:
        raise HTTPException(status_code=404, detail=f"Grup reference '{group}' tidak ada.")
    key = g.get("custom_setting") or ("permit.types_custom" if group == "permit_type" else None)
    if not (g.get("dynamic") and g.get("allow_new", True) and key):
        raise HTTPException(status_code=400, detail=f"Grup '{group}' tidak menerima nilai baru.")
    value = " ".join(payload.value.split())
    if len(value) < 2:
        raise HTTPException(status_code=400, detail="Nilai minimal 2 huruf.")
    org = user.get("org_id", ORG_ID)
    known = {o["value"].lower() for o in g.get("options", [])} | {
        v.lower() for v in (await _org_values(org)).get(group, [])}
    if value.lower() not in known:
        cur = [str(v) for v in (await cfg.get(key, org_id=org) or [])]
        await cfg.set_value(key, cur + [value], actor=user.get("email"), org_id=org)
    registry = ref.public_registry(await _org_values(org))
    return {"data": {"group": group, "value": value, "options": registry[group]["options"]}}


@router.get("")
async def get_reference(user: dict = Depends(get_current_user)):
    org = user.get("org_id", ORG_ID)
    registry = ref.public_registry(await _org_values(org))
    for name, opts in (await _labeled_options(org)).items():
        known = {o["value"] for o in registry[name]["options"]}
        registry[name]["options"] += [o for o in opts if o["value"] not in known]
    # `allow_new=False` -> pemilih TIDAK menawarkan "Nilai baru…" walau grupnya dinamis
    # (mis. akun GL: harus sudah ada di bagan akun sebelum dipakai).
    for name, group in ref.GROUPS.items():
        registry[name]["allow_new"] = bool(group.get("allow_new", True))
    return {"data": registry, "total": len(registry),
            "maps": {"channel_to_source": ref.CHANNEL_TO_SOURCE,
                     "source_score": ref.SOURCE_SCORE}}


@router.get("/{group}")
async def get_reference_group(group: str, user: dict = Depends(get_current_user)):
    if group not in ref.GROUPS:
        raise HTTPException(status_code=404, detail=f"Grup reference '{group}' tidak ada.")
    org = user.get("org_id", ORG_ID)
    registry = ref.public_registry(await _org_values(org))
    for name, opts in (await _labeled_options(org)).items():
        if name != group:
            continue
        known = {o["value"] for o in registry[name]["options"]}
        registry[name]["options"] += [o for o in opts if o["value"] not in known]
    data = registry[group]
    data["allow_new"] = bool(ref.GROUPS[group].get("allow_new", True))
    return {"data": data}
