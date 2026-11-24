// Deck: dissection of BTN Housingpreneur winners (Batch 1 2024, Batch 2 2025) and what it means for Estora.
const fa = require('react-icons/fa6');
const { HEX, ASSETS, iconCircle, card, txt, bullets, source, path } = require('./lib');
const { dissect, fitRow } = require('./slides_bedah_lib');
const I = (f, w, h, alt) => ({ path: path.join(ASSETS, 'bd', f + '.png'), w, h, alt });
const A2 = (f) => path.join(ASSETS, f);

const head = (t, o = {}) => ({ text: t, options: Object.assign({ fill: { color: HEX.dk2 }, color: 'FFFFFF', bold: true, valign: 'middle', align: 'center' }, o) });
const plain = (t, o = {}) => ({ text: t, options: Object.assign({ fill: { color: 'FFFFFF' }, color: HEX.dk1, valign: 'middle' }, o) });
const YN = { Ya: ['D5EBEF', HEX.accent1, true], Sebagian: ['FBEBC8', '7A4F00', false], Tidak: ['F2F4F4', '8A9A9F', false] };
const yn = (k) => ({ text: k, options: { fill: { color: YN[k][0] }, color: YN[k][1], bold: YN[k][2], align: 'center', valign: 'middle', fontSize: 11 } });

// ---------------- Opening ----------------
async function opening(pres, C, sec) {
  // Summary
  {
    const s = pres.addSlide({ masterName: 'CONTENT', sectionTitle: sec });
    s.addText('RINGKASAN', { placeholder: 'kicker' });
    s.addText('Pemenang menang dengan bukti fisik, bukan software saja', { placeholder: 'title' });
    const rows = [
      [fa.FaTrophy, 'Siapa yang menang', '47 juara dalam dua batch. Hanya 5 produk murni digital, dan tidak satu pun berupa software operasional developer.'],
      [fa.FaFlask, 'Kenapa menang', 'Juara Established punya wujud nyata, bukti pihak ketiga (uji Sucofindo, sertifikat BGH, uji meja getar), dan satu angka dampak yang mudah diingat.'],
      [fa.FaLayerGroup, 'Peran digital', 'Digital selalu menjadi lapisan di atas layanan atau perangkat fisik: penjemputan sampah, tukang, pelatihan, panel surya, IoT listrik.'],
      [fa.FaBuildingColumns, 'Sinergi BTN', 'Sinergi setelah menang selalu berbentuk KPR unit, pasokan program BTN, atau kawasan NPL. Dua juara digital 2024 tidak tercatat mendapat kerja sama dengan BTN.'],
      [fa.FaStar, 'Temuan khusus', 'PT Harmony Land Group adalah juara Eco House Design 2024 dan tercatat punya sinergi BTN (kawasan NPL). Perlu dicek hubungannya dengan Estora.'],
    ];
    for (let i = 0; i < rows.length; i++) {
      const [ic, lead, body] = rows[i];
      const y = 1.45 + i * 0.86;
      await iconCircle(s, C, ic, 0.6, y + 0.08, 0.56, i === 4 ? C.accent3 : C.accent1, lead);
      txt(s, lead, { x: 1.35, y: y + 0.02, w: 2.35, h: 0.7, fontSize: 15, bold: true, color: C.text1, valign: 'middle' });
      txt(s, body, { x: 3.75, y, w: 8.95, h: 0.78, fontSize: 14, color: C.text1, valign: 'middle' });
    }
    card(s, C, 0.6, 5.8, 12.12, 0.78, { fill: C.accent1, name: 'recommendation' });
    s.addText([{ text: 'Implikasi: ', options: { bold: true } }, { text: 'Estora harus tampil sebagai software yang menggerakkan pembangunan rumah sungguhan, dengan angka nyata, bukti pihak ketiga, dan janji sinergi yang bisa dihitung BTN dalam akad KPR.' }],
      { isTextBox: true, x: 0.85, y: 5.82, w: 11.7, h: 0.74, fontSize: 14, color: C.background1, margin: 0, valign: 'middle', objectName: 'implication text' });
  }
  // Competition numbers
  {
    const s = pres.addSlide({ masterName: 'CONTENT', sectionTitle: sec });
    s.addText('KOMPETISI · ANGKA', { placeholder: 'kicker' });
    s.addText('Dari 1.171 karya hanya 27 juara; hadiah Established Rp100 jt', { placeholder: 'title' });
    txt(s, 'Corong seleksi Batch 2 (2025)', { x: 0.6, y: 1.45, w: 6.4, h: 0.35, fontSize: 15, bold: true, color: C.text1 });
    const funnel = [['1.171', 'karya masuk'], ['746', 'evaluasi ide bisnis'], ['181', 'live pitching (±10 per kategori Established)'], ['58', 'finalis Grand Judging'], ['27', 'juara']];
    funnel.forEach(([n, l], i) => {
      const w = 6.3 - i * 0.95, x = 0.6 + (6.3 - w) / 2, y = 1.9 + i * 0.78;
      s.addShape('roundRect', { x, y, w, h: 0.66, rectRadius: 0.08, fill: { color: i === 4 ? HEX.accent2 : HEX.accent1 }, line: { color: 'FFFFFF', width: 0 }, objectName: 'funnel ' + i });
      txt(s, n, { x, y, w: 1.4, h: 0.66, fontSize: 18, bold: true, color: C.background1, align: 'center', valign: 'middle' });
      txt(s, l, { x: x + 1.35, y, w: w - 1.45, h: 0.66, fontSize: 12, color: C.background1, valign: 'middle' });
    });
    txt(s, 'Batch 1 (2024): 946 tim, 20 juara dari 4 kelompok kategori.', { x: 0.6, y: 5.9, w: 6.4, h: 0.4, fontSize: 13, color: C.accent5 });
    const rows = [[head('Kelompok', { align: 'left' }), head('Juara 1'), head('Juara 2'), head('Juara 3')],
      [plain('Established: Technology, Value Chain, Affordable', { bold: true }), plain('Rp100 jt', { align: 'center', bold: true, color: HEX.accent1 }), plain('Rp70 jt', { align: 'center' }), plain('Rp50 jt', { align: 'center' })],
      [plain('Established: House Design', { bold: true }), plain('Rp85 jt', { align: 'center' }), plain('—', { align: 'center' }), plain('—', { align: 'center' })],
      [plain('Umum (non-mahasiswa)', { bold: true }), plain('Rp65 jt', { align: 'center' }), plain('Rp45 jt', { align: 'center' }), plain('Rp25–50 jt', { align: 'center' })],
      [plain('Mahasiswa', { bold: true }), plain('Rp55 jt', { align: 'center' }), plain('Rp35 jt', { align: 'center' }), plain('Rp20 jt', { align: 'center' })]];
    txt(s, 'Hadiah per peringkat 2025 (dari papan cek di foto resmi)', { x: 7.3, y: 1.45, w: 5.4, h: 0.35, fontSize: 15, bold: true, color: C.text1 });
    s.addTable(rows, { x: 7.3, y: 1.9, w: 5.42, colW: [2.6, 0.94, 0.94, 0.94], rowH: 0.56, fontSize: 12, border: { type: 'solid', pt: 0.75, color: 'D5E2E5' }, margin: 0.06, objectName: 'prize table' });
    card(s, C, 7.3, 4.95, 5.42, 1.35, { fill: 'FFF6E3', name: 'prize note' });
    txt(s, 'Total hadiah Rp1 M (2024) dan Rp1,5 M (2025). Menurut seorang juri 2025, perusahaan mapan ikut bukan demi hadiah, tetapi demi "orderan dari developer-developer" mitra BTN.', { x: 7.5, y: 5.02, w: 5.05, h: 1.2, fontSize: 12, color: C.text1, valign: 'middle' });
    source(s, C, 'Sumber: btnhousingpreneur.com/kilas-balik (corong & foto papan hadiah), Sumsel Pos (Batch 1), Metro TV. Diakses 24 Nov 2026. Hadiah House Design mahasiswa tidak terbaca di foto.');
  }
  // Judges and BTN
  {
    const s = pres.addSlide({ masterName: 'CONTENT', sectionTitle: sec });
    s.addText('KOMPETISI · JURI & BTN', { placeholder: 'kicker' });
    s.addText('BTN mencari inovasi yang bisa dibiayai dan diperbesar', { placeholder: 'title' });
    card(s, C, 0.6, 1.45, 5.6, 5.05, { fill: 'F3F6F7', name: 'pitch photo panel' });
    fitRow(s, [I('b1_auto_pitch', 770, 513, 'Foto Grand Judging Batch 1: slide Autoconz "Inspiration: 12 juta keluarga Indonesia masih menunggu rumah yang layak"')], 0.75, 1.6, 5.3, 3.55);
    txt(s, 'Grand Judging 13 Feb 2025, Menara BTN: pitch Autoconz dibuka dengan slide "INSPIRATION: 12 juta keluarga Indonesia masih menunggu rumah yang layak", sesuai struktur dokumen resmi.', { x: 0.8, y: 5.25, w: 5.2, h: 1.15, fontSize: 12, color: C.text1 });
    const q = [
      ['Setiyo Wibowo, Direktur BTN (2025)', 'Ide yang "layak dibiayai perbankan", "bankable", proptech, dan mitra yang bisa "di-scale up".'],
      ['Nixon Napitupulu, Dirut BTN (2025)', 'Ajang "event matching" antara developer dan anak muda pemasok desain serta material.'],
      ['Ryan M. Tallulah, juri 2025 (BARDI)', 'Perusahaan mapan ikut bukan demi hadiah, tapi demi "orderan dari developer-developer" mitra BTN.'],
      ['Ridwan Kamil, juri 2024', 'Memuji "inovasi material baru ramah lingkungan" dan menyinggung perubahan iklim.'],
    ];
    q.forEach(([who, what], i) => {
      const y = 1.45 + i * 1.27;
      card(s, C, 6.45, y, 6.27, 1.15, { fill: i % 2 ? 'FFFFFF' : C.background2, name: 'quote ' + i });
      txt(s, who, { x: 6.65, y: y + 0.1, w: 5.9, h: 0.3, fontSize: 12, bold: true, color: C.accent2 });
      txt(s, what, { x: 6.65, y: y + 0.42, w: 5.9, h: 0.68, fontSize: 13, color: C.text1 });
    });
    source(s, C, 'Sumber: Kompasiana (foto Grand Judging Autoconz), Antara, Investortrust, Metro TV, CNBC Indonesia, Beritajatim. Juri Batch 1 juga Yu Sing (AKANOMA). Alasan menang per juara tidak pernah dipublikasikan.');
  }
  // Type distribution
  {
    const s = pres.addSlide({ masterName: 'CONTENT', sectionTitle: sec });
    s.addText('KOMPETISI · JENIS KARYA JUARA', { placeholder: 'kicker' });
    s.addText('47 juara: hanya 5 murni digital, nol software developer', { placeholder: 'title' });
    const labels = ['Batch 1 (2024) · 20 juara', 'Batch 2 (2025) · 27 juara'];
    s.addChart(pres.charts.BAR, [
      { name: 'Digital', labels, values: [3, 2] },
      { name: 'Hybrid (alat + aplikasi)', labels, values: [0, 3] },
      { name: 'Fisik: material, jasa, model', labels, values: [3, 7] },
      { name: 'Desain rumah', labels, values: [9, 11] },
      { name: 'Developer perumahan', labels, values: [4, 4] },
      { name: 'Tidak diketahui', labels, values: [1, 0] },
    ], {
      x: 0.6, y: 1.45, w: 7.6, h: 5.05, barDir: 'bar', barGrouping: 'stacked', barGapWidthPct: 45,
      chartColors: [HEX.accent1, HEX.accent4, HEX.accent2, HEX.accent3, HEX.accent5, 'C9D3D6'],
      showValue: true, dataLabelPosition: 'ctr', dataLabelFormatCode: '0;;;', dataLabelColor: 'FFFFFF', dataLabelFontSize: 13, dataLabelFontBold: true, dataLabelFontFace: '+mn-lt',
      catAxisLabelColor: HEX.dk1, catAxisLabelFontSize: 13, catAxisLabelFontFace: '+mn-lt', catAxisOrientation: 'maxMin',
      valAxisHidden: true, valGridLine: { style: 'none' }, catGridLine: { style: 'none' },
      showLegend: true, legendPos: 'b', legendFontSize: 11, legendFontFace: '+mn-lt', legendColor: HEX.dk1,
      showTitle: true, title: 'Jumlah juara menurut jenis karya', titleFontSize: 14, titleColor: HEX.dk1, titleFontFace: '+mn-lt',
      objectName: 'winner type chart', altText: 'Jenis karya juara: Batch 1 3 digital, 3 fisik, 9 desain, 4 developer, 1 tidak diketahui; Batch 2 2 digital, 3 hybrid, 7 fisik, 11 desain, 4 developer',
    });
    card(s, C, 8.5, 1.45, 4.22, 5.05, { fill: C.background2, name: 'digital winners card' });
    txt(s, 'Yang digital atau hybrid', { x: 8.72, y: 1.6, w: 3.8, h: 0.35, fontSize: 15, bold: true, color: C.text1 });
    bullets(s, [
      [{ text: '2024: ', options: { bold: true } }, { text: 'CIROES (aplikasi bank sampah), Paktukang (platform tukang), Platform Rusun Swadaya (konsep)' }],
      [{ text: '2025 digital: ', options: { bold: true } }, { text: 'TRAIN-O (pelatihan tukang), GeoFloodAI (skor risiko banjir)' }],
      [{ text: '2025 hybrid: ', options: { bold: true } }, { text: 'AITOMA dan myECO (IoT hemat listrik), KPR Energy (PLTS + aplikasi monitor)' }],
    ], { x: 8.72, y: 2.05, w: 3.85, h: 3.1, fontSize: 13, color: C.text1, paraSpaceAfter: 6 });
    card(s, C, 8.72, 5.2, 3.78, 1.1, { fill: C.accent1, name: 'gap card' });
    txt(s, 'Celah: belum ada juara yang mengurus operasi developer dari booking sampai serah terima.', { x: 8.88, y: 5.25, w: 3.5, h: 1.0, fontSize: 12, bold: true, color: C.background1, valign: 'middle' });
    source(s, C, 'Klasifikasi tim riset dari deskripsi produk publik (Kilas Balik, Sumsel Pos, situs pemenang). "Fisik" mencakup material, jasa, prototipe, dan model kelembagaan.');
  }
}

