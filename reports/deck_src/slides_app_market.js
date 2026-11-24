// App-domain slides: resident (post-handover) apps and BTN Housingpreneur winners' products.
const fa = require('react-icons/fa6');
const { HEX, ASSETS, iconCircle, card, txt, bullets, source, path } = require('./lib');
const A = (f) => path.join(ASSETS, f);

const ST = {
  A: { text: 'Ada', fill: 'D5EBEF', color: HEX.accent1, bold: true },
  S: { text: 'Sebagian', fill: 'FBEBC8', color: '7A4F00', bold: false },
  '-': { text: '—', fill: 'F2F4F4', color: '8A9A9F', bold: false },
};
const cell = (k) => ({ text: ST[k].text, options: { fill: { color: ST[k].fill }, color: ST[k].color, bold: ST[k].bold, align: 'center', valign: 'middle' } });
const head = (t, o = {}) => ({ text: t, options: Object.assign({ fill: { color: HEX.dk2 }, color: 'FFFFFF', bold: true, valign: 'middle', align: 'center' }, o) });
const plain = (t, o = {}) => ({ text: t, options: Object.assign({ fill: { color: 'FFFFFF' }, color: HEX.dk1, valign: 'middle' }, o) });
const REL = { Tinggi: ['D5EBEF', HEX.accent1], Sedang: ['FBEBC8', '7A4F00'], Rendah: ['F2F4F4', '6B7F86'] };

function legend(s, C, x, y) {
  [['A', 'ada'], ['S', 'sebagian / terbatas'], ['-', 'tidak ada']].forEach(([k, l], i) => {
    const xx = x + i * 2.5;
    s.addShape('roundRect', { x: xx, y, w: 0.85, h: 0.28, rectRadius: 0.05, fill: { color: ST[k].fill }, line: { color: ST[k].fill, width: 0 }, objectName: 'legend ' + k });
    txt(s, ST[k].text, { x: xx, y, w: 0.85, h: 0.28, fontSize: 11, bold: ST[k].bold, color: ST[k].color, align: 'center', valign: 'middle' });
    txt(s, l, { x: xx + 0.95, y, w: 1.5, h: 0.28, fontSize: 11, color: C.accent5, valign: 'middle' });
  });
}

