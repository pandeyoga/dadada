// App-domain deck: summary, lifecycle map, pre-handover apps, and implications for Estora's app.
const fa = require('react-icons/fa6');
const { HEX, ASSETS, iconCircle, card, txt, bullets, source, path } = require('./lib');
const A = (f) => path.join(ASSETS, f);

const ST = {
  A: { text: 'Ada', fill: 'D5EBEF', color: HEX.accent1, bold: true },
  S: { text: 'Sebagian', fill: 'FBEBC8', color: '7A4F00', bold: false },
  '-': { text: '—', fill: 'F2F4F4', color: '8A9A9F', bold: false },
};
const cell = (k, fs) => ({ text: ST[k].text, options: { fill: { color: ST[k].fill }, color: ST[k].color, bold: ST[k].bold, align: 'center', valign: 'middle', fontSize: fs } });
const head = (t, o = {}) => ({ text: t, options: Object.assign({ fill: { color: HEX.dk2 }, color: 'FFFFFF', bold: true, valign: 'middle', align: 'center' }, o) });
const plain = (t, o = {}) => ({ text: t, options: Object.assign({ fill: { color: 'FFFFFF' }, color: HEX.dk1, valign: 'middle' }, o) });

function legend(s, C, x, y) {
  [['A', 'ada'], ['S', 'sebagian / klaim'], ['-', 'tidak ada']].forEach(([k, l], i) => {
    const xx = x + i * 2.5;
    s.addShape('roundRect', { x: xx, y, w: 0.85, h: 0.28, rectRadius: 0.05, fill: { color: ST[k].fill }, line: { color: ST[k].fill, width: 0 }, objectName: 'legend ' + k });
    txt(s, ST[k].text, { x: xx, y, w: 0.85, h: 0.28, fontSize: 11, bold: ST[k].bold, color: ST[k].color, align: 'center', valign: 'middle' });
    txt(s, l, { x: xx + 0.95, y, w: 1.5, h: 0.28, fontSize: 11, color: C.accent5, valign: 'middle' });
  });
}

// Lay out phone screenshots (all 900px tall) in a row of fixed height with equal gaps.
function phoneRow(s, C, items, x0, x1, y, h, capY) {
  const minGap = 0.18;
  const sumW = (hh) => items.reduce((a, it) => a + hh * it.w / 900, 0);
  if (sumW(h) + minGap * (items.length - 1) > x1 - x0) h = (x1 - x0 - minGap * (items.length - 1)) / sumW(1);
  const ws = items.map((it) => h * it.w / 900);
  const gap = (x1 - x0 - ws.reduce((a, b) => a + b, 0)) / Math.max(1, items.length - 1);
  const pad = Math.min(gap, 0.5) / 2 - 0.03;
  let x = x0;
  items.forEach((it, i) => {
    s.addImage({ path: A(it.f), x, y, w: ws[i], h, objectName: 'screen ' + it.name, altText: 'Screenshot ' + it.name + (it.cap ? ': ' + it.cap : '') });
    if (it.name) txt(s, it.name, { x: x - pad, y: y + h + 0.1, w: ws[i] + 2 * pad, h: 0.3, fontSize: 13, bold: true, color: C.text1, align: 'center' });
    if (it.cap) txt(s, it.cap, { x: x - pad, y: y + h + 0.4, w: ws[i] + 2 * pad, h: 0.6, fontSize: 11, color: C.accent5, align: 'center' });
    x += ws[i] + gap;
  });
}

