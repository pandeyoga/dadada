const { THEME, newDeck } = require('./lib');
const K = require('./slides_known');
const RN = require('./slides_app_rn');
const M = require('./slides_app_market');
let P = {};
try { P = require('./slides_app_pre'); } catch (e) { if (e.code !== 'MODULE_NOT_FOUND') throw e; }
const { applyTheme } = require('/root/.claude/skills/synced/f5f29f8b-67fe-4c81-89b1-19a5c4c0ab8d_f02363ae-4898-4f21-97aa-8e26cf30bd42/pptx/scripts/apply_theme.js');
const OUT = process.argv[2] || 'deck_app.pptx';

function divider(pres, sec, num, title, body) {
  const s = pres.addSlide({ masterName: 'SECTION_DARK', sectionTitle: sec });
  s.addText(num, { placeholder: 'num' }); s.addText(title, { placeholder: 'title' }); s.addText(body, { placeholder: 'body' });
}

(async () => {
  const { pres, C } = newDeck();
  pres.title = 'Riset aplikasi pesaing dan pemenang BTN Housingpreneur';
  const S0 = 'Pembuka', S1 = 'A. Aplikasi Rumah Ningrat', S2 = 'B. Aplikasi penghuni', S3 = 'C. Aplikasi developer, agen & pembeli', S4 = 'D. Pemenang BTN Housingpreneur', S5 = 'E. Implikasi untuk aplikasi Estora';

  pres.addSection({ title: S0 });
  const t = pres.addSlide({ masterName: 'TITLE_DARK', sectionTitle: S0 });
  t.addText('RISET APLIKASI', { placeholder: 'kicker' });
  t.addText('Aplikasi perumahan: Rumah Ningrat, pesaing, dan pemenang BTN Housingpreneur', { placeholder: 'title' });
  t.addText('Apa yang sudah ada, apa yang disukai pengguna dan juri, dan di mana aplikasi Estora bisa unggul', { placeholder: 'body' });
  t.addText('24 November 2026 · Data publik toko aplikasi & situs resmi per 23–24 November 2026', { placeholder: 'meta' });
  if (P.summary) await P.summary(pres, C, S0);
  if (P.lifecycle) await P.lifecycle(pres, C, S0);

  pres.addSection({ title: S1 });
  divider(pres, S1, '01', 'Aplikasi Rumah Ningrat', 'Empat lapis digital dari booking sampai penghuni, semuanya dibangun sendiri');
  await K.rnStack(pres, C, S1);
  await RN.rnBuyerWeb(pres, C, S1);
  await K.rnApp(pres, C, S1);
  await RN.rnApp2(pres, C, S1);
  await K.rnMitra(pres, C, S1);

  pres.addSection({ title: S2 });
  divider(pres, S2, '02', 'Aplikasi penghuni pesaing', '12 aplikasi estate dan RT: rating, pola layar, keluhan, dan peta fitur');
  await M.phRatings(pres, C, S2);
  await M.phGallery(pres, C, S2);
  await M.phComplaints(pres, C, S2);
  await M.phMatrix(pres, C, S2);
  await M.phModule(pres, C, S2);

  if (P.pre) {
    pres.addSection({ title: S3 });
    divider(pres, S3, '03', 'Aplikasi developer, agen & pembeli', 'Sebelum serah terima: alat bank, software developer, dan aplikasi agen');
    await P.pre(pres, C, S3);
  }

  pres.addSection({ title: S4 });
  divider(pres, S4, P.pre ? '04' : '03', 'Pemenang BTN Housingpreneur', 'Produk apa yang menang di 2024 dan 2025, dan apa artinya untuk Estora');
  await K.btnCriteria(pres, C, S4);
  await M.winTable(pres, C, S4);
  await M.winVisual(pres, C, S4);
  await M.winPatterns(pres, C, S4);

  if (P.implications) {
    pres.addSection({ title: S5 });
    divider(pres, S5, '05', 'Implikasi untuk aplikasi Estora', 'Celah fitur, layar yang perlu ditunjukkan, dan prioritas pengembangan');
    await P.implications(pres, C, S5);
  }

  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log('wrote', OUT);
})().catch((e) => { console.error(e); process.exit(1); });
