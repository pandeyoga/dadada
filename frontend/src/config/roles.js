/**
 * roles.js — FASE E-8 (E8.1) · **REGISTRY PERAN sisi layar** (cermin
 * `backend/role_registry.py`).
 */
import { ROLE_HOME_REGISTRY } from "./navMeta";

/*
 * KENAPA ADA: label peran, beranda peran, dan "siapa boleh melihat menu apa" dulu
 * tersebar sebagai literal `"manager"`/`"sales"` di ~81 tempat. Menambah dua peran
 * baru (`sales_admin`, `finance`) dengan cara lama berarti menyunting puluhan berkas
 * dan berharap tidak ada yang terlewat.
 *
 * SATU aturan penting soal MENU: `navStructure.js`/`hubTabs.js` TIDAK disentuh untuk
 * peran baru. Alasannya bukan kemalasan — daftar `roles:` di sana adalah niat desain
 * yang sudah diaudit; menambah dua nama ke ~40 baris membuat riwayat perubahan sulit
 * dibaca dan mudah salah. Sebagai gantinya peran baru dinyatakan EKSPLISIT di satu
 * tempat (di bawah): mewarisi menu peran lain, ditambah/dikurangi daftar yang jelas.
 * Dengan begitu "Admin Sales boleh lihat apa" bisa dibaca sekali pandang.
 */

export const ROLE_REGISTRY = {
  admin: {
    label: "Admin",
    longLabel: "Admin sistem",
    rank: 4,
    crossEntity: true,
    scopeHint: "lintas badan usaha",
    order: 1,
  },
  manager: {
    label: "Manajer",
    longLabel: "Manajer",
    rank: 3,
    crossEntity: true,
    scopeHint: "lintas badan usaha",
    order: 2,
  },
  sales_admin: {
    label: "Admin Sales",
    longLabel: "Admin Sales (alur pesanan)",
    rank: 2,
    crossEntity: false,
    scopeHint: "1 badan usaha (bisa ditugaskan ke beberapa)",
    order: 3,
    newIn: "E-8",
  },
  finance: {
    label: "Finance",
    longLabel: "Kasir / Finance",
    rank: 2,
    crossEntity: false,
    scopeHint: "1 badan usaha (bisa ditugaskan ke beberapa)",
    order: 4,
    newIn: "E-8",
  },
  sales: {
    label: "Sales",
    longLabel: "Sales (lapangan)",
    rank: 1,
    crossEntity: false,
    scopeHint: "1 badan usaha",
    order: 5,
  },
  warehouse: {
    label: "Gudang",
    longLabel: "Gudang (WMS)",
    rank: 1,
    crossEntity: false,
    scopeHint: "1 badan usaha",
    order: 6,
  },
  // FASE D — peran ke-7 (keputusan pemilik): desainer ber-AKUN supaya ia sendiri
  // yang mengunggah artwork & menyerahkannya, dan rapor desainer terisi dari
  // pekerjaan nyata. Cermin `backend/role_registry.py`.
  designer: {
    label: "Desainer",
    longLabel: "Desainer (MD Desain)",
    rank: 1,
    crossEntity: false,
    scopeHint: "1 badan usaha",
    order: 7,
    newIn: "D",
  },
  // FB-02 — peran ke-8: sopir/kurir armada sendiri (modul Logistik). Cermin `backend/role_registry.py`.
  driver: {
    label: "Sopir",
    longLabel: "Sopir / Kurir (Logistik)",
    rank: 1,
    crossEntity: false,
    scopeHint: "1 badan usaha",
    order: 8,
    newIn: "FB-2",
  },
  // Sesi #087 — dua peran pelaksana baru dengan MEJA KERJA sendiri. Cermin `backend/role_registry.py`.
  md: {
    label: "MD",
    longLabel: "MD / Merchandiser (produk, sample & desain)",
    rank: 2,
    crossEntity: false,
    scopeHint: "1 badan usaha (bisa ditugaskan ke beberapa)",
    order: 9,
    newIn: "R-9",
  },
  warehouse_admin: {
    label: "Admin Gudang",
    longLabel: "Admin Gudang (kepala operasi gudang & logistik)",
    rank: 2,
    crossEntity: false,
    scopeHint: "1 badan usaha (bisa ditugaskan ke beberapa)",
    order: 10,
    newIn: "R-9",
  },
  // REVISI SAMPEL — peran ke-11: Admin Sampel (pesanan sampel SOS-). Cermin `backend/role_registry.py`.
  sample_admin: {
    label: "Admin Sampel",
    longLabel: "Admin Sampel (alur pesanan sampel)",
    rank: 2,
    crossEntity: false,
    scopeHint: "1 badan usaha (bisa ditugaskan ke beberapa)",
    order: 11,
    newIn: "SMP",
  },
};

