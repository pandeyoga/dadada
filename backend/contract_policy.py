"""Kebijakan tingkat KONTRAK — penimpaan per kontrak + nilai yang DIBEKUKAN saat kontrak lahir (docs/audit/12 §1.1, W2-B).

`policy.resolve(..., contract=)` sudah membaca `contract["policy_overrides"][kunci] = {value, by, at, reason}` dan
`contract["policy_snapshot"][kunci] = {value, origin, at}` untuk kunci yang `levels`-nya memuat "contract" (W0). Modul ini adalah PENULISNYA:

  * `snapshot_new` — dipanggil `contracts_engine.ensure_contract`: nilai kunci ber-level kontrak yang berlaku SAAT kontrak lahir direkam di
    kontrak. Kontrak lama tanpa snapshot dibekukan malas (`ensure_snapshot`, idempoten — baris ber-syarat `$exists: False`) saat pertama
    dibaca/diubah. Dengan begitu mengganti bawaan organisasi/proyek TIDAK mengubah kontrak yang sudah ada diam-diam.
  * `view` — nilai efektif + asal tiap kunci (contract · snapshot-asal project/org/default/skema), penimpaan, nilai warisan hidup, opsi & label,
    boleh-diubah atau alasan terkunci, riwayat.
  * `set_override` / `clear_override` — PUT/DELETE: hanya kunci ber-level kontrak; validasi `settings_store.coerce` (opsi `unavailable` ditolak);
    kunci sensitif wajib alasan (≥ 10 karakter); diserialkan per kontrak (mutex) + CAS pada `updated_at`; riwayat (aktor, waktu, dari → ke,
    alasan; maks 50) di dokumen kontrak; kontrak batal/selesai ditolak; penangan per keluarga kunci (`HANDLERS`, kini `bphtb.`) menentukan
    kapan tidak boleh diubah (uang sudah bergerak) dan apa akibat lanjutannya (komponen biaya, invoice).
Izin dan audit di router (`routers/contract_policy_router.py`). Perubahan berlaku KE DEPAN; tidak ada jurnal ulang.
"""
import importlib
import logging

import policy
import reference as _ref
import settings_store as cfg
from core_utils import now_iso
from db import db
from idempotency import cas, expect_of, mutex

logger = logging.getLogger("sipro.contract_policy")

HANDLERS = {"bphtb.": "bphtb_policy"}   # awalan kunci → modul penangan (antarmuka: lihat bphtb_policy bagian "penangan tingkat KONTRAK")
MIN_REASON = 10
HISTORY_MAX = 50
ORIGIN_LABEL = {"contract": "Khusus kontrak ini", "project": "Pengaturan proyek (dibekukan saat kontrak lahir)",
                "org": "Pengaturan organisasi (dibekukan saat kontrak lahir)", "default": "Bawaan sistem (dibekukan saat kontrak lahir)",
                "cluster": "Pengaturan klaster (dibekukan saat kontrak lahir)", "snapshot": "Dibekukan saat kontrak lahir",
                "skema": "Mengikuti skema all-in kontrak", "legacy": "Input biaya bebas (kontrak lama)"}


def contract_keys() -> list:
    """Kunci yang boleh ditimpa di tingkat kontrak (spesifikasi `levels` memuat "contract")."""
    return [k for k, s in cfg.DEFAULTS.items() if "contract" in (s.get("levels") or ())]


def _spec(key: str) -> dict:
    spec = cfg.DEFAULTS.get(key)
    if not spec:
        raise ValueError(f"Kebijakan tidak dikenal: {key}")
    if "contract" not in (spec.get("levels") or ()):
        raise ValueError(f"'{spec['label']}' tidak bisa diatur di tingkat kontrak (hanya: {', '.join(contract_keys()) or '-'}).")
    return spec


def handler_of(key: str):
    for prefix, mod in HANDLERS.items():
        if key.startswith(prefix):
            return importlib.import_module(mod)
    return None


def _valid(key: str, value):
    try:
        return cfg.coerce(cfg.DEFAULTS[key], value)
    except (ValueError, KeyError):
        return None


def writer_of(key: str) -> tuple:
    """Izin yang dibutuhkan MENGUBAH kunci ini: `writer` spesifikasi (kunci keuangan = finance:manage), selain itu contracts:manage."""
    return tuple((cfg.DEFAULTS.get(key) or {}).get("writer") or ("contracts", "manage"))


# ----------------------------------------------------------------------------- snapshot
async def snapshot_new(org: str, contract: dict) -> dict:
    """{kunci: {value, origin, at}} nilai kunci ber-level kontrak yang berlaku untuk kontrak ini SEKARANG. Kunci yang punya penangan
    dibaca dari keadaan kontrak sendiri (mis. BPHTB dari snapshot komponen biaya — yang benar-benar menjadi tagihan); selebihnya dari
    resolver (proyek → organisasi → bawaan)."""
    ts, out = now_iso(), {}
    for key in contract_keys():
        h = handler_of(key)
        got = h.contract_applied(contract).get(key) if h else None
        if got is None:
            got = await policy.resolve_with_origin(key, org_id=org, project_id=contract.get("project_id"))
        out[key] = {"value": got[0], "origin": got[1], "at": ts}
    return out