// ---------------- Batch 1 ----------------
function batch1(pres, C, sec) {
  dissect(pres, C, sec, {
    kicker: 'BATCH 1 · 2024 · TECHNOLOGY', title: 'CIROES: aplikasi bank sampah yang melayani perumahan',
    meta: 'Juara 1 Technology (Established) · PT Inovasi Keberlanjutan Indonesia · Balikpapan', relevance: 'Sedang',
    rows: [[I('b1_ciroes_play1', 500, 1024, 'CIROES Play Store'), I('b1_ciroes_play5', 500, 1024, 'CIROES Play Store')], [I('b1_ciroes_untuk', 1100, 483, 'Situs CIROES: layanan untuk perumahan, kawasan industri')]],
    caption: 'Etalase Play Store dan situs: perumahan sebagai segmen klien',
    blocks: [
      ['Masalah', 'Sampah rumah tangga tidak terpilah dan tidak bernilai; perumahan butuh pengangkutan rutin.'],
      ['Solusi', 'Aplikasi: saldo, harga sampah per kg, "Jemput" terjadwal, langganan, Cistore terdekat. Perumahan dilayani sebagai klien berbayar.'],
      ['Bukti', 'Android 5rb+ unduhan, 4,3★. Portofolio "Perumahan Green Valley": jemput 6 hari/minggu, 25.000 kg/bulan; klaim 50+ klien korporat.'],
      ['Bisnis & BTN', 'Langganan pengangkutan + jual-beli daur ulang. Setelah menang: kolaborasi IPL dengan Paktukang (hanya di Kilas Balik); tak ada kerja sama BTN tercatat.'],
      ['Kenapa menang', '(Inferensi) Sudah berjalan dengan angka, dampak lingkungan terukur, dan menyentuh layanan kawasan hunian.'],
    ],
    lesson: 'aplikasi menang karena menggerakkan layanan fisik dengan angka. Hati-hati: aplikasinya kini mandek (update terakhir Sep 2025, keluhan gagal login Jun 2026).',
    source: 'Sumber: Google Play CIROES, cirowaste.com, Sumsel Pos, btnhousingpreneur.com/kilas-balik; diakses 24 Nov 2026.',
  });
  dissect(pres, C, sec, {
    kicker: 'BATCH 1 · 2024 · TECHNOLOGY', title: 'Paktukang: RAB transparan dan tukang terkurasi',
    meta: 'Juara 2 Technology (Established) · Paktukang Teknologi Karya Global · Malang', relevance: 'Sedang',
    rows: [[I('b1_pak_hero', 1100, 628, 'Situs Paktukang: bangun rumah')], [I('b1_pak_alur', 1100, 346, 'Alur Paktukang: konsultasi, survei, RAB, eksekusi'), I('b1_pak_cicil', 800, 860, 'Promo renov & bangun diangsur 15 tahun tanpa agunan')]],
    caption: 'Alur layanan dan skema cicilan 15 tahun tanpa agunan',
    blocks: [
      ['Masalah', 'Membangun/renovasi rumah penuh ketidakpastian: tukang tidak terpercaya, biaya membengkak, tanpa pembiayaan.'],
      ['Solusi', 'Konsultasi → survei → RAB (jasa & material terpisah) → tukang terkurasi, dibayar ≤24 jam; laporan progres. Pesan lewat WhatsApp.'],
      ['Bukti', '658+ pekerjaan, 158 tukang, 92 pemasok; 2025: 91 renovasi dan 2.061 konsultasi. Rumah contoh Rp2,8 jt/m² dalam 3 bulan.'],
      ['Bisnis & BTN', 'Fee ±10% upah tukang (2021); cicilan 15 th tanpa agunan, lalu "kredit multiguna" (pemberi kredit tak disebut). Logo mitra: Apersi, REI, Habitat; tanpa bank.'],
      ['Kenapa menang', '(Inferensi) Platform yang menggerakkan pekerjaan konstruksi nyata, transparansi biaya, dan kait pembiayaan.'],
    ],
    lesson: 'pesaing konsep terdekat (transparansi RAB + progres). Calon mitra untuk perbaikan pascahuni; pembiayaannya justru celah untuk KPR/kredit BTN.',
    source: 'Sumber: paktukang.com (beranda, blog, portofolio, mitra tukang), Sumsel Pos; diakses 24 Nov 2026.',
  });
  dissect(pres, C, sec, {
    kicker: 'BATCH 1 · 2024 · TECHNOLOGY', title: 'Autoconz: pitch dibuka dengan angka nasional',
    meta: 'Juara 3 Technology (Established) · PT Berdikari Teknologi Indonesia · Yogyakarta', relevance: 'Rendah',
    rows: [[I('b1_auto_pitch', 770, 513, 'Pitch Autoconz di Grand Judging')], [I('b1_auto_news', 1000, 720, 'Berita Autoconz membangun rumah 3D printing')]],
    caption: 'Pitch di Grand Judging dan liputan rumah cetak 3D (2022)',
    blocks: [
      ['Masalah', '"12 juta keluarga Indonesia masih menunggu rumah yang layak" (slide pembuka pitch).'],
      ['Solusi', 'Mesin cetak 3D konstruksi dan mortar khusus untuk mempercepat pembangunan dan menekan material.'],
      ['Bukti', 'Rumah cetak 3D sejak 2022 (lereng Merapi). Kilas Balik: rumah 3D printing dengan KPR BTN; tidak ada sumber independen soal lokasi atau jumlah.'],
      ['Bisnis & BTN', 'Jual mesin/material dan jasa cetak. Sinergi BTN tercatat: KPR untuk rumah 3D printing; kolaborasi material dengan Rebricks.'],
      ['Kenapa menang', '(Inferensi) Teknologi konstruksi modern yang terlihat, dengan narasi backlog perumahan nasional.'],
    ],
    lesson: 'tiru struktur pitchnya: buka dengan angka nasional yang besar dan foto rumah nyata, baru masuk ke solusi.',
    source: 'Sumber: Kompasiana (foto Grand Judging), Djawanews (Jan 2022), btnhousingpreneur.com/kilas-balik; diakses 24 Nov 2026.',
  });
  dissect(pres, C, sec, {
    kicker: 'BATCH 1 · 2024 · VALUE CHAIN', title: 'Rebricks & Plustik: sampah plastik jadi material',
    meta: 'Juara 1 & 2 Value Chain (Established) · PT Dua Mitra Gemilang (Rebricks) · PT Plustik Maju Bersama', relevance: 'Rendah',
    rows: [[I('b1_rebricks', 1100, 724, 'Situs Rebricks'), I('b1_rebricks_hab', 1100, 724, 'Rebricks dan Habitat for Humanity')], [I('b1_plustik_btn', 1100, 563, 'Rilis BTN: Program Rumah Rendah Emisi dengan Rebrick dan Plustik')]],
    caption: 'Rebricks, kerja sama Habitat, dan rilis BTN soal Rumah Rendah Emisi',
    blocks: [
      ['Masalah', 'Plastik "rejected" (saset) tidak didaur ulang; material bangunan beremisi tinggi.'],
      ['Solusi', 'Rebricks: paving, batako, roster dari plastik saset (kuat tekan 250 kg/cm²). Plustik: material dari plastik rumah tangga.'],
      ['Bukti', 'Rebricks (Agu 2023): 20–21 t plastik diolah, ±17 rumah Habitat (270 kg plastik per rumah), klien HokBen.'],
      ['Bisnis & BTN', 'Jual material. Keduanya masuk Program Rumah Rendah Emisi BTN (±11.000 rumah dibiayai s.d. akhir 2025); founder Plustik jadi narasumber BTN.'],
      ['Kenapa menang', '(Inferensi) Material nyata dengan angka per rumah, cocok dengan program BTN yang sudah ada sejak Q4 2024.'],
    ],
    lesson: 'BTN memberi sinergi pada yang pas dengan programnya. Petakan Estora ke program BTN yang sudah berjalan (KPR subsidi, Bale, rumah rendah emisi).',
    source: 'Sumber: rebricks.id, Detik (Apr 2024), rilis BTN 28 Okt 2025 & 16 Okt 2026, Sumsel Pos; diakses 24 Nov 2026. Tidak ada Juara 3 Value Chain 2024.',
  });
  dissect(pres, C, sec, {
    kicker: 'BATCH 1 · 2024 · BUSINESS IDEATION', title: 'Rusun Swadaya: ide yang inti bisnisnya pembiayaan BTN',
    meta: 'Juara 1 Business Ideation · Anugerah Nurrewa (bersama mitra startup mobility)', relevance: 'Sedang',
    rows: [[I('b1_rusun', 814, 1100, 'Artikel Investortrust tentang Platform Rusun Swadaya')]],
    caption: 'Investortrust, Feb 2025',
    blocks: [
      ['Masalah', 'Generasi muda di kota sulit punya hunian dekat transportasi umum.'],
      ['Solusi', 'Platform yang menghimpun komunitas untuk membangun rusun swadaya di pusat kota dekat transportasi publik.'],
      ['Bukti', 'Tahap ide; tidak ditemukan prototipe atau tindak lanjut publik.'],
      ['Bisnis & BTN', 'Komunitas mendapat "akses pembiayaan dari BTN"; platform jadi "fasilitator pembiayaan dengan risiko minim karena berbasis komunitas".'],
      ['Kenapa menang', '(Inferensi) Menjawab akses kepemilikan dan langsung menawarkan risiko kredit yang lebih rendah bagi BTN.'],
    ],
    lesson: 'bingkai portal pembeli dan data Estora sebagai pengurang risiko kredit BTN (data lengkap, bukti bayar, progres bangun), bukan sekadar fitur.',
    source: 'Sumber: Investortrust (16 Feb 2025), Sumsel Pos; diakses 24 Nov 2026.',
  });
  dissect(pres, C, sec, {
    kicker: 'BATCH 1 · 2024 · ECO HOUSE DESIGN', title: 'Harmony Land Group: juara desain dengan sinergi BTN',
    meta: 'Pemenang Eco House Design (Established) · PT Harmony Land Group · Muhammad Ridlo Aditya', relevance: 'Tinggi',
    rows: [[I('b1_harmony_foto', 702, 490, 'Foto liputan Metro TV')], [I('b1_harmony_card', 387, 170, 'Kartu sinergi BTN: Compact Harmony Living House'), I('b1_harmony_infra', 590, 212, 'Kolaborasi Harmonyland × TANAREKA')]],
    caption: 'Kartu "Sinergi dengan BTN" dan kolaborasi resmi di Kilas Balik',
    blocks: [
      ['Karya', 'Desain rumah ramah lingkungan yang "menggabungkan inovasi teknologi dengan kearifan lokal ... solusi nyata bagi masa depan".'],
      ['Sinergi BTN', '"Pengembangan kawasan NPL dengan Compact Harmony Living House" (kartu resmi Kilas Balik).'],
      ['Kolaborasi', 'PT Harmonyland × TANAREKA: berbagi perencanaan masterplan infrastruktur dan proyek.'],
      ['Status', 'Detail proyek NPL dan tanggalnya tidak dipublikasikan.'],
      ['Kaitan Estora', 'Repo Estora mencatat PT Harmony Cahaya Land (proyek Harmony Land 5). Hubungan kedua entitas belum terverifikasi.'],
    ],
    lesson: 'jika satu grup, ceritanya kuat: alumni juara yang membangun sistem operasinya sendiri dan menjalankannya di proyek sinergi BTN.',
    source: 'Sumber: btnhousingpreneur.com/kilas-balik (Sinergi dengan BTN; Kolaborasi), Metro TV (19 Feb 2025), Sumsel Pos; diakses 24 Nov 2026.',
  });
}