export const ROLE_IDS = Object.keys(ROLE_REGISTRY)
  .sort((a, b) => ROLE_REGISTRY[a].order - ROLE_REGISTRY[b].order);

export const CROSS_ENTITY_ROLES = ROLE_IDS.filter((r) => ROLE_REGISTRY[r].crossEntity);

export function roleLabel(role, long = false) {
  const e = ROLE_REGISTRY[role];
  if (!e) return role || "—";
  return long ? e.longLabel : e.label;
}

/** Peran (atau peran ACUAN untuk peran kustom) termasuk daftar? Pengganti `[..].includes(role)`. */
export function roleIs(role, list) {
  if (list.includes(role)) return true;
  const base = ROLE_REGISTRY[role]?.baseRole;
  return !!base && list.includes(base);
}

export function roleRank(role) {
  return ROLE_REGISTRY[role]?.rank || 0;
}

/** Apakah peran aktor memenuhi tuntutan peran sebuah aturan persetujuan? */
export function roleSatisfies(actorRole, requiredRole) {
  if (!requiredRole) return true;
  const need = ROLE_REGISTRY[requiredRole]?.rank ?? ROLE_REGISTRY.manager.rank;
  return roleRank(actorRole) >= need;
}

/** Pilihan peran untuk formulir akun (layar "Badan Usaha & Akses"). */
export const ROLE_OPTIONS = ROLE_IDS.map((id) => ({
  value: id,
  label: ROLE_REGISTRY[id].longLabel,
  scope: ROLE_REGISTRY[id].scopeHint,
  isNew: !!ROLE_REGISTRY[id].newIn,
}));

