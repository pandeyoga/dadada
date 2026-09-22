import KNDatePicker from "@/components/KNDatePicker";
import { useState, useEffect, useCallback, useMemo } from "react";
import MoneyInput from "@/components/MoneyInput";
import { RefreshCw, Settings, Plus, Save, ShieldCheck, UserCog, Check, AlertTriangle, ChevronUp, ChevronDown, Filter } from "lucide-react";
import CategoryManager from "./CategoryManager";
import IntegrationsPanel from "./IntegrationsPanel";
import GeminiIntegrationPanel from "./GeminiIntegrationPanel";
import PermissionMatrixRecords from "./PermissionMatrixRecords";
import { auditActionLabel } from "../../config/auditLabels";   // X-2
import KNSelect from "../../components/KNSelect";
import FormModal from "../../components/FormModal";
import UomConversionView from "./uom/UomConversionView";
import ProductMasterForm from "./products/ProductMasterForm";
import LineFilter from "../../components/LineFilter";   // FASE L — chip penyaring lini
import ProductLifecycleCell from "../rnd/ProductLifecycleCell";
import axios, { API } from "../../services/apiClient";
import { formatCurrency } from "../../utils/formatters";
import { productMatches, supplierCodesLabel } from "../../utils/productSearch";   // MD-08
import { useEntityScope } from "../../context/EntityScopeContext";
import { scopeSuffix } from "../../utils/entityLabel";
// INV-ROLE-01 — wewenang layar dibaca dari IZIN pengguna, bukan nama peran.
import { can } from "../../config/roles";

