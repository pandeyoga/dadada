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
]}
