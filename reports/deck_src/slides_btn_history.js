// BTN Housingpreneur schedule and past technology winners.
const { HEX, card, txt, bullets, source } = require('./lib');

async function btnHistory(pres, C, sec) {
  const s = pres.addSlide({ masterName: 'CONTENT', sectionTitle: sec });
  s.addText('ARENA · JADWAL & PEMENANG SEBELUMNYA', { placeholder: 'kicker' });
  s.addText('Belum pernah ada juara yang berupa sistem operasi developer', { placeholder: 'title' });

  txt(s, 'Jadwal Batch 3', { x: 0.6, y: 1.5, w: 5.6, h: 0.35, fontSize: 16, bold: true, color: C.text1 });
  const ev = [
    ['30 Nov 2026', 'Pendaftaran ditutup'],
    ['30 Nov–4 Des', 'Seleksi awal'],
    ['7–11 Des', 'Evaluasi ide bisnis'],
    ['14–18 Des', 'Live pitching (luring di 2 kota, lainnya daring)'],
    ['4–8 Jan 2027', 'Pengembangan kapasitas finalis'],
    ['13–14 Jan', 'Grand Judging di Jakarta, wajib hadir'],
    ['17 Jan 2027', 'Penganugerahan di Jakarta'],
  ];
  const lx = 0.7, y0 = 2.0, step = 0.62;
  s.addShape('line', { x: lx + 0.11, y: y0 + 0.12, w: 0, h: step * (ev.length - 1), line: { color: HEX.accent2, width: 2 }, objectName: 'schedule spine' });
  ev.forEach(([d, t], i) => {
    const y = y0 + i * step;
    s.addShape('ellipse', { x: lx, y: y + 0.01, w: 0.24, h: 0.24, fill: { color: i === 0 ? C.accent3 : C.accent2 }, line: { color: 'FFFFFF', width: 1.5 }, objectName: 'schedule dot ' + (i + 1) });
    txt(s, d, { x: lx + 0.45, y: y - 0.02, w: 1.75, h: 0.32, fontSize: 13, bold: true, color: i === 0 ? '9A6A00' : C.accent2 });
    txt(s, t, { x: lx + 2.25, y: y - 0.02, w: 3.4, h: 0.5, fontSize: 13, color: C.text1 });
  });

  card(s, C, 6.6, 1.5, 6.12, 3.05, { fill: C.background2, name: 'past winners card' });
  txt(s, 'Juara kategori teknologi sebelumnya', { x: 6.85, y: 1.65, w: 5.7, h: 0.35, fontSize: 16, bold: true, color: C.text1 });
  bullets(s, [
    [{ text: '2024: ', options: { bold: true } }, { text: 'CIROES (PT Inovasi Keberlanjutan Indonesia) juara Teknologi; Paktukang. Keduanya dikaitkan dengan pengelolaan IPL dan pemasaran properti digital.' }],
    [{ text: '2025: ', options: { bold: true } }, { text: '1.171 karya → 181 live pitching → 58 finalis. House Technology: PRANA TECH, Hayago Robotika, Mercusuar Agresif Perkasa. Value Chain: Parongpong RAW Lab, Wasteforchange, Andalusia Intra Teknologi.' }],
    [{ text: 'Hadiah: ', options: { bold: true } }, { text: 'total Rp1 M (2024) dan Rp1,5 M (2025); Batch 3 "miliaran". Juara mendapat inkubasi 3 bulan dan business matching dengan BTN.' }],
  ], { x: 6.85, y: 2.08, w: 5.7, h: 2.4, fontSize: 13, color: C.text1, paraSpaceAfter: 5 });

  card(s, C, 6.6, 4.75, 6.12, 1.7, { fill: C.accent1, name: 'real site rule' });
  txt(s, 'Syarat kunci untuk Estora', { x: 6.85, y: 4.88, w: 5.7, h: 0.32, fontSize: 15, bold: true, color: C.background1 });
  txt(s, 'Kategori usaha mapan wajib menunjuk perumahan nyata yang sudah dibangun, lengkap dengan titik Google Maps. Estora masuk lewat proyek Harmony Land 5 dengan persetujuan tertulis developer. Konfirmasi ke panitia sebelum 30 Nov.', { x: 6.85, y: 5.22, w: 5.7, h: 1.18, fontSize: 13, color: C.background1 });

  source(s, C, 'Sumber: btnhousingpreneur.com (jadwal, FAQ, kilas balik, panduan dokumen); pemberitaan BTN 15 Feb 2025 dan 31 Jan 2026. Nama juara 2024 peringkat 2–3 hanya dari situs agregator. Diakses 24 Nov 2026.');
  s.addNotes('Catatan risiko: surat pernyataan wajib memberi BTN hak memakai karya "untuk keperluan komersial maupun non-komersial" untuk promosi dan pengembangan, walau kepemilikan tetap di tim. Bagian hadiah, pajak, dan HKI di halaman syarat masih bertuliskan "MENUNGGU TEKS RESMI DARI LEGAL BTN". Struktur pitch 7 halaman menurut panduan: masalah & urgensi; pendekatan & pasar; ide; keunggulan kompetitif; konsep/prototipe; manfaat; model bisnis termasuk Sinergi BTN dan RAB.');
}

module.exports = { btnHistory };
