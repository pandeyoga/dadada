// X-1 / X-2 (audit 2026-09-02) — label Indonesia untuk kunci mentah modul izin & aksi audit.
// Kunci yang belum terpetakan jatuh ke pemformatan generik (snake_case → "Kata Kata").

export const MODULE_LABEL = {
  product: "Produk", customer: "Pelanggan", warehouse: "Gudang", uom: "Satuan (UOM)", template: "Template Dokumen",
  order: "Pesanan Penjualan", sales: "Penjualan", sales_admin: "Meja Admin Sales", invoice: "Invoice",
  ar_receipt: "Penerimaan AR", payment_plan: "Rencana Pembayaran", penalty: "Denda", tax: "Pajak", tax_invoice: "Faktur Pajak",
  input_tax: "PPN Masukan", document: "Dokumen", document_delivery: "Pengiriman Dokumen", pdf_template: "Template PDF",
  inventory: "Persediaan", wms: "WMS / Gudang", cycle_count: "Stock Opname", transfer: "Transfer Antar Gudang",
  logistics: "Logistik / Pengiriman", vehicle_log: "Log Kendaraan", label: "Label RFID", inspection: "Inspeksi QC",
  purchase_order: "Purchase Order", purchase_requisition: "Permintaan Pembelian", purchase_return: "Retur Pembelian",
  rfq: "RFQ / Penawaran", supplier: "Supplier", supplier_contract: "Kontrak Supplier", supplier_item: "Item Supplier",
  vendor_bill: "Tagihan Supplier", contra_bon: "Kontrabon", landed_cost: "Landed Cost", makloon: "Makloon", makloon_order: "Order Makloon",
  process_recipe: "Resep Proses", production: "Produksi", rnd: "R&D", design_request: "Permintaan Desain", designer: "Desainer",
  color: "Warna / Labdip", sales_return: "Retur Penjualan", internal_request: "Permintaan Internal", cash: "Kas",
  cash_advance: "Kasbon", cash_settlement: "Pertanggungjawaban Kasbon", finance: "Keuangan", finance_case: "Kasus Keuangan",
  finance_amendment: "Amandemen Keuangan", accounting: "Akuntansi / GL", period: "Periode Akuntansi", budget: "Anggaran",
  fixed_asset: "Aset Tetap", interco: "Antar-Badan Usaha", interco_finance: "Keuangan Antar-BU", entity: "Badan Usaha",
  price_approval: "Persetujuan Harga", pricelist: "Daftar Harga", approval: "Persetujuan", permission: "Matriks Izin",
  user: "Pengguna", settings: "Pengaturan", scheduler: "Penjadwal", audit: "Audit", reports: "Laporan", report: "Laporan",
  hr: "SDM (HRD)", esign: "Tanda Tangan Elektronik", pegging: "Alokasi Stok", driver: "Sopir",
};

export const ACTION_LABEL = {
  view: "Lihat", create: "Buat", update: "Ubah", delete: "Hapus", import: "Impor", export: "Ekspor", print: "Cetak",
  approve: "Setujui", reject: "Tolak", verify: "Verifikasi", confirm: "Konfirmasi", cancel: "Batalkan", void: "Batalkan (void)",
  manage: "Kelola", configure: "Konfigurasi", submit: "Ajukan", complete: "Selesaikan", assign: "Tugaskan", dispatch: "Dispatch",
  ship: "Kirim", deliver: "Serahkan", receive: "Terima", scan: "Scan", adjust: "Penyesuaian", pay: "Bayar", settle: "Lunasi",
  disburse: "Cairkan", claim: "Klaim", claim_approve: "Setujui Klaim", waive: "Bebaskan", backdate: "Tanggal Mundur",
  release: "Lepaskan", reopen: "Buka Kembali", unlock: "Buka Kunci", sign: "Tandatangani", send: "Kirim", run: "Jalankan",
  generate: "Hasilkan", issue: "Terbitkan", inspect: "Inspeksi", assess: "Nilai", award: "Tetapkan Pemenang", decide: "Putuskan",
  propose: "Usulkan", resolve: "Selesaikan Kasus", return: "Retur", replace: "Ganti", convert: "Konversi", dispose: "Hapus Buku",
  manage_bom: "Kelola BOM", manage_org: "Kelola Organisasi", manage_attendance: "Kelola Absensi", manage_payroll: "Kelola Gaji",
  manage_settings: "Kelola Pengaturan", view_pii: "Lihat Data Pribadi", approve_count: "Setujui Opname",
};

