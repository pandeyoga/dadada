// Slides built from the competitor, software-landscape, Estora-inventory and BTN research notes.
const fa = require('react-icons/fa6');
const { HEX, iconCircle, card, txt, bullets, source } = require('./lib');
let H = {};
try { H = require('./slides_btn_history'); } catch (e) { if (e.code !== 'MODULE_NOT_FOUND') throw e; }

const ST = {
  A: { text: 'Ada', fill: 'D5EBEF', color: HEX.accent1, bold: true },
  S: { text: 'Sebagian', fill: 'FBEBC8', color: '7A4F00', bold: false },
  '-': { text: '—', fill: 'F2F4F4', color: '8A9A9F', bold: false },
};
const cell = (k) => ({ text: ST[k].text, options: { fill: { color: ST[k].fill }, color: ST[k].color, bold: ST[k].bold, align: 'center', valign: 'middle' } });
const head = (t, o = {}) => ({ text: t, options: Object.assign({ fill: { color: HEX.dk2 }, color: 'FFFFFF', bold: true, valign: 'middle', align: 'center' }, o) });
const rowLabel = (t, sub) => ({ text: sub ? [{ text: t, options: { bold: true, breakLine: true } }, { text: sub, options: { fontSize: 11, color: HEX.accent5 } }] : t, options: { fill: { color: 'FFFFFF' }, color: HEX.dk1, bold: !sub, valign: 'middle', align: 'left' } });
const BORDER = { type: 'solid', pt: 1, color: 'FFFFFF' };

function legend(s, C, x, y) {
  [['A', 'ada / terbukti publik'], ['S', 'sebagian atau hanya klaim'], ['-', 'tidak ditemukan']].forEach(([k, l], i) => {
    const xx = x + i * 2.75;
    s.addShape('roundRect', { x: xx, y, w: 0.85, h: 0.3, rectRadius: 0.05, fill: { color: ST[k].fill }, line: { color: ST[k].fill, width: 0 }, objectName: 'legend swatch ' + k });
    txt(s, ST[k].text, { x: xx, y, w: 0.85, h: 0.3, fontSize: 11, bold: ST[k].bold, color: ST[k].color, align: 'center', valign: 'middle' });
    txt(s, l, { x: xx + 0.95, y, w: 1.75, h: 0.3, fontSize: 11, color: C.accent5, valign: 'middle' });
  });
}

async function summary(pres, C, sec) {
  const s = pres.addSlide({ masterName: 'CONTENT', sectionTitle: sec });
  s.addText('RINGKASAN', { placeholder: 'kicker' });
  s.addText('Estora unggul di kedalaman operasi, tertinggal di bukti pasar', { placeholder: 'title' });
  const rows = [
    [fa.FaTrophy, 'Arena', 'BTN Housingpreneur Batch 3 tutup 30 Nov 2026. Untuk platform developer, kategori yang paling cocok adalah Housing Ecosystem (usaha ≥ 2 tahun) atau Housing Innovation (usaha < 2 tahun).'],
    [fa.FaHouse, 'Rumah Ningrat', 'Tumpukan digital paling lengkap di segmen subsidi, semuanya in-house. Tetapi aplikasi penghuninya baru 1.000+ unduhan tanpa ulasan, dan risiko terbesarnya ada di mutu tapak (Klayan 5).'],
    [fa.FaPeopleGroup, 'Developer sejenis', 'Tidak ada developer subsidi lain yang menutup lebih dari satu atau dua lapis digital. Perumnas paling maju di sisi penjualan. Aplikasi penghuni developer besar rata-rata hanya 2–3 bintang.'],
    [fa.FaLaptopCode, 'Software', 'Aplikasi gratis BTN untuk developer (balé developer) sudah dipakai 12.600+ developer untuk stok, SPR, VA, dan status KPR. Belum ada yang menyambung FLPP, piutang bertahap, bukti konstruksi, BAST, dan PSU.'],
  ];
  for (let i = 0; i < rows.length; i++) {
    const [ic, lead, body] = rows[i];
    const y = 1.55 + i * 1.0;
    await iconCircle(s, C, ic, 0.6, y + 0.1, 0.62, C.accent1, lead);
    txt(s, lead, { x: 1.45, y: y + 0.05, w: 2.3, h: 0.7, fontSize: 16, bold: true, color: C.text1, valign: 'middle' });
    txt(s, body, { x: 3.75, y: y + 0.02, w: 8.95, h: 0.85, fontSize: 14, color: C.text1, valign: 'middle' });
  }
  card(s, C, 0.6, 5.6, 12.12, 0.95, { fill: C.accent1, name: 'recommendation bar' });
  s.addText([
    { text: 'Rekomendasi: ', options: { bold: true } },
    { text: 'posisikan Estora sebagai pelengkap balé developer, "dari lead sampai garansi dengan jejak bukti per unit", dan siapkan angka nyata dari instance produksi Harmony Land 5 sebelum pitch.' },
  ], { isTextBox: true, x: 0.85, y: 5.65, w: 11.7, h: 0.85, fontSize: 15, color: C.background1, margin: 0, valign: 'middle', objectName: 'recommendation text' });
}

