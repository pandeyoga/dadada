/** SpecialOrderChainPanel — lini masa fase OD + rantai dokumen (OD ↔ Permintaan Desain ↔ Sample ↔ SKU ↔ PR ↔ SO) + referensi pelanggan. */
import { useState } from "react";
import { CheckCircle2, Circle, ExternalLink, Image as ImageIcon, Send, Upload } from "lucide-react";
import axios, { API } from "../../services/apiClient";
import ProductColorChip from "../../components/ProductColorChip";
import { useProofBlob } from "../rnd/ProofImage";
import { openRnd } from "../rnd/rndDeepLink";
import { SAMPLE_STATUS_META } from "../rnd/rndMeta";

const TYPE_LABEL = { printing: "Kain printing", labdip: "Warna khusus (labdip)", handfeel: "Handfeel", proofing: "Proofing" };

export default function SpecialOrderChainPanel({ order, canEdit, onChanged }) {
  const ch = order.chain || {};
  const phases = ch.phases || [];
  const idx = Math.max(0, phases.findIndex(([k]) => k === ch.phase));
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const routed = !!(order.design_request_id || (order.sample_ids || []).length);
  const approved = !["draft", "pending_approval", "cancelled"].includes(order.status);

  const upload = async (files) => {
    setBusy(true); setMsg("");
    try {
      for (const file of files) { const fd = new FormData(); fd.append("file", file); await axios.post(`${API}/special-orders/${order.id}/references`, fd); }
      setMsg(`${files.length} referensi terunggah.`); onChanged?.();
    } catch (e) { setMsg(e.response?.data?.detail || "Unggah gagal."); } finally { setBusy(false); }
  };
  const route = async () => {
    setBusy(true); setMsg("");
    try { await axios.post(`${API}/special-orders/${order.id}/route`); setMsg("Diteruskan ke Desainer / R&D."); onChanged?.(); }
    catch (e) { setMsg(e.response?.data?.detail || "Gagal meneruskan."); } finally { setBusy(false); }
  };

  return (
    <div className="grid gap-3" data-testid="od-chain-panel">
      <section className="section-card !p-3">
        <p className="mb-2 text-[10.5px] font-bold uppercase tracking-wide text-[#8E8E93]">Lini masa pesanan khusus</p>
        <ol className="flex flex-wrap items-center gap-1" data-testid="od-phases">
          {phases.map(([k, label], i) => (
            <li key={k} className={`flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10.5px] ${i < idx ? "border-[#CDE9D6] bg-[#EAF7EF] text-[#1A7A3A]" : i === idx ? "border-[#0058CC] bg-[#0058CC] font-bold text-white" : "border-[#EFF0F2] text-[#9A9BA3]"}`}
              data-testid={`od-phase-${k}`}>
              {i < idx ? <CheckCircle2 size={10} /> : <Circle size={10} />} {label}
            </li>
          ))}
        </ol>
        <p className="mt-2 text-[11px] text-[#6B6B73]">
          Tipe permintaan: <b>{(order.request_types || []).map((t) => TYPE_LABEL[t] || t).join(", ") || "—"}</b> · detail: <b>{order.detail_level === "full" ? "spesifikasi lengkap" : "hanya referensi"}</b>
          {order.reference_notes ? <> · {order.reference_notes}</> : null}
        </p>
        {order.spec && Object.values(order.spec).some(Boolean) && (
          <p className="mt-1 text-[11px] text-[#3C3C43]" data-testid="od-spec-summary">
            Spesifikasi: {[order.spec.fabric_type, order.spec.gramasi && `${order.spec.gramasi} gsm`, order.spec.lebar && `lebar ${order.spec.lebar} cm`, order.spec.sku_hint && `SKU ${order.spec.sku_hint}`, order.spec.color_new_note && `warna baru: ${order.spec.color_new_note}`].filter(Boolean).join(" · ") || "—"}
          </p>
        )}
      </section>

      <section className="section-card !p-3" data-testid="od-chain">
        <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
          <p className="text-[10.5px] font-bold uppercase tracking-wide text-[#8E8E93]">Rantai dokumen</p>
          {approved && !routed && canEdit && (
            <button className="primary-button !py-1 text-[11px]" disabled={busy} data-testid="od-route-button" onClick={route}><Send size={12} /> Teruskan ke Desainer / R&amp;D</button>
          )}
        </div>
        {(order.routing_errors || []).length > 0 && <p className="mb-2 text-[11px] text-[#C0392B]" data-testid="od-routing-errors">{order.routing_errors.join(" · ")}</p>}
        <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-4">
          <Node title="Permintaan desain" on={!!ch.design_request} testId="od-node-design">
            {ch.design_request ? <>
              <b className="font-mono">{ch.design_request.number}</b> · {ch.design_request.status}{ch.design_request.assigned_to_name ? ` · ${ch.design_request.assigned_to_name}` : ""}
              {ch.design && <span className="block">Desain <b className="font-mono">{ch.design.code}</b> · {ch.design.status}</span>}
            </> : (order.request_types || []).includes("printing") ? "lahir saat OD disetujui" : "tidak perlu (bukan printing)"}
          </Node>
          <Node title="Sample R&D" on={(ch.samples || []).length > 0} testId="od-node-samples">
            {(ch.samples || []).length === 0 ? ((order.request_types || []).includes("printing") ? "proofing dibuat MD setelah desain ACC" : "lahir saat OD disetujui") : ch.samples.map((s) => (
              <button key={s.id} type="button" className="block text-left hover:underline" data-testid={`od-sample-${s.id}`} onClick={() => openRnd({ view: "rnd-samples", sampleId: s.id, sampleNumber: s.number })}>
                <b className="font-mono">{s.number}</b> · {(SAMPLE_STATUS_META[s.status] || {}).label || s.status} · {(s.sample_types || []).join("+")}
                {s.decision?.supplier_name ? ` · pemenang ${s.decision.supplier_name}` : ""}{s.revision_of_sample_id ? " · revisi pelanggan" : ""} <ExternalLink size={9} className="inline text-[#0058CC]" />
              </button>
            ))}
          </Node>
          <Node title="SKU produk (eksklusif pelanggan ini)" on={(ch.products || []).length > 0} testId="od-node-products">
            {(ch.products || []).length === 0 ? "lahir saat sampling ACC" : ch.products.map((p) => (
              <span key={p.id} className="block"><b className="font-mono">{p.sku}</b> {p.name} <ProductColorChip product={p} compact />{p.exclusive_customer_name ? <span className="ml-1 rounded-full bg-[#B45309] px-1.5 py-px text-[9.5px] font-bold text-white" data-testid={`od-product-exclusive-${p.id}`}>Eksklusif: {p.exclusive_customer_name}</span> : null}</span>
            ))}
          </Node>
          <Node title="PR / PO → SO" on={!!ch.pr || !!ch.so || (ch.po || []).length > 0} testId="od-node-purchasing">
            {ch.pr ? <span className="block">PR <b className="font-mono">{ch.pr.number}</b> · {ch.pr.status}</span> : <span className="block">PR belum dibuat</span>}
            {(ch.po || []).map((p) => <span key={p.id} className="block" data-testid={`od-po-${p.id}`}>PO <b className="font-mono">{p.po_number}</b> · {p.supplier_name} · {p.status}</span>)}
            {ch.so ? <span className="block">SO <b className="font-mono">{ch.so.order_number || ch.so.number}</b> · {ch.so.status}</span> : <span className="block">SO belum dikonversi</span>}
          </Node>
        </div>
      </section>

      <section className="section-card !p-3" data-testid="od-references">
        <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
          <p className="text-[10.5px] font-bold uppercase tracking-wide text-[#8E8E93]">Referensi pelanggan · {(order.references || []).length}</p>
          {canEdit && (
            <label className="secondary-button cursor-pointer !py-1 text-[11px]" data-testid="od-reference-upload-label">
              <Upload size={12} /> Unggah foto / pattern / swatch
              <input type="file" accept="image/*,.pdf" multiple className="hidden" data-testid="od-reference-upload" onChange={(e) => { const fs = Array.from(e.target.files || []); if (fs.length) upload(fs); e.target.value = ""; }} />
            </label>
          )}
        </div>
        {msg && <p className="mb-2 text-[11px] text-[#0058CC]" data-testid="od-reference-msg">{msg}</p>}
        {(order.references || []).length === 0 ? (
          <p className="flex items-center justify-center gap-1 rounded-lg border border-dashed border-[#D9D9DE] py-5 text-[11px] text-[#9A9BA3]"><ImageIcon size={14} /> belum ada referensi — unggah foto swatch / pattern dari pelanggan</p>
        ) : (
          <div className="grid grid-cols-3 gap-2 sm:grid-cols-5 lg:grid-cols-8">
            {order.references.map((r) => <RefThumb key={r.id} url={`${API}/special-orders/${order.id}/references/${r.id}`} meta={r} />)}
          </div>
        )}
      </section>
    </div>
  );
}

