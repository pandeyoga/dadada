import React from "react";
import { render, screen } from "@testing-library/react";
import "@testing-library/jest-dom";

import QuotationBreakdown from "./QuotationBreakdown";

jest.mock("@/components/patterns/StatusPill", () => () => <span>pill</span>);
jest.mock("@/components/patterns/MoneyText", () => ({ value }) => <span>{String(value)}</span>);
jest.mock("@/utils/formatters", () => ({ formatDateWIB: (d) => d }));
jest.mock("@/constants/testIds", () => ({ QUOTE: { breakdown: "quotation-breakdown", kprBox: "quotation-kpr-box" } }));

const calc = {
  base_price: 650000000, gross_price: 650000000, net_price: 650000000,
  addons: [], discount_lines: [], terms: [{ id: "t1", label: "DP", due_date: "2026-01-01", amount: 65000000 }],
  scheme: { name: "KPR" }, kpr: { state: "missing_data", missing: ["tenor_bulan"] },
  taxes: { ppn: 78000000, ppn_rate: 12, bphtb: 28500000, bphtb_rate: 5 },
};

test("tidak ada sisa ekspresi JSX (') : null}') yang bocor ke layar", () => {
  const { container } = render(<QuotationBreakdown calc={calc} />);
  expect(container.textContent).not.toContain(") : null}");
  expect(container.textContent).not.toContain("{");
  expect(screen.getByTestId("quotation-tax-note")).toBeInTheDocument();
});

test("hideKpr menyembunyikan kotak KPR tetapi catatan pajak tetap tampil", () => {
  render(<QuotationBreakdown calc={calc} hideKpr />);
  expect(screen.queryByTestId("quotation-kpr-box")).toBeNull();
  expect(screen.getByTestId("quotation-tax-note")).toBeInTheDocument();
});

test("tanpa data pajak → catatan pajak tidak dirender, calc null → kosong", () => {
  const { container, rerender } = render(<QuotationBreakdown calc={{ ...calc, taxes: {} }} />);
  expect(screen.queryByTestId("quotation-tax-note")).toBeNull();
  rerender(<QuotationBreakdown calc={null} />);
  expect(container.textContent).toBe("");
});

// W2-A: catatan pajak mengikuti mode PPN proyek (bawaan = teks lama "di luar harga").
test("mode PPN: eksklusif (bawaan) = di luar harga; inklusif = sudah termasuk harga; bebas = PPN bebas 0%", () => {
  const note = (taxes) => {
    const { container, unmount } = render(<QuotationBreakdown calc={{ ...calc, taxes }} />);
    const t = screen.getByTestId("quotation-tax-note").textContent;
    expect(container.textContent).not.toContain("{");
    unmount();
    return t;
  };
  const lama = note({ ppn: 78000000, ppn_rate: 12, bphtb: 1, bphtb_rate: 5 });
  expect(lama).toContain("(di luar harga): PPN 12% 78000000");
  expect(note({ ppn: 78000000, ppn_rate: 12, ppn_mode: "eksklusif", bphtb: 1, bphtb_rate: 5 })).toBe(lama);
  const inkl = note({ ppn: 69642857, ppn_rate: 12, ppn_mode: "inklusif", bphtb: 1, bphtb_rate: 5 });
  expect(inkl).toContain("PPN 12% 69642857 (sudah termasuk dalam harga)");
  expect(inkl).not.toContain("di luar harga");
  expect(note({ ppn: 0, ppn_rate: 0, ppn_mode: "bebas_ppn", bphtb: 1, bphtb_rate: 5 })).toContain("PPN bebas (0%)");
});
