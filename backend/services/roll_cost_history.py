"""services/roll_cost_history.py — JEJAK setiap perubahan HPP satu roll.

KENAPA ADA (2026-06, sesudah `INV-GL-DRIFT` ditutup)
===================================================
Selisih Rp 900.000 di buku CV Kanda Suka bertahan berbulan-bulan karena nilai sebuah
roll BISA BERUBAH tanpa meninggalkan jejak siapa pun: migrasi startup mengisi ulang HPP
yang sengaja nol, jembatan retur antar-PT menilai ulang roll, voucher biaya masuk
menambah HPP. Tidak satu pun tercatat, jadi satu-satunya cara mengetahui "kenapa roll
ini bernilai Rp 90.000" adalah membaca kode dan menebak.

Modul ini membuat kenaikan/penurunan nilai persediaan **mustahil diam-diam**: setiap
penulis HPP roll memanggil `record()` dengan nilai lama, nilai baru, ALASAN, aktor, dan
dokumen sumbernya. Riwayatnya dibaca layar detail roll dan ikut ditempelkan sebagai
bukti pada tuduhan selisih persediaan.

Aturan: jejak ini BUKAN jurnal. Ia menjawab "siapa & atas dasar apa", bukan
menggantikan `journal_entries` — kalau perubahan nilai seharusnya berjurnal, yang
menegakkannya tetap rekonsiliasi GL 1-1300 vs subledger.
"""
from typing import Any, Dict, List, Optional

from core_utils import new_id, now_iso
from db import db

COLLECTION = "roll_cost_history"

#: Alasan yang dikenali + kalimat manusianya. Sengaja daftar tertutup: "alasan bebas"
#: berujung pada catatan seperti "update" yang tidak menjelaskan apa pun setahun lagi.
REASONS: Dict[str, str] = {
    "interco_return_revalue": "Dinilai ulang ke harga perolehan penjual (retur antar-PT)",
    "interco_purchase_revalue": "Dinilai ulang ke harga beli internal (pembelian antar-PT)",
    "landed_cost_allocation": "Biaya masuk (landed cost) dialokasikan ke roll",
    "startup_backfill": "Migrasi startup mengisi HPP roll yang belum pernah dinilai",
    # T8 DIBAYAR (2026-06c): `cycle_count_adjustment` DIHAPUS dari registry — tidak
    # ada satu pun penulisnya. Penyesuaian stock opname mengubah KUANTITAS roll
    # (`apply_cycle_count_adjustment`), bukan HPP/unit-nya, jadi tak ada perubahan
    # nilai per unit untuk dicatat di sini. Nama yang hidup tanpa penulis membuat
    # sesi berikutnya percaya jejaknya sudah ada (drift kelas D2).
}


async def record(roll: Dict[str, Any], new_unit_cost: float, reason: str,
                 actor: str = "sistem", ref_type: str = "", ref_id: str = "",
                 ref_number: str = "", note: str = "") -> Optional[Dict[str, Any]]:
    """Catat SATU perubahan HPP. Nilai yang tidak berubah tidak dicatat (hindari bising).

    `roll` = dokumen roll SEBELUM diperbarui (butuh `id`, `roll_no`, `unit_cost`).
    """
    # Nilai LAMA dibaca APA ADANYA dari `unit_cost` bila fieldnya ada — termasuk 0.
    # Sengaja BUKAN `unit_cost or base_unit_cost`: roll ber-`unit_cost` 0 yang dinilai
    # ulang ke Rp 90.000 memang BERUBAH nilainya, dan justru perubahan seperti itulah
    # yang dulu tidak terlihat siapa pun (akar selisih buku CV Kanda Suka).
    raw = roll.get("unit_cost")
    old = float(raw if raw is not None else (roll.get("base_unit_cost") or 0))
    new = round(float(new_unit_cost or 0), 4)
    if abs(new - old) < 0.005:
        return None
    length = float(roll.get("length_remaining") or 0)
    entry = {
        "id": new_id("rch"),
        "roll_id": roll.get("id", ""),
        "roll_no": roll.get("roll_no", ""),
        "entity_id": roll.get("owner_entity_id") or roll.get("entity_id", ""),
        "at": now_iso(),
        "actor": actor or "sistem",
        "reason": reason,
        "reason_label": REASONS.get(reason, reason),
        "note": note,
        "old_unit_cost": round(old, 4),
        "new_unit_cost": new,
        "delta_unit_cost": round(new - old, 4),
        # Selisih NILAI roll — angka inilah yang harus punya pasangan jurnal bila
        # perubahannya menaikkan/menurunkan nilai persediaan.
        "delta_value": round((new - old) * length, 2),
        "length_remaining": length,
        "direction": "naik" if new > old else "turun",
        "ref_type": ref_type,
        "ref_id": ref_id,
        "ref_number": ref_number,
    }
    await db[COLLECTION].insert_one(dict(entry))
    return entry


async def history(roll_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Riwayat satu roll, TERBARU dulu."""
    return await (db[COLLECTION].find({"roll_id": roll_id}, {"_id": 0})
                  .sort([("at", -1)]).limit(max(1, limit)).to_list(max(1, limit)))
