// Slides whose content is already established: BTN context and the Rumah Ningrat case.
const fa = require('react-icons/fa6');
const { HEX, ASSETS, iconCircle, card, txt, bullets, source, path } = require('./lib');

const A = (f) => path.join(ASSETS, f);

async function btnTracks(pres, C, sec) {
  const s = pres.addSlide({ masterName: 'CONTENT', sectionTitle: sec });
  s.addText('ARENA · BTN HOUSINGPRENEUR BATCH 3', { placeholder: 'kicker' });
  s.addText('Pendaftaran tutup 30 November; Estora punya dua jalur', { placeholder: 'title' });

  const tracks = [
    { icon: fa.FaGraduationCap, name: 'Mahasiswa', rule: 'Mahasiswa aktif min. D3 · tim maks 5', cats: 'Rumah Nusantara · Housing Design · Housing Innovation', fit: false },
    { icon: fa.FaLightbulb, name: 'Umum (Non-Mahasiswa)', rule: 'Usia ≥ 18 · belum punya usaha atau usaha < 2 tahun · tim maks 3', cats: [['Rumah Nusantara · Housing Design · ', false], ['Housing Innovation', true]], fit: true },
    { icon: fa.FaBuilding, name: 'Developer & Pengusaha', rule: 'Usaha berjalan min. 2 tahun · inovasi sudah diimplementasikan · "hadiah miliaran rupiah"', cats: [['Rumah Nusantara · ', false], ['Housing Ecosystem', true], [' · ', false], ['Housing Tech', true], [' · Housing Design · Affordable Housing · Commercial Housing', false]], fit: true },
  ];
  const x0 = 0.6, w = 3.88, gap = 0.23, y = 1.6, h = 3.35;
  for (let i = 0; i < tracks.length; i++) {
    const t = tracks[i];
    const x = x0 + i * (w + gap);
    card(s, C, x, y, w, h, { fill: t.fit ? C.background2 : 'F6F8F8', line: t.fit ? HEX.accent1 : undefined, name: 'track card ' + t.name });
    await iconCircle(s, C, t.icon, x + 0.3, y + 0.3, 0.62, t.fit ? C.accent1 : C.accent5, t.name);
    txt(s, t.name, { x: x + 1.08, y: y + 0.42, w: w - 1.3, h: 0.45, fontSize: 19, bold: true, color: C.text1 });
    txt(s, t.rule, { x: x + 0.3, y: y + 1.12, w: w - 0.6, h: 0.85, fontSize: 14, color: C.text1 });
    const catRuns = typeof t.cats === 'string'
      ? [{ text: t.cats, options: { color: C.accent5 } }]
      : t.cats.map(([tx, hl]) => ({ text: tx, options: hl ? { bold: true, color: C.accent1 } : { color: C.accent5 } }));
    txt(s, 'Kategori', { x: x + 0.3, y: y + 2.0, w: w - 0.6, h: 0.3, fontSize: 11, bold: true, color: C.accent5 });
    s.addText(catRuns, { isTextBox: true, x: x + 0.3, y: y + 2.3, w: w - 0.6, h: 0.95, fontSize: 14, margin: 0, valign: 'top', objectName: 'track cats ' + t.name });
  }

  card(s, C, 0.6, 5.2, 12.12, 1.25, { fill: 'FFF6E3', name: 'docs callout' });
  await iconCircle(s, C, fa.FaFileLines, 0.85, 5.45, 0.62, C.accent3, 'dokumen');
  s.addText([
    { text: 'Dokumen wajib jalur Developer: ', options: { bold: true } },
    { text: 'pitch deck maksimal 7 slide (Inspiration, Ideation, Solution, Business Model termasuk RAB), company profile, profil proyek dengan titik Google Maps, NPWP perusahaan, KTP dan foto ketua, Pakta Integritas bermeterai. Gratis; boleh mengirim lebih dari satu karya di kategori berbeda.' },
  ], { isTextBox: true, x: 1.7, y: 5.38, w: 10.8, h: 0.95, fontSize: 14, color: C.text1, margin: 0, valign: 'middle', objectName: 'docs text' });
  source(s, C, 'Sumber: btnhousingpreneur.com/kompetisi (tab Mahasiswa, Umum, Developer & Pengusaha; Syarat dan Ketentuan; Dokumen Kelengkapan), diakses 24 Nov 2026.');
  s.addNotes('Tiga jalur peserta. Estora relevan untuk jalur Umum (Housing Innovation) bila usahanya belum 2 tahun, atau jalur Developer & Pengusaha (Housing Ecosystem / Housing Tech) bila usaha sudah berjalan minimal 2 tahun. Batas pendaftaran 30 November 2026.');
}

