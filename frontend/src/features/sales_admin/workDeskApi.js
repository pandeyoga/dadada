/**
 * workDeskApi.js — FASE E-8 (E8.7/E8.13/E8.15/E8.20) · **MEJA KERJA** (Admin Sales & Finance).
 *
 * SATU tempat untuk panggilan API kedua meja + kamus tampilannya. Alasannya bukan
 * kerapian: dua meja membicarakan ANTREAN yang sama-sama berisi "pesanan", "retur",
 * "jatuh tempo". Kalau tiap layar menyalin label & warnanya sendiri, satu keadaan
 * (`pending_approval`) berakhir dengan dua kata berbeda di dua layar — dan pengguna
 * menyimpulkan ada dua hal berbeda.
 *
 * Pembagian meja mengikuti keputusan pemilik E8.10b#2: faktur pajak & uang masuk
 * ada di **Meja Finance**, alur pesanan & pemenuhan di **Meja Admin Sales**.
 */
import axios, { API } from "../../services/apiClient";
import {
  AlertTriangle, ArrowLeftRight, BadgeCheck, CalendarClock, CheckCircle2,
  ClipboardCheck, FileSignature, PackageSearch, Printer, RotateCcw, Scale,
  ShieldQuestion, Wallet,
} from "lucide-react";

// ─── PANGGILAN API ──────────────────────────────────────────────────────────
export const salesAdminDesk = (params = {}) =>
  axios.get(`${API}/sales-admin/desk`, { params }).then((r) => r.data);

export const financeDesk = (params = {}) =>
  axios.get(`${API}/finance/desk`, { params }).then((r) => r.data);

/** U-2 (2026-09) — Meja Saya: peran admin/manager/sales/warehouse/designer/driver. */
export const myDesk = (params = {}) =>
  axios.get(`${API}/desks/me`, { params }).then((r) => r.data);

/** Daftar periksa kelengkapan (read-only) — dibaca SEBELUM menekan Verifikasi. */
export const verificationPreview = (orderId) =>
  axios.get(`${API}/sales-orders/${orderId}/verification`).then((r) => r.data);

export const verifyOrder = (orderId, note = "") =>
  axios.post(`${API}/sales-orders/${orderId}/verify`, { note }).then((r) => r.data);

export const confirmOrder = (orderId) =>
  axios.post(`${API}/sales-orders/${orderId}/confirm`).then((r) => r.data);

export const fulfillmentOptions = (orderId) =>
  axios.get(`${API}/sales-admin/orders/${orderId}/fulfillment`).then((r) => r.data);

export const fulfillmentDecision = (orderId, payload) =>
  axios.post(`${API}/sales-admin/orders/${orderId}/fulfillment-decision`, payload)
    .then((r) => r.data);

/** US12 — perjalanan pesanan (read-only, tanpa akses layar gudang). */
export const orderJourney = (orderId) =>
  axios.get(`${API}/sales-orders/${orderId}/journey`).then((r) => r.data);

export const issueTaxInvoice = (orderId) =>
  axios.post(`${API}/sales-orders/${orderId}/tax-invoice`, {}).then((r) => r.data);

/** E8.3 — riwayat kunjungan MILIK SENDIRI + KPI ringkasnya (tanpa izin HR). */
export const myVisitsHistory = (month = "") =>
  axios.get(`${API}/hr/visits/mine`, { params: month ? { month } : {} }).then((r) => r.data);

