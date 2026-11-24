# Sumber deck "Riset kompetitor dan BTN Housingpreneur"

Generator pptxgenjs untuk `reports/Riset kompetitor dan BTN Housingpreneur.pptx`.

1. `npm install` di folder ini (pptxgenjs, react-icons, react, react-dom, sharp).
2. `python3 prep_assets.py "<repo>/research_notes/Riset Rumah Ningrat dan aplikasinya/screenshots" assets` — membuat screenshot ponsel bersudut bulat dan potongan portal mitra.
3. `NODE_PATH=$PWD/node_modules node deck.js out.pptx`

`deck.js` memanggil `apply_theme.js` dari skill pptx (path absolut di dalam file); sesuaikan bila dijalankan di mesin lain.
Isi data ada di `slides_known.js` (BTN + Rumah Ningrat), `slides_btn_history.js`, dan `slides_research.js` (pesaing + implikasi).
