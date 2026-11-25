const DAY = 86400000;
const HOUR = 3600000;
const MIN = 60000;
const iso = (t) => new Date(t).toISOString();

export function buildSecurity(now) {
  return {
    energy: { kwh: 142, lastKwh: 131, deltaPct: 8 },
    door: { state: "locked", changedAt: iso(now - 2 * HOUR) },
    cameras: {
      home: 2,
      area: 6,
      areaList: ["Gerbang utama", "Pos satpam", "Taman bermain", "Jalan Blok C", "Lapangan serbaguna", "Gerbang belakang"],
    },
    accessCodes: [{ id: "ac-1", label: "Bu Siti · ART", pin: "4821", validUntil: iso(now + 30 * DAY), revoked: false }],
    guestPasses: [],
    doorLog: [
      { id: "dl-1", who: "Rina Ayu", how: "Aplikasi", state: "unlocked", at: iso(now - 2 * HOUR - 5 * MIN) },
      { id: "dl-2", who: "Rina Ayu", how: "Otomatis terkunci", state: "locked", at: iso(now - 2 * HOUR) },
      { id: "dl-3", who: "Bu Siti · ART", how: "Kode akses", state: "unlocked", at: iso(now - 26 * HOUR) },
      { id: "dl-4", who: "Bu Siti · ART", how: "Otomatis terkunci", state: "locked", at: iso(now - 26 * HOUR + 30000) },
    ],
    gateLog: [
      { id: "gl-1", name: "Kurir paket", plate: "B 4421 KXA", purpose: "Antar paket", direction: "masuk", at: iso(now - 3 * HOUR) },
      { id: "gl-2", name: "Kurir paket", plate: "B 4421 KXA", purpose: "Antar paket", direction: "keluar", at: iso(now - 3 * HOUR + 12 * MIN) },
      { id: "gl-3", name: "Tukang galon", plate: "B 9120 PQ", purpose: "Antar galon", direction: "masuk", at: iso(now - 30 * HOUR) },
      { id: "gl-4", name: "Ojek online", plate: "B 6677 TZ", purpose: "Antar makanan", direction: "masuk", at: iso(now - 52 * HOUR) },
    ],
    sos: [],
    patrols: [
      { id: "pt-1", checkpoint: "Gerbang utama", note: "Aman, palang berfungsi normal.", by: "Pak Sutrisno", at: iso(now - 5 * HOUR) },
      { id: "pt-2", checkpoint: "Taman bermain", note: "Lampu taman menyala semua.", by: "Pak Sutrisno", at: iso(now - 4 * HOUR) },
      { id: "pt-3", checkpoint: "Jalan Blok C", note: "Tidak ada kendaraan mencurigakan.", by: "Pak Sutrisno", at: iso(now - 3 * HOUR) },
    ],
    contacts: [
      { id: "ct-1", name: "Satpam Estora (pos)", phone: "0857-1111-2200", role: "Keamanan" },
      { id: "ct-2", name: "Pak RT 04", phone: "0812-9000-4404", role: "Ketua RT" },
      { id: "ct-3", name: "Mas Dimas (suami)", phone: "0812-3456-7001", role: "Keluarga" },
    ],
  };
}

export function buildBills(now) {
  const due = (m) => `2026-${m}-10`;
  const mk = (id, period, m, paid, offsetDays) => ({
    id, kind: "ipl", period, amount: 150000, dueDate: due(m),
    status: paid ? "paid" : "unpaid",
    ...(paid ? { paidAt: iso(now - offsetDays * DAY), receiptId: `rc-${id}` } : {}),
  });
  const ipl = [
    mk("ipl-2026-12", "Desember 2026", "12", false),
    mk("ipl-2026-11", "November 2026", "11", true, 18),
    mk("ipl-2026-10", "Oktober 2026", "10", true, 48),
    mk("ipl-2026-09", "September 2026", "09", true, 78),
  ];
  const months = ["Juni", "Juli", "Agustus", "September", "Oktober", "November"];
  const cashReport = months.map((m, i) => {
    const garden = 250000 + (i % 3) * 50000;
    const income = 3000000 + i * 120000;
    return {
      month: `${m} 2026`,
      in: income,
      out: 1800000 + 350000 + garden,
      items: [
        { label: "Iuran IPL warga", amount: income, type: "in" },
        { label: "Gaji satpam dan kebersihan", amount: -1800000, type: "out" },
        { label: "Listrik penerangan jalan", amount: -350000, type: "out" },
        { label: "Perawatan taman", amount: -garden, type: "out" },
      ],
    };
  });
  return {
    ipl,
    air: [],
    payments: [],
    receipts: [
      { id: "rc-booking", targetType: "installment", targetId: "booking", title: "Biaya booking", amount: 500000, method: "va_bri", paidAt: iso(now - 152 * DAY) },
      { id: "rc-dp-1", targetType: "installment", targetId: "dp-1", title: "Uang muka 1 dari 5", amount: 1000000, method: "va_bni", paidAt: iso(now - 92 * DAY) },
      { id: "rc-dp-2", targetType: "installment", targetId: "dp-2", title: "Uang muka 2 dari 5", amount: 1000000, method: "qris", paidAt: iso(now - 47 * DAY) },
      ...ipl.filter((b) => b.status === "paid").map((b) => ({
        id: b.receiptId, targetType: "bill", targetId: b.id, title: `IPL ${b.period}`, amount: b.amount, method: "va_btn", paidAt: b.paidAt,
      })),
    ],
    ppobTx: [],
    cashOpening: 18500000, // saldo kas per akhir Mei 2026
    cashReport,
    ppobCatalog: [
      { id: "pulsa", label: "Pulsa", options: [10000, 25000, 50000, 100000].map((v) => ({ id: `pulsa-${v}`, label: `Pulsa ${v / 1000}rb`, nominal: v, price: v + 1500 })) },
      { id: "data", label: "Paket data", options: [{ id: "data-5", label: "Data 5 GB / 30 hari", nominal: 45000, price: 45000 }, { id: "data-12", label: "Data 12 GB / 30 hari", nominal: 75000, price: 75000 }] },
      { id: "listrik", label: "Token listrik", options: [20000, 50000, 100000, 200000].map((v) => ({ id: `pln-${v}`, label: `Token PLN ${v / 1000}rb`, nominal: v, price: v + 2500 })) },
      { id: "pdam", label: "Air PDAM", options: [{ id: "pdam-bulan", label: "Tagihan air bulan ini", nominal: 87500, price: 87500 }] },
      { id: "internet", label: "Internet rumah", options: [{ id: "net-20", label: "Paket 20 Mbps", price: 185000 }, { id: "net-50", label: "Paket 50 Mbps", price: 275000 }] },
    ],
  };
}