// ─── KAMUS TAMPILAN ANTREAN ─────────────────────────────────────────────────
// `tone` dipakai untuk ikon & angka; `bg` untuk latar lencana ikon.
export const QUEUE_META = {
  perlu_verifikasi:    { icon: ClipboardCheck, tone: "#8A5300", bg: "rgba(255,149,0,.16)" },
  siap_dikonfirmasi:   { icon: CheckCircle2,   tone: "#1B7F4B", bg: "rgba(52,199,89,.16)" },
  menunggu_manajer:    { icon: ShieldQuestion, tone: "#6B219A", bg: "rgba(107,33,154,.12)" },
  siap_cetak_dokumen:  { icon: Printer,        tone: "#0058CC", bg: "rgba(0,122,255,.12)" },
  perlu_dipenuhi:      { icon: PackageSearch,  tone: "#B23B14", bg: "rgba(255,89,48,.14)" },
  jatuh_tempo:         { icon: CalendarClock,  tone: "#C0392B", bg: "rgba(255,59,48,.14)" },
  retur:               { icon: RotateCcw,      tone: "#8A5300", bg: "rgba(255,149,0,.16)" },
  permintaan_internal: { icon: ArrowLeftRight, tone: "#0058CC", bg: "rgba(0,122,255,.12)" },
  siap_faktur_pajak:   { icon: FileSignature,  tone: "#6B219A", bg: "rgba(107,33,154,.12)" },
  uang_masuk:          { icon: Wallet,         tone: "#1B7F4B", bg: "rgba(52,199,89,.16)" },
  selisih_bayar:       { icon: Scale,          tone: "#8A5300", bg: "rgba(255,149,0,.16)" },
  denda_draft:         { icon: AlertTriangle,  tone: "#C0392B", bg: "rgba(255,59,48,.14)" },
};

export const DEFAULT_QUEUE_META = {
  icon: BadgeCheck, tone: "#0058CC", bg: "rgba(0,122,255,.12)",
};

export const queueMeta = (id) => QUEUE_META[id] || DEFAULT_QUEUE_META;

// ─── LENCANA BARIS ──────────────────────────────────────────────────────────
// Kunci = status/penanda MENTAH dari server (huruf kecil). Nilai = kata yang
// dibaca pengguna. Tanpa kamus ini layar menuliskan `partially_shipped` mentah.
const BADGE_LABEL = {
  draft: "Draf",
  reserved: "Dipesan",
  waiting_approval: "Menunggu persetujuan",
  waiting_stock: "Menunggu stok",
  approved: "Disetujui",
  confirmed: "Dikonfirmasi",
  partially_picked: "Sebagian diambil",
  picked: "Sudah diambil",
  partially_shipped: "Sebagian dikirim",
  shipped: "Dikirim",
  dispatched: "Dikirim",
  done: "Selesai",
  cancelled: "Dibatalkan",
  menunggu: "Menunggu manajer",
  covered: "Barang masuk menutup",
  partial: "Tertutup sebagian",
  uncovered: "Belum ada penutup",
  lewat: "Lewat tempo",
  segera: "Segera jatuh tempo",
  pending_approval: "Menunggu persetujuan",
  pending_process: "Menunggu diproses",
  quarantine: "Karantina",
  submitted: "Diajukan",
  open: "Terbuka",
  pending: "Menunggu",
  // WMS / logistik / inspeksi
  picking: "Pengambilan", packing: "Pengepakan", packed: "Terkemas", loading: "Pemuatan",
  scheduled: "Terjadwal", prepared: "Disiapkan", loaded: "Dimuat", in_transit: "Dalam perjalanan",
  delivered: "Terkirim", failed: "Gagal", terkirim: "Terkirim", gagal: "Gagal", opname: "Opname",
  transfer: "Transfer", receiving: "Penerimaan", assigned: "Ditugaskan", in_progress: "Berjalan",
  kewajiban: "Kewajiban", "diakui (historis)": "Diakui (historis)",
};

const BADGE_TONE = {
  danger: "border-[#F5C9BC] bg-[#FDEDE7] text-[#C0392B]",
  warn: "border-[#F5D9A8] bg-[#FFF4E5] text-[#8A5300]",
  ok: "border-[#BFE6CE] bg-[#E6F6EC] text-[#1B7F4B]",
  info: "border-[#CBDFFF] bg-[#EAF2FF] text-[#0058CC]",
  mute: "border-[#E2E2E7] bg-[#F2F2F5] text-[#6E6E73]",
};

const BADGE_GROUP = {
  danger: ["lewat", "uncovered", "cancelled", "quarantine", "failed", "gagal", "diakui (historis)"],
  warn: ["segera", "partial", "menunggu", "waiting_approval", "waiting_stock",
         "pending_approval", "pending_process", "pending", "draft"],
  ok: ["approved", "confirmed", "picked", "shipped", "dispatched", "done", "covered", "delivered", "terkirim", "packed", "loaded"],
  info: ["reserved", "submitted", "open", "partially_picked", "partially_shipped", "picking", "packing", "loading",
         "scheduled", "prepared", "in_transit", "receiving", "assigned", "in_progress", "kewajiban"],
};

