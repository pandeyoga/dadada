const { THEME, newDeck } = require('./lib');
const B = require('./slides_bedah');
const { applyTheme } = require('/root/.claude/skills/synced/f5f29f8b-67fe-4c81-89b1-19a5c4c0ab8d_f02363ae-4898-4f21-97aa-8e26cf30bd42/pptx/scripts/apply_theme.js');
const OUT = process.argv[2] || 'deck_bedah.pptx';
function divider(pres, sec, num, title, body) {
  const s = pres.addSlide({ masterName: 'SECTION_DARK', sectionTitle: sec });
  s.addText(num, { placeholder: 'num' }); s.addText(title, { placeholder: 'title' }); s.addText(body, { placeholder: 'body' });
}
(async () => {
  const { pres, C } = newDeck();
  pres.title = 'Bedah pemenang BTN Housingpreneur 2024-2025';
  const S0 = 'Pembuka', S1 = 'A. Batch 1 (2024)', S2 = 'B. Batch 2 (2025)', S3 = 'C. Sintesis', S4 = 'D. Untuk Estora';
  pres.addSection({ title: S0 });
  const t = pres.addSlide({ masterName: 'TITLE_DARK', sectionTitle: S0 });
  t.addText('BEDAH PEMENANG', { placeholder: 'kicker' });
  t.addText('BTN Housingpreneur 2024–2025: apa yang menang dan kenapa', { placeholder: 'title' });
  t.addText('17 juara dibedah dengan screenshot dan analisis, lalu diterjemahkan menjadi strategi pitch Estora', { placeholder: 'body' });
  t.addText('24 November 2026 · Sumber resmi BTN, situs pemenang, dan media per 24 November 2026', { placeholder: 'meta' });
  await B.opening(pres, C, S0);
  pres.addSection({ title: S1 });
  divider(pres, S1, '01', 'Batch 1 (2024): 946 tim, 20 juara', 'CIROES, Paktukang, Autoconz, Rebricks & Plustik, Rusun Swadaya, dan Harmony Land Group');
  B.batch1(pres, C, S1);
  pres.addSection({ title: S2 });
  divider(pres, S2, '02', 'Batch 2 (2025): 1.171 karya, 27 juara', 'House Technology, Value Chain, Affordable, ideasi, dan finalis Ontoown');
  B.batch2(pres, C, S2);
  pres.addSection({ title: S3 });
  divider(pres, S3, '03', 'Sintesis', 'Sinergi BTN setelah menang, perbandingan, pola, dan anatomi pitch juara');
  await B.synthesis(pres, C, S3);
  pres.addSection({ title: S4 });
  divider(pres, S4, '04', 'Untuk Estora', 'Posisi dibanding juara, usulan alur pitch, dan mitra dari alumni');
  await B.forEstora(pres, C, S4);
  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log('wrote', OUT);
})().catch((e) => { console.error(e); process.exit(1); });
