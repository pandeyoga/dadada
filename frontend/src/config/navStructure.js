// ─── NAV STRUCTURE DATA (hub-and-tab IA) + HUB TABS ──────────────────────────
// Dipisah dari navigationConfig.js agar file config di bawah batas guardrail.
import {
  AlertTriangle,
  Megaphone,
  Sparkles,
  Scissors,
  BarChart3,
  Bell,
  Boxes,
  Briefcase,
  Calculator,
  CalendarClock,
  CalendarX,
  Truck,
  Clock,
  CreditCard,
  Cpu,
  DollarSign,
  FileText,
  FileStack,
  FileBarChart,
  Home,
  IdCard,
  Landmark,
  Layers3,
  MapPin,
  Palette,
  Percent,
  PieChart,
  Printer,
  Receipt,
  Settings,
  ShoppingBag,
  ShoppingCart,
  Tag,
  Target,
  TrendingUp,
  TrendingDown,
  UserCheck,
  Users,
  Warehouse,
  Wifi,
  ClipboardList,
  Factory,
  FlaskConical,
  Wallet,
  Car,
  ReceiptText,
  FolderTree,
  Unlock,
  BellRing,
} from "lucide-react";

// HUB TABS (tab per hub) dipindah ke `hubTabs.js` — re-export agar impor lama tetap jalan.
export { HUB_TABS } from "./hubTabs";

