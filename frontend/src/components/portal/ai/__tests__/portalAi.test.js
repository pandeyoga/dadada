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

test("panel berkata Asisten belum tersedia saat enabled false, tanpa teks pemberitahuan privasi", async () => {
  api.getStatus.mockResolvedValue({
    enabled: false, noticed: false, stopped: false,
    notice_text: "Anda sedang berbicara dengan Tanya Estora. Tekan Bicara dengan CS kapan saja.",
  });
  render(<PortalAiPanel onClose={() => {}} />);
  expect(await screen.findByText("Asisten belum tersedia")).toBeInTheDocument();
  expect(screen.getByText("Silakan hubungi CS kami lewat tab Komplain.")).toBeInTheDocument();
  expect(screen.queryByText(/Anda sedang berbicara dengan Tanya Estora/)).not.toBeInTheDocument();
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
  api.confirmAction.mockResolvedValue({ action: { id: "ac2", status: "executed",
    summary: "Klaim KG-1 tercatat namun DITOLAK: masa garansi habis." } });
  render(<PortalAiConfirmCard action={{
    id: "ac2", status: "pending", summary: "Kirim komplain ini?",
    preview: { title: "Kirim komplain ini?", changes: ["Subjek: Atap bocor", "Pesan: bocor di kamar"] },
  }} />);
  expect(screen.getByText("Kirim komplain ini?")).toBeInTheDocument();
  expect(screen.getByText("Subjek: Atap bocor")).toBeInTheDocument();
  fireEvent.click(screen.getByTestId("portal-ai-confirm-send"));
  await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("tercatat namun DITOLAK"));
});

test("event done tidak mengganti kunci pesan: kartu yang sudah dikirim tidak muncul lagi dengan Kirim/Batal", async () => {
  const m = applyPortalEvent({ id: "a-1", role: "assistant", text: "" }, { type: "done", message_id: "srv-9" });
  expect(m.id).toBe("a-1");
  expect(m.messageId).toBe("srv-9");
  api.getStatus.mockResolvedValue({ enabled: true, effective_mode: "live", noticed: true, stopped: false, quota: { used: 0, limit: 30 } });
  api.listConversations.mockResolvedValue([]);
  api.createConversation.mockResolvedValue({ id: "c2" });
  api.confirmAction.mockResolvedValue({ action: { id: "ac3", status: "executed", summary: "Komplain terkirim: Atap bocor." } });
  const { streamPortalMessage } = require("../portalAiStream");
  let finish;
  streamPortalMessage.mockImplementation((_id, _t, { onEvent }) => {
    onEvent({ type: "action_proposed", action: { id: "ac3", status: "pending", preview: { title: "Kirim komplain ini?", changes: [] } } });
    return new Promise((r) => { finish = () => { onEvent({ type: "done", message_id: "srv-1" }); r(); }; });
  });
  render(<PortalAiPanel onClose={() => {}} />);
  fireEvent.change(await screen.findByTestId("portal-ai-input"), { target: { value: "Atap bocor" } });
  fireEvent.click(screen.getByLabelText("Kirim pesan"));
  fireEvent.click(await screen.findByTestId("portal-ai-confirm-send"));
  await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("Komplain terkirim"));
  finish();
  await waitFor(() => expect(screen.getByLabelText("Kirim pesan")).toBeInTheDocument());
  expect(screen.queryByTestId("portal-ai-confirm-send")).not.toBeInTheDocument();
  expect(screen.getByRole("status")).toHaveTextContent("Komplain terkirim");
  expect(api.confirmAction).toHaveBeenCalledTimes(1);
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
