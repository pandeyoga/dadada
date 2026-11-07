"""Validasi MASTER komponen biaya, skema all-in, skema pencairan KPR & konfigurasi pajak (audit FN-02, FN-12c).

Latar belakang: `POST/PUT /cost-components` dan `/allin-schemes` dulu menerima apa saja — nominal negatif,
persen 500%, akun GL "9-9999", cara hitung "xyz", butir skema yang merujuk komponen yang tidak ada. Satu
salah ketik di master mengubah tagihan SEMUA reservasi baru (Rp 4,25 M per unit pada uji audit), dan akun
GL yang tak ada melahirkan tagihan AP `approved` tanpa jurnal. Validasi sebelumnya hanya ada di layar (UI);
API harus menolaknya sendiri.

Semua fungsi melempar `ValueError` berpesan Indonesia (router → HTTP 400). Untuk UPDATE, yang divalidasi
hanya kolom yang SEDANG diubah: komponen lama yang sudah rusak tetap bisa dinonaktifkan tanpa harus
membereskan seluruh isinya dulu.
"""
import math
import re

import coa_rules
import gl_engine as gl
from db import db

MAX_NOMINAL = 1_000_000_000_000          # Rp 1 triliun: batas kewajaran satu komponen/override
CALC_METHODS = ("nominal_tetap", "persen_harga", "rumus_bphtb")
TREATMENTS = ("developer_borne", "customer_pass_through")
CODE_RE = re.compile(r"^[A-Z0-9][A-Z0-9_-]{1,31}$")
GL_AP_CODE = "2-1100"                    # pembayaran AP selalu mendebet 2-1100 → akun utang komponen harus ini
DEFAULTS = {"gl_expense": "6-1700", "gl_liability": "2-1470", "gl_ap": GL_AP_CODE}
GL_ROLES = {   # kolom → (label pesan, tipe akun yang sah)
    "gl_expense": ("beban", ("expense",)),
    "gl_liability": ("titipan/kewajiban", ("liability",)),
    "gl_ap": ("utang usaha (AP)", ("liability",)),
}


def _num(v, label: str, lo: float, hi: float, integer: bool = False):
    if isinstance(v, bool) or v is None:
        raise ValueError(f"{label} harus berupa angka.")
    try:
        x = float(v)
    except (TypeError, ValueError):
        raise ValueError(f"{label} harus berupa angka.")
    if not math.isfinite(x):
        raise ValueError(f"{label} harus berupa angka yang wajar.")
    if integer and x != int(x):
        raise ValueError(f"{label} harus bilangan bulat rupiah.")
    if x < lo or x > hi:
        raise ValueError(f"{label} harus di antara {_fmt(lo)} dan {_fmt(hi)}.")
    return int(x) if integer else x


def _fmt(x: float) -> str:
    return f"{x:,.0f}".replace(",", ".") if abs(x) >= 1000 else f"{x:g}"


async def check_account(org: str, code: str, field: str) -> str:
    """Akun GL untuk komponen harus NYATA, AKTIF, bertipe sesuai peran kolomnya (pakai aturan CoA)."""
    label, types = GL_ROLES[field]
    code = (code or "").strip() or DEFAULTS[field]
    if not coa_rules.CODE_RE.match(code):
        raise ValueError(f"Akun {label} '{code}' tidak valid — format kode akun angka-tanda hubung-empat "
                         "angka, mis. 6-1700.")
    await gl.ensure_coa(org)
    acc = await db.accounts.find_one({"org_id": org, "code": code}, {"_id": 0})
    if not acc:
        raise ValueError(f"Akun {label} {code} tidak ada dalam Bagan Akun (CoA).")
    if acc.get("is_active") is False:
        raise ValueError(f"Akun {label} {code} {acc.get('name') or ''} NONAKTIF — pilih akun lain atau aktifkan "
                         "dulu di Bagan Akun.")
    if acc.get("type") not in types:
        raise ValueError(f"Akun {label} {code} {acc.get('name') or ''} bertipe '{acc.get('type')}', "
                         f"seharusnya {' / '.join(types)}.")
    if field == "gl_liability" and code in coa_rules.CONTROL_ACCOUNTS:
        raise ValueError(f"Akun {code} {coa_rules.CONTROL_ACCOUNTS[code]} adalah akun kendali subledger — "
                         "tidak boleh dipakai sebagai akun titipan komponen (pakai 2-1470 atau akun kewajiban lain).")
    if field == "gl_ap" and code != GL_AP_CODE:
        raise ValueError(f"Akun utang usaha komponen harus {GL_AP_CODE}: pembayaran tagihan AP selalu "
                         f"mendebet {GL_AP_CODE}, akun lain membuat saldo utang tidak cocok dengan subledger.")
    return code


async def clean_component(org: str, data: dict, *, creating: bool) -> dict:
    """Validasi & normalisasi kolom master komponen yang ADA di `data` (lengkap saat membuat)."""
    out = {}
    if creating or "code" in data:
        code = str(data.get("code") or "").strip().upper()
        if not CODE_RE.match(code):
            raise ValueError("Kode komponen wajib 2–32 karakter huruf besar/angka/_/- dan diawali huruf atau "
                             "angka (mis. BPHTB, NOTARY_FEE).")
        out["code"] = code
    if creating or "name" in data:
        name = str(data.get("name") or "").strip()
        if not name or len(name) > 120:
            raise ValueError("Nama komponen wajib diisi (maksimal 120 karakter).")
        out["name"] = name
    if creating or "calc_method" in data:
        if data.get("calc_method") not in CALC_METHODS:
            raise ValueError(f"Cara hitung '{data.get('calc_method')}' tidak dikenal ({', '.join(CALC_METHODS)}).")
        out["calc_method"] = data["calc_method"]
    if creating or "default_treatment" in data:
        if data.get("default_treatment") not in TREATMENTS:
            raise ValueError(f"Perlakuan '{data.get('default_treatment')}' tidak dikenal ({', '.join(TREATMENTS)}).")
        out["default_treatment"] = data["default_treatment"]
    if "amount" in data or creating:
        out["amount"] = _num(data.get("amount") or 0, "Nominal komponen", 0, MAX_NOMINAL, integer=True)
    if "pct" in data or creating:
        out["pct"] = _num(data.get("pct") or 0, "Persentase komponen", 0, 100)
    for f in GL_ROLES:
        if creating or f in data:
            out[f] = await check_account(org, data.get(f), f)
    for f in ("kpr_only", "is_active"):
        if f in data:
            out[f] = bool(data[f])
    return out


