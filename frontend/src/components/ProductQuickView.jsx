import { useEffect, useMemo, useState } from "react";
import { X, Plus, Minus, ShoppingBag, Printer, Layers, Scissors } from "lucide-react";
import { formatCurrency, formatQty } from "../utils/formatters";
import { variantLabel } from "../utils/variants";
import VariantAxisPicker from "./VariantAxisPicker";
import { ProductGallery } from "./ProductGallery";
import LabelPrinterModal from "./LabelPrinterModal";
import RollPicker from "./RollPicker";
import RollReconcileSheet from "./RollReconcileSheet";
import { overlayDismiss } from "@/utils/overlayDismiss";
import { blocksOrder, lifecycleLabel, notOrderableReason } from "../utils/lifecycle";
import { pickPrice, sourceMeta } from "../hooks/useEffectivePrices";
import { sampleLimit, clampSampleQty } from "../utils/sampleOrder";

/**
 * ProductQuickView — popup (desktop) detail produk + pemilih varian.
 * SALES REVAMP V2:
 *  - Mode "Per Yard" (qty) ATAU "Beli per Roll" (pilih roll spesifik, FEFO + paginasi).
 *  - Inventory POS = TOTAL GLOBAL saja (tanpa breakdown per gudang/lot/entitas).
 * Satuan FIXED ke base_unit (F2 UoM SSOT). z-[140].
 *
 * FASE F — varian yang belum dirilis ke produksi tidak bisa ditambahkan; alasannya
 * ditulis di layar beserta jalan keluarnya (bukan sekadar tombol mati).
 */
