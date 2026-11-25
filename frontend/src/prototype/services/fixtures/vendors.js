// Mitra kawasan: penyewa ruko (produk di Pasar warga) dan penyedia jasa rumah (Jasa rumah).
// itemIds merujuk community.market, serviceIds merujuk community.services.
const TENANTS = [
  ["vd-t1", "Minimarket Estora", "Ruko R-01", "Sembako", ["mk-10"]],
  ["vd-t2", "Kedai Kopi Senja", "Ruko R-03", "Minuman", ["mk-11"]],
  ["vd-t3", "Laundry Bersih", "Ruko R-02", "Jasa", ["mk-12"]],
];

const PROVIDERS = [
  ["sv-1", "Pak Hendra", "B-05", "Servis AC"],
  ["sv-2", "Pak Dedi", "C-08", "Tukang ledeng"],
  ["sv-3", "Bu Yuni", "B-02", "Laundry kiloan"],
  ["sv-4", "Bu Siti", "Warga", "Asisten rumah tangga"],
  ["sv-5", "Bu Dewi", "A-07", "Katering harian"],
  ["sv-6", "Pak Bambang", "D-13", "Les privat"],
  ["sv-7", "Pak Rudi", "A-11", "Ojek antar sekolah"],
  ["sv-8", "Pak Slamet", "E-01", "Perbaikan rumah"],
  ["sv-9", "Bu Sari", "D-03", "Kebersihan rumah"],
  ["sv-10", "Pak Anto", "A-02", "Isi ulang galon"],
  ["sv-11", "Pak Yanto", "E-08", "Sedot WC"],
  ["sv-12", "Pak Eko", "C-04", "Perawatan taman"],
];

export function buildVendors() {
  return [
    ...TENANTS.map(([id, name, place, category, itemIds]) => ({ id, name, kind: "tenant", place, category, itemIds, serviceIds: [], status: "aktif" })),
    ...PROVIDERS.map(([sv, name, place, category], i) => ({ id: `vd-s${i + 1}`, name, kind: "jasa", place, category, itemIds: [], serviceIds: [sv], status: "aktif" })),
  ];
}