async function summary(pres, C, sec) {
  const s = pres.addSlide({ masterName: 'CONTENT', sectionTitle: sec });
  s.addText('RINGKASAN', { placeholder: 'kicker' });
  s.addText('Estora kuat di mesin belakang, kurang di layar untuk pihak luar', { placeholder: 'title' });
  const rows = [
    [fa.FaHouse, 'Rumah Ningrat', 'Empat lapis aplikasi dibangun sendiri. Aplikasi penghuninya paling lengkap di segmen subsidi, tetapi baru 1.000+ unduhan tanpa ulasan; pembeli dilayani lewat web.'],
    [fa.FaPeopleRoof, 'Aplikasi penghuni', 'Rating ditentukan oleh keandalan bayar IPL dan komplain, bukan jumlah fitur. Ciputra Hub turun dari 4,17 ke 1,77; RTPintar 4,6 berkat CS cepat dan kas transparan.'],
    [fa.FaLaptopCode, 'Aplikasi developer', 'Aplikasi gratis BTN menutup stok, SPR, VA, dan status KPR. Pesaing terdekat Porta Pro. Pesaing punya booking + VA, login agen, dan cek kredit instan; Estora belum.'],
    [fa.FaTrophy, 'Pemenang BTN HP', 'Juara digital adalah software yang menggerakkan layanan fisik dan punya angka. Belum ada OS developer yang menang; Ontoown (sewa menjadi DP KPR) paling relevan.'],
  ];
  for (let i = 0; i < rows.length; i++) {
    const [ic, lead, body] = rows[i];
    const y = 1.5 + i * 1.0;
    await iconCircle(s, C, ic, 0.6, y + 0.1, 0.62, C.accent1, lead);
    txt(s, lead, { x: 1.45, y: y + 0.05, w: 2.4, h: 0.7, fontSize: 16, bold: true, color: C.text1, valign: 'middle' });
    txt(s, body, { x: 3.85, y: y + 0.02, w: 8.85, h: 0.85, fontSize: 14, color: C.text1, valign: 'middle' });
  }
  card(s, C, 0.6, 5.55, 12.12, 1.0, { fill: C.accent1, name: 'recommendation' });
  s.addText([
    { text: 'Rekomendasi: ', options: { bold: true } },
    { text: 'bangun layar untuk pembeli, mitra, dan warga di atas mesin yang sudah ada (booking + VA, login mitra, akun warga & tagihan IPL), lalu tunjukkan alur ujung ke ujung dengan angka nyata Harmony Land 5.' },
  ], { isTextBox: true, x: 0.85, y: 5.6, w: 11.7, h: 0.9, fontSize: 15, color: C.background1, margin: 0, valign: 'middle', objectName: 'recommendation text' });
}

async function lifecycle(pres, C, sec) {
  const s = pres.addSlide({ masterName: 'CONTENT', sectionTitle: sec });
  s.addText('PETA APLIKASI', { placeholder: 'kicker' });
  s.addText('Belum ada aplikasi yang menutup seluruh siklus perumahan', { placeholder: 'title' });
  const stages = ['Pemasaran & agen', 'Booking & bayar', 'KPR', 'Konstruksi & QC', 'Serah terima & garansi', 'Pascahuni'];
  const rowsD = [
    ['Estora', 'web/PWA', 'A', 'S', 'A', 'A', 'A', '-'],
    ['Rumah Ningrat', 'in-house, 4 aplikasi', 'A', 'A', 'A', 'S', 'S', 'A'],
    ['Bank & pemerintah', 'BTN Properti Dev, Bale, Tapera', 'S', 'A', 'A', 'S', '-', 'S'],
    ['Software developer', 'Porta Pro, Simandor, Mandep, Ndalem', 'S', 'S', 'S', 'A', 'S', 'S'],
    ['Aplikasi agen', 'Pinhome, Rumah123 Pro, eAgent', 'A', '-', 'S', '-', '-', '-'],
    ['Aplikasi penghuni', 'Ciputra Hub, RTPintar, Klasterin…', '-', '-', '-', '-', 'S', 'A'],
  ];
  const rows = [[head('Kelompok', { align: 'left' }), ...stages.map((st) => head(st))]];
  rowsD.forEach((r, i) => rows.push([
    { text: [{ text: r[0], options: { bold: true, breakLine: true, color: i === 0 ? HEX.accent1 : HEX.dk1 } }, { text: r[1], options: { fontSize: 11, color: HEX.accent5 } }], options: { fill: { color: 'FFFFFF' }, valign: 'middle' } },
    ...r.slice(2).map((k) => cell(k, 13)),
  ]));
  s.addTable(rows, { x: 0.6, y: 1.45, w: 12.12, colW: [3.12, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5], rowH: [0.55, 0.66, 0.66, 0.66, 0.66, 0.66, 0.66], fontSize: 13, border: { type: 'solid', pt: 1, color: 'FFFFFF' }, margin: 0.06, objectName: 'lifecycle coverage table' });
  legend(s, C, 0.6, 6.12);
  txt(s, 'Estora paling dekat ke siklus penuh; lubangnya di booking-bayar online dan pascahuni.', { x: 8.15, y: 6.05, w: 4.57, h: 0.45, fontSize: 12, bold: true, color: C.accent1 });
  source(s, C, 'Sumber: catatan riset aplikasi (Google Play, App Store, situs resmi), diakses 24 Nov 2026. Estora dari inventaris repositori. Penilaian per kelompok memakai aplikasi terbaik di kelompok itu.');
}

