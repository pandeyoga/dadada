import React, { act } from "react";
import { render, screen, waitFor, within, fireEvent } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import PrototypeApp from "@/prototype/PrototypeApp";
import { __initStoreForTest, getState, setState } from "@/prototype/services/store";
import { setLatency } from "@/prototype/services/latency";
import {
  listTickets, createTicket, advanceTicket, confirmTicket, listWarranty, claimWarranty,
  listHomeDocuments, submitRenovation, listRenovations, listFacilities, bookFacility,
} from "@/prototype/services/api/care";
import {
  listFamily, inviteFamily, listDevices, getEnergy, listNotifications, markRead, markAllRead,
} from "@/prototype/services/api/account";
import { askQuestion } from "@/prototype/services/api/buyer";

const NOW = Date.parse("2026-11-25T03:00:00Z");
const mount = (path) =>
  render(
    <MemoryRouter initialEntries={[path]}>
      <Routes><Route path="/app/*" element={<PrototypeApp />} /></Routes>
    </MemoryRouter>
  );

beforeEach(() => {
  __initStoreForTest({ storage: null, now: () => NOW });
  setLatency(0);
});
afterAll(() => setLatency(null));

describe("tiket", () => {
  test("createTicket deskripsi pendek melempar pesan persis", async () => {
    await expect(createTicket({ kind: "rusak", category: "Kebocoran", description: "bocor", photos: [] }))
      .rejects.toThrow("Ceritakan kerusakannya sedikit lebih jelas");
    expect(getState().care.tickets).toHaveLength(2);
  });

  test("create + 3 advance + confirm: dikonfirmasi, riwayat 5", async () => {
    const t = await createTicket({ kind: "rusak", category: "Listrik", description: "Stopkontak ruang tamu mati total", photos: ["a"] });
    expect(t).toMatchObject({ status: "dibuat", kind: "rusak", photos: ["a"] });
    expect((await listTickets())[0].id).toBe(t.id);
    for (const s of ["diverifikasi", "dikerjakan", "selesai"]) {
      expect((await advanceTicket(t.id)).status).toBe(s);
    }
    await expect(advanceTicket(t.id)).rejects.toThrow("Tiket sudah selesai");
    const done = await confirmTicket(t.id, 5);
    expect(done).toMatchObject({ status: "dikonfirmasi", rating: 5 });
    expect(done.history).toHaveLength(5);
  });

  test("confirmTicket sebelum selesai melempar pesan persis; rating divalidasi", async () => {
    const t = await createTicket({ kind: "rusak", category: "Listrik", description: "Stopkontak ruang tamu mati total" });
    await expect(confirmTicket(t.id, 5)).rejects.toThrow("Tiket belum selesai dikerjakan");
    await advanceTicket(t.id); await advanceTicket(t.id); await advanceTicket(t.id);
    await expect(confirmTicket(t.id, 0)).rejects.toThrow("Beri nilai 1 sampai 5 bintang");
    await expect(confirmTicket(t.id, 6)).rejects.toThrow("Beri nilai 1 sampai 5 bintang");
    expect((await listTickets()).find((x) => x.id === t.id).status).toBe("selesai");
  });

  test("pertanyaan pembeli (tanya) memakai penulis tiket yang sama", async () => {
    const q = await askQuestion({ category: "KPR", description: "Kapan akad dijadwalkan?" });
    expect(q).toMatchObject({ kind: "tanya", status: "dibuat" });
    expect(q.history).toHaveLength(1);
    expect((await listTickets()).some((x) => x.id === q.id)).toBe(true);
  });
});

