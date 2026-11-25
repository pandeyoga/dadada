const DAY = 86400000;
const iso = (t) => new Date(t).toISOString();

export function buildPartner(now) {
  return {
    registered: false,
    profile: { name: "Dimas Pratama", phone: "0812-3456-7001", code: "MITRA-DP01", tier: "Perak" },
    points: 1250,
    commissions: [
      { id: "cm-1", title: "Komisi akad · Sari Wulandari", amount: 1500000, status: "cair", at: iso(now - 40 * DAY) },
      { id: "cm-2", title: "Komisi booking · Anto Wibowo", amount: 500000, status: "cair", at: iso(now - 18 * DAY) },
      { id: "cm-3", title: "Komisi booking · Lilis Suryani", amount: 500000, status: "diproses", at: iso(now - 4 * DAY) },
    ],
    referrals: [
      { id: "rf-1", name: "Sari Wulandari", phone: "0813-5000-1001", stage: "akad", at: iso(now - 70 * DAY) },
      { id: "rf-2", name: "Anto Wibowo", phone: "0813-5000-1002", stage: "booking", at: iso(now - 25 * DAY) },
      { id: "rf-3", name: "Lilis Suryani", phone: "0813-5000-1003", stage: "booking", at: iso(now - 9 * DAY) },
      { id: "rf-4", name: "Fajar Nugroho", phone: "0813-5000-1004", stage: "lead", at: iso(now - 3 * DAY) },
      { id: "rf-5", name: "Mega Anggraini", phone: "0813-5000-1005", stage: "lead", at: iso(now - 1 * DAY) },
    ],
    payouts: [],
    leaderboard: [
      { name: "Budi Santoso", listings: 14 },
      { name: "Wulan Pertiwi", listings: 11 },
      { name: "Dimas Pratama", listings: 8 },
      { name: "Hendra Gunawan", listings: 6 },
      { name: "Siti Rahmawati", listings: 4 },
    ],
    catalog: [
      { id: "C-14", block: "C-14", type: "36/72", price: 166000000, status: "tersedia", img: "unit/tipe-36", project: "Estora Residence" },
      { id: "F-02", block: "F-02", type: "30/60", price: 166000000, status: "tersedia", img: "unit/tipe-30", project: "Estora Residence" },
      { id: "F-03", block: "F-03", type: "30/60", price: 166000000, status: "tersedia", img: "unit/tipe-30", project: "Estora Residence" },
      { id: "F-05", block: "F-05", type: "36/72", price: 166000000, status: "tersedia", img: "unit/tipe-36", project: "Estora Residence" },
      { id: "F-06", block: "F-06", type: "36/72", price: 166000000, status: "tersedia", img: "unit/tipe-36", project: "Estora Residence" },
      { id: "G-01", block: "G-01", type: "36/84", price: 189000000, status: "tersedia", img: "unit/tipe-36", project: "Estora Residence" },
      { id: "G-04", block: "G-04", type: "36/84", price: 189000000, status: "tersedia", img: "unit/tipe-36", project: "Estora Residence" },
      { id: "G-07", block: "G-07", type: "45/90", price: 235000000, status: "tersedia", img: "unit/tipe-45", project: "Estora Residence" },
    ],
  };
}