// ---------------- Batch 2 ----------------
function batch2(pres, C, sec) {
  dissect(pres, C, sec, {
    kicker: 'BATCH 2 · 2025 · HOUSE TECHNOLOGY', title: 'TRAIN-O: lapisan digital di atas bisnis konstruksi',
    meta: 'Juara 1 House Technology Innovation (Established) · PRANA TECH · Rp100 jt', relevance: 'Sedang',
    rows: [[I('b2_traino_foto', 900, 600, 'Foto resmi Juara 1 House Technology')], [I('b2_traino_news', 780, 220, 'Judul berita TRAIN-O dan MODULA')]],
    caption: 'Foto resmi BTN Expo 2026 dan liputan Indoposco',
    blocks: [
      ['Masalah', 'Kekurangan 8,3–9 juta tenaga aplikator konstruksi bersertifikat.'],
      ['Solusi', 'Platform pelatihan → sertifikasi → penempatan kerja (mobile learning + simulasi VR), dipadukan dengan rumah modular MODULA.'],
      ['Bukti', '3.500 → 3.569 → 4.324 orang terlatih (2022–2024); mitra BLK, SMK, BNSP. MODULA: rumah jadi 7 hari, limbah −70%.'],
      ['Bisnis & BTN', 'Jasa pelatihan dan penyaluran tenaga; "PRANA" kemungkinan kontraktor pracetak PT Struktur Pracetak Nasional. Tidak ada kait pembiayaan.'],
      ['Kenapa menang', '(Inferensi) Traksi tiga tahun berturut-turut, sertifikasi pihak ketiga, dan narasi "SDM + industrialisasi" yang lengkap.'],
    ],
    lesson: 'juara 1 tech adalah software yang ditopang bisnis fisik yang sudah jalan. Estora perlu menampilkan proyek Harmony Land 5 sebagai "bisnis fisik"-nya.',
    source: 'Sumber: btnhousingpreneur.com/kilas-balik, Indoposco (3 Feb 2026), Kitabaru; diakses 24 Nov 2026. Antarmuka TRAIN-O tidak publik.',
  });
  dissect(pres, C, sec, {
    kicker: 'BATCH 2 · 2025 · HOUSE TECHNOLOGY', title: 'AITOMA: IoT industri yang dibingkai ulang untuk rumah',
    meta: 'Juara 2 House Technology Innovation (Established) · PT Hayago Robotika Indonesia · Rp70 jt', relevance: 'Rendah',
    rows: [[I('b2_ht23_foto', 900, 600, 'Foto resmi Juara 2 dan 3 House Technology')], [I('b2_aitoma_news', 900, 900, 'Berita Beritajatim tentang AITOMA')]],
    caption: 'Foto resmi Juara 2–3 dan liputan Beritajatim',
    blocks: [
      ['Masalah', 'Tagihan listrik rumah tinggi dan boros tanpa disadari.'],
      ['Solusi', 'Stopkontak pintar + sensor panel listrik + aplikasi cloud berbasis AI; skala satu rumah sampai satu kawasan.'],
      ['Bukti', 'Klaim hemat listrik hingga 40%. Validasi startup (Pertamuda, ajang ASEAN–Korea); belum ada traksi publik untuk produk rumah.'],
      ['Bisnis & BTN', 'Bisnis inti: predictive maintenance industri (sensor IoT + AI). Tidak ada kait pembiayaan.'],
      ['Kenapa menang', '(Inferensi) Satu angka dampak yang tegas (−40%) dan teknologi yang terlihat canggih untuk rumah.'],
    ],
    lesson: 'satu angka dampak mudah diingat juri. Pilih satu angka Estora, mis. "hari dari booking ke akad turun X%".',
    source: 'Sumber: btnhousingpreneur.com/kilas-balik, Beritajatim (18 Feb 2026); diakses 24 Nov 2026. hayago.id tidak dapat diakses dari sesi riset.',
  });
  dissect(pres, C, sec, {
    kicker: 'BATCH 2 · 2025 · HOUSE TECHNOLOGY', title: 'RUMAH GOKILS: jasa anti rayap dengan garansi',
    meta: 'Juara 3 House Technology Innovation (Established) · PT Mercusuar Agresif Perkasa (GoodKills) · Rp50 jt', relevance: 'Sedang',
    rows: [[I('b2_ht23_foto', 900, 600, 'Foto resmi Juara 2 dan 3 House Technology')]],
    caption: 'Foto resmi Juara 2–3 House Technology (situs GoodKills tertahan verifikasi bot)',
    blocks: [
      ['Masalah', 'Kerugian akibat rayap dan hama pada rumah, termasuk rumah baru.'],
      ['Solusi', 'Layanan pengendalian hama dan anti rayap, termasuk pra-konstruksi, dibingkai sebagai "sistem perlindungan hunian" bergaransi.'],
      ['Bukti', 'GoodKills berdiri Mar 2020 di Surabaya, beroperasi di 62 kota, klien korporasi. Detail produk lomba hanya dari ringkasan pencarian.'],
      ['Bisnis & BTN', 'Jasa + garansi (hingga ±3 tahun). Tidak ada kait pembiayaan.'],
      ['Kenapa menang', '(Inferensi) Bisnis lama yang sudah berjalan, dibingkai ulang untuk mutu dan perlindungan hunian.'],
    ],
    lesson: 'kategori "teknologi" pun menerima jasa berbingkai kuat. Calon mitra untuk modul garansi Estora (anti rayap pra-konstruksi tercatat per unit).',
    source: 'Sumber: btnhousingpreneur.com/kilas-balik; profil GoodKills dari ringkasan pencarian; diakses 24 Nov 2026.',
  });
  dissect(pres, C, sec, {
    kicker: 'BATCH 2 · 2025 · VALUE CHAIN (≈ HOUSING ECOSYSTEM)', title: 'Parongpong RAW Lab: bukti terpasang di bangunan nyata',
    meta: 'Juara 1 House Value Chain Innovation · PT Raesaka Amanah Widyakarya · Rp100 jt', relevance: 'Rendah',
    rows: [[I('b2_parong_foto', 900, 600, 'Foto resmi Juara 1 Value Chain')], [I('b2_parong_site', 1100, 724, 'Situs Parongpong: waste-to-material dan klien')]],
    caption: 'Foto resmi dan situs Parongpong (logo klien, termasuk BTN)',
    blocks: [
      ['Masalah', 'Sampah residu non-plastik tanpa industri daur ulang: jaring nelayan, puntung rokok, masker, karung semen.'],
      ['Solusi', 'Proses hidrotermal tanpa pembakaran (Prototech) menjadi ubin, panel, decking (mis. Oriplast dari karung semen).'],
      ['Bukti', 'Terpasang di PIK, ARCH:ID 2024, Potato Head, Net Zero House; ekspor Jepang; DBS grant. Klaim karbon −50%, bobot −50%, TKDN 100%.'],
      ['Bisnis & BTN', 'Jual material. Sister company RAWHAUS sudah di jalur KPR Hijau/Tapera BTN.'],
      ['Kenapa menang', '(Inferensi) Bukti terpasang di proyek ternama, angka lingkungan, dan jalur pembiayaan BTN lewat entitas saudara.'],
    ],
    lesson: 'di kategori sasaran Estora, juara 1 menang dengan bukti terpasang. Bawa bukti "terpasang": proyek, unit, transaksi yang berjalan di Estora.',
    source: 'Sumber: btnhousingpreneur.com/kilas-balik, parongpong.com, CNBC Indonesia (30 Jan 2026); diakses 24 Nov 2026.',
  });
  dissect(pres, C, sec, {
    kicker: 'BATCH 2 · 2025 · VALUE CHAIN (≈ HOUSING ECOSYSTEM)', title: 'RR Board: sampah sungai jadi papan dan atap teruji',
    meta: 'Juara 2 House Value Chain Innovation · PT Wasteforchange Alam Indonesia · Rp70 jt', relevance: 'Rendah',
    rows: [[I('b2_rr_booth', 694, 522, 'Booth RR Board di BTN Expo'), I('b2_rr_booth2', 518, 389, 'Produk RR Board')], [I('b2_vc23_foto', 900, 600, 'Foto resmi Juara 2 dan 3 Value Chain')]],
    caption: 'Booth BTN Expo 2026 (Detik) dan foto resmi Juara 2–3',
    blocks: [
      ['Masalah', 'Plastik bernilai rendah (saset, kresek) mencemari Sungai Citarum.'],
      ['Solusi', 'Papan 1,2 × 2,4 m dari plastik sungai, dipres tanpa campuran lain; pengganti triplek; untuk perumahan ditawarkan sebagai atap.'],
      ['Bukti', 'Lulus uji Sucofindo; pabrik di Bandung Barat sejak 2024 (23 pekerja); harga dari Rp405.500/lembar.'],
      ['Bisnis & BTN', 'Jual papan dan atap (Waste4Change × River Recycle). Tidak ada kait pembiayaan.'],
      ['Kenapa menang', '(Inferensi) Bukti uji pihak ketiga, harga terbuka, dan cerita lingkungan yang kuat dari lembaga mapan.'],
    ],
    lesson: 'uji pihak ketiga dan harga terbuka menaikkan kredibilitas. Bawa audit/uji independen (keamanan data, uji beban) dan daftar harga Estora.',
    source: 'Sumber: btnhousingpreneur.com/kilas-balik, Detik (29 Jan 2026), DetikX; diakses 24 Nov 2026.',
  });
  dissect(pres, C, sec, {
    kicker: 'BATCH 2 · 2025 · VALUE CHAIN (≈ HOUSING ECOSYSTEM)', title: 'KPR Energy: produk yang dinamai dengan bahasa BTN',
    meta: 'Juara 3 House Value Chain Innovation · PT Andalusia Intra Teknologi (GridSolr) · Rp50 jt', relevance: 'Sedang',
    rows: [[I('b2_vc23_foto', 900, 600, 'Foto resmi Juara 2 dan 3 Value Chain')], [{ path: A2('win_gridsolr.png'), w: 1100, h: 724, alt: 'Situs GridSolr' }]],
    caption: 'Foto resmi dan situs GridSolr ("3rd Winner BTN Housingpreneur 2025")',
    blocks: [
      ['Masalah', 'Pemilik rumah baru sulit memiliki PLTS atap karena biaya awal.'],
      ['Solusi', 'PLTS hybrid "DIY-assisted" dengan BOM terbuka; paket 4.700 Wp + baterai LFP 16 kWh + aplikasi monitoring real-time.'],
      ['Bukti', '"80% pelanggan" memilih paket 4,7 kWp (tanpa jumlah pelanggan). ROI 4–5 tahun, garansi panel 25 tahun.'],
      ['Bisnis & BTN', '"KPR Energy" = kepemilikan PLTS lewat bingkai KPR; mekanismenya tidak publik. GridSolr jadi pembicara roadshow Batch 3.'],
      ['Kenapa menang', '(Inferensi) Satu-satunya juara Value Chain yang menempelkan produknya pada produk inti BTN, plus ROI yang jelas.'],
    ],
    lesson: 'namai dan bingkai fitur dengan bahasa BTN (KPR, akad, FLPP). Contoh: "KPR-ready dossier" dari data Estora untuk mempercepat akad.',
    source: 'Sumber: btnhousingpreneur.com/kilas-balik, gridsolr.com; diakses 24 Nov 2026.',
  });
  dissect(pres, C, sec, {
    kicker: 'BATCH 2 · 2025 · AFFORDABLE HOUSE', title: 'MGK Serang: rumah subsidi hijau pertama, calon pilot',
    meta: 'Juara 1 Affordable House Development · PT Infiniti Triniti Jaya · Rp100 jt', relevance: 'Tinggi',
    rows: [[I('b2_mgk_foto', 900, 600, 'Foto resmi Juara 1 Affordable')], [I('b2_mgk_rumah', 694, 393, 'Deret rumah subsidi MGK')]],
    caption: 'Foto resmi dan deret rumah MGK (dok. PT Infiniti Triniti Jaya)',
    blocks: [
      ['Masalah', 'Rumah subsidi identik dengan mutu rendah dan boros energi.'],
      ['Solusi', 'Perumahan Mulia Gading Kencana: rumah subsidi bersertifikat Bangunan Gedung Hijau (BGH) predikat Utama.'],
      ['Bukti', 'Klaim perumahan subsidi pertama dengan BGH Utama (PUPR), rekor MURI; harga Rp150,5–166 jt.'],
      ['Bisnis & BTN', 'Rumah subsidi ber-KPR. Biaya BGH +8–12% diserap developer; 80% penjualan dari media sosial; punya divisi Tenant Relation.'],
      ['Kenapa menang', '(Inferensi) Sertifikasi pihak ketiga dan inovasi di harga patokan subsidi.'],
    ],
    lesson: 'calon pilot ideal: developer subsidi pemenang yang menjual via media sosial dan mengurus penghuni. Atribusi iklan dan portal pembeli Estora cocok.',
    source: 'Sumber: btnhousingpreneur.com/kilas-balik, Infobanknews, Detik Properti; diakses 24 Nov 2026.',
  });
  dissect(pres, C, sec, {
    kicker: 'BATCH 2 · 2025 · IDEASI MAHASISWA', title: 'GeoFloodAI: aplikasi murni yang menang di jalur ide',
    meta: 'Juara 1 Housing Related Innovation (Mahasiswa) · Ali Sulas Hidayat dkk. · Palembang · Rp55 jt', relevance: 'Rendah',
    rows: [[I('b2_geo_foto', 900, 600, 'Foto resmi Juara 1 HRI Mahasiswa')], [I('b2_geo_news', 1000, 900, 'Liputan SWA tentang GeoFloodAI')]],
    caption: 'Foto resmi dan liputan SWA',
    blocks: [
      ['Masalah', 'Rumah dibangun di lahan rawan banjir tanpa analisis sejak tahap perencanaan.'],
      ['Solusi', 'Pengguna menandai lokasi di peta, lalu model machine learning memberi skor risiko banjir (data hidrologi, geospasial, crowdsourcing).'],
      ['Bukti', 'Berasal dari tesis S2; uji pengguna ±50 orang.'],
      ['Bisnis & BTN', 'Belum ada model bisnis publik; potensi analisis risiko agunan untuk bank.'],
      ['Kenapa menang', '(Inferensi) Masalah iklim nasional dengan solusi AI yang mudah dipahami, di jalur ide mahasiswa.'],
    ],
    lesson: 'aplikasi murni menang di jalur ide, bukan Established. Untuk jalur Established, aplikasi saja tidak cukup tanpa operasi nyata.',
    source: 'Sumber: btnhousingpreneur.com/kilas-balik, SWA, Monitor Indonesia; diakses 24 Nov 2026.',
  });
  dissect(pres, C, sec, {
    kicker: 'BATCH 2 · 2025 · IDEASI UMUM', title: 'myECO: IoT hemat listrik dengan aplikasi yang sudah dipakai',
    meta: 'Juara 2 Housing Related Innovation (Umum) · Maulana Derifato Achmad · Malang · Rp45 jt', relevance: 'Rendah',
    rows: [[I('b2_myeco_1', 618, 1100, 'myECO biaya listrik'), I('b2_myeco_2', 618, 1100, 'myECO timer'), I('b2_myeco_4', 618, 1100, 'myECO perangkat')], [I('b2_umum23_foto', 900, 537, 'Foto resmi Juara 2 dan 3 HRI Umum')]],
    caption: 'Screenshot Play Store dan foto resmi Juara 2–3 HRI Umum',
    blocks: [
      ['Masalah', 'Listrik rumah terbuang karena perangkat menyala tanpa dipakai.'],
      ['Solusi', '"Smart EcoRoom": nyala/mati otomatis lewat jadwal, web, atau sensor keberadaan orang; dipantau dari aplikasi.'],
      ['Bukti', 'Klaim hemat hingga 55%; Android 1rb+ unduhan, rating 4,9; klien institusional termasuk PLN (2023).'],
      ['Bisnis & BTN', 'Jual perangkat + aplikasi. Tidak ada kait pembiayaan. Logo myECO juga tampil di situs Paktukang.'],
      ['Kenapa menang', '(Inferensi) Produk sudah dipakai, angka penghematan jelas, dibingkai "rumah yang bisa berpikir sendiri".'],
    ],
    lesson: 'tampilkan layar asli yang sudah dipakai pengguna, bukan mockup. Screenshot produksi Estora lebih meyakinkan daripada desain.',
    source: 'Sumber: Google Play myECO, btnhousingpreneur.com/kilas-balik; diakses 24 Nov 2026. Situs myeco.id sedang dijeda.',
  });
  dissect(pres, C, sec, {
    kicker: 'BATCH 2 · 2025 · IDEASI UMUM', title: 'Proteka: uji meja getar sebagai bukti utama',
    meta: 'Juara 1 Housing Related Innovation (Umum) · PT Inovasi Tangguh Bencana · Zamzam Multazam · Rp65 jt', relevance: 'Rendah',
    rows: [[I('b2_proteka_foto', 900, 537, 'Foto resmi Juara 1 HRI Umum')], [I('b2_proteka_site', 1100, 724, 'Situs Proteka')]],
    caption: 'Foto resmi dan situs Proteka',
    blocks: [
      ['Masalah', 'Dinding bata rumah rentan runtuh saat gempa.'],
      ['Solusi', 'Pelapis berpenguat serat ("WallPro") yang diaplikasikan seperti cat untuk memperkuat dinding (retrofit).'],
      ['Bukti', 'Uji meja getar; diterapkan di sekolah di Lembang dan "panic room" rumah. Penggagas: doktor mitigasi bencana University of Tokyo.'],
      ['Bisnis & BTN', 'Jual material + layanan asesmen, program kemitraan aplikator, alat analisis numerik gratis.'],
      ['Kenapa menang', '(Inferensi) Masalah bencana nasional, bukti uji ilmiah, dan pendiri dengan kredibilitas akademik.'],
    ],
    lesson: 'kredibilitas tim dan uji ilmiah menutup keraguan juri. Tunjukkan rekam jejak tim dan hasil uji gate/verifikasi Estora.',
    source: 'Sumber: btnhousingpreneur.com/kilas-balik, proteka (situs resmi), Akurat; diakses 24 Nov 2026.',
  });
  dissect(pres, C, sec, {
    kicker: 'BATCH 2 · 2025 · FINALIS', title: 'Ontoown: sewa yang menjadi DP KPR, paling dekat Estora',
    meta: 'Finalis 2025 (bukan juara) · Bandung', relevance: 'Tinggi',
    rows: [[I('b2_onto_expo', 822, 463, 'Foto BTN Expo 2026')], [I('b2_onto_par', 850, 210, 'Paragraf Monitor Indonesia tentang Ontoown')]],
    caption: 'Liputan BTN Expo 2026 (Monitor Indonesia)',
    blocks: [
      ['Masalah', '"Banyak aset hunian menganggur, sementara Gen Z membutuhkan rumah tetapi terkendala credit history dan DP."'],
      ['Solusi', 'Aplikasi rent-to-own: sewa bulanan dikumpulkan sampai cukup untuk uang muka KPR.'],
      ['Bukti', 'Tidak ada traksi, mitra, atau produk yang terlihat publik.'],
      ['Bisnis & BTN', 'Kait pembiayaan langsung: sewa → DP → KPR.'],
      ['Kenapa tidak juara', '(Inferensi) Ide kuat dengan kait BTN, tetapi tanpa bukti berjalan; di 2025 yang juara punya traksi.'],
    ],
    lesson: 'ide tabungan DP bertahap bisa jadi modul Estora (jadwal setoran + portal pembeli), dengan bukti nyata yang tidak dimiliki Ontoown.',
    source: 'Sumber: Monitor Indonesia (Jan 2026), CNBC Indonesia; diakses 24 Nov 2026.',
  });
}