/** Kata Indonesia untuk penanda baris; tak dikenal → dirapikan, tidak dibuang. */
export function badgeLabel(badge) {
  if (!badge) return "";
  const key = String(badge).toLowerCase();
  return BADGE_LABEL[key] || String(badge).replace(/_/g, " ");
}

export function badgeClass(badge) {
  const key = String(badge || "").toLowerCase();
  const group = Object.keys(BADGE_GROUP).find((g) => BADGE_GROUP[g].includes(key));
  return BADGE_TONE[group || "mute"];
}

// ─── ISYARAT UMUR (SLA) ─────────────────────────────────────────────────────
// US15 menuntut "umur tertua" terbaca. Angka telanjang tidak menjelaskan apa pun —
// yang menolong adalah WARNA yang memberi tahu kapan sebuah baris mulai basi.
export function ageTone(days) {
  const d = Number(days || 0);
  if (d >= 7) return { cls: BADGE_TONE.danger, label: `${d} hari` };
  if (d >= 3) return { cls: BADGE_TONE.warn, label: `${d} hari` };
  if (d >= 1) return { cls: BADGE_TONE.info, label: `${d} hari` };
  return { cls: BADGE_TONE.mute, label: "hari ini" };
}

// ─── TUJUAN NAVIGASI SATU BARIS ─────────────────────────────────────────────
// Meja kerja bukan tempat mengerjakan SEGALA hal; ia tempat MENEMUKAN pekerjaan
// lalu melompat ke layar yang memang menanganinya. Peta ini membuat lompatan itu
// satu klik (memakai `openDocument` yang sudah ada: navigasi + auto-buka dokumen).
export const ROW_TARGET = {
  sales_order:      { view: "orders",            nav_id: "sales-orders",  focus_type: "sales_order" },
  purchase_order:   { view: "purchasing",        nav_id: "purchase-orders", focus_type: "purchase_order" },
  sales_return:     { view: "returns",           nav_id: "sales-orders",  focus_type: "sales_return" },
  internal_request: { view: "internal-requests", nav_id: "sales-orders",  focus_type: "internal_request" },
  customer:         { view: "customers-crm",     nav_id: "customers-crm", focus_type: "customer" },
  special_order:    { view: "special-orders",    nav_id: "special-orders", focus_type: "special_order" },
};

/** Antrean Finance menunjuk layar yang berbeda walau jenis dokumennya sama. */
export const FINANCE_QUEUE_TARGET = {
  siap_faktur_pajak: { view: "orders", nav_id: "sales-orders", focus_type: "sales_order" },
  uang_masuk:        { view: "customers-crm", nav_id: "customers-crm", focus_type: "customer" },
  selisih_bayar:     { view: "payment-plans", nav_id: "payment-plans", focus_type: "ar_receipt", tab: "selisih" },
  denda_draft:       { view: "payment-plans", nav_id: "payment-plans", focus_type: "penalty", tab: "denda" },
  // jatuh tempo → aging PER PELANGGAN: fokus ke pelanggannya (row.customer_id), bukan pesanannya
  jatuh_tempo:       { view: "ar-aging", nav_id: "ar-aging", focus_type: "customer", focus_key: "customer_id", number_key: "title" },
  hutang_jatuh_tempo: { view: "purchasing", nav_id: "purchase-orders", focus_type: "purchase_order" },
  uang_muka_belum_kirim: { view: "orders", nav_id: "sales-orders", focus_type: "sales_order" },
};