async function competitors(pres, C, sec) {
  // C1 — subsidized developer comparables
  {
    const s = pres.addSlide({ masterName: 'CONTENT', sectionTitle: sec });
    s.addText('PESAING · DEVELOPER SUBSIDI', { placeholder: 'kicker' });
    s.addText('Tak ada developer subsidi lain selengkap Rumah Ningrat', { placeholder: 'title' });
    const cols = ['Developer', 'Skala (klaim/publik)', 'Booking online', 'Simulator KPR', 'Portal agen', 'Dashboard pembeli', 'Aplikasi penghuni'];
    const data = [
      ['Rumah Ningrat', 'Trusmi Group, Cirebon', '10.000+ unit terjual', 'A', 'A', 'A', 'A', 'A'],
      ['Perumnas', 'BUMN', '500.000+ unit sejak 1974', 'A', 'A', 'S', '-', '-'],
      ['Vista Land Group', 'swasta, 30+ proyek', '60.000+ unit diserahkan', '-', '-', '-', '-', '-'],
      ['Pesona Kahuripan', 'Bogor', '2.400 unit (2024)', 'S', 'A', '-', '-', '-'],
      ['Puri Delta Asri', 'Kendal', 'tidak dipublikasikan', '-', '-', '-', '-', 'A'],
      ['Delta Group · Infiniti Realty · SPS', 'BTN Awards 2025; juara BTN HP 2025', 'beragam', '-', '-', '-', '-', '-'],
    ];
    const rows = [cols.map((c, i) => head(c, i === 0 ? { align: 'left' } : {}))];
    data.forEach((r) => rows.push([rowLabel(r[0], r[1]), { text: r[2], options: { fill: { color: 'FFFFFF' }, color: HEX.dk1, fontSize: 12, valign: 'middle' } }, ...r.slice(3).map(cell)]));
    s.addTable(rows, { x: 0.6, y: 1.5, w: 12.12, colW: [2.9, 2.17, 1.41, 1.41, 1.41, 1.41, 1.41], rowH: [0.5, 0.62, 0.62, 0.62, 0.62, 0.62, 0.62], fontSize: 13, border: BORDER, margin: 0.06, objectName: 'developer comparables table' });
    legend(s, C, 0.6, 5.95);
    txt(s, 'Perumnas: toko di Blibli sampai booking, skema afiliasi "Sobat Bisnis Perumnas" (komisi tidak dipublikasikan), ±60% penjualan dari konten digital.', { x: 0.6, y: 6.3, w: 12.1, h: 0.3, fontSize: 11, color: C.accent5 });
    source(s, C, 'Sumber: situs resmi developer, Google Play/App Store, BTN Awards 2025, BP Tapera Awards 2025, Bisnis.com, Detik Properti. Diakses 24 Nov 2026. Peringkat FLPP per developer tidak dipublikasikan.');
  }
  // C2 — large developer resident apps ratings
  {
    const s = pres.addSlide({ masterName: 'CONTENT', sectionTitle: sec });
    s.addText('PESAING · APLIKASI PENGHUNI', { placeholder: 'kicker' });
    s.addText('Aplikasi penghuni developer besar pun hanya 2–3 bintang', { placeholder: 'title' });
    const labels = ['Summarecon Home (10K+)', 'Ciputra Hub (100K+)', 'LEAP · Lippo (10K+)', 'Paramount Estate (10K+)', 'OneSmile · Sinar Mas Land (100K+)'];
    s.addChart(pres.charts.BAR, [{ name: 'Rating Google Play', labels, values: [3.9, 2.9, 2.8, 2.7, 2.2] }], {
      x: 0.6, y: 1.5, w: 7.4, h: 4.95, barDir: 'bar', barGapWidthPct: 60,
      chartColors: [HEX.accent2], showValue: true, dataLabelPosition: 'outEnd', dataLabelFormatCode: '0.0', dataLabelColor: HEX.dk1, dataLabelFontSize: 13, dataLabelFontFace: '+mn-lt',
      catAxisLabelColor: HEX.dk1, catAxisLabelFontSize: 13, catAxisLabelFontFace: '+mn-lt', catAxisOrientation: 'maxMin',
      valAxisMinVal: 0, valAxisMaxVal: 5, valAxisMajorUnit: 1, valAxisLabelColor: HEX.accent5, valAxisLabelFontSize: 11, valAxisLabelFontFace: '+mn-lt',
      valGridLine: { color: 'E3E9EB', size: 0.75 }, catGridLine: { style: 'none' }, showLegend: false,
      showTitle: true, title: 'Rating Google Play (bintang) dan jumlah unduhan, 24 Nov 2026', titleFontSize: 14, titleColor: HEX.dk1, titleFontFace: '+mn-lt',
      objectName: 'resident app rating chart', altText: 'Rating Google Play aplikasi penghuni developer besar: Summarecon Home 3,9; Ciputra Hub 2,9; LEAP 2,8; Paramount Estate 2,7; OneSmile 2,2',
    });
    card(s, C, 8.35, 1.5, 4.37, 4.95, { fill: C.background2, name: 'resident app commentary' });
    bullets(s, [
      'Fiturnya mirip semua: tagihan IPL, izin renovasi, komplain, akses tamu, SOS.',
      'Rating iOS lebih rendah lagi, banyak di 1,4–2,9 bintang.',
      'Keluarga Ningrat baru 1.000+ unduhan tanpa ulasan; Puri Delta Asri 500+.',
      'Developer subsidi lain menerbitkan aplikasi lewat akun pribadi atau akun proyek.',
    ], { x: 8.6, y: 1.72, w: 3.9, h: 3.0, fontSize: 14, color: C.text1 });
    card(s, C, 8.6, 4.85, 3.87, 1.4, { fill: C.accent1, name: 'resident lesson' });
    txt(s, 'Bagi Estora: mulai pascahuni dari tagihan IPL lewat portal dan WhatsApp, bukan super-app.', { x: 8.8, y: 4.95, w: 3.5, h: 1.2, fontSize: 14, bold: true, color: C.background1, valign: 'middle' });
    source(s, C, 'Sumber: Google Play & App Store (Ciputra Hub, OneSmile, Summarecon Home, LEAP, Paramount Estate, Keluarga Ningrat, Rumahku Puri Delta Asri), diakses 24 Nov 2026.');
  }
  // C3 — BTN's free developer tool
  {
    const s = pres.addSlide({ masterName: 'CONTENT', sectionTitle: sec });
    s.addText('PESAING · ALAT GRATIS DARI BANK', { placeholder: 'kicker' });
    s.addText('Pesaing terdekat Estora adalah alat gratis milik BTN', { placeholder: 'title' });
    const stats = [['12.600+', 'developer di Bale Properti (Jul 2025)'], ['10K+', 'unduhan BTN Properti for Developer'], ['4,3', 'rating Google Play']];
    stats.forEach(([n, l], i) => {
      const x = 0.6 + i * 4.11;
      card(s, C, x, 1.5, 3.9, 1.15, { fill: C.background2, name: 'btn stat ' + i });
      txt(s, n, { x: x + 0.25, y: 1.62, w: 1.75, h: 0.9, fontSize: 30, bold: true, color: C.accent1, valign: 'middle' });
      txt(s, l, { x: x + 2.0, y: 1.62, w: 1.75, h: 0.9, fontSize: 13, color: C.text1, valign: 'middle' });
    });
    card(s, C, 0.6, 2.9, 5.95, 3.15, { fill: 'FFFFFF', line: HEX.accent1, name: 'btn covers' });
    await iconCircle(s, C, fa.FaCircleCheck, 0.85, 3.1, 0.5, C.accent1, 'dicakup');
    txt(s, 'Sudah dicakup BTN (gratis)', { x: 1.5, y: 3.15, w: 4.8, h: 0.4, fontSize: 17, bold: true, color: C.text1 });
    bullets(s, ['Stok unit dan surat booking (SPR) otomatis', 'Virtual account untuk booking fee, DP, dan tunai bertahap', 'Pengajuan dan status KPR online, khusus BTN', 'Peran admin, marketing, dan keuangan', 'Insentif tunai untuk admin developer (Mar–Jun 2026)'], { x: 0.9, y: 3.75, w: 5.45, h: 2.6, fontSize: 14, color: C.text1 });
    card(s, C, 6.77, 2.9, 5.95, 3.15, { fill: 'FFF6E3', name: 'btn gaps' });
    await iconCircle(s, C, fa.FaCircleXmark, 7.02, 3.1, 0.5, C.accent2, 'tidak dicakup');
    txt(s, 'Tidak dicakup: ruang untuk Estora', { x: 7.67, y: 3.15, w: 4.8, h: 0.4, fontSize: 17, bold: true, color: C.text1 });
    bullets(s, ['Lead dan atribusi iklan, fee mitra', 'Pembatalan, refund, denda keterlambatan, jurnal', 'Bank selain BTN', 'Komplain ber-SLA, BAST, garansi', 'Izin dan serah terima PSU'], { x: 7.07, y: 3.75, w: 5.45, h: 2.6, fontSize: 14, color: C.text1 });
    source(s, C, 'Sumber: Google Play "BTN Properti for Developer" (update 21 Nov 2025), pemberitaan BTN tentang Bale Properti (Jul 2025) dan insentif admin developer 2026; sebagian dari cuplikan pencarian karena btn.co.id memblokir akses otomatis.');
  }
  // C4 — software vendors
  {
    const s = pres.addSlide({ masterName: 'CONTENT', sectionTitle: sec });
    s.addText('PESAING · VENDOR SOFTWARE DEVELOPER', { placeholder: 'kicker' });
    s.addText('Vendor lokal kuat di ERP dan RAB, lemah di sisi pembeli', { placeholder: 'title' });
    const H2 = ['Vendor', 'Kelas', 'Harga publik', 'Kekuatan', 'Bukti traksi'];
    const v = [
      ['Batavianet eProperty', 'Enterprise, sejak 1996', 'tidak dibuka', 'Penalti piutang, komisi agen, pembatalan, legal', 'klaim 300+ klien'],
      ['IFCA Property365', 'Enterprise, sejak 1995', 'tidak dibuka', 'Penjualan, sewa, aset, akuntansi proyek', '70 staf (profil)'],
      ['ECes.Q · Porta Pro', 'Menengah', 'tidak dibuka', 'Perizinan, pembangunan, monitor berkas KPR', 'klaim 400+ proyek; app 1K+'],
      ['Ndalem', 'UKM, sejak 2016', 'Rp1,499 jt/bln · Rp14,9 jt/thn', 'SPR, siteplan, KPR, RAB, akuntansi; subsidi & komersial', 'app 10+ unduhan'],
      ['Mandep', 'UKM', 'Rp15–40 jt/thn (per batas unit)', 'Booking, RAB, inventori, siteplan', 'app 500+ unduhan'],
      ['Simandor', 'UKM', 'tidak dibuka', 'Aplikasi pembeli SmartMandor: kewajiban bayar & progres', '—'],
      ['Alphasoft (Odoo)', 'Konsultan kustom', 'tidak dibuka', 'Klaim FLPP/SiKasep, denda cicilan, izin, BAST, IPL', 'proyek kustom'],
      ['AutoKon', 'Pengawasan via WhatsApp', 'tidak dibuka', 'Progres proyek; pembeli lapor cacat', 'MoU dengan REI, Okt 2025'],
    ];
    const rows = [H2.map((c) => head(c, { align: 'left' }))];
    v.forEach((r) => rows.push(r.map((t, i) => ({ text: t, options: { fill: { color: 'FFFFFF' }, color: HEX.dk1, bold: i === 0, fontSize: i === 0 ? 13 : 12, valign: 'middle' } }))));
    s.addTable(rows, { x: 0.6, y: 1.45, w: 12.12, colW: [2.3, 2.05, 2.25, 3.7, 1.82], rowH: 0.52, fontSize: 12, border: { type: 'solid', pt: 0.75, color: 'D5E2E5' }, margin: 0.06, objectName: 'software vendor table' });
    source(s, C, 'Sumber: situs vendor (softwareproperti.com, mediasarana.com, ndalem.app, mandep.id/harga, simandor.id, alphasoft.co.id), Google Play, Detik (30 Okt 2025). Klaim jumlah klien belum diverifikasi pihak ketiga. Tidak ditemukan berita pendanaan.');
  }
  // C5 — white space
  {
    const s = pres.addSlide({ masterName: 'CONTENT', sectionTitle: sec });
    s.addText('PESAING · CELAH PASAR', { placeholder: 'kicker' });
    s.addText('Lima celah pasar dan posisi Estora di tiap celah', { placeholder: 'title' });
    const gaps = [
      [fa.FaRoute, 'Alur FLPP ujung ke ujung', 'tersambung ke SiKumbang, Tapera Mobile, dan pengecekan "trilogi stok" sebelum akad', 'S', 'Satu produk BTN FLPP; belum ada tautan SiKumbang/SiKasep'],
      [fa.FaMoneyBillWave, 'Piutang tunai bertahap', 'cicilan in-house dengan denda dan jurnal otomatis, termasuk skema syariah tanpa denda', 'A', 'Jadwal, denda, refund, jurnal buku besar'],
      [fa.FaCamera, 'Rantai bukti per unit', 'foto lapangan → SiPetruk & cek bank → BAST → klaim garansi ber-SLA', 'A', 'Progres berfoto ber-watermark, BAST terkunci isu, garansi; belum ke SiPetruk'],
      [fa.FaRoad, 'Serah terima PSU', 'jalan, drainase, dan fasum ke Pemda; inti kasus Klayan 5', '-', 'Belum ada modul PSU'],
      [fa.FaMobileScreenButton, 'Portal pembeli & lapangan offline', 'login OTP, SLA komplain, aplikasi tim lapangan yang jalan tanpa sinyal', 'A', 'OTP WhatsApp, SLA 48 jam, PWA offline'],
    ];
    for (let i = 0; i < gaps.length; i++) {
      const [ic, h, d, st, ev] = gaps[i];
      const y = 1.5 + i * 0.98;
      card(s, C, 0.6, y, 12.12, 0.86, { fill: i % 2 ? 'FFFFFF' : C.background2, name: 'gap row ' + (i + 1) });
      await iconCircle(s, C, ic, 0.78, y + 0.15, 0.56, C.accent2, h);
      txt(s, h, { x: 1.55, y: y + 0.1, w: 3.2, h: 0.66, fontSize: 15, bold: true, color: C.text1, valign: 'middle' });
      txt(s, d, { x: 4.8, y: y + 0.08, w: 3.95, h: 0.7, fontSize: 13, color: C.text1, valign: 'middle' });
      s.addShape('roundRect', { x: 8.9, y: y + 0.24, w: 1.05, h: 0.38, rectRadius: 0.06, fill: { color: ST[st].fill }, line: { color: ST[st].fill, width: 0 }, objectName: 'estora status ' + (i + 1) });
      txt(s, ST[st].text, { x: 8.9, y: y + 0.24, w: 1.05, h: 0.38, fontSize: 12, bold: true, color: ST[st].color, align: 'center', valign: 'middle' });
      txt(s, ev, { x: 10.1, y: y + 0.08, w: 2.5, h: 0.7, fontSize: 12, color: C.accent5, valign: 'middle' });
    }
    txt(s, 'Status Estora', { x: 8.9, y: 1.22, w: 1.6, h: 0.25, fontSize: 11, bold: true, color: C.accent5 });
    source(s, C, 'Celah disimpulkan dari klaim fitur publik vendor, bukan wawancara developer. Status Estora dari inventaris repositori (dokumen & kode), bukan uji fungsional.');
  }
}