// ---------------- Synthesis ----------------
async function synthesis(pres, C, sec) {
  // Synergy
  {
    const s = pres.addSlide({ masterName: 'CONTENT', sectionTitle: sec });
    s.addText('SINTESIS · SINERGI BTN SETELAH MENANG', { placeholder: 'kicker' });
    s.addText('Sinergi BTN selalu berupa KPR, program, atau kawasan NPL', { placeholder: 'title' });
    fitRow(s, [I('sinergi_cards', 1212, 376, 'Enam kartu Sinergi dengan BTN di Kilas Balik')], 0.6, 1.45, 7.3, 2.4);
    txt(s, 'Kartu resmi "Sinergi dengan BTN" di Kilas Balik: Rumah Pracetak Bandung, Habitatland, RAWHAUS, TANAREKA, Autoconz, PT Harmony Land Group.', { x: 0.6, y: 3.95, w: 7.3, h: 0.6, fontSize: 12, color: C.accent5 });
    const kinds = [['KPR untuk unit', 'Habitatland, Autoconz (rumah 3D printing)'], ['Pasokan program BTN', 'Rebricks, Plustik, Rumah Pracetak (Rumah Rendah Emisi)'], ['Kawasan NPL', 'PT Harmony Land Group (Compact Harmony Living House)']];
    kinds.forEach(([k, v], i) => {
      const y = 4.65 + i * 0.6;
      s.addShape('roundRect', { x: 0.6, y, w: 2.2, h: 0.48, rectRadius: 0.06, fill: { color: HEX.accent1 }, line: { color: HEX.accent1, width: 0 }, objectName: 'kind ' + i });
      txt(s, k, { x: 0.6, y, w: 2.2, h: 0.48, fontSize: 12, bold: true, color: C.background1, align: 'center', valign: 'middle' });
      txt(s, v, { x: 2.95, y, w: 4.95, h: 0.48, fontSize: 12, color: C.text1, valign: 'middle' });
    });
    card(s, C, 8.2, 1.45, 4.52, 5.05, { fill: 'FFF6E3', name: 'synergy lesson' });
    txt(s, 'Yang tidak terjadi', { x: 8.42, y: 1.6, w: 4.1, h: 0.35, fontSize: 15, bold: true, color: C.text1 });
    bullets(s, [
      'CIROES dan Paktukang (juara digital 2024) tidak tercatat punya kerja sama dengan BTN; hanya berkolaborasi satu sama lain soal IPL.',
      'Belum ada sinergi BTN yang dipublikasikan untuk juara 2025.',
      'Program Rumah Rendah Emisi sudah ada sebelum penganugerahan: juara masuk karena cocok, bukan karena menang.',
    ], { x: 8.42, y: 2.0, w: 4.1, h: 2.85, fontSize: 13, color: C.text1, paraSpaceAfter: 6 });
    card(s, C, 8.42, 4.95, 4.08, 1.38, { fill: C.accent1, name: 'synergy implication' });
    txt(s, 'Janjikan sinergi yang bisa dihitung BTN: jumlah akad KPR BTN lewat developer pengguna Estora.', { x: 8.6, y: 5.0, w: 3.75, h: 1.28, fontSize: 13, bold: true, color: C.background1, valign: 'middle' });
    source(s, C, 'Sumber: btnhousingpreneur.com/kilas-balik (Sinergi dengan BTN; Kolaborasi strategis antar finalis), rilis BTN 16 Okt 2026; diakses 24 Nov 2026. Klaim Kilas Balik tidak bertanggal.');
  }
  // Comparison matrix
  {
    const s = pres.addSlide({ masterName: 'CONTENT', sectionTitle: sec });
    s.addText('SINTESIS · PERBANDINGAN', { placeholder: 'kicker' });
    s.addText('Juara Established hampir selalu punya bukti dan angka dampak', { placeholder: 'title' });
    const cols = ['Juara', 'Kategori', 'Digital', 'Bukti pihak ketiga / traksi', 'Angka dampak', 'Kait pembiayaan', 'Sinergi BTN'];
    const d = [
      ['CIROES', 'Tech 2024 · J1', 'Ya', '5rb+ unduhan; 50+ klien', '25 t sampah/bln satu perumahan', 'Tidak', 'Tidak'],
      ['Paktukang', 'Tech 2024 · J2', 'Ya', '658+ pekerjaan, 158 tukang', 'Rp2,8 jt/m², 3 bulan', 'Sebagian', 'Tidak'],
      ['Autoconz', 'Tech 2024 · J3', 'Tidak', 'Rumah 3D sejak 2022', '12 juta keluarga menunggu', 'Tidak', 'Ya'],
      ['Rebricks', 'Value Chain 2024 · J1', 'Tidak', '±17 rumah Habitat', '270 kg plastik/rumah', 'Tidak', 'Ya'],
      ['TRAIN-O', 'House Tech 2025 · J1', 'Ya', '4.324 terlatih (2024); BNSP', 'Rumah 7 hari, limbah −70%', 'Tidak', 'Tidak'],
      ['AITOMA', 'House Tech 2025 · J2', 'Sebagian', 'Validasi startup', 'Hemat listrik 40%', 'Tidak', 'Tidak'],
      ['Parongpong', 'Value Chain 2025 · J1', 'Tidak', 'Terpasang di PIK, ARCH:ID', 'Karbon −50%', 'Sebagian', 'Sebagian'],
      ['RR Board', 'Value Chain 2025 · J2', 'Tidak', 'Uji Sucofindo; pabrik', 'Rp405.500/lembar', 'Tidak', 'Tidak'],
      ['KPR Energy', 'Value Chain 2025 · J3', 'Sebagian', '"80% pelanggan" 4,7 kWp', 'ROI 4–5 tahun', 'Ya', 'Tidak'],
      ['MGK Serang', 'Affordable 2025 · J1', 'Tidak', 'Sertifikat BGH Utama', 'Biaya hijau +8–12% diserap', 'Ya', 'Sebagian'],
    ];
    const rows = [cols.map((c, i) => head(c, i === 0 || i === 3 || i === 4 ? { align: 'left' } : {}))];
    d.forEach((r) => rows.push([plain(r[0], { bold: true, fontSize: 12 }), plain(r[1], { fontSize: 11 }), yn(r[2]), plain(r[3], { fontSize: 11 }), plain(r[4], { fontSize: 11 }), yn(r[5]), yn(r[6])]));
    s.addTable(rows, { x: 0.6, y: 1.42, w: 12.12, colW: [1.45, 1.95, 1.05, 2.85, 2.6, 1.11, 1.11], rowH: [0.42, ...Array(10).fill(0.43)], fontSize: 11, border: { type: 'solid', pt: 0.75, color: 'D5E2E5' }, margin: 0.05, objectName: 'winner comparison' });
    source(s, C, 'Sumber: catatan bedah Batch 1 & 2 (situs pemenang, Kilas Balik, media). "Sebagian" = ada tetapi tidak langsung/tidak publik. Diakses 24 Nov 2026.');
  }
  // Patterns
  {
    const s = pres.addSlide({ masterName: 'CONTENT', sectionTitle: sec });
    s.addText('SINTESIS · POLA PEMENANG', { placeholder: 'kicker' });
    s.addText('Enam pola yang berulang pada juara', { placeholder: 'title' });
    const p = [
      [fa.FaHouseCircleCheck, 'Wujud nyata', 'Produk sudah terpasang atau dipakai: Parongpong di PIK, Rebricks di rumah Habitat, TRAIN-O ribuan peserta.'],
      [fa.FaCertificate, 'Bukti pihak ketiga', 'Uji Sucofindo, sertifikat BGH, uji meja getar, sertifikasi BNSP.'],
      [fa.FaArrowsRotate, 'Bisnis lama, bingkai baru', 'AITOMA, GoodKills, Waste4Change, PRANA, GridSolr membawa bisnis yang sudah jalan ke konteks perumahan.'],
      [fa.FaChartLine, 'Satu angka dampak', 'Hemat 40% atau 55%, ROI 4–5 tahun, rumah 7 hari, limbah −70%.'],
      [fa.FaEarthAsia, 'Masalah skala nasional', 'Backlog rumah, bencana, iklim, sampah, kekurangan tenaga kerja.'],
      [fa.FaLayerGroup, 'Digital sebagai lapisan', 'Aplikasi menggerakkan layanan atau perangkat fisik; aplikasi murni hanya menang di jalur ide.'],
    ];
    const w = 3.88, h = 2.35, gx = 0.24, gy = 0.25;
    for (let i = 0; i < p.length; i++) {
      const [ic, t, d] = p[i];
      const x = 0.6 + (i % 3) * (w + gx), y = 1.45 + Math.floor(i / 3) * (h + gy);
      card(s, C, x, y, w, h, { fill: C.background2, name: 'pattern ' + (i + 1) });
      await iconCircle(s, C, ic, x + 0.25, y + 0.25, 0.56, C.accent2, t);
      txt(s, t, { x: x + 0.95, y: y + 0.3, w: w - 1.15, h: 0.46, fontSize: 16, bold: true, color: C.text1, valign: 'middle' });
      txt(s, d, { x: x + 0.25, y: y + 0.98, w: w - 0.5, h: 1.25, fontSize: 13, color: C.text1 });
    }
    source(s, C, 'Pola disimpulkan tim riset dari 17 juara yang dibedah; juri tidak mempublikasikan alasan per juara.');
  }
  // Pitch anatomy
  {
    const s = pres.addSlide({ masterName: 'CONTENT', sectionTitle: sec });
    s.addText('SINTESIS · ANATOMI PITCH', { placeholder: 'kicker' });
    s.addText('Tujuh halaman resmi, diisi seperti para juara mengisinya', { placeholder: 'title' });
    const H = ['#', 'Halaman resmi (panduan)', 'Cara juara mengisinya', 'Contoh'];
    const d = [
      ['1', 'Masalah & urgensi', 'Satu angka nasional besar + foto rumah nyata', 'Autoconz: "12 juta keluarga menunggu rumah layak"'],
      ['2', 'Pendekatan & pasar', 'Segmen jelas dan ukurannya', 'TRAIN-O: kekurangan 8,3–9 juta aplikator'],
      ['3', 'Ide', 'Satu kalimat yang mudah diulang juri', 'myECO: "rumah yang bisa berpikir sendiri"'],
      ['4', 'Keunggulan kompetitif', 'Bukti pihak ketiga, bukan klaim', 'RR Board: uji Sucofindo; MGK: BGH Utama'],
      ['5', 'Konsep / prototipe', 'Sudah terpasang atau dipakai, dengan foto', 'Parongpong: terpasang di PIK, Potato Head'],
      ['6', 'Manfaat', 'Satu angka dampak', 'AITOMA hemat 40%; KPR Energy ROI 4–5 tahun'],
      ['7', 'Model bisnis + Sinergi BTN + RAB', 'Harga terbuka dan kait ke produk BTN', 'RR Board Rp405.500/lembar; "KPR Energy"'],
    ];
    const rows = [H.map((h, i) => head(h, i ? { align: 'left' } : {}))];
    d.forEach((r) => rows.push([plain(r[0], { align: 'center', bold: true, color: HEX.accent2, fontSize: 15 }), plain(r[1], { bold: true, fontSize: 13 }), plain(r[2], { fontSize: 12 }), plain(r[3], { fontSize: 12, color: HEX.accent5 })]));
    s.addTable(rows, { x: 0.6, y: 1.45, w: 12.12, colW: [0.55, 3.0, 4.0, 4.57], rowH: [0.45, ...Array(7).fill(0.62)], fontSize: 12, border: { type: 'solid', pt: 0.75, color: 'D5E2E5' }, margin: 0.06, objectName: 'pitch anatomy' });
    source(s, C, 'Struktur 7 halaman dari panduan dokumen BTN Housingpreneur Batch 3; contoh dari materi publik para juara. Isi pitch deck juara tidak dipublikasikan.');
  }
}

