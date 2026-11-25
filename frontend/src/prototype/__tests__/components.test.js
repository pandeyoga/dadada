import React, { act } from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import "@testing-library/jest-dom";
import HoldToConfirm from "@/prototype/components/HoldToConfirm";
import SlideToConfirm from "@/prototype/components/SlideToConfirm";
import PayFlow from "@/prototype/components/PayFlow";
import BottomNav from "@/prototype/components/BottomNav";
import Sheet from "@/prototype/components/Sheet";
import { __initStoreForTest, getState } from "@/prototype/services/store";
import { setLatency } from "@/prototype/services/latency";

// jsdom 16 tidak punya PointerEvent; tanpa ini clientX hilang dari event pointer.
beforeAll(() => {
  if (!window.PointerEvent) {
    window.PointerEvent = class PointerEvent extends MouseEvent {
      constructor(type, init = {}) {
        super(type, init);
        this.pointerId = init.pointerId ?? 1;
      }
    };
  }
});

describe("HoldToConfirm", () => {
  beforeEach(() => jest.useFakeTimers());
  afterEach(() => jest.useRealTimers());

  const setup = () => {
    const onConfirm = jest.fn();
    render(<HoldToConfirm onConfirm={onConfirm} label="SOS" />);
    return { onConfirm, btn: screen.getByRole("button", { name: /SOS/ }) };
  };

  test("tahan 3000 ms memicu onConfirm tepat sekali", () => {
    const { onConfirm, btn } = setup();
    fireEvent.pointerDown(btn);
    act(() => jest.advanceTimersByTime(2999));
    expect(onConfirm).not.toHaveBeenCalled();
    act(() => jest.advanceTimersByTime(1));
    expect(onConfirm).toHaveBeenCalledTimes(1);
    act(() => jest.advanceTimersByTime(5000));
    expect(onConfirm).toHaveBeenCalledTimes(1);
  });

  test("lepas sebelum 3000 ms membatalkan", () => {
    const { onConfirm, btn } = setup();
    fireEvent.pointerDown(btn);
    act(() => jest.advanceTimersByTime(2000));
    fireEvent.pointerUp(btn);
    act(() => jest.advanceTimersByTime(2000));
    expect(onConfirm).not.toHaveBeenCalled();
  });

  test("tahan tombol Space 3000 ms memicu onConfirm; lepas lebih awal batal", () => {
    const { onConfirm, btn } = setup();
    fireEvent.keyDown(btn, { key: " ", code: "Space" });
    act(() => jest.advanceTimersByTime(1500));
    fireEvent.keyUp(btn, { key: " ", code: "Space" });
    act(() => jest.advanceTimersByTime(3000));
    expect(onConfirm).not.toHaveBeenCalled();

    fireEvent.keyDown(btn, { key: " ", code: "Space" });
    act(() => jest.advanceTimersByTime(3000));
    expect(onConfirm).toHaveBeenCalledTimes(1);
  });

  test("menampilkan hitung mundur saat ditahan", () => {
    const { btn } = setup();
    expect(btn).toHaveTextContent("Tahan 3 detik");
    fireEvent.pointerDown(btn);
    act(() => jest.advanceTimersByTime(1000));
    expect(btn).toHaveTextContent("2 detik lagi");
  });
});

describe("SlideToConfirm", () => {
  test("fokus + Enter memicu onConfirm", () => {
    const onConfirm = jest.fn();
    render(<SlideToConfirm onConfirm={onConfirm} label="Geser untuk buka" />);
    const slider = screen.getByRole("slider", { name: "Geser untuk buka" });
    slider.focus();
    expect(slider).toHaveFocus();
    fireEvent.keyDown(slider, { key: "Enter" });
    expect(onConfirm).toHaveBeenCalledTimes(1);
  });

  describe("geser dengan pointer", () => {
    let rectSpy;
    beforeEach(() => {
      rectSpy = jest.spyOn(Element.prototype, "getBoundingClientRect").mockImplementation(function rect() {
        const w = this.dataset.slideTrack !== undefined ? 300 : this.dataset.slideKnob !== undefined ? 52 : 0;
        return { x: 0, y: 0, left: 0, top: 0, right: w, bottom: 0, width: w, height: 0 };
      });
    });
    afterEach(() => rectSpy.mockRestore());

    const drag = (knob, dx) => {
      fireEvent.pointerDown(knob, { clientX: 10, pointerId: 1 });
      fireEvent.pointerMove(knob, { clientX: 10 + dx, pointerId: 1 });
      fireEvent.pointerUp(knob, { clientX: 10 + dx, pointerId: 1 });
    };

    test("ketuk saja atau geser < 90 % tidak membuka; geser >= 90 % membuka", () => {
      const onConfirm = jest.fn();
      const { container } = render(<SlideToConfirm onConfirm={onConfirm} label="Geser untuk buka" />);
      const knob = container.querySelector("[data-slide-knob]");
      drag(knob, 0);
      drag(knob, 180); // 180 / 240 = 75 %
      expect(onConfirm).not.toHaveBeenCalled();
      drag(knob, 230); // 230 / 240 ≈ 96 %
      expect(onConfirm).toHaveBeenCalledTimes(1);
    });
  });
});