describe("garansi", () => {
  test("listWarranty menghitung sisa masa; klaim membuat tiket garansi", async () => {
    const list = await listWarranty();
    const atap = list.find((w) => w.id === "wr-2");
    expect(atap).toMatchObject({ active: true, remainingMonths: 11 });
    expect(atap.remainingDays).toBeGreaterThan(300);
    const t = await claimWarranty({ itemId: "wr-2", description: "Genteng bocor di kamar belakang" });
    expect(t).toMatchObject({ kind: "garansi", category: "Atap dan talang", status: "dibuat" });
  });

  test("garansi kedaluwarsa tidak bisa diklaim", async () => {
    setState((s) => ({ ...s, care: { ...s.care, warranty: s.care.warranty.map((w) => (w.id === "wr-5" ? { ...w, startedAt: new Date(NOW - 400 * 86400000).toISOString() } : w)) } }));
    expect((await listWarranty()).find((w) => w.id === "wr-5").active).toBe(false);
    await expect(claimWarranty({ itemId: "wr-5", description: "Dinding retak besar di ruang tamu" })).rejects.toThrow("Masa garansi Plester dan cat dinding sudah berakhir");
    await expect(claimWarranty({ itemId: "wr-2", description: "bocor" })).rejects.toThrow("Ceritakan kerusakannya sedikit lebih jelas");
    await expect(claimWarranty({ itemId: "zzz", description: "Dinding retak besar di ruang tamu" })).rejects.toThrow("Bagian rumah tidak ditemukan");
  });
});

describe("dokumen & renovasi", () => {
  test("listHomeDocuments memuat BAST, sertifikat, garansi, denah, jalur instalasi", async () => {
    const docs = await listHomeDocuments();
    const titles = docs.map((d) => d.title).join("|");
    ["BAST", "Sertifikat", "Garansi", "Denah", "Jalur instalasi"].forEach((k) => expect(titles).toContain(k));
    expect(docs.every((d) => d.status && d.kind)).toBe(true);
  });

  test("BAST tersedia untuk warga meski persona warga dipilih tanpa simulasi BAST", async () => {
    const bast = async () => (await listHomeDocuments()).find((d) => d.kind === "bast");
    expect((await bast()).status).toBe("Menunggu serah terima");
    setState((s) => ({ ...s, mode: "resident" }));
    expect(await bast()).toMatchObject({ status: "Tersedia", tone: "ok" });
  });

  test("submitRenovation memvalidasi dan menyimpan", async () => {
    await expect(submitRenovation({ type: "", startDate: "2026-12-01", endDate: "2026-12-10", contractor: "CV Maju" })).rejects.toThrow("Pilih jenis renovasi");
    await expect(submitRenovation({ type: "Tambah kamar", startDate: "2026-12-10", endDate: "2026-12-01", contractor: "CV Maju" })).rejects.toThrow("Tanggal selesai tidak boleh sebelum tanggal mulai");
    await expect(submitRenovation({ type: "Tambah kamar", startDate: "2026-12-01", endDate: "2026-12-10", contractor: " " })).rejects.toThrow("Nama kontraktor belum diisi");
    const r = await submitRenovation({ type: "Tambah kamar", startDate: "2026-12-01", endDate: "2026-12-10", contractor: "CV Maju" });
    expect(r.status).toBe("diajukan");
    expect(await listRenovations()).toHaveLength(1);
  });
});

describe("fasilitas", () => {
  test("bookFacility slot sama dua kali melempar pesan bentrok", async () => {
    const [lap] = await listFacilities();
    const b = await bookFacility({ facilityId: lap.id, date: "2026-12-01", slot: lap.slots[0] });
    expect(b).toMatchObject({ facilityId: lap.id, status: "dikonfirmasi" });
    await expect(bookFacility({ facilityId: lap.id, date: "2026-12-01", slot: lap.slots[0] })).rejects.toThrow("Jam ini sudah dipesan");
    await bookFacility({ facilityId: lap.id, date: "2026-12-02", slot: lap.slots[0] });
    expect(getState().care.bookings).toHaveLength(2);
    expect((await listFacilities())[0].bookings.map((x) => x.date)).toContain("2026-12-01");
  });

  test("validasi fasilitas, jam, dan tanggal", async () => {
    await expect(bookFacility({ facilityId: "x", date: "2026-12-01", slot: "09.00" })).rejects.toThrow("Fasilitas tidak ditemukan");
    await expect(bookFacility({ facilityId: "fc-1", date: "2026-12-01", slot: "03.00" })).rejects.toThrow("Pilih jam yang tersedia");
    await expect(bookFacility({ facilityId: "fc-1", date: "", slot: "16.00" })).rejects.toThrow("Pilih tanggal");
  });
});