// ---------- Resident apps ----------
async function phRatings(pres, C, sec) {
  const s = pres.addSlide({ masterName: 'CONTENT', sectionTitle: sec });
  s.addText('APLIKASI PENGHUNI · RATING', { placeholder: 'kicker' });
  s.addText('Yang paling banyak dipasang justru paling dikeluhkan', { placeholder: 'title' });
  const labels = ['RTPintar · SaaS RT (50rb+)', 'bale community · BTN (50rb+)', 'Summarecon Home (10rb+)', 'Ciputra Hub (100rb+)', 'LEAP · Lippo (10rb+)', 'Paramount Estate (10rb+)', 'OneSmile · Sinar Mas Land (100rb+)'];
  s.addChart(pres.charts.BAR, [
    { name: 'Aplikasi developer', labels, values: [0, 0, 3.9, 2.9, 2.8, 2.7, 2.2] },
    { name: 'SaaS / bank', labels, values: [4.6, 4.5, 0, 0, 0, 0, 0] },
  ], {
    x: 0.6, y: 1.5, w: 7.5, h: 4.95, barDir: 'bar', barGrouping: 'stacked', barGapWidthPct: 55,
    chartColors: [HEX.accent2, HEX.accent1],
    showValue: true, dataLabelPosition: 'inEnd', dataLabelFormatCode: '0.0;;;', dataLabelColor: 'FFFFFF', dataLabelFontSize: 12, dataLabelFontBold: true, dataLabelFontFace: '+mn-lt',
    catAxisLabelColor: HEX.dk1, catAxisLabelFontSize: 12, catAxisLabelFontFace: '+mn-lt', catAxisOrientation: 'maxMin',
    valAxisMinVal: 0, valAxisMaxVal: 5, valAxisMajorUnit: 1, valAxisLabelColor: HEX.accent5, valAxisLabelFontSize: 11, valAxisLabelFontFace: '+mn-lt',
    valGridLine: { color: 'E3E9EB', size: 0.75 }, catGridLine: { style: 'none' },
    showLegend: true, legendPos: 'b', legendFontSize: 12, legendFontFace: '+mn-lt', legendColor: HEX.dk1,
    showTitle: true, title: 'Rating Google Play (bintang) dan jumlah unduhan, 24 Nov 2026', titleFontSize: 14, titleColor: HEX.dk1, titleFontFace: '+mn-lt',
    objectName: 'resident rating chart', altText: 'Rating Google Play aplikasi penghuni: RTPintar 4,6; bale community 4,5; Summarecon Home 3,9; Ciputra Hub 2,9; LEAP 2,8; Paramount Estate 2,7; OneSmile 2,2',
  });
  card(s, C, 8.4, 1.5, 4.32, 4.95, { fill: C.background2, name: 'rating trend card' });
  txt(s, 'Tren rating dari sampel ulasan', { x: 8.62, y: 1.65, w: 3.9, h: 0.35, fontSize: 15, bold: true, color: C.text1 });
  const tr = [['Ciputra Hub', '4,17 → 2,91 → 1,77', '2024 → 2025 → 2026'], ['OneSmile', '4,79 → 1,29', '2023 → 2025'], ['bale community', '119 dari 140 ulasan', 'bertanggal Jan 2023 (peluncuran); ulasan 2025 rata-rata 1,0']];
  tr.forEach(([a, v, d], i) => {
    const y = 2.1 + i * 0.95;
    txt(s, a, { x: 8.62, y, w: 3.9, h: 0.28, fontSize: 13, bold: true, color: C.text1 });
    txt(s, v, { x: 8.62, y: y + 0.27, w: 3.9, h: 0.34, fontSize: 17, bold: true, color: C.accent2 });
    txt(s, d, { x: 8.62, y: y + 0.6, w: 3.9, h: 0.3, fontSize: 11, color: C.accent5 });
  });
  txt(s, 'Unduhan tinggi karena bayar IPL diwajibkan lewat aplikasi, bukan karena disukai. RTPintar dipuji karena CS cepat dan laporan kas terbuka.', { x: 8.62, y: 5.0, w: 3.9, h: 1.35, fontSize: 13, color: C.text1 });
  source(s, C, 'Sumber: Google Play & App Store, sampel ulasan berbahasa Indonesia (7–140 per aplikasi), diakses 24 Nov 2026. Rating iOS umumnya lebih rendah (LEAP 1,8; Paramount 1,38).');
}

async function phGallery(pres, C, sec) {
  const s = pres.addSlide({ masterName: 'CONTENT', sectionTitle: sec });
  s.addText('APLIKASI PENGHUNI · POLA LAYAR', { placeholder: 'kicker' });
  s.addText('Layar yang berulang: tagihan, izin, tiket, dan progres', { placeholder: 'title' });
  const ims = [
    ['ph_ciputra.png', 414, 'Ciputra Hub', 'Bayar IPL beberapa unit sekaligus'],
    ['ph_leap.png', 506, 'LEAP · Lippo', 'Izin renovasi dengan status'],
    ['ph_klasterin.png', 414, 'Klasterin', 'Tiket komplain berlinimasa & SLA'],
    ['ph_rtpintar.png', 506, 'RTPintar', 'Tagihan, lapor, CCTV dalam satu beranda'],
    ['ph_rumahku.png', 506, 'Rumahku · Puri Delta Asri', 'Angsuran, progres bangun, dan IPL'],
  ];
  const h = 4.1, ws = ims.map(([, w]) => h * w / 900), gap = (12.12 - ws.reduce((a, b) => a + b, 0)) / (ims.length - 1);
  let x = 0.6;
  ims.forEach(([f, , name, cap], i) => {
    s.addImage({ path: A(f), x, y: 1.5, w: ws[i], h, objectName: 'resident screen ' + name, altText: 'Screenshot toko ' + name + ': ' + cap });
    txt(s, name, { x: x - 0.1, y: 5.7, w: ws[i] + 0.2, h: 0.3, fontSize: 13, bold: true, color: i === 4 ? C.accent1 : C.text1, align: 'center' });
    txt(s, cap, { x: x - 0.15, y: 6.0, w: ws[i] + 0.3, h: 0.55, fontSize: 11, color: C.accent5, align: 'center' });
    x += ws[i] + gap;
  });
  source(s, C, 'Sumber: screenshot resmi App Store / Google Play, diakses 24 Nov 2026. Rumahku satu-satunya yang menyambung perjalanan pembeli ke warga dalam satu aplikasi.');
}

