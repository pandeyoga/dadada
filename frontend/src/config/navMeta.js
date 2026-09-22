// ─── NAV META DATA (SSOT untuk TopBar kicker/title, role-home, guidance) ──────
// Dipisah dari navigationConfig.js agar file config di bawah batas guardrail.

// PAGE META (SSOT untuk TopBar kicker + title)
export const PAGE_META = {
  // S#094 — nama menu 1–2 kata; istilah teknis/singkatan (POS, CRM, WMS, PO, AP, BOM, R&D) hidup di judul halaman.
  "orders":               { kicker: "Penjualan",      title: "Pesanan Penjualan (SO) & Retur" },
  "purchasing":           { kicker: "Pembelian",      title: "Pesanan Pembelian (PO)" },
  "operations":           { kicker: "Gudang",         title: "Operasi Gudang (WMS) · Barang Masuk, Keluar, Opname & Transfer" },
  "suppliers":            { kicker: "Pembelian",      title: "Pemasok (Supplier) · Master & Kinerja" },
  "makloons":             { kicker: "Pembelian",      title: "Pengadaan (Sourcing) · Makloon & RFQ" },
  "amendments":           { kicker: "Penjualan",      title: "Koreksi Pesanan (Amendment)" },
  "costing":              { kicker: "Pembelian",      title: "Harga Pokok & Landed Cost" },
  "reorder":              { kicker: "Gudang",         title: "Titik Pesan Ulang (Reorder Point)" },
  "reports":              { kicker: "Keuangan",       title: "Laporan & Analitik Keuangan" },
  "documents":            { kicker: "Alat",           title: "Pusat Cetak · Dokumen PDF & Label" },
  "admin":                { kicker: "Pengaturan",     title: "Pengaturan & Master Data" },
  "escalations":          { kicker: "Kerja Saya",     title: "Eskalasi & Tindak Lanjut" },
  "home":                 { kicker: "Kerja Saya",     title: "Beranda" },
  admin:                  { kicker: "Pengaturan",     title: "Master Data & Audit" },
  "admin-home":           { kicker: "Eksekutif",      title: "Control Tower" },
  "manager-home":         { kicker: "Manajer",        title: "Dasbor Manajer \u00b7 Persetujuan, Target Tim & Keterlambatan" },
  sales:                  { kicker: "Penjualan",      title: "POS / Sales Portal" },
  "sales-home":           { kicker: "Penjualan",      title: "Performa Saya" },
  "customers-crm":        { kicker: "Penjualan",      title: "Pelanggan & CRM \u00b7 Sales Force" },
  "price-approvals":      { kicker: "Persetujuan",      title: "Persetujuan Harga Khusus" },
  orders:                 { kicker: "Penjualan",      title: "Pesanan Penjualan" },
  // FASE E-8 (E8.7/E8.20) — dua MEJA KERJA peran baru. Tanpa baris ini kepala halaman
  // jatuh ke cadangan "BERANDA · Kain Nusantara" di layar yang justru jadi tempat kerja
  // harian dua peran (kelas bug yang ditangkap `check_nav_map.py` CHECK 5).
  "sales-admin-desk":     { kicker: "Admin Sales",    title: "Meja Admin Sales \u00b7 Antrean Alur Pesanan" },
  "finance-desk":         { kicker: "Finance",        title: "Meja Finance \u00b7 Uang Masuk & Pajak Keluaran" },
  "md-desk":              { kicker: "MD",             title: "Meja MD \u00b7 Desain, Sample & Bahan" },
  "my-desk":              { kicker: "Kerja saya",     title: "Meja Saya \u00b7 Giliran & Antrean Peran" },
  "warehouse-admin-desk": { kicker: "Admin Gudang",   title: "Meja Admin Gudang \u00b7 Operasi Gudang & Logistik" },
  "sample-admin-desk":    { kicker: "Admin Sampel",   title: "Meja Admin Sampel \u00b7 Antrean Pesanan Sampel" },
  "sample-orders":        { kicker: "Penjualan",      title: "Pesanan Sampel (SOS) \u00b7 Terpisah dari SO Biasa" },
  amendments:             { kicker: "Keuangan \u00b7 Kendali", title: "Pusat Amandemen \u00b7 Koreksi Ber-alasan & Ber-jejak" },
  "tax-invoices":         { kicker: "Keuangan \u00b7 Pajak", title: "Faktur Pajak Keluaran" },
  "returns":              { kicker: "Penjualan",      title: "Retur & Barang Sisa" },
  "return-policies":      { kicker: "Penjualan",      title: "Kebijakan Retur Jual" },
  "special-orders":       { kicker: "Penjualan",      title: "Pesanan Khusus · Produk Custom Pelanggan" },
  // FASE E-7 (E7d) — permintaan barang antar badan usaha. Tanpa baris ini judul layar
  // jatuh ke cadangan "Kain Nusantara" / kicker "Workspace" (pengguna kehilangan konteks).
  "internal-requests":    { kicker: "Antar Entitas",  title: "Permintaan Internal (PIN)" },
  // FASE D — papan pekerjaan desain (CHECK 5 `check_nav_map`: setiap layar wajib berjudul).
  "design-requests":      { kicker: "Desain",         title: "Permintaan Desain (DSR)" },
  "marketing-hub":        { kicker: "Marketing",      title: "Marketing & Sosial Media" },
  "mkt-calendar":         { kicker: "Marketing",      title: "Kalender Konten \u00b7 Rencana, Review & Jadwal Tayang" },
  "mkt-campaigns":        { kicker: "Marketing",      title: "Kampanye \u00b7 Tema & Periode Konten" },
  "mkt-analytics":        { kicker: "Marketing",      title: "Dashboard Sosmed \u00b7 KPI, Tren & Performa Konten" },
  "mkt-accounts":         { kicker: "Marketing",      title: "Akun Sosmed \u00b7 per Badan Usaha" },
  // FASE I — dokumen inspeksi & QC (SPK). Tanpa baris ini judul layar jatuh ke
  // cadangan "Kain Nusantara" dan CHECK 5 `check_nav_map` memerah.
  "inspections":          { kicker: "Gudang & Operasi", title: "SPK Inspeksi & QC (INS)" },
  "pricelist":            { kicker: "Penjualan",      title: "Pricelist per-Entitas (PT)" },
  "color-library":        { kicker: "Penjualan",      title: "Pustaka Warna (Pantone)" },
  "domain-registry":      { kicker: "Pengaturan",     title: "Registri Domain Tekstil (Tahap · Jenis Kain · Grade)" },
  "product-templates":    { kicker: "Produk & Harga", title: "Produk & Varian" },
  "approval-inbox":       { kicker: "Persetujuan",      title: "Pusat Persetujuan" },
  "my-approvals":         { kicker: "Persetujuan",      title: "Persetujuan Saya \u00b7 Matriks Divisi (ACC Desain \u00b7 Sample \u00b7 PO Custom \u00b7 PR \u00b7 Klaim Makloon)" },
  "approval-rules":       { kicker: "Pengaturan",     title: "Aturan Persetujuan" },
  "entity-masters":       { kicker: "Pengaturan",     title: "Master per Badan Usaha" },
  "pdf-templates":        { kicker: "Pengaturan",     title: "Desainer Template PDF" },
  "document-center":      { kicker: "Dokumen",        title: "Pusat Dokumen" },
  "doc-trace":            { kicker: "Dokumen",        title: "Jejak Dokumen (Relasi Antar Surat)" },
  "payment-plans":        { kicker: "Keuangan",       title: "Rencana Pembayaran & Denda" },
  purchasing:             { kicker: "Pembelian",      title: "Pesanan Pembelian (PO)" },
  "po-board":             { kicker: "Pembelian",      title: "Papan PO per Lini" },
  "blanket-po":           { kicker: "Pembelian",      title: "Blanket / Contract PO · Call-off" },
  "purchase-requisitions":{ kicker: "Pembelian",      title: "Permintaan Pembelian (PR)" },
  reorder:                { kicker: "Pembelian",      title: "Saran Reorder · Replenishment" },
  suppliers:              { kicker: "Pembelian",      title: "Master Pemasok (Supplier)" },
  makloons:               { kicker: "Pembelian",      title: "Mitra Makloon (Subkontraktor)" },
  "process-recipes":      { kicker: "Pembelian",      title: "Resep Proses (Konversi & Rumus Makloon)" },
  "makloon-orders":       { kicker: "Pembelian",      title: "Order Makloon (Subkontrak \u00b7 WIP-at-Vendor)" },
  "makloon-claims":       { kicker: "Pembelian",      title: "Klaim Selisih Makloon \u00b7 Persetujuan & Skor Mitra" },
  "supplier-contracts":   { kicker: "Pembelian",      title: "Kontrak Mitra & Supplier \u00b7 Tarif, Susut & Toleransi" },
  "supplier-items":       { kicker: "Pembelian",      title: "Barang Supplier \u00b7 Peta SKU/Nama Supplier & Impor Massal" },
  "md-products":          { kicker: "Master Data",    title: "Produk & Varian" },
  // FASE F — R&D (hulu rantai: spesifikasi → labdip/proofing → kontrak).
  "rnd-specs":            { kicker: "R&D",             title: "Spesifikasi Produk (R&D) \u00b7 Target Kain, Warna & Desain" },
  "rnd-samples":          { kicker: "R&D",             title: "Permintaan Sample \u00b7 Labdip / Handfeel / Proofing" },
  "rnd-labdip":           { kicker: "R&D",             title: "Labdip (Master) \u00b7 Sampel Warna per Supplier" },
  "rnd-handfeel":         { kicker: "R&D",             title: "Handfeel (Master) \u00b7 Sampel Pegangan & Konstruksi Kain" },
  "rnd-proofing":         { kicker: "R&D",             title: "Proofing (Master) \u00b7 Sampel Cetak Desain" },
  "rnd-reports":          { kicker: "R&D",             title: "Laporan R&D \u00b7 SLA Round & Tahap Produk" },
  // PS-18 — menu DESAINER (terpisah dari R&D): orang + karyanya.
  "designer-kpi":         { kicker: "Desainer",        title: "KPI Desainer \u00b7 Tepat Waktu, Pengulangan & Eskalasi SLA" },
  "rnd-designs":          { kicker: "Desainer",        title: "Desain & Pattern (Master) \u00b7 Kode, Versi & Pengesahan" },
  "rnd-divisions":        { kicker: "Desainer",        title: "Divisi & Persetujuan R&D \u00b7 Penempatan Tim & Matriks Approver" },
  "md-categories":        { kicker: "Master Data",    title: "Kategori Produk" },
  "md-uoms":              { kicker: "Master Data",    title: "Satuan & Konversi" },
  "uom-conversions":      { kicker: "Master Data",    title: "Satuan & Konversi" },
  "inventory-lots":       { kicker: "Gudang",         title: "Lot & Silsilah \u00b7 Traceability, Recall & Label" },
  "md-warehouses":        { kicker: "Gudang",         title: "Gudang (Master) \u00b7 Lokasi & Bin" },
  "purchase-approval":    { kicker: "Persetujuan",      title: "Persetujuan Pembelian" },
  "cash-management":      { kicker: "Keuangan",       title: "Transaksi Kas" },
  "purchase-returns":     { kicker: "Pembelian",      title: "Retur Pembelian (Nota Debit)" },
  "vendor-bills":         { kicker: "Pembelian",      title: "Tagihan Supplier · 3-Way Matching" },
  "landed-cost":          { kicker: "Pembelian",      title: "Landed Cost · Alokasi HPP Roll" },
  "input-tax":            { kicker: "Keuangan \u00b7 Pajak", title: "Faktur Pajak Masukan · PPN Masukan & Rekap" },
  "rfq":                  { kicker: "Pembelian",      title: "RFQ / Penawaran · Tender & Banding Harga Supplier" },
  operations:             { kicker: "Gudang",         title: "Operasi Gudang (WMS)" },
  "qc-inspection":        { kicker: "Gudang",         title: "Inspeksi QC · Penerimaan" },
  "inventory-board":      { kicker: "Gudang",         title: "Status Stok & ATP" },
  "stock-buckets":        { kicker: "Gudang",         title: "Stok Multi-Kantong (WIP / Ditahan / Dalam Perjalanan)" },
  "interco-transfers":    { kicker: "Gudang",         title: "Transfer Antar-Entitas" },
  escalations:            { kicker: "Eskalasi",       title: "Eskalasi Barang Masuk & Barang Keluar" },
  documents:              { kicker: "Dokumen",        title: "Pusat Cetak & Label" },
  reports:                { kicker: "Analitik",       title: "Dasbor & Analitik" },
  costing:                { kicker: "Analitik (BI)",  title: "Margin & HPP (WAC)" },
  // Coming Soon views (cs-* yang benar-benar belum live)
  "cs-price-list":        { kicker: "Produk & Harga", title: "Harga per Pelanggan" },
  "cs-bom":               { kicker: "Pembelian",      title: "BOM Printing" },
  "cs-stock-analytics":   { kicker: "Gudang",         title: "Analitik Stok (Cepat/Lambat/Mati)" },
  "wms-locations":        { kicker: "Gudang",         title: "Lokasi Gudang & Penempatan Rak" },
  "production":           { kicker: "Gudang",         title: "Produksi In-House \u00b7 BOM & Work Order" },
  "scheduler":            { kicker: "Pengaturan",     title: "Penjadwal & Notifikasi \u00b7 Alert Otomatis" },
  "cs-rfid-lokasi":       { kicker: "RFID",           title: "Lokasi RFID" },
  "cs-rfid-tags":         { kicker: "RFID",           title: "Tags (tag↔item)" },
  "cs-rfid-devices":      { kicker: "RFID",           title: "Devices (Reader / Gate)" },
  "cs-rfid-gate":         { kicker: "RFID",           title: "Gate Monitor" },
  "chart-of-accounts":    { kicker: "Keuangan",       title: "Bagan Akun · Chart of Accounts" },
  "general-ledger":       { kicker: "Keuangan",       title: "Buku Besar · Jurnal Umum" },
  "financial-statements": { kicker: "Keuangan",       title: "Laporan Keuangan · Laba-Rugi, Neraca & Arus Kas" },
  "finance-tower":        { kicker: "Keuangan",       title: "Dashboard Keuangan · Control Tower" },
  "profitability":        { kicker: "Keuangan",       title: "Profitabilitas & Margin (WAC)" },
  "cashflow-forecast":    { kicker: "Keuangan",       title: "Proyeksi Arus Kas · Likuiditas" },
  "budget":               { kicker: "Keuangan",       title: "Anggaran vs Realisasi · Commitment Control" },
  "bank-accounts":        { kicker: "Keuangan",       title: "Kas & Bank · Rekening & Saldo" },
  // FASE G-8 — tanpa entri ini TopBar jatuh ke fallback "Workspace · Kain Nusantara"
  // sehingga pengguna kehilangan jejak posisinya (temuan penutupan fase).
  "bank-reconciliation":  { kicker: "Keuangan",       title: "Kas & Bank · Rekonsiliasi Bank Otomatis" },
  "finance-cases":        { kicker: "Keuangan",       title: "Pusat Kasus Keuangan" },
  // FASE G-7 — tanpa entri ini TopBar jatuh ke fallback "Workspace · Kain Nusantara"
  // sehingga pengguna kehilangan jejak posisinya (pelajaran penutupan G-8).
  "contra-bons":          { kicker: "Pembelian",      title: "Kontrabon \u00b7 Siklus Tukar Faktur Supplier" },
  // FASE G-6 — antar-PT sebagai jual-beli (bukan pindah gudang).
  "interco-transactions": { kicker: "Pembelian",      title: "Transaksi Antar Entitas \u00b7 Jual-Beli Antar-PT" },
  "settings-config":      { kicker: "Pengaturan",     title: "Pusat Pengaturan (Konfigurasi Berjalan)" },
  "entities-access":      { kicker: "Pengaturan",     title: "Badan Usaha & Akses \u00b7 Entitas, Akun, Kesiapan" },
  "cash-advances":        { kicker: "Kas & Petty Cash", title: "Pengajuan Dana (PD) · Cash Advance" },
  "settlements":          { kicker: "Kas & Petty Cash", title: "Pertanggungjawaban (LPJ) · Petty Cash" },
  "expense-categories":   { kicker: "Kas & Petty Cash", title: "Kategori Beban → Akun COA" },
  "vehicle-logs":         { kicker: "Aset & GA",      title: "Penggunaan & Biaya Kendaraan" },
  "fixed-assets":         { kicker: "Kas & Aset",     title: "Aset Tetap \u00b7 Penyusutan & Disposal" },
  "cs-pajak":             { kicker: "Keuangan \u00b7 Pajak", title: "PPh & Rekap Pajak" },
  "ar-aging":             { kicker: "Keuangan",       title: "AR / Piutang & Umur" },
  "advance-report":       { kicker: "Keuangan",       title: "Uang Muka Pelanggan" },
  "store-credit":         { kicker: "Keuangan",       title: "Store Credit / Saldo Pelanggan" },
  "consolidation":        { kicker: "Keuangan",       title: "Konsolidasi Grup · Eliminasi Intercompany" },
  "closing":              { kicker: "Keuangan",       title: "Tutup Buku · Closing Bulanan & Tahunan" },
  "period-unlock":        { kicker: "Keuangan · Kendali", title: "Buka Periode (Unlock) · Kontrol Ganda & Jendela Waktu" },
  "hr-employees":         { kicker: "SDM (HRD)",      title: "Karyawan" },
  "hr-org-units":         { kicker: "SDM (HRD)",      title: "Struktur Organisasi" },
  "hr-my-profile":        { kicker: "SDM (HRD)",      title: "Profil Saya (ESS)" },
  "logistics":            { kicker: "Logistik",       title: "Pengiriman & Pelacakan \u00b7 Ekspedisi, Armada Sendiri, Foto Muat & POD" },
  "hr-attendance":        { kicker: "SDM (HRD)",      title: "Presensi & Kehadiran" },
  "hr-attendance-setup":  { kicker: "SDM (HRD)",      title: "Shift & Geofence" },
  "hr-live-tracking":     { kicker: "SDM (HRD)",      title: "Lacak Lapangan · Live Tracking Sales" },
  "hr-visits":            { kicker: "Penjualan",      title: "Kunjungan Sales (Visit)" },
  "hr-payroll-runs":      { kicker: "SDM (HRD)",      title: "Penggajian (Payroll Run)" },
  "hr-payslips":          { kicker: "SDM (HRD)",      title: "Slip Gaji (Payslip)" },
  "hr-leave":             { kicker: "SDM (HRD)",      title: "Cuti & Izin" },
  "hr-overtime":          { kicker: "SDM (HRD)",      title: "Lembur (Overtime)" },
  "cs-kpi":               { kicker: "SDM (HRD)",      title: "KPI Karyawan (input manual per periode)" },
  "cs-design-gallery":    { kicker: "Desainer",       title: "Galeri Desain (Showcase)" },
  "cs-bi-sales":          { kicker: "Analitik (BI)",  title: "Dasbor Penjualan (Business Intelligence)" },
  "cs-bi-stock":          { kicker: "Analitik (BI)",  title: "Dasbor Stok (Business Intelligence)" },
  "bi-finance":           { kicker: "Analitik (BI)",  title: "BI Keuangan · Tren, Rasio & Perbandingan PT" },
  "cs-bi-hrd":            { kicker: "Analitik (BI)",  title: "Dasbor BI SDM" },
};

