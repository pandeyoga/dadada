"""MASTER PAJAK — SATU sumber tarif & dasar pajak, boleh ditimpa per proyek (docs/audit/12 keputusan #15 FN-12 dan #1 PPN).

Dulu nilai pajak tersebar: dokumen `finance_configs` (PPN/BPHTB/PPh/NPOPTKP), persen BPHTB di komponen biaya, persen BANK_FEE
dari harga, `npoptkp` proyek yang tak pernah tersimpan. Sekarang semuanya kunci pengaturan `tax.master.*` / `tax.ppn.*`
(grup "Master Pajak & PPN", level organisasi + proyek, sensitif = alasan wajib + riwayat) dan SEMUA perhitungan membacanya
lewat `resolve(project_id)` di sini:

  * `finance_engine.compute_taxes` → catatan pajak AR, penawaran, dasar komisi "nilai bersih";
  * `allin_engine` → komponen biaya BPHTB (tarif, NPOPTKP, NJOP) dan BANK_FEE (% plafon);
  * `tax_engine` → Faktur Pajak dan estimasi PPN masukan.

`/finance/config/tax` hanya LAPISAN KOMPATIBILITAS: membaca/menulis master. Dokumen `finance_configs.finance_config` dimigrasikan
SEKALI ke level organisasi (idempoten; ditandai `migrated_to_master`) lalu tidak dibaca lagi — bukan sumber kedua.

PPN (keputusan #1): `tax.ppn.mode` ∈ eksklusif (BAWAAN = perilaku sebelum pengaturan ada) · inklusif · bebas_ppn. SATU fungsi
(`ppn_split`) yang menurunkan DPP/PPN dari harga; semua titik hitung memakainya. Mengganti mode/tarif berlaku KE DEPAN: dokumen
yang sudah lahir (penawaran, deal → `pricing.taxes`, AR → `taxes` + `policy_snapshot`) membekukan mode+tarif saat lahir, dan
pembacanya (susun-ulang AR, Faktur Pajak, dasar komisi) memakai beku itu — bukan master hari ini.
"""
import logging

import policy
import settings_store as cfg
from core_utils import new_id, now_iso
from db import db, ORG_ID

logger = logging.getLogger("sipro.tax_master")

K_PPN_MODE, K_PPN_RATE = "tax.ppn.mode", "tax.ppn.rate"
K_NPOPTKP, K_BPHTB, K_PPH = "tax.master.npoptkp", "tax.master.bphtb_rate", "tax.master.pph_final_rate"
K_NJOP, K_BANK_FEE = "tax.master.njop_per_m2", "tax.master.bank_fee_pct_of_plafon"
FIELDS = {"npoptkp": K_NPOPTKP, "bphtb_rate": K_BPHTB, "pph_final_rate": K_PPH, "njop_per_m2": K_NJOP,
          "bank_fee_pct_of_plafon": K_BANK_FEE, "ppn_rate": K_PPN_RATE, "ppn_mode": K_PPN_MODE}
LEGACY = {"ppn_rate": K_PPN_RATE, "bphtb_rate": K_BPHTB, "pph_rate": K_PPH, "npoptkp": K_NPOPTKP}   # bidang finance_config → kunci master
PPN_MODES = ("eksklusif", "inklusif", "bebas_ppn")
MODE_DEFAULT = "eksklusif"
DEFAULT_TAX = {"ppn_rate": 12.0, "bphtb_rate": 5.0, "pph_rate": 2.5, "npoptkp": 80_000_000}   # cadangan bila config tak lengkap
_DONE: set = set()   # organisasi yang sudah dimigrasikan pada proses ini


