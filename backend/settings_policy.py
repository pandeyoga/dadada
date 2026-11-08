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
       src="SISTEM", ref_group=None, levels=("org", "project"), unavailable=None, validator=None, editor=None,
       group="kebijakan", writer=None):
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
        "key": key, "value": value, "type": type_, "group": group, "label": label, "help": help_,
        "impact": impact, "sensitive": sensitive, "min": minimum, "max": maximum, "options": options,
        "source": src, "ref_group": ref_group, "levels": tuple(levels), "unavailable": dict(unavailable or {}),
        "validator": validator, "editor": editor,   # nama (string) supaya spec tetap bisa diserialisasi ke UI
        "writer": tuple(writer) if writer else None,   # (resource, aksi) pemegang izin MENGUBAH kunci ini; kosong = settings:manage
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
    # ============ reservasi kedaluwarsa, booking fee sudah dibayar (keputusan #13) ============
    _d("reservation.expiry.paid_booking_fee", "perpanjang", "enum", "Reservasi kedaluwarsa, booking fee sudah dibayar",
       "Masa keep unit habis padahal pembeli sudah membayar booking fee (penilaian dari kuitansi booking fee yang tidak "
       "void, bukan dari penanda di deal). Reservasi TANPA booking fee terbayar tetap kedaluwarsa dan unitnya dilepas. "
       "Perpanjang: unit tidak dilepas, masa keep ditambah sebanyak 'Lama perpanjangan' (sampai batas 'Maksimum "
       "perpanjangan'); sesudah batas, sistem membuat tugas tindak lanjut sales & Keuangan dan unit tetap ditahan sampai "
       "manusia memutuskan (batalkan lewat jalur batal yang ada). Antrean refund: unit dilepas, uang tetap tercatat "
       "sebagai titipan 2-1450 dan Keuangan diberi tugas mengembalikannya. Hangus: unit dilepas dan booking fee diakui "
       "hangus (pendapatan lain-lain) lewat jalur hangus yang sudah ada.",
       impact="'Hangus' memindahkan uang pembeli menjadi pendapatan tanpa keputusan manusia pada saat itu — pastikan SPR "
              "memuat klausulnya. 'Perpanjang' menahan unit lebih lama; bila perpanjangan habis, unit tetap ditahan "
              "sampai ada yang membatalkan.",
       ref_group="reservation_expiry_paid_fee_policy"),
    _d("reservation.expiry.extend_days", 7, "int", "Lama perpanjangan reservasi (hari)",
       "Berlaku bila kebijakan = Perpanjang. Masa keep ditambah sebanyak ini tiap kali jatuh tempo (dihitung dari saat "
       "jatuh tempo diproses bila sudah lewat, supaya perpanjangan tidak habis sekaligus).",
       impact="Terlalu panjang = unit mati bagi pembeli lain; terlalu pendek = tugas tindak lanjut terlalu sering.",
       minimum=1, maximum=90),
    _d("reservation.expiry.max_extensions", 2, "int", "Maksimum perpanjangan reservasi (kali)",
       "Berlaku bila kebijakan = Perpanjang. Setelah sebanyak ini perpanjangan, unit TIDAK dilepas diam-diam: sistem "
       "membuat tugas tindak lanjut sales & Keuangan (sekali) dan unit tetap ditahan sampai manusia memutuskan. 0 = "
       "tidak pernah memperpanjang (langsung tugas tindak lanjut).",
       impact="Perpanjangan tanpa batas membuat unit 'mati' selamanya; batas ini memaksa ada keputusan manusia.",
       minimum=0, maximum=12),

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


# ===== W2-A — Master Pajak (keputusan #15) + PPN terkonfigurasi (keputusan #1) =====
# Satu sumber tarif/dasar pajak yang boleh ditimpa per proyek; dibaca LEWAT `tax_master.resolve(project_id)` oleh perhitungan
# pajak AR/penawaran, komponen biaya BPHTB/BANK_FEE, Faktur Pajak, dan dasar komisi. Dokumen `finance_configs` lama hanya
# dimigrasikan ke sini (sekali, idempoten) lalu tidak dibaca lagi. Mengubah tarif/mode berlaku KE DEPAN (lihat `tax_master`).
# Hanya pemegang `finance:manage` (Manajer Keuangan, owner, super admin) yang boleh mengubah — staf Keuangan tidak.
_PAJAK_WRITER = ("finance", "manage")
_PAJAK = dict(group="master_pajak", writer=_PAJAK_WRITER)

