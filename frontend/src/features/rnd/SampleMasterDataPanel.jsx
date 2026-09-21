/**
 * SampleMasterDataPanel — "apa yang lahir dari permintaan ini" dalam satu kotak, urut alurnya:
 * Spesifikasi → ACC sampling (kontrak · barang supplier · warna supplier) → SKU produk (varian induk) → Rilis produksi.
 */
import { useState } from "react";
import { Boxes, CheckCircle2, Circle, FileSignature, Package, Palette, Rocket, ClipboardList } from "lucide-react";
import { formatCurrency } from "../../utils/formatters";
import { askReason } from "../../services/confirmService";
import { approveSpec, releaseProduct } from "./rndApi";
import { errMsg, lifecycleMeta, SPEC_STATUS_META } from "./rndMeta";
import ProductColorChip from "../../components/ProductColorChip";

export default function SampleMasterDataPanel({ sample, canDecide, busy, onAct }) {
  const md = sample.master_data || {};
  const dec = sample.decision || {};
  const spec = md.spec;
  const prod = md.product;
  const [sku, setSku] = useState(spec?.sku_hint || "");
  const [showAcc, setShowAcc] = useState(false);
  const decided = !!dec.supplier_id;
  const specOpen = spec && ["draft", "review"].includes(spec.status);
  const myVariant = (md.color?.supplier_variants || []).find((v) => v.supplier_id === dec.supplier_id);

  const doApproveSpec = () => onAct(async () => { await approveSpec(spec.id, { sku, name: spec.title, price: 0, note: `ACC dari permintaan ${sample.number}` }); setShowAcc(false); }, "Spesifikasi di-ACC — SKU produk lahir (belum boleh dijual).");
  const doRelease = async () => {
    const reason = await askReason({ title: "Rilis produk ke produksi", message: `Produk ${prod?.sku} akan boleh dipesan & dijual.`, confirmLabel: "Rilis" });
    if (!reason) return;
    onAct(() => releaseProduct(spec.id, reason), "Produk dirilis ke produksi — boleh dijual.");
  };

  const steps = [
    { key: "spec", icon: ClipboardList, title: "Spesifikasi produk", done: !!spec,
      body: spec ? <>{spec.number} · <span className={`status-pill ${(SPEC_STATUS_META[spec.status] || {}).cls || ""}`}>{(SPEC_STATUS_META[spec.status] || {}).label || spec.status}</span>
        {md.template ? <span className="block text-[10.5px] text-[#6B6B73]">Induk: <b>{md.template.name}</b> → SKU lahir sebagai <b>varian</b></span>
          : <span className="block text-[10.5px] text-[#6B6B73]">Tanpa induk → SKU lahir sebagai produk mandiri</span>}
        {spec.target?.fabric_type && <span className="block text-[10.5px] text-[#6B6B73]">{spec.target.fabric_type}{spec.target.gramasi ? ` · ${spec.target.gramasi} gsm` : ""}{spec.target.lebar ? ` · lebar ${spec.target.lebar} cm` : ""}</span>}</>
        : <span className="text-[#9A9BA3]">tidak ada — isi bagian “Spesifikasi produk” saat membuat permintaan</span> },
    { key: "acc", icon: FileSignature, title: "ACC sampling → kontrak & barang supplier", done: decided,
      body: decided ? <>Pemenang <b>{dec.supplier_name}</b> · {formatCurrency(dec.price || 0)}
        {md.contract?.number ? <span className="block text-[10.5px] text-[#6B6B73]">Kontrak <b>{md.contract.number}</b>{md.supplier_item ? ` · barang supplier ${md.supplier_item.supplier_sku || "terdaftar"}` : ""}</span>
          : <span className="block text-[10.5px] text-[#B26A00]">Kontrak otomatis nonaktif — buat manual di Pembelian.</span>}</>
        : <span className="text-[#9A9BA3]">menunggu keputusan pemenang (tombol Pilih pemenang)</span> },
    ...(md.color ? [{ key: "color", icon: Palette, title: "Warna versi supplier → Pustaka Warna", done: !!myVariant,
      body: <><span className="inline-block h-3 w-3 rounded-full border border-[#E5E5EA] align-middle" style={{ background: md.color.hex || "#fff" }} /> <b>{md.color.code}</b> {md.color.name}
        {myVariant ? <span className="block text-[10.5px] text-[#6B6B73]">Versi {myVariant.supplier_name}: <b>{myVariant.supplier_color_name || "—"}</b>{myVariant.supplier_color_code ? ` (${myVariant.supplier_color_code})` : ""}</span>
          : <span className="block text-[10.5px] text-[#9A9BA3]">nama/kode warna supplier diisi saat ACC sampling</span>}</> }] : []),
    { key: "product", icon: Package, title: "SKU produk di master", done: !!prod,
      body: prod ? <><b className="font-mono">{prod.sku}</b> {prod.name}
        <ProductColorChip product={prod} className="mt-0.5" />
        <span className="block text-[10.5px] text-[#6B6B73]">{md.template ? `Varian dari induk ${md.template.name}` : "Produk mandiri"}{Object.keys(prod.variant_attrs || {}).length ? ` · ${Object.entries(prod.variant_attrs).map(([k, v]) => `${k}: ${v}`).join(", ")}` : ""} · lifecycle <b style={{ color: lifecycleMeta(prod.lifecycle).tone }}>{lifecycleMeta(prod.lifecycle).label}</b></span></>
        : spec ? (dec.master_error ? <span className="text-[#C62828]">Belum lahir: {dec.master_error}</span> : <span className="text-[#9A9BA3]">lahir saat spesifikasi di-ACC</span>)
          : <span className="text-[#9A9BA3]">butuh spesifikasi</span> },
    { key: "release", icon: Rocket, title: "Rilis ke produksi (boleh dijual)", done: prod?.lifecycle === "produksi",
      body: prod?.lifecycle === "produksi" ? "Produk aktif di katalog & boleh dipesan" : <span className="text-[#9A9BA3]">setelah SKU lahir</span> },
  ];

  return (
    <div className="section-card" data-testid="sample-master-data">
      <p className="text-[11px] font-bold uppercase tracking-wide text-[#9A9BA3]">Master data dari permintaan ini</p>
      <ol className="mt-2 grid gap-1.5">
        {steps.map((s) => (
          <li key={s.key} className={`flex gap-2.5 rounded-lg border px-3 py-2 ${s.done ? "border-[#CDE9D6] bg-[#F4FCF6]" : "border-[#EFF0F2] bg-white"}`} data-testid={`sample-master-${s.key}`}>
            {s.done ? <CheckCircle2 size={15} className="mt-0.5 shrink-0 text-[#1A7A3A]" /> : <Circle size={15} className="mt-0.5 shrink-0 text-[#C7C9CF]" />}
            <div className="min-w-0 flex-1 text-[11.5px] text-[#1C1C1E]">
              <p className="flex items-center gap-1.5 font-bold"><s.icon size={12} className="text-[#6B6B73]" /> {s.title}</p>
              <div className="mt-0.5">{s.body}</div>
            </div>
          </li>
        ))}
      </ol>
      {canDecide && decided && specOpen && (
        <div className="mt-2 rounded-lg border border-[#BFD7FF] bg-[#F6F9FF] p-2.5" data-testid="sample-master-acc-spec">
          {!showAcc ? (
            <button className="primary-button !py-1.5 text-[11px]" disabled={busy} data-testid="sample-master-acc-spec-button" onClick={() => setShowAcc(true)}>
              <Package size={12} /> ACC spesifikasi → lahirkan SKU produk
            </button>
          ) : (
            <div className="flex flex-wrap items-end gap-2">
              <label className="block flex-1 min-w-[160px]">
                <span className="mb-1 block text-[10.5px] font-semibold text-[#6B6B73]">Kode SKU (kosong = otomatis)</span>
                <input className="field" value={sku} onChange={(e) => setSku(e.target.value.toUpperCase())} data-testid="sample-master-sku-input" />
              </label>
              <button className="primary-button !py-1.5 text-[11px]" disabled={busy} data-testid="sample-master-acc-spec-confirm" onClick={doApproveSpec}>Lahirkan SKU</button>
              <button className="secondary-button !py-1.5 text-[11px]" onClick={() => setShowAcc(false)}>Batal</button>
            </div>
          )}
        </div>
      )}
      {canDecide && prod && prod.lifecycle !== "produksi" && spec && (
        <button className="secondary-button mt-2 !py-1.5 text-[11px]" disabled={busy} data-testid="sample-master-release-button" onClick={doRelease}>
          <Rocket size={12} /> Rilis {prod.sku} ke produksi
        </button>
      )}
      <p className="mt-2 flex items-center gap-1 text-[10px] text-[#9A9BA3]"><Boxes size={10} /> Semua master data di atas juga terlihat di Katalog Produk, Pustaka Warna & Master Pembelian.</p>
    </div>
  );
}