// ---------------- For Estora ----------------
async function forEstora(pres, C, sec) {
  // Scorecard
  {
    const s = pres.addSlide({ masterName: 'CONTENT', sectionTitle: sec });
    s.addText('UNTUK ESTORA · POSISI', { placeholder: 'kicker' });
    s.addText('Dibanding juara: teknologi lebih dalam, bukti lebih tipis', { placeholder: 'title' });
    const H = ['Kriteria Housing Ecosystem', 'Bobot', 'Yang ditunjukkan juara', 'Estora hari ini', 'Bawa ke pitch'];
    const d = [
      ['Kematangan teknologi', '25%', 'Produk terpasang/dipakai', '±1.019 endpoint, 70 gate verifikasi, PWA offline', 'Demo langsung + layar produksi'],
      ['Skalabilitas & replikasi', '20%', 'Pabrik, 62 kota, ribuan peserta', '1 instance produksi', 'Developer pilot kedua / LOI (mis. alumni)'],
      ['Kelayakan bisnis', '20%', 'Harga terbuka, pelanggan', 'Belum ada harga & penagihan', 'Harga + RAB; patokan Rp1,5 jt/bln–Rp40 jt/thn'],
      ['Executable', '15%', 'Sudah berjalan', 'Berjalan di Harmony Land 5', 'Angka nyata: unit, transaksi, hari ke akad'],
      ['Relevansi masalah', '10%', 'Angka nasional', 'FLPP 2026: 350 rb unit, 45,7% tersalurkan (Sep)', 'Satu angka pembuka + foto proyek'],
      ['Kolaborasi ekosistem', '10%', 'KPR, program BTN, NPL', 'Belum ada integrasi', 'Janji akad KPR BTN lewat Estora; mitra alumni'],
    ];
    const rows = [H.map((h, i) => head(h, i === 1 ? {} : { align: 'left' }))];
    d.forEach((r) => rows.push([plain(r[0], { bold: true, fontSize: 12 }), plain(r[1], { align: 'center', bold: true, color: HEX.accent1 }), plain(r[2], { fontSize: 11 }), plain(r[3], { fontSize: 11 }), plain(r[4], { fontSize: 11, bold: true })]));
    s.addTable(rows, { x: 0.6, y: 1.45, w: 12.12, colW: [2.4, 0.75, 2.7, 3.12, 3.15], rowH: [0.45, ...Array(6).fill(0.72)], fontSize: 12, border: { type: 'solid', pt: 0.75, color: 'D5E2E5' }, margin: 0.06, objectName: 'estora scorecard' });
    source(s, C, 'Bobot: btnhousingpreneur.com (Developer & Pengusaha › Housing Ecosystem). Estora: inventaris repositori. Juara: catatan bedah Batch 1 & 2.');
  }
  // Pitch storyline
  {
    const s = pres.addSlide({ masterName: 'CONTENT', sectionTitle: sec });
    s.addText('UNTUK ESTORA · ALUR PITCH', { placeholder: 'kicker' });
    s.addText('Usulan isi tujuh halaman pitch Estora', { placeholder: 'title' });
    const pages = [
      ['Masalah & urgensi', 'FLPP 2026 350 rb unit, baru 45,7% tersalurkan; developer kecil masih Excel & WA; kasus banjir & PSU (Klayan 5).'],
      ['Pendekatan & pasar', 'Developer subsidi 1–2 proyek tanpa tim IT; anggota REI/APERSI; 12.600+ developer sudah di Bale BTN.'],
      ['Ide', '"Sistem operasi developer subsidi: dari lead sampai garansi, dengan jejak bukti per unit."'],
      ['Keunggulan', 'Satu-satunya yang menyambung piutang bertahap, bukti konstruksi, BAST & garansi; hasil uji gate; tanpa vendor lain.'],
      ['Prototipe', 'Layar produksi Harmony Land 5: peta kavling, KPR, progres berfoto, tiket ber-SLA.'],
      ['Manfaat', 'Satu angka: hari booking → akad, atau % komplain selesai sesuai SLA (ambil dari hl5).'],
      ['Bisnis + BTN + RAB', 'Harga langganan; RAB pengembangan; sinergi: akad KPR BTN lewat Estora, data siap-KPR, VA BTN.'],
    ];
    pages.forEach(([t, d], i) => {
      const col = i < 4 ? 0 : 1, row = i < 4 ? i : i - 4;
      const x = 0.6 + col * 6.18, y = 1.45 + row * 1.24, w = 5.94;
      card(s, C, x, y, w, 1.1, { fill: row % 2 ? 'FFFFFF' : C.background2, name: 'page ' + (i + 1) });
      s.addShape('ellipse', { x: x + 0.18, y: y + 0.28, w: 0.54, h: 0.54, fill: { color: HEX.accent2 }, line: { color: 'FFFFFF', width: 0 }, objectName: 'page num ' + (i + 1) });
      txt(s, String(i + 1), { x: x + 0.18, y: y + 0.28, w: 0.54, h: 0.54, fontSize: 16, bold: true, color: C.background1, align: 'center', valign: 'middle' });
      txt(s, t, { x: x + 0.88, y: y + 0.08, w: w - 1.05, h: 0.32, fontSize: 14, bold: true, color: C.text1 });
      txt(s, d, { x: x + 0.88, y: y + 0.42, w: w - 1.05, h: 0.64, fontSize: 12, color: C.text1 });
    });
    card(s, C, 6.78, 5.17, 5.94, 1.1, { fill: C.accent1, name: 'pitch rule' });
    txt(s, 'Aturan dari para juara: setiap halaman membawa satu bukti (foto, angka, atau dokumen pihak ketiga).', { x: 6.98, y: 5.22, w: 5.55, h: 1.0, fontSize: 13, bold: true, color: C.background1, valign: 'middle' });
    source(s, C, 'Struktur halaman: panduan dokumen BTN Housingpreneur Batch 3. Angka Estora (hari ke akad, % SLA) harus diambil dari instance produksi sebelum dipakai.');
  }
  // Partners from alumni
  {
    const s = pres.addSlide({ masterName: 'CONTENT', sectionTitle: sec });
    s.addText('UNTUK ESTORA · MITRA DARI ALUMNI', { placeholder: 'kicker' });
    s.addText('Alumni BTN Housingpreneur bisa jadi pilot dan mitra Estora', { placeholder: 'title' });
    const groups = [
      ['Calon pilot developer', HEX.accent1, [['MGK Serang (Infiniti)', 'Juara Affordable 2025; jual via medsos, ada Tenant Relation'], ['Habitatland, Prosya, Kreasi Prima, Sembilan Bintang', 'Juara developer 2024'], ['PT Harmony Land Group', 'Juara desain 2024; sinergi kawasan NPL']]],
      ['Mitra modul Estora', HEX.accent2, [['Paktukang', 'Perbaikan & renovasi pascahuni'], ['GoodKills', 'Anti rayap pra-konstruksi dalam garansi'], ['TRAIN-O', 'Tukang bersertifikat untuk QC'], ['CIROES', 'Layanan sampah dalam tagihan IPL'], ['GridSolr', 'Paket PLTS untuk rumah baru']]],
    ];
    groups.forEach(([g, col, items], gi) => {
      const x = 0.6 + gi * 6.18, w = 5.94;
      s.addShape('roundRect', { x, y: 1.45, w, h: 0.45, rectRadius: 0.06, fill: { color: col }, line: { color: col, width: 0 }, objectName: 'group ' + gi });
      txt(s, g, { x: x + 0.2, y: 1.45, w: w - 0.4, h: 0.45, fontSize: 15, bold: true, color: C.background1, valign: 'middle' });
      items.forEach(([n, d], i) => {
        const y = 2.05 + i * (gi ? 0.8 : 1.33), h = gi ? 0.7 : 1.2;
        card(s, C, x, y, w, h, { fill: i % 2 ? 'FFFFFF' : C.background2, name: 'partner ' + gi + i });
        txt(s, n, { x: x + 0.2, y: y + 0.05, w: w - 0.4, h: gi ? 0.3 : 0.5, fontSize: 13, bold: true, color: C.text1, valign: 'middle' });
        txt(s, d, { x: x + 0.2, y: y + (gi ? 0.35 : 0.58), w: w - 0.4, h: gi ? 0.32 : 0.55, fontSize: 12, color: C.accent5 });
      });
    });
    card(s, C, 0.6, 6.06, 5.94, 0.36, { fill: 'FFF6E3', name: 'harmony question' });
    txt(s, 'Perlu dicek: Harmony Land Group dan Harmony Cahaya Land satu grup?', { x: 0.75, y: 6.06, w: 5.7, h: 0.36, fontSize: 11, bold: true, color: C.text1, valign: 'middle' });
    source(s, C, 'Kolaborasi antar-finalis adalah pola yang disorot BTN di Kilas Balik (mis. CIROES × Paktukang, Autoconz × Rebricks). Kecocokan mitra adalah inferensi tim riset.');
  }
  // Method
  {
    const s = pres.addSlide({ masterName: 'CONTENT', sectionTitle: sec });
    s.addText('LAMPIRAN', { placeholder: 'kicker' });
    s.addText('Metode, sumber, dan batas pembedahan', { placeholder: 'title' });
    card(s, C, 0.6, 1.5, 5.95, 4.95, { fill: C.background2, name: 'method card' });
    txt(s, 'Metode', { x: 0.85, y: 1.7, w: 5.5, h: 0.4, fontSize: 17, bold: true, color: C.text1 });
    bullets(s, [
      'Halaman Kilas Balik, galeri, dan berita BTN dirender dengan Chromium; setiap tab dan kartu di-screenshot.',
      'Situs, Play Store, dan liputan media tiap juara diperiksa; 200+ screenshot disimpan dengan URL sumbernya.',
      'Hadiah per peringkat dibaca dari papan cek di foto resmi.',
      'Tidak ada login, pendaftaran, unduhan video, atau API privat.',
    ], { x: 0.85, y: 2.2, w: 5.5, h: 4.1, fontSize: 14, color: C.text1 });
    card(s, C, 6.77, 1.5, 5.95, 4.95, { fill: 'FFF6E3', name: 'limits card' });
    txt(s, 'Batas yang perlu diingat', { x: 7.02, y: 1.7, w: 5.5, h: 0.4, fontSize: 17, bold: true, color: C.text1 });
    bullets(s, [
      'Alasan menang per juara tidak dipublikasikan; "kenapa menang" adalah inferensi.',
      'Bobot penilaian 2024 dan 2025 tidak dipublikasikan; dipakai bobot Batch 3 sebagai proksi.',
      'Isi pitch deck juara tidak publik; hanya satu slide (Autoconz) terlihat di foto.',
      'Beberapa situs tidak bisa diakses (hayago.id, goodkills.id, autoconz.com, plustik.id); Instagram tidak dibuka.',
      'Catatan lengkap: research_notes/Bedah pemenang BTN Housingpreneur/.',
    ], { x: 7.02, y: 2.2, w: 5.5, h: 4.1, fontSize: 14, color: C.text1 });
  }
}

module.exports = { opening, batch1, batch2, synthesis, forEstora };
