"""Kebijakan akuntansi, pembatalan, dan siklus deal yang TERKONFIGURASI (docs/audit/12 — "sistem tidak kaku").

Dipisah dari `settings_store.py` (batas 800 baris) dan digabung ke `DEFAULTS` olehnya — registry tetap SATU.

Aturan setiap kunci di sini:
  * nilai bawaan = jawaban pemilik; opsi lain tetap bisa dipilih (enum → grup di `/api/reference`, aturan CFG-03);
  * `levels` = tingkat penimpaan yang sah: "org", "project", "cluster" (disimpan di `settings`) dan/atau "contract"
    (disimpan di dokumen kontrak, dibaca lewat `policy.resolve`);
  * `unavailable` = {opsi: alasan} untuk opsi yang BELUM dibangun — ditolak server dan dinonaktifkan di UI, sehingga
    tidak pernah ada pengaturan yang diam-diam tidak berpengaruh;
  * kunci baru HANYA didaftarkan bersama pembacanya (tidak ada pengaturan yatim).
"""


def _d(key, value, type_, label, help_, *, impact="", sensitive=True, minimum=None, maximum=None,
       src="SISTEM", ref_group=None, levels=("org", "project"), unavailable=None):
    options = []
    if ref_group:
        import reference as _ref
        options = list(_ref.values(ref_group))
    elif type_ == "enum":
        raise ValueError(f"Setting enum '{key}' harus punya ref_group")
    bad = [o for o in (unavailable or {}) if o not in options]
    if bad:
        raise ValueError(f"Setting '{key}': opsi belum-tersedia {bad} tidak ada di grup {ref_group}")
    if type_ == "enum" and value in (unavailable or {}):
        raise ValueError(f"Setting '{key}': nilai bawaan '{value}' tidak boleh berstatus belum tersedia")
    return {
        "key": key, "value": value, "type": type_, "group": "kebijakan", "label": label, "help": help_,
        "impact": impact, "sensitive": sensitive, "min": minimum, "max": maximum, "options": options,
        "source": src, "ref_group": ref_group, "levels": tuple(levels), "unavailable": dict(unavailable or {}),
    }