async function phComplaints(pres, C, sec) {
  const s = pres.addSlide({ masterName: 'CONTENT', sectionTitle: sec });
  s.addText('APLIKASI PENGHUNI · KELUHAN PENGGUNA', { placeholder: 'kicker' });
  s.addText('Enam penyebab bintang 1, hampir semuanya soal keandalan', { placeholder: 'title' });
  const rows = [
    ['Bayar IPL gagal atau status tak berubah lunas', 'paling sering di awal bulan · Ciputra Hub, LEAP, bale'],
    ['Gagal masuk', 'OTP tidak datang, verifikasi KTP ditolak'],
    ['Pilihan bank terbatas', 'Paramount hanya Mandiri; Ciputra Hub 2 bank'],
    ['Update membuat aplikasi tak bisa dibuka', 'dikeluhkan di beberapa aplikasi developer besar'],
    ['Komplain ditutup padahal belum beres', 'Ciputra Hub'],
    ['Gerbang QR dipaksakan tanpa alternatif', 'Paramount; warga minta kartu atau satpam'],
  ];
  rows.forEach(([h, d], i) => {
    const y = 1.5 + i * 0.8;
    s.addShape('ellipse', { x: 0.6, y: y + 0.08, w: 0.5, h: 0.5, fill: { color: i < 2 ? C.accent2 : C.accent5 }, line: { color: 'FFFFFF', width: 0 }, objectName: 'cause num ' + (i + 1) });
    txt(s, String(i + 1), { x: 0.6, y: y + 0.08, w: 0.5, h: 0.5, fontSize: 16, bold: true, color: C.background1, align: 'center', valign: 'middle' });
    txt(s, h, { x: 1.3, y: y + 0.02, w: 6.3, h: 0.35, fontSize: 15, bold: true, color: C.text1 });
    txt(s, d, { x: 1.3, y: y + 0.38, w: 6.3, h: 0.32, fontSize: 12, color: C.accent5 });
  });
  card(s, C, 8.0, 1.5, 4.72, 4.95, { fill: C.background2, name: 'onboarding card' });
  txt(s, 'Masuk aplikasi: siapa yang membuat akun?', { x: 8.25, y: 1.68, w: 4.3, h: 0.6, fontSize: 15, bold: true, color: C.text1 });
  txt(s, 'Banyak dikeluhkan', { x: 8.25, y: 2.4, w: 4.3, h: 0.3, fontSize: 12, bold: true, color: C.accent2 });
  txt(s, 'Warga klaim unit sendiri, unggah KTP, cari kode pelanggan, atau minta referral (Ciputra Hub, Summarecon, LEAP, bale).', { x: 8.25, y: 2.7, w: 4.3, h: 1.0, fontSize: 13, color: C.text1 });
  txt(s, 'Lebih mulus', { x: 8.25, y: 3.8, w: 4.3, h: 0.3, fontSize: 12, bold: true, color: C.accent1 });
  txt(s, 'Pengelola membuat atau mengimpor akun, warga cukup OTP WhatsApp (RTPintar, Klasterin).', { x: 8.25, y: 4.1, w: 4.3, h: 0.8, fontSize: 13, color: C.text1 });
  card(s, C, 8.25, 5.05, 4.22, 1.2, { fill: C.accent1, name: 'onboarding lesson' });
  txt(s, 'Estora sudah memegang data pembeli: akun pembeli bisa otomatis jadi akun warga saat BAST.', { x: 8.42, y: 5.12, w: 3.9, h: 1.06, fontSize: 13, bold: true, color: C.background1, valign: 'middle' });
  source(s, C, 'Sumber: ulasan Google Play (Indonesia, urut terbaru) dan ulasan pilihan App Store, diakses 24 Nov 2026. Urutan berdasarkan frekuensi tema dalam sampel.');
}