async def _project_ids_ok(org: str, ids: list) -> list:
    ids = [str(i).strip() for i in ids if str(i).strip()]
    if len(ids) != len(set(ids)):
        raise ValueError("Daftar proyek skema memuat proyek ganda.")
    if ids:
        found = {p["id"] async for p in db.projects.find({"org_id": org, "id": {"$in": ids}}, {"_id": 0, "id": 1})}
        missing = [i for i in ids if i not in found]
        if missing:
            raise ValueError(f"Proyek tidak ditemukan di organisasi ini: {', '.join(missing[:3])}.")
    return ids


async def clean_scheme(org: str, data: dict, *, current: dict = None) -> dict:
    """Validasi skema all-in. `current` = skema tersimpan (UPDATE): butir yang SUDAH ada di skema
    dan merujuk komponen yang kemudian dinonaktifkan tidak memblokir penyimpanan ulang."""
    creating = current is None
    out = {}
    if creating or "name" in data:
        name = str(data.get("name") or "").strip()
        if not name or len(name) > 120:
            raise ValueError("Nama skema wajib diisi (maksimal 120 karakter).")
        out["name"] = name
    if "note" in data:
        out["note"] = str(data.get("note") or "").strip()[:500]
    if "project_ids" in data:
        out["project_ids"] = await _project_ids_ok(org, data.get("project_ids") or [])
    if "unit_types" in data:
        uts = [str(u).strip() for u in (data.get("unit_types") or []) if str(u).strip()]
        if len(uts) > 50:
            raise ValueError("Tipe unit skema terlalu banyak.")
        out["unit_types"] = uts
    if "is_active" in data:
        out["is_active"] = bool(data["is_active"])
    if creating or "items" in data:
        items = data.get("items")
        if not isinstance(items, list) or not items:
            raise ValueError("Skema wajib memuat minimal satu komponen.")
        comps = {c["code"]: c for c in await db.cost_components.find({"org_id": org}, {"_id": 0}).to_list(500)}
        had = {(it or {}).get("component_code") for it in (current or {}).get("items") or []}
        seen, clean = set(), []
        for it in items:
            if not isinstance(it, dict):
                raise ValueError("Butir skema harus berupa objek {component_code, treatment, override_amount}.")
            code = str(it.get("component_code") or "").strip().upper()
            comp = comps.get(code)
            if not comp:
                raise ValueError(f"Komponen '{code or it.get('component_code')}' tidak ada di master komponen biaya.")
            if code in seen:
                raise ValueError(f"Komponen {code} muncul lebih dari sekali dalam skema.")
            seen.add(code)
            if comp.get("is_active") is False and code not in had:
                raise ValueError(f"Komponen {code} NONAKTIF — tidak boleh dimasukkan ke skema. Aktifkan dulu "
                                 "komponennya atau pilih komponen lain.")
            tr = it.get("treatment") or comp.get("default_treatment")
            if tr not in TREATMENTS:
                raise ValueError(f"Perlakuan '{it.get('treatment')}' tidak dikenal ({', '.join(TREATMENTS)}).")
            ov = it.get("override_amount")
            if ov is not None:
                ov = _num(ov, f"Nominal terkunci komponen {code}", 0, MAX_NOMINAL, integer=True)
            clean.append({"component_code": code, "treatment": tr, "override_amount": ov})
        out["items"] = clean
    return out


def clean_kpr_scheme(doc: dict) -> dict:
    """Tambahan atas `kpr_disburse.validate_scheme`: rentang angka (persen tahap -50 + 150 dulu lolos total 100%)."""
    doc["name"] = str(doc.get("name") or "").strip()[:120]
    if not doc["name"]:
        raise ValueError("Nama skema pencairan wajib diisi.")
    doc["tolerance_pct"] = _num(doc.get("tolerance_pct"), "Toleransi pencairan (%)", 0, 100)
    for t in doc.get("tranches") or []:
        t["pct"] = _num(t.get("pct"), f"Persentase tahap {t.get('code')}", 0, 100)
        t["amount"] = _num(t.get("amount"), f"Nominal tahap {t.get('code')}", 0, MAX_NOMINAL, integer=True)
    return doc


def clean_tax_config(ppn_rate, bphtb_rate, pph_rate, npoptkp) -> tuple:
    """Tarif pajak 0–100% & NPOPTKP ≥ 0 (dulu ppn_rate −5, bphtb_rate 500, npoptkp −1 tersimpan)."""
    return (_num(ppn_rate, "Tarif PPN (%)", 0, 100), _num(bphtb_rate, "Tarif BPHTB (%)", 0, 100),
            _num(pph_rate, "Tarif PPh (%)", 0, 100), _num(npoptkp, "NPOPTKP", 0, MAX_NOMINAL, integer=True))