async def ensure_snapshot(org: str, contract: dict) -> dict:
    """Kontrak dengan snapshot (membekukan malas yang belum punya). Idempoten: dua pemanggil bersamaan → satu yang menulis."""
    if isinstance(contract.get("policy_snapshot"), dict) and contract["policy_snapshot"]:
        return contract
    snap = await snapshot_new(org, contract)
    await db.contracts.update_one({"id": contract["id"], "org_id": org, "policy_snapshot": {"$exists": False}},
                                  {"$set": {"policy_snapshot": snap, "policy_snapshot_lazy": True}})
    fresh = await db.contracts.find_one({"id": contract["id"], "org_id": org}, {"_id": 0})
    return fresh or contract


# ----------------------------------------------------------------------------- nilai efektif
async def _current(org: str, contract: dict, key: str, h) -> tuple:
    """(nilai, asal) yang SEDANG berlaku: penimpaan kontrak → keadaan kontrak (penangan) → snapshot beku → resolver hidup."""
    ov = (contract.get("policy_overrides") or {}).get(key)
    if isinstance(ov, dict) and _valid(key, ov.get("value")) is not None:
        return _valid(key, ov["value"]), "contract"
    got = h.contract_applied(contract).get(key) if h else None
    if got is not None:
        return got
    sn = (contract.get("policy_snapshot") or {}).get(key)
    if isinstance(sn, dict) and _valid(key, sn.get("value")) is not None:
        return _valid(key, sn["value"]), sn.get("origin") or "snapshot"
    return await policy.resolve_with_origin(key, org_id=org, project_id=contract.get("project_id"))


async def _live(org: str, contract: dict, key: str) -> tuple:
    """Nilai warisan HIDUP (proyek → organisasi → bawaan) — apa yang didapat kontrak bila penimpaannya dicabut."""
    return await policy.resolve_with_origin(key, org_id=org, project_id=contract.get("project_id"))


async def lock_reason(org: str, contract: dict, key: str):
    """Kenapa kunci ini tidak boleh diubah sekarang (atau None): kontrak batal/selesai, atau penangannya melarang (uang sudah bergerak)."""
    import cancellation_costs as cc
    why = await cc.closed_reason(org, contract.get("deal_id"), contract.get("id"))
    if why:
        return f"Kontrak/deal ini sudah {why} — kebijakan kontrak tidak bisa diubah."
    if contract.get("state") in ("cancelled", "completed"):
        return "Kontrak ini sudah selesai/dibatalkan — kebijakan kontrak tidak bisa diubah."
    h = handler_of(key)
    return await h.contract_lock_reason(org, contract) if h else None


async def view(org: str, contract: dict) -> dict:
    """Isi `GET /contracts/{id}/policy`."""
    contract = await ensure_snapshot(org, contract)
    rows = []
    for key in contract_keys():
        spec, h = cfg.DEFAULTS[key], handler_of(key)
        value, origin = await _current(org, contract, key, h)
        live_v, live_o = await _live(org, contract, key)
        why = await lock_reason(org, contract, key)
        ov = (contract.get("policy_overrides") or {}).get(key)
        rows.append({
            "key": key, "label": spec["label"], "help": spec["help"], "impact": spec.get("impact"), "type": spec["type"],
            "options": list(spec.get("options") or []), "option_labels": _ref.labels(spec["ref_group"]) if spec.get("ref_group") else {},
            "unavailable": dict(spec.get("unavailable") or {}), "sensitive": bool(spec.get("sensitive")),
            "min": spec.get("min"), "max": spec.get("max"), "default_value": spec["value"],
            "writer": list(writer_of(key)),
            "value": value, "origin": origin, "origin_label": ORIGIN_LABEL.get(origin, origin),
            "override": ov if isinstance(ov, dict) else None,
            "inherited": {"value": live_v, "origin": live_o, "origin_label": ORIGIN_LABEL.get(live_o, live_o)},
            "snapshot": (contract.get("policy_snapshot") or {}).get(key),
            "editable": why is None, "locked_reason": why})
    summary = {}
    for mod in {handler_of(r["key"]) for r in rows if handler_of(r["key"])}:
        if hasattr(mod, "contract_summary"):
            summary[mod.__name__.replace("_policy", "")] = mod.contract_summary(contract)
    return {"contract_id": contract["id"], "contract_number": contract.get("number"), "state": contract.get("state"),
            "keys": rows, "summary": summary,
            "history": list(reversed((contract.get("policy_history") or [])[-HISTORY_MAX:]))}