async function phMatrix(pres, C, sec) {
  const s = pres.addSlide({ masterName: 'CONTENT', sectionTitle: sec });
  s.addText('APLIKASI PENGHUNI · PETA FITUR', { placeholder: 'kicker' });
  s.addText('Keluarga Ningrat paling lengkap, tapi lepas dari data pembeli', { placeholder: 'title' });
  const cols = ['Aplikasi', 'Bayar IPL', 'Keamanan', 'Tiket komplain', 'Komunitas', 'Izin renovasi', 'Info pembeli', 'Akun dari pengelola'];
  const m = [
    ['Keluarga Ningrat', 'A', 'A', 'A', 'A', '-', '-', '-'],
    ['Ciputra Hub', 'A', 'S', 'S', 'A', 'A', 'S', '-'],
    ['OneSmile', 'A', 'S', 'S', 'A', '-', 'A', '-'],
    ['Summarecon Home', 'A', 'S', 'S', 'A', 'A', 'S', '-'],
    ['LEAP · Lippo', 'A', '-', 'A', 'A', 'A', 'S', 'S'],
    ['Paramount Estate', 'S', 'A', 'S', 'A', 'A', '-', 'S'],
    ['Rumahku · Puri Delta Asri', 'A', '-', 'A', 'A', '-', 'A', 'S'],
    ['bale community · BTN', 'A', '-', 'A', 'A', '-', 'S', 'S'],
    ['RTPintar', 'A', 'A', 'A', 'A', '-', '-', 'A'],
    ['Klasterin', 'A', 'A', 'A', 'A', '-', '-', 'A'],
  ];
  const rows = [cols.map((c, i) => head(c, i === 0 ? { align: 'left' } : {}))];
  m.forEach((r, i) => rows.push([plain(r[0], { bold: true, color: i === 0 ? HEX.accent1 : HEX.dk1 }), ...r.slice(1).map(cell)]));
  s.addTable(rows, { x: 0.6, y: 1.45, w: 12.12, colW: [3.0, 1.3, 1.3, 1.3, 1.3, 1.3, 1.3, 1.32], rowH: [0.5, ...Array(10).fill(0.41)], fontSize: 13, border: { type: 'solid', pt: 1, color: 'FFFFFF' }, margin: 0.05, objectName: 'resident feature matrix' });
  legend(s, C, 0.6, 6.15);
  txt(s, 'Info pembeli = angsuran, progres bangun, atau dokumen dari developer di dalam aplikasi warga.', { x: 8.2, y: 6.12, w: 4.52, h: 0.4, fontSize: 11, color: C.accent5 });
  source(s, C, 'Sumber: deskripsi toko, catatan rilis, dan screenshot resmi, diakses 24 Nov 2026. Keamanan = CCTV, gerbang, tamu, atau SOS.');
}

