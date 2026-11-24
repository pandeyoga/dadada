// Reusable "dissection" slide for one competition winner: screenshots on the left, analysis on the right.
const { HEX, card, txt } = require('./lib');

const REL = { Tinggi: ['D5EBEF', HEX.accent1], Sedang: ['FBEBC8', '7A4F00'], Rendah: ['F2F4F4', '6B7F86'] };

// Fit images (each {path, w, h} in px) side by side inside a box, same height, with a gap.
function fitRow(s, imgs, bx, by, bw, bh, gap = 0.15) {
  const ratioSum = imgs.reduce((a, im) => a + im.w / im.h, 0);
  let h = Math.min(bh, (bw - gap * (imgs.length - 1)) / ratioSum);
  const totalW = ratioSum * h + gap * (imgs.length - 1);
  let x = bx + (bw - totalW) / 2;
  const y = by + (bh - h) / 2;
  imgs.forEach((im, i) => {
    const w = h * im.w / im.h;
    s.addImage({ path: im.path, x, y, w, h, objectName: 'evidence ' + i, altText: im.alt || 'screenshot' });
    x += w + gap;
  });
  return { y, h };
}

// Stack image rows vertically: rows = [[img, img], [img]]
function fitGrid(s, rows, bx, by, bw, bh, gap = 0.15) {
  const rh = (bh - gap * (rows.length - 1)) / rows.length;
  rows.forEach((r, i) => fitRow(s, r, bx, by + i * (rh + gap), bw, rh, gap));
}

function dissect(pres, C, sec, d) {
  const s = pres.addSlide({ masterName: 'CONTENT', sectionTitle: sec });
  s.addText(d.kicker, { placeholder: 'kicker' });
  s.addText(d.title, { placeholder: 'title' });
  const lx = 0.6, lw = d.leftW || 5.05, top = 1.45, bottom = 6.5;
  card(s, C, lx, top, lw, bottom - top, { fill: 'F3F6F7', name: 'evidence panel' });
  const capH = d.caption ? 0.4 : 0;
  if (d.rows) fitGrid(s, d.rows, lx + 0.15, top + 0.15, lw - 0.3, bottom - top - 0.3 - capH);
  if (d.caption) txt(s, d.caption, { x: lx + 0.15, y: bottom - 0.5, w: lw - 0.3, h: 0.38, fontSize: 10, color: C.accent5, align: 'center', valign: 'middle' });

  const rx = lx + lw + 0.3, rw = 12.72 - rx;
  txt(s, d.meta, { x: rx, y: top - 0.02, w: rw - 1.35, h: 0.46, fontSize: 11, bold: true, color: C.accent2, valign: 'middle' });
  const [rf, rc] = REL[d.relevance] || REL.Sedang;
  s.addShape('roundRect', { x: 12.72 - 1.25, y: top, w: 1.25, h: 0.36, rectRadius: 0.06, fill: { color: rf }, line: { color: rf, width: 0 }, objectName: 'relevance badge' });
  txt(s, 'Relevansi: ' + d.relevance, { x: 12.72 - 1.25, y: top, w: 1.25, h: 0.36, fontSize: 10, bold: true, color: rc, align: 'center', valign: 'middle' });

  const blocks = d.blocks;
  const lessonH = 0.82, avail = bottom - (top + 0.56) - lessonH - 0.12;
  const bh = avail / blocks.length;
  blocks.forEach(([label, body], i) => {
    const y = top + 0.56 + i * bh;
    txt(s, label, { x: rx, y, w: 1.55, h: bh - 0.06, fontSize: 12, bold: true, color: C.accent1 });
    txt(s, body, { x: rx + 1.6, y, w: rw - 1.6, h: bh - 0.06, fontSize: d.bodySize || 12, color: C.text1 });
    if (i < blocks.length - 1) s.addShape('line', { x: rx, y: y + bh - 0.04, w: rw, h: 0, line: { color: 'E1E8EA', width: 0.75 }, objectName: 'divider ' + i });
  });
  card(s, C, rx, bottom - lessonH, rw, lessonH, { fill: C.accent1, name: 'lesson' });
  s.addText([{ text: 'Untuk Estora: ', options: { bold: true, color: HEX.accent3 } }, { text: d.lesson, options: { color: 'FFFFFF' } }],
    { isTextBox: true, x: rx + 0.18, y: bottom - lessonH + 0.04, w: rw - 0.36, h: lessonH - 0.08, fontSize: 12, margin: 0, valign: 'middle', objectName: 'lesson text' });
  if (d.source) txt(s, d.source, { x: 0.6, y: 6.62, w: 12.1, h: 0.32, fontSize: 10, color: C.accent5, italic: true });
  if (d.notes) s.addNotes(d.notes);
  return s;
}

module.exports = { dissect, fitRow, fitGrid, REL };