export default function ProductQuickView({ open, group, specialMap = {}, onAdd, onClose,
  entityId = "", rndEnforcement = "block", allowRollPick = true, cartKind = "" }) {
  const variants = useMemo(() => group?.variants || [], [group]);
  const [selectedId, setSelectedId] = useState(null);
  const [qty, setQty] = useState(1);
  const [mode, setMode] = useState("qty");      // "qty" | "roll"
  // REVISI SAMPEL — jenis pesanan dipilih SETELAH bahan, SEBELUM qty: "regular" (PO biasa) | "sample".
  // Keranjang hanya boleh satu jenis; kalau sudah berisi, jenisnya mengikuti keranjang.
  const [orderKind, setOrderKind] = useState(cartKind || "regular");
  const kindLocked = !!cartKind;
  const [showLabel, setShowLabel] = useState(false);
  const [showReconcile, setShowReconcile] = useState(false);   // C2 — genapkan roll

  // Pilih varian default saat popup dibuka.
  useEffect(() => {
    if (!open || variants.length === 0) return;
    const firstAvail = variants.find((v) => Number(v.available_qty || 0) > 0) || variants[0];
    setSelectedId(firstAvail.id);
    setQty(1);
    setMode("qty");
    setOrderKind(cartKind || "regular");
    setShowReconcile(false); setShowLabel(false);
  }, [open, group?.key]); // eslint-disable-line react-hooks/exhaustive-deps

  const selected = useMemo(
    () => variants.find((v) => v.id === selectedId) || null,
    [variants, selectedId]
  );

  const axisMode = variants.length > 1;

  if (!open || !group || !variants.length) return null;

  const special = selected ? pickPrice(specialMap[selected.id], qty) : null;
  const baseUnit = selected?.base_unit || "";
  // F1b — harga yang ditampilkan = harga EFEKTIF pelanggan (khusus → pelanggan → PT → umum).
  const unitPrice = special && special.price != null
    ? Number(special.price) : Number(selected?.price || 0);
  const priceSrc = special ? sourceMeta(special.source) : null;
  const avail = Number(selected?.available_qty || 0);
  const reserved = Number(selected?.reserved_qty || 0);
  const rollCount = Number(selected?.roll_count || 0);
  // F3 — deskripsi ikut varian terpilih; fallback ke deskripsi grup (rep).
  const description = selected ? (selected.description || group.description || "").trim() : "";
  const availState = avail <= 0 ? "habis" : avail <= 40 ? "low" : "ready";
  const availPill = { habis: "status-cancelled", low: "status-waiting_approval", ready: "status-confirmed" }[availState];
  const availLabel = { habis: "Habis", low: "Stok rendah", ready: "Tersedia" }[availState];
  const lineTotal = unitPrice * (Number(qty) || 0);
  const isSampleKind = orderKind === "sample";
  const limit = selected ? sampleLimit(selected) : null;
  const step = (d) => setQty((q) => {
    const next = Number(q || 1) + d;
    if (isSampleKind) return Math.max(0.5, Math.min(limit?.max_qty || 5, next));
    return Math.max(1, next);
  });
  const pickKind = (k) => {
    if (kindLocked) return;
    setOrderKind(k);
    if (k === "sample") { setMode("qty"); setQty(selected ? sampleLimit(selected).max_qty : 5); }
    else setQty(1);
  };
  // FASE F — varian terpilih belum sah dijual?
  const blocked = !selected || blocksOrder(selected, rndEnforcement);
  const chooseVariant = v => { setSelectedId(v?.id || null); setMode("qty"); setShowReconcile(false); setShowLabel(false); };

  return (
    <div data-testid="product-quickview" className="fixed inset-0 z-[140] flex items-center justify-center bg-black/50 p-4" {...overlayDismiss(onClose)}>
      <div className="flex max-h-[90vh] w-full max-w-[560px] flex-col overflow-hidden rounded-xl bg-white shadow-2xl" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="flex items-start justify-between gap-3 border-b border-[#EFF0F2] px-4 py-3">
          <div className="min-w-0">
            <p className="text-[10.5px] font-bold uppercase tracking-wide text-[#0058CC]">
              {group.category}{group.isMulti ? ` · ${variants.length} varian` : ""}
            </p>
            <h2 data-testid="quickview-product-name" className="text-[16px] font-bold leading-tight">{group.name}</h2>
          </div>
          <button data-testid="quickview-close" className="icon-button" onClick={onClose} aria-label="Tutup"><X size={18} /></button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          <div className="grid gap-3 sm:grid-cols-[180px_1fr]">
            <div className="relative">
              <ProductGallery product={selected} testId="quickview-gallery" compact />
              {selected && <span data-testid="quickview-stock-status" className={`status-pill ${availPill} absolute left-2 top-2`}>{availLabel}</span>}
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 content-start">
              <Stat label="Tersedia" value={selected ? `${formatQty(avail)} ${baseUnit}` : "—"} tone="#126E2C" testId="quickview-available" />
              <Stat label="Roll" value={selected ? `${rollCount} roll` : "—"} tone="#1C1C1E" testId="quickview-roll-count" />
              <Stat label="Dipesan" value={selected ? `${formatQty(reserved)} ${baseUnit}` : "—"} tone="#6B219A" testId="quickview-reserved" />
              {/* F1b — kotak harga menampilkan harga EFEKTIF pelanggan; kalau berbeda dari
                  harga umum, lencana di bawah menjelaskan asalnya. Dulu kotak ini selalu
                  harga umum sehingga satu popup memperlihatkan dua harga berbeda. */}
              <Stat label={`Harga/${baseUnit}`}
                value={selected ? formatCurrency(unitPrice) : "—"}
                tone={special && special.price != null && Number(special.price) !== Number(selected?.price || 0) ? "#0058CC" : "#1C1C1E"}
                small testId="quickview-base-price" />
            </div>
          </div>

          {/* Pemilih varian — M0: dua sumbu terpisah (Warna + Grade) */}
          {axisMode ? (
            <VariantAxisPicker variants={variants} selectedId={selectedId} onSelect={chooseVariant} testIdPrefix="quickview" />
          ) : group.isMulti ? (
            <div>
              <label className="mb-1 flex items-center gap-1 text-[10px] font-bold uppercase tracking-wide text-[#6B6B73]"><Layers size={11} /> Pilih Varian</label>
              <div className="flex flex-wrap gap-2" data-testid="quickview-variant-list">
                {variants.map((v) => {
                  const va = Number(v.available_qty || 0);
                  const active = v.id === selected?.id;
                  return (
                    <button key={v.id} data-testid={`quickview-variant-${v.id}`} onClick={() => chooseVariant(v)}
                      className={`rounded-lg border px-2.5 py-1.5 text-left transition ${active ? "border-[#0058CC] bg-[#EAF2FF] ring-1 ring-[#0058CC]" : "border-[#E5E5EA] bg-white hover:border-[#9A9BA3]"}`}>
                      <span className="block text-[12px] font-semibold text-[#1C1C1E]">{variantLabel(v)}</span>
                      <span className={`block text-[10px] ${va <= 0 ? "text-[#A8221A]" : "text-[#6B6B73]"}`}>
                        {va <= 0 ? "Habis" : `Stok ${formatQty(va)}`} · {formatCurrency(v.price)}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>
          ) : null}

          {priceSrc && ["special_approval", "customer"].includes(special.source) && (
            <p data-testid="quickview-special"
              className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10.5px] font-bold"
              style={{ background: priceSrc.bg, color: priceSrc.fg }}>
              {priceSrc.label} {formatCurrency(unitPrice)}
              {Number(special.normal_price) > unitPrice && (
                <span className="font-normal text-[#8E8E93] line-through">{formatCurrency(special.normal_price)}</span>
              )}
            </p>
          )}
          {special?.special_blocked_by_min && (
            <p data-testid="quickview-min-qty" className="text-[10.5px] font-semibold text-[#B26A00]">
              Harga khusus {formatCurrency(special.special_price)} berlaku dari {formatQty(special.min_quantity)} {baseUnit}
            </p>
          )}
          <p className="text-[11.5px] text-[#3C3C43]">
            <span data-testid="quickview-sku" className="font-semibold text-[#0058CC]">{selected?.sku || "—"}</span>{selected && ` · ${selected.color || ""} • ${selected.motif || ""} • Grade ${selected.grade || "—"}`}
          </p>
          {selected?.base_fabric_name && (
            <p data-testid="quickview-base-fabric" className="text-[11px] text-[#6B6B73]">Kain dasar: <b className="text-[#1C1C1E]">{selected.base_fabric_name}</b></p>
          )}

          {/* FASE F — barang hasil R&D yang belum dirilis: alasan + jalan keluar */}
          {blocked && (
            <div data-testid="quickview-not-orderable"
              className="rounded-lg border border-[#F0D7A8] bg-[#FFF6E5] p-2.5 text-[11.5px] leading-relaxed text-[#8C4A00]">
              {selected ? <><b>{lifecycleLabel(selected)} — belum boleh dijual.</b> {notOrderableReason(selected)}</> : "Kombinasi tidak tersedia. Tidak ada SKU yang dipilih."}
            </div>
          )}

          {/* F3 — Deskripsi produk (ikut varian terpilih) */}
          {description && (
            <div data-testid="quickview-description" className="rounded-lg border border-[#EFF0F2] bg-[#FAFBFC] p-2.5 text-[11.5px] leading-relaxed text-[#3C3C43] whitespace-pre-line">
              {description}
            </div>
          )}

          {/* REVISI SAMPEL — LANGKAH WAJIB setelah pilih bahan: Order Biasa (PO) atau Order Sampel.
              Sampel dibatasi: woven maks 5 yard · knitting maks 2 kg (default = maksimum). */}
          {selected && !blocked && (
            <div data-testid="quickview-kind-toggle" className={`rounded-lg border p-2 ${isSampleKind ? "border-[#F3D9A4] bg-[#FFF9EC]" : "border-[#EFF0F2] bg-[#FAFBFC]"}`}>
              <p className="mb-1.5 text-[10px] font-bold uppercase tracking-wide text-[#6B6B73]">Jenis pesanan {kindLocked && <span className="ml-1 rounded-full bg-[#E5E5EA] px-1.5 py-0.5 text-[9px] normal-case text-[#3C3C43]">mengikuti keranjang</span>}</p>
              <div className="grid grid-cols-2 gap-2">
                <button type="button" data-testid="quickview-kind-regular" onClick={() => pickKind("regular")} disabled={kindLocked && orderKind !== "regular"}
                  className={`flex items-center justify-center gap-1.5 rounded-md border px-3 py-2 text-[12px] font-semibold transition disabled:opacity-40 ${!isSampleKind ? "border-[#0058CC] bg-[#EAF2FF] text-[#0058CC]" : "border-[#E5E5EA] bg-white text-[#3C3C43] hover:border-[#9A9BA3]"}`}>
                  <ShoppingBag size={13} /> Pesanan Biasa (PO)
                </button>
                <button type="button" data-testid="quickview-kind-sample" onClick={() => pickKind("sample")} disabled={kindLocked && orderKind !== "sample"}
                  className={`flex items-center justify-center gap-1.5 rounded-md border px-3 py-2 text-[12px] font-semibold transition disabled:opacity-40 ${isSampleKind ? "border-[#9A5B00] bg-[#FFF3D6] text-[#9A5B00]" : "border-[#E5E5EA] bg-white text-[#3C3C43] hover:border-[#9A9BA3]"}`}>
                  <Scissors size={13} /> Pesanan Sampel
                </button>
              </div>
              {isSampleKind && limit && (
                <p data-testid="quickview-sample-limit" className="mt-1.5 text-[10.5px] text-[#9A5B00]">Sampel kain <b>{limit.label}</b>: maks <b>{limit.max_qty} {limit.unit}</b> per bahan · dipotong gudang dari roll (RFID) · gratis/berbayar dipilih saat checkout.</p>
              )}
            </div>
          )}

          {/* SALES REVAMP V2 — Pilih cara beli: per yard ATAU per roll.
              KONFIG allocation.roll_pick_sales OFF → sales tidak melihat pilihan roll;
              roll dipilih otomatis (FEFO) dan bisa DIGANTI Admin Sales di detail pesanan. */}
          {allowRollPick && !isSampleKind && (
          <div data-testid="quickview-mode-toggle" className="grid grid-cols-2 gap-2">
            <button type="button" data-testid="quickview-mode-qty" onClick={() => setMode("qty")}
              className={`flex items-center justify-center gap-1.5 rounded-md border px-3 py-2 text-[12px] font-semibold transition ${mode === "qty" ? "border-[#0058CC] bg-[#EAF2FF] text-[#0058CC]" : "border-[#E5E5EA] bg-white text-[#3C3C43] hover:border-[#9A9BA3]"}`}>
              Per {baseUnit}
            </button>
            <button type="button" data-testid="quickview-mode-roll" onClick={() => setMode("roll")} disabled={rollCount <= 0 || blocked}
              className={`flex items-center justify-center gap-1.5 rounded-md border px-3 py-2 text-[12px] font-semibold transition disabled:opacity-40 ${mode === "roll" ? "border-[#0058CC] bg-[#EAF2FF] text-[#0058CC]" : "border-[#E5E5EA] bg-white text-[#3C3C43] hover:border-[#9A9BA3]"}`}>
              <Scissors size={13} /> Beli per Roll
            </button>
          </div>
          )}

          {mode === "qty" ? (
            /* Qty + Satuan (FIXED ke base_unit — F2 UoM SSOT) */
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="mb-1 block text-[10px] font-bold uppercase tracking-wide text-[#8E8E93]">{isSampleKind ? `Panjang sampel (maks ${limit?.max_qty} ${limit?.unit})` : "Jumlah (Qty)"}</label>
                <div className={`flex items-center rounded-md border ${isSampleKind ? "border-[#F3D9A4]" : "border-[#E5E5EA]"}`}>
                  <button data-testid="quickview-qty-minus" className="px-3 py-2 text-[#6B6B73] hover:bg-[#F5F5F7]" onClick={() => step(-1)} aria-label="Kurangi"><Minus size={14} /></button>
                  <input data-testid="quickview-qty-input" type="number" min={isSampleKind ? "0.1" : "1"} step={isSampleKind ? "0.5" : "1"} max={isSampleKind ? limit?.max_qty : undefined}
                    className="w-full border-x border-[#E5E5EA] bg-transparent py-2 text-center text-[14px] outline-none" value={qty}
                    onChange={(e) => setQty(isSampleKind ? clampSampleQty(selected, e.target.value) || 0.5 : Math.max(1, Number(e.target.value) || 1))} />
                  <button data-testid="quickview-qty-plus" className="px-3 py-2 text-[#6B6B73] hover:bg-[#F5F5F7]" onClick={() => step(1)} aria-label="Tambah"><Plus size={14} /></button>
                </div>
              </div>
              <div className="min-w-0">
                <label className="mb-1 block text-[10px] font-bold uppercase tracking-wide text-[#8E8E93]">Satuan</label>
                <div data-testid="quickview-unit-fixed" className="field flex items-center bg-[#F5F5F7] font-semibold text-[#3C3C43]">{baseUnit}</div>
                <p className="mt-1 text-[10px] text-[#9A9BA3]">{rollCount} roll · panjang per roll bervariasi</p>
              </div>
            </div>
          ) : selected && !blocked ? (
            <RollPicker
              productId={selected.id}
              entityId={entityId}
              unitPrice={unitPrice}
              baseUnit={baseUnit}
              onConfirm={(rollLines, snapshot, totalQty) => {
                if (blocked) return;
                onAdd(selected, totalQty, baseUnit, { purchase_mode: "roll", roll_lines: rollLines, rolls_snapshot: snapshot });
                onClose();
              }}
            />
          ) : null}
        </div>

        {/* Footer (hanya mode qty — mode roll punya tombol konfirmasi sendiri) */}
        {mode === "qty" && (
          <div className="border-t border-[#EFF0F2] px-4 py-3">
            <div className="mb-2 flex items-center justify-between">
              <span className="text-[11px] font-bold uppercase tracking-wide text-[#6B6B73]">Subtotal ({qty} {baseUnit})</span>
              <span data-testid="quickview-line-total" className="text-[16px] font-bold tabular-nums">{selected ? formatCurrency(lineTotal) : "—"}</span>
            </div>
            <div className="flex gap-2">
              {isSampleKind ? (
                <button data-testid="quickview-sample-button" className="primary-button flex-1 justify-center py-2.5 !bg-[#9A5B00] hover:!bg-[#7A4700]" disabled={avail <= 0 || blocked || !(qty > 0)}
                  title="Pesanan Sampel — dipotong gudang dari roll; gratis/berbayar dipilih saat checkout"
                  onClick={() => { if (blocked || avail <= 0) return; onAdd(selected, clampSampleQty(selected, qty), baseUnit, { is_sample: true }); onClose(); }}>
                  <Scissors size={15} /> {avail <= 0 ? "Stok Habis" : `Tambah Sampel (${qty} ${baseUnit})`}
                </button>
              ) : (
                <button data-testid="quickview-add-button" className="primary-button flex-1 justify-center py-2.5" disabled={avail <= 0 || blocked} onClick={() => {
                  if (blocked || avail <= 0) return;
                  if (rollCount > 0 && allowRollPick) { setShowReconcile(true); }
                  else { onAdd(selected, qty, baseUnit); onClose(); }
                }}>
                  <ShoppingBag size={15} /> {!selected ? "Kombinasi tidak tersedia" : blocked ? "Belum boleh dijual" : avail <= 0 ? "Stok Habis" : "Tambah ke Keranjang"}
                </button>
              )}
              <button data-testid="quickview-print-button" className="secondary-button px-3" disabled={!selected} onClick={() => setShowLabel(true)} aria-label="Cetak Label"><Printer size={15} /></button>
            </div>
          </div>
        )}

        {showLabel && selected && <LabelPrinterModal product={selected} warehouse={null} onClose={() => setShowLabel(false)} />}

        {selected && !blocked && <RollReconcileSheet
          key={selected.id}
          open={showReconcile}
          productId={selected.id}
          entityId={entityId}
          targetQty={qty}
          unitPrice={unitPrice}
          baseUnit={baseUnit}
          onClose={() => setShowReconcile(false)}
          onConfirm={(rollLines, totalQty, snapshot) => {
            if (blocked) return;
            setShowReconcile(false);
            onAdd(selected, totalQty, baseUnit, { purchase_mode: "roll", roll_lines: rollLines, rolls_snapshot: snapshot });
            onClose();
          }}
        />}
      </div>
    </div>
  );
}

function Stat({ label, value, tone, testId, small }) {
  return (
    <div className="rounded-md border border-[#EFF0F2] bg-[#FAFBFC] p-2">
      <p className="text-[9.5px] font-bold uppercase text-[#6B6B73]">{label}</p>
      <p data-testid={testId} className={`${small ? "text-[12px]" : "text-[15px]"} font-bold leading-tight`} style={{ color: tone }}>{value}</p>
    </div>
  );
}
