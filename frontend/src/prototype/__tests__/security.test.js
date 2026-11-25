import React, { act } from "react";
import { render, screen, waitFor, fireEvent, within } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import "@testing-library/jest-dom";
import PrototypeApp from "@/prototype/PrototypeApp";
import { __initStoreForTest, getState } from "@/prototype/services/store";
import { setLatency } from "@/prototype/services/latency";
import { setLocation } from "@/prototype/services/api/session";
import {
  doorStatus, unlockDoor, lockDoor, createAccessCode, revokeAccessCode,
  createGuestPass, revokeGuestPass, openGate,
} from "@/prototype/services/api/security";
import {
  sendSos, cancelSos, acceptSos, resolveSos, activeSos, listContacts, saveContact, removeContact,
} from "@/prototype/services/api/sos";

jest.mock("@/prototype/lib/scrollTop", () => ({ scrollToTop: jest.fn() }));

const NOW = Date.parse("2026-11-25T03:00:00Z"); // 10.00 WIB
let clock = NOW;

beforeAll(() => {
  if (!window.PointerEvent) {
    window.PointerEvent = class PointerEvent extends MouseEvent {
      constructor(type, init = {}) { super(type, init); this.pointerId = init.pointerId ?? 1; }
    };
  }
});
beforeEach(() => {
  clock = NOW;
  __initStoreForTest({ storage: null, now: () => clock });
  setLatency(0);
});
afterAll(() => setLatency(null));

const mount = (path) =>
  render(
    <MemoryRouter initialEntries={[path]}>
      <Routes><Route path="/app/*" element={<PrototypeApp />} /></Routes>
    </MemoryRouter>
  );

describe("kunci pintu", () => {
  test("unlockDoor: terbuka 10 detik, terkunci kembali setelah 30 detik, tercatat di riwayat", async () => {
    await unlockDoor();
    const s = getState();
    expect(doorStatus(s, NOW + 10000)).toBe("unlocked");
    expect(doorStatus(s, NOW + 30000)).toBe("locked");
    expect(s.security.doorLog[0]).toMatchObject({ who: "Rina", how: "Aplikasi", state: "unlocked" });
  });

  test("lockDoor menulis 'Otomatis terkunci' sekali saja (idempoten)", async () => {
    await unlockDoor();
    clock = NOW + 31000;
    await lockDoor();
    await lockDoor();
    const log = getState().security.doorLog;
    expect(getState().security.door.state).toBe("locked");
    expect(log.filter((l) => l.how === "Otomatis terkunci" && l.at === new Date(NOW + 30000).toISOString())).toHaveLength(1);
    expect(log[0].state).toBe("locked");
    expect(log.length).toBe(4 + 2);
  });

  test("kode akses: PIN 4 digit, bisa dicabut, label wajib", async () => {
    const code = await createAccessCode({ label: "Tukang AC", validUntil: new Date(NOW + 86400000).toISOString() });
    expect(code.pin).toMatch(/^\d{4}$/);
    expect(code.revoked).toBe(false);
    expect(getState().security.accessCodes[0].id).toBe(code.id);
    await revokeAccessCode(code.id);
    expect(getState().security.accessCodes.find((c) => c.id === code.id).revoked).toBe(true);
    await expect(createAccessCode({ label: " ", validUntil: new Date(NOW + 1000).toISOString() })).rejects.toThrow("Nama kode belum diisi");
  });
});

describe("tamu", () => {
  test("createGuestPass: kode 6 huruf/angka kapital, status active; revoke", async () => {
    const p = await createGuestPass({ guestName: "Pak Anto", date: "2026-11-26", from: "09:00", to: "12:00" });
    expect(p.code).toMatch(/^[A-Z0-9]{6}$/);
    expect(p.status).toBe("active");
    expect(getState().security.guestPasses[0].id).toBe(p.id);
    await revokeGuestPass(p.id);
    expect(getState().security.guestPasses[0].status).toBe("revoked");
  });

  test("validasi undangan", async () => {
    await expect(createGuestPass({ guestName: "", date: "2026-11-26", from: "09:00", to: "12:00" })).rejects.toThrow("Nama tamu belum diisi");
    await expect(createGuestPass({ guestName: "A", date: "", from: "09:00", to: "12:00" })).rejects.toThrow("Tanggal kunjungan belum diisi");
    await expect(createGuestPass({ guestName: "A", date: "2026-11-26", from: "12:00", to: "09:00" })).rejects.toThrow("Jam selesai harus setelah jam mulai");
  });
});

