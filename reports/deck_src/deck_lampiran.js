// Deck gabungan: halaman Canva 1-9 + Lampiran screenshot prototipe "Rumah Dalam Genggaman".
// Pakai: NODE_PATH=<node_modules> node deck_lampiran.js "<out.pptx>"
const pptxgen = require('pptxgenjs');
const sharp = require('sharp');
const fs = require('fs');
const os = require('os');
const path = require('path');

const ROOT = path.join(__dirname, '..', '..');
const CANVA = path.join(__dirname, 'assets', 'canva');
const BRAND = path.join(ROOT, 'docs/superpowers/specs/assets/brand');
const INDEX = JSON.parse(fs.readFileSync(path.join(ROOT, 'docs/prototype/screens/index.json'), 'utf8'));
const OUT = process.argv[2] || path.join(ROOT, 'reports/Estora pitch deck + lampiran prototipe.pptx');
const TMP = fs.mkdtempSync(path.join(os.tmpdir(), 'lampiran-'));
const CANVA_PAGES = 9; // halaman Canva 10 = "DRAFT LAMPIRAN" (diganti sampul), 11-13 kosong

const FONT = 'Inter';
const C = { deep: '053B36', teal: '0A5A5E', mint: 'D6EFE6', ink: '14232A', muted: '5B6B70', accent: 'F2C14E', card: 'FFFFFF', line: 'D5E0E0', soft: 'E6F2EE', footer: 'B9D6D2' };
const SECTIONS = [
  { letter: 'A', role: 'Demo', name: 'Demo & masuk', sent: 'Cara juri berpindah peran: peluncur demo, masuk dengan OTP simulasi, dan pengaturan ulang data contoh.' },
  { letter: 'B', role: 'Pembeli', name: 'Pembeli', sent: 'Perjalanan pembeli dari memilih unit dan booking, memantau progres pembangunan, sampai pengajuan KPR.' },
  { letter: 'C', role: 'Serah terima', name: 'Serah terima', sent: 'Onboarding saat serah terima unit: berita acara serah terima (BAST) dan aktivasi akun penghuni.' },
  { letter: 'D', role: 'Warga', name: 'Warga', sent: 'Aplikasi harian penghuni: iuran, layanan, pasar warga, dan keamanan kawasan berbasis IoT (CCTV, SOS, tamu).' },
  { letter: 'E', role: 'Satpam', name: 'Satpam', sent: 'Aplikasi petugas keamanan untuk menerima SOS warga, mencatat tamu, dan memantau kejadian di kawasan.' },
  { letter: 'F', role: 'Pengelola', name: 'Pengelola', sent: 'Dasbor desktop pengelola kawasan: tagihan, tiket layanan, warga, dan laporan operasional.' },
  { letter: 'G', role: 'Mitra', name: 'Mitra', sent: 'Portal mitra pemasaran: prospek, komisi, dan status penjualan unit.' },
];
for (const s of SECTIONS) {
  s.items = INDEX.filter((x) => x.role === s.role);
  s.range = s.items.length === 1 ? s.items[0].id2 : `${s.items[0].id2}–${s.items[s.items.length - 1].id2}`;
}
const total = INDEX.length;