DEFAULTS_W2A: dict = {d["key"]: d for d in [
    _d("tax.ppn.mode", "eksklusif", "enum", "Perlakuan harga jual terhadap PPN",
       "Menentukan cara harga jual diperlakukan terhadap PPN. EKSKLUSIF (bawaan = perilaku sistem sebelum pengaturan ini ada): "
       "harga belum termasuk PPN — DPP = harga, PPN = tarif × DPP; dicatat sebagai catatan pajak & Faktur Pajak dan TIDAK "
       "ditambahkan ke jadwal tagihan pembeli (tagihan tetap = harga). INKLUSIF: harga sudah termasuk PPN — DPP = harga × "
       "100/(100+tarif), PPN = harga − DPP; tagihan pembeli tetap = harga. BEBAS PPN: tarif efektif 0 (mis. rumah subsidi) — "
       "tanpa catatan PPN dan tanpa Faktur Pajak. Penawaran, deal, dan jadwal tagihan yang SUDAH ada tetap memakai mode saat ia lahir.",
       impact="Mengubah angka PPN pada penawaran, catatan pajak, Faktur Pajak, dan dasar komisi 'nilai bersih' untuk transaksi BARU. "
              "Akrual PPN tetap dibukukan ke Beban Pajak 6-1400 / Utang Pajak 2-1300 (pemisahan akun PPN Keluaran menunggu keputusan GL-04).",
       ref_group="ppn_mode", **_PAJAK),
    _d("tax.ppn.rate", 12.0, "pct", "Tarif PPN (%)",
       "Tarif PPN nominal. Dipakai semua perhitungan PPN penjualan (kecuali mode Bebas PPN, yang berlaku 0%) dan estimasi PPN "
       "masukan dari tagihan vendor. Konfirmasikan ke konsultan pajak.",
       impact="Mengubah PPN untuk transaksi BARU; catatan pajak & Faktur Pajak yang sudah terbit tidak dihitung ulang.",
       minimum=0, maximum=100, **_PAJAK),
    _d("tax.master.npoptkp", 80_000_000, "money", "NPOPTKP BPHTB (Rp)",
       "Nilai Perolehan Objek Pajak Tidak Kena Pajak untuk BPHTB — ditetapkan Perda tiap daerah, jadi layak ditimpa per proyek. "
       "Dibaca komponen biaya BPHTB (skema all-in), penawaran, dan catatan pajak BPHTB.",
       impact="Mengubah nominal BPHTB pada reservasi/penawaran BARU; kontrak yang sudah terbit (snapshot) tidak berubah.",
       minimum=0, maximum=1_000_000_000_000, **_PAJAK),
    _d("tax.master.bphtb_rate", 5.0, "pct", "Tarif BPHTB (%)",
       "SATU sumber tarif BPHTB: komponen biaya BPHTB (rumus tarif × (NPOP − NPOPTKP)) dan catatan pajak BPHTB sama-sama membaca "
       "ini (dulu komponen punya persennya sendiri).",
       impact="Mengubah nominal BPHTB pada reservasi/penawaran BARU.", minimum=0, maximum=100, **_PAJAK),
    _d("tax.master.pph_final_rate", 2.5, "pct", "Tarif PPh Final penjual (%)",
       "PPh Final atas pengalihan hak tanah/bangunan (bawaan 2,5%). Timpa per proyek untuk proyek rumah sederhana/rusun sederhana "
       "(tarif lebih rendah menurut peraturan) — konfirmasikan ke konsultan pajak.",
       impact="Mengubah nominal catatan PPh Final pada jadwal tagihan yang dibuat/disusun ulang SETELAH perubahan.",
       minimum=0, maximum=100, **_PAJAK),
    _d("tax.master.njop_per_m2", 0, "money", "NJOP tanah per m² (Rp)",
       "Dasar BPHTB pembanding: 0 = tidak dipakai (NPOP = harga transaksi, seperti sebelumnya). Bila > 0: NPOP = nilai TERBESAR antara "
       "harga transaksi dan NJOP per m² × luas tanah unit (luas tanah unit harus terisi; bila kosong NJOP tidak diterapkan). "
       "NJOP bangunan belum dimodelkan.",
       impact="Menaikkan dasar BPHTB (komponen biaya & catatan pajak) bila NJOP lebih tinggi dari harga.",
       minimum=0, maximum=1_000_000_000, **_PAJAK),
    _d("tax.master.bank_fee_pct_of_plafon", 0.0, "pct", "Biaya bank (BANK_FEE) sebagai % dari plafon KPR",
       "0 = tidak dipakai (komponen BANK_FEE tetap menghitung persen × harga, seperti sebelumnya). Bila > 0 dan plafon KPR diketahui, "
       "BANK_FEE = persen ini × plafon: pada penawaran/reservasi plafon = porsi bank skema pembayaran KPR terpilih (cadangan: simulasi KPR "
       "lengkap), pada amandemen skema biaya = plafon SP3K kontrak; bila plafon belum diketahui komponen memakai rumus aslinya. Tagihan "
       "biaya yang sudah terbit tidak dihitung ulang otomatis — pakai amandemen skema biaya.",
       impact="Mengubah nominal BANK_FEE pada komponen biaya yang dihitung/diamandemen SETELAH perubahan.",
       minimum=0, maximum=100, **_PAJAK),
]}
DEFAULTS_POLICY.update(DEFAULTS_W2A)


