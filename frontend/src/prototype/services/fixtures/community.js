const DAY = 86400000;
const HOUR = 3600000;
const iso = (t) => new Date(t).toISOString();

export function buildCommunity(now) {
  return {
    announcements: [
      { id: "an-1", title: "Penyemprotan nyamuk (fogging)", body: "Fogging seluruh blok hari Jumat pukul 15.30. Mohon jendela ditutup dan hewan peliharaan dibawa masuk.", author: "Pengelola", at: iso(now - 1 * DAY), pinned: true },
      { id: "an-2", title: "Pemadaman listrik terjadwal", body: "PLN memadamkan listrik Blok C-D, Sabtu 08.00-11.00 untuk perawatan trafo.", author: "Pengelola", at: iso(now - 3 * DAY), pinned: false },
      { id: "an-3", title: "Iuran IPL Desember", body: "Iuran IPL Rp150.000 jatuh tempo 10 Des. Bayar lewat aplikasi agar tercatat otomatis.", author: "Bendahara RT", at: iso(now - 5 * DAY), pinned: false },
    ],
    events: [
      { id: "ev-1", title: "Kerja bakti Minggu, 7 Des", date: "2026-12-07", time: "07.00", place: "Lapangan serbaguna", body: "Bersih-bersih saluran air dan taman. Bawa sapu dan sarung tangan.", going: 14, rsvp: false },
      { id: "ev-2", title: "Senam pagi bersama", date: "2026-11-30", time: "06.00", place: "Taman bermain", body: "Senam sehat setiap Minggu pagi, terbuka untuk semua usia.", going: 22, rsvp: false },
      { id: "ev-3", title: "Pengajian bulanan", date: "2026-12-14", time: "19.30", place: "Musala Al-Ikhlas", body: "Pengajian rutin dengan Ustaz Rahmat, dilanjutkan makan bersama.", going: 31, rsvp: false },
      { id: "ev-4", title: "Bazar UMKM warga", date: "2026-12-21", time: "09.00", place: "Lapangan serbaguna", body: "Warga menjual makanan dan kerajinan. Daftar lewat pengelola.", going: 9, rsvp: false },
    ],
    groups: [
      { id: "gr-1", name: "Ibu-ibu Estora", members: 48, about: "Arisan, resep, dan info belanja." },
      { id: "gr-2", name: "Bapak-bapak Ronda", members: 36, about: "Jadwal ronda dan info keamanan." },
      { id: "gr-3", name: "Pecinta Tanaman", members: 27, about: "Tukar bibit dan tips berkebun." },
      { id: "gr-4", name: "Klub Futsal Estora", members: 22, about: "Main bareng tiap Rabu malam." },
      { id: "gr-5", name: "Orang Tua Murid TK", members: 19, about: "Antar jemput dan info sekolah." },
    ],
    polls: [
      { id: "po-1", question: "Jam ronda malam sebaiknya mulai pukul berapa?", options: [{ id: "a", label: "21.00", votes: 18 }, { id: "b", label: "22.00", votes: 25 }, { id: "c", label: "23.00", votes: 7 }], voted: null, closesAt: iso(now + 4 * DAY) },
      { id: "po-2", question: "Setuju memasang lampu taman tambahan (iuran sekali Rp20.000)?", options: [{ id: "a", label: "Setuju", votes: 41 }, { id: "b", label: "Tidak setuju", votes: 6 }], voted: null, closesAt: iso(now + 7 * DAY) },
    ],
    market: [
      { id: "mk-1", name: "Nasi kuning komplit", seller: "Bu Ratna · D-10", price: 15000, img: "market/nasi-kuning", sellerType: "warga", category: "Makanan", stock: 20 },
      { id: "mk-2", name: "Kue brownies kukus", seller: "Bu Maya · B-09", price: 35000, img: "market/brownies", sellerType: "warga", category: "Makanan", stock: 12 },
      { id: "mk-3", name: "Keripik singkong pedas", seller: "Bu Wati · E-05", price: 18000, img: "market/keripik", sellerType: "warga", category: "Makanan", stock: 30 },
      { id: "mk-4", name: "Es kopi susu botol", seller: "Pak Andi · E-12", price: 12000, img: "market/kopi", sellerType: "warga", category: "Minuman", stock: 25 },
      { id: "mk-5", name: "Bibit cabai rawit", seller: "Pak Joko · C-15", price: 8000, img: "market/cabai", sellerType: "warga", category: "Tanaman", stock: 40 },
      { id: "mk-6", name: "Pot tanaman gerabah", seller: "Pak Eko · C-04", price: 25000, img: "market/pot", sellerType: "warga", category: "Tanaman", stock: 15 },
      { id: "mk-7", name: "Sprei katun motif batik", seller: "Bu Lina · C-17", price: 85000, img: "market/sprei", sellerType: "warga", category: "Rumah tangga", stock: 8 },
      { id: "mk-8", name: "Telur ayam kampung (10 butir)", seller: "Pak Slamet · E-01", price: 32000, img: "market/telur", sellerType: "warga", category: "Makanan", stock: 18 },
      { id: "mk-9", name: "Gantungan kunci rajut", seller: "Bu Fitri · B-14", price: 10000, img: "market/rajut", sellerType: "warga", category: "Kerajinan", stock: 35 },
      { id: "mk-10", name: "Beras premium 5 kg", seller: "Minimarket Estora · Ruko R-01", price: 72000, img: "market/beras", sellerType: "tenant", category: "Sembako", stock: 30 },
      { id: "mk-11", name: "Kopi susu gula aren", seller: "Kedai Kopi Senja · Ruko R-03", price: 18000, img: "market/kopi", sellerType: "tenant", category: "Minuman", stock: 50 },
      { id: "mk-12", name: "Paket laundry 5 kg", seller: "Laundry Bersih · Ruko R-02", price: 35000, img: "market/laundry", sellerType: "tenant", category: "Jasa", stock: 20 },
    ],
    services: [
      { id: "sv-1", name: "Servis AC", provider: "Pak Hendra · B-05", price: "Mulai Rp75.000", phone: "0813-2000-4100", category: "Perbaikan", rating: 4.8 },
      { id: "sv-2", name: "Tukang ledeng", provider: "Pak Dedi · C-08", price: "Mulai Rp60.000", phone: "0813-2074-4153", category: "Perbaikan", rating: 4.6 },
      { id: "sv-3", name: "Laundry kiloan", provider: "Bu Yuni · B-02", price: "Rp7.000/kg", phone: "0813-2111-4206", category: "Rumah tangga", rating: 4.7 },
      { id: "sv-4", name: "Asisten rumah tangga harian", provider: "Bu Siti", price: "Rp70.000/hari", phone: "0813-2148-4259", category: "Rumah tangga", rating: 4.9 },
      { id: "sv-5", name: "Katering harian", provider: "Bu Dewi · A-07", price: "Rp18.000/porsi", phone: "0813-2037-4112", category: "Makanan", rating: 4.5 },
      { id: "sv-6", name: "Les privat matematika SD", provider: "Pak Bambang · D-13", price: "Rp50.000/sesi", phone: "0813-2555-4411", category: "Pendidikan", rating: 4.8 },
      { id: "sv-7", name: "Ojek antar sekolah", provider: "Pak Rudi · A-11", price: "Rp10.000/trip", phone: "0813-2222-4300", category: "Antar jemput", rating: 4.4 },
      { id: "sv-8", name: "Tukang perbaikan rumah", provider: "Pak Slamet · E-01", price: "Rp120.000/hari", phone: "0813-2301-4500", category: "Perbaikan", rating: 4.7 },
      { id: "sv-9", name: "Kebersihan rumah", provider: "Bu Sari · D-03", price: "Mulai Rp90.000", phone: "0813-2302-4511", category: "Rumah tangga", rating: 4.6 },
      { id: "sv-10", name: "Isi ulang galon", provider: "Pak Anto · A-02", price: "Rp20.000/galon", phone: "0813-2303-4522", category: "Rumah tangga", rating: 4.8 },
      { id: "sv-11", name: "Sedot WC", provider: "Pak Yanto · E-08", price: "Mulai Rp250.000", phone: "0813-2304-4533", category: "Perbaikan", rating: 4.5 },
      { id: "sv-12", name: "Perawatan taman", provider: "Pak Eko · C-04", price: "Mulai Rp80.000", phone: "0813-2305-4544", category: "Taman", rating: 4.7 },
    ],
    facilities: [
      { id: "fc-1", name: "Lapangan serbaguna", about: "Futsal dan bulu tangkis, tersedia 06.00-21.00.", fee: "Rp50.000/jam", slots: ["16.00", "17.00", "19.00", "20.00"], img: "facility/lapangan" },
      { id: "fc-2", name: "Musala Al-Ikhlas", about: "Ruang ibadah dan pengajian, kapasitas 80 orang.", fee: "Gratis", slots: ["09.00", "13.00", "19.30"], img: "facility/musala" },
      { id: "fc-3", name: "Balai warga", about: "Untuk hajatan dan rapat, termasuk kursi dan sound system.", fee: "Rp250.000/acara", slots: ["Pagi", "Siang", "Malam"], img: "facility/balai" },
      { id: "fc-4", name: "Taman bermain anak", about: "Ayunan dan perosotan, diawasi satpam.", fee: "Gratis", slots: [], img: "facility/taman" },
    ],
    chats: [
      { id: "ch-1", groupId: "gr-1", from: "Bu Ratna", text: "Arisan bulan ini di rumah Bu Maya ya, Sabtu jam 4.", at: iso(now - 4 * HOUR) },
      { id: "ch-2", groupId: "gr-1", from: "Bu Maya", text: "Siap, saya siapkan kue.", at: iso(now - 3 * HOUR) },
    ],
    bookings: [],
    cart: [],
    orders: [],
  };
}