describe("gerbang", () => {
  test("di luar area: melempar pesan persis, tidak menulis log", async () => {
    setLocation("outside");
    await expect(openGate("masuk")).rejects.toThrow("Anda di luar area gerbang");
    expect(getState().security.gateLog).toHaveLength(4);
  });
  test("di dalam area: mencatat gerbang", async () => {
    await openGate("keluar");
    expect(getState().security.gateLog[0]).toMatchObject({ name: "Rina Ayu", purpose: "Penghuni", direction: "keluar" });
    await expect(openGate("samping")).rejects.toThrow("Arah gerbang tidak valid");
  });
});

describe("SOS", () => {
  test("sendSos: event + notifikasi darurat; kedua kali melempar; cancelSos membuka kembali", async () => {
    const e = await sendSos("kemalingan");
    expect(e).toMatchObject({ type: "kemalingan", unit: "C-12", status: "sent" });
    expect(activeSos(getState()).id).toBe(e.id);
    const n = getState().notifications[0];
    expect(n).toMatchObject({ tier: "darurat", link: "/app/warga/sos", read: false });
    await expect(sendSos("kemalingan")).rejects.toThrow("Masih ada laporan darurat yang aktif");
    await cancelSos(e.id);
    expect(getState().security.sos[0].status).toBe("cancelled");
    expect(activeSos(getState())).toBeNull();
    const e2 = await sendSos("medis");
    expect(e2.status).toBe("sent");
  });

  test("acceptSos lalu resolveSos; cancel setelah diterima ditolak", async () => {
    const e = await sendSos("kebakaran");
    await acceptSos(e.id, "Sutrisno");
    expect(activeSos(getState())).toMatchObject({ status: "accepted", acceptedBy: "Sutrisno" });
    await expect(cancelSos(e.id)).rejects.toThrow("Laporan sudah diterima satpam dan tidak bisa dibatalkan");
    await resolveSos(e.id);
    expect(getState().security.sos[0].status).toBe("resolved");
    expect(getState().security.sos[0].resolvedAt).toBeTruthy();
    expect(activeSos(getState())).toBeNull();
  });

  test("jenis tidak dikenal ditolak", async () => {
    await expect(sendSos("iseng")).rejects.toThrow("Jenis darurat tidak dikenal");
  });
});

describe("kontak darurat", () => {
  test("saveContact menyimpan role, memformat nomor, validasi dan duplikat; removeContact", async () => {
    const c = await saveContact({ name: "Bu Lastri", phone: "6281355550123", relation: "Tetangga" });
    expect(c).toMatchObject({ name: "Bu Lastri", phone: "0813-5555-0123", role: "Tetangga" });
    expect((await listContacts())[0].id).toBe(c.id);
    await expect(saveContact({ name: "Lain", phone: "0813-5555-0123", relation: "Keluarga" })).rejects.toThrow("Nomor ini sudah ada di kontak darurat");
    await expect(saveContact({ name: "", phone: "081355550999", relation: "x" })).rejects.toThrow("Nama belum diisi");
    await expect(saveContact({ name: "Dina", phone: "0813", relation: "x" })).rejects.toThrow("Nomor Dina belum lengkap");
    await removeContact(c.id);
    expect(getState().security.contacts.find((x) => x.id === c.id)).toBeUndefined();
  });
});