# ----------------------------------------------------------------------------- pembacaan
async def resolve(project_id: str = None, *, org_id: str = ORG_ID) -> dict:
    """Nilai master EFEKTIF untuk (organisasi, proyek): proyek menimpa organisasi, organisasi menimpa bawaan kode.
    Hasil: {npoptkp, bphtb_rate, pph_final_rate, njop_per_m2, bank_fee_pct_of_plafon, ppn_rate, ppn_mode, origins:{bidang: asal}}."""
    out, origins = {}, {}
    for field, key in FIELDS.items():
        out[field], origins[field] = await policy.resolve_with_origin(key, org_id=org_id, project_id=project_id)
    out["origins"] = origins
    return out


def _snapshot_of(m: dict) -> dict:
    return {K_PPN_MODE: {"value": m["ppn_mode"], "origin": m["origins"]["ppn_mode"]},
            K_PPN_RATE: {"value": m["ppn_rate"], "origin": m["origins"]["ppn_rate"]}}


async def config_for(org_id: str = ORG_ID, project_id: str = None) -> dict:
    """Bentuk lama `finance_config` ({ppn_rate, bphtb_rate, pph_rate, npoptkp}) + kunci baru, dari master."""
    m = await resolve(project_id, org_id=org_id)
    return {"org_id": org_id, "key": "finance_config", "project_id": project_id,
            "ppn_rate": m["ppn_rate"], "ppn_mode": m["ppn_mode"], "bphtb_rate": m["bphtb_rate"],
            "pph_rate": m["pph_final_rate"], "npoptkp": m["npoptkp"], "njop_per_m2": m["njop_per_m2"],
            "bank_fee_pct_of_plafon": m["bank_fee_pct_of_plafon"], "origins": m["origins"],
            "policy_snapshot": _snapshot_of(m)}


def _frozen_ppn(ar: dict = None, deal: dict = None):
    """Mode+tarif PPN yang dibekukan saat dokumen lahir — AR dulu (paling akhir lahir), lalu rincian harga deal. None bila tak ada."""
    pricing = (deal or {}).get("pricing") or {}
    for snap, taxes in (((ar or {}).get("policy_snapshot"), (ar or {}).get("taxes")),
                        (pricing.get("policy_snapshot"), pricing.get("taxes"))):
        if isinstance(snap, dict) and K_PPN_MODE in snap and K_PPN_RATE in snap:
            return {"mode": snap[K_PPN_MODE]["value"], "rate": snap[K_PPN_RATE]["value"], "snapshot": snap}
        if isinstance(taxes, dict) and taxes.get("ppn_rate") is not None:   # dokumen lama: sebelum mode ada = eksklusif
            mode = taxes.get("ppn_mode") or MODE_DEFAULT
            snap = {K_PPN_MODE: {"value": mode, "origin": "dokumen"}, K_PPN_RATE: {"value": taxes["ppn_rate"], "origin": "dokumen"}}
            return {"mode": mode, "rate": taxes["ppn_rate"], "snapshot": snap}
    return None


async def config_for_deal(org_id: str, deal: dict = None, ar: dict = None) -> dict:
    """Konfigurasi pajak untuk SATU deal: tarif/dasar dari master (proyek deal), tetapi mode+tarif PPN memakai yang DIBEKUKAN saat
    penawaran/deal/AR-nya lahir (mengganti mode berlaku ke depan; transaksi lama tidak dihitung ulang)."""
    c = await config_for(org_id, (deal or {}).get("project_id") or (ar or {}).get("project_id"))
    frozen = _frozen_ppn(ar, deal)
    if frozen:
        c["ppn_mode"], c["ppn_rate"], c["policy_snapshot"] = frozen["mode"], frozen["rate"], frozen["snapshot"]
    return c


