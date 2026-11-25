import { buildVendors } from "./vendors";

const DAY = 86400000;
const HOUR = 3600000;
const iso = (t) => new Date(t).toISOString();

export function buildCare(now) {
  return {
    tickets: [
      {
        id: "tk-1", kind: "rusak", category: "Kebocoran", description: "Atap dapur merembes saat hujan deras.",
        photos: ["ticket/bocor-dapur"], status: "dikerjakan", assignee: "Tim Teknik Estora",
        history: [
          { status: "dibuat", at: iso(now - 6 * DAY), note: "Laporan dibuat oleh Rina Ayu." },
          { status: "diverifikasi", at: iso(now - 5 * DAY), note: "Teknisi memeriksa lokasi." },
          { status: "dikerjakan", at: iso(now - 2 * DAY), note: "Perbaikan talang dan genteng dijadwalkan." },
        ],
      },
      {
        id: "tk-2", kind: "tanya", category: "Administrasi", description: "Kapan jadwal tanda tangan akad KPR?",
        photos: [], status: "selesai", assignee: "Admin Estora", rating: 5,
        history: [
          { status: "dibuat", at: iso(now - 20 * DAY), note: "Pertanyaan dikirim." },
          { status: "dikerjakan", at: iso(now - 19 * DAY), note: "Admin menghubungi pihak bank." },
          { status: "selesai", at: iso(now - 18 * DAY), note: "Akad dijadwalkan setelah rumah siap huni." },
        ],
      },
    ],
    warranty: [
      { id: "wr-1", part: "Struktur dan pondasi", months: 120, startedAt: iso(now - 200 * DAY), note: "Garansi struktur 10 tahun." },
      { id: "wr-2", part: "Atap dan talang", months: 12, startedAt: iso(now - 30 * DAY), note: "Termasuk kebocoran akibat pemasangan." },
      { id: "wr-3", part: "Instalasi listrik", months: 12, startedAt: iso(now - 30 * DAY), note: "Kabel, saklar, dan MCB." },
      { id: "wr-4", part: "Instalasi air dan sanitasi", months: 12, startedAt: iso(now - 30 * DAY), note: "Pipa, kran, dan kloset." },
      { id: "wr-5", part: "Plester dan cat dinding", months: 6, startedAt: iso(now - 30 * DAY), note: "Retak rambut di luar garansi." },
      { id: "wr-6", part: "Pintu, jendela, dan keramik", months: 6, startedAt: iso(now - 30 * DAY), note: "Termasuk kunci dan engsel." },
    ],
    renovations: [],
    bookings: [],
    family: [
      { id: "fm-1", name: "Dimas Pratama", relation: "Suami", role: "keluarga", phone: "0812-3456-7001", access: ["pintu", "cctv"] },
      { id: "fm-2", name: "Alya Pratama", relation: "Anak", role: "keluarga", phone: "", access: [] },
    ],
    devices: [
      { id: "dv-1", kind: "kunci", name: "Kunci pintu depan", status: "online", battery: 82 },
      { id: "dv-2", kind: "kamera", name: "Kamera teras", status: "online", battery: null },
      { id: "dv-3", kind: "kamera", name: "Kamera ruang tamu", status: "online", battery: null },
      { id: "dv-4", kind: "hub", name: "Hub Estora", status: "online", battery: null },
    ],
  };
}

export function buildManager(now, world) {
  const units = [{ block: world.unit.block, owner: world.resident.name }, ...world.neighbors.slice(0, 19).map((n) => ({ block: n.block, owner: n.name }))];
  const status = (i) => (i === 0 ? "belum" : i % 5 === 0 ? "belum" : i % 7 === 0 ? "terlambat" : "lunas");
  const full = units.map((u, i) => ({ ...u, ipl: status(i), amount: 150000, phone: i === 0 ? world.resident.phone : world.neighbors[i - 1].phone }));
  return {
    units: full,
    occupancy: { occupied: 18, total: 20 },
    // Status unit per periode; status C-12 selalu dibaca dari bills.ipl (sumber tunggal).
    iplPeriods: [
      { period: "2026-12", label: "Desember 2026", issuedAt: iso(now - 14 * DAY), statuses: Object.fromEntries(full.slice(1).map((u) => [u.block, u.ipl])) },
    ],
    technicians: ["Tim Teknik Estora", "Pak Dedi (ledeng)", "Pak Slamet (bangunan)", "Pak Hendra (listrik dan AC)"],
    vendors: buildVendors(),
    announcements: [
      { id: "mgr-an-1", title: "Rapat warga akhir tahun", body: "Rapat evaluasi keamanan dan iuran, Sabtu 13 Des pukul 19.30 di balai warga.", tier: "info", at: iso(now - 2 * DAY) },
    ],
  };
}

export function buildNotifications(now) {
  const mk = (id, tier, title, body, ago, read, link) => ({ id, tier, title, body, at: iso(now - ago), read, ...(link ? { link } : {}) });
  return [
    mk("nt-1", "darurat", "Peringatan banjir wilayah Setu", "Curah hujan tinggi. Waspada genangan di Jalan Blok C.", 2 * HOUR, false),
    mk("nt-2", "keamanan", "Pintu depan terkunci otomatis", "Kunci pintu C-12 terkunci kembali setelah 30 detik.", 2 * HOUR, false, "/app/warga/keamanan/kunci"),
    mk("nt-3", "keamanan", "Tamu tiba di gerbang", "Kurir paket masuk melalui gerbang utama.", 3 * HOUR, true),
    mk("nt-4", "info", "Tagihan IPL Desember", "Iuran Rp150.000 jatuh tempo 10 Des.", 1 * DAY, false, "/app/warga/tagihan"),
    mk("nt-5", "info", "Foto progres pembangunan baru", "Tahap pintu, jendela, dan listrik telah diunggah.", 6 * DAY, true),
    mk("nt-6", "info", "Uang muka ke-3 jatuh tempo 10 Des", "Siapkan Rp1.000.000 untuk pembayaran uang muka.", 2 * DAY, false),
  ];
}