// Aksi audit (audit_logs.action). Awalan modul dipakai untuk kunci yang belum terdaftar.
export const AUDIT_ACTION_LABEL = {
  login: "Masuk (login)", logout: "Keluar", CREATE: "Dibuat", APPROVE: "Disetujui", COMPLETE: "Diselesaikan",
  ESCALATE: "Dieskalasi", RESOLVE_ESCALATION: "Eskalasi diselesaikan",
  order_created: "Pesanan dibuat", order_verified: "Pesanan diverifikasi", order_confirmed: "Pesanan dikonfirmasi",
  order_auto_approved: "Pesanan disetujui otomatis", sales_order_verified: "Pesanan diverifikasi",
  outbound_tasks_auto_created: "Tugas outbound dibuat otomatis", backorder_auto_fulfilled: "Backorder terpenuhi otomatis",
  inbound_scan_receive: "Scan penerimaan barang", inbound_completed: "Penerimaan selesai", restock_requested: "Permintaan restock",
  roll_grade_changed: "Grade roll diubah", qc_decision: "Keputusan QC",
  po_created: "PO dibuat", vendor_bill_created: "Tagihan supplier dibuat", vendor_bill_posted: "Tagihan supplier diposting",
  vendor_bill_payment: "Pembayaran tagihan supplier", supplier_contract_created: "Kontrak supplier dibuat",
  supplier_invoice_exchange_set: "Tukar faktur ditetapkan", purchase_return_created: "Retur pembelian dibuat",
  contra_bon_created: "Kontrabon dibuat", contra_bon_submitted: "Kontrabon diajukan", contra_bon_verified: "Kontrabon diverifikasi",
  contra_bon_approved: "Kontrabon disetujui", contra_bon_scheduled: "Kontrabon dijadwalkan", contra_bon_paid: "Kontrabon dibayar",
  contra_bon_deduction_added: "Potongan kontrabon ditambah",
  sales_return_created: "Retur penjualan dibuat", sales_return_approved: "Retur penjualan disetujui",
  sales_return_inspect_started: "Inspeksi retur dimulai", sales_return_inspected: "Retur diinspeksi",
  sales_return_quarantine_released: "Karantina retur dilepas", sales_return_settled: "Retur penjualan diselesaikan",
  interco_transaction_created: "Transaksi antar-BU dibuat", interco_transaction_invoiced: "Transaksi antar-BU ditagihkan",
  interco_return_created: "Retur antar-BU dibuat", interco_return_approved: "Retur antar-BU disetujui",
  interco_return_task_created: "Tugas retur antar-BU dibuat", interco_warehouse_task_created: "Tugas gudang antar-BU dibuat",
  inter_company_transfer_executed: "Transfer antar-BU dijalankan",
  internal_request_created: "Permintaan internal dibuat", internal_request_converted: "Permintaan internal dikonversi",
  logistics_create: "Pengiriman dibuat", logistics_update: "Pengiriman diubah", logistics_status: "Status pengiriman diubah",
  logistics_photo: "Foto pengiriman diunggah", logistics_photo_delete: "Foto pengiriman dihapus", logistics_position: "Posisi pengiriman dicatat",
  logistics_position_delete: "Posisi pengiriman dihapus", logistics_route: "Urutan rute sopir disusun",
  design_gallery_ai_illustrate: "Ilustrasi AI galeri dibuat", design_gallery_ai_comment: "Komentar ilustrasi AI",
  design_gallery_ai_comment_delete: "Komentar ilustrasi AI dihapus", design_gallery_autotag: "Auto-tag AI galeri",
  integrations_update: "Integrasi AI diubah", integrations_gemini_test: "Uji koneksi Gemini",
  document_generated: "Dokumen dihasilkan", journal_entry_created: "Jurnal dibuat", gl_posted: "Diposting ke GL",
};

const humanize = (key) => String(key || "").replace(/[_-]+/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

export const moduleLabel = (key) => MODULE_LABEL[key] || humanize(key);
export const actionLabel = (key) => ACTION_LABEL[key] || humanize(key);
export const auditActionLabel = (key) => AUDIT_ACTION_LABEL[key] || humanize(key);