describe("Sheet", () => {
  test("dirender di dalam pohon pemanggil (tanpa portal), tutup dengan Esc dan klik latar", () => {
    const onClose = jest.fn();
    const { container } = render(
      <div className="rdg">
        <Sheet open onClose={onClose} title="Keranjang">
          <p>Isi</p>
        </Sheet>
      </div>
    );
    const dialog = screen.getByRole("dialog", { name: "Keranjang" });
    expect(dialog).toHaveAttribute("aria-modal", "true");
    expect(container.querySelector(".rdg [role=dialog]")).toBe(dialog);
    fireEvent.keyDown(document, { key: "Escape" });
    expect(onClose).toHaveBeenCalledTimes(1);
    fireEvent.click(container.querySelector("[data-sheet-backdrop]"));
    expect(onClose).toHaveBeenCalledTimes(2);
  });

  test("tertutup tidak merender apa pun", () => {
    render(<Sheet open={false} onClose={() => {}} title="X">isi</Sheet>);
    expect(screen.queryByRole("dialog")).toBeNull();
  });
});

describe("PayFlow", () => {
  beforeEach(() => {
    __initStoreForTest({ storage: null });
    setLatency(0);
  });
  afterEach(() => setLatency(null));

  const target = { type: "installment", id: "dp-3", title: "Uang muka 3 dari 5", amount: 1000000 };

  test("VA BRI → kode 16 digit berawalan 8 → Saya sudah bayar → lunas + satu kuitansi", async () => {
    const onPaid = jest.fn();
    // StrictMode seperti di index.js: efek dipasang-lepas-pasang saat dev.
    render(
      <React.StrictMode>
        <PayFlow open onClose={() => {}} target={target} onPaid={onPaid} />
      </React.StrictMode>
    );
    fireEvent.click(screen.getByRole("button", { name: /VA BRI/ }));

    const code = await screen.findByText(/^8\d{3} \d{4} \d{4} \d{4}$/);
    expect(code.textContent.replace(/\s/g, "")).toMatch(/^8800\d{12}$/);
    expect(getState().bills.payments[0].code).toBe(code.textContent.replace(/\s/g, ""));

    const before = getState().bills.receipts.length;
    const pay = screen.getByRole("button", { name: "Saya sudah bayar" });
    fireEvent.click(pay);
    fireEvent.click(pay);

    await screen.findByText("Pembayaran berhasil");
    expect(onPaid).toHaveBeenCalledTimes(1);
    expect(onPaid.mock.calls[0][0].receipt.amount).toBe(target.amount);
    expect(getState().bills.receipts.length).toBe(before + 1);
    expect(getState().buyer.installments.find((i) => i.id === "dp-3").status).toBe("paid");
  });

  test("QRIS menampilkan pola QR lokal (SVG) dan WhatsApp hanya menampilkan teks tautan", async () => {
    const { unmount } = render(<PayFlow open onClose={() => {}} target={target} onPaid={() => {}} />);
    fireEvent.click(screen.getByRole("button", { name: /QRIS/ }));
    const qr = await screen.findByRole("img", { name: /Kode QRIS/ });
    expect(qr.tagName.toLowerCase()).toBe("svg");
    unmount();

    render(<PayFlow open onClose={() => {}} target={target} onPaid={() => {}} />);
    fireEvent.click(screen.getByRole("button", { name: /WhatsApp/ }));
    const link = await screen.findByText(/^https:\/\/wa\.me\/\?text=/);
    expect(link.closest("a")).toBeNull();
  });

  test("tagihan yang sudah lunas menampilkan pesan, bukan kode bayar", async () => {
    render(<PayFlow open onClose={() => {}} target={{ ...target, id: "dp-1" }} onPaid={() => {}} />);
    fireEvent.click(screen.getByRole("button", { name: /VA BNI/ }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Tagihan ini sudah lunas");
  });
});

describe("BottomNav", () => {
  const renderNav = (variant, path) =>
    render(
      <MemoryRouter initialEntries={[path]}>
        <BottomNav variant={variant} />
      </MemoryRouter>
    );

  test("resident: 5 tautan, SOS di tengah dengan aria-label", () => {
    renderNav("resident", "/app/warga");
    const links = screen.getAllByRole("link");
    expect(links.map((l) => l.textContent)).toEqual(["Beranda", "Keamanan", "SOS", "Tagihan", "Komunitas"]);
    expect(links.map((l) => l.getAttribute("href"))).toEqual([
      "/app/warga", "/app/warga/keamanan", "/app/warga/sos", "/app/warga/tagihan", "/app/warga/komunitas",
    ]);
    expect(screen.getByRole("link", { name: "SOS darurat" })).toBe(links[2]);
    expect(links[0]).toHaveAttribute("aria-current", "page");
  });

  test("tab aktif juga di subhalaman, Beranda tidak", () => {
    renderNav("resident", "/app/warga/keamanan/kunci");
    expect(screen.getByRole("link", { name: "Keamanan" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "Beranda" })).not.toHaveAttribute("aria-current");
  });

  test.each([
    ["buyer", "/app/pembeli", ["Beranda", "Progres", "Bayar", "Dokumen", "Akun"],
      ["/app/pembeli", "/app/pembeli/progres", "/app/pembeli/bayar", "/app/pembeli/dokumen", "/app/pembeli/akun"]],
    ["satpam", "/app/satpam", ["Pos", "Tamu", "CCTV", "Patroli"],
      ["/app/satpam", "/app/satpam/tamu", "/app/satpam/cctv", "/app/satpam/patroli"]],
    ["partner", "/app/mitra", ["Beranda", "Katalog", "Rujukan", "Komisi"],
      ["/app/mitra", "/app/mitra/katalog", "/app/mitra/rujukan", "/app/mitra/komisi"]],
  ])("%s: label dan tujuan sesuai", (variant, path, labels, hrefs) => {
    renderNav(variant, path);
    const links = screen.getAllByRole("link");
    expect(links.map((l) => l.textContent)).toEqual(labels);
    expect(links.map((l) => l.getAttribute("href"))).toEqual(hrefs);
  });
});
