"""Kebijakan penerimaan TITIPAN pada deal yang sudah batal (`deposit.on_cancelled_deal`, docs/audit/12 keputusan #10).

Titipan pada deal batal tidak pernah menjadi pendapatan atau pembayaran termin — satu-satunya nasibnya dikembalikan ke
pembeli. Yang diatur di sini hanya apakah ia boleh dicatat, dan bila boleh, apakah Keuangan otomatis diberi tugas refund.
"""
import policy
from core_utils import now_iso
from deal_state import deal_of, is_cancelled

KEY = "deposit.on_cancelled_deal"
ANTREAN = "wajib_alasan_dan_antrean_refund"
MIN_ALASAN = 10


async def gate(org: str, deal_id: str, note: str):
    """None bila deal hidup. Untuk deal batal: lempar ValueError bila ditolak/tanpa alasan; kembalikan konteks bila boleh."""
    deal = await deal_of(org, deal_id)
    if not is_cancelled(deal):
        return None
    mode = await policy.resolve(KEY, org_id=org, project_id=deal.get("project_id"))
    if mode == "tolak":
        raise ValueError("Deal ini sudah DIBATALKAN dan kebijakan (Pusat Konfigurasi → Kebijakan → "
                         "'Penerimaan titipan pada deal yang sudah batal') menolak penerimaan titipan. "
                         "Catat uang masuk lewat jalur penerimaan lain dan hubungi Keuangan.")
    if mode == ANTREAN and len((note or "").strip()) < MIN_ALASAN:
        raise ValueError(f"Deal ini sudah DIBATALKAN — alasan penerimaan titipan wajib diisi (minimal {MIN_ALASAN} karakter), "
                         "mis. 'pembeli transfer terlambat tanggal …'.")
    return {"mode": mode, "deal": deal}


async def follow_up(org: str, ctx, amount: int, note: str) -> bool:
    """Setelah titipan tercatat: bila kebijakan = antrean refund, buat tugas + notifikasi Keuangan. True bila dibuat."""
    if not ctx or ctx["mode"] != ANTREAN:
        return False
    from engine import auto_create_task
    from finance_engine import notify_finance
    deal = ctx["deal"]
    did = deal.get("id")
    body = (f"Titipan Rp {int(amount):,} diterima pada deal unit {deal.get('unit_code') or '-'} yang sudah BATAL "
            f"(alasan: {(note or '').strip()}). Titipan ini tidak bisa menagih apa pun — proses pengembaliannya ke pembeli.")
    await notify_finance(org, "Titipan masuk pada deal batal — perlu refund", body, "finance", "deal", did)
    await auto_create_task(source_event=f"deposit_batal:{did}:{now_iso()}",
                           title=f"Refund titipan deal batal {deal.get('unit_code') or '-'}: Rp {int(amount):,}",
                           type="todo", related_entity_type="deal", related_entity_id=did, assigned_to=None,
                           description=body, priority="high", org_id=org)
    return True
