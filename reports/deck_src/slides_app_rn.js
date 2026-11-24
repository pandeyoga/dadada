// App-domain slides for Rumah Ningrat beyond the ones in slides_known.js.
const { ASSETS, card, txt, bullets, source, path } = require('./lib');
const A = (f) => path.join(ASSETS, f);

async function rnBuyerWeb(pres, C, sec) {
  const s = pres.addSlide({ masterName: 'CONTENT', sectionTitle: sec });
  s.addText('RUMAH NINGRAT · SEBELUM SERAH TERIMA', { placeholder: 'kicker' });
  s.addText('Pembeli dilayani lewat web, bukan aplikasi di toko', { placeholder: 'title' });
  const cols = [
    { img: 'rn_cost.png', w0: 432, h0: 501, head: 'Booking mandiri', pts: ['Pilih blok langsung di peta', 'Rincian biaya terbuka per komponen', 'Bayar lewat payment gateway; diskon untuk booking online'] },
    { img: 'rn_buyer_app.png', w0: 500, h0: 505, head: '"Ningrat Apps" pembeli', pts: ['Status proses, sisa tagihan, jatuh tempo', 'Progres bangunan per tahap (contoh 13/27)', 'SPR digital, invoice, komplain'] },
    { img: 'rn_complaint.png', w0: 615, h0: 455, head: 'Dashboard Warga', pts: ['Masuk dengan nomor KTP', 'Tiket komplain: dibuat → verifikasi → eskalasi', 'Ada PIC, foto, dan status garansi'] },
  ];
  const cw = 3.88, gap = 0.24, ih = 2.55;
  cols.forEach((c, i) => {
    const x = 0.6 + i * (cw + gap);
    card(s, C, x, 1.5, cw, 4.95, { fill: C.background2, name: 'buyer col ' + c.head });
    let w = ih * c.w0 / c.h0, h = ih;
    if (w > cw - 0.4) { w = cw - 0.4; h = w * c.h0 / c.w0; }
    s.addImage({ path: A(c.img), x: x + (cw - w) / 2, y: 1.7 + (ih - h) / 2, w, h, objectName: 'buyer img ' + c.head, altText: 'Screenshot Rumah Ningrat: ' + c.head });
    txt(s, c.head, { x: x + 0.25, y: 4.42, w: cw - 0.5, h: 0.38, fontSize: 16, bold: true, color: C.text1 });
    bullets(s, c.pts, { x: x + 0.25, y: 4.85, w: cw - 0.5, h: 1.5, fontSize: 13, color: C.text1, paraSpaceAfter: 3 });
  });
  source(s, C, 'Sumber: rumahningrat.com/detail/70, rnliving.rumahningrat.com, customer.rumahningrat.com (halaman publik, dirender 24 Nov 2026). "Ningrat Apps" tampil sebagai mockup; tidak ditemukan di Google Play atau App Store.');
  s.addNotes('Mockup Ningrat Apps memperlihatkan aplikasi pembeli pra-serah terima. Di toko hanya ada Keluarga Ningrat (penghuni). Kemungkinan Ningrat Apps = dashboard web yang sama atau rencana aplikasi. Login Dashboard Warga hanya meminta nomor KTP di halaman publik; langkah verifikasi berikutnya tidak diuji.');
}

async function rnApp2(pres, C, sec) {
  const s = pres.addSlide({ masterName: 'CONTENT', sectionTitle: sec });
  s.addText('RUMAH NINGRAT · FITUR ANDALAN APLIKASI PENGHUNI', { placeholder: 'kicker' });
  s.addText('Uang dan rasa aman jadi alasan warga membuka aplikasi', { placeholder: 'title' });
  const phones = [
    ['app_05.png', 'Ningrat Pay', 'PPOB: pulsa, data, PLN, PDAM'],
    ['app_07.png', 'SOS', 'Tahan 3 detik; peringatan UU ITE'],
    ['app_09.png', 'Live CCTV', 'Kamera EZVIZ per titik'],
    ['app_03.png', 'Marketplace', 'Jualan antar-warga & jasa'],
  ];
  const ph = 4.3, pw = ph * 480 / 1039, gap = (12.12 - 4 * pw) / 3;
  phones.forEach(([f, h, d], i) => {
    const x = 0.6 + i * (pw + gap);
    s.addImage({ path: A(f), x, y: 1.5, w: pw, h: ph, objectName: 'phone ' + h, altText: 'Screenshot Keluarga Ningrat: ' + h });
    txt(s, h, { x: x - 0.3, y: 5.9, w: pw + 0.6, h: 0.32, fontSize: 15, bold: true, color: C.text1, align: 'center' });
    txt(s, d, { x: x - 0.4, y: 6.22, w: pw + 0.8, h: 0.32, fontSize: 12, color: C.accent5, align: 'center' });
  });
  source(s, C, 'Sumber: screenshot resmi App Store (id6752388007) dan Google Play (com.trusmi.keluarganingrat); set Play identik dengan iOS. Diakses 24 Nov 2026.');
}

module.exports = { rnBuyerWeb, rnApp2 };
