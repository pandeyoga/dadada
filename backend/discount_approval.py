"""Persetujuan diskon BERTINGKAT menurut nilai (docs/audit/12 keputusan #8).

Kunci pengaturan (Pusat Konfigurasi › Aturan Bisnis, tingkat org + proyek):
  * `discount.approval_mode`  — `satu_level` (perilaku lama: semua pemegang izin persetujuan harga setara) atau
    `bertingkat` (bawaan);
  * `discount.approval_tiers` — daftar `{max_amount, role}`: total potongan D disetujui oleh `role` (atau yang lebih
    tinggi) pada tingkat PERTAMA dengan D <= max_amount; `max_amount: null` = tak terbatas.

Yang TIDAK berubah: KAPAN sebuah potongan butuh persetujuan (ambang persen, ambang nominal, mode per skema/promo/kupon di
`pricing_engine.evaluate_approval`). Pengaturan ini hanya menentukan SIAPA yang boleh memutuskan.

Aturan penjaga:
  * snapshot kebijakan direkam di dokumen permohonan saat LAHIR (`policy_snapshot` pada `deal.pricing_approval`,
    `approval_policy` pada penawaran) — mengganti pengaturan tidak mengubah permohonan yang sedang menunggu;
  * permohonan tanpa snapshot (lahir sebelum fitur ini) diperlakukan `satu_level` persis seperti dulu;
  * pada mode bertingkat pemohon tidak boleh memutuskan permohonannya sendiri pada tingkat mana pun (tanpa pengecualian
    owner); peran di bawah tingkat yang dibutuhkan ditolak dengan pesan yang menyebut peran minimum.

Urutan kewenangan (naik): sales_manager < finance_manager < owner; super_admin selalu boleh. Peran kustom pemegang izin
persetujuan setara sales_manager (tingkat dasar).
"""
import policy

KEY_MODE = "discount.approval_mode"
KEY_TIERS = "discount.approval_tiers"
SATU, BERTINGKAT = "satu_level", "bertingkat"

RANK = {"sales_manager": 1, "finance_manager": 2, "owner": 3}
ROLE_LABEL = {"sales_manager": "Manajer Penjualan", "finance_manager": "Manajer Keuangan", "owner": "Owner"}
SUPER_RANK = 99      # super_admin
FLOOR_RANK = 1       # pemegang izin persetujuan lain (peran kustom) = tingkat dasar
MAX_AMOUNT_LIMIT = 100_000_000_000_000
DEFAULT_TIERS = [{"max_amount": None, "role": "sales_manager"}]


class Forbidden(PermissionError):
    """Penyetuju tidak berwenang untuk tingkat yang dibutuhkan / memutuskan permohonannya sendiri."""


def rank_of(role: str) -> int:
    if role == "super_admin":
        return SUPER_RANK
    return RANK.get(role, FLOOR_RANK)


def _int(v, label: str):
    if isinstance(v, bool) or v is None or (isinstance(v, str) and not v.strip()):
        raise ValueError(f"{label}: harus berupa angka bulat.")
    try:
        f = float(v)
    except (TypeError, ValueError):
        raise ValueError(f"{label}: harus berupa angka bulat.")
    if f != int(f):
        raise ValueError(f"{label}: harus berupa angka bulat (tanpa pecahan).")
    return int(f)


def validate(value) -> list:
    """Validasi + normalisasi tabel tingkat. Melempar ValueError (pesan Indonesia) bila tidak sah.

    Syarat: tidak kosong; tiap baris `{max_amount, role}` (opsional `min_amount` HARUS sama dengan batas atas tingkat
    sebelumnya); `max_amount` bilangan bulat > 0 dan MENAIK ketat (sama/turun = tumpang tindih/tidak ascending);
    tingkat terakhir `max_amount` kosong (menutup sampai tak terbatas — tanpa itu ada celah di atas batas terakhir);
    peran dikenal dan tidak turun ketika nilai naik."""
    if not isinstance(value, list) or not value:
        raise ValueError("Tabel tingkat persetujuan: harus berupa daftar tingkat dan tidak boleh kosong.")
    out, prev_max, prev_rank = [], 0, 0
    for i, t in enumerate(value, 1):
        lab = f"Tingkat {i}"
        if not isinstance(t, dict):
            raise ValueError(f"{lab}: harus berupa objek {{max_amount, role}}.")
        bad = set(t) - {"max_amount", "role", "min_amount"}
        if bad:
            raise ValueError(f"{lab}: kolom tidak dikenal ({', '.join(sorted(bad))}).")
        if prev_max is None:
            raise ValueError(f"{lab}: tidak boleh ada tingkat setelah tingkat 'tak terbatas' (tingkat {i - 1}).")
        role = t.get("role")
        if role not in RANK:
            raise ValueError(f"{lab}: peran '{role}' tidak dikenal — pilih salah satu: {', '.join(RANK)}.")
        if t.get("min_amount") not in (None, ""):
            mn = _int(t["min_amount"], f"{lab} min_amount")
            if mn > prev_max:
                raise ValueError(f"{lab}: ada CELAH — mulai dari Rp {mn:,} padahal tingkat sebelumnya berakhir di "
                                 f"Rp {prev_max:,}. Rentang harus menyambung dari 0 sampai tak terbatas.".replace(",", "."))
            if mn < prev_max:
                raise ValueError(f"{lab}: TUMPANG TINDIH — mulai dari Rp {mn:,} padahal tingkat sebelumnya berakhir di "
                                 f"Rp {prev_max:,}.".replace(",", "."))
        mx = t.get("max_amount")
        if mx in (None, ""):
            mx = None
        else:
            mx = _int(mx, f"{lab} max_amount")
            if mx <= 0:
                raise ValueError(f"{lab}: batas nominal harus lebih dari 0.")
            if mx > MAX_AMOUNT_LIMIT:
                raise ValueError(f"{lab}: batas nominal tidak wajar (> Rp {MAX_AMOUNT_LIMIT:,}).".replace(",", "."))
            if mx <= prev_max:
                raise ValueError(f"{lab}: batas Rp {mx:,} harus LEBIH BESAR dari batas tingkat sebelumnya "
                                 f"(Rp {prev_max:,}) — tingkat harus menaik, tidak boleh tumpang tindih."
                                 .replace(",", "."))
        if RANK[role] < prev_rank:
            raise ValueError(f"{lab}: peran {ROLE_LABEL[role]} lebih rendah daripada tingkat sebelumnya — nilai yang "
                             "lebih besar tidak boleh disetujui peran yang lebih rendah.")
        out.append({"max_amount": mx, "role": role})
        prev_max, prev_rank = mx, RANK[role]
    if out[-1]["max_amount"] is not None:
        raise ValueError("Tingkat terakhir harus tak terbatas (kosongkan batas nominalnya) — tanpa itu ada CELAH: "
                         f"potongan di atas Rp {out[-1]['max_amount']:,} tidak punya penyetuju.".replace(",", "."))
    return out


