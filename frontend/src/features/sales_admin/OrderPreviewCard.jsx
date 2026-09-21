/**
 * OrderPreviewCard — ringkasan DATA pesanan di dalam dialog Verifikasi & Pemenuhan.
 *
 * Checklist tanpa datanya memaksa Admin membuka dua layar. Kartu ini menaruh
 * pelanggan, alamat kirim, termin, baris barang + kondisi stok, dan total
 * TEPAT di samping daftar periksa — sumber datanya `order_preview` dari server.
 */
import { CalendarDays, MapPin, Package, StickyNote, UserRound, Wallet } from "lucide-react";
import { formatCurrency, formatQty } from "../../utils/formatters";

export default function OrderPreviewCard({ preview, testPrefix = "order-preview" }) {
  if (!preview) return null;
  const items = Array.isArray(preview.items) ? preview.items : [];
  const backs = Array.isArray(preview.backorders) ? preview.backorders : [];
  const t = preview.totals || {};
  const addr = preview.shipping_address || {};
  const isPickup = (preview.fulfillment_method || "kirim") === "ambil";
  const tanggal = (preview.created_at || "").slice(0, 10);

  return (
    <div className="rounded-lg border border-[#EFF0F2]" data-testid={testPrefix}>
      <div className="flex items-center gap-1.5 border-b border-[#F4F5F7] bg-[#FAFBFC] px-3 py-2">
        <Package size={13} className="text-[#0058CC]" />
        <p className="text-[10.5px] font-bold uppercase tracking-wide text-[#6B6B73]">
          Data Pesanan
        </p>
      </div>

      <div className="grid gap-x-4 gap-y-2 px-3 py-2.5 sm:grid-cols-2"
           data-testid={`${testPrefix}-info`}>
        <InfoRow icon={UserRound} label="Pelanggan"
                 value={`${preview.customer_name || "—"}${preview.customer_city ? ` · ${preview.customer_city}` : ""}`}
                 testId={`${testPrefix}-customer`} />
        {isPickup ? (
          <InfoRow icon={MapPin} label="Pemenuhan"
                   value={`Ambil sendiri di gudang${preview.pickup_date ? ` · ${preview.pickup_date}` : ""} — tanpa alamat kirim`}
                   testId={`${testPrefix}-pickup`} />
        ) : (<>
        <InfoRow icon={UserRound} label="Penerima"
                 value={addr.recipient_name
                   ? `${addr.recipient_name}${addr.phone ? ` · ${addr.phone}` : ""}`
                   : "Belum diisi"}
                 warn={!addr.recipient_name}
                 testId={`${testPrefix}-recipient`} />
        <InfoRow icon={MapPin} label="Alamat kirim"
                 value={addr.address
                   ? `${addr.address}${addr.city ? `, ${addr.city}` : ""}`
                   : "Belum diisi"}
                 warn={!addr.address}
                 testId={`${testPrefix}-address`} />
        </>)}
        <InfoRow icon={Wallet} label="Termin bayar"
                 value={preview.payment_term || "Belum dipilih"}
                 warn={!preview.payment_term}
                 testId={`${testPrefix}-term`} />
        <InfoRow icon={CalendarDays} label="Tanggal pesanan" value={tanggal || "—"}
                 testId={`${testPrefix}-date`} />
        <InfoRow icon={UserRound} label="Sales pembuat" value={preview.sales_name || "—"}
                 testId={`${testPrefix}-sales`} />
      </div>

      <div className="border-t border-[#F4F5F7]" data-testid={`${testPrefix}-items`}>
        <div className="grid grid-cols-[1.7fr_86px_100px_106px_86px] bg-[#FAFBFC] px-3 py-1.5 text-[9.5px] font-bold uppercase text-[#6B6B73]">
          <span>Barang</span><span className="text-right">Qty</span>
          <span className="text-right">Harga</span><span className="text-right">Subtotal</span>
          <span className="text-right">Stok</span>
        </div>
        {items.length === 0 && backs.length === 0 && (
          <p className="px-3 py-5 text-center text-[11.5px] text-[#6B6B73]">
            Belum ada baris barang pada pesanan ini.
          </p>
        )}
        {items.map((it) => (
          <div key={it.product_id}
               data-testid={`${testPrefix}-item-${it.product_id}`}
               className="grid grid-cols-[1.7fr_86px_100px_106px_86px] items-center border-t border-[#F4F5F7] px-3 py-1.5">
            <div className="min-w-0">
              <p className="truncate text-[11.5px] font-semibold">{it.product_name}</p>
              <p className="truncate text-[10px] text-[#9A9BA3]">
                {it.sku}{it.discount_percent > 0 ? ` · disc ${formatQty(it.discount_percent)}%` : ""}
              </p>
            </div>
            <span className="text-right text-[11px] tabular-nums">
              {formatQty(it.quantity)} {it.unit}
            </span>
            <span className="text-right text-[11px] tabular-nums">{formatCurrency(it.price)}</span>
            <span className="text-right text-[11.5px] font-semibold tabular-nums">
              {formatCurrency(it.line_total)}
            </span>
            <span className={`text-right text-[10.5px] font-bold ${
              it.stock_ok ? "text-[#1B7F4B]" : "text-[#C0392B]"}`}>
              {it.stock_ok ? "cukup" : `sisa ${formatQty(it.available_qty)}`}
            </span>
          </div>
        ))}
        {backs.map((b, i) => (
          <div key={`${b.sku}-${i}`}
               data-testid={`${testPrefix}-backorder-${i}`}
               className="grid grid-cols-[1.7fr_86px_100px_106px_86px] items-center border-t border-[#F4F5F7] bg-[#FFF9EF] px-3 py-1.5">
            <div className="min-w-0">
              <p className="truncate text-[11.5px] font-semibold">{b.product_name}</p>
              <p className="truncate text-[10px] text-[#9A9BA3]">{b.sku} · kurang stok</p>
            </div>
            <span className="text-right text-[11px] tabular-nums">
              {formatQty(b.backorder_qty)} {b.unit}
            </span>
            <span className="text-right text-[10.5px] text-[#9A9BA3]">—</span>
            <span className="text-right text-[10.5px] text-[#9A9BA3]">—</span>
            <span className="text-right text-[10.5px] font-bold text-[#8A5300]">backorder</span>
          </div>
        ))}
      </div>

      <div className="border-t border-[#F4F5F7] px-3 py-2" data-testid={`${testPrefix}-totals`}>
        <TotalRow label="Subtotal" value={formatCurrency(t.net_subtotal)} />
        {t.discount_total > 0 && (
          <TotalRow label="Diskon" value={`− ${formatCurrency(t.discount_total)}`} />
        )}
        <TotalRow
          label={t.is_pkp ? `PPN ${formatQty(t.ppn_rate)}%` : "PPN (non-PKP)"}
          value={formatCurrency(t.ppn_amount)} />
        <div className="mt-1 flex items-center justify-between border-t border-[#EFF0F2] pt-1.5">
          <span className="text-[11px] font-bold uppercase text-[#6B6B73]">Total Pesanan</span>
          <span className="text-[13.5px] font-bold tabular-nums" data-testid={`${testPrefix}-grand-total`}>
            {formatCurrency(t.grand_total)}
          </span>
        </div>
      </div>

      {preview.notes && (
        <div className="flex items-start gap-1.5 border-t border-[#F4F5F7] px-3 py-2"
             data-testid={`${testPrefix}-notes`}>
          <StickyNote size={11} className="mt-0.5 shrink-0 text-[#9A9BA3]" />
          <p className="text-[10.5px] text-[#6B6B73]">{preview.notes}</p>
        </div>
      )}
    </div>
  );
}

function InfoRow({ icon: Icon, label, value, warn = false, testId }) {
  return (
    <div className="flex items-start gap-1.5" data-testid={testId}>
      <Icon size={12} className="mt-0.5 shrink-0 text-[#9A9BA3]" />
      <div className="min-w-0">
        <p className="text-[9.5px] font-bold uppercase tracking-wide text-[#9A9BA3]">{label}</p>
        <p className={`text-[11.5px] ${warn ? "font-semibold text-[#C0392B]" : "text-[#1C1C1E]"}`}>
          {value}
        </p>
      </div>
    </div>
  );
}

function TotalRow({ label, value }) {
  return (
    <div className="flex items-center justify-between py-0.5">
      <span className="text-[10.5px] text-[#6B6B73]">{label}</span>
      <span className="text-[11.5px] tabular-nums">{value}</span>
    </div>
  );
}