async function btnCriteria(pres, C, sec) {
  const s = pres.addSlide({ masterName: 'CONTENT', sectionTitle: sec });
  s.addText('ARENA · KRITERIA PENILAIAN', { placeholder: 'kicker' });
  s.addText('Housing Ecosystem paling cocok untuk platform developer', { placeholder: 'title' });

  const labels = ['Housing Tech (Developer)', 'Housing Ecosystem (Developer)', 'Housing Innovation (Umum)'];
  const data = [
    { name: 'Dasar: relevansi, executable, kolaborasi ekosistem', labels, values: [35, 35, 15] },
    { name: 'Rumah fisik: keterjangkauan, kelayakhunian, keberlanjutan', labels, values: [65, 0, 0] },
    { name: 'Teknologi, bisnis & dampak', labels, values: [0, 65, 85] },
  ];
  s.addChart(pres.charts.BAR, data, {
    x: 0.6, y: 1.55, w: 7.3, h: 4.9, barDir: 'bar', barGrouping: 'stacked', barGapWidthPct: 55,
    chartColors: [HEX.accent5, HEX.accent2, HEX.accent1],
    showValue: true, dataLabelPosition: 'ctr', dataLabelColor: 'FFFFFF', dataLabelFontSize: 13, dataLabelFontBold: true, dataLabelFontFace: '+mn-lt',
    dataLabelFormatCode: '0"%";;;',
    catAxisLabelColor: HEX.dk1, catAxisLabelFontSize: 13, catAxisLabelFontFace: '+mn-lt', catAxisOrientation: 'maxMin',
    valAxisHidden: true, valAxisMaxVal: 100, valAxisMinVal: 0,
    valGridLine: { style: 'none' }, catGridLine: { style: 'none' },
    showLegend: true, legendPos: 'b', legendFontSize: 12, legendFontFace: '+mn-lt', legendColor: HEX.dk1,
    showTitle: true, title: 'Komposisi bobot penilaian (%)', titleFontSize: 14, titleColor: HEX.dk1, titleFontFace: '+mn-lt',
    objectName: 'criteria weight chart', altText: 'Bobot penilaian tiga kategori: Housing Tech 65% rumah fisik; Housing Ecosystem 65% teknologi dan bisnis; Housing Innovation 85% teknologi, bisnis dan dampak',
  });

  card(s, C, 8.25, 1.55, 4.47, 4.9, { fill: C.background2, name: 'criteria commentary' });
  bullets(s, [
    [{ text: 'Housing Tech: ', options: { bold: true } }, { text: 'keterjangkauan 30%, kelayakhunian 20%, keberlanjutan 15%. Software harus membuktikan dampaknya ke harga dan mutu rumah.' }],
    [{ text: 'Housing Ecosystem: ', options: { bold: true } }, { text: 'kematangan teknologi 25%, skalabilitas 20%, kelayakan bisnis 20%. Cakupannya dari perencanaan sampai layanan purna bangun.' }],
    [{ text: 'Housing Innovation: ', options: { bold: true } }, { text: 'orisinalitas & kesiapan 25%, dampak 25%. Contoh resmi: "platform terintegrasi pencarian, pembiayaan, pengelolaan hunian".' }],
  ], { x: 8.5, y: 1.8, w: 4.0, h: 3.3, fontSize: 14, color: C.text1 });
  card(s, C, 8.5, 5.15, 3.97, 1.1, { fill: C.accent1, name: 'recommendation' });
  txt(s, 'Usaha ≥ 2 tahun → Housing Ecosystem. Usaha < 2 tahun → Housing Innovation.', { x: 8.7, y: 5.25, w: 3.6, h: 0.9, fontSize: 14, bold: true, color: C.background1, valign: 'middle' });
  source(s, C, 'Sumber: btnhousingpreneur.com/kompetisi, diakses 24 Nov 2026. Pengelompokan bobot oleh tim riset; label "Dampak" dihitung ke kelompok teknologi, bisnis & dampak.');
  s.addNotes('Bobot asli: Housing Tech = Relevansi 10, Executable 15, Kolaborasi 10, Keterjangkauan 30, Kelayakhunian 20, Keberlanjutan 15. Housing Ecosystem = Relevansi 10, Executable 15, Kolaborasi 10, Skalabilitas & Replikasi 20, Kelayakan Bisnis 20, Keunggulan & Kematangan Teknologi 25. Housing Innovation (Umum) = Relevansi 15, Orisinalitas & Kesiapan Wujud 25, Dampak 25, Skalabilitas & Replikasi 20, Kelayakan Bisnis 15.');
}