# ----------------------------------------------------------------------------- penulisan
async def _fresh(org: str, contract_id: str) -> dict:
    c = await db.contracts.find_one({"id": contract_id, "org_id": org}, {"_id": 0})
    if not c:
        raise LookupError("Kontrak tidak ditemukan")
    return c


async def _write(org: str, contract: dict, key: str, *, action: str, value, new_origin: str, old: tuple, reason: str,
                 actor: str, overrides: dict, snapshot: dict, h, eff: dict) -> dict:
    """Satu penulisan atomik (CAS pada `updated_at`): penimpaan, snapshot, riwayat, dan field turunan dari penangan."""
    plan = (await h.contract_plan(org, contract, eff)) if h else None
    ts = now_iso()
    entry = {"at": ts, "by": actor, "key": key, "action": action, "from": old[0], "from_origin": old[1], "to": value,
             "to_origin": new_origin, "reason": reason or None}
    update = {"$set": {"policy_overrides": overrides, "policy_snapshot": snapshot, "updated_at": ts, **((plan or {}).get("fields") or {})},
              "$push": {"policy_history": {"$each": [entry], "$slice": -HISTORY_MAX}}}
    await cas("contracts", {"id": contract["id"], "org_id": org}, expect_of(contract, "updated_at"), update, what="Kontrak ini")
    out = {"changed_components": bool(plan and plan["material"]), "entry": entry, "after": None}
    if plan and plan["material"] and h:
        try:
            out["after"] = await h.contract_after(org, contract["id"], actor, f"kebijakan kontrak {key}: {action}")
        except Exception as e:  # noqa: BLE001 — kontrak sudah benar; invoice bisa diterbitkan ulang Keuangan dari layar kontrak
            logger.exception("Efek lanjutan kebijakan kontrak %s gagal untuk kontrak %s", key, contract["id"])
            out["after"] = {"error": f"Komponen biaya sudah diperbarui, tetapi invoice biaya belum diterbitkan ulang ({e}). "
                                     "Terbitkan ulang dari layar kontrak › Biaya transaksi."}
    return out


def _check(key: str, reason: str):
    spec = _spec(key)
    reason = (reason or "").strip()
    if spec.get("sensitive") and len(reason) < MIN_REASON:
        raise ValueError(f"'{spec['label']}' adalah kebijakan sensitif — alasan wajib diisi (minimal {MIN_REASON} karakter).")
    return spec, reason


async def set_override(org: str, contract_id: str, key: str, value, reason: str, actor: str) -> dict:
    spec, reason = _check(key, reason)
    value = cfg.coerce(spec, value)   # opsi 'belum tersedia' ditolak di sini
    async with mutex(f"contract.policy:{org}:{contract_id}", what="Kebijakan kontrak ini"):
        contract = await ensure_snapshot(org, await _fresh(org, contract_id))
        why = await lock_reason(org, contract, key)
        if why:
            raise ValueError(why)
        h = handler_of(key)
        old = await _current(org, contract, key, h)
        eff = {k: await _current(org, contract, k, h) for k in (h.KEYS if h else (key,))}
        eff[key] = (value, "contract")
        ts = now_iso()
        overrides = {**(contract.get("policy_overrides") or {}), key: {"value": value, "by": actor, "at": ts, "reason": reason}}
        res = await _write(org, contract, key, action="set", value=value, new_origin="contract", old=old, reason=reason,
                           actor=actor, overrides=overrides, snapshot=contract.get("policy_snapshot") or {}, h=h, eff=eff)
    return {**res, "key": key, "value": value, "origin": "contract"}


async def clear_override(org: str, contract_id: str, key: str, reason: str, actor: str) -> dict:
    spec, reason = _check(key, reason)
    async with mutex(f"contract.policy:{org}:{contract_id}", what="Kebijakan kontrak ini"):
        contract = await ensure_snapshot(org, await _fresh(org, contract_id))
        if key not in (contract.get("policy_overrides") or {}):
            raise ValueError(f"'{spec['label']}' tidak sedang ditimpa pada kontrak ini — sudah mengikuti proyek/organisasi.")
        why = await lock_reason(org, contract, key)
        if why:
            raise ValueError(why)
        h = handler_of(key)
        old = await _current(org, contract, key, h)
        live_v, live_o = await _live(org, contract, key)   # "kembali mengikuti proyek/organisasi" = nilai hidup SEKARANG, lalu dibekukan lagi
        eff = {k: await _current(org, contract, k, h) for k in (h.KEYS if h else (key,))}
        eff[key] = (live_v, live_o)
        overrides = {k: v for k, v in (contract.get("policy_overrides") or {}).items() if k != key}
        snapshot = {**(contract.get("policy_snapshot") or {}), key: {"value": live_v, "origin": live_o, "at": now_iso()}}
        res = await _write(org, contract, key, action="clear", value=live_v, new_origin=live_o, old=old, reason=reason,
                           actor=actor, overrides=overrides, snapshot=snapshot, h=h, eff=eff)
    return {**res, "key": key, "value": live_v, "origin": live_o}
