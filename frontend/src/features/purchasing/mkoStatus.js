/**
 * Konstanta status Order Makloon (MKO) — file terpisah supaya
 * MakloonOrdersView ⇄ MakloonOrderDetailPanel tidak saling impor (impor melingkar
 * = TDZ "Cannot access X before initialization" di bundle produksi).
 */
export const MKO_STATUS = {
  draft: { label: "Draf", cls: "pill-muted" },
  in_process: { label: "Diproses", cls: "pill-info" },
  partially_received: { label: "Sebagian", cls: "pill-warning" },
  completed: { label: "Selesai", cls: "pill-success" },
  cancelled: { label: "Batal", cls: "pill-danger" },
};
