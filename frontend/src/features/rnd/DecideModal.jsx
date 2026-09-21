/**
 * DecideModal — pilih SUPPLIER PEMENANG sample (ACC sampling).
 * DI SINI (bukan di awal) nama & kode warna versi supplier diisi, lalu master data yang
 * terbentuk ditampilkan terang-terangan: kontrak harga · barang supplier · warna supplier di pustaka
 * warna · (opsional) ACC spesifikasi → SKU produk lahir sebagai varian induk.
 */
import { useState } from "react";
import MoneyInput from "@/components/MoneyInput";
import { Boxes, FileSignature, Package, Palette, Trophy } from "lucide-react";
import FormModal from "../../components/FormModal";
import KNSelect from "../../components/KNSelect";
import { formatCurrency } from "../../utils/formatters";
import { Field, Footer, Hint } from "./RndField";
import { sampleTypesOf } from "./sampleTypeMeta";

export default function DecideModal({ sample, reasons, onClose, onConfirm, busy }) {
  const accBySupplier = {};
  (sample.rounds || []).forEach((r) => { if (r.result === "acc") accBySupplier[r.supplier_id] = r; });
  const candidates = (sample.participants || []).filter((p) => accBySupplier[p.supplier_id]);
  const spec = sample.spec || null;
  const specOpen = !!spec && ["draft", "review"].includes(spec.status);
  const hasColor = !!sample.color_target?.color_id;
  const isLabdip = sampleTypesOf(sample).includes("labdip");

  const [supplierId, setSupplierId] = useState(candidates[0]?.supplier_id || "");
  const [reasonCode, setReasonCode] = useState(reasons?.[0]?.value || "");
  const [price, setPrice] = useState("");
  const [supplierSku, setSupplierSku] = useState("");
  const [supplierUom, setSupplierUom] = useState(sample.unit || "");
  const [moq, setMoq] = useState("");
  const [lead, setLead] = useState("");
  const [note, setNote] = useState("");
  const [colorName, setColorName] = useState("");
  const [colorCode, setColorCode] = useState("");
  const [approveSpec, setApproveSpec] = useState(specOpen);
  const [productSku, setProductSku] = useState(spec?.sku_hint || "");
  const [productName, setProductName] = useState(spec?.title || "");

  const supplier = candidates.find((p) => p.supplier_id === supplierId);
  const colorOk = !hasColor || !isLabdip || colorName.trim() || colorCode.trim();

  const body = {
    supplier_id: supplierId, reason_code: reasonCode, note,
    price: price || 0, supplier_sku: supplierSku, supplier_uom: supplierUom,
    moq: moq || 0, lead_time_days: lead || 0,
    supplier_color_name: colorName, supplier_color_code: colorCode,
    approve_spec: !!(spec && specOpen && approveSpec), product_sku: productSku, product_name: productName,
  };
  return (
    <FormModal open onClose={onClose} size="lg" testId="decide-modal" icon={Trophy}
      title="ACC Sampling · Pilih Supplier Pemenang" subtitle={`${sample.number} · ${sample.title}`}
      footer={<Footer onClose={onClose} onConfirm={() => onConfirm(body)} busy={busy} icon={Trophy} testId="decide-confirm"
        confirmLabel="ACC & bentuk master data" disabled={!supplierId || !reasonCode || !price || !colorOk}
        title={!colorOk ? "Nama/kode warna versi supplier wajib untuk labdip" : ""} />}>
      <div className="grid gap-3">
          {candidates.length === 0 ? (
            <Hint tone="warn" testId="decide-no-candidate">Belum ada supplier yang hasilnya <b>ACC</b>. Nilai dulu hasil sample-nya — pemenang hanya boleh dipilih dari supplier yang sudah ACC.</Hint>
          ) : (
            <div className="grid gap-3 lg:grid-cols-[minmax(0,1.1fr)_minmax(260px,0.9fr)]">
              <div className="space-y-3">
                <Block step={1} title="Keputusan">
                  <Field label="Supplier pemenang *">
                    <KNSelect data-testid="decide-supplier" className="field" value={supplierId}
                      options={candidates.map((p) => ({ value: p.supplier_id, label: `${p.supplier_name} · skor ${accBySupplier[p.supplier_id]?.score ?? "—"}` }))}
                      onValueChange={setSupplierId} />
                  </Field>
                  <Field label="Alasan keputusan *">
                    <KNSelect data-testid="decide-reason" className="field" value={reasonCode}
                      options={(reasons || []).map((r) => ({ value: r.value, label: r.label }))} onValueChange={setReasonCode} />
                  </Field>
                  <Field label="Catatan">
                    <input className="field" data-testid="decide-note" value={note} onChange={(e) => setNote(e.target.value)} placeholder="mis. ΔE 0.9 paling dekat" />
                  </Field>
                </Block>

                <Block step={2} title="Data supplier (diisi saat ACC — bukan di awal)">
                  <div className="grid gap-2.5 sm:grid-cols-2">
                    <Field label="Harga kesepakatan per satuan (Rp) *">
                      <MoneyInput className="field" testId="decide-price" value={price} onChange={(v) => setPrice(v)} placeholder="42500" />
                    </Field>
                    <Field label="Kode barang versi supplier">
                      <input className="field" data-testid="decide-supplier-sku" value={supplierSku} onChange={(e) => setSupplierSku(e.target.value)} placeholder="SUP-KTN-135" />
                    </Field>
                    {hasColor && (
                      <>
                        <Field label={`Nama warna versi supplier${isLabdip ? " *" : ""}`}>
                          <input className="field" data-testid="decide-supplier-color-name" value={colorName} onChange={(e) => setColorName(e.target.value)} placeholder="mis. Navy 07" />
                        </Field>
                        <Field label={`Kode warna versi supplier${isLabdip ? " *" : ""}`}>
                          <input className="field" data-testid="decide-supplier-color-code" value={colorCode} onChange={(e) => setColorCode(e.target.value)} placeholder="mis. NV-07" />
                        </Field>
                      </>
                    )}
                    <Field label="Satuan supplier"><input className="field" data-testid="decide-supplier-uom" value={supplierUom} onChange={(e) => setSupplierUom(e.target.value)} placeholder="meter" /></Field>
                    <Field label="MOQ"><input className="field" data-testid="decide-moq" value={moq} onChange={(e) => setMoq(e.target.value)} placeholder="100" /></Field>
                    <Field label="Lead time (hari)"><input className="field" data-testid="decide-lead" value={lead} onChange={(e) => setLead(e.target.value)} placeholder="14" /></Field>
                  </div>
                  {hasColor && (
                    <p className="mt-1.5 text-[10.5px] text-[#6B6B73]">
                      Warna target <b>{sample.color_target.code} · {sample.color_target.name}</b> — nama/kode versi supplier disimpan ke <b>Pustaka Warna</b> sebagai versi supplier ini.
                    </p>
                  )}
                </Block>

                {spec && (
                  <Block step={3} title="Master produk">
                    {specOpen ? (
                      <>
                        <label className="flex items-start gap-2 text-[11.5px]">
                          <input type="checkbox" className="mt-0.5" checked={approveSpec} onChange={(e) => setApproveSpec(e.target.checked)} data-testid="decide-approve-spec" />
                          <span>Sekaligus <b>ACC spesifikasi {spec.number}</b> → SKU produk lahir (status <i>disetujui</i>, belum dijual). Rilis ke produksi dilakukan terpisah.</span>
                        </label>
                        {approveSpec && (
                          <div className="mt-2 grid gap-2.5 sm:grid-cols-2">
                            <Field label="Kode SKU produk (kosong = otomatis)">
                              <input className="field" data-testid="decide-product-sku" value={productSku} onChange={(e) => setProductSku(e.target.value.toUpperCase())} placeholder="KTN-150-NAVY" />
                            </Field>
                            <Field label="Nama produk">
                              <input className="field" data-testid="decide-product-name" value={productName} onChange={(e) => setProductName(e.target.value)} />
                            </Field>
                          </div>
                        )}
                      </>
                    ) : (
                      <p className="text-[11.5px] text-[#3C3C43]">Spesifikasi {spec.number} sudah <b>{spec.status === "approved" ? `disetujui — produk ${spec.product_sku || ""}` : spec.status}</b>.</p>
                    )}
                  </Block>
                )}
              </div>

              <aside className="rounded-xl border border-[#BFD7FF] bg-[#F6F9FF] p-3" data-testid="decide-impact">
                <p className="mb-2 text-[10.5px] font-bold uppercase tracking-wide text-[#0058CC]">Master data yang akan terbentuk</p>
                <ul className="space-y-2 text-[11.5px] text-[#1C1C1E]">
                  <Impact icon={FileSignature} title="Kontrak harga pembelian" on>
                    {supplier?.supplier_name || "—"} · {price ? formatCurrency(Number(price) || 0) : "harga belum diisi"} / {supplierUom || sample.unit || "satuan"}
                    <span className="block text-[10px] text-[#6B6B73]">Asal harga: {sample.number} → dipakai PO. Cek di Pembelian → Master Pembelian.</span>
                  </Impact>
                  <Impact icon={Boxes} title="Barang supplier" on>
                    {supplierSku || "kode otomatis dari SKU produk"}{moq ? ` · MOQ ${moq}` : ""}{lead ? ` · ${lead} hari` : ""}
                  </Impact>
                  <Impact icon={Palette} title="Warna versi supplier → Pustaka Warna" on={hasColor && (colorName || colorCode)}>
                    {hasColor ? (colorName || colorCode ? `${sample.color_target.code}: ${colorName}${colorCode ? ` (${colorCode})` : ""}` : "isi nama/kode warna supplier") : "permintaan tanpa warna target"}
                  </Impact>
                  <Impact icon={Package} title="Produk (SKU) di master" on={spec && specOpen && approveSpec}>
                    {!spec ? "tidak ada spesifikasi — buat lewat form permintaan" : specOpen ? (approveSpec ? `${productSku || "SKU otomatis"} — ${productName || spec.title}` : "tidak di-ACC sekarang") : `sudah ada: ${spec.product_sku || spec.status}`}
                    {spec?.template_id && <span className="block text-[10px] text-[#6B6B73]">Menjadi VARIAN dari induk yang dipilih di spesifikasi.</span>}
                    {spec && !spec.template_id && <span className="block text-[10px] text-[#6B6B73]">Tanpa induk — lahir sebagai produk konsep mandiri.</span>}
                  </Impact>
                </ul>
              </aside>
            </div>
          )}
      </div>
    </FormModal>
  );
}

function Block({ step, title, children }) {
  return (
    <section className="rounded-xl border border-[#EFF0F2] bg-[#FAFBFC] p-3">
      <p className="mb-2 flex items-center gap-2 text-[12px] font-bold text-[#1C1C1E]">
        <span className="flex h-5 w-5 items-center justify-center rounded-full bg-[#0058CC] text-[10px] text-white">{step}</span>{title}
      </p>
      <div className="space-y-2.5">{children}</div>
    </section>
  );
}
function Impact({ icon: Icon, title, on, children }) {
  return (
    <li className={`flex gap-2 rounded-lg border bg-white px-2.5 py-2 ${on ? "border-[#CDE9D6]" : "border-[#EFF0F2] opacity-70"}`}>
      <Icon size={14} className={`mt-0.5 shrink-0 ${on ? "text-[#1A7A3A]" : "text-[#9A9BA3]"}`} />
      <div className="min-w-0"><p className="font-bold">{title}</p><p className="text-[11px] text-[#3C3C43]">{children}</p></div>
    </li>
  );
}
