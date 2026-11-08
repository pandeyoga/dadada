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
       src="SISTEM", ref_group=None, levels=("org", "project"), unavailable=None, validator=None, editor=None):
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
        "validator": validator, "editor": editor,   # nama (string) supaya spec tetap bisa diserialisasi ke UI
    }


def _tiers_validator(value):
    import discount_approval
    return discount_approval.validate(value)


# Validator khusus per kunci (dipanggil `settings_store.coerce` SETELAH validasi tipe umum). Impor malas: modul bisnis
# memuat `policy` → `settings_store`, jadi tidak boleh diimpor saat registry ini dimuat.
VALIDATORS = {"approval_tiers": _tiers_validator}


DEFAULTS_POLICY: dict = {d["key"]: d for d in [
    # ============ penerimaan titipan pada deal yang sudah batal (keputusan #10) ============
    _d("deposit.on_cancelled_deal", "bebas", "enum", "Penerimaan titipan pada deal yang sudah batal",
       "Uang kadang tetap masuk sesudah deal dibatalkan (pembeli transfer terlambat). Pengaturan ini menentukan apakah "
       "titipan semacam itu boleh dicatat. Titipan pada deal batal TIDAK PERNAH bisa dipakai menagih apa pun — hanya "
       "dikembalikan ke pembeli.",
       impact="'Tolak' membuat uang nyasar harus dicatat lewat jalur lain; 'wajib alasan + antrean refund' membuat tugas "
              "pengembalian dana bagi Keuangan setiap kali titipan masuk.",
       ref_group="deposit_cancelled_deal_policy"),
    # ============ ganti skema pembayaran SETELAH ada pembayaran (keputusan #9, IN-14) ============
    _d("payment.scheme_change.allocation", "manual_keuangan", "enum", "Alokasi pembayaran saat skema diganti sesudah ada pembayaran",
       "Bila skema deal/kontrak diganti setelah pembeli membayar (kuitansi kas/KPR), uang yang sudah masuk harus dipasang "
       "ke termin skema baru. Penerapan skema baru DITAHAN sampai Keuangan memastikan pemetaannya: 'manual' = Keuangan "
       "menyerahkan alokasi tiap kuitansi; 'urut termin tertua' / 'proporsional' = sistem menghitung dan Keuangan "
       "mengonfirmasi. Mengubah alokasi tidak mengubah kas atau jurnal; kuitansi lama tetap utuh sebagai jejak.",
       impact="Ganti skema pada deal yang sudah ada pembayaran tidak langsung berlaku — ia menunggu Keuangan.",
       ref_group="payment_scheme_change_allocation"),
    # ============ ganti skema KONTRAK ke KPR setelah kontrak dibuat (keputusan #14, FN-11) ============
    _d("contract.scheme_change_to_kpr", "tolak_buat_baru", "enum", "Ganti skema kontrak ke KPR setelah kontrak dibuat",
       "Skema KPR punya komponen khusus (biaya bank/BANK_FEE, asuransi, plafon) yang tidak ikut terbawa saat kontrak yang "
       "sudah ada diganti ke KPR. 'Tolak' = batalkan lalu buat kontrak baru berskema KPR; 'hitung ulang dengan persetujuan' = "
       "komponen KPR dihitung ulang dan harus disetujui Keuangan (amandemen skema biaya); 'izinkan manual' = perilaku lama.",
       impact="Tanpa komponen KPR, biaya bank dan asuransi tidak pernah tertagih ke pembeli.",
       ref_group="contract_scheme_change_to_kpr"),
    # ============ persetujuan diskon bertingkat menurut nilai (keputusan #8) ============
    _d("discount.approval_mode", "bertingkat", "enum", "Mode persetujuan diskon",
       "Siapa yang boleh menyetujui potongan yang SUDAH wajib persetujuan (ambang persen/nominal & mode per promo/kupon tidak berubah). "
       "'Bertingkat' memilih peran penyetuju menurut TOTAL potongan memakai tabel tingkat di bawah; 'satu level' = semua "
       "pemegang izin persetujuan harga setara (perilaku lama).",
       impact="Mode bertingkat melarang pemohon memutuskan permohonannya sendiri. Berlaku ke depan: permohonan yang "
              "sedang menunggu memakai kebijakan saat ia diajukan.",
       ref_group="discount_approval_mode"),
    _d("discount.approval_tiers", [{"max_amount": None, "role": "sales_manager"}], "list",
       "Tingkat persetujuan diskon (nominal → peran)",
       "Tabel tingkat: total potongan D disetujui oleh peran pada tingkat PERTAMA dengan D ≤ batas nominal; batas kosong = tak "
       "terbatas. Batas harus menaik dan tingkat terakhir tak terbatas. Urutan kewenangan: Manajer Penjualan < Manajer "
       "Keuangan < Owner (peran yang lebih tinggi boleh memutuskan tingkat di bawahnya). Bawaan = satu tingkat "
       "(perilaku lama) sampai pemilik mengisi angka.",
       impact="Mengisi batas mengubah siapa yang boleh menyetujui diskon berikutnya; permohonan yang menunggu tidak berubah.",
       validator="approval_tiers", editor="approval_tiers"),
]}