async function pre(pres, C, sec) {
  // C1 — BTN Properti for Developer
  {
    const s = pres.addSlide({ masterName: 'CONTENT', sectionTitle: sec });
    s.addText('APLIKASI DEVELOPER · BANK', { placeholder: 'kicker' });
    s.addText('Aplikasi gratis BTN: kuat di KPR, kosong di operasi developer', { placeholder: 'title' });
    phoneRow(s, C, [
      { f: 'pre_btn2.png', w: 506, name: 'Dashboard', cap: 'Penjualan & stok' },
      { f: 'pre_btn3.png', w: 506, name: 'Stok', cap: 'Available / Booked / Sold' },
      { f: 'pre_btn4.png', w: 506, name: 'KPR', cap: 'Draft → Approved / Reject' },
    ], 0.6, 7.75, 1.5, 3.95, 5.55);
    const px = 8.15, pw = 4.57;
    [['10K+', 'unduhan · 4,3★ (56 ulasan)'], ['12.600+', 'developer di Bale Properti'], ['38 rb', 'pengajuan KPR online 2024 (±21% total BTN)']].forEach(([n, l], i) => {
      const y = 1.5 + i * 0.78;
      card(s, C, px, y, pw, 0.66, { fill: C.background2, name: 'btn stat ' + i });
      txt(s, n, { x: px + 0.2, y: y + 0.06, w: 1.45, h: 0.54, fontSize: 22, bold: true, color: C.accent1, valign: 'middle' });
      txt(s, l, { x: px + 1.7, y: y + 0.06, w: pw - 1.85, h: 0.54, fontSize: 12, color: C.text1, valign: 'middle' });
    });
    card(s, C, px, 3.95, pw, 2.6, { fill: 'FFF6E3', name: 'btn lacks' });
    txt(s, 'Tidak ada di aplikasi ini', { x: px + 0.2, y: 4.07, w: pw - 0.4, h: 0.32, fontSize: 14, bold: true, color: C.text1 });
    bullets(s, ['Site plan dan CRM lead', 'Jadwal bayar bertahap dan denda', 'Komisi mitra', 'Progres konstruksi, BAST, garansi', 'Keluhan utama pengguna: gagal login'], { x: px + 0.2, y: 4.45, w: pw - 0.4, h: 2.0, fontSize: 13, color: C.text1, paraSpaceAfter: 3 });
    source(s, C, 'Sumber: Google Play com.btnproperti.developer (v1.0.60, update 21 Nov 2025), Kontan (Bale Properti). Diakses 24 Nov 2026. Estora sebaiknya menyinkronkan stok, SPR, dan status KPR ke aplikasi ini.');
  }
  // C2 — patterns Estora lacks
  {
    const s = pres.addSlide({ masterName: 'CONTENT', sectionTitle: sec });
    s.addText('APLIKASI DEVELOPER · POLA YANG BELUM DIMILIKI ESTORA', { placeholder: 'kicker' });
    s.addText('Enam layar untuk pihak luar yang sudah ada di pesaing', { placeholder: 'title' });
    phoneRow(s, C, [
      { f: 'pre_pesona.png', w: 415, name: 'Pesona Kahuripan', cap: 'Pembeli pilih kavling, bayar VA BTN' },
      { f: 'pre_eagent.png', w: 415, name: 'SML eAgent', cap: 'Agen daftar sendiri; poin & komisi' },
      { f: 'pre_pinhome.png', w: 506, name: 'Pinhome Rekan', cap: 'Simulasi KPR dibagikan agen' },
      { f: 'pre_ideal.png', w: 506, name: 'IDEAL', cap: 'Cek kredit instan untuk pembeli' },
      { f: 'pre_vcloud.png', w: 506, name: 'vCloud+ Approvals', cap: 'Approval batal/alih hak di HP, push' },
      { f: 'pre_porta7.png', w: 426, name: 'Porta Pro', cap: 'Kartu bayar + "Kirim WA Tagihan"' },
    ], 0.6, 12.72, 1.5, 4.0, 5.6);
    source(s, C, 'Sumber: screenshot resmi Google Play tiap aplikasi, diakses 24 Nov 2026. Layar menunjukkan fitur ada, bukan kedalamannya. Estora sudah punya mesin di baliknya: booking fee, fee mitra, pre-screen iDeb, approval, pengingat WA.');
  }
  // C3 — sync problems
  {
    const s = pres.addSlide({ masterName: 'CONTENT', sectionTitle: sec });
    s.addText('APLIKASI DEVELOPER · KELUHAN', { placeholder: 'kicker' });
    s.addText('Status tak sinkron jadi keluhan di aplikasi bank & pemerintah', { placeholder: 'title' });
    const h = 4.95, w = h * 415 / 900;
    s.addImage({ path: A('pre_tapera.png'), x: 0.6, y: 1.5, w, h, objectName: 'tapera screen', altText: 'Screenshot Tapera Mobile: daftar stok rumah subsidi developer' });
    const x = 0.6 + w + 0.4, cw = 12.72 - x;
    const quotes = [
      ['Tapera Mobile · 14 Apr 2026', '"status udah sp3k ... masih di follow up"', 'Status di aplikasi tertinggal dari bank'],
      ['Tapera Mobile · 2026', 'Tidak bisa membatalkan atau pindah bank', 'Pembeli terkunci di satu pengajuan'],
      ['Tapera Mobile · 2026', '"Unit ready" yang tidak ada di lapangan', 'Stok developer di aplikasi tidak akurat'],
      ['BTN Properti for Developer · Jan & Jun 2026', 'Gagal login', 'Admin developer tidak bisa bekerja'],
    ];
    quotes.forEach(([src, q, m], i) => {
      const y = 1.5 + i * 0.98;
      card(s, C, x, y, cw, 0.86, { fill: i % 2 ? 'FFFFFF' : C.background2, name: 'quote ' + i });
      txt(s, src, { x: x + 0.2, y: y + 0.06, w: 3.0, h: 0.74, fontSize: 11, bold: true, color: C.accent5, valign: 'middle' });
      txt(s, q, { x: x + 3.25, y: y + 0.06, w: 3.0, h: 0.74, fontSize: 13, bold: true, color: C.text1, valign: 'middle' });
      txt(s, m, { x: x + 6.35, y: y + 0.06, w: cw - 6.55, h: 0.74, fontSize: 12, color: C.text1, valign: 'middle' });
    });
    card(s, C, x, 5.5, cw, 0.95, { fill: C.accent1, name: 'sync lesson' });
    txt(s, 'Peluang Estora: jadi sumber data unit dan status yang benar, lalu menyinkronkannya ke BTN dan Tapera; ini juga mengisi kriteria kolaborasi ekosistem.', { x: x + 0.2, y: 5.55, w: cw - 0.4, h: 0.85, fontSize: 13, bold: true, color: C.background1, valign: 'middle' });
    source(s, C, 'Sumber: Google Play Tapera Mobile (500rb+, 3,5★ dari 885 ulasan) dan BTN Properti for Developer, ulasan diakses 24 Nov 2026.');
  }
  // C4 — feature matrix
  {
    const s = pres.addSlide({ masterName: 'CONTENT', sectionTitle: sec });
    s.addText('APLIKASI DEVELOPER · PETA FITUR', { placeholder: 'kicker' });
    s.addText('Estora unggul di operasi, kalah di booking-bayar dan mitra', { placeholder: 'title' });
    const cols = ['Fitur', 'Estora', 'BTN Prop. Dev', 'Porta Pro', 'Simandor', 'Mandep', 'Ndalem', 'Pesona Kahuripan', 'Pinhome Rekan'];
    const m = [
      ['Lead & CRM', 'A', '-', 'S', 'A', 'S', 'S', 'S', 'A'],
      ['Stok & site plan', 'A', 'S', 'A', 'A', 'S', 'A', 'A', 'S'],
      ['Booking mandiri pembeli', '-', '-', '-', '-', '-', '-', 'A', '-'],
      ['Bayar online VA/QRIS', '-', 'A', '-', '-', '-', '-', 'A', '-'],
      ['Piutang, termin, denda', 'A', 'S', 'A', 'S', 'S', 'S', '-', '-'],
      ['Pengajuan & status KPR', 'A', 'A', 'A', 'S', '-', 'S', 'S', 'A'],
      ['Cek kredit', 'S', '-', '-', '-', '-', '-', '-', '-'],
      ['Komisi & login mitra', 'S', '-', '-', '-', '-', '-', 'S', 'A'],
      ['Konstruksi berfoto', 'A', '-', 'A', 'A', 'A', 'S', '-', '-'],
      ['BAST & garansi', 'A', '-', 'S', '-', '-', 'S', '-', '-'],
      ['Portal/aplikasi pembeli', 'A', '-', '-', 'A', '-', '-', 'A', '-'],
      ['Offline untuk lapangan', 'A', '-', '-', '-', '-', '-', '-', '-'],
    ];
    const rows = [cols.map((c, i) => head(c, i === 0 ? { align: 'left' } : { fontSize: 12 }))];
    m.forEach((r) => rows.push([plain(r[0], { bold: true, fontSize: 12 }), ...r.slice(1).map((k, j) => { const c = cell(k, 12); if (j === 0) c.options.fill = { color: k === 'A' ? 'BFE1E7' : ST[k].fill }; return c; })]));
    s.addTable(rows, { x: 0.6, y: 1.42, w: 12.12, colW: [2.6, 1.19, 1.19, 1.19, 1.19, 1.19, 1.19, 1.19, 1.19], rowH: [0.5, ...Array(12).fill(0.355)], fontSize: 12, border: { type: 'solid', pt: 1, color: 'FFFFFF' }, margin: 0.04, objectName: 'pre-handover matrix' });
    legend(s, C, 0.6, 6.3);
    source(s, C, 'Sumber: deskripsi toko & screenshot (pesaing), inventaris repositori (Estora), diakses 24 Nov 2026. Pesaing langsung: Porta Pro, Simandor, Mandep, Ndalem. Pesona Kahuripan & Pinhome = acuan fitur.');
  }
}

