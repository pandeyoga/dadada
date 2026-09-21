// CheckoutDrawer — Step 3 (Review) dipisah agar file utama di bawah batas guardrail.
// Murni presentational: render dari props (state & handler tetap di CheckoutDrawer).
import KNDatePicker from "@/components/KNDatePicker";
import { Truck, PackageCheck, Receipt, ShieldAlert, ShieldCheck, CreditCard } from "lucide-react";
import { formatCurrency } from "../../utils/formatters";
import { Row } from "./CheckoutItemCard";

export default function CheckoutStep3({
  fulfillmentMethod, setFulfillmentMethod, pickupDate, setPickupDate,
  deliveryDate, setDeliveryDate,
  selectedCustomer, addresses, selectedAddress, p, cart, pricedCart, paymentTerm,
  needsTaxInvoice, setNeedsTaxInvoice, credit, creditBlocked,
  hasBackorderLine, allowBackorder, requiresLotConfirmation, mixedLotLines, sampleCount = 0,
}) {
  const today = new Date().toISOString().slice(0, 10);
  return (
    <div data-testid="checkout-step-3" className="space-y-3">
      {/* Order Pengambilan — metode pemenuhan (Kirim / Ambil di Gudang) */}
      <div className="rounded-md border border-[#EFF0F2] bg-white p-3">
        <p className="text-[11px] font-bold uppercase tracking-wide text-[#6B6B73]">Metode Pemenuhan</p>
        <div className="mt-2 grid grid-cols-2 gap-2">
          <button type="button" data-testid="fulfillment-kirim"
            onClick={() => { setFulfillmentMethod("kirim"); setPickupDate(""); }}
            className={`flex items-center justify-center gap-1.5 rounded-md border px-2 py-2 text-[12px] font-semibold ${fulfillmentMethod === "kirim" ? "border-[#0058CC] bg-[#EFF4FF] text-[#0058CC]" : "border-[#EFF0F2] bg-white text-[#6B6B73]"}`}>
            <Truck size={14} /> Kirim
          </button>
          <button type="button" data-testid="fulfillment-ambil"
            onClick={() => setFulfillmentMethod("ambil")}
            className={`flex items-center justify-center gap-1.5 rounded-md border px-2 py-2 text-[12px] font-semibold ${fulfillmentMethod === "ambil" ? "border-[#0058CC] bg-[#EFF4FF] text-[#0058CC]" : "border-[#EFF0F2] bg-white text-[#6B6B73]"}`}>
            <PackageCheck size={14} /> Ambil di Gudang
          </button>
        </div>
        {fulfillmentMethod === "ambil" && (
          <div className="mt-2">
            <label className="text-[10px] font-bold uppercase tracking-wide text-[#8E8E93]">Tanggal Pengambilan</label>
            <KNDatePicker data-testid="pickup-date-input" value={pickupDate} onChange={setPickupDate} />
            <p className="mt-1 text-[10px] text-[#9A5B00]">Daftar pengambilan ditahan sampai tanggal ini — gudang baru menyiapkan barang pada/ setelah tanggal pengambilan.</p>
          </div>
        )}
      </div>
      {fulfillmentMethod === "kirim" ? (
        <div className="rounded-md border border-[#EFF0F2] bg-white p-3">
          <p className="text-[11px] font-bold uppercase tracking-wide text-[#6B6B73]">Kirim ke</p>
          <p className="text-[13px] font-semibold">{selectedCustomer?.name}</p>
          {(() => { const a = addresses.find((x) => x.id === selectedAddress) || {}; return (
            <div data-testid="checkout-review-address" className="text-[11.5px] text-[#6B6B73]">
              <p className="font-semibold text-[#3C3C43]">{a.label || "—"}{a.recipient_name ? ` · ${a.recipient_name}` : ""}</p>
              <p className="leading-snug">{a.address || "Alamat belum diisi"}{a.city ? `, ${a.city}` : ""}</p>
              {a.phone && <p>{a.phone}</p>}
            </div>); })()}
          <div className="mt-2.5 border-t border-[#F2F3F5] pt-2.5">
            <label className="text-[10px] font-bold uppercase tracking-wide text-[#8E8E93]">Tanggal Pengiriman (opsional)</label>
            <KNDatePicker data-testid="delivery-date-input" min={today}
              value={deliveryDate || ""} onChange={setDeliveryDate} />
            <p className="mt-1 text-[10px] text-[#6B6B73]">Kosongkan bila mengikuti jadwal gudang. Bila diisi: request tanggal kirim — tidak boleh tanggal yang sudah lewat.</p>
          </div>
        </div>
      ) : (
        <div className="rounded-md border border-[#EFF0F2] bg-white p-3">
          <p className="text-[11px] font-bold uppercase tracking-wide text-[#6B6B73]">Diambil oleh</p>
          <p className="text-[13px] font-semibold">{selectedCustomer?.name}</p>
          <p className="text-[11.5px] text-[#6B6B73]">Ambil di gudang{pickupDate ? ` · ${pickupDate}` : " · pilih tanggal dahulu"}</p>
        </div>
      )}
      <div className="rounded-md bg-black p-3 text-white">
        <div className="flex items-center gap-1.5"><Receipt size={12} className="text-white/70" /><p className="text-[10.5px] font-bold uppercase tracking-wide text-white/70">Ringkasan ({cart.length} item)</p></div>
        <ul data-testid="checkout-review-lines" className="mt-1.5 divide-y divide-white/10 text-[11.5px]">
          {(pricedCart || cart).map((it) => {
            const unit = it.unit || it.product?.base_unit || "";
            const price = Number(it.product?.price || 0);
            const disc = Number(it.discount_percent || 0);
            return (
              <li key={it.product?.id} data-testid={`checkout-review-line-${it.product?.id}`} className="flex items-start justify-between gap-2 py-1">
                <span className="min-w-0">
                  <span className="block truncate font-semibold">{it.product?.name}{it.is_sample ? <span data-testid={`checkout-review-sample-${it.product?.id}`} className="ml-1 rounded-full bg-[#FFF3D6] px-1.5 py-0.5 text-[9px] font-bold text-[#9A5B00]">SAMPEL</span> : null}</span>
                  <span className="block text-[10.5px] text-white/60 tabular-nums">{it.quantity} {unit} × {formatCurrency(price)}{disc > 0 ? ` · disc ${disc}%` : ""}</span>
                </span>
                <span className="shrink-0 tabular-nums">{formatCurrency(price * Number(it.quantity || 0) * (1 - disc / 100))}</span>
              </li>
            );
          })}
        </ul>
        <div className="mt-1.5 space-y-1 border-t border-white/15 pt-1.5 text-[11.5px]">
          <Row label="Subtotal (bruto)" value={formatCurrency(p.gross)} />
          {p.discountTotal > 0 && <Row label="Diskon" value={`- ${formatCurrency(p.discountTotal)}`} />}
          {p.ppn > 0 && <Row label={`PPN ${p.ppnRate}%${p.dppNilaiLain ? " (DPP 11/12)" : ""}`} value={formatCurrency(p.ppn)} />}
          {p.isPkp === false && <Row label="PPN" value="Non-PKP (0)" muted />}
          <Row label="Termin" value={paymentTerm || "Default"} />
        </div>
        <div className="mt-2 flex items-end justify-between border-t border-white/15 pt-2">
          <p className="text-[10.5px] font-bold uppercase tracking-wide text-white/70">Grand Total</p>
          <p data-testid="cart-grand-total" className="text-[18px] font-bold">{formatCurrency(p.grand)}</p>
        </div>
      </div>

      {/* F6 — Faktur Pajak per-order: hanya relevan bila entitas PKP (kena PPN) */}
      {p.isPkp !== false ? (
        <button type="button" data-testid="checkout-tax-invoice-toggle"
          onClick={() => setNeedsTaxInvoice((v) => !v)}
          className={`flex w-full items-center justify-between rounded-md border p-2.5 text-left ${needsTaxInvoice ? "border-[#0058CC] bg-[#EFF4FF]" : "border-[#EFF0F2] bg-white"}`}>
          <span className="flex items-center gap-2 text-[12px]">
            <Receipt size={14} className={needsTaxInvoice ? "text-[#0058CC]" : "text-[#8E8E93]"} />
            <span>
              <span className="block font-semibold text-[#1C1C1E]">Minta Faktur Pajak</span>
              <span className="block text-[10.5px] text-[#6B6B73]">Entitas PKP — PPN {p.ppnRate || 12}%{p.dppNilaiLain ? " (DPP Nilai Lain 11/12, efektif 11%)" : ""} berlaku. Centang bila pelanggan minta Faktur Pajak.</span>
            </span>
          </span>
          <span className={`flex h-5 w-9 items-center rounded-full p-0.5 transition-colors ${needsTaxInvoice ? "bg-[#0058CC]" : "bg-[#D1D1D6]"}`}>
            <span className={`h-4 w-4 rounded-full bg-white shadow transition-transform ${needsTaxInvoice ? "translate-x-4" : ""}`} />
          </span>
        </button>
      ) : (
        <div data-testid="checkout-tax-nonpkp-note" className="rounded-md border border-[#EFF0F2] bg-[#FAFBFC] p-2.5 text-[11px] text-[#6B6B73]">
          <span className="flex items-center gap-1.5"><Receipt size={13} className="text-[#8E8E93]" /> Entitas <b>non-PKP</b> — transaksi tanpa PPN, Faktur Pajak tidak diterbitkan.</span>
        </div>
      )}

      {credit && credit.level !== "ok" && (
        <div data-testid="credit-status-banner" className={`rounded-md border p-2.5 ${creditBlocked ? "border-[#F1B0AB] bg-[#FDECEA]" : credit.has_approved_override ? "border-[#A7D8B0] bg-[#EAF7EE]" : "border-[#F5C9A6] bg-[#FFF7EF]"}`}>
          <div className="flex items-start gap-2">
            {creditBlocked ? <ShieldAlert size={14} className="mt-0.5 shrink-0 text-[#C0392B]" /> : <ShieldCheck size={14} className="mt-0.5 shrink-0 text-[#9A5B00]" />}
            <div className="min-w-0 text-[11px]">
              <p className={`font-semibold ${creditBlocked ? "text-[#9B1C13]" : "text-[#8C4A00]"}`}>
                {creditBlocked ? "Kredit terblokir — order tidak bisa dibuat" : credit.has_approved_override ? "Kredit terblokir, tapi ada Override disetujui" : "Peringatan kredit (mendekati limit / ada tunggakan)"}
              </p>
              {(credit.reasons || []).map((r, i) => <p key={i} className="text-[10.5px] text-[#6B6B73]">• {r}</p>)}
              <p className="mt-0.5 text-[10px] text-[#9A9BA3] tabular-nums">AR {formatCurrency(credit.credit?.ar_outstanding)} / limit {credit.credit?.credit_limit > 0 ? formatCurrency(credit.credit.credit_limit) : "∞"} · proyeksi {formatCurrency(credit.projected_ar)}</p>
            </div>
          </div>
        </div>
      )}
      {credit && credit.level === "ok" && (
        <div className="flex items-center gap-2 rounded-md border border-[#A7D8B0] bg-[#EAF7EE] p-2.5 text-[11.5px] text-[#126E2C]"><ShieldCheck size={14} /> Kredit OK · ATP & alokasi tervalidasi.</div>
      )}

      <div className="rounded-md border border-[#EFF0F2] bg-white p-3 text-[11.5px] text-[#6B6B73]">
        <div className="flex items-center gap-1.5 text-[#1C1C1E]"><CreditCard size={13} /><span className="font-semibold">Pemenuhan</span></div>
        <p className="mt-1">{hasBackorderLine ? (allowBackorder ? "Sebagian via backorder (disetujui)." : "Ada baris kurang stok — aktifkan backorder di langkah 2.") : "Semua baris dapat dipenuhi dari stok entitas."}</p>
        {sampleCount > 0 && <p data-testid="checkout-sample-fulfillment-note" className="mt-0.5 text-[#9A5B00]">{sampleCount} baris sampel → permintaan potong ke admin gudang saat pesanan dikonfirmasi (pindai roll RFID, potong, catat panjang aktual), lalu ikut dikirim bersama pesanan.</p>}
        {requiresLotConfirmation && <p className="mt-0.5 text-[#6B219A]">{mixedLotLines.length} item beda lot — konfirmasi saat kirim.</p>}
      </div>
    </div>
  );
}
