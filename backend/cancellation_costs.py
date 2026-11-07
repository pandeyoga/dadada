"""Titipan biaya (2-1470) & invoice biaya pada PEMBATALAN KONTRAK (audit FN-03) — sisi AMAN saja.

Perlakuan uangnya (dikembalikan penuh ke pembeli? dipotong? disalurkan dulu ke notaris/BPN? invoice biaya
di-void?) adalah KEPUTUSAN PEMILIK — modul ini TIDAK menjurnal apa pun dan TIDAK mengubah saldo. Yang dikerjakan:

  * `holds()` menghitung apa yang masih menggantung (saldo titipan biaya + invoice biaya yang belum lunas/void)
    supaya layar & berkas pengajuan MENAMPILKANNYA;
  * `assert_ack()` memblokir PERSETUJUAN pembatalan selama masih ada yang menggantung, kecuali penyetuju secara
    sadar menyatakan `acknowledge_costs=true` disertai catatan penanganan ≥ 10 huruf (dicatat di keputusan & audit).
"""
MIN_NOTE = 10


async def holds(org: str, contract: dict) -> dict:
    """Saldo titipan biaya + invoice biaya terbuka milik kontrak ini (hanya membaca)."""
    import allin_engine as allin
    led = await allin.ledger(org, contract)
    open_inv = [{"number": i.get("number"), "status": i.get("status"), "outstanding": int(i.get("outstanding") or 0)}
                for i in led["invoices"] if i.get("status") not in ("void", "paid") and int(i.get("outstanding") or 0) > 0]
    titipan = max(0, int(led.get("titipan_balance") or 0))
    open_total = sum(i["outstanding"] for i in open_inv)
    return {"titipan_balance": titipan, "open_invoices": open_inv, "open_invoice_total": open_total,
            "has_holds": bool(titipan or open_inv)}


def _rp(v) -> str:
    return f"Rp {int(v):,}".replace(",", ".")


def assert_ack(hold: dict, ack: dict, actor: str, ts: str) -> dict:
    """Tolak persetujuan bila ada tanggungan biaya yang belum diakui. Kembalikan catatan pengakuan (atau None)."""
    if not (hold or {}).get("has_holds"):
        return None
    ack = ack or {}
    note = str(ack.get("reason") or "").strip()
    if ack.get("acknowledge") and len(note) >= MIN_NOTE:
        return {"acknowledged_by": actor, "at": ts, "note": note, "titipan_balance": hold["titipan_balance"],
                "open_invoice_total": hold["open_invoice_total"],
                "open_invoices": [i["number"] for i in hold["open_invoices"]]}
    parts = []
    if hold["titipan_balance"]:
        parts.append(f"saldo titipan biaya {_rp(hold['titipan_balance'])} (2-1470) belum disalurkan/dikembalikan")
    if hold["open_invoices"]:
        parts.append(f"invoice biaya terbuka {_rp(hold['open_invoice_total'])} "
                     f"({', '.join(str(i['number']) for i in hold['open_invoices'])})")
    if ack.get("acknowledge"):
        raise ValueError(f"Catatan penanganan biaya wajib diisi (minimal {MIN_NOTE} huruf) bila "
                         "acknowledge_costs=true.")
    raise ValueError("Pembatalan belum bisa disetujui: masih ada " + " dan ".join(parts) + ". Perlakuan uang biaya "
                     "ini keputusan pemilik dan TIDAK dijurnal otomatis oleh pembatalan. Selesaikan dulu, atau "
                     "setujui dengan acknowledge_costs=true + catatan penanganan (minimal "
                     f"{MIN_NOTE} huruf) — pengakuan ini dicatat pada keputusan dan audit log.")