async function rnProfile(pres, C, sec) {
  const s = pres.addSlide({ masterName: 'CONTENT', sectionTitle: sec });
  s.addText('STUDI KASUS · RUMAH NINGRAT', { placeholder: 'kicker' });
  s.addText('Developer subsidi regional dengan skala nasional', { placeholder: 'title' });
  const stats = [
    ['10.000+', 'unit terjual', 'klaim perusahaan'],
    ['32', 'perumahan', 'klaim; kanal lain menyebut 25+ atau 45+'],
    ['Rp166 jt', 'harga rumah tipe 30/60', 'Bekasi Rp185 jt; booking mulai Rp100 rb'],
    ['7', 'kota/kabupaten', 'Cirebon, Kuningan, Majalengka, Indramayu, Subang, Kendal, Bekasi'],
  ];
  const w = 2.85, gap = 0.24;
  stats.forEach(([n, l, sub], i) => {
    const x = 0.6 + i * (w + gap);
    card(s, C, x, 1.65, w, 2.55, { fill: C.background2, name: 'stat ' + l });
    txt(s, n, { x: x + 0.25, y: 1.85, w: w - 0.5, h: 0.85, fontSize: 40, bold: true, color: C.accent1 });
    txt(s, l, { x: x + 0.25, y: 2.75, w: w - 0.5, h: 0.4, fontSize: 16, bold: true, color: C.text1 });
    txt(s, sub, { x: x + 0.25, y: 3.17, w: w - 0.5, h: 0.9, fontSize: 12, color: C.accent5 });
  });
  card(s, C, 0.6, 4.45, 12.12, 1.95, { fill: 'FFFFFF', line: 'D5E2E5', name: 'identity card' });
  bullets(s, [
    [{ text: 'Siapa: ', options: { bold: true } }, { text: 'merek perumahan PT Raja Sukses Propertindo, unit properti Trusmi Group (pemilik Batik Trusmi), Cirebon. Berdiri 24 Maret 2013; bernama Trusmiland sampai April 2023. Pendiri & CEO: Ibnu Riyanto.' }],
    [{ text: 'Model: ', options: { bold: true } }, { text: 'rumah subsidi berharga patokan pemerintah, dibiayai KPR bank (terutama BTN). Pembeda: pagar dan tembok belakang gratis, one-gate, CCTV per blok, dan aplikasi penghuni.' }],
    [{ text: 'Validasi luar: ', options: { bold: true } }, { text: 'BTN "Developer Subsidi Terbaik 2023". Halaman penghargaan di situsnya sendiri masih berisi teks percobaan ("2028", "test").' }],
  ], { x: 0.85, y: 4.62, w: 11.6, h: 1.7, fontSize: 14, color: C.text1 });
  source(s, C, 'Sumber: rumahningrat.com, rumahningratgold.com, mitra.rumahningrat.com; Kompas (2 Jun 2024); Liputan6 (31 Mei 2024); Radar Cirebon (17 Apr 2023). Diakses 23–24 Nov 2026.');
}