async function phModule(pres, C, sec) {
  const s = pres.addSlide({ masterName: 'CONTENT', sectionTitle: sec });
  s.addText('APLIKASI PENGHUNI · USULAN UNTUK ESTORA', { placeholder: 'kicker' });
  s.addText('Modul pascahuni Estora: mulai dari tagihan, bukan CCTV', { placeholder: 'title' });
  const tiers = [
    ['MVP', C.accent1, ['Akun pembeli otomatis jadi akun warga saat BAST', 'Tagihan IPL: VA multi-bank + QRIS, lunas otomatis, link bayar WhatsApp', 'Komplain 48 jam diperluas jadi tiket pascahuni dengan konfirmasi warga', 'Pengumuman + dashboard web pengelola']],
    ['Tahap 2', C.accent3, ['QR tamu dengan cadangan kartu/satpam', 'Tombol darurat', 'Izin renovasi berstatus', 'Klaim garansi tersambung ke data unit']],
    ['Tahap 3', C.accent5, ['Live CCTV dan smart gate', 'Booking fasilitas', 'Marketplace dan PPOB', 'Bernilai, tapi mahal dan bukan penentu rating']],
  ];
  const w = 3.88, gap = 0.24;
  tiers.forEach(([name, col, items], i) => {
    const x = 0.6 + i * (w + gap);
    card(s, C, x, 1.5, w, 3.1, { fill: C.background2, name: 'tier ' + name });
    s.addShape('roundRect', { x: x + 0.25, y: 1.7, w: 1.2, h: 0.4, rectRadius: 0.08, fill: { color: col }, line: { color: col, width: 0 }, objectName: 'tier tag ' + name });
    txt(s, name, { x: x + 0.25, y: 1.7, w: 1.2, h: 0.4, fontSize: 14, bold: true, color: i === 1 ? C.text1 : C.background1, align: 'center', valign: 'middle' });
    bullets(s, items, { x: x + 0.25, y: 2.3, w: w - 0.5, h: 2.2, fontSize: 14, color: C.text1, paraSpaceAfter: 6 });
  });
  card(s, C, 0.6, 4.85, 12.12, 1.15, { fill: 'FFF6E3', name: 'pricing benchmark' });
  s.addText([
    { text: 'Patokan harga SaaS estate: ', options: { bold: true } },
    { text: 'RTPintar Rp120 rb–900 rb/bulan (≤100 sampai 2.500 unit) · Klasterin Rp180 rb per 100 unit/bulan (promo; normal Rp450 rb) · bale BTN Rp2.000 per tagihan. Bentuk awal cukup PWA + WhatsApp, tanpa aplikasi native.' },
  ], { isTextBox: true, x: 0.85, y: 4.9, w: 11.7, h: 1.05, fontSize: 14, color: C.text1, margin: 0, valign: 'middle', objectName: 'pricing text' });
  source(s, C, 'Prioritas disimpulkan dari tema keluhan dan peta fitur; harga dari halaman resmi vendor, diakses 24 Nov 2026.');
}

// ---------- BTN Housingpreneur winners ----------
async function winTable(pres, C, sec) {
  const s = pres.addSlide({ masterName: 'CONTENT', sectionTitle: sec });
  s.addText('PEMENANG BTN HOUSINGPRENEUR · PRODUK', { placeholder: 'kicker' });
  s.addText('Dari sepuluh produk unggulan, hanya sebagian yang aplikasi', { placeholder: 'title' });
  const H = ['Tahun', 'Posisi', 'Produk', 'Apa yang dibuat', 'Jenis', 'Relevansi'];
  const d = [
    ['2024', 'Juara 1 Teknologi', 'CIROES', 'Aplikasi bank sampah: jual sampah per kg, jemput terjadwal (Android 5rb+, 4,3★)', 'Aplikasi', 'Sedang'],
    ['2024', 'Juara 2 Teknologi', 'Paktukang', 'Jasa tukang & renovasi via WhatsApp: survei, RAB terbuka, laporan progres, kredit', 'Platform web', 'Sedang'],
    ['2024', 'Juara 3 Teknologi', 'Autoconz (Berdikari)', 'Mesin cetak 3D konstruksi dan mortar', 'Mesin', 'Rendah'],
    ['2024', 'Juara 1 Ideasi', 'Platform Rusun Swadaya', 'Komunitas membangun rusun dengan akses pembiayaan BTN', 'Platform (ide)', 'Sedang'],
    ['2025', 'Juara 1 House Tech', 'TRAIN-O (PRANA TECH)', 'Pelatihan & sertifikasi tukang: mobile learning, VR, penyaluran kerja', 'Platform', 'Sedang'],
    ['2025', 'Juara 2 House Tech', 'AITOMA (Hayago)', 'Smart plug & sensor panel + aplikasi AI hemat energi', 'IoT + aplikasi', 'Rendah'],
    ['2025', 'Juara 3 House Tech', 'RUMAH GOKILS', 'Belum terverifikasi; pemilik merek pest control GoodKills', 'Layanan', 'Rendah'],
    ['2025', 'Juara 3 Value Chain', 'KPR Energy (GridSolr)', 'PLTS atap untuk pemilik rumah baru; ROI 4–5 tahun, monitoring', 'Energi + pembiayaan', 'Sedang'],
    ['2025', 'Finalis', 'Ontoown', 'Rent-to-own: sewa bulanan dikumpulkan jadi DP KPR, untuk Gen Z', 'Aplikasi', 'Tinggi'],
    ['2025', 'Juara 1 Mahasiswa', 'GeoFloodAI', 'AI pemetaan risiko banjir sejak tahap desain', 'AI', 'Rendah'],
  ];
  const rows = [H.map((h, i) => head(h, i === 3 || i === 2 ? { align: 'left' } : {}))];
  d.forEach((r) => {
    const [f, c] = REL[r[5]];
    rows.push([plain(r[0], { align: 'center', fontSize: 12 }), plain(r[1], { fontSize: 12 }), plain(r[2], { bold: true, fontSize: 12 }), plain(r[3], { fontSize: 12 }), plain(r[4], { fontSize: 12, align: 'center' }), { text: r[5], options: { fill: { color: f }, color: c, bold: r[5] !== 'Rendah', align: 'center', valign: 'middle', fontSize: 12 } }]);
  });
  s.addTable(rows, { x: 0.6, y: 1.42, w: 12.12, colW: [0.75, 1.75, 2.2, 4.85, 1.45, 1.12], rowH: [0.42, ...Array(10).fill(0.46)], fontSize: 12, border: { type: 'solid', pt: 0.75, color: 'D5E2E5' }, margin: 0.05, objectName: 'winners table' });
  source(s, C, 'Sumber: btnhousingpreneur.com/kilas-balik, Sumsel Pos, CNBC Indonesia, Akurat, Google Play CIROES, paktukang.com, gridsolr.com; diakses 24 Nov 2026. Relevansi = kedekatan dengan aplikasi Estora, penilaian tim riset.');
}

