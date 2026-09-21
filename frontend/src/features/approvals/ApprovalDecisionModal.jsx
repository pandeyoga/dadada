/**
 * ApprovalDecisionModal — "KEPUTUSAN DI TEMPAT" untuk Pusat Persetujuan (2026-06).
 *
 * Sebelum ini setiap baris hanya punya "Tinjau & Putuskan" yang MEMINDAHKAN layar;
 * pemutus kehilangan konteks daftar dan harus mencari dokumennya lagi. Pop-up ini
 * membawa DETAIL dokumen (diambil dari endpoint detail per jenis) + tombol
 * Setujui / Tolak beserta catatan/alasan — tanpa pindah layar. "Buka layar penuh"
 * tetap tersedia untuk kasus yang butuh konteks lebih dalam (mis. inspeksi retur).
 *
 * Wewenang tetap milik SERVER: tombol hanya tampil bila matriks izin peran ini
 * memuat aksinya, dan endpoint tujuan tetap memeriksa sendiri (SoD, ambang, status).
 */
import { useEffect, useState } from "react";
import ErrorNotice from "../../components/ErrorNotice";
import axios, { API } from "../../services/apiClient";
import { ArrowRight, Check, Clock, ExternalLink, Loader2, X } from "lucide-react";
import { formatCurrency } from "../../utils/formatters";
import { apiErrorText } from "../../utils/apiError";
import { can } from "../../config/roles";
import { overlayDismiss } from "@/utils/overlayDismiss";
import { useEscapeClose } from "@/utils/escapeLayers";

const fmtN = (v) => new Intl.NumberFormat("id-ID").format(Number(v || 0));

// jenis → izin yang membolehkan tombol keputusan tampil (server tetap penjaga akhir)
const CAN_DECIDE = {
  so: ["order", "approve"],
  po: ["purchase_order", "approve"],
  price: ["price_approval", "approve"],
  sales_return: ["sales_return", "approve"],
  purchase_return: ["purchase_return", "approve"],
  cycle: ["inventory", "approve_count"],
  amendment: ["finance_amendment", "approve"],
};

const kindOf = (it) => (it.isSO ? "so" : it.kind);

function detailUrl(it) {
  if (it.isSO) return `/sales-orders/${it.orderId}`;
  return {
    po: `/purchase-orders/${it.id}`,
    price: `/price-approvals/${it.id}`,
    sales_return: `/sales-returns/${it.id}`,
    purchase_return: `/purchase-returns/${it.id}`,
    cycle: `/cycle-count/sessions/${it.id}`,
    amendment: `/amendments/${it.id}`,
  }[it.kind];
}

async function submitDecision(it, decision, notes) {
  const k = kindOf(it);
  if (k === "so")
    return axios.post(`${API}/sales-orders/${it.orderId}/approvals/${it.id}/decide`,
      { decision, notes });
  if (k === "po")
    return axios.post(`${API}/purchase-orders/${it.id}/${decision === "approve" ? "approve" : "reject"}`);
  if (k === "cycle")
    return axios.post(`${API}/cycle-count/sessions/${it.id}/${decision}`,
      { reason: notes || (decision === "approve" ? "Disetujui sesuai hasil cycle count" : "") });
  if (k === "amendment")
    return axios.post(`${API}/amendments/${it.id}/decision`, { action: decision, note: notes || "" });
  const base = { price: "price-approvals", sales_return: "sales-returns",
                 purchase_return: "purchase-returns" }[k];
  return axios.post(`${API}/${base}/${it.id}/${decision === "approve" ? "approve" : "reject"}`, { notes });
}

function Info({ label, children, testId }) {
  return (
    <div data-testid={testId} className="min-w-0">
      <p className="text-[10px] font-bold uppercase tracking-wide text-[#8E8E93]">{label}</p>
      <div className="mt-0.5 text-[12px] font-semibold text-[#1C1C1E]">{children ?? "—"}</div>
    </div>
  );
}