async function rnStack(pres, C, sec) {
  const s = pres.addSlide({ masterName: 'CONTENT', sectionTitle: sec });
  s.addText('STUDI KASUS · EKOSISTEM DIGITAL', { placeholder: 'kicker' });
  s.addText('Empat lapis digital, semuanya dibangun sendiri', { placeholder: 'title' });
  const nodes = [
    { stage: 'AKUISISI', icon: fa.FaGlobe, name: 'Booking mandiri', host: 'rumahningrat.com', pts: 'Pilih kavling per blok · booking Rp100 rb · diskon Rp3 jt untuk booking online · BI checking otomatis' },
    { stage: 'DISTRIBUSI', icon: fa.FaHandshake, name: 'Mitra Ningrat', host: 'mitra.rumahningrat.com', pts: 'Agen & afiliasi daftar mandiri · komisi berjenjang · halaman pribadi per agen · leaderboard' },
    { stage: 'TRANSAKSI', icon: fa.FaClipboardCheck, name: 'Dashboard Warga', host: 'customer.rumahningrat.com', pts: 'Status KPR · progres bangun · riwayat bayar · komplain · login dengan nomor KTP' },
    { stage: 'PASCAHUNI', icon: fa.FaMobileScreenButton, name: 'Keluarga Ningrat', host: 'Android & iOS', pts: 'Tagihan IPL · live CCTV · gate geofence · SOS · marketplace · PPOB' },
  ];
  const w = 2.78, gap = 0.33, y = 1.75;
  for (let i = 0; i < nodes.length; i++) {
    const n = nodes[i];
    const x = 0.6 + i * (w + gap);
    txt(s, n.stage, { x, y, w, h: 0.3, fontSize: 12, bold: true, color: C.accent2, charSpacing: 1 });
    card(s, C, x, y + 0.38, w, 3.45, { fill: C.background2, name: 'layer ' + n.name });
    await iconCircle(s, C, n.icon, x + 0.25, y + 0.62, 0.6, C.accent1, n.name);
    txt(s, n.name, { x: x + 0.25, y: y + 1.35, w: w - 0.5, h: 0.4, fontSize: 17, bold: true, color: C.text1 });
    txt(s, n.host, { x: x + 0.25, y: y + 1.75, w: w - 0.5, h: 0.3, fontSize: 11, color: C.accent5 });
    txt(s, n.pts, { x: x + 0.25, y: y + 2.12, w: w - 0.5, h: 1.6, fontSize: 13, color: C.text1 });
    if (i < nodes.length - 1) {
      s.addShape('rightArrow', { x: x + w + 0.05, y: y + 1.9, w: 0.23, h: 0.32, fill: { color: C.accent2 }, line: { color: C.accent2, width: 0 }, objectName: 'flow arrow ' + (i + 1) });
    }
  }
  card(s, C, 0.6, 5.75, 12.12, 0.8, { fill: 'FFF6E3', name: 'governance note' });
  s.addText([
    { text: 'Dibangun IT Trusmi Group, tanpa vendor. ', options: { bold: true } },
    { text: 'Tata kelolanya tertinggal: akun toko aplikasi atas nama perorangan, label privasi "tidak mengumpulkan data", domain tersebar ke 5+ alamat.' },
  ], { isTextBox: true, x: 0.85, y: 5.8, w: 11.7, h: 0.7, fontSize: 14, color: C.text1, margin: 0, valign: 'middle', objectName: 'governance text' });
  source(s, C, 'Sumber: situs dan subdomain rumahningrat.com, Google Play & App Store (com.trusmi.keluarganingrat), rnliving.rumahningrat.com. Diakses 23–24 Nov 2026.');
}