// ─── VISIBILITAS MENU UNTUK PERAN BARU ───────────────────────────────────────
// `inherit` : mulai dari menu peran ini (biar tidak menulis ulang puluhan id).
// `add`     : id menu / id grup / `view` tab hub yang DITAMBAHKAN.
// `remove`  : yang DICABUT walau ikut terwarisi (pemisahan tugas E8.2).
export const ROLE_NAV = {
  sales_admin: {
    // Admin Sales bekerja di wilayah yang sama dengan sales, plus wewenang
    // pemenuhan: mengajukan pembelian (PR) & mengurus transaksi antar-PT.
    inherit: "sales",
    add: [
      "sales-admin-desk",          // Meja Admin Sales (gelombang 2)
      // E8.3 — sales DICABUT dari "Operasi Gudang" (layar mati: `/api/wms/tasks` 403),
      // tetapi Admin Sales PUNYA izin `wms.view` untuk memantau progres tanpa aksi.
      // Tanpa baris ini ia ikut kehilangan menu itu karena mewarisi menu sales.
      "wms-operations",
      "pembelian", "sourcing", "purchase-requisitions",
      "interco-transactions",
      "return-policies",           // perlu membaca kebijakan retur saat memproses retur
      "document-center", "doc-trace",
      // AUDIT SALES vs ADMIN SALES (sesi 2026-08-15) — keputusan pemilik E8.1b memberi
      // peran ini `approval: ["view"]` ("melihat antrean, tanpa menyetujui"). Izin itu
      // dulu TANPA PINTU: tabnya hanya untuk admin/manager, jadi Admin Sales tak punya
      // cara melihat persetujuan yang nyangkut padahal mengejarnya adalah tugasnya.
      // Layar ini read-only (keputusan tetap di layar kaya konteks milik manajer).
      "approval-inbox",
    ],
    remove: [
      // "Hutang Supplier" (accounts-payable) DICABUT. Menunya dulu ada di sini,
      // tetapi `GET /vendor-bills` menuntut `vendor_bill.view` yang SENGAJA tidak
      // dimiliki peran ini (plan.md E8.1b: "sisi HUTANG tetap manager/admin —
      // jangan diperluas sendiri"). Hasilnya layar mati. Obat yang benar =
      // mencabut menunya, BUKAN melebarkan izinnya.
      "accounts-payable",
      // "Kunjungan Sales" DICABUT. `VisitsView` bercabang: peran `sales` melihat
      // kunjungan MILIKNYA (`/hr/visits/mine`), peran lain masuk ke Log Kunjungan
      // yang memanggil `/hr/visits` + `/hr/employees` (izin HR — bukan milik peran
      // ini). Karena menunya terwarisi dari `sales`, Admin Sales mendarat di layar
      // yang selalu 403. Kunjungan lapangan memang bukan wilayahnya.
      "hr-visits",
    ],
  },
  designer: {
    // Desainer TIDAK mewarisi siapa pun: wilayahnya sengaja sempit — papan
    // pekerjaannya sendiri + tempat karyanya. Menu lain (pesanan, stok, uang,
    // master) bukan urusannya, dan menampilkannya hanya melahirkan layar mati.
    inherit: null,
    add: [
      "design-requests",   // papan pekerjaan (beranda perannya)
      "designer-hub",      // hub tempat papan & galeri hidup
      "rnd-designs", "cs-design-gallery",
      "hr-my-profile",     // Profil Saya (ESS) — termasuk KPI desainer miliknya
    ],
    remove: [
      // Tab hub Desainer yang menilai ORANG (KPI lintas desainer) & matriks divisi
      // bukan wewenang yang dinilai — pola privasi yang sama dengan PS-18.
      "designer-kpi", "rnd-divisions",
    ],
  },
  // FB-02 — sopir hanya melihat modul Logistik + Profil Saya.
  driver: {
    inherit: null,
    add: ["logistics", "hr-my-profile"],
    remove: [],
  },
  finance: {
    // Finance TIDAK mewarisi siapa pun: wilayahnya sempit & spesifik supaya
    // "kasir" tidak diam-diam mendapat layar operasional/master.
    inherit: null,
    add: [
      "finance-desk",              // Meja Finance (gelombang 2) — beranda perannya
      "home", "hr-my-profile", "documents",
      "document-center", "doc-trace",
      // Penjualan: hanya MELIHAT pesanan & retur (untuk menagih & mencocokkan)
      "penjualan", "sales-orders", "orders", "returns",
      // REVISI SAMPEL — menyetujui pembayaran sampel berbayar dari daftar Pesanan Sampel
      "sample-orders",
      "customers-crm",
      // Keuangan: uang masuk, piutang, denda, kas, pajak keluaran
      "keuangan", "finance-tower", "ar-aging", "advance-report", "payment-plans", "finance-cases",
      "cash-bank", "cash-management",
      "tax-hub", "tax-invoices",
      "store-credit",
      // 2026-09 — hutang jatuh tempo (Meja Finance) → PO hanya-lihat
      "pembelian", "purchase-orders", "purchasing",
    ],
    remove: [],
  },
  // Sesi #087 — MD/Merchandiser: pengembangan produk. Tidak mewarisi siapa pun.
  md: {
    inherit: null,
    add: [
      "md-desk", "home", "hr-my-profile",
      // R&D & desain
      "rnd-hub", "rnd-specs", "rnd-samples", "rnd-labdip", "rnd-handfeel", "rnd-proofing", "rnd-reports",
      "designer-hub", "design-requests", "rnd-designs", "cs-design-gallery",
      // produk & harga
      "penjualan", "products-pricing", "md-products", "product-templates", "md-categories", "color-library", "md-uoms",
      "cs-price-list", "products-pricing", "sales-orders", "orders",
      // pembelian bahan (PR/RFQ hanya-lihat PO)
      "pembelian", "sourcing", "purchase-requisitions", "rfq", "purchase-orders", "purchasing", "master-pembelian", "suppliers",
      // pantau inspeksi (acuan sample)
      "gudang", "wms-operations", "inspections",
      // Persetujuan MD (desain/sample) diputus di Meja MD — Pusat Persetujuan lintas modul bukan haknya.
      "document-center", "doc-trace",
    ],
    remove: ["designer-kpi", "rnd-divisions", "operations", "qc-inspection", "interco-transfers"],
  },
  // Sesi #087 — Admin Gudang: semua menu gudang + logistik + persetujuan gudang.
  warehouse_admin: {
    inherit: "warehouse",
    add: [
      "warehouse-admin-desk", "home", "hr-my-profile",
      "logistics",
      // Persetujuan gudang (opname/transfer) diputus di Meja Admin Gudang — bukan Pusat Persetujuan lintas modul.
      "document-center", "doc-trace",
      "cs-stock-analytics",
    ],
    remove: [],
  },
  // REVISI SAMPEL — Admin Sampel: meja sampel + daftar pesanan sampel + pantau gudang/logistik. Tidak mewarisi siapa pun.
  sample_admin: {
    inherit: null,
    add: [
      "sample-admin-desk", "home", "hr-my-profile",
      "penjualan", "sales-orders", "sample-orders", "customers-crm",
      "gudang", "wms-operations", "logistics",
      "document-center", "doc-trace",
    ],
    remove: ["orders", "amendments", "returns", "return-policies", "special-orders", "internal-requests"],
  },
};