function MiniTable({ cols, rows, testId, max = 8 }) {
  if (!rows?.length) return null;
  return (
    <div className="overflow-x-auto rounded-lg border border-[#EFF0F2]" data-testid={testId}>
      <table className="w-full text-[11.5px]">
        <thead>
          <tr className="bg-[#FAFBFC] text-left text-[10px] font-bold uppercase tracking-wide text-[#8E8E93]">
            {cols.map((c) => (
              <th key={c.h} className={`px-2.5 py-1.5 ${c.right ? "text-right" : ""}`}>{c.h}</th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-[#F4F5F7]">
          {rows.slice(0, max).map((r, i) => (
            <tr key={i}>
              {cols.map((c) => (
                <td key={c.h} className={`px-2.5 py-1.5 ${c.right ? "text-right tabular-nums" : ""}`}>
                  {c.render(r)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {rows.length > max && (
        <p className="border-t border-[#EFF0F2] bg-[#FAFBFC] px-2.5 py-1 text-[10.5px] text-[#8E8E93]">
          +{rows.length - max} baris lagi — lihat selengkapnya di layar penuh.
        </p>
      )}
    </div>
  );
}

/** Isi detail per jenis — informasi yang dibutuhkan untuk MEMUTUSKAN, bukan seluruh dokumen. */
function DetailBody({ item, doc }) {
  const k = kindOf(item);
  const qty = (r) => `${fmtN(r.qty ?? r.qty_ordered ?? r.quantity ?? r.quantity_returned ?? 0)} ${r.unit || ""}`;

  if (k === "so") {
    const entry = (doc?.pending_approvals || []).find((p) => p.id === item.id) || {};
    return (
      <>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Info label="Pelanggan">{doc?.customer_name}</Info>
          <Info label="Total Pesanan">{formatCurrency(doc?.grand_total)}</Info>
          <Info label="Status SO">{doc?.status}</Info>
          <Info label="Pembayaran">{doc?.payment_terms || doc?.payment_status || "—"}</Info>
        </div>
        {entry.type === "special_price" && (
          <div className="rounded-lg border border-[#F5E0C3] bg-[#FDF6EC] px-3 py-2 text-[12px]">
            <b>{entry.product_name || "Item"}</b> · harga normal{" "}
            <b>{formatCurrency(entry.normal_price)}</b> → diminta{" "}
            <b className="text-[#B45309]">{formatCurrency(entry.requested_price ?? entry.amount)}</b>
          </div>
        )}
        {entry.reason && (
          <p className="text-[12px] text-[#3C3C43]"><b>Alasan pengajuan:</b> {entry.reason}</p>
        )}
        <MiniTable testId="decision-items" rows={doc?.items || []} cols={[
          { h: "Item", render: (r) => r.product_name || r.name || "—" },
          { h: "Qty", right: true, render: qty },
          { h: "Harga", right: true, render: (r) => formatCurrency(r.price ?? r.unit_price) },
          { h: "Subtotal", right: true,
            render: (r) => formatCurrency(r.line_total ?? r.subtotal ?? (Number(r.qty || r.quantity || 0) * Number(r.price ?? r.unit_price ?? 0))) },
        ]} />
      </>
    );
  }

  if (k === "po") {
    return (
      <>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Info label="Supplier">{doc?.supplier_name}</Info>
          <Info label="Gudang Tujuan">{doc?.warehouse_name}</Info>
          <Info label="Total PO">{formatCurrency(doc?.total_amount)}</Info>
          <Info label="Termin">{doc?.payment_terms || "—"}</Info>
        </div>
        {doc?.notes && <p className="text-[12px] text-[#3C3C43]"><b>Catatan:</b> {doc.notes}</p>}
        <MiniTable testId="decision-items" rows={doc?.items || []} cols={[
          { h: "Item", render: (r) => r.product_name || r.name || "—" },
          { h: "Qty", right: true, render: qty },
          { h: "Harga", right: true, render: (r) => formatCurrency(r.unit_price ?? r.price) },
          { h: "Subtotal", right: true,
            render: (r) => formatCurrency(r.subtotal ?? (Number(r.qty || 0) * Number(r.unit_price ?? r.price ?? 0))) },
        ]} />
      </>
    );
  }

  if (k === "price") {
    return (
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        <Info label="Produk">{doc?.product_name || doc?.sku}</Info>
        <Info label="Pelanggan">{doc?.customer_name}</Info>
        <Info label="Diskon">{doc?.discount_percent ? `${doc.discount_percent}%` : "—"}</Info>
        <Info label="Harga Normal">{formatCurrency(doc?.normal_price)}</Info>
        <Info label="Harga Diminta">
          <span className="text-[#B45309]">{formatCurrency(doc?.requested_price)}</span>
        </Info>
        <Info label="Alasan">{doc?.reason || doc?.notes || "—"}</Info>
      </div>
    );
  }

  if (k === "sales_return" || k === "purchase_return") {
    const isSell = k === "sales_return";
    return (
      <>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Info label={isSell ? "Pelanggan" : "Supplier"}>{doc?.customer_name || doc?.supplier_name}</Info>
          <Info label="Dokumen Sumber">{doc?.order_number || doc?.po_number || "—"}</Info>
          <Info label="Tipe">{doc?.return_type || "retur"}</Info>
          <Info label={isSell ? "Estimasi Nilai" : "Total"}>
            {formatCurrency(doc?.estimated_value ?? doc?.total_amount)}
            {isSell && <span className="ml-1 text-[10px] font-normal text-[#8E8E93]">(dari harga SO)</span>}
          </Info>
        </div>
        {doc?.notes && <p className="text-[12px] text-[#3C3C43]"><b>Catatan:</b> {doc.notes}</p>}
        <MiniTable testId="decision-items" rows={doc?.items || []} cols={[
          { h: "Item", render: (r) => r.product_name || r.product_id || "—" },
          { h: "Qty", right: true, render: qty },
          { h: "Kondisi", render: (r) => (r.condition === "ok" ? "Baik" : (r.condition ? "Rusak" : "—")) },
          { h: "Alasan", render: (r) => r.reason || "—" },
          ...(isSell ? [{ h: "Nilai", right: true, render: (r) => formatCurrency(r.line_total_est) }] : []),
        ]} />
      </>
    );
  }

  if (k === "cycle") {
    const disc = doc?.discrepancies || [];
    return (
      <>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          <Info label="Gudang">{doc?.warehouse_name}</Info>
          <Info label="Item Dihitung">{doc?.items?.length || 0}</Info>
          <Info label="Selisih Ditemukan">{disc.length}</Info>
        </div>
        <MiniTable testId="decision-items" rows={disc} cols={[
          { h: "Produk", render: (r) => r.product_name || r.product_id || "—" },
          { h: "Sistem", right: true, render: (r) => fmtN(r.system_qty) },
          { h: "Fisik", right: true, render: (r) => fmtN(r.counted_qty) },
          { h: "Selisih", right: true,
            render: (r) => (
              <span className={Number(r.difference) < 0 ? "text-[#C62828]" : "text-[#1B7F4B]"}>
                {Number(r.difference) > 0 ? "+" : ""}{fmtN(r.difference)}
              </span>
            ) },
        ]} />
        {disc.length === 0 && (
          <p className="text-[12px] text-[#1B7F4B]">Tidak ada selisih — stok fisik cocok dengan sistem.</p>
        )}
      </>
    );
  }

  if (k === "amendment") {
    const imp = doc?.impact || {};
    return (
      <>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Info label="Dokumen">{doc?.doc_number}</Info>
          <Info label="Alasan">{doc?.reason_label || doc?.reason}</Info>
          <Info label="Metode">{doc?.method_label || doc?.method}</Info>
          <Info label="Dampak Nilai">
            <span className={Number(imp.delta) < 0 ? "text-[#C62828]" : "text-[#1B7F4B]"}>
              {Number(imp.delta) > 0 ? "+" : ""}{formatCurrency(imp.delta)}
            </span>
          </Info>
        </div>
        {(imp.before != null || imp.after != null) && (
          <p className="text-[12px] text-[#3C3C43]">
            Nilai dokumen: <b>{formatCurrency(imp.before)}</b> → <b>{formatCurrency(imp.after)}</b>
          </p>
        )}
        {doc?.note && <p className="text-[12px] text-[#3C3C43]"><b>Catatan pengaju:</b> {doc.note}</p>}
      </>
    );
  }

  return null;
}

export default function ApprovalDecisionModal({ item, currentUser, onClose, onOpenFull, onDecided, meta, queuePos = null, queueTotal = 0 }) {
  const [doc, setDoc] = useState(null);
  const [loading, setLoading] = useState(true);
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState("");
  const [err, setErr] = useState("");
  useEscapeClose(true, onClose);

  const k = kindOf(item);
  const allowed = can(currentUser?.permissions, ...(CAN_DECIDE[k] || ["", ""]));
  const Icon = meta?.icon || Check;
  const accent = meta?.fg || "#0058CC";

  useEffect(() => {
    let on = true;
    (async () => {
      try {
        const res = await axios.get(`${API}${detailUrl(item)}`);
        if (on) setDoc(res.data);
      } catch (e) {
        if (on) setErr(apiErrorText(e, "Gagal memuat detail dokumen."));
      } finally { if (on) setLoading(false); }
    })();
    return () => { on = false; };
  }, [item]); // eslint-disable-line

  async function decide(decision) {
    if (decision === "reject" && !notes.trim() && k !== "po") return;
    setBusy(decision); setErr("");
    try {
      await submitDecision(item, decision, notes.trim());
      onDecided(`${item.title} ${decision === "approve" ? "disetujui" : "ditolak"}.`);
    } catch (e) {
      setErr(apiErrorText(e, "Gagal menyimpan keputusan."));
      setBusy("");
    }
  }

  return (
    <div className="modal-overlay fixed inset-0 z-[60] flex items-start justify-center overflow-y-auto bg-black/40 p-4 sm:items-center"
      data-testid="decision-modal-overlay" {...overlayDismiss(onClose)}>
      <div role="dialog" aria-modal="true" data-testid="decision-modal"
        className="my-auto w-full max-w-2xl rounded-xl bg-white shadow-2xl"
        onClick={(e) => e.stopPropagation()}>

        {/* KEPALA */}
        <div className="flex items-start justify-between gap-3 rounded-t-xl border-b border-[#EFF0F2] px-4 py-3">
          <div className="flex min-w-0 items-center gap-2.5">
            <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full"
              style={{ background: meta?.bg || "#EFF4FF", color: accent }}>
              <Icon size={16} />
            </span>
            <div className="min-w-0">
              <h3 className="flex flex-wrap items-center gap-2 text-[13.5px] font-bold text-[#1C1C1E]"
                data-testid="decision-modal-title">
                <span className="truncate">{item.title}</span>
                <span className="rounded px-1.5 py-0.5 text-[9px] font-bold uppercase"
                  style={{ background: meta?.bg || "#EFF4FF", color: accent }}>
                  {meta?.label || item.kind}
                </span>
              </h3>
              <p className="mt-0.5 flex flex-wrap items-center gap-x-2 text-[11px] text-[#6B6B73]">
                <span className="truncate">{item.subtitle}</span>
                <span className="inline-flex items-center gap-1"><Clock size={10} />
                  diajukan {item.requester || "—"} · butuh <b className="uppercase">{item.role || "manager"}</b></span>
              </p>
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            {/* SISA ANTREAN (2026-06) — pemutus tahu posisinya: "3 dari 7". */}
            {queuePos != null && queueTotal > 0 && (
              <span data-testid="decision-queue-pos"
                className="rounded-full bg-[#F2F2F7] px-2 py-0.5 text-[10.5px] font-bold tabular-nums text-[#6B6B73]"
                title="Posisi dokumen ini dalam antrean saringan aktif">
                {queuePos} dari {queueTotal}
              </span>
            )}
            {item.amount != null && (
              <span className="text-[14px] font-bold tabular-nums text-[#1C1C1E]"
                data-testid="decision-modal-amount">{formatCurrency(item.amount)}</span>
            )}
            <button type="button" className="icon-button" aria-label="Tutup"
              data-testid="decision-modal-close" onClick={onClose}><X size={14} /></button>
          </div>
        </div>

        {/* BADAN — detail dokumen */}
        <div className="max-h-[52vh] space-y-3 overflow-y-auto px-4 py-3" data-testid="decision-modal-body">
          {loading ? (
            <p className="flex items-center gap-2 py-6 text-[12px] text-[#6B6B73]">
              <Loader2 size={14} className="animate-spin" /> Memuat detail dokumen…
            </p>
          ) : doc ? (
            <DetailBody item={item} doc={doc} />
          ) : !err ? null : (
            /* Detail tak terbaca (mis. 403 untuk peran peninjau) — jangan pamerkan
               kisi berisi "—" / "Rp 0" yang menyesatkan; info baris di kepala cukup. */
            <p className="text-[12px] text-[#6B6B73]" data-testid="decision-modal-no-detail">
              Detail lengkap tidak dapat dimuat untuk peran Anda — gunakan informasi di
              kepala pop-up, atau buka layar penuh.
            </p>
          )}
          {/* INV-UI-03 — bilah error DI DALAM modal (bilah layar induk tertutup lapisan ini). */}
          {err && <ErrorNotice message={err} onDismiss={() => setErr("")} testId="decision-modal-error" />}
        </div>

        {/* KAKI — keputusan */}
        <div className="rounded-b-xl border-t border-[#EFF0F2] bg-[#FAFBFC] px-4 py-3">
          {allowed ? (
            <>
              <textarea data-testid="decision-modal-notes" rows={2}
                className="w-full rounded-lg border border-[#E5E5EA] bg-white px-3 py-2 text-[12px] outline-none focus:border-[#0058CC]"
                placeholder={k === "po"
                  ? "Catatan (opsional — untuk PO alasan rinci dicatat di layar penuh)…"
                  : "Catatan keputusan — WAJIB diisi saat menolak…"}
                value={notes} onChange={(e) => setNotes(e.target.value)} />
              <div className="mt-2 flex flex-wrap items-center gap-2">
                <button type="button" data-testid="decision-modal-approve"
                  className="primary-button" disabled={!!busy}
                  onClick={() => decide("approve")}>
                  {busy === "approve" ? <Loader2 size={13} className="animate-spin" /> : <Check size={13} />} Setujui
                </button>
                <button type="button" data-testid="decision-modal-reject"
                  className="danger-button"
                  disabled={!!busy || (k !== "po" && !notes.trim())}
                  title={k !== "po" && !notes.trim() ? "Isi alasan penolakan dulu" : ""}
                  onClick={() => decide("reject")}>
                  {busy === "reject" ? <Loader2 size={13} className="animate-spin" /> : <X size={13} />} Tolak
                </button>
                <button type="button" data-testid="decision-modal-open-full"
                  onClick={onOpenFull}
                  className="ml-auto inline-flex items-center gap-1 text-[11.5px] font-bold text-[#0058CC] hover:underline">
                  <ExternalLink size={12} /> Buka layar penuh <ArrowRight size={11} />
                </button>
              </div>
            </>
          ) : (
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-[11.5px] text-[#6B6B73]" data-testid="decision-modal-readonly">
                Peran Anda hanya bisa <b>meninjau</b> — keputusan butuh peran{" "}
                <b className="uppercase">{item.role || "manager"}</b>.
              </p>
              <button type="button" data-testid="decision-modal-open-full"
                onClick={onOpenFull}
                className="inline-flex items-center gap-1 text-[11.5px] font-bold text-[#0058CC] hover:underline">
                <ExternalLink size={12} /> Buka layar penuh <ArrowRight size={11} />
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