async function implications(pres, C, sec) {
  // D1 — capability matrix
  {
    const s = pres.addSlide({ masterName: 'CONTENT', sectionTitle: sec });
    s.addText('IMPLIKASI · POSISI', { placeholder: 'kicker' });
    s.addText('Estora unggul di transaksi, kalah di booking dan pascahuni', { placeholder: 'title' });
    const cols = ['Kapabilitas', 'Estora', 'Rumah Ningrat', 'BTN balé developer', 'Vendor lokal'];
    const m = [
      ['Lead & atribusi iklan', 'A', 'S', '-', 'S'],
      ['Booking online & pembayaran VA', 'S', 'A', 'A', 'S'],
      ['Pipeline & status KPR', 'A', 'A', 'S', 'S'],
      ['Cicilan bertahap, denda, jurnal', 'A', '-', 'S', 'A'],
      ['Pembatalan & refund', 'A', '-', '-', 'A'],
      ['Fee mitra / afiliasi', 'S', 'A', '-', 'A'],
      ['Progres konstruksi berbukti foto', 'A', 'S', '-', 'S'],
      ['BAST, garansi, komplain ber-SLA', 'A', 'S', '-', 'S'],
      ['Pascahuni: IPL & keamanan', '-', 'A', 'S', 'S'],
      ['Izin & serah terima PSU', 'S', '-', '-', 'S'],
    ];
    const rows = [cols.map((c, i) => head(c, i === 0 ? { align: 'left' } : {}))];
    m.forEach((r) => rows.push([{ text: r[0], options: { fill: { color: 'FFFFFF' }, color: HEX.dk1, bold: true, valign: 'middle' } }, ...r.slice(1).map(cell)]));
    s.addTable(rows, { x: 0.6, y: 1.45, w: 12.12, colW: [4.12, 2.0, 2.0, 2.0, 2.0], rowH: 0.43, fontSize: 13, border: BORDER, margin: 0.05, objectName: 'capability matrix' });
    legend(s, C, 0.6, 6.25);
    source(s, C, 'Estora: inventaris repositori. Rumah Ningrat & BTN: pengamatan publik. Vendor lokal: gabungan klaim terbaik (Batavianet, Alphasoft, Simandor, Ndalem), bukan satu produk.');
    s.addNotes('Fee mitra di Estora dinilai Sebagian karena aturan fee ada tetapi belum ada portal login untuk mitra. Izin Estora ada (peringatan masa berlaku KRK/IMB/PBG/SLF/AMDAL) tetapi PSU belum, sehingga Sebagian. Pascahuni BTN Sebagian karena aplikasi bale community terpisah dari alat developer.');
  }
  // D2 — criteria mapping
  {
    const s = pres.addSlide({ masterName: 'CONTENT', sectionTitle: sec });
    s.addText('IMPLIKASI · KESIAPAN UNTUK JURI', { placeholder: 'kicker' });
    s.addText('Menurut kriteria juri: teknologi kuat, bukti bisnis tipis', { placeholder: 'title' });
    const rowsD = [
      ['Kematangan teknologi', '25%', 'A', '±1.019 endpoint, 56 halaman, jurnal otomatis, ekspor Coretax, PWA offline; 70 gate verifikasi & ±842 tes', 'Demo langsung; jalankan ulang gate dan simpan lognya'],
      ['Skalabilitas & replikasi', '20%', 'S', 'Multi-organisasi; skrip deploy ke subdomain estora.id', 'Baru satu instance produksi: cari pilot developer kedua atau LOI'],
      ['Kelayakan bisnis', '20%', '-', 'Belum ada harga atau penagihan', 'Tetapkan harga (patokan Rp1,5 jt/bln–Rp40 jt/thn) dan RAB'],
      ['Executable', '15%', 'A', 'Berjalan di proyek Harmony Land 5', 'Tarik angka unit, transaksi, waktu proses dari hl5'],
      ['Relevansi masalah', '10%', 'A', 'Kuota FLPP 2026: 350 rb unit, baru 45,7% tersalurkan per 28 Sep', 'Tambah kutipan developer dan kasus Klayan 5'],
      ['Kolaborasi ekosistem', '10%', 'S', 'Belum ada integrasi BTN/Tapera', 'Jangan klaim integrasi; tunjukkan rencana ke BTN Properti for Developer, VA/QRIS BTN, data FLPP'],
    ];
    const hdr = ['Kriteria', 'Bobot', 'Status', 'Bukti Estora hari ini', 'Yang harus disiapkan'].map((c, i) => head(c, i >= 3 || i === 0 ? { align: 'left' } : {}));
    const rows = [hdr];
    rowsD.forEach((r) => rows.push([
      { text: r[0], options: { fill: { color: 'FFFFFF' }, color: HEX.dk1, bold: true, valign: 'middle' } },
      { text: r[1], options: { fill: { color: 'FFFFFF' }, color: HEX.accent1, bold: true, align: 'center', valign: 'middle' } },
      cell(r[2]),
      { text: r[3], options: { fill: { color: 'FFFFFF' }, color: HEX.dk1, fontSize: 12, valign: 'middle' } },
      { text: r[4], options: { fill: { color: 'FFFFFF' }, color: HEX.dk1, fontSize: 12, valign: 'middle' } },
    ]));
    s.addTable(rows, { x: 0.6, y: 1.45, w: 12.12, colW: [2.35, 0.8, 1.15, 4.2, 3.62], rowH: [0.45, 0.72, 0.72, 0.72, 0.72, 0.72, 0.72], fontSize: 13, border: { type: 'solid', pt: 0.75, color: 'D5E2E5' }, margin: 0.06, objectName: 'criteria readiness table' });
    source(s, C, 'Bobot: btnhousingpreneur.com (Developer & Pengusaha › Housing Ecosystem). Bukti Estora: inventaris repositori; hasil gate terakhir tercatat 7 Sep 2026, log tidak di-commit. Data FLPP: pemberitaan BP Tapera 2026.');
  }
  // D3 — next steps
  {
    const s = pres.addSlide({ masterName: 'CONTENT', sectionTitle: sec });
    s.addText('IMPLIKASI · LANGKAH BERIKUTNYA', { placeholder: 'kicker' });
    s.addText('Enam hari menuju 30 November: jalur dulu, lalu bukti', { placeholder: 'title' });
    const steps = [
      ['24–25 Nov', fa.FaScaleBalanced, 'Putuskan jalur', 'Cek umur badan usaha: ≥ 2 tahun → Housing Ecosystem; < 2 tahun → Housing Innovation. Minta persetujuan tertulis developer Harmony Land 5; konfirmasi ke panitia.'],
      ['25–27 Nov', fa.FaChartLine, 'Kumpulkan angka', 'Tarik data nyata dari instance Harmony Land 5: unit, transaksi, waktu proses booking sampai akad. Tetapkan model harga.'],
      ['26–28 Nov', fa.FaFileLines, 'Susun pitch 7 slide', 'Ikuti 7 halaman resmi: masalah & urgensi, pasar, ide, keunggulan, prototipe, manfaat, model bisnis + Sinergi BTN + RAB.'],
      ['28–30 Nov', fa.FaShieldHalved, 'Rapikan & kirim', 'Company profile, profil proyek Harmony Land 5 + Google Maps, NPWP, Pakta Integritas. Baca klausul pemakaian karya. Rotasi kata sandi bawaan.'],
    ];
    const w = 2.86, gap = 0.23;
    for (let i = 0; i < steps.length; i++) {
      const [d, ic, h, b] = steps[i];
      const x = 0.6 + i * (w + gap);
      txt(s, d, { x, y: 1.5, w, h: 0.35, fontSize: 14, bold: true, color: C.accent2 });
      card(s, C, x, 1.9, w, 3.05, { fill: C.background2, name: 'step ' + (i + 1) });
      await iconCircle(s, C, ic, x + 0.25, 2.1, 0.58, C.accent1, h);
      txt(s, h, { x: x + 0.25, y: 2.8, w: w - 0.5, h: 0.4, fontSize: 16, bold: true, color: C.text1 });
      txt(s, b, { x: x + 0.25, y: 3.25, w: w - 0.5, h: 1.6, fontSize: 13, color: C.text1 });
    }
    card(s, C, 0.6, 5.25, 12.12, 0.98, { fill: C.text2, name: 'positioning statement' });
    s.addText([
      { text: 'Kalimat posisi: ', options: { bold: true, color: HEX.accent3 } },
      { text: 'Estora adalah sistem operasi developer subsidi yang melengkapi balé developer: dari lead sampai garansi, dengan jejak bukti per unit yang bisa diperiksa bank, Pemda, dan pembeli.', options: { color: 'FFFFFF' } },
    ], { isTextBox: true, x: 0.85, y: 5.3, w: 11.7, h: 0.88, fontSize: 15, margin: 0, valign: 'middle', objectName: 'positioning text' });
  }
  // D4 — sources & method
  {
    const s = pres.addSlide({ masterName: 'CONTENT', sectionTitle: sec });
    s.addText('LAMPIRAN', { placeholder: 'kicker' });
    s.addText('Metode, sumber, dan batas riset', { placeholder: 'title' });
    card(s, C, 0.6, 1.5, 5.95, 4.95, { fill: C.background2, name: 'method card' });
    txt(s, 'Metode', { x: 0.85, y: 1.7, w: 5.5, h: 0.4, fontSize: 17, bold: true, color: C.text1 });
    bullets(s, [
      'Data publik 23–24 Nov 2026: situs resmi, Google Play, App Store, pemberitaan nasional dan lokal.',
      'Halaman berbasis JavaScript dirender dengan Chromium, termasuk btnhousingpreneur.com dan mitra.rumahningrat.com.',
      'Screenshot aplikasi berasal dari etalase resmi toko; tidak ada login ke akun siapa pun.',
      'Fitur Estora dari dokumen dan kode repositori, bukan uji fungsional.',
    ], { x: 0.85, y: 2.2, w: 5.5, h: 4.1, fontSize: 14, color: C.text1 });
    card(s, C, 6.77, 1.5, 5.95, 4.95, { fill: 'FFF6E3', name: 'limits card' });
    txt(s, 'Batas yang perlu diingat', { x: 7.02, y: 1.7, w: 5.5, h: 0.4, fontSize: 17, bold: true, color: C.text1 });
    bullets(s, [
      'Angka skala developer kebanyakan klaim perusahaan.',
      'Peringkat FLPP per developer tidak dipublikasikan BP Tapera.',
      'Sebagian data BTN dan SiKumbang dari cuplikan pencarian karena situsnya memblokir akses otomatis.',
      'Dashboard agen, portal pembeli, dan isi aplikasi penghuni di balik login tidak diperiksa.',
      'Catatan lengkap: research_notes/ di repositori.',
    ], { x: 7.02, y: 2.2, w: 5.5, h: 4.1, fontSize: 14, color: C.text1 });
  }
}

module.exports = { summary, competitors, implications, btnHistory: H.btnHistory };