/**
 * SATU definisi "boleh lihat menu ini?" — dipakai `navigationConfig.js`
 * (sidebar, tab hub, command palette, deep-link) supaya keempatnya tidak
 * pernah berbeda pendapat.
 *
 * @param {string[]|undefined} roles daftar peran pada entri menu/tab
 * @param {string} role peran pengguna
 * @param {string} id id menu / groupId / view tab
 */
export function roleCanSee(roles, role, id, depth = 0) {
  const rule = ROLE_NAV[role];
  if (rule && id && rule.remove.includes(id)) return false;
  if (!Array.isArray(roles)) return true;      // tab tanpa `roles` = semua peran
  if (roles.includes(role)) return true;
  if (!rule) return false;
  if (id && rule.add.includes(id)) return true;
  // Peran kustom mewarisi peran acuannya (yang mungkin punya overlay sendiri).
  if (rule.inherit && depth < 3) return roleCanSee(roles, rule.inherit, id, depth + 1);
  return false;
}

// ─── PERAN KUSTOM (dibuat admin di "Peran & Hak Akses") ─────────────────────
// Server (`GET /api/roles`) adalah sumbernya; di sini registry, overlay menu, dan
// beranda peran diisi SAAT RUNTIME supaya seluruh navigasi memakai satu jawaban.
const CUSTOM_IDS = new Set();

function rebuildDerived() {
  const ids = Object.keys(ROLE_REGISTRY).sort((a, b) => ROLE_REGISTRY[a].order - ROLE_REGISTRY[b].order);
  ROLE_IDS.splice(0, ROLE_IDS.length, ...ids);
  ROLE_OPTIONS.splice(0, ROLE_OPTIONS.length, ...ids.map((id) => ({
    value: id,
    label: ROLE_REGISTRY[id].longLabel,
    scope: ROLE_REGISTRY[id].scopeHint,
    isNew: !!ROLE_REGISTRY[id].newIn,
    custom: !!ROLE_REGISTRY[id].custom,
  })));
}

/** Daftarkan peran kustom dari server. Mengembalikan true bila ada yang berubah. */
export function registerDynamicRoles(list) {
  const incoming = (list || []).filter((r) => r && r.custom && r.id);
  const before = JSON.stringify([...CUSTOM_IDS].sort().map((id) => [id, ROLE_NAV[id], ROLE_REGISTRY[id]?.label]));
  for (const id of [...CUSTOM_IDS]) {
    delete ROLE_REGISTRY[id]; delete ROLE_NAV[id]; delete ROLE_HOME_REGISTRY[id];
  }
  CUSTOM_IDS.clear();
  incoming.forEach((r, i) => {
    CUSTOM_IDS.add(r.id);
    ROLE_REGISTRY[r.id] = {
      label: r.label, longLabel: r.long_label || r.label, rank: r.rank || 1,
      crossEntity: false, scopeHint: r.scope_hint || "1 badan usaha", order: 100 + i,
      custom: true, baseRole: r.base_role || "",
    };
    ROLE_NAV[r.id] = { inherit: r.base_role || null, add: r.nav?.add || [], remove: r.nav?.remove || [] };
    ROLE_HOME_REGISTRY[r.id] = ROLE_HOME_REGISTRY[r.base_role]
      || { view: "hr-my-profile", navId: "hr-my-profile" };
  });
  rebuildDerived();
  const after = JSON.stringify([...CUSTOM_IDS].sort().map((id) => [id, ROLE_NAV[id], ROLE_REGISTRY[id]?.label]));
  return before !== after;
}

/** Overlay sementara untuk PRATINJAU menu di editor peran (id `__preview`). */
export function setPreviewRoleNav(rule) {
  if (rule) ROLE_NAV.__preview = rule; else delete ROLE_NAV.__preview;
}

/** Izin efektif pengguna (dikirim server saat login) → `can(perms, "interco", "create")`. */
export function can(perms, module, action) {
  const actions = (perms || {})[module] || [];
  return actions.includes(action) || actions.includes("*");
}