describe("energi, notifikasi, keluarga", () => {
  test("getEnergy: 6 bulan, terbaru 142 dan sebelumnya 131 kWh", async () => {
    const e = await getEnergy();
    expect(e.months).toHaveLength(6);
    expect(e.months[5]).toMatchObject({ kwh: 142 });
    expect(e.months[4].kwh).toBe(131);
    expect(e.months[5].month).toBe("Nov");
    expect(e.tips.length).toBeGreaterThan(1);
  });

  test("listNotifications (mode warga) urut darurat dulu, lalu keamanan, info, terbaru dulu", async () => {
    setState((s) => ({ ...s, mode: "resident" }));
    const list = await listNotifications();
    expect(list[0].tier).toBe("darurat");
    const rank = { darurat: 0, keamanan: 1, info: 2 };
    for (let i = 1; i < list.length; i += 1) {
      const a = list[i - 1]; const b = list[i];
      expect(rank[a.tier] <= rank[b.tier]).toBe(true);
      if (a.tier === b.tier) expect(Date.parse(a.at) >= Date.parse(b.at)).toBe(true);
    }
  });

  test("markRead dan markAllRead (mode warga)", async () => {
    setState((s) => ({ ...s, mode: "resident" }));
    await markRead("nt-1");
    expect(getState().notifications.find((n) => n.id === "nt-1").read).toBe(true);
    await markAllRead();
    expect(getState().notifications.filter((n) => n.audience === "resident").every((n) => n.read)).toBe(true);
  });

  test("inviteFamily validasi, hak akses, dan dedup", async () => {
    await expect(inviteFamily({ name: " ", phone: "081234567890", role: "keluarga", access: [] })).rejects.toThrow("Nama belum diisi");
    await expect(inviteFamily({ name: "Bu Sari", phone: "0812", role: "penyewa", access: [] })).rejects.toThrow("Nomor WhatsApp Bu Sari belum lengkap");
    const m = await inviteFamily({ name: "Bu Sari", phone: "081234567890", role: "penyewa", access: ["pintu"] });
    expect(m).toMatchObject({ name: "Bu Sari", role: "penyewa", relation: "Penyewa", access: ["pintu"], phone: "0812-3456-7890" });
    const n = (await listFamily()).length;
    await inviteFamily({ name: "bu sari", phone: "081299990000", role: "penyewa", access: [] });
    expect((await listFamily())).toHaveLength(n);
    expect((await listFamily()).find((f) => f.id === "fm-1").access).toEqual(["pintu", "cctv"]);
  });

  test("listFamily menormalkan access boolean lama; listDevices", async () => {
    setState((s) => ({ ...s, care: { ...s.care, family: [{ id: "x", name: "A", relation: "Suami", phone: "", access: true }, { id: "y", name: "B", relation: "Anak", phone: "", access: false }] } }));
    const f = await listFamily();
    expect(f[0]).toMatchObject({ access: ["pintu", "cctv"], role: "keluarga" });
    expect(f[1].access).toEqual([]);
    expect((await listDevices()).some((d) => d.battery != null)).toBe(true);
  });
});

