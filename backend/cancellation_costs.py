"""Titipan biaya (2-1470) & invoice biaya pada PEMBATALAN KONTRAK (audit FN-03) — sisi AMAN saja.

Perlakuan uangnya (dikembalikan penuh ke pembeli? dipotong? disalurkan dulu ke notaris/BPN? invoice biaya
di-void?) adalah KEPUTUSAN PEMILIK — modul ini TIDAK menjurnal apa pun dan TIDAK mengubah saldo. Keputusan itu kini
KEBIJAKAN TERKONFIGURASI (`cancel.cost_deposit.policy`, W1-C #12): bawaan `refund_dan_batalkan_invoice` ditangani modul
`cancel_cost_settlement` (permohonan refund + pembatalan invoice); `manual_dengan_pengakuan` = gerbang pengakuan di bawah
(perilaku lama, tidak berubah). Yang dikerjakan modul ini:

  * `holds()` menghitung apa yang masih menggantung (saldo titipan biaya + invoice biaya yang belum lunas/void)
    supaya layar & berkas pengajuan MENAMPILKANNYA;
  * `assert_ack()` memblokir PERSETUJUAN pembatalan selama masih ada yang menggantung, kecuali penyetuju secara
    sadar menyatakan `acknowledge_costs=true` disertai catatan penanganan ≥ 10 huruf (dicatat di keputusan & audit).
    Gerbang yang SAMA dipakai jalur formal (`cancellation_engine.decide`) dan jalur satu-klik (`deal_cancel.cancel`);
  * `assert_movable()` menahan uang biaya BERGERAK sesudah deal batal (bayar invoice biaya / salurkan titipan) —
    sisa FN-03: dulu masih 200 sesudah batal. Hanya pemegang `finance:approve` dengan alasan ≥ 10 huruf yang boleh
    menerobos (`override_of()`); tidak ada jurnal baru di sini.
"""
MIN_NOTE = 10
KEY_POLICY = "cancel.cost_deposit.policy"                      # W1-C #12 (docs/audit/12)
POLICY_HANDLING = ("refund_dan_batalkan_invoice", "hangus_sebagian")   # kebijakan yang MENANGANI titipan/invoice sendiri
POLICY_MANUAL = "manual_dengan_pengakuan"                      # perilaku lama: gerbang pengakuan + catatan


async def holds(org: str, contract: dict, project_id: str = None) -> dict:
    """Saldo titipan biaya + invoice biaya terbuka milik kontrak ini (hanya membaca).

    W1-C #12: memuat juga kebijakan yang berlaku (`policy`, `handled_by_policy`). Bila kebijakan MENANGANI titipan/invoice itu
    (refund + batalkan invoice / hangus sebagian), pembatalan tidak lagi diblok gerbang pengakuan — penutup deal batal
    (`cancel_cost_settlement`) melahirkan permohonan refund. Kebijakan `manual_dengan_pengakuan` = gerbang lama persis."""
    import allin_engine as allin
    import policy
    led = await allin.ledger(org, contract)
    open_inv = [{"id": i.get("id"), "number": i.get("number"), "status": i.get("status"),
                 "outstanding": int(i.get("outstanding") or 0)}
                for i in led["invoices"] if i.get("status") not in ("void", "paid", "cancelled") and int(i.get("outstanding") or 0) > 0]
    titipan = max(0, int(led.get("titipan_balance") or 0))
    open_total = sum(i["outstanding"] for i in open_inv)
    mode = await policy.resolve(KEY_POLICY, org_id=org, project_id=project_id or contract.get("project_id"))
    has = bool(titipan or open_inv)
    return {"titipan_balance": titipan, "open_invoices": open_inv, "open_invoice_total": open_total,
            "has_holds": has, "policy": mode, "handled_by_policy": has and mode in POLICY_HANDLING}


async def holds_of_deal(org: str, deal: dict, project_id: str = None) -> dict:
    """`holds()` untuk sebuah DEAL (jalur batal satu-klik): memakai "kontrak semu" dari deal, sehingga invoice/kuitansi
    biaya yang lahir saat booking (belum punya kontrak) ikut terbaca — sama dengan `allin_engine._scope`."""
    import allin_engine as allin
    return await holds(org, await allin.deal_as_contract(org, deal), project_id or deal.get("project_id"))


def _rp(v) -> str:
    return f"Rp {int(v):,}".replace(",", ".")


