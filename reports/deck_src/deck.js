const { THEME, newDeck } = require('./lib');
const K = require('./slides_known');
let R = {};
try { R = require('./slides_research'); } catch (e) { if (e.code !== 'MODULE_NOT_FOUND') throw e; }
const { applyTheme } = require('/root/.claude/skills/synced/f5f29f8b-67fe-4c81-89b1-19a5c4c0ab8d_f02363ae-4898-4f21-97aa-8e26cf30bd42/pptx/scripts/apply_theme.js');

const OUT = process.argv[2] || 'deck.pptx';

function divider(pres, sec, num, title, body) {
  const s = pres.addSlide({ masterName: 'SECTION_DARK', sectionTitle: sec });
  s.addText(num, { placeholder: 'num' });
  s.addText(title, { placeholder: 'title' });
  s.addText(body, { placeholder: 'body' });
  return s;
}

(async () => {
  const { pres, C } = newDeck();

  const S0 = 'Pembuka', S1 = 'A. Arena BTN Housingpreneur', S2 = 'B. Studi kasus Rumah Ningrat', S3 = 'C. Peta pesaing', S4 = 'D. Implikasi untuk Estora';

  pres.addSection({ title: S0 });
  const t = pres.addSlide({ masterName: 'TITLE_DARK', sectionTitle: S0 });
  t.addText('RISET PASAR & KOMPETITOR', { placeholder: 'kicker' });
  t.addText('Digitalisasi developer perumahan: Rumah Ningrat, pesaing, dan peluang Estora', { placeholder: 'title' });
  t.addText('Bekal posisi Estora untuk BTN Housingpreneur Batch 3', { placeholder: 'body' });
  t.addText('24 November 2026 · Data publik per 23–24 November 2026', { placeholder: 'meta' });
  if (R.summary) await R.summary(pres, C, S0);

  pres.addSection({ title: S1 });
  divider(pres, S1, '01', 'Arena: BTN Housingpreneur Batch 3', 'Siapa boleh ikut, kategori mana yang cocok, dan apa yang dinilai juri');
  await K.btnTracks(pres, C, S1);
  await K.btnCriteria(pres, C, S1);
  if (R.btnHistory) await R.btnHistory(pres, C, S1);

  pres.addSection({ title: S2 });
  divider(pres, S2, '02', 'Studi kasus: Rumah Ningrat', 'Developer rumah subsidi dengan tumpukan digital paling lengkap di kelasnya');
  await K.rnProfile(pres, C, S2);
  await K.rnStack(pres, C, S2);
  await K.rnApp(pres, C, S2);
  await K.rnMitra(pres, C, S2);
  await K.rnRisk(pres, C, S2);

  if (R.competitors) {
    pres.addSection({ title: S3 });
    divider(pres, S3, '03', 'Peta pesaing', 'Developer sejenis dan perangkat lunak yang sudah dipakai developer');
    await R.competitors(pres, C, S3);
  }
  if (R.implications) {
    pres.addSection({ title: S4 });
    divider(pres, S4, '04', 'Implikasi untuk Estora', 'Posisi, celah yang harus ditutup, dan langkah menuju 30 November');
    await R.implications(pres, C, S4);
  }

  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log('wrote', OUT);
})().catch((e) => { console.error(e); process.exit(1); });
