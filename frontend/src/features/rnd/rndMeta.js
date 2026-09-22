/**
 * rndMeta (FASE F) — label & warna status R&D di SATU tempat supaya semua layar
 * memakai kosakata yang sama (tidak ada istilah teknis yang bocor ke pengguna).
 */
export const SPEC_STATUS_META = {
  draft: { label: "Draf", cls: "pill-muted" },
  review: { label: "Menunggu ACC", cls: "pill-warning" },
  approved: { label: "Disetujui", cls: "pill-success" },
  rejected: { label: "Ditolak", cls: "pill-danger" },
};

export const SAMPLE_STATUS_META = {
  draft: { label: "Draf", cls: "pill-muted" },
  sent: { label: "Terkirim ke supplier", cls: "pill-info" },
  in_progress: { label: "Dikerjakan", cls: "pill-warning" },
  assessed: { label: "Ada yang ACC", cls: "pill-success" },
  decided: { label: "Pemenang dipilih", cls: "pill-success" },
  cancelled: { label: "Dibatalkan", cls: "pill-danger" },
};

/** Urutan kolom papan Permintaan Sample — cermin alur `draft → sent → in_progress → assessed → decided`. */
export const SAMPLE_BOARD_ORDER = ["draft", "sent", "in_progress", "assessed", "decided"];

/** Tahapan stepper rincian sample (dibatalkan = cabang keluar). */
export const SAMPLE_STEPS = [
  { key: "draft", label: "Draf" },
  { key: "sent", label: "Terkirim" },
  { key: "in_progress", label: "Dikerjakan" },
  { key: "assessed", label: "Ada ACC" },
  { key: "decided", label: "Pemenang" },
];

/** Warna lencana per JENIS sampling — satu kosakata untuk kartu papan, tab, dan rincian. */
export const SAMPLE_TYPE_TONE = {
  labdip: { bg: "#EEF4FF", fg: "#0058CC" },
  handfeel: { bg: "#EAF7EF", fg: "#1A7A3A" },
  proofing: { bg: "#F1E9F7", fg: "#6B219A" },
};
export const typeTone = (code) => SAMPLE_TYPE_TONE[String(code || "").toLowerCase()]
  || { bg: "#F2F2F5", fg: "#6B6B73" };


export const LIFECYCLE_META = {
  konsep: { label: "Konsep", tone: "#8E8E93", sellable: false },
  labdip: { label: "Labdip", tone: "#0058CC", sellable: false },
  proofing: { label: "Proofing", tone: "#6B219A", sellable: false },
  disetujui: { label: "Disetujui (belum rilis)", tone: "#B26A00", sellable: false },
  produksi: { label: "Produksi (boleh dijual)", tone: "#1B7F4B", sellable: true },
  dihentikan: { label: "Dihentikan", tone: "#C0392B", sellable: false },
};

export const ROUND_RESULT_META = {
  "": { label: "Menunggu hasil", tone: "#8E8E93" },
  revisi: { label: "Revisi", tone: "#B26A00" },
  acc: { label: "ACC", tone: "#1B7F4B" },
  tolak: { label: "Ditolak", tone: "#C0392B" },
};

// FASE S — label CADANGAN saja. Sumber sebenarnya adalah master `sample_types`
// (dibaca lewat `/api/rnd/meta` → `features/rnd/sampleTypeMeta.js`). Peta ini
// dipertahankan supaya layar tetap terbaca sebelum meta termuat dan untuk dokumen
// lama; jenis yang DITAMBAH pemilik tidak perlu \u2014 dan tidak boleh \u2014 ditulis di sini.
export const SAMPLE_TYPE_LABEL = {
  labdip: "Labdip (kain polos)",
  handfeel: "Handfeel (rasa & konstruksi)",
  proofing: "Proofing (sample printing)",
  bulk_sample: "Bulk sample (dinonaktifkan)",
};

export const DESIGN_TYPE_LABEL = {
  motif: "Motif",
  pattern: "Pattern",
  artwork: "Artwork",
};

export const DESIGN_STATUS_META = {
  draft: { label: "Draf", cls: "pill-muted", tone: "#8E8E93" },
  pending_approval: { label: "Diajukan", cls: "pill-info", tone: "#0058CC" },
  in_review: { label: "Dalam Review", cls: "pill-warning", tone: "#A05000" },
  revision: { label: "Perlu Revisi", cls: "pill-danger", tone: "#C62828" },
  approved: { label: "ACC · Berkas Final", cls: "pill-success", tone: "#1A7A3A" },
  final_submitted: { label: "Final Diserahkan", cls: "pill-info", tone: "#0058CC" },
  active: { label: "Aktif / Produksi", cls: "pill-success", tone: "#0F6E4A" },
  archived: { label: "Diarsipkan", cls: "pill-muted", tone: "#6B6B73" },
  retired: { label: "Diarsipkan", cls: "pill-muted", tone: "#6B6B73" },
};