describe("layar", () => {
  test("W21: buat laporan → linimasa → konfirmasi + nilai", async () => {
    mount("/app/warga/lapor");
    expect(await screen.findByText("Atap dapur merembes saat hujan deras.")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Lapor kerusakan baru" }));
    const dialog = await screen.findByRole("dialog");
    fireEvent.click(within(dialog).getByRole("button", { name: "Listrik" }));
    fireEvent.change(within(dialog).getByLabelText("Ceritakan kerusakannya"), { target: { value: "bocor" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Kirim laporan" }));
    expect(await within(dialog).findByText("Ceritakan kerusakannya sedikit lebih jelas")).toBeTruthy();
    fireEvent.change(within(dialog).getByLabelText("Ceritakan kerusakannya"), { target: { value: "Stopkontak dapur mati sejak kemarin" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Kirim laporan" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    const mine = getState().care.tickets[0];
    expect(mine.status).toBe("dibuat");
    const card = (await screen.findByText("Stopkontak dapur mati sejak kemarin")).closest("[data-ticket]");
    expect(within(card).getByRole("listitem", { current: "step" }).textContent).toContain("Dibuat");
    for (let i = 0; i < 3; i += 1) { await act(() => advanceTicket(mine.id)); }
    fireEvent.click(await within(card).findByRole("button", { name: "Konfirmasi selesai + beri nilai" }));
    const rate = await screen.findByRole("dialog");
    fireEvent.click(within(rate).getByRole("button", { name: "4 bintang" }));
    fireEvent.click(within(rate).getByRole("button", { name: "Kirim nilai" }));
    await waitFor(() => expect(card.querySelector(".rdg-chip").textContent).toBe("Dikonfirmasi"));
    expect(getState().care.tickets[0]).toMatchObject({ status: "dikonfirmasi", rating: 4 });
  });

  test("W25: jam yang sudah dipesan tampil nonaktif", async () => {
    await bookFacility({ facilityId: "fc-1", date: "2026-12-01", slot: "16.00" });
    mount("/app/warga/fasilitas");
    fireEvent.click(await screen.findByRole("button", { name: "Pesan Lapangan serbaguna" }));
    const dialog = await screen.findByRole("dialog");
    fireEvent.change(within(dialog).getByLabelText("Tanggal"), { target: { value: "2026-12-01" } });
    await waitFor(() => expect(within(dialog).getByRole("button", { name: "16.00" }).disabled).toBe(true));
    expect(within(dialog).getByRole("button", { name: "17.00" }).disabled).toBe(false);
  });

  test("W27: darurat paling atas, tandai semua dibaca menghapus titik di beranda", async () => {
    setState((s) => ({ ...s, mode: "resident" }));
    mount("/app/notifikasi");
    const items = await screen.findAllByTestId("notif-item");
    expect(items[0].textContent).toContain("Peringatan banjir wilayah Setu");
    expect(screen.getByRole("heading", { name: "Darurat" })).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Tandai semua dibaca" }));
    await waitFor(() => expect(getState().notifications.filter((n) => n.audience === "resident").every((n) => n.read)).toBe(true));
  });

  test("W1: titik bel hilang setelah semua notifikasi dibaca", async () => {
    setState((s) => ({ ...s, mode: "resident" }));
    mount("/app/warga");
    const bell = await screen.findByRole("link", { name: "Notifikasi" });
    expect(bell.hasAttribute("data-badge")).toBe(true);
    await act(() => markAllRead());
    await waitFor(() => expect(screen.getByRole("link", { name: "Notifikasi" }).hasAttribute("data-badge")).toBe(false));
  });

  test("W28: data contoh, keluarga dengan chip akses, undangan tervalidasi, keluar", async () => {
    mount("/app/warga/akun");
    expect(await screen.findByText("Data contoh")).toBeTruthy();
    expect(await screen.findByText("Dimas Pratama")).toBeTruthy();
    expect(screen.getAllByText("Pintu").length).toBeGreaterThan(0);
    fireEvent.click(screen.getByRole("button", { name: "Undang anggota" }));
    const dialog = await screen.findByRole("dialog");
    fireEvent.change(within(dialog).getByLabelText("Nama"), { target: { value: "Bu Sari" } });
    fireEvent.change(within(dialog).getByLabelText("Nomor WhatsApp"), { target: { value: "0812" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Kirim undangan" }));
    expect(await within(dialog).findByText("Nomor WhatsApp Bu Sari belum lengkap")).toBeTruthy();
    fireEvent.change(within(dialog).getByLabelText("Nomor WhatsApp"), { target: { value: "081234567890" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Kirim undangan" }));
    expect(await screen.findByText("Bu Sari")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Keluar" }));
    await waitFor(() => expect(getState().session.loggedIn).toBe(false));
    await waitFor(() => expect(document.querySelector('[data-screen="U1"]')).not.toBeNull());
  });

  test.each([
    ["/app/warga/layanan", "W20"], ["/app/warga/garansi", "W22"], ["/app/warga/dokumen", "W23"],
    ["/app/warga/renovasi", "W24"], ["/app/warga/energi", "W26"],
  ])("%s merender layar %s", async (path, id) => {
    const { container } = mount(path);
    await waitFor(() => expect(container.querySelector(`[data-screen="${id}"]`)).not.toBeNull());
    await waitFor(() => expect(screen.queryByText("Memuat…")).toBeNull());
  });
});