export default function AdminView({
  data,
  uoms,
  templates,
  permissions,
  previewHtml,
  auditLogs,
  auditFilters,
  setAuditFilters,
  onAdminCreate,
  onAdminPatch,
  onAdminDelete,
  onImportMaster,
  onExportMaster,
  onUpdatePermissions,
  onPreviewTemplate,
  onRefreshAudit,
  onShowDetail,
  onSeedDemo,
  onReload,   // FASE F — muat ulang data master setelah produk dirilis ke produksi
  currentUser,
  only,   // opsional: array tab id (mis. ["products"]) untuk embed master data di domain hub
}) {
  const [tab, setTab] = useState(Array.isArray(only) && only.length ? only[0] : "products");
  // FASE E-3 (user story 7) — di mode "Semua Entitas" pembuatan data DIMATIKAN
  // (pelanggan ber-badan-usaha). Master bersama (produk/UOM/template/gudang)
  // tetap boleh karena tidak punya kolom badan usaha.
  const { canWrite, writeBlockHint,
    selectedEntity: scopeEntityId, entities: scopeEntities } = useEntityScope();
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [categories, setCategories] = useState([]);
  const [salesOwners, setSalesOwners] = useState([]);   // PS-20 — daftar sales utk produk eksklusif
  const loadCategories = useCallback(async () => {
    try {
      const res = await axios.get(`${API}/product-categories`);
      setCategories(Array.isArray(res.data) ? res.data : []);
    } catch (_) { /* non-blocking: form produk fallback ke daftar baku */ }
  }, []);
  useEffect(() => { loadCategories(); }, [loadCategories]);
  const loadSalesOwners = useCallback(async () => {
    /**
     * AUDIT PERAN (2026-08-15) — JANGAN memanggil apa yang tak boleh dipakai.
     * `GET /products/sales-owners` digerbang `product.update` (hanya admin — sengaja,
     * supaya daftar akun sales tidak bocor). Peran manajer membuka Master Produk
     * hanya untuk MELIHAT, jadi panggilan ini dulu selalu 403 lalu ditelan `catch`:
     * bersih di layar, tetapi setiap pembukaan layar meninggalkan 403 di jaringan &
     * log server, dan audit peran menandainya sebagai "panel mati" tiap kali dijalankan.
     * Pemilih "pemilik produk eksklusif" pun hanya dirender bagi yang boleh menyunting.
     */
    if (!can(currentUser?.permissions || {}, "product", "update")) {
      setSalesOwners([]);
      return;
    }
    try {
      const res = await axios.get(`${API}/products/sales-owners`);
      setSalesOwners(Array.isArray(res.data) ? res.data : []);
    } catch (_) { /* non-blocking: hanya admin (product:update) yang berhak */ }
  }, [currentUser]);
  useEffect(() => { loadSalesOwners(); }, [loadSalesOwners]);
  // Opsi dropdown kategori (aktif saja) untuk form produk; fallback 7 kategori baku.
  const categoryOptions = (categories.length
    ? categories.filter((c) => c.status === "active")
    : ["Batik", "Tenun", "Lurik", "Songket", "Ulos", "Jumputan", "Endek"].map((n) => ({ name: n })))
    .map((c) => ({ value: c.name, label: c.name }));
  // Fase A (PS-01/02/03/09) — field domain tekstil wajib ada di state form.
  const [product, setProduct] = useState({ sku: "", name: "", category: "Batik", variant: "Regular", color: "", color_code: "", color_name: "", color_hex: "", stage: "finished", fabric_type: "woven", line_code: "", yarn_count: "", yarn_count_system: "", motif: "", grade: "A", supplier: "", base_unit: "meter", price: 0, gramasi: 0, lebar: 0, image: "", description: "", uom_conversions: [] });
  const [savingProduct, setSavingProduct] = useState(false);
  const [editingProductId, setEditingProductId] = useState(null);
  const [productError, setProductError] = useState("");
  const [customer, setCustomer] = useState({ name: "", pic_name: "", phone: "", city: "Jakarta", address: "", npwp: "", credit_limit: 0, sales_pic: "" });
  const [entity, setEntity] = useState({ legal_name: "", short_name: "", type: "PT", npwp: "", address: "", city: "Bandung", default_tax_mode: "ppn", doc_prefix: "", logo_url: "" });
  // FASE U (D1) — master satuan kini membawa `aliases`: kata satuan yang BENAR-BENAR
  // tersimpan di dokumen (`yard`, `kg`, `meter`, `panel`). Tanpa alias, baris master
  // tidak pernah cocok dengan isi dokumen sehingga menambah satuan tidak mengubah
  // apa pun di layar. `factor_per_document` = satuan yang faktornya boleh ditulis
  // per baris dokumen (keputusan pemilik: panjang 1 panel berbeda per pesanan).
  const [showImportExport, setShowImportExport] = useState(false);
  const [uom, setUom] = useState({ code: "", name: "", base_type: "length", precision: 2, factor_to_base: 1, aliases: "", factor_per_document: false });
  const [template, setTemplate] = useState({ document_type: "surat_jalan", name: "", header: "Kain Nusantara", footer: "", columns: "SKU,Nama Barang,Qty,Unit", logo_url: "", paper_size: "A4", orientation: "portrait", margin_mm: 12, signature_left: "Dibuat Oleh", signature_right: "Disetujui Oleh", section_order: ["header", "customer", "items", "allocation", "signature", "footer"] });
  const [userForm, setUserForm] = useState({ name: "", email: "", role: "sales", password: "demo12345", home_entity_id: "", allowed_entity_ids: [] });
  // FASE L — penyaring lini pada Master Produk. Daftar `records` sudah datang
  // ter-pagar dari server (`line_scope` di GET /api/products); chip ini hanya
  // mempersempit tampilan, jadi tidak ada pintu kedua yang bisa berbeda arti.
  const [lineFilter, setLineFilter] = useState("");
  const [importFile, setImportFile] = useState(null);
  const [importPreview, setImportPreview] = useState(null);
  const [importLoading, setImportLoading] = useState(false);

  // Sub-fase 1.13 — helper form produk (uom_conversions + create/edit)
  const emptyProduct = { sku: "", name: "", category: "Batik", variant: "Regular", color: "", color_code: "", color_name: "", color_hex: "", stage: "finished", fabric_type: "woven", line_code: "", yarn_count: "", yarn_count_system: "", motif: "", grade: "A", supplier: "", base_unit: "meter", price: 0, gramasi: 0, lebar: 0, image: "", description: "", uom_conversions: [], exclusivity: "umum", owner_sales_ids: [] };
  const resetProductForm = () => { setProduct(emptyProduct); setEditingProductId(null); setProductError(""); };
  const updateConv = (idx, key, val) => setProduct({
    ...product,
    uom_conversions: (product.uom_conversions || []).map((c, i) => i === idx ? { ...c, [key]: val } : c),
  });
  const addConv = () => setProduct({ ...product, uom_conversions: [...(product.uom_conversions || []), { from_unit: "", to_unit: product.base_unit || "meter", factor: 0 }] });
  const removeConv = (idx) => setProduct({ ...product, uom_conversions: (product.uom_conversions || []).filter((_, i) => i !== idx) });
  // Sub-fase 1.13 — validasi konversi: unit wajib diisi, factor > 0, from != to.
  const validateConversions = () => {
    const rows = product.uom_conversions || [];
    for (let i = 0; i < rows.length; i++) {
      const from = String(rows[i].from_unit || "").trim();
      const to = String(rows[i].to_unit || "").trim();
      const factor = Number(rows[i].factor);
      if (!from || !to) return `Konversi #${i + 1}: unit "Dari" dan "Ke" wajib diisi.`;
      if (from.toLowerCase() === to.toLowerCase()) return `Konversi #${i + 1}: unit "Dari" dan "Ke" tidak boleh sama.`;
      if (!(factor > 0)) return `Konversi #${i + 1}: faktor harus lebih besar dari 0.`;
    }
    return "";
  };
  const saveProduct = async () => {
    const err = validateConversions();
    if (err) { setProductError(err); return; }
    setProductError(""); setSavingProduct(true);
    // Fase A — form TIDAK direset bila server menolak (mis. GSM/fabric_type belum
    // lengkap) supaya isian pengguna tidak hilang & pesan validasi terbaca.
    const res = editingProductId
      ? await onAdminPatch("products", editingProductId, product)
      : await onAdminCreate("products", product);
    setSavingProduct(false);
    if (res && res.ok === false) { setProductError(res.error || "Gagal menyimpan produk."); return; }
    resetProductForm();
    setShowCreateForm(false);   // sukses → modal ditutup (bukan berpindah diam-diam ke mode Buat)
  };
  const loadProductForEdit = (row) => {
    setProduct({
      sku: row.sku || "", name: row.name || "", category: row.category || "", variant: row.variant || "",
      color: row.color || "", color_code: row.color_code || "", color_name: row.color_name || "", color_hex: row.color_hex || "",
      stage: row.stage || "finished", fabric_type: row.fabric_type || "",
      line_code: row.line_code || "",          // FASE L — lini kerja MD
      yarn_count: row.yarn_count || "", yarn_count_system: row.yarn_count_system || "",
      motif: row.motif || "", grade: row.grade || "", supplier: row.supplier || "",
      base_unit: row.base_unit || "meter", price: Number(row.price || 0), hpp: Number(row.hpp || 0), hpp_source: row.hpp_source || "",
      gramasi: Number(row.gramasi || 0), lebar: Number(row.lebar || 0), image: row.image || "", description: row.description || "", uom_conversions: row.uom_conversions || [],
      exclusivity: row.exclusivity || "umum", owner_sales_ids: row.owner_sales_ids || [],
    });
    setEditingProductId(row.id);
    setShowCreateForm(true);  // F3 — buka form saat Edit (sebelumnya tetap tertutup)
  };

  // FASE G-0 — tab "Pengaturan" DIHAPUS dari sini. Seluruh setting kini hanya ada di
  // "Pusat Pengaturan" (menu tetangga pada hub yang sama) supaya tidak ada dua form
  // yang bisa menyimpan kunci yang sama dengan cara berbeda.
  // FASE E-3 — tab "Entities" & "Users" DIHAPUS dari sini. Keduanya pindah ke layar
  // "Badan Usaha & Akses" (satu pintu). Dulu formulir di sini bisa mengetik
  // `home_entity_id` bebas sehingga bertentangan dengan data HR, dan tidak punya
  // pagar kunci prefix / pratinjau dampak arsip. Dua pintu untuk satu urusan =
  // aturan yang berlaku tergantung pintu mana yang dipakai.
  // FASE E-4 (E4.1) — tab "Warehouse" DIHAPUS dari sini. Gudang kini punya aturan
  // pemakaian per badan usaha (bersama / khusus + pagar agar stok tidak terkurung),
  // dan formulir generik di sini tidak punya pagar itu: gudang bisa lahir tanpa mode.
  // Satu pintu saja → layar "Gudang (Master)" (`features/wms/warehouses`).
  const ALL_TABS = [
    ["products", "Produk"], ["categories", "Kategori"], ["customers", "Pelanggan"], ["uoms", "Satuan (UOM)"], ["integrations", "Integrasi AI"], ["templates", "Template Dokumen"], ["permissions", "Hak Akses"], ["audit", "Jejak Audit"],
  ];
  const TAB_SINGULAR = { products: "Produk", customers: "Pelanggan", uoms: "Satuan", templates: "Template Dokumen" };
  const SECTION_LABEL = { header: "Kop surat", customer: "Data pelanggan", items: "Daftar barang", allocation: "Alokasi roll", signature: "Tanda tangan", footer: "Catatan kaki" };
  const tabLabel = Object.fromEntries(ALL_TABS);
  const statusLabel = (row) => ((row.status || (row.active === false ? "inactive" : "active")) === "inactive" ? "nonaktif" : "aktif");
  const isInactive = (row) => statusLabel(row) === "nonaktif";
  const tabs = Array.isArray(only) && only.length ? ALL_TABS.filter(([id]) => only.includes(id)) : ALL_TABS;
  // Embedded (1 tab): sembunyikan header + tab-bar internal — konteks sudah dari HubTabs + PageMeta.
  const embedded = Array.isArray(only) && only.length === 1;
  const currentResource = tab === "templates" ? "templates" : tab;
  // FASE E-3 — daftar record per tab. Dulu memakai rantai ternary yang JATUH ke
  // `users` untuk tab yang tidak dikenal, sehingga tab "Integrasi AI" menampilkan
  // daftar pengguna. Sekarang eksplisit: tab tanpa daftar mengembalikan [].
  // Tab `users` & `entities` SUDAH TIDAK ADA di sini (pindah ke "Badan Usaha & Akses"),
  // jadi prop `users`/`entities` pun tidak lagi diterima komponen ini.
  const RECORDS_BY_TAB = {
    products: data.products, customers: data.customers,
    uoms, templates,
  };
  const records = RECORDS_BY_TAB[tab] || [];

  // FASE L — penyaring lini pada Master Produk. WAJIB dideklarasikan SETELAH
  // `records` (dulu di atasnya → TDZ "Cannot access before initialization" yang
  // membuat seluruh halaman Produk & Harga blank di bundle produksi).
  const [productQuery, setProductQuery] = useState("");   // MD-08 — cari kode KN / kode pabrik
  const AUDIT_PAGE = 50;   // X-2 — render bertahap, bukan 500 baris sekaligus
  const [auditShown, setAuditShown] = useState(AUDIT_PAGE);
  const visibleRecords = useMemo(() => {
    let rows = records;
    if (tab === "products" && lineFilter) {
      const want = lineFilter.split(",").map((s) => s.trim()).filter(Boolean);
      rows = (rows || []).filter((r) => want.includes(String(r.line_code || "")));
    }
    if (tab === "products" && productQuery.trim()) rows = (rows || []).filter((r) => productMatches(r, productQuery));
    return rows;
  }, [records, tab, lineFilter, productQuery]);

  const handleDryRunImport = async () => {
    if (!importFile) return;
    setImportLoading(true);
    const result = await onImportMaster(currentResource, importFile, true);
    setImportPreview(result);
    setImportLoading(false);
  };

  const emptyCustomer = { name: "", pic_name: "", phone: "", city: "Jakarta", address: "", npwp: "", credit_limit: 0, sales_pic: "" };
  const emptyUom = { code: "", name: "", base_type: "length", factor_to_base: 1, precision: 2, aliases: "", factor_per_document: false };
  const [modalBusy, setModalBusy] = useState(false);
  const modalSubmit = {
    customers: async () => {
      const r = await onAdminCreate("customers", customer);
      if (r?.ok) { setCustomer(emptyCustomer); setShowCreateForm(false); }
    },
    uoms: async () => {
      const r = await onAdminCreate("uoms", { ...uom, aliases: String(uom.aliases || "").split(",").map((a) => a.trim()).filter(Boolean) });
      if (r?.ok) { setUom(emptyUom); setShowCreateForm(false); }   // tutup & kosongkan supaya tidak tercipta duplikat
    },
    templates: async () => {
      const r = await onAdminCreate("document-templates", { ...template, columns: template.columns.split(",").map((c) => c.trim()).filter(Boolean) });
      if (r?.ok) setShowCreateForm(false);
    },
    audit: () => { onRefreshAudit(); setShowCreateForm(false); },
  }[tab];
  const modalSubmitDisabled = {
    customers: !canWrite || !customer.name.trim(),
    uoms: !uom.code || !uom.name || !(uom.factor_to_base > 0),
    templates: !template.document_type.trim() || !template.name.trim(),
    audit: false,
  }[tab] ?? false;
  const modalSubmitLabel = { customers: "Simpan Pelanggan", uoms: "Simpan Satuan", templates: "Simpan Template", audit: "Terapkan Filter" }[tab];
  const runModalSubmit = async () => {
    if (!modalSubmit) return;
    setModalBusy(true);
    try { await modalSubmit(); } finally { setModalBusy(false); }
  };

  const moveSection = (section, direction) => {
    const next = [...template.section_order];
    const index = next.indexOf(section);
    const target = index + direction;
    if (target < 0 || target >= next.length) return;
    [next[index], next[target]] = [next[target], next[index]];
    setTemplate({ ...template, section_order: next });
  };

  return (
    <div data-testid="admin-view">
      {!embedded && (
      <section className="section-card mb-3">
        <div className="section-head">
          <div className="flex items-center gap-3 min-w-0">
            <span className="kicker">Admin Master Data</span>
            <h2>Kelola produk · pelanggan · satuan · template dokumen · hak akses · jejak audit</h2>
          </div>
          {onSeedDemo && (
            <button
              data-testid="admin-seed-demo-button"
              onClick={onSeedDemo}
              className="ml-auto secondary-button text-orange-700 border-orange-200 hover:bg-orange-50"
              title="Reset database & isi ulang dengan demo data (DESTRUCTIVE)"
            >
              <RefreshCw size={13} /> Reset Demo Data
            </button>
          )}
        </div>
        <div className="flex flex-wrap gap-1.5 px-3 pb-3" role="tablist">
          {tabs.map(([id, label]) => <button key={id} type="button" role="tab" aria-selected={tab === id} data-testid={`admin-tab-${id}-button`} className={`tab-pill inline-flex items-center gap-1.5 ${tab === id ? "active" : ""}`} onClick={() => setTab(id)}><Settings size={13} /> {label}</button>)}
        </div>
      </section>
      )}
      {tab === "categories" && <CategoryManager onChanged={loadCategories} />}
      {tab === "integrations" && <div className="grid gap-3"><IntegrationsPanel /><GeminiIntegrationPanel /></div>}
      {tab !== "categories" && tab !== "integrations" && (
      <section className="flex flex-col gap-3">
        {/* FASE P4 — form master data menjadi POP-UP. Tombolnya kini di ATAS daftar
            (dulu menempati kolom kiri 360px yang tampak sebagai panel kosong besar). */}
        {tab !== "permissions" && (
          <button
            data-testid="toggle-admin-create-form-button"
            className="secondary-button self-start"
            onClick={() => setShowCreateForm(true)}
          >
            {tab === "audit" ? <><Filter size={14} /> Filter Jejak Audit</> : <><Plus size={14} /> Buat {TAB_SINGULAR[tab] || "Data"}</>}
          </button>
        )}
        <FormModal
          open={showCreateForm}
          onClose={() => setShowCreateForm(false)}
          title={tab === "audit" ? "Filter Jejak Audit" : editingProductId && tab === "products" ? `Ubah ${TAB_SINGULAR[tab]}` : `Buat ${TAB_SINGULAR[tab] || "Data Master"}`}
          subtitle={tab === "products" ? "Data induk produk. Harga di sini = harga dasar untuk pesanan BARU; pesanan yang sudah dibuat tidak berubah."
            : tab === "audit" ? "Persempit jejak audit berdasarkan pelaku, modul, aksi, dan rentang tanggal."
            : `Isian ${TAB_SINGULAR[tab] || "data master"} baru.`}
          icon={tab === "audit" ? Filter : Plus}
          size="md"
          testId="admin-create-form"
          onSubmit={modalSubmit ? runModalSubmit : null}
          submitLabel={modalSubmitLabel}
          submitDisabled={modalSubmitDisabled}
          busy={modalBusy}
          submitTestId={{ customers: "admin-create-customer-button", uoms: "admin-create-uom-button", templates: "admin-create-template-button", audit: "refresh-audit-button" }[tab] || ""}
        >
          {tab === "products" && (
            <ProductMasterForm
              product={product}
              setProduct={setProduct}
              editingProductId={editingProductId}
              productError={productError}
              saving={savingProduct}
              categoryOptions={categoryOptions}
              salesOwners={salesOwners}
              onSave={saveProduct}
              onCancel={resetProductForm}
              addConv={addConv}
              updateConv={updateConv}
              removeConv={removeConv}
            />
          )}
          {tab === "customers" && <div className="grid gap-2">
            {[["name", "Nama pelanggan"], ["pic_name", "Nama PIC"], ["phone", "Telepon"], ["city", "Kota"], ["address", "Alamat"], ["npwp", "NPWP"], ["sales_pic", "Sales penanggung jawab"]].map(([key, ph]) => (
              <label key={key} className="grid gap-1 text-[11px] font-semibold text-[#3C3C43]">{ph}{key === "name" ? " *" : ""}
                <input data-testid={`admin-customer-${key}-input`} className="field" placeholder={ph} value={customer[key]} onChange={(e) => setCustomer({ ...customer, [key]: e.target.value })} />
              </label>
            ))}
            <label className="grid gap-1 text-[11px] font-semibold text-[#3C3C43]">Batas kredit
              <MoneyInput testId="admin-customer-credit_limit-input" className="field" placeholder="Batas kredit" value={customer.credit_limit} onChange={(v) => setCustomer({ ...customer, credit_limit: Number(v) || 0 })} />
            </label>
            {!canWrite && <p data-testid="admin-customer-scope-note" className="text-[10.5px] text-[#8C4A00]">{writeBlockHint}</p>}
          </div>}
          {tab === "uoms" && <div className="grid gap-2.5" data-testid="admin-uom-form">
            <p className="text-[11px] text-[#6B6B73]">Satuan dasar yang dipakai stok, PO, SO, dan POS. Faktor ke satuan dasar menentukan konversi tetap (mis. 1 yard = 0,9144 meter). Konversi khusus per produk (isi 1 roll) diisi di Master Produk.</p>
            <div className="grid gap-2 sm:grid-cols-2">
              <label className="grid gap-1 text-[11px] font-semibold text-[#3C3C43]">Kode satuan *
                <input data-testid="admin-uom-code-input" className="field" placeholder="mis. PANEL" value={uom.code} onChange={(e) => setUom({ ...uom, code: e.target.value.toUpperCase() })} /></label>
              <label className="grid gap-1 text-[11px] font-semibold text-[#3C3C43]">Nama satuan *
                <input data-testid="admin-uom-name-input" className="field" placeholder="mis. Panel" value={uom.name} onChange={(e) => setUom({ ...uom, name: e.target.value })} /></label>
              <label className="grid gap-1 text-[11px] font-semibold text-[#3C3C43]">Dimensi *
                <KNSelect data-testid="admin-uom-base_type-input" className="field" value={uom.base_type} placeholder="Pilih dimensi"
                  onValueChange={(v) => setUom({ ...uom, base_type: v })}
                  options={[{ value: "length", label: "Panjang (dasar: meter)" }, { value: "weight", label: "Berat (dasar: kg)" }, { value: "count", label: "Hitungan (dasar: pcs)" }]} /></label>
              <label className="grid gap-1 text-[11px] font-semibold text-[#3C3C43]">Faktor ke satuan dasar *
                <input data-testid="admin-uom-factor_to_base-input" className="field" type="number" step="any" min="0" placeholder="mis. 0.9144 untuk yard" value={uom.factor_to_base} onChange={(e) => setUom({ ...uom, factor_to_base: Number(e.target.value) })} /></label>
              <label className="grid gap-1 text-[11px] font-semibold text-[#3C3C43]">Angka desimal
                <input data-testid="admin-uom-precision-input" className="field" type="number" min="0" max="6" value={uom.precision} onChange={(e) => setUom({ ...uom, precision: Number(e.target.value) })} /></label>
              <label className="grid gap-1 text-[11px] font-semibold text-[#3C3C43]">Alias (dipisah koma)
                <input data-testid="admin-uom-aliases-input" className="field" placeholder="mis. panel, pnl"
                  title="Kata satuan yang tersimpan di dokumen. Tanpa alias, satuan ini tidak akan dikenali dokumen yang sudah ada."
                  value={uom.aliases} onChange={(e) => setUom({ ...uom, aliases: e.target.value })} /></label>
            </div>
            <label className="flex items-center gap-2 text-[11.5px] text-[#3C3C43]">
              <input data-testid="admin-uom-factor-per-document-input" type="checkbox"
                checked={!!uom.factor_per_document}
                onChange={(e) => setUom({ ...uom, factor_per_document: e.target.checked })} />
              Faktor berbeda per dokumen (mis. panjang 1 panel berbeda tiap pesanan)
            </label>
          </div>}
          {tab === "templates" && <div className="grid gap-2">
            <div className="grid gap-2 sm:grid-cols-2">
              {[["document_type", "Tipe dokumen", "mis. surat_jalan / invoice"], ["name", "Nama template", "mis. Template SJ Standard"], ["header", "Kop / header", "Kain Nusantara"], ["footer", "Catatan kaki", "Terima kasih"], ["columns", "Kolom (pisahkan koma)", "SKU,Nama Barang,Qty,Unit"], ["logo_url", "URL logo", "https://…"], ["margin_mm", "Margin (mm)", "12"], ["signature_left", "Tanda tangan kiri", "Dibuat Oleh"], ["signature_right", "Tanda tangan kanan", "Disetujui Oleh"]].map(([key, label, ph]) => (
                <label key={key} className={`grid gap-1 text-[11px] font-semibold text-[#3C3C43] ${["columns", "logo_url"].includes(key) ? "sm:col-span-2" : ""}`}>{label}{["document_type", "name"].includes(key) ? " *" : ""}
                  <input data-testid={`admin-template-${key}-input`} className="field" type={key === "margin_mm" ? "number" : "text"} min={key === "margin_mm" ? 0 : undefined} placeholder={ph} value={template[key]} onChange={(e) => setTemplate({ ...template, [key]: key === "margin_mm" ? Number(e.target.value) : e.target.value })} />
                </label>
              ))}
              <label className="grid gap-1 text-[11px] font-semibold text-[#3C3C43]">Ukuran kertas
                <KNSelect data-testid="admin-template-paper_size-input" className="field" value={template.paper_size}
                  options={[{ value: "A4", label: "A4" }, { value: "A5", label: "A5" }, { value: "Letter", label: "Letter" }, { value: "F4", label: "F4 / Folio" }]} onValueChange={(v) => setTemplate({ ...template, paper_size: v })} />
              </label>
              <label className="grid gap-1 text-[11px] font-semibold text-[#3C3C43]">Orientasi
                <KNSelect data-testid="admin-template-orientation-input" className="field" value={template.orientation}
                  options={[{ value: "portrait", label: "Tegak (portrait)" }, { value: "landscape", label: "Mendatar (landscape)" }]} onValueChange={(v) => setTemplate({ ...template, orientation: v })} />
              </label>
            </div>
            <div data-testid="template-section-order-editor" className="rounded-md border border-[#EFF0F2] bg-[#FAFBFC] p-2.5">
              <p className="mb-1.5 text-[11px] font-bold uppercase tracking-wide text-[#6B6B73]">Urutan bagian dokumen</p>
              {template.section_order.map((section) => <div key={section} data-testid={`template-section-${section}`} className="mb-1.5 flex items-center justify-between rounded-md bg-white px-2 py-1 text-[12px] font-semibold border border-[#EFF0F2]"><span>{SECTION_LABEL[section] || section}</span><span className="flex gap-1"><button type="button" aria-label="Naik" data-testid={`template-section-${section}-up-button`} className="icon-button" onClick={() => moveSection(section, -1)}><ChevronUp size={13} /></button><button type="button" aria-label="Turun" data-testid={`template-section-${section}-down-button`} className="icon-button" onClick={() => moveSection(section, 1)}><ChevronDown size={13} /></button></span></div>)}
            </div>
          </div>}
          {tab === "audit" && <div data-testid="audit-filter-panel" className="grid gap-2">
            <label className="grid gap-1 text-[11px] font-semibold text-[#3C3C43]">Pelaku
              <input data-testid="audit-actor-filter-input" className="field" placeholder="nama / email pelaku" value={auditFilters.actor} onChange={(e) => setAuditFilters({ ...auditFilters, actor: e.target.value })} /></label>
            <label className="grid gap-1 text-[11px] font-semibold text-[#3C3C43]">Modul / entitas
              <input data-testid="audit-module-filter-input" className="field" placeholder="mis. pengguna, pesanan" value={auditFilters.module} onChange={(e) => setAuditFilters({ ...auditFilters, module: e.target.value })} /></label>
            <label className="grid gap-1 text-[11px] font-semibold text-[#3C3C43]">Kunci aksi
              <input data-testid="audit-action-filter-input" className="field" placeholder="mis. masuk, buat" value={auditFilters.action} onChange={(e) => setAuditFilters({ ...auditFilters, action: e.target.value })} /></label>
            <div className="grid grid-cols-2 gap-2">
              <label className="grid gap-1 text-[11px] font-semibold text-[#3C3C43]">Dari tanggal
                <KNDatePicker data-testid="audit-date-from-input" placeholder="Dari" value={auditFilters.date_from} onChange={(v) => setAuditFilters({ ...auditFilters, date_from: v })} /></label>
              <label className="grid gap-1 text-[11px] font-semibold text-[#3C3C43]">Sampai tanggal
                <KNDatePicker data-testid="audit-date-to-input" placeholder="Sampai" min={auditFilters.date_from} value={auditFilters.date_to} onChange={(v) => setAuditFilters({ ...auditFilters, date_to: v })} /></label>
            </div>
          </div>}
        </FormModal>
        <div className="section-card">
          <div className="section-head flex items-center justify-between gap-2">
            <h2>{tab === "permissions" ? "Matriks Hak Akses per Peran" : tab === "audit" ? "Jejak Audit" : `Daftar ${tabLabel[tab] || "Data"}`}</h2>
            {tab === "permissions" && (
              <button data-testid="save-permissions-button" className="primary-button" onClick={() => onUpdatePermissions(permissions.matrix)}><ShieldCheck size={14} /> Simpan Hak Akses</button>
            )}
            {!["permissions", "audit", "integrations"].includes(tab) && (
              <button type="button" data-testid="admin-toggle-import-export" className="secondary-button text-[11px]"
                onClick={() => setShowImportExport((v) => !v)}>
                {showImportExport ? "Tutup Impor / Ekspor" : "Impor / Ekspor CSV"}
              </button>
            )}
          </div>
          <div className="section-body">
          {!["permissions", "audit", "integrations"].includes(tab) && showImportExport && <div data-testid="admin-import-export-panel" className="mb-3 grid gap-2 rounded-md border border-[#EFF0F2] bg-[#FAFBFC] p-2.5">
            <p className="text-[11px] font-bold uppercase tracking-wide text-[#6B6B73]">Impor / Ekspor massal — {tabLabel[tab] || currentResource}</p>
            <p className="text-[10.5px] text-[#6B6B73]">Unggah CSV/XLSX untuk membuat atau memperbarui banyak baris sekaligus. Gunakan <b>Pratinjau (dry-run)</b> dulu untuk melihat dampaknya tanpa menyimpan.</p>
            <input data-testid="admin-import-file-input" className="field" type="file" accept=".csv,.xlsx" onChange={(e) => setImportFile(e.target.files?.[0] || null)} />
            <div className="flex flex-wrap gap-1.5">
              <button data-testid="admin-dry-run-button" className="secondary-button" disabled={importLoading || !importFile} onClick={handleDryRunImport}>{importLoading ? "Memeriksa…" : "Pratinjau (dry-run)"}</button>
              <button data-testid="admin-import-button" className="secondary-button" disabled={!importFile} onClick={() => { onImportMaster(currentResource, importFile, false); setImportPreview(null); }}>Impor</button>
              <button data-testid="admin-export-csv-button" className="secondary-button" onClick={() => onExportMaster(currentResource, "csv")}>Ekspor CSV</button>
              {tab === "products" && (
                <button data-testid="admin-export-yarn-button" className="secondary-button" title="Katalog benang + kode versi supplier — untuk dibagikan ke pabrik"
                  onClick={() => onExportMaster("yarn", "csv")}>Ekspor Katalog Benang</button>
              )}
            </div>
            {importPreview && (
              <div data-testid="import-preview-result" className="rounded-md border border-[#EFF0F2] bg-white p-2 text-[11.5px]">
                <p className="font-bold mb-1">Pratinjau: {importPreview.total} baris</p>
                <p className="text-green-700 inline-flex items-center gap-1"><Check size={12} /> Akan dibuat: {importPreview.created}</p>
                <p className="text-blue-700">~ Akan diperbarui: {importPreview.updated}</p>
                {(importPreview.errors || []).length > 0 && (
                  <div className="mt-1 max-h-24 overflow-auto">
                    <p className="text-red-700 font-bold inline-flex items-center gap-1"><AlertTriangle size={12} /> {importPreview.errors.length} galat:</p>
                    {(importPreview.errors || []).map((e, i) => <p key={i} className="text-red-600 text-[10.5px]">{e}</p>)}
                  </div>
                )}
                <button data-testid="confirm-import-button" className="mt-1 primary-button text-[11px]" onClick={() => { onImportMaster(currentResource, importFile, false); setImportPreview(null); }}>Konfirmasi Impor</button>
              </div>
            )}
          </div>}
          {tab === "permissions" && <div className="grid gap-2">
            <p className="text-[11.5px] text-[#6B6B73]" data-testid="permission-matrix-hint">Klik pil izin untuk mengubahnya. Perubahan hanya tampil di layar sampai tombol <b>Simpan Hak Akses</b> ditekan.</p>
            <PermissionMatrixRecords matrix={permissions.matrix} onUpdatePermissions={onUpdatePermissions} />
          </div>}
          {tab === "audit" && <div data-testid="audit-history-records" className="grid gap-2">
            {(auditLogs || []).slice(0, auditShown).map((log) => <button data-testid={`audit-row-${log.id}`} key={log.id} className="rounded-md border border-[#EFF0F2] bg-[#FAFBFC] interactive-card p-2.5 text-left" onClick={() => onShowDetail({ title: auditActionLabel(log.action), body: `Dicatat oleh ${log.actor} pada ${log.entity_type}. Kunci aksi: ${log.action}`, facts: [{ label: "Sumber Daya", value: `${log.entity_type} · ${log.entity_id}` }, { label: "Badan Usaha", value: log.scope_entity_name || log.scope_entity_id || "Tingkat grup" }, { label: "Peran", value: log.role || "—" }, { label: "Waktu", value: new Date(log.timestamp).toLocaleString("id-ID") }], target: "admin", cta: "Tetap di Audit" })}><div className="flex flex-wrap items-center justify-between gap-2"><p className="text-[12.5px] font-semibold">{auditActionLabel(log.action)} <span className="text-[10px] font-mono font-normal text-[#9A9BA3]" title="kunci aksi">{log.action}</span></p><p className="text-[10.5px] font-semibold text-[#0058CC]">{new Date(log.timestamp).toLocaleString("id-ID")}</p></div><p className="mt-0.5 text-[11.5px] text-[#3C3C43]">{log.actor} • {log.entity_type} • {log.entity_id}{log.scope_entity_name ? ` • ${log.scope_entity_name}` : ""}</p><p className="mt-1 line-clamp-2 text-[10.5px] text-[#3C3C43]">{JSON.stringify(log.after ?? log.details ?? {}).slice(0, 240)}</p></button>)}
            {(auditLogs || []).length > auditShown && (
              <button data-testid="audit-show-more" className="secondary-button justify-self-center" onClick={() => setAuditShown((n) => n + AUDIT_PAGE)}>
                Tampilkan {Math.min(AUDIT_PAGE, (auditLogs || []).length - auditShown)} lagi ({auditShown} dari {(auditLogs || []).length})
              </button>
            )}
            {(auditLogs || []).length === 0 && <p data-testid="audit-empty" className="px-3 py-6 text-center text-[12px] text-[#6B6B73]">Tidak ada jejak audit untuk filter ini.</p>}
          </div>}
          {!['permissions', 'audit', 'integrations'].includes(tab) && <>
          <div className="grid gap-2">
            {tab === "products" && (
              <>
                <input data-testid="admin-products-search" className="field mb-1" value={productQuery}
                  onChange={(e) => setProductQuery(e.target.value)}
                  placeholder="Cari SKU / nama produk atau kode / nama versi supplier…" />
                <LineFilter value={lineFilter} onChange={setLineFilter} storageKey="admin-products"
                            allowed={currentUser?.allowed_line_codes} className="mb-1"
                            testId="admin-products-line-filter" />
              </>
            )}
            {visibleRecords.length === 0 && (
              <div data-testid={`admin-records-empty-${tab}`} className="px-3 py-8 text-center text-[12px] text-[#6B6B73]">Belum ada {(tabLabel[tab] || tab).toLowerCase()} {scopeSuffix(scopeEntities, scopeEntityId)}.</div>
            )}
            {visibleRecords.map((row) => (
              <div data-testid={`admin-record-${tab}-${row.id}`} key={row.id} role="button" tabIndex={0} className="rounded-md border border-[#EFF0F2] bg-[#FAFBFC] interactive-card flex flex-col gap-2 p-2.5 md:flex-row md:items-center md:justify-between" onClick={() => onShowDetail(tab === "products"
                ? {
                    title: row.name,
                    body: `${row.sku || "SKU —"}${row.category ? ` · ${row.category}` : ""}${row.variant ? ` · ${row.variant}` : ""}${row.description ? ` — ${row.description}` : ""}`,
                    facts: [
                      { label: "Harga Jual", value: Number(row.price) > 0 ? `${formatCurrency(row.price)} / ${row.base_unit || "unit"}` : "Belum diisi" },
                      { label: "HPP (dari pembelian)", value: Number(row.hpp) > 0 ? `${formatCurrency(row.hpp)} / ${row.base_unit || "unit"}` : "Belum ada penerimaan PO" },
                      { label: "Lini · Grade", value: `${row.line_code ? `Lini ${row.line_code}` : "Lini belum diisi"} · Grade ${row.grade || "—"}` },
                      { label: "Spesifikasi", value: row.stage === "yarn"
                        ? [row.yarn_count ? `${row.yarn_count}${row.yarn_count_system ? ` ${row.yarn_count_system}` : ""}` : null, row.yarn_material, row.yarn_ply ? `${row.yarn_ply} ply` : null, row.yarn_twist ? `puntiran ${row.yarn_twist}` : null, row.yarn_dye_status].filter(Boolean).join(" · ") || "benang —"
                        : [row.fabric_type, Number(row.gramasi) > 0 ? `${row.gramasi} gsm` : null, Number(row.lebar) > 0 ? `lebar ${row.lebar}` : null].filter(Boolean).join(" · ") || "—" },
                      { label: "Status", value: `${row.status || (row.active === false ? "inactive" : "active")} · tahap ${row.stage || "finished"}` },
                    ],
                  }
                : { title: row.name || row.legal_name || row.code || row.email, body: `${TAB_SINGULAR[tab] || "Data"} — gunakan tombol di baris ini untuk mengubah atau menonaktifkan.`, facts: [{ label: "Modul", value: tabLabel[tab] || tab }, { label: "Status", value: statusLabel(row) }] })}>
                <div className="min-w-0">
                  <p data-testid={`admin-record-title-${row.id}`} className="text-[12.5px] font-semibold truncate">{row.name || row.legal_name || row.code || row.email}</p>
                  <p data-testid={`admin-record-meta-${row.id}`} className="text-[11px] text-[#3C3C43] truncate">{tab === "uoms"
                    ? `${row.code} · ${{ length: "panjang", weight: "berat", count: "hitungan" }[row.base_type] || row.base_type || "—"} · 1 ${row.code} = ${row.factor_to_base ?? "?"} satuan dasar · ${row.precision ?? 2} desimal${(row.aliases || []).length ? ` · alias: ${row.aliases.join(", ")}` : ""}${row.factor_per_document ? " · faktor per dokumen" : ""}`
                    : <>{row.sku || row.code || row.document_type || row.role || row.short_name || row.city} • <span className={isInactive(row) ? "text-[#8E8E93]" : "text-[#1A7A3A]"}>{statusLabel(row)}</span>{tab === "products" ? supplierCodesLabel(row) : ""}</>}</p>
                  {tab === "products" && (
                    <div data-testid={`admin-product-domain-${row.id}`} className="mt-1 flex flex-wrap items-center gap-1">
                      <ProductLifecycleCell product={row}
                        canManage={["admin", "manager"].includes(currentUser?.role)}
                        onPatch={(id, patch) => onAdminPatch("products", id, patch)}
                        onDone={onReload} />
                      <span className="status-pill pill-muted">{row.stage || "finished"}</span>
                      <span className="status-pill pill-muted">{row.fabric_type || "fabric_type?"}</span>
                      {/* FASE L — lini kerja MD. Dibedakan warnanya dari `fabric_type`
                          supaya tidak terbaca sebagai dua nama untuk hal yang sama. */}
                      <span data-testid={`admin-product-line-${row.id}`} className="status-pill"
                        style={row.line_code ? { background: "#F3E9FA", color: "#6B219A" }
                                             : { background: "#F5F5F7", color: "#8E8E93" }}>
                        {row.line_code ? `Lini ${row.line_code}` : "Lini belum diisi"}
                      </span>
                      <span className="status-pill pill-success">Grade {row.grade || "—"}</span>
                      {Number(row.gramasi) > 0 && <span className="status-pill pill-muted tabular-nums">{row.gramasi} gsm</span>}
                      {row.needs_review && (
                        <span data-testid={`admin-product-needs-review-${row.id}`} className="status-pill pill-warning">
                          <AlertTriangle size={10} /> Perlu dilengkapi
                        </span>
                      )}
                      {row.exclusivity === "sales_tertentu" && (
                        <span data-testid={`admin-product-exclusive-${row.id}`}
                          className="status-pill" style={{ background: "#EDE6FB", color: "#6D4AC0" }}>
                          Eksklusif · {(row.owner_sales_ids || []).length} sales
                        </span>
                      )}
                    </div>
                  )}
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {tab === "products" && <button data-testid={`admin-edit-products-${row.id}-button`} className="secondary-button" onClick={(e) => { e.stopPropagation(); loadProductForEdit(row); window.scrollTo({ top: 0, behavior: "smooth" }); }}>Ubah</button>}
                  {!["products", "uoms"].includes(tab) && isInactive(row) && <button data-testid={`admin-update-${tab}-${row.id}-button`} className="secondary-button" onClick={(e) => { e.stopPropagation(); onAdminPatch(tab === "templates" ? "document-templates" : tab, row.id, { status: "active" }); }}>Aktifkan</button>}
                  {tab === "templates" && data.orders?.[0] && <button data-testid={`admin-preview-template-${row.id}-button`} className="secondary-button" onClick={(e) => { e.stopPropagation(); onPreviewTemplate(row.id, data.orders[0].id); }}>Pratinjau</button>}
                  {!isInactive(row) && <button data-testid={`admin-delete-${tab}-${row.id}-button`} className="danger-button" onClick={(e) => { e.stopPropagation(); onAdminDelete(tab === "templates" ? "document-templates" : tab, row.id); }}>Nonaktifkan</button>}
                </div>
              </div>
            ))}
          </div>
          {tab === "uoms" && (
            <div className="mt-4" data-testid="admin-uom-conversions-embed">
              <UomConversionView user={currentUser} products={data.products || []} />
            </div>
          )}
          {tab === "templates" && previewHtml && <iframe data-testid="template-live-preview-frame" title="Template Preview" className="mt-4 h-[480px] w-full rounded-md border border-[#EFF0F2] bg-white" srcDoc={previewHtml} />}
          </>}
          </div>
        </div>
      </section>
      )}
    </div>
  );
}