async function rnApp(pres, C, sec) {
  const s = pres.addSlide({ masterName: 'CONTENT', sectionTitle: sec });
  s.addText('STUDI KASUS · APLIKASI PENGHUNI', { placeholder: 'kicker' });
  s.addText('Aplikasi penghuni: fitur lengkap, pengguna masih tipis', { placeholder: 'title' });
  const phones = [['app_02.png', 'Beranda warga'], ['app_04.png', 'Gate dengan cek lokasi GPS'], ['app_08.png', 'Bayar IPL via virtual account']];
  const ph = 4.55, pw = ph * 480 / 1039;
  phones.forEach(([f, cap], i) => {
    const x = 0.6 + i * (pw + 0.32);
    s.addImage({ path: A(f), x, y: 1.55, w: pw, h: ph, objectName: 'phone ' + cap, altText: 'Screenshot aplikasi Keluarga Ningrat: ' + cap });
    txt(s, cap, { x, y: 6.15, w: pw, h: 0.4, fontSize: 12, color: C.accent5, align: 'center' });
  });
  const px = 8.35, pw2 = 4.37;
  const stats = [['1.000+', 'unduhan Android; iOS tak dipublikasikan'], ['0', 'rating dan ulasan di kedua toko'], ['±10–22%', 'perkiraan rumah tangga yang memasang (vs 10.000 unit)']];
  stats.forEach(([n, l], i) => {
    const y = 1.55 + i * 1.02;
    card(s, C, px, y, pw2, 0.88, { fill: C.background2, name: 'app stat ' + i });
    txt(s, n, { x: px + 0.2, y: y + 0.12, w: 1.75, h: 0.64, fontSize: 26, bold: true, color: C.accent1, valign: 'middle' });
    txt(s, l, { x: px + 1.95, y: y + 0.12, w: pw2 - 2.1, h: 0.64, fontSize: 13, color: C.text1, valign: 'middle' });
  });
  card(s, C, px, 4.68, pw2, 1.85, { fill: 'FFFFFF', line: 'D5E2E5', name: 'tech notes' });
  bullets(s, [
    'CCTV memakai kamera konsumen EZVIZ',
    'IPL & PPOB dibayar lewat VA Permata dan BRI, tanda pakai payment gateway',
    'Gate menolak buka bila lokasi tidak sesuai (geofence)',
    'Isi aplikasi hanya terbuka untuk penghuni terdaftar',
  ], { x: px + 0.2, y: 4.8, w: pw2 - 0.4, h: 1.65, fontSize: 13, color: C.text1, paraSpaceAfter: 3 });
  source(s, C, 'Sumber: screenshot resmi App Store id6752388007 & Google Play com.trusmi.keluarganingrat (v1.0.11, 20 Nov 2026). Persentase adopsi adalah estimasi tim riset, bukan angka perusahaan.');
}

async function rnMitra(pres, C, sec) {
  const s = pres.addSlide({ masterName: 'CONTENT', sectionTitle: sec });
  s.addText('STUDI KASUS · PORTAL MITRA', { placeholder: 'kicker' });
  s.addText('Portal mitra menjadikan agen kanal distribusi', { placeholder: 'title' });
  s.addImage({ path: A('mitra_tools.png'), x: 0.6, y: 1.55, w: 6.15, h: 6.15 * 999 / 1400, objectName: 'mitra tools screenshot', altText: 'Bagian Tools portal Mitra Ningrat: landing page personal, website pribadi, Mitra Apps monitoring referral' });
  const sh = 4.85, sw = sh * 860 / 1640;
  s.addImage({ path: A('mitra_sim.png'), x: 6.95, y: 1.5, w: sw, h: sh, objectName: 'kpr simulator screenshot', altText: 'Simulator KPR di halaman produk Mitra Ningrat' });
  const tx = 6.95 + sw + 0.3, tw = 12.72 - tx;
  bullets(s, [
    [{ text: 'Daftar mandiri 4 tahap: ', options: { bold: true } }, { text: 'akun, data pribadi, rekening bank, media sosial' }],
    [{ text: 'Komisi berjenjang ', options: { bold: true } }, { text: 'plus bonus kinerja dan poin' }],
    [{ text: 'Halaman pribadi per agen ', options: { bold: true } }, { text: 'dengan listing dan bank konten' }],
    [{ text: 'Halaman produk publik ', options: { bold: true } }, { text: 'dengan simulator KPR dan tombol Share' }],
    [{ text: 'Leaderboard: ', options: { bold: true } }, { text: '#1 Cirebon memegang 36 listing' }],
  ], { x: tx, y: 1.6, w: tw, h: 4.8, fontSize: 14, color: C.text1, paraSpaceAfter: 8 });
  txt(s, 'Portal web, bukan aplikasi di toko. Dashboard agen terkunci login dan tidak diperiksa.', { x: 0.6, y: 6.05, w: 6.15, h: 0.45, fontSize: 12, color: C.accent5 });
  source(s, C, 'Sumber: mitra.rumahningrat.com (landing, /register, /product/32-trusmiland-cikoneng-majalengka), dirender 24 Nov 2026.');
}

