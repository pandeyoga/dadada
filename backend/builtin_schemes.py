"""SKEMA PEMBAYARAN BAWAAN (jaring terakhir Fase 53) — dipisah dari `contracts_engine.py`.

Termin bawaan menurut dokumen owner, dibaca dari Pusat Konfigurasi (`payment.cash.*`,
`payment.staged.*`, `payment.kpr.*`). Dipakai untuk (a) mengisi tabel `payment_schemes` saat
organisasi belum punya skema (`ensure_payment_scheme`, `seed_phase57`) dan (b) jaring terakhir
`contracts_engine.scheme_terms_spec`.

## KT-10 — konfigurasi tidak boleh hilang di jalan

Dulu baris termin bawaan hanya membawa KALIMAT (`due_rule`) dan penanda `event`. Semua bidang
terstruktur yang dipakai mesin (`due_mode`, `due_day`, `month_index`, `event_code`,
`grace_days`) tidak ikut, lalu `payment_scheme_engine.normalize_terms` MENIMPA kalimat dengan
bawaan "N hari setelah kontrak diaktifkan" dan menjadikan `event=False`. Hasilnya tanggal 7 /
toleransi tanggal 20 (`payment.staged.*`) dan "30 hari sejak bangunan 100% + perpanjangan 7 hari"
(`payment.cash.*`) tidak pernah berlaku, padahal kalimat itulah yang tercetak di SPR.
Sekarang bidang terstruktur dilewatkan sehingga mesin (jatuh tempo, toleransi, penanda
perkiraan) dan teks SPR sama-sama mengikuti konfigurasi. Rumus NOMINAL termin tidak berubah.
"""
from core_utils import new_id, now_iso
from db import db

import payment_scheme_engine as psx
import settings_store as cfg

# Perkiraan lama pembangunan (hari sejak kontrak aktif) untuk TANGGAL PERKIRAAN pelunasan cash
# keras. Teks SPR menyebut "maks N hari sejak pembangunan 100%" (konfigurasi); tanggal di jadwal
# tagihan tetap perkiraan lama (tanda `event_based`), supaya penagihan tidak menuduh terlambat
# sebelum bangunan selesai.
PERKIRAAN_BANGUN_HARI = 180


async def builtin_spec(org: str, scheme: str) -> dict:
    """Termin bawaan menurut dokumen owner (jaring terakhir Fase 53)."""
    if scheme == "cash_keras":
        dp = float(await cfg.get("payment.cash.dp_pct", org_id=org) or 80)
        days = int(await cfg.get("payment.cash.payoff_days_after_completion", org_id=org) or 30)
        grace = int(await cfg.get("payment.cash.payoff_grace_days", org_id=org) or 7)
        items = [
            {"label": f"DP tahap pertama {dp:g}%", "basis": "percent", "value": dp,
             "due_mode": "offset_days", "due_offset_days": 0},
            # Pelunasan menunggu peristiwa pembangunan 100%: batas `days` hari sejak itu,
            # ditambah perpanjangan `grace` hari. Tanggal di jadwal = perkiraan (tanda event).
            {"label": f"Pelunasan {100 - dp:g}%", "basis": "percent", "value": 100 - dp,
             "due_mode": "event", "event_code": "build_complete", "due_offset_days": days,
             "estimate_offset_days": PERKIRAAN_BANGUN_HARI, "grace_days": grace},
        ]
        return {"code": "cash_keras", "name": f"Cash keras (DP {dp:g}% + pelunasan)",
                "items": psx.normalize_terms(items)}
    if scheme == "cash_bertahap":
        dp = float(await cfg.get("payment.staged.dp_pct", org_id=org) or 80)
        n = int(await cfg.get("payment.staged.installment_count", org_id=org) or 6)
        day = int(await cfg.get("payment.staged.due_day", org_id=org) or 7)
        # `grace_day` = TANGGAL batas toleransi (mis. 20); mesin memakai toleransi dalam HARI
        # setelah tanggal jatuh tempo (20 − 7 = 13 hari).
        grace_date = int(await cfg.get("payment.staged.grace_day", org_id=org) or 20)
        grace_days = max(0, grace_date - day)
        sisa = 100 - dp
        items = [{"label": f"DP tahap pertama {dp:g}%", "basis": "percent", "value": dp,
                  "due_mode": "offset_days", "due_offset_days": 0}]
        for i in range(1, n + 1):
            items.append({"label": f"Cicilan {i}/{n}", "basis": "percent",
                          "value": round(sisa / n, 4), "due_mode": "monthly_day",
                          "due_day": day, "month_index": i, "grace_days": grace_days})
        return {"code": "cash_bertahap",
                "name": f"Cash bertahap (DP {dp:g}% + {n}× cicilan)",
                "items": psx.normalize_terms(items)}
    dp = float(await cfg.get("payment.kpr.dp_pct", org_id=org) or 0)
    items = []
    if dp > 0:
        items.append({"label": f"Uang muka (DP) {dp:g}%", "basis": "percent", "value": dp,
                      "due_mode": "offset_days", "due_offset_days": 0})
    items.append({"label": f"Pencairan KPR {100 - dp:g}%", "basis": "percent",
                  "value": 100 - dp, "due_mode": "event", "event_code": "akad_kredit",
                  "due_offset_days": 45, "payer": "bank"})
    return {"code": "kpr", "name": f"KPR (DP {dp:g}% + pencairan bank)",
            "items": psx.normalize_terms(items)}