// ─── NAV STRUCTURE (IA v2 — hub-and-tab, 7±2 per grup, urutan = alur proses) ──
export const NAV_STRUCTURE = [

  // ── BERANDA ──────────────────────────────────────────────────────────────────
  {
    type: "standalone",
    id:    "home",
    label: "Beranda",
    icon:  Home,
    roles: ["admin", "sales", "manager", "warehouse"],
    view:  null,  // App.js resolve via defaultViewForRole
  },

  // ── PUSAT PERSETUJUAN (satu pintu semua approval) ────────────────────────────
  {
    type: "standalone",
    id:    "approval-inbox",
    label: "Pusat Persetujuan",
    icon:  Bell,
    roles: ["manager", "admin", "sales"],
    hub:   "approval-inbox",
  },

  // ── MEJA KERJA PERAN (FASE E-8 · E8.7/E8.20) ────────────────────────────────
  // Dua peran baru bekerja dari ANTREAN, bukan dari daftar dokumen. Karena itu
  // mejanya berada di puncak menu (setara "Pusat Persetujuan" milik manajer),
  // bukan terkubur di dalam grup: ia layar pertama yang dibuka tiap pagi.
  // `roles: ["admin"]` saja — dua peran baru mendapatkannya lewat overlay
  // `ROLE_NAV` di `config/roles.js` (lihat alasannya di berkas itu).
  // U-2 (2026-09) — Meja Saya untuk admin, manager, sales, warehouse, designer, driver.
  {
    type: "standalone",
    id:    "my-desk",
    label: "Meja Saya",
    icon:  BellRing,
    roles: ["admin", "manager", "sales", "warehouse", "designer", "driver"],
    view:  "my-desk",
  },
  {
    type: "standalone",
    id:    "sales-admin-desk",
    label: "Meja Admin Sales",
    icon:  ClipboardList,
    roles: ["admin"],
    view:  "sales-admin-desk",
  },
  {
    type: "standalone",
    id:    "finance-desk",
    label: "Meja Finance",
    icon:  Landmark,
    roles: ["admin"],
    view:  "finance-desk",
  },
  // Sesi #087 — meja MD & Admin Gudang (peran barunya lewat ROLE_NAV, pola yang sama).
  {
    type: "standalone",
    id:    "md-desk",
    label: "Meja MD",
    icon:  Palette,
    roles: ["admin"],
    view:  "md-desk",
  },
  {
    type: "standalone",
    id:    "warehouse-admin-desk",
    label: "Meja Gudang",
    icon:  Warehouse,
    roles: ["admin"],
    view:  "warehouse-admin-desk",
  },
  // REVISI SAMPEL — Meja Admin Sampel (peran `sample_admin` lewat ROLE_NAV).
  {
    type: "standalone",
    id:    "sample-admin-desk",
    label: "Meja Sampel",
    icon:  Scissors,
    roles: ["admin"],
    view:  "sample-admin-desk",
  },

  // ── PENJUALAN ────────────────────────────────────────────────────────────────
  {
    type:    "group",
    groupId: "penjualan",
    label:   "Penjualan",
    icon:    ShoppingCart,
    roles:   ["admin", "sales", "manager"],
    items: [
      { id: "sales",            label: "Kasir & Portal", icon: ShoppingBag, roles: ["admin", "sales"] },
      // SPECIAL ORDER — permintaan produk custom pelanggan (referensi/pattern/warna/handfeel) → routing ke Desainer & R&D.
      { id: "special-orders",   label: "Pesanan Khusus", icon: Sparkles, roles: ["admin", "sales", "manager", "sales_admin"], view: "special-orders" },
      { id: "sales-orders",     label: "Pesanan",    icon: FileText,    roles: ["admin", "sales", "manager"], hub: "sales-orders" },
      // REVISI SAMPEL — daftar pesanan sampel TERPISAH dari SO biasa (klien: "jangan digabung").
      { id: "sample-orders",    label: "Pesanan Sampel", icon: Scissors, roles: ["admin", "sales", "manager"], view: "sample-orders" },
      { id: "customers-crm",    label: "Pelanggan",    icon: Users,       roles: ["admin", "sales", "manager"], hub: "customers-crm" },
      // Sales hanya melihat tab "Harga per Pelanggan" di hub ini (tab lain admin/manager).
      { id: "products-pricing", label: "Produk & Harga",     icon: Layers3,     roles: ["admin", "manager", "sales"], hub: "products-pricing" },
    ],
  },

  // ── PEMBELIAN ────────────────────────────────────────────────────────────────
  {
    type:    "group",
    groupId: "pembelian",
    label:   "Pembelian",
    icon:    ClipboardList,
    roles:   ["admin", "manager", "warehouse", "finance"],
    items: [
      { id: "sourcing",         label: "Pengadaan",    icon: Target,        roles: ["admin", "manager", "warehouse"], hub: "sourcing" },
      { id: "purchase-orders",  label: "Pesanan Pembelian",  icon: ClipboardList, roles: ["admin", "manager", "finance"],   hub: "purchase-orders" },
      { id: "accounts-payable", label: "Hutang Pemasok",    icon: Receipt,       roles: ["admin", "manager", "warehouse"], hub: "accounts-payable" },
      { id: "master-pembelian", label: "Master Pembelian",        icon: Factory,       roles: ["admin", "manager"],              hub: "master-pembelian" },
      { id: "cs-bom",           label: "Bahan Cetak",            icon: Printer,       roles: ["admin"], comingSoon: true },
    ],
  },

  // ── R&D (FASE F) — hulu rantai: spesifikasi → labdip/proofing → kontrak harga.
  // Menu ini SENGAJA hanya berisi PROSES R&D. Urusan ORANG & KARYA desain dipisah
  // ke menu "Desainer" di bawah (keputusan pemilik PS-18: jangan digabung).
  {
    type:  "standalone",
    id:    "rnd-hub",
    label: "Riset & Sampel",
    icon:  FlaskConical,
    roles: ["admin", "manager", "sales", "warehouse"],
    hub:   "rnd-hub",
  },

  // ── DESAINER (PS-18) — menu TERPISAH dari R&D: KPI desainer, master desain
  // & galeri artwork. Sebelumnya tersebar di hub R&D dan hub SDM sehingga
  // pemilik harus berpindah dua menu untuk menilai satu orang.
  {
    type:  "standalone",
    id:    "designer-hub",
    label: "Desainer",
    icon:  Palette,
    // FASE D — peran `designer` (ke-7) masuk di sini: hub ini memuat papan
    // Permintaan Desain (pintu kerjanya) + Galeri Desain (tempat karyanya).
    roles: ["admin", "manager", "designer"],
    hub:   "designer-hub",
  },

  // ── MARKETING ─────────────────────────────────────────────────────────────────
  {
    type:  "standalone",
    id:    "marketing-hub",
    label: "Marketing & Sosmed",
    icon:  Megaphone,
    roles: ["admin", "manager", "designer", "sales", "sales_admin"],
    hub:   "marketing-hub",
  },

  // ── GUDANG ───────────────────────────────────────────────────────────────────
  {
    type:    "group",
    groupId: "gudang",
    label:   "Gudang & Logistik",
    icon:    Warehouse,
    roles:   ["admin", "warehouse", "manager", "sales", "driver", "sales_admin", "warehouse_admin", "md"],
    items: [
      // FASE E-8 (E8.3 · SD3) — `sales` DICABUT dari menu ini. Bukan pengetatan
      // baru: `/api/wms/tasks` memang sudah 403 untuk sales, jadi menunya adalah
      // LAYAR MATI — pengguna mengeklik, layar menolak, dan ia menyalahkan dirinya
      // sendiri. Gantinya sales mendapat "Perjalanan Pesanan" (E8.14) yang memuat
      // progres gudang TANPA membuka layar gudang. `sales_admin` tetap melihatnya
      // (izin `wms.view` — memantau, tanpa aksi) lewat overlay ROLE_NAV.
      { id: "wms-operations",     label: "Operasi Gudang", icon: Warehouse, roles: ["admin", "warehouse", "manager"], hub: "wms-operations" },
      { id: "stock-atp",          label: "Stok & ATP",           icon: Boxes,     roles: ["admin", "warehouse", "manager", "sales"], hub: "stock-atp" },
      { id: "production",         label: "Produksi",  icon: Factory,   roles: ["admin", "manager", "warehouse"] },
      { id: "wms-locations",      label: "Lokasi Rak",     icon: MapPin,    roles: ["admin", "warehouse", "manager"] },
      { id: "md-warehouses",      label: "Data Gudang",      icon: Warehouse, roles: ["admin", "warehouse", "manager"] },
      { id: "cs-stock-analytics", label: "Analitik Stok",      icon: TrendingUp, roles: ["admin", "manager"] },
      // Pengiriman (ekspedisi / armada sendiri, foto muat & POD). Sopir hanya melihat item ini.
      { id: "logistics",          label: "Pengiriman", icon: Truck, roles: ["admin", "manager", "warehouse", "driver", "sales", "sales_admin", "warehouse_admin"], view: "logistics" },
    ],
  },

  // ── RFID & TRACEABILITY (Fase 5 — SIMULATOR, LIVE) ──────────────────────────
  {
    type:    "group",
    groupId: "rfid",
    label:   "RFID",
    icon:    Cpu,
    roles:   ["admin", "warehouse"],
    items: [
      { id: "cs-rfid-lokasi",  label: "Lokasi RFID",           icon: MapPin, roles: ["admin", "warehouse"] },
      { id: "cs-rfid-tags",    label: "Tag RFID",       icon: Tag,    roles: ["admin", "warehouse"] },
      { id: "cs-rfid-devices", label: "Perangkat", icon: Wifi,   roles: ["admin"] },
      { id: "cs-rfid-gate",    label: "Monitor Gerbang",          icon: Cpu,    roles: ["admin", "warehouse"] },
    ],
  },

  // ── KEUANGAN (menyerap Kas dari Pembelian + Pajak 3-pintu jadi 1) ────────────
  {
    type:    "group",
    groupId: "keuangan",
    label:   "Keuangan",
    icon:    DollarSign,
    roles:   ["admin", "manager"],
    items: [
      { id: "finance-tower", label: "Dasbor Keuangan",     icon: PieChart,     roles: ["admin", "manager"] },
      { id: "cash-bank",   label: "Kas & Bank",            icon: CreditCard,   roles: ["admin", "manager"], hub: "cash-bank" },
      { id: "ar-aging",    label: "Piutang",  icon: TrendingDown, roles: ["admin", "manager"] },
      // KEB-PDPT (S#090) — saldo 2-1400 per pelanggan: uang muka pesanan belum dikirim + deposit.
      { id: "advance-report", label: "Uang Muka Pelanggan", icon: Wallet,      roles: ["admin", "manager"] },
      { id: "payment-plans", label: "Rencana Bayar", icon: CalendarClock, roles: ["admin", "manager"] },
      // FASE G-9 — antrean uang yang nyangkut. Sales ikut dilibatkan: mereka yang paling
      // sering menerima kabar "sudah transfer kok" dari pelanggan, jadi boleh MELAPOR &
      // memantau (izin finance_case: view+create), tetapi tidak menutup kasus uang.
      { id: "finance-cases", label: "Kasus Keuangan", icon: Briefcase, roles: ["admin", "manager", "sales"] },
      { id: "store-credit", label: "Saldo Kredit", icon: Wallet,      roles: ["admin", "manager"] },
      { id: "tax-hub",     label: "Pajak",     icon: Percent,      roles: ["admin", "manager"], hub: "tax-hub" },
      { id: "ledger",      label: "Buku Besar",      icon: FileStack,    roles: ["admin", "manager"], hub: "ledger" },
      { id: "fin-reports", label: "Laporan",    icon: FileBarChart, roles: ["admin", "manager"], hub: "fin-reports" },
      { id: "closing",     label: "Tutup Buku",  icon: CalendarX,    roles: ["admin", "manager"] },
      { id: "period-unlock", label: "Buka Periode", icon: Unlock,     roles: ["admin", "manager"] },
    ],
  },

  // ── KAS & ASET (Digitalisasi Formulir Sukacita — PD/LPJ/Kendaraan) ───────────
  {
    type:    "group",
    groupId: "kas-aset",
    label:   "Kas & Aset",
    icon:    Wallet,
    roles:   ["admin", "manager", "sales", "warehouse"],
    items: [
      { id: "petty-cash",   label: "Kas Kecil",  icon: Wallet, roles: ["admin", "manager", "sales"],              hub: "petty-cash" },
      { id: "vehicle-logs", label: "Kendaraan",        icon: Car,    roles: ["admin", "manager", "warehouse", "sales"], view: "vehicle-logs" },
      { id: "fixed-assets", label: "Aset Tetap",       icon: Boxes,  roles: ["admin", "manager"],                       view: "fixed-assets" },
    ],
  },

  // ── SDM (HRD) ────────────────────────────────────────────────────────────────
  {
    type:    "group",
    groupId: "hrd",
    label:   "SDM",
    icon:    Users,
    roles:   ["admin", "manager"],
    items: [
      { id: "hr-people",         label: "Karyawan", icon: UserCheck,  roles: ["admin", "manager"], hub: "hr-people" },
      { id: "hr-attendance-hub", label: "Kehadiran",      icon: Clock,      roles: ["admin", "manager"], hub: "hr-attendance-hub" },
      { id: "hr-payroll-hub",    label: "Penggajian",               icon: Calculator, roles: ["admin", "manager"], hub: "hr-payroll-hub" },
      { id: "hr-kpi-hub",        label: "KPI",          icon: Target,     roles: ["admin", "manager"], hub: "hr-kpi-hub" },
    ],
  },

  // ── ANALITIK (satu hub) ──────────────────────────────────────────────────────
  {
    type:  "standalone",
    id:    "analytics",
    label: "Analitik",
    icon:  BarChart3,
    roles: ["admin", "manager"],
    hub:   "analytics",
  },
  { type: "standalone", id: "cs-bi-sales", label: "Analitik Penjualan", icon: TrendingUp, roles: ["admin", "manager"], comingSoon: true },
  { type: "standalone", id: "cs-bi-stock", label: "Dasbor Stok",  icon: PieChart,   roles: ["admin", "manager"], comingSoon: true },

  // ── UTILITAS & PENGATURAN ────────────────────────────────────────────────────
  {
    type:  "standalone",
    id:    "document-center",
    label: "Pusat Dokumen",
    icon:  FileStack,
    roles: ["admin", "sales", "manager", "warehouse"],
    // FASE G-4 — hub: tab "Daftar Dokumen" + "Jejak Dokumen" (lihat HUB_TABS).
    hub:   "document-center",
    view:  "document-center",
  },
  {
    type:  "standalone",
    id:    "documents",
    label: "Pusat Cetak",
    icon:  Printer,
    roles: ["admin", "sales", "warehouse", "manager"],
    view:  "documents",
  },
  {
    type:  "standalone",
    id:    "settings-hub",
    label: "Pengaturan",
    icon:  Settings,
    // manager: HANYA tab "Penjadwal & Notifikasi" (lihat + jalankan job, tanpa configure)
    // selaras permissions_config resource `scheduler`; tab lain tetap admin-only.
    roles: ["admin", "manager"],
    hub:   "settings-hub",
  },
  {
    type:  "standalone",
    id:    "hr-my-profile",
    label: "Profil Saya",
    icon:  IdCard,
    roles: ["admin", "sales", "manager", "warehouse"],
    view:  "hr-my-profile",
  },
  {
    type:  "standalone",
    id:    "escalations",
    label: "Eskalasi",
    icon:  AlertTriangle,
    roles: ["admin", "warehouse", "manager"],
    view:  "escalations",
  },
];
