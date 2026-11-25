const NAMES = [
  "Budi Santoso", "Siti Aminah", "Agus Wijaya", "Dewi Lestari", "Hendra Gunawan",
  "Yuni Kartika", "Rudi Hartono", "Maya Sari", "Dedi Kurniawan", "Fitri Handayani",
  "Eko Prasetyo", "Lina Marlina", "Joko Susilo", "Ani Rahayu", "Bambang Irawan",
  "Wati Susanti", "Slamet Riyadi", "Nur Hasanah", "Andi Saputra", "Ratna Dewi",
];
const BLOCKS = ["A-03", "A-07", "A-11", "B-02", "B-05", "B-09", "B-14", "C-01", "C-04", "C-08",
  "C-15", "C-17", "D-02", "D-06", "D-10", "D-13", "E-01", "E-05", "E-09", "E-12"];

export function buildWorld() {
  return {
    project: { name: "Estora Residence", city: "Kab. Bekasi", address: "Jl. Raya Setu No. 88, Kab. Bekasi" },
    unit: { block: "C-12", type: "36/72", price: 166000000, scheme: "KPR Subsidi FLPP", bank: "Bank BTN" },
    resident: { name: "Rina Ayu", phone: "0812-3456-7890", email: "rina.ayu@contoh.id" },
    neighbors: NAMES.map((name, i) => ({
      id: `nb-${i + 1}`,
      name,
      block: BLOCKS[i],
      phone: `0813-${String(2000 + i * 37).padStart(4, "0")}-${String(4100 + i * 53).padStart(4, "0")}`,
    })),
    guards: [
      { id: "g-1", name: "Pak Sutrisno", shift: "Pagi 06.00-14.00", phone: "0857-1111-2201" },
      { id: "g-2", name: "Pak Wahyu", shift: "Siang 14.00-22.00", phone: "0857-1111-2202" },
      { id: "g-3", name: "Pak Darmin", shift: "Malam 22.00-06.00", phone: "0857-1111-2203" },
      { id: "g-4", name: "Pak Joko", phone: "0857-1111-2204", post: "Pos gerbang utama" },
    ],
  };
}