// ---------- aset ----------
async function bgGradient(name, dir) {
  const f = path.join(TMP, name + '.png');
  const [x2, y2] = dir === 'h' ? [1, 0.3] : [0.4, 1];
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080"><defs><linearGradient id="g" x1="0" y1="0" x2="${x2}" y2="${y2}"><stop offset="0" stop-color="#${C.deep}"/><stop offset="1" stop-color="#${C.teal}"/></linearGradient></defs><rect width="1920" height="1080" fill="url(#g)"/></svg>`;
  await sharp(Buffer.from(svg)).png().toFile(f);
  return f;
}
async function logoChip() { // logo di atas pil putih agar terbaca di latar hijau
  const f = path.join(TMP, 'logo-chip.png');
  const logo = await sharp(path.join(BRAND, 'estora_logo_full.png')).resize({ height: 150 }).toBuffer();
  const lm = await sharp(logo).metadata();
  const w = lm.width + 120, h = 150 + 90;
  const bg = Buffer.from(`<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}"><rect width="${w}" height="${h}" rx="44" fill="#fff"/></svg>`);
  await sharp(bg).composite([{ input: logo, left: 60, top: 45 }]).png().toFile(f);
  return { file: f, ratio: w / h };
}
async function rounded(src, out, height, radius) {
  const buf = await sharp(src).resize({ height }).toBuffer();
  const m = await sharp(buf).metadata();
  const w = m.width, h = m.height;
  const mask = Buffer.from(`<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}"><rect width="${w}" height="${h}" rx="${radius}" fill="#fff"/></svg>`);
  const border = Buffer.from(`<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}"><rect x="1" y="1" width="${w - 2}" height="${h - 2}" rx="${radius}" fill="none" stroke="#9FB3B3" stroke-width="2"/></svg>`);
  await sharp(buf).composite([{ input: mask, blend: 'dest-in' }, { input: border }]).png({ compressionLevel: 9, palette: false }).toFile(out);
  return { file: out, ratio: w / h };
}

// ---------- komponen ----------
let pres;
const footerText = 'Estora · Rumah Dalam Genggaman — prototipe, data contoh';
function footer(slide) {
  slide.addText(footerText, { x: 0.6, y: 7.05, w: 8, h: 0.28, fontFace: FONT, fontSize: 10, color: C.footer, margin: 0, valign: 'middle' });
  slide.slideNumber = { x: 12.2, y: 7.05, w: 0.55, h: 0.28, fontFace: FONT, fontSize: 10, color: C.footer, align: 'right' };
}
function title(slide, text) {
  slide.addText(text, { x: 0.6, y: 0.35, w: 12.1, h: 0.55, fontFace: FONT, fontSize: 24, bold: true, color: 'FFFFFF', margin: 0, valign: 'middle', fit: 'shrink' });
}
function labelBlock(slide, it, x, y, w, h, opts = {}) {
  const fs = opts.fs || 11;
  slide.addText([
    { text: `${it.id2} · ${it.title}`, options: { bold: true, fontSize: 13, color: C.deep, breakLine: true } },
    { text: it.desc, options: { fontSize: fs, color: C.ink, breakLine: true, paraSpaceBefore: 3 } },
    { text: it.route, options: { fontSize: 9, color: C.muted, fontFace: 'DejaVu Sans Mono', paraSpaceBefore: 4 } },
  ], { x, y, w, h, fontFace: FONT, margin: 0, valign: 'top', objectName: `label ${it.id2}` });
}
function rangeText(items) { return items.length === 1 ? items[0].id2 : `${items[0].id2}–${items[items.length - 1].id2}`; }