def pick(tiers, total: int) -> dict:
    """Tingkat PERTAMA dengan total <= max_amount (None = tak terbatas)."""
    for t in tiers:
        if t.get("max_amount") is None or int(total) <= int(t["max_amount"]):
            return t
    return tiers[-1]


async def snapshot(org: str, project_id: str, total_discount: int) -> dict:
    """Kebijakan yang berlaku SAAT permohonan lahir: mode, tabel tingkat, dan peran yang dibutuhkan untuk total ini."""
    pol = await policy.snapshot([KEY_MODE, KEY_TIERS], org_id=org, project_id=project_id)
    mode, tiers = pol[KEY_MODE]["value"], pol[KEY_TIERS]["value"]
    try:
        tiers = validate(tiers)
    except ValueError:       # nilai tersimpan rusak: jatuh ke bawaan, bukan menahan semua permohonan
        tiers = list(DEFAULT_TIERS)
    # kunci berisi titik diganti garis bawah: nama kolom ber-titik bermasalah di MongoDB (path `$set` ambigu).
    snap = {"mode": mode, "tiers": tiers, "total_discount": int(total_discount or 0),
            "policy": {k.replace(".", "_"): v for k, v in pol.items()}}
    if mode == BERTINGKAT:
        t = pick(tiers, snap["total_discount"])
        snap.update(tier_index=tiers.index(t) + 1, required_role=t["role"], required_rank=RANK[t["role"]])
    return snap


def is_tiered(snap) -> bool:
    return bool(snap) and snap.get("mode") == BERTINGKAT


def covers(snap, role: str) -> bool:
    """Apakah `role` berwenang pada tingkat yang dibutuhkan snapshot (legacy/satu_level: selalu True)."""
    return (not is_tiered(snap)) or rank_of(role) >= int(snap.get("required_rank") or 0)


def required_text(snap) -> str:
    r = snap.get("required_role")
    return (f"tingkat {snap.get('tier_index')} (total potongan Rp {int(snap.get('total_discount') or 0):,}) "
            f"memerlukan minimal {ROLE_LABEL.get(r, r)}").replace(",", ".")


def check_decider(snap, *, role: str, email: str, requester: str) -> None:
    """Lempar `Forbidden` bila `email`/`role` tidak boleh memutuskan permohonan ini.

    Legacy/`satu_level`: tidak ada pemeriksaan di sini (larangan lama pemohon-sendiri tetap di pemanggil, dengan
    pengecualian owner/super_admin). Bertingkat: tanpa pengecualian + pemeriksaan peran."""
    if not is_tiered(snap):
        return
    if requester and requester == email:
        raise Forbidden("Pemohon tidak boleh menyetujui permohonannya sendiri (persetujuan bertingkat) — minta "
                        f"{ROLE_LABEL.get(snap.get('required_role'), 'penyetuju lain')} atau yang lebih tinggi.")
    if not covers(snap, role):
        raise Forbidden(f"Peran Anda ({ROLE_LABEL.get(role, role)}) di bawah tingkat yang dibutuhkan: "
                        f"{required_text(snap)}.")


async def approver_rows(org: str, min_rank: int = 0) -> list:
    """[(email, role)] pemegang izin `pricing:approve` yang rank-nya cukup (untuk notifikasi)."""
    from db import db
    from rbac import can
    out = []
    async for u in db.users.find({"org_id": org, "is_active": {"$ne": False}}, {"_id": 0, "email": 1, "role": 1}):
        if u.get("email") and rank_of(u.get("role")) >= min_rank and await can(u.get("role"), "pricing", "approve"):
            out.append((u["email"], u.get("role")))
    return out[:30]