// ROLE-HOME REGISTRY (F5) — landing per role
export const ROLE_HOME_REGISTRY = {
  admin:     { view: "admin-home", navId: "home" },
  // EPIC 1 · PS-18 — manajer akhirnya punya landing sendiri (dulu mendarat di
  // layar "Laporan" generik sehingga harus berkeliling menu untuk tahu apa yang
  // perlu ditindak).
  manager:   { view: "manager-home", navId: "home" },
  warehouse: { view: "operations", navId: "wms-operations" },
  sales:     { view: "sales-home", navId: "home" },
  // FASE E-8 (E8.1) — dua peran baru. WAJIB sama dengan `backend/role_registry.py`
  // (POC E-8 memeriksa kesamaannya). GELOMBANG 2: keduanya kini mendarat di MEJA
  // KERJA-nya sendiri — antrean pekerjaan hari itu, bukan daftar dokumen generik.
  // Peran pelaksana yang mendarat di daftar harus menyaring sendiri untuk menemukan
  // apa yang perlu ditindak; meja kerja sudah menyusunnya.
  sales_admin: { view: "sales-admin-desk", navId: "sales-admin-desk" },
  finance:     { view: "finance-desk", navId: "finance-desk" },
  // FASE D — peran ke-7. WAJIB sama dengan `backend/role_registry.py` (diperiksa POC).
  // Desainer mendarat langsung di papan pekerjaannya, bukan di beranda generik.
  designer:    { view: "design-requests", navId: "designer-hub" },
  // FB-02 — sopir mendarat langsung di papan pengiriman.
  driver:      { view: "logistics", navId: "logistics" },
  // Sesi #087 — MD & Admin Gudang mendarat di mejanya.
  md:              { view: "md-desk", navId: "md-desk" },
  warehouse_admin: { view: "warehouse-admin-desk", navId: "warehouse-admin-desk" },
  // REVISI SAMPEL — Admin Sampel mendarat di mejanya.
  sample_admin:    { view: "sample-admin-desk", navId: "sample-admin-desk" },
};

// Smart guidance CTA.
export const GUIDANCE_MAP = {
  admin:                { label: "Audit",       target: "admin" },
  sales:                { label: "Cari Produk", target: "sales" },
  orders:               { label: "Review",      target: "orders" },
  purchasing:           { label: "Buat PO",     target: "purchasing" },
  operations:           { label: "WMS",         target: "operations" },
  "inventory-board":    { label: "Cek ATP",     target: "inventory-board" },
  "interco-transfers":  { label: "Setujui",     target: "interco-transfers" },
  escalations:          { label: "Resolve",     target: "escalations" },
  documents:            { label: "Cetak",       target: "documents" },
};