/** Urutan tahapan siklus hidup desain untuk stepper (revisi = cabang balik ke desainer). */
export const DESIGN_LIFECYCLE_STEPS = [
  { key: "draft", label: "Draf" },
  { key: "pending_approval", label: "Diajukan" },
  { key: "in_review", label: "Review" },
  { key: "approved", label: "ACC" },
  { key: "final_submitted", label: "Final (mockup + file asli)" },
  { key: "active", label: "Aktif" },
];

/** Label ronde: v1 = pengajuan awal, vN = revisi ke-(N-1). */
export const roundLabel = (version) => (Number(version || 1) <= 1 ? "Pengajuan awal" : `Revisi ${Number(version) - 1}`);

export const DESIGN_EVENT_LABEL = {
  created: "Desain dibuat", submit: "Diajukan untuk review", start_review: "Review dimulai",
  request_revision: "Diminta revisi (ronde baru dibuka)", approve: "Disetujui (ACC) + nilai akhir",
  submit_final: "Berkas final diserahkan", return_final: "Berkas final dikembalikan",
  activate: "Diaktifkan untuk produksi",
  archive: "Diarsipkan", reopen: "Dibuka kembali", new_version: "Versi baru",
  scored: "Diberi nilai", feedback: "Umpan balik", colorway_added: "Alternatif warna ditambah",
  colorway_updated: "Alternatif warna diubah", colorway_deleted: "Alternatif warna dihapus",
  artwork_uploaded: "Berkas desain diunggah", reference_uploaded: "Foto referensi diunggah",
  mockup_uploaded: "Mockup diunggah", colorway_uploaded: "Varian warna final diunggah", source_uploaded: "File desain asli diunggah",
  file_deleted: "Berkas dihapus", updated: "Data desain diubah",
  hold: "Desain di-HOLD", release_hold: "Hold dilepas",
  proofing_requested: "Masuk proofing R&D", proofing_finished: "Proofing selesai (sample jadi)",
  proofing_decided: "Proofing diputus (pemenang dipilih)",
  sample_requested: "Permintaan sample R&D dibuat", sample_finished: "Sample R&D jadi", sample_decided: "Sample R&D diputus",
  spec_linked: "Ditautkan ke spesifikasi", master_product_created: "Menjadi master produk",
  master_product_released: "Master produk dirilis ke produksi",
};

/** Kelompok riwayat untuk penyaring detail: satu kelompok = beberapa jenis peristiwa. */
export const DESIGN_HISTORY_GROUPS = [
  { key: "", label: "Semua" },
  { key: "lifecycle", label: "Status & keputusan", events: ["created", "submit", "start_review", "request_revision", "approve", "submit_final", "return_final", "activate", "archive", "reopen", "new_version", "scored"] },
  { key: "files", label: "Berkas", events: ["artwork_uploaded", "reference_uploaded", "mockup_uploaded", "colorway_uploaded", "source_uploaded", "file_deleted"] },
  { key: "edits", label: "Perubahan data", events: ["updated", "colorway_added", "colorway_updated", "colorway_deleted"] },
  { key: "hold", label: "Ditahan", events: ["hold", "release_hold"] },
  { key: "rnd", label: "Proofing & master produk", events: ["proofing_requested", "proofing_finished", "proofing_decided", "sample_requested", "sample_finished", "sample_decided", "spec_linked", "master_product_created", "master_product_released"] },
  { key: "feedback", label: "Umpan balik", events: ["feedback"] },
];

export const PROOFING_STATE_META = {
  none: { label: "Belum proofing", bg: "#F5F5F7", fg: "#6B6B73" },
  in_progress: { label: "Proofing berjalan", bg: "#F1E9F7", fg: "#6B219A" },
  finished: { label: "Proofing selesai", bg: "#EAF7EF", fg: "#1A7A3A" },
  master: { label: "Sudah jadi master produk", bg: "#E3F0FF", fg: "#0058CC" },
};

export const DESIGN_DATE_FIELDS = [
  { value: "approved_at", label: "Tanggal ACC" },
  { value: "updated_at", label: "Update terakhir" },
];

export const SCORE_STEPS = Array.from({ length: 9 }, (_, i) => i * 0.25);
export const fmtScore = (v) => (v === null || v === undefined || v === "" ? "—"
  : Number(v).toFixed(2).replace(".", ",").replace(/,?0+$/, "").replace(/,$/, "") || "0");

export const lifecycleMeta = (value) =>
  LIFECYCLE_META[(value || "produksi").toLowerCase()] || LIFECYCLE_META.produksi;

/** Ambil pesan galat backend yang sudah ramah pengguna (Bahasa Indonesia). */
export const errMsg = (e, fallback) => e?.response?.data?.detail || fallback;
