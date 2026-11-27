# Sumber deck "Riset kompetitor dan BTN Housingpreneur"

Generator pptxgenjs untuk `reports/Riset kompetitor dan BTN Housingpreneur.pptx`.

1. `npm install` di folder ini (pptxgenjs, react-icons, react, react-dom, sharp).
2. `python3 prep_assets.py "<repo>/research_notes/Riset Rumah Ningrat dan aplikasinya/screenshots" assets` — membuat screenshot ponsel bersudut bulat dan potongan portal mitra.
3. `NODE_PATH=$PWD/node_modules node deck.js out.pptx`

`deck.js` memanggil `apply_theme.js` dari skill pptx (path absolut di dalam file); sesuaikan bila dijalankan di mesin lain.
Isi data ada di `slides_known.js` (BTN + Rumah Ningrat), `slides_btn_history.js`, dan `slides_research.js` (pesaing + implikasi).

## Deck riset aplikasi
`NODE_PATH=$PWD/node_modules node deck_app.js out.pptx` membangun `reports/Riset aplikasi pesaing dan pemenang BTN.pptx`
(29 slide, khusus domain aplikasi). Selain aset dari `prep_assets.py`, deck ini memakai potongan screenshot dari
`research_notes/Riset aplikasi pesaing dan pemenang BTN/screenshots/` dan `research_notes/Riset Rumah Ningrat dan aplikasinya/screenshots/web/`
yang diskalakan ke tinggi 900 px dengan sudut membulat (nama berkas `ph_*`, `pre_*`, `win_*`, `rn_*` di folder assets).

## Deck bedah pemenang BTN Housingpreneur
`NODE_PATH=$PWD/node_modules node deck_bedah.js out.pptx` membangun `reports/Bedah pemenang BTN Housingpreneur.pptx` (34 slide).
Gambar di `assets/bd/` dipotong dari `research_notes/Bedah pemenang BTN Housingpreneur/screenshots/` (lihat kotak potong di
skrip persiapan aset dalam riwayat sesi) dan diskalakan maksimal 1100 px dengan sudut membulat.

## Deck gabungan + lampiran
`NODE_PATH=$PWD/node_modules node deck_lampiran.js "../Estora pitch deck + lampiran prototipe.pptx"` membangun deck gabungan
(46 slide): halaman Canva 1–9 sebagai gambar penuh (`assets/canva/page-NN.jpg`), sampul Lampiran, pembatas + slide isi per peran (A–G),
dan daftar halaman. Screenshot diambil dari `docs/prototype/screens/index.json` (kolom `first`, PNG `--layar`); fonta Inter.
Halaman Canva diekspor dari PDF dengan `pdftoppm -jpeg -jpegopt quality=85 -scale-to-x 1920 -scale-to-y 1080 <pdf> assets/canva/page`
(halaman 10 "DRAFT LAMPIRAN" dan 11–13 kosong tidak dipakai). PDF: halaman 1–9 diambil langsung dari PDF Canva asli (vektor, bisa dicari; diskalakan ke 960×540 pt dengan pypdf), halaman 10 dst. dari hasil `soffice --headless --convert-to pdf "<pptx>"`, digabung dengan pypdf (`PdfWriter`).