# ----------------------------------------------------------------------------- perhitungan (satu pintu)
def ppn_split(price: int, mode: str, rate: float) -> dict:
    """SATU-SATUNYA tempat DPP/PPN diturunkan dari harga. eksklusif: DPP = harga, PPN = harga × tarif/100 (persis rumus lama);
    inklusif: harga sudah memuat PPN; bebas_ppn: tarif efektif 0. Pembulatan = round() Python seperti sebelumnya."""
    price = int(price or 0)
    if mode == "bebas_ppn":
        return {"dpp": price, "ppn": 0, "rate": 0.0, "mode": mode}
    if mode == "inklusif":
        dpp = round(price * 100 / (100 + rate)) if rate else price
        return {"dpp": int(dpp), "ppn": price - int(dpp), "rate": rate, "mode": mode}
    if mode != "eksklusif":
        raise ValueError(f"Mode PPN tidak dikenal: {mode}")
    return {"dpp": price, "ppn": round(price * rate / 100), "rate": rate, "mode": mode}


def land_area_of(unit: dict):
    """Luas tanah unit (m²): kolom master unit `luas_tanah` (ditulis PATCH /units & impor); `land_area` = nama lama/dokumen. None bila kosong."""
    u = unit or {}
    return u.get("luas_tanah") or u.get("land_area") or None


def bphtb_npop(price: int, njop_per_m2=0, land_area=None) -> int:
    """NPOP BPHTB = harga transaksi; bila NJOP dipakai (> 0) dan luas tanah unit diketahui → nilai TERBESAR keduanya."""
    price = int(price or 0)
    try:
        njop = int(round(float(njop_per_m2 or 0) * float(land_area or 0)))
    except (TypeError, ValueError):
        njop = 0
    return max(price, njop)


def compute(price: int, config: dict, land_area=None) -> dict:
    """Pajak dari harga: PPN (sesuai mode), BPHTB (tarif × (NPOP − NPOPTKP)), PPh Final (tarif × harga). Bentuk keluaran =
    `compute_taxes` lama + `ppn_mode` dan `dpp`."""
    price = int(price or 0)
    ppn = ppn_split(price, config.get("ppn_mode") or MODE_DEFAULT, config.get("ppn_rate", DEFAULT_TAX["ppn_rate"]))
    bphtb_rate = config.get("bphtb_rate", DEFAULT_TAX["bphtb_rate"])
    pph_rate = config.get("pph_rate", DEFAULT_TAX["pph_rate"])
    npoptkp = int(config.get("npoptkp", DEFAULT_TAX["npoptkp"]))
    bphtb_base = max(0, bphtb_npop(price, config.get("njop_per_m2"), land_area) - npoptkp)
    return {
        "ppn": ppn["ppn"], "ppn_rate": ppn["rate"], "ppn_mode": ppn["mode"], "dpp": ppn["dpp"],
        "bphtb": round(bphtb_base * bphtb_rate / 100), "bphtb_rate": bphtb_rate, "bphtb_base": bphtb_base,
        "pph": round(price * pph_rate / 100), "pph_rate": pph_rate,
    }


def record_rows(taxes: dict, price: int) -> list:
    """Baris catatan pajak (jenis, dasar, tarif, jumlah). Mode Bebas PPN → TANPA catatan PPN."""
    rows = []
    if taxes.get("ppn_mode") != "bebas_ppn":
        rows.append(("ppn", int(taxes.get("dpp", price)), taxes["ppn_rate"], taxes["ppn"]))
    rows.append(("bphtb", taxes["bphtb_base"], taxes["bphtb_rate"], taxes["bphtb"]))
    rows.append(("pph", price, taxes["pph_rate"], taxes["pph"]))
    return rows