# ===== W2-B — BPHTB dipilih PER KONTRAK (keputusan #3) =====
# Siapa menanggung BPHTB: pembeli (ditagih lewat invoice biaya → titipan 2-1470), developer (tidak ditagih; beban developer lewat
# jalur `developer_borne` yang sudah ada: Dr 6-1700 / Cr 2-1100 saat dicatat), atau dibagi menurut persen. SATU fungsi pembagi
# (`bphtb_policy.split_amount`) dibaca semua titik hitung. Tingkat penimpaan: organisasi, proyek, dan KONTRAK (disimpan di
# dokumen kontrak, ditulis `routers/contract_policy_router.py`). Perubahan berlaku KE DEPAN: komponen biaya sebuah kontrak adalah
# snapshot saat ia lahir; mengganti pengaturan organisasi/proyek tidak mengubah kontrak yang sudah ada.
# Hanya pemegang `finance:manage` (Manajer Keuangan, owner, super admin) yang boleh mengubah — di semua tingkat.
_BPHTB = dict(levels=("org", "project", "contract"), writer=("finance", "manage"))

DEFAULTS_W2B: dict = {d["key"]: d for d in [
    _d("bphtb.borne_by", "pembeli", "enum", "Penanggung BPHTB",
       "Siapa yang menanggung BPHTB atas penjualan unit. PEMBELI (bawaan = jawaban pemilik): BPHTB ditagih ke pembeli lewat invoice "
       "biaya dan ditampung sebagai titipan biaya 2-1470 (bukan pendapatan), lalu disalurkan ke notaris/BPN. DEVELOPER: BPHTB tidak "
       "ditagihkan ke pembeli dan menjadi beban developer (komponen 'ditanggung developer': dicatat lewat 'Catat beban' — Dr Beban "
       "Penjualan 6-1700 / Cr Utang Usaha 2-1100, akun mengikuti master komponen). DIBAGI: pembeli menanggung (100 − porsi developer)% "
       "dan developer menanggung porsi developer% (kunci di bawah). Selama BELUM ada pilihan eksplisit di tingkat organisasi/proyek/"
       "kontrak (nilai bawaan), perlakuan BPHTB mengikuti skema all-in yang dipilih sales saat reservasi (mis. 'Exclude' = pembeli, "
       "'All-in Standar' = developer) — persis perilaku sebelum pengaturan ini ada; begitu dipilih eksplisit, pilihan itu menang atas skema. "
       "Bisa ditimpa per proyek dan per KONTRAK (Kontrak › Kebijakan kontrak) selama uang BPHTB belum bergerak.",
       impact="Berlaku untuk penawaran/reservasi BARU; kontrak yang sudah ada tidak berubah diam-diam. Mengubah penanggung pada kontrak "
              "membatalkan invoice biaya yang belum dibayar dan menerbitkannya ulang; ditolak bila uang BPHTB sudah bergerak "
              "(kuitansi biaya, penyaluran, beban developer, catatan pajak dilaporkan/disetor).",
       ref_group="bphtb_borne_by", **_BPHTB),
    _d("bphtb.developer_share_pct", 50, "pct", "Porsi BPHTB ditanggung developer (%) — untuk 'Dibagi'",
       "Hanya dipakai bila penanggung BPHTB = Dibagi: developer menanggung persen ini dari BPHTB, pembeli sisanya (dibulatkan ke Rupiah; "
       "sisa pembulatan masuk bagian pembeli). Usulan sistem 50% (bukan dokumen legal) — isi sesuai kesepakatan/SPR.",
       impact="Mengubah pembagian BPHTB pada penawaran/reservasi BARU (atau pada kontrak yang ditimpa 'Dibagi').",
       minimum=0, maximum=100, **_BPHTB),
]}
DEFAULTS_POLICY.update(DEFAULTS_W2B)
