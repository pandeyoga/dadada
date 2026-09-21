# Kelanjutan katalog / R&D / sales — 2026-09-06

- Sumber disetujui pengguna: repo publik https://github.com/abagatacaba/kn, `main`, commit `3abbcabd3c3126d25115baba55e64d93080fde62`.
- Pengguna memilih: perbaiki selector varian, tuntaskan R&D hingga rilis dan deep-link, verifikasi sales mobile sampai SKU tersimpan dalam pesanan.
- Workspace awal template. Repo diimpor tanpa `.git`, `.emergent`, `.env`, node_modules atau build. Data produksi/foto lama tidak tersedia di repo ini. Database lokal menggunakan MONGO_URL/DB_NAME awal; bootstrap repo saja, tanpa menjalankan seed reset atau mereset transaksi.
- Pertahankan panduan `design_guidelines.md`, schema, SKU/product_id, routing, konfigurasi & Gemini lama. Tidak menambahkan integrasi atau key AI. AI tetap nonaktif jika belum dikonfigurasi.
- Runtime: React dev server melalui supervisor, FastAPI 8001, MongoDB dari env. KN_ALLOWED_ORIGINS ditambahkan menggunakan asal preview; variabel yang ada tidak ditimpa.
- Pemasangan pip penuh tersandung konflik dependency `emergentintegrations`/`litellm`; paket aplikasi terpasang dari requirements selain dua paket bawaan tersebut. Yarn frozen lockfile berhasil. Catatan ini bukan perubahan provider AI.
- Laporan lama iteration_3 menganggap penanda opsi hilang, tetapi snapshot repo SUDAH memuat ID opsi. Penyelidikan berfokus perilaku sebenarnya, bukan menambah ID ganda.
- Perubahan saat ini: penanda listbox/nilai opsi & disabled KNSelect, pemilih keluarga dengan pencarian stabil, loading/error/retry & cegah save sebelum kombinasi siap, mode hanya-baca mengikuti EntityScopeContext, izin submit/assess/decide sesuai endpoint, hilangkan fallback SKU pada quickview desktop/mobile.
- Pengujian lengkap belum selesai; jangan mengklaim hasil iteration_3 sebagai bukti sesi ini.