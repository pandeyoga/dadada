/**
 * ProductMasterForm (Fase A · PS-01/02/03/09/15) — form master produk tekstil.
 *
 * Dipisah dari `AdminView.jsx` (batas ukuran file) dan ditingkatkan agar patuh:
 *   R1  — stage/fabric_type/grade WAJIB dropdown dari registry (`useDomainEnums`)
 *   D-02 — fabric_type wajib sejak stage `yarn`
 *   D-22 — GSM + lebar wajib ≥ grey (woven); `yarn_count` wajib di stage yarn;
 *          untuk knit field terukur hanya disarankan (peringatan, tidak memblokir)
 *   PS-15 — semua input angka menerima koma-desimal via <DecimalInput>
 *
 * Props: product, setProduct, editingProductId, productError, saving,
 *        categoryOptions, onSave, onCancel, addConv, updateConv, removeConv
 */
import MoneyInput from "../../../components/MoneyInput";
import { formatCurrency } from "../../../utils/formatters";
import { AlertTriangle, CheckCircle2, Info, Plus, Save, XCircle } from "lucide-react";
import DecimalInput from "../../../components/DecimalInput";
import KNSelect from "../../../components/KNSelect";
import PantoneFinder from "../../../components/PantoneFinder";
import useDomainEnums from "../../../hooks/useDomainEnums";
import useUomConversions from "../../../hooks/useUomConversions";    // FASE U
import { uomSelectOptions } from "../../../utils/uomCatalog";        // FASE U
import useCatalogMasters from "../../../hooks/useCatalogMasters";
import { parseDecimal } from "../../../utils/decimalInput";

const TEXT_FIELDS = [
  ["sku", "SKU / kode produk", "mis. BTK-MEGA-001"], ["name", "Nama produk", "mis. Batik Mega Mendung Premium"],
  ["variant", "Varian", "mis. Premium"],
];
// Motif & pemasok dipilih dari master (Master Desain/motif terpakai; Master Supplier) — bukan ketik bebas.
const MASTER_SELECT_FIELDS = [["motif", "Motif", "motifOptions"], ["supplier", "Pabrik / pemasok", "supplierOptions"]];
const MONEY_FIELDS = [
  ["price", "Harga jual dasar (per satuan dasar)", "Harga acuan untuk pesanan/penawaran BARU. Pesanan yang sudah dibuat tetap memakai harga saat dibuat. Harga per badan usaha & per pelanggan diatur di tab Harga."],
];
const HPP_SOURCE_LABEL = { roll: "rata-rata tertimbang roll (dari PO/penerimaan)", roll_partial: "rata-rata roll (sebagian roll belum ber-cost)",
  harga_pokok: "cadangan HPP lama — belum ada penerimaan PO", price: "belum ada PO — sementara memakai harga jual", none: "belum ada penerimaan PO" };