DEFAULTS_POLICY: dict = {d["key"]: d for d in [
    # ============ penerimaan titipan pada deal yang sudah batal (keputusan #10) ============
    _d("deposit.on_cancelled_deal", "bebas", "enum", "Penerimaan titipan pada deal yang sudah batal",
       "Uang kadang tetap masuk sesudah deal dibatalkan (pembeli transfer terlambat). Pengaturan ini menentukan apakah "
       "titipan semacam itu boleh dicatat. Titipan pada deal batal TIDAK PERNAH bisa dipakai menagih apa pun — hanya "
       "dikembalikan ke pembeli.",
       impact="'Tolak' membuat uang nyasar harus dicatat lewat jalur lain; 'wajib alasan + antrean refund' membuat tugas "
              "pengembalian dana bagi Keuangan setiap kali titipan masuk.",
       ref_group="deposit_cancelled_deal_policy"),

    # ============ W1-C — deal batal: akrual komisi / fee marketing / pajak (keputusan #11) ============
    # Dibaca saat pembatalan oleh `cancel_accrual_reversal` (via `deal_cancel_cleanup.close_deal_dependents`); nilai yang
    # berlaku DISNAPSHOT ke hasil penutupan (`policy_snapshot`). Berlaku ke depan: pembatalan lama tidak dijurnal ulang.
    _d("cancel.accrual_reversal.commission", "manual_keuangan", "enum",
       "Komisi sales yang sudah disetujui/dibayar pada deal batal",
       "Menentukan apa yang terjadi pada komisi sales berstatus DISETUJUI (akrual Dr 6-1100 / Cr 2-1600 sudah dijurnal) atau "
       "DIBAYAR saat deal dibatalkan. Komisi yang belum disetujui selalu dibatalkan otomatis.",
       impact="'Manual' = komisi ditandai + tugas & notifikasi Keuangan, TIDAK ada jurnal balik. 'Balik otomatis yang belum "
              "dibayar' = akrual dibalik dengan jurnal koreksi dan komisi menjadi 'dibatalkan'; yang sudah dibayar tetap "
              "tugas manual Keuangan (tagih balik ke penerima).",
       ref_group="cancel_accrual_reversal_mode",
       unavailable={"balik_otomatis_semua": "Menarik kembali komisi yang SUDAH DIBAYAR butuh akun piutang ke penerima komisi; "
                    "Bagan Akun standar tidak punya akun itu (1-1300 dikendalikan subledger AR pembeli, 1-1500 kas bon) dan "
                    "akun tidak boleh dikarang. Tetap manual oleh Keuangan sampai pemilik menetapkan akunnya."}),
    _d("cancel.accrual_reversal.marketing_fee", "manual_keuangan", "enum",
       "Fee marketing mitra yang sudah disetujui/dibayar pada deal batal",
       "Sama seperti komisi, untuk fee marketing agen/broker/referral (akrual Dr 6-1200 / Cr 2-1500 [+ Cr 2-1300 PPh dipotong]). "
       "Fee yang belum disetujui selalu dibatalkan otomatis.",
       impact="'Balik otomatis yang belum dibayar' hanya membalik fee yang belum dibayar SAMA SEKALI; fee yang sudah dibayar "
              "(sebagian/penuh) tetap tugas manual Keuangan.",
       ref_group="cancel_accrual_reversal_mode",
       unavailable={"balik_otomatis_semua": "Menarik kembali fee yang SUDAH DIBAYAR butuh akun piutang ke agen/mitra; Bagan Akun "
                    "standar tidak punya akun itu dan akun tidak boleh dikarang. Tetap manual oleh Keuangan."}),
    _d("cancel.accrual_reversal.tax", "manual_keuangan", "enum",
       "Pajak (PPN/PPh/BPHTB) yang sudah dilaporkan/disetor pada deal batal",
       "Catatan pajak baru dijurnal setelah DILAPORKAN (akrual) atau DISETOR; yang berstatus 'menunggu' tidak punya jurnal dan "
       "selalu dibatalkan otomatis. Yang sudah dilaporkan/disetor ke negara TIDAK PERNAH dibalik otomatis — butuh pembetulan "
       "SPT / permintaan kembali kelebihan bayar oleh Keuangan.",
       impact="Satu-satunya perilaku yang sah: ditandai + tugas & notifikasi Keuangan.",
       ref_group="cancel_accrual_reversal_mode",
       unavailable={
           "balik_otomatis_yang_belum_dibayar": "Akrual pajak baru dijurnal saat catatan DILAPORKAN ke negara; membaliknya adalah "
                                                "pembetulan SPT, bukan koreksi internal — tidak boleh otomatis.",
           "balik_otomatis_semua": "Pajak yang sudah disetor/dilaporkan tidak boleh dibalik otomatis (pembetulan SPT / restitusi "
                                   "dikerjakan Keuangan bersama konsultan pajak)."}),

    # ============ W1-C — deal batal: titipan biaya 2-1470 & invoice biaya terbuka (keputusan #12) ============
    _d("cancel.cost_deposit.policy", "refund_dan_batalkan_invoice", "enum",
       "Titipan biaya (2-1470) & invoice biaya terbuka pada deal batal",
       "Menentukan nasib titipan biaya customer (BPHTB/notaris yang sudah diterima tetapi belum disalurkan) dan invoice biaya "
       "yang masih terbuka ketika deal dibatalkan. Saldo titipan sudah dikurangi biaya yang benar-benar DISALURKAN ke pihak ketiga.",
       impact="'Refund + batalkan invoice' = saldo titipan menjadi utang refund pembeli (2-1460) dan invoice biaya terbuka "
              "dibatalkan, setelah disetujui Keuangan (bila diwajibkan). 'Manual dengan pengakuan' = pembatalan diblok sampai "
              "titipan/invoice diakui + catatan, tanpa jurnal. 'Hangus sebagian' = sebagian titipan (persentase di bawah) ditahan "
              "developer sebagai Pendapatan Lain-lain 4-1200, sisanya direfund.",
       ref_group="cancel_cost_deposit_policy"),
    _d("cancel.cost_deposit.forfeit_pct", 0, "pct",
       "Persentase titipan biaya yang hangus (untuk 'Hangus sebagian')",
       "Hanya dipakai bila kebijakan titipan biaya = 'Hangus sebagian'. Persentase dari saldo titipan biaya yang ditahan developer; "
       "sisanya dikembalikan ke pembeli. Usulan sistem 0% (bukan dokumen legal) — isi sesuai SPR.",
       impact="Titipan biaya adalah uang pembeli untuk pihak ketiga; menahannya mengikuti klausul SPR dan perlakuan pajak "
              "yang perlu dikonfirmasi pemilik/konsultan pajak.", minimum=0, maximum=100),
    _d("cancel.cost_deposit.requires_approval", True, "bool",
       "Refund titipan biaya wajib disetujui Keuangan",
       "Bila aktif, pembatalan hanya melahirkan PERMOHONAN refund titipan biaya; jurnal dan pembatalan invoice biaya baru berlaku "
       "setelah disetujui Keuangan (penyetuju harus orang lain dari pemohon). Bila nonaktif, permohonan langsung dijalankan "
       "saat pembatalan; pembayaran uang keluarnya tetap langkah Keuangan terpisah.",
       impact="Menonaktifkan membuat jurnal refund titipan lahir otomatis saat deal dibatalkan, tanpa pemeriksa kedua."),
]}
