import "@testing-library/jest-dom";
import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import AiActionCard from "../AiActionCard";
import * as aiApi from "../aiApi";

jest.mock("../aiApi", () => ({
  approveAction: jest.fn(),
  rejectAction: jest.fn(),
  friendlyError: () => "galat",
}));

test("Setujui dipanggil sekali walau diklik dua kali cepat", async () => {
  let resolve;
  aiApi.approveAction.mockReturnValue(new Promise((r) => { resolve = r; }));
  const action = { id: "a1", status: "pending", preview: { changes: ["Ubah tahap Budi"], checks: [{ ok: true, label: "Bukti lengkap" }] } };
  render(<AiActionCard action={action} />);
  const btn = screen.getByTestId("ai-approve");
  fireEvent.click(btn);
  fireEvent.click(btn);
  expect(aiApi.approveAction).toHaveBeenCalledTimes(1);
  resolve({ status: "executed" });
  await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent(/Sudah dijalankan/));
  expect(aiApi.approveAction).toHaveBeenCalledTimes(1);
});