export default function ProductMasterForm({
  product, setProduct, editingProductId, productError, saving = false,
  categoryOptions = [], salesOwners = [], onSave, onCancel, addConv, updateConv, removeConv,
}) {
  const { loading, error: enumError, options, labelOf, fieldRules, fieldLabels } = useDomainEnums();
  // FASE U — SATUAN DASAR produk dari MASTER SATUAN (`uoms`). Ini pemilih satuan yang
  // paling penting di seluruh aplikasi: `products.base_unit` adalah satuan kendali yang
  // dipakai stok, PO, SO, dan konversi. Sebelum ini daftarnya diketik 7 nilai di berkas
  // ini, sehingga pemilik yang menambah `PANEL` di master TIDAK bisa membuat satu pun
  // produk ber-satuan panel — masternya ada, gunanya tidak.
  useUomConversions();
  const baseUnitOptions = uomSelectOptions({
    dimensions: ["length", "weight", "count"],
    extra: [product.base_unit].filter(Boolean),
  });
  const set = (patch) => setProduct({ ...product, ...patch });
  const masters = useCatalogMasters({ current: { motif: product.motif, supplier: product.supplier } });

  const isExclusive = (product.exclusivity || "umum") === "sales_tertentu";
  const ownerIds = product.owner_sales_ids || [];
  const toggleOwner = (id) => {
    const next = ownerIds.includes(id) ? ownerIds.filter((x) => x !== id) : [...ownerIds, id];
    set({ owner_sales_ids: next });
  };

  const stage = product.stage || "finished";
  const fabric = product.fabric_type || "";
  const rules = fieldRules(stage, fabric);
  const isYarn = stage === "yarn";
  const gsm = parseDecimal(product.gramasi);
  const lebar = parseDecimal(product.lebar);
  const kgPerMeter = (gsm || 0) * (lebar || 0) / 1000;

  const valueOf = (f) => (f === "gramasi" ? gsm : f === "lebar" ? lebar : product[f]);
  const missing = rules.required.filter((f) => {
    const v = valueOf(f);
    return typeof v === "number" ? !(v > 0) : !String(v || "").trim();
  });
  const advisory = rules.recommended.filter((f) => {
    const v = valueOf(f);
    return typeof v === "number" ? !(v > 0) : !String(v || "").trim();
  });
  const req = (f) => rules.required.includes(f);
  const lbl = (f) => fieldLabels[f] || f;

  return (
    <div className="grid gap-2" data-testid="admin-product-form">
      <div className="grid gap-2 sm:grid-cols-2" data-testid="admin-product-identity">
        {TEXT_FIELDS.map(([key, ph, hint]) => (
          <label key={key} className={`grid gap-1 text-[11px] font-semibold text-[#3C3C43] ${key === "name" ? "sm:col-span-2" : ""}`}>
            <span>{ph}{["sku", "name"].includes(key) ? " *" : ""}</span>
            <input data-testid={`admin-product-${key}-input`} className="field" type="text"
              placeholder={hint} value={product[key] ?? ""}
              onChange={(e) => set({ [key]: e.target.value })} />
          </label>
        ))}
        <label className="grid gap-1 text-[11px] font-semibold text-[#3C3C43]"><span>Kategori</span>
          <KNSelect data-testid="admin-product-category-input" className="field"
            value={product.category ?? ""} placeholder="Pilih kategori"
            onValueChange={(v) => set({ category: v })} options={categoryOptions} /></label>
        {MASTER_SELECT_FIELDS.map(([key, ph, src]) => (
          <label key={key} className="grid gap-1 text-[11px] font-semibold text-[#3C3C43]"><span>{ph}</span>
            <KNSelect data-testid={`admin-product-${key}-input`} className="field" searchable
              value={product[key] ?? ""} placeholder={`Pilih ${ph.toLowerCase()}`}
              onValueChange={(v) => set({ [key]: v })} options={masters[src]} /></label>
        ))}
        <label className="grid gap-1 text-[11px] font-semibold text-[#3C3C43]"><span>Satuan dasar *</span>
          <KNSelect data-testid="admin-product-base_unit-input" className="field"
            value={product.base_unit ?? "meter"} placeholder="Satuan Dasar"
            onValueChange={(v) => set({ base_unit: v })} options={baseUnitOptions} />
          <span className="text-[10px] font-normal text-[#8E8E93]">Satuan kendali stok, PO, SO & POS untuk produk ini.</span></label>
        {MONEY_FIELDS.map(([key, ph, hint]) => (
          <label key={key} className="grid gap-1 text-[11px] font-semibold text-[#3C3C43]"><span>{ph}</span>
            <MoneyInput testId={`admin-product-${key}-input`} placeholder="0"
              value={product[key] ?? ""} onChange={(v) => set({ [key]: v })} />
            <span className="text-[10px] font-normal text-[#8E8E93]">{hint}</span></label>
        ))}
        <div className="grid gap-1 text-[11px] font-semibold text-[#3C3C43]" data-testid="admin-product-hpp-readonly">
          <span>Harga pokok (HPP) — otomatis dari pembelian</span>
          <div className="field flex items-center justify-between bg-[#F7F8FA] text-[#1C1C1E]" aria-readonly="true">
            <span data-testid="admin-product-hpp-value">{Number(product.hpp) > 0 ? formatCurrency(product.hpp) : "Belum ada penerimaan PO"}</span>
            <span className="text-[10px] font-normal text-[#8E8E93]">{HPP_SOURCE_LABEL[product.hpp_source] || ""}</span>
          </div>
          <span className="text-[10px] font-normal text-[#8E8E93]">
            Tidak bisa diisi manual. HPP terbentuk dari harga PO pembelian nyata + landed cost saat barang diterima (rata-rata tertimbang per roll); jurnal HPP memakai cost roll aktual.
          </span>
        </div>
      </div>

      {/* ── Panel domain tekstil (Fase A) ─────────────────────────────────── */}
      <div data-testid="admin-product-domain-panel"
        className="grid gap-2 rounded-md border border-[#DCE7FA] bg-[#F6F9FF] p-2.5">
        <p className="text-[11px] font-bold uppercase tracking-wide text-[#0058CC]">
          Spesifikasi Tekstil (wajib)
        </p>
        {enumError && (
          <p data-testid="admin-product-enum-error"
            className="text-[11px] font-semibold text-[#D14343]">{enumError}</p>
        )}
        {loading ? (
          <p data-testid="admin-product-domain-loading" className="text-[11px] text-[#6B6B73]">
            Memuat registry enum domain…
          </p>
        ) : (
          <>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="mb-1 block text-[10px] font-bold uppercase tracking-wide text-[#8E8E93]">
                  Tahap Bahan (stage) *
                </label>
                <KNSelect data-testid="admin-product-stage-input" className="field"
                  value={stage} onValueChange={(v) => set({ stage: v })}
                  options={options("stage")} />
              </div>
              <div>
                <label className="mb-1 block text-[10px] font-bold uppercase tracking-wide text-[#8E8E93]">
                  Jenis Kain (fabric_type) {req("fabric_type") ? "*" : ""}
                </label>
                <KNSelect data-testid="admin-product-fabric_type-input" className="field"
                  value={fabric} placeholder="Pilih woven / knit"
                  onValueChange={(v) => set({ fabric_type: v })} options={options("fabric_type")} />
              </div>
            </div>
            {/* FASE L — LINI PRODUK: pembagian kerja MD (siapa yang mengerjakan &
                papan mana). Sengaja berdampingan dengan Jenis Kain supaya bedanya
                terlihat: jenis kain = FISIKA (menentukan rumus & satuan kendali),
                lini = PEMBAGIAN KERJA. Nilainya dari master (bisa ditambah pemilik),
                dan server menolak kombinasi yang bertentangan (INV-LINE-02). */}
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="mb-1 block text-[10px] font-bold uppercase tracking-wide text-[#8E8E93]">
                  Lini Produk (pembagian kerja)
                </label>
                <KNSelect data-testid="admin-product-line_code-input" className="field"
                  value={product.line_code ?? ""} placeholder="Belum bergolong lini"
                  onValueChange={(v) => set({ line_code: v })}
                  options={options("product_line", [{ value: "", label: "— belum bergolong —" }])} />
                <p className="mt-1 text-[10px] text-[#8E8E93]">
                  Menentukan siapa yang boleh mengerjakannya & chip penyaring di 12 layar.
                  Bukan pengganti Jenis Kain. Tambah lini baru di Pengaturan → Master →
                  Lini Produk.
                </p>
              </div>
            </div>
            {!isYarn && (
            <div className="grid grid-cols-3 gap-2">
              <div>
                <label className="mb-1 block text-[10px] font-bold uppercase tracking-wide text-[#8E8E93]">
                  Grade *
                </label>
                <KNSelect data-testid="admin-product-grade-input" className="field"
                  value={product.grade ?? ""} placeholder="Pilih grade"
                  onValueChange={(v) => set({ grade: v })} options={options("grade")} />
              </div>
              <div>
                <label className="mb-1 block text-[10px] font-bold uppercase tracking-wide text-[#8E8E93]">
                  Gramasi (gsm) {req("gramasi") ? "*" : ""}
                </label>
                <DecimalInput data-testid="admin-product-gramasi-input" placeholder="mis. 180,5"
                  suffix="gsm" min={0} value={product.gramasi ?? ""}
                  invalid={missing.includes("gramasi")}
                  onChange={(v) => set({ gramasi: v })} />
              </div>
              <div>
                <label className="mb-1 block text-[10px] font-bold uppercase tracking-wide text-[#8E8E93]">
                  Lebar (meter) {req("lebar") ? "*" : ""}
                </label>
                <DecimalInput data-testid="admin-product-lebar-input" placeholder="mis. 1,15"
                  suffix="m" min={0} value={product.lebar ?? ""}
                  invalid={missing.includes("lebar")}
                  onChange={(v) => set({ lebar: v })} />
              </div>
            </div>
            )}
            {isYarn && (
              <div className="rounded-md border border-[#DCE7F7] bg-[#F7FAFF] p-2.5 space-y-2" data-testid="admin-product-yarn-fields">
                <p className="text-[10.5px] font-bold uppercase tracking-wide text-[#0058CC]">Isian khas benang (MD-02) — bukan gramasi/lebar</p>
                <div className="grid grid-cols-3 gap-2">
                  <div>
                    <label className="mb-1 block text-[10px] font-bold uppercase tracking-wide text-[#8E8E93]">Grade *</label>
                    <KNSelect data-testid="admin-product-grade-input" className="field"
                      value={product.grade ?? ""} placeholder="Pilih grade"
                      onValueChange={(v) => set({ grade: v })} options={options("grade")} />
                  </div>
                  <div>
                    <label className="mb-1 block text-[10px] font-bold uppercase tracking-wide text-[#8E8E93]">
                      Nomor Benang {req("yarn_count") ? "*" : ""}
                    </label>
                    <input data-testid="admin-product-yarn_count-input" className="field"
                      placeholder="mis. 30s / 150D" value={product.yarn_count ?? ""}
                      onChange={(e) => set({ yarn_count: e.target.value })} />
                  </div>
                  <div>
                    <label className="mb-1 block text-[10px] font-bold uppercase tracking-wide text-[#8E8E93]">Sistem Nomor</label>
                    <KNSelect data-testid="admin-product-yarn_count_system-input" className="field"
                      value={product.yarn_count_system ?? ""} placeholder="Ne / Nm / Denier / Tex"
                      onValueChange={(v) => set({ yarn_count_system: v })}
                      options={options("yarn_count_system")} />
                  </div>
                </div>
                <div className="grid grid-cols-4 gap-2">
                  <div>
                    <label className="mb-1 block text-[10px] font-bold uppercase tracking-wide text-[#8E8E93]">Bahan benang</label>
                    <KNSelect data-testid="admin-product-yarn_material-input" className="field"
                      value={product.yarn_material ?? ""} placeholder="katun / poliester…"
                      onValueChange={(v) => set({ yarn_material: v })} options={options("yarn_material")} />
                  </div>
                  <div>
                    <label className="mb-1 block text-[10px] font-bold uppercase tracking-wide text-[#8E8E93]">Ply</label>
                    <input data-testid="admin-product-yarn_ply-input" className="field" placeholder="1 / 2"
                      value={product.yarn_ply ?? ""} onChange={(e) => set({ yarn_ply: e.target.value })} />
                  </div>
                  <div>
                    <label className="mb-1 block text-[10px] font-bold uppercase tracking-wide text-[#8E8E93]">Puntiran</label>
                    <KNSelect data-testid="admin-product-yarn_twist-input" className="field"
                      value={product.yarn_twist ?? ""} placeholder="S / Z"
                      onValueChange={(v) => set({ yarn_twist: v })} options={options("yarn_twist")} />
                  </div>
                  <div>
                    <label className="mb-1 block text-[10px] font-bold uppercase tracking-wide text-[#8E8E93]">Status celup</label>
                    <KNSelect data-testid="admin-product-yarn_dye_status-input" className="field"
                      value={product.yarn_dye_status ?? ""} placeholder="mentah / celup"
                      onValueChange={(v) => set({ yarn_dye_status: v })} options={options("yarn_dye_status")} />
                  </div>
                </div>
              </div>
            )}
            <div>
              <label className="mb-1 block text-[10px] font-bold uppercase tracking-wide text-[#8E8E93]">
                Warna
              </label>
              <PantoneFinder triggerTestId="admin-product-color-input"
                value={product.color_code} valueName={product.color_name || product.color}
                valueHex={product.color_hex}
                onSelect={(c) => set({ color_code: c.code, color_name: c.name, color_hex: c.hex, color: c.name })}
                label="Pilih warna dari pustaka…" />
            </div>

            {missing.length > 0 ? (
              <p data-testid="admin-product-domain-missing"
                className="flex items-start gap-1 text-[11px] font-semibold text-[#D14343]">
                <AlertTriangle size={12} className="mt-0.5 shrink-0" />
                Wajib dilengkapi untuk stage “{labelOf("stage", stage)}”: {missing.map(lbl).join(", ")}.
              </p>
            ) : (
              <p data-testid="admin-product-domain-ok"
                className="flex items-center gap-1 text-[11px] font-semibold text-[#1E7B34]">
                <CheckCircle2 size={12} /> Kelengkapan domain untuk stage “{labelOf("stage", stage)}” terpenuhi.
              </p>
            )}
            {advisory.length > 0 && (
              <p data-testid="admin-product-domain-advisory"
                className="flex items-start gap-1 text-[11px] text-[#8C4A00]">
                <Info size={12} className="mt-0.5 shrink-0" />
                Disarankan (tidak memblokir{fabric === "knit" ? " — knit dikendalikan kg" : ""}): {advisory.map(lbl).join(", ")}.
              </p>
            )}
          </>
        )}
      </div>

      {/* ── Kepemilikan / Eksklusivitas (PS-20 · "PO sendiri") ──────────────── */}
      <div data-testid="admin-product-exclusivity-panel"
        className="grid gap-2 rounded-md border border-[#E6DCFA] bg-[#F8F5FF] p-2.5">
        <p className="text-[11px] font-bold uppercase tracking-wide text-[#6D4AC0]">
          Kepemilikan Produk
        </p>
        <div className="flex gap-1.5" role="group" aria-label="Eksklusivitas produk">
          <button type="button" data-testid="admin-product-excl-umum"
            onClick={() => set({ exclusivity: "umum", owner_sales_ids: [] })}
            className={`flex-1 rounded-md border px-2.5 py-1.5 text-[12px] font-semibold transition ${
              !isExclusive
                ? "border-[#6D4AC0] bg-[#6D4AC0] text-white"
                : "border-[#DcD3F0] bg-white text-[#6E6E73] hover:border-[#B9A6E8]"}`}>
            Umum (semua sales)
          </button>
          <button type="button" data-testid="admin-product-excl-exclusive"
            onClick={() => set({ exclusivity: "sales_tertentu" })}
            className={`flex-1 rounded-md border px-2.5 py-1.5 text-[12px] font-semibold transition ${
              isExclusive
                ? "border-[#6D4AC0] bg-[#6D4AC0] text-white"
                : "border-[#DcD3F0] bg-white text-[#6E6E73] hover:border-[#B9A6E8]"}`}>
            Eksklusif (sales tertentu)
          </button>
        </div>
        {isExclusive && (
          <div data-testid="admin-product-owner-picker" className="grid gap-1.5">
            <p className="text-[11px] text-[#6E6E73]">
              Pilih sales pemilik. Hanya mereka (dan admin/manajer) yang dapat <b>melihat</b> &
              <b> membuat SO</b> untuk produk ini — sales lain tidak melihat kodenya.
            </p>
            {salesOwners.length === 0 ? (
              <p className="text-[11px] text-[#8C4A00]">
                Daftar sales belum termuat (butuh hak akses admin).
              </p>
            ) : (
              <div className="grid grid-cols-2 gap-1.5">
                {salesOwners.map((s) => {
                  const checked = ownerIds.includes(s.id);
                  return (
                    <label key={s.id} data-testid={`admin-product-owner-${s.id}`}
                      className={`flex cursor-pointer items-center gap-2 rounded-md border px-2 py-1.5 text-[12px] transition ${
                        checked ? "border-[#6D4AC0] bg-white" : "border-[#EAE3F7] bg-white hover:border-[#C9BAF0]"}`}>
                      <input type="checkbox" checked={checked} onChange={() => toggleOwner(s.id)}
                        className="h-3.5 w-3.5 accent-[#6D4AC0]" />
                      <span className="truncate font-medium text-[#1D1D1F]">{s.name}</span>
                    </label>
                  );
                })}
              </div>
            )}
            {ownerIds.length === 0 && salesOwners.length > 0 && (
              <p data-testid="admin-product-owner-warning"
                className="flex items-center gap-1 text-[11px] font-semibold text-[#D14343]">
                <AlertTriangle size={12} /> Pilih minimal 1 sales pemilik untuk produk eksklusif.
              </p>
            )}
          </div>
        )}
      </div>

      <p className="-mt-0.5 text-[11px] text-[#6B6B73]">
        <b>Satuan Dasar</b>: 1 produk = 1 satuan untuk semua roll-nya. Tiap roll beda <b>panjang</b>,
        bukan beda satuan. POS menjual per satuan dasar (tampil “X roll / Y {product.base_unit || "meter"}”).
      </p>
      {kgPerMeter > 0 ? (
        <p data-testid="admin-product-kgm-info" className="-mt-0.5 text-[11px] text-[#3A7D44]">
          Catch-weight aktif: 1 {product.base_unit || "meter"} ≈ {kgPerMeter.toFixed(3)} kg
          <span className="text-[#8E8E93]"> (kg/m = gramasi × lebar ÷ 1000) · unit “kg” tersedia di penjualan</span>
        </p>
      ) : (
        <p data-testid="admin-product-kgm-info" className="-mt-0.5 text-[11px] text-[#8E8E93]">
          Isi Gramasi (gsm) & Lebar (meter) untuk mengaktifkan penjualan per “kg” (catch-weight).
        </p>
      )}

      {/* Gambar & deskripsi */}
      <div data-testid="admin-product-media" className="space-y-2 rounded-md border border-[#EFF0F2] bg-[#FAFBFC] p-2.5">
        <p className="text-[11px] font-bold uppercase tracking-wide text-[#8E8E93]">Gambar Varian & Deskripsi</p>
        <div className="flex gap-2.5">
          {product.image ? (
            <img data-testid="admin-product-image-preview" src={product.image} alt="preview varian"
              className="h-16 w-16 shrink-0 rounded-md border border-[#EFF0F2] object-cover" />
          ) : (
            <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-md border border-dashed border-[#D9DBE0] text-[10px] text-[#B0B2BA]">
              Tanpa gambar
            </div>
          )}
          <input data-testid="admin-product-image-input" className="field flex-1"
            placeholder="URL gambar varian (https://...)" value={product.image ?? ""}
            onChange={(e) => set({ image: e.target.value })} />
        </div>
        <textarea data-testid="admin-product-description-input" className="field min-h-[70px] resize-y"
          placeholder="Deskripsi produk (mis. komposisi, motif, perawatan) — tampil di popup detail POS"
          value={product.description ?? ""} onChange={(e) => set({ description: e.target.value })} />
      </div>

      {/* Konversi UOM */}
      <div data-testid="admin-product-uom-editor" className="rounded-md border border-[#EFF0F2] bg-[#FAFBFC] p-2.5">
        <div className="flex items-center justify-between">
          <p className="text-[11px] font-bold uppercase tracking-wide text-[#8E8E93]">Isi roll standar produk ini (konversi khusus)</p>
          <button type="button" data-testid="admin-product-add-conv-button" className="secondary-button" onClick={addConv}>
            <Plus size={13} /> Konversi
          </button>
        </div>
        {(product.uom_conversions || []).length === 0 && (
          <p className="mt-1 text-[11px] text-[#6B6B73]">
            Belum ada konversi khusus. Konversi umum (meter↔yard↔cm) sudah otomatis dari tab Satuan & Konversi;
            kg otomatis bila gramasi & lebar terisi. Isi di sini hanya bila produk ini punya isi roll standar
            (mis. 1 roll = 50 yard) supaya POS/gudang bisa menghitung roll ↔ yard.
          </p>
        )}
        {(product.uom_conversions || []).map((c, i) => (
          <div key={i} className="mt-2 grid grid-cols-[1fr_1fr_1fr_30px] items-center gap-1.5">
            <input data-testid={`admin-product-conv-from-${i}`} className="field" placeholder="Dari (mis. roll)"
              value={c.from_unit} onChange={(e) => updateConv(i, "from_unit", e.target.value)} />
            <input data-testid={`admin-product-conv-to-${i}`} className="field" placeholder="Ke (mis. yard)"
              value={c.to_unit} onChange={(e) => updateConv(i, "to_unit", e.target.value)} />
            <DecimalInput data-testid={`admin-product-conv-factor-${i}`} placeholder="Isi (mis. 50)"
              min={0} value={c.factor} onChange={(v) => updateConv(i, "factor", v)} />
            <button type="button" data-testid={`admin-product-conv-remove-${i}`} className="icon-button"
              onClick={() => removeConv(i)} aria-label="Hapus konversi"><XCircle size={14} /></button>
          </div>
        ))}
      </div>

      {productError && (
        <p data-testid="admin-product-error" className="text-[12px] font-semibold text-[#D14343]">{productError}</p>
      )}
      <div className="flex gap-2">
        <button data-testid="admin-create-product-button" className="primary-button"
          disabled={saving} onClick={onSave}>
          <Save size={14} /> {saving ? "Menyimpan…" : editingProductId ? "Simpan Perubahan" : "Simpan Produk"}
        </button>
        {editingProductId && (
          <button data-testid="admin-cancel-edit-product-button" className="secondary-button" onClick={onCancel}>
            Batal Ubah
          </button>
        )}
      </div>
    </div>
  );
}