async function winVisual(pres, C, sec) {
  const s = pres.addSlide({ masterName: 'CONTENT', sectionTitle: sec });
  s.addText('PEMENANG BTN HOUSINGPRENEUR · PRODUK DIGITAL', { placeholder: 'kicker' });
  s.addText('Juara digital menggerakkan layanan fisik, bukan software saja', { placeholder: 'title' });
  const ph = 4.15, pw = ph * 439 / 900;
  s.addImage({ path: A('win_ciroes1.png'), x: 0.6, y: 1.5, w: pw, h: ph, objectName: 'ciroes screen 1', altText: 'Screenshot Play Store CIROES: beranda dengan saldo dan layanan jemput' });
  s.addImage({ path: A('win_ciroes3.png'), x: 0.6 + pw + 0.2, y: 1.5, w: pw, h: ph, objectName: 'ciroes screen 2', altText: 'Screenshot Play Store CIROES' });
  txt(s, 'CIROES · Juara 1 Teknologi 2024', { x: 0.6, y: 5.75, w: 2 * pw + 0.2, h: 0.3, fontSize: 13, bold: true, color: C.text1 });
  txt(s, 'Saldo, Cistore terdekat, harga sampah per kg, jemput terjadwal, langganan', { x: 0.6, y: 6.05, w: 2 * pw + 0.2, h: 0.5, fontSize: 11, color: C.accent5 });
  const rx = 0.6 + 2 * pw + 0.55, rw = 12.72 - rx, iw = (rw - 0.25) / 2, ih = iw * 724 / 1100;
  [['win_paktukang.png', 'Paktukang · Juara 2 Teknologi 2024', 'Survei → RAB terbuka → pengerjaan; 658+ pekerjaan, 158 tukang'], ['win_gridsolr.png', 'KPR Energy (GridSolr) · Juara 3 Value Chain 2025', 'Paket PLTS atap 4,7 kWp, monitoring, ROI 4–5 tahun']].forEach(([f, h, d], i) => {
    const x = rx + i * (iw + 0.25);
    s.addImage({ path: A(f), x, y: 1.5, w: iw, h: ih, objectName: 'winner web ' + i, altText: 'Screenshot situs ' + h });
    txt(s, h, { x, y: 1.6 + ih, w: iw, h: 0.55, fontSize: 13, bold: true, color: C.text1 });
    txt(s, d, { x, y: 2.15 + ih, w: iw, h: 0.55, fontSize: 12, color: C.accent5 });
  });
  card(s, C, rx, 5.25, rw, 1.3, { fill: C.accent1, name: 'common thread' });
  txt(s, 'Benang merahnya: software yang menggerakkan pekerjaan atau barang fisik (sampah, tukang, panel surya), sudah berjalan, dan punya angka. Belum ada pemenang berupa software back-office developer.', { x: rx + 0.25, y: 5.3, w: rw - 0.5, h: 1.2, fontSize: 14, bold: true, color: C.background1, valign: 'middle' });
  source(s, C, 'Sumber: Google Play CIROES (5rb+ unduhan, 4,3★, update 4 Sep 2025); paktukang.com; gridsolr.com. Diakses 24 Nov 2026.');
}