describe("layar keamanan", () => {
  test("W2: geser buka → terbuka + hitung mundur", async () => {
    mount("/app/warga/keamanan");
    const slider = await screen.findByRole("slider", { name: "Geser untuk buka" });
    slider.focus();
    fireEvent.keyDown(slider, { key: "Enter" });
    expect(await screen.findByText(/Terkunci otomatis dalam 30 detik/)).toBeInTheDocument();
    expect(screen.getAllByText(/Dibuka · Rina \(aplikasi\)/).length).toBeGreaterThan(0);
  });

  test("W2: tab Kawasan menampilkan 6 kamera dan satpam", async () => {
    mount("/app/warga/keamanan");
    fireEvent.click(await screen.findByRole("tab", { name: "Kawasan" }));
    expect(await screen.findAllByRole("figure")).toHaveLength(6);
    expect(screen.getByText(/Satpam bertugas/)).toBeInTheDocument();
  });

  test("W7: buat undangan → kode dan QR tampil", async () => {
    mount("/app/warga/keamanan/tamu");
    fireEvent.change(await screen.findByLabelText("Nama tamu"), { target: { value: "Pak Anto" } });
    fireEvent.click(screen.getByRole("button", { name: "Buat undangan" }));
    const qr = await screen.findByRole("img", { name: /QR undangan Pak Anto/ });
    expect(qr).toBeInTheDocument();
    const code = getState().security.guestPasses[0].code;
    expect(screen.getAllByText(code).length).toBeGreaterThan(0);
    const wa = screen.getByRole("link", { name: /Kirim lewat WhatsApp/ });
    expect(wa.getAttribute("href")).toMatch(/^https:\/\/wa\.me\/\?text=/);
  });

  test("W6: di luar area → pesan galat", async () => {
    setLocation("outside");
    mount("/app/warga/keamanan/gerbang");
    fireEvent.click(await screen.findByRole("button", { name: /Buka gerbang masuk/ }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Anda di luar area gerbang");
  });

  test("W8: tahan 3 detik → pilih jenis → menunggu → diterima satpam", async () => {
    mount("/app/warga/sos");
    const btn = screen.getByRole("button", { name: /SOS/ });
    jest.useFakeTimers();
    try {
      fireEvent.pointerDown(btn);
      act(() => jest.advanceTimersByTime(2999));
      expect(screen.queryByRole("radio")).not.toBeInTheDocument();
      act(() => jest.advanceTimersByTime(1));
    } finally {
      jest.useRealTimers();
    }
    expect(screen.getByRole("radio", { name: /Kemalingan/ })).toBeChecked();
    fireEvent.click(screen.getByRole("radio", { name: /Medis/ }));
    fireEvent.click(screen.getByRole("button", { name: "Kirim laporan" }));
    expect(await screen.findByText("Menunggu satpam…")).toBeInTheDocument();
    expect(getState().security.sos[0].type).toBe("medis");
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(screen.getByText(/Laporan palsu dapat dikenai sanksi pengelola/)).toBeInTheDocument();
    await act(async () => { await acceptSos(getState().security.sos[0].id, "Sutrisno"); });
    expect(await screen.findByText("Pak Sutrisno menuju rumah Anda")).toBeInTheDocument();
    await act(async () => { await resolveSos(getState().security.sos[0].id); });
    expect(await screen.findByText("Selesai", { selector: "h2" })).toBeInTheDocument();
  });

  test("W8: kirim → batalkan → tahan lagi → sheet bersih (jenis bawaan, tombol aktif) → kirim berhasil", async () => {
    mount("/app/warga/sos");
    const hold = () => {
      const btn = screen.getByRole("button", { name: /SOS/ });
      jest.useFakeTimers();
      try {
        fireEvent.pointerDown(btn);
        act(() => jest.advanceTimersByTime(3000));
      } finally {
        jest.useRealTimers();
      }
    };
    hold();
    fireEvent.click(screen.getByRole("radio", { name: /Kebakaran/ }));
    fireEvent.click(screen.getByRole("button", { name: "Kirim laporan" }));
    fireEvent.click(await screen.findByRole("button", { name: "Batalkan laporan" }));
    await waitFor(() => expect(getState().security.sos[0].status).toBe("cancelled"));
    await waitFor(() => expect(screen.getByRole("button", { name: /SOS/ })).toBeInTheDocument());
    hold();
    expect(screen.getByRole("radio", { name: /Kemalingan/ })).toBeChecked();
    const send = screen.getByRole("button", { name: "Kirim laporan" });
    expect(send).toBeEnabled();
    fireEvent.click(send);
    expect(await screen.findByText("Menunggu satpam…")).toBeInTheDocument();
    expect(getState().security.sos[0]).toMatchObject({ type: "kemalingan", status: "sent" });
  });

  test("W9: tambah kontak lewat formulir", async () => {
    mount("/app/warga/sos/kontak");
    fireEvent.click(await screen.findByRole("button", { name: /Tambah kontak/ }));
    fireEvent.change(await screen.findByLabelText("Nama"), { target: { value: "Bu Lastri" } });
    fireEvent.change(screen.getByLabelText("Nomor telepon"), { target: { value: "081355550123" } });
    fireEvent.change(screen.getByLabelText("Hubungan"), { target: { value: "Tetangga" } });
    fireEvent.click(screen.getByRole("button", { name: "Simpan kontak" }));
    await waitFor(() => expect(screen.getByText("Bu Lastri")).toBeInTheDocument());
    expect(within(document.body).getByText(/Tetangga · 0813-5555-0123/)).toBeInTheDocument();
  });
});