/** Sesi #087 — tujuan baris Meja MD & Meja Admin Gudang (per ref_type). */
export const ROLE_DESK_TARGET = {
  design_request:     { view: "design-requests",       nav_id: "designer-hub",   focus_type: "design_request" },
  sample_request:     { view: "orders",                nav_id: "sales-orders",   focus_type: "sales_order" },
  price_approval:     { view: "approvals",             nav_id: "approvals",      focus_type: "price_approval" },
  purchase_return:    { view: "purchase-returns",      nav_id: "purchase-returns", focus_type: "purchase_return" },
  md_sample:          { view: "rnd-samples",           nav_id: "rnd-hub",        focus_type: "md_sample" },
  purchase_requisition: { view: "purchase-requisitions", nav_id: "sourcing",     focus_type: "purchase_requisition" },
  inspection:         { view: "inspections",           nav_id: "wms-operations", focus_type: "inspection" },
  shipment:           { view: "logistics",             nav_id: "logistics",      focus_type: "shipment" },
  wms_task:           { view: "operations",            nav_id: "wms-operations", focus_type: "wms_task", tab: "outbound" },
  cycle_count:        { view: "operations",            nav_id: "wms-operations", focus_type: "cycle_count", tab: "cycle" },
  warehouse_transfer: { view: "operations",            nav_id: "wms-operations", focus_type: "warehouse_transfer", tab: "transfer" },
  logistics_delivery: { view: "logistics",             nav_id: "logistics",      focus_type: "logistics_delivery" },
};
export const mdDesk = (params) => axios.get(`${API}/md/desk`, { params }).then((r) => r.data);
export const warehouseAdminDesk = (params) => axios.get(`${API}/warehouse-admin/desk`, { params }).then((r) => r.data);

/** Meja Admin Gudang: PO dibuka langsung di Barang Masuk (tugas penerimaan terpilih), bukan di layar PO. */
const WH_DESK_TARGET = {
  purchase_order: { view: "operations", nav_id: "wms-operations", focus_type: "purchase_order", tab: "inbound" },
};

/** Tautan untuk ALAMAT DOKUMEN (?doc=NOMOR) — mencakup semua jenis di resolver backend. */
const DOC_TARGET = {
  ar_receipt:  { view: "payment-plans", nav_id: "payment-plans", focus_type: "ar_receipt", tab: "selisih" },
  tax_invoice: { view: "tax-invoices",  nav_id: "tax-hub",       focus_type: "tax_invoice" },
};
export function docLinkTarget(doc) {
  const t = DOC_TARGET[doc?.ref_type] || ROLE_DESK_TARGET[doc?.ref_type] || ROW_TARGET[doc?.ref_type];
  if (!t) return null;   // jenis belum punya layar — pemanggil menampilkan pesan, bukan melompat sembarangan
  const link = { view: t.view, nav_id: t.nav_id, focus_type: t.focus_type || doc.ref_type, focus_id: doc.ref_id, number: doc.number || "", tab: t.tab };
  if (doc.ref_type === "shipment" || doc.ref_type === "logistics_delivery") link.logistics = doc.ref_type === "shipment" ? { search: doc.number } : { deliveryId: doc.ref_id };
  return link;
}

export function rowLink(row, queueId = "", desk = "sales_admin") {
  if (desk === "md" || desk === "warehouse_admin") {
    const t = (desk === "warehouse_admin" && WH_DESK_TARGET[row?.ref_type])
      || ROLE_DESK_TARGET[row?.ref_type] || ROW_TARGET[row?.ref_type] || ROW_TARGET.sales_order;
    return { view: t.view, nav_id: t.nav_id, focus_type: t.focus_type, focus_id: row?.ref_id, number: row?.number, tab: t.tab };
  }
  const byQueue = desk === "finance" ? FINANCE_QUEUE_TARGET[queueId] : null;
  const base = byQueue || ROW_TARGET[row?.ref_type] || ROW_TARGET.sales_order;
  // `number` ikut dikirim supaya layar tujuan bisa MENYARING tabelnya ke baris ini —
  // pengguna tidak perlu mencari lagi setelah melompat dari meja.
  return {
    view: base.view,
    nav_id: base.nav_id,
    focus_type: base.focus_type || row?.ref_type || "",
    focus_id: (base.focus_key ? row?.[base.focus_key] : (row?.order_id || row?.ref_id)) || "",
    number: (base.number_key ? row?.[base.number_key] : row?.number) || "",
    tab: base.tab,
  };
}
