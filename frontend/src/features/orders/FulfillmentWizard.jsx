/**
 * FulfillmentWizard (FASE R7) — matriks skenario S1–S8 menjadi aksi terpandu.
 * Analisis per item SO: stok sendiri / stok entitas lain (interco) / pengadaan,
 * dengan aksi 1-klik: DRAFT Interco atau DRAFT PR. Wizard tidak memotong stok.
 */
import { useEffect, useState } from "react";
import { X, Wand2, PackageCheck, ArrowLeftRight, ShoppingCart, ChevronRight } from "lucide-react";
import axios, { API } from "../../services/apiClient";

const REC_STYLE = {
  alokasi_stok: ["#1B7F4B", "#E6F6EC", "Stok Sendiri", PackageCheck],
  interco: ["#6B219A", "#F3E9FA", "Beli Antar-PT", ArrowLeftRight],
  pengadaan: ["#B23B14", "#FDEDE7", "Pengadaan Baru", ShoppingCart],
};

export default function FulfillmentWizard({ orderId, onClose }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState([]);

  const load = () => {
    axios.get(`${API}/fulfillment/wizard/${orderId}`)
      .then((r) => setData(r.data))
      .catch((e) => setError(e.response?.data?.detail || e.message));
  };
  useEffect(() => { load(); }, [orderId]); // eslint-disable-line

  const createInterco = async (draft) => {
    setBusy(true); setError("");
    try {
      const r = await axios.post(`${API}/fulfillment/wizard/${orderId}/create-interco`, {
        seller_entity_id: draft.seller_entity_id, items: draft.items,
      });
      const num = r.data.buyer?.number || r.data.seller?.number || r.data.pair_id || "";
      setDone((d) => [...d, `Draft Interco ${num} dibuat (${draft.seller_entity_name} → ${data.so.entity_name}). Lanjutkan di menu Antar Entitas.`]);
    } catch (e) { setError(e.response?.data?.detail || "Gagal membuat interco"); } finally { setBusy(false); }
  };

  const createPR = async () => {
    setBusy(true); setError("");
    try {
      const r = await axios.post(`${API}/fulfillment/wizard/${orderId}/create-pr`, {
        items: data.procurement_items.map((i) => ({ product_id: i.product_id, quantity: i.quantity })),
      });
      setDone((d) => [...d, `Draft PR ${r.data.number} dibuat — approve → PO, lalu terima di Gudang Transit dengan routing CROSS-DOCK.`]);
    } catch (e) { setError(e.response?.data?.detail || "Gagal membuat PR"); } finally { setBusy(false); }
  };

  return (
    <div className="fixed inset-0 z-[120] flex items-center justify-center bg-black/40 p-4"
      data-testid="fulfillment-wizard" onClick={onClose}>
      <div className="max-h-[88vh] w-full max-w-2xl overflow-y-auto rounded-xl bg-white p-4 shadow-2xl"
        onClick={(e) => e.stopPropagation()}>
        <div className="mb-2 flex items-center justify-between">
          <p className="flex items-center gap-1.5 text-[13px] font-bold">
            <Wand2 size={15} className="text-[#6B219A]" /> Wizard Pemenuhan {data?.so?.number || ""}
            {data && <span className="rounded bg-[#F5F5F7] px-1.5 py-0.5 text-[10px] font-bold text-[#6B6B73]">{data.so.entity_name}</span>}
          </p>
          <button data-testid="wizard-close" className="icon-button" onClick={onClose}><X size={15} /></button>
        </div>
        {error && <p data-testid="wizard-error" className="mb-2 rounded bg-[#FBE9E7] px-2 py-1.5 text-[11.5px] font-semibold text-[#C0341D]">{error}</p>}
        {done.map((m, i) => <p key={i} data-testid={`wizard-done-${i}`} className="mb-1.5 rounded bg-[#E7F7EC] px-2 py-1.5 text-[11.5px] font-semibold text-[#1B7E3B]">✓ {m}</p>)}
        {!data && !error && <div className="h-32 animate-pulse rounded bg-[#F5F5F7]" />}

        {data && (
          <div className="space-y-2.5">
            {data.items.length === 0 && (
              <p data-testid="wizard-empty" className="rounded-lg bg-[#FFF4E5] px-3 py-2 text-[12px] font-semibold text-[#8C4A00]">
                SO ini tidak punya baris item aktif (mis. menunggu stok / backorder) — tidak ada yang bisa dianalisis wizard.
              </p>
            )}
            {data.items.map((it, ii) => {
              const [color, bg, recLabel, Icon] = REC_STYLE[it.recommendation] || REC_STYLE.alokasi_stok;
              return (
                <div key={ii} data-testid={`wizard-item-${ii}`} className="rounded-lg border border-[#EFF0F2] p-2.5">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="min-w-0 flex-1">
                      <span className="block text-[12.5px] font-bold">{it.sku} · {it.product_name}</span>
                      <span className="block text-[11px] text-[#6B6B73]">
                        Butuh <b>{it.qty_needed} {it.unit}</b> · stok sendiri {it.own_available}
                        {it.other_entities.map((o) => ` · ${o.entity_name}: ${o.available_qty}${o.contract ? " (kontrak ✓)" : ""}`).join("")}
                      </span>
                    </span>
                    <span className="flex items-center gap-1 rounded-full px-2.5 py-1 text-[10.5px] font-bold"
                      style={{ color, background: bg }} data-testid={`wizard-rec-${ii}`}>
                      <Icon size={11} /> {recLabel} · {it.scenario}
                    </span>
                  </div>
                  <p className="mt-1 text-[11.5px] font-semibold" style={{ color }}>{it.label}</p>
                  <ol className="mt-1 space-y-0.5">
                    {it.steps.map((s, si) => (
                      <li key={si} className="flex items-start gap-1 text-[11px] text-[#6B6B73]">
                        <ChevronRight size={11} className="mt-0.5 shrink-0" style={{ color }} /> {s}
                      </li>
                    ))}
                  </ol>
                </div>
              );
            })}

            {(data.interco_drafts.length > 0 || data.procurement_items.length > 0) && (
              <div className="rounded-lg bg-[#FAFBFC] p-2.5" data-testid="wizard-actions">
                <p className="mb-1.5 text-[11px] font-bold uppercase tracking-wide text-[#6B6B73]">Aksi 1-Klik (dokumen DRAF — tidak memotong stok)</p>
                <div className="flex flex-wrap gap-1.5">
                  {data.interco_drafts.map((d, di) => (
                    <button key={di} data-testid={`wizard-create-interco-${di}`} disabled={busy}
                      onClick={() => createInterco(d)}
                      className="flex items-center gap-1 rounded-lg bg-[#6B219A] px-3 py-1.5 text-[11.5px] font-semibold text-white disabled:opacity-40">
                      <ArrowLeftRight size={12} /> Buat Draf Interco dari {d.seller_entity_name} ({d.items.length} item)
                    </button>
                  ))}
                  {data.procurement_items.length > 0 && (
                    <button data-testid="wizard-create-pr" disabled={busy} onClick={createPR}
                      className="flex items-center gap-1 rounded-lg bg-[#B23B14] px-3 py-1.5 text-[11.5px] font-semibold text-white disabled:opacity-40">
                      <ShoppingCart size={12} /> Buat Draft PR ({data.procurement_items.length} item, saran CROSS-DOCK)
                    </button>
                  )}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
