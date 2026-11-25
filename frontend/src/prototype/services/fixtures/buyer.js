const DAY = 86400000;
const iso = (t) => new Date(t).toISOString();

export function buildBuyer(now) {
  const dpDue = (n) => `${2026 + (n > 3 ? 1 : 0)}-${["", "", "", "12", "01", "02"][n]}-10`;
  return {
    journey: {
      steps: ["Booking", "Cek kredit", "Bangun", "Pengajuan KPR", "Akad", "Serah terima"],
      current: 2,
      progress: 72,
    },
    installments: [
      { id: "booking", label: "Biaya booking", amount: 500000, dueDate: iso(now - 150 * DAY), status: "paid", paidAt: iso(now - 152 * DAY), receiptId: "rc-booking" },
      { id: "dp-1", label: "Uang muka 1 dari 5", amount: 1000000, dueDate: iso(now - 90 * DAY), status: "paid", paidAt: iso(now - 92 * DAY), receiptId: "rc-dp-1" },
      { id: "dp-2", label: "Uang muka 2 dari 5", amount: 1000000, dueDate: iso(now - 45 * DAY), status: "paid", paidAt: iso(now - 47 * DAY), receiptId: "rc-dp-2" },
      { id: "dp-3", label: "Uang muka 3 dari 5", amount: 1000000, dueDate: "2026-12-10", status: "unpaid" },
      { id: "dp-4", label: "Uang muka 4 dari 5", amount: 1000000, dueDate: dpDue(4), status: "unpaid" },
      { id: "dp-5", label: "Uang muka 5 dari 5", amount: 1000000, dueDate: dpDue(5), status: "unpaid" },
    ],
    progressPhotos: [
      { stage: "Pembersihan lahan", date: iso(now - 140 * DAY), caption: "Lahan Blok C diratakan dan dipatok.", img: "progress/lahan" },
      { stage: "Pondasi", date: iso(now - 115 * DAY), caption: "Pondasi batu kali selesai dicor.", img: "progress/pondasi" },
      { stage: "Dinding", date: iso(now - 85 * DAY), caption: "Pasangan bata setinggi plafon.", img: "progress/dinding" },
      { stage: "Atap", date: iso(now - 55 * DAY), caption: "Rangka baja ringan dan genteng terpasang.", img: "progress/atap" },
      { stage: "Plester dan lantai", date: iso(now - 25 * DAY), caption: "Plester dinding dan keramik lantai 40x40.", img: "progress/plester" },
      { stage: "Pintu, jendela, dan listrik", date: iso(now - 6 * DAY), caption: "Kusen terpasang, instalasi listrik 1.300 VA.", img: "progress/kusen" },
    ],
    kpr: { status: "menunggu rumah siap", principal: 161000000, rate: 5, tenorYears: 20, monthly: 1062500, note: "Dibayar ke bank setelah akad", product: "KPR Subsidi · Bank BTN" },
    documents: [
      { id: "doc-1", title: "KTP Rina Ayu", status: "terverifikasi", at: iso(now - 150 * DAY) },
      { id: "doc-2", title: "Kartu Keluarga", status: "terverifikasi", at: iso(now - 150 * DAY) },
      { id: "doc-3", title: "NPWP", status: "terverifikasi", at: iso(now - 148 * DAY) },
      { id: "doc-4", title: "Slip gaji 3 bulan terakhir", status: "terverifikasi", at: iso(now - 146 * DAY) },
      { id: "doc-5", title: "Surat pesanan rumah (SPR)", status: "terverifikasi", at: iso(now - 152 * DAY) },
      { id: "doc-6", title: "Surat keterangan belum memiliki rumah", status: "diperiksa", at: iso(now - 20 * DAY) },
    ],
    promos: [
      { id: "pr-1", title: "Gratis biaya akad", body: "Biaya notaris akad ditanggung developer untuk akad sebelum Maret 2027.", until: iso(now + 90 * DAY) },
      { id: "pr-2", title: "Paket kanopi dan pagar", body: "Kanopi dan pagar depan potongan Rp1.500.000 untuk pembeli Blok C.", until: iso(now + 60 * DAY) },
      { id: "pr-3", title: "Ajak tetangga baru", body: "Poin 500 untuk setiap teman yang booking lewat kode Anda.", until: iso(now + 120 * DAY) },
    ],
    cancellation: null,
    referral: { code: "RINA-C12", invited: [] },
  };
}
