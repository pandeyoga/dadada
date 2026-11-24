// Shared theme, layouts and drawing helpers for the research deck.
const pptxgen = require('pptxgenjs');
const React = require('react');
const ReactDOMServer = require('react-dom/server');
const sharp = require('sharp');
const path = require('path');

const ASSETS = path.join(__dirname, 'assets');

const THEME = {
  name: 'Estora Riset',
  headFontFace: 'Cambria',
  bodyFontFace: 'Calibri',
  colors: {
    dk1: '14232A', lt1: 'FFFFFF', dk2: '0B3A4A', lt2: 'EEF4F5',
    accent1: '066784', // Estora teal
    accent2: 'C2562F', // terracotta (genteng)
    accent3: 'E3A82B', // amber
    accent4: '4F8A6E', // sage
    accent5: '6B7F86', // slate
    accent6: '8E3B5B', // berry
    hlink: '066784', folHlink: '4F6B75',
  },
};
const HEX = THEME.colors;

function newDeck() {
  const pres = new pptxgen();
  pres.layout = 'LAYOUT_WIDE'; // 13.333 x 7.5
  pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
  pres.author = 'Tim Estora';
  pres.title = 'Riset Rumah Ningrat, Kompetitor dan BTN Housingpreneur';
  pres.subject = 'Riset pasar dan kompetitor digitalisasi developer perumahan';
  const C = pres.SchemeColor;

  const FOOT = 'Riset pasar & kompetitor · Estora · November 2026';

  pres.defineSlideMaster({
    title: 'TITLE_DARK',
    background: { color: C.text2 },
    objects: [
      { placeholder: { options: { name: 'kicker', type: 'body', x: 0.8, y: 1.35, w: 9.5, h: 0.45, fontSize: 16, bold: true, color: C.accent3, margin: 0, valign: 'top' }, text: '' } },
      { placeholder: { options: { name: 'title', type: 'title', x: 0.8, y: 1.9, w: 10.2, h: 2.4, fontSize: 44, bold: true, color: C.background1, margin: 0, valign: 'top', align: 'left' }, text: '' } },
      { placeholder: { options: { name: 'body', type: 'body', x: 0.8, y: 4.45, w: 9.5, h: 1.0, fontSize: 20, color: 'CFE3E8', margin: 0, valign: 'top' }, text: '' } },
      { placeholder: { options: { name: 'meta', type: 'body', x: 0.8, y: 6.3, w: 9.0, h: 0.4, fontSize: 14, color: 'A9C4CB', margin: 0, valign: 'top' }, text: '' } },
    ],
  });

  pres.defineSlideMaster({
    title: 'SECTION_DARK',
    background: { color: C.text2 },
    objects: [
      { placeholder: { options: { name: 'num', type: 'body', x: 0.8, y: 2.0, w: 3.0, h: 1.2, fontSize: 72, bold: true, color: C.accent3, margin: 0, valign: 'top' }, text: '' } },
      { placeholder: { options: { name: 'title', type: 'title', x: 0.8, y: 3.3, w: 10.5, h: 1.2, fontSize: 40, bold: true, color: C.background1, margin: 0, valign: 'top', align: 'left' }, text: '' } },
      { placeholder: { options: { name: 'body', type: 'body', x: 0.8, y: 4.55, w: 10.0, h: 1.0, fontSize: 18, color: 'CFE3E8', margin: 0, valign: 'top' }, text: '' } },
    ],
    slideNumber: { x: 12.2, y: 6.95, w: 0.6, h: 0.3, fontSize: 10, color: 'A9C4CB', align: 'right' },
  });

  pres.defineSlideMaster({
    title: 'CONTENT',
    background: { color: C.background1 },
    margin: [0.5, 0.5, 0.7, 0.5],
    objects: [
      { placeholder: { options: { name: 'kicker', type: 'body', x: 0.6, y: 0.32, w: 10.0, h: 0.32, fontSize: 12, bold: true, color: C.accent1, margin: 0, valign: 'top', charSpacing: 1 }, text: '' } },
      { placeholder: { options: { name: 'title', type: 'title', x: 0.6, y: 0.62, w: 12.1, h: 0.75, fontSize: 28, bold: true, color: C.text1, margin: 0, valign: 'top', align: 'left' }, text: '' } },
      { text: { text: FOOT, options: { x: 0.6, y: 7.0, w: 8.0, h: 0.28, fontSize: 10, color: C.accent5, margin: 0, isTextBox: true } } },
    ],
    slideNumber: { x: 12.2, y: 6.98, w: 0.55, h: 0.28, fontSize: 10, color: HEX.accent5, align: 'right' },
  });

  return { pres, C };
}

async function icon(Comp, colorHex, size = 256) {
  const svg = ReactDOMServer.renderToStaticMarkup(React.createElement(Comp, { color: '#' + colorHex, size: String(size) }));
  const buf = await sharp(Buffer.from(svg)).png().toBuffer();
  return 'image/png;base64,' + buf.toString('base64');
}

// A filled circle with a white icon centred in it.
async function iconCircle(slide, C, Comp, x, y, d, fill, name) {
  slide.addShape('ellipse', { x, y, w: d, h: d, fill: { color: fill }, line: { color: fill, width: 0 }, objectName: (name || 'icon') + ' circle' });
  const pad = d * 0.27;
  slide.addImage({ data: await icon(Comp, 'FFFFFF'), x: x + pad, y: y + pad, w: d - 2 * pad, h: d - 2 * pad, objectName: (name || 'icon') + ' glyph', altText: name || 'ikon' });
}

function card(slide, C, x, y, w, h, opts = {}) {
  slide.addShape('roundRect', {
    x, y, w, h, rectRadius: 0.12,
    fill: { color: opts.fill || C.background2 },
    line: opts.line ? { color: opts.line, width: opts.lineW || 1.25 } : { color: opts.fill || C.background2, width: 0 },
    shadow: opts.shadow ? { type: 'outer', color: '0B3A4A', opacity: 0.12, blur: 8, offset: 2, angle: 90 } : undefined,
    objectName: opts.name || 'card',
  });
}

function txt(slide, text, o) {
  slide.addText(text, Object.assign({ isTextBox: true, margin: 0, valign: 'top', fontSize: 14 }, o));
}

function bullets(slide, items, o) {
  const runs = items.map((it, i) => {
    const base = typeof it === 'string' ? [{ text: it }] : it;
    return base.map((r, j) => ({ text: r.text, options: Object.assign({}, r.options || {}, j === 0 ? { bullet: { indent: 14 } } : {}, (j === base.length - 1 && i < items.length - 1) ? { breakLine: true } : {}) }));
  }).flat();
  slide.addText(runs, Object.assign({ isTextBox: true, margin: 0, valign: 'top', fontSize: 14, paraSpaceAfter: 6 }, o));
}

function source(slide, C, text) {
  txt(slide, text, { x: 0.6, y: 6.62, w: 12.1, h: 0.32, fontSize: 10, color: C.accent5, italic: true, objectName: 'source' });
}

module.exports = { THEME, HEX, ASSETS, newDeck, icon, iconCircle, card, txt, bullets, source, path };
