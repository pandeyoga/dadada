import "@testing-library/jest-dom";
import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { createSseParser, applyPortalEvent } from "../portalAiStream";
import PortalAiConfirmCard from "../PortalAiConfirmCard";
import PortalAiPanel from "../PortalAiPanel";
import * as api from "../portalAiApi";

jest.mock("../portalAiApi", () => ({
  getStatus: jest.fn(), ackNotice: jest.fn(), stopAssistant: jest.fn(), resumeAssistant: jest.fn(),
  listConversations: jest.fn(), createConversation: jest.fn(), getConversation: jest.fn(),
  deleteAllConversations: jest.fn(), confirmAction: jest.fn(), cancelAction: jest.fn(),
  portalAiError: () => "galat",
}));
jest.mock("../portalAiStream", () => ({
  ...jest.requireActual("../portalAiStream"),
  streamPortalMessage: jest.fn(),
}));

test("parser SSE menyambung potongan terputus dan membaca event handoff", () => {
  const got = [];
  const p = createSseParser((e) => got.push(e));
  const full = 'data: {"type":"text_delta","text":"Halo"}\n\ndata: {"type":"handoff","ticket":{"id":"T1","subject":"CS-1","due_at":"2026-01-01T10:00:00Z"}}\n\n';
  p.push(full.slice(0, 15));
  p.push(full.slice(15, 70));
  p.push(full.slice(70));
  expect(got).toHaveLength(2);
  const m = got.reduce(applyPortalEvent, { role: "assistant", text: "" });
  expect(m.text).toBe("Halo");
  expect(m.ticket.id).toBe("T1");
});

test("kartu konfirmasi memanggil confirm sekali walau diklik dua kali", async () => {
  let resolve;
  api.confirmAction.mockReturnValue(new Promise((r) => { resolve = r; }));
  render(<PortalAiConfirmCard action={{ id: "ac1", status: "pending", payload: { json: { subjek: "Bocor" } } }} />);
  const btn = screen.getByTestId("portal-ai-confirm-send");
  fireEvent.click(btn);
  fireEvent.click(btn);
  resolve({ action: { id: "ac1", status: "executed" } });
  await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("Sudah dikirim"));
  expect(api.confirmAction).toHaveBeenCalledTimes(1);
});

test("panel berkata Asisten belum tersedia saat enabled false", async () => {
  api.getStatus.mockResolvedValue({ enabled: false });
  render(<PortalAiPanel onClose={() => {}} />);
  expect(await screen.findByText("Asisten belum tersedia")).toBeInTheDocument();
});

test("panel menampilkan pemberitahuan pada pembukaan pertama dan menutupnya dengan Mengerti", async () => {
  api.getStatus.mockResolvedValue({
    enabled: true, effective_mode: "live", noticed: false, stopped: false,
    quota: { used: 2, limit: 30 }, notice_text: "Ini asisten AI.",
  });
  api.listConversations.mockResolvedValue([]);
  api.ackNotice.mockResolvedValue({});
  render(<PortalAiPanel onClose={() => {}} />);
  expect(await screen.findByTestId("portal-ai-notice")).toHaveTextContent("Ini asisten AI.");
  fireEvent.click(screen.getByText("Mengerti"));
  await waitFor(() => expect(screen.getByTestId("portal-ai-input")).toBeInTheDocument());
  expect(api.ackNotice).toHaveBeenCalledTimes(1);
  expect(screen.getByTestId("portal-ai-quota")).toHaveTextContent("Sisa 28/30");
});

test("kartu konfirmasi membaca bentuk backend (preview.title/changes, summary saat executed)", async () => {
  api.confirmAction.mockResolvedValue({ action: { id: "ac2", status: "executed" } });
  render(<PortalAiConfirmCard action={{
    id: "ac2", status: "pending", summary: "Kirim komplain ini?",
    preview: { title: "Kirim komplain ini?", changes: ["Subjek: Atap bocor", "Pesan: bocor di kamar"] },
  }} />);
  expect(screen.getByText("Kirim komplain ini?")).toBeInTheDocument();
  expect(screen.getByText("Subjek: Atap bocor")).toBeInTheDocument();
  fireEvent.click(screen.getByTestId("portal-ai-confirm-send"));
  await waitFor(() => expect(screen.getByRole("status")).toBeInTheDocument());
});

test("tombol Bicara dengan CS mengirim teks pendek yang memicu serah deterministik", async () => {
  api.getStatus.mockResolvedValue({ enabled: true, effective_mode: "live", noticed: true, stopped: false, quota: { used: 0, limit: 30 } });
  api.listConversations.mockResolvedValue([]);
  api.createConversation.mockResolvedValue({ id: "c1" });
  const { streamPortalMessage } = require("../portalAiStream");
  streamPortalMessage.mockResolvedValue(undefined);
  render(<PortalAiPanel onClose={() => {}} />);
  fireEvent.click(await screen.findByText("Bicara dengan CS"));
  await waitFor(() => expect(streamPortalMessage).toHaveBeenCalledWith("c1", "Bicara dengan CS", expect.anything()));
});