async function rnRisk(pres, C, sec) {
  const s = pres.addSlide({ masterName: 'CONTENT', sectionTitle: sec });
  s.addText('STUDI KASUS · REPUTASI', { placeholder: 'kicker' });
  s.addText('Risiko terbesarnya di mutu tapak, bukan di aplikasi', { placeholder: 'title' });
  txt(s, 'Trusmiland Klayan Tahap 5 (Kab. Cirebon)', { x: 0.6, y: 1.55, w: 7.4, h: 0.4, fontSize: 17, bold: true, color: C.text1 });
  const ev = [
    ['2023', 'Banjir pertama, sebelum perumahan resmi dihuni'],
    ['11 Sep 2026', 'Petisi ratusan warga dibawa ke DPRD dan Bupati'],
    ['18 Sep & 20 Okt', 'Dua mediasi dengan pengembang gagal'],
    ['26 Okt 2026', 'Komisi III DPRD minta pembangunan dihentikan sementara'],
  ];
  const lx = 0.85;
  s.addShape('line', { x: lx + 0.14, y: 2.25, w: 0, h: 3.1, line: { color: HEX.accent2, width: 2 }, objectName: 'timeline spine' });
  ev.forEach(([d, t], i) => {
    const y = 2.1 + i * 0.95;
    s.addShape('ellipse', { x: lx, y: y + 0.02, w: 0.3, h: 0.3, fill: { color: C.accent2 }, line: { color: 'FFFFFF', width: 2 }, objectName: 'timeline dot ' + (i + 1) });
    txt(s, d, { x: lx + 0.55, y, w: 2.0, h: 0.35, fontSize: 14, bold: true, color: C.accent2 });
    txt(s, t, { x: lx + 2.6, y, w: 4.6, h: 0.75, fontSize: 14, color: C.text1 });
  });
  card(s, C, 8.35, 1.55, 4.37, 2.55, { fill: C.background2, name: 'plangon card' });
  txt(s, 'Bukit Plangon, Kec. Sumber', { x: 8.6, y: 1.72, w: 3.9, h: 0.4, fontSize: 16, bold: true, color: C.text1 });
  bullets(s, [
    'Dikaitkan dengan banjir kantor Pemkab, 23 Des 2025',
    'Izin dilaporkan dicabut, aktivitas disebut tetap jalan (Feb–Mar 2026)',
    '28 Apr 2026: ultimatum DPRD, hijaukan bukit, keruk sungai',
  ], { x: 8.6, y: 2.18, w: 3.95, h: 1.85, fontSize: 13, color: C.text1, paraSpaceAfter: 4 });
  card(s, C, 8.35, 4.3, 4.37, 2.15, { fill: C.accent1, name: 'lesson card' });
  txt(s, 'Pelajaran untuk Estora', { x: 8.6, y: 4.45, w: 3.9, h: 0.35, fontSize: 15, bold: true, color: C.background1 });
  txt(s, 'Tab komplain sudah ada, tapi keluhan tidak tersambung ke data elevasi, drainase, dan serah terima PSU. Sambungan itulah yang belum dimiliki siapa pun.', { x: 8.6, y: 4.85, w: 3.9, h: 1.5, fontSize: 13, color: C.background1 });
  source(s, C, 'Sumber: Kabarbaru.co (11 Sep & 26 Okt 2026), Alexanews (26 Okt 2026), Ciremai Today (9 Feb 2026), Jabar Publisher (29 Apr 2026). Tidak ada temuan penipuan, proyek mangkrak, atau putusan sengketa konsumen.');
}

module.exports = { btnTracks, btnCriteria, rnProfile, rnStack, rnApp, rnMitra, rnRisk };
