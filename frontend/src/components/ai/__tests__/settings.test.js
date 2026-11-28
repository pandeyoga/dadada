import "@testing-library/jest-dom";
import React from "react";
import { render, screen } from "@testing-library/react";
import AutonomyTable from "../settings/AutonomyTable";
import ApiKeyCard from "../settings/ApiKeyCard";

jest.mock("../aiApi", () => ({
  setCategoryMode: jest.fn(), saveApiKey: jest.fn(), testConnection: jest.fn(), saveSettings: jest.fn(),
  friendlyError: () => "galat",
}));

test("Otomatis nonaktif dan alasan tampil bila can_enable_auto false", () => {
  const cats = [{
    key: "kpr", label: "Simulasi KPR", accuracy: 0.931, samples: 40, mode: "draft",
    canAuto: false, reason: "sampel kurang (40 dari 50)", locked: false,
  }];
  render(<AutonomyTable categories={cats} threshold={0.95} onThreshold={() => {}} />);
  const row = screen.getByTestId("cat-kpr");
  expect(row.querySelector('input[value="auto"]')).toBeDisabled();
  expect(row.querySelector('input[value="draft"]')).not.toBeDisabled();
  expect(screen.getByTestId("reason-kpr")).toHaveTextContent("sampel kurang (40 dari 50)");
});

test("kunci API tidak pernah tampil utuh", () => {
  const { container } = render(<ApiKeyCard settings={{ has_key: true, key_last4: "9XyZ", key: "sk-ant-RAHASIA-9XyZ", effective_mode: "live" }} />);
  expect(container.textContent).toContain("9XyZ");
  expect(container.textContent).not.toContain("sk-ant-RAHASIA");
  expect(container.innerHTML).not.toContain("sk-ant-RAHASIA");
});
