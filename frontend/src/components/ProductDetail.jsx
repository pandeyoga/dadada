import { useState } from "react";
import { XCircle, ShoppingBag, Printer } from "lucide-react";
import { formatCurrency, formatQty } from "../utils/formatters";
import LabelPrinterModal from "./LabelPrinterModal";

export function ProductDetail({ product, breakdown, onClose, onAdd }) {
  const [showLabelModal, setShowLabelModal] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);
  
  if (!product) return null;
  
  return (
    <>
      <div data-testid="product-detail-panel" className="section-card mb-3">
        <div className="section-head">
          <div className="min-w-0">
            <p 
              data-testid="detail-product-sku" 
              className="text-[10.5px] font-bold uppercase tracking-wide text-[#0058CC]"
            >
              {product.sku}
            </p>
            <h2 data-testid="detail-product-name" className="text-[15px] font-bold tracking-tight">
              {product.name}
            </h2>
            <p data-testid="detail-product-meta" className="text-[11.5px] text-[#3C3C43]">
              {product.category} • {product.color} • {product.motif} • Grade {product.grade}
            </p>
            {(product.color_ref || product.rnd_supplier) && (
              <div className="mt-1.5 rounded-lg border border-[#EFF0F2] bg-[#FAFBFC] px-2.5 py-2" data-testid="detail-product-colors">
                <p className="text-[9.5px] font-bold uppercase tracking-wide text-[#8E8E93]">Dua warna &amp; supplier (dari R&amp;D)</p>
                {product.color_ref && (
                  <p className="mt-1 flex flex-wrap items-center gap-1.5 text-[11px]">
                    <span className="text-[#6B6B73]">Warna internal:</span>
                    <span className="inline-block h-3 w-3 rounded-full border border-black/10" style={{ background: product.color_ref.hex }} />
                    <b className="font-mono">{product.color_ref.code}</b> {product.color_ref.name}
                  </p>
                )}
                {(product.supplier_colors || []).length > 0 ? (
                  <ul className="mt-1 grid gap-0.5 text-[11px]" data-testid="detail-product-supplier-colors">
                    {product.supplier_colors.map((v) => (
                      <li key={v.supplier_id} className="flex flex-wrap items-center gap-1.5">
                        <span className="text-[#6B6B73]">Warna supplier</span>
                        <span className="rounded bg-[#F1E9F7] px-1.5 py-px font-bold text-[#6B219A]">{v.supplier_name}</span>
                        <b>{v.supplier_color_name || "—"}</b>{v.supplier_color_code ? <span className="font-mono text-[#6B6B73]">({v.supplier_color_code})</span> : null}
                        {v.sample_number && <span className="text-[10px] text-[#8E8E93]">· dari {v.sample_number}</span>}
                      </li>
                    ))}
                  </ul>
                ) : product.color_ref ? <p className="mt-1 text-[10.5px] text-[#8E8E93]">belum ada versi warna supplier (terisi saat labdip ACC)</p> : null}
                {product.rnd_supplier && (
                  <p className="mt-1 text-[11px]" data-testid="detail-product-rnd-supplier">
                    <span className="text-[#6B6B73]">Supplier pemenang R&amp;D:</span> <b>{product.rnd_supplier.name}</b>
                    {product.rnd_supplier.contract_number ? <span className="text-[#6B6B73]"> · kontrak {product.rnd_supplier.contract_number}</span> : null}
                    {product.rnd_supplier.sample_number ? <span className="text-[#6B6B73]"> · sample {product.rnd_supplier.sample_number}</span> : null}
                  </p>
                )}
              </div>
            )}
          </div>
          <button 
            data-testid="close-product-detail-button" 
            className="icon-button" 
            onClick={onClose} 
            aria-label="Tutup detail"
          >
            <XCircle size={16} />
          </button>
        </div>
        <div className="section-body">
          <div className="grid gap-3 md:grid-cols-[180px_1fr]">
            <img 
              data-testid="detail-product-image" 
              src={product.image} 
              alt={product.name} 
              className="aspect-[4/3] w-full rounded-md object-cover border border-[#EFF0F2]" 
            />
            <div className="grid gap-2 sm:grid-cols-3">
              <div className="rounded-md border border-[#EFF0F2] bg-[#FAFBFC] p-2.5">
                <p className="text-[10.5px] font-bold uppercase text-[#6B6B73]">Tersedia</p>
                <p 
                  data-testid="detail-available-qty" 
                  className="text-[16px] font-bold text-[#126E2C]"
                >
                  {formatQty(product.available_qty)}
                </p>
              </div>
              <div className="rounded-md border border-[#EFF0F2] bg-[#FAFBFC] p-2.5">
                <p className="text-[10.5px] font-bold uppercase text-[#6B6B73]">Dipesan</p>
                <p 
                  data-testid="detail-reserved-qty" 
                  className="text-[16px] font-bold text-[#6B219A]"
                >
                  {formatQty(product.reserved_qty)}
                </p>
              </div>
              <div className="rounded-md border border-[#EFF0F2] bg-[#FAFBFC] p-2.5">
                <p className="text-[10.5px] font-bold uppercase text-[#6B6B73]">Harga</p>
                <p data-testid="detail-price" className="text-[13px] font-bold">
                  {formatCurrency(product.price)}
                </p>
              </div>
            </div>
          </div>
          <button data-testid="detail-advanced-toggle" onClick={() => setShowAdvanced((v) => !v)} className="mt-3 flex w-full items-center justify-between rounded-md border border-[#EFF0F2] bg-[#FAFBFC] px-3 py-2 text-[11.5px] font-semibold text-[#3C3C43]">
            <span>Lanjutan — stok per gudang, lot, entitas & roll</span>
            <span className="text-[#6B6B73]">{showAdvanced ? "Sembunyikan \u25B2" : "Tampilkan \u25BC"}</span>
          </button>
          {showAdvanced && (<>
          <div className="mt-3 overflow-hidden rounded-md border border-[#EFF0F2]">
            <div className="grid grid-cols-5 bg-[#FAFBFC] px-3 py-1.5 text-[10.5px] font-bold uppercase tracking-wide text-[#6B6B73]">
              <span>Gudang</span>
              <span>Kota</span>
              <span>Stok Fisik</span>
              <span>Dipesan</span>
              <span>Tersedia</span>
            </div>
            {(breakdown?.balances || []).length === 0 && (
              <div data-testid="detail-stock-empty" className="border-t border-[#EFF0F2] px-3 py-3 text-center text-[11.5px] text-[#6B6B73] animate-pulse">
                Memuat / belum ada data stok per gudang…
              </div>
            )}
            {(breakdown?.balances || []).map((row) => (
              <div 
                data-testid={`detail-stock-row-${row.warehouse_id}`} 
                key={row.warehouse_id} 
                className="grid grid-cols-5 border-t border-[#EFF0F2] px-3 py-1.5 text-[11.5px]"
              >
                <span 
                  data-testid={`detail-stock-warehouse-${row.warehouse_id}`} 
                  className="font-semibold"
                >
                  {row.warehouse_name}
                </span>
                <span data-testid={`detail-stock-city-${row.warehouse_id}`}>
                  {row.warehouse_city}
                </span>
                <span data-testid={`detail-stock-onhand-${row.warehouse_id}`}>
                  {formatQty(row.on_hand_qty)}
                </span>
                <span data-testid={`detail-stock-reserved-${row.warehouse_id}`}>
                  {formatQty(row.reserved_qty)}
                </span>
                <span data-testid={`detail-stock-available-${row.warehouse_id}`}>
                  {formatQty(row.available_qty)}
                </span>
              </div>
            ))}
          </div>

          {/* Ownership Matrix — Owner × Gudang × Lot (Roll-as-SSOT, KN_15 §8) */}
          {(breakdown?.ownership_matrix || []).length > 0 && (
            <div className="mt-3 overflow-hidden rounded-md border border-[#E0E7FF]" data-testid="ownership-matrix">
              <div className="bg-[#EEF2FF] px-3 py-1.5 text-[10.5px] font-bold uppercase tracking-wide text-[#4338CA]">
                Kepemilikan per Entitas · Lot · Gudang
              </div>
              <div className="grid grid-cols-6 bg-[#FAFBFC] px-3 py-1.5 text-[10px] font-bold uppercase tracking-wide text-[#6B6B73]">
                <span>Pemilik</span>
                <span>Gudang</span>
                <span>Lot</span>
                <span className="text-right">Tersedia</span>
                <span className="text-right">Dipesan</span>
                <span className="text-right">Roll</span>
              </div>
              {(breakdown?.ownership_matrix || []).map((cell, i) => (
                <div
                  key={`${cell.owner_entity_id}-${cell.warehouse_id}-${cell.lot}-${i}`}
                  data-testid={`ownership-cell-${i}`}
                  className="grid grid-cols-6 border-t border-[#EFF0F2] px-3 py-1.5 text-[11px]"
                >
                  <span className="font-semibold text-[#4338CA] truncate">{cell.owner_entity_name}</span>
                  <span className="truncate">{cell.warehouse_name}</span>
                  <span className="font-mono text-[10px]">{cell.lot}</span>
                  <span className="text-right font-semibold text-[#126E2C]">{formatQty(cell.available_qty)}</span>
                  <span className="text-right text-[#FF9500]">{formatQty(cell.reserved_qty)}</span>
                  <span className="text-right tabular-nums">{cell.roll_count}</span>
                </div>
              ))}
            </div>
          )}
          </>)}
          <div className="mt-3 flex flex-wrap gap-2">
            <button 
              data-testid="detail-add-to-cart-button" 
              className="primary-button" 
              onClick={() => onAdd(product)}
            >
              <ShoppingBag size={14} /> Tambah ke Draf
            </button>
            <button 
              data-testid="detail-print-label-button" 
              className="secondary-button" 
              onClick={() => setShowLabelModal(true)}
            >
              <Printer size={14} /> Cetak Label
            </button>
          </div>
        </div>
      </div>
      {showLabelModal && (
        <LabelPrinterModal
          product={product}
          warehouse={null}
          onClose={() => setShowLabelModal(false)}
        />
      )}
    </>
  );
}
