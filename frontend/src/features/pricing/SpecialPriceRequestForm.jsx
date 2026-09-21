import { useEffect, useRef, useState } from "react";
import { Paperclip, Send, ChevronDown, ChevronUp, Info } from "lucide-react";
import axios, { API } from "../../services/apiClient";
import { formatCurrency } from "../../utils/formatters";
import KNDatePicker from "@/components/KNDatePicker";
import MoneyInput from "@/components/MoneyInput";

/**
 * §3-B — SATU komponen permintaan harga khusus, dipakai di 4 pintu (POS, detail SO,
 * layar Persetujuan Harga, mobile). Bawaan: harga + bukti (WAJIB, ditegakkan backend);
 * jumlah minimum / berlaku sampai / "jadikan harga langganan" tersembunyi di "Atur lebih lanjut".
 * Alur: POST /price-approvals (draf) → POST attachments → POST /submit → onSubmitted(doc).
 */
export default function SpecialPriceRequestForm({ product, customer, entityId = "", soId = "", defaultQty = 0, onSubmitted, onCancel, compact = false }) {
  const normalPrice = Number(product?.price || 0);
  const [price, setPrice] = useState("");
  const [file, setFile] = useState(null);
  const [more, setMore] = useState(false);
  const [minQty, setMinQty] = useState(defaultQty ? String(Math.round(defaultQty)) : "");
  const [validUntil, setValidUntil] = useState("");
  const [standing, setStanding] = useState(false);
  const [reason, setReason] = useState("");
  const [hint, setHint] = useState(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [done, setDone] = useState(null);
  const fileRef = useRef(null);
  const priceNum = parseFloat(price);

  useEffect(() => {
    if (!(priceNum > 0) || !product?.id) { setHint(null); return undefined; }
    const t = setTimeout(() => {
      axios.get(`${API}/price-approvals/hint`, { params: { product_id: product.id, price: priceNum, entity_id: entityId || "" } })
        .then((r) => setHint(r.data)).catch(() => setHint(null));
    }, 350);
    return () => clearTimeout(t);
  }, [priceNum, product?.id, entityId]);

  const submit = async () => {
    setErr("");
    if (!customer?.id) { setErr("Pilih pelanggan dulu."); return; }
    if (!(priceNum > 0)) { setErr("Harga khusus harus lebih dari 0."); return; }
    if (normalPrice > 0 && priceNum >= normalPrice) { setErr("Harga khusus harus lebih rendah dari harga daftar."); return; }
    if (!file) { setErr("Bukti (tangkapan chat/penawaran) wajib dilampirkan."); return; }
    setBusy(true);
    try {
      const { data: draft } = await axios.post(`${API}/price-approvals`, {
        customer_id: customer.id, product_id: product.id, requested_price: priceNum,
        min_quantity: parseFloat(minQty) || 0, valid_until: standing ? (validUntil || "") : "",
        reason: reason || "", submit_now: false, entity_id: entityId || "",
        scope: standing ? "standing" : "order", so_id: soId || "",
      });
      const fd = new FormData(); fd.append("file", file);
      await axios.post(`${API}/price-approvals/${draft.id}/attachments`, fd, { headers: { "Content-Type": "multipart/form-data" } });
      const { data: sent } = await axios.post(`${API}/price-approvals/${draft.id}/submit`);
      setDone(sent);
      onSubmitted?.(sent);
    } catch (e) {
      const d = e.response?.data?.detail;
      setErr((d && (d.message || d)) || "Gagal mengajukan harga khusus.");
    } finally { setBusy(false); }
  };

  if (done) {
    return (
      <div className="notice-bar success" data-testid="spr-submitted">
        <b>Terkirim — menunggu persetujuan.</b> {done.number || done.id} · {formatCurrency(done.requested_price)} ·
        {done.scope === "standing" ? " harga langganan" : " untuk pesanan ini saja"} · penyetuju: {(hint?.approver_roles || ["manager", "admin"]).join("/")} · diajukan baru saja.
      </div>
    );
  }
  const pct = normalPrice > 0 && priceNum > 0 ? Math.round((1 - priceNum / normalPrice) * 1000) / 10 : 0;
  return (
    <div className={`space-y-3 ${compact ? "text-sm" : ""}`} data-testid="special-price-request-form">
      <div className="text-xs text-[#6E6E73]">{product?.name} · harga daftar <b className="tabular-nums">{formatCurrency(normalPrice)}</b>{customer?.name ? ` · ${customer.name}` : ""}</div>
      <label className="field"><span>Harga yang diminta pelanggan</span>
        <MoneyInput value={price} onChange={setPrice} placeholder="0" testId="spr-price-input" /></label>
      {priceNum > 0 && (
        <div className={`notice-bar ${hint?.needs_manager ? "danger" : "success"} flex items-center gap-2`} data-testid="spr-hint">
          <Info size={14} /> <span>{pct}% di bawah harga daftar{hint ? ` — ${hint.verdict}` : ""}</span>
        </div>
      )}
      <div>
        <input ref={fileRef} type="file" accept="image/*,.pdf" className="hidden" data-testid="spr-file-input"
          onChange={(e) => setFile(e.target.files?.[0] || null)} />
        <button type="button" className="secondary-button w-full flex items-center justify-center gap-2" onClick={() => fileRef.current?.click()} data-testid="spr-file-btn">
          <Paperclip size={14} /> {file ? file.name : "Lampirkan bukti chat / penawaran (wajib)"}
        </button>
      </div>
      <button type="button" className="text-xs text-[#0058CC] flex items-center gap-1" onClick={() => setMore((m) => !m)} data-testid="spr-more-toggle">
        {more ? <ChevronUp size={12} /> : <ChevronDown size={12} />} Atur lebih lanjut
      </button>
      {more && (
        <div className="space-y-2 rounded-md border border-[#E5E5EA] p-2">
          <label className="field"><span>Catatan / alasan</span><input value={reason} onChange={(e) => setReason(e.target.value)} data-testid="spr-reason-input" /></label>
          <label className="field"><span>Jumlah minimum</span><input type="number" value={minQty} onChange={(e) => setMinQty(e.target.value)} data-testid="spr-minqty-input" /></label>
          <label className="flex items-center gap-2 text-xs"><input type="checkbox" checked={standing} onChange={(e) => setStanding(e.target.checked)} data-testid="spr-standing-toggle" />
            Jadikan harga langganan pelanggan ini (berlaku untuk pesanan berikutnya)</label>
          {standing && <label className="field"><span>Berlaku sampai</span><KNDatePicker value={validUntil} onChange={setValidUntil} testId="spr-valid-until" /></label>}
        </div>
      )}
      {err && <div className="notice-bar danger" data-testid="spr-error">{String(err)}</div>}
      <div className="flex gap-2">
        {onCancel && <button type="button" className="secondary-button flex-1" onClick={onCancel} data-testid="spr-cancel">Batal</button>}
        <button type="button" className="primary-button flex-1 flex items-center justify-center gap-2" disabled={busy} onClick={submit} data-testid="spr-submit">
          <Send size={14} /> {busy ? "Mengirim…" : "Ajukan"}
        </button>
      </div>
    </div>
  );
}