async function implications(pres, C, sec) {
  // E1 — prioritized gaps
  {
    const s = pres.addSlide({ masterName: 'CONTENT', sectionTitle: sec });
    s.addText('IMPLIKASI · PRIORITAS FITUR', { placeholder: 'kicker' });
    s.addText('Celah aplikasi Estora, diurutkan dari dampak terbesar', { placeholder: 'title' });
    const H = ['#', 'Fitur', 'Bukti dari pesaing & pengguna', 'Mesin yang sudah ada di Estora', 'Usaha'];
    const d = [
      ['1', 'Booking mandiri + bayar VA/QRIS', 'Pesona Kahuripan, Rumah Ningrat (diskon Rp3 jt booking online), VA BTN', 'Booking fee, masa tahan, atribusi', 'Sedang'],
      ['2', 'Login mitra: poin, komisi, link katalog & simulasi KPR', 'SML eAgent, Pinhome Rekan, Mitra Ningrat', 'Mesin fee mitra', 'Sedang'],
      ['3', 'Akun warga otomatis + tagihan IPL + link bayar WA', 'Keluhan #1 aplikasi penghuni; RTPintar 4,6★', 'Portal OTP, piutang, pengingat WA', 'Sedang'],
      ['4', 'Sinkron ke BTN Properti Dev & Tapera', 'Status tak sinkron dikeluhkan di Tapera & BTN', 'Data unit, SPR, status KPR', 'Tinggi*'],
      ['5', 'Cek kredit instan lewat mitra berlisensi', 'IDEAL, Ringkas, "Auto BIC" Rumah Ningrat', 'Pre-screen iDeb manual', 'Sedang'],
      ['6', 'Approval di HP dengan notifikasi push', 'vCloud+ Approvals', 'Approval berlapis (PWA)', 'Rendah'],
    ];
    const rows = [H.map((h, i) => head(h, i >= 1 && i <= 3 ? { align: 'left' } : {}))];
    d.forEach((r, i) => rows.push([
      plain(r[0], { align: 'center', bold: true, color: i < 3 ? HEX.accent2 : HEX.accent5, fontSize: 16 }),
      plain(r[1], { bold: true, fontSize: 13 }), plain(r[2], { fontSize: 12 }), plain(r[3], { fontSize: 12 }),
      plain(r[4], { align: 'center', fontSize: 12 }),
    ]));
    s.addTable(rows, { x: 0.6, y: 1.45, w: 12.12, colW: [0.55, 3.6, 3.9, 2.97, 1.1], rowH: [0.45, ...Array(6).fill(0.68)], fontSize: 12, border: { type: 'solid', pt: 0.75, color: 'D5E2E5' }, margin: 0.06, objectName: 'priority table' });
    txt(s, '* Bergantung pada akses API dari BTN/Tapera; tidak ada API publik yang ditemukan. Mulai dari ekspor data, jangan klaim integrasi.', { x: 0.6, y: 6.05, w: 12.1, h: 0.45, fontSize: 12, color: C.accent5 });
    source(s, C, 'Prioritas = gabungan frekuensi keluhan pengguna, jumlah pesaing yang sudah punya, dan kesiapan mesin Estora. Penilaian tim riset.');
  }
  // E2 — screens to show in the pitch
  {
    const s = pres.addSlide({ masterName: 'CONTENT', sectionTitle: sec });
    s.addText('IMPLIKASI · LAYAR UNTUK PITCH', { placeholder: 'kicker' });
    s.addText('Enam layar yang perlu ditunjukkan ke juri', { placeholder: 'title' });
    const tiles = [
      [fa.FaMapLocationDot, 'Peta kavling → booking → VA', 'Pembeli MBR booking sendiri; angka: waktu booking', 'Keterjangkauan & akses'],
      [fa.FaBuildingColumns, 'Pipeline KPR BTN', 'Status yang dilihat pembeli, sinkron ke BTN; angka: hari booking → akad', 'Sinergi BTN'],
      [fa.FaFileInvoiceDollar, 'Jadwal bayar & denda berjurnal', 'Piutang tunai bertahap rapi; angka: tunggakan turun', 'Kelayakan bisnis'],
      [fa.FaHelmetSafety, 'Progres konstruksi berfoto', 'Software menggerakkan pekerjaan fisik; foto ber-watermark, QC', 'Kematangan teknologi'],
      [fa.FaClipboardCheck, 'BAST → garansi → tiket ber-SLA', 'Keluhan selesai sesuai SLA; angka: % tepat waktu', 'Dampak terukur'],
      [fa.FaPeopleRoof, 'Akun warga & tagihan IPL', 'Pembeli jadi warga tanpa daftar ulang; bayar lewat link WA', 'Keberlanjutan'],
    ];
    const w = 3.88, h = 2.35, gx = 0.24, gy = 0.25;
    for (let i = 0; i < tiles.length; i++) {
      const [ic, t, d, crit] = tiles[i];
      const x = 0.6 + (i % 3) * (w + gx), y = 1.5 + Math.floor(i / 3) * (h + gy);
      card(s, C, x, y, w, h, { fill: C.background2, name: 'screen tile ' + (i + 1) });
      await iconCircle(s, C, ic, x + 0.25, y + 0.25, 0.56, C.accent1, t);
      txt(s, crit, { x: x + 0.95, y: y + 0.32, w: w - 1.15, h: 0.42, fontSize: 11, bold: true, color: C.accent2, valign: 'middle' });
      txt(s, t, { x: x + 0.25, y: y + 0.95, w: w - 0.5, h: 0.4, fontSize: 15, bold: true, color: C.text1 });
      txt(s, d, { x: x + 0.25, y: y + 1.38, w: w - 0.5, h: 0.85, fontSize: 12, color: C.text1 });
    }
    source(s, C, 'Label oranye = kriteria juri yang dijawab layar itu. Layar 1 dan 6 belum ada di Estora; layar 2–5 sudah ada mesinnya.');
  }
  // E3 — method & limits
  {
    const s = pres.addSlide({ masterName: 'CONTENT', sectionTitle: sec });
    s.addText('LAMPIRAN', { placeholder: 'kicker' });
    s.addText('Metode, sumber, dan batas riset aplikasi', { placeholder: 'title' });
    card(s, C, 0.6, 1.5, 5.95, 4.95, { fill: C.background2, name: 'method card' });
    txt(s, 'Metode', { x: 0.85, y: 1.7, w: 5.5, h: 0.4, fontSize: 17, bold: true, color: C.text1 });
    bullets(s, [
      '30+ aplikasi dibandingkan dari etalase resmi Google Play dan App Store, 23–24 Nov 2026.',
      '170+ screenshot toko resmi disimpan di research_notes/ beserta URL sumbernya.',
      'Ulasan: Play berbahasa Indonesia urut terbaru; App Store dari halaman publik (feed RSS kosong).',
      'Halaman web publik dirender dengan Chromium.',
      'Tidak ada login, pendaftaran, uji coba, APK, atau API privat.',
    ], { x: 0.85, y: 2.2, w: 5.5, h: 4.1, fontSize: 14, color: C.text1 });
    card(s, C, 6.77, 1.5, 5.95, 4.95, { fill: 'FFF6E3', name: 'limits card' });
    txt(s, 'Batas yang perlu diingat', { x: 7.02, y: 1.7, w: 5.5, h: 0.4, fontSize: 17, bold: true, color: C.text1 });
    bullets(s, [
      'Screenshot toko adalah materi pemasaran: menunjukkan layar ada, bukan kedalaman fiturnya.',
      'Isi aplikasi di balik login (dashboard mitra, portal pembeli, aplikasi warga) tidak diperiksa.',
      'Sampel ulasan kecil untuk sebagian aplikasi (7–15 ulasan).',
      'Produk beberapa pemenang BTN tidak terverifikasi (RUMAH GOKILS, Dua Mitra Gemilang).',
      'Fitur Estora dari dokumen dan kode, bukan uji fungsional.',
    ], { x: 7.02, y: 2.2, w: 5.5, h: 4.1, fontSize: 14, color: C.text1 });
  }
}

module.exports = { summary, lifecycle, pre, implications };