function Node({ title, on, children, testId }) {
  return (
    <div className={`rounded-lg border p-2.5 text-[11.5px] ${on ? "border-[#CDE9D6] bg-[#F4FCF6]" : "border-[#EFF0F2] bg-white"}`} data-testid={testId}>
      <p className="mb-1 flex items-center gap-1 text-[10px] font-bold uppercase tracking-wide text-[#6B6B73]">{on ? <CheckCircle2 size={11} className="text-[#1A7A3A]" /> : <Circle size={11} className="text-[#C7C9CF]" />} {title}</p>
      <div className={on ? "text-[#1C1C1E]" : "text-[#9A9BA3]"}>{children}</div>
    </div>
  );
}

function RefThumb({ url, meta }) {
  const { src, status } = useProofBlob(url, meta.content_type?.startsWith("image/"));
  return (
    <a href={url} target="_blank" rel="noreferrer" className="block overflow-hidden rounded-lg border border-[#E5E5EA] bg-[#F5F5F7]" title={meta.caption || meta.filename} data-testid={`od-reference-${meta.id}`}>
      <div className="flex aspect-square items-center justify-center">{status === "ok" && src ? <img src={src} alt={meta.filename} className="h-full w-full object-cover" /> : <ImageIcon size={16} className="text-[#B5B5BC]" />}</div>
      <p className="truncate px-1.5 py-1 text-[9.5px] font-semibold">{meta.caption || meta.filename}</p>
    </a>
  );
}