# ----------------------------------------------------------------------------- lapisan kompatibilitas `/finance/config/tax`
async def write_legacy(org_id: str, *, ppn_rate, bphtb_rate, pph_rate, npoptkp, actor: str, reason: str,
                       project_id: str = None, extra: dict = None) -> list:
    """Tulis empat nilai bentuk lama ke MASTER (level organisasi, atau proyek bila `project_id`); `extra` = {kunci master: nilai}
    untuk kunci lain (mode PPN, NJOP, % plafon). Hanya nilai yang BERUBAH yang ditulis (riwayat tidak dikotori). Validasi
    tipe/rentang = spesifikasi kunci. Kembalikan daftar kunci yang berubah."""
    scope, scope_id = ("project", project_id) if project_id else ("org", org_id)
    wanted = {K_PPN_RATE: ppn_rate, K_BPHTB: bphtb_rate, K_PPH: pph_rate, K_NPOPTKP: npoptkp, **(extra or {})}
    now = await resolve(project_id, org_id=org_id)
    by_key = {v: k for k, v in FIELDS.items()}
    for key, val in wanted.items():
        cfg.coerce(cfg.DEFAULTS[key], val)   # semua divalidasi dulu — jangan menulis sebagian
    changed = []
    for key, val in wanted.items():
        cur = now[by_key[key]]
        if (cur == val) if isinstance(cur, str) else (float(cur) == float(val)):
            continue
        await cfg.set_value(key, val, actor=actor, reason=reason, org_id=org_id, scope=scope, scope_id=scope_id)
        changed.append(key)
    return changed


# ----------------------------------------------------------------------------- migrasi `finance_configs` → master
async def ensure_migrated(org_id: str) -> None:
    """Pindahkan nilai `finance_configs.finance_config` yang BERBEDA dari bawaan ke level organisasi master — SEKALI (idempoten:
    penanda `migrated_to_master` + baris yang sudah ada tidak ditimpa). Dipanggil oleh `settings_store._rows` sehingga setiap
    pembaca/tampilan melihat nilai yang sama sejak pembacaan pertama. Gagal → dicatat, tidak memblokir pembacaan setting."""
    if org_id in _DONE:
        return
    try:
        doc = await db.finance_configs.find_one({"org_id": org_id, "key": "finance_config"}, {"_id": 0})
        if doc and not doc.get("migrated_to_master"):
            await _migrate(org_id, doc)
        _DONE.add(org_id)
    except Exception:  # noqa: BLE001
        logger.exception("Migrasi finance_config → master pajak gagal untuk %s (diulang pada pembacaan berikut)", org_id)


async def _migrate(org_id: str, doc: dict) -> None:
    ts = now_iso()
    for legacy, key in LEGACY.items():
        spec = cfg.DEFAULTS[key]
        if doc.get(legacy) is None:
            continue
        try:
            val = cfg.coerce(spec, doc[legacy])
        except ValueError:
            logger.warning("Nilai lama %s=%r tidak sah menurut master — dilewati", legacy, doc[legacy])
            continue
        if float(val) == float(spec["value"]):
            continue   # sama dengan bawaan: tidak perlu penimpaan
        flt = {"org_id": org_id, "key": key, "scope": "org", "scope_id": org_id}
        row = {"id": new_id(), "type": spec["type"], "group": spec["group"], "value": val, "updated_by": "migrasi",
               "updated_at": ts, "created_at": ts,
               "history": [{"at": ts, "by": "migrasi", "from": spec["value"], "to": val,
                            "reason": "Migrasi otomatis dari konfigurasi pajak lama (finance_configs)"}]}
        await db.settings.update_one(flt, {"$setOnInsert": row}, upsert=True)   # tidak menimpa nilai master yang sudah ada
    comp = await db.cost_components.find_one({"org_id": org_id, "code": "BPHTB", "calc_method": "rumus_bphtb"}, {"_id": 0, "pct": 1})
    rate = doc.get("bphtb_rate")
    if comp and rate is not None and float(comp.get("pct") or 0) not in (0.0, float(rate)):
        logger.warning("Persen komponen BPHTB (%s) berbeda dari tarif BPHTB lama (%s): kini SATU tarif master dipakai keduanya",
                       comp.get("pct"), rate)
    await db.finance_configs.update_one({"org_id": org_id, "key": "finance_config"},
                                        {"$set": {"migrated_to_master": True, "migrated_at": ts}})
    cfg.invalidate()