async function winPatterns(pres, C, sec) {
  const s = pres.addSlide({ masterName: 'CONTENT', sectionTitle: sec });
  s.addText('PEMENANG BTN HOUSINGPRENEUR · PELAJARAN', { placeholder: 'kicker' });
  s.addText('Yang dihargai juri, dan cara aplikasi Estora menjawabnya', { placeholder: 'title' });
  txt(s, 'Pola pemenang', { x: 0.6, y: 1.45, w: 5.2, h: 0.32, fontSize: 13, bold: true, color: C.accent2 });
  txt(s, 'Jawaban Estora', { x: 6.45, y: 1.45, w: 6.2, h: 0.32, fontSize: 13, bold: true, color: C.accent1 });
  const rows = [
    [fa.FaChartLine, 'Sudah berjalan, punya angka traksi', 'Tunjukkan alur ujung ke ujung di Harmony Land 5 dengan angka nyata'],
    [fa.FaHelmetSafety, 'Software yang menggerakkan pekerjaan fisik', 'Jejak bukti konstruksi: foto progres, QC, BAST, garansi per unit'],
    [fa.FaBuildingColumns, 'Ada kait pembiayaan BTN', 'Pipeline KPR BTN lebih cepat; pertimbangkan tabungan DP bertahap ala Ontoown'],
    [fa.FaSeedling, 'Dampak terukur', 'Ukur waktu booking sampai akad, komplain selesai sesuai SLA, pembeli MBR terlayani'],
    [fa.FaHandshake, 'Kolaborasi antar-finalis', 'Ajak alumni jadi mitra: Paktukang untuk perbaikan, GridSolr untuk paket PLTS'],
  ];
  for (let i = 0; i < rows.length; i++) {
    const [ic, a, b] = rows[i];
    const y = 1.85 + i * 0.86;
    card(s, C, 0.6, y, 12.12, 0.74, { fill: i % 2 ? 'FFFFFF' : C.background2, name: 'pattern row ' + (i + 1) });
    await iconCircle(s, C, ic, 0.75, y + 0.12, 0.5, C.accent2, a);
    txt(s, a, { x: 1.45, y: y + 0.08, w: 4.6, h: 0.58, fontSize: 14, bold: true, color: C.text1, valign: 'middle' });
    s.addShape('rightArrow', { x: 6.05, y: y + 0.24, w: 0.25, h: 0.26, fill: { color: C.accent1 }, line: { color: C.accent1, width: 0 }, objectName: 'pattern arrow ' + (i + 1) });
    txt(s, b, { x: 6.45, y: y + 0.08, w: 6.1, h: 0.58, fontSize: 14, color: C.text1, valign: 'middle' });
  }
  card(s, C, 0.6, 6.2, 12.12, 0.42, { fill: 'FFF6E3', name: 'risk note' });
  txt(s, 'Risiko: belum pernah ada software back-office yang menang, dan juri 2025 condong ke teknologi fisik, IoT, dan material.', { x: 0.8, y: 6.22, w: 11.8, h: 0.38, fontSize: 13, color: C.text1, valign: 'middle' });
}

module.exports = { phRatings, phGallery, phComplaints, phMatrix, phModule, winTable, winVisual, winPatterns };