def assert_ack(hold: dict, ack: dict, actor: str, ts: str, aksi: str = "disetujui") -> dict:
    """Tolak persetujuan bila ada tanggungan biaya yang belum diakui. Kembalikan catatan pengakuan (atau None).
    Bila kebijakan MENANGANI tanggungan itu (`hold["handled_by_policy"]`), tidak ada yang ditolak.
    `aksi` hanya mengubah kata kerja pada pesan ("disetujui" untuk jalur formal, "dilakukan" untuk satu-klik)."""
    if not (hold or {}).get("has_holds"):
        return None
    ack = ack or {}
    note = str(ack.get("reason") or "").strip()
    if ack.get("acknowledge") and len(note) >= MIN_NOTE:
        return {"acknowledged_by": actor, "at": ts, "note": note, "titipan_balance": hold["titipan_balance"],
                "open_invoice_total": hold["open_invoice_total"],
                "open_invoices": [i["number"] for i in hold["open_invoices"]],
                **({"handled_by_policy": hold["policy"]} if hold.get("handled_by_policy") else {})}
    if hold.get("handled_by_policy"):
        # W1-C #12: kebijakan menangani titipan/invoice biaya (permohonan refund lahir di penutup deal batal) → tidak diblok.
        return {"handled_by_policy": hold["policy"], "at": ts, "by": actor, "titipan_balance": hold["titipan_balance"],
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
    lanjut = "setujui" if aksi == "disetujui" else "lanjutkan"
    raise ValueError(f"Pembatalan belum bisa {aksi}: masih ada " + " dan ".join(parts) + ". Perlakuan uang biaya "
                     "ini keputusan pemilik dan TIDAK dijurnal otomatis oleh pembatalan. Selesaikan dulu, atau "
                     f"{lanjut} dengan acknowledge_costs=true + catatan penanganan (minimal "
                     f"{MIN_NOTE} huruf) — pengakuan ini dicatat pada keputusan dan audit log.")


# ------------------------------------------------------------------ uang biaya SESUDAH batal (sisa FN-03)
async def closed_reason(org: str, deal_id: str = None, contract_id: str = None) -> str:
    """Alasan deal/kontrak ini sudah "tutup" (batal / kedaluwarsa) atau None. Predikat batal = `deal_state`."""
    import deal_state as ds
    from db import db
    if deal_id:
        deal = await ds.deal_of(org, deal_id)
        if deal and ds.is_cancelled(deal):
            return "DIBATALKAN"
        if deal and deal.get("status") == "expired":
            return "KEDALUWARSA (reservasi dilepas)"
    if contract_id:
        c = await db.contracts.find_one({"id": contract_id, "org_id": org}, {"_id": 0, "state": 1, "cancellation_id": 1})
        if c and (c.get("state") == "cancelled" or c.get("cancellation_id")):
            return "DIBATALKAN"
    return None


def override_of(user: dict, allowed: bool, requested: bool, reason: str) -> dict:
    """Terobosan SADAR atas gerbang uang-biaya-setelah-batal. `allowed` = pemegang `finance:approve` (diperiksa
    pemanggil/router). Mengembalikan catatan terobosan (atau None bila tidak diminta); galat 403/400 oleh router."""
    if not requested:
        return None
    if not allowed:
        raise PermissionError("Menerobos larangan uang biaya sesudah pembatalan hanya untuk pemegang izin "
                              "Keuangan (finance:approve).")
    note = str(reason or "").strip()
    if len(note) < MIN_NOTE:
        raise ValueError(f"Alasan terobosan wajib diisi (minimal {MIN_NOTE} huruf) — dicatat pada kuitansi/penyaluran "
                         "dan audit log.")
    from core_utils import now_iso
    return {"by": (user or {}).get("email"), "reason": note, "at": now_iso()}


async def assert_movable(org: str, *, deal_id: str = None, contract_id: str = None, what: str,
                         override: dict = None) -> dict:
    """Tolak menggerakkan uang biaya pada deal/kontrak yang sudah batal. Mengembalikan catatan terobosan bila
    `override` sah dipakai (dicatat pemanggil pada dokumen yang lahir), selain itu None. TIDAK menjurnal apa pun."""
    why = await closed_reason(org, deal_id, contract_id)
    if not why:
        return None
    if override:
        return override
    raise ValueError(
        f"Deal ini sudah {why} — {what} tidak boleh dilakukan: uang biaya (titipan 2-1470 / invoice biaya) pada "
        "penjualan yang batal adalah keputusan pemilik dan tidak boleh bergerak diam-diam. Bila memang harus "
        "(mis. menyalurkan ke notaris yang sudah bekerja atau mengembalikan ke pembeli), pemegang izin Keuangan "
        f"mengulang dengan override_cancelled=true + override_reason (minimal {MIN_NOTE} huruf); dicatat di audit log.")