async function main() {
  pres = new pptxgen();
  pres.layout = 'LAYOUT_WIDE';
  pres.author = 'Tim Estora';
  pres.title = 'Estora pitch deck + lampiran prototipe Rumah Dalam Genggaman';
  pres.subject = 'BTN Housingpreneur 2026';
  pres.theme = { headFontFace: FONT, bodyFontFace: FONT };

  const bgV = await bgGradient('bg-v', 'v');
  const bgH = await bgGradient('bg-h', 'h');
  const chip = await logoChip();

  // 1-9: halaman Canva
  for (let i = 1; i <= CANVA_PAGES; i++) {
    const s = pres.addSlide();
    s.background = { color: 'FFFFFF' };
    s.addImage({ path: path.join(CANVA, `page-${String(i).padStart(2, '0')}.jpg`), x: 0, y: 0, w: 13.333, h: 7.5, altText: `Halaman pitch deck ${i}` });
  }

  // sampul Lampiran
  {
    const s = pres.addSlide();
    s.background = { path: bgH };
    s.addImage({ path: chip.file, x: 0.7, y: 0.6, h: 0.8, w: 0.8 * chip.ratio, altText: 'Logo Estora' });
    s.addText('Lampiran', { x: 0.7, y: 1.85, w: 7, h: 1.1, fontFace: FONT, fontSize: 60, bold: true, color: 'FFFFFF', margin: 0 });
    s.addText('Prototipe aplikasi Rumah Dalam Genggaman', { x: 0.7, y: 3.0, w: 6.6, h: 0.9, fontFace: FONT, fontSize: 24, color: C.mint, margin: 0, valign: 'top' });
    s.addText(`${total} halaman · 7 peran · data contoh, tanpa backend`, { x: 0.7, y: 4.15, w: 6.6, h: 0.4, fontFace: FONT, fontSize: 16, color: C.accent, bold: true, margin: 0 });
    // daftar bagian dalam kartu putih
    const cx = 7.9, cy = 1.0, cw = 4.8, ch = 5.5;
    s.addShape('roundRect', { x: cx, y: cy, w: cw, h: ch, rectRadius: 0.15, fill: { color: 'FFFFFF' }, line: { color: 'FFFFFF', width: 0 }, shadow: { type: 'outer', color: '000000', opacity: 0.25, blur: 10, offset: 3, angle: 90 } });
    s.addText('Isi lampiran', { x: cx + 0.35, y: cy + 0.25, w: cw - 0.7, h: 0.4, fontFace: FONT, fontSize: 15, bold: true, color: C.deep, margin: 0 });
    SECTIONS.forEach((sec, k) => {
      const y = cy + 0.85 + k * 0.62;
      s.addShape('ellipse', { x: cx + 0.35, y: y + 0.03, w: 0.42, h: 0.42, fill: { color: C.deep }, line: { color: C.deep, width: 0 } });
      s.addText(sec.letter, { x: cx + 0.35, y: y + 0.03, w: 0.42, h: 0.42, fontFace: FONT, fontSize: 13, bold: true, color: 'FFFFFF', align: 'center', valign: 'middle', margin: 0 });
      s.addText([{ text: sec.name, options: { bold: true, color: C.ink } }], { x: cx + 0.95, y, w: 2.6, h: 0.48, fontFace: FONT, fontSize: 14, valign: 'middle', margin: 0 });
      s.addText(sec.range, { x: cx + 3.4, y, w: 1.05, h: 0.48, fontFace: FONT, fontSize: 12, color: C.muted, align: 'right', valign: 'middle', margin: 0 });
    });
    footer(s);
  }

  // per bagian
  for (const sec of SECTIONS) {
    // pembatas
    {
      const s = pres.addSlide();
      s.background = { path: bgH };
      s.addImage({ path: chip.file, x: 0.7, y: 0.6, h: 0.6, w: 0.6 * chip.ratio, altText: 'Logo Estora' });
      s.addText(`Lampiran ${sec.letter}`, { x: 0.7, y: 2.3, w: 10, h: 0.6, fontFace: FONT, fontSize: 24, bold: true, color: C.accent, margin: 0 });
      s.addText(sec.name, { x: 0.7, y: 2.9, w: 11.5, h: 1.2, fontFace: FONT, fontSize: 54, bold: true, color: 'FFFFFF', margin: 0, valign: 'top' });
      s.addText(sec.sent, { x: 0.7, y: 4.25, w: 8.4, h: 1.0, fontFace: FONT, fontSize: 20, color: C.mint, margin: 0, valign: 'top' });
      s.addText(`${sec.range} · ${sec.items.length} halaman`, { x: 0.7, y: 5.55, w: 8, h: 0.4, fontFace: FONT, fontSize: 16, bold: true, color: 'FFFFFF', margin: 0 });
      footer(s);
    }
    const desktop = sec.role === 'Pengelola';
    const per = desktop ? 1 : 3;
    for (let i = 0; i < sec.items.length; i += per) {
      const group = sec.items.slice(i, i + per);
      const s = pres.addSlide();
      s.background = { path: bgV };
      title(s, `Lampiran ${sec.letter} · ${sec.name} — ${rangeText(group)}`);
      footer(s);
      if (desktop) {
        const it = group[0];
        const img = await rounded(path.join(ROOT, it.first), path.join(TMP, `${it.id2}.png`), 1100, 22);
        const ih = 5.5, iw = ih * img.ratio; // ~8.35 in
        s.addShape('roundRect', { x: 0.6, y: 1.2, w: 12.13, h: 5.65, rectRadius: 0.12, fill: { color: C.card }, line: { color: C.card, width: 0 } });
        s.addImage({ path: img.file, x: 0.68, y: 1.275, w: iw, h: ih, altText: `${it.id2} ${it.title}` });
        const lx = 0.68 + iw + 0.4;
        labelBlock(s, it, lx, 1.6, 12.73 - lx - 0.35 + 0.0, 4.5, { fs: 13 });
      } else {
        const cw = 3.85, gap = 0.29, x0 = (13.333 - (group.length * cw + (group.length - 1) * gap)) / 2;
        for (let k = 0; k < group.length; k++) {
          const it = group[k];
          const cx = x0 + k * (cw + gap);
          const img = await rounded(path.join(ROOT, it.first), path.join(TMP, `${it.id2}.png`), 620, 30);
          s.addShape('roundRect', { x: cx, y: 1.1, w: cw, h: 5.75, rectRadius: 0.12, fill: { color: C.card }, line: { color: C.card, width: 0 } });
          const ph = 4.2, pw = ph * img.ratio;
          s.addImage({ path: img.file, x: cx + (cw - pw) / 2, y: 1.25, w: pw, h: ph, altText: `${it.id2} ${it.title}` });
          labelBlock(s, it, cx + 0.22, 5.6, cw - 0.44, 1.2);
        }
      }
    }
  }

  // daftar halaman (2 slide, 2 tabel per slide)
  const rows = INDEX.map((x) => {
    const sec = SECTIONS.find((q) => q.role === x.role);
    return [x.id2, x.title, `${sec.letter} · ${sec.name}`];
  });
  const half = Math.ceil(rows.length / 4);
  const pages = [rows.slice(0, half * 2), rows.slice(half * 2)];
  pages.forEach((pg, pi) => {
    const s = pres.addSlide();
    s.background = { path: bgV };
    title(s, `Daftar halaman lampiran (${pi + 1}/2)`);
    footer(s);
    const mid = Math.ceil(pg.length / 2);
    [pg.slice(0, mid), pg.slice(mid)].forEach((part, ci) => {
      const hdr = ['ID', 'Halaman', 'Lampiran'].map((t) => ({ text: t, options: { bold: true, color: 'FFFFFF', fill: { color: C.deep }, fontSize: 10 } }));
      const body = part.map((r, ri) => r.map((t, k) => ({ text: t, options: { color: k === 0 ? C.deep : C.ink, bold: k === 0, fontSize: 10, fill: { color: ri % 2 ? C.soft : 'FFFFFF' } } })));
      s.addTable([hdr, ...body], {
        x: 0.6 + ci * 6.15, y: 1.1, w: 5.95, colW: [0.75, 3.1, 2.1], rowH: 0.34, fontFace: FONT, valign: 'middle',
        margin: [0, 0.08, 0, 0.08], border: { type: 'solid', color: C.line, pt: 0.5 },
      });
    });
  });

  await pres.writeFile({ fileName: OUT });
  console.log('OK', OUT, 'slides:', CANVA_PAGES + 1 + SECTIONS.length + INDEX.length / 3);
}
main().catch((e) => { console.error(e); process.exit(1); });