async def ensure_payment_scheme(org: str, scheme: str) -> dict:
    """Jaring terakhir: sediakan skema bawaan untuk satu JENIS bila belum ada satu pun.

    Fase 57A mengubah aturan penting di sini: bila skema dengan kode ini SUDAH ADA, ia
    dikembalikan **apa adanya** dan tidak pernah ditimpa lagi. Sebelumnya setiap kali
    kontrak diaktifkan termin ditulis ulang dari termin bawaan — yang berarti setiap
    penyuntingan skema oleh pemakai akan hilang diam-diam pada aktivasi kontrak berikutnya.
    """
    doc = await db.payment_schemes.find_one({"org_id": org, "code": scheme}, {"_id": 0})
    if doc:
        return doc
    spec = await builtin_spec(org, scheme)
    ts = now_iso()
    doc = {"id": new_id(), "org_id": org, "code": scheme, "name": spec["name"],
           "kind": scheme, "items": psx.normalize_terms(spec["items"]),
           "active": True, "is_default": False, "applies_project_ids": [],
           "source": "DOC", "created_by": "system", "created_at": ts, "updated_at": ts}
    await db.payment_schemes.insert_one(dict(doc))
    doc.pop("_id", None)
    return doc


async def refresh_unedited(org: str) -> list:
    """Segarkan skema bawaan lama yang BELUM PERNAH disunting pemakai (KT-10).

    Skema bawaan yang tersimpan sebelum perbaikan ini membawa kalimat/penanda yang salah dan
    TIDAK akan pernah terbarui karena `ensure_payment_scheme`/`seed_phase57` tidak menimpa. Yang
    disegarkan hanya: sumber `DOC`, dibuat sistem/seed, tanpa `updated_by` (tak pernah disunting),
    dan belum dipakai kontrak yang sudah ada penerimaannya. Skema buatan/suntingan pemakai
    TIDAK disentuh. Idempoten.
    """
    hasil = []
    for kind in psx.KINDS:
        doc = await db.payment_schemes.find_one({"org_id": org, "code": kind}, {"_id": 0})
        if not doc or doc.get("source") != "DOC" or doc.get("created_by") not in ("system", "seed"):
            continue
        if doc.get("updated_by") or doc.get("history"):
            continue
        baru = psx.normalize_terms((await builtin_spec(org, kind))["items"])
        if baru == (doc.get("items") or []):
            continue
        if await psx._contracts_with_money(org, doc["id"]):  # noqa: SLF001
            continue
        await db.payment_schemes.update_one({"id": doc["id"]}, {"$set": {
            "items": baru, "updated_at": now_iso(), "refreshed_by": "seed:kt10"}})
        hasil.append(kind)
    return hasil
