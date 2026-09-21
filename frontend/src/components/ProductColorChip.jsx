/**
 * ProductColorChip — "dua warna" satu produk di mana pun produk tampil (MD, Pembelian RFQ/PO, pemilih produk, katalog):
 * warna INTERNAL (pustaka KN) + versi warna SUPPLIER, selalu dilabeli nama supplier-nya.
 * `supplierId` → tampilkan hanya versi supplier itu (mis. baris PO ke supplier X). Tanpa supplierId → semua versi.
 */
import { Factory } from "lucide-react";

export function productColorText(p, supplierId = "") {
  const c = p?.color_ref;
  if (!c) return "";
  const list = supplierVersions(p, supplierId);
  const sup = list.map((v) => `${v.supplier_name}: ${v.supplier_color_name || v.supplier_color_code || "—"}`).join(", ");
  return `${c.code} ${c.name}${sup ? ` · ${sup}` : ""}`;
}

export function supplierVersions(p, supplierId = "") {
  const all = p?.supplier_colors || [];
  return supplierId ? all.filter((v) => v.supplier_id === supplierId) : all;
}

export default function ProductColorChip({ product: p, supplierId = "", compact = false, className = "", testId }) {
  const c = p?.color_ref;
  if (!c) return null;
  const list = supplierVersions(p, supplierId);
  return (
    <span className={`inline-flex max-w-full flex-wrap items-center gap-1 ${className}`} data-testid={testId || `product-color-${p.id}`}>
      <span className="inline-flex items-center gap-1 rounded-full border border-[#E5E5EA] bg-white px-1.5 py-px text-[10px] text-[#1C1C1E]" title={`Warna internal ${c.code} · ${c.name}`}>
        <span className="inline-block h-2.5 w-2.5 rounded-full border border-black/10" style={{ background: c.hex || "#fff" }} />
        <b className="font-mono">{c.code}</b>{!compact && <span className="text-[#6B6B73]">{c.name}</span>}
      </span>
      {list.map((v) => (
        <span key={`${v.supplier_id}-${v.at || ""}`} className="inline-flex items-center gap-1 rounded-full bg-[#F1E9F7] px-1.5 py-px text-[10px] text-[#6B219A]"
          title={`Versi warna supplier ${v.supplier_name}${v.sample_number ? ` · dari ${v.sample_number}` : ""}`} data-testid={`product-color-supplier-${p.id}-${v.supplier_id}`}>
          <Factory size={9} /> {compact ? "" : `${v.supplier_name}: `}<b>{v.supplier_color_name || "—"}</b>{v.supplier_color_code ? <span className="font-mono">({v.supplier_color_code})</span> : null}
        </span>
      ))}
      {supplierId && list.length === 0 && (
        <span className="rounded-full bg-[#F5F5F7] px-1.5 py-px text-[10px] text-[#8E8E93]" title="Supplier ini belum punya versi warna ACC untuk produk ini">belum ada versi warna supplier ini</span>
      )}
    </span>
  );
}
